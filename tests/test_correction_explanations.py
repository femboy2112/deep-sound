from __future__ import annotations

from deep_sound.services.explanation_service import ExplanationService
from deep_sound.services.similarity_service import SimilarityResult


def test_explanation_surfaces_feedback_adjustment_without_definitive_language() -> None:
    summary = ExplanationService().summarize(
        SimilarityResult(
            owner_id="track-2",
            score=0.85,
            baseline_score=0.80,
            feedback_adjustment=0.05,
            dimension_scores={"rhythm.global": 0.80, "feedback_adjustment": 0.05},
        )
    )

    assert "User feedback adjusted the ranking from 0.80 to 0.85 (+0.05)." in summary
    assert "Possible match" in summary or "possible match" in summary
