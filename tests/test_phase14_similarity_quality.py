from __future__ import annotations

from deep_sound.domain.confidence import Confidence
from deep_sound.domain.feature_view import FeatureType, FeatureView, OwnerType
from deep_sound.services.feature_service import FeatureService
from deep_sound.services.similarity_service import SearchMode, SimilarityService


def test_quality_search_mode_uses_track_level_quality_dimensions() -> None:
    features = FeatureService()
    for owner_id, production, structure in [
        ("query", [1.0, 0.0], [0.9, 0.1]),
        ("close", [0.9, 0.1], [0.8, 0.2]),
        ("far", [0.0, 1.0], [0.1, 0.9]),
    ]:
        _put(features, owner_id, FeatureType.RHYTHM_GLOBAL, [1.0, 0.0])
        _put(features, owner_id, FeatureType.HARMONY_CHROMA, [1.0, 0.0])
        _put(features, owner_id, FeatureType.TIMBRE_MFCC_STATS, [1.0, 0.0])
        _put(features, owner_id, FeatureType.PRODUCTION_TEXTURE, production)
        _put(features, owner_id, FeatureType.STRUCTURE_SECTION_SEQUENCE, structure)

    results = SimilarityService(features).search_mode("query", SearchMode.QUALITY)

    assert [result.owner_id for result in results] == ["close", "far"]
    assert set(results[0].dimension_scores) == {
        "rhythm.global",
        "harmony.chroma",
        "timbre.mfcc_stats",
        "production.texture",
        "structure.section_sequence",
    }
    assert all(0.0 <= score <= 1.0 for score in results[0].dimension_scores.values())


def test_quality_weight_key_is_supported_without_index_service() -> None:
    features = FeatureService()
    _put(features, "query", FeatureType.PRODUCTION_TEXTURE, [1.0, 0.0])
    _put(features, "candidate", FeatureType.PRODUCTION_TEXTURE, [0.8, 0.2])

    results = SimilarityService(features).search("query", {"quality": 1.0}, top_k=1)

    assert results[0].owner_id == "candidate"
    assert results[0].search_backend == "scan"


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
