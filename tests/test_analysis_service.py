from __future__ import annotations

from pathlib import Path

from deep_sound.domain.feature_view import FeatureType, OwnerType
from deep_sound.domain.track import Track
from deep_sound.infra.storage.sqlite_store import SqliteStore
from deep_sound.services.analysis_service import AnalysisService


def test_analysis_service_persists_full_mix_feature_views(
    tmp_path: Path,
    click_track_wav: Path,
) -> None:
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    track = Track(id="track-1", filepath=click_track_wav)
    progress: list[tuple[str, float]] = []

    views = AnalysisService(
        store,
        progress_callback=lambda stage, value: progress.append((stage, value)),
    ).analyze(track)

    persisted = store.list_feature_views_for_owner("track-1")
    assert {view.id for view in persisted} == {view.id for view in views}
    assert [view.owner_type for view in persisted] == [OwnerType.TRACK] * 3
    assert {view.feature_type for view in persisted} == {
        FeatureType.RHYTHM_GLOBAL,
        FeatureType.HARMONY_CHROMA,
        FeatureType.TIMBRE_MFCC_STATS,
    }
    assert all(view.confidence is not None for view in persisted)
    assert progress == [
        ("started", 0.0),
        ("rhythm.global", 1.0 / 3.0),
        ("harmony.chroma", 2.0 / 3.0),
        ("timbre.mfcc_stats", 1.0),
    ]
