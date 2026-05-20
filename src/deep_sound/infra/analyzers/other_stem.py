"""Accompaniment/other-stem harmony and timbre summaries."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from deep_sound.domain.confidence import Confidence
from deep_sound.infra.analyzers.chroma_librosa import summarize_chroma
from deep_sound.infra.analyzers.mfcc_librosa import summarize_mfcc
from deep_sound.infra.analyzers.tempo_librosa import DEFAULT_SAMPLE_RATE


@dataclass(frozen=True, slots=True)
class OtherStemSummary:
    chroma: list[float]
    mfcc: list[float]
    confidence: Confidence
    analyzer: str = "librosa-other-stem-summary"
    analyzer_version: str = "1"


def summarize_other_stem(path: Path, sample_rate: int = DEFAULT_SAMPLE_RATE) -> OtherStemSummary:
    chroma = summarize_chroma(path, sample_rate=sample_rate)
    mfcc = summarize_mfcc(path, sample_rate=sample_rate)
    confidence = Confidence(
        min(chroma.confidence.value, mfcc.confidence.value)
        if chroma.confidence is not None and mfcc.confidence is not None
        else 0.0
    )
    return OtherStemSummary(
        chroma=chroma.chroma,
        mfcc=mfcc.mfcc,
        confidence=confidence,
    )
