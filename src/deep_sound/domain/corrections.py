"""Typed correction payloads and validation helpers for Phase 4."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from deep_sound.domain.harmony import ChordEvent
from deep_sound.domain.source import SourceType


class CorrectionEntityType(StrEnum):
    SOURCE = "source"
    CHORD_EVENT = "chord_event"
    RESULT_FEEDBACK = "result_feedback"


class ResultFeedbackValue(StrEnum):
    RELEVANT = "relevant"
    IRRELEVANT = "irrelevant"


@dataclass(frozen=True, slots=True)
class SourceCorrectionPayload:
    label: str | None = None
    source_type: SourceType | None = None

    def __post_init__(self) -> None:
        if self.label is None and self.source_type is None:
            raise ValueError("source correction requires a label or source_type")
        if self.label is not None and not self.label.strip():
            raise ValueError("source correction label must not be blank")


@dataclass(frozen=True, slots=True)
class ChordCorrectionPayload:
    chord_label: str

    def __post_init__(self) -> None:
        if not self.chord_label.strip():
            raise ValueError("chord correction label must not be blank")


@dataclass(frozen=True, slots=True)
class ResultFeedbackPayload:
    result_owner_id: str
    feedback: ResultFeedbackValue

    def __post_init__(self) -> None:
        if not self.result_owner_id.strip():
            raise ValueError("result feedback requires a result_owner_id")


@dataclass(frozen=True, slots=True)
class EffectiveSourceLabel:
    label: str
    source_type: SourceType
    confidence: float
    is_user_corrected: bool
    correction_id: str | None = None


@dataclass(frozen=True, slots=True)
class EffectiveChordLabel:
    chord_label: str
    confidence: float
    is_user_corrected: bool
    correction_id: str | None = None


@dataclass(frozen=True, slots=True)
class EffectiveChordEvent:
    event: ChordEvent
    effective_label: EffectiveChordLabel


def bounded_feedback_adjustment(relevant_count: int, irrelevant_count: int) -> float:
    """Return a deterministic Phase 4 reranking delta in [-0.10, 0.10]."""
    raw = (0.05 * relevant_count) - (0.05 * irrelevant_count)
    return max(-0.10, min(0.10, raw))


def clamp_score(score: float) -> float:
    return max(0.0, min(1.0, float(score)))
