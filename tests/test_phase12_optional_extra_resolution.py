from __future__ import annotations

import re
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_demucs_extra_uses_cpu_pytorch_sources() -> None:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    demucs_deps = pyproject["project"]["optional-dependencies"]["demucs"]
    assert "torchaudio>=2.0" in demucs_deps

    uv_config = pyproject["tool"]["uv"]
    cpu_indexes = [index for index in uv_config["index"] if index["name"] == "pytorch-cpu"]
    assert cpu_indexes == [
        {
            "name": "pytorch-cpu",
            "url": "https://download.pytorch.org/whl/cpu",
            "explicit": True,
        }
    ]
    assert uv_config["sources"]["torch"] == {"index": "pytorch-cpu", "extra": "demucs"}
    assert uv_config["sources"]["torchaudio"] == {
        "index": "pytorch-cpu",
        "extra": "demucs",
    }


def test_lockfile_default_demucs_path_has_no_cuda_packages() -> None:
    lock_text = (REPO_ROOT / "uv.lock").read_text(encoding="utf-8")

    forbidden_package_names = {
        "nvidia-cublas",
        "nvidia-cuda-cupti",
        "nvidia-cuda-nvrtc",
        "nvidia-cuda-runtime",
        "nvidia-cudnn-cu13",
        "nvidia-cufft",
        "nvidia-cufile",
        "nvidia-curand",
        "nvidia-cusolver",
        "nvidia-cusparse",
        "nvidia-cusparselt-cu13",
        "nvidia-nccl-cu13",
        "nvidia-nvjitlink",
        "nvidia-nvshmem-cu13",
        "nvidia-nvtx",
        "triton",
    }
    package_names = set(re.findall(r'^name = "([^"]+)"$', lock_text, flags=re.MULTILINE))
    assert forbidden_package_names.isdisjoint(package_names)

    assert 'registry = "https://download.pytorch.org/whl/cpu"' in lock_text
    assert 'name = "pyside6"' in lock_text
