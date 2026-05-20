"""Broad-stem separation providers for Phase 2."""

from __future__ import annotations

import hashlib
import shutil
import subprocess
from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from deep_sound.domain.confidence import Confidence
from deep_sound.domain.stem import StemType

BROAD_STEM_TYPES: tuple[StemType, ...] = (
    StemType.VOCALS,
    StemType.DRUMS,
    StemType.BASS,
    StemType.OTHER,
)


@dataclass(frozen=True, slots=True)
class SeparationArtifact:
    stem_type: StemType
    artifact_path: Path
    confidence: Confidence
    algorithm: str
    algorithm_version: str
    params_hash: str
    model_version: str
    input_hash: str


class SeparationProvider(ABC):
    algorithm: str
    algorithm_version: str
    model_version: str

    @abstractmethod
    def separate(self, input_path: Path, output_dir: Path) -> list[SeparationArtifact]:
        """Write broad-stem artifacts under `output_dir` and return provenance."""


class FakeSeparationProvider(SeparationProvider):
    """Deterministic provider for tests and dependency-light core verification."""

    algorithm = "fake-broad-stem-copy"
    algorithm_version = "1"
    model_version = "test-fixture"

    def __init__(self, confidence: Confidence | None = None) -> None:
        self._confidence = confidence or Confidence(0.5)

    def separate(self, input_path: Path, output_dir: Path) -> list[SeparationArtifact]:
        input_hash = file_sha256(input_path)
        params_hash = params_sha256({"provider": self.algorithm, "model": self.model_version})
        output_dir.mkdir(parents=True, exist_ok=True)
        artifacts: list[SeparationArtifact] = []
        for stem_type in BROAD_STEM_TYPES:
            artifact_path = output_dir / f"{stem_type.value}.wav"
            shutil.copyfile(input_path, artifact_path)
            artifacts.append(
                SeparationArtifact(
                    stem_type=stem_type,
                    artifact_path=artifact_path,
                    confidence=self._confidence,
                    algorithm=self.algorithm,
                    algorithm_version=self.algorithm_version,
                    params_hash=params_hash,
                    model_version=self.model_version,
                    input_hash=input_hash,
                )
            )
        return artifacts


class DemucsProvider(SeparationProvider):
    """Optional Demucs CLI adapter. Importing this class does not require Demucs."""

    algorithm = "demucs"
    algorithm_version = "4"

    def __init__(self, *, model_version: str = "htdemucs", executable: str = "demucs") -> None:
        self.model_version = model_version
        self._executable = executable

    def separate(self, input_path: Path, output_dir: Path) -> list[SeparationArtifact]:
        input_hash = file_sha256(input_path)
        params_hash = params_sha256(
            {"provider": self.algorithm, "model": self.model_version, "stems": "4"}
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        demucs_root = output_dir / "_demucs"
        command = [
            self._executable,
            "--two-stems",
            "none",
            "-n",
            self.model_version,
            "-o",
            str(demucs_root),
            str(input_path),
        ]
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
        except FileNotFoundError as exc:
            raise RuntimeError(
                "Demucs executable is not available; install the [demucs] extra."
            ) from exc
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.strip() if exc.stderr else "no stderr"
            raise RuntimeError(f"Demucs separation failed: {stderr}") from exc

        produced_dir = demucs_root / self.model_version / input_path.stem
        artifacts: list[SeparationArtifact] = []
        for stem_type in BROAD_STEM_TYPES:
            produced = produced_dir / f"{stem_type.value}.wav"
            if not produced.exists():
                raise RuntimeError(f"Demucs did not produce expected stem: {produced}")
            artifact_path = output_dir / f"{stem_type.value}.wav"
            shutil.copyfile(produced, artifact_path)
            artifacts.append(
                SeparationArtifact(
                    stem_type=stem_type,
                    artifact_path=artifact_path,
                    confidence=Confidence(0.75),
                    algorithm=self.algorithm,
                    algorithm_version=self.algorithm_version,
                    params_hash=params_hash,
                    model_version=self.model_version,
                    input_hash=input_hash,
                )
            )
        return artifacts


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def params_sha256(params: Mapping[str, str]) -> str:
    encoded = ";".join(f"{key}={params[key]}" for key in sorted(params))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
