from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import soundfile as sf

from deep_sound.infra.storage.sqlite_store import SqliteStore
from deep_sound.services.library_analysis_service import AnalysisProfile
from deep_sound.ui.library_workflow import (
    AnalyzeIntentDTO,
    ClipSelectionIntentDTO,
    DesktopWorkflowController,
    FeedbackIntentDTO,
    ImportIntentDTO,
    IndexIntentDTO,
    SearchIntentDTO,
    WaveformIntentDTO,
)


def test_phase9_controller_acceptance_workflow_with_failed_import(
    tmp_path: Path,
) -> None:
    library_dir = tmp_path / "library"
    library_dir.mkdir()
    query_path = library_dir / "query.wav"
    near_path = library_dir / "near.wav"
    broken_path = library_dir / "broken.wav"
    _write_click_track(query_path, bpm=120.0)
    _write_click_track(near_path, bpm=124.0)
    broken_path.write_text("not audio", encoding="utf-8")
    original_hash = _sha256(query_path)

    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    controller = DesktopWorkflowController(store, app_data_dir=tmp_path / "app_data")

    import_job = controller.import_paths(ImportIntentDTO(paths=(library_dir,)))
    tracks = store.list_tracks()
    query_track = next(track for track in tracks if track.filepath == query_path)
    analyze_job = controller.analyze(AnalyzeIntentDTO(profile=AnalysisProfile.SEARCHABLE))
    index_job = controller.build_index(IndexIntentDTO(profile=AnalysisProfile.SEARCHABLE))
    results = controller.search(SearchIntentDTO(query_id=query_track.id, mode="rhythm"))
    waveform_job, cache = controller.build_waveform(WaveformIntentDTO(track_id=query_track.id))
    clip, clip_query = controller.create_clip_selection(
        ClipSelectionIntentDTO(
            track_id=query_track.id,
            start_sec=0.1,
            end_sec=0.8,
            label="intro",
        )
    )
    feedback_job = controller.submit_feedback(
        FeedbackIntentDTO(
            query_owner_id=query_track.id,
            result_owner_id=results[0].result_owner_id or results[0].track_title,
            value="relevant",
        )
    )
    snapshot = controller.snapshot()

    assert import_job.status == "completed"
    assert len(tracks) == 2
    assert any(
        job.status == "failed" and "broken.wav" in job.target_id for job in store.list_jobs()
    )
    assert analyze_job.status == "completed"
    assert index_job.status == "completed"
    assert results
    assert results[0].search_backend == "index"
    assert results[0].result_owner_id is not None
    assert waveform_job.status == "completed"
    assert cache.artifact_path.is_relative_to(tmp_path / "app_data")
    assert clip.id == clip_query.query_owner_id
    assert feedback_job.status == "completed"
    assert snapshot.track_count == 2
    assert snapshot.clip_count == 1
    assert _sha256(query_path) == original_hash


def _write_click_track(path: Path, *, bpm: float) -> None:
    sample_rate = 22050
    duration_sec = 3.0
    period_sec = 60.0 / bpm
    samples = np.zeros(int(sample_rate * duration_sec), dtype=np.float32)
    click_len = int(0.02 * sample_rate)
    envelope = np.exp(-np.linspace(0, 6, click_len)).astype(np.float32)
    t = 0.0
    while t < duration_sec:
        start = int(t * sample_rate)
        end = min(start + click_len, samples.shape[0])
        samples[start:end] += envelope[: end - start]
        t += period_sec
    sf.write(path, samples, sample_rate)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()
