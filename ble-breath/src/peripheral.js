'use strict';

/**
 * BLE Peripheral — broadcasts an encrypted mood/breath advertisement.
 *
 * Uses @abandonware/bleno to emit manufacturer-specific data every BROADCAST_MS.
 * No device name, no service names, no identifiable strings in the advertisement.
 *
 * Advertisement structure:
 *   Flags         (mandatory, 3 bytes)
 *   Manufacturer  (2-byte company ID 0xFFFF + 19-byte encrypted packet)
 *
 * The broadcaster rotates its ephemeral key automatically because the key is
 * derived from floor(Date.now() / 10_000) — no explicit re-keying needed.
 */

const bleno = require('@abandonware/bleno');
const { encodePacket, toManufacturerData } = require('./payload');

const BROADCAST_MS = 10_000;

class Peripheral {
  /**
   * @param {string}   secret          BREATH_SECRET
   * @param {Function} getMood         () → { calm, stressed, joyful, tired, neutral }
   * @param {Function} getBreath       () → { rate, depth }
   * @param {Function} [onAdvertising] called when advertising starts/stops
   */
  constructor({ secret, getMood, getBreath, onAdvertising }) {
    this._secret        = secret;
    this._getMood       = getMood;
    this._getBreath     = getBreath;
    this._onAdvertising = onAdvertising ?? (() => {});
    this._timer         = null;
    this._advertising   = false;
    this._joyBorrowNext = false;   // set externally to inject joy-borrow flag once
  }

  // ── public ─────────────────────────────────────────────────────────────────

  start() {
    bleno.on('stateChange', state => {
      if (state === 'poweredOn') {
        this._advertise();
        this._timer = setInterval(() => this._advertise(), BROADCAST_MS);
      } else {
        bleno.stopAdvertising();
        this._advertising = false;
      }
    });
  }

  stop() {
    if (this._timer) clearInterval(this._timer);
    bleno.stopAdvertising();
    this._advertising = false;
  }

  /** Signal that the next broadcast should carry the joy-borrow flag. */
  requestJoyBorrow() {
    this._joyBorrowNext = true;
  }

  get isAdvertising() { return this._advertising; }

  // ── internal ────────────────────────────────────────────────────────────────

  _advertise() {
    const mood      = this._getMood();
    const breath    = this._getBreath();
    const joyBorrow = this._joyBorrowNext;
    this._joyBorrowNext = false;

    const pkt  = encodePacket(mood, breath, joyBorrow, this._secret);
    const mfrData = toManufacturerData(pkt);

    // bleno startAdvertisingWithEIRData: raw AD bytes
    // AD structure: Flags (3 B) + Manufacturer Specific (2+pkt.length B)
    const adData = Buffer.concat([
      // Flags AD: length=2, type=0x01, value=0x06 (LE General Discoverable | BR/EDR Not Supported)
      Buffer.from([0x02, 0x01, 0x06]),
      // Manufacturer Specific AD: length=1+mfrData.length, type=0xFF
      Buffer.from([1 + mfrData.length, 0xFF]),
      mfrData,
    ]);

    bleno.startAdvertisingWithEIRData(adData, Buffer.alloc(0), err => {
      this._advertising = !err;
      this._onAdvertising(!err);
    });
  }
}

module.exports = Peripheral;
