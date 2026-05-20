from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from deep_sound.domain.feature_view import FeatureType, FeatureView, OwnerType
from deep_sound.infra.storage.sqlite_store import SqliteStore
from deep_sound.services.index_service import IndexService


def _view(owner_id: str, values: tuple[float, float]) -> FeatureView:
    return FeatureView(
        id=f"{owner_id}:rhythm",
        owner_type=OwnerType.TRACK,
        owner_id=owner_id,
        feature_type=FeatureType.RHYTHM_GLOBAL,
        algorithm="test",
        algorithm_version="1",
        params_hash="params",
        stats={"x": values[0], "y": values[1]},
    )


def test_index_service_builds_manifest_and_queries(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    store.add_feature_view(_view("query", (1.0, 0.0)))
    store.add_feature_view(_view("near", (0.9, 0.1)))
    store.add_feature_view(_view("far", (0.0, 1.0)))
    service = IndexService(store, index_root=tmp_path / "indices")

    status = service.build_index(FeatureType.RHYTHM_GLOBAL)
    ids, query_status = service.query(
        FeatureType.RHYTHM_GLOBAL,
        [1.0, 0.0],
        top_k=3,
    )

    assert status.available is True
    assert status.stale is False
    assert query_status.backend in {"numpy", "faiss"}
    assert ids[:2] == ["query", "near"]
    assert store.list_similarity_indices(FeatureType.RHYTHM_GLOBAL.value)


def test_index_service_detects_stale_feature_set(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    store.add_feature_view(_view("query", (1.0, 0.0)))
    service = IndexService(store, index_root=tmp_path / "indices")
    service.build_index(FeatureType.RHYTHM_GLOBAL)
    store.add_feature_view(replace(_view("new", (0.5, 0.5)), id="new:rhythm"))

    status = service.status(FeatureType.RHYTHM_GLOBAL)

    assert status.available is False
    assert status.stale is True
    assert any("feature_count" in caveat for caveat in status.caveats)
