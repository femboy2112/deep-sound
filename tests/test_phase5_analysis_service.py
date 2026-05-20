from __future__ import annotations

from pathlib import Path

from deep_sound.domain.feature_view import FeatureType, OwnerType
from deep_sound.domain.track import Track
from deep_sound.infra.storage.sqlite_store import SqliteStore
from deep_sound.services.analysis_service import AnalysisService


def test_analysis_service_persists_production_texture(
    tmp_path: Path,
    click_track_wav: Path,
) -> None:
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    track = Track(id="track-1", filepath=click_track_wav)

    view = AnalysisService(store).analyze_production_texture(track)

    assert view.owner_type is OwnerType.TRACK
    assert view.feature_type is FeatureType.PRODUCTION_TEXTURE
    assert view.confidence is not None
    assert store.list_feature_views_for_owner("track-1") == [view]
