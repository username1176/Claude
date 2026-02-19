/**
 * SettingsScreen
 *
 * Configures:
 *   • BREATH_SECRET (shared passphrase)
 *   • Local breathing rate + depth (manual calibration)
 *   • Smart-plug backend: stub / IFTTT / Home Assistant
 *   • Opt-out button
 *
 * All changes are persisted to AsyncStorage immediately.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  StyleSheet, View, Text, TextInput, Pressable, Switch,
  ScrollView, StatusBar, KeyboardAvoidingView, Platform,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { getConfig, setConfig } from '../services/AutomationService';
import { clearAllEffects }      from '../services/MoodActions';

const PREFS_KEY = '@moodaura/prefs';

export function SettingsScreen({ onOptOut }) {
  const [secret,      setSecret]      = useState('default');
  const [breathRate,  setBreathRate]  = useState('14');
  const [breathDepth, setBreathDepth] = useState('0.65');
  const [backend,     setBackend]     = useState('stub');
  const [iftttKey,    setIftttKey]    = useState('');
  const [iftttEvent,  setIftttEvent]  = useState('brew_coffee');
  const [haUrl,       setHaUrl]       = useState('');
  const [haToken,     setHaToken]     = useState('');
  const [haEntity,    setHaEntity]    = useState('switch.coffee_maker');
  const [saved,       setSaved]       = useState(false);

  useEffect(() => {
    Promise.all([
      AsyncStorage.getItem(PREFS_KEY),
      getConfig(),
    ]).then(([raw, cfg]) => {
      if (raw) {
        const p = JSON.parse(raw);
        if (p.secret)      setSecret(p.secret);
        if (p.breathRate)  setBreathRate(String(p.breathRate));
        if (p.breathDepth) setBreathDepth(String(p.breathDepth));
      }
      if (cfg) {
        setBackend(cfg.backend ?? 'stub');
        if (cfg.iftttKey)   setIftttKey(cfg.iftttKey);
        if (cfg.iftttEvent) setIftttEvent(cfg.iftttEvent);
        if (cfg.haUrl)      setHaUrl(cfg.haUrl);
        if (cfg.haToken)    setHaToken(cfg.haToken);
        if (cfg.haEntityId) setHaEntity(cfg.haEntityId);
      }
    });
  }, []);

  const save = useCallback(async () => {
    await Promise.all([
      AsyncStorage.setItem(PREFS_KEY, JSON.stringify({
        secret,
        breathRate:  parseFloat(breathRate)  || 14,
        breathDepth: parseFloat(breathDepth) || 0.65,
      })),
      setConfig({
        backend,
        iftttKey,
        iftttEvent,
        haUrl,
        haToken,
        haEntityId: haEntity,
      }),
    ]);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }, [secret, breathRate, breathDepth, backend, iftttKey, iftttEvent, haUrl, haToken, haEntity]);

  const handleOptOut = useCallback(async () => {
    await clearAllEffects();
    onOptOut?.();
  }, [onOptOut]);

  return (
    <KeyboardAvoidingView
      style={{ flex: 1 }}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <StatusBar barStyle="light-content" />
      <ScrollView style={styles.root} contentContainerStyle={styles.scroll}>
        <Text style={styles.heading}>Settings</Text>

        <Section title="Network">
          <Field label="Breath secret (shared passphrase)">
            <TextInput
              style={styles.input}
              value={secret}
              onChangeText={setSecret}
              secureTextEntry
              autoCapitalize="none"
              placeholder="same as BREATH_SECRET on ble-breath"
              placeholderTextColor={C.muted}
            />
          </Field>
        </Section>

        <Section title="Local Breathing (manual calibration)">
          <Field label="Breathing rate (breaths/min)">
            <TextInput
              style={styles.input}
              value={breathRate}
              onChangeText={setBreathRate}
              keyboardType="decimal-pad"
              placeholderTextColor={C.muted}
            />
          </Field>
          <Field label="Breath depth (0 – 1)">
            <TextInput
              style={styles.input}
              value={breathDepth}
              onChangeText={setBreathDepth}
              keyboardType="decimal-pad"
              placeholderTextColor={C.muted}
            />
          </Field>
        </Section>

        <Section title="Coffee Smart Plug">
          <BackendToggle value={backend} onChange={setBackend} />

          {backend === 'ifttt' && (
            <>
              <Field label="IFTTT API key">
                <TextInput style={styles.input} value={iftttKey} onChangeText={setIftttKey}
                  secureTextEntry autoCapitalize="none" placeholderTextColor={C.muted} />
              </Field>
              <Field label="Event name">
                <TextInput style={styles.input} value={iftttEvent} onChangeText={setIftttEvent}
                  autoCapitalize="none" placeholderTextColor={C.muted} />
              </Field>
            </>
          )}

          {backend === 'homeassistant' && (
            <>
              <Field label="Home Assistant URL">
                <TextInput style={styles.input} value={haUrl} onChangeText={setHaUrl}
                  autoCapitalize="none" keyboardType="url" placeholderTextColor={C.muted}
                  placeholder="http://homeassistant.local:8123" />
              </Field>
              <Field label="Long-lived access token">
                <TextInput style={styles.input} value={haToken} onChangeText={setHaToken}
                  secureTextEntry autoCapitalize="none" placeholderTextColor={C.muted} />
              </Field>
              <Field label="Entity ID">
                <TextInput style={styles.input} value={haEntity} onChangeText={setHaEntity}
                  autoCapitalize="none" placeholderTextColor={C.muted} />
              </Field>
            </>
          )}
        </Section>

        <Pressable style={[styles.btn, styles.btnSave]} onPress={save}>
          <Text style={styles.btnTextPrimary}>{saved ? '✓ Saved' : 'Save'}</Text>
        </Pressable>

        <Pressable style={[styles.btn, styles.btnOptOut]} onPress={handleOptOut}>
          <Text style={styles.btnTextMuted}>Opt out &amp; stop MoodAura</Text>
        </Pressable>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

// ── sub-components ────────────────────────────────────────────────────────────

function Section({ title, children }) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title.toUpperCase()}</Text>
      {children}
    </View>
  );
}

function Field({ label, children }) {
  return (
    <View style={styles.field}>
      <Text style={styles.label}>{label}</Text>
      {children}
    </View>
  );
}

function BackendToggle({ value, onChange }) {
  const opts = ['stub', 'ifttt', 'homeassistant'];
  const labels = { stub: 'Disabled', ifttt: 'IFTTT', homeassistant: 'Home Assistant' };
  return (
    <View style={styles.segmented}>
      {opts.map(o => (
        <Pressable
          key={o}
          style={[styles.segment, value === o && styles.segmentActive]}
          onPress={() => onChange(o)}
        >
          <Text style={[styles.segmentText, value === o && styles.segmentTextActive]}>
            {labels[o]}
          </Text>
        </Pressable>
      ))}
    </View>
  );
}

// ── styles ────────────────────────────────────────────────────────────────────

const C = {
  bg: '#0A0A0A', card: '#161616', text: '#E8E8E8',
  muted: '#666', accent: '#E8A020', danger: '#C0392B',
};

const styles = StyleSheet.create({
  root:             { flex: 1, backgroundColor: C.bg },
  scroll:           { padding: 24, paddingBottom: 60 },
  heading:          { color: C.text, fontSize: 22, fontWeight: '700', marginBottom: 28 },
  section:          { marginBottom: 28 },
  sectionTitle:     { color: C.accent, fontSize: 10, fontWeight: '700', letterSpacing: 1.4, marginBottom: 12 },
  field:            { marginBottom: 16 },
  label:            { color: C.muted, fontSize: 12, marginBottom: 6 },
  input:            { backgroundColor: C.card, color: C.text, borderRadius: 8, paddingHorizontal: 14, paddingVertical: 12, fontSize: 14 },
  btn:              { borderRadius: 10, paddingVertical: 15, alignItems: 'center', marginBottom: 12 },
  btnSave:          { backgroundColor: C.accent },
  btnOptOut:        { backgroundColor: C.card },
  btnTextPrimary:   { color: '#0A0A0A', fontWeight: '700', fontSize: 15 },
  btnTextMuted:     { color: C.danger, fontSize: 14 },
  segmented:        { flexDirection: 'row', backgroundColor: C.card, borderRadius: 8, marginBottom: 16 },
  segment:          { flex: 1, paddingVertical: 10, alignItems: 'center', borderRadius: 8 },
  segmentActive:    { backgroundColor: C.accent },
  segmentText:      { color: C.muted, fontSize: 13 },
  segmentTextActive:{ color: '#0A0A0A', fontWeight: '700' },
});
