"""Stem — broad separated audio component. Spec §11.2 `stems`."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from deep_sound.domain.confidence import Confidence


class StemType(StrEnum):
    VOCALS = "vocals"
    DRUMS = "drums"
    BASS = "bass"
    OTHER = "other"
    FULL_MIX = "full_mix"


@dataclass(frozen=True, slots=True)
class Stem:
    """Broad source group (vocals/drums/bass/other) separated from a track.

    Stub for Phase 0; full separation lands in Phase 2 with Demucs.
    """

    id: str
    track_id: str
    stem_type: StemType
    confidence: Confidence
    artifact_path: Path | None = None
    model_name: str | None = None
    model_version: str | None = None
