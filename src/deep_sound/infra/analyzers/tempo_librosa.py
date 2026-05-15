"""Tempo / beat analyzer using librosa. Phase 0 deliverable. Spec §13.2."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import librosa
import numpy as np

from deep_sound.domain.confidence import Confidence

DEFAULT_SAMPLE_RATE = 22050
ANALYZER_NAME = "tempo_librosa"
ANALYZER_VERSION = "0.1.0"


@dataclass(frozen=True, slots=True)
class TempoEstimate:
    tempo_bpm: float
    confidence: Confidence
    beats_sec: list[float]
    duration_sec: float
    sample_rate: int
    analyzer: str = ANALYZER_NAME
    analyzer_version: str = ANALYZER_VERSION


def estimate_tempo(path: Path | str, sample_rate: int = DEFAULT_SAMPLE_RATE) -> TempoEstimate:
    """Estimate tempo and beat positions for an audio file.

    The confidence is a placeholder heuristic (see docs/build/DECISIONS.md):
    rewards tracks where the beat tracker found roughly ≥ 0.5 beats per
    second. Replaceable with a real salience metric later.

    Args:
        path: Audio file path. Any format librosa+soundfile/audioread can read.
        sample_rate: Resample target for analysis (does not modify the file).

    Returns:
        TempoEstimate with `tempo_bpm`, `confidence`, beat positions in seconds.
    """
    y, sr = librosa.load(str(path), sr=sample_rate, mono=True)
    duration = float(librosa.get_duration(y=y, sr=sr))

    tempo_value, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    # librosa>=0.10 returns tempo as a 1-d ndarray; extract a scalar safely.
    tempo_bpm = float(np.atleast_1d(np.asarray(tempo_value)).ravel()[0])
    beats_sec_arr = librosa.frames_to_time(beat_frames, sr=sr)
    beats_sec = [float(t) for t in beats_sec_arr]

    raw_conf = min(1.0, len(beats_sec) / max(1.0, duration * 0.5))
    confidence = Confidence(raw_conf)

    return TempoEstimate(
        tempo_bpm=tempo_bpm,
        confidence=confidence,
        beats_sec=beats_sec,
        duration_sec=duration,
        sample_rate=int(sr),
    )
