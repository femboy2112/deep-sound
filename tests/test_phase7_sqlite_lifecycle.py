from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from deep_sound.domain.confidence import Confidence
from deep_sound.domain.feature_view import FeatureType, FeatureView, OwnerType
from deep_sound.domain.track import Track
from deep_sound.infra.storage.sqlite_store import SqliteStore


def _view(
    view_id: str,
    *,
    owner_id: str = "track-1",
    feature_type: FeatureType = FeatureType.RHYTHM_GLOBAL,
    value: float = 1.0,
) -> FeatureView:
    return FeatureView(
        id=view_id,
        owner_type=OwnerType.TRACK,
        owner_id=owner_id,
        feature_type=feature_type,
        algorithm="test",
        algorithm_version="1",
        params_hash="params",
        stats={"value": value},
        confidence=Confidence(0.8),
    )


def test_upsert_feature_view_replaces_same_id(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    original = _view("track-1:rhythm.global", value=1.0)
    replacement = replace(original, stats={"value": 2.0})

    store.upsert_feature_view(original)
    saved = store.upsert_feature_view(replacement)

    assert saved.stats == {"value": 2.0}
    assert store.list_feature_views_for_owner("track-1") == [replacement]


def test_replace_feature_view_for_owner_removes_duplicate_family_rows(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    store.add_feature_view(_view("legacy-1", value=1.0))
    store.add_feature_view(_view("legacy-2", value=2.0))

    canonical = _view("track-1:rhythm.global", value=3.0)
    saved = store.replace_feature_view_for_owner(canonical)

    assert saved == canonical
    assert store.get_feature_view_for_owner("track-1", FeatureType.RHYTHM_GLOBAL) == canonical
    assert store.list_feature_views_for_owner("track-1") == [canonical]


def test_track_analysis_status_updates_and_missing_track_rejects(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    store.add_track(Track(id="track-1", filepath=tmp_path / "song.wav", audio_hash="hash"))

    assert store.update_track_analysis_status("track-1", "analyzing").analysis_status == "analyzing"
    assert (
        store.update_track_analysis_status("track-1", "searchable").analysis_status == "searchable"
    )

    with pytest.raises(KeyError):
        store.update_track_analysis_status("missing", "failed")


def test_record_failed_analysis_job_marks_track_failed(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    store.add_track(Track(id="track-1", filepath=tmp_path / "song.wav", audio_hash="hash"))

    job = store.record_failed_analysis_job(
        target_type="track",
        target_id="track-1",
        error_message="decode failed",
        job_type="analyze_library_track",
    )

    assert job.status == "failed"
    assert job.progress == 1.0
    assert job.error_message == "decode failed"
    assert store.get_track("track-1").analysis_status == "failed"
    assert store.list_jobs(status="failed") == [job]
