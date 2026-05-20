from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf
from click.testing import CliRunner

from deep_sound.cli import main
from deep_sound.infra.storage.sqlite_store import SqliteStore


def test_beta_acceptance_import_analyze_index_search_hydrated_results(tmp_path: Path) -> None:
    library_dir = tmp_path / "library"
    library_dir.mkdir()
    _write_click_track(library_dir / "query_song.wav", bpm=120.0)
    _write_click_track(library_dir / "near_song.wav", bpm=124.0)
    db_path = tmp_path / "library.sqlite"
    index_root = tmp_path / "indices"
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
            "searchable",
        ],
    )
    store = SqliteStore(db_path)
    tracks = store.list_tracks()
    query_id = next(track.id for track in tracks if track.title == "query_song")
    index = runner.invoke(
        main,
        [
            "index-library",
            "--library-db",
            str(db_path),
            "--index-root",
            str(index_root),
            "--profile",
            "searchable",
        ],
    )
    search = runner.invoke(
        main,
        [
            "search-library",
            "--library-db",
            str(db_path),
            "--query-id",
            query_id,
            "--mode",
            "rhythm",
            "--index-root",
            str(index_root),
            "--show-titles",
            "--explain",
        ],
    )

    assert analyze.exit_code == 0, analyze.output
    assert "profile=searchable" in analyze.output
    assert "failed=0" in analyze.output
    assert len(tracks) == 2
    assert index.exit_code == 0, index.output
    assert "production.texture: indexed 2 track row(s)" in index.output
    assert "structure.section_sequence: indexed 2 track row(s)" in index.output
    assert search.exit_code == 0, search.output
    assert "near_song" in search.output
    assert "entity=track" in search.output
    assert "backend=index" in search.output
    assert "rhythm.global=" in search.output


def _write_click_track(path: Path, *, bpm: float) -> None:
    sample_rate = 22050
    duration_sec = 3.0
    period_sec = 60.0 / bpm
    samples = np.zeros(int(sample_rate * duration_sec), dtype=np.float32)
    click_len = int(0.02 * sample_rate)
    envelope = np.exp(-np.linspace(0, 6, click_len)).astype(np.float32)
    t = 0.0
    while t < duration_sec:
        start = int(t * sample_rate)
        end = min(start + click_len, samples.shape[0])
        samples[start:end] += envelope[: end - start]
        t += period_sec
    sf.write(path, samples, sample_rate)
