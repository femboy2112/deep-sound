"""Harmony domain records and normalization helpers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from itertools import pairwise

from deep_sound.domain.confidence import Confidence


class HarmonicOwnerType(StrEnum):
    FULL_MIX = "full_mix"
    STEM = "stem"
    SOURCE = "source"


ROOTS: tuple[str, ...] = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
MAJOR_ROMANS: tuple[str, ...] = (
    "I",
    "bII",
    "II",
    "bIII",
    "III",
    "IV",
    "#IV",
    "V",
    "bVI",
    "VI",
    "bVII",
    "VII",
)
MINOR_ROMANS: tuple[str, ...] = (
    "i",
    "bii",
    "ii",
    "bIII",
    "III",
    "iv",
    "#iv",
    "v",
    "bVI",
    "VI",
    "bVII",
    "VII",
)


@dataclass(frozen=True, slots=True)
class ChordEvent:
    id: str
    owner_type: HarmonicOwnerType
    owner_id: str
    start_sec: float
    end_sec: float
    chord_label: str
    confidence: Confidence
    roman_numeral: str | None = None
    root: str | None = None
    quality: str | None = None
    bass_note: str | None = None
    source: str = "auto"


@dataclass(frozen=True, slots=True)
class NoteEvent:
    id: str
    owner_type: HarmonicOwnerType
    owner_id: str
    start_sec: float
    end_sec: float
    pitch_midi: float
    pitch_name: str
    confidence: Confidence
    velocity: float | None = None


def root_index(root: str) -> int:
    try:
        return ROOTS.index(_normalize_root(root))
    except ValueError as exc:
        raise ValueError(f"Unsupported chord root: {root}") from exc


def root_motion_tokens(events: list[ChordEvent]) -> list[int]:
    roots = [event.root for event in events if event.root is not None]
    if len(roots) < 2:
        return []
    indexes = [root_index(root) for root in roots]
    return [(right - left) % 12 for left, right in pairwise(indexes)]


def roman_numeral(root: str, key_root: str, quality: str = "major") -> str:
    interval = (root_index(root) - root_index(key_root)) % 12
    scale = MINOR_ROMANS if quality == "minor" else MAJOR_ROMANS
    return scale[interval]


def normalize_chord_sequence(events: list[ChordEvent]) -> list[str]:
    if not events:
        return []
    key_root = next((event.root for event in events if event.root is not None), None)
    if key_root is None:
        return [event.chord_label for event in events]
    tokens: list[str] = []
    for event in events:
        if event.roman_numeral:
            tokens.append(event.roman_numeral)
        elif event.root is not None:
            tokens.append(roman_numeral(event.root, key_root, event.quality or "major"))
        else:
            tokens.append(event.chord_label)
    return tokens


def _normalize_root(root: str) -> str:
    aliases = {
        "Db": "C#",
        "Eb": "D#",
        "Gb": "F#",
        "Ab": "G#",
        "Bb": "A#",
    }
    stripped = root.strip()
    return aliases.get(stripped, stripped)
