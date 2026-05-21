from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from deep_sound.domain.track import Track
from deep_sound.services.playback_service import (
    LocalPlaybackAdapter,
    PlaybackRequest,
    PlaybackStatus,
)


def test_opt_in_real_playback_smoke_plays_generated_audio(tmp_path: Path) -> None:
    if os.environ.get("DEEP_SOUND_RUN_PLAYBACK_SMOKE") != "1":
        pytest.skip("Set DEEP_SOUND_RUN_PLAYBACK_SMOKE=1 to run real playback smoke.")
    pytest.importorskip("sounddevice")

    audio_path = tmp_path / "generated_playback_smoke.wav"
    sample_rate = 22_050
    t = np.linspace(0.0, 0.20, int(sample_rate * 0.20), endpoint=False)
    sf.write(audio_path, (0.05 * np.sin(2.0 * np.pi * 440.0 * t)).astype(np.float32), sample_rate)
    before = audio_path.read_bytes()

    adapter = LocalPlaybackAdapter(audio_output_enabled=True)
    state = adapter.play(
        PlaybackRequest(
            Track(id="playback-smoke", filepath=audio_path, duration_sec=0.20),
            position_sec=0.0,
        )
    )
    stopped = adapter.stop()

    assert state.status is PlaybackStatus.PLAYING
    assert state.is_output_active is True
    assert stopped.status is PlaybackStatus.STOPPED
    assert audio_path.read_bytes() == before
