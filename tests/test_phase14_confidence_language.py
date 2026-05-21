from __future__ import annotations

from deep_sound.domain.feature_view import OwnerType
from deep_sound.services.explanation_service import ExplanationService
from deep_sound.services.similarity_service import SimilarityResult


def test_quality_explanation_keeps_similarity_distinct_from_confidence() -> None:
    result = SimilarityResult(
        owner_id="track-2",
        score=0.82,
        owner_type=OwnerType.TRACK,
        matched_entity_type="track",
        dimension_scores={
            "production.texture": 0.9,
            "structure.section_sequence": 0.74,
            "harmony.chroma": 0.65,
        },
        caveats=("Generated quality profile evidence uses deterministic MIR proxies.",),
    )

    text = ExplanationService().summarize(result)

    assert "possible match" in text
    assert "similarity evidence" in text
    assert "definitive identification" in text
    assert "deterministic MIR proxies" in text
    assert "definite match" not in text
    assert "confidence score" not in text
