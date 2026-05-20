from __future__ import annotations

from pathlib import Path

import pytest

from deep_sound.domain.clip import ClipWindow
from deep_sound.domain.confidence import Confidence
from deep_sound.domain.feature_view import FeatureType, FeatureView, OwnerType
from deep_sound.domain.track import Track
from deep_sound.infra.storage.sqlite_store import SqliteStore


def test_clip_window_validates_time_bounds() -> None:
    with pytest.raises(ValueError, match="greater"):
        ClipWindow(id="clip-1", track_id="track-1", start_sec=2.0, end_sec=1.0)


def test_clip_window_storage_round_trip_and_feature_owner_typing(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    store.add_track(Track(id="track-1", filepath=tmp_path / "song.wav", audio_hash="hash"))
    clip = ClipWindow(
        id="clip-1",
        track_id="track-1",
        start_sec=1.0,
        end_sec=4.0,
        label="hook",
    )

    saved = store.add_clip_window(clip)
    view = FeatureView(
        id="clip-1:rhythm.global",
        owner_type=OwnerType.CLIP,
        owner_id=clip.id,
        feature_type=FeatureType.RHYTHM_GLOBAL,
        algorithm="test",
        algorithm_version="1",
        params_hash="params",
        stats={"tempo_bpm": 120.0},
        confidence=Confidence(0.8),
    )
    store.add_feature_view(view)

    assert saved == clip
    assert store.get_clip_window(clip.id) == clip
    assert store.list_clip_windows_for_track("track-1") == [clip]
    assert store.list_feature_views_for_owner(clip.id) == [view]
