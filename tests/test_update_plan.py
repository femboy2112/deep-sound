from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from scripts import update_plan

PLAN_TEXT = """# FILE_PLAN

## Rows

| id | path | phase | spec_refs | status | depends_on | owner_agent | summary | verify | last_attempt | notes |
|---|---|---|---|---|---|---|---|---|---|---|
| P1-001 | src/a.py | 1 | §1 | DONE | - | build-engineer | first row | pytest | - | - |
"""


def _args(**overrides: object) -> argparse.Namespace:
    defaults: dict[str, object] = {
        "add_row": False,
        "id": "P1-001",
        "status": None,
        "path": None,
        "phase": None,
        "spec_refs": None,
        "depends_on": None,
        "owner_agent": None,
        "summary": None,
        "verify": None,
        "notes": None,
        "note": None,
        "last_attempt": None,
        "dry_run": False,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


@pytest.fixture()
def plan_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "FILE_PLAN.md"
    path.write_text(PLAN_TEXT)
    monkeypatch.setattr(update_plan, "PLAN_PATH", path)
    return path


def test_add_row_renders_in_phase_and_id_order(plan_path: Path) -> None:
    new_text, changes = update_plan.mutate(
        _args(
            add_row=True,
            id="P2-001",
            status="TODO",
            path="src/b.py",
            phase=2,
            spec_refs="§12",
            depends_on="P1-001",
            owner_agent="source-separation-specialist",
            summary="add broad stem provider",
            verify="pytest tests/test_demucs_provider.py",
        )
    )

    assert changes == ["P2-001: row added"]
    assert (
        "| P2-001 | src/b.py | 2 | §12 | TODO | P1-001 | "
        "source-separation-specialist | add broad stem provider | "
        "pytest tests/test_demucs_provider.py | - | - |"
    ) in new_text
    assert new_text.index("| P1-001 |") < new_text.index("| P2-001 |")
    assert plan_path.read_text() == PLAN_TEXT


def test_add_row_rejects_duplicate_id(plan_path: Path) -> None:
    with pytest.raises(SystemExit, match="already exists"):
        update_plan.mutate(
            _args(
                add_row=True,
                id="P1-001",
                status="TODO",
                path="src/b.py",
                phase=2,
                spec_refs="§12",
                depends_on="-",
                owner_agent="source-separation-specialist",
                summary="duplicate",
                verify="pytest",
            )
        )


@pytest.mark.parametrize("depends_on", ["P9-999", "P1-001,,P1-002", "bad-id"])
def test_add_row_rejects_malformed_dependencies(plan_path: Path, depends_on: str) -> None:
    with pytest.raises(SystemExit):
        update_plan.mutate(
            _args(
                add_row=True,
                id="P2-001",
                status="TODO",
                path="src/b.py",
                phase=2,
                spec_refs="§12",
                depends_on=depends_on,
                owner_agent="source-separation-specialist",
                summary="bad deps",
                verify="pytest",
            )
        )


def test_dry_run_cli_does_not_write(plan_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = update_plan.main_from_args(
        [
            "--add-row",
            "--id",
            "P2-001",
            "--path",
            "src/b.py",
            "--phase",
            "2",
            "--spec-refs",
            "§12",
            "--status",
            "TODO",
            "--depends-on",
            "P1-001",
            "--owner-agent",
            "source-separation-specialist",
            "--summary",
            "add broad stem provider",
            "--verify",
            "pytest",
            "--dry-run",
        ]
    )

    assert exit_code == 0
    assert "(dry-run: no write)" in capsys.readouterr().out
    assert plan_path.read_text() == PLAN_TEXT


def test_existing_row_status_update_still_renders_table(plan_path: Path) -> None:
    new_text, changes = update_plan.mutate(_args(status="IN_PROGRESS"))

    assert changes == ["P1-001: status DONE -> IN_PROGRESS"]
    assert "| P1-001 | src/a.py | 1 | §1 | IN_PROGRESS | - |" in new_text
