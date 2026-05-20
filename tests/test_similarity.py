"""Tests for Phase 0 cosine similarity search."""

from __future__ import annotations

import pytest

from deep_sound.domain.feature_view import FeatureType, FeatureView, OwnerType
from deep_sound.services.feature_service import FeatureService
from deep_sound.services.similarity_service import SearchMode, SimilarityService, cosine_score


def _put_feature(
    service: FeatureService,
    owner_id: str,
    feature_type: FeatureType,
    values: list[float],
) -> None:
    service.put(
        FeatureView(
            id=f"{owner_id}:{feature_type.value}",
            owner_type=OwnerType.TRACK,
            owner_id=owner_id,
            feature_type=feature_type,
            algorithm="test",
            algorithm_version="0.0",
            params_hash="params",
            stats={f"v_{index:02d}": value for index, value in enumerate(values)},
        )
    )


def test_cosine_score_handles_identity_orthogonal_and_zero_vectors() -> None:
    assert cosine_score([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
    assert cosine_score([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)
    assert cosine_score([1.0, 0.0], [0.0, 0.0]) == pytest.approx(0.0)


def test_similarity_service_ranks_by_mode_specific_cosine() -> None:
    features = FeatureService()
    _put_feature(features, "query", FeatureType.TIMBRE_MFCC_STATS, [1.0, 0.0])
    _put_feature(features, "close", FeatureType.TIMBRE_MFCC_STATS, [1.0, 0.0])
    _put_feature(features, "far", FeatureType.TIMBRE_MFCC_STATS, [0.0, 1.0])

    results = SimilarityService(features).search_mode("query", SearchMode.TIMBRE)

    assert [result.owner_id for result in results] == ["close", "far"]
    assert results[0].score == pytest.approx(1.0)
    assert results[1].score == pytest.approx(0.0)


def test_similarity_service_combines_weighted_dimensions() -> None:
    features = FeatureService()
    for owner_id, timbre, harmony in (
        ("query", [1.0, 0.0], [1.0, 0.0]),
        ("balanced", [1.0, 0.0], [0.0, 1.0]),
        ("harmony", [0.0, 1.0], [1.0, 0.0]),
    ):
        _put_feature(features, owner_id, FeatureType.TIMBRE_MFCC_STATS, timbre)
        _put_feature(features, owner_id, FeatureType.HARMONY_CHROMA, harmony)

    results = SimilarityService(features).search(
        "query",
        {"timbre": 1.0, "harmony": 3.0},
    )

    assert [result.owner_id for result in results] == ["harmony", "balanced"]
    assert results[0].score == pytest.approx(0.75)
    assert results[1].score == pytest.approx(0.25)
