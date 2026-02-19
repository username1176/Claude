'use strict';

/**
 * Haptic / LED output.
 *
 * Tries each backend in priority order and uses the first that succeeds.
 * All output is silent — no console emission during normal operation.
 *
 * Backends (in order):
 *   1. Custom command  — HAPTIC_CMD env var or --haptic-cmd CLI arg
 *   2. Linux LED sysfs — /sys/class/leds/<led>/brightness
 *   3. Linux vibrator  — /sys/class/leds/vibrator/activate (Android-style)
 *   4. GPIO write      — HAPTIC_GPIO_PIN env var → /sys/class/gpio/gpio<n>/value
 *   5. ANSI terminal   — dim flash via ANSI escape (visual feedback only)
 */

const fs    = require('fs');
const { execFile } = require('child_process');

// ── configuration ────────────────────────────────────────────────────────────

const LED_PATH     = process.env.HAPTIC_LED_PATH ?? '/sys/class/leds/input0::capslock/brightness';
const VIB_PATH     = '/sys/class/leds/vibrator/activate';
const GPIO_PIN     = process.env.HAPTIC_GPIO_PIN;
const CUSTOM_CMD   = process.env.HAPTIC_CMD;

// pulse types
const PULSE = {
  MATCH:  'match',    // breath resonance detected — medium pulse
  WARMTH: 'warmth',   // joy-borrow received — short gentle pulse
  JOY:    'joy',      // local high-joy, sending warmth — burst
};

// durations per type (ms)
const DURATION = {
  [PULSE.MATCH]:  250,
  [PULSE.WARMTH]: 100,
  [PULSE.JOY]:    150,
};

// ── backend implementations ───────────────────────────────────────────────────

function tryWrite(path, value) {
  try { fs.writeFileSync(path, String(value)); return true; }
  catch (_) { return false; }
}

function ledPulse(duration) {
  if (tryWrite(LED_PATH, '1')) {
    setTimeout(() => tryWrite(LED_PATH, '0'), duration);
    return true;
  }
  return false;
}

function vibratorPulse(duration) {
  if (tryWrite(VIB_PATH, String(Math.ceil(duration)))) {
    return true;
  }
  return false;
}

function gpioPulse(duration) {
  if (!GPIO_PIN) return false;
  const path = `/sys/class/gpio/gpio${GPIO_PIN}/value`;
  if (tryWrite(path, '1')) {
    setTimeout(() => tryWrite(path, '0'), duration);
    return true;
  }
  return false;
}

function customCmdPulse(type, duration) {
  if (!CUSTOM_CMD) return false;
  try {
    execFile(CUSTOM_CMD, [type, String(duration)], { timeout: 2000 });
    return true;
  } catch (_) { return false; }
}

// ANSI: invert terminal colours briefly — visible in a terminal session
function terminalPulse(type, duration) {
  process.stdout.write('\x1b[7m');         // reverse video on
  setTimeout(() => process.stdout.write('\x1b[27m'), duration);  // reverse video off
  return true;
}

// ── public API ────────────────────────────────────────────────────────────────

let _backend = null;

/**
 * Trigger a haptic/LED pulse.
 * @param {string} type  one of PULSE.*
 */
function pulse(type = PULSE.MATCH) {
  const dur = DURATION[type] ?? 200;

  if (_backend === 'custom'    && customCmdPulse(type, dur)) return;
  if (_backend === 'led'       && ledPulse(dur))              return;
  if (_backend === 'vibrator'  && vibratorPulse(dur))         return;
  if (_backend === 'gpio'      && gpioPulse(dur))             return;
  if (_backend === 'terminal'  && terminalPulse(type, dur))   return;

  // Auto-detect on first call
  if (CUSTOM_CMD                  && customCmdPulse(type, dur)) { _backend = 'custom';   return; }
  if (ledPulse(dur))                                            { _backend = 'led';      return; }
  if (vibratorPulse(dur))                                       { _backend = 'vibrator'; return; }
  if (GPIO_PIN && gpioPulse(dur))                               { _backend = 'gpio';     return; }
  terminalPulse(type, dur); _backend = 'terminal';
}

module.exports = { pulse, PULSE };
