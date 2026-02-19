/**
 * SilentModeGate
 *
 * Wraps the entire app.  When silent=true, all mood-driven effects are
 * suppressed.  Shows a subtle indicator so the user always knows which
 * mode is active.
 *
 * The indicator:
 *   • Silent ON  → small grey pill "◉ silent" — bottom-right corner
 *   • Silent OFF → small amber pill "◎ active" — fades to 20% after 3 s
 *
 * Double-tap anywhere toggles the mode.
 *
 * Props:
 *   silent     boolean
 *   onToggle   () => void
 *   children   React.ReactNode
 */

import React, { useEffect, useRef } from 'react';
import { StyleSheet, Text, View, Animated, Pressable } from 'react-native';
import { DoubleTapToggle } from './DoubleTapToggle';

export function SilentModeGate({ silent, onToggle, children }) {
  const opacity = useRef(new Animated.Value(1)).current;

  // Fade indicator to ghost opacity after 3 s when active
  useEffect(() => {
    opacity.setValue(1);
    const timer = setTimeout(() => {
      Animated.timing(opacity, {
        toValue:         silent ? 1 : 0.20,
        duration:        800,
        useNativeDriver: true,
      }).start();
    }, 3000);
    return () => clearTimeout(timer);
  }, [silent, opacity]);

  return (
    <DoubleTapToggle onToggle={onToggle}>
      <View style={styles.root}>
        {children}

        {/* Silent mode pill — touchable for single-tap toggle as fallback */}
        <Animated.View style={[styles.pill, silent ? styles.pillSilent : styles.pillActive, { opacity }]}>
          <Pressable onPress={onToggle} hitSlop={12}>
            <Text style={styles.pillText}>
              {silent ? '◉ silent' : '◎ active'}
            </Text>
          </Pressable>
        </Animated.View>
      </View>
    </DoubleTapToggle>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
  },
  pill: {
    position: 'absolute',
    bottom: 28,
    right: 18,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 20,
  },
  pillSilent: {
    backgroundColor: 'rgba(80,80,80,0.55)',
  },
  pillActive: {
    backgroundColor: 'rgba(200,140,30,0.60)',
  },
  pillText: {
    color: '#fff',
    fontSize: 11,
    fontWeight: '600',
    letterSpacing: 0.4,
  },
});
