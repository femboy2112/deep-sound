"""FeatureService — spec §10.2, §16.4. Phase 0 minimal in-memory; Phase 1 SQLite."""

from __future__ import annotations

import math

from deep_sound.domain.feature_view import FeatureType, FeatureView, OwnerType
from deep_sound.domain.source import SourceType
from deep_sound.infra.storage.sqlite_store import SqliteStore


class FeatureService:
    """Read/write feature views for Phase 0 in-memory search.

    SQLite-backed version lands in Phase 1. For Phase 0, numeric vectors are
    stored in `FeatureView.stats` with deterministic key ordering.
    """

    def __init__(self, store: SqliteStore | None = None) -> None:
        self._store = store
        self._views: dict[str, FeatureView] = {}

    def put(self, view: FeatureView) -> None:
        if not view.id:
            raise ValueError("FeatureView.id must not be empty")
        if view.id in self._views:
            raise ValueError(f"FeatureView already exists: {view.id}")
        self._validate_stats(view)
        if self._store is not None:
            self._store.add_feature_view(view)
        self._views[view.id] = view

    def get(self, view_id: str) -> FeatureView:
        try:
            return self._views[view_id]
        except KeyError as exc:
            if self._store is None:
                raise KeyError(f"FeatureView not found: {view_id}") from exc
        return self._store.get_feature_view(view_id)

    def list_by_owner(self, owner_id: str) -> list[FeatureView]:
        if self._store is not None:
            return self._store.list_feature_views_for_owner(owner_id)
        return [view for view in self._views.values() if view.owner_id == owner_id]

    def list_by_type(
        self,
        feature_type: FeatureType,
        owner_type: OwnerType | None = None,
    ) -> list[FeatureView]:
        if self._store is not None:
            return self._store.list_feature_views_by_type(feature_type, owner_type=owner_type)
        return [
            view
            for view in self._views.values()
            if view.feature_type is feature_type
            and (owner_type is None or view.owner_type is owner_type)
        ]

    def get_for_owner(
        self,
        owner_id: str,
        feature_type: FeatureType,
        owner_type: OwnerType | None = None,
    ) -> FeatureView:
        if self._store is not None:
            return self._store.get_feature_view_for_owner(
                owner_id,
                feature_type,
                owner_type=owner_type,
            )
        matches = [
            view
            for view in self._views.values()
            if view.owner_id == owner_id
            and view.feature_type is feature_type
            and (owner_type is None or view.owner_type is owner_type)
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

    def source_type_for_owner(self, owner_id: str) -> SourceType | None:
        if self._store is None:
            return None
        try:
            return self._store.get_source(owner_id).source_type
        except KeyError:
            return None

    def _validate_stats(self, view: FeatureView) -> None:
        for key, value in view.stats.items():
            if not key:
                raise ValueError("FeatureView.stats keys must not be empty")
            if not math.isfinite(value):
                raise ValueError(f"FeatureView.stats[{key!r}] must be finite")
