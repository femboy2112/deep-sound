"""Conservative bass-stem root-motion proxy features."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import librosa
import numpy as np

from deep_sound.domain.confidence import Confidence
from deep_sound.infra.analyzers.tempo_librosa import DEFAULT_SAMPLE_RATE


@dataclass(frozen=True, slots=True)
class BassStemSummary:
    low_energy_ratio: float
    pitch_motion: float
    root_stability: float
    confidence: Confidence
    analyzer: str = "librosa-bass-root-motion-proxy"
    analyzer_version: str = "1"


def summarize_bass_stem(path: Path, sample_rate: int = DEFAULT_SAMPLE_RATE) -> BassStemSummary:
    y, sr = librosa.load(path, sr=sample_rate, mono=True)
    if y.size == 0 or float(np.max(np.abs(y))) == 0.0:
        return BassStemSummary(0.0, 0.0, 0.0, Confidence(0.0))

    spectrum = np.abs(librosa.stft(y))
    freqs = librosa.fft_frequencies(sr=sr)
    low_mask = freqs <= 250.0
    low_energy = float(np.sum(spectrum[low_mask]))
    total_energy = float(np.sum(spectrum))
    low_energy_ratio = 0.0 if total_energy == 0.0 else low_energy / total_energy

    contour = _dominant_low_frequency_contour(spectrum, freqs)
    pitch_motion = _normalized_motion(contour)
    root_stability = _stability(contour)
    confidence = Confidence(min(1.0, low_energy_ratio * 1.25 if contour else 0.0))
    return BassStemSummary(
        low_energy_ratio=low_energy_ratio,
        pitch_motion=pitch_motion,
        root_stability=root_stability,
        confidence=confidence,
    )


def _dominant_low_frequency_contour(spectrum: np.ndarray, freqs: np.ndarray) -> list[float]:
    contour: list[float] = []
    low_indexes = np.where((freqs >= 40.0) & (freqs <= 400.0))[0]
    if low_indexes.size == 0:
        return contour
    low_spectrum = spectrum[low_indexes, :]
    for frame in range(low_spectrum.shape[1]):
        column = low_spectrum[:, frame]
        index = int(np.argmax(column))
        if float(column[index]) > 0.0:
            contour.append(float(freqs[int(low_indexes[index])]))
    return contour


def _normalized_motion(contour: list[float]) -> float:
    if len(contour) < 2:
        return 0.0
    diffs = np.abs(np.diff(np.asarray(contour, dtype=np.float64)))
    mean_diff = float(np.mean(diffs))
    return min(1.0, mean_diff / 200.0)


def _stability(contour: list[float]) -> float:
    if len(contour) < 2:
        return 0.0
    mean_pitch = float(np.mean(contour))
    if mean_pitch <= 0.0:
        return 0.0
    return max(0.0, min(1.0, 1.0 - float(np.std(contour) / mean_pitch)))
