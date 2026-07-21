"""Tests for the CrossRefDialog label picker."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from epy_reports._core.bib import BibEntry
from epy_reports._core.snippets import Label
from epy_reports._ui.xref_dialog import CrossRefDialog

_app: QApplication | None = None


@pytest.fixture(scope="module")
def qapp():
    """Provide a module-scoped QApplication instance."""
    global _app
    if _app is None:
        _app = QApplication.instance() or QApplication([])
    return _app


_LABELS = [
    Label(kind="fig", name="fig-capacity"),
    Label(kind="tbl", name="tbl-loads"),
    Label(kind="eq", name="eq-euler"),
    Label(kind="sec", name="sec-intro"),
]


def test_dialog_lists_all_labels(qapp):
    """Every label appears as a list row."""
    dlg = CrossRefDialog(_LABELS)
    assert dlg.list_widget.count() == len(_LABELS)


def test_first_row_is_selected(qapp):
    """The first label is pre-selected so Enter inserts something."""
    dlg = CrossRefDialog(_LABELS)
    assert dlg.list_widget.currentRow() == 0


def test_selected_label_returns_current(qapp):
    """``selected_label`` returns the highlighted Label."""
    dlg = CrossRefDialog(_LABELS)
    dlg.list_widget.setCurrentRow(2)
    selected = dlg.selected_label()
    assert selected is not None
    assert selected.name == "eq-euler"


def test_filter_by_kind_keyword(qapp):
    """Typing a kind keyword narrows to that kind."""
    dlg = CrossRefDialog(_LABELS)
    dlg._refilter("fig")
    assert dlg.list_widget.count() == 1


def test_filter_by_substring(qapp):
    """Typing a substring matches any label name containing it."""
    dlg = CrossRefDialog(_LABELS)
    dlg._refilter("euler")
    assert dlg.list_widget.count() == 1


def test_empty_filter_shows_everything(qapp):
    """Clearing the filter restores the full list."""
    dlg = CrossRefDialog(_LABELS)
    dlg._refilter("fig")
    dlg._refilter("")
    assert dlg.list_widget.count() == len(_LABELS)


def test_citation_labels_use_bib_lookup(qapp):
    """A cite label renders its bibliography short label."""
    labels = [Label(kind="cite", name="smith2020")]
    lookup = {
        "smith2020": BibEntry(
            key="smith2020", type="article",
            title="On X", author="Smith, J", year="2020",
        )
    }
    dlg = CrossRefDialog(labels, bib_lookup=lookup)
    item = dlg.list_widget.item(0)
    assert "smith2020" in item.text()


def test_selected_label_none_when_empty(qapp):
    """An empty filter result yields no selection."""
    dlg = CrossRefDialog(_LABELS)
    dlg._refilter("nonexistent-substring-xyz")
    assert dlg.selected_label() is None
