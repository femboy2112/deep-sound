from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from deep_sound.cli import main
from deep_sound.domain.feature_view import FeatureType, FeatureView, OwnerType
from deep_sound.infra.storage.sqlite_store import SqliteStore
from deep_sound.services.index_service import IndexService

SEARCHABLE_TYPES = (
    FeatureType.RHYTHM_GLOBAL,
    FeatureType.HARMONY_CHROMA,
    FeatureType.TIMBRE_MFCC_STATS,
    FeatureType.PRODUCTION_TEXTURE,
    FeatureType.STRUCTURE_SECTION_SEQUENCE,
)


def _view(owner_id: str, feature_type: FeatureType, value: float) -> FeatureView:
    return FeatureView(
        id=f"{owner_id}:{feature_type.value}",
        owner_type=OwnerType.TRACK,
        owner_id=owner_id,
        feature_type=feature_type,
        algorithm="test",
        algorithm_version="1",
        params_hash="params",
        stats={"x": value, "y": 1.0 - value},
    )


def _seed_searchable_features(store: SqliteStore) -> None:
    for owner_id, value in [("query", 1.0), ("near", 0.9)]:
        for feature_type in SEARCHABLE_TYPES:
            store.add_feature_view(_view(owner_id, feature_type, value))


def test_index_service_builds_searchable_profile(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    _seed_searchable_features(store)

    statuses = IndexService(store, index_root=tmp_path / "indices").build_profile("searchable")

    assert [(status.owner_type, status.feature_type) for status in statuses] == [
        (OwnerType.TRACK, feature_type) for feature_type in SEARCHABLE_TYPES
    ]
    assert all(status.available for status in statuses)
    assert all(status.feature_count == 2 for status in statuses)


def test_index_library_cli_profile_searchable_builds_all_required_indexes(tmp_path: Path) -> None:
    db_path = tmp_path / "library.sqlite"
    store = SqliteStore(db_path)
    store.init_schema()
    _seed_searchable_features(store)
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "index-library",
            "--library-db",
            str(db_path),
            "--index-root",
            str(tmp_path / "indices"),
            "--profile",
            "searchable",
        ],
    )

    assert result.exit_code == 0, result.output
    for feature_type in SEARCHABLE_TYPES:
        assert f"{feature_type.value}: indexed 2 track row(s)" in result.output
