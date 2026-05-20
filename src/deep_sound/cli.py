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
from deep_sound.infra.storage.sqlite_store import SqliteStore
from deep_sound.services.analysis_service import AnalysisService
from deep_sound.services.feature_service import FeatureService
from deep_sound.services.index_service import IndexService
from deep_sound.services.library_analysis_service import AnalysisProfile, LibraryAnalysisService
from deep_sound.services.library_service import LibraryService
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


@main.command(name="analyze-library")
@click.option("--library-db", required=True, type=click.Path(dir_okay=False))
@click.option("--import-path", "import_paths", multiple=True, type=click.Path(exists=True))
@click.option("--sample-rate", default=22050, show_default=True, type=int)
@click.option(
    "--profile",
    type=click.Choice([profile.value for profile in AnalysisProfile]),
    default=AnalysisProfile.MINIMAL.value,
    show_default=True,
)
@click.option("--app-data-dir", type=click.Path(file_okay=False), default=None)
def analyze_library(
    library_db: str,
    import_paths: tuple[str, ...],
    sample_rate: int,
    profile: str,
    app_data_dir: str | None,
) -> None:
    """Import optional files/folders, then persist profile features in SQLite."""
    store = SqliteStore(Path(library_db))
    store.init_schema()
    library = LibraryService(store)
    for raw_path in import_paths:
        path = Path(raw_path)
        if path.is_dir():
            library.import_folder(path)
        else:
            library.import_file(path)

    db_path = Path(library_db)
    resolved_app_data_dir = (
        Path(app_data_dir) if app_data_dir is not None else db_path.parent / "app_data"
    )
    service = LibraryAnalysisService(
        store,
        analysis_service=AnalysisService(store, sample_rate=sample_rate),
        app_data_dir=resolved_app_data_dir,
    )
    result = service.analyze_library(profile=profile)
    click.echo(
        f"Analyzed {result.completed_count}/{result.requested_count} track(s) "
        f"profile={result.profile.value} features={result.feature_count} failed={result.failed_count} "
        f"in {library_db}"
    )


@main.command(name="index-library")
@click.option("--library-db", required=True, type=click.Path(exists=True, dir_okay=False))
@click.option("--index-root", type=click.Path(file_okay=False), default=None)
@click.option(
    "--feature-type",
    multiple=True,
    type=click.Choice([feature_type.value for feature_type in FeatureType]),
)
@click.option(
    "--profile",
    type=click.Choice([profile.value for profile in AnalysisProfile]),
    default=AnalysisProfile.MINIMAL.value,
    show_default=True,
)
@click.option(
    "--owner-type",
    type=click.Choice([owner_type.value for owner_type in OwnerType]),
    default=OwnerType.TRACK.value,
    show_default=True,
)
def index_library(
    library_db: str,
    index_root: str | None,
    feature_type: tuple[str, ...],
    profile: str,
    owner_type: str,
) -> None:
    """Build persisted vector indexes for SQLite feature rows."""
    db_path = Path(library_db)
    store = SqliteStore(db_path)
    root = Path(index_root) if index_root is not None else db_path.parent / "app_data" / "indices"
    service = IndexService(store, index_root=root)
    statuses = (
        tuple(
            service.build_index(FeatureType(raw_feature_type), owner_type=OwnerType(owner_type))
            for raw_feature_type in feature_type
        )
        if feature_type
        else service.build_profile(profile)
    )
    for status in statuses:
        click.echo(
            f"{status.feature_type.value}: indexed {status.feature_count} "
            f"{status.owner_type.value} row(s), backend={status.backend}, stale={status.stale}"
        )


@main.command(name="search-library")
@click.option("--library-db", required=True, type=click.Path(exists=True, dir_okay=False))
@click.option("--query-id", required=True)
@click.option(
    "--mode",
    type=click.Choice([mode.value for mode in SearchMode]),
    default=SearchMode.WEIGHTED.value,
    show_default=True,
)
@click.option("--top-k", default=10, show_default=True, type=int)
@click.option("--index-root", type=click.Path(file_okay=False), default=None)
@click.option("--show-titles", is_flag=True, help="Show hydrated title/path metadata.")
@click.option("--explain", is_flag=True, help="Show backend caveats and result caveats.")
def search_library(
    library_db: str,
    query_id: str,
    mode: str,
    top_k: int,
    index_root: str | None,
    show_titles: bool,
    explain: bool,
) -> None:
    """Search persisted SQLite feature rows, using indexes when current."""
    db_path = Path(library_db)
    store = SqliteStore(db_path)
    root = Path(index_root) if index_root is not None else db_path.parent / "app_data" / "indices"
    features = FeatureService(store)
    index_service = IndexService(store, index_root=root, features=features)
    service = SimilarityService(features, index_service=index_service)
    results = service.search_mode(query_id, SearchMode(mode), top_k=top_k)
    click.echo(f"Query: {query_id}")
    click.echo(f"Mode:  {mode}")
    click.echo("Results:")
    for rank, result in enumerate(results, start=1):
        dimensions = ", ".join(
            f"{name}={score:.3f}" for name, score in sorted(result.dimension_scores.items())
        )
        owner_metadata = _hydrate_result_owner(store, result.owner_type, result.owner_id)
        title = ""
        if show_titles and owner_metadata:
            title = f" title={owner_metadata['title']} path={owner_metadata['path']}"
        caveats = ""
        if explain:
            all_caveats = (*result.caveats, *result.retrieval_caveats)
            if all_caveats:
                caveats = " caveats=" + " | ".join(dict.fromkeys(all_caveats))
        click.echo(
            f"{rank}. {result.owner_id} score={result.score:.3f} "
            f"entity={result.matched_entity_type or result.owner_type.value} "
            f"backend={result.search_backend} ({dimensions}){title}{caveats}".rstrip()
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


def _hydrate_result_owner(
    store: SqliteStore,
    owner_type: OwnerType,
    owner_id: str,
) -> dict[str, str]:
    if owner_type is OwnerType.TRACK:
        try:
            track = store.get_track(owner_id)
        except KeyError:
            return {"title": owner_id, "path": owner_id}
        return {"title": track.title or track.filepath.stem, "path": str(track.filepath)}

    if owner_type is OwnerType.SOURCE:
        try:
            source = store.get_source(owner_id)
            track = store.get_track(source.track_id)
        except KeyError:
            return {"title": owner_id, "path": owner_id}
        title = f"{track.title or track.filepath.stem} / {source.source_label}"
        return {"title": title, "path": str(track.filepath)}

    if owner_type is OwnerType.STEM:
        for track in store.list_tracks():
            for stem in store.list_stems_for_track(track.id):
                if stem.id == owner_id:
                    title = f"{track.title or track.filepath.stem} / {stem.stem_type.value}"
                    path = str(stem.artifact_path or track.filepath)
                    return {"title": title, "path": path}

    return {"title": owner_id, "path": owner_id}


if __name__ == "__main__":
    main()
