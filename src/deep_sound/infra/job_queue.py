"""In-memory background job queue primitives. Spec §10.3, §18.1."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from enum import StrEnum
from typing import TypeAlias
from uuid import uuid4

JsonScalar: TypeAlias = None | bool | int | float | str
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
JobWorker: TypeAlias = Callable[["JobContext"], JsonValue]


class JobState(StrEnum):
    """Lifecycle states from spec §18.1."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class JobType(StrEnum):
    """Known analysis job types from spec §18."""

    IMPORT_TRACK = "import_track"
    DECODE_TRACK = "decode_track"
    BUILD_WAVEFORM = "build_waveform"
    ANALYZE_FULL_MIX = "analyze_full_mix"
    SEGMENT_TRACK = "segment_track"
    SEPARATE_STEMS = "separate_stems"
    ANALYZE_STEM = "analyze_stem"
    DISCOVER_SOURCES = "discover_sources"
    ANALYZE_SOURCE = "analyze_source"
    INFER_CHORDS = "infer_chords"
    TRANSCRIBE_NOTES = "transcribe_notes"
    BUILD_INDEX = "build_index"
    SEARCH = "search"


class JobTargetType(StrEnum):
    """Entities that a job can operate on."""

    TRACK = "track"
    SECTION = "section"
    STEM = "stem"
    SOURCE = "source"
    LIBRARY = "library"
    FEATURE_TYPE = "feature_type"
    QUERY = "query"


class JobCancelled(RuntimeError):
    """Raised by cooperative workers after cancellation has been requested."""


@dataclass(frozen=True, slots=True)
class JobError:
    """Structured failure details suitable for storage or UI presentation."""

    code: str
    message: str
    retryable: bool = False
    details: dict[str, JsonValue] = field(default_factory=dict)

    @classmethod
    def from_exception(cls, exc: Exception, retryable: bool = False) -> JobError:
        return cls(code=type(exc).__name__, message=str(exc), retryable=retryable)


@dataclass(frozen=True, slots=True)
class JobRecord:
    """A typed job row matching the spec's persisted job model."""

    id: str
    job_type: JobType
    target_type: JobTargetType
    target_id: str
    state: JobState
    progress: float
    created_at: datetime
    updated_at: datetime
    parameters: dict[str, JsonValue] = field(default_factory=dict)
    result: JsonValue = None
    error: JobError | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    cancellation_requested: bool = False


class JobContext:
    """Worker-facing handle for progress updates and cooperative cancellation."""

    def __init__(self, queue: JobQueue, job_id: str) -> None:
        self._queue = queue
        self._job_id = job_id

    @property
    def job(self) -> JobRecord:
        return self._queue.get(self._job_id)

    def update_progress(self, progress: float) -> JobRecord:
        return self._queue.update_progress(self._job_id, progress)

    def cancellation_requested(self) -> bool:
        return self.job.cancellation_requested

    def check_canceled(self) -> None:
        if self.cancellation_requested():
            raise JobCancelled(f"Job canceled: {self._job_id}")


