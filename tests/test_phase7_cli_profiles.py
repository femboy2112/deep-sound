from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from deep_sound.cli import main
from deep_sound.domain.feature_view import FeatureType
from deep_sound.infra.storage.sqlite_store import SqliteStore


def test_analyze_library_cli_searchable_profile_materializes_expected_features(
    tmp_path: Path,
    click_track_wav: Path,
) -> None:
    db_path = tmp_path / "library.sqlite"
    runner = CliRunner()

    first = runner.invoke(
        main,
        [
            "analyze-library",
            "--library-db",
            str(db_path),
            "--import-path",
            str(click_track_wav),
            "--profile",
            "searchable",
        ],
    )
    second = runner.invoke(
        main,
        [
            "analyze-library",
            "--library-db",
            str(db_path),
            "--profile",
            "searchable",
        ],
    )

    assert first.exit_code == 0, first.output
    assert second.exit_code == 0, second.output
    assert "profile=searchable" in first.output
    assert "features=5" in second.output

    store = SqliteStore(db_path)
    track = store.list_tracks()[0]
    assert track.analysis_status == "searchable"
    assert {view.feature_type for view in store.list_feature_views_for_owner(track.id)} == {
        FeatureType.RHYTHM_GLOBAL,
        FeatureType.HARMONY_CHROMA,
        FeatureType.TIMBRE_MFCC_STATS,
        FeatureType.PRODUCTION_TEXTURE,
        FeatureType.STRUCTURE_SECTION_SEQUENCE,
    }
