from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf

from deep_sound.infra.analyzers.source_chords import infer_source_chord_events


def test_source_chord_analyzer_returns_confidence_bounded_events(tmp_path: Path) -> None:
    sample_rate = 22050
    duration = 2.0
    t = np.linspace(0.0, duration, int(sample_rate * duration), endpoint=False)
    audio = (
        0.2 * np.sin(2 * np.pi * 261.63 * t)
        + 0.2 * np.sin(2 * np.pi * 329.63 * t)
        + 0.2 * np.sin(2 * np.pi * 392.0 * t)
    ).astype(np.float32)
    path = tmp_path / "c_major.wav"
    sf.write(path, audio, sample_rate)

    analysis = infer_source_chord_events(path, owner_id="source-1", sample_rate=sample_rate)

    assert analysis.events
    assert {event.owner_id for event in analysis.events} == {"source-1"}
    assert all(event.chord_label for event in analysis.events)
    assert all(event.roman_numeral for event in analysis.events)
    assert all(0.0 <= event.confidence.value <= 1.0 for event in analysis.events)


def test_source_chord_analyzer_ignores_silence(tmp_path: Path) -> None:
    sample_rate = 22050
    path = tmp_path / "silence.wav"
    sf.write(path, np.zeros(sample_rate, dtype=np.float32), sample_rate)

    analysis = infer_source_chord_events(path, owner_id="source-1", sample_rate=sample_rate)

    assert analysis.events == []
