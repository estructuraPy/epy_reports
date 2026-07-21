"""Tests for FootnoteDialog and next_footnote_suffix."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from epy_reports._ui.footnote_dialog import FootnoteDialog
from epy_reports._ui.tab import next_footnote_suffix

_app: QApplication | None = None


@pytest.fixture(scope="module")
def qapp():
    """Provide a module-scoped QApplication instance."""
    global _app
    if _app is None:
        _app = QApplication.instance() or QApplication([])
    return _app


def test_build_parts_default(qapp):
    dlg = FootnoteDialog(default_id="2")
    dlg.note_edit.setPlainText("A note about the method.")
    dlg.id_edit.setText("2")
    marker, definition = dlg.build_parts()
    assert marker == "[^fn-2]"
    assert definition == "[^fn-2]: A note about the method."


def test_note_text_fallback(qapp):
    dlg = FootnoteDialog(default_id="1")
    dlg.note_edit.setPlainText("   ")
    assert dlg.note_text == "Footnote text"


def test_reference_id_fallback(qapp):
    dlg = FootnoteDialog(default_id="5")
    dlg.id_edit.setText("")
    assert dlg.reference_id == "5"


def test_next_footnote_suffix_empty():
    assert next_footnote_suffix("No footnotes here.") == "1"


def test_next_footnote_suffix_increments():
    text = "Body [^fn-1] more [^fn-3] text.\n\n[^fn-1]: a\n[^fn-3]: b\n"
    assert next_footnote_suffix(text) == "4"


def test_next_footnote_suffix_ignores_non_integer():
    text = "See [^fn-note] and [^fn-2].\n"
    assert next_footnote_suffix(text) == "3"
