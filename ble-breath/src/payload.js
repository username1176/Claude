'use strict';

/**
 * Advertisement packet layout (19 bytes manufacturer data).
 *
 *  Offset  Len  Field
 *  ──────  ───  ─────────────────────────────────────────────────────────────
 *   0       1   version  (0x01)
 *   1       2   windowMod — sender's window & 0xFFFF  (uint16 LE)
 *   3       8   ciphertext  (8 bytes of AES-GCM output)
 *  11       8   auth tag    (truncated GCM tag, 8 bytes)
 *  ──────  ───
 *  Total  19 bytes  ← fits in 27-byte BLE manufacturer-data payload
 *
 * Plaintext layout (8 bytes):
 *
 *  Byte  Field
 *  ────  ────────────────────────────────────────────────────────────────────
 *   0    mood.calm      uint8  (0–255, normalised from [0,1])
 *   1    mood.stressed  uint8
 *   2    mood.joyful    uint8
 *   3    mood.tired     uint8
 *   4    mood.neutral   uint8
 *   5    breathRate     uint8  (breaths-per-minute × 10; range 0–25.5 BPM)
 *   6    breathDepth    uint8  (normalised inspiration depth, 0–255)
 *   7    flags          uint8  bit-0 = joy_borrow_request
 */

const { encrypt, decrypt } = require('./crypto');

const VERSION        = 0x01;
const COMPANY_ID     = 0xFFFF;   // 0xFFFF = test / no registered company
const PLAINTEXT_LEN  = 8;
const CT_LEN         = PLAINTEXT_LEN;   // AES-GCM: ciphertext same length as plaintext
const TAG_LEN        = 8;
const PACKET_LEN     = 1 + 2 + CT_LEN + TAG_LEN;   // 19

// ── encoding helpers ─────────────────────────────────────────────────────────

function toUint8(f) { return Math.max(0, Math.min(255, Math.round(f * 255))); }
function fromUint8(b) { return b / 255; }

/**
 * Build a 19-byte encrypted manufacturer-data buffer.
 *
 * @param {object} mood         { calm, stressed, joyful, tired, neutral }  (floats 0–1)
 * @param {object} breath       { rate, depth }  rate in BPM, depth 0–1
 * @param {boolean} joyBorrow   set the joy-borrow-request flag
 * @param {string}  secret      BREATH_SECRET
 * @returns {Buffer}
 */
function encodePacket(mood, breath, joyBorrow, secret) {
  const pt = Buffer.allocUnsafe(PLAINTEXT_LEN);
  pt[0] = toUint8(mood.calm     ?? 0);
  pt[1] = toUint8(mood.stressed ?? 0);
  pt[2] = toUint8(mood.joyful   ?? 0);
  pt[3] = toUint8(mood.tired    ?? 0);
  pt[4] = toUint8(mood.neutral  ?? 0);
  pt[5] = Math.max(0, Math.min(255, Math.round((breath.rate  ?? 0) * 10)));
  pt[6] = toUint8(breath.depth ?? 0);
  pt[7] = joyBorrow ? 0x01 : 0x00;

  const { windowMod, ct, tag } = encrypt(pt, secret);

  const pkt = Buffer.allocUnsafe(PACKET_LEN);
  pkt[0] = VERSION;
  pkt.writeUInt16LE(windowMod, 1);
  ct.copy(pkt, 3);
  tag.copy(pkt, 3 + CT_LEN);
  return pkt;
}

/**
 * Decode and authenticate a raw 19-byte manufacturer-data buffer.
 *
 * @param {Buffer} pkt    raw packet
 * @param {string} secret BREATH_SECRET
 * @returns {object|null}   decoded { mood, breath, joyBorrow } or null on failure
 */
function decodePacket(pkt, secret) {
  if (!Buffer.isBuffer(pkt) || pkt.length < PACKET_LEN) return null;
  if (pkt[0] !== VERSION) return null;

  const windowMod = pkt.readUInt16LE(1);
  const ct        = pkt.subarray(3,          3 + CT_LEN);
  const tag       = pkt.subarray(3 + CT_LEN, 3 + CT_LEN + TAG_LEN);

  const pt = decrypt(ct, tag, windowMod, secret);
  if (!pt) return null;

  return {
    mood: {
      calm:     fromUint8(pt[0]),
      stressed: fromUint8(pt[1]),
      joyful:   fromUint8(pt[2]),
      tired:    fromUint8(pt[3]),
      neutral:  fromUint8(pt[4]),
    },
    breath: {
      rate:  pt[5] / 10,
      depth: fromUint8(pt[6]),
    },
    joyBorrow: !!(pt[7] & 0x01),
  };
}

/**
 * Wrap packet in BLE manufacturer-data AD format:
 *   company_id_lo | company_id_hi | packet...
 */
function toManufacturerData(pkt) {
  const buf = Buffer.allocUnsafe(2 + pkt.length);
  buf.writeUInt16LE(COMPANY_ID, 0);
  pkt.copy(buf, 2);
  return buf;
}

/**
 * Extract our packet from a noble advertisement's manufacturerData field.
 * Returns null if the company ID or version don't match.
 */
function fromManufacturerData(mfr) {
  if (!Buffer.isBuffer(mfr) || mfr.length < 2 + PACKET_LEN) return null;
  if (mfr.readUInt16LE(0) !== COMPANY_ID) return null;
  const pkt = mfr.subarray(2, 2 + PACKET_LEN);
  if (pkt[0] !== VERSION) return null;
  return pkt;
}

module.exports = { encodePacket, decodePacket, toManufacturerData, fromManufacturerData };
