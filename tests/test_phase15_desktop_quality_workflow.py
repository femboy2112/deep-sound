from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np
import soundfile as sf
from click.testing import CliRunner

from deep_sound.cli import main
from deep_sound.infra.storage.sqlite_store import SqliteStore
from deep_sound.services.library_analysis_service import AnalysisProfile
from deep_sound.ui.library_workflow import (
    AnalyzeIntentDTO,
    DesktopWorkflowController,
    ImportIntentDTO,
    IndexIntentDTO,
    SearchIntentDTO,
)


def test_cli_quality_analyze_index_search_round_trip(
    tmp_path: Path,
    click_track_wav: Path,
) -> None:
    library_dir = tmp_path / "library"
    library_dir.mkdir()
    query_path = library_dir / "query.wav"
    near_path = library_dir / "near.wav"
    shutil.copyfile(click_track_wav, query_path)
    _write_click(near_path, bpm=124.0)
    db_path = tmp_path / "library.sqlite"
    runner = CliRunner()

    analyze = runner.invoke(
        main,
        [
            "analyze-library",
            "--library-db",
            str(db_path),
            "--import-path",
            str(library_dir),
            "--profile",
            "quality",
        ],
    )
    index = runner.invoke(
        main,
        ["index-library", "--library-db", str(db_path), "--profile", "quality"],
    )
    query_id = SqliteStore(db_path).list_tracks()[0].id
    search = runner.invoke(
        main,
        [
            "search-library",
            "--library-db",
            str(db_path),
            "--query-id",
            query_id,
            "--mode",
            "quality",
            "--show-titles",
            "--explain",
        ],
    )

    assert analyze.exit_code == 0, analyze.output
    assert "profile=quality" in analyze.output
    assert index.exit_code == 0, index.output
    assert "rhythm.global: indexed" in index.output
    assert search.exit_code == 0, search.output
    assert "backend=index" in search.output
    assert "entity=track" in search.output


def test_desktop_controller_quality_workflow(
    tmp_path: Path,
    click_track_wav: Path,
) -> None:
    library_dir = tmp_path / "library"
    library_dir.mkdir()
    shutil.copyfile(click_track_wav, library_dir / "query.wav")
    _write_click(library_dir / "near.wav", bpm=124.0)
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    controller = DesktopWorkflowController(store, app_data_dir=tmp_path / "app_data")

    import_job = controller.import_paths(ImportIntentDTO(paths=(library_dir,)))
    analyze_job = controller.analyze(AnalyzeIntentDTO(profile=AnalysisProfile.QUALITY))
    index_job = controller.build_index(IndexIntentDTO(profile=AnalysisProfile.QUALITY))
    track = store.list_tracks()[0]
    results = controller.search(SearchIntentDTO(query_id=track.id, mode="quality"))
    snapshot = controller.snapshot()

    assert import_job.status == "completed"
    assert analyze_job.status == "completed"
    assert index_job.status == "completed"
    assert results
    assert results[0].search_backend == "index"
    assert snapshot.active_profile is AnalysisProfile.QUALITY
    assert snapshot.index_statuses


def _write_click(path: Path, *, bpm: float) -> None:
    sample_rate = 22_050
    duration_sec = 4.0
    period_sec = 60.0 / bpm
    samples = np.zeros(int(sample_rate * duration_sec), dtype=np.float32)
    click_len = int(0.02 * sample_rate)
    envelope = np.exp(-np.linspace(0, 6, click_len)).astype(np.float32)
    beat = 0.0
    while beat < duration_sec:
        start = int(beat * sample_rate)
        end = min(start + click_len, samples.shape[0])
        samples[start:end] += envelope[: end - start]
        beat += period_sec
    sf.write(path, samples, sample_rate)
