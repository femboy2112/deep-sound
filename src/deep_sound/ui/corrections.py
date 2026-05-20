"""Import-safe correction UI DTO helpers."""

from __future__ import annotations

from dataclasses import dataclass

from deep_sound.domain.corrections import ResultFeedbackValue
from deep_sound.domain.source import SourceType


@dataclass(frozen=True, slots=True)
class SourceCorrectionControlData:
    source_id: str
    current_label: str
    current_source_type: str
    confidence: float
    is_user_corrected: bool
    allowed_source_types: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ChordCorrectionControlData:
    chord_event_id: str
    current_label: str
    confidence: float
    is_user_corrected: bool


@dataclass(frozen=True, slots=True)
class ResultFeedbackControlData:
    query_owner_id: str
    result_owner_id: str
    current_score: float
    relevant_value: str = ResultFeedbackValue.RELEVANT.value
    irrelevant_value: str = ResultFeedbackValue.IRRELEVANT.value


def source_correction_control(
    *,
    source_id: str,
    current_label: str,
    current_source_type: SourceType,
    confidence: float,
    is_user_corrected: bool = False,
) -> SourceCorrectionControlData:
    return SourceCorrectionControlData(
        source_id=source_id,
        current_label=current_label,
        current_source_type=current_source_type.value,
        confidence=confidence,
        is_user_corrected=is_user_corrected,
        allowed_source_types=tuple(source_type.value for source_type in SourceType),
    )


def chord_correction_control(
    *,
    chord_event_id: str,
    current_label: str,
    confidence: float,
    is_user_corrected: bool = False,
) -> ChordCorrectionControlData:
    return ChordCorrectionControlData(
        chord_event_id=chord_event_id,
        current_label=current_label,
        confidence=confidence,
        is_user_corrected=is_user_corrected,
    )


def result_feedback_control(
    *,
    query_owner_id: str,
    result_owner_id: str,
    current_score: float,
) -> ResultFeedbackControlData:
    return ResultFeedbackControlData(
        query_owner_id=query_owner_id,
        result_owner_id=result_owner_id,
        current_score=max(0.0, min(1.0, current_score)),
    )
