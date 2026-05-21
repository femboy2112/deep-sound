from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import soundfile as sf

from deep_sound.domain.feature_view import FeatureType, OwnerType
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


def test_phase11_live_searchable_workflow_covers_import_search_clip_feedback(
    tmp_path: Path,
) -> None:
    library_dir = tmp_path / "live-library"
    library_dir.mkdir()
    query_path = library_dir / "query_120bpm.wav"
    near_path = library_dir / "near_124bpm.wav"
    broken_path = library_dir / "broken.wav"
    _write_click_track(query_path, bpm=120.0)
    _write_click_track(near_path, bpm=124.0)
    broken_path.write_text("not audio", encoding="utf-8")
    original_hashes = {query_path: _sha256(query_path), near_path: _sha256(near_path)}

    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    app_data_dir = tmp_path / "app_data"
    controller = DesktopWorkflowController(store, app_data_dir=app_data_dir)

    import_job = controller.import_paths(ImportIntentDTO(paths=(library_dir,)))
    tracks = store.list_tracks()
    query_track = next(track for track in tracks if track.filepath == query_path)
    analyze_job = controller.analyze(AnalyzeIntentDTO(profile=AnalysisProfile.SEARCHABLE))
    index_job = controller.build_index(IndexIntentDTO(profile=AnalysisProfile.SEARCHABLE))
    results = controller.search(SearchIntentDTO(query_id=query_track.id, mode="rhythm"))
    waveform_job, waveform = controller.build_waveform(WaveformIntentDTO(track_id=query_track.id))
    clip, clip_query = controller.create_clip_selection(
        ClipSelectionIntentDTO(
            track_id=query_track.id,
            start_sec=0.25,
            end_sec=1.25,
            label="live-hook",
        )
    )
    feedback_job = controller.submit_feedback(
        FeedbackIntentDTO(
            query_owner_id=clip_query.query_owner_id,
            result_owner_id=results[0].result_owner_id or results[0].track_title,
            value="relevant",
        )
    )
    snapshot = controller.snapshot()

    assert import_job.status == "completed"
    assert {track.filepath for track in tracks} == {query_path, near_path}
    assert any(
        job.status == "failed" and "broken.wav" in job.target_id for job in store.list_jobs()
    )
    assert analyze_job.status == "completed"
    assert index_job.status == "completed"
    assert results
    assert results[0].search_backend == "index"
    assert results[0].matched_entity_type == "track"
    assert "rhythm.global" in results[0].dimension_scores
    assert waveform_job.status == "completed"
    assert waveform.artifact_path.is_relative_to(app_data_dir)
    assert len(waveform.points) <= 512
    assert waveform.points
    assert clip.id == clip_query.query_owner_id
    assert clip_query.track_id == query_track.id
    assert feedback_job.status == "completed"
    assert snapshot.active_profile is AnalysisProfile.SEARCHABLE
    assert snapshot.track_count == 2
    assert snapshot.clip_count == 1
    assert all(_sha256(path) == digest for path, digest in original_hashes.items())

    feature_views = [
        feature for track in tracks for feature in store.list_feature_views_for_owner(track.id)
    ]
    assert {(feature.owner_type, feature.feature_type) for feature in feature_views} >= {
        (OwnerType.TRACK, FeatureType.RHYTHM_GLOBAL),
        (OwnerType.TRACK, FeatureType.PRODUCTION_TEXTURE),
        (OwnerType.TRACK, FeatureType.STRUCTURE_SECTION_SEQUENCE),
    }
    assert all(
        feature.confidence is None or 0.0 <= feature.confidence.value <= 1.0
        for feature in feature_views
    )


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
