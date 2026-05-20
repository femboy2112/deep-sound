from __future__ import annotations

from deep_sound.domain.corrections import ResultFeedbackValue
from deep_sound.ui.results_view import ResultCardData, result_card_actions


def test_result_card_actions_map_preview_compare_and_feedback() -> None:
    card = ResultCardData(
        track_title="Near Song",
        artist="Artist",
        combined_score=0.91,
        dimension_scores={"rhythm.global": 0.91},
        explanation="Likely similar rhythm evidence.",
        query_owner_id="query",
        result_owner_id="result",
        matched_entity_type="clip",
        matched_range="0.50-1.50s",
    )

    actions = result_card_actions(card)

    assert actions.preview is not None
    assert actions.preview.result_owner_id == "result"
    assert actions.preview.matched_entity_type == "clip"
    assert actions.compare is not None
    assert actions.compare.query_owner_id == "query"
    assert actions.relevant_feedback is not None
    assert actions.relevant_feedback.value is ResultFeedbackValue.RELEVANT
    assert actions.irrelevant_feedback is not None
    assert actions.irrelevant_feedback.value is ResultFeedbackValue.IRRELEVANT


def test_result_card_actions_disable_owner_dependent_actions_without_ids() -> None:
    card = ResultCardData(
        track_title="Unknown",
        artist=None,
        combined_score=0.4,
        dimension_scores={},
        explanation="No actionable owner ids.",
    )

    actions = result_card_actions(card)

    assert actions.preview is None
    assert actions.compare is None
    assert actions.relevant_feedback is None
    assert actions.irrelevant_feedback is None
