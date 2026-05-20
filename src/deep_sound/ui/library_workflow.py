"""Import-safe controller DTOs for the Phase 7 library workflow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from deep_sound.domain.corrections import ResultFeedbackValue
from deep_sound.domain.feature_view import OwnerType
from deep_sound.infra.storage.sqlite_store import JobRecord, SqliteStore
from deep_sound.services.index_service import IndexStatus
from deep_sound.services.library_analysis_service import AnalysisProfile
from deep_sound.services.similarity_service import SimilarityResult
from deep_sound.ui.query_builder import IndexStatusDTO
from deep_sound.ui.results_view import ResultCardData, confidence_warnings


@dataclass(frozen=True, slots=True)
class ImportIntentDTO:
    paths: tuple[Path, ...]
    recursive: bool = True


@dataclass(frozen=True, slots=True)
class AnalyzeIntentDTO:
    profile: AnalysisProfile
    reanalyze: bool = True


@dataclass(frozen=True, slots=True)
class IndexIntentDTO:
    profile: AnalysisProfile
    rebuild: bool = True


@dataclass(frozen=True, slots=True)
class SearchIntentDTO:
    query_id: str
    mode: str
    top_k: int = 10


@dataclass(frozen=True, slots=True)
class FeedbackIntentDTO:
    query_owner_id: str
    result_owner_id: str
    value: ResultFeedbackValue


@dataclass(frozen=True, slots=True)
class WorkflowJobDTO:
    job_id: str
    job_type: str
    target_type: str
    target_id: str
    status: str
    progress: float
    error_message: str | None = None
    retry_enabled: bool = False


@dataclass(frozen=True, slots=True)
class WorkflowWarningDTO:
    severity: str
    message: str


@dataclass(frozen=True, slots=True)
class WorkflowSnapshotDTO:
    active_profile: AnalysisProfile
    jobs: tuple[WorkflowJobDTO, ...] = ()
    index_statuses: tuple[IndexStatusDTO, ...] = ()
    warnings: tuple[WorkflowWarningDTO, ...] = ()


def job_dto(job: JobRecord) -> WorkflowJobDTO:
    return WorkflowJobDTO(
        job_id=job.id,
        job_type=job.job_type,
        target_type=job.target_type,
        target_id=job.target_id,
        status=job.status,
        progress=job.progress,
        error_message=job.error_message,
        retry_enabled=job.status == "failed",
    )


def index_status_dto(status: IndexStatus) -> IndexStatusDTO:
    return IndexStatusDTO(
        feature_type=status.feature_type,
        owner_type=status.owner_type,
        available=status.available,
        stale=status.stale,
        backend=status.backend,
        feature_count=status.feature_count,
        dim=status.dim,
        warnings=status.caveats,
    )


def stale_index_warnings(statuses: tuple[IndexStatus, ...]) -> tuple[WorkflowWarningDTO, ...]:
    warnings: list[WorkflowWarningDTO] = []
    for status in statuses:
        for caveat in status.caveats:
            warnings.append(WorkflowWarningDTO(severity="warning", message=caveat))
    return tuple(warnings)


def result_card_from_similarity(
    store: SqliteStore,
    result: SimilarityResult,
    *,
    explanation: str,
) -> ResultCardData:
    title, artist = _result_title_and_artist(store, result)
    warnings = confidence_warnings(result.dimension_scores)
    return ResultCardData(
        track_title=title,
        artist=artist,
        combined_score=result.score,
        dimension_scores=result.dimension_scores,
        explanation=explanation,
        matched_entity_type=result.matched_entity_type,
        matched_range=result.matched_range,
        matched_source=result.matched_source,
        matched_stem=result.matched_stem,
        baseline_score=result.baseline_score,
        feedback_adjustment=result.feedback_adjustment,
        search_backend=result.search_backend,
        stale_index_warnings=result.retrieval_caveats,
        caveats=result.caveats,
        warnings=warnings,
    )


def _result_title_and_artist(
    store: SqliteStore, result: SimilarityResult
) -> tuple[str, str | None]:
    if result.owner_type is OwnerType.TRACK:
        try:
            track = store.get_track(result.owner_id)
        except KeyError:
            return result.owner_id, None
        return track.title or track.filepath.stem, track.artist

    track_id: str | None = None
    suffix = result.owner_id
    if result.owner_type is OwnerType.SOURCE:
        try:
            source = store.get_source(result.owner_id)
        except KeyError:
            source = None
        if source is not None:
            track_id = source.track_id
            suffix = source.source_label
    elif result.owner_type is OwnerType.STEM:
        for track in store.list_tracks():
            for stem in store.list_stems_for_track(track.id):
                if stem.id == result.owner_id:
                    track_id = track.id
                    suffix = stem.stem_type.value
                    break

    if track_id is None:
        return result.owner_id, None
    track = store.get_track(track_id)
    return f"{track.title or track.filepath.stem} / {suffix}", track.artist
