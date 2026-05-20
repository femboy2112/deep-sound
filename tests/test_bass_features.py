from __future__ import annotations

from pathlib import Path

from deep_sound.infra.analyzers.bass_stem import summarize_bass_stem


def test_bass_stem_summary_is_confidence_bounded(click_track_wav: Path) -> None:
    summary = summarize_bass_stem(click_track_wav)

    assert 0.0 <= summary.low_energy_ratio <= 1.0
    assert 0.0 <= summary.pitch_motion <= 1.0
    assert 0.0 <= summary.root_stability <= 1.0
    assert 0.0 <= summary.confidence.value <= 1.0
