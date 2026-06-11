"""Tests for ChecklistDialog.build_markdown output."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from epy_mdr.checklist_dialog import ChecklistDialog

# ---------------------------------------------------------------------------
# Module-scoped QApplication (required for any QWidget instantiation)
# ---------------------------------------------------------------------------

_app: QApplication | None = None


@pytest.fixture(scope="module")
def qapp():
    """Provide a module-scoped QApplication instance."""
    global _app
    if _app is None:
        _app = QApplication.instance() or QApplication([])
    return _app


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_default_item_count(qapp):
    """Default build_markdown produces exactly 3 checklist items."""
    dlg = ChecklistDialog()
    md = dlg.build_markdown()
    items = [ln for ln in md.splitlines() if ln.startswith("- [ ]")]
    assert len(items) == 3


def test_item_prefix(qapp):
    """Every item line starts with '- [ ] '."""
    dlg = ChecklistDialog()
    dlg.items_spin.setValue(5)
    md = dlg.build_markdown()
    items = [ln for ln in md.splitlines() if ln.strip()]
    checklist_items = [ln for ln in items if not ln.startswith("**")]
    assert all(ln.startswith("- [ ] ") for ln in checklist_items)


def test_item_numbering(qapp):
    """Items are numbered 1..N with 'Item N' placeholder text."""
    dlg = ChecklistDialog()
    dlg.items_spin.setValue(4)
    md = dlg.build_markdown()
    items = [ln for ln in md.splitlines() if ln.startswith("- [ ]")]
    assert items == [
        "- [ ] Item 1",
        "- [ ] Item 2",
        "- [ ] Item 3",
        "- [ ] Item 4",
    ]


def test_leading_blank_line(qapp):
    """build_markdown output starts with a blank line."""
    dlg = ChecklistDialog()
    md = dlg.build_markdown()
    assert md.startswith("\n"), (
        "Expected leading blank line for Markdown separation"
    )


def test_optional_title_present(qapp):
    """When a title is set, a bold title line appears before the items."""
    dlg = ChecklistDialog()
    dlg.items_spin.setValue(2)
    dlg.title_edit.setText("My Tasks")
    md = dlg.build_markdown()
    lines = md.splitlines()
    assert "**My Tasks**" in lines
    title_idx = lines.index("**My Tasks**")
    first_item_idx = next(
        i for i, ln in enumerate(lines) if ln.startswith("- [ ]")
    )
    assert title_idx < first_item_idx


def test_optional_title_absent(qapp):
    """When no title is given, no bold line appears in the output."""
    dlg = ChecklistDialog()
    dlg.title_edit.setText("")
    md = dlg.build_markdown()
    assert "**" not in md


def test_custom_item_count(qapp):
    """Spinbox value drives the exact number of output items."""
    dlg = ChecklistDialog()
    dlg.items_spin.setValue(7)
    md = dlg.build_markdown()
    items = [ln for ln in md.splitlines() if ln.startswith("- [ ]")]
    assert len(items) == 7


def test_trailing_newline(qapp):
    """build_markdown output ends with a newline character."""
    dlg = ChecklistDialog()
    md = dlg.build_markdown()
    assert md.endswith("\n")
