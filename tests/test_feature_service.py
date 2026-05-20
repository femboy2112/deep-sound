"""Tests for the Phase 0 in-memory FeatureService."""

from __future__ import annotations

import pytest

from deep_sound.domain.feature_view import FeatureType, FeatureView, OwnerType
from deep_sound.services.feature_service import FeatureService


def _feature_view(
    view_id: str = "view-1",
    owner_id: str = "track-1",
    feature_type: FeatureType = FeatureType.HARMONY_CHROMA,
) -> FeatureView:
    return FeatureView(
        id=view_id,
        owner_type=OwnerType.TRACK,
        owner_id=owner_id,
        feature_type=feature_type,
        algorithm="test",
        algorithm_version="0.0",
        params_hash="params",
        stats={"v_01": 2.0, "v_00": 1.0},
    )


def test_feature_service_put_get_and_vector_order() -> None:
    service = FeatureService()
    view = _feature_view()

    service.put(view)

    assert service.get("view-1") == view
    assert service.vector_for(view) == [1.0, 2.0]


def test_feature_service_lists_by_owner_and_type() -> None:
    service = FeatureService()
    harmony = _feature_view("harmony", "track-1", FeatureType.HARMONY_CHROMA)
    timbre = _feature_view("timbre", "track-1", FeatureType.TIMBRE_MFCC_STATS)
    other = _feature_view("other", "track-2", FeatureType.HARMONY_CHROMA)

    service.put(harmony)
    service.put(timbre)
    service.put(other)

    assert service.list_by_owner("track-1") == [harmony, timbre]
    assert service.list_by_type(FeatureType.HARMONY_CHROMA) == [harmony, other]
    assert service.get_for_owner("track-1", FeatureType.TIMBRE_MFCC_STATS) == timbre


def test_feature_service_rejects_missing_duplicate_and_invalid_stats() -> None:
    service = FeatureService()
    view = _feature_view()
    service.put(view)

    with pytest.raises(KeyError):
        service.get("missing")
    with pytest.raises(ValueError):
        service.put(view)
    with pytest.raises(ValueError):
        service.put(
            FeatureView(
                id="nan",
                owner_type=OwnerType.TRACK,
                owner_id="track-nan",
                feature_type=FeatureType.HARMONY_CHROMA,
                algorithm="test",
                algorithm_version="0.0",
                params_hash="params",
                stats={"value": float("nan")},
            )
        )
