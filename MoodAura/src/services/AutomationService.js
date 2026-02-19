/**
 * AutomationService
 *
 * Sends a "brew coffee" trigger when the composite 'dragging' mood is detected
 * (tired > 0.40 AND stressed > 0.40 simultaneously).
 *
 * Two backends — configured in app settings stored in AsyncStorage:
 *
 *   backend = 'ifttt'
 *     Sends a POST to https://maker.ifttt.com/trigger/<event>/with/key/<key>
 *     Event name, API key, and optional value1/value2/value3 are configurable.
 *
 *   backend = 'homeassistant'
 *     Calls the HA REST API:  POST /api/services/switch/turn_on
 *     with entity_id = configured smart-plug entity.
 *
 *   backend = 'stub'  (default / no config)
 *     Does nothing — logs to no-where.  The dragging detection still fires
 *     haptic feedback so the user knows the trigger would have run.
 *
 * Rate limiting: at most one trigger per COOLDOWN_MS (default 30 min).
 * All network errors are silently swallowed — this is ambient, not critical.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';

const CONFIG_KEY   = '@moodaura/automation';
const COOLDOWN_MS  = 30 * 60 * 1000;   // 30 minutes

let _lastTriggered = 0;

// ── config helpers ────────────────────────────────────────────────────────────

export async function getConfig() {
  try {
    const raw = await AsyncStorage.getItem(CONFIG_KEY);
    return raw ? JSON.parse(raw) : { backend: 'stub' };
  } catch (_) {
    return { backend: 'stub' };
  }
}

export async function setConfig(cfg) {
  await AsyncStorage.setItem(CONFIG_KEY, JSON.stringify(cfg));
}

// ── trigger ───────────────────────────────────────────────────────────────────

/**
 * Attempt to trigger the coffee smart-plug.
 * Returns 'triggered' | 'cooldown' | 'stub' | 'error'.
 */
export async function triggerCoffee() {
  const now = Date.now();
  if (now - _lastTriggered < COOLDOWN_MS) return 'cooldown';

  const cfg = await getConfig();

  try {
    switch (cfg.backend) {
      case 'ifttt':        await triggerIFTTT(cfg);         break;
      case 'homeassistant': await triggerHomeAssistant(cfg); break;
      default:             return 'stub';
    }
    _lastTriggered = now;
    return 'triggered';
  } catch (_) {
    return 'error';
  }
}

// ── IFTTT webhook ─────────────────────────────────────────────────────────────

async function triggerIFTTT(cfg) {
  const { iftttKey, iftttEvent = 'brew_coffee', value1, value2, value3 } = cfg;
  if (!iftttKey) throw new Error('No IFTTT key configured');

  const url  = `https://maker.ifttt.com/trigger/${iftttEvent}/with/key/${iftttKey}`;
  const body = JSON.stringify({ value1, value2, value3 });

  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body,
  });
  if (!res.ok) throw new Error(`IFTTT ${res.status}`);
}

// ── Home Assistant REST API ───────────────────────────────────────────────────

async function triggerHomeAssistant(cfg) {
  const { haUrl, haToken, haEntityId = 'switch.coffee_maker' } = cfg;
  if (!haUrl || !haToken) throw new Error('HA not configured');

  const res = await fetch(`${haUrl}/api/services/switch/turn_on`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${haToken}`,
      'Content-Type':  'application/json',
    },
    body: JSON.stringify({ entity_id: haEntityId }),
  });
  if (!res.ok) throw new Error(`HA ${res.status}`);
}

// ── dragging detection ────────────────────────────────────────────────────────

export const DRAGGING_THRESHOLD = 0.40;

export function isDragging(mood) {
  return mood.tired    >= DRAGGING_THRESHOLD
      && mood.stressed >= DRAGGING_THRESHOLD;
}
