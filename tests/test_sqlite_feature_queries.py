from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from deep_sound.domain.feature_view import FeatureType, FeatureView, OwnerType
from deep_sound.infra.storage.sqlite_store import SqliteStore


def _view(owner_id: str, feature_type: FeatureType, value: float) -> FeatureView:
    return FeatureView(
        id=f"{owner_id}:{feature_type.value}",
        owner_type=OwnerType.TRACK,
        owner_id=owner_id,
        feature_type=feature_type,
        algorithm="test",
        algorithm_version="1",
        params_hash="params",
        stats={"x": value, "y": value + 1.0},
    )


def test_sqlite_feature_queries_by_type_and_owner(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    rhythm = _view("track-1", FeatureType.RHYTHM_GLOBAL, 1.0)
    timbre = _view("track-1", FeatureType.TIMBRE_MFCC_STATS, 2.0)
    other = _view("track-2", FeatureType.RHYTHM_GLOBAL, 3.0)
    store.add_feature_view(rhythm)
    store.add_feature_view(timbre)
    store.add_feature_view(other)

    assert store.list_feature_views_by_type(FeatureType.RHYTHM_GLOBAL) == [rhythm, other]
    assert store.list_feature_views_by_type(
        FeatureType.RHYTHM_GLOBAL,
        owner_type=OwnerType.TRACK,
    ) == [rhythm, other]
    assert store.get_feature_view_for_owner("track-1", FeatureType.TIMBRE_MFCC_STATS) == timbre


def test_sqlite_feature_owner_type_lookup_rejects_duplicates(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    store.add_feature_view(_view("track-1", FeatureType.RHYTHM_GLOBAL, 1.0))
    duplicate = _view("track-1", FeatureType.RHYTHM_GLOBAL, 2.0)
    store.add_feature_view(replace(duplicate, id="dupe"))

    with pytest.raises(ValueError, match="Multiple FeatureViews"):
        store.get_feature_view_for_owner("track-1", FeatureType.RHYTHM_GLOBAL)
