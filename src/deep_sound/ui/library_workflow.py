"""Import-safe controller DTOs for desktop library workflows."""

from __future__ import annotations

from collections.abc import Callable, Mapping
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
StageReporter = Callable[[str], JobRecord]


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
    stage: str = "queued"
    stage_label: str = "Queued"
    progress_label: str = "0%"
    retry_action: WorkflowRetryActionDTO | None = None


@dataclass(frozen=True, slots=True)
class WorkflowRetryActionDTO:
    controller_method: str
    label: str
    intent_type: str
    target_id: str


@dataclass(frozen=True, slots=True)
class WorkflowProgressStageDTO:
    stage: str
    label: str
    progress: float


_IMPORT_PROGRESS: dict[str, WorkflowProgressStageDTO] = {
    "scanning": WorkflowProgressStageDTO("scanning", "Scanning import paths", 0.10),
    "importing": WorkflowProgressStageDTO("importing", "Importing audio", 0.45),
    "finalizing": WorkflowProgressStageDTO("finalizing", "Finalizing library", 0.90),
}
_ANALYZE_PROGRESS: dict[str, WorkflowProgressStageDTO] = {
    "preparing": WorkflowProgressStageDTO("preparing", "Preparing analysis", 0.10),
    "analyzing": WorkflowProgressStageDTO("analyzing", "Analyzing library", 0.55),
    "summarizing": WorkflowProgressStageDTO("summarizing", "Summarizing results", 0.90),
}
_INDEX_PROGRESS: dict[str, WorkflowProgressStageDTO] = {
    "preparing": WorkflowProgressStageDTO("preparing", "Preparing indexes", 0.10),
    "indexing": WorkflowProgressStageDTO("indexing", "Building indexes", 0.60),
    "validating": WorkflowProgressStageDTO("validating", "Validating indexes", 0.90),
}
_WAVEFORM_PROGRESS: dict[str, WorkflowProgressStageDTO] = {
    "loading": WorkflowProgressStageDTO("loading", "Loading audio", 0.20),
    "summarizing": WorkflowProgressStageDTO("summarizing", "Summarizing waveform", 0.70),
    "caching": WorkflowProgressStageDTO("caching", "Caching waveform", 0.90),
}
_FEEDBACK_PROGRESS: dict[str, WorkflowProgressStageDTO] = {
    "recording": WorkflowProgressStageDTO("recording", "Recording feedback", 0.75),
}


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
        def worker(report: StageReporter) -> int:
            imported_count = 0
            report("scanning")
            for path in intent.paths:
                report("importing")
                if path.expanduser().is_dir():
                    imported_count += len(
                        self._library.import_folder(path, recursive=intent.recursive)
                    )
                else:
                    self._library.import_file(path)
                    imported_count += 1
            report("finalizing")
            return imported_count

        job = self._run_store_job(
            job_type="desktop_import",
            target_type="library",
            target_id="library",
            progress_plan=_IMPORT_PROGRESS,
            worker=worker,
        )
        return job_dto(job)

    def retry_import_paths(self, intent: ImportIntentDTO) -> WorkflowJobDTO:
        return self.import_paths(intent)

    def analyze(self, intent: AnalyzeIntentDTO) -> WorkflowJobDTO:
        self.set_active_profile(intent.profile)

        def worker(report: StageReporter) -> int:
            report("preparing")
            report("analyzing")
            summary = self._analysis.analyze_library(profile=self._active_profile)
            report("summarizing")
            if summary.failed_count:
                raise RuntimeError(
                    f"{summary.failed_count} track(s) failed during {self._active_profile.value}"
                )
            return summary.completed_count

        job = self._run_store_job(
            job_type=f"desktop_analyze_{self._active_profile.value}",
            target_type="library",
            target_id="library",
            progress_plan=_ANALYZE_PROGRESS,
            worker=worker,
        )
        return job_dto(job)

    def retry_analyze(self, intent: AnalyzeIntentDTO) -> WorkflowJobDTO:
        return self.analyze(intent)

    def build_index(self, intent: IndexIntentDTO) -> WorkflowJobDTO:
        self.set_active_profile(intent.profile)

        def worker(report: StageReporter) -> int:
            report("preparing")
            report("indexing")
            count = len(self._index.build_profile(self._active_profile))
            report("validating")
            return count

        job = self._run_store_job(
            job_type=f"desktop_index_{self._active_profile.value}",
            target_type="library",
            target_id="library",
            progress_plan=_INDEX_PROGRESS,
            worker=worker,
        )
        return job_dto(job)

    def retry_build_index(self, intent: IndexIntentDTO) -> WorkflowJobDTO:
        return self.build_index(intent)

    def build_waveform(self, intent: WaveformIntentDTO) -> tuple[WorkflowJobDTO, WaveformCacheDTO]:
        cache: WaveformCacheDTO | None = None

        def worker(report: StageReporter) -> int:
            nonlocal cache
            report("loading")
            cache = self._waveforms.build_cache(
                self._store.get_track(intent.track_id),
                point_count=intent.point_count,
            )
            report("summarizing")
            report("caching")
            return len(cache.points)

        job = self._run_store_job(
            job_type="desktop_waveform",
            target_type="track",
            target_id=intent.track_id,
            progress_plan=_WAVEFORM_PROGRESS,
            worker=worker,
        )
        if cache is None:
            raise RuntimeError("Waveform cache was not produced")
        return job_dto(job), cache

    def retry_build_waveform(
        self, intent: WaveformIntentDTO
    ) -> tuple[WorkflowJobDTO, WaveformCacheDTO]:
        return self.build_waveform(intent)

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
        def worker(report: StageReporter) -> int:
            report("recording")
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
            progress_plan=_FEEDBACK_PROGRESS,
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
        progress_plan: Mapping[str, WorkflowProgressStageDTO],
        worker: Callable[[StageReporter], T],
    ) -> JobRecord:
        job = self._store.create_job(
            job_type=job_type,
            target_type=target_type,
            target_id=target_id,
            status="queued",
            progress=0.0,
        )
        current_job = job

        def report(stage: str) -> JobRecord:
            nonlocal current_job
            progress_stage = progress_plan[stage]
            progress = max(current_job.progress, progress_stage.progress)
            current_job = self._store.update_job(
                job.id,
                status="running",
                progress=progress,
            )
            return current_job

        try:
            worker(report)
        except Exception as exc:
            return self._store.update_job(
                job.id,
                status="failed",
                progress=current_job.progress,
                error_message=str(exc),
            )
        return self._store.update_job(job.id, status="completed", progress=1.0)

    def _profile_features(self) -> tuple[tuple[OwnerType, FeatureType], ...]:
        from deep_sound.services.index_service import INDEX_PROFILE_FEATURES

        return INDEX_PROFILE_FEATURES[self._active_profile]


