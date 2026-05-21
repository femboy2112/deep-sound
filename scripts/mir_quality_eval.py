"""Run generated-fixture MIR quality checks and write evidence reports."""
# ruff: noqa: E402

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

try:
    import numpy as np
    import soundfile as sf
except ModuleNotFoundError:
    if __name__ != "__main__" or os.environ.get("DEEP_SOUND_MIR_QUALITY_REEXEC") == "1":
        raise
    env = os.environ.copy()
    env["DEEP_SOUND_MIR_QUALITY_REEXEC"] = "1"
    os.execvpe("uv", ["uv", "run", "python3", str(Path(__file__).resolve()), *sys.argv[1:]], env)

from deep_sound.domain.feature_view import FeatureType
from deep_sound.domain.track import Track
from deep_sound.infra.analyzers.bass_stem import summarize_bass_stem
from deep_sound.infra.analyzers.chroma_librosa import summarize_chroma
from deep_sound.infra.analyzers.drum_stem import summarize_drum_stem
from deep_sound.infra.analyzers.melody_contour import summarize_melody_contour
from deep_sound.infra.analyzers.source_chords import infer_source_chord_events
from deep_sound.infra.analyzers.tempo_librosa import estimate_tempo
from deep_sound.infra.separation.providers import file_sha256
from deep_sound.infra.storage.sqlite_store import SqliteStore
from deep_sound.services.library_analysis_service import AnalysisProfile, LibraryAnalysisService

BUILD_DIR = REPO_ROOT / ".build"
JSON_REPORT_PATH = BUILD_DIR / "mir_quality_report.json"
MD_REPORT_PATH = BUILD_DIR / "mir_quality_report.md"
SAMPLE_RATE = 22_050


@dataclass(frozen=True, slots=True)
class QualityGate:
    name: str
    status: str
    summary: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MirQualityReport:
    timestamp: str
    overall: str
    fixture_mode: str
    run_dir: str
    gates: list[QualityGate]


def _utc_timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _safe_stamp() -> str:
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def _write_audio(path: Path, audio: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(path, np.clip(audio, -0.9, 0.9).astype(np.float32), SAMPLE_RATE)


def _tone(frequency: float, duration_sec: float, *, amplitude: float = 0.2) -> np.ndarray:
    t = np.linspace(0.0, duration_sec, int(SAMPLE_RATE * duration_sec), endpoint=False)
    return amplitude * np.sin(2.0 * np.pi * frequency * t)


def _clicks(duration_sec: float, *, bpm: float = 120.0, amplitude: float = 0.35) -> np.ndarray:
    samples = np.zeros(int(SAMPLE_RATE * duration_sec), dtype=np.float64)
    click_len = int(0.02 * SAMPLE_RATE)
    envelope = np.exp(-np.linspace(0, 6, click_len)).astype(np.float64)
    t = 0.0
    while t < duration_sec:
        start = int(t * SAMPLE_RATE)
        end = min(start + click_len, samples.shape[0])
        samples[start:end] += amplitude * envelope[: end - start]
        t += 60.0 / bpm
    return samples


def _chord_progression() -> np.ndarray:
    c_major = _tone(261.63, 1.5) + _tone(329.63, 1.5) + _tone(392.00, 1.5)
    g_major = _tone(196.00, 1.5) + _tone(246.94, 1.5) + _tone(392.00, 1.5)
    return np.concatenate([c_major, g_major])


def _rising_melody() -> np.ndarray:
    segments = [_tone(freq, 0.45, amplitude=0.25) for freq in (261.63, 293.66, 329.63, 392.0)]
    return np.concatenate(segments)


def _bass_motion() -> np.ndarray:
    segments = [_tone(freq, 0.5, amplitude=0.28) for freq in (82.41, 98.0, 110.0, 123.47)]
    return np.concatenate(segments)


def _prepare_generated_fixtures(run_dir: Path) -> dict[str, Path]:
    fixture_dir = run_dir / "fixtures"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "tempo": fixture_dir / "tempo_120.wav",
        "chords": fixture_dir / "chord_progression.wav",
        "melody": fixture_dir / "rising_melody.wav",
        "drums": fixture_dir / "drum_clicks.wav",
        "bass": fixture_dir / "bass_motion.wav",
        "mix": fixture_dir / "quality_mix.wav",
    }
    _write_audio(paths["tempo"], _clicks(4.0, bpm=120.0))
    _write_audio(paths["chords"], _chord_progression())
    _write_audio(paths["melody"], _rising_melody())
    _write_audio(paths["drums"], _clicks(3.0, bpm=120.0))
    _write_audio(paths["bass"], _bass_motion())
    mix = (
        1.5 * _pad(_chord_progression(), 4.0)
        + 0.8 * _pad(_rising_melody(), 4.0)
        + 0.8 * _pad(_bass_motion(), 4.0)
        + _clicks(4.0, bpm=120.0, amplitude=0.2)
    )
    _write_audio(paths["mix"], mix)
    return paths


