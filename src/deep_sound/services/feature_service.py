"""FeatureService — spec §10.2, §16.4. Phase 0 minimal in-memory; Phase 1 SQLite."""

from __future__ import annotations

import math

from deep_sound.domain.feature_view import FeatureType, FeatureView


class FeatureService:
    """Read/write feature views for Phase 0 in-memory search.

    SQLite-backed version lands in Phase 1. For Phase 0, numeric vectors are
    stored in `FeatureView.stats` with deterministic key ordering.
    """

    def __init__(self) -> None:
        self._views: dict[str, FeatureView] = {}

    def put(self, view: FeatureView) -> None:
        if not view.id:
            raise ValueError("FeatureView.id must not be empty")
        if view.id in self._views:
            raise ValueError(f"FeatureView already exists: {view.id}")
        self._validate_stats(view)
        self._views[view.id] = view

    def get(self, view_id: str) -> FeatureView:
        try:
            return self._views[view_id]
        except KeyError as exc:
            raise KeyError(f"FeatureView not found: {view_id}") from exc

    def list_by_owner(self, owner_id: str) -> list[FeatureView]:
        return [view for view in self._views.values() if view.owner_id == owner_id]

    def list_by_type(self, feature_type: FeatureType) -> list[FeatureView]:
        return [view for view in self._views.values() if view.feature_type is feature_type]

    def get_for_owner(self, owner_id: str, feature_type: FeatureType) -> FeatureView:
        matches = [
            view
            for view in self._views.values()
            if view.owner_id == owner_id and view.feature_type is feature_type
        ]
        if not matches:
            raise KeyError(
                f"FeatureView not found for owner={owner_id!r}, type={feature_type.value!r}"
            )
        if len(matches) > 1:
            raise ValueError(
                f"Multiple FeatureViews for owner={owner_id!r}, type={feature_type.value!r}"
            )
        return matches[0]

    def vector_for(self, view: FeatureView) -> list[float]:
        if not view.stats:
            return []
        return [view.stats[key] for key in sorted(view.stats)]

    def _validate_stats(self, view: FeatureView) -> None:
        for key, value in view.stats.items():
            if not key:
                raise ValueError("FeatureView.stats keys must not be empty")
            if not math.isfinite(value):
                raise ValueError(f"FeatureView.stats[{key!r}] must be finite")
