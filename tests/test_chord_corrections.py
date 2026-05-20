from __future__ import annotations

from pathlib import Path

from deep_sound.domain.confidence import Confidence
from deep_sound.domain.harmony import ChordEvent, HarmonicOwnerType
from deep_sound.infra.storage.sqlite_store import SqliteStore
from deep_sound.services.correction_service import CorrectionService


def test_chord_correction_overlay_preserves_raw_event(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    event = store.add_chord_event(
        ChordEvent(
            id="chord-1",
            owner_type=HarmonicOwnerType.SOURCE,
            owner_id="source-1",
            start_sec=0.0,
            end_sec=1.0,
            chord_label="C",
            confidence=Confidence(0.62),
        )
    )
    service = CorrectionService(store)

    service.add_chord_label_correction(event, chord_label="Cmaj7")

    effective = service.effective_chord_event(event)
    assert effective.chord_label == "Cmaj7"
    assert effective.is_user_corrected
    assert store.get_chord_event("chord-1") == event
