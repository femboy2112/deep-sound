"""SQLite-backed metadata store. Spec §11.2, §17.1. Phase 1 target (P1-001)."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from uuid import uuid4

from deep_sound.domain.confidence import Confidence
from deep_sound.domain.feature_view import FeatureType, FeatureView, OwnerType
from deep_sound.domain.source import Source, SourceType
from deep_sound.domain.stem import Stem, StemType
from deep_sound.domain.track import Track

JobStatus = Literal["queued", "running", "completed", "failed", "canceled"]


@dataclass(frozen=True, slots=True)
class SectionRecord:
    id: str
    track_id: str
    start_sec: float
    end_sec: float
    label: str
    confidence: Confidence
    source: str = "auto"


@dataclass(frozen=True, slots=True)
class SourceActivityRecord:
    id: str
    source_id: str
    start_sec: float
    end_sec: float
    confidence: Confidence
    section_id: str | None = None


@dataclass(frozen=True, slots=True)
class SimilarityIndexRecord:
    id: str
    feature_type: str
    owner_type: str
    index_path: Path
    manifest_path: Path
    version: str
    created_at: str | None = None
    source_type_filter: str | None = None


@dataclass(frozen=True, slots=True)
class CorrectionRecord:
    id: str
    entity_type: str
    entity_id: str
    old_value_json: str
    new_value_json: str
    created_at: str | None = None


@dataclass(frozen=True, slots=True)
class JobRecord:
    id: str
    job_type: str
    target_type: str
    target_id: str
    status: JobStatus
    progress: float
    created_at: str
    updated_at: str
    error_message: str | None = None


class SqliteStore:
    """Embedded local metadata database with narrow DAO methods."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def init_schema(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(SCHEMA_SQL)

    def add_track(self, track: Track) -> Track:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO tracks (
                    id, filepath, title, artist, album, duration_sec, sample_rate,
                    audio_hash, import_status, analysis_status, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE(?, datetime('now')))
                """,
                (
                    track.id,
                    str(track.filepath),
                    track.title,
                    track.artist,
                    track.album,
                    track.duration_sec,
                    track.sample_rate,
                    track.audio_hash,
                    track.import_status,
                    track.analysis_status,
                    track.created_at,
                ),
            )
        return self.get_track(track.id)

    def get_track(self, track_id: str) -> Track:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM tracks WHERE id = ?", (track_id,)).fetchone()
        if row is None:
            raise KeyError(f"Track not found: {track_id}")
        return _track_from_row(row)

    def get_track_by_hash(self, audio_hash: str) -> Track | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM tracks
                WHERE audio_hash = ? AND import_status = 'imported'
                ORDER BY created_at ASC, id ASC
                LIMIT 1
                """,
                (audio_hash,),
            ).fetchone()
        return None if row is None else _track_from_row(row)

    def list_tracks(self) -> list[Track]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM tracks ORDER BY created_at ASC, id ASC").fetchall()
        return [_track_from_row(row) for row in rows]

    def add_section(self, section: SectionRecord) -> SectionRecord:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO sections (
                    id, track_id, start_sec, end_sec, label, confidence, source
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    section.id,
                    section.track_id,
                    section.start_sec,
                    section.end_sec,
                    section.label,
                    section.confidence.value,
                    section.source,
                ),
            )
        return section

    def list_sections_for_track(self, track_id: str) -> list[SectionRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM sections WHERE track_id = ? ORDER BY start_sec ASC, id ASC",
                (track_id,),
            ).fetchall()
        return [_section_from_row(row) for row in rows]

    def add_stem(self, stem: Stem) -> Stem:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO stems (
                    id, track_id, stem_type, artifact_path, model_name, model_version, confidence
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    stem.id,
                    stem.track_id,
                    stem.stem_type.value,
                    None if stem.artifact_path is None else str(stem.artifact_path),
                    stem.model_name,
                    stem.model_version,
                    stem.confidence.value,
                ),
            )
        return stem

    def list_stems_for_track(self, track_id: str) -> list[Stem]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM stems WHERE track_id = ? ORDER BY id ASC",
                (track_id,),
            ).fetchall()
        return [_stem_from_row(row) for row in rows]

    def add_source(self, source: Source) -> Source:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO sources (
                    id, track_id, parent_stem_id, source_type, source_label,
                    confidence, user_label, is_user_corrected
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source.id,
                    source.track_id,
                    source.parent_stem_id,
                    source.source_type.value,
                    source.source_label,
                    source.confidence.value,
                    source.user_label,
                    int(source.is_user_corrected),
                ),
            )
        return source

    def list_sources_for_track(self, track_id: str) -> list[Source]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM sources WHERE track_id = ? ORDER BY id ASC",
                (track_id,),
            ).fetchall()
        return [_source_from_row(row) for row in rows]

    def add_source_activity(self, activity: SourceActivityRecord) -> SourceActivityRecord:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO source_activity (
                    id, source_id, section_id, start_sec, end_sec, confidence
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    activity.id,
                    activity.source_id,
                    activity.section_id,
                    activity.start_sec,
                    activity.end_sec,
                    activity.confidence.value,
                ),
            )
        return activity

    def list_source_activity(self, source_id: str) -> list[SourceActivityRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM source_activity WHERE source_id = ? ORDER BY start_sec ASC, id ASC",
                (source_id,),
            ).fetchall()
        return [_source_activity_from_row(row) for row in rows]

    def add_feature_view(self, view: FeatureView) -> FeatureView:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO feature_views (
                    id, owner_type, owner_id, feature_type, vector_path,
                    symbolic_json, stats_json, algorithm, algorithm_version,
                    params_hash, confidence
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    view.id,
                    view.owner_type.value,
                    view.owner_id,
                    view.feature_type.value,
                    None if view.vector_path is None else str(view.vector_path),
                    view.symbolic_json,
                    json.dumps(view.stats, sort_keys=True),
                    view.algorithm,
                    view.algorithm_version,
                    view.params_hash,
                    None if view.confidence is None else view.confidence.value,
                ),
            )
        return view

    def list_feature_views_for_owner(self, owner_id: str) -> list[FeatureView]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM feature_views WHERE owner_id = ? ORDER BY feature_type ASC, id ASC",
                (owner_id,),
            ).fetchall()
        return [_feature_view_from_row(row) for row in rows]

    def add_similarity_index(self, record: SimilarityIndexRecord) -> SimilarityIndexRecord:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO similarity_indices (
                    id, feature_type, owner_type, source_type_filter,
                    index_path, manifest_path, version, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, COALESCE(?, datetime('now')))
                """,
                (
                    record.id,
                    record.feature_type,
                    record.owner_type,
                    record.source_type_filter,
                    str(record.index_path),
                    str(record.manifest_path),
                    record.version,
                    record.created_at,
                ),
            )
        return self.get_similarity_index(record.id)

    def get_similarity_index(self, index_id: str) -> SimilarityIndexRecord:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM similarity_indices WHERE id = ?",
                (index_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"Similarity index not found: {index_id}")
        return _similarity_index_from_row(row)

    def list_similarity_indices(
        self, feature_type: str | None = None
    ) -> list[SimilarityIndexRecord]:
        sql = "SELECT * FROM similarity_indices"
        params: tuple[str, ...] = ()
        if feature_type is not None:
            sql += " WHERE feature_type = ?"
            params = (feature_type,)
        sql += " ORDER BY created_at ASC, id ASC"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [_similarity_index_from_row(row) for row in rows]

    def add_correction(self, record: CorrectionRecord) -> CorrectionRecord:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO corrections (
                    id, entity_type, entity_id, old_value_json, new_value_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, COALESCE(?, datetime('now')))
                """,
                (
                    record.id,
                    record.entity_type,
                    record.entity_id,
                    record.old_value_json,
                    record.new_value_json,
                    record.created_at,
                ),
            )
        return self.get_correction(record.id)

    def get_correction(self, correction_id: str) -> CorrectionRecord:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM corrections WHERE id = ?",
                (correction_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"Correction not found: {correction_id}")
        return _correction_from_row(row)

    def list_corrections(self, entity_id: str | None = None) -> list[CorrectionRecord]:
        sql = "SELECT * FROM corrections"
        params: tuple[str, ...] = ()
        if entity_id is not None:
            sql += " WHERE entity_id = ?"
            params = (entity_id,)
        sql += " ORDER BY created_at ASC, id ASC"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [_correction_from_row(row) for row in rows]

    def create_job(
        self,
        *,
        job_type: str,
        target_type: str,
        target_id: str,
        status: JobStatus = "queued",
        progress: float = 0.0,
        error_message: str | None = None,
        job_id: str | None = None,
    ) -> JobRecord:
        normalized_progress = _clamp_progress(progress)
        resolved_id = job_id or str(uuid4())
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO jobs (
                    id, job_type, target_type, target_id, status, progress,
                    error_message, created_at, updated_at
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now')
                )
                """,
                (
                    resolved_id,
                    job_type,
                    target_type,
                    target_id,
                    status,
                    normalized_progress,
                    error_message,
                ),
            )
        return self.get_job(resolved_id)

    def update_job(
        self,
        job_id: str,
        *,
        status: JobStatus | None = None,
        progress: float | None = None,
        error_message: str | None = None,
    ) -> JobRecord:
        assignments: list[str] = ["updated_at = datetime('now')"]
        values: list[str | float | None] = []
        if status is not None:
            assignments.append("status = ?")
            values.append(status)
        if progress is not None:
            assignments.append("progress = ?")
            values.append(_clamp_progress(progress))
        if error_message is not None:
            assignments.append("error_message = ?")
            values.append(error_message)
        values.append(job_id)
        with self._connect() as conn:
            conn.execute(
                f"UPDATE jobs SET {', '.join(assignments)} WHERE id = ?",
                values,
            )
        return self.get_job(job_id)

    def get_job(self, job_id: str) -> JobRecord:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if row is None:
            raise KeyError(f"Job not found: {job_id}")
        return _job_from_row(row)

    def list_jobs(self, status: JobStatus | None = None) -> list[JobRecord]:
        sql = "SELECT * FROM jobs"
        params: tuple[str, ...] = ()
        if status is not None:
            sql += " WHERE status = ?"
            params = (status,)
        sql += " ORDER BY created_at ASC, id ASC"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [_job_from_row(row) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn


def _track_from_row(row: sqlite3.Row) -> Track:
    return Track(
        id=str(row["id"]),
        filepath=Path(str(row["filepath"])),
        title=_optional_str(row["title"]),
        artist=_optional_str(row["artist"]),
        album=_optional_str(row["album"]),
        duration_sec=_optional_float(row["duration_sec"]),
        sample_rate=_optional_int(row["sample_rate"]),
        audio_hash=_optional_str(row["audio_hash"]),
        import_status=str(row["import_status"]),
        analysis_status=str(row["analysis_status"]),
        created_at=str(row["created_at"]),
    )


def _stem_from_row(row: sqlite3.Row) -> Stem:
    artifact_path = _optional_str(row["artifact_path"])
    return Stem(
        id=str(row["id"]),
        track_id=str(row["track_id"]),
        stem_type=StemType(str(row["stem_type"])),
        artifact_path=None if artifact_path is None else Path(artifact_path),
        model_name=_optional_str(row["model_name"]),
        model_version=_optional_str(row["model_version"]),
        confidence=Confidence(float(row["confidence"])),
    )


def _section_from_row(row: sqlite3.Row) -> SectionRecord:
    return SectionRecord(
        id=str(row["id"]),
        track_id=str(row["track_id"]),
        start_sec=float(row["start_sec"]),
        end_sec=float(row["end_sec"]),
        label=str(row["label"]),
        confidence=Confidence(float(row["confidence"])),
        source=str(row["source"]),
    )


def _source_from_row(row: sqlite3.Row) -> Source:
    return Source(
        id=str(row["id"]),
        track_id=str(row["track_id"]),
        parent_stem_id=str(row["parent_stem_id"]),
        source_type=SourceType(str(row["source_type"])),
        source_label=str(row["source_label"]),
        confidence=Confidence(float(row["confidence"])),
        user_label=_optional_str(row["user_label"]),
        is_user_corrected=bool(row["is_user_corrected"]),
    )


def _source_activity_from_row(row: sqlite3.Row) -> SourceActivityRecord:
    return SourceActivityRecord(
        id=str(row["id"]),
        source_id=str(row["source_id"]),
        section_id=_optional_str(row["section_id"]),
        start_sec=float(row["start_sec"]),
        end_sec=float(row["end_sec"]),
        confidence=Confidence(float(row["confidence"])),
    )


def _feature_view_from_row(row: sqlite3.Row) -> FeatureView:
    confidence = row["confidence"]
    return FeatureView(
        id=str(row["id"]),
        owner_type=OwnerType(str(row["owner_type"])),
        owner_id=str(row["owner_id"]),
        feature_type=FeatureType(str(row["feature_type"])),
        vector_path=None if row["vector_path"] is None else Path(str(row["vector_path"])),
        symbolic_json=_optional_str(row["symbolic_json"]),
        stats=_stats_from_json(str(row["stats_json"])),
        algorithm=str(row["algorithm"]),
        algorithm_version=str(row["algorithm_version"]),
        params_hash=str(row["params_hash"]),
        confidence=None if confidence is None else Confidence(float(confidence)),
    )


def _similarity_index_from_row(row: sqlite3.Row) -> SimilarityIndexRecord:
    return SimilarityIndexRecord(
        id=str(row["id"]),
        feature_type=str(row["feature_type"]),
        owner_type=str(row["owner_type"]),
        source_type_filter=_optional_str(row["source_type_filter"]),
        index_path=Path(str(row["index_path"])),
        manifest_path=Path(str(row["manifest_path"])),
        version=str(row["version"]),
        created_at=str(row["created_at"]),
    )


def _correction_from_row(row: sqlite3.Row) -> CorrectionRecord:
    return CorrectionRecord(
        id=str(row["id"]),
        entity_type=str(row["entity_type"]),
        entity_id=str(row["entity_id"]),
        old_value_json=str(row["old_value_json"]),
        new_value_json=str(row["new_value_json"]),
        created_at=str(row["created_at"]),
    )


def _job_from_row(row: sqlite3.Row) -> JobRecord:
    return JobRecord(
        id=str(row["id"]),
        job_type=str(row["job_type"]),
        target_type=str(row["target_type"]),
        target_id=str(row["target_id"]),
        status=_job_status(str(row["status"])),
        progress=float(row["progress"]),
        error_message=_optional_str(row["error_message"]),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def _stats_from_json(raw_json: str) -> dict[str, float]:
    decoded = json.loads(raw_json)
    if not isinstance(decoded, dict):
        raise ValueError("feature_views.stats_json must decode to an object")
    stats: dict[str, float] = {}
    for key, value in decoded.items():
        if not isinstance(key, str):
            raise ValueError("feature_views.stats_json keys must be strings")
        stats[key] = float(value)
    return stats


def _optional_str(value: object) -> str | None:
    return None if value is None else str(value)


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, str | int | float):
        return float(value)
    raise TypeError(f"Expected numeric SQLite value, got {type(value).__name__}")


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, str | int | float):
        return int(value)
    raise TypeError(f"Expected integer SQLite value, got {type(value).__name__}")


def _clamp_progress(progress: float) -> float:
    return max(0.0, min(1.0, float(progress)))


def _job_status(status: str) -> JobStatus:
    allowed: tuple[JobStatus, ...] = ("queued", "running", "completed", "failed", "canceled")
    if status not in allowed:
        raise ValueError(f"Unsupported job status: {status}")
    return status


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS tracks (
    id TEXT PRIMARY KEY,
    filepath TEXT NOT NULL,
    title TEXT,
    artist TEXT,
    album TEXT,
    duration_sec REAL,
    sample_rate INTEGER,
    audio_hash TEXT,
    import_status TEXT NOT NULL CHECK (import_status IN ('imported', 'missing', 'duplicate', 'failed')),
    analysis_status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_tracks_audio_hash_imported
ON tracks(audio_hash)
WHERE audio_hash IS NOT NULL AND import_status = 'imported';

CREATE INDEX IF NOT EXISTS idx_tracks_filepath ON tracks(filepath);

CREATE TABLE IF NOT EXISTS sections (
    id TEXT PRIMARY KEY,
    track_id TEXT NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
    start_sec REAL NOT NULL,
    end_sec REAL NOT NULL,
    label TEXT NOT NULL,
    confidence REAL NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    source TEXT NOT NULL CHECK (source IN ('auto', 'user')),
    CHECK (end_sec >= start_sec)
);

CREATE TABLE IF NOT EXISTS stems (
    id TEXT PRIMARY KEY,
    track_id TEXT NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
    stem_type TEXT NOT NULL,
    artifact_path TEXT,
    model_name TEXT,
    model_version TEXT,
    confidence REAL NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0)
);

CREATE INDEX IF NOT EXISTS idx_stems_track_id ON stems(track_id);

CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    track_id TEXT NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
    parent_stem_id TEXT NOT NULL REFERENCES stems(id) ON DELETE CASCADE,
    source_type TEXT NOT NULL,
    source_label TEXT NOT NULL,
    confidence REAL NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    user_label TEXT,
    is_user_corrected INTEGER NOT NULL DEFAULT 0 CHECK (is_user_corrected IN (0, 1))
);

CREATE INDEX IF NOT EXISTS idx_sources_track_id ON sources(track_id);
CREATE INDEX IF NOT EXISTS idx_sources_parent_stem_id ON sources(parent_stem_id);

CREATE TABLE IF NOT EXISTS source_activity (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    section_id TEXT REFERENCES sections(id) ON DELETE SET NULL,
    start_sec REAL NOT NULL,
    end_sec REAL NOT NULL,
    confidence REAL NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    CHECK (end_sec >= start_sec)
);

CREATE INDEX IF NOT EXISTS idx_source_activity_source_id ON source_activity(source_id);

CREATE TABLE IF NOT EXISTS feature_views (
    id TEXT PRIMARY KEY,
    owner_type TEXT NOT NULL,
    owner_id TEXT NOT NULL,
    feature_type TEXT NOT NULL,
    vector_path TEXT,
    symbolic_json TEXT,
    stats_json TEXT,
    algorithm TEXT NOT NULL,
    algorithm_version TEXT NOT NULL,
    params_hash TEXT NOT NULL,
    confidence REAL CHECK (confidence >= 0.0 AND confidence <= 1.0)
);

CREATE INDEX IF NOT EXISTS idx_feature_views_owner ON feature_views(owner_type, owner_id);
CREATE INDEX IF NOT EXISTS idx_feature_views_feature_type ON feature_views(feature_type);

CREATE TABLE IF NOT EXISTS chord_events (
    id TEXT PRIMARY KEY,
    owner_type TEXT NOT NULL,
    owner_id TEXT NOT NULL,
    start_sec REAL NOT NULL,
    end_sec REAL NOT NULL,
    chord_label TEXT NOT NULL,
    roman_numeral TEXT,
    root TEXT,
    quality TEXT,
    bass_note TEXT,
    confidence REAL NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    source TEXT NOT NULL CHECK (source IN ('auto', 'user')),
    CHECK (end_sec >= start_sec)
);

CREATE TABLE IF NOT EXISTS note_events (
    id TEXT PRIMARY KEY,
    owner_type TEXT NOT NULL,
    owner_id TEXT NOT NULL,
    start_sec REAL NOT NULL,
    end_sec REAL NOT NULL,
    pitch_midi REAL NOT NULL,
    pitch_name TEXT NOT NULL,
    velocity REAL,
    confidence REAL NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    CHECK (end_sec >= start_sec)
);

CREATE TABLE IF NOT EXISTS similarity_indices (
    id TEXT PRIMARY KEY,
    feature_type TEXT NOT NULL,
    owner_type TEXT NOT NULL,
    source_type_filter TEXT,
    index_path TEXT NOT NULL,
    manifest_path TEXT NOT NULL,
    version TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_similarity_indices_feature_type
ON similarity_indices(feature_type);

CREATE TABLE IF NOT EXISTS corrections (
    id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    old_value_json TEXT NOT NULL,
    new_value_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_corrections_entity ON corrections(entity_type, entity_id);

CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    job_type TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'completed', 'failed', 'canceled')),
    progress REAL NOT NULL CHECK (progress >= 0.0 AND progress <= 1.0),
    error_message TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_target ON jobs(target_type, target_id);
"""
