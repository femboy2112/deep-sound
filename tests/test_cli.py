"""Smoke tests for the deep-sound CLI surface."""

from __future__ import annotations

from click.testing import CliRunner

from deep_sound.cli import main


def test_help_lists_analyze() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0, result.output
    assert "analyze" in result.output


def test_version_prints() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert result.output.strip()
