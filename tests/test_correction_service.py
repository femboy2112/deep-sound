from __future__ import annotations

from pathlib import Path

import pytest

from deep_sound.domain.confidence import Confidence
from deep_sound.domain.corrections import ResultFeedbackValue
from deep_sound.domain.harmony import ChordEvent, HarmonicOwnerType
from deep_sound.domain.source import Source, SourceType
from deep_sound.infra.storage.sqlite_store import SqliteStore
from deep_sound.services.correction_service import CorrectionService


def _source() -> Source:
    return Source(
        id="source-1",
        track_id="track-1",
        parent_stem_id="stem-1",
        source_type=SourceType.PITCHED_HARMONIC,
        source_label="possible accompaniment stem",
        confidence=Confidence(0.71),
    )


def _chord_event() -> ChordEvent:
    return ChordEvent(
        id="chord-1",
        owner_type=HarmonicOwnerType.SOURCE,
        owner_id="source-1",
        start_sec=0.0,
        end_sec=1.0,
        chord_label="C",
        confidence=Confidence(0.62),
    )


def test_correction_service_records_source_and_chord_overrides(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    service = CorrectionService(store)
    source = _source()
    chord = store.add_chord_event(_chord_event())

    source_record = service.add_source_label_correction(
        source,
        label="likely electric guitar",
        source_type=SourceType.MELODIC,
    )
    chord_record = service.add_chord_label_correction(chord, chord_label="Cmaj7")

    effective_source = service.effective_source(source)
    effective_chord = service.effective_chord_event(chord)
    effective_events = service.effective_chord_events_for_owner(chord.owner_id)
    assert source_record.entity_type == "source"
    assert chord_record.entity_type == "chord_event"
    assert effective_source.label == "likely electric guitar"
    assert effective_source.source_type is SourceType.MELODIC
    assert effective_source.is_user_corrected
    assert effective_chord.chord_label == "Cmaj7"
    assert effective_chord.is_user_corrected
    assert effective_events[0].effective_label.chord_label == "Cmaj7"


def test_latest_source_correction_wins_with_app_supplied_timestamps(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    service = CorrectionService(store)
    source = _source()

    service.add_source_label_correction(source, label="likely piano")
    service.add_source_label_correction(source, label="likely guitar")

    assert service.effective_source(source).label == "likely guitar"


def test_correction_service_feedback_adjustment_is_query_scoped(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    service = CorrectionService(store)

    service.add_result_feedback(
        query_owner_id="query-1",
        result_owner_id="result-1",
        feedback=ResultFeedbackValue.RELEVANT,
    )
    service.add_result_feedback(
        query_owner_id="query-1",
        result_owner_id="result-2",
        feedback=ResultFeedbackValue.IRRELEVANT,
    )

    assert service.feedback_adjustment("query-1", "result-1") == 0.05
    assert service.feedback_adjustment("query-1", "result-2") == -0.05
    assert service.feedback_adjustment("query-2", "result-1") == 0.0


def test_correction_service_rejects_invalid_payloads(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    service = CorrectionService(store)

    with pytest.raises(ValueError, match="blank"):
        service.add_source_label_correction(_source(), label=" ")
    with pytest.raises(ValueError, match="result_owner_id"):
        service.add_result_feedback(
            query_owner_id="query-1",
            result_owner_id="",
            feedback="relevant",
        )
