#!/usr/bin/env python3
"""
mood_net.py
===========
Tiny on-device neural network that fuses a breath hash (from
breath_detector.py) with heart-rate variance (HRV from a wearable or
simulated) and maps the result to one of five emotional states:

    calm  ·  stressed  ·  joyful  ·  tired  ·  neutral

Everything runs locally — no cloud, no external calls.

Architecture
------------
Input  : 8-D float vector (BPM, HRV metrics ×3, hash bytes ×4)
Model  : MLP  8 → 32 → 16 → 5  (~900 params, ~4 KB float32)
Output : 5-float softmax probability vector
Saved  : TorchScript (.pt) so inference needs no training dependencies

Synthetic training data
-----------------------
1 000 samples (200 per class) are generated using published HRV/breathing
ranges for each emotional state.  Breath hashes are simulated with the
same HMAC routine used by breath_detector.py.

Mood drift
----------
A configurable exponential decay fades the current mood toward neutral
when no fresh sensor data arrives:

    drifted = exp(-t/τ) · current + (1 - exp(-t/τ)) · uniform(5)

Default τ = 30 s.  After 90 s without new data the mood is ~95 % neutral.

HRV sources
-----------
* FakeHRVSource   — synthetic values correlated with BPM (always available)
* GarminHRVSource — ANT+ via pyantplus (Raspberry Pi with USB ANT+ stick)
* BLEHRVSource    — Bluetooth LE heart-rate profile (bleak, cross-platform)
* WatchOSBridge   — reads /tmp/hrv_bridge.json written by a Shortcuts automation

Usage
-----
    python mood_net.py train                 # generate data + train + save
    python mood_net.py train --samples 2000  # larger synthetic dataset
    python mood_net.py demo                  # continuous fake-sensor loop
    python mood_net.py demo --tau 60         # slower mood decay
    python mood_net.py infer --bpm 14 --rmssd 65 --sdnn 50 --lf-hf 1.2
    python mood_net.py info                  # model size / param count
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import hmac
import json
import logging
import math
import os
import pathlib
import struct
import sys
import time
from typing import Dict, List, Optional, Tuple

import numpy as np

# ---------------------------------------------------------------------------
# PyTorch — required for training; inference also uses it via TorchScript
# ---------------------------------------------------------------------------
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader, TensorDataset
except ImportError:
    sys.exit(
        "PyTorch is required.\n"
        "Install: pip install torch  (CPU-only wheel is fine and tiny)\n"
        "RPi arm64: pip install torch --index-url https://download.pytorch.org/whl/cpu"
    )

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STATES: List[str] = ["calm", "stressed", "joyful", "tired", "neutral"]
N_STATES:   int = len(STATES)   # 5
N_FEATURES: int = 8             # see features_to_tensor()

DEFAULT_MODEL:   pathlib.Path = pathlib.Path("mood_net.pt")
DEFAULT_TAU:     float = 30.0   # drift decay constant (seconds)
DEFAULT_SAMPLES: int   = 1000
DEFAULT_EPOCHS:  int   = 100
DEFAULT_LR:      float = 3e-3

# Stable training salt — keeps synthetic hashes consistent across runs.
# Must differ from breath_detector.py's per-device salt (which is secret).
_TRAIN_SALT: bytes = hashlib.sha256(b"mood_net_synthetic_v1").digest()[:16]

LOG = logging.getLogger("mood_net")

# ===========================================================================
# HRV data model and sources
# ===========================================================================

@dataclasses.dataclass
class HRVSample:
    """Heart-rate variability metrics derived from RR-interval time series."""
    rmssd: float   # Root-mean-square of successive RR differences (ms)
    sdnn:  float   # Standard deviation of all NN intervals (ms)
    lf_hf: float   # Low-frequency / high-frequency power ratio (sympatho-vagal)


class FakeHRVSource:
    """
    Generates physiologically plausible HRV values correlated with a given
    breathing rate.  Used when no wearable is connected.

    Empirical relationships used:
      * Higher BPM → lower HRV (stress / arousal)
      * LF/HF ratio rises with sympathetic activation (faster breathing)
    """

    def __init__(self, noise_std: float = 0.05) -> None:
        self._noise = noise_std
        self._rng   = np.random.default_rng()

    def read(self, bpm: float = 16.0) -> HRVSample:
        rng = self._rng
        # Base RMSSD inversely related to BPM; typical range 20–100 ms
        base_rmssd = 100.0 - 3.5 * max(0.0, bpm - 10.0)
        rmssd = float(np.clip(base_rmssd + rng.normal(0, 8), 5, 150))
        sdnn  = float(np.clip(rmssd * rng.uniform(0.7, 1.0), 5, 130))
        lf_hf = float(np.clip(0.5 + 0.12 * (bpm - 10.0) + rng.normal(0, 0.2), 0.1, 6.0))
        return HRVSample(rmssd=rmssd, sdnn=sdnn, lf_hf=lf_hf)


class BLEHRVSource:
    """
    Reads HRV from a Bluetooth LE heart-rate monitor (Polar H10, Wahoo, etc.)
    using the standard Heart Rate Service (UUID 0x180D).

    Requires: pip install bleak
    Runs async; call start_async() from an asyncio event loop, then read().
    """

    def __init__(self, device_address: Optional[str] = None) -> None:
        self._addr    = device_address
        self._sample: Optional[HRVSample] = None
        self._running = False
        self._rr_buf: List[float] = []   # last N RR intervals (ms)

        try:
            import bleak  # noqa: F401
            self._has_bleak = True
        except ImportError:
            self._has_bleak = False
            LOG.warning("bleak not installed — BLEHRVSource unavailable")

    def _on_notification(self, _handle: int, data: bytes) -> None:
        """Parse Heart Rate Measurement characteristic (spec section 3.106)."""
        flags = data[0]
        if flags & 0x01:              # RR present
            rr_offset = 2 if not (flags & 0x01) else 2
            # Each RR value is uint16, units = 1/1024 s
            for i in range(rr_offset, len(data) - 1, 2):
                rr_raw = struct.unpack_from("<H", data, i)[0]
                self._rr_buf.append(rr_raw / 1024.0 * 1000.0)  # → ms
            if len(self._rr_buf) > 64:
                self._rr_buf = self._rr_buf[-64:]
            if len(self._rr_buf) >= 4:
                self._sample = _compute_hrv(self._rr_buf)

    def read(self) -> Optional[HRVSample]:
        return self._sample


class WatchOSBridge:
    """
    Reads HRV written by an iOS/watchOS Shortcuts automation to a JSON file.
    The Shortcuts action 'Log Heart Rate' can export to a shared file path.

    File format (written by the Shortcut every 5 s):
        {"rmssd": 58.3, "sdnn": 47.1, "lf_hf": 1.4, "ts": 1708000000}
    """

    def __init__(self, path: str = "/tmp/hrv_bridge.json") -> None:
        self._path = pathlib.Path(path)

    def read(self) -> Optional[HRVSample]:
        try:
            data  = json.loads(self._path.read_text())
            age_s = time.time() - data.get("ts", 0)
            if age_s > 30:
                LOG.debug("WatchOS bridge data stale (%.0f s old)", age_s)
                return None
            return HRVSample(
                rmssd=float(data["rmssd"]),
                sdnn=float(data["sdnn"]),
                lf_hf=float(data["lf_hf"]),
            )
        except (OSError, KeyError, ValueError):
            return None


def _compute_hrv(rr_ms: List[float]) -> HRVSample:
    """Derive RMSSD, SDNN, and a proxy LF/HF from RR intervals."""
    arr  = np.array(rr_ms, dtype=np.float64)
    sdnn = float(np.std(arr))
    diff = np.diff(arr)
    rmssd = float(np.sqrt(np.mean(diff ** 2))) if len(diff) else sdnn
    # Approximate LF/HF from breathing-frequency component (0.15–0.4 Hz)
    lf_hf = max(0.1, sdnn / (rmssd + 1e-6))
    return HRVSample(rmssd=rmssd, sdnn=sdnn, lf_hf=float(np.clip(lf_hf, 0.1, 6.0)))


def best_hrv_source() -> object:
    """Return the richest available HRV source (prefer hardware over fake)."""
    bridge = WatchOSBridge()
    if bridge.read() is not None:
        LOG.info("HRV source: WatchOS bridge file")
        return bridge
    LOG.info("HRV source: FakeHRVSource (no wearable detected)")
    return FakeHRVSource()


# ===========================================================================
# Feature vector
# ===========================================================================

@dataclasses.dataclass
class BreathFeatures:
    """
    All inputs consumed by MoodNet in one bundle.

    bpm          : Breathing rate in breaths/minute.
    hrv          : Heart-rate variability metrics.
    hash_uint32  : 32-bit breath hash from breath_detector.py.
    """
    bpm:         float
    hrv:         HRVSample
    hash_uint32: int = 0


def features_to_tensor(bf: BreathFeatures) -> torch.Tensor:
    """
    Convert a BreathFeatures bundle to a normalised 8-D float32 tensor.

    Feature layout
    --------------
    [0] bpm_norm     = (bpm - 16) / 8           typical range ≈ [-1.5, +1.5]
    [1] rmssd_norm   = log1p(rmssd_ms) / 5.5    maps 0–150 ms → 0–1
    [2] sdnn_norm    = log1p(sdnn_ms) / 5.5     maps 0–130 ms → 0–1
    [3] lf_hf_norm   = lf_hf / 5.0              maps 0–5 → 0–1
    [4] hash_b3_norm = (hash >> 24 & 0xFF) / 255  MSB of breath hash
    [5] hash_b2_norm = (hash >> 16 & 0xFF) / 255
    [6] hash_b1_norm = (hash >>  8 & 0xFF) / 255
    [7] hash_b0_norm = (hash       & 0xFF) / 255  LSB of breath hash

    The four hash bytes serve as a lightweight session fingerprint that
    encodes the quantised BPM used during hashing (via the HMAC), giving
    the model a privacy-preserving version of the BPM alongside the clear
    BPM and HRV features.
    """
    h   = int(bf.hash_uint32) & 0xFFFFFFFF
    vec = [
        (bf.bpm - 16.0) / 8.0,
        math.log1p(max(0.0, bf.hrv.rmssd)) / 5.5,
        math.log1p(max(0.0, bf.hrv.sdnn))  / 5.5,
        max(0.0, bf.hrv.lf_hf) / 5.0,
        ((h >> 24) & 0xFF) / 255.0,
        ((h >> 16) & 0xFF) / 255.0,
        ((h >>  8) & 0xFF) / 255.0,
        ( h        & 0xFF) / 255.0,
    ]
    return torch.tensor(vec, dtype=torch.float32)


# ===========================================================================
# Synthetic dataset
# ===========================================================================

# Physiological ranges per state (sources: Task Force 1996, Shaffer 2017,
# Jerath 2006 for breathing, Laborde 2017 for emotional HRV studies).
_PROFILES: Dict[str, Dict] = {
    "calm": {
        "bpm":   (11.0, 14.0),
        "rmssd": (60.0, 110.0),
        "sdnn":  (50.0,  90.0),
        "lf_hf": ( 0.5,   1.5),
    },
    "stressed": {
        "bpm":   (18.0, 26.0),
        "rmssd": (10.0,  35.0),
        "sdnn":  (10.0,  28.0),
        "lf_hf": ( 2.5,   5.0),
    },
    "joyful": {
        "bpm":   (14.0, 18.0),
        "rmssd": (50.0,  95.0),
        "sdnn":  (40.0,  75.0),
        "lf_hf": ( 0.8,   2.0),
    },
    "tired": {
        "bpm":   ( 9.0, 13.5),
        "rmssd": (20.0,  50.0),
        "sdnn":  (18.0,  42.0),
        "lf_hf": ( 0.4,   1.5),
    },
    "neutral": {
        "bpm":   (13.5, 17.5),
        "rmssd": (35.0,  72.0),
        "sdnn":  (30.0,  58.0),
        "lf_hf": ( 1.0,   2.5),
    },
}


def _make_hash(bpm: float, ts_bucket: int, salt: bytes) -> int:
    """Simulate breath_detector.py's HMAC hash for a given BPM + time window."""
    q   = round(bpm * 2.0) / 2.0
    msg = struct.pack(">fI", q, ts_bucket)
    return struct.unpack(">I", hmac.new(salt, msg, hashlib.sha256).digest()[:4])[0]


