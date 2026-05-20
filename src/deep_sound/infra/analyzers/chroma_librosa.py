"""Chroma analyzer using librosa. Phase 0 deliverable. Spec §13.4."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import librosa
import numpy as np
import numpy.typing as npt

from deep_sound.domain.confidence import Confidence

DEFAULT_SAMPLE_RATE = 22050
ANALYZER_NAME = "chroma_librosa"
ANALYZER_VERSION = "0.1.0"


@dataclass(frozen=True, slots=True)
class ChromaSummary:
    chroma: list[float]
    confidence: Confidence
    duration_sec: float
    sample_rate: int
    analyzer: str = ANALYZER_NAME
    analyzer_version: str = ANALYZER_VERSION


def _normalize_distribution(values: npt.NDArray[np.float64]) -> list[float]:
    clipped = np.maximum(values, 0.0)
    total = float(np.sum(clipped))
    if total <= 0.0:
        return [0.0] * 12
    return [float(v) for v in clipped / total]


def summarize_chroma(path: Path | str, sample_rate: int = DEFAULT_SAMPLE_RATE) -> ChromaSummary:
    """Compute a track-level 12-bin chroma distribution for an audio file.

    Phase 0 stores a compact full-track summary rather than beat-synchronous or
    chord-level harmony. The confidence is a simple energy-presence heuristic:
    silent or near-silent inputs stay low while tonal material rises toward 1.
    """
    y, sr = librosa.load(str(path), sr=sample_rate, mono=True)
    duration = float(librosa.get_duration(y=y, sr=sr))

    if y.size == 0:
        return ChromaSummary(
            chroma=[0.0] * 12,
            confidence=Confidence(0.0),
            duration_sec=duration,
            sample_rate=int(sr),
        )

    chroma_matrix = librosa.feature.chroma_stft(y=y, sr=sr, tuning=0.0)
    chroma_mean = np.asarray(np.mean(chroma_matrix, axis=1), dtype=np.float64)
    chroma = _normalize_distribution(chroma_mean)

    rms = np.asarray(librosa.feature.rms(y=y), dtype=np.float64)
    mean_rms = float(np.mean(rms)) if rms.size else 0.0
    confidence = Confidence(min(1.0, mean_rms * 20.0))

    return ChromaSummary(
        chroma=chroma,
        confidence=confidence,
        duration_sec=duration,
        sample_rate=int(sr),
    )
