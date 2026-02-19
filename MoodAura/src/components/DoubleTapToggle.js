/**
 * DoubleTapToggle
 *
 * An invisible full-screen overlay that listens for double-taps and calls
 * onToggle().  Uses react-native-gesture-handler for reliable multi-tap
 * detection independent of React Native's JS-thread-throttled responder.
 *
 * Props:
 *   onToggle   () => void   called on double-tap
 *   children   React.ReactNode
 */

import React from 'react';
import { StyleSheet } from 'react-native';
import { GestureDetector, Gesture } from 'react-native-gesture-handler';

export function DoubleTapToggle({ onToggle, children }) {
  const doubleTap = Gesture.Tap()
    .numberOfTaps(2)
    .maxDuration(300)
    .runOnJS(true)
    .onEnd(() => onToggle?.());

  return (
    <GestureDetector gesture={doubleTap}>
      {/* Must be a single child view; pointer events pass through */}
      <>{children}</>
    </GestureDetector>
  );
}

const styles = StyleSheet.create({});
