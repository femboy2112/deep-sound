"""Track — top-level imported audio file. Spec §11.2 `tracks`."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Track:
    """A single imported audio file with library metadata.

    Stub for Phase 0. Full schema (sample_rate, audio_hash, import_status,
    created_at, etc.) lands with the SQLite store in Phase 1 — see
    docs/DATA_MODEL.md and spec §11.2.
    """

    id: str
    filepath: Path
    title: str | None = None
    artist: str | None = None
    duration_sec: float | None = None
