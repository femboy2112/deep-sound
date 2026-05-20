from __future__ import annotations

from deep_sound.domain.confidence import Confidence
from deep_sound.domain.feature_view import FeatureType, FeatureView, OwnerType
from deep_sound.services.feature_service import FeatureService
from deep_sound.services.similarity_service import SearchMode, SimilarityService


def test_production_search_mode_scores_texture_features() -> None:
    features = FeatureService()
    _put(features, "query", FeatureType.PRODUCTION_TEXTURE, [1.0, 0.0])
    _put(features, "close", FeatureType.PRODUCTION_TEXTURE, [0.9, 0.1])
    _put(features, "far", FeatureType.PRODUCTION_TEXTURE, [0.0, 1.0])

    results = SimilarityService(features).search_mode("query", SearchMode.PRODUCTION)

    assert [result.owner_id for result in results] == ["close", "far"]
    assert "production.texture" in results[0].dimension_scores


def test_advanced_search_mode_combines_phase5_dimensions() -> None:
    features = FeatureService()
    for owner_id, production, structure in [
        ("query", [1.0, 0.0], [0.8, 0.2]),
        ("close", [0.9, 0.1], [0.7, 0.3]),
        ("far", [0.0, 1.0], [0.1, 0.9]),
    ]:
        _put(features, owner_id, FeatureType.PRODUCTION_TEXTURE, production)
        _put(features, owner_id, FeatureType.STRUCTURE_SECTION_SEQUENCE, structure)

    results = SimilarityService(features).search_mode("query", SearchMode.ADVANCED)

    assert [result.owner_id for result in results] == ["close", "far"]
    assert set(results[0].dimension_scores) == {
        "production.texture",
        "structure.section_sequence",
    }


def _put(
    features: FeatureService,
    owner_id: str,
    feature_type: FeatureType,
    values: list[float],
) -> None:
    features.put(
        FeatureView(
            id=f"{owner_id}:{feature_type.value}",
            owner_type=OwnerType.TRACK,
            owner_id=owner_id,
            feature_type=feature_type,
            algorithm="test",
            algorithm_version="1",
            params_hash="params",
            stats={f"value_{index}": value for index, value in enumerate(values)},
            confidence=Confidence(0.8),
        )
    )
