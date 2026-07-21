"""Tests for TableDialog — reference_id field and build_markdown output."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from epy_reports._ui.table_dialog import TableDialog

_app: QApplication | None = None


@pytest.fixture(scope="module")
def qapp():
    """Provide a module-scoped QApplication instance."""
    global _app
    if _app is None:
        _app = QApplication.instance() or QApplication([])
    return _app


def test_default_id_prefilled(qapp):
    """default_id is shown in the Reference ID field."""
    dlg = TableDialog(default_id="5")
    assert dlg.id_edit.text() == "5"


def test_reference_id_property(qapp):
    """reference_id property returns the field text."""
    dlg = TableDialog(default_id="1")
    dlg.id_edit.setText("beam-loads")
    assert dlg.reference_id == "beam-loads"


def test_reference_id_fallback_to_default(qapp):
    """Empty field falls back to default_id."""
    dlg = TableDialog(default_id="3")
    dlg.id_edit.setText("  ")
    assert dlg.reference_id == "3"


def test_build_markdown_uses_reference_id(qapp):
    """build_markdown emits ': caption {#tbl-<id>}'."""
    dlg = TableDialog(default_id="7")
    dlg.caption_edit.setText("Beam properties")
    dlg.id_edit.setText("7")
    md = dlg.build_markdown()
    assert ": Beam properties {#tbl-7}" in md


def test_id_distinct_from_caption_slug(qapp):
    """The id does not derive from the caption text."""
    dlg = TableDialog(default_id="2")
    dlg.caption_edit.setText("Long descriptive caption text here")
    dlg.id_edit.setText("2")
    md = dlg.build_markdown()
    # Must NOT contain a caption-derived slug
    assert "long-descriptive-caption" not in md
    assert "#tbl-2" in md


def test_caption_and_id_are_independent(qapp):
    """Caption and id fields can differ freely."""
    dlg = TableDialog(default_id="1")
    dlg.caption_edit.setText("Material strengths")
    dlg.id_edit.setText("42")
    md = dlg.build_markdown()
    assert "Material strengths" in md
    assert "#tbl-42" in md


def test_no_caption_omits_caption_line(qapp):
    """When caption is empty, no caption line is emitted."""
    dlg = TableDialog(default_id="1")
    dlg.caption_edit.setText("")
    md = dlg.build_markdown()
    # No caption line means no {#tbl-...} anchor in the output
    assert "#tbl-" not in md


def test_explicit_label_overrides_reference_id(qapp):
    """Passing an explicit label to build_markdown takes precedence."""
    dlg = TableDialog(default_id="1")
    dlg.caption_edit.setText("Override test")
    dlg.id_edit.setText("99")
    md = dlg.build_markdown(label="#tbl-explicit")
    assert "#tbl-explicit" in md
    assert "#tbl-99" not in md
