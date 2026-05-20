from __future__ import annotations

from pathlib import Path

from deep_sound.domain.feature_view import FeatureType, FeatureView, OwnerType
from deep_sound.infra.storage.sqlite_store import SqliteStore
from deep_sound.services.feature_service import FeatureService
from deep_sound.services.index_service import IndexService
from deep_sound.services.similarity_service import SearchMode, SimilarityService


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


def test_similarity_uses_current_index_for_candidate_retrieval(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    store.add_feature_view(_view("query", (1.0, 0.0)))
    store.add_feature_view(_view("near", (0.9, 0.1)))
    store.add_feature_view(_view("far", (0.0, 1.0)))
    features = FeatureService(store)
    index = IndexService(store, index_root=tmp_path / "indices", features=features)
    index.build_index(FeatureType.RHYTHM_GLOBAL)

    results = SimilarityService(features, index_service=index).search_mode(
        "query",
        SearchMode.RHYTHM,
    )

    assert [result.owner_id for result in results] == ["near", "far"]
    assert {result.search_backend for result in results} == {"index"}
    assert (
        results[0].dimension_scores[FeatureType.RHYTHM_GLOBAL.value]
        > results[1].dimension_scores[FeatureType.RHYTHM_GLOBAL.value]
    )


def test_similarity_falls_back_to_scan_when_index_missing(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    store.add_feature_view(_view("query", (1.0, 0.0)))
    store.add_feature_view(_view("near", (0.9, 0.1)))
    features = FeatureService(store)
    index = IndexService(store, index_root=tmp_path / "indices", features=features)

    result = SimilarityService(features, index_service=index).search_mode(
        "query",
        SearchMode.RHYTHM,
    )[0]

    assert result.owner_id == "near"
    assert result.search_backend == "scan"
    assert result.retrieval_caveats
