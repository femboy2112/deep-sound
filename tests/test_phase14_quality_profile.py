from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf

from deep_sound.domain.feature_view import FeatureType
from deep_sound.domain.stem import StemType
from deep_sound.domain.track import Track
from deep_sound.infra.separation.providers import file_sha256
from deep_sound.infra.storage.sqlite_store import SqliteStore
from deep_sound.services.library_analysis_service import AnalysisProfile, LibraryAnalysisService


def test_quality_profile_is_dependency_light_and_source_aware(tmp_path: Path) -> None:
    sample_rate = 22_050
    audio_path = tmp_path / "quality_mix.wav"
    _write_quality_mix(audio_path, sample_rate=sample_rate)
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    track = store.add_track(
        Track(
            id="track-1",
            filepath=audio_path,
            duration_sec=4.0,
            sample_rate=sample_rate,
            audio_hash=file_sha256(audio_path),
        )
    )

    result = LibraryAnalysisService(store, app_data_dir=tmp_path / "app_data").analyze_track(
        track,
        profile=AnalysisProfile.QUALITY,
    )

    assert result.succeeded
    assert result.profile is AnalysisProfile.QUALITY
    assert store.get_track(track.id).analysis_status == "quality"
    assert {stem.stem_type for stem in store.list_stems_for_track(track.id)} == {
        StemType.VOCALS,
        StemType.DRUMS,
        StemType.BASS,
        StemType.OTHER,
    }
    feature_types = {
        view.feature_type
        for owner_id in _all_owner_ids(store, track.id)
        for view in store.list_feature_views_for_owner(owner_id)
    }
    assert {
        FeatureType.RHYTHM_GLOBAL,
        FeatureType.PRODUCTION_TEXTURE,
        FeatureType.RHYTHM_DRUM,
        FeatureType.BASS_ROOT_MOTION,
        FeatureType.MELODY_CONTOUR,
        FeatureType.TIMBRE_EMBEDDING,
    } <= feature_types


def _write_quality_mix(path: Path, *, sample_rate: int) -> None:
    duration = 4.0
    t = np.linspace(0.0, duration, int(sample_rate * duration), endpoint=False)
    chord = 0.2 * (
        np.sin(2 * np.pi * 261.63 * t)
        + np.sin(2 * np.pi * 329.63 * t)
        + np.sin(2 * np.pi * 392.0 * t)
    )
    bass = 0.16 * np.sin(2 * np.pi * 82.41 * t)
    clicks = np.zeros_like(t)
    click_len = int(0.02 * sample_rate)
    envelope = np.exp(-np.linspace(0, 6, click_len))
    beat = 0.0
    while beat < duration:
        start = int(beat * sample_rate)
        end = min(start + click_len, clicks.shape[0])
        clicks[start:end] += 0.2 * envelope[: end - start]
        beat += 0.5
    sf.write(path, np.clip(chord + bass + clicks, -0.9, 0.9).astype(np.float32), sample_rate)


def _all_owner_ids(store: SqliteStore, track_id: str) -> list[str]:
    stems = store.list_stems_for_track(track_id)
    sources = store.list_sources_for_track(track_id)
    return [track_id, *(stem.id for stem in stems), *(source.id for source in sources)]
