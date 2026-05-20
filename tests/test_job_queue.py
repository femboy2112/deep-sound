"""Tests for Phase 1 in-memory job queue primitives."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from deep_sound.infra.job_queue import (
    JobCancelled,
    JobContext,
    JobQueue,
    JobState,
    JobTargetType,
    JobType,
)


class SequenceFactory:
    def __init__(self, values: list[str]) -> None:
        self._values = values
        self._index = 0

    def __call__(self) -> str:
        value = self._values[self._index]
        self._index += 1
        return value


class Clock:
    def __init__(self) -> None:
        self._now = datetime(2026, 5, 19, tzinfo=UTC)

    def __call__(self) -> datetime:
        value = self._now
        self._now = self._now + timedelta(seconds=1)
        return value


def _queue() -> JobQueue:
    return JobQueue(id_factory=SequenceFactory(["job-1", "job-2", "job-3"]), clock=Clock())


def test_submit_records_typed_queued_job() -> None:
    queue = _queue()

    job = queue.submit(
        JobType.ANALYZE_FULL_MIX,
        JobTargetType.TRACK,
        "track-1",
        parameters={"priority": 1, "force": False},
    )

    assert job.id == "job-1"
    assert job.job_type is JobType.ANALYZE_FULL_MIX
    assert job.target_type is JobTargetType.TRACK
    assert job.state is JobState.QUEUED
    assert job.progress == 0.0
    assert job.parameters == {"priority": 1, "force": False}
    assert queue.list_jobs() == [job]


def test_run_next_executes_fifo_and_records_progress_and_result() -> None:
    queue = _queue()
    first = queue.submit(JobType.ANALYZE_FULL_MIX, JobTargetType.TRACK, "track-1")
    second = queue.submit(JobType.BUILD_INDEX, JobTargetType.FEATURE_TYPE, "rhythm.global")
    seen: list[str] = []

    def worker(context: JobContext) -> dict[str, str]:
        seen.append(context.job.id)
        updated = context.update_progress(0.5)
        assert updated.state is JobState.RUNNING
        return {"job": context.job.id}

    completed = queue.run_next(worker)

    assert completed is not None
    assert completed.id == first.id
    assert completed.state is JobState.COMPLETED
    assert completed.progress == 1.0
    assert completed.result == {"job": "job-1"}
    assert completed.started_at is not None
    assert completed.finished_at is not None
    assert seen == ["job-1"]
    assert queue.next_queued() == second


def test_worker_exception_records_structured_error_and_leaves_next_job_queued() -> None:
    queue = _queue()
    failed = queue.submit(JobType.SEPARATE_STEMS, JobTargetType.TRACK, "track-1")
    waiting = queue.submit(JobType.BUILD_INDEX, JobTargetType.LIBRARY, "library")

    def worker(context: JobContext) -> dict[str, str]:
        context.update_progress(0.25)
        raise RuntimeError("decoder unavailable")

    result = queue.run_next(worker)

    assert result is not None
    assert result.id == failed.id
    assert result.state is JobState.FAILED
    assert result.progress == 0.25
    assert result.error is not None
    assert result.error.code == "RuntimeError"
    assert result.error.message == "decoder unavailable"
    assert result.error.retryable is False
    assert queue.next_queued() == waiting


def test_cancel_marks_queued_job_without_running_it() -> None:
    queue = _queue()
    job = queue.submit(JobType.IMPORT_TRACK, JobTargetType.TRACK, "track-1")

    canceled = queue.cancel(job.id)

    assert canceled.state is JobState.CANCELED
    assert canceled.cancellation_requested is True
    assert canceled.finished_at is not None
    assert queue.run_next(lambda context: {"unexpected": context.job.id}) is None


def test_running_cancellation_is_cooperative_and_finishes_canceled() -> None:
    queue = _queue()
    job = queue.submit(JobType.ANALYZE_STEM, JobTargetType.STEM, "stem-1")

    def worker(context: JobContext) -> dict[str, str]:
        context.update_progress(0.4)
        marked = queue.cancel(context.job.id)
        assert marked.id == job.id
        assert marked.state is JobState.RUNNING
        assert marked.cancellation_requested is True
        with pytest.raises(JobCancelled):
            context.check_canceled()
        raise JobCancelled("stopped")

    result = queue.run_next(worker)

    assert result is not None
    assert result.id == job.id
    assert result.state is JobState.CANCELED
    assert result.progress == 0.4
    assert result.cancellation_requested is True
    assert result.finished_at is not None


def test_rejects_invalid_progress_updates() -> None:
    queue = _queue()
    job = queue.submit(JobType.ANALYZE_SOURCE, JobTargetType.SOURCE, "source-1")

    def worker(context: JobContext) -> dict[str, str]:
        with pytest.raises(ValueError):
            context.update_progress(1.01)
        return {"job": context.job.id}

    completed = queue.run_next(worker)

    assert completed is not None
    assert completed.id == job.id
    assert completed.state is JobState.COMPLETED
