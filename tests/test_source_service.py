from __future__ import annotations

from pathlib import Path

from deep_sound.domain.stem import StemType
from deep_sound.domain.track import Track
from deep_sound.infra.separation import FakeSeparationProvider
from deep_sound.infra.storage.sqlite_store import SqliteStore
from deep_sound.services.source_service import SourceService


def test_source_service_separates_and_builds_broad_source_graph(
    tmp_path: Path,
    click_track_wav: Path,
) -> None:
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    track = store.add_track(Track(id="track-1", filepath=click_track_wav, audio_hash="hash"))
    service = SourceService(
        store,
        app_data_dir=tmp_path / "app_data",
        separation_provider=FakeSeparationProvider(),
    )

    stems = service.separate_broad_stems(track)
    graph = service.source_graph(track.id)

    assert {stem.stem_type for stem in stems} == {
        StemType.VOCALS,
        StemType.DRUMS,
        StemType.BASS,
        StemType.OTHER,
    }
    assert len(graph.stems) == 4
    assert all(graph_stem.sources for graph_stem in graph.stems)
    assert all(
        graph_stem.stem.input_hash == track.audio_hash or graph_stem.stem.input_hash
        for graph_stem in graph.stems
    )
    assert {source.source_label for source in service.list_sources(track.id)} >= {
        "possible drums stem",
        "possible bass stem",
    }
