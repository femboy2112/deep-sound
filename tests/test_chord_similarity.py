from __future__ import annotations

from deep_sound.domain.confidence import Confidence
from deep_sound.domain.feature_view import FeatureType, FeatureView, OwnerType
from deep_sound.services.feature_service import FeatureService
from deep_sound.services.similarity_service import SimilarityService


def _source_chord_feature(owner_id: str, token_i: float, token_v: float) -> FeatureView:
    return FeatureView(
        id=f"{owner_id}:harmony.chord_sequence",
        owner_type=OwnerType.SOURCE,
        owner_id=owner_id,
        feature_type=FeatureType.HARMONY_CHORD_SEQUENCE,
        algorithm="test",
        algorithm_version="1",
        params_hash="params",
        stats={"token_I": token_i, "token_V": token_v},
        confidence=Confidence(0.7),
    )


def test_source_chord_search_filters_to_source_owners_and_returns_metadata() -> None:
    features = FeatureService()
    features.put(_source_chord_feature("source-1", 1.0, 1.0))
    features.put(_source_chord_feature("source-2", 0.9, 1.1))
    features.put(
        FeatureView(
            id="track-3:harmony.chord_sequence",
            owner_type=OwnerType.TRACK,
            owner_id="track-3",
            feature_type=FeatureType.HARMONY_CHORD_SEQUENCE,
            algorithm="test",
            algorithm_version="1",
            params_hash="params",
            stats={"token_I": 0.9, "token_V": 1.1},
        )
    )

    results = SimilarityService(features).search_source_chords(
        "source-1",
        include_chord_change=False,
    )

    assert [result.owner_id for result in results] == ["source-2"]
    assert results[0].matched_source == "source-2"
    assert results[0].matched_range == "source chord events"
    assert 0.0 <= results[0].score <= 1.0
