from __future__ import annotations

from pathlib import Path

import pytest

from deep_sound.domain.stem import StemType
from deep_sound.infra.separation import DemucsProvider
from tests.phase10_helpers import write_fake_demucs_executable


def test_demucs_provider_missing_executable_reports_opt_in_profile(
    tmp_path: Path,
    click_track_wav: Path,
) -> None:
    provider = DemucsProvider(executable=str(tmp_path / "missing-demucs"))

    with pytest.raises(RuntimeError, match="source_aware_real requires"):
        provider.separate(click_track_wav, tmp_path / "app_data" / "stems")


def test_demucs_provider_persists_validated_stems_with_provenance(
    tmp_path: Path,
    click_track_wav: Path,
) -> None:
    executable = write_fake_demucs_executable(tmp_path / "demucs")
    output_dir = tmp_path / "app_data" / "stems" / "track-1"
    original_bytes = click_track_wav.read_bytes()

    artifacts = DemucsProvider(executable=str(executable)).separate(click_track_wav, output_dir)

    assert {artifact.stem_type for artifact in artifacts} == {
        StemType.VOCALS,
        StemType.DRUMS,
        StemType.BASS,
        StemType.OTHER,
    }
    assert all(artifact.algorithm == "demucs" for artifact in artifacts)
    assert all(artifact.model_version == "htdemucs" for artifact in artifacts)
    assert all(artifact.input_hash for artifact in artifacts)
    assert all(artifact.params_hash for artifact in artifacts)
    assert all(artifact.artifact_path.parent == output_dir for artifact in artifacts)
    assert all(artifact.artifact_path.stat().st_size > 0 for artifact in artifacts)
    assert click_track_wav.read_bytes() == original_bytes


def test_demucs_provider_rejects_missing_expected_stems(
    tmp_path: Path,
    click_track_wav: Path,
) -> None:
    script = """#!/usr/bin/env python3
from __future__ import annotations

import shutil
import sys
from pathlib import Path

args = sys.argv[1:]
output_root = Path(args[args.index("-o") + 1])
model = args[args.index("-n") + 1]
input_path = Path(args[-1])
produced_dir = output_root / model / input_path.stem
produced_dir.mkdir(parents=True, exist_ok=True)
shutil.copyfile(input_path, produced_dir / "vocals.wav")
"""
    executable = tmp_path / "demucs"
    executable.write_text(script, encoding="utf-8")
    executable.chmod(0o755)

    with pytest.raises(RuntimeError, match="expected stem"):
        DemucsProvider(executable=str(executable)).separate(
            click_track_wav,
            tmp_path / "app_data" / "stems" / "track-1",
        )
