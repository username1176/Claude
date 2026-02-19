/**
 * WhiteNoiseService
 *
 * Plays a looping white-noise track when the 'stressed' mood is detected.
 * Uses react-native-sound.
 *
 * Asset: place `white-noise.mp3` in src/assets/audio/ and link it via the
 * metro bundler.  On Android it goes in android/app/src/main/res/raw/.
 * On iOS, add it to the Xcode project bundle.
 *
 * play()  — starts looping, volume fade-in over 3 s
 * stop()  — fade-out over 2 s then stop
 */

import Sound from 'react-native-sound';

Sound.setCategory('Playback', true);   // mix with other audio, no ducking

const TRACK      = 'white_noise';      // filename without extension
const BASE_PATH  = Sound.MAIN_BUNDLE;
const FADE_STEPS = 30;

let _sound  = null;
let _active = false;
let _fadeTimer = null;

function clearFade() {
  if (_fadeTimer) { clearInterval(_fadeTimer); _fadeTimer = null; }
}

function loadSound() {
  return new Promise((resolve, reject) => {
    const s = new Sound(TRACK + '.mp3', BASE_PATH, err => {
      if (err) reject(err);
      else resolve(s);
    });
  });
}

function fadeVolume(sound, from, to, durationMs, onDone) {
  clearFade();
  const steps    = FADE_STEPS;
  const interval = durationMs / steps;
  const delta    = (to - from) / steps;
  let current    = from;
  let step       = 0;
  sound.setVolume(from);
  _fadeTimer = setInterval(() => {
    step++;
    current += delta;
    sound.setVolume(Math.max(0, Math.min(1, current)));
    if (step >= steps) {
      clearFade();
      onDone?.();
    }
  }, interval);
}

export async function playWhiteNoise() {
  if (_active) return;
  _active = true;
  try {
    if (!_sound) {
      _sound = await loadSound();
      _sound.setNumberOfLoops(-1);   // infinite loop
    }
    _sound.setVolume(0);
    _sound.play();
    fadeVolume(_sound, 0, 0.55, 3000);
  } catch (_) {
    _active = false;
  }
}

export async function stopWhiteNoise() {
  if (!_active || !_sound) return;
  clearFade();
  fadeVolume(_sound, _sound.getVolume?.() ?? 0.55, 0, 2000, () => {
    _sound?.stop();
    _active = false;
  });
}

export const isPlaying = () => _active;
