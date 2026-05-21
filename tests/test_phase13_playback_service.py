from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np

from deep_sound.domain.track import Track
from deep_sound.services import playback_service
from deep_sound.services.playback_service import (
    LocalPlaybackAdapter,
    PlaybackRequest,
    PlaybackStatus,
    PlaybackTransport,
)


def test_local_playback_adapter_uses_sounddevice_when_enabled(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    audio_path = tmp_path / "song.wav"
    audio_path.write_bytes(b"decoded by fake soundfile")
    calls: list[tuple[str, object]] = []

    fake_soundfile = SimpleNamespace(
        read=lambda path, always_2d: (np.arange(10, dtype=np.float32), 10)
    )

    def play(data: object, sample_rate: int, *, blocking: bool) -> None:
        calls.append(("play", (len(data), sample_rate, blocking)))

    def stop() -> None:
        calls.append(("stop", None))

    fake_sounddevice = SimpleNamespace(play=play, stop=stop)

    def fake_import_module(name: str) -> object:
        return fake_soundfile if name == "soundfile" else fake_sounddevice

    monkeypatch.setattr(playback_service, "import_module", fake_import_module)
    adapter: PlaybackTransport = LocalPlaybackAdapter(audio_output_enabled=True)

    state = adapter.play(PlaybackRequest(_track(audio_path), position_sec=0.2))
    seeked = adapter.seek(99.0)
    stopped = adapter.stop()

    assert state.status is PlaybackStatus.PLAYING
    assert state.is_output_active is True
    assert seeked.position_sec == 1.0
    assert stopped.status is PlaybackStatus.STOPPED
    assert calls == [
        ("play", (8, 10, False)),
        ("stop", None),
        ("play", (0, 10, False)),
        ("stop", None),
    ]


def test_local_playback_adapter_reports_decode_or_device_error(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    audio_path = tmp_path / "song.wav"
    audio_path.write_bytes(b"bad")

    def fake_import_module(name: str) -> object:
        if name == "soundfile":
            raise RuntimeError("decode failed")
        return SimpleNamespace()

    monkeypatch.setattr(playback_service, "import_module", fake_import_module)
    adapter = LocalPlaybackAdapter(audio_output_enabled=True)

    state = adapter.play(PlaybackRequest(_track(audio_path), position_sec=0.0))

    assert state.status is PlaybackStatus.FAILED
    assert state.error_message == "decode failed"
    assert state.is_output_active is False


def _track(audio_path: Path) -> Track:
    return Track(id="track-1", filepath=audio_path, duration_sec=1.0)
