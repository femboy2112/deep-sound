from __future__ import annotations

from pathlib import Path

from deep_sound.domain.track import Track
from deep_sound.services.playback_service import PlaybackState, PlaybackStatus
from deep_sound.ui.track_detail import PlaybackAction, playback_controls_data, track_detail_data


def test_track_detail_data_includes_play_pause_seek_action_dtos(tmp_path: Path) -> None:
    track = Track(
        id="track-1",
        filepath=tmp_path / "song.wav",
        title="Song",
        duration_sec=30.0,
    )
    state = PlaybackState(
        track_id="track-1",
        source_path=track.filepath,
        status=PlaybackStatus.PAUSED,
        position_sec=8.5,
        duration_sec=30.0,
        backend="local-sounddevice",
    )

    detail = track_detail_data(track, playback_state=state)

    assert detail.playback is not None
    assert detail.playback.status is PlaybackStatus.PAUSED
    assert detail.playback.backend == "local-sounddevice"
    assert detail.playback.play_action is not None
    assert detail.playback.play_action.action is PlaybackAction.PLAY
    assert detail.playback.play_action.position_sec == 8.5
    assert detail.playback.play_action.source_path == str(track.filepath)
    assert detail.playback.pause_action is not None
    assert detail.playback.pause_action.action is PlaybackAction.PAUSE
    assert detail.playback.seek_action is not None
    assert detail.playback.seek_action.action is PlaybackAction.SEEK
    assert detail.playback.seek_action.duration_sec == 30.0


def test_track_detail_ignores_other_track_playback_state(tmp_path: Path) -> None:
    track = Track(id="track-1", filepath=tmp_path / "song.wav", duration_sec=10.0)
    other_state = PlaybackState(
        track_id="track-2",
        source_path=tmp_path / "other.wav",
        status=PlaybackStatus.PLAYING,
        position_sec=7.0,
        duration_sec=20.0,
    )

    controls = playback_controls_data(track, playback_state=other_state)

    assert controls.status is PlaybackStatus.STOPPED
    assert controls.position_sec == 0.0
    assert controls.duration_sec == 10.0
    assert controls.error_message is None
