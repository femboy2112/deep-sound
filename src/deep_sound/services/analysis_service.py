"""AnalysisService — spec §10.2, §16.2. Phase 1 full-mix extraction."""

from __future__ import annotations

import json
from collections.abc import Callable

from deep_sound.domain.confidence import Confidence
from deep_sound.domain.feature_view import FeatureType, FeatureView, OwnerType
from deep_sound.domain.harmony import ChordEvent, normalize_chord_sequence, root_motion_tokens
from deep_sound.domain.source import Source, SourceType
from deep_sound.domain.stem import Stem, StemType
from deep_sound.domain.track import Track
from deep_sound.infra.analyzers.bass_stem import summarize_bass_stem
from deep_sound.infra.analyzers.chroma_librosa import summarize_chroma
from deep_sound.infra.analyzers.drum_stem import summarize_drum_stem
from deep_sound.infra.analyzers.melody_contour import summarize_melody_contour
from deep_sound.infra.analyzers.mfcc_librosa import summarize_mfcc
from deep_sound.infra.analyzers.other_stem import summarize_other_stem
from deep_sound.infra.analyzers.production_texture import summarize_production_texture
from deep_sound.infra.analyzers.source_chords import (
    ANALYZER_NAME as SOURCE_CHORD_ANALYZER_NAME,
)
from deep_sound.infra.analyzers.source_chords import (
    ANALYZER_VERSION as SOURCE_CHORD_ANALYZER_VERSION,
)
from deep_sound.infra.analyzers.source_chords import (
    infer_source_chord_events,
)
from deep_sound.infra.analyzers.tempo_librosa import DEFAULT_SAMPLE_RATE, estimate_tempo
from deep_sound.infra.storage.sqlite_store import SectionRecord, SqliteStore
from deep_sound.services.source_service import SourceService

ProgressCallback = Callable[[str, float], None]