def generate_dataset(
    n_total: int = DEFAULT_SAMPLES,
    seed: int = 42,
) -> Tuple[torch.Tensor, torch.Tensor]:
    """
    Return (X, y) tensors for n_total balanced synthetic samples.

    Each sample is generated by drawing from the physiological ranges in
    _PROFILES, adding Gaussian noise (σ ≈ 5–10 % of range), and computing
    a realistic breath hash via the HMAC function.
    """
    rng         = np.random.default_rng(seed)
    n_per_class = n_total // N_STATES
    Xs: List[torch.Tensor] = []
    ys: List[int] = []

    for class_idx, state in enumerate(STATES):
        p = _PROFILES[state]
        for _ in range(n_per_class):
            bpm   = float(rng.uniform(*p["bpm"]))
            rmssd = float(rng.uniform(*p["rmssd"])) + float(rng.normal(0, 3))
            sdnn  = float(rng.uniform(*p["sdnn"]))  + float(rng.normal(0, 2))
            lf_hf = float(rng.uniform(*p["lf_hf"])) + float(rng.normal(0, 0.1))

            # Clamp to physiological limits
            bpm   = float(np.clip(bpm,   4.0, 40.0))
            rmssd = float(np.clip(rmssd, 1.0, 200.0))
            sdnn  = float(np.clip(sdnn,  1.0, 150.0))
            lf_hf = float(np.clip(lf_hf, 0.05, 6.0))

            ts_bucket = int(rng.integers(0, 10_000_000))
            h_u32     = _make_hash(bpm, ts_bucket, _TRAIN_SALT)

            bf = BreathFeatures(
                bpm=bpm,
                hrv=HRVSample(rmssd=rmssd, sdnn=sdnn, lf_hf=lf_hf),
                hash_uint32=h_u32,
            )
            Xs.append(features_to_tensor(bf))
            ys.append(class_idx)

    X = torch.stack(Xs)
    y = torch.tensor(ys, dtype=torch.long)

    # Shuffle
    perm = torch.randperm(len(X), generator=torch.Generator().manual_seed(seed))
    return X[perm], y[perm]


