# PulseSync — Privacy Policy and Data Practices

**Version:** 1.0
**Effective:** 2024-01-01
**Jurisdiction:** This document is written to satisfy the informational
requirements of the GDPR (EU 2016/679), CCPA (Cal. Civ. Code § 1798.100 et
seq.), and equivalent statutes. Because PulseSync collects no personal data,
most regulatory obligations do not apply — this document explains why.

---

## 1. Summary

PulseSync does not collect, transmit, or retain personal data.

| Question | Answer |
|---|---|
| Do you collect personal data? | No |
| Do you use cookies or tracking pixels? | No |
| Do you send data to a server? | No — there is no server |
| Do you sell data to third parties? | No |
| Do you require an account? | No |
| Is there a privacy officer to contact? | See §10 |

If you are a regulator or auditor and need to verify these claims,
the complete source code is available under GPLv3. Every claim in
this document corresponds to a specific, auditable code path.

---

## 2. Definitions

**"PulseSync"** refers to the ble-breath Node.js package, the MoodAura
React Native application, and the mood_net.py inference module, collectively.

**"Breath vector"** means the pair `{ rate: breaths-per-minute, depth: 0–1 }`
derived from or entered by the user to describe their current breathing pattern.

**"Mood vector"** means the five-dimensional probability distribution
`{ calm, stressed, joyful, tired, neutral }` output by the on-device neural
network. All values sum to approximately 1.

**"Shared secret"** (`BREATH_SECRET`) means a passphrase chosen by the user
and entered identically on all devices that should be able to resonate. It
is never generated or stored by PulseSync — the user supplies it.

**"Sync window"** means a 10-second interval during which a single ephemeral
AES-256-GCM key is valid. After the window closes, the key is
irrecoverable — not archived, not escrowed.

---

## 3. Data we do not collect

### 3.1 Biometric data

Breathing rate, breath depth, and derived mood classifications are
**processed exclusively on-device and in process memory**. They are:

- Never written to disk by PulseSync.
- Never transmitted to a PulseSync server (there is none).
- Never included in crash reports, analytics events, or telemetry.
- Transmitted over BLE only in authenticated-encrypted form (AES-256-GCM),
  readable only by devices sharing the same `BREATH_SECRET`.

The BLE ciphertext that does leave the device is:
- Authenticated: a receiver with the wrong key cannot even verify whether
  decryption succeeded; it receives a MAC failure exception.
- Ephemeral: the key that produced it expires within 10 seconds and is
  never stored.
- Content-indistinguishable: without the shared secret, the 19-byte packet
  is computationally indistinguishable from random bytes.

### 3.2 Device identifiers

No persistent device identifier appears in any PulseSync advertisement or
data store. Specifically:

- No device name is broadcast (the `localName` field in BLE advertising
  data is omitted).
- The BLE MAC address in advertisements is subject to OS-level randomisation
  (Android ≥ 6, iOS, and Linux with BlueZ ≥ 5.43 all rotate MAC addresses
  for non-bonded peripherals).
- No UUID or serial number is included in the manufacturer-specific payload.
- The 2-byte `windowMod` field in each packet is the sender's epoch window
  modulo 65536. It changes every 10 seconds and is the same value for all
  PulseSync devices in the same window — it cannot identify a specific device.

### 3.3 Location data

PulseSync does not access GPS, cell tower, Wi-Fi positioning, or IP
geolocation. BLE radio range (typically 5–15 m) implicitly indicates
physical proximity, but PulseSync neither records this fact nor transmits
it anywhere.

On Android, `ACCESS_FINE_LOCATION` is requested on API levels below 31
because the Android SDK requires it for BLE scanning, not because PulseSync
uses location. On Android 12+ (API 31+), `BLUETOOTH_SCAN` and
`BLUETOOTH_CONNECT` are requested instead, with no location permission.

### 3.4 Usage analytics and crash reporting

PulseSync includes no analytics SDK, crash-reporting library, or telemetry
framework. The dependency list (`package.json` in each component) can be
audited to confirm the absence of Crashlytics, Sentry, Amplitude, Segment,
or equivalent.

---

## 4. Data stored locally (MoodAura)

The MoodAura application writes four keys to `AsyncStorage` (the platform
key-value store on the local device):

| Key | Type | Contents | Biometric? |
|---|---|---|---|
| `@moodaura/opted_in` | boolean | Whether the user has opted in | No |
| `@moodaura/silent` | boolean | Silent-mode preference | No |
| `@moodaura/prefs` | JSON | User-entered `breathRate`, `breathDepth`, `secret` | Self-reported preference, not measured |
| `@moodaura/automation` | JSON | Smart-plug backend selection and API credentials | No |

`@moodaura/prefs` contains `breathRate` and `breathDepth`. These values are
entered by the user in the Settings screen as a calibration preference — they
are not measured from a sensor by PulseSync. If you enter `14` for rate and
`0.65` for depth, those numbers are stored. No actual breathing measurement
is written to disk.

The `secret` field in `@moodaura/prefs` is the `BREATH_SECRET` passphrase.
It is stored in `AsyncStorage` on the device. It is **not** a password
generated or known by PulseSync — it is a passphrase you choose and share
with other devices you control. Treat it like a Wi-Fi password.

---

## 5. One-way breath commitments

ble-breath uses SHA-256 to produce a session-scoped one-way commitment of
each breath vector for internal integrity verification:

