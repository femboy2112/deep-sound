from __future__ import annotations

from deep_sound.domain.feature_view import FeatureType, OwnerType
from deep_sound.ui.query_builder import IndexedSearchResultMetadata, IndexStatusDTO
from deep_sound.ui.results_view import ResultCardData


def test_index_status_dto_is_import_safe() -> None:
    status = IndexStatusDTO(
        feature_type=FeatureType.RHYTHM_GLOBAL,
        owner_type=OwnerType.TRACK,
        available=False,
        stale=True,
        backend="scan",
        feature_count=3,
        dim=2,
        warnings=("Index is stale for feature_count.",),
    )

    assert status.stale is True
    assert status.warnings == ("Index is stale for feature_count.",)


def test_indexed_result_metadata_preserves_backend_and_caveats() -> None:
    metadata = IndexedSearchResultMetadata(
        search_backend="mixed",
        matched_entity_type="track",
        matched_range=None,
        dimension_scores={"rhythm.global": 0.9},
        caveats=("No usable index for one dimension.",),
        feedback_adjustment=0.1,
    )
    card = ResultCardData(
        track_title="Song",
        artist=None,
        combined_score=0.9,
        dimension_scores=metadata.dimension_scores,
        explanation="Probabilistic similarity result.",
        search_backend=metadata.search_backend,
        stale_index_warnings=metadata.caveats,
    )

    assert card.search_backend == "mixed"
    assert card.stale_index_warnings == ("No usable index for one dimension.",)