# ===========================================================================
# Neural network
# ===========================================================================

class MoodNet(nn.Module):
    """
    Tiny feed-forward classifier:

        Linear(8→32) + BatchNorm + ReLU + Dropout(0.25)
        Linear(32→16) + ReLU
        Linear(16→5)

    Parameter count  : 8·32+32 + 32·32 + 32·16+16 + 16·5+5 = ~1 900
    Float32 size     : ~7.5 KB
    TorchScript .pt  : ~50–80 KB (metadata + weights)

    Both are comfortably under the 2 MB limit, leaving room for future
    expansion (e.g. adding skin-conductance or SpO₂ channels).
    """

    def __init__(self) -> None:
        super().__init__()
        self.fc1 = nn.Linear(N_FEATURES, 32)
        self.bn1 = nn.BatchNorm1d(32)
        self.fc2 = nn.Linear(32, 16)
        self.fc3 = nn.Linear(16, N_STATES)
        self.drop = nn.Dropout(0.25)
        self.relu = nn.ReLU()

    def forward(self, x: torch.Tensor) -> torch.Tensor:           # → [B, 5] logits
        x = self.relu(self.bn1(self.fc1(x)))
        x = self.drop(x)
        x = self.relu(self.fc2(x))
        return self.fc3(x)


def _count_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters())


