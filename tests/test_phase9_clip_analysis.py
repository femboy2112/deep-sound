from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import soundfile as sf

from deep_sound.domain.clip import ClipWindow
from deep_sound.domain.feature_view import FeatureType, OwnerType
from deep_sound.domain.track import Track
from deep_sound.infra.storage.sqlite_store import SqliteStore
from deep_sound.services.clip_analysis_service import ClipAnalysisService


def test_clip_analysis_materializes_clip_owned_feature_views(tmp_path: Path) -> None:
    audio_path = tmp_path / "song.wav"
    _write_tone(audio_path)
    original_digest = _digest(audio_path)
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    store.add_track(
        Track(
            id="track-1",
            filepath=audio_path,
            title="Song",
            duration_sec=2.0,
            sample_rate=22050,
        )
    )
    store.add_clip_window(
        ClipWindow(
            id="clip-1",
            track_id="track-1",
            start_sec=0.25,
            end_sec=1.25,
            label="hook",
        )
    )

    result = ClipAnalysisService(
        store,
        app_data_dir=tmp_path / "app_data",
    ).analyze_clip("clip-1")

    persisted = store.list_feature_views_for_owner("clip-1")
    assert result.artifact_path.is_file()
    assert result.artifact_path.is_relative_to(tmp_path / "app_data")
    assert _digest(audio_path) == original_digest
    assert {view.feature_type for view in persisted} == {
        FeatureType.RHYTHM_GLOBAL,
        FeatureType.HARMONY_CHROMA,
        FeatureType.TIMBRE_MFCC_STATS,
    }
    assert {view.owner_type for view in persisted} == {OwnerType.CLIP}
    assert all("track_id=track-1" in view.params_hash for view in persisted)


def test_clip_analysis_rerun_replaces_canonical_clip_features(tmp_path: Path) -> None:
    audio_path = tmp_path / "song.wav"
    _write_tone(audio_path)
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    store.add_track(Track(id="track-1", filepath=audio_path, duration_sec=2.0))
    store.add_clip_window(ClipWindow(id="clip-1", track_id="track-1", start_sec=0.0, end_sec=1.0))
    service = ClipAnalysisService(store, app_data_dir=tmp_path / "app_data")

    service.analyze_clip("clip-1")
    service.analyze_clip("clip-1")

    persisted = store.list_feature_views_for_owner("clip-1")
    assert len(persisted) == 3


def _write_tone(path: Path, sample_rate: int = 22050) -> None:
    t = np.linspace(0.0, 2.0, sample_rate * 2, endpoint=False)
    samples = 0.25 * np.sin(2.0 * np.pi * 440.0 * t)
    sf.write(path, samples, sample_rate)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
