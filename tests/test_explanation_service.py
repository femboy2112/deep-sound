from __future__ import annotations

from deep_sound.services.explanation_service import ExplanationService
from deep_sound.services.similarity_service import SimilarityResult


def test_explanation_service_summarizes_similarity_result_cautiously() -> None:
    summary = ExplanationService().summarize(
        SimilarityResult(
            owner_id="track-2",
            score=0.72,
            dimension_scores={
                "rhythm.global": 0.83,
                "harmony.chroma": 0.31,
                "timbre.mfcc_stats": 0.62,
            },
        )
    )

    assert "track-2 is a possible match" in summary
    assert "rhythm.global similarity at 0.83" in summary
    assert "Low-confidence or weak dimensions (harmony.chroma)" in summary
    assert "cautiously" in summary


def test_explanation_service_handles_raw_scores_and_empty_details() -> None:
    raw_summary = ExplanationService().summarize({"timbre.mfcc_stats": 0.7})
    empty_summary = ExplanationService().summarize({})

    assert raw_summary.startswith("Possible match based on available score details.")
    assert "not a definitive identification" in raw_summary
    assert "no comparable score details" in empty_summary
