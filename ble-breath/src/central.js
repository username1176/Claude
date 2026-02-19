'use strict';

/**
 * BLE Central — scans for mood broadcasts and handles resonance.
 *
 * For each advertisement received:
 *   1. Extract manufacturer-data bytes.
 *   2. Decrypt with rotating ephemeral key (BREATH_SECRET).
 *      → If decryption fails: silently discard (wrong network / tampered).
 *   3. Compare remote breath vector against local breath vector (±5%).
 *      → No match: discard.
 *   4. On match:
 *        a. Trigger local haptic MATCH pulse.
 *        b. If remote.joyBorrow: trigger WARMTH pulse (100 ms) immediately.
 *        c. If remote.mood.joyful > JOY_THRESHOLD: set joy-borrow flag on
 *           peripheral so next broadcast carries the request, triggering the
 *           remote device's WARMTH response.
 *
 * Privacy: noble reports peripheral addresses; we deliberately never store
 * or log them.  Only the transient resonance check matters.
 */

const noble = require('@abandonware/noble');
const { decodePacket, fromManufacturerData } = require('./payload');
const { breathMatches }                       = require('./breath');
const { pulse, PULSE }                        = require('./haptic');

const JOY_THRESHOLD  = 0.80;    // joy value above which we send a joy-borrow
const WARMTH_COOLDOWN_MS = 30_000;  // avoid warmth-spam: one per 30 s per "peer"
const COMPANY_ID     = 0xFFFF;

class Central {
  /**
   * @param {string}     secret          BREATH_SECRET
   * @param {Function}   getBreath       () → { rate, depth }
   * @param {object}     [peripheral]    Peripheral instance (for joy-borrow)
   */
  constructor({ secret, getBreath, peripheral }) {
    this._secret      = secret;
    this._getBreath   = getBreath;
    this._peripheral  = peripheral ?? null;
    // Track last warmth emission time per "peer fingerprint" to rate-limit.
    // Fingerprint = resonanceScore bucket, deliberately lossy — no real ID.
    this._warmthSent  = new Map();
  }

  // ── public ──────────────────────────────────────────────────────────────────

  start() {
    noble.on('stateChange', state => {
      if (state === 'poweredOn') {
        // duplicates=true so we keep receiving fresh broadcasts from same device
        noble.startScanning([], true);
      } else {
        noble.stopScanning();
      }
    });

    noble.on('discover', peripheral => this._onDiscover(peripheral));
  }

  stop() {
    noble.stopScanning();
  }

  // ── internal ────────────────────────────────────────────────────────────────

  _onDiscover(adv) {
    // Pull raw manufacturer data — noble exposes it as a Buffer
    const mfrRaw = adv.advertisement?.manufacturerData;
    if (!mfrRaw) return;

    const pkt = fromManufacturerData(mfrRaw);
    if (!pkt) return;   // different company ID or version

    // Decrypt — returns null for wrong key (wrong network) or tampered payload
    const decoded = decodePacket(pkt, this._secret);
    if (!decoded) return;

    const { mood, breath: remotBreath, joyBorrow } = decoded;
    const localBreath = this._getBreath();

    // Breath-signature gate: ±5 % on every dimension
    if (!breathMatches(localBreath, remotBreath)) return;

    // ── Resonance detected ───────────────────────────────────────────────────

    pulse(PULSE.MATCH);

    // Joy-borrow received: emit warmth pulse locally (100 ms)
    if (joyBorrow) {
      setTimeout(() => pulse(PULSE.WARMTH), 50);
    }

    // High joy on remote: request that our next broadcast carries joy-borrow
    // so the remote device receives warmth on its next scan cycle.
    if (mood.joyful >= JOY_THRESHOLD && this._peripheral) {
      if (!this._joyBorrowCooledDown()) return;
      this._peripheral.requestJoyBorrow();
      pulse(PULSE.JOY);
      this._markWarmthSent();
    }
  }

  // Rate-limit joy-borrow emissions (global, not per-peer — no peer tracking)
  _joyBorrowCooledDown() {
    const last = this._warmthSent.get('global') ?? 0;
    return (Date.now() - last) >= WARMTH_COOLDOWN_MS;
  }

  _markWarmthSent() {
    this._warmthSent.set('global', Date.now());
    // Expire old entries to avoid memory growth
    for (const [k, t] of this._warmthSent) {
      if (Date.now() - t > WARMTH_COOLDOWN_MS * 2) this._warmthSent.delete(k);
    }
  }
}

module.exports = Central;
