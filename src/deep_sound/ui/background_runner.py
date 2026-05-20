"""Import-safe background runner seam for desktop controller jobs."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from importlib import import_module
from typing import Generic, Literal, TypeAlias, TypeVar

T = TypeVar("T")

JobEventKind: TypeAlias = Literal["started", "progress", "completed", "failed"]


@dataclass(frozen=True, slots=True)
class JobStartedEventDTO:
    job_id: str
    label: str
    progress: float = 0.0
    stage: str = "started"
    message: str | None = None
    kind: Literal["started"] = "started"


@dataclass(frozen=True, slots=True)
class JobProgressEventDTO:
    job_id: str
    label: str
    progress: float
    stage: str
    message: str | None = None
    kind: Literal["progress"] = "progress"


@dataclass(frozen=True, slots=True)
class JobCompletedEventDTO:
    job_id: str
    label: str
    result: object | None = None
    progress: float = 1.0
    stage: str = "completed"
    message: str | None = None
    kind: Literal["completed"] = "completed"


@dataclass(frozen=True, slots=True)
class JobFailedEventDTO:
    job_id: str
    label: str
    error_type: str
    error_message: str
    progress: float
    stage: str = "failed"
    message: str | None = None
    kind: Literal["failed"] = "failed"


ControllerJobEventDTO: TypeAlias = (
    JobStartedEventDTO | JobProgressEventDTO | JobCompletedEventDTO | JobFailedEventDTO
)
JobEventSink: TypeAlias = Callable[[ControllerJobEventDTO], None]
ControllerJobWorker: TypeAlias = Callable[["JobProgressReporter"], T]


@dataclass(frozen=True, slots=True)
class ControllerJob(Generic[T]):
    """Import-safe description of a controller job runnable by any adapter."""

    job_id: str
    label: str
    worker: ControllerJobWorker[T]


@dataclass(frozen=True, slots=True)
class JobRunResult(Generic[T]):
    job_id: str
    succeeded: bool
    events: tuple[ControllerJobEventDTO, ...]
    result: T | None = None
    error_message: str | None = None


class JobProgressReporter:
    """Worker-facing progress callback that emits DTOs without Qt coupling."""

    def __init__(
        self,
        *,
        job_id: str,
        label: str,
        emit: JobEventSink,
    ) -> None:
        self._job_id = job_id
        self._label = label
        self._emit = emit
        self._progress = 0.0

    @property
    def progress(self) -> float:
        return self._progress

    def update(
        self,
        progress: float,
        *,
        stage: str = "running",
        message: str | None = None,
    ) -> JobProgressEventDTO:
        normalized = _validate_progress(progress)
        event = JobProgressEventDTO(
            job_id=self._job_id,
            label=self._label,
            progress=normalized,
            stage=stage,
            message=message,
        )
        self._progress = normalized
        self._emit(event)
        return event


class SynchronousJobRunner:
    """Deterministic runner for tests and future UI adapters."""

    def __init__(self, *, event_sink: JobEventSink | None = None) -> None:
        self._event_sink = event_sink
        self._events: list[ControllerJobEventDTO] = []

    @property
    def events(self) -> tuple[ControllerJobEventDTO, ...]:
        return tuple(self._events)

    def run(self, job: ControllerJob[T]) -> JobRunResult[T]:
        run_events: list[ControllerJobEventDTO] = []

        def emit(event: ControllerJobEventDTO) -> None:
            run_events.append(event)
            self._events.append(event)
            if self._event_sink is not None:
                self._event_sink(event)

        emit(JobStartedEventDTO(job_id=job.job_id, label=job.label))
        reporter = JobProgressReporter(job_id=job.job_id, label=job.label, emit=emit)
        try:
            result = job.worker(reporter)
        except Exception as exc:
            failed = JobFailedEventDTO(
                job_id=job.job_id,
                label=job.label,
                error_type=type(exc).__name__,
                error_message=str(exc),
                progress=reporter.progress,
            )
            emit(failed)
            return JobRunResult(
                job_id=job.job_id,
                succeeded=False,
                events=tuple(run_events),
                error_message=failed.error_message,
            )

        emit(JobCompletedEventDTO(job_id=job.job_id, label=job.label, result=result))
        return JobRunResult(
            job_id=job.job_id,
            succeeded=True,
            events=tuple(run_events),
            result=result,
        )


def create_qt_background_runner(*, event_sink: JobEventSink | None = None) -> SynchronousJobRunner:
    """Import-gated factory for a Qt adapter without import-time PySide coupling."""

    try:
        import_module("PySide6.QtCore")
    except ImportError as exc:  # pragma: no cover - depends on optional ui extra.
        raise RuntimeError(
            "Install deep-sound with the [ui] extra to create Qt background runners."
        ) from exc
    return SynchronousJobRunner(event_sink=event_sink)


def _validate_progress(progress: float) -> float:
    normalized = float(progress)
    if not 0.0 <= normalized <= 1.0:
        raise ValueError(f"Job progress must be in [0, 1]: {progress}")
    return normalized
