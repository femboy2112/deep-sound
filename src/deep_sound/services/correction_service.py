"""CorrectionService — user overrides and feedback records."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict
from datetime import UTC, datetime
from uuid import uuid4

from deep_sound.domain.corrections import (
    ChordCorrectionPayload,
    CorrectionEntityType,
    EffectiveChordEvent,
    EffectiveChordLabel,
    EffectiveSourceLabel,
    ResultFeedbackPayload,
    ResultFeedbackValue,
    SourceCorrectionPayload,
    bounded_feedback_adjustment,
)
from deep_sound.domain.harmony import ChordEvent
from deep_sound.domain.source import Source, SourceType
from deep_sound.infra.storage.sqlite_store import CorrectionRecord, SqliteStore


class CorrectionService:
    """Public API over correction storage.

    Raw analyzer/model records are never rewritten. Effective reads combine the
    raw record with the latest correction for display or ranking.
    """

    def __init__(self, store: SqliteStore) -> None:
        self._store = store

    def add_source_label_correction(
        self,
        source: Source,
        *,
        label: str | None = None,
        source_type: SourceType | None = None,
    ) -> CorrectionRecord:
        payload = SourceCorrectionPayload(label=label, source_type=source_type)
        old_value = {
            "label": source.source_label,
            "source_type": source.source_type.value,
            "confidence": source.confidence.value,
        }
        new_value = {
            "label": payload.label,
            "source_type": None if payload.source_type is None else payload.source_type.value,
        }
        return self._add(
            entity_type=CorrectionEntityType.SOURCE,
            entity_id=source.id,
            old_value=old_value,
            new_value=new_value,
        )

    def add_chord_label_correction(
        self,
        event: ChordEvent,
        *,
        chord_label: str,
    ) -> CorrectionRecord:
        payload = ChordCorrectionPayload(chord_label=chord_label)
        return self._add(
            entity_type=CorrectionEntityType.CHORD_EVENT,
            entity_id=event.id,
            old_value={
                "chord_label": event.chord_label,
                "confidence": event.confidence.value,
            },
            new_value=asdict(payload),
        )

    def add_result_feedback(
        self,
        *,
        query_owner_id: str,
        result_owner_id: str,
        feedback: ResultFeedbackValue | str,
    ) -> CorrectionRecord:
        payload = ResultFeedbackPayload(
            result_owner_id=result_owner_id,
            feedback=ResultFeedbackValue(feedback),
        )
        return self._add(
            entity_type=CorrectionEntityType.RESULT_FEEDBACK,
            entity_id=query_owner_id,
            old_value={},
            new_value={
                "result_owner_id": payload.result_owner_id,
                "feedback": payload.feedback.value,
            },
        )

    def list_for_entity(
        self,
        entity_type: CorrectionEntityType | str,
        entity_id: str,
    ) -> list[CorrectionRecord]:
        return self._store.list_corrections(
            entity_id=entity_id,
            entity_type=CorrectionEntityType(entity_type).value,
        )

    def effective_source(self, source: Source) -> EffectiveSourceLabel:
        corrections = self.list_for_entity(CorrectionEntityType.SOURCE, source.id)
        if not corrections:
            return EffectiveSourceLabel(
                label=source.source_label,
                source_type=source.source_type,
                confidence=source.confidence.value,
                is_user_corrected=False,
            )
        latest = corrections[-1]
        payload = _decode_json_object(latest.new_value_json)
        label = _optional_str(payload.get("label")) or source.source_label
        raw_source_type = _optional_str(payload.get("source_type"))
        source_type = source.source_type if raw_source_type is None else SourceType(raw_source_type)
        return EffectiveSourceLabel(
            label=label,
            source_type=source_type,
            confidence=source.confidence.value,
            is_user_corrected=True,
            correction_id=latest.id,
        )

    def effective_chord_event(self, event: ChordEvent) -> EffectiveChordLabel:
        corrections = self.list_for_entity(CorrectionEntityType.CHORD_EVENT, event.id)
        if not corrections:
            return EffectiveChordLabel(
                chord_label=event.chord_label,
                confidence=event.confidence.value,
                is_user_corrected=False,
            )
        latest = corrections[-1]
        payload = _decode_json_object(latest.new_value_json)
        label = _optional_str(payload.get("chord_label"))
        if label is None:
            raise ValueError(f"Chord correction {latest.id} has no chord_label")
        return EffectiveChordLabel(
            chord_label=label,
            confidence=event.confidence.value,
            is_user_corrected=True,
            correction_id=latest.id,
        )

    def effective_chord_events_for_owner(self, owner_id: str) -> list[EffectiveChordEvent]:
        return [
            EffectiveChordEvent(
                event=event,
                effective_label=self.effective_chord_event(event),
            )
            for event in self._store.list_chord_events_for_owner(owner_id)
        ]

    def feedback_adjustment(self, query_owner_id: str, result_owner_id: str) -> float:
        relevant = 0
        irrelevant = 0
        for correction in self.list_for_entity(
            CorrectionEntityType.RESULT_FEEDBACK,
            query_owner_id,
        ):
            payload = _decode_json_object(correction.new_value_json)
            if payload.get("result_owner_id") != result_owner_id:
                continue
            feedback = ResultFeedbackValue(str(payload.get("feedback")))
            if feedback is ResultFeedbackValue.RELEVANT:
                relevant += 1
            else:
                irrelevant += 1
        return bounded_feedback_adjustment(relevant, irrelevant)

    def _add(
        self,
        *,
        entity_type: CorrectionEntityType,
        entity_id: str,
        old_value: Mapping[str, object],
        new_value: Mapping[str, object],
    ) -> CorrectionRecord:
        if not entity_id.strip():
            raise ValueError("correction entity_id must not be blank")
        return self._store.add_correction(
            CorrectionRecord(
                id=str(uuid4()),
                entity_type=entity_type.value,
                entity_id=entity_id,
                old_value_json=json.dumps(old_value, sort_keys=True),
                new_value_json=json.dumps(new_value, sort_keys=True),
                created_at=datetime.now(UTC).isoformat(timespec="microseconds"),
            )
        )


def _decode_json_object(raw_json: str) -> dict[str, object]:
    decoded = json.loads(raw_json)
    if not isinstance(decoded, dict):
        raise ValueError("correction JSON payload must be an object")
    return decoded


def _optional_str(value: object) -> str | None:
    return None if value is None else str(value)
