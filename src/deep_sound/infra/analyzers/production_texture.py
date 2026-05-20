"""Lightweight production texture proxies for Phase 5."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf

from deep_sound.domain.confidence import Confidence
from deep_sound.infra.analyzers.tempo_librosa import DEFAULT_SAMPLE_RATE

ANALYZER_NAME = "production_texture_librosa_proxy"
ANALYZER_VERSION = "0.1.0"


@dataclass(frozen=True, slots=True)
class ProductionTextureSummary:
    stats: dict[str, float]
    confidence: Confidence
    duration_sec: float
    sample_rate: int
    analyzer: str = ANALYZER_NAME
    analyzer_version: str = ANALYZER_VERSION


def summarize_production_texture(
    path: Path | str,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
) -> ProductionTextureSummary:
    """Estimate production texture with deterministic signal descriptors."""
    y, sr = librosa.load(str(path), sr=sample_rate, mono=True)
    duration = float(librosa.get_duration(y=y, sr=sr))
    if y.size == 0 or float(np.max(np.abs(y))) == 0.0:
        return ProductionTextureSummary(
            stats=_zero_stats(),
            confidence=Confidence(0.0),
            duration_sec=duration,
            sample_rate=int(sr),
        )

    rms = np.asarray(librosa.feature.rms(y=y), dtype=np.float64).reshape(-1)
    centroid = np.asarray(librosa.feature.spectral_centroid(y=y, sr=sr), dtype=np.float64)
    bandwidth = np.asarray(librosa.feature.spectral_bandwidth(y=y, sr=sr), dtype=np.float64)
    flatness = np.asarray(librosa.feature.spectral_flatness(y=y), dtype=np.float64)
    rolloff = np.asarray(librosa.feature.spectral_rolloff(y=y, sr=sr), dtype=np.float64)
    onset_env = np.asarray(librosa.onset.onset_strength(y=y, sr=sr), dtype=np.float64)

    stats = {
        "rms_mean": _bounded(float(np.mean(rms)) * 10.0),
        "loudness_profile": _bounded(_safe_cv(rms)),
        "dynamic_range": _bounded(_percentile_range(rms) * 20.0),
        "spectral_balance": _bounded(float(np.mean(bandwidth)) / max(sr / 2.0, 1.0)),
        "brightness": _bounded(float(np.mean(centroid)) / max(sr / 2.0, 1.0)),
        "low_end_weight": _bounded(_low_end_weight(y, int(sr))),
        "flatness": _bounded(float(np.mean(flatness))),
        "rolloff": _bounded(float(np.mean(rolloff)) / max(sr / 2.0, 1.0)),
        "transient_density": _bounded(_transient_density(onset_env, duration)),
        "stereo_width": _bounded(_stereo_width(path)),
    }
    confidence = Confidence(min(1.0, max(float(np.mean(rms)) * 25.0, duration / 10.0)))
    return ProductionTextureSummary(
        stats=stats,
        confidence=confidence,
        duration_sec=duration,
        sample_rate=int(sr),
    )


def _zero_stats() -> dict[str, float]:
    return {
        "rms_mean": 0.0,
        "loudness_profile": 0.0,
        "dynamic_range": 0.0,
        "spectral_balance": 0.0,
        "brightness": 0.0,
        "low_end_weight": 0.0,
        "flatness": 0.0,
        "rolloff": 0.0,
        "transient_density": 0.0,
        "stereo_width": 0.0,
    }


def _bounded(value: float) -> float:
    if not np.isfinite(value):
        return 0.0
    return max(0.0, min(1.0, float(value)))


def _safe_cv(values: np.ndarray) -> float:
    mean = float(np.mean(values)) if values.size else 0.0
    if mean <= 0.0:
        return 0.0
    return float(np.std(values) / mean)


def _percentile_range(values: np.ndarray) -> float:
    if values.size == 0:
        return 0.0
    return float(np.percentile(values, 95) - np.percentile(values, 5))


def _low_end_weight(y: np.ndarray, sample_rate: int) -> float:
    spectrum = np.abs(np.fft.rfft(y))
    if spectrum.size == 0:
        return 0.0
    freqs = np.fft.rfftfreq(y.size, d=1.0 / sample_rate)
    total = float(np.sum(spectrum))
    if total <= 0.0:
        return 0.0
    low = float(np.sum(spectrum[freqs <= 250.0]))
    return low / total


def _transient_density(onset_env: np.ndarray, duration_sec: float) -> float:
    if onset_env.size < 3 or duration_sec <= 0.0:
        return 0.0
    threshold = float(np.mean(onset_env) + np.std(onset_env))
    peaks = int(np.sum(onset_env > threshold))
    return peaks / max(duration_sec * 8.0, 1.0)


def _stereo_width(path: Path | str) -> float:
    try:
        data, _sr = sf.read(str(path), always_2d=True)
    except (RuntimeError, OSError):
        return 0.0
    if data.shape[1] < 2:
        return 0.0
    left = np.asarray(data[:, 0], dtype=np.float64)
    right = np.asarray(data[:, 1], dtype=np.float64)
    if float(np.max(np.abs(left))) == 0.0 and float(np.max(np.abs(right))) == 0.0:
        return 0.0
    side = left - right
    mid = left + right
    return float(np.sqrt(np.mean(side * side)) / max(np.sqrt(np.mean(mid * mid)), 1e-9))
