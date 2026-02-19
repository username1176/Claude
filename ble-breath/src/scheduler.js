'use strict';

/**
 * Single-adapter scheduler.
 *
 * Most laptops and embedded boards have one BLE HCI adapter.  Both noble
 * (central/scan) and bleno (peripheral/advertise) need exclusive access.
 *
 * Strategy — time-multiplex with a 10 s cycle:
 *
 *   ┌───────────────────────────────────────────────────────────────────┐
 *   │  0 s    ────── ADVERTISE 2 s ──────►  SCAN 8 s ──────► 10 s      │
 *   └───────────────────────────────────────────────────────────────────┘
 *
 * The 2-second advertising window is enough for nearby scanners to catch
 * the broadcast.  The 8-second scan window gives plenty of time to receive
 * and process incoming packets.
 *
 * If TWO HCI adapters are present (NOBLE_HCI_DEVICE_ID ≠ BLENO_HCI_DEVICE_ID),
 * set DUAL_ADAPTER=1 and this scheduler becomes a no-op — both run in parallel.
 */

const DUAL = !!process.env.DUAL_ADAPTER;

const ADV_MS  = 2_000;   // advertise window
const SCAN_MS = 8_000;   // scan window

class Scheduler {
  /**
   * @param {Peripheral} peripheral
   * @param {Central}    central
   */
  constructor(peripheral, central) {
    this._p     = peripheral;
    this._c     = central;
    this._timer = null;
    this._phase = 'scan';
  }

  start() {
    if (DUAL) {
      // Two adapters: run both simultaneously
      this._p.start();
      this._c.start();
      return;
    }

    // Single adapter: start scan first, then multiplex
    this._c.start();
    this._phase = 'scan';
    this._timer = setInterval(() => this._tick(), ADV_MS + SCAN_MS);

    // Kick off first cycle after SCAN_MS
    setTimeout(() => this._advertisePhase(), SCAN_MS);
  }

  stop() {
    if (this._timer) clearInterval(this._timer);
    this._p.stop();
    this._c.stop();
  }

  // ── internal ────────────────────────────────────────────────────────────────

  _tick() {
    this._advertisePhase();
  }

  _advertisePhase() {
    this._c.stop();
    this._p.start();
    this._phase = 'advertise';

    setTimeout(() => this._scanPhase(), ADV_MS);
  }

  _scanPhase() {
    this._p.stop();
    this._c.start();
    this._phase = 'scan';
  }
}

module.exports = Scheduler;
