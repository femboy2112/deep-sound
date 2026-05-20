"""Track — top-level imported audio file. Spec §11.2 `tracks`."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Track:
    """A single imported audio file with library metadata.

    Phase 1 carries the SQLite-backed metadata needed for import, dedupe, and
    analysis-status tracking while keeping the Phase 0 fields backward
    compatible.
    """

    id: str
    filepath: Path
    title: str | None = None
    artist: str | None = None
    album: str | None = None
    duration_sec: float | None = None
    sample_rate: int | None = None
    audio_hash: str | None = None
    import_status: str = "imported"
    analysis_status: str = "pending"
    created_at: str | None = None