def job_dto(job: JobRecord) -> WorkflowJobDTO:
    stage = _stage_for_job(job)
    retry_action = _retry_action_for_job(job)
    return WorkflowJobDTO(
        job_id=job.id,
        job_type=job.job_type,
        target_type=job.target_type,
        target_id=job.target_id,
        status=job.status,
        progress=job.progress,
        error_message=job.error_message,
        retry_enabled=retry_action is not None,
        stage=stage.stage,
        stage_label=stage.label,
        progress_label=f"{job.progress:.0%}",
        retry_action=retry_action,
    )


def _stage_for_job(job: JobRecord) -> WorkflowProgressStageDTO:
    if job.status == "queued":
        return WorkflowProgressStageDTO("queued", "Queued", 0.0)
    if job.status == "completed":
        return WorkflowProgressStageDTO("completed", "Completed", 1.0)
    if job.status == "failed":
        return WorkflowProgressStageDTO("failed", "Failed", job.progress)

    progress_plan = _progress_plan_for_job_type(job.job_type)
    stage = WorkflowProgressStageDTO("running", "Running", job.progress)
    for candidate in sorted(progress_plan.values(), key=lambda item: item.progress):
        if job.progress >= candidate.progress:
            stage = candidate
    return stage


def _progress_plan_for_job_type(job_type: str) -> Mapping[str, WorkflowProgressStageDTO]:
    if job_type == "desktop_import":
        return _IMPORT_PROGRESS
    if job_type.startswith("desktop_analyze_") or job_type.startswith("analyze_"):
        return _ANALYZE_PROGRESS
    if job_type.startswith("desktop_index_") or job_type == "build_index":
        return _INDEX_PROGRESS
    if job_type == "desktop_waveform":
        return _WAVEFORM_PROGRESS
    if job_type == "desktop_feedback":
        return _FEEDBACK_PROGRESS
    return {}


def _retry_action_for_job(job: JobRecord) -> WorkflowRetryActionDTO | None:
    if job.status != "failed":
        return None
    if job.job_type == "desktop_import":
        return WorkflowRetryActionDTO(
            controller_method="retry_import_paths",
            label="Retry import",
            intent_type="ImportIntentDTO",
            target_id=job.target_id,
        )
    if job.job_type.startswith("desktop_analyze_") or job.job_type.startswith("analyze_"):
        return WorkflowRetryActionDTO(
            controller_method="retry_analyze",
            label="Retry analysis",
            intent_type="AnalyzeIntentDTO",
            target_id=job.target_id,
        )
    if job.job_type.startswith("desktop_index_") or job.job_type == "build_index":
        return WorkflowRetryActionDTO(
            controller_method="retry_build_index",
            label="Retry index",
            intent_type="IndexIntentDTO",
            target_id=job.target_id,
        )
    if job.job_type == "desktop_waveform":
        return WorkflowRetryActionDTO(
            controller_method="retry_build_waveform",
            label="Retry waveform",
            intent_type="WaveformIntentDTO",
            target_id=job.target_id,
        )
    return None


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
