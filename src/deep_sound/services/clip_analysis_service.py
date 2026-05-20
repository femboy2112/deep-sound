"""Clip-owned feature materialization for interactive desktop queries."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import soundfile as sf

from deep_sound.domain.clip import ClipWindow
from deep_sound.domain.feature_view import FeatureType, FeatureView, OwnerType
from deep_sound.infra.analyzers.chroma_librosa import summarize_chroma
from deep_sound.infra.analyzers.mfcc_librosa import summarize_mfcc
from deep_sound.infra.analyzers.tempo_librosa import DEFAULT_SAMPLE_RATE, estimate_tempo
from deep_sound.infra.storage.sqlite_store import SqliteStore


@dataclass(frozen=True, slots=True)
class ClipAnalysisResult:
    clip: ClipWindow
    artifact_path: Path
    feature_views: tuple[FeatureView, ...]


class ClipAnalysisService:
    """Materialize selected clips as app-data artifacts and clip-owned features."""

    def __init__(
        self,
        store: SqliteStore,
        *,
        app_data_dir: Path,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
    ) -> None:
        self._store = store
        self._app_data_dir = app_data_dir
        self._sample_rate = sample_rate

    def analyze_clip(self, clip_id: str) -> ClipAnalysisResult:
        clip = self._store.get_clip_window(clip_id)
        track = self._store.get_track(clip.track_id)
        artifact_path = self._write_clip_artifact(clip, track.filepath)
        views = self._feature_views(clip, artifact_path)
        for view in views:
            self._store.replace_feature_view_for_owner(view)
        return ClipAnalysisResult(
            clip=clip,
            artifact_path=artifact_path,
            feature_views=tuple(views),
        )

    def _write_clip_artifact(self, clip: ClipWindow, track_path: Path) -> Path:
        data, source_sample_rate = sf.read(str(track_path), always_2d=True)
        start_sample = max(0, round(clip.start_sec * source_sample_rate))
        end_sample = min(len(data), round(clip.end_sec * source_sample_rate))
        if end_sample <= start_sample:
            raise ValueError(
                f"Clip {clip.id} has no readable audio in {clip.start_sec:.3f}-{clip.end_sec:.3f}s"
            )

        artifact_dir = self._app_data_dir / "clip_analysis" / clip.track_id
        artifact_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = artifact_dir / f"{clip.id}.wav"
        sf.write(str(artifact_path), data[start_sample:end_sample], source_sample_rate)
        return artifact_path

    def _feature_views(self, clip: ClipWindow, artifact_path: Path) -> list[FeatureView]:
        params_hash = (
            f"sample_rate={self._sample_rate};track_id={clip.track_id};"
            f"start_sec={clip.start_sec:.6f};end_sec={clip.end_sec:.6f}"
        )

        tempo = estimate_tempo(artifact_path, sample_rate=self._sample_rate)
        rhythm = FeatureView(
            id=f"{clip.id}:rhythm.global",
            owner_type=OwnerType.CLIP,
            owner_id=clip.id,
            feature_type=FeatureType.RHYTHM_GLOBAL,
            algorithm=tempo.analyzer,
            algorithm_version=tempo.analyzer_version,
            params_hash=params_hash,
            stats={
                "tempo_bpm": tempo.tempo_bpm,
                "beats_per_sec": len(tempo.beats_sec) / max(tempo.duration_sec, 1.0),
            },
            confidence=tempo.confidence,
        )

        chroma = summarize_chroma(artifact_path, sample_rate=self._sample_rate)
        harmony = FeatureView(
            id=f"{clip.id}:harmony.chroma",
            owner_type=OwnerType.CLIP,
            owner_id=clip.id,
            feature_type=FeatureType.HARMONY_CHROMA,
            algorithm=chroma.analyzer,
            algorithm_version=chroma.analyzer_version,
            params_hash=params_hash,
            stats=_vector_stats("chroma", chroma.chroma),
            confidence=chroma.confidence,
        )

        mfcc = summarize_mfcc(artifact_path, sample_rate=self._sample_rate)
        timbre = FeatureView(
            id=f"{clip.id}:timbre.mfcc_stats",
            owner_type=OwnerType.CLIP,
            owner_id=clip.id,
            feature_type=FeatureType.TIMBRE_MFCC_STATS,
            algorithm=mfcc.analyzer,
            algorithm_version=mfcc.analyzer_version,
            params_hash=f"{params_hash};n_mfcc={mfcc.n_mfcc}",
            stats=_vector_stats("mfcc", mfcc.mfcc),
            confidence=mfcc.confidence,
        )
        return [rhythm, harmony, timbre]


def _vector_stats(prefix: str, values: list[float]) -> dict[str, float]:
    return {f"{prefix}_{index:02d}": value for index, value in enumerate(values)}
