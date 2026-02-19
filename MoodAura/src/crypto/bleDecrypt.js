'use strict';

/**
 * Mirrors the ble-breath crypto protocol exactly so this app can decode
 * advertisements without pairing or sharing keys out-of-band.
 *
 * Key schedule (identical to ble-breath/src/crypto.js):
 *   key   = HKDF-SHA256(BREATH_SECRET, salt=window_uint32LE, info="breath-ble-v1")
 *   nonce = HMAC-SHA256(key, "nonce")[0:12]   ← derived, never on wire
 *
 * Wire format (19 bytes manufacturer payload, after 2-byte company ID):
 *   [0]     version (must be 0x01)
 *   [1-2]   windowMod  uint16 LE
 *   [3-10]  ciphertext (8 bytes)
 *   [11-18] auth tag   (8 bytes, truncated GCM)
 *
 * Uses react-native-quick-crypto which exposes the same API as Node.js crypto,
 * including createDecipheriv with authTagLength and hkdfSync.
 */

import QuickCrypto from 'react-native-quick-crypto';

// ── constants (must match ble-breath/src/crypto.js) ─────────────────────────

const ALGORITHM  = 'aes-256-gcm';
const TAG_LEN    = 8;
const NONCE_LEN  = 12;
const KEY_LEN    = 32;
const WINDOW_MS  = 10_000;
const HKDF_INFO  = Buffer.from('breath-ble-v1', 'utf8');

const COMPANY_ID   = 0xFFFF;
const VERSION      = 0x01;
const CT_LEN       = 8;
const PACKET_LEN   = 1 + 2 + CT_LEN + TAG_LEN;    // 19
const MFR_MIN_LEN  = 2 + PACKET_LEN;               // 21

// ── pure-JS HKDF-SHA256 (extract + expand) ───────────────────────────────────
// Used as fallback if QuickCrypto.hkdfSync is unavailable.

function hmacSHA256(key, data) {
  return QuickCrypto.createHmac('sha256', key).update(data).digest();
}

function hkdf(ikm, salt, info, length) {
  // Extract
  const prk    = hmacSHA256(salt, ikm);
  // Expand
  const blocks = [];
  let prev     = Buffer.alloc(0);
  let i        = 1;
  while (blocks.reduce((s, b) => s + b.length, 0) < length) {
    prev = hmacSHA256(prk, Buffer.concat([prev, info, Buffer.from([i++])]));
    blocks.push(prev);
  }
  return Buffer.concat(blocks).subarray(0, length);
}

// ── key derivation ────────────────────────────────────────────────────────────

function windowNow() {
  return Math.floor(Date.now() / WINDOW_MS);
}

function deriveKey(secret, window) {
  const ikm  = Buffer.from(secret, 'utf8');
  const salt = Buffer.alloc(4);
  salt.writeUInt32LE(window >>> 0, 0);

  // Prefer native hkdfSync when available
  if (typeof QuickCrypto.hkdfSync === 'function') {
    return Buffer.from(QuickCrypto.hkdfSync('sha256', ikm, salt, HKDF_INFO, KEY_LEN));
  }
  return hkdf(ikm, salt, HKDF_INFO, KEY_LEN);
}

function deriveNonce(key) {
  return hmacSHA256(key, Buffer.from('nonce', 'utf8')).subarray(0, NONCE_LEN);
}

// ── packet parsing ────────────────────────────────────────────────────────────

/**
 * Extract the 19-byte ble-breath packet from raw manufacturer data.
 * manufacturerData is base64-encoded by react-native-ble-plx.
 *
 * @param {string|null} b64  device.manufacturerData from ble-plx
 * @returns {Buffer|null}
 */
export function extractPacket(b64) {
  if (!b64) return null;
  const buf = Buffer.from(b64, 'base64');
  if (buf.length < MFR_MIN_LEN) return null;
  if (buf.readUInt16LE(0) !== COMPANY_ID) return null;
  const pkt = buf.subarray(2, 2 + PACKET_LEN);
  if (pkt[0] !== VERSION) return null;
  return pkt;
}

// ── decryption ────────────────────────────────────────────────────────────────

/**
 * Decrypt a ble-breath packet.  Tries window ±1 to absorb clock skew.
 *
 * @param {Buffer} pkt    19-byte extracted packet
 * @param {string} secret BREATH_SECRET
 * @returns {{ mood, breath, joyBorrow }|null}
 */
export function decodePacket(pkt, secret) {
  if (!pkt || pkt.length < PACKET_LEN) return null;

  const windowMod = pkt.readUInt16LE(1);
  const ct        = pkt.subarray(3,          3 + CT_LEN);
  const tag       = pkt.subarray(3 + CT_LEN, 3 + CT_LEN + TAG_LEN);
  const base      = windowNow();

  const candidates = new Set([
    base - 1, base, base + 1,
    (base & ~0xFFFF) | windowMod,
    ((base & ~0xFFFF) | windowMod) - 0x10000,
    ((base & ~0xFFFF) | windowMod) + 0x10000,
  ]);

  for (const win of candidates) {
    const key   = deriveKey(secret, win);
    const nonce = deriveNonce(key);
    try {
      const dec = QuickCrypto.createDecipheriv(ALGORITHM, key, nonce, { authTagLength: TAG_LEN });
      dec.setAuthTag(tag);
      const pt = Buffer.concat([dec.update(ct), dec.final()]);
      return parsePlaintext(pt);
    } catch (_) { /* wrong window or tampered */ }
  }
  return null;
}

function parsePlaintext(pt) {
  if (pt.length < 8) return null;
  return {
    mood: {
      calm:     pt[0] / 255,
      stressed: pt[1] / 255,
      joyful:   pt[2] / 255,
      tired:    pt[3] / 255,
      neutral:  pt[4] / 255,
    },
    breath: {
      rate:  pt[5] / 10,
      depth: pt[6] / 255,
    },
    joyBorrow: !!(pt[7] & 0x01),
  };
}
