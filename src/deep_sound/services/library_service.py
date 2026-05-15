"""LibraryService — spec §10.2, §16.1. Phase 1 target."""

from __future__ import annotations

from pathlib import Path

from deep_sound.domain.track import Track


class LibraryService:
    """File import, metadata extraction, dedupe, analysis-status tracking.

    Stub — implemented in Phase 1 (P1-002 in FILE_PLAN).
    """

    def import_file(self, path: Path) -> Track:
        raise NotImplementedError("LibraryService.import_file pending P1-002")

    def import_folder(self, path: Path, recursive: bool = True) -> list[Track]:
        raise NotImplementedError("LibraryService.import_folder pending P1-002")