class JobQueue:
    """Small in-memory FIFO queue with deterministic synchronous execution."""

    def __init__(
        self,
        *,
        id_factory: Callable[[], str] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._id_factory = id_factory or (lambda: str(uuid4()))
        self._clock = clock or (lambda: datetime.now(UTC))
        self._jobs: dict[str, JobRecord] = {}
        self._order: list[str] = []

    def submit(
        self,
        job_type: JobType,
        target_type: JobTargetType,
        target_id: str,
        *,
        parameters: Mapping[str, JsonValue] | None = None,
    ) -> JobRecord:
        job_id = self._id_factory()
        if not job_id:
            raise ValueError("Job id must not be empty")
        if job_id in self._jobs:
            raise ValueError(f"Job already exists: {job_id}")
        if not target_id:
            raise ValueError("Job target_id must not be empty")

        now = self._now()
        job = JobRecord(
            id=job_id,
            job_type=job_type,
            target_type=target_type,
            target_id=target_id,
            state=JobState.QUEUED,
            progress=0.0,
            created_at=now,
            updated_at=now,
            parameters=dict(parameters or {}),
        )
        self._jobs[job.id] = job
        self._order.append(job.id)
        return job

    def get(self, job_id: str) -> JobRecord:
        try:
            return self._jobs[job_id]
        except KeyError as exc:
            raise KeyError(f"Job not found: {job_id}") from exc

    def list_jobs(self, state: JobState | None = None) -> list[JobRecord]:
        jobs = [self._jobs[job_id] for job_id in self._order]
        if state is None:
            return jobs
        return [job for job in jobs if job.state is state]

    def next_queued(self) -> JobRecord | None:
        for job in self.list_jobs(JobState.QUEUED):
            return job
        return None

    def update_progress(self, job_id: str, progress: float) -> JobRecord:
        self._validate_progress(progress)
        job = self.get(job_id)
        if job.state is not JobState.RUNNING:
            raise ValueError(f"Cannot update progress for {job.state.value} job: {job_id}")
        return self._store(replace(job, progress=progress, updated_at=self._now()))

    def cancel(self, job_id: str) -> JobRecord:
        job = self.get(job_id)
        if job.state is JobState.QUEUED:
            now = self._now()
            return self._store(
                replace(
                    job,
                    state=JobState.CANCELED,
                    cancellation_requested=True,
                    updated_at=now,
                    finished_at=now,
                )
            )
        if job.state is JobState.RUNNING:
            return self._store(replace(job, cancellation_requested=True, updated_at=self._now()))
        return job

    def run_next(self, worker: JobWorker) -> JobRecord | None:
        queued = self.next_queued()
        if queued is None:
            return None

        now = self._now()
        running = self._store(
            replace(
                queued,
                state=JobState.RUNNING,
                updated_at=now,
                started_at=now,
                error=None,
            )
        )
        context = JobContext(self, running.id)

        try:
            context.check_canceled()
            result = worker(context)
        except JobCancelled:
            return self._finish_canceled(running.id)
        except Exception as exc:
            return self._finish_failed(running.id, JobError.from_exception(exc))

        latest = self.get(running.id)
        if latest.cancellation_requested:
            return self._finish_canceled(running.id)
        return self._finish_completed(running.id, result)

    def _finish_completed(self, job_id: str, result: JsonValue) -> JobRecord:
        job = self.get(job_id)
        if job.state is not JobState.RUNNING:
            raise ValueError(f"Cannot complete {job.state.value} job: {job_id}")
        now = self._now()
        return self._store(
            replace(
                job,
                state=JobState.COMPLETED,
                progress=1.0,
                result=result,
                updated_at=now,
                finished_at=now,
            )
        )

    def _finish_failed(self, job_id: str, error: JobError) -> JobRecord:
        job = self.get(job_id)
        now = self._now()
        return self._store(
            replace(
                job,
                state=JobState.FAILED,
                error=error,
                updated_at=now,
                finished_at=now,
            )
        )

    def _finish_canceled(self, job_id: str) -> JobRecord:
        job = self.get(job_id)
        now = self._now()
        return self._store(
            replace(
                job,
                state=JobState.CANCELED,
                cancellation_requested=True,
                updated_at=now,
                finished_at=now,
            )
        )

    def _store(self, job: JobRecord) -> JobRecord:
        self._validate_progress(job.progress)
        self._jobs[job.id] = job
        return job

    def _now(self) -> datetime:
        return self._clock()

    def _validate_progress(self, progress: float) -> None:
        if not 0.0 <= progress <= 1.0:
            raise ValueError(f"Job progress must be in [0, 1]: {progress}")


def submit_build_index_job(
    queue: JobQueue,
    *,
    feature_type: str,
    owner_type: str = "track",
    target_id: str = "library",
) -> JobRecord:
    """Queue a resumable index-build job with feature/owner metadata."""
    return queue.submit(
        JobType.BUILD_INDEX,
        JobTargetType.LIBRARY,
        target_id,
        parameters={"feature_type": feature_type, "owner_type": owner_type},
    )
