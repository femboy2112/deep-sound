"""Shared pytest fixtures.

The headline fixture is `click_track_wav`: a 120-BPM click track generated at
test time. We avoid pure sine waves because they have no onsets and the beat
tracker returns tempo=0 (documented in docs/build/DECISIONS.md).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf


@pytest.fixture
def click_track_wav(tmp_path: Path) -> Path:
    """Generate a 4-second, 120-BPM click track at 22050 Hz, mono.

    Two clicks per second = 120 BPM. Each click is a short exponentially
    decaying impulse so the beat tracker can lock onto a clear periodic
    onset envelope.
    """
    sample_rate = 22050
    duration_sec = 4.0
    bpm = 120.0
    period_sec = 60.0 / bpm  # 0.5

    samples = np.zeros(int(sample_rate * duration_sec), dtype=np.float32)
    click_len = int(0.02 * sample_rate)  # 20 ms click
    envelope = np.exp(-np.linspace(0, 6, click_len)).astype(np.float32)
    noise = np.random.default_rng(0).standard_normal(click_len).astype(np.float32) * 0.3
    click = envelope * (noise + 1.0)  # bright transient

    t = 0.0
    while t < duration_sec:
        start = int(t * sample_rate)
        end = min(start + click_len, samples.shape[0])
        samples[start:end] += click[: end - start]
        t += period_sec

    out = tmp_path / "click_120bpm.wav"
    sf.write(out, samples, sample_rate)
    return out
