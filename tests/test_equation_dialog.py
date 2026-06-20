"""Tests for EquationDialog.build_markdown output."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from epy_reports.equation_dialog import EquationDialog

_app: QApplication | None = None


@pytest.fixture(scope="module")
def qapp():
    """Provide a module-scoped QApplication instance."""
    global _app
    if _app is None:
        _app = QApplication.instance() or QApplication([])
    return _app


def test_build_markdown_format(qapp):
    """build_markdown returns '$$\\n<body>\\n$$ {#eq-id}'."""
    dlg = EquationDialog(default_id="2")
    dlg.body_edit.setPlainText("E = mc^2")
    dlg.id_edit.setText("2")
    md = dlg.build_markdown()
    assert md == "$$\nE = mc^2\n$$ {#eq-2}"


def test_default_id_prefilled(qapp):
    """default_id is shown in the Reference ID field."""
    dlg = EquationDialog(default_id="4")
    assert dlg.id_edit.text() == "4"


def test_reference_id_property(qapp):
    """reference_id returns the id field text."""
    dlg = EquationDialog(default_id="1")
    dlg.id_edit.setText("euler-beam")
    assert dlg.reference_id == "euler-beam"


def test_reference_id_fallback(qapp):
    """Empty id field falls back to default_id."""
    dlg = EquationDialog(default_id="9")
    dlg.id_edit.setText("")
    assert dlg.reference_id == "9"


def test_body_property(qapp):
    """body property returns stripped plain text."""
    dlg = EquationDialog(default_id="1")
    dlg.body_edit.setPlainText("  y = ax + b  ")
    assert dlg.body == "y = ax + b"


def test_default_body(qapp):
    """Default body is 'y = f(x)'."""
    dlg = EquationDialog(default_id="1")
    assert "y = f(x)" in dlg.body


def test_multiline_body(qapp):
    """Multi-line LaTeX body is preserved inside the $$ block."""
    dlg = EquationDialog(default_id="1")
    dlg.body_edit.setPlainText("\\sigma = \\frac{M \\cdot y}{I}")
    dlg.id_edit.setText("1")
    md = dlg.build_markdown()
    assert md.startswith("$$\n")
    assert md.endswith("$$ {#eq-1}")
    assert "\\sigma" in md


def test_opening_closing_delimiters(qapp):
    """Output starts with '$$' and the label line starts with '$$ '."""
    dlg = EquationDialog(default_id="1")
    dlg.id_edit.setText("1")
    md = dlg.build_markdown()
    lines = md.split("\n")
    assert lines[0] == "$$"
    assert lines[-1] == "$$ {#eq-1}"
