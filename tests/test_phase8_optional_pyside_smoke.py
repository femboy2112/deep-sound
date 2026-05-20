from __future__ import annotations

import pytest


def test_phase8_optional_pyside_widget_factories_skip_without_ui_extra() -> None:
    pyside = pytest.importorskip("PySide6")
    assert pyside is not None
