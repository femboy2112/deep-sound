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
from deep_sound.infra.analyzers.mfcc_librosa import summarize_mfcc
from deep_sound.infra.analyzers.other_stem import summarize_other_stem
from deep_sound.infra.analyzers.source_chords import infer_source_chord_events
from deep_sound.infra.analyzers.tempo_librosa import DEFAULT_SAMPLE_RATE, estimate_tempo
from deep_sound.infra.storage.sqlite_store import SqliteStore
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
        self._store.add_feature_view(rhythm)
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
        self._store.add_feature_view(harmony)
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
        self._store.add_feature_view(timbre)
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
            self._store.add_feature_view(view)
        return views

    def analyze_source(self, source: Source) -> list[FeatureView]:
        """Extract routed Phase 3 feature views for a compatible source."""
        events = self.infer_source_chords(source)
        return self.chord_feature_views(source, events)

    def infer_source_chords(self, source: Source) -> list[ChordEvent]:
        """Infer and persist source chord events for pitched-harmonic sources only."""
        if source.source_type is not SourceType.PITCHED_HARMONIC:
            raise ValueError(
                f"Chord analysis is not enabled for source type {source.source_type.value}"
            )
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
            algorithm="source_chords_chroma_template",
            algorithm_version="0.1.0",
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
            algorithm="source_chords_chroma_template",
            algorithm_version="0.1.0",
            params_hash=f"sample_rate={self._sample_rate}",
            symbolic_json=json.dumps({"root_motion": root_motion}, sort_keys=True),
            stats={f"interval_{index:02d}": float(root_motion.count(index)) for index in range(12)},
            confidence=Confidence(confidence),
        )
        views = [sequence, change]
        for view in views:
            self._store.add_feature_view(view)
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
