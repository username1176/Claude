/**
 * useSilentMode
 *
 * Silent mode: when active, all mood-driven actions are suppressed.
 * Toggled by a double-tap anywhere on the overlay.
 *
 * The hook persists the last-known preference via AsyncStorage so that
 * the app starts in the user's preferred mode after a restart.
 *
 * Returns:
 *   silent       — boolean
 *   toggle       — () => void   (call this on double-tap)
 *   setSilent    — (bool) => void
 */

import { useState, useEffect, useCallback } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';

const KEY = '@moodaura/silent';

export function useSilentMode(defaultSilent = true) {
  const [silent, setSilentState] = useState(defaultSilent);
  const [loaded, setLoaded]      = useState(false);

  // Hydrate from storage on mount
  useEffect(() => {
    AsyncStorage.getItem(KEY)
      .then(val => {
        if (val !== null) setSilentState(val === 'true');
      })
      .finally(() => setLoaded(true));
  }, []);

  const setSilent = useCallback((value) => {
    setSilentState(value);
    AsyncStorage.setItem(KEY, String(value));
  }, []);

  const toggle = useCallback(() => {
    setSilent(!silent);
  }, [silent, setSilent]);

  return { silent: loaded ? silent : defaultSilent, toggle, setSilent };
}
