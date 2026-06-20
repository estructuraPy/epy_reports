"""Tests for FigureDialog.build_markdown output."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from epy_reports.figure_dialog import FigureDialog

_app: QApplication | None = None


@pytest.fixture(scope="module")
def qapp():
    """Provide a module-scoped QApplication instance."""
    global _app
    if _app is None:
        _app = QApplication.instance() or QApplication([])
    return _app


def test_build_markdown_format(qapp):
    """build_markdown returns '![cap](path){#fig-id width=80%}'."""
    dlg = FigureDialog(default_id="3")
    dlg.path_edit.setText("figures/beam.png")
    dlg.caption_edit.setText("Beam cross-section")
    dlg.width_edit.setText("80%")
    dlg.id_edit.setText("3")
    md = dlg.build_markdown()
    assert md == "![Beam cross-section](figures/beam.png){#fig-3 width=80%}"


def test_default_id_prefilled(qapp):
    """default_id is shown in the Reference ID field."""
    dlg = FigureDialog(default_id="7")
    assert dlg.id_edit.text() == "7"


def test_reference_id_property(qapp):
    """reference_id property returns the field text."""
    dlg = FigureDialog(default_id="1")
    dlg.id_edit.setText("my-figure")
    assert dlg.reference_id == "my-figure"


def test_reference_id_fallback(qapp):
    """Empty field falls back to default_id."""
    dlg = FigureDialog(default_id="5")
    dlg.id_edit.setText("")
    assert dlg.reference_id == "5"


def test_width_default(qapp):
    """Width defaults to '80%' when field is cleared."""
    dlg = FigureDialog(default_id="1")
    dlg.width_edit.setText("")
    assert dlg.width == "80%"


def test_custom_width(qapp):
    """Custom width appears in build_markdown output."""
    dlg = FigureDialog(default_id="1")
    dlg.path_edit.setText("img.png")
    dlg.caption_edit.setText("Test")
    dlg.width_edit.setText("60%")
    dlg.id_edit.setText("1")
    md = dlg.build_markdown()
    assert "width=60%" in md


def test_path_property(qapp):
    """path property returns stripped text."""
    dlg = FigureDialog(default_id="1")
    dlg.path_edit.setText("  figures/x.svg  ")
    assert dlg.path == "figures/x.svg"


def test_caption_in_alt_text(qapp):
    """Caption appears as the image alt text, not as a separate line."""
    dlg = FigureDialog(default_id="1")
    dlg.path_edit.setText("a.png")
    dlg.caption_edit.setText("My caption")
    dlg.id_edit.setText("1")
    md = dlg.build_markdown()
    assert md.startswith("![My caption]")
    assert "\n" not in md
