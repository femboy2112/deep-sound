"""Tests for the Phase 0 chroma analyzer."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from deep_sound.infra.analyzers.chroma_librosa import summarize_chroma


def test_summarize_chroma_returns_12_bin_distribution(tmp_path: Path) -> None:
    sample_rate = 22050
    duration_sec = 2.0
    t = np.linspace(0.0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
    audio = (0.5 * np.sin(2.0 * np.pi * 440.0 * t)).astype(np.float32)
    audio_path = tmp_path / "a4.wav"
    sf.write(audio_path, audio, sample_rate)

    result = summarize_chroma(audio_path)

    assert len(result.chroma) == 12
    assert all(value >= 0.0 for value in result.chroma)
    assert sum(result.chroma) == pytest.approx(1.0, abs=1e-6)
    assert max(result.chroma) > 0.2
    assert 0.0 <= result.confidence.value <= 1.0
    assert result.duration_sec > 1.9
    assert result.sample_rate == sample_rate


def test_summarize_chroma_handles_silence(tmp_path: Path) -> None:
    sample_rate = 22050
    audio_path = tmp_path / "silence.wav"
    sf.write(audio_path, np.zeros(sample_rate, dtype=np.float32), sample_rate)

    result = summarize_chroma(audio_path)

    assert result.chroma == [0.0] * 12
    assert result.confidence.value == 0.0
