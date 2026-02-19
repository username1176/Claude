/**
 * MoodRing
 *
 * Ambient circular indicator that reflects the current mood without numbers
 * or labels.  The ring colour and pulse speed encode the dominant mood:
 *
 *   calm     → slow blue pulse
 *   joyful   → warm amber, faster
 *   stressed → red, quick flutter
 *   tired    → cool grey, very slow
 *   neutral  → dim white
 *
 * Props:
 *   mood       { calm, stressed, joyful, tired, neutral }
 *   resonance  float 0–1 (opacity of the ring — brighter when in sync)
 *   size       number (default 120)
 */

import React, { useEffect, useRef } from 'react';
import { Animated, StyleSheet, View } from 'react-native';

const MOOD_STYLES = {
  calm:     { color: '#4A90D9', period: 4000 },
  joyful:   { color: '#E8A020', period: 2200 },
  stressed: { color: '#D94040', period: 1200 },
  tired:    { color: '#7A8A9A', period: 6000 },
  neutral:  { color: '#AAAAAA', period: 5000 },
};

function dominantMood(mood) {
  return Object.entries(mood).reduce((a, b) => (b[1] > a[1] ? b : a))[0];
}

export function MoodRing({ mood, resonance = 0, size = 120 }) {
  const scale   = useRef(new Animated.Value(1)).current;
  const opacity = useRef(new Animated.Value(0.3)).current;

  const dom    = dominantMood(mood);
  const style  = MOOD_STYLES[dom] ?? MOOD_STYLES.neutral;

  useEffect(() => {
    const pulse = Animated.loop(
      Animated.sequence([
        Animated.parallel([
          Animated.timing(scale,   { toValue: 1.12, duration: style.period / 2, useNativeDriver: true }),
          Animated.timing(opacity, { toValue: 0.6 + resonance * 0.4, duration: style.period / 2, useNativeDriver: true }),
        ]),
        Animated.parallel([
          Animated.timing(scale,   { toValue: 1.00, duration: style.period / 2, useNativeDriver: true }),
          Animated.timing(opacity, { toValue: 0.2 + resonance * 0.3, duration: style.period / 2, useNativeDriver: true }),
        ]),
      ])
    );
    pulse.start();
    return () => pulse.stop();
  }, [dom, resonance, scale, opacity, style.period]);

  return (
    <View style={[styles.container, { width: size, height: size }]}>
      <Animated.View
        style={[
          styles.ring,
          {
            width:           size,
            height:          size,
            borderRadius:    size / 2,
            borderColor:     style.color,
            transform:       [{ scale }],
            opacity,
          },
        ]}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems:     'center',
    justifyContent: 'center',
  },
  ring: {
    borderWidth: 3,
    backgroundColor: 'transparent',
  },
});