def run_generated_quality(run_dir: Path) -> list[QualityGate]:
    paths = _prepare_generated_fixtures(run_dir)
    gates = [
        _tempo_gate(paths["tempo"]),
        _chroma_chord_gate(paths["chords"]),
        _melody_gate(paths["melody"]),
        _drum_gate(paths["drums"]),
        _bass_gate(paths["bass"]),
        _source_routing_gate(paths["mix"], run_dir),
    ]
    gates.append(_confidence_bounds_gate(gates))
    return gates


def _tempo_gate(path: Path) -> QualityGate:
    summary = estimate_tempo(path, sample_rate=SAMPLE_RATE)
    passed = 112.0 <= summary.tempo_bpm <= 128.0 and summary.confidence.value > 0.5
    return QualityGate(
        name="tempo_stability",
        status="passed" if passed else "failed",
        summary="Generated 120 BPM click fixture produced a bounded tempo estimate.",
        details={"tempo_bpm": summary.tempo_bpm, "confidence": summary.confidence.value},
    )


def _chroma_chord_gate(path: Path) -> QualityGate:
    chroma = summarize_chroma(path, sample_rate=SAMPLE_RATE)
    chords = infer_source_chord_events(path, owner_id="quality-source", sample_rate=SAMPLE_RATE)
    labels = [event.chord_label for event in chords.events]
    passed = bool(labels) and any(label.startswith("C") for label in labels)
    passed = passed and all(0.0 <= event.confidence.value <= 1.0 for event in chords.events)
    return QualityGate(
        name="chroma_chord_consistency",
        status="passed" if passed else "failed",
        summary="Generated chord fixture produced probabilistic chord events consistent with chroma.",
        details={
            "chroma_confidence": chroma.confidence.value,
            "labels": labels,
            "event_count": len(chords.events),
        },
    )


def _melody_gate(path: Path) -> QualityGate:
    summary = summarize_melody_contour(path, sample_rate=SAMPLE_RATE)
    contour = summary.contour
    passed = (
        contour["activity"] > 0.5
        and contour["upward_motion"] >= contour["downward_motion"]
        and summary.confidence.value > 0.3
    )
    return QualityGate(
        name="melody_contour_shape",
        status="passed" if passed else "failed",
        summary="Generated rising melody fixture produced active upward contour evidence.",
        details={"contour": contour, "confidence": summary.confidence.value},
    )


def _drum_gate(path: Path) -> QualityGate:
    summary = summarize_drum_stem(path, sample_rate=SAMPLE_RATE)
    passed = (
        summary.onset_density > 1.0
        and summary.groove_regularity > 0.5
        and summary.confidence.value > 0.3
    )
    return QualityGate(
        name="drum_groove_proxy",
        status="passed" if passed else "failed",
        summary="Generated click fixture produced drum onset and regularity evidence.",
        details={
            "onset_density": summary.onset_density,
            "groove_regularity": summary.groove_regularity,
            "transient_strength": summary.transient_strength,
            "confidence": summary.confidence.value,
        },
    )


def _bass_gate(path: Path) -> QualityGate:
    summary = summarize_bass_stem(path, sample_rate=SAMPLE_RATE)
    passed = (
        summary.low_energy_ratio > 0.5
        and summary.pitch_motion > 0.0
        and summary.root_stability > 0.2
        and summary.confidence.value > 0.4
    )
    return QualityGate(
        name="bass_motion_proxy",
        status="passed" if passed else "failed",
        summary="Generated bass fixture produced low-frequency and root-motion evidence.",
        details={
            "low_energy_ratio": summary.low_energy_ratio,
            "pitch_motion": summary.pitch_motion,
            "root_stability": summary.root_stability,
            "pitch_variety": summary.pitch_variety,
            "confidence": summary.confidence.value,
        },
    )


