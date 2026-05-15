"""FeatureService — spec §10.2, §16.4. Phase 0 minimal in-memory; Phase 1 SQLite."""

from __future__ import annotations

from deep_sound.domain.feature_view import FeatureView


class FeatureService:
    """Read/write feature views, validate versions, invalidate stale features.

    Stub — minimal in-memory variant arrives in Phase 0 (P0-016);
    SQLite-backed version in Phase 1.
    """

    def put(self, view: FeatureView) -> None:
        raise NotImplementedError("FeatureService.put pending P0-016")

    def get(self, view_id: str) -> FeatureView:
        raise NotImplementedError("FeatureService.get pending P0-016")
