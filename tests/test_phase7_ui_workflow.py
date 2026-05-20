from __future__ import annotations

from pathlib import Path

from deep_sound.domain.feature_view import FeatureType, OwnerType
from deep_sound.domain.track import Track
from deep_sound.infra.storage.sqlite_store import SqliteStore
from deep_sound.services.index_service import IndexStatus
from deep_sound.services.library_analysis_service import AnalysisProfile
from deep_sound.services.similarity_service import SimilarityResult
from deep_sound.ui.library_workflow import (
    AnalyzeIntentDTO,
    FeedbackIntentDTO,
    ImportIntentDTO,
    IndexIntentDTO,
    SearchIntentDTO,
    WorkflowSnapshotDTO,
    index_status_dto,
    job_dto,
    result_card_from_similarity,
    stale_index_warnings,
)


def test_library_workflow_intent_dtos_are_import_safe(tmp_path: Path) -> None:
    snapshot = WorkflowSnapshotDTO(
        active_profile=AnalysisProfile.SEARCHABLE,
        jobs=(),
        index_statuses=(),
        warnings=(),
    )

    assert ImportIntentDTO(paths=(tmp_path,), recursive=True).paths == (tmp_path,)
    assert AnalyzeIntentDTO(profile=AnalysisProfile.SEARCHABLE).reanalyze is True
    assert IndexIntentDTO(profile=AnalysisProfile.SEARCHABLE).rebuild is True
    assert SearchIntentDTO(query_id="track-1", mode="rhythm").top_k == 10
    assert (
        FeedbackIntentDTO(
            query_owner_id="query",
            result_owner_id="result",
            value="relevant",
        ).value
        == "relevant"
    )
    assert snapshot.active_profile is AnalysisProfile.SEARCHABLE


def test_library_workflow_maps_jobs_and_index_warnings(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    job = store.create_job(
        job_type="analyze_searchable",
        target_type="track",
        target_id="track-1",
        status="failed",
        progress=1.0,
        error_message="decode failed",
    )
    status = IndexStatus(
        feature_type=FeatureType.RHYTHM_GLOBAL,
        owner_type=OwnerType.TRACK,
        available=False,
        stale=True,
        backend="scan",
        feature_count=2,
        dim=2,
        caveats=("Index is stale for feature_count; search will scan feature rows.",),
    )

    mapped_job = job_dto(job)
    mapped_status = index_status_dto(status)
    warnings = stale_index_warnings((status,))

    assert mapped_job.retry_enabled is True
    assert mapped_job.error_message == "decode failed"
    assert mapped_status.warnings == status.caveats
    assert warnings[0].severity == "warning"


def test_library_workflow_maps_similarity_result_to_result_card(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    store.add_track(
        Track(
            id="near",
            filepath=tmp_path / "near.wav",
            title="Near Song",
            artist="Artist",
            audio_hash="hash",
        )
    )
    result = SimilarityResult(
        owner_id="near",
        score=0.91,
        dimension_scores={"rhythm.global": 0.91},
        owner_type=OwnerType.TRACK,
        matched_entity_type="track",
        baseline_score=0.9,
        feedback_adjustment=0.01,
        search_backend="mixed",
        retrieval_caveats=("No usable index for one dimension.",),
        caveats=("Similarity result is probabilistic.",),
    )

    card = result_card_from_similarity(
        store,
        result,
        explanation="Probabilistic similarity result.",
    )

    assert card.track_title == "Near Song"
    assert card.artist == "Artist"
    assert card.search_backend == "mixed"
    assert card.stale_index_warnings == ("No usable index for one dimension.",)
    assert card.caveats == ("Similarity result is probabilistic.",)
