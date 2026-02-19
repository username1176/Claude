/**
 * MoodAura — root entry point.
 *
 * Navigation flow:
 *   OptIn not done → OptInScreen
 *   OptIn done     → Tab navigator (Home | Settings)
 *
 * Permissions requested at startup (BLE, notifications suppressed — no noise):
 *   Android: BLUETOOTH_SCAN, BLUETOOTH_CONNECT, ACCESS_FINE_LOCATION
 *   iOS:     NSBluetoothAlwaysUsageDescription (Info.plist)
 *
 * react-native-gesture-handler must be the first import in the entry file.
 */

import 'react-native-gesture-handler';

import React, { useEffect } from 'react';
import { Platform, StatusBar } from 'react-native';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { NavigationContainer }    from '@react-navigation/native';
import { createStackNavigator }   from '@react-navigation/stack';
import { SafeAreaProvider }       from 'react-native-safe-area-context';
import { check, request, PERMISSIONS, RESULTS } from 'react-native-permissions';

import { useOptIn }         from './src/hooks/useOptIn';
import { OptInScreen }      from './src/screens/OptInScreen';
import { HomeScreen }       from './src/screens/HomeScreen';
import { SettingsScreen }   from './src/screens/SettingsScreen';

const Stack = createStackNavigator();

// ── BLE permissions ───────────────────────────────────────────────────────────

async function requestBlePermissions() {
  if (Platform.OS === 'android') {
    const perms = Platform.Version >= 31
      ? [PERMISSIONS.ANDROID.BLUETOOTH_SCAN, PERMISSIONS.ANDROID.BLUETOOTH_CONNECT]
      : [PERMISSIONS.ANDROID.ACCESS_FINE_LOCATION];
    for (const p of perms) {
      const status = await check(p);
      if (status !== RESULTS.GRANTED) await request(p);
    }
  }
  // iOS: BLE usage description is declared in Info.plist; no runtime request needed
}

// ── App ───────────────────────────────────────────────────────────────────────

export default function App() {
  const { optedIn, optIn, optOut, loading } = useOptIn();

  useEffect(() => {
    if (optedIn) requestBlePermissions();
  }, [optedIn]);

  if (loading) return null;   // splash screen covers this

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <StatusBar barStyle="light-content" backgroundColor="#0A0A0A" />
        <NavigationContainer theme={NAV_THEME}>
          {!optedIn ? (
            // Pre-opt-in: single screen, no navigation chrome
            <Stack.Navigator screenOptions={{ headerShown: false }}>
              <Stack.Screen name="OptIn">
                {() => <OptInScreen onOptIn={optIn} onDecline={() => {}} />}
              </Stack.Screen>
            </Stack.Navigator>
          ) : (
            <Stack.Navigator screenOptions={SCREEN_OPTIONS}>
              <Stack.Screen
                name="Home"
                component={HomeScreen}
                options={{ headerShown: false }}
              />
              <Stack.Screen
                name="Settings"
                options={{ title: '', headerTransparent: true, headerTintColor: '#888' }}
              >
                {({ navigation }) => (
                  <SettingsScreen onOptOut={() => { optOut(); navigation.navigate('Home'); }} />
                )}
              </Stack.Screen>
            </Stack.Navigator>
          )}
        </NavigationContainer>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}

// ── navigation theme ──────────────────────────────────────────────────────────

const NAV_THEME = {
  dark: true,
  colors: {
    primary:      '#E8A020',
    background:   '#0A0A0A',
    card:         '#161616',
    text:         '#E8E8E8',
    border:       '#222222',
    notification: '#E8A020',
  },
};

const SCREEN_OPTIONS = {
  cardStyle:   { backgroundColor: '#0A0A0A' },
  headerStyle: { backgroundColor: '#0A0A0A', elevation: 0, shadowOpacity: 0 },
};
