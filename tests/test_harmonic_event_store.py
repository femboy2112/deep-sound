from __future__ import annotations

from pathlib import Path

from deep_sound.domain.confidence import Confidence
from deep_sound.domain.harmony import ChordEvent, HarmonicOwnerType, NoteEvent
from deep_sound.infra.storage.sqlite_store import SqliteStore


def test_chord_and_note_events_round_trip_with_confidence(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    chord = store.add_chord_event(
        ChordEvent(
            id="chord-1",
            owner_type=HarmonicOwnerType.SOURCE,
            owner_id="source-1",
            start_sec=0.0,
            end_sec=1.5,
            chord_label="C",
            roman_numeral="I",
            root="C",
            quality="major",
            bass_note="C",
            confidence=Confidence(0.71),
        )
    )
    note = store.add_note_event(
        NoteEvent(
            id="note-1",
            owner_type=HarmonicOwnerType.SOURCE,
            owner_id="source-1",
            start_sec=0.1,
            end_sec=0.8,
            pitch_midi=60.0,
            pitch_name="C4",
            velocity=0.6,
            confidence=Confidence(0.64),
        )
    )

    assert store.list_chord_events_for_owner("source-1") == [chord]
    assert store.list_note_events_for_owner("source-1") == [note]
    assert 0.0 <= chord.confidence.value <= 1.0
    assert 0.0 <= note.confidence.value <= 1.0