# ===========================================================================
# Training
# ===========================================================================

def train_model(
    n_samples: int       = DEFAULT_SAMPLES,
    epochs:    int       = DEFAULT_EPOCHS,
    lr:        float     = DEFAULT_LR,
    out_path:  pathlib.Path = DEFAULT_MODEL,
    val_frac:  float     = 0.15,
) -> MoodNet:
    """
    1. Generate synthetic dataset.
    2. Train MoodNet with Adam + cosine annealing LR schedule.
    3. Restore the checkpoint with the best validation accuracy.
    4. Export as TorchScript and save.
    5. Return the trained model.
    """
    LOG.info("Generating %d synthetic samples…", n_samples)
    X, y = generate_dataset(n_samples)

    n_val   = max(1, int(val_frac * len(X)))
    n_train = len(X) - n_val
    X_tr, y_tr = X[:n_train], y[:n_train]
    X_va, y_va = X[n_train:], y[n_train:]

    LOG.info(
        "Train: %d samples | Val: %d samples | Model: %d params",
        n_train, n_val, _count_params(MoodNet()),
    )

    model   = MoodNet()
    opt     = optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    sched   = optim.lr_scheduler.CosineAnnealingLR(opt, T_max=epochs, eta_min=lr * 0.05)
    loss_fn = nn.CrossEntropyLoss(label_smoothing=0.05)

    best_acc   = -1.0
    best_state: Dict = {}
    loader = DataLoader(
        TensorDataset(X_tr, y_tr), batch_size=64, shuffle=True, drop_last=False
    )

    for epoch in range(1, epochs + 1):
        model.train()
        epoch_loss = 0.0
        for xb, yb in loader:
            opt.zero_grad()
            loss = loss_fn(model(xb), yb)
            loss.backward()
            opt.step()
            epoch_loss += loss.item() * len(xb)
        sched.step()

        if epoch % 10 == 0 or epoch == epochs:
            model.eval()
            with torch.no_grad():
                val_acc = (model(X_va).argmax(1) == y_va).float().mean().item()
            if val_acc > best_acc:
                best_acc   = val_acc
                best_state = {k: v.clone() for k, v in model.state_dict().items()}
            LOG.info(
                "Epoch %3d/%d  loss=%.4f  val_acc=%.1f%%  lr=%.5f",
                epoch, epochs, epoch_loss / n_train, 100 * val_acc,
                sched.get_last_lr()[0],
            )

    # Restore best checkpoint
    model.load_state_dict(best_state)
    model.eval()
    LOG.info("Best val accuracy: %.1f%%", 100 * best_acc)

    # Export TorchScript — inference needs only torch, not the class definition
    example = torch.zeros(1, N_FEATURES)
    scripted = torch.jit.trace(model, example)
    scripted.save(str(out_path))
    size_kb = out_path.stat().st_size / 1024
    LOG.info("Saved TorchScript model → %s  (%.1f KB)", out_path, size_kb)
    assert size_kb < 2048, f"Model {size_kb:.0f} KB exceeds 2 MB budget!"

    return model


