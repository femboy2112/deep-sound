from __future__ import annotations

from pathlib import Path

from deep_sound.domain.feature_view import OwnerType
from deep_sound.domain.track import Track
from deep_sound.infra.separation import DemucsProvider
from deep_sound.infra.storage.sqlite_store import SqliteStore
from deep_sound.services.library_analysis_service import AnalysisProfile, LibraryAnalysisService
from deep_sound.services.source_service import SourceService
from tests.phase10_helpers import write_fake_demucs_executable


def test_source_aware_real_profile_uses_demucs_provider_and_preserves_fake_default(
    tmp_path: Path,
    click_track_wav: Path,
) -> None:
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
    real_source_service = SourceService(
        store,
        app_data_dir=app_data_dir,
        separation_provider=DemucsProvider(executable=str(executable)),
    )
    real_service = LibraryAnalysisService(
        store,
        app_data_dir=app_data_dir,
        source_service=real_source_service,
    )

    real_result = real_service.analyze_track(track, profile=AnalysisProfile.SOURCE_AWARE_REAL)

    assert real_result.succeeded
    assert real_result.profile is AnalysisProfile.SOURCE_AWARE_REAL
    assert store.get_track(track.id).analysis_status == "source_aware_real"
    real_stems = store.list_stems_for_track(track.id)
    assert {stem.model_name for stem in real_stems} == {"demucs"}
    assert all(stem.artifact_path is not None for stem in real_stems)
    assert all(str(stem.artifact_path).startswith(str(app_data_dir)) for stem in real_stems)
    assert OwnerType.SOURCE in {view.owner_type for view in real_result.feature_views}

    fake_store = SqliteStore(tmp_path / "fake-library.sqlite")
    fake_store.init_schema()
    fake_track = fake_store.add_track(
        Track(
            id="track-1",
            filepath=click_track_wav,
            duration_sec=4.0,
            sample_rate=22050,
            audio_hash="hash",
        )
    )
    fake_result = LibraryAnalysisService(
        fake_store,
        app_data_dir=tmp_path / "fake_app_data",
    ).analyze_track(fake_track, profile=AnalysisProfile.SOURCE_AWARE)

    assert fake_result.succeeded
    assert {stem.model_name for stem in fake_store.list_stems_for_track(fake_track.id)} == {
        "fake-broad-stem-copy"
    }
