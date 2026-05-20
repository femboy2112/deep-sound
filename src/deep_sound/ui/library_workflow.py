"""Import-safe controller DTOs for desktop library workflows."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar
from uuid import uuid4

from deep_sound.domain.clip import ClipWindow
from deep_sound.domain.corrections import ResultFeedbackValue
from deep_sound.domain.feature_view import FeatureType, OwnerType
from deep_sound.infra.storage.sqlite_store import JobRecord, SqliteStore
from deep_sound.services.correction_service import CorrectionService
from deep_sound.services.feature_service import FeatureService
from deep_sound.services.index_service import IndexService, IndexStatus
from deep_sound.services.library_analysis_service import AnalysisProfile, LibraryAnalysisService
from deep_sound.services.library_service import LibraryService
from deep_sound.services.similarity_service import SearchMode, SimilarityResult, SimilarityService
from deep_sound.services.waveform_service import (
    ClipWindowDTO,
    WaveformCacheDTO,
    WaveformService,
    clip_window_dto,
)
from deep_sound.ui.query_builder import IndexStatusDTO, QueryWeights
from deep_sound.ui.results_view import ResultCardData, confidence_warnings

T = TypeVar("T")


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
class WaveformIntentDTO:
    track_id: str
    point_count: int = 512


@dataclass(frozen=True, slots=True)
class ClipSelectionIntentDTO:
    track_id: str
    start_sec: float
    end_sec: float
    label: str | None = None


@dataclass(frozen=True, slots=True)
class ClipQueryMetadataDTO:
    query_owner_id: str
    query_owner_type: OwnerType
    track_id: str
    start_sec: float
    end_sec: float
    label: str | None = None


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
    track_count: int = 0
    clip_count: int = 0


class DesktopWorkflowController:
    """Thin desktop intent controller over existing services.

    The controller is intentionally import-safe for default tests. PySide widget
    modules can call into it, but no Qt objects cross this boundary.
    """

    def __init__(
        self,
        store: SqliteStore,
        *,
        app_data_dir: Path,
        active_profile: AnalysisProfile = AnalysisProfile.SEARCHABLE,
        library_service: LibraryService | None = None,
        analysis_service: LibraryAnalysisService | None = None,
        index_service: IndexService | None = None,
        similarity_service: SimilarityService | None = None,
        correction_service: CorrectionService | None = None,
        waveform_service: WaveformService | None = None,
    ) -> None:
        self._store = store
        self._app_data_dir = app_data_dir
        self._active_profile = active_profile
        self._library = library_service or LibraryService(store)
        self._analysis = analysis_service or LibraryAnalysisService(
            store,
            app_data_dir=app_data_dir,
        )
        self._index = index_service or IndexService(
            store,
            index_root=app_data_dir / "indexes",
        )
        self._corrections = correction_service or CorrectionService(store)
        self._similarity = similarity_service or SimilarityService(
            FeatureService(store, correction_service=self._corrections),
            correction_service=self._corrections,
            index_service=self._index,
        )
        self._waveforms = waveform_service or WaveformService(app_data_dir)

    @property
    def active_profile(self) -> AnalysisProfile:
        return self._active_profile

    def set_active_profile(self, profile: AnalysisProfile | str) -> AnalysisProfile:
        self._active_profile = AnalysisProfile(profile)
        return self._active_profile

    def import_paths(self, intent: ImportIntentDTO) -> WorkflowJobDTO:
        def worker() -> int:
            imported_count = 0
            for path in intent.paths:
                if path.expanduser().is_dir():
                    imported_count += len(
                        self._library.import_folder(path, recursive=intent.recursive)
                    )
                else:
                    self._library.import_file(path)
                    imported_count += 1
            return imported_count

        job = self._run_store_job(
            job_type="desktop_import",
            target_type="library",
            target_id="library",
            worker=worker,
        )
        return job_dto(job)

    def analyze(self, intent: AnalyzeIntentDTO) -> WorkflowJobDTO:
        self.set_active_profile(intent.profile)

        def worker() -> int:
            summary = self._analysis.analyze_library(profile=self._active_profile)
            if summary.failed_count:
                raise RuntimeError(
                    f"{summary.failed_count} track(s) failed during {self._active_profile.value}"
                )
            return summary.completed_count

        job = self._run_store_job(
            job_type=f"desktop_analyze_{self._active_profile.value}",
            target_type="library",
            target_id="library",
            worker=worker,
        )
        return job_dto(job)

    def build_index(self, intent: IndexIntentDTO) -> WorkflowJobDTO:
        self.set_active_profile(intent.profile)

        def worker() -> int:
            return len(self._index.build_profile(self._active_profile))

        job = self._run_store_job(
            job_type=f"desktop_index_{self._active_profile.value}",
            target_type="library",
            target_id="library",
            worker=worker,
        )
        return job_dto(job)

    def build_waveform(self, intent: WaveformIntentDTO) -> tuple[WorkflowJobDTO, WaveformCacheDTO]:
        cache: WaveformCacheDTO | None = None

        def worker() -> int:
            nonlocal cache
            cache = self._waveforms.build_cache(
                self._store.get_track(intent.track_id),
                point_count=intent.point_count,
            )
            return len(cache.points)

        job = self._run_store_job(
            job_type="desktop_waveform",
            target_type="track",
            target_id=intent.track_id,
            worker=worker,
        )
        if cache is None:
            raise RuntimeError("Waveform cache was not produced")
        return job_dto(job), cache

    def create_clip_selection(
        self,
        intent: ClipSelectionIntentDTO,
    ) -> tuple[ClipWindowDTO, ClipQueryMetadataDTO]:
        clip = self._store.add_clip_window(
            ClipWindow(
                id=str(uuid4()),
                track_id=intent.track_id,
                start_sec=intent.start_sec,
                end_sec=intent.end_sec,
                label=intent.label,
            )
        )
        return clip_window_dto(clip), ClipQueryMetadataDTO(
            query_owner_id=clip.id,
            query_owner_type=OwnerType.CLIP,
            track_id=clip.track_id,
            start_sec=clip.start_sec,
            end_sec=clip.end_sec,
            label=clip.label,
        )

    def search(
        self,
        intent: SearchIntentDTO,
        *,
        weights: QueryWeights | None = None,
    ) -> tuple[ResultCardData, ...]:
        mode = SearchMode(intent.mode)
        resolved_weights = _weights_for_search_mode(mode, weights or QueryWeights())
        owner_type = OwnerType.SOURCE if mode in _SOURCE_SEARCH_MODES else None
        results = self._similarity.search(
            query_id=intent.query_id,
            weights=resolved_weights,
            top_k=intent.top_k,
            owner_type=owner_type,
        )
        return tuple(
            _result_card_with_query(
                self._store,
                result,
                query_owner_id=intent.query_id,
                explanation=_desktop_result_explanation(result),
            )
            for result in results
        )

    def submit_feedback(self, intent: FeedbackIntentDTO) -> WorkflowJobDTO:
        def worker() -> int:
            self._corrections.add_result_feedback(
                query_owner_id=intent.query_owner_id,
                result_owner_id=intent.result_owner_id,
                feedback=intent.value,
            )
            return 1

        job = self._run_store_job(
            job_type="desktop_feedback",
            target_type="query",
            target_id=intent.query_owner_id,
            worker=worker,
        )
        return job_dto(job)

    def snapshot(self) -> WorkflowSnapshotDTO:
        statuses = tuple(
            self._index.status(feature_type, owner_type=owner_type)
            for owner_type, feature_type in self._profile_features()
        )
        tracks = self._store.list_tracks()
        return WorkflowSnapshotDTO(
            active_profile=self._active_profile,
            jobs=tuple(job_dto(job) for job in self._store.list_jobs()),
            index_statuses=tuple(index_status_dto(status) for status in statuses),
            warnings=stale_index_warnings(statuses),
            track_count=len(tracks),
            clip_count=sum(
                len(self._store.list_clip_windows_for_track(track.id)) for track in tracks
            ),
        )

    def _run_store_job(
        self,
        *,
        job_type: str,
        target_type: str,
        target_id: str,
        worker: Callable[[], T],
    ) -> JobRecord:
        job = self._store.create_job(
            job_type=job_type,
            target_type=target_type,
            target_id=target_id,
            status="queued",
            progress=0.0,
        )
        self._store.update_job(job.id, status="running", progress=0.05)
        try:
            worker()
        except Exception as exc:
            return self._store.update_job(
                job.id,
                status="failed",
                progress=1.0,
                error_message=str(exc),
            )
        return self._store.update_job(job.id, status="completed", progress=1.0)

    def _profile_features(self) -> tuple[tuple[OwnerType, FeatureType], ...]:
        from deep_sound.services.index_service import INDEX_PROFILE_FEATURES

        return INDEX_PROFILE_FEATURES[self._active_profile]


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
        result_owner_id=result.owner_id,
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


def _result_card_with_query(
    store: SqliteStore,
    result: SimilarityResult,
    *,
    query_owner_id: str,
    explanation: str,
) -> ResultCardData:
    card = result_card_from_similarity(store, result, explanation=explanation)
    return ResultCardData(
        track_title=card.track_title,
        artist=card.artist,
        combined_score=card.combined_score,
        dimension_scores=card.dimension_scores,
        explanation=card.explanation,
        query_owner_id=query_owner_id,
        result_owner_id=card.result_owner_id,
        matched_entity_type=card.matched_entity_type,
        matched_range=card.matched_range,
        matched_source=card.matched_source,
        matched_stem=card.matched_stem,
        baseline_score=card.baseline_score,
        feedback_adjustment=card.feedback_adjustment,
        search_backend=card.search_backend,
        stale_index_warnings=card.stale_index_warnings,
        caveats=card.caveats,
        warnings=card.warnings,
    )


_SOURCE_SEARCH_MODES = {
    SearchMode.SOURCE_CHORDS,
    SearchMode.CHORD_CHANGE,
    SearchMode.MELODY,
    SearchMode.VOCAL_TIMBRE,
    SearchMode.SOURCE_ROLE,
}


def _weights_for_search_mode(mode: SearchMode, weights: QueryWeights) -> dict[str, float]:
    if mode is SearchMode.WEIGHTED:
        return weights.normalized_phase5_weights()
    return {mode.value: 1.0}


def _desktop_result_explanation(result: SimilarityResult) -> str:
    backend = result.search_backend
    entity = result.matched_entity_type or result.owner_type.value
    return (
        f"Probabilistic {entity} similarity result using {backend} retrieval; "
        "review caveats and confidence scores before treating it as a match."
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
