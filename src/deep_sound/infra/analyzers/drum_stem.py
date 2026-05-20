"""Conservative drum-stem rhythm and timbre proxies."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import librosa
import numpy as np

from deep_sound.domain.confidence import Confidence
from deep_sound.infra.analyzers.tempo_librosa import DEFAULT_SAMPLE_RATE


@dataclass(frozen=True, slots=True)
class DrumStemSummary:
    onset_density: float
    groove_regularity: float
    spectral_centroid: float
    confidence: Confidence
    analyzer: str = "librosa-drum-stem-proxy"
    analyzer_version: str = "1"


def summarize_drum_stem(path: Path, sample_rate: int = DEFAULT_SAMPLE_RATE) -> DrumStemSummary:
    y, sr = librosa.load(path, sr=sample_rate, mono=True)
    if y.size == 0 or float(np.max(np.abs(y))) == 0.0:
        return DrumStemSummary(0.0, 0.0, 0.0, Confidence(0.0))

    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    duration = max(float(librosa.get_duration(y=y, sr=sr)), 1e-6)
    onset_frames = _peak_frames(onset_env)
    onset_density = float(len(onset_frames) / duration)
    groove_regularity = _regularity(onset_frames)
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
    spectral_centroid = float(np.mean(centroid) / max(sr / 2.0, 1.0))
    confidence = Confidence(min(1.0, len(onset_frames) / max(duration * 2.0, 1.0)))
    return DrumStemSummary(
        onset_density=onset_density,
        groove_regularity=groove_regularity,
        spectral_centroid=spectral_centroid,
        confidence=confidence,
    )


def _peak_frames(onset_env: np.ndarray) -> np.ndarray:
    if onset_env.size < 3:
        return np.asarray([], dtype=np.int64)
    threshold = float(np.mean(onset_env) + np.std(onset_env))
    peaks: list[int] = []
    for index in range(1, onset_env.size - 1):
        if (
            float(onset_env[index]) > threshold
            and float(onset_env[index]) >= float(onset_env[index - 1])
            and float(onset_env[index]) >= float(onset_env[index + 1])
        ):
            peaks.append(index)
    return np.asarray(peaks, dtype=np.int64)


def _regularity(onset_frames: np.ndarray) -> float:
    if len(onset_frames) < 3:
        return 0.0
    intervals = np.diff(onset_frames).astype(np.float64)
    mean_interval = float(np.mean(intervals))
    if mean_interval <= 0.0:
        return 0.0
    coefficient = float(np.std(intervals) / mean_interval)
    return max(0.0, min(1.0, 1.0 - coefficient))
