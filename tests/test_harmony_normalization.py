from __future__ import annotations

from deep_sound.domain.confidence import Confidence
from deep_sound.domain.harmony import (
    ChordEvent,
    HarmonicOwnerType,
    normalize_chord_sequence,
    roman_numeral,
    root_motion_tokens,
)


def _event(root: str, quality: str = "major") -> ChordEvent:
    label = f"{root}{'m' if quality == 'minor' else ''}"
    return ChordEvent(
        id=f"event-{root}-{quality}",
        owner_type=HarmonicOwnerType.SOURCE,
        owner_id="source-1",
        start_sec=0.0,
        end_sec=1.0,
        chord_label=label,
        root=root,
        quality=quality,
        confidence=Confidence(0.7),
    )


def test_roman_numerals_and_root_motion_are_transposition_aware() -> None:
    assert roman_numeral("G", "C") == "V"
    assert roman_numeral("A", "C", "minor") == "VI"
    assert normalize_chord_sequence([_event("C"), _event("G"), _event("A", "minor")]) == [
        "I",
        "V",
        "VI",
    ]
    assert normalize_chord_sequence([_event("D"), _event("A"), _event("B", "minor")]) == [
        "I",
        "V",
        "VI",
    ]
    assert root_motion_tokens([_event("C"), _event("G"), _event("A")]) == [7, 2]
