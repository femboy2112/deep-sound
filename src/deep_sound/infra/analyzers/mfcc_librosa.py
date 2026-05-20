"""MFCC timbre analyzer using librosa. Phase 0 deliverable. Spec §13.7."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import librosa
import numpy as np
import numpy.typing as npt

from deep_sound.domain.confidence import Confidence

DEFAULT_SAMPLE_RATE = 22050
DEFAULT_N_MFCC = 13
ANALYZER_NAME = "mfcc_librosa"
ANALYZER_VERSION = "0.1.0"


@dataclass(frozen=True, slots=True)
class MfccSummary:
    mfcc: list[float]
    confidence: Confidence
    duration_sec: float
    sample_rate: int
    n_mfcc: int = DEFAULT_N_MFCC
    analyzer: str = ANALYZER_NAME
    analyzer_version: str = ANALYZER_VERSION


def _zero_summary(duration: float, sample_rate: int, n_mfcc: int) -> MfccSummary:
    return MfccSummary(
        mfcc=[0.0] * (n_mfcc * 2),
        confidence=Confidence(0.0),
        duration_sec=duration,
        sample_rate=sample_rate,
        n_mfcc=n_mfcc,
    )


def _summary_vector(mfcc_matrix: npt.NDArray[np.float64]) -> list[float]:
    means = np.mean(mfcc_matrix, axis=1)
    stds = np.std(mfcc_matrix, axis=1)
    return [float(value) for value in np.concatenate([means, stds])]


def summarize_mfcc(
    path: Path | str,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    n_mfcc: int = DEFAULT_N_MFCC,
) -> MfccSummary:
    """Compute a compact full-track MFCC mean/std timbre summary."""
    y, sr = librosa.load(str(path), sr=sample_rate, mono=True)
    duration = float(librosa.get_duration(y=y, sr=sr))
    if y.size == 0 or not np.any(y):
        return _zero_summary(duration, int(sr), n_mfcc)

    mfcc_matrix = np.asarray(librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc), dtype=np.float64)
    mfcc = _summary_vector(mfcc_matrix)

    rms = np.asarray(librosa.feature.rms(y=y), dtype=np.float64)
    mean_rms = float(np.mean(rms)) if rms.size else 0.0
    confidence = Confidence(min(1.0, mean_rms * 20.0))

    return MfccSummary(
        mfcc=mfcc,
        confidence=confidence,
        duration_sec=duration,
        sample_rate=int(sr),
        n_mfcc=n_mfcc,
    )
