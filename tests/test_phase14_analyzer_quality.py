from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf

from deep_sound.infra.analyzers.bass_stem import summarize_bass_stem
from deep_sound.infra.analyzers.drum_stem import summarize_drum_stem
from deep_sound.infra.analyzers.melody_contour import summarize_melody_contour
from deep_sound.infra.analyzers.source_chords import infer_source_chord_events


def test_chord_analyzer_segments_changes_and_merges_repeated_labels(tmp_path: Path) -> None:
    sample_rate = 22_050
    first = _chord(sample_rate, (261.63, 329.63, 392.0), 1.0)
    repeated = _chord(sample_rate, (261.63, 329.63, 392.0), 1.0)
    changed = _chord(sample_rate, (196.0, 246.94, 392.0), 1.0)
    path = tmp_path / "progression.wav"
    sf.write(path, np.concatenate([first, repeated, changed]).astype(np.float32), sample_rate)

    analysis = infer_source_chord_events(path, owner_id="source-1", sample_rate=sample_rate)

    assert len(analysis.events) >= 2
    assert analysis.events[0].chord_label == "C"
    assert analysis.events[0].end_sec > 1.5
    assert all(0.0 <= event.confidence.value <= 1.0 for event in analysis.events)


def test_melody_contour_reports_smoothed_voicing_metrics(tmp_path: Path) -> None:
    sample_rate = 22_050
    path = tmp_path / "rising.wav"
    tones = [_tone(sample_rate, frequency, 0.4) for frequency in (261.63, 293.66, 329.63, 392.0)]
    sf.write(path, np.concatenate(tones).astype(np.float32), sample_rate)

    summary = summarize_melody_contour(path, sample_rate=sample_rate)

    assert summary.analyzer_version == "0.2.0"
    assert summary.contour["activity"] > 0.5
    assert summary.contour["voicing_confidence"] == summary.contour["activity"]
    assert summary.contour["contour_smoothness"] > 0.5
    assert summary.contour["upward_motion"] >= summary.contour["downward_motion"]
    assert all(0.0 <= value <= 1.0 for value in summary.contour.values())


def test_bass_and_drum_quality_stats_are_normalized(tmp_path: Path) -> None:
    sample_rate = 22_050
    bass_path = tmp_path / "bass.wav"
    bass = np.concatenate([_tone(sample_rate, freq, 0.45, amplitude=0.3) for freq in (82.41, 98.0)])
    sf.write(bass_path, bass.astype(np.float32), sample_rate)
    drum_path = tmp_path / "drums.wav"
    sf.write(drum_path, _clicks(sample_rate, 2.0).astype(np.float32), sample_rate)

    bass_summary = summarize_bass_stem(bass_path, sample_rate=sample_rate)
    drum_summary = summarize_drum_stem(drum_path, sample_rate=sample_rate)

    assert bass_summary.analyzer_version == "2"
    assert drum_summary.analyzer_version == "2"
    assert 0.0 <= bass_summary.pitch_variety <= 1.0
    assert 0.0 <= bass_summary.median_register <= 1.0
    assert 0.0 <= drum_summary.transient_strength <= 1.0
    assert 0.0 <= drum_summary.high_frequency_ratio <= 1.0


def _tone(
    sample_rate: int,
    frequency: float,
    duration_sec: float,
    *,
    amplitude: float = 0.2,
) -> np.ndarray:
    t = np.linspace(0.0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
    return amplitude * np.sin(2.0 * np.pi * frequency * t)


def _chord(sample_rate: int, frequencies: tuple[float, ...], duration_sec: float) -> np.ndarray:
    tones = [_tone(sample_rate, frequency, duration_sec) for frequency in frequencies]
    return np.sum(np.asarray(tones), axis=0)


def _clicks(sample_rate: int, duration_sec: float) -> np.ndarray:
    samples = np.zeros(int(sample_rate * duration_sec), dtype=np.float64)
    click_len = int(0.02 * sample_rate)
    envelope = np.exp(-np.linspace(0, 6, click_len))
    beat = 0.0
    while beat < duration_sec:
        start = int(beat * sample_rate)
        end = min(start + click_len, samples.shape[0])
        samples[start:end] += 0.35 * envelope[: end - start]
        beat += 0.5
    return samples