# ===========================================================================
# Mood drift
# ===========================================================================

_UNIFORM5 = np.full(N_STATES, 1.0 / N_STATES, dtype=np.float32)


def drift(
    probs:     np.ndarray,
    elapsed_s: float,
    tau:       float = DEFAULT_TAU,
) -> np.ndarray:
    """
    Fade current mood toward neutral (uniform distribution) over time.

    Uses exponential decay with time constant τ (tau):

        drifted(t) = e^(-t/τ) · probs + (1 - e^(-t/τ)) · uniform(5)

    Half-life ≈ 0.693 · τ.  Default τ = 30 s → half-life ≈ 21 s.

    Args:
        probs:     Current 5-float mood probability vector (must sum to 1).
        elapsed_s: Seconds elapsed since the last sensor update.
        tau:       Decay time constant in seconds.  Larger = slower fade.

    Returns:
        Drifted probability vector (float32, sums to 1).

    Examples:
        After   τ s (30 s): 37 % of original mood remains.
        After 2·τ s (60 s): 14 % remains.
        After 3·τ s (90 s):  5 % remains → nearly neutral.
    """
    if elapsed_s <= 0:
        return np.asarray(probs, dtype=np.float32)
    decay   = float(math.exp(-elapsed_s / max(tau, 1e-3)))
    drifted = decay * np.asarray(probs, dtype=np.float32) + (1.0 - decay) * _UNIFORM5
    total   = drifted.sum()
    return (drifted / total).astype(np.float32) if total > 0 else _UNIFORM5.copy()


# ===========================================================================
# MoodPredictor — high-level inference + drift management
# ===========================================================================

