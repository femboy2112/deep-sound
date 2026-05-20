from __future__ import annotations

from deep_sound.ui.results_view import ResultCardData, confidence_warnings, result_feedback_action


def test_result_card_feedback_action_requires_query_and_result_ids() -> None:
    card = ResultCardData(
        track_title="Near Song",
        artist=None,
        combined_score=0.8,
        dimension_scores={"rhythm.global": 0.8},
        explanation="Probabilistic similarity result.",
        query_owner_id="query",
        result_owner_id="result",
        search_backend="mixed",
        stale_index_warnings=("Index is stale for feature_count.",),
        caveats=("Similarity result is probabilistic.",),
    )

    action = result_feedback_action(card)

    assert action is not None
    assert action.query_owner_id == "query"
    assert action.result_owner_id == "result"


def test_similarity_warnings_do_not_label_scores_as_confidence() -> None:
    warnings = confidence_warnings({"rhythm.global": 0.25})

    assert warnings == ("rhythm.global similarity evidence is weak (0.25)",)
