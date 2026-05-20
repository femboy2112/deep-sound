from __future__ import annotations

from pathlib import Path

from deep_sound.domain.corrections import ResultFeedbackValue
from deep_sound.infra.storage.sqlite_store import SqliteStore
from deep_sound.services.correction_service import CorrectionService


def test_result_feedback_records_relevant_and_irrelevant_values(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    service = CorrectionService(store)

    relevant = service.add_result_feedback(
        query_owner_id="query-1",
        result_owner_id="result-1",
        feedback=ResultFeedbackValue.RELEVANT,
    )
    irrelevant = service.add_result_feedback(
        query_owner_id="query-1",
        result_owner_id="result-1",
        feedback="irrelevant",
    )

    records = service.list_for_entity("result_feedback", "query-1")
    assert {record.id for record in records} == {relevant.id, irrelevant.id}
    assert service.feedback_adjustment("query-1", "result-1") == 0.0
