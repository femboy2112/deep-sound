"""Tests for the Phase 0 MFCC timbre analyzer."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf

from deep_sound.infra.analyzers.mfcc_librosa import DEFAULT_N_MFCC, summarize_mfcc


def test_summarize_mfcc_returns_mean_std_vector(tmp_path: Path) -> None:
    sample_rate = 22050
    duration_sec = 2.0
    t = np.linspace(0.0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
    audio = (
        0.35 * np.sin(2.0 * np.pi * 220.0 * t) + 0.20 * np.sin(2.0 * np.pi * 880.0 * t)
    ).astype(np.float32)
    audio_path = tmp_path / "tone.wav"
    sf.write(audio_path, audio, sample_rate)

    result = summarize_mfcc(audio_path)

    assert len(result.mfcc) == DEFAULT_N_MFCC * 2
    assert any(value != 0.0 for value in result.mfcc)
    assert 0.0 <= result.confidence.value <= 1.0
    assert result.duration_sec > 1.9
    assert result.sample_rate == sample_rate


def test_summarize_mfcc_handles_silence(tmp_path: Path) -> None:
    sample_rate = 22050
    audio_path = tmp_path / "silence.wav"
    sf.write(audio_path, np.zeros(sample_rate, dtype=np.float32), sample_rate)

    result = summarize_mfcc(audio_path)

    assert result.mfcc == [0.0] * (DEFAULT_N_MFCC * 2)
    assert result.confidence.value == 0.0
