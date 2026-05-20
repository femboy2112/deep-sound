from __future__ import annotations

from deep_sound.infra.job_queue import JobQueue, JobType, submit_build_index_job


def test_submit_build_index_job_records_resumable_target_metadata() -> None:
    queue = JobQueue(id_factory=lambda: "job-1")

    job = submit_build_index_job(
        queue,
        feature_type="rhythm.global",
        owner_type="track",
        target_id="library",
    )

    assert job.job_type is JobType.BUILD_INDEX
    assert job.parameters == {"feature_type": "rhythm.global", "owner_type": "track"}
    assert queue.next_queued() == job
