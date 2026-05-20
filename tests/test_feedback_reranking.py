from __future__ import annotations

from pathlib import Path

from deep_sound.domain.feature_view import FeatureType, FeatureView, OwnerType
from deep_sound.infra.storage.sqlite_store import SqliteStore
from deep_sound.services.correction_service import CorrectionService
from deep_sound.services.feature_service import FeatureService
from deep_sound.services.similarity_service import SimilarityService


def _feature(owner_id: str, x: float) -> FeatureView:
    return FeatureView(
        id=f"{owner_id}:rhythm",
        owner_type=OwnerType.TRACK,
        owner_id=owner_id,
        feature_type=FeatureType.RHYTHM_GLOBAL,
        algorithm="test",
        algorithm_version="1",
        params_hash="params",
        stats={"x": x, "y": 1.0},
    )


def test_feedback_reranking_adds_bounded_metadata_and_keeps_scores_normalized(
    tmp_path: Path,
) -> None:
    features = FeatureService()
    features.put(_feature("query-1", 1.0))
    features.put(_feature("candidate-1", 0.9))
    features.put(_feature("candidate-2", 0.8))
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    corrections = CorrectionService(store)
    corrections.add_result_feedback(
        query_owner_id="query-1",
        result_owner_id="candidate-2",
        feedback="relevant",
    )
    corrections.add_result_feedback(
        query_owner_id="query-1",
        result_owner_id="candidate-1",
        feedback="irrelevant",
    )

    results = SimilarityService(features, correction_service=corrections).search_mode(
        "query-1",
        mode="rhythm",
    )

    by_id = {result.owner_id: result for result in results}
    assert by_id["candidate-2"].feedback_adjustment == 0.05
    assert by_id["candidate-1"].feedback_adjustment == -0.05
    assert "feedback_adjustment" not in by_id["candidate-2"].dimension_scores
    assert all(0.0 <= result.score <= 1.0 for result in results)


def test_no_feedback_keeps_similarity_results_unchanged() -> None:
    features = FeatureService()
    features.put(_feature("query-1", 1.0))
    features.put(_feature("candidate-1", 0.9))

    result = SimilarityService(features).search_mode("query-1", mode="rhythm")[0]

    assert result.feedback_adjustment == 0.0
    assert "feedback_adjustment" not in result.dimension_scores
