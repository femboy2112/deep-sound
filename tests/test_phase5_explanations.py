from __future__ import annotations

from deep_sound.domain.feature_view import OwnerType
from deep_sound.services.explanation_service import ExplanationService
from deep_sound.services.similarity_service import SimilarityResult


def test_phase5_explanation_mentions_entity_and_advanced_dimensions() -> None:
    summary = ExplanationService().summarize(
        SimilarityResult(
            owner_id="track-2",
            owner_type=OwnerType.TRACK,
            matched_entity_type="track",
            score=0.82,
            dimension_scores={
                "production.texture": 0.88,
                "structure.section_sequence": 0.76,
            },
            caveats=("Production texture evidence is probabilistic.",),
        )
    )

    assert "production.texture similarity at 0.88" in summary
    assert "matched entity type is track" in summary
    assert "Production texture evidence is probabilistic" in summary
