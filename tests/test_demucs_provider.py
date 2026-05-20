from __future__ import annotations

from pathlib import Path

from deep_sound.domain.stem import StemType
from deep_sound.infra.separation import FakeSeparationProvider


def test_fake_provider_writes_four_broad_stems_with_provenance(
    tmp_path: Path,
    click_track_wav: Path,
) -> None:
    original_bytes = click_track_wav.read_bytes()

    artifacts = FakeSeparationProvider().separate(click_track_wav, tmp_path / "stems")

    assert {artifact.stem_type for artifact in artifacts} == {
        StemType.VOCALS,
        StemType.DRUMS,
        StemType.BASS,
        StemType.OTHER,
    }
    assert all(artifact.artifact_path.exists() for artifact in artifacts)
    assert all(artifact.input_hash for artifact in artifacts)
    assert all(artifact.params_hash for artifact in artifacts)
    assert click_track_wav.read_bytes() == original_bytes
