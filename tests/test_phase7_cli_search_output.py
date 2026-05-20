from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from deep_sound.cli import main
from deep_sound.domain.feature_view import FeatureType, FeatureView, OwnerType
from deep_sound.domain.track import Track
from deep_sound.infra.storage.sqlite_store import SqliteStore


def _view(owner_id: str, value: float) -> FeatureView:
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


def test_search_library_cli_hydrates_track_metadata_and_caveats(tmp_path: Path) -> None:
    db_path = tmp_path / "library.sqlite"
    store = SqliteStore(db_path)
    store.init_schema()
    store.add_track(
        Track(
            id="query",
            filepath=tmp_path / "query.wav",
            title="Query Song",
            audio_hash="query-hash",
        )
    )
    store.add_track(
        Track(
            id="near",
            filepath=tmp_path / "near.wav",
            title="Near Song",
            audio_hash="near-hash",
        )
    )
    store.add_feature_view(_view("query", 1.0))
    store.add_feature_view(_view("near", 0.9))
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "search-library",
            "--library-db",
            str(db_path),
            "--query-id",
            "query",
            "--mode",
            "rhythm",
            "--show-titles",
            "--explain",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "near score=" in result.output
    assert "entity=track" in result.output
    assert "backend=scan" in result.output
    assert "rhythm.global=" in result.output
    assert "title=Near Song" in result.output
    assert "path=" in result.output
    assert "caveats=No persisted index is available" in result.output