class AnalysisService:
    """Orchestrates Phase 1 full-mix feature extraction for a track."""

    def __init__(
        self,
        store: SqliteStore,
        *,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        self._store = store
        self._sample_rate = sample_rate
        self._progress_callback = progress_callback

    def analyze(self, track: Track) -> list[FeatureView]:
        """Extract and persist rhythm, chroma, and MFCC views for a track.

        Phase 1 deliberately stays at the full-mix track level. Source, stem,
        chord, and section-level feature views are later phases.
        """
        self._emit_progress("started", 0.0)

        tempo = estimate_tempo(track.filepath, sample_rate=self._sample_rate)
        rhythm = FeatureView(
            id=f"{track.id}:rhythm.global",
            owner_type=OwnerType.TRACK,
            owner_id=track.id,
            feature_type=FeatureType.RHYTHM_GLOBAL,
            algorithm=tempo.analyzer,
            algorithm_version=tempo.analyzer_version,
            params_hash=f"sample_rate={self._sample_rate}",
            stats={
                "tempo_bpm": tempo.tempo_bpm,
                "beats_per_sec": len(tempo.beats_sec) / max(tempo.duration_sec, 1.0),
            },
            confidence=tempo.confidence,
        )
        self._store.replace_feature_view_for_owner(rhythm)
        self._emit_progress("rhythm.global", 1.0 / 3.0)

        chroma = summarize_chroma(track.filepath, sample_rate=self._sample_rate)
        harmony = FeatureView(
            id=f"{track.id}:harmony.chroma",
            owner_type=OwnerType.TRACK,
            owner_id=track.id,
            feature_type=FeatureType.HARMONY_CHROMA,
            algorithm=chroma.analyzer,
            algorithm_version=chroma.analyzer_version,
            params_hash=f"sample_rate={self._sample_rate}",
            stats=_vector_stats("chroma", chroma.chroma),
            confidence=chroma.confidence,
        )
        self._store.replace_feature_view_for_owner(harmony)
        self._emit_progress("harmony.chroma", 2.0 / 3.0)

        mfcc = summarize_mfcc(track.filepath, sample_rate=self._sample_rate)
        timbre = FeatureView(
            id=f"{track.id}:timbre.mfcc_stats",
            owner_type=OwnerType.TRACK,
            owner_id=track.id,
            feature_type=FeatureType.TIMBRE_MFCC_STATS,
            algorithm=mfcc.analyzer,
            algorithm_version=mfcc.analyzer_version,
            params_hash=f"sample_rate={self._sample_rate};n_mfcc={mfcc.n_mfcc}",
            stats=_vector_stats("mfcc", mfcc.mfcc),
            confidence=mfcc.confidence,
        )
        self._store.replace_feature_view_for_owner(timbre)
        self._emit_progress("timbre.mfcc_stats", 1.0)

        return [rhythm, harmony, timbre]

    def separate_stems(self, track: Track, source_service: SourceService) -> list[Stem]:
        """Run broad-stem separation through SourceService and persist stems."""
        self._emit_progress("separate_stems.started", 0.0)
        stems = source_service.separate_broad_stems(track)
        self._emit_progress("separate_stems.completed", 1.0)
        return stems

    def analyze_stem(self, stem: Stem) -> list[FeatureView]:
        """Extract conservative Phase 2 feature views for a broad stem."""
        if stem.artifact_path is None:
            raise ValueError(f"Stem {stem.id} has no artifact_path")
        views: list[FeatureView] = []
        if stem.stem_type is StemType.DRUMS:
            drum_summary = summarize_drum_stem(stem.artifact_path, sample_rate=self._sample_rate)
            views.append(
                FeatureView(
                    id=f"{stem.id}:rhythm.drum",
                    owner_type=OwnerType.STEM,
                    owner_id=stem.id,
                    feature_type=FeatureType.RHYTHM_DRUM,
                    algorithm=drum_summary.analyzer,
                    algorithm_version=drum_summary.analyzer_version,
                    params_hash=f"sample_rate={self._sample_rate}",
                    stats={
                        "groove_regularity": drum_summary.groove_regularity,
                        "onset_density": drum_summary.onset_density,
                        "spectral_centroid": drum_summary.spectral_centroid,
                        "transient_strength": drum_summary.transient_strength,
                        "high_frequency_ratio": drum_summary.high_frequency_ratio,
                    },
                    confidence=drum_summary.confidence,
                )
            )
        elif stem.stem_type is StemType.BASS:
            bass_summary = summarize_bass_stem(stem.artifact_path, sample_rate=self._sample_rate)
            views.append(
                FeatureView(
                    id=f"{stem.id}:bass.root_motion",
                    owner_type=OwnerType.STEM,
                    owner_id=stem.id,
                    feature_type=FeatureType.BASS_ROOT_MOTION,
                    algorithm=bass_summary.analyzer,
                    algorithm_version=bass_summary.analyzer_version,
                    params_hash=f"sample_rate={self._sample_rate}",
                    stats={
                        "low_energy_ratio": bass_summary.low_energy_ratio,
                        "pitch_motion": bass_summary.pitch_motion,
                        "root_stability": bass_summary.root_stability,
                        "pitch_variety": bass_summary.pitch_variety,
                        "median_register": bass_summary.median_register,
                    },
                    confidence=bass_summary.confidence,
                )
            )
        elif stem.stem_type is StemType.OTHER:
            other_summary = summarize_other_stem(stem.artifact_path, sample_rate=self._sample_rate)
            views.extend(
                [
                    FeatureView(
                        id=f"{stem.id}:harmony.chroma",
                        owner_type=OwnerType.STEM,
                        owner_id=stem.id,
                        feature_type=FeatureType.HARMONY_CHROMA,
                        algorithm=other_summary.analyzer,
                        algorithm_version=other_summary.analyzer_version,
                        params_hash=f"sample_rate={self._sample_rate}",
                        stats=_vector_stats("chroma", other_summary.chroma),
                        confidence=other_summary.confidence,
                    ),
                    FeatureView(
                        id=f"{stem.id}:timbre.mfcc_stats",
                        owner_type=OwnerType.STEM,
                        owner_id=stem.id,
                        feature_type=FeatureType.TIMBRE_MFCC_STATS,
                        algorithm=other_summary.analyzer,
                        algorithm_version=other_summary.analyzer_version,
                        params_hash=f"sample_rate={self._sample_rate}",
                        stats=_vector_stats("mfcc", other_summary.mfcc),
                        confidence=other_summary.confidence,
                    ),
                ]
            )
        else:
            return []

        for view in views:
            self._store.replace_feature_view_for_owner(view)
        return views

    def analyze_source(self, source: Source) -> list[FeatureView]:
        """Extract routed Phase 3 feature views for a compatible source."""
        events = self.infer_source_chords(source)
        return self.chord_feature_views(source, events)

    def analyze_production_texture(self, track: Track) -> FeatureView:
        """Extract and persist Phase 5 track-level production texture."""
        summary = summarize_production_texture(track.filepath, sample_rate=self._sample_rate)
        view = FeatureView(
            id=f"{track.id}:production.texture",
            owner_type=OwnerType.TRACK,
            owner_id=track.id,
            feature_type=FeatureType.PRODUCTION_TEXTURE,
            algorithm=summary.analyzer,
            algorithm_version=summary.analyzer_version,
            params_hash=f"sample_rate={self._sample_rate}",
            stats=summary.stats,
            confidence=summary.confidence,
        )
        self._store.replace_feature_view_for_owner(view)
        return view

    def structure_feature_view(self, track: Track) -> FeatureView:
        """Create a structure.section_sequence view from existing section rows."""
        sections = self._store.list_sections_for_track(track.id)
        stats = _section_sequence_stats(sections, track.duration_sec)
        confidence_value = min(
            (section.confidence.value for section in sections),
            default=0.0,
        )
        view = FeatureView(
            id=f"{track.id}:structure.section_sequence",
            owner_type=OwnerType.TRACK,
            owner_id=track.id,
            feature_type=FeatureType.STRUCTURE_SECTION_SEQUENCE,
            algorithm="section_sequence_existing_rows",
            algorithm_version="0.1.0",
            params_hash="source=sqlite.sections",
            symbolic_json=json.dumps(
                {
                    "sections": [
                        {
                            "label": section.label,
                            "start_sec": section.start_sec,
                            "end_sec": section.end_sec,
                            "confidence": section.confidence.value,
                        }
                        for section in sections
                    ]
                },
                sort_keys=True,
            ),
            stats=stats,
            confidence=Confidence(confidence_value),
        )
        self._store.replace_feature_view_for_owner(view)
        return view

    def analyze_melody_contour(self, source: Source) -> FeatureView:
        """Extract melody contour for routed melodic or vocal-like sources."""
        if source.source_type not in {SourceType.MELODIC, SourceType.PITCHED_HARMONIC}:
            raise ValueError(
                f"Melody contour is not enabled for source type {source.source_type.value}"
            )
        stem = self._stem_for_source(source)
        if stem.artifact_path is None:
            raise ValueError(f"Source {source.id} parent stem has no artifact_path")
        summary = summarize_melody_contour(stem.artifact_path, sample_rate=self._sample_rate)
        view = FeatureView(
            id=f"{source.id}:melody.contour",
            owner_type=OwnerType.SOURCE,
            owner_id=source.id,
            feature_type=FeatureType.MELODY_CONTOUR,
            algorithm=summary.analyzer,
            algorithm_version=summary.analyzer_version,
            params_hash=f"sample_rate={self._sample_rate}",
            stats=summary.contour,
            confidence=Confidence(min(summary.confidence.value, source.confidence.value)),
        )
        self._store.replace_feature_view_for_owner(view)
        return view

    def analyze_source_timbre(self, source: Source) -> FeatureView:
        """Extract a source-owned timbre proxy using existing MFCC summaries."""
        if source.source_type not in {
            SourceType.MELODIC,
            SourceType.PITCHED_HARMONIC,
            SourceType.TEXTURE,
        }:
            raise ValueError(
                f"Source timbre is not enabled for source type {source.source_type.value}"
            )
        stem = self._stem_for_source(source)
        if stem.artifact_path is None:
            raise ValueError(f"Source {source.id} parent stem has no artifact_path")
        summary = summarize_mfcc(stem.artifact_path, sample_rate=self._sample_rate)
        texture = summarize_production_texture(stem.artifact_path, sample_rate=self._sample_rate)
        stats = _vector_stats("timbre", summary.mfcc)
        stats.update({f"texture_{key}": value for key, value in texture.stats.items()})
        view = FeatureView(
            id=f"{source.id}:timbre.embedding",
            owner_type=OwnerType.SOURCE,
            owner_id=source.id,
            feature_type=FeatureType.TIMBRE_EMBEDDING,
            algorithm=f"{summary.analyzer}_source_quality_proxy",
            algorithm_version=f"{summary.analyzer_version}+quality.1",
            params_hash=f"sample_rate={self._sample_rate};n_mfcc={summary.n_mfcc}",
            stats=stats,
            confidence=Confidence(
                min(summary.confidence.value, texture.confidence.value, source.confidence.value)
            ),
        )
        self._store.replace_feature_view_for_owner(view)
        return view

    def infer_source_chords(self, source: Source) -> list[ChordEvent]:
        """Infer and persist source chord events for pitched-harmonic sources only."""
        if source.source_type is not SourceType.PITCHED_HARMONIC:
            raise ValueError(
                f"Chord analysis is not enabled for source type {source.source_type.value}"
            )
        existing = self._store.list_chord_events_for_owner(source.id)
        if existing:
            return existing
        stem = self._stem_for_source(source)
        if stem.artifact_path is None:
            raise ValueError(f"Source {source.id} parent stem has no artifact_path")
        analysis = infer_source_chord_events(
            stem.artifact_path,
            owner_id=source.id,
            sample_rate=self._sample_rate,
        )
        for event in analysis.events:
            self._store.add_chord_event(event)
        return analysis.events

    def chord_feature_views(self, source: Source, events: list[ChordEvent]) -> list[FeatureView]:
        """Persist source-owned chord sequence and chord-change feature views."""
        if not events:
            return []
        sequence_tokens = normalize_chord_sequence(events)
        root_motion = root_motion_tokens(events)
        confidence = min(event.confidence.value for event in events)
        sequence = FeatureView(
            id=f"{source.id}:harmony.chord_sequence",
            owner_type=OwnerType.SOURCE,
            owner_id=source.id,
            feature_type=FeatureType.HARMONY_CHORD_SEQUENCE,
            algorithm=SOURCE_CHORD_ANALYZER_NAME,
            algorithm_version=SOURCE_CHORD_ANALYZER_VERSION,
            params_hash=f"sample_rate={self._sample_rate}",
            symbolic_json=json.dumps({"tokens": sequence_tokens}, sort_keys=True),
            stats=_token_histogram(sequence_tokens),
            confidence=Confidence(confidence),
        )
        change = FeatureView(
            id=f"{source.id}:harmony.chord_change",
            owner_type=OwnerType.SOURCE,
            owner_id=source.id,
            feature_type=FeatureType.HARMONY_CHORD_CHANGE,
            algorithm=SOURCE_CHORD_ANALYZER_NAME,
            algorithm_version=SOURCE_CHORD_ANALYZER_VERSION,
            params_hash=f"sample_rate={self._sample_rate}",
            symbolic_json=json.dumps({"root_motion": root_motion}, sort_keys=True),
            stats={f"interval_{index:02d}": float(root_motion.count(index)) for index in range(12)},
            confidence=Confidence(confidence),
        )
        views = [sequence, change]
        for view in views:
            self._store.replace_feature_view_for_owner(view)
        return views

    def _stem_for_source(self, source: Source) -> Stem:
        for stem in self._store.list_stems_for_track(source.track_id):
            if stem.id == source.parent_stem_id:
                return stem
        raise KeyError(f"Parent stem not found for source: {source.id}")

    def _emit_progress(self, stage: str, progress: float) -> None:
        if self._progress_callback is not None:
            self._progress_callback(stage, progress)


def _vector_stats(prefix: str, values: list[float]) -> dict[str, float]:
    return {f"{prefix}_{index:02d}": value for index, value in enumerate(values)}


def _token_histogram(tokens: list[str]) -> dict[str, float]:
    vocabulary = (
        "I",
        "bII",
        "II",
        "bIII",
        "III",
        "IV",
        "#IV",
        "V",
        "bVI",
        "VI",
        "bVII",
        "VII",
        "i",
        "bii",
        "ii",
        "iv",
        "#iv",
        "v",
    )
    counts: dict[str, float] = {f"token_{token}": 0.0 for token in vocabulary}
    for token in tokens:
        key = f"token_{token}"
        if key in counts:
            counts[key] += 1.0
    counts["token_count"] = float(len(tokens))
    return counts


def _section_sequence_stats(
    sections: list[SectionRecord],
    track_duration_sec: float | None,
) -> dict[str, float]:
    duration = max(track_duration_sec or 0.0, 0.0)
    stats = {
        "section_count": float(len(sections)),
        "average_section_fraction": 0.0,
        "duration_variation": 0.0,
        "label_variety": 0.0,
        "coverage": 0.0,
    }
    if not sections:
        return stats
    lengths = [max(0.0, section.end_sec - section.start_sec) for section in sections]
    total = sum(lengths)
    denominator = duration if duration > 0.0 else max(total, 1.0)
    mean_length = total / len(lengths)
    stats["average_section_fraction"] = mean_length / denominator
    stats["duration_variation"] = (
        0.0 if mean_length <= 0.0 else min(1.0, _std(lengths) / mean_length)
    )
    stats["label_variety"] = len({section.label.lower() for section in sections}) / len(sections)
    stats["coverage"] = min(1.0, total / denominator)
    return stats


def _std(values: list[float]) -> float:
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    return float((sum((value - mean) ** 2 for value in values) / len(values)) ** 0.5)
