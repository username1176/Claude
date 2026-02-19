/**
 * useOptIn
 *
 * Per-device opt-in gate.  Until the user explicitly opts in, no BLE scanning
 * starts and no mood actions fire.  Stored in AsyncStorage.
 *
 * Returns:
 *   optedIn    — boolean
 *   optIn      — () => void
 *   optOut     — () => void
 *   loading    — boolean (true while reading storage)
 */

import { useState, useEffect, useCallback } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';

const KEY = '@moodaura/opted_in';

export function useOptIn() {
  const [optedIn, setOptedIn] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    AsyncStorage.getItem(KEY)
      .then(val => setOptedIn(val === 'true'))
      .finally(() => setLoading(false));
  }, []);

  const optIn = useCallback(() => {
    setOptedIn(true);
    AsyncStorage.setItem(KEY, 'true');
  }, []);

  const optOut = useCallback(() => {
    setOptedIn(false);
    AsyncStorage.setItem(KEY, 'false');
  }, []);

  return { optedIn, optIn, optOut, loading };
}
