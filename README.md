# PulseSync

**Anonymous physiological resonance over Bluetooth Low Energy.**

Two phones. No accounts. No names. No server. If your breathing patterns
match within ±5%, something quietly happens — a dimmed screen, a breath of
white noise, a gentle LED pulse. If they stop matching, nothing persists.

---

## Table of Contents

1. [How it works](#how-it-works)
2. [Privacy guarantees](#privacy-guarantees)
3. [Data lifecycle](#data-lifecycle)
4. [Kill switch](#kill-switch)
5. [Architecture](#architecture)
6. [Installation](#installation)
7. [Usage](#usage)
8. [MoodAura (mobile companion)](#moodaura-mobile-companion)
9. [Supported actions](#supported-actions)
10. [Smart-plug integration](#smart-plug-integration)
11. [Contributing](#contributing)
12. [License](#license)

---

## How it works

PulseSync has three layers:

```
┌─────────────────────────────────────────────────────────────────┐
│  mood_net.py          — on-device neural net, 5-class mood       │
│                         inference from breathing metrics          │
├─────────────────────────────────────────────────────────────────┤
│  ble-breath/          — Node.js BLE broadcaster / scanner        │
│                         encrypted mood + breath vector, no IDs   │
├─────────────────────────────────────────────────────────────────┤
│  MoodAura/            — React Native companion app               │
│                         phone APIs: brightness, audio, smart-plug│
└─────────────────────────────────────────────────────────────────┘
```

**Broadcast (every 10 seconds):**

1. Your local breathing rate and depth are encoded into an 8-byte plaintext.
2. A 256-bit AES-GCM key is derived via `HKDF-SHA256(BREATH_SECRET, salt=window)`,
   where `window = ⌊unix_time / 10⌋`. The key changes every 10 seconds.
3. The nonce is derived deterministically — `HMAC-SHA256(key, "nonce")[0:12]` —
   and never transmitted. Observers see random-looking manufacturer data.
4. The 19-byte encrypted packet is broadcast in BLE advertisement
   manufacturer-specific data. No service UUIDs, no device names.

**Reception:**

1. A nearby scanner decrypts with its own derived key (same shared secret,
   same time window).
2. If decryption succeeds (authenticated), it compares the decoded breath
   vector against its own local vector.
3. If all components match within **±5%**, resonance is declared.
4. If decryption fails, the packet is silently discarded.
   Wrong-network devices see authenticated noise.

**No resonance is possible without:**
- The same `BREATH_SECRET` (a passphrase you set)
- A matching breathing pattern (±5% on rate and depth)
- Being within BLE radio range (≈10 m typical)

---

## Privacy guarantees

### Nothing is transmitted that identifies you

| Field | In advertisement? | Notes |
|---|---|---|
| Device name | ✗ | Advertising uses raw EIR bytes; `localName` is empty |
| MAC address | randomised | BLE address rotation controlled by OS/driver |
| Mood vector | ✓ (encrypted) | 256-bit AES-GCM; unreadable without shared secret |
| Breath vector | ✓ (encrypted) | Same ciphertext; rate and depth quantised to uint8 |
| Device type | ✗ | Company ID 0xFFFF (test range) |
| Timestamp | ✗ | Key window `mod 65536` — not a unique identifier |

### Breath hashes are one-way

When a session starts, `ble-breath` generates a 16-byte random **session
salt** via `crypto.randomBytes(16)`. This salt lives only in process memory.

The breath commitment is:

```
breathHash(vec) = SHA-256( session_salt ‖ rate_uint8 ‖ depth_uint8 )
```

Properties:
- **Pre-image resistant.** The hash reveals nothing about the underlying
  rate or depth values to anyone who does not already have the session salt.
- **Session-scoped.** The salt is never written to disk. Every time the
  process starts, a new salt is generated, making cross-session correlation
  cryptographically impossible even for someone with the shared secret.
- **Not transmitted.** The commitment hash is used only in-process for
  internal integrity checks. Only the AES-GCM ciphertext goes over the air.

### Syncs expire automatically

| Timer | Value | What resets |
|---|---|---|
| Key window | 10 s | Ephemeral AES key rotates; old broadcasts become undecryptable |
| Warmth cooldown | 30 s | Joy-borrow resonance state clears; device acts neutral again |
| Scan dedup | per-scan | `allowDuplicates: true` — no per-address dedup table is kept |

After 30 seconds without a matching broadcast, every in-memory resonance
state resets to neutral. There is no "relationship" between two devices
that persists beyond the current window.

### Nothing is written to disk (ble-breath)

`ble-breath` holds zero persistent state:

```
$ ls -la ~/.config/ble-breath 2>/dev/null || echo "directory does not exist"
directory does not exist
```

The only data that exists is the in-process `SESSION_SALT` buffer (16 bytes,
in RAM, gone on exit) and the keys derived from it (also in RAM, also gone).

### MoodAura stores preferences, not biometrics

The mobile companion writes to `AsyncStorage` only:

| Key | Contents | Personal? |
|---|---|---|
| `@moodaura/opted_in` | boolean | No |
| `@moodaura/silent` | boolean | No |
| `@moodaura/prefs` | `{ breathRate, breathDepth }` user-entered values | Self-reported, not measured |
| `@moodaura/automation` | Smart-plug backend + API key | Credentials, not biometric |

Mood classifications and sync events are **never written to AsyncStorage**.

---

## Data lifecycle

```
Process start
  │
  ├─ SESSION_SALT = randomBytes(16)            ← 16 bytes, RAM only
  │
  │   Every 10 seconds
  │   ├─ window = ⌊now/10000⌋
  │   ├─ key    = HKDF-SHA256(secret, window)  ← derived, not stored
  │   ├─ nonce  = HMAC-SHA256(key, "nonce")    ← derived, not stored
  │   ├─ ct     = AES-256-GCM(plaintext, key)  ← broadcast, then forgotten
  │   └─ plaintext                             ← overwritten next cycle
  │
  │   On receive
  │   ├─ decrypt → breathVec                   ← compared once, discarded
  │   ├─ if match → fire haptic               ← no address retained
  │   └─ if joy-borrow → set flag              ← cleared after next broadcast
  │
Process exit / --wipe
  └─ All RAM freed; SESSION_SALT gone; no traces on disk
```

---

## Kill switch

### ble-breath (Node.js)

```bash
node index.js --wipe
# stdout: pulse:wiped
# exit code: 0
```

What it does:
1. Overwrites `SESSION_SALT` with fresh random bytes (the old breath hash
   commitments are now irrecoverable even in-process).
2. Prints `pulse:wiped` to stdout so shell scripts can confirm success.
3. Exits immediately — no BLE adapter is touched, no files are written.

What it does not need to do:
- Delete files (there are none)
- Revoke keys (they expire in ≤10 seconds on their own)
- Contact a server (there is no server)

You can verify no state persists by running:

```bash
node index.js --wipe && node -e "
  const { SESSION_SALT } = require('./src/breath');
  // This is a DIFFERENT process; SESSION_SALT is new randomBytes(16)
  console.log('new salt:', SESSION_SALT.toString('hex'));
"
```

### MoodAura (mobile)

**Via Settings screen:** tap **"Opt out & stop MoodAura"** — this calls
`wipeAllLocalData()` which removes all four `@moodaura/*` keys and stops
all active services before the UI navigates away.

**Via code:**

```js
import { wipeAllLocalData, forgetPulseAndRestart } from './src/services/WipeService';

// Wipe and stay in-app (caller handles navigation):
const { keysRemoved } = await wipeAllLocalData();

// Wipe and restart the JS bundle (no in-memory state survives):
await forgetPulseAndRestart();
```

**Restart equals forget.** Because MoodAura stores no biometric data, and
because the shared `BREATH_SECRET` is re-read from the settings on each
run (not cached in memory between restarts), killing and relaunching the
app is sufficient to start with a completely clean slate. The `--wipe`/
`wipeAllLocalData()` commands simply make this guarantee explicit and
shell-scriptable.

---

## Architecture

```
pulsesync/
│
├── mood_net.py               5-class PyTorch mood classifier
│   └── mood_net.pt           pre-trained TorchScript model (16.6 KB)
│
├── ble-breath/               BLE protocol (Node.js ≥ 16)
│   ├── index.js              entry — BLE + sim + --wipe
│   └── src/
│       ├── crypto.js         HKDF + AES-256-GCM key schedule
│       ├── payload.js        19-byte packet codec
│       ├── breath.js         ±5% matcher + SHA-256 commitment
│       ├── peripheral.js     bleno advertiser
│       ├── central.js        noble scanner + joy-borrow logic
│       ├── scheduler.js      single/dual HCI adapter time-multiplex
│       └── haptic.js         LED sysfs / GPIO / ANSI fallback
│
└── MoodAura/                 React Native companion (Android + iOS)
    ├── App.js                opt-in gate + navigation
    └── src/
        ├── crypto/
        │   └── bleDecrypt.js   mirrors ble-breath key schedule in RN
        ├── hooks/
        │   ├── useBleListener.js  scan + decrypt + breath gate
        │   ├── useSilentMode.js   persisted silent toggle
        │   └── useOptIn.js        consent gate
        ├── services/
        │   ├── BrightnessService.js   native brightness (Android + iOS)
        │   ├── WhiteNoiseService.js   fade-in/out audio loop
        │   ├── AutomationService.js   IFTTT / Home Assistant stub
        │   ├── MoodActions.js         debounced action orchestrator
        │   └── WipeService.js         kill switch
        ├── components/
        │   ├── DoubleTapToggle.js     gesture-handler double-tap
        │   ├── SilentModeGate.js      overlay + animated indicator
        │   └── MoodRing.js            ambient pulsing colour ring
        └── screens/
            ├── OptInScreen.js         first-launch consent
            ├── HomeScreen.js          main ambient view
            └── SettingsScreen.js      calibration + smart-plug config
```

---

## Installation

### Prerequisites

| Component | Requirement |
|---|---|
| mood_net.py | Python ≥ 3.9, PyTorch ≥ 2.0 |
| ble-breath | Node.js ≥ 16, BlueZ ≥ 5.50 (Linux) or CoreBluetooth (macOS) |
| MoodAura | React Native 0.75, Xcode ≥ 15 (iOS) or Android SDK 34 |

### ble-breath

```bash
cd ble-breath
npm install
```

On Linux, grant BLE capabilities without running as root:

```bash
sudo setcap 'cap_net_raw,cap_net_admin+eip' $(which node)
```

### MoodAura

```bash
cd MoodAura
npm install

# iOS
cd ios && pod install && cd ..
npx react-native run-ios

# Android
npx react-native run-android
```

Add `white_noise.mp3` (any loopable white-noise track) to:
- `android/app/src/main/res/raw/white_noise.mp3`
- Xcode project bundle (drag into Resources group)

Register `BrightnessPackage` in `MainApplication.java`:

```java
@Override
protected List<ReactPackage> getPackages() {
    return Arrays.asList(
        new MainReactPackage(),
        new BrightnessPackage()   // ← add this
    );
}
```

---

## Usage

### Basic (simulation, no BLE hardware)

```bash
BREATH_SECRET=mysecret node ble-breath/index.js --sim \
  --rate 14 --depth 0.68 \
  --mood '{"calm":0.5,"stressed":0.1,"joyful":0.3,"tired":0.05,"neutral":0.05}'
```

### Two devices on the same network

**Device A:**
```bash
BREATH_SECRET=mysecret DUAL_ADAPTER=1 \
  NOBLE_HCI_DEVICE_ID=0 BLENO_HCI_DEVICE_ID=1 \
  node ble-breath/index.js --rate 13.8 --depth 0.70
```

**Device B:**
```bash
BREATH_SECRET=mysecret DUAL_ADAPTER=1 \
  NOBLE_HCI_DEVICE_ID=0 BLENO_HCI_DEVICE_ID=1 \
  node ble-breath/index.js --rate 14.1 --depth 0.68
```
Both breathing rates are within ±5% → resonance fires within one broadcast cycle.

### Live mood updates via stdin

```bash
BREATH_SECRET=mysecret node ble-breath/index.js | while true; do
  python mood_net.py infer --bpm 13.5 --rmssd 72 --sdnn 55 --lf-hf 1.1 \
    | python -c "import sys,json; d=json.load(sys.stdin); print(json.dumps({'mood':d}))"
  sleep 10
done | BREATH_SECRET=mysecret node ble-breath/index.js
```

### Forget your pulse

```bash
# ble-breath
node ble-breath/index.js --wipe   # → pulse:wiped

# MoodAura: Settings → "Opt out & stop MoodAura"
# or simply kill and relaunch the app — no state persists
```

---

## MoodAura (mobile companion)

1. Install and launch. The **opt-in screen** appears — read it, then tap
   **Enable MoodAura** (or **Not now** to keep the app dormant).

2. The app scans for BLE advertisements matching your `BREATH_SECRET`.
   **It starts in silent mode** — no effects fire until you unlock them.

3. **Double-tap anywhere** to toggle silent mode. A small pill indicator
   shows `◉ silent` (grey) or `◎ active` (amber) and fades to 20% opacity
   after 3 seconds so it doesn't distract.

4. Go to **Settings** (navigate from Home) to set:
   - Your shared passphrase (`BREATH_SECRET`)
   - Manual breath calibration (rate + depth)
   - Smart-plug backend and credentials

5. To fully forget: **Settings → Opt out & stop MoodAura** — all four
   storage keys are removed and the app returns to the opt-in screen.

---

## Supported actions

| Mood trigger | Threshold | Action | Undone when |
|---|---|---|---|
| `tired > 0.55` | held 4 s | Screen dims 20% | `tired < 0.47` for 4 s |
| `stressed > 0.55` | held 4 s | White noise fades in | `stressed < 0.47` |
| `joyful > 0.80` | held 2 s | Brightness restored | — |
| `dragging`¹ | held 8 s | Coffee smart-plug | 30 min cooldown |
| Remote `joyBorrow` flag | immediate | 100 ms warmth haptic | next broadcast |

¹ `dragging` = `tired > 0.40` AND `stressed > 0.40` simultaneously.

All actions are suppressed when silent mode is active (`◉ silent`).
Silent mode survives app backgrounding but resets to `true` on full restart.

---

## Smart-plug integration

### IFTTT

1. Create an applet: **Webhook → Smart Life / TP-Link / etc.**
2. Event name: `brew_coffee` (or configure in Settings)
3. API key: your IFTTT Maker key

In Settings, set backend to **IFTTT** and enter the key and event name.
The trigger URL is: `https://maker.ifttt.com/trigger/{event}/with/key/{key}`

### Home Assistant

1. Create a long-lived access token (Profile → Long-Lived Access Tokens)
2. Note your HA URL (e.g. `http://homeassistant.local:8123`)
3. Find the entity ID of your coffee maker smart plug

In Settings, set backend to **Home Assistant** and fill in the three fields.
The trigger calls: `POST /api/services/switch/turn_on` with `{ entity_id }`.

### Custom (curl example)

```bash
HAPTIC_CMD="curl -s -X POST https://my-home-server/api/coffee" \
  node ble-breath/index.js
```

---

## Contributing

PulseSync is free software. Contributions are welcome under the terms of the
GNU General Public License v3.

```
git clone https://github.com/example/pulsesync
cd pulsesync
# ble-breath: node index.js --sim  to develop without hardware
# MoodAura:   react-native run-android / run-ios
```

Please read [PRIVACY.md](PRIVACY.md) before contributing features that
touch the BLE payload, key schedule, or storage layer — any change that
could introduce persistent identifiers or reduce the privacy properties
documented there requires a corresponding update to PRIVACY.md and a
clear explanation in the pull request.

**Things we will not merge:**
- Features that log, upload, or aggregate mood or breath data
- Changes that add persistent per-device identifiers to the BLE payload
- Reduced key rotation intervals (must stay ≤ 10 seconds)
- Opt-out flows that require network confirmation

---

## License

```
PulseSync — anonymous physiological BLE resonance
Copyright (C) 2024  PulseSync Contributors

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
```

See [LICENSE](LICENSE) for the full text.
