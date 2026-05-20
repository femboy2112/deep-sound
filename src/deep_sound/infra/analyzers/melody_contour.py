"""Conservative melody contour proxies for routed melodic sources."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import librosa
import numpy as np

from deep_sound.domain.confidence import Confidence
from deep_sound.infra.analyzers.tempo_librosa import DEFAULT_SAMPLE_RATE

ANALYZER_NAME = "melody_contour_librosa_proxy"
ANALYZER_VERSION = "0.1.0"


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
    contour_hz: list[float] = []
    for frame in range(spectrum.shape[1]):
        column = spectrum[:, frame]
        if float(np.max(column)) <= 0.0:
            continue
        index = int(np.argmax(column))
        hz = float(freqs[index])
        if hz > 0.0:
            contour_hz.append(hz)
    if len(contour_hz) < 3:
        return MelodyContourSummary(_zero_contour(), Confidence(0.2), duration, int(sr))

    midi = librosa.hz_to_midi(np.asarray(contour_hz, dtype=np.float64))
    diffs = np.diff(midi)
    contour = {
        "range_semitones": _bounded(float(np.percentile(midi, 95) - np.percentile(midi, 5)) / 36.0),
        "mean_step": _bounded(float(np.mean(np.abs(diffs))) / 12.0),
        "upward_motion": _bounded(float(np.mean(diffs > 0.25))),
        "downward_motion": _bounded(float(np.mean(diffs < -0.25))),
        "stability": _bounded(1.0 - float(np.std(diffs)) / 12.0),
        "activity": _bounded(len(contour_hz) / max(spectrum.shape[1], 1)),
    }
    confidence = Confidence(min(0.95, max(0.25, contour["activity"])))
    return MelodyContourSummary(contour, confidence, duration, int(sr))


def _zero_contour() -> dict[str, float]:
    return {
        "range_semitones": 0.0,
        "mean_step": 0.0,
        "upward_motion": 0.0,
        "downward_motion": 0.0,
        "stability": 0.0,
        "activity": 0.0,
    }


def _bounded(value: float) -> float:
    if not np.isfinite(value):
        return 0.0
    return max(0.0, min(1.0, float(value)))
