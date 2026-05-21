from __future__ import annotations

import os
import shutil
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from deep_sound.domain.feature_view import FeatureType, OwnerType
from deep_sound.infra.separation import DemucsProvider
from deep_sound.infra.storage.sqlite_store import SqliteStore
from deep_sound.services.feature_service import FeatureService
from deep_sound.services.index_service import IndexService
from deep_sound.services.library_analysis_service import AnalysisProfile, LibraryAnalysisService
from deep_sound.services.library_service import LibraryService
from deep_sound.services.source_service import SourceService


def test_phase11_live_demucs_workflow_runs_only_when_explicitly_enabled(
    tmp_path: Path,
) -> None:
    if os.environ.get("DEEP_SOUND_RUN_DEMUCS_SMOKE") != "1":
        pytest.skip("set DEEP_SOUND_RUN_DEMUCS_SMOKE=1 to run optional Demucs smoke")
    executable = shutil.which(os.environ.get("DEEP_SOUND_DEMUCS_EXECUTABLE", "demucs"))
    if executable is None:
        pytest.skip("Demucs executable is not installed")
    fixture = os.environ.get("DEEP_SOUND_DEMUCS_SMOKE_AUDIO")
    fixture_path = Path(fixture) if fixture is not None else tmp_path / "generated_demucs_smoke.wav"
    if fixture is None:
        _write_demucs_fixture(fixture_path)
    if not fixture_path.is_file():
        pytest.skip(f"Demucs smoke fixture is not a file: {fixture_path}")

    library_dir = tmp_path / "library"
    library_dir.mkdir()
    first_audio = library_dir / "demucs_query.wav"
    second_audio = library_dir / "demucs_candidate.wav"
    shutil.copyfile(fixture_path, first_audio)
    shutil.copyfile(fixture_path, second_audio)

    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    library = LibraryService(store)
    tracks = [library.import_file(first_audio), library.import_file(second_audio)]
    app_data_dir = tmp_path / "app_data"
    source_service = SourceService(
        store,
        app_data_dir=app_data_dir,
        separation_provider=DemucsProvider(executable=executable),
    )

    summary = LibraryAnalysisService(
        store,
        app_data_dir=app_data_dir,
        source_service=source_service,
    ).analyze_library(tracks, profile=AnalysisProfile.SOURCE_AWARE_REAL)

    assert summary.failed_count == 0, [
        result.error_message for result in summary.results if result.error_message
    ]
    assert summary.completed_count == 2
    for track in tracks:
        stems = store.list_stems_for_track(track.id)
        assert {stem.stem_type.value for stem in stems} == {"vocals", "drums", "bass", "other"}
        assert all(stem.model_name == "demucs" for stem in stems)
        assert all(stem.model_version == "htdemucs" for stem in stems)
        assert all(stem.artifact_path is not None for stem in stems)
        assert all(stem.artifact_path.is_relative_to(app_data_dir) for stem in stems)
        assert store.list_sources_for_track(track.id)

    feature_service = FeatureService(store)
    source_features = feature_service.list_by_type(
        FeatureType.HARMONY_CHORD_SEQUENCE,
        owner_type=OwnerType.SOURCE,
    )
    all_source_features = [
        feature
        for track in tracks
        for source in store.list_sources_for_track(track.id)
        for feature in feature_service.list_by_owner(source.id)
    ]

    assert store.list_feature_views_by_type(FeatureType.RHYTHM_DRUM, owner_type=OwnerType.STEM)
    assert store.list_feature_views_by_type(FeatureType.BASS_ROOT_MOTION, owner_type=OwnerType.STEM)
    assert store.list_feature_views_by_type(
        FeatureType.HARMONY_CHROMA,
        owner_type=OwnerType.STEM,
    )
    assert all(
        feature.confidence is None or 0.0 <= feature.confidence.value <= 1.0
        for feature in all_source_features
    )
    index = IndexService(store, index_root=tmp_path / "indices")
    stem_status = index.build_index(
        FeatureType.RHYTHM_DRUM,
        owner_type=OwnerType.STEM,
    )
    assert stem_status.available

    if len(source_features) >= 2:
        source_status = index.build_index(
            FeatureType.HARMONY_CHORD_SEQUENCE,
            owner_type=OwnerType.SOURCE,
        )
        assert source_status.available


def _write_demucs_fixture(path: Path) -> None:
    sample_rate = 22_050
    duration_sec = 2.0
    t = np.linspace(0.0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
    bass = 0.22 * np.sin(2.0 * np.pi * 82.41 * t)
    chord = 0.12 * (
        np.sin(2.0 * np.pi * 261.63 * t)
        + np.sin(2.0 * np.pi * 329.63 * t)
        + np.sin(2.0 * np.pi * 392.00 * t)
    )
    click = np.zeros_like(t)
    click_len = int(0.015 * sample_rate)
    envelope = np.exp(-np.linspace(0, 6, click_len)).astype(np.float64)
    for beat in (0.0, 0.5, 1.0, 1.5):
        start = int(beat * sample_rate)
        end = min(start + click_len, click.shape[0])
        click[start:end] += 0.35 * envelope[: end - start]
    audio = np.clip(bass + chord + click, -0.9, 0.9).astype(np.float32)
    sf.write(path, audio, sample_rate)
