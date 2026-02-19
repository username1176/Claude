/**
 * OptInScreen
 *
 * Shown on first launch.  Explains what the app does and asks the user
 * to explicitly opt in before any BLE scanning or phone-API access begins.
 *
 * No dark patterns — the "don't enable" path is equally prominent.
 */

import React from 'react';
import {
  StyleSheet, View, Text, Pressable, ScrollView, StatusBar,
} from 'react-native';

const BULLET = '·';

export function OptInScreen({ onOptIn, onDecline }) {
  return (
    <View style={styles.root}>
      <StatusBar barStyle="light-content" />
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.title}>MoodAura</Text>
        <Text style={styles.subtitle}>ambient mood companion</Text>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>What this does</Text>
          {[
            'Listens for anonymised breathing patterns from nearby devices via Bluetooth',
            'Dims your screen slightly when nearby breathing suggests fatigue',
            'Plays soft white noise when stress patterns are detected',
            'Optionally triggers a smart plug (coffee maker) when you\'re dragging',
            'Everything is local — no servers, no accounts, no names',
          ].map((line, i) => (
            <Text key={i} style={styles.bullet}>{BULLET}  {line}</Text>
          ))}
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>What this does NOT do</Text>
          {[
            'Identify you or store any device IDs',
            'Send any data off your device',
            'Work without your explicit permission',
          ].map((line, i) => (
            <Text key={i} style={styles.bullet}>{BULLET}  {line}</Text>
          ))}
        </View>

        <Text style={styles.note}>
          You can opt out at any time in Settings.  Silent mode (double-tap
          anywhere) suppresses all effects instantly.
        </Text>
      </ScrollView>

      <View style={styles.actions}>
        <Pressable style={[styles.btn, styles.btnPrimary]} onPress={onOptIn}>
          <Text style={styles.btnTextPrimary}>Enable MoodAura</Text>
        </Pressable>
        <Pressable style={[styles.btn, styles.btnSecondary]} onPress={onDecline}>
          <Text style={styles.btnTextSecondary}>Not now</Text>
        </Pressable>
      </View>
    </View>
  );
}

const C = { bg: '#0A0A0A', card: '#161616', text: '#E8E8E8', muted: '#888', accent: '#E8A020' };

const styles = StyleSheet.create({
  root:           { flex: 1, backgroundColor: C.bg },
  scroll:         { padding: 28, paddingTop: 60, paddingBottom: 20 },
  title:          { color: C.text, fontSize: 28, fontWeight: '700', letterSpacing: 1.2 },
  subtitle:       { color: C.muted, fontSize: 14, marginTop: 4, marginBottom: 32, letterSpacing: 0.8 },
  card:           { backgroundColor: C.card, borderRadius: 12, padding: 18, marginBottom: 16 },
  cardTitle:      { color: C.accent, fontSize: 12, fontWeight: '700', letterSpacing: 1, marginBottom: 12, textTransform: 'uppercase' },
  bullet:         { color: C.text, fontSize: 14, lineHeight: 22, marginBottom: 6 },
  note:           { color: C.muted, fontSize: 13, lineHeight: 20, marginTop: 8 },
  actions:        { padding: 24, gap: 12 },
  btn:            { borderRadius: 12, paddingVertical: 16, alignItems: 'center' },
  btnPrimary:     { backgroundColor: C.accent },
  btnSecondary:   { backgroundColor: C.card },
  btnTextPrimary: { color: '#0A0A0A', fontSize: 15, fontWeight: '700' },
  btnTextSecondary:{ color: C.muted, fontSize: 15 },
});
