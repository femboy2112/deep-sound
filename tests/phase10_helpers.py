from __future__ import annotations

import os
from pathlib import Path


def write_fake_demucs_executable(path: Path) -> Path:
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
for stem in ("vocals", "drums", "bass", "other"):
    shutil.copyfile(input_path, produced_dir / f"{stem}.wav")
"""
    path.write_text(script, encoding="utf-8")
    os.chmod(path, 0o755)
    return path
