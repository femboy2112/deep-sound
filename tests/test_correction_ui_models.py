from __future__ import annotations

from deep_sound.domain.source import SourceType
from deep_sound.ui.corrections import (
    chord_correction_control,
    result_feedback_control,
    source_correction_control,
)
from deep_sound.ui.results_view import ResultCardData


def test_correction_ui_dtos_are_import_safe_and_expose_controls() -> None:
    source = source_correction_control(
        source_id="source-1",
        current_label="likely piano",
        current_source_type=SourceType.MELODIC,
        confidence=0.7,
        is_user_corrected=True,
    )
    chord = chord_correction_control(
        chord_event_id="chord-1",
        current_label="Cmaj7",
        confidence=0.6,
        is_user_corrected=True,
    )
    feedback = result_feedback_control(
        query_owner_id="query-1",
        result_owner_id="result-1",
        current_score=1.5,
    )

    assert SourceType.MELODIC.value in source.allowed_source_types
    assert source.is_user_corrected
    assert chord.current_label == "Cmaj7"
    assert feedback.current_score == 1.0
    assert feedback.relevant_value == "relevant"


def test_result_card_dto_exposes_feedback_metadata_without_pyside_imports() -> None:
    card = ResultCardData(
        track_title="Track",
        artist=None,
        combined_score=0.85,
        baseline_score=0.80,
        feedback_adjustment=0.05,
        dimension_scores={"rhythm.global": 0.8},
        explanation="Possible match.",
    )

    assert card.baseline_score == 0.80
    assert card.feedback_adjustment == 0.05
