'use strict';

/**
 * ble-breath — anonymous BLE mood resonance
 *
 * Usage:
 *   BREATH_SECRET=mysecret node index.js [options]
 *
 * Options:
 *   --rate   <n>      Breathing rate in breaths/min   (default: 14)
 *   --depth  <n>      Breath depth 0–1                (default: 0.65)
 *   --mood   <json>   Mood vector JSON string          (default: neutral)
 *   --haptic-cmd <cmd> Shell command to invoke on haptic events
 *   --dual            Force dual-adapter mode
 *   --sim             Simulation mode (no real BLE; prints matched packets)
 *
 * Environment:
 *   BREATH_SECRET        Shared passphrase (required; fallback: "default")
 *   HAPTIC_LED_PATH      Sysfs LED path
 *   HAPTIC_GPIO_PIN      GPIO pin number
 *   HAPTIC_CMD           Custom haptic shell command
 *   NOBLE_HCI_DEVICE_ID  HCI adapter index for noble   (default: 0)
 *   BLENO_HCI_DEVICE_ID  HCI adapter index for bleno   (default: 0)
 *   DUAL_ADAPTER         Set to 1 to run both roles simultaneously
 *
 * Mood JSON format (all values 0–1, should sum to ≈1):
 *   '{"calm":0.6,"stressed":0.1,"joyful":0.2,"tired":0.05,"neutral":0.05}'
 *
 * Privacy guarantees:
 *   • No device names or identifiers are transmitted.
 *   • No data is sent to any server.
 *   • Nothing is written to disk or logged.
 *   • Payload is authenticated-encrypted; wrong-network devices see noise.
 *   • Only devices whose local breath matches the sender's (±5%) respond.
 */

// ── suppress all third-party debug chatter ────────────────────────────────────
process.env.DEBUG = '';

const { pulse, PULSE } = require('./src/haptic');

// ── CLI / env parsing ─────────────────────────────────────────────────────────

function parseArgs() {
  const args = process.argv.slice(2);
  const get  = flag => {
    const i = args.indexOf(flag);
    return i >= 0 ? args[i + 1] : undefined;
  };
  const has = flag => args.includes(flag);

  return {
    rate:       parseFloat(get('--rate')  ?? 14),
    depth:      parseFloat(get('--depth') ?? 0.65),
    mood:       JSON.parse(get('--mood')  ?? 'null'),
    hapticCmd:  get('--haptic-cmd'),
    dual:       has('--dual'),
    sim:        has('--sim'),
    wipe:       has('--wipe'),
  };
}

const cfg = parseArgs();

// ── kill switch ───────────────────────────────────────────────────────────────
// node index.js --wipe
//
// ble-breath holds NO persistent state — every key is derived fresh from
// floor(Date.now()/10000) and every session salt is randomBytes(16).
// Restarting the process is sufficient to "forget" any pulse history.
// --wipe makes this contract explicit and machine-verifiable.
if (cfg.wipe) {
  // 1. Overwrite the in-process session salt (belt-and-suspenders).
  const { SESSION_SALT } = require('./src/breath');
  require('crypto').randomFillSync(SESSION_SALT);   // zero-knowledge overwrite

  // 2. Nothing else to clear — no files, no sockets, no DB.
  //    Print to stdout so shell scripts can confirm the wipe completed.
  process.stdout.write('pulse:wiped\n');
  process.exit(0);
}

if (cfg.hapticCmd) process.env.HAPTIC_CMD = cfg.hapticCmd;
if (cfg.dual)      process.env.DUAL_ADAPTER = '1';

const SECRET = process.env.BREATH_SECRET ?? 'default';

// ── live state (can be updated externally via IPC / stdin in future) ──────────

let _breath = { rate: cfg.rate, depth: cfg.depth };

let _mood = cfg.mood ?? {
  calm:     0.20,
  stressed: 0.10,
  joyful:   0.15,
  tired:    0.15,
  neutral:  0.40,
};

const getMood   = () => ({ ..._mood });
const getBreath = () => ({ ..._breath });

// ── allow mood + breath updates via newline-delimited JSON on stdin ───────────

if (!process.stdin.isTTY) {
  let buf = '';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', chunk => {
    buf += chunk;
    const lines = buf.split('\n');
    buf = lines.pop();
    for (const line of lines) {
      if (!line.trim()) continue;
      try {
        const update = JSON.parse(line);
        if (update.mood)   _mood   = { ..._mood,   ...update.mood };
        if (update.breath) _breath = { ..._breath, ...update.breath };
      } catch (_) { /* ignore malformed lines */ }
    }
  });
}

// ── simulation mode (no real BLE hardware needed) ────────────────────────────

if (cfg.sim) {
  const { encodePacket, decodePacket, toManufacturerData, fromManufacturerData } = require('./src/payload');
  const { breathMatches } = require('./src/breath');

  process.stdout.write('[sim] Starting simulation — transmit/receive loop\n');

  let tick = 0;
  const runTick = () => {
    tick++;
    const pkt    = encodePacket(getMood(), getBreath(), tick % 5 === 0, SECRET);
    const mfr    = toManufacturerData(pkt);
    const rawPkt = fromManufacturerData(mfr);
    const decoded = decodePacket(rawPkt, SECRET);

    if (!decoded) {
      process.stdout.write('[sim] ✗ decryption failed\n');
      return;
    }

    const matches = breathMatches(getBreath(), decoded.breath);
    const joyHigh = decoded.mood.joyful >= 0.80;
    const line = [
      `[sim] t=${tick * 10}s`,
      `calm=${(decoded.mood.calm * 100).toFixed(0)}%`,
      `joy=${(decoded.mood.joyful * 100).toFixed(0)}%`,
      `rate=${decoded.breath.rate.toFixed(1)}bpm`,
      `match=${matches}`,
      decoded.joyBorrow ? '♥ joy-borrow' : '',
      joyHigh           ? '✨ high-joy'   : '',
    ].filter(Boolean).join('  ');

    process.stdout.write(line + '\n');

    if (matches)            pulse(PULSE.MATCH);
    if (decoded.joyBorrow)  pulse(PULSE.WARMTH);
    if (joyHigh && matches) pulse(PULSE.JOY);
  };

  runTick();   // fire immediately, then every 10 s
  const loop = setInterval(runTick, 10_000);

  process.on('SIGINT', () => { clearInterval(loop); process.exit(0); });
  return;
}

// ── real BLE mode ─────────────────────────────────────────────────────────────

const Peripheral = require('./src/peripheral');
const Central    = require('./src/central');
const Scheduler  = require('./src/scheduler');

const peripheral = new Peripheral({
  secret:       SECRET,
  getMood,
  getBreath,
});

const central = new Central({
  secret:     SECRET,
  getBreath,
  peripheral,
});

const scheduler = new Scheduler(peripheral, central);
scheduler.start();

process.on('SIGINT',  () => { scheduler.stop(); process.exit(0); });
process.on('SIGTERM', () => { scheduler.stop(); process.exit(0); });
