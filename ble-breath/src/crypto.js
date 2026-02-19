'use strict';

/**
 * Rotating ephemeral key cryptography.
 *
 * Each 10-second window produces a unique AES-256-GCM key:
 *   key  = HKDF-SHA256(BREATH_SECRET, salt=window_uint32, info="breath-ble-v1")
 *   nonce = HMAC-SHA256(key, "nonce")[0:12]   ← deterministic, not transmitted
 *
 * Transmitted packet is therefore just:
 *   window_mod (2 B) | ciphertext (N B) | tag (8 B)
 *
 * Truncating the GCM tag to 8 bytes is intentional: this is a wellness /
 * proximity application, not a financial protocol.
 */

const { createHmac, hkdfSync, createCipheriv, createDecipheriv } = require('crypto');

const ALGORITHM   = 'aes-256-gcm';
const TAG_LEN     = 8;          // truncated GCM tag (64-bit)
const KEY_LEN     = 32;
const NONCE_LEN   = 12;         // GCM spec requires 12 bytes
const WINDOW_MS   = 10_000;     // key rotation interval
const HKDF_INFO   = Buffer.from('breath-ble-v1');

// ── internal helpers ────────────────────────────────────────────────────────

function windowNow() {
  return Math.floor(Date.now() / WINDOW_MS);
}

function deriveKey(secret, window) {
  const ikm  = Buffer.from(secret, 'utf8');
  const salt = Buffer.allocUnsafe(4);
  salt.writeUInt32LE(window >>> 0, 0);
  return Buffer.from(hkdfSync('sha256', ikm, salt, HKDF_INFO, KEY_LEN));
}

function deriveNonce(key) {
  return createHmac('sha256', key)
    .update('nonce')
    .digest()
    .subarray(0, NONCE_LEN);
}

// ── public API ───────────────────────────────────────────────────────────────

/**
 * Encrypt plaintext with the current window's ephemeral key.
 * @param {Buffer} plaintext
 * @param {string} secret   BREATH_SECRET
 * @returns {{ windowMod: number, ct: Buffer, tag: Buffer }}
 */
function encrypt(plaintext, secret) {
  const win   = windowNow();
  const key   = deriveKey(secret, win);
  const nonce = deriveNonce(key);

  const cipher = createCipheriv(ALGORITHM, key, nonce, { authTagLength: TAG_LEN });
  const ct     = Buffer.concat([cipher.update(plaintext), cipher.final()]);
  const tag    = cipher.getAuthTag();          // 8 bytes

  return { windowMod: win & 0xFFFF, ct, tag };
}

/**
 * Decrypt a received packet.  Tries current window ± 1 to absorb clock skew.
 * @param {Buffer} ct
 * @param {Buffer} tag
 * @param {number} windowMod   low 16 bits of sender's window
 * @param {string} secret
 * @returns {Buffer|null}  plaintext, or null on decryption failure
 */
function decrypt(ct, tag, windowMod, secret) {
  const baseWin = windowNow();

  // Candidate windows: recover full window from mod-65536 hint
  const candidates = [-1, 0, 1].map(d => {
    const full = (baseWin & ~0xFFFF) | windowMod;
    return full + d * 0x10000;
  });
  candidates.push(baseWin - 1, baseWin, baseWin + 1);

  for (const win of [...new Set(candidates)]) {
    const key   = deriveKey(secret, win);
    const nonce = deriveNonce(key);
    try {
      const decipher = createDecipheriv(ALGORITHM, key, nonce, { authTagLength: TAG_LEN });
      decipher.setAuthTag(tag);
      return Buffer.concat([decipher.update(ct), decipher.final()]);
    } catch (_) { /* wrong key or tampered — try next */ }
  }
  return null;
}

module.exports = { encrypt, decrypt, windowNow, WINDOW_MS };
