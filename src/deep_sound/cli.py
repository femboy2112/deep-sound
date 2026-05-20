"""deep-sound command-line interface. Phase 0 entry point. Spec §19."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import click

from deep_sound import __version__
from deep_sound.domain.feature_view import FeatureType, FeatureView, OwnerType
from deep_sound.infra.analyzers.chroma_librosa import summarize_chroma
from deep_sound.infra.analyzers.mfcc_librosa import summarize_mfcc
from deep_sound.infra.analyzers.tempo_librosa import estimate_tempo
from deep_sound.services.feature_service import FeatureService
from deep_sound.services.similarity_service import SearchMode, SimilarityService


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


@main.command(name="search-similar")
@click.argument("path", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--corpus-dir",
    required=True,
    type=click.Path(exists=True, file_okay=False),
    help="Directory of candidate audio files to compare against.",
)
@click.option(
    "--mode",
    type=click.Choice([mode.value for mode in SearchMode]),
    default=SearchMode.WEIGHTED.value,
    show_default=True,
)
@click.option("--top-k", default=10, show_default=True, type=int)
@click.option("--sample-rate", default=22050, show_default=True, type=int)
def search_similar(
    path: str,
    corpus_dir: str,
    mode: str,
    top_k: int,
    sample_rate: int,
) -> None:
    """Rank corpus files by Phase 0 audio similarity."""
    query_path = Path(path)
    candidates = [
        candidate
        for candidate in _iter_audio_files(Path(corpus_dir))
        if candidate.resolve() != query_path.resolve()
    ]
    if not candidates:
        raise click.ClickException("No candidate audio files found in corpus directory.")

    features = FeatureService()
    _add_phase0_features(features, query_path, "query", sample_rate)
    for index, candidate in enumerate(candidates):
        _add_phase0_features(features, candidate, f"candidate-{index}", sample_rate)

    service = SimilarityService(features)
    results = service.search_mode("query", SearchMode(mode), top_k=top_k)
    paths_by_id = {f"candidate-{index}": candidate for index, candidate in enumerate(candidates)}

    click.echo(f"Query: {query_path}")
    click.echo(f"Mode:  {mode}")
    click.echo("Results:")
    for rank, result in enumerate(results, start=1):
        dimensions = ", ".join(
            f"{name}={score:.3f}" for name, score in sorted(result.dimension_scores.items())
        )
        click.echo(
            f"{rank}. {paths_by_id[result.owner_id].name} score={result.score:.3f} ({dimensions})"
        )


def _iter_audio_files(corpus_dir: Path) -> Iterable[Path]:
    suffixes = {".aif", ".aiff", ".flac", ".m4a", ".mp3", ".ogg", ".wav"}
    for path in sorted(corpus_dir.iterdir()):
        if path.is_file() and path.suffix.lower() in suffixes:
            yield path


def _add_phase0_features(
    features: FeatureService,
    path: Path,
    owner_id: str,
    sample_rate: int,
) -> None:
    tempo = estimate_tempo(path, sample_rate=sample_rate)
    chroma = summarize_chroma(path, sample_rate=sample_rate)
    mfcc = summarize_mfcc(path, sample_rate=sample_rate)

    features.put(
        FeatureView(
            id=f"{owner_id}:rhythm",
            owner_type=OwnerType.TRACK,
            owner_id=owner_id,
            feature_type=FeatureType.RHYTHM_GLOBAL,
            algorithm=tempo.analyzer,
            algorithm_version=tempo.analyzer_version,
            params_hash=f"sample_rate={sample_rate}",
            stats={
                "tempo_bpm": tempo.tempo_bpm,
                "beats_per_sec": len(tempo.beats_sec) / max(tempo.duration_sec, 1.0),
            },
            confidence=tempo.confidence,
        )
    )
    features.put(
        FeatureView(
            id=f"{owner_id}:harmony",
            owner_type=OwnerType.TRACK,
            owner_id=owner_id,
            feature_type=FeatureType.HARMONY_CHROMA,
            algorithm=chroma.analyzer,
            algorithm_version=chroma.analyzer_version,
            params_hash=f"sample_rate={sample_rate}",
            stats=_vector_stats("chroma", chroma.chroma),
            confidence=chroma.confidence,
        )
    )
    features.put(
        FeatureView(
            id=f"{owner_id}:timbre",
            owner_type=OwnerType.TRACK,
            owner_id=owner_id,
            feature_type=FeatureType.TIMBRE_MFCC_STATS,
            algorithm=mfcc.analyzer,
            algorithm_version=mfcc.analyzer_version,
            params_hash=f"sample_rate={sample_rate};n_mfcc={mfcc.n_mfcc}",
            stats=_vector_stats("mfcc", mfcc.mfcc),
            confidence=mfcc.confidence,
        )
    )


def _vector_stats(prefix: str, values: list[float]) -> dict[str, float]:
    return {f"{prefix}_{index:02d}": value for index, value in enumerate(values)}


if __name__ == "__main__":
    main()
