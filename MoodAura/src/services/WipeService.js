/**
 * WipeService — PulseSync local-data kill switch.
 *
 * Clears every key MoodAura has ever written to AsyncStorage, stops all
 * active services, and resets the opt-in flag so the consent screen
 * reappears on the next launch.
 *
 * What is erased:
 *   @moodaura/opted_in       — consent flag
 *   @moodaura/silent         — silent-mode preference
 *   @moodaura/automation     — smart-plug backend + credentials
 *   @moodaura/prefs          — shared secret, breath calibration
 *
 * What was never stored (and therefore cannot be wiped):
 *   • Raw breath vectors (never written to disk)
 *   • Mood classifications (in-memory only, lost on restart)
 *   • Remote device addresses (never retained past a scan callback)
 *   • Sync history (derived from rotating ephemeral keys; keys not stored)
 *
 * Usage from JS:
 *   import { wipeAllLocalData } from '../services/WipeService';
 *   await wipeAllLocalData();   // then navigate to OptIn or call RNRestart
 *
 * Usage from the Settings screen: "Opt out & stop MoodAura" calls this.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import { clearAllEffects } from './MoodActions';

/** Every AsyncStorage key the app owns. */
const ALL_KEYS = [
  '@moodaura/opted_in',
  '@moodaura/silent',
  '@moodaura/automation',
  '@moodaura/prefs',
];

/**
 * Wipe all local data and stop all active services.
 *
 * Resolves to an audit object listing what was cleared — useful for
 * presenting confirmation UI without logging anything to a server.
 *
 * @returns {Promise<{ keysRemoved: string[], servicesCleared: string[] }>}
 */
export async function wipeAllLocalData() {
  // 1. Stop all ambient effects before touching storage.
  await clearAllEffects();
  const servicesCleared = ['brightness', 'whiteNoise', 'pendingDebounces'];

  // 2. Remove all known AsyncStorage keys atomically.
  await AsyncStorage.multiRemove(ALL_KEYS);

  // 3. Verify removal (belt-and-suspenders).
  const remaining = await AsyncStorage.multiGet(ALL_KEYS);
  const stillPresent = remaining.filter(([, v]) => v !== null).map(([k]) => k);
  if (stillPresent.length > 0) {
    // Force-null anything that survived
    await AsyncStorage.multiSet(stillPresent.map(k => [k, null]));
    await AsyncStorage.multiRemove(stillPresent);
  }

  return { keysRemoved: ALL_KEYS, servicesCleared };
}

/**
 * Convenience: wipe then trigger a full JS reload so no in-memory state
 * survives.  Requires react-native-restart or DevSettings.reload().
 *
 * Call this from the Settings screen's "Forget my pulse" button.
 */
export async function forgetPulseAndRestart() {
  await wipeAllLocalData();
  // Dynamically import to avoid making react-native-restart a hard dep.
  try {
    const { default: RNRestart } = await import('react-native-restart');
    RNRestart.restart();
  } catch (_) {
    // Fallback: reset navigation to OptIn screen; caller handles navigation.
  }
}
