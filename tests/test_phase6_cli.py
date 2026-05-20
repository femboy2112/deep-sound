from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from deep_sound.cli import main
from deep_sound.domain.feature_view import FeatureType, FeatureView, OwnerType
from deep_sound.infra.storage.sqlite_store import SqliteStore


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


def test_index_and_search_library_cli_over_sqlite_features(tmp_path: Path) -> None:
    db_path = tmp_path / "library.sqlite"
    store = SqliteStore(db_path)
    store.init_schema()
    store.add_feature_view(_view("query", (1.0, 0.0)))
    store.add_feature_view(_view("near", (0.9, 0.1)))
    runner = CliRunner()

    index_result = runner.invoke(
        main,
        [
            "index-library",
            "--library-db",
            str(db_path),
            "--index-root",
            str(tmp_path / "indices"),
            "--feature-type",
            FeatureType.RHYTHM_GLOBAL.value,
        ],
    )
    search_result = runner.invoke(
        main,
        [
            "search-library",
            "--library-db",
            str(db_path),
            "--query-id",
            "query",
            "--mode",
            "rhythm",
            "--index-root",
            str(tmp_path / "indices"),
        ],
    )

    assert index_result.exit_code == 0, index_result.output
    assert "rhythm.global: indexed 2 track row(s)" in index_result.output
    assert search_result.exit_code == 0, search_result.output
    assert "near score=" in search_result.output
    assert "backend=index" in search_result.output
