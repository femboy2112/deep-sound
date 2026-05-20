from __future__ import annotations

from pathlib import Path

from deep_sound.infra.analyzers.drum_stem import summarize_drum_stem


def test_drum_stem_summary_is_confidence_bounded(click_track_wav: Path) -> None:
    summary = summarize_drum_stem(click_track_wav)

    assert summary.onset_density > 0.0
    assert 0.0 <= summary.groove_regularity <= 1.0
    assert 0.0 <= summary.spectral_centroid <= 1.0
    assert 0.0 <= summary.confidence.value <= 1.0
