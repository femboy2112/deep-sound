from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from deep_sound.domain.track import Track
from deep_sound.infra.separation import DemucsProvider
from deep_sound.infra.storage.sqlite_store import SqliteStore
from deep_sound.services.library_analysis_service import AnalysisProfile, LibraryAnalysisService
from deep_sound.services.source_service import SourceService


def test_optional_demucs_smoke_runs_only_when_explicitly_enabled(tmp_path: Path) -> None:
    if os.environ.get("DEEP_SOUND_RUN_DEMUCS_SMOKE") != "1":
        pytest.skip("set DEEP_SOUND_RUN_DEMUCS_SMOKE=1 to run optional Demucs smoke")
    executable = shutil.which(os.environ.get("DEEP_SOUND_DEMUCS_EXECUTABLE", "demucs"))
    if executable is None:
        pytest.skip("Demucs executable is not installed")
    fixture = os.environ.get("DEEP_SOUND_DEMUCS_SMOKE_AUDIO")
    if fixture is None:
        pytest.skip("set DEEP_SOUND_DEMUCS_SMOKE_AUDIO to a tiny local audio fixture")
    audio_path = Path(fixture)
    if not audio_path.is_file():
        pytest.skip(f"Demucs smoke fixture is not a file: {audio_path}")

    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    track = store.add_track(
        Track(
            id="track-1",
            filepath=audio_path,
            duration_sec=None,
            sample_rate=None,
            audio_hash="manual-smoke",
        )
    )
    app_data_dir = tmp_path / "app_data"
    source_service = SourceService(
        store,
        app_data_dir=app_data_dir,
        separation_provider=DemucsProvider(executable=executable),
    )

    result = LibraryAnalysisService(
        store,
        app_data_dir=app_data_dir,
        source_service=source_service,
    ).analyze_track(track, profile=AnalysisProfile.SOURCE_AWARE_REAL)

    assert result.succeeded, result.error_message
    assert len(store.list_stems_for_track(track.id)) == 4
    assert all(stem.model_name == "demucs" for stem in store.list_stems_for_track(track.id))
