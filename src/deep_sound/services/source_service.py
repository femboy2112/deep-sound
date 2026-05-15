"""SourceService — spec §10.2, §16.3. Phase 2+ target."""

from __future__ import annotations

from deep_sound.domain.source import Source


class SourceService:
    """Manage stems, detected sources, labels, activity, and corrections.

    Stub — implemented in Phase 2 (broad stems) and Phase 3 (sub-sources).
    """

    def list_sources(self, track_id: str) -> list[Source]:
        raise NotImplementedError("SourceService.list_sources pending P2/P3")
