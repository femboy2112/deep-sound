"""End-to-end test of the Phase 0 `analyze` command on a generated click track."""

from __future__ import annotations

import re
from pathlib import Path

from click.testing import CliRunner

from deep_sound.cli import main
from deep_sound.infra.analyzers.tempo_librosa import estimate_tempo


def test_estimate_tempo_locks_on_click_track(click_track_wav: Path) -> None:
    result = estimate_tempo(click_track_wav)
    # 120 BPM click track. Allow generous tolerance — librosa often reports
    # half/double tempo. Accept the family {60, 120, 240}.
    assert result.tempo_bpm > 0
    candidates = (60.0, 120.0, 240.0)
    assert any(abs(result.tempo_bpm - c) < 6.0 for c in candidates), result.tempo_bpm
    assert 0.0 <= result.confidence.value <= 1.0
    assert result.duration_sec > 3.5  # 4-second fixture


def test_analyze_cli_prints_tempo(click_track_wav: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["analyze", str(click_track_wav)])
    assert result.exit_code == 0, result.output
    assert "Tempo:" in result.output
    assert "confidence" in result.output
    m = re.search(r"Tempo:\s+([\d.]+)\s+BPM", result.output)
    assert m is not None
    assert float(m.group(1)) > 0