```
SESSION_SALT  = crypto.randomBytes(16)    ← generated once, at process start
breathHash(v) = SHA-256( SESSION_SALT ‖ quantise(v.rate) ‖ quantise(v.depth) )
```

`SESSION_SALT` is 16 random bytes generated by the OS CSPRNG at startup.
It is held only in process memory (a Node.js `Buffer`). It is never:

- Written to disk
- Transmitted over BLE or any network
- Derivable from the BLE ciphertext even by a party with `BREATH_SECRET`

**What this means for you:** Even if an adversary recorded every BLE
advertisement your device ever emitted and later obtained your
`BREATH_SECRET`, they could decrypt those advertisements to recover your
encrypted breath vectors — but they could not reconstruct the `SESSION_SALT`
that was in memory at the time of broadcast. The SHA-256 breath commitment
is therefore irrecoverable after the process exits, independent of the
secrecy of `BREATH_SECRET`.

When you run `node index.js --wipe`, the `SESSION_SALT` buffer is
overwritten with fresh random bytes before the process exits, closing the
window between `--wipe` and OS memory reclamation.

---

## 6. Sync expiry

Resonance state is not persistent. The following timers govern all
in-memory sync state:

| Timer | Duration | Effect |
|---|---|---|
| Key window | 10 seconds | Ephemeral AES key expires; past broadcasts become undecryptable |
| Warmth cooldown | 30 seconds | Joy-borrow resonance resets; device returns to neutral |
| Debounce | 4–8 seconds | Mood actions require sustained signal before firing |
| Hysteresis | 8 % | Actions reverse only after mood drops well below threshold |

After 30 seconds without a matching broadcast from a given direction,
every resonance state — dim flag, white-noise flag, coffee-trigger flag —
resets to its default (inactive) state.

There is no "friendship" or "pairing" concept. There is no stored history
of which devices you have resonated with. Every broadcast cycle starts
from scratch.

---

## 7. Forgetting your pulse

### Immediate: silent mode

Double-tap the screen in MoodAura to activate silent mode. All mood-driven
actions stop immediately. The BLE scanner continues to run (to remain
available if you re-enable), but no effects fire.

### Complete: kill switch

**ble-breath:**

```bash
node index.js --wipe
# stdout:  pulse:wiped
# exit:    0
```

This command:
1. Overwrites the in-process `SESSION_SALT` with fresh random bytes.
2. Prints `pulse:wiped` to stdout.
3. Exits immediately.

There are no files, databases, or network calls involved because there
is nothing to delete — ble-breath stores nothing on disk.

**MoodAura:**

Navigate to **Settings → Opt out & stop MoodAura**.

This call chain executes synchronously before the UI transitions:

```
wipeAllLocalData()
  ├─ clearAllEffects()              — stops brightness dim, white noise, timers
  └─ AsyncStorage.multiRemove([    — atomic multi-key removal
       '@moodaura/opted_in',
       '@moodaura/silent',
       '@moodaura/automation',
       '@moodaura/prefs'
     ])
```

After this call, `AsyncStorage.getAllKeys()` returns no `@moodaura/*` keys.
The opt-in screen appears on next launch as if the app were freshly installed.

**Equivalent: restart the app.**
Because MoodAura stores no biometric data and ble-breath stores nothing at
all, simply killing and relaunching both processes produces the same result
as the kill switch. The kill switch exists to make this guarantee explicit
and to provide a machine-verifiable confirmation (`pulse:wiped`) for
automated environments.

---

## 8. Third-party services

PulseSync optionally integrates with:

### IFTTT Webhook

If you configure an IFTTT API key in Settings, MoodAura will send an HTTP
POST request to `https://maker.ifttt.com/trigger/{event}/with/key/{key}` when
the "dragging" mood is detected. This request is:

- Sent by your device directly to IFTTT's servers.
- Subject to IFTTT's own privacy policy (https://ifttt.com/terms).
- Rate-limited by PulseSync to at most once per 30 minutes.
- Configurable: you may set the backend to "Disabled" to prevent any IFTTT
  contact.

The request body is `{ "value1": null, "value2": null, "value3": null }` —
no mood data, no breath data, no device identifier.

### Home Assistant

If you configure a Home Assistant URL and access token, MoodAura sends
`POST /api/services/switch/turn_on` with the configured entity ID to your
local Home Assistant instance. This request stays within your local network
unless you have exposed Home Assistant to the internet.

### Neither integration is active by default.

The default automation backend is `stub` — no network request is ever sent.

---

## 9. Children's privacy

PulseSync is not directed at children under 13 (US) or 16 (EU/EEA). Because
PulseSync collects no personal data from any user, it does not collect
personal data from children either. No age-gate is implemented because no
data collection requiring one exists.

---

## 10. Contact and source code

This policy can be verified by reading the source code, which is available
in full under the GNU General Public License v3. Every claim above
corresponds to auditable code.

To report a privacy concern, open an issue on the project repository with
the label `privacy`. Do not include your `BREATH_SECRET` or smart-plug
credentials in any issue or pull request.

---

## 11. Changes to this policy

Because PulseSync collects no personal data, changes to this policy are
unlikely. If a future version introduces any data collection, the version
number and effective date at the top of this document will change, and the
change will be described in the project changelog. Releases that alter
the privacy properties documented here will be tagged `privacy-change` in
the Git history.

---

*This document is provided for informational purposes. It does not constitute
legal advice. PulseSync Contributors disclaim all liability to the fullest
extent permitted by applicable law.*
