/**
 * useBleListener
 *
 * Scans for ble-breath advertisements, decrypts each packet, checks the
 * breath-signature gate (±5 %), and returns the latest matched mood.
 *
 * Returns:
 *   mood          — { calm, stressed, joyful, tired, neutral }  (0–1 floats)
 *   breath        — { rate, depth }
 *   joyBorrow     — boolean: remote requested a warmth signal
 *   resonance     — float 0–1 (how closely breaths match)
 *   ready         — BLE adapter powered on
 *
 * The hook never stores device addresses or any persistent identifier.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { BleManager } from 'react-native-ble-plx';
import { extractPacket, decodePacket } from '../crypto/bleDecrypt';

const MATCH_THRESHOLD = 0.05;   // ±5 %

function breathMatches(local, remote) {
  const rateDiff  = Math.abs(local.rate  - remote.rate)  / Math.max(local.rate,  1);
  const depthDiff = Math.abs(local.depth - remote.depth) / Math.max(local.depth, 1e-6);
  return rateDiff <= MATCH_THRESHOLD && depthDiff <= MATCH_THRESHOLD;
}

function resonanceScore(local, remote) {
  const rateDiff  = Math.abs(local.rate  - remote.rate)  / Math.max(local.rate,  1);
  const depthDiff = Math.abs(local.depth - remote.depth) / Math.max(local.depth, 1e-6);
  return Math.max(0, 1 - Math.max(rateDiff, depthDiff) / MATCH_THRESHOLD);
}

const NEUTRAL_MOOD = { calm: 0.2, stressed: 0.1, joyful: 0.1, tired: 0.1, neutral: 0.5 };

export function useBleListener({ secret, localBreath, enabled = true }) {
  const [mood,      setMood]      = useState(NEUTRAL_MOOD);
  const [breath,    setBreath]    = useState({ rate: 0, depth: 0 });
  const [joyBorrow, setJoyBorrow] = useState(false);
  const [resonance, setResonance] = useState(0);
  const [ready,     setReady]     = useState(false);

  const managerRef = useRef(null);

  const handleDiscover = useCallback((device) => {
    const pkt = extractPacket(device.manufacturerData);
    if (!pkt) return;

    const decoded = decodePacket(pkt, secret);
    if (!decoded) return;

    if (!breathMatches(localBreath, decoded.breath)) return;

    setMood(decoded.mood);
    setBreath(decoded.breath);
    setJoyBorrow(decoded.joyBorrow);
    setResonance(resonanceScore(localBreath, decoded.breath));
  }, [secret, localBreath]);

  useEffect(() => {
    if (!enabled) return;

    const manager = new BleManager();
    managerRef.current = manager;

    const sub = manager.onStateChange(state => {
      if (state === 'PoweredOn') {
        setReady(true);
        manager.startDeviceScan(null, { allowDuplicates: true }, (err, device) => {
          if (err || !device) return;
          handleDiscover(device);
        });
      } else {
        setReady(false);
      }
    }, true);

    return () => {
      sub.remove();
      manager.stopDeviceScan();
      manager.destroy();
      managerRef.current = null;
    };
  }, [enabled, handleDiscover]);

  return { mood, breath, joyBorrow, resonance, ready };
}
