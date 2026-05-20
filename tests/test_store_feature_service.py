from __future__ import annotations

from pathlib import Path

from deep_sound.domain.feature_view import FeatureType, FeatureView, OwnerType
from deep_sound.infra.storage.sqlite_store import SqliteStore
from deep_sound.services.feature_service import FeatureService


def test_store_backed_feature_service_reads_persisted_views(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    view = FeatureView(
        id="track-1:rhythm",
        owner_type=OwnerType.TRACK,
        owner_id="track-1",
        feature_type=FeatureType.RHYTHM_GLOBAL,
        algorithm="test",
        algorithm_version="1",
        params_hash="params",
        stats={"b": 2.0, "a": 1.0},
    )
    store.add_feature_view(view)
    service = FeatureService(store)

    assert service.get(view.id) == view
    assert service.list_by_owner("track-1") == [view]
    assert service.list_by_type(FeatureType.RHYTHM_GLOBAL, owner_type=OwnerType.TRACK) == [view]
    assert service.get_for_owner("track-1", FeatureType.RHYTHM_GLOBAL) == view
    assert service.vector_for(view) == [1.0, 2.0]


def test_store_backed_feature_service_put_persists_view(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    service = FeatureService(store)
    view = FeatureView(
        id="track-1:timbre",
        owner_type=OwnerType.TRACK,
        owner_id="track-1",
        feature_type=FeatureType.TIMBRE_MFCC_STATS,
        algorithm="test",
        algorithm_version="1",
        params_hash="params",
        stats={"x": 0.5},
    )

    service.put(view)

    assert store.get_feature_view(view.id) == view