def _source_routing_gate(path: Path, run_dir: Path) -> QualityGate:
    store = SqliteStore(run_dir / "quality.sqlite")
    store.init_schema()
    track = store.add_track(
        Track(
            id="quality-track",
            filepath=path,
            duration_sec=4.0,
            sample_rate=SAMPLE_RATE,
            audio_hash=file_sha256(path),
        )
    )
    service = LibraryAnalysisService(store, app_data_dir=run_dir / "app_data")
    result = service.analyze_track(track, profile=AnalysisProfile.QUALITY)
    feature_types = {
        view.feature_type.value
        for owner_id in _owner_ids_for_quality_report(store, track.id)
        for view in store.list_feature_views_for_owner(owner_id)
    }
    expected = {
        FeatureType.RHYTHM_GLOBAL.value,
        FeatureType.HARMONY_CHROMA.value,
        FeatureType.TIMBRE_MFCC_STATS.value,
        FeatureType.PRODUCTION_TEXTURE.value,
        FeatureType.RHYTHM_DRUM.value,
        FeatureType.BASS_ROOT_MOTION.value,
        FeatureType.HARMONY_CHORD_SEQUENCE.value,
        FeatureType.MELODY_CONTOUR.value,
        FeatureType.TIMBRE_EMBEDDING.value,
    }
    passed = result.succeeded and expected <= feature_types
    return QualityGate(
        name="quality_profile_source_routing",
        status="passed" if passed else "failed",
        summary="Quality profile routed generated mix through fake stems and deterministic analyzers.",
        details={
            "profile": AnalysisProfile.QUALITY.value,
            "feature_count": len(feature_types),
            "feature_types": sorted(feature_types),
            "status": result.status,
            "error_message": result.error_message,
        },
    )


def _confidence_bounds_gate(gates: list[QualityGate]) -> QualityGate:
    confidence_values: list[float] = []
    for gate in gates:
        confidence = gate.details.get("confidence")
        if isinstance(confidence, int | float):
            confidence_values.append(float(confidence))
    passed = all(0.0 <= value <= 1.0 for value in confidence_values)
    return QualityGate(
        name="confidence_bounds",
        status="passed" if passed else "failed",
        summary="Generated quality checks kept reported confidence values bounded.",
        details={"confidence_values": confidence_values},
    )


def _owner_ids_for_quality_report(store: SqliteStore, track_id: str) -> list[str]:
    stems = store.list_stems_for_track(track_id)
    sources = store.list_sources_for_track(track_id)
    return [track_id, *(stem.id for stem in stems), *(source.id for source in sources)]


def _pad(audio: np.ndarray, duration_sec: float) -> np.ndarray:
    target = int(SAMPLE_RATE * duration_sec)
    if audio.shape[0] >= target:
        return audio[:target]
    return np.pad(audio, (0, target - audio.shape[0]))


def write_reports(report: MirQualityReport) -> None:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    JSON_REPORT_PATH.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True), encoding="utf-8"
    )
    lines = [
        "# MIR Quality Report",
        "",
        f"- Timestamp: `{report.timestamp}`",
        f"- Fixture mode: `{report.fixture_mode}`",
        f"- Overall: `{report.overall}`",
        f"- Run dir: `{report.run_dir}`",
        "",
        "## Gates",
        "",
    ]
    for gate in report.gates:
        lines.extend(
            [
                f"### {gate.name}: {gate.status}",
                "",
                gate.summary,
                "",
                f"Details: `{json.dumps(gate.details, sort_keys=True)}`",
                "",
            ]
        )
    MD_REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def build_report(*, fixture_mode: str, output_dir: Path | None = None) -> MirQualityReport:
    if fixture_mode != "generated":
        raise ValueError("Only --fixture-mode generated is supported in Phase 14")
    run_dir = output_dir or BUILD_DIR / f"mir_quality_{_safe_stamp()}"
    run_dir.mkdir(parents=True, exist_ok=True)
    gates = run_generated_quality(run_dir)
    overall = "passed" if all(gate.status == "passed" for gate in gates) else "failed"
    return MirQualityReport(
        timestamp=_utc_timestamp(),
        overall=overall,
        fixture_mode=fixture_mode,
        run_dir=str(run_dir),
        gates=gates,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture-mode", choices=["generated"], default="generated")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(fixture_mode=args.fixture_mode, output_dir=args.output_dir)
    write_reports(report)
    print(f"MIR quality overall: {report.overall}")
    print(f"JSON report: {JSON_REPORT_PATH}")
    print(f"Markdown report: {MD_REPORT_PATH}")
    if args.strict and report.overall != "passed":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
