from __future__ import annotations

import importlib
import sys

from deep_sound.ui.background_runner import (
    ControllerJob,
    ControllerJobEventDTO,
    JobCompletedEventDTO,
    JobFailedEventDTO,
    JobProgressReporter,
    SynchronousJobRunner,
)


def test_synchronous_runner_emits_success_event_sequence() -> None:
    observed: list[ControllerJobEventDTO] = []
    runner = SynchronousJobRunner(event_sink=observed.append)

    def worker(progress: JobProgressReporter) -> str:
        progress.update(0.25, stage="decode", message="decoded")
        progress.update(0.75, stage="analyze")
        return "done"

    result = runner.run(ControllerJob(job_id="job-1", label="Analyze track", worker=worker))

    assert result.succeeded is True
    assert result.result == "done"
    assert [event.kind for event in result.events] == [
        "started",
        "progress",
        "progress",
        "completed",
    ]
    assert observed == list(result.events)
    assert runner.events == result.events
    completed = result.events[-1]
    assert isinstance(completed, JobCompletedEventDTO)
    assert completed.result == "done"
    assert completed.progress == 1.0


def test_synchronous_runner_emits_failed_event_sequence() -> None:
    runner = SynchronousJobRunner()

    def worker(progress: JobProgressReporter) -> str:
        progress.update(0.4, stage="decode")
        raise ValueError("decode failed")

    result = runner.run(ControllerJob(job_id="job-2", label="Import file", worker=worker))

    assert result.succeeded is False
    assert result.result is None
    assert result.error_message == "decode failed"
    assert [event.kind for event in result.events] == ["started", "progress", "failed"]
    failed = result.events[-1]
    assert isinstance(failed, JobFailedEventDTO)
    assert failed.error_type == "ValueError"
    assert failed.error_message == "decode failed"
    assert failed.progress == 0.4


def test_background_runner_import_does_not_load_pyside() -> None:
    for module_name in tuple(sys.modules):
        if module_name == "PySide6" or module_name.startswith("PySide6."):
            del sys.modules[module_name]

    importlib.import_module("deep_sound.ui.background_runner")

    assert "PySide6" not in sys.modules
    assert not any(module_name.startswith("PySide6.") for module_name in sys.modules)
