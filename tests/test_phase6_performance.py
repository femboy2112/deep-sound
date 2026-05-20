from __future__ import annotations

from pathlib import Path

from deep_sound.domain.feature_view import FeatureType, FeatureView, OwnerType
from deep_sound.infra.storage.sqlite_store import SqliteStore
from deep_sound.services.feature_service import FeatureService
from deep_sound.services.index_service import IndexService
from deep_sound.services.similarity_service import SearchMode, SimilarityService


def test_medium_synthetic_library_index_smoke_is_core_light(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    for index in range(150):
        store.add_feature_view(
            FeatureView(
                id=f"track-{index}:rhythm",
                owner_type=OwnerType.TRACK,
                owner_id=f"track-{index}",
                feature_type=FeatureType.RHYTHM_GLOBAL,
                algorithm="synthetic",
                algorithm_version="1",
                params_hash="params",
                stats={"tempo": float(90 + index % 30), "density": float(index % 7)},
            )
        )
    features = FeatureService(store)
    index_service = IndexService(store, index_root=tmp_path / "indices", features=features)

    status = index_service.build_index(FeatureType.RHYTHM_GLOBAL)
    results = SimilarityService(features, index_service=index_service).search_mode(
        "track-0",
        SearchMode.RHYTHM,
        top_k=10,
    )

    assert status.feature_count == 150
    assert len(results) == 10
    assert {result.search_backend for result in results} == {"index"}
