from __future__ import annotations

from deep_sound.domain.confidence import Confidence
from deep_sound.domain.feature_view import FeatureType, FeatureView, OwnerType
from deep_sound.services.feature_service import FeatureService
from deep_sound.services.similarity_service import SimilarityService


def _stem_feature(owner_id: str, value: float) -> FeatureView:
    return FeatureView(
        id=f"{owner_id}:rhythm.drum",
        owner_type=OwnerType.STEM,
        owner_id=owner_id,
        feature_type=FeatureType.RHYTHM_DRUM,
        algorithm="test",
        algorithm_version="1",
        params_hash="params",
        stats={"a": value, "b": 1.0 - value},
        confidence=Confidence(0.8),
    )


def test_stem_search_filters_to_stem_owners_and_returns_metadata() -> None:
    features = FeatureService()
    features.put(_stem_feature("track-1:drums", 0.9))
    features.put(_stem_feature("track-2:drums", 0.85))
    features.put(
        FeatureView(
            id="track-3:track-rhythm",
            owner_type=OwnerType.TRACK,
            owner_id="track-3",
            feature_type=FeatureType.RHYTHM_DRUM,
            algorithm="test",
            algorithm_version="1",
            params_hash="params",
            stats={"a": 0.85, "b": 0.15},
        )
    )

    results = SimilarityService(features).search_stems("track-1:drums", {"rhythm.drum": 1.0})

    assert [result.owner_id for result in results] == ["track-2:drums"]
    assert results[0].matched_stem == "track-2:drums"
    assert results[0].matched_range == "full stem"
    assert 0.0 <= results[0].score <= 1.0
