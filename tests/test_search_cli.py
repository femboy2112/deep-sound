"""End-to-end tests for the Phase 0 search-similar CLI."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf
from click.testing import CliRunner

from deep_sound.cli import main


def _write_tone(path: Path, frequency: float, sample_rate: int = 22050) -> None:
    duration_sec = 1.5
    t = np.linspace(0.0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
    audio = (
        0.35 * np.sin(2.0 * np.pi * frequency * t)
        + 0.10 * np.sin(2.0 * np.pi * frequency * 2.0 * t)
    ).astype(np.float32)
    sf.write(path, audio, sample_rate)


def test_search_similar_ranks_closest_candidate_first(tmp_path: Path) -> None:
    query = tmp_path / "query.wav"
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    close = corpus / "close.wav"
    far = corpus / "far.wav"
    _write_tone(query, 440.0)
    _write_tone(close, 440.0)
    _write_tone(far, 196.0)

    result = CliRunner().invoke(
        main,
        [
            "search-similar",
            str(query),
            "--corpus-dir",
            str(corpus),
            "--mode",
            "timbre",
            "--top-k",
            "2",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Results:" in result.output
    assert "1. close.wav" in result.output
    assert "2. far.wav" in result.output
    assert "timbre.mfcc_stats=" in result.output
