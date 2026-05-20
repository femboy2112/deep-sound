from __future__ import annotations

from deep_sound.domain.feature_view import OwnerType
from deep_sound.services.explanation_service import ExplanationService
from deep_sound.services.similarity_service import SimilarityResult


def test_source_chord_explanations_distinguish_source_specific_harmony() -> None:
    summary = ExplanationService().summarize(
        SimilarityResult(
            owner_id="source-2",
            owner_type=OwnerType.SOURCE,
            score=0.61,
            dimension_scores={"harmony.chord_sequence": 0.61},
            matched_source="source-2",
            matched_range="source chord events",
            caveats=("Source-specific chord match is probabilistic.",),
        )
    )

    assert "matched source is source-2" in summary
    assert "source and chord labels are probabilistic" in summary
    assert "source chord events" in summary
    assert "Source-specific chord match is probabilistic." in summary
