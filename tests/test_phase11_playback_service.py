from __future__ import annotations

from pathlib import Path

from deep_sound.domain.track import Track
from deep_sound.services.playback_service import (
    LocalPlaybackAdapter,
    PlaybackRequest,
    PlaybackService,
    PlaybackStatus,
)


def test_playback_service_is_import_safe_state_machine(tmp_path: Path) -> None:
    audio_path = tmp_path / "song.wav"
    audio_path.write_bytes(b"not decoded in default playback tests")
    track = Track(id="track-1", filepath=audio_path, duration_sec=12.0)
    service = PlaybackService()

    ready = service.prepare(PlaybackRequest(track, position_sec=-1.0))
    playing = service.play(PlaybackRequest(track, position_sec=3.5))
    paused = service.pause()
    seeked = service.seek(99.0)
    stopped = service.stop()

    assert ready.status is PlaybackStatus.READY
    assert ready.position_sec == 0.0
    assert playing.status is PlaybackStatus.PLAYING
    assert playing.is_output_active is False
    assert paused.status is PlaybackStatus.PAUSED
    assert seeked.position_sec == 12.0
    assert stopped.status is PlaybackStatus.STOPPED


def test_playback_service_reports_missing_file_without_device_access(tmp_path: Path) -> None:
    track = Track(id="track-1", filepath=tmp_path / "missing.wav", duration_sec=4.0)
    service = PlaybackService()

    state = service.play(PlaybackRequest(track, position_sec=2.0))

    assert state.status is PlaybackStatus.FAILED
    assert state.position_sec == 2.0
    assert state.error_message == f"Audio file not found: {track.filepath}"


def test_local_playback_adapter_is_guarded_by_default(tmp_path: Path) -> None:
    audio_path = tmp_path / "song.wav"
    audio_path.write_bytes(b"not decoded in default playback tests")
    track = Track(id="track-1", filepath=audio_path, duration_sec=8.0)
    adapter = LocalPlaybackAdapter()

    state = adapter.play(PlaybackRequest(track, position_sec=1.25))

    assert state.status is PlaybackStatus.PLAYING
    assert state.backend == "local-sounddevice"
    assert state.is_output_active is False
