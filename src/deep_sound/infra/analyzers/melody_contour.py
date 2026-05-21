"""Conservative melody contour proxies for routed melodic sources."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import librosa
import numpy as np

from deep_sound.domain.confidence import Confidence
from deep_sound.infra.analyzers.tempo_librosa import DEFAULT_SAMPLE_RATE

ANALYZER_NAME = "melody_contour_librosa_proxy"
ANALYZER_VERSION = "0.2.0"


@dataclass(frozen=True, slots=True)
class MelodyContourSummary:
    contour: dict[str, float]
    confidence: Confidence
    duration_sec: float
    sample_rate: int
    analyzer: str = ANALYZER_NAME
    analyzer_version: str = ANALYZER_VERSION


def summarize_melody_contour(
    path: Path | str,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
) -> MelodyContourSummary:
    """Summarize pitch movement without emitting definitive note labels."""
    y, sr = librosa.load(str(path), sr=sample_rate, mono=True)
    duration = float(librosa.get_duration(y=y, sr=sr))
    if y.size == 0 or float(np.max(np.abs(y))) == 0.0:
        return MelodyContourSummary(_zero_contour(), Confidence(0.0), duration, int(sr))

    spectrum = np.abs(librosa.stft(y=y))
    freqs = librosa.fft_frequencies(sr=sr)
    contour_hz, voiced_frames, total_frames = _dominant_pitch_contour(spectrum, freqs)
    if len(contour_hz) < 3:
        return MelodyContourSummary(_zero_contour(), Confidence(0.2), duration, int(sr))

    midi = _median_smooth(librosa.hz_to_midi(np.asarray(contour_hz, dtype=np.float64)))
    diffs = np.diff(midi)
    activity = _bounded(voiced_frames / max(total_frames, 1))
    smoothness = _bounded(1.0 - float(np.mean(np.abs(diffs))) / 12.0)
    contour = {
        "range_semitones": _bounded(float(np.percentile(midi, 95) - np.percentile(midi, 5)) / 36.0),
        "mean_step": _bounded(float(np.mean(np.abs(diffs))) / 12.0),
        "upward_motion": _bounded(float(np.mean(diffs > 0.25))),
        "downward_motion": _bounded(float(np.mean(diffs < -0.25))),
        "stability": _bounded(1.0 - float(np.std(diffs)) / 12.0),
        "activity": activity,
        "voicing_confidence": activity,
        "contour_smoothness": smoothness,
        "median_pitch": _bounded(float(np.median(midi) - 36.0) / 60.0),
    }
    confidence = Confidence(min(0.95, max(0.15, 0.65 * activity + 0.35 * smoothness)))
    return MelodyContourSummary(contour, confidence, duration, int(sr))


def _zero_contour() -> dict[str, float]:
    return {
        "range_semitones": 0.0,
        "mean_step": 0.0,
        "upward_motion": 0.0,
        "downward_motion": 0.0,
        "stability": 0.0,
        "activity": 0.0,
        "voicing_confidence": 0.0,
        "contour_smoothness": 0.0,
        "median_pitch": 0.0,
    }


def _dominant_pitch_contour(
    spectrum: np.ndarray,
    freqs: np.ndarray,
    *,
    min_hz: float = 80.0,
    max_hz: float = 2000.0,
) -> tuple[list[float], int, int]:
    band_indexes = np.where((freqs >= min_hz) & (freqs <= max_hz))[0]
    if band_indexes.size == 0 or spectrum.shape[1] == 0:
        return [], 0, int(spectrum.shape[1])

    band = spectrum[band_indexes, :]
    frame_energy = np.sum(band, axis=0)
    max_energy = float(np.max(frame_energy)) if frame_energy.size else 0.0
    if max_energy <= 0.0:
        return [], 0, int(spectrum.shape[1])
    threshold = max_energy * 0.08

    contour: list[float] = []
    voiced_frames = 0
    for frame in range(band.shape[1]):
        if float(frame_energy[frame]) < threshold:
            continue
        column = band[:, frame]
        peak_index = int(np.argmax(column))
        peak_energy = float(column[peak_index])
        if peak_energy <= 0.0:
            continue
        contour.append(float(freqs[int(band_indexes[peak_index])]))
        voiced_frames += 1
    return contour, voiced_frames, int(spectrum.shape[1])


def _median_smooth(values: np.ndarray) -> np.ndarray:
    if values.size < 5:
        return values
    smoothed = values.copy()
    for index in range(2, values.size - 2):
        smoothed[index] = float(np.median(values[index - 2 : index + 3]))
    return smoothed


def _bounded(value: float) -> float:
    if not np.isfinite(value):
        return 0.0
    return max(0.0, min(1.0, float(value)))
