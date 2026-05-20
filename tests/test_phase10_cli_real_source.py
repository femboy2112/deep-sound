from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from deep_sound.cli import main
from deep_sound.infra.storage.sqlite_store import SqliteStore
from tests.phase10_helpers import write_fake_demucs_executable


def test_analyze_library_source_aware_real_reports_missing_demucs(
    tmp_path: Path,
    click_track_wav: Path,
) -> None:
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "analyze-library",
            "--library-db",
            str(tmp_path / "library.sqlite"),
            "--import-path",
            str(click_track_wav),
            "--profile",
            "source_aware_real",
            "--demucs-executable",
            str(tmp_path / "missing-demucs"),
        ],
    )

    assert result.exit_code != 0
    assert "source_aware_real analysis failed" in result.output
    assert "source_aware_real requires" in result.output


def test_analyze_library_source_aware_real_uses_explicit_demucs_executable(
    tmp_path: Path,
    click_track_wav: Path,
) -> None:
    db_path = tmp_path / "library.sqlite"
    app_data_dir = tmp_path / "app_data"
    executable = write_fake_demucs_executable(tmp_path / "demucs")
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "analyze-library",
            "--library-db",
            str(db_path),
            "--import-path",
            str(click_track_wav),
            "--profile",
            "source_aware_real",
            "--app-data-dir",
            str(app_data_dir),
            "--demucs-executable",
            str(executable),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "profile=source_aware_real" in result.output

    store = SqliteStore(db_path)
    track = store.list_tracks()[0]
    assert track.analysis_status == "source_aware_real"
    assert {stem.model_name for stem in store.list_stems_for_track(track.id)} == {"demucs"}
