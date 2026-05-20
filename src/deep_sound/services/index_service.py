"""Persisted feature index orchestration for Phase 6 indexed-library beta."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from deep_sound.domain.feature_view import FeatureType, FeatureView, OwnerType
from deep_sound.infra.index.faiss_index import INDEX_VERSION, FaissIndex
from deep_sound.infra.storage.sqlite_store import SimilarityIndexRecord, SqliteStore
from deep_sound.services.feature_service import FeatureService
from deep_sound.services.library_analysis_service import AnalysisProfile, normalize_analysis_profile

INDEX_SERVICE_VERSION = "index-service-v1"

INDEX_PROFILE_FEATURES: dict[AnalysisProfile, tuple[tuple[OwnerType, FeatureType], ...]] = {
    AnalysisProfile.MINIMAL: (
        (OwnerType.TRACK, FeatureType.RHYTHM_GLOBAL),
        (OwnerType.TRACK, FeatureType.HARMONY_CHROMA),
        (OwnerType.TRACK, FeatureType.TIMBRE_MFCC_STATS),
    ),
    AnalysisProfile.SEARCHABLE: (
        (OwnerType.TRACK, FeatureType.RHYTHM_GLOBAL),
        (OwnerType.TRACK, FeatureType.HARMONY_CHROMA),
        (OwnerType.TRACK, FeatureType.TIMBRE_MFCC_STATS),
        (OwnerType.TRACK, FeatureType.PRODUCTION_TEXTURE),
        (OwnerType.TRACK, FeatureType.STRUCTURE_SECTION_SEQUENCE),
    ),
    AnalysisProfile.SOURCE_AWARE: (
        (OwnerType.TRACK, FeatureType.RHYTHM_GLOBAL),
        (OwnerType.TRACK, FeatureType.HARMONY_CHROMA),
        (OwnerType.TRACK, FeatureType.TIMBRE_MFCC_STATS),
        (OwnerType.TRACK, FeatureType.PRODUCTION_TEXTURE),
        (OwnerType.TRACK, FeatureType.STRUCTURE_SECTION_SEQUENCE),
        (OwnerType.STEM, FeatureType.RHYTHM_DRUM),
        (OwnerType.STEM, FeatureType.BASS_ROOT_MOTION),
        (OwnerType.STEM, FeatureType.HARMONY_CHROMA),
        (OwnerType.STEM, FeatureType.TIMBRE_MFCC_STATS),
        (OwnerType.SOURCE, FeatureType.HARMONY_CHORD_SEQUENCE),
        (OwnerType.SOURCE, FeatureType.HARMONY_CHORD_CHANGE),
        (OwnerType.SOURCE, FeatureType.MELODY_CONTOUR),
        (OwnerType.SOURCE, FeatureType.TIMBRE_EMBEDDING),
    ),
}


@dataclass(frozen=True, slots=True)
class IndexStatus:
    feature_type: FeatureType
    owner_type: OwnerType
    available: bool
    stale: bool
    backend: str
    feature_count: int
    dim: int
    caveats: tuple[str, ...] = ()
    record: SimilarityIndexRecord | None = None


class IndexService:
    """Build, load, and validate vector indexes from persisted FeatureView rows."""

    def __init__(
        self,
        store: SqliteStore,
        *,
        index_root: Path,
        features: FeatureService | None = None,
    ) -> None:
        self._store = store
        self._index_root = index_root
        self._features = features or FeatureService(store)

    def build_index(
        self,
        feature_type: FeatureType,
        *,
        owner_type: OwnerType = OwnerType.TRACK,
    ) -> IndexStatus:
        views = self._features.list_by_type(feature_type, owner_type=owner_type)
        if not views:
            raise ValueError(
                f"No persisted feature views for {owner_type.value}/{feature_type.value}"
            )
        vectors = [self._features.vector_for(view) for view in views]
        dims = {len(vector) for vector in vectors}
        if len(dims) != 1:
            raise ValueError("Cannot build index from mixed-dimension feature vectors")
        dim = dims.pop()
        if dim <= 0:
            raise ValueError("Cannot build index from empty feature vectors")

        paths = self._paths(feature_type, owner_type)
        paths.index_path.unlink(missing_ok=True)
        paths.manifest_path.unlink(missing_ok=True)
        index = FaissIndex(paths.index_path, paths.manifest_path, dim=dim)
        for view, vector in zip(views, vectors, strict=True):
            index.add(view.owner_id, vector)

        base_manifest = json.loads(paths.manifest_path.read_text(encoding="utf-8"))
        metadata = self._metadata(feature_type, owner_type, views, dim)
        paths.manifest_path.write_text(
            json.dumps({**base_manifest, **metadata}, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        record = self._store.add_similarity_index(
            SimilarityIndexRecord(
                id=str(uuid4()),
                feature_type=feature_type.value,
                owner_type=owner_type.value,
                index_path=paths.index_path,
                manifest_path=paths.manifest_path,
                version=INDEX_SERVICE_VERSION,
            )
        )
        return self.status(feature_type, owner_type=owner_type, record=record)

    def build_profile(self, profile: AnalysisProfile | str) -> tuple[IndexStatus, ...]:
        selected_profile = normalize_analysis_profile(profile)
        return tuple(
            self.build_index(feature_type, owner_type=owner_type)
            for owner_type, feature_type in INDEX_PROFILE_FEATURES[selected_profile]
        )

    def status(
        self,
        feature_type: FeatureType,
        *,
        owner_type: OwnerType = OwnerType.TRACK,
        record: SimilarityIndexRecord | None = None,
    ) -> IndexStatus:
        views = self._features.list_by_type(feature_type, owner_type=owner_type)
        vectors = [self._features.vector_for(view) for view in views]
        dim = len(vectors[0]) if vectors else 0
        selected = record or self._latest_record(feature_type, owner_type)
        if selected is None:
            return IndexStatus(
                feature_type=feature_type,
                owner_type=owner_type,
                available=False,
                stale=True,
                backend="scan",
                feature_count=len(views),
                dim=dim,
                caveats=("No persisted index is available; search will scan feature rows.",),
            )
        if not selected.index_path.exists() or not selected.manifest_path.exists():
            return IndexStatus(
                feature_type=feature_type,
                owner_type=owner_type,
                available=False,
                stale=True,
                backend="scan",
                feature_count=len(views),
                dim=dim,
                record=selected,
                caveats=("Index record points to missing files; search will scan feature rows.",),
            )

        manifest = json.loads(selected.manifest_path.read_text(encoding="utf-8"))
        expected = self._metadata(feature_type, owner_type, views, dim)
        stale_reasons = tuple(
            key for key, expected_value in expected.items() if manifest.get(key) != expected_value
        )
        backend = str(manifest.get("backend", "unknown"))
        return IndexStatus(
            feature_type=feature_type,
            owner_type=owner_type,
            available=not stale_reasons,
            stale=bool(stale_reasons),
            backend=backend,
            feature_count=len(views),
            dim=dim,
            record=selected,
            caveats=tuple(
                f"Index is stale for {reason}; search will scan feature rows."
                for reason in stale_reasons
            ),
        )

    def query(
        self,
        feature_type: FeatureType,
        query_vector: list[float],
        *,
        owner_type: OwnerType = OwnerType.TRACK,
        top_k: int = 50,
    ) -> tuple[list[str], IndexStatus]:
        status = self.status(feature_type, owner_type=owner_type)
        if not status.available or status.record is None:
            return ([], status)
        index = FaissIndex(status.record.index_path, status.record.manifest_path, dim=status.dim)
        return ([entity_id for entity_id, _score in index.query(query_vector, k=top_k)], status)

    def _latest_record(
        self,
        feature_type: FeatureType,
        owner_type: OwnerType,
    ) -> SimilarityIndexRecord | None:
        records = [
            record
            for record in self._store.list_similarity_indices(feature_type.value)
            if record.owner_type == owner_type.value
        ]
        return records[-1] if records else None

    def _metadata(
        self,
        feature_type: FeatureType,
        owner_type: OwnerType,
        views: list[FeatureView],
        dim: int,
    ) -> dict[str, object]:
        fingerprint_rows: list[dict[str, str]] = []
        for view in views:
            fingerprint_rows.append(
                {
                    "owner_id": view.owner_id,
                    "algorithm": view.algorithm,
                    "algorithm_version": view.algorithm_version,
                    "params_hash": view.params_hash,
                }
            )
        fingerprint = hashlib.sha256(
            json.dumps(fingerprint_rows, sort_keys=True).encode("utf-8")
        ).hexdigest()
        return {
            "index_service_version": INDEX_SERVICE_VERSION,
            "vector_index_version": INDEX_VERSION,
            "feature_type": feature_type.value,
            "owner_type": owner_type.value,
            "feature_count": len(views),
            "dim": dim,
            "feature_fingerprint": fingerprint,
        }

    def _paths(self, feature_type: FeatureType, owner_type: OwnerType) -> _IndexPaths:
        stem = f"{owner_type.value}_{feature_type.value.replace('.', '_')}"
        return _IndexPaths(
            index_path=self._index_root / f"{stem}.index",
            manifest_path=self._index_root / f"{stem}.json",
        )


@dataclass(frozen=True, slots=True)
class _IndexPaths:
    index_path: Path
    manifest_path: Path
