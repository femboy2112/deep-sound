"""deep-sound command-line interface. Phase 0 entry point. Spec §19."""

from __future__ import annotations

from pathlib import Path

import click

from deep_sound import __version__
from deep_sound.infra.analyzers.tempo_librosa import estimate_tempo


@click.group()
@click.version_option(__version__)
def main() -> None:
    """deep-sound — source-aware music similarity (Phase 0 CLI)."""


@main.command()
@click.argument("path", type=click.Path(exists=True, dir_okay=False))
@click.option("--sample-rate", default=22050, show_default=True, type=int)
def analyze(path: str, sample_rate: int) -> None:
    """Analyze an audio file and print tempo with confidence (spec §3.3)."""
    audio_path = Path(path)
    result = estimate_tempo(audio_path, sample_rate=sample_rate)
    click.echo(
        f"File:       {audio_path}\n"
        f"Duration:   {result.duration_sec:.2f} s\n"
        f"Sample rate:{result.sample_rate} Hz\n"
        f"Tempo:      {result.tempo_bpm:.2f} BPM "
        f"(confidence {result.confidence} - {result.confidence.band.value})\n"
        f"Beats:      {len(result.beats_sec)} detected\n"
        f"Analyzer:   {result.analyzer} v{result.analyzer_version}"
    )


if __name__ == "__main__":
    main()
