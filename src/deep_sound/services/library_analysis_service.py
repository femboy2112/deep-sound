"""Library analysis profiles for Phase 7 beta workflows."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from deep_sound.domain.feature_view import FeatureView
from deep_sound.domain.track import Track
from deep_sound.infra.separation import DemucsProvider, FakeSeparationProvider
from deep_sound.infra.storage.sqlite_store import SqliteStore
from deep_sound.services.analysis_service import AnalysisService
from deep_sound.services.source_service import SourceService


class AnalysisProfile(StrEnum):
    MINIMAL = "minimal"
    SEARCHABLE = "searchable"
    SOURCE_AWARE = "source_aware"
    SOURCE_AWARE_REAL = "source_aware_real"


@dataclass(frozen=True, slots=True)
class TrackAnalysisResult:
    track_id: str
    profile: AnalysisProfile
    status: str
    feature_views: tuple[FeatureView, ...] = ()
    error_message: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.error_message is None


@dataclass(frozen=True, slots=True)
class LibraryAnalysisSummary:
    profile: AnalysisProfile
    requested_count: int
    completed_count: int
    failed_count: int
    feature_count: int
    results: tuple[TrackAnalysisResult, ...]


class LibraryAnalysisService:
    """Thin profile orchestrator over analysis/source services.

    It does not introduce new analyzer behavior; it selects existing service
    calls and relies on canonical feature replacement for rerun safety.
    """

    def __init__(
        self,
        store: SqliteStore,
        *,
        analysis_service: AnalysisService | None = None,
        app_data_dir: Path | None = None,
        source_service: SourceService | None = None,
    ) -> None:
        self._store = store
        self._analysis = analysis_service or AnalysisService(store)
        self._app_data_dir = app_data_dir
        self._source_service = source_service

    def analyze_library(
        self,
        tracks: list[Track] | None = None,
        *,
        profile: AnalysisProfile | str = AnalysisProfile.MINIMAL,
    ) -> LibraryAnalysisSummary:
        selected_profile = normalize_analysis_profile(profile)
        selected_tracks = self._store.list_tracks() if tracks is None else tracks
        results = tuple(
            self.analyze_track(track, profile=selected_profile) for track in selected_tracks
        )
        completed_count = sum(1 for result in results if result.succeeded)
        feature_count = sum(len(result.feature_views) for result in results)
        return LibraryAnalysisSummary(
            profile=selected_profile,
            requested_count=len(selected_tracks),
            completed_count=completed_count,
            failed_count=len(results) - completed_count,
            feature_count=feature_count,
            results=results,
        )

    def analyze_track(
        self,
        track: Track,
        *,
        profile: AnalysisProfile | str = AnalysisProfile.MINIMAL,
    ) -> TrackAnalysisResult:
        selected_profile = normalize_analysis_profile(profile)
        try:
            self._store.update_track_analysis_status(track.id, "analyzing")
            views = self._analyze_track(track, selected_profile)
            self._store.update_track_analysis_status(track.id, selected_profile.value)
            return TrackAnalysisResult(
                track_id=track.id,
                profile=selected_profile,
                status=selected_profile.value,
                feature_views=tuple(views),
            )
        except Exception as exc:
            self._store.record_failed_analysis_job(
                target_type="track",
                target_id=track.id,
                error_message=str(exc),
                job_type=f"analyze_{selected_profile.value}",
            )
            return TrackAnalysisResult(
                track_id=track.id,
                profile=selected_profile,
                status="failed",
                error_message=str(exc),
            )

    def _analyze_track(self, track: Track, profile: AnalysisProfile) -> list[FeatureView]:
        views = list(self._analysis.analyze(track))
        if profile in {
            AnalysisProfile.SEARCHABLE,
            AnalysisProfile.SOURCE_AWARE,
            AnalysisProfile.SOURCE_AWARE_REAL,
        }:
            views.append(self._analysis.analyze_production_texture(track))
            views.append(self._analysis.structure_feature_view(track))
        if profile in {AnalysisProfile.SOURCE_AWARE, AnalysisProfile.SOURCE_AWARE_REAL}:
            views.extend(self._analyze_source_aware(track, profile=profile))
        return views

    def _analyze_source_aware(
        self,
        track: Track,
        *,
        profile: AnalysisProfile,
    ) -> list[FeatureView]:
        source_service = self._source_service or self._default_source_service(profile)
        views: list[FeatureView] = []
        stems = self._analysis.separate_stems(track, source_service)
        for stem in stems:
            views.extend(self._analysis.analyze_stem(stem))
            for source in source_service.discover_pitched_harmonic_sources(stem):
                views.extend(self._analysis.analyze_source(source))
                views.append(self._analysis.analyze_melody_contour(source))
                views.append(self._analysis.analyze_source_timbre(source))
        return views

    def _default_source_service(self, profile: AnalysisProfile) -> SourceService:
        if self._app_data_dir is None:
            raise RuntimeError(f"{profile.value} profile requires app_data_dir or source_service")
        separation_provider = (
            DemucsProvider()
            if profile is AnalysisProfile.SOURCE_AWARE_REAL
            else FakeSeparationProvider()
        )
        return SourceService(
            self._store,
            app_data_dir=self._app_data_dir,
            separation_provider=separation_provider,
        )


def normalize_analysis_profile(profile: AnalysisProfile | str) -> AnalysisProfile:
    if isinstance(profile, AnalysisProfile):
        return profile
    try:
        return AnalysisProfile(profile)
    except ValueError as exc:
        allowed = ", ".join(profile.value for profile in AnalysisProfile)
        raise ValueError(
            f"Unsupported analysis profile {profile!r}; choose one of {allowed}"
        ) from exc