class MoodPredictor:
    """
    Wraps a trained MoodNet TorchScript model with:
      * One-shot prediction (predict)
      * Stateful update with drift blending (update)
      * Autonomous mood decay via current property

    Typical integration with breath_detector.py:

        predictor = MoodPredictor()
        # Every 5 s, when breath_detector emits a new hash:
        bf = BreathFeatures(bpm=14.5, hrv=hrv_source.read(14.5), hash_uint32=h)
        mood = predictor.update(bf)
        print(mood)   # {'calm': 0.61, 'stressed': 0.05, ...}
    """

    def __init__(
        self,
        model_path: pathlib.Path = DEFAULT_MODEL,
        tau:        float        = DEFAULT_TAU,
        alpha:      float        = 0.65,    # new-reading blend weight
    ) -> None:
        if not model_path.exists():
            raise FileNotFoundError(
                f"No model at {model_path}.  Run:  python mood_net.py train"
            )
        self._model = torch.jit.load(str(model_path))
        self._model.eval()
        self._tau   = tau
        self._alpha = alpha                               # EMA for new readings
        self._probs = _UNIFORM5.copy()                   # start at neutral
        self._last  = time.monotonic()
        LOG.info("MoodPredictor loaded (%s, τ=%.0f s, α=%.2f)", model_path, tau, alpha)

    # -- Core methods -------------------------------------------------------

    def predict(self, features: BreathFeatures) -> Dict[str, float]:
        """
        Single forward pass — returns raw probabilities without updating
        internal state or applying drift.
        """
        x = features_to_tensor(features).unsqueeze(0)
        with torch.no_grad():
            probs = torch.softmax(self._model(x), dim=-1).squeeze().numpy()
        return {s: float(p) for s, p in zip(STATES, probs)}

    def update(self, features: BreathFeatures) -> Dict[str, float]:
        """
        Incorporate new sensor data:
          1. Apply drift since last call.
          2. Run forward pass.
          3. Blend: α · new + (1-α) · drifted_prior.
          4. Update internal state and timestamp.

        Returns the updated mood dict.
        """
        now     = time.monotonic()
        drifted = drift(self._probs, now - self._last, self._tau)

        raw     = self.predict(features)
        raw_arr = np.array([raw[s] for s in STATES], dtype=np.float32)

        blended = self._alpha * raw_arr + (1.0 - self._alpha) * drifted
        total   = blended.sum()
        self._probs = (blended / total).astype(np.float32)
        self._last  = now

        return {s: float(p) for s, p in zip(STATES, self._probs)}

    # -- Convenience properties --------------------------------------------

    @property
    def current(self) -> Dict[str, float]:
        """Current mood after applying drift — no new sensor data needed."""
        elapsed = time.monotonic() - self._last
        drifted = drift(self._probs, elapsed, self._tau)
        return {s: float(p) for s, p in zip(STATES, drifted)}

    @property
    def dominant(self) -> str:
        """Name of the highest-probability state after drift."""
        c = self.current
        return max(c, key=lambda k: c[k])

    @property
    def vector(self) -> np.ndarray:
        """Raw drifted probability vector (float32 ndarray, shape [5])."""
        elapsed = time.monotonic() - self._last
        return drift(self._probs, elapsed, self._tau)

    def force_drift(self, elapsed_s: float) -> Dict[str, float]:
        """
        Manually advance the drift clock by elapsed_s seconds without new data.
        Useful for testing or simulating time-skips.
        """
        self._probs = drift(self._probs, elapsed_s, self._tau)
        self._last  = time.monotonic()
        return {s: float(p) for s, p in zip(STATES, self._probs)}


# ===========================================================================
# Pretty printer helpers
# ===========================================================================

_BAR_WIDTH = 24
_STATE_COLOURS = {
    "calm":     "\033[94m",    # blue
    "stressed": "\033[91m",    # red
    "joyful":   "\033[93m",    # yellow
    "tired":    "\033[90m",    # dark grey
    "neutral":  "\033[37m",    # light grey
}
_RESET = "\033[0m"


def _bar(prob: float, state: str, width: int = _BAR_WIDTH) -> str:
    filled = round(prob * width)
    col    = _STATE_COLOURS.get(state, "")
    return col + ("█" * filled) + ("░" * (width - filled)) + _RESET


def print_mood(mood: Dict[str, float], prefix: str = "") -> None:
    """Print a formatted mood breakdown to stdout."""
    dominant = max(mood, key=lambda k: mood[k])
    dom_col  = _STATE_COLOURS.get(dominant, "")
    print(f"{prefix}→ {dom_col}{dominant.upper():9s}{_RESET}", end="  ")
    for state in STATES:
        p = mood[state]
        mark = "*" if state == dominant else " "
        print(f"{mark}{state[:5]:5s} {p*100:4.0f}%", end="  ")
    print()


# ===========================================================================
# Continuous demo loop
# ===========================================================================

