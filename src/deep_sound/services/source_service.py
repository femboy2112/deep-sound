"""SourceService — spec §10.2, §16.3. Phase 2 broad source graph APIs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from deep_sound.domain.confidence import Confidence
from deep_sound.domain.feature_view import FeatureView
from deep_sound.domain.source import Source, SourceType
from deep_sound.domain.stem import Stem, StemType
from deep_sound.domain.track import Track
from deep_sound.infra.separation import BROAD_STEM_TYPES, SeparationProvider
from deep_sound.infra.storage.sqlite_store import SqliteStore
from deep_sound.services.correction_service import CorrectionService


@dataclass(frozen=True, slots=True)
class SourceGraphStem:
    stem: Stem
    sources: tuple[Source, ...]
    feature_views: tuple[FeatureView, ...]


@dataclass(frozen=True, slots=True)
class SourceGraph:
    track_id: str
    stems: tuple[SourceGraphStem, ...]


STEM_SOURCE_TYPES: dict[StemType, SourceType] = {
    StemType.VOCALS: SourceType.MELODIC,
    StemType.DRUMS: SourceType.DRUM,
    StemType.BASS: SourceType.BASS,
    StemType.OTHER: SourceType.PITCHED_HARMONIC,
}


class SourceService:
    """Manage broad stems, inferred broad sources, and source graph reads."""

    def __init__(
        self,
        store: SqliteStore,
        *,
        app_data_dir: Path,
        separation_provider: SeparationProvider | None = None,
        correction_service: CorrectionService | None = None,
    ) -> None:
        self._store = store
        self._app_data_dir = app_data_dir
        self._separation_provider = separation_provider
        self._correction_service = correction_service

    def separate_broad_stems(self, track: Track) -> list[Stem]:
        if self._separation_provider is None:
            raise RuntimeError("No separation provider configured")
        output_dir = self._app_data_dir / "stems" / track.id
        artifacts = self._separation_provider.separate(track.filepath, output_dir)
        stems: list[Stem] = []
        for artifact in artifacts:
            stem = Stem(
                id=f"{track.id}:{artifact.stem_type.value}",
                track_id=track.id,
                stem_type=artifact.stem_type,
                confidence=artifact.confidence,
                artifact_path=artifact.artifact_path,
                model_name=artifact.algorithm,
                model_version=artifact.model_version,
                params_hash=artifact.params_hash,
                input_hash=artifact.input_hash,
            )
            self._store.add_stem(stem)
            self._store.add_source(source_from_stem(stem))
            stems.append(stem)
        return stems

    def list_sources(self, track_id: str) -> list[Source]:
        return self._store.list_sources_for_track(track_id)

    def list_effective_sources(self, track_id: str) -> list[Source]:
        sources = self._store.list_sources_for_track(track_id)
        if self._correction_service is None:
            return sources
        return [self._apply_source_correction(source) for source in sources]

    def discover_pitched_harmonic_sources(self, stem: Stem) -> list[Source]:
        """Create probabilistic pitched-harmonic candidates from compatible stems."""
        if stem.stem_type not in {StemType.OTHER, StemType.VOCALS}:
            return []
        existing_ids = {source.id for source in self._store.list_sources_for_track(stem.track_id)}
        candidate_id = f"{stem.id}:pitched-harmonic"
        if candidate_id in existing_ids:
            return [
                source
                for source in self._store.list_sources_for_track(stem.track_id)
                if source.id == candidate_id
            ]
        confidence = Confidence(min(0.85, max(0.35, stem.confidence.value * 0.8)))
        label = (
            "possible pitched harmonic accompaniment"
            if stem.stem_type is StemType.OTHER
            else "possible pitched vocal harmony"
        )
        source = Source(
            id=candidate_id,
            track_id=stem.track_id,
            parent_stem_id=stem.id,
            source_type=SourceType.PITCHED_HARMONIC,
            source_label=label,
            confidence=confidence,
        )
        self._store.add_source(source)
        return [source]

    def source_graph(self, track_id: str) -> SourceGraph:
        sources_by_stem: dict[str, list[Source]] = {}
        for source in self.list_effective_sources(track_id):
            sources_by_stem.setdefault(source.parent_stem_id, []).append(source)

        graph_stems: list[SourceGraphStem] = []
        for stem in self._store.list_stems_for_track(track_id):
            features = tuple(self._store.list_feature_views_for_owner(stem.id))
            graph_stems.append(
                SourceGraphStem(
                    stem=stem,
                    sources=tuple(sources_by_stem.get(stem.id, [])),
                    feature_views=features,
                )
            )
        return SourceGraph(track_id=track_id, stems=tuple(graph_stems))

    def _apply_source_correction(self, source: Source) -> Source:
        if self._correction_service is None:
            return source
        effective = self._correction_service.effective_source(source)
        if not effective.is_user_corrected:
            return source
        return Source(
            id=source.id,
            track_id=source.track_id,
            parent_stem_id=source.parent_stem_id,
            source_type=effective.source_type,
            source_label=effective.label,
            confidence=source.confidence,
            user_label=effective.label,
            is_user_corrected=True,
        )


def source_from_stem(stem: Stem) -> Source:
    source_type = STEM_SOURCE_TYPES.get(stem.stem_type, SourceType.UNKNOWN)
    label = _broad_source_label(stem.stem_type)
    confidence = stem.confidence if stem.stem_type in BROAD_STEM_TYPES else Confidence(0.4)
    return Source(
        id=f"{stem.id}:source",
        track_id=stem.track_id,
        parent_stem_id=stem.id,
        source_type=source_type,
        source_label=label,
        confidence=confidence,
    )


def _broad_source_label(stem_type: StemType) -> str:
    labels = {
        StemType.VOCALS: "possible vocals stem",
        StemType.DRUMS: "possible drums stem",
        StemType.BASS: "possible bass stem",
        StemType.OTHER: "possible accompaniment stem",
        StemType.FULL_MIX: "full mix",
    }
    return labels[stem_type]
