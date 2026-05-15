"""Source — specific sound-producing component within a stem. Spec §11.2."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from deep_sound.domain.confidence import Confidence


class SourceType(StrEnum):
    """Spec section 12.6: routes which analyzers are allowed for this source."""

    DRUM = "drum_source"
    BASS = "bass_source"
    PITCHED_HARMONIC = "pitched_harmonic_source"
    MELODIC = "melodic_source"
    TEXTURE = "texture_source"
    EFFECT = "effect_source"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class Source:
    """A detected source within a stem (e.g. "likely electric guitar").

    Spec §3.3: every source label is probabilistic. The `confidence` field
    is mandatory.
    """

    id: str
    track_id: str
    parent_stem_id: str
    source_type: SourceType
    source_label: str  # e.g. "likely electric guitar"
    confidence: Confidence
    user_label: str | None = None
    is_user_corrected: bool = False
