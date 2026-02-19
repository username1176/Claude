/**
 * MoodActions
 *
 * Central orchestrator.  Given a new mood vector, fires the appropriate
 * ambient responses — but only when silentMode is false.
 *
 * Thresholds (all configurable via THRESHOLDS export):
 *   tired    > 0.55  → dim screen 20 %
 *   stressed > 0.55  → play white noise
 *   dragging        → trigger coffee smart-plug (tired>0.4 AND stressed>0.4)
 *   joyful   > 0.80  → restore screen brightness (feeling good = wants light)
 *
 * Each transition is debounced: the action fires only when the mood crosses
 * the threshold and remains there for DEBOUNCE_MS.  Returning below the
 * threshold (with HYSTERESIS gap) undoes the action.
 */

import { dimScreen, restoreScreen, isDimmed } from './BrightnessService';
import { playWhiteNoise, stopWhiteNoise, isPlaying } from './WhiteNoiseService';
import { triggerCoffee, isDragging }               from './AutomationService';

export const THRESHOLDS = {
  tired:    0.55,
  stressed: 0.55,
  joyful:   0.80,
};

const HYSTERESIS  = 0.08;    // must drop below (threshold − hysteresis) to undo
const DEBOUNCE_MS = 4_000;   // mood must hold for 4 s before action fires

// Track active states
const _state = {
  tired:    false,
  stressed: false,
  dragging: false,
};

// Pending debounce timers
const _timers = {};

function debounce(key, fn, ms) {
  clearTimeout(_timers[key]);
  _timers[key] = setTimeout(fn, ms);
}

function cancelDebounce(key) {
  clearTimeout(_timers[key]);
  delete _timers[key];
}

/**
 * Call this every time a new matched mood arrives.
 *
 * @param {object}  mood       { calm, stressed, joyful, tired, neutral }
 * @param {boolean} silent     if true, nothing fires
 * @param {Function} [onEvent] (eventName: string) → void  for UI feedback
 */
export function applyMood(mood, silent, onEvent) {
  if (silent) {
    // Cancel any pending debounces while in silent mode
    ['tired', 'stressed', 'dragging'].forEach(cancelDebounce);
    return;
  }

  // ── TIRED → dim screen ────────────────────────────────────────────────────

  if (mood.tired >= THRESHOLDS.tired) {
    if (!_state.tired) {
      debounce('tired_on', async () => {
        _state.tired = true;
        await dimScreen();
        onEvent?.('dim');
      }, DEBOUNCE_MS);
    }
  } else if (mood.tired < THRESHOLDS.tired - HYSTERESIS) {
    cancelDebounce('tired_on');
    if (_state.tired) {
      _state.tired = false;
      if (!_state.dragging) restoreScreen();
      onEvent?.('undim');
    }
  }

  // ── JOYFUL → restore if dimmed ────────────────────────────────────────────

  if (mood.joyful >= THRESHOLDS.joyful && isDimmed()) {
    debounce('joy_restore', async () => {
      await restoreScreen();
      onEvent?.('brightened');
    }, DEBOUNCE_MS / 2);
  }

  // ── STRESSED → white noise ────────────────────────────────────────────────

  if (mood.stressed >= THRESHOLDS.stressed) {
    if (!_state.stressed) {
      debounce('stressed_on', async () => {
        _state.stressed = true;
        await playWhiteNoise();
        onEvent?.('noise_on');
      }, DEBOUNCE_MS);
    }
  } else if (mood.stressed < THRESHOLDS.stressed - HYSTERESIS) {
    cancelDebounce('stressed_on');
    if (_state.stressed) {
      _state.stressed = false;
      stopWhiteNoise();
      onEvent?.('noise_off');
    }
  }

  // ── DRAGGING → coffee trigger ─────────────────────────────────────────────

  if (isDragging(mood)) {
    if (!_state.dragging) {
      debounce('dragging_on', async () => {
        _state.dragging = true;
        const result = await triggerCoffee();
        onEvent?.(`coffee_${result}`);
      }, DEBOUNCE_MS * 2);   // longer debounce for physical action
    }
  } else {
    cancelDebounce('dragging_on');
    _state.dragging = false;
  }
}

/**
 * Tear down all active effects (call on unmount or opt-out).
 */
export async function clearAllEffects() {
  ['tired_on', 'stressed_on', 'dragging_on', 'joy_restore'].forEach(cancelDebounce);
  _state.tired    = false;
  _state.stressed = false;
  _state.dragging = false;
  await Promise.allSettled([restoreScreen(), stopWhiteNoise()]);
}

export const getActiveStates = () => ({ ..._state });
