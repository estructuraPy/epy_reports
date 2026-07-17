"""Tests for the MarkdownTab editor/preview widget.

The synchronous editor actions (formatting, block insertion, bibliography
linking, dirty tracking) are exercised directly. Dialog-driven inserts are
covered by patching the dialog class with a fake that returns Accepted and a
known ``build_markdown`` payload. The async preview render machinery is not
driven here; only its synchronous entry points run during construction.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QApplication, QDialog

from epy_reports import tab as tab_mod
from epy_reports.tab import (
    MarkdownTab,
    next_footnote_suffix,
    next_label_suffix,
)

_app: QApplication | None = None


@pytest.fixture(scope="module")
def qapp():
    """Provide a module-scoped QApplication instance."""
    global _app
    if _app is None:
        _app = QApplication.instance() or QApplication([])
    return _app


@pytest.fixture
def tab(qapp):
    """Build a MarkdownTab and clean up its preview temp dir."""
    t = MarkdownTab()
    try:
        yield t
    finally:
        t.cleanup_preview_tmp()
        # Flush the deferred delete NOW (see test_app.py): zombie tabs with
        # WebEngine previews crash Qt's native teardown at exit.
        t.deleteLater()
        from PySide6.QtCore import QEvent

        qapp.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        qapp.processEvents()


# ---------------------------------------------------------------------------
# Module-level suffix helpers
# ---------------------------------------------------------------------------


def test_next_label_suffix_increments():
    text = "{#fig-1}\n{#fig-2}\n"
    assert next_label_suffix(text, "fig") == "3"


def test_next_label_suffix_starts_at_one():
    assert next_label_suffix("no labels", "tbl") == "1"


def test_next_footnote_suffix_increments():
    assert next_footnote_suffix("[^fn-1] and [^fn-4]") == "5"


def test_next_footnote_suffix_starts_at_one():
    assert next_footnote_suffix("no footnotes") == "1"


# ---------------------------------------------------------------------------
# Title / dirty / text state
# ---------------------------------------------------------------------------


def test_initial_state_is_untitled_and_clean(tab):
    assert tab.path is None
    assert tab.dirty is False
    assert tab.title() == "untitled.md"


def test_title_marks_dirty_with_asterisk(tab):
    tab.set_initial_text("body", path=None)
    tab.editor.setPlainText("edited")
    assert tab.dirty is True
    assert tab.title().endswith("*")


def test_set_initial_text_resets_dirty(tab):
    tab.editor.setPlainText("dirty")
    tab.set_initial_text("clean text", path=None)
    assert tab.dirty is False
    assert tab.text() == "clean text"


# ---------------------------------------------------------------------------
# Save / load / reload
# ---------------------------------------------------------------------------


def test_save_without_path_returns_false(tab):
    tab.set_initial_text("x", path=None)
    assert tab.save() is False


def test_save_writes_to_path(tab, tmp_path):
    target = tmp_path / "f.md"
    tab.set_initial_text("content here", path=target)
    assert tab.save() is True
    assert target.read_text(encoding="utf-8") == "content here"
    assert tab.dirty is False


def test_save_as_adopts_path(tab, tmp_path):
    target = tmp_path / "g.md"
    tab.set_initial_text("body", path=None)
    tab.save_as(target)
    assert tab.path == target
    assert target.read_text(encoding="utf-8") == "body"


def test_load_file_reads_from_disk(tab, tmp_path):
    src = tmp_path / "doc.md"
    src.write_text("# Loaded\n", encoding="utf-8")
    tab.load_file(src)
    assert "# Loaded" in tab.text()
    assert tab.path == src


def test_reload_discards_changes(tab, tmp_path):
    src = tmp_path / "r.md"
    src.write_text("original\n", encoding="utf-8")
    tab.load_file(src)
    tab.editor.setPlainText("edited")
    tab.reload()
    assert tab.text().strip() == "original"


def test_reload_without_path_is_noop(tab):
    tab.set_initial_text("x", path=None)
    tab.reload()  # must not raise


# ---------------------------------------------------------------------------
# Formatting actions (synchronous, no dialogs)
# ---------------------------------------------------------------------------


def test_toggle_bold_wraps_selection(tab):
    tab.set_initial_text("hello", path=None)
    cursor = tab.editor.textCursor()
    cursor.select(QTextCursor.SelectionType.Document)
    tab.editor.setTextCursor(cursor)
    tab.toggle_bold()
    assert "**hello**" in tab.text()


def test_toggle_italic_inserts_placeholder(tab):
    tab.set_initial_text("", path=None)
    tab.toggle_italic()
    assert "*italic*" in tab.text()


def test_toggle_inline_code_inserts_placeholder(tab):
    tab.set_initial_text("", path=None)
    tab.toggle_inline_code()
    assert "`code`" in tab.text()


def test_set_heading_level_applies_prefix(tab):
    tab.set_initial_text("My heading", path=None)
    tab.set_heading_level(2)
    assert tab.text().startswith("## My heading")


def test_set_heading_level_zero_strips_prefix(tab):
    tab.set_initial_text("### Already a heading", path=None)
    tab.set_heading_level(0)
    assert tab.text().startswith("Already a heading")


def test_set_heading_level_clamped_to_six(tab):
    tab.set_initial_text("Deep", path=None)
    tab.set_heading_level(9)
    assert tab.text().startswith("###### Deep")


def test_insert_link_with_selection(tab):
    tab.set_initial_text("anchor", path=None)
    cursor = tab.editor.textCursor()
    cursor.select(QTextCursor.SelectionType.Document)
    tab.editor.setTextCursor(cursor)
    tab.insert_link()
    assert "[anchor](URL)" in tab.text()


def test_insert_link_without_selection(tab):
    tab.set_initial_text("", path=None)
    tab.insert_link()
    assert "[TEXT](URL)" in tab.text()


# ---------------------------------------------------------------------------
# Block-insertion actions (no dialog)
# ---------------------------------------------------------------------------


def test_insert_page_break(tab):
    tab.set_initial_text("para", path=None)
    tab.insert_page_break()
    assert "[[pagebreak]]" in tab.text()


def test_insert_index_marker(tab):
    tab.set_initial_text("", path=None)
    tab.insert_index_marker("toc")
    assert "[[toc]]" in tab.text()


def test_insert_code_block(tab):
    tab.set_initial_text("", path=None)
    tab.insert_code_block()
    assert "```python" in tab.text()


def test_insert_callout_note_has_no_title_prompt(tab):
    tab.set_initial_text("", path=None)
    tab.insert_callout("note")
    assert ".callout-note" in tab.text()


def test_insert_callout_with_title_prompt(tab):
    tab.set_initial_text("", path=None)
    with patch(
        "PySide6.QtWidgets.QInputDialog.getText",
        return_value=("Heads up", True),
    ):
        tab.insert_callout("warning")
    assert ".callout-warning" in tab.text()
    assert "Heads up" in tab.text()


# ---------------------------------------------------------------------------
# Dialog-driven inserts (dialog patched with a fake)
# ---------------------------------------------------------------------------


def _fake_dialog(markdown: str):
    """Return a dialog class that accepts and yields ``markdown``."""

    class _Fake:
        def __init__(self, *a, **k):
            pass

        def exec(self):
            return QDialog.DialogCode.Accepted

        def build_markdown(self):
            return markdown

    return _Fake


def test_insert_section_heading(tab):
    tab.set_initial_text("", path=None)
    with patch(
        "PySide6.QtWidgets.QInputDialog.getText",
        return_value=("Intro", True),
    ):
        tab.insert_section_heading()
    text = tab.text()
    assert "## Intro {#sec-1}" in text


def test_insert_figure_uses_dialog_markdown(tab):
    tab.set_initial_text("para", path=None)
    with patch.object(
        tab_mod, "FigureDialog", _fake_dialog("![cap](x.png){#fig-1}")
    ):
        tab.insert_figure()
    assert "![cap](x.png){#fig-1}" in tab.text()


def test_insert_table_uses_dialog_markdown(tab):
    tab.set_initial_text("", path=None)
    with patch.object(
        tab_mod, "TableDialog", _fake_dialog("\n| a |\n| - |\n")
    ):
        tab.insert_table()
    assert "| a |" in tab.text()


def test_insert_equation_uses_dialog_markdown(tab):
    tab.set_initial_text("", path=None)
    with patch.object(
        tab_mod, "EquationDialog", _fake_dialog("$$x$$ {#eq-1}")
    ):
        tab.insert_equation()
    assert "$$x$$ {#eq-1}" in tab.text()


def test_insert_two_columns(tab):
    tab.set_initial_text("", path=None)
    with patch.object(
        tab_mod, "TwoColumnDialog", _fake_dialog("\n:::: {.columns}\n::::\n")
    ):
        tab.insert_two_columns()
    assert ":::: {.columns}" in tab.text()


def test_insert_footnote_appends_definition(tab):
    tab.set_initial_text("body", path=None)

    class _FakeFn:
        def __init__(self, *a, **k):
            pass

        def exec(self):
            return QDialog.DialogCode.Accepted

        def build_parts(self):
            return "[^fn-1]", "[^fn-1]: the note"

    with patch.object(tab_mod, "FootnoteDialog", _FakeFn):
        tab.insert_footnote()
    text = tab.text()
    assert "[^fn-1]" in text
    assert "[^fn-1]: the note" in text


# ---------------------------------------------------------------------------
# Bibliography helpers
# ---------------------------------------------------------------------------


def test_link_bibliography_writes_relative_path(tab, tmp_path):
    doc = tmp_path / "doc.md"
    tab.set_initial_text("# Doc\n", path=doc)
    bib_file = tmp_path / "refs.bib"
    bib_file.write_text("@misc{a, title={A}}\n", encoding="utf-8")
    tab.link_bibliography(bib_file)
    assert "bibliography: refs.bib" in tab.text()


def test_bib_path_resolves_relative(tab, tmp_path):
    doc = tmp_path / "doc.md"
    tab.set_initial_text(
        "---\nbibliography: refs.bib\n---\n\nBody\n", path=doc
    )
    resolved = tab.bib_path()
    assert resolved == (tmp_path / "refs.bib").resolve()


def test_bib_path_none_when_unset(tab):
    tab.set_initial_text("# no bib\n", path=None)
    assert tab.bib_path() is None


def test_bib_entries_reads_linked_file(tab, tmp_path):
    doc = tmp_path / "doc.md"
    bib_file = tmp_path / "refs.bib"
    bib_file.write_text(
        "@article{x, title={X}, author={A}, year={2020}}\n",
        encoding="utf-8",
    )
    tab.set_initial_text(
        "---\nbibliography: refs.bib\n---\n\nBody\n", path=doc
    )
    entries = tab.bib_entries()
    assert len(entries) == 1
    assert entries[0].key == "x"


def test_bib_entries_empty_without_link(tab):
    tab.set_initial_text("# nothing\n", path=None)
    assert tab.bib_entries() == []


# ---------------------------------------------------------------------------
# Cross-reference picker
# ---------------------------------------------------------------------------


def test_insert_cross_reference_informs_when_empty(tab):
    tab.set_initial_text("plain, nothing to cite\n", path=None)
    with patch(
        "epy_reports.tab.QMessageBox.information"
    ) as info:
        tab.insert_cross_reference()
    info.assert_called_once()


def test_insert_cross_reference_inserts_label(tab):
    tab.set_initial_text("![cap](x.png){#fig-1}\n\n", path=None)
    # Place caret at end of buffer.
    cursor = tab.editor.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    tab.editor.setTextCursor(cursor)

    class _FakeXref:
        def __init__(self, *a, **k):
            pass

        def exec(self):
            return QDialog.DialogCode.Accepted

        def selected_label(self):
            from epy_reports.snippets import Label

            return Label(kind="fig", name="fig-1")

    with patch.object(tab_mod, "CrossRefDialog", _FakeXref):
        tab.insert_cross_reference()
    assert "@fig-1" in tab.text()


# ---------------------------------------------------------------------------
# Page-layout helper + theme/paged setters
# ---------------------------------------------------------------------------


def test_set_theme_css_records_values(tab):
    tab.set_initial_text("# x\n", path=None)
    tab.set_theme_css(":root { --bg: #fff; }", "#fff")
    assert tab._theme_css == ":root { --bg: #fff; }"
    assert tab._page_bg == "#fff"


def test_set_paged_toggles_flag(tab):
    tab.set_initial_text("# x\n", path=None)
    tab.set_paged(True)
    assert tab._paged is True


def test_cleanup_preview_tmp_is_safe_twice(tab):
    tab.set_initial_text("# x\n", path=None)
    tab.cleanup_preview_tmp()
    tab.cleanup_preview_tmp()  # second call must not raise
