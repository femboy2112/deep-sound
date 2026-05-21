from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType


def test_mir_quality_eval_generated_report_passes(tmp_path: Path) -> None:
    mir_quality = _load_mir_quality_module()

    report = mir_quality.build_report(fixture_mode="generated", output_dir=tmp_path / "run")
    mir_quality.write_reports(report)

    assert report.overall == "passed"
    assert {gate.name for gate in report.gates} >= {
        "tempo_stability",
        "chroma_chord_consistency",
        "melody_contour_shape",
        "drum_groove_proxy",
        "bass_motion_proxy",
        "quality_profile_source_routing",
        "confidence_bounds",
    }
    payload = json.loads(Path(mir_quality.JSON_REPORT_PATH).read_text(encoding="utf-8"))
    assert payload["overall"] == "passed"
    assert Path(mir_quality.MD_REPORT_PATH).is_file()


def _load_mir_quality_module() -> ModuleType:
    path = Path(__file__).resolve().parents[1] / "scripts" / "mir_quality_eval.py"
    spec = importlib.util.spec_from_file_location("deep_sound_mir_quality_eval_test", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
