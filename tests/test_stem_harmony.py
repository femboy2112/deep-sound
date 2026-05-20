from __future__ import annotations

from pathlib import Path

from deep_sound.infra.analyzers.other_stem import summarize_other_stem


def test_other_stem_summary_contains_harmony_and_timbre(click_track_wav: Path) -> None:
    summary = summarize_other_stem(click_track_wav)

    assert len(summary.chroma) == 12
    assert len(summary.mfcc) == 26
    assert 0.0 <= summary.confidence.value <= 1.0
