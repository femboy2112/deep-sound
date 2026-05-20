from __future__ import annotations

from pathlib import Path

from deep_sound.domain.confidence import Confidence
from deep_sound.domain.feature_view import FeatureType
from deep_sound.domain.track import Track
from deep_sound.infra.storage.sqlite_store import SectionRecord, SqliteStore
from deep_sound.services.library_analysis_service import AnalysisProfile, LibraryAnalysisService


def test_library_analysis_service_minimal_profile_is_idempotent(
    tmp_path: Path,
    click_track_wav: Path,
) -> None:
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    track = store.add_track(Track(id="track-1", filepath=click_track_wav, audio_hash="hash"))
    service = LibraryAnalysisService(store)

    first = service.analyze_track(track, profile=AnalysisProfile.MINIMAL)
    second = service.analyze_track(track, profile="minimal")

    assert first.succeeded
    assert second.succeeded
    assert second.status == "minimal"
    assert store.get_track("track-1").analysis_status == "minimal"
    assert [view.feature_type for view in store.list_feature_views_for_owner("track-1")] == [
        FeatureType.HARMONY_CHROMA,
        FeatureType.RHYTHM_GLOBAL,
        FeatureType.TIMBRE_MFCC_STATS,
    ]


def test_library_analysis_service_searchable_profile_extends_minimal_features(
    tmp_path: Path,
    click_track_wav: Path,
) -> None:
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    track = store.add_track(
        Track(
            id="track-1",
            filepath=click_track_wav,
            duration_sec=2.0,
            audio_hash="hash",
        )
    )
    store.add_section(SectionRecord("a", "track-1", 0.0, 1.0, "intro", Confidence(0.8)))
    store.add_section(SectionRecord("b", "track-1", 1.0, 2.0, "verse", Confidence(0.7)))

    summary = LibraryAnalysisService(store).analyze_library([track], profile="searchable")
    LibraryAnalysisService(store).analyze_library([track], profile="searchable")

    assert summary.profile is AnalysisProfile.SEARCHABLE
    assert summary.requested_count == 1
    assert summary.completed_count == 1
    assert summary.failed_count == 0
    assert summary.feature_count == 5
    assert store.get_track("track-1").analysis_status == "searchable"
    assert {view.feature_type for view in store.list_feature_views_for_owner("track-1")} == {
        FeatureType.RHYTHM_GLOBAL,
        FeatureType.HARMONY_CHROMA,
        FeatureType.TIMBRE_MFCC_STATS,
        FeatureType.PRODUCTION_TEXTURE,
        FeatureType.STRUCTURE_SECTION_SEQUENCE,
    }


def test_library_analysis_service_records_failed_track_and_continues(
    tmp_path: Path,
    click_track_wav: Path,
) -> None:
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    good = store.add_track(Track(id="good", filepath=click_track_wav, audio_hash="good"))
    bad = store.add_track(Track(id="bad", filepath=tmp_path / "missing.wav", audio_hash="bad"))

    summary = LibraryAnalysisService(store).analyze_library([bad, good], profile="minimal")

    assert summary.requested_count == 2
    assert summary.completed_count == 1
    assert summary.failed_count == 1
    assert store.get_track("bad").analysis_status == "failed"
    assert store.get_track("good").analysis_status == "minimal"
    assert len(store.list_jobs(status="failed")) == 1
