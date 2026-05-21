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
    pitch_variety: float
    median_register: float
    confidence: Confidence
    analyzer: str = "librosa-bass-root-motion-proxy"
    analyzer_version: str = "2"


def summarize_bass_stem(path: Path, sample_rate: int = DEFAULT_SAMPLE_RATE) -> BassStemSummary:
    y, sr = librosa.load(path, sr=sample_rate, mono=True)
    if y.size == 0 or float(np.max(np.abs(y))) == 0.0:
        return BassStemSummary(0.0, 0.0, 0.0, 0.0, 0.0, Confidence(0.0))

    spectrum = np.abs(librosa.stft(y))
    freqs = librosa.fft_frequencies(sr=sr)
    low_mask = freqs <= 250.0
    low_energy = float(np.sum(spectrum[low_mask]))
    total_energy = float(np.sum(spectrum))
    low_energy_ratio = 0.0 if total_energy == 0.0 else low_energy / total_energy

    contour = _dominant_low_frequency_contour(spectrum, freqs)
    pitch_motion = _normalized_motion(contour)
    root_stability = _stability(contour)
    pitch_variety = _pitch_variety(contour)
    median_register = _median_register(contour)
    voiced_ratio = len(contour) / max(spectrum.shape[1], 1)
    confidence = Confidence(
        min(1.0, low_energy_ratio * 0.85 + voiced_ratio * 0.15 if contour else 0.0)
    )
    return BassStemSummary(
        low_energy_ratio=low_energy_ratio,
        pitch_motion=pitch_motion,
        root_stability=root_stability,
        pitch_variety=pitch_variety,
        median_register=median_register,
        confidence=confidence,
    )


def _dominant_low_frequency_contour(spectrum: np.ndarray, freqs: np.ndarray) -> list[float]:
    contour: list[float] = []
    low_indexes = np.where((freqs >= 40.0) & (freqs <= 400.0))[0]
    if low_indexes.size == 0:
        return contour
    low_spectrum = spectrum[low_indexes, :]
    frame_energy = np.sum(low_spectrum, axis=0)
    max_energy = float(np.max(frame_energy)) if frame_energy.size else 0.0
    if max_energy <= 0.0:
        return contour
    threshold = max_energy * 0.08
    for frame in range(low_spectrum.shape[1]):
        if float(frame_energy[frame]) < threshold:
            continue
        column = low_spectrum[:, frame]
        index = int(np.argmax(column))
        if float(column[index]) > 0.0:
            contour.append(float(freqs[int(low_indexes[index])]))
    return contour


def _normalized_motion(contour: list[float]) -> float:
    if len(contour) < 2:
        return 0.0
    midi = librosa.hz_to_midi(np.asarray(contour, dtype=np.float64))
    diffs = np.abs(np.diff(midi))
    mean_diff = float(np.mean(diffs))
    return min(1.0, mean_diff / 12.0)


def _stability(contour: list[float]) -> float:
    if len(contour) < 2:
        return 0.0
    mean_pitch = float(np.mean(contour))
    if mean_pitch <= 0.0:
        return 0.0
    return max(0.0, min(1.0, 1.0 - float(np.std(contour) / mean_pitch)))


def _pitch_variety(contour: list[float]) -> float:
    if not contour:
        return 0.0
    midi = np.round(librosa.hz_to_midi(np.asarray(contour, dtype=np.float64))).astype(int)
    return max(0.0, min(1.0, len(set(int(value) for value in midi)) / 12.0))


def _median_register(contour: list[float]) -> float:
    if not contour:
        return 0.0
    midi = librosa.hz_to_midi(np.asarray(contour, dtype=np.float64))
    return max(0.0, min(1.0, float(np.median(midi) - 24.0) / 36.0))