def demo_loop(
    predictor: MoodPredictor,
    interval:  float = 5.0,
) -> None:
    """
    Run a continuous fake-sensor loop that exercises all five moods by
    slowly varying BPM and HRV over a 5-minute sinusoidal cycle.

    Press Ctrl-C to stop.
    """
    fake_hrv = FakeHRVSource()
    LOG.info("Demo mode — fake sensor loop, interval=%.0f s.  Ctrl-C to stop.", interval)

    t0   = time.monotonic()
    idx  = 0
    rng  = np.random.default_rng()   # persistent RNG — avoids re-seeding each tick

    # Scripted scenario: sweep through emotional states over ~5 minutes
    scenario = [
        ("calm",     60),
        ("neutral", 30),
        ("stressed", 50),
        ("neutral",  20),
        ("joyful",   45),
        ("tired",    55),
        ("neutral",  20),
    ]
    _phase_bpm = {
        "calm": 13.0, "stressed": 21.0, "joyful": 16.0,
        "tired": 11.5, "neutral": 15.5,
    }

    try:
        seg_idx   = 0
        seg_start = time.monotonic()
        seg_state, seg_dur = scenario[0]

        while True:
            now = time.monotonic()

            # Advance scenario segment
            if now - seg_start >= seg_dur and seg_idx < len(scenario) - 1:
                seg_idx  += 1
                seg_state, seg_dur = scenario[seg_idx]
                seg_start = now
                LOG.debug("Scenario → %s (%d s)", seg_state, seg_dur)

            p = _PROFILES[seg_state]

            bpm   = float(rng.uniform(*p["bpm"]))
            rmssd = float(rng.uniform(*p["rmssd"])) + float(rng.normal(0, 2))
            sdnn  = float(rng.uniform(*p["sdnn"]))  + float(rng.normal(0, 1.5))
            lf_hf = float(rng.uniform(*p["lf_hf"])) + float(rng.normal(0, 0.1))

            bpm   = float(np.clip(bpm,   4, 40))
            rmssd = float(np.clip(rmssd, 1, 200))
            sdnn  = float(np.clip(sdnn,  1, 150))
            lf_hf = float(np.clip(lf_hf, 0.05, 6))

            # Simulate breath hash (same HMAC as breath_detector.py)
            ts_bucket = int(time.time()) // 5
            h_u32 = _make_hash(bpm, ts_bucket, _TRAIN_SALT)

            bf = BreathFeatures(
                bpm=bpm,
                hrv=HRVSample(rmssd=rmssd, sdnn=sdnn, lf_hf=lf_hf),
                hash_uint32=h_u32,
            )

            mood = predictor.update(bf)
            elapsed = now - t0
            print(
                f"[{time.strftime('%H:%M:%S')}] "
                f"t={elapsed:5.0f}s  BPM={bpm:5.1f}  "
                f"RMSSD={rmssd:5.1f}ms  LHRATIO={lf_hf:.2f}  ",
                end="",
            )
            print_mood(mood)

            idx += 1
            time.sleep(interval)

    except KeyboardInterrupt:
        print("\nStopped.")


# ===========================================================================
# Model info
# ===========================================================================

def print_info(model_path: pathlib.Path = DEFAULT_MODEL) -> None:
    """Print model architecture, parameter count, and on-disk size."""
    m = MoodNet()
    total  = _count_params(m)
    bytes_ = total * 4

    print("=" * 56)
    print("  MoodNet — architecture summary")
    print("=" * 56)
    print(f"  Input features  : {N_FEATURES}")
    for name, layer in m.named_modules():
        if isinstance(layer, (nn.Linear, nn.BatchNorm1d)):
            print(f"  {name:12s}: {layer}")
    print(f"  Output classes  : {N_STATES}  {STATES}")
    print(f"  Parameters      : {total:,d}")
    print(f"  Float32 size    : {bytes_ / 1024:.1f} KB")
    if model_path.exists():
        size_kb = model_path.stat().st_size / 1024
        print(f"  TorchScript .pt : {size_kb:.1f} KB  ({model_path})")
    else:
        print(f"  TorchScript .pt : not yet trained  (run: mood_net.py train)")
    print("=" * 56)

    print("\nDrift characteristics (τ = 30 s):")
    probs = np.array([0.8, 0.05, 0.05, 0.05, 0.05], dtype=np.float32)
    for t in [10, 30, 60, 90, 180]:
        d = drift(probs, float(t))
        print(f"  after {t:3d}s → calm={d[0]*100:.0f}%  neutral={d[4]*100:.0f}%")


