"""SQLite-backed metadata store. Spec §11.2, §17.1. Phase 1 target (P1-001)."""

from __future__ import annotations

from pathlib import Path


class SqliteStore:
    """Embedded local metadata database.

    Stub — schema for tracks/sections/stems/sources/feature_views/chord_events/
    note_events/similarity_indices/corrections/jobs arrives in P1-001.
    """

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def init_schema(self) -> None:
        raise NotImplementedError("SqliteStore.init_schema pending P1-001")
