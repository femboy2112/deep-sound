from __future__ import annotations

from deep_sound.domain.confidence import Confidence
from deep_sound.domain.feature_view import FeatureType, FeatureView, OwnerType
from deep_sound.services.feature_service import FeatureService
from deep_sound.services.similarity_service import SimilarityService


def test_source_role_matching_returns_source_metadata() -> None:
    features = FeatureService()
    for owner_id, melody, timbre in [
        ("query-source", [0.8, 0.2], [1.0, 0.0]),
        ("close-source", [0.75, 0.25], [0.9, 0.1]),
        ("far-source", [0.1, 0.9], [0.0, 1.0]),
    ]:
        _put_source(features, owner_id, FeatureType.MELODY_CONTOUR, melody)
        _put_source(features, owner_id, FeatureType.TIMBRE_EMBEDDING, timbre)

    results = SimilarityService(features).search_source_roles("query-source")

    assert [result.owner_id for result in results] == ["close-source", "far-source"]
    assert results[0].matched_source == "close-source"
    assert results[0].matched_range == "source melody and timbre features"
    assert "chord" not in " ".join(results[0].caveats).lower()


def _put_source(
    features: FeatureService,
    owner_id: str,
    feature_type: FeatureType,
    values: list[float],
) -> None:
    features.put(
        FeatureView(
            id=f"{owner_id}:{feature_type.value}",
            owner_type=OwnerType.SOURCE,
            owner_id=owner_id,
            feature_type=feature_type,
            algorithm="test",
            algorithm_version="1",
            params_hash="params",
            stats={f"value_{index}": value for index, value in enumerate(values)},
            confidence=Confidence(0.8),
        )
    )
