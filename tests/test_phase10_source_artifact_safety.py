from __future__ import annotations

from pathlib import Path

from deep_sound.domain.track import Track
from deep_sound.infra.separation import DemucsProvider
from deep_sound.infra.storage.sqlite_store import SqliteStore
from deep_sound.services.library_analysis_service import AnalysisProfile, LibraryAnalysisService
from deep_sound.services.source_service import SourceService
from tests.phase10_helpers import write_fake_demucs_executable


def test_source_aware_real_writes_artifacts_under_app_data_and_preserves_original(
    tmp_path: Path,
    click_track_wav: Path,
) -> None:
    original_bytes = click_track_wav.read_bytes()
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    track = store.add_track(
        Track(
            id="track-1",
            filepath=click_track_wav,
            duration_sec=4.0,
            sample_rate=22050,
            audio_hash="hash",
        )
    )
    app_data_dir = tmp_path / "app_data"
    executable = write_fake_demucs_executable(tmp_path / "demucs")
    source_service = SourceService(
        store,
        app_data_dir=app_data_dir,
        separation_provider=DemucsProvider(executable=str(executable)),
    )

    result = LibraryAnalysisService(
        store,
        app_data_dir=app_data_dir,
        source_service=source_service,
    ).analyze_track(track, profile=AnalysisProfile.SOURCE_AWARE_REAL)

    assert result.succeeded
    assert click_track_wav.read_bytes() == original_bytes
    stems = store.list_stems_for_track(track.id)
    assert len(stems) == 4
    for stem in stems:
        assert stem.artifact_path is not None
        assert stem.artifact_path.exists()
        assert stem.artifact_path.is_relative_to(app_data_dir)
        assert stem.model_name == "demucs"
        assert stem.model_version == "htdemucs"
        assert stem.params_hash
        assert stem.input_hash
    assert store.list_sources_for_track(track.id)
