/**
 * BrightnessService
 *
 * Wraps the native BrightnessModule (Android + iOS) with a simple JS API.
 * dim()     — reduce current brightness by DIM_FRACTION (default 20 %)
 * restore() — undo the last dim
 *
 * Calls are no-ops if the native module is unavailable (simulator, web).
 */

import { NativeModules } from 'react-native';

const { BrightnessModule } = NativeModules;

const DIM_FRACTION = 0.20;   // 20 % reduction for 'tired' state

let _dimActive = false;

/**
 * Dim the screen by DIM_FRACTION.  Idempotent — won't double-dim.
 */
export async function dimScreen() {
  if (!BrightnessModule || _dimActive) return;
  try {
    await BrightnessModule.dimBy(DIM_FRACTION);
    _dimActive = true;
  } catch (_) { /* permission not granted or no activity */ }
}

/**
 * Restore brightness to what it was before dimScreen().
 */
export async function restoreScreen() {
  if (!BrightnessModule || !_dimActive) return;
  try {
    await BrightnessModule.restoreBrightness();
    _dimActive = false;
  } catch (_) {}
}

/**
 * Read current brightness (0–1).  Returns null on error.
 */
export async function getBrightness() {
  if (!BrightnessModule) return null;
  try {
    return await BrightnessModule.getBrightness();
  } catch (_) { return null; }
}

export const isDimmed = () => _dimActive;
