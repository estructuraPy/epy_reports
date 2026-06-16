"""Tests for the latex_catalog module."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from epy_mdr.equation_dialog import EquationDialog
from epy_mdr.latex_catalog import CATALOG, LatexEntry, find, total_entries

_app: QApplication | None = None


@pytest.fixture(scope="module")
def qapp():
    """Provide a module-scoped QApplication instance."""
    global _app
    if _app is None:
        _app = QApplication.instance() or QApplication([])
    return _app


def test_catalog_not_empty():
    """The catalog ships with at least one category and one entry."""
    assert CATALOG
    assert total_entries() > 0


def test_catalog_minimum_size():
    """We promised to cover practically every math need — keep it big."""
    assert total_entries() >= 100
    assert len(CATALOG) >= 6


def test_every_entry_is_a_latex_entry():
    """Type-check the catalog payload."""
    for category, entries in CATALOG.items():
        assert isinstance(category, str)
        assert entries, f"category {category!r} is empty"
        for entry in entries:
            assert isinstance(entry, LatexEntry)
            assert entry.label
            assert entry.latex
            assert entry.tooltip


def test_no_duplicate_labels_within_category():
    """A category should not show the same button twice."""
    for category, entries in CATALOG.items():
        labels = [e.label for e in entries]
        assert len(labels) == len(set(labels)), (
            f"duplicate label in {category!r}: {labels}"
        )


def test_find_by_tooltip_keyword():
    """The search helper matches against the tooltip."""
    hits = find("sumatoria")
    assert hits
    assert all("sumatoria" in entry.tooltip.lower() for _, entry in hits)


def test_find_by_latex_command():
    r"""The search helper matches against the LaTeX source."""
    hits = find(r"\sigma")
    assert hits


def test_find_case_insensitive():
    """The search helper is case-insensitive."""
    assert find("ALPHA") and find("alpha")


# ---------------------------------------------------------------------------
# Integration with EquationDialog
# ---------------------------------------------------------------------------


def test_equation_dialog_has_catalog_tabs(qapp):
    """The dialog exposes one tab per CATALOG category."""
    dlg = EquationDialog()
    assert dlg.catalog_tabs.count() == len(CATALOG)


def test_equation_dialog_insert_appends_latex(qapp):
    """_insert puts the LaTeX source at the body_edit caret."""
    dlg = EquationDialog()
    dlg.body_edit.setPlainText("")
    dlg._insert(r"\sigma_{ij}")
    assert r"\sigma_{ij}" in dlg.body_edit.toPlainText()


def test_equation_dialog_insert_preserves_existing_body(qapp):
    """Inserting at the caret preserves text before/after the caret."""
    dlg = EquationDialog()
    dlg.body_edit.setPlainText("E = mc^2")
    cursor = dlg.body_edit.textCursor()
    cursor.movePosition(cursor.MoveOperation.End)
    dlg.body_edit.setTextCursor(cursor)
    dlg._insert(r" + \hbar \omega")
    assert dlg.body_edit.toPlainText() == r"E = mc^2 + \hbar \omega"


def test_equation_dialog_build_markdown_after_insert(qapp):
    """build_markdown still emits the canonical form after insertions."""
    dlg = EquationDialog(default_id="hooke")
    dlg.body_edit.setPlainText("")
    dlg._insert(r"\sigma = E")
    dlg._insert(r" \cdot \varepsilon")
    md = dlg.build_markdown()
    assert md == "$$\n\\sigma = E \\cdot \\varepsilon\n$$ {#eq-hooke}"
