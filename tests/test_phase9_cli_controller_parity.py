from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from deep_sound.cli import main
from deep_sound.domain.feature_view import FeatureType, FeatureView, OwnerType
from deep_sound.domain.track import Track
from deep_sound.infra.storage.sqlite_store import SqliteStore
from deep_sound.ui.library_workflow import DesktopWorkflowController, SearchIntentDTO


def test_cli_and_controller_search_expose_same_backend_and_result_owner(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "library.sqlite"
    index_root = tmp_path / "indices"
    store = SqliteStore(db_path)
    store.init_schema()
    store.add_track(Track(id="query", filepath=tmp_path / "query.wav", audio_hash="query-hash"))
    store.add_track(
        Track(
            id="near",
            filepath=tmp_path / "near.wav",
            title="Near Song",
            audio_hash="near-hash",
        )
    )
    store.add_feature_view(_feature("query", 1.0))
    store.add_feature_view(_feature("near", 0.9))
    runner = CliRunner()

    index = runner.invoke(
        main,
        [
            "index-library",
            "--library-db",
            str(db_path),
            "--index-root",
            str(index_root),
            "--feature-type",
            FeatureType.RHYTHM_GLOBAL.value,
        ],
    )
    cli = runner.invoke(
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
            str(index_root),
            "--show-titles",
            "--explain",
        ],
    )
    controller = DesktopWorkflowController(
        store,
        app_data_dir=tmp_path / "app_data",
    )
    cards = controller.search(SearchIntentDTO(query_id="query", mode="rhythm"))

    assert index.exit_code == 0, index.output
    assert cli.exit_code == 0, cli.output
    assert "near score=" in cli.output
    assert "backend=index" in cli.output
    assert cards[0].result_owner_id == "near"
    assert cards[0].search_backend == "index"


def _feature(owner_id: str, value: float) -> FeatureView:
    return FeatureView(
        id=f"{owner_id}:rhythm.global",
        owner_type=OwnerType.TRACK,
        owner_id=owner_id,
        feature_type=FeatureType.RHYTHM_GLOBAL,
        algorithm="test",
        algorithm_version="1",
        params_hash="params",
        stats={"x": value, "y": 1.0 - value},
    )
