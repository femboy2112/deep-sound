"""FeatureView — one numeric/symbolic representation of audio. Spec §13.1."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from deep_sound.domain.confidence import Confidence


class OwnerType(StrEnum):
    TRACK = "track"
    SECTION = "section"
    STEM = "stem"
    SOURCE = "source"
    CLIP = "clip"


class FeatureType(StrEnum):
    """Spec section 13.1 feature view categories."""

    RHYTHM_GLOBAL = "rhythm.global"
    RHYTHM_DRUM = "rhythm.drum"
    HARMONY_CHROMA = "harmony.chroma"
    HARMONY_CHORD_SEQUENCE = "harmony.chord_sequence"
    HARMONY_CHORD_CHANGE = "harmony.chord_change"
    BASS_ROOT_MOTION = "bass.root_motion"
    MELODY_CONTOUR = "melody.contour"
    TIMBRE_MFCC_STATS = "timbre.mfcc_stats"
    TIMBRE_EMBEDDING = "timbre.embedding"
    PRODUCTION_TEXTURE = "production.texture"
    STRUCTURE_SECTION_SEQUENCE = "structure.section_sequence"
    EMBEDDING_GLOBAL = "embedding.global"


@dataclass(frozen=True, slots=True)
class FeatureView:
    """One feature representation tied to an owner entity.

    Spec §17.2: every artifact records algorithm, version, parameters hash,
    and (when applicable) confidence — for stale-feature detection.
    """

    id: str
    owner_type: OwnerType
    owner_id: str
    feature_type: FeatureType
    algorithm: str
    algorithm_version: str
    params_hash: str
    vector_path: Path | None = None
    symbolic_json: str | None = None
    stats: dict[str, float] = field(default_factory=dict)
    confidence: Confidence | None = None
