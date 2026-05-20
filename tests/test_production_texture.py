from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf

from deep_sound.infra.analyzers.production_texture import summarize_production_texture


def test_production_texture_returns_bounded_stats_for_audio(click_track_wav: Path) -> None:
    summary = summarize_production_texture(click_track_wav)

    assert set(summary.stats) == {
        "rms_mean",
        "loudness_profile",
        "dynamic_range",
        "spectral_balance",
        "brightness",
        "low_end_weight",
        "flatness",
        "rolloff",
        "transient_density",
        "stereo_width",
    }
    assert all(0.0 <= value <= 1.0 for value in summary.stats.values())
    assert summary.confidence.value > 0.0


def test_production_texture_silence_has_zero_confidence(tmp_path: Path) -> None:
    path = tmp_path / "silence.wav"
    sf.write(path, np.zeros(22050, dtype=np.float32), 22050)

    summary = summarize_production_texture(path)

    assert summary.confidence.value == 0.0
    assert all(value == 0.0 for value in summary.stats.values())