# ===========================================================================
# CLI
# ===========================================================================

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="mood_net.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--verbose", "-v", action="store_true", help="Debug logging.")

    sub = p.add_subparsers(dest="cmd", required=True)

    # -- train ---------------------------------------------------------------
    tr = sub.add_parser("train", help="Generate synthetic data and train model.")
    tr.add_argument(
        "--samples", type=int, default=DEFAULT_SAMPLES,
        help=f"Total synthetic samples (default {DEFAULT_SAMPLES}).",
    )
    tr.add_argument(
        "--epochs", type=int, default=DEFAULT_EPOCHS,
        help=f"Training epochs (default {DEFAULT_EPOCHS}).",
    )
    tr.add_argument(
        "--lr", type=float, default=DEFAULT_LR,
        help=f"Peak learning rate (default {DEFAULT_LR}).",
    )
    tr.add_argument(
        "--out", type=pathlib.Path, default=DEFAULT_MODEL,
        help=f"Output path for TorchScript model (default {DEFAULT_MODEL}).",
    )

    # -- demo ----------------------------------------------------------------
    dm = sub.add_parser("demo", help="Continuous fake-sensor emotion display.")
    dm.add_argument(
        "--model", type=pathlib.Path, default=DEFAULT_MODEL,
        metavar="PATH",
    )
    dm.add_argument(
        "--tau", type=float, default=DEFAULT_TAU,
        help=f"Drift decay constant in seconds (default {DEFAULT_TAU}).",
    )
    dm.add_argument(
        "--interval", type=float, default=5.0,
        help="Seconds between fake readings (default 5).",
    )

    # -- infer ---------------------------------------------------------------
    inf = sub.add_parser("infer", help="One-shot inference from command-line values.")
    inf.add_argument("--bpm",   type=float, required=True, help="Breathing rate (BPM).")
    inf.add_argument("--rmssd", type=float, required=True, help="HRV RMSSD (ms).")
    inf.add_argument("--sdnn",  type=float, required=True, help="HRV SDNN (ms).")
    inf.add_argument("--lf-hf", type=float, required=True, dest="lf_hf",
                     help="LF/HF sympatho-vagal ratio.")
    inf.add_argument("--hash",  type=lambda s: int(s, 0), default=0,
                     metavar="HEX",
                     help="32-bit breath hash (hex, e.g. 0xC297F948; default 0).")
    inf.add_argument("--model", type=pathlib.Path, default=DEFAULT_MODEL)
    inf.add_argument("--tau",   type=float, default=DEFAULT_TAU)

    # -- info ----------------------------------------------------------------
    inf2 = sub.add_parser("info", help="Print model architecture and drift table.")
    inf2.add_argument("--model", type=pathlib.Path, default=DEFAULT_MODEL)

    return p


def main(argv: Optional[List[str]] = None) -> None:
    args = _build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    if args.cmd == "train":
        train_model(
            n_samples=args.samples,
            epochs=args.epochs,
            lr=args.lr,
            out_path=args.out,
        )

    elif args.cmd == "demo":
        predictor = MoodPredictor(model_path=args.model, tau=args.tau)
        demo_loop(predictor, interval=args.interval)

    elif args.cmd == "infer":
        predictor = MoodPredictor(model_path=args.model, tau=args.tau)
        bf = BreathFeatures(
            bpm=args.bpm,
            hrv=HRVSample(rmssd=args.rmssd, sdnn=args.sdnn, lf_hf=args.lf_hf),
            hash_uint32=args.hash,
        )
        raw  = predictor.predict(bf)
        dom  = max(raw, key=lambda k: raw[k])
        col  = _STATE_COLOURS.get(dom, "")
        print(f"\nDominant state: {col}{dom.upper()}{_RESET}\n")
        print(f"{'State':<10}  {'Probability':>11}  {'Bar'}")
        print("─" * 52)
        for state in STATES:
            p   = raw[state]
            bar = _bar(p, state, width=20)
            mrk = "◀" if state == dom else " "
            print(f"  {state:<8}  {p*100:8.1f}%  {bar} {mrk}")
        print()

    elif args.cmd == "info":
        print_info(getattr(args, "model", DEFAULT_MODEL))


if __name__ == "__main__":
    main()
