/**
 * HomeScreen
 *
 * The main ambient view.  Shows the MoodRing and handles all mood-driven
 * effects via MoodActions.  No numbers, no mood labels — just the ring.
 *
 * Wires together:
 *   useBleListener   → mood vector + joyBorrow
 *   useSilentMode    → silent flag + double-tap toggle
 *   MoodActions      → fires brightness / noise / coffee actions
 *   SilentModeGate   → wraps view, shows silent indicator
 */

import React, { useEffect, useCallback } from 'react';
import { StyleSheet, View, StatusBar } from 'react-native';

import { useBleListener }  from '../hooks/useBleListener';
import { useSilentMode }   from '../hooks/useSilentMode';
import { SilentModeGate }  from '../components/SilentModeGate';
import { MoodRing }        from '../components/MoodRing';
import { applyMood, clearAllEffects } from '../services/MoodActions';

// Placeholder local breath reading — in a real device, these come from
// the camera-based breathing detector or a wearable sensor.
const LOCAL_BREATH = { rate: 14.0, depth: 0.65 };

const NEUTRAL_MOOD = { calm: 0.2, stressed: 0.1, joyful: 0.1, tired: 0.1, neutral: 0.5 };

export function HomeScreen() {
  const { silent, toggle: toggleSilent } = useSilentMode(true);

  const secret = process.env.BREATH_SECRET ?? 'default';

  const { mood, resonance, joyBorrow, ready } = useBleListener({
    secret,
    localBreath: LOCAL_BREATH,
    enabled: true,
  });

  // Apply mood effects whenever mood or silent changes
  useEffect(() => {
    applyMood(mood, silent);
  }, [mood, silent]);

  // Clean up on unmount
  useEffect(() => () => { clearAllEffects(); }, []);

  // Joy borrow: pulse MoodRing briefly at full resonance (visual warmth)
  // Actual haptic is handled in ble-breath peripheral; here we just note it
  const displayMood = joyBorrow
    ? { ...mood, joyful: Math.min(1, (mood.joyful ?? 0) + 0.3) }
    : mood;

  return (
    <SilentModeGate silent={silent} onToggle={toggleSilent}>
      <StatusBar hidden />
      <View style={styles.root}>
        <MoodRing
          mood={displayMood}
          resonance={resonance}
          size={160}
        />
      </View>
    </SilentModeGate>
  );
}

const styles = StyleSheet.create({
  root: {
    flex:            1,
    backgroundColor: '#0A0A0A',
    alignItems:      'center',
    justifyContent:  'center',
  },
});
