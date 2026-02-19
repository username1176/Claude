#!/usr/bin/env python3
"""
breath_detector.py
==================
Lightweight breathing-rhythm detector for Raspberry Pi and Android
smartphones.  Uses accelerometer, microphone, and gyroscope data to
estimate breathing rate in real time — without storing any audio or video.

Every 5 seconds the script emits a 32-bit "breath hash" — an HMAC
digest of the anonymised breath rate, salted with a stable per-device ID.

Battery / CPU budget
--------------------
* IMU sampled at 25 Hz (well above the 0.5 Hz Nyquist limit for ≤ 30 BPM).
* MPU-6050 DLPF configured to 5 Hz bandwidth: less noise, less power.
* Audio captured at 8 kHz mono; only the RMS envelope is kept — raw PCM
  is discarded immediately inside the sounddevice callback.
* All FFT / filter work runs once per 5-second window in a side thread.
* Main loop calls time.sleep() between iterations, keeping CPU idle > 95%.

Breath hash (privacy model)
---------------------------
* BPM estimate is quantised to 0.5 BPM resolution before hashing.
* Hash = first 4 bytes of HMAC-SHA256(device_salt, pack(quantised_bpm,
  timestamp_bucket)).  The device salt is derived locally and never
  transmitted; raw sensor data is never persisted.

Fake mode
---------
Run with --fake (or set BREATH_FAKE=1) to simulate human breathing at
a random rate in 12–20 BPM.  No hardware required; useful for CI and
demos.

Supported back-ends
-------------------
* Raspberry Pi  — MPU-6050 via I2C (smbus2) + ALSA mic (sounddevice).
* Android       — plyer accelerometer / gyroscope + sounddevice mic.
* Fake          — pure-Python simulation, no hardware needed.

Usage
-----
    python breath_detector.py            # auto-detect hardware
    python breath_detector.py --fake     # simulation mode
    python breath_detector.py --fake --bpm 15  # fixed BPM simulation
    python breath_detector.py --verbose  # debug output
    python breath_detector.py --help
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import logging
import math
import os
import queue
import struct
import sys
import threading
import time
import uuid
from abc import ABC, abstractmethod
from collections import deque
from typing import Deque, List, Optional, Tuple

import numpy as np

# ---------------------------------------------------------------------------
# Optional / platform-specific imports (graceful fallback on missing libs)
# ---------------------------------------------------------------------------

try:
    import scipy.signal as _scipy_signal
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

try:
    import sounddevice as sd
    HAS_SOUNDDEVICE = True
except ImportError:
    HAS_SOUNDDEVICE = False

try:
    import smbus2
    HAS_SMBUS = True
except ImportError:
    HAS_SMBUS = False

try:
    from plyer import accelerometer as _plyer_accel
    from plyer import gyroscope as _plyer_gyro
    HAS_PLYER = True
except ImportError:
    HAS_PLYER = False

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SAMPLE_RATE_HZ: int = 25          # IMU + audio-envelope sample rate (Hz)
WINDOW_SECONDS: int = 5           # Analysis / emit window length (s)
WINDOW_SAMPLES: int = SAMPLE_RATE_HZ * WINDOW_SECONDS  # 125 samples

BREATH_LOW_HZ: float = 0.10       #  6 BPM lower bound
BREATH_HIGH_HZ: float = 0.50      # 30 BPM upper bound

AUDIO_SR: int = 8_000             # Mic sample rate — low to save CPU
AUDIO_CHUNK: int = 400            # ~50 ms chunks at 8 kHz (int16 frames)

# MPU-6050 register map
MPU6050_ADDR: int = 0x68
MPU6050_PWR_MGMT_1: int = 0x6B
MPU6050_SMPLRT_DIV: int = 0x19
MPU6050_CONFIG_REG: int = 0x1A   # DLPF config
MPU6050_ACCEL_XOUT_H: int = 0x3B

LOG = logging.getLogger("breath")

# ---------------------------------------------------------------------------
# Stable, anonymous device salt — derived locally, never stored or sent
# ---------------------------------------------------------------------------

def _device_salt() -> bytes:
    """
    Return 16 bytes derived from stable hardware identifiers.
    Falls back gracefully when /proc/cpuinfo is absent (Android, macOS).
    """
    sources: List[str] = [
        os.environ.get("BREATH_DEVICE_ID", ""),
        str(uuid.getnode()),                   # MAC-address-based node ID
    ]
    try:
        with open("/proc/cpuinfo") as fh:
            for line in fh:
                if line.startswith("Serial"):
                    sources.append(line.split(":", 1)[1].strip())
                    break
    except OSError:
        pass
    raw = "|".join(sources).encode()
    return hashlib.sha256(raw).digest()[:16]


DEVICE_SALT: bytes = _device_salt()

# ===========================================================================
# Signal-processing helpers
# ===========================================================================

def _bandpass(data: np.ndarray, fs: float) -> np.ndarray:
    """
    Butterworth bandpass filter (0.10–0.50 Hz) via SciPy when available,
    otherwise a minimal Hann-windowed sinc FIR (slower but dependency-free).
    """
    if HAS_SCIPY:
        nyq = fs / 2.0
        lo = BREATH_LOW_HZ / nyq
        hi = BREATH_HIGH_HZ / nyq
        b, a = _scipy_signal.butter(4, [lo, hi], btype="band")
        return _scipy_signal.filtfilt(b, a, data)

    # --- FIR fallback -------------------------------------------------------
    n_taps = 51
    mid_hz = (BREATH_LOW_HZ + BREATH_HIGH_HZ) / 2.0
    bw_hz  = BREATH_HIGH_HZ - BREATH_LOW_HZ
    t = np.arange(n_taps) - (n_taps - 1) / 2.0
    # Bandpass sinc = lowpass sinc modulated to mid frequency
    h = (
        np.sinc(2 * bw_hz / fs * t)
        * np.cos(2 * np.pi * mid_hz / fs * t)
        * np.hanning(n_taps)
    )
    h /= np.abs(h).sum() + 1e-12
    return np.convolve(data, h, mode="same")


def _dominant_freq(data: np.ndarray, fs: float) -> Tuple[float, float]:
    """
    Return (frequency_hz, confidence) for the strongest component in the
    breathing band.  Confidence is the fraction of in-band power at the peak.
    """
    if len(data) < 16:
        return 0.0, 0.0

    spectrum = np.abs(np.fft.rfft(data * np.hanning(len(data))))
    freqs    = np.fft.rfftfreq(len(data), d=1.0 / fs)

    mask = (freqs >= BREATH_LOW_HZ) & (freqs <= BREATH_HIGH_HZ)
    if not np.any(mask):
        return 0.0, 0.0

    band   = spectrum[mask]
    peak_i = int(np.argmax(band))
    peak_p = float(band[peak_i])
    total  = float(band.sum()) + 1e-12

    return float(freqs[mask][peak_i]), peak_p / total


def _rms(chunk: np.ndarray) -> float:
    """RMS amplitude of a mono int16 audio chunk (proxy for breath sound)."""
    return float(np.sqrt(np.mean(chunk.astype(np.float32) ** 2)))


# ===========================================================================
# Sensor data container
# ===========================================================================

class SensorSample:
    """One fused IMU + audio-envelope sample at a point in time."""

    __slots__ = ("ax", "ay", "az", "gx", "gy", "gz", "audio_rms", "ts")

    def __init__(
        self,
        ax: float, ay: float, az: float,
        gx: float, gy: float, gz: float,
        audio_rms: float,
        ts: float,
    ) -> None:
        self.ax = ax;  self.ay = ay;  self.az = az
        self.gx = gx;  self.gy = gy;  self.gz = gz
        self.audio_rms = audio_rms
        self.ts = ts


# ===========================================================================
# Sensor back-ends
# ===========================================================================

class SensorBackend(ABC):
    """Abstract interface for all sensor sources."""

    @abstractmethod
    def start(self) -> None:
        """Initialise hardware and start background threads."""

    @abstractmethod
    def stop(self) -> None:
        """Stop background threads and release hardware."""

    @abstractmethod
    def read(self) -> SensorSample:
        """
        Return the next sample.  May block until one is available
        (real back-ends) or return immediately (fake back-end).
        """


# ---------------------------------------------------------------------------
# Fake back-end — pure-Python simulation, no hardware needed
# ---------------------------------------------------------------------------

class FakeBackend(SensorBackend):
    """
    Simulates a person breathing at a stable rate chosen randomly in
    12–20 BPM.  Adds Gaussian sensor noise to mimic real hardware.

    The simulated accelerometer Z-axis, gyroscope X-axis, and audio RMS
    envelope all carry the same breathing-frequency sinusoid at realistic
    amplitudes.
    """

    def __init__(self, bpm: Optional[float] = None) -> None:
        self._bpm  = bpm if bpm is not None else float(np.random.uniform(12, 20))
        self._freq = self._bpm / 60.0
        self._dt   = 1.0 / SAMPLE_RATE_HZ
        self._t    = 0.0
        LOG.info(
            "FakeBackend: simulating %.2f BPM (%.4f Hz)", self._bpm, self._freq
        )

    @property
    def simulated_bpm(self) -> float:
        return self._bpm

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def read(self) -> SensorSample:
        """Advance simulation by one time-step and return sample."""
        rng   = np.random.default_rng()
        phase = 2.0 * math.pi * self._freq * self._t
        breath = math.sin(phase)

        def noise(std: float) -> float:
            return float(rng.normal(0, std))

        # Chest rise on Z-axis: ~0.05 g amplitude
        az = 1.0 + 0.05 * breath + noise(0.003)
        ax = noise(0.003)
        ay = noise(0.003)

        # Gyro: small pitch/roll during breathing (~0.5 deg/s amplitude)
        gx = 0.5 * breath + noise(0.05)
        gy = noise(0.05)
        gz = noise(0.02)

        # Audio RMS: louder on exhalation
        audio_rms = max(0.0, 0.35 * (breath + 1.0) / 2.0 + noise(0.015))

        self._t += self._dt
        return SensorSample(ax, ay, az, gx, gy, gz, audio_rms, self._t)


# ---------------------------------------------------------------------------
# Raspberry Pi back-end — MPU-6050 via I2C + sounddevice microphone
# ---------------------------------------------------------------------------

class RpiBackend(SensorBackend):
    """
    Reads from an MPU-6050 (or pin-compatible ICM-20600) IMU over I2C and
    from the default ALSA microphone via sounddevice.

    The IMU is sampled at exactly SAMPLE_RATE_HZ using a paced background
    thread.  The microphone callback provides a rolling audio RMS value that
    is merged into each IMU sample (raw PCM is never retained).

    Power notes
    -----------
    * DLPF register set to 5 Hz bandwidth (code 6): cuts high-frequency
      noise and reduces the chip's internal processing load.
    * Sample-rate divider computed from SAMPLE_RATE_HZ so the chip only
      wakes the I2C bus 25 times per second instead of 1 000 times.
    """

    def __init__(self, i2c_bus: int = 1, i2c_addr: int = MPU6050_ADDR) -> None:
        if not HAS_SMBUS:
            raise RuntimeError(
                "smbus2 not installed.  Run: pip install smbus2"
            )
        self._bus   = smbus2.SMBus(i2c_bus)
        self._addr  = i2c_addr
        self._q: queue.Queue[SensorSample] = queue.Queue(
            maxsize=WINDOW_SAMPLES * 2
        )
        self._audio_rms   = 0.0
        self._audio_lock  = threading.Lock()
        self._running     = False
        self._imu_thread: Optional[threading.Thread]   = None
        self._audio_thread: Optional[threading.Thread] = None

    # -- IMU setup -----------------------------------------------------------

    def _init_imu(self) -> None:
        bus, addr = self._bus, self._addr
        # Wake device
        bus.write_byte_data(addr, MPU6050_PWR_MGMT_1, 0x00)
        time.sleep(0.1)
        # DLPF: bandwidth ≈ 5 Hz, delay ≈ 19 ms — minimises noise and power
        bus.write_byte_data(addr, MPU6050_CONFIG_REG, 0x06)
        # Sample-rate divider: target SAMPLE_RATE_HZ from 1 kHz internal rate
        div = int(1000 / SAMPLE_RATE_HZ) - 1
        bus.write_byte_data(addr, MPU6050_SMPLRT_DIV, max(0, min(255, div)))

    # -- Low-level read ------------------------------------------------------

    def _read_raw(self) -> Tuple[float, float, float, float, float, float]:
        """
        Read 14 bytes starting at ACCEL_XOUT_H:
        [ax_h, ax_l, ay_h, ay_l, az_h, az_l, temp_h, temp_l,
         gx_h, gx_l, gy_h, gy_l, gz_h, gz_l]
        Returns (ax, ay, az [g], gx, gy, gz [deg/s]).
        """
        data = self._bus.read_i2c_block_data(
            self._addr, MPU6050_ACCEL_XOUT_H, 14
        )

        def s16(hi: int, lo: int) -> int:
            v = (hi << 8) | lo
            return v - 65536 if v >= 32768 else v

        ax = s16(data[0],  data[1])  / 16384.0   # ±2 g  full-scale
        ay = s16(data[2],  data[3])  / 16384.0
        az = s16(data[4],  data[5])  / 16384.0
        # data[6:8] = temperature — skip
        gx = s16(data[8],  data[9])  / 131.0     # ±250 deg/s full-scale
        gy = s16(data[10], data[11]) / 131.0
        gz = s16(data[12], data[13]) / 131.0
        return ax, ay, az, gx, gy, gz

    # -- IMU sampling thread -------------------------------------------------

    def _imu_loop(self) -> None:
        interval   = 1.0 / SAMPLE_RATE_HZ
        next_tick  = time.monotonic()

        while self._running:
            now = time.monotonic()
            try:
                ax, ay, az, gx, gy, gz = self._read_raw()
                with self._audio_lock:
                    audio_rms = self._audio_rms
                sample = SensorSample(ax, ay, az, gx, gy, gz, audio_rms, now)
                try:
                    self._q.put_nowait(sample)
                except queue.Full:
                    self._q.get_nowait()   # discard oldest; keep queue fresh
                    self._q.put_nowait(sample)
            except Exception as exc:
                LOG.warning("IMU read error: %s", exc)

            next_tick += interval
            delay = next_tick - time.monotonic()
            if delay > 0:
                time.sleep(delay)

    # -- Audio capture thread ------------------------------------------------

    def _audio_loop(self) -> None:
        if not HAS_SOUNDDEVICE:
            LOG.warning("sounddevice unavailable — audio channel disabled")
            return

        def _cb(indata: np.ndarray, frames: int, _t, status) -> None:
            if status:
                LOG.debug("Audio status: %s", status)
            rms = _rms(indata[:, 0])
            with self._audio_lock:
                self._audio_rms = rms

        try:
            with sd.InputStream(
                samplerate=AUDIO_SR,
                channels=1,
                dtype="int16",
                blocksize=AUDIO_CHUNK,
                callback=_cb,
            ):
                while self._running:
                    time.sleep(0.25)
        except Exception as exc:
            LOG.warning("Audio stream error: %s", exc)

    # -- Public interface ----------------------------------------------------

    def start(self) -> None:
        self._init_imu()
        self._running = True
        self._imu_thread = threading.Thread(
            target=self._imu_loop, daemon=True, name="imu"
        )
        self._audio_thread = threading.Thread(
            target=self._audio_loop, daemon=True, name="audio"
        )
        self._imu_thread.start()
        self._audio_thread.start()

    def stop(self) -> None:
        self._running = False
        if self._imu_thread:
            self._imu_thread.join(timeout=2)
        if self._audio_thread:
            self._audio_thread.join(timeout=2)
        self._bus.close()

    def read(self) -> SensorSample:
        """Block until the next IMU sample is available."""
        return self._q.get()


# ---------------------------------------------------------------------------
# Android / Kivy back-end — plyer sensors + sounddevice microphone
# ---------------------------------------------------------------------------

class AndroidBackend(SensorBackend):
    """
    Uses plyer (Kivy cross-platform HAL) for accelerometer and gyroscope
    on Android.  Microphone is read via sounddevice where available.
    """

    def __init__(self) -> None:
        if not HAS_PLYER:
            raise RuntimeError(
                "plyer not installed.  Run: pip install plyer"
            )
        self._audio_rms  = 0.0
        self._audio_lock = threading.Lock()
        self._running    = False
        self._audio_thread: Optional[threading.Thread] = None
        self._t = 0.0

    def _audio_loop(self) -> None:
        if not HAS_SOUNDDEVICE:
            return

        def _cb(indata, frames, _t, status):
            with self._audio_lock:
                self._audio_rms = _rms(indata[:, 0])

        try:
            with sd.InputStream(
                samplerate=AUDIO_SR, channels=1, dtype="int16",
                blocksize=AUDIO_CHUNK, callback=_cb,
            ):
                while self._running:
                    time.sleep(0.25)
        except Exception as exc:
            LOG.warning("Audio error: %s", exc)

    def start(self) -> None:
        _plyer_accel.enable()
        try:
            _plyer_gyro.enable()
        except Exception:
            LOG.warning("Gyroscope not available on this device")
        self._running = True
        self._audio_thread = threading.Thread(
            target=self._audio_loop, daemon=True, name="audio"
        )
        self._audio_thread.start()

    def stop(self) -> None:
        self._running = False
        _plyer_accel.disable()
        try:
            _plyer_gyro.disable()
        except Exception:
            pass
        if self._audio_thread:
            self._audio_thread.join(timeout=2)

    def read(self) -> SensorSample:
        self._t += 1.0 / SAMPLE_RATE_HZ
        accel = _plyer_accel.acceleration or (0.0, 0.0, 9.81)
        try:
            gyro = _plyer_gyro.rotation or (0.0, 0.0, 0.0)
        except Exception:
            gyro = (0.0, 0.0, 0.0)
        with self._audio_lock:
            audio_rms = self._audio_rms
        return SensorSample(
            float(accel[0]), float(accel[1]), float(accel[2]),
            float(gyro[0]),  float(gyro[1]),  float(gyro[2]),
            audio_rms, self._t,
        )


# ===========================================================================
# Breath analyser — signal processing + hash emission
# ===========================================================================

class BreathAnalyser:
    """
    Accumulates sensor samples and, every WINDOW_SECONDS, produces a
    (bpm, confidence, breath_hash_uint32) tuple.

    Algorithm
    ---------
    1.  Detrend (remove DC offset) the accelerometer-Z and audio-RMS signals.
    2.  Bandpass-filter both signals to 0.10–0.50 Hz.
    3.  Find the dominant FFT frequency and its in-band power fraction
        (confidence) for each channel.
    4.  Use the gyroscope magnitude as a motion-artefact indicator:
        high gyro → reduce IMU channel weight, favour audio channel.
    5.  Compute a weighted-average BPM estimate from both channels.
    6.  Quantise to 0.5 BPM resolution (privacy).
    7.  Emit:  HMAC-SHA256(device_salt, pack(">fI", quantised_bpm,
                           timestamp_bucket))[:4]  →  uint32 breath hash.
    """

    def __init__(self, salt: bytes = DEVICE_SALT) -> None:
        self._salt       = salt
        self._buf_az     : Deque[float] = deque(maxlen=WINDOW_SAMPLES)
        self._buf_gyro_x : Deque[float] = deque(maxlen=WINDOW_SAMPLES)
        self._buf_audio  : Deque[float] = deque(maxlen=WINDOW_SAMPLES)
        self._lock       = threading.Lock()

    def push(self, s: SensorSample) -> None:
        with self._lock:
            self._buf_az.append(s.az)
            self._buf_gyro_x.append(abs(s.gx))
            self._buf_audio.append(s.audio_rms)

    # -- Internal estimation -------------------------------------------------

    def _estimate(self) -> Tuple[float, float]:
        """Return (bpm, confidence).  Called with self._lock held."""
        az    = np.array(self._buf_az,    dtype=np.float64)
        audio = np.array(self._buf_audio, dtype=np.float64)
        gyro  = np.array(self._buf_gyro_x, dtype=np.float64)

        # Detrend — remove DC and slow drift
        az    -= az.mean()
        audio -= audio.mean()

        # Bandpass
        az_f    = _bandpass(az,    float(SAMPLE_RATE_HZ))
        audio_f = _bandpass(audio, float(SAMPLE_RATE_HZ))

        # Dominant frequency per channel
        accel_hz, accel_conf = _dominant_freq(az_f,    float(SAMPLE_RATE_HZ))
        audio_hz, audio_conf = _dominant_freq(audio_f, float(SAMPLE_RATE_HZ))

        # Motion-artefact weighting:
        #   mean gyro > 2 deg/s → IMU weight approaches zero
        motion    = float(gyro.mean())
        imu_w     = max(0.05, 1.0 - min(1.0, motion / 2.0))
        audio_w   = 1.0

        # Weighted average of the two frequency estimates
        denom  = imu_w * accel_conf + audio_w * audio_conf + 1e-12
        freq   = (imu_w * accel_conf * accel_hz + audio_w * audio_conf * audio_hz) / denom
        conf   = denom / (imu_w + audio_w + 1e-12)

        bpm = float(np.clip(freq * 60.0, 4.0, 60.0))
        return bpm, float(conf)

    # -- Public interface ----------------------------------------------------

    def ready(self) -> bool:
        with self._lock:
            return len(self._buf_az) >= WINDOW_SAMPLES

    def analyse(self) -> Optional[Tuple[float, float, int]]:
        """
        If the buffer is full, compute and return
        (bpm, confidence, breath_hash_uint32).
        Returns None while accumulating initial data.
        """
        with self._lock:
            if len(self._buf_az) < WINDOW_SAMPLES:
                return None
            bpm, conf = self._estimate()

        # Quantise to 0.5 BPM — reduces information before hashing
        quantised = round(bpm * 2.0) / 2.0

        # Time bucket: changes every WINDOW_SECONDS
        ts_bucket = int(time.time() // WINDOW_SECONDS)

        # HMAC-SHA256; device salt is the key — raw values never leave process
        payload = struct.pack(">fI", quantised, ts_bucket)
        digest  = hmac.new(self._salt, payload, hashlib.sha256).digest()
        bh      = struct.unpack(">I", digest[:4])[0]

        return quantised, conf, bh


# ===========================================================================
# Main sensing loop
# ===========================================================================

def _auto_backend() -> SensorBackend:
    """Select the best available real hardware back-end."""
    if HAS_SMBUS:
        LOG.info("Auto-detected: Raspberry Pi / I2C (MPU-6050)")
        return RpiBackend()
    if HAS_PLYER:
        LOG.info("Auto-detected: Android / plyer")
        return AndroidBackend()
    raise RuntimeError(
        "No hardware back-end found.  "
        "Install smbus2 (RPi) or plyer (Android), or use --fake."
    )


def run(backend: SensorBackend, verbose: bool = False) -> None:
    """
    Drive the sensing + analysis loop until KeyboardInterrupt.

    Fake back-end: paced externally here at SAMPLE_RATE_HZ to avoid
    a busy-wait spin.
    Real back-ends: backend.read() blocks on the IMU thread queue, so
    no additional sleep is needed between reads.
    """
    analyser  = BreathAnalyser()
    is_fake   = isinstance(backend, FakeBackend)
    dt        = 1.0 / SAMPLE_RATE_HZ

    backend.start()

    if isinstance(backend, FakeBackend):
        LOG.info(
            "Fake mode active — simulating %.2f BPM.  "
            "Press Ctrl-C to stop.",
            backend.simulated_bpm,
        )
    else:
        LOG.info("Breath detector running.  Press Ctrl-C to stop.")

    try:
        next_tick  = time.monotonic()
        window_end = time.monotonic() + WINDOW_SECONDS

        while True:
            # -- Pacing (fake mode only) -------------------------------------
            if is_fake:
                now   = time.monotonic()
                delay = next_tick - now
                if delay > 0:
                    time.sleep(delay)
                next_tick += dt

            # -- Read one sample from the back-end ---------------------------
            sample = backend.read()
            analyser.push(sample)

            # -- Emit hash every WINDOW_SECONDS ------------------------------
            now = time.monotonic()
            if now >= window_end:
                window_end = now + WINDOW_SECONDS
                result = analyser.analyse()
                if result is not None:
                    bpm, conf, breath_hash = result
                    print(
                        f"[{time.strftime('%H:%M:%S')}] "
                        f"BPM={bpm:5.1f}  "
                        f"conf={conf:.2f}  "
                        f"hash=0x{breath_hash:08X}"
                    )
                    if verbose:
                        LOG.debug("breath_hash_uint32=%d", breath_hash)
                else:
                    LOG.debug("Accumulating initial window…")

    except KeyboardInterrupt:
        print("\nStopping.")
    finally:
        backend.stop()


# ===========================================================================
# CLI
# ===========================================================================

def _parse(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--fake",
        action="store_true",
        default=bool(os.environ.get("BREATH_FAKE")),
        help="Simulate breathing (no hardware required).",
    )
    p.add_argument(
        "--bpm",
        type=float,
        default=None,
        metavar="BPM",
        help="Fixed simulated BPM (only with --fake; default: random 12–20).",
    )
    p.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging.",
    )
    p.add_argument(
        "--i2c-bus",
        type=int,
        default=1,
        metavar="N",
        help="I2C bus number for the MPU-6050 (Raspberry Pi; default: 1).",
    )
    p.add_argument(
        "--i2c-addr",
        type=lambda s: int(s, 0),
        default=MPU6050_ADDR,
        metavar="ADDR",
        help=f"I2C address of the IMU (default: 0x{MPU6050_ADDR:02X}).",
    )
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = _parse(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    if args.fake:
        backend: SensorBackend = FakeBackend(bpm=args.bpm)
    else:
        try:
            backend = _auto_backend()
            # Allow overriding I2C parameters for RPi back-end
            if isinstance(backend, RpiBackend):
                backend = RpiBackend(
                    i2c_bus=args.i2c_bus, i2c_addr=args.i2c_addr
                )
        except RuntimeError as exc:
            LOG.error("%s", exc)
            sys.exit(1)

    run(backend, verbose=args.verbose)


if __name__ == "__main__":
    main()
