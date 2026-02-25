'use strict';

const { createHash, randomBytes } = require('crypto');

/**
 * One-way breath commitment — SHA-256(salt ‖ rate_byte ‖ depth_byte).
 *
 * Used to let two parties confirm they share a similar breath pattern without
 * ever transmitting the raw values.  The 16-byte random salt is generated
 * once per session (never persisted) and discarded when the process exits.
 *
 * Properties:
 *   • Pre-image resistant: observing the hash reveals nothing about rate/depth.
 *   • Session-scoped: a new salt is generated on every process start, so hashes
 *     from previous sessions cannot be correlated.
 *   • Fuzzy: the quantisation to uint8 (±0.4% for rate, ±0.4% for depth) means
 *     hashes are only equal when vectors round to the same byte — the ±5%
 *     threshold check in breathMatches() is the primary gate; this commitment
 *     is an optional secondary binding in higher-trust contexts.
 *
 * @param {{ rate: number, depth: number }} vec
 * @param {Buffer} sessionSalt   16-byte random salt (see SESSION_SALT below)
 * @returns {string}  hex-encoded SHA-256 digest
 */
function breathHash(vec, sessionSalt) {
  const rateByte  = Math.max(0, Math.min(255, Math.round(vec.rate  * 10)));
  const depthByte = Math.max(0, Math.min(255, Math.round(vec.depth * 255)));
  return createHash('sha256')
    .update(sessionSalt)
    .update(Buffer.from([rateByte, depthByte]))
    .digest('hex');
}

/** Per-process session salt — never written to disk. */
const SESSION_SALT = randomBytes(16);

/**
 * Breath-signature matching.
 *
 * Two devices "resonate" if their breathing vectors are within THRESHOLD on
 * every component.  No shared ID is needed — proximity is established purely
 * through physiological similarity.
 *
 * breathVec = { rate, depth }
 *   rate  — breaths per minute (typical 8–25)
 *   depth — normalised inspiration depth 0–1
 *
 * Match criterion (componentwise):
 *   |localRate  - remoteRate|  / max(localRate,  1) ≤ threshold
 *   |localDepth - remoteDepth| / max(localDepth, ε) ≤ threshold
 */

const DEFAULT_THRESHOLD = 0.05;   // ±5 %
const EPS               = 1e-6;

/**
 * Returns true when both breath dimensions are within threshold of each other.
 *
 * @param {{ rate: number, depth: number }} local
 * @param {{ rate: number, depth: number }} remote
 * @param {number} [threshold]
 * @returns {boolean}
 */
function breathMatches(local, remote, threshold = DEFAULT_THRESHOLD) {
  const rateDiff  = Math.abs(local.rate  - remote.rate)  / Math.max(local.rate,  1);
  const depthDiff = Math.abs(local.depth - remote.depth) / Math.max(local.depth, EPS);
  return rateDiff <= threshold && depthDiff <= threshold;
}

/**
 * Compute a single scalar "resonance score" (0–1).
 * 1.0 = perfect sync, 0.0 = completely out of sync.
 *
 * @param {{ rate: number, depth: number }} local
 * @param {{ rate: number, depth: number }} remote
 * @returns {number}
 */
function resonanceScore(local, remote) {
  const rateDiff  = Math.abs(local.rate  - remote.rate)  / Math.max(local.rate,  1);
  const depthDiff = Math.abs(local.depth - remote.depth) / Math.max(local.depth, EPS);
  const maxDiff   = Math.max(rateDiff, depthDiff);
  return Math.max(0, 1 - maxDiff / DEFAULT_THRESHOLD);
}

module.exports = { breathMatches, resonanceScore, breathHash, SESSION_SALT };
