"""Conservative chroma-template source chord analyzer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import librosa
import numpy as np
import numpy.typing as npt

from deep_sound.domain.confidence import Confidence
from deep_sound.domain.harmony import ROOTS, ChordEvent, HarmonicOwnerType, roman_numeral
from deep_sound.infra.analyzers.tempo_librosa import DEFAULT_SAMPLE_RATE

ANALYZER_NAME = "source_chords_chroma_template"
ANALYZER_VERSION = "0.2.0"


@dataclass(frozen=True, slots=True)
class SourceChordAnalysis:
    events: list[ChordEvent]
    analyzer: str = ANALYZER_NAME
    analyzer_version: str = ANALYZER_VERSION


def infer_source_chord_events(
    path: Path,
    *,
    owner_id: str,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
) -> SourceChordAnalysis:
    y, sr = librosa.load(str(path), sr=sample_rate, mono=True)
    duration = float(librosa.get_duration(y=y, sr=sr))
    if y.size == 0 or duration <= 0.0:
        return SourceChordAnalysis(events=[])

    chroma_matrix = librosa.feature.chroma_stft(y=y, sr=sr, tuning=0.0)
    if chroma_matrix.size == 0:
        return SourceChordAnalysis(events=[])
    rms = np.asarray(librosa.feature.rms(y=y), dtype=np.float64)
    mean_rms = float(np.mean(rms)) if rms.size else 0.0
    if mean_rms < 1e-4:
        return SourceChordAnalysis(events=[])

    segments = _segment_chroma(chroma_matrix, duration)
    if not segments:
        return SourceChordAnalysis(events=[])

    preliminary: list[tuple[float, float, str, str, str, float]] = []
    for start_sec, end_sec, chroma in segments:
        root, quality, confidence = _classify_chord(chroma, mean_rms)
        if confidence.value < 0.15:
            continue
        label = f"{root}{'m' if quality == 'minor' else ''}"
        preliminary.append((start_sec, end_sec, root, quality, label, confidence.value))

    preliminary = _merge_adjacent_duplicates(preliminary)
    if not preliminary:
        return SourceChordAnalysis(events=[])

    key_root = _reference_root(preliminary)
    events = [
        ChordEvent(
            id=f"{owner_id}:chord:{index:03d}",
            owner_type=HarmonicOwnerType.SOURCE,
            owner_id=owner_id,
            start_sec=start,
            end_sec=end,
            chord_label=label,
            roman_numeral=roman_numeral(root, key_root, quality),
            root=root,
            quality=quality,
            bass_note=root,
            confidence=Confidence(confidence),
        )
        for index, (start, end, root, quality, label, confidence) in enumerate(preliminary)
    ]
    return SourceChordAnalysis(events=events)


def _segment_chroma(
    chroma_matrix: npt.NDArray[np.float64],
    duration: float,
    *,
    max_segments: int = 12,
) -> list[tuple[float, float, npt.NDArray[np.float64]]]:
    frame_count = chroma_matrix.shape[1]
    if frame_count <= 0:
        return []
    frame_edges = _chroma_change_edges(chroma_matrix, max_segments=max_segments)
    time_edges = [duration * edge / frame_count for edge in frame_edges]
    segments: list[tuple[float, float, npt.NDArray[np.float64]]] = []
    for left, right, start, end in zip(
        frame_edges[:-1],
        frame_edges[1:],
        time_edges[:-1],
        time_edges[1:],
        strict=True,
    ):
        if right <= left:
            continue
        chroma = np.asarray(np.mean(chroma_matrix[:, left:right], axis=1), dtype=np.float64)
        segments.append((float(start), float(end), chroma))
    return segments


def _chroma_change_edges(
    chroma_matrix: npt.NDArray[np.float64],
    *,
    max_segments: int,
) -> list[int]:
    frame_count = chroma_matrix.shape[1]
    if frame_count <= 1:
        return [0, frame_count]

    normalized = np.maximum(chroma_matrix.astype(np.float64), 0.0)
    totals = np.sum(normalized, axis=0, keepdims=True)
    normalized = np.divide(normalized, totals, out=np.zeros_like(normalized), where=totals > 0.0)
    deltas = np.linalg.norm(np.diff(normalized, axis=1), axis=0)
    if deltas.size == 0 or float(np.max(deltas)) <= 0.0:
        return [0, frame_count]

    threshold = float(np.mean(deltas) + 0.75 * np.std(deltas))
    min_gap = max(2, frame_count // max(max_segments * 2, 1))
    peaks: list[int] = []
    for index in range(1, deltas.size - 1):
        if len(peaks) >= max_segments - 1:
            break
        if (
            float(deltas[index]) >= threshold
            and float(deltas[index]) >= float(deltas[index - 1])
            and float(deltas[index]) >= float(deltas[index + 1])
            and (not peaks or index + 1 - peaks[-1] >= min_gap)
        ):
            peaks.append(index + 1)

    if not peaks:
        segment_count = max(1, min(max_segments, int(np.ceil(frame_count / 44.0))))
        return list(np.linspace(0, frame_count, segment_count + 1, dtype=int))
    return [0, *peaks, frame_count]


def _classify_chord(
    chroma: npt.NDArray[np.float64], mean_rms: float
) -> tuple[str, str, Confidence]:
    normalized = np.maximum(chroma, 0.0)
    total = float(np.sum(normalized))
    if total <= 0.0:
        return "C", "major", Confidence(0.0)
    normalized = normalized / total

    best_root = 0
    best_quality = "major"
    best_score = -1.0
    second_score = -1.0
    for root in range(12):
        for quality, intervals in {"major": (0, 4, 7), "minor": (0, 3, 7)}.items():
            template = np.zeros(12, dtype=np.float64)
            for interval in intervals:
                template[(root + interval) % 12] = 1.0 / 3.0
            score = float(np.dot(normalized, template))
            if score > best_score:
                second_score = best_score
                best_score = score
                best_root = root
                best_quality = quality
            elif score > second_score:
                second_score = score

    margin = max(0.0, best_score - max(0.0, second_score))
    best_intervals = (0, 3, 7) if best_quality == "minor" else (0, 4, 7)
    triad_energy = sum(
        float(normalized[(best_root + interval) % 12]) for interval in best_intervals
    )
    non_triad_energy = max(0.0, 1.0 - triad_energy)
    clarity = max(0.0, triad_energy - 0.5 * non_triad_energy)
    energy_factor = min(1.0, mean_rms * 20.0)
    confidence = Confidence(
        min(0.94, max(0.0, (0.55 * best_score + 0.30 * margin + 0.15 * clarity) * energy_factor))
    )
    return ROOTS[best_root], best_quality, confidence


def _merge_adjacent_duplicates(
    segments: list[tuple[float, float, str, str, str, float]],
) -> list[tuple[float, float, str, str, str, float]]:
    merged: list[tuple[float, float, str, str, str, float]] = []
    for start, end, root, quality, label, confidence in segments:
        if merged and merged[-1][4] == label:
            prior_start, _prior_end, prior_root, prior_quality, prior_label, prior_confidence = (
                merged[-1]
            )
            merged[-1] = (
                prior_start,
                end,
                prior_root,
                prior_quality,
                prior_label,
                max(prior_confidence, confidence),
            )
        else:
            merged.append((start, end, root, quality, label, confidence))
    return merged


def _reference_root(segments: list[tuple[float, float, str, str, str, float]]) -> str:
    weights: dict[str, float] = {}
    for start, end, root, _quality, _label, confidence in segments:
        weights[root] = weights.get(root, 0.0) + max(0.0, end - start) * confidence
    if not weights:
        return segments[0][2]
    return sorted(weights.items(), key=lambda item: (-item[1], item[0]))[0][0]
