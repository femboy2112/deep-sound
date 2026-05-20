from __future__ import annotations

from pathlib import Path

from deep_sound.domain.confidence import Confidence
from deep_sound.domain.feature_view import FeatureType
from deep_sound.domain.track import Track
from deep_sound.infra.storage.sqlite_store import SectionRecord, SqliteStore
from deep_sound.services.analysis_service import AnalysisService
from deep_sound.services.feature_service import FeatureService
from deep_sound.services.similarity_service import SearchMode, SimilarityService


def test_structure_feature_view_uses_existing_sections(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    track = Track(id="track-1", filepath=tmp_path / "track.wav", duration_sec=30.0)
    store.add_track(track)
    store.add_section(SectionRecord("a", "track-1", 0.0, 10.0, "verse", Confidence(0.8)))
    store.add_section(SectionRecord("b", "track-1", 10.0, 30.0, "chorus", Confidence(0.7)))

    view = AnalysisService(store).structure_feature_view(track)

    assert view.feature_type is FeatureType.STRUCTURE_SECTION_SEQUENCE
    assert view.stats["section_count"] == 2.0
    assert view.stats["coverage"] == 1.0
    assert view.confidence is not None
    assert view.confidence.value == 0.7


def test_structure_similarity_mode_scores_section_sequences() -> None:
    features = FeatureService()
    for owner_id, count, variety in [
        ("query", 3.0, 0.66),
        ("close", 3.0, 0.66),
        ("far", 8.0, 0.1),
    ]:
        features.put(_structure_view(owner_id, {"section_count": count, "label_variety": variety}))

    results = SimilarityService(features).search_mode("query", SearchMode.STRUCTURE)

    assert [result.owner_id for result in results] == ["close", "far"]


def _structure_view(owner_id: str, stats: dict[str, float]):
    from deep_sound.domain.feature_view import FeatureView, OwnerType

    return FeatureView(
        id=f"{owner_id}:structure.section_sequence",
        owner_type=OwnerType.TRACK,
        owner_id=owner_id,
        feature_type=FeatureType.STRUCTURE_SECTION_SEQUENCE,
        algorithm="test",
        algorithm_version="1",
        params_hash="params",
        stats=stats,
        confidence=Confidence(0.8),
    )
