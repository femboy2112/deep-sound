from __future__ import annotations

import sqlite3
from pathlib import Path

from deep_sound.domain.confidence import Confidence
from deep_sound.domain.feature_view import FeatureType, FeatureView, OwnerType
from deep_sound.domain.source import Source, SourceType
from deep_sound.domain.stem import Stem, StemType
from deep_sound.domain.track import Track
from deep_sound.infra.storage.sqlite_store import (
    CorrectionRecord,
    SectionRecord,
    SimilarityIndexRecord,
    SourceActivityRecord,
    SqliteStore,
)


def test_init_schema_creates_phase1_tables(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()

    with sqlite3.connect(tmp_path / "library.sqlite") as conn:
        table_names = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
            )
        }

    assert {
        "tracks",
        "sections",
        "stems",
        "sources",
        "source_activity",
        "feature_views",
        "chord_events",
        "note_events",
        "similarity_indices",
        "corrections",
        "jobs",
    } <= table_names


def test_track_round_trip_and_hash_lookup(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    track = Track(
        id="track-1",
        filepath=tmp_path / "song.wav",
        title="song",
        artist="artist",
        album="album",
        duration_sec=1.5,
        sample_rate=44100,
        audio_hash="abc123",
    )

    saved = store.add_track(track)

    assert saved.audio_hash == "abc123"
    assert saved.sample_rate == 44100
    assert saved.analysis_status == "pending"
    assert store.get_track_by_hash("abc123") == saved
    assert store.list_tracks() == [saved]


def test_sections_source_graph_and_feature_dao_round_trip(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    store.add_track(Track(id="track-1", filepath=tmp_path / "song.wav", audio_hash="hash"))
    section = store.add_section(
        SectionRecord(
            id="section-1",
            track_id="track-1",
            start_sec=0.0,
            end_sec=8.0,
            label="intro",
            confidence=Confidence(0.66),
        )
    )
    stem = store.add_stem(
        Stem(
            id="stem-1",
            track_id="track-1",
            stem_type=StemType.FULL_MIX,
            artifact_path=tmp_path / "stems" / "full.wav",
            model_name="none",
            model_version="0",
            confidence=Confidence(1.0),
        )
    )
    source = store.add_source(
        Source(
            id="source-1",
            track_id="track-1",
            parent_stem_id=stem.id,
            source_type=SourceType.PITCHED_HARMONIC,
            source_label="likely piano",
            confidence=Confidence(0.72),
        )
    )
    activity = store.add_source_activity(
        SourceActivityRecord(
            id="activity-1",
            source_id=source.id,
            section_id=section.id,
            start_sec=0.0,
            end_sec=1.0,
            confidence=Confidence(0.81),
        )
    )
    view = FeatureView(
        id="feature-1",
        owner_type=OwnerType.TRACK,
        owner_id="track-1",
        feature_type=FeatureType.RHYTHM_GLOBAL,
        algorithm="test",
        algorithm_version="1",
        params_hash="params",
        vector_path=tmp_path / "features" / "rhythm.npy",
        stats={"tempo": 120.0},
        confidence=Confidence(0.9),
    )
    store.add_feature_view(view)

    assert store.list_sections_for_track("track-1") == [section]
    assert store.list_stems_for_track("track-1") == [stem]
    assert store.list_sources_for_track("track-1") == [source]
    assert store.list_source_activity(source.id) == [activity]
    assert store.list_feature_views_for_owner("track-1") == [view]


def test_similarity_indices_corrections_and_jobs_round_trip(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()

    index = store.add_similarity_index(
        SimilarityIndexRecord(
            id="index-1",
            feature_type=FeatureType.RHYTHM_GLOBAL.value,
            owner_type=OwnerType.TRACK.value,
            index_path=tmp_path / "indices" / "rhythm.faiss",
            manifest_path=tmp_path / "indices" / "rhythm.json",
            version="v1",
        )
    )
    correction = store.add_correction(
        CorrectionRecord(
            id="correction-1",
            entity_type="source",
            entity_id="source-1",
            old_value_json='{"label": "likely piano"}',
            new_value_json='{"label": "likely guitar"}',
        )
    )
    job = store.create_job(job_type="analyze_track", target_type="track", target_id="track-1")
    updated_job = store.update_job(job.id, status="completed", progress=1.5)

    assert store.list_similarity_indices(FeatureType.RHYTHM_GLOBAL.value) == [index]
    assert index.created_at is not None
    assert store.list_corrections("source-1") == [correction]
    assert correction.created_at is not None
    assert updated_job.status == "completed"
    assert updated_job.progress == 1.0
    assert store.list_jobs(status="completed") == [updated_job]
