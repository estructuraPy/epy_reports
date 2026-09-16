"""Tests for the MarkdownTab editor/preview widget.

The synchronous editor actions (formatting, block insertion, bibliography
linking, dirty tracking) are exercised directly. Dialog-driven inserts are
covered by patching the dialog class with a fake that returns Accepted and a
known ``build_markdown`` payload. The async preview render machinery is not
driven here; only its synchronous entry points run during construction.
"""

from __future__ import annotations

import base64
import time
from unittest.mock import patch

import pytest
from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QApplication, QDialog

from epy_reports._ui import tab as tab_mod
from epy_reports._ui.tab import (
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
        _instance = QApplication.instance()
        _app = (
            _instance
            if isinstance(_instance, QApplication)
            else QApplication([])
        )
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
# Preview navigation: popup links, back/forward, render history hygiene
# ---------------------------------------------------------------------------


def test_popup_links_open_in_system_browser(qapp, monkeypatch):
    """target=_blank navigation is handed to the OS browser."""
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtWebEngineCore import QWebEnginePage

    opened: list[str] = []
    monkeypatch.setattr(
        QDesktopServices, "openUrl", lambda url: opened.append(url.toString())
    )
    page = tab_mod._ExternalOpenPage(None)
    accepted = page.acceptNavigationRequest(
        QUrl("https://example.test/doc"),
        QWebEnginePage.NavigationType.NavigationTypeLinkClicked,
        True,
    )
    assert accepted is False
    assert opened == ["https://example.test/doc"]


def test_preview_view_creates_external_page(qapp):
    """createWindow returns the throwaway external-open page."""
    from PySide6.QtWebEngineCore import QWebEnginePage

    view = tab_mod._PreviewView()
    page = view.createWindow(QWebEnginePage.WebWindowType.WebBrowserTab)
    assert isinstance(page, tab_mod._ExternalOpenPage)
    view.deleteLater()


def test_render_load_clears_history_flagged(tab):
    """A flagged (render) load clears history; unflagged keeps it."""
    calls: list[str] = []

    class _FakeHistory:
        def clear(self):
            calls.append("clear")

    class _FakeView:
        def history(self):
            return _FakeHistory()

    tab.view = _FakeView()  # type: ignore[assignment] — behavioral stub
    tab._expect_render_load = True
    tab._on_preview_load_finished(True)
    assert calls == ["clear"]
    assert tab._expect_render_load is False

    tab._on_preview_load_finished(True)
    assert calls == ["clear"]


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


def test_next_label_suffix_ignores_other_kinds():
    """A mix of kinds counts only the requested one (max + 1 for THAT kind,
    not across kinds)."""
    text = "{#fig-1}\n{#tbl-1}\n{#tbl-2}\n"
    assert next_label_suffix(text, "fig") == "2"
    assert next_label_suffix(text, "tbl") == "3"


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


def test_setup_editor_falls_back_to_consolas_when_no_fixed_font(
    qapp, monkeypatch
):
    """No usable system fixed-pitch font (pointSize() < 1) falls back to
    Consolas, so the editor never ends up fontless."""
    from PySide6.QtGui import QFont

    monkeypatch.setattr(QFont, "pointSize", lambda self: 0)
    t = MarkdownTab()
    try:
        # pointSize() itself is patched to always read 0, so the family
        # name is the only unpatched signal that the fallback branch ran.
        assert t.editor.font().family() == "Consolas"
    finally:
        t.cleanup_preview_tmp()
        t.deleteLater()


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


def test_insert_page_break_mid_line_gets_own_line(tab):
    tab.set_initial_text("para", path=None)
    cursor = tab.editor.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    tab.editor.setTextCursor(cursor)
    tab.insert_page_break()
    assert "para\n[[pagebreak]]" in tab.text()


def test_insert_index_marker(tab):
    tab.set_initial_text("", path=None)
    tab.insert_index_marker("toc")
    assert "[[toc]]" in tab.text()


def test_insert_index_marker_mid_line_gets_own_line(tab):
    tab.set_initial_text("para", path=None)
    cursor = tab.editor.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    tab.editor.setTextCursor(cursor)
    tab.insert_index_marker("lof")
    assert "para\n[[lof]]" in tab.text()


def test_insert_code_block(tab):
    tab.set_initial_text("", path=None)
    tab.insert_code_block()
    assert "```python" in tab.text()


def test_insert_code_block_mid_line_gets_own_line(tab):
    """_insert_template's leading-newline branch for a block template."""
    tab.set_initial_text("para", path=None)
    cursor = tab.editor.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    tab.editor.setTextCursor(cursor)
    tab.insert_code_block()
    assert "para\n```python" in tab.text()


def test_insert_design_block_inserts_a_skeleton(tab):
    tab.set_initial_text("", path=None)
    tab.insert_design_block("stat")
    assert "::: {.stat}" in tab.text()
    assert "[Metric label]{.stat-label}" in tab.text()


def test_insert_disclosure_inserts_a_skeleton(tab):
    tab.set_initial_text("", path=None)
    tab.insert_disclosure("ai")
    assert "::: {.disclosure}" in tab.text()
    assert "This document was prepared with the assistance of AI" in (
        tab.text()
    )


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


def test_insert_section_heading_cancelled_uses_default_title(tab):
    """Cancelling (or clearing) the prompt still inserts a real heading,
    using the "Section title" default rather than an empty one."""
    tab.set_initial_text("", path=None)
    with patch(
        "PySide6.QtWidgets.QInputDialog.getText",
        return_value=("", False),
    ):
        tab.insert_section_heading()
    assert "## Section title {#sec-1}" in tab.text()


def test_insert_section_heading_mid_line_gets_own_line(tab):
    """Inserting mid-line pushes the new heading onto its own line."""
    tab.set_initial_text("existing text", path=None)
    cursor = tab.editor.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    tab.editor.setTextCursor(cursor)
    with patch(
        "PySide6.QtWidgets.QInputDialog.getText",
        return_value=("Intro", True),
    ):
        tab.insert_section_heading()
    assert "existing text\n## Intro {#sec-1}" in tab.text()


def test_insert_figure_uses_dialog_markdown(tab):
    tab.set_initial_text("para", path=None)
    with patch.object(
        tab_mod, "FigureDialog", _fake_dialog("![cap](x.png){#fig-1}")
    ):
        tab.insert_figure()
    assert "![cap](x.png){#fig-1}" in tab.text()


def _cancelled_dialog():
    """Return a dialog class whose exec() reports Rejected."""

    class _Cancelled:
        def __init__(self, *a, **k):
            pass

        def exec(self):
            return QDialog.DialogCode.Rejected

    return _Cancelled


def test_insert_figure_cancelled_leaves_buffer_unchanged(tab):
    tab.set_initial_text("para", path=None)
    with patch.object(tab_mod, "FigureDialog", _cancelled_dialog()):
        tab.insert_figure()
    assert tab.text() == "para"


def test_insert_figure_mid_line_gets_own_line(tab):
    tab.set_initial_text("para", path=None)
    cursor = tab.editor.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    tab.editor.setTextCursor(cursor)
    with patch.object(
        tab_mod, "FigureDialog", _fake_dialog("![cap](x.png){#fig-1}")
    ):
        tab.insert_figure()
    assert "para\n![cap](x.png){#fig-1}" in tab.text()


def test_insert_table_uses_dialog_markdown(tab):
    tab.set_initial_text("", path=None)
    with patch.object(
        tab_mod, "TableDialog", _fake_dialog("\n| a |\n| - |\n")
    ):
        tab.insert_table()
    assert "| a |" in tab.text()


def test_insert_table_cancelled_leaves_buffer_unchanged(tab):
    tab.set_initial_text("para", path=None)
    with patch.object(tab_mod, "TableDialog", _cancelled_dialog()):
        tab.insert_table()
    assert tab.text() == "para"


def test_insert_table_mid_line_gets_own_line(tab):
    tab.set_initial_text("para", path=None)
    cursor = tab.editor.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    tab.editor.setTextCursor(cursor)
    with patch.object(
        tab_mod, "TableDialog", _fake_dialog("| a |\n| - |\n")
    ):
        tab.insert_table()
    assert "para\n| a |" in tab.text()


# ---------------------------------------------------------------------------
# Checklist dialog
# ---------------------------------------------------------------------------


def test_insert_checklist_uses_dialog_markdown(tab):
    tab.set_initial_text("", path=None)
    with patch.object(
        tab_mod,
        "ChecklistDialog",
        _fake_dialog("\n- [ ] Item one\n- [ ] Item two\n"),
    ):
        tab.insert_checklist()
    assert "- [ ] Item one" in tab.text()


def test_insert_checklist_cancelled_leaves_buffer_unchanged(tab):
    tab.set_initial_text("para", path=None)
    with patch.object(tab_mod, "ChecklistDialog", _cancelled_dialog()):
        tab.insert_checklist()
    assert tab.text() == "para"


def test_insert_equation_uses_dialog_markdown(tab):
    tab.set_initial_text("", path=None)
    with patch.object(
        tab_mod, "EquationDialog", _fake_dialog("$$x$$ {#eq-1}")
    ):
        tab.insert_equation()
    assert "$$x$$ {#eq-1}" in tab.text()


def test_insert_equation_cancelled_leaves_buffer_unchanged(tab):
    tab.set_initial_text("para", path=None)
    with patch.object(tab_mod, "EquationDialog", _cancelled_dialog()):
        tab.insert_equation()
    assert tab.text() == "para"


def test_insert_equation_mid_line_gets_own_line(tab):
    tab.set_initial_text("para", path=None)
    cursor = tab.editor.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    tab.editor.setTextCursor(cursor)
    with patch.object(
        tab_mod, "EquationDialog", _fake_dialog("$$x$$ {#eq-1}")
    ):
        tab.insert_equation()
    assert "para\n$$x$$ {#eq-1}" in tab.text()


def test_insert_two_columns(tab):
    tab.set_initial_text("", path=None)
    with patch.object(
        tab_mod, "TwoColumnDialog", _fake_dialog("\n:::: {.columns}\n::::\n")
    ):
        tab.insert_two_columns()
    assert ":::: {.columns}" in tab.text()


def test_insert_two_columns_cancelled_leaves_buffer_unchanged(tab):
    tab.set_initial_text("para", path=None)
    with patch.object(tab_mod, "TwoColumnDialog", _cancelled_dialog()):
        tab.insert_two_columns()
    assert tab.text() == "para"


def test_insert_three_columns_uses_dialog_markdown(tab):
    tab.set_initial_text("", path=None)
    with patch.object(
        tab_mod,
        "ThreeColumnDialog",
        _fake_dialog("\n:::: {.columns3}\n::::\n"),
    ):
        tab.insert_three_columns()
    assert ":::: {.columns3}" in tab.text()


def test_insert_three_columns_cancelled_leaves_buffer_unchanged(tab):
    tab.set_initial_text("para", path=None)
    with patch.object(tab_mod, "ThreeColumnDialog", _cancelled_dialog()):
        tab.insert_three_columns()
    assert tab.text() == "para"


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


def test_insert_footnote_cancelled_leaves_buffer_unchanged(tab):
    tab.set_initial_text("body", path=None)
    with patch.object(tab_mod, "FootnoteDialog", _cancelled_dialog()):
        tab.insert_footnote()
    assert tab.text() == "body"


# ---------------------------------------------------------------------------
# insert_image_from_dialog: file picker + copy-to-figures/ + caption/width
# prompts. Every test drives it with a document path under tmp_path so
# nothing is ever copied next to the real repo.
# ---------------------------------------------------------------------------


def _write_source_image(tmp_path, name="photo.png"):
    src = tmp_path / "incoming" / name
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_bytes(b"\x89PNG\r\n\x1a\nfake-but-nonempty")
    return src


def test_insert_image_from_dialog_cancelled_is_a_noop(tab, tmp_path):
    tab.set_initial_text("para", path=tmp_path / "doc.md")
    with patch(
        "PySide6.QtWidgets.QFileDialog.getOpenFileName",
        return_value=("", ""),
    ):
        tab.insert_image_from_dialog()
    assert tab.text() == "para"


def test_insert_image_from_dialog_copies_and_inserts_markdown(
    tab, tmp_path
):
    doc = tmp_path / "project" / "doc.md"
    doc.parent.mkdir(parents=True)
    tab.set_initial_text("para", path=doc)
    src = _write_source_image(tmp_path)
    with patch(
        "PySide6.QtWidgets.QFileDialog.getOpenFileName",
        return_value=(str(src), ""),
    ), patch(
        "PySide6.QtWidgets.QInputDialog.getText",
        side_effect=[("My caption", True), ("60%", True)],
    ):
        tab.insert_image_from_dialog()

    copied = doc.parent / "figures" / "photo.png"
    assert copied.is_file()
    text = tab.text()
    assert "![My caption](figures/photo.png){#fig-1 width=60%}" in text


def test_insert_image_from_dialog_caption_cancelled_uses_filename_stem(
    tab, tmp_path
):
    doc = tmp_path / "project" / "doc.md"
    doc.parent.mkdir(parents=True)
    tab.set_initial_text("", path=doc)
    src = _write_source_image(tmp_path, name="beam-detail.png")
    with patch(
        "PySide6.QtWidgets.QFileDialog.getOpenFileName",
        return_value=(str(src), ""),
    ), patch(
        "PySide6.QtWidgets.QInputDialog.getText",
        side_effect=[("ignored", False), ("80%", True)],
    ):
        tab.insert_image_from_dialog()
    assert "![beam-detail]" in tab.text()


def test_insert_image_from_dialog_width_cancelled_defaults_to_80_percent(
    tab, tmp_path
):
    doc = tmp_path / "project" / "doc.md"
    doc.parent.mkdir(parents=True)
    tab.set_initial_text("", path=doc)
    src = _write_source_image(tmp_path)
    with patch(
        "PySide6.QtWidgets.QFileDialog.getOpenFileName",
        return_value=(str(src), ""),
    ), patch(
        "PySide6.QtWidgets.QInputDialog.getText",
        side_effect=[("Cap", True), ("   ", True)],
    ):
        tab.insert_image_from_dialog()
    assert "width=80%" in tab.text()


def test_insert_image_from_dialog_name_collision_gets_suffixed(
    tab, tmp_path
):
    """A same-named file already in figures/ is not overwritten; the new
    copy is suffixed -1, -2, ... instead."""
    doc = tmp_path / "project" / "doc.md"
    doc.parent.mkdir(parents=True)
    figures = doc.parent / "figures"
    figures.mkdir()
    (figures / "photo.png").write_bytes(b"already-here")
    tab.set_initial_text("", path=doc)
    src = _write_source_image(tmp_path)
    with patch(
        "PySide6.QtWidgets.QFileDialog.getOpenFileName",
        return_value=(str(src), ""),
    ), patch(
        "PySide6.QtWidgets.QInputDialog.getText",
        side_effect=[("Cap", True), ("80%", True)],
    ):
        tab.insert_image_from_dialog()
    assert (figures / "photo-1.png").is_file()
    # The pre-existing file was left untouched.
    assert (figures / "photo.png").read_bytes() == b"already-here"
    assert "figures/photo-1.png" in tab.text()


def test_insert_image_from_dialog_without_a_document_path_uses_cwd(
    tab, tmp_path, monkeypatch
):
    """No document path yet: figures/ is created under the CWD, not next
    to a (nonexistent) document directory. chdir's to tmp_path so this
    never touches the real repository working directory."""
    monkeypatch.chdir(tmp_path)
    tab.set_initial_text("", path=None)
    src = _write_source_image(tmp_path)
    with patch(
        "PySide6.QtWidgets.QFileDialog.getOpenFileName",
        return_value=(str(src), ""),
    ), patch(
        "PySide6.QtWidgets.QInputDialog.getText",
        side_effect=[("Cap", True), ("80%", True)],
    ):
        tab.insert_image_from_dialog()
    assert (tmp_path / "figures" / "photo.png").is_file()


def test_insert_image_from_dialog_mid_line_gets_own_line(tab, tmp_path):
    doc = tmp_path / "project" / "doc.md"
    doc.parent.mkdir(parents=True)
    tab.set_initial_text("para", path=doc)
    cursor = tab.editor.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    tab.editor.setTextCursor(cursor)
    src = _write_source_image(tmp_path)
    with patch(
        "PySide6.QtWidgets.QFileDialog.getOpenFileName",
        return_value=(str(src), ""),
    ), patch(
        "PySide6.QtWidgets.QInputDialog.getText",
        side_effect=[("Cap", True), ("80%", True)],
    ):
        tab.insert_image_from_dialog()
    assert "para\n![Cap]" in tab.text()


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


def test_bib_entries_empty_when_linked_file_does_not_exist(tab, tmp_path):
    """A bibliography: link pointing at a file that is not on disk
    yields no entries instead of raising."""
    doc = tmp_path / "doc.md"
    tab.set_initial_text(
        "---\nbibliography: ghost.bib\n---\n\nBody\n", path=doc
    )
    assert tab.bib_entries() == []


def test_link_bibliography_is_a_noop_when_value_unchanged(tab, tmp_path):
    """Re-linking the same already-set bib path does not touch the buffer
    (set_metadata_field would be a no-op, so _apply_buffer_replacement,
    which would dirty + re-render, must not run)."""
    doc = tmp_path / "doc.md"
    bib_file = tmp_path / "refs.bib"
    tab.set_initial_text(
        "---\nbibliography: refs.bib\n---\n\nBody\n", path=doc
    )
    tab._set_dirty(False)
    tab.link_bibliography(bib_file)
    assert tab.dirty is False


def test_link_bibliography_without_a_document_path(tab, tmp_path):
    """No document path yet: the bib path is stored absolute (there is no
    document directory to resolve it against)."""
    bib_file = tmp_path / "refs.bib"
    tab.set_initial_text("# Doc\n", path=None)
    tab.link_bibliography(bib_file)
    assert tab.bib_path() == bib_file.resolve()


def test_relative_to_doc_falls_back_to_absolute_when_unrelated(
    tab, tmp_path
):
    """A bib file outside the document's own directory tree cannot be
    expressed as a relative path (Path.relative_to has no ../ support
    pre-3.12) and falls back to the absolute path instead of raising."""
    doc_dir = tmp_path / "docs"
    doc_dir.mkdir()
    doc = doc_dir / "doc.md"
    tab.set_initial_text("# Doc\n", path=doc)
    unrelated = tmp_path / "elsewhere" / "refs.bib"
    unrelated.parent.mkdir()
    unrelated.write_text("@misc{a, title={A}}\n", encoding="utf-8")
    tab.link_bibliography(unrelated)
    # The absolute path contains a ':' (Windows drive letter), which the
    # YAML writer quotes; assert on the resolved value, not the raw line.
    resolved = tab.bib_path()
    assert resolved == unrelated.resolve()


# ---------------------------------------------------------------------------
# _render / _store_position (internal entry points the debounce timer and
# the position-poll timer call; exercised directly rather than by actually
# waiting on their timers)
# ---------------------------------------------------------------------------


def test_render_delegates_to_render_now_preserving_position(tab):
    tab.set_initial_text("# x\n", path=None)
    tab._last_pos = "epypos=s:0.5"
    tab._render()  # must not raise; exercises the debounced entry point
    assert tab.text() == "# x\n"


def test_store_position_records_a_nonempty_token(tab):
    tab.set_initial_text("# x\n", path=None)
    tab._store_position("epypos=s:0.42")
    assert tab._last_pos == "epypos=s:0.42"


def test_store_position_ignores_empty_and_none(tab):
    tab.set_initial_text("# x\n", path=None)
    tab._last_pos = "epypos=s:0.1"
    tab._store_position("")
    assert tab._last_pos == "epypos=s:0.1"
    tab._store_position(None)
    assert tab._last_pos == "epypos=s:0.1"


# ---------------------------------------------------------------------------
# Cross-reference picker
# ---------------------------------------------------------------------------


def test_insert_cross_reference_informs_when_empty(tab):
    tab.set_initial_text("plain, nothing to cite\n", path=None)
    with patch(
        "epy_reports._ui.tab.QMessageBox.information"
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
            from epy_reports._core.snippets import Label

            return Label(kind="fig", name="fig-1")

    with patch.object(tab_mod, "CrossRefDialog", _FakeXref):
        tab.insert_cross_reference()
    assert "@fig-1" in tab.text()


def test_insert_cross_reference_cancelled_leaves_buffer_unchanged(tab):
    tab.set_initial_text("![cap](x.png){#fig-1}\n\n", path=None)
    with patch.object(tab_mod, "CrossRefDialog", _cancelled_dialog()):
        tab.insert_cross_reference()
    assert tab.text() == "![cap](x.png){#fig-1}\n\n"


def test_insert_cross_reference_no_selection_is_a_noop(tab):
    """The picker opens but the user confirms with nothing selected."""
    tab.set_initial_text("![cap](x.png){#fig-1}\n\n", path=None)

    class _FakeXrefNoSelection:
        def __init__(self, *a, **k):
            pass

        def exec(self):
            return QDialog.DialogCode.Accepted

        def selected_label(self):
            return None

    with patch.object(tab_mod, "CrossRefDialog", _FakeXrefNoSelection):
        tab.insert_cross_reference()
    assert tab.text() == "![cap](x.png){#fig-1}\n\n"


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


def test_refresh_preview_does_not_raise(tab):
    tab.set_initial_text("# x\n", path=None)
    tab.refresh_preview()  # exercises the language-switch re-render hook


def test_page_layout_maps_each_page_size(qapp):
    from PySide6.QtGui import QPageLayout, QPageSize

    for key, page_id in (
        ("letter", QPageSize.PageSizeId.Letter),
        ("a4", QPageSize.PageSizeId.A4),
        ("legal", QPageSize.PageSizeId.Legal),
        ("unknown", QPageSize.PageSizeId.Letter),
    ):
        layout = MarkdownTab._page_layout(key)
        assert layout.pageSize().id() == page_id
        assert layout.orientation() == QPageLayout.Orientation.Portrait


def test_poll_position_queries_the_view(tab):
    """_poll_position reaches the page() is not None branch with a real
    (offscreen) QWebEngineView, and does not raise."""
    tab.set_initial_text("# x\n", path=None)
    tab._poll_position()  # fire-and-forget async JS query; must not raise


def test_cleanup_preview_tmp_is_safe_twice(tab):
    tab.set_initial_text("# x\n", path=None)
    tab.cleanup_preview_tmp()
    tab.cleanup_preview_tmp()  # second call must not raise


def test_render_into_view_shows_error_html_on_render_failure(tab, monkeypatch):
    """A render_markdown failure degrades to an inline error page instead
    of crashing the tab or leaving the preview stuck on stale content."""

    def _raise(*args, **kwargs):
        raise ValueError("boom & <bad message")

    monkeypatch.setattr(tab_mod, "render_markdown", _raise)
    tab.set_initial_text("# x\n", path=None)
    preview_html = (tab._preview_tmp_dir / "preview.html").read_text(
        encoding="utf-8"
    )
    assert "Render error" in preview_html
    assert "boom &amp; &lt;bad message" in preview_html


# ---------------------------------------------------------------------------
# export_pdf: the async, WebEngine-driven PDF export flow.
#
# Like _core/_export_pdf.render_report_pdf, this drives a real
# QWebEngineView through page-load / MathJax-ready / printToPdf signals.
# tab.view is swapped for a fake that fires those same signals from a
# QTimer (see test_export_pdf.py's module docstring for the rationale),
# writing a REAL multi-page PDF via reportlab where the real view would
# have printed one. Stamping (header/footer/watermark/metadata/cover/
# annexes) then runs through the REAL epy_export package against that
# real PDF, exactly as in test_export_pdf.py.
# ---------------------------------------------------------------------------


class _FakeTabSignal:
    """connect()/disconnect() + a QTimer-deferred emit. Accepts (and
    ignores) the Qt.ConnectionType second positional arg tab.py passes."""

    def __init__(self) -> None:
        self._slot = None

    def connect(self, slot, _conn_type=None):
        self._slot = slot
        return self

    def disconnect(self, _conn=None):
        self._slot = None

    def emit(self, *args):
        slot, self._slot = self._slot, None  # SingleShot: fire once
        if slot is not None:
            slot(*args)

    def emit_later(self, *args, delay_ms: int = 5):
        from PySide6.QtCore import QTimer

        QTimer.singleShot(delay_ms, lambda: self.emit(*args))


class _FakeTabPage:
    def __init__(self, pages: int, print_ok, paged_done_after: int = 1):
        self.pdfPrintingFinished = _FakeTabSignal()
        self._pages = pages
        self._print_ok = print_ok
        self._print_call = 0
        self._paged_done_polls = 0
        self._paged_done_after = paged_done_after

    def runJavaScript(self, expr, callback):  # noqa: N802 - Qt API name
        from PySide6.QtCore import QTimer

        if expr == "window._paged_done === true":
            self._paged_done_polls += 1
            value = self._paged_done_polls >= self._paged_done_after
        else:
            value = True
        QTimer.singleShot(5, lambda: callback(value))

    def _next_print_result(self) -> bool:
        if isinstance(self._print_ok, list):
            index = min(self._print_call, len(self._print_ok) - 1)
            self._print_call += 1
            return self._print_ok[index]
        return self._print_ok

    def printToPdf(self, path, _layout):  # noqa: N802 - Qt API name
        from reportlab.pdfgen import canvas as _canvas

        ok = self._next_print_result()
        if ok:
            c = _canvas.Canvas(str(path))
            for i in range(self._pages):
                c.drawString(72, 720, f"Page {i + 1}")
                c.showPage()
            c.save()
        self.pdfPrintingFinished.emit_later(path, ok)


class _FakeTabView:
    """Stands in for tab.view (a QWebEngineView subclass)."""

    def __init__(
        self, pages=2, print_ok=True, paged_done_after=1, load_ok=True
    ):
        self.loadFinished = _FakeTabSignal()
        self._page = _FakeTabPage(pages, print_ok, paged_done_after)
        self._load_ok = load_ok

    def load(self, _url):
        self.loadFinished.emit_later(self._load_ok)

    def page(self):
        return self._page


def _pump_until(predicate, timeout: float = 5.0) -> None:
    """Spin the real (offscreen) Qt event loop so QTimer.singleShot-based
    fake signals actually fire, until ``predicate()`` is true."""
    deadline = time.monotonic() + timeout
    while not predicate() and time.monotonic() < deadline:
        QCoreApplication.processEvents()


def test_export_pdf_no_named_destinations_single_pass(tab, tmp_path):
    """A plain body with no anchors falls back to a single print pass
    (real epy_export.extract_anchor_pages on a plain reportlab PDF
    genuinely finds none)."""
    tab.set_initial_text("# Title\n\nBody.\n", path=None)
    tab.view = _FakeTabView(pages=2)
    done = []
    out = tmp_path / "out.pdf"
    tab.export_pdf(out, on_done=lambda target, ok: done.append((target, ok)))
    # Pump the event loop until the async chain (load -> ready-poll ->
    # print -> finalize) completes.
    _pump_until(lambda: done)
    assert done == [(out, True)]
    assert out.is_file()
    import pypdf

    assert len(pypdf.PdfReader(str(out)).pages) == 2


def test_export_pdf_with_named_destinations_two_pass(
    tab, tmp_path, monkeypatch
):
    import epy_export

    tab.set_initial_text("# Title\n\nBody.\n", path=None)
    tab.view = _FakeTabView(pages=3)
    monkeypatch.setattr(
        epy_export,
        "extract_anchor_pages",
        lambda pdf_path: {
            "toc-h-1": 1, "fig-a": 2,
            "epy-section-roman-1": 1,
            "epy-section-arabic-1": 2,
        },
    )
    done = []
    out = tmp_path / "out.pdf"
    tab.export_pdf(out, on_done=lambda target, ok: done.append((target, ok)))
    _pump_until(lambda: done)
    assert done == [(out, True)]
    import pypdf

    assert len(pypdf.PdfReader(str(out)).pages) == 3


def test_export_pdf_pass1_failure_reports_not_ok(tab, tmp_path):
    tab.set_initial_text("# Title\n\nBody.\n", path=None)
    tab.view = _FakeTabView(print_ok=False)
    done = []
    out = tmp_path / "out.pdf"
    tab.export_pdf(out, on_done=lambda target, ok: done.append((target, ok)))
    _pump_until(lambda: done)
    assert done == [(out, False)]
    assert not out.exists()


def test_export_pdf_page_load_failure_reports_not_ok(tab, tmp_path):
    """The view failing to LOAD the export page (distinct from printToPdf
    failing) is reported the same way: not ok, nothing written."""
    tab.set_initial_text("# Title\n\nBody.\n", path=None)
    tab.view = _FakeTabView(load_ok=False)
    done = []
    out = tmp_path / "out.pdf"
    tab.export_pdf(out, on_done=lambda target, ok: done.append((target, ok)))
    _pump_until(lambda: done)
    assert done == [(out, False)]
    assert not out.exists()


def test_export_pdf_joins_cover_and_annexes(tab, tmp_path):
    cover = tmp_path / "cover.pdf"
    annex = tmp_path / "annex.pdf"
    for pdf_path in (cover, annex):
        from reportlab.pdfgen import canvas as _canvas

        c = _canvas.Canvas(str(pdf_path))
        c.drawString(72, 720, "page")
        c.showPage()
        c.save()

    doc = tmp_path / "doc.md"
    source = (
        "---\n"
        'cover-pdf: "cover.pdf"\n'
        'annexes: ["annex.pdf"]\n'
        "---\n\n# T\n\nBody.\n"
    )
    tab.set_initial_text(source, path=doc)
    tab.view = _FakeTabView(pages=2)
    done = []
    out = tmp_path / "out.pdf"
    tab.export_pdf(out, on_done=lambda target, ok: done.append((target, ok)))
    _pump_until(lambda: done)
    assert done == [(out, True)]
    import pypdf

    # 2 body pages + 1 annex (appended before stamping) + 1 cover
    # (prepended after stamping) = 4.
    assert len(pypdf.PdfReader(str(out)).pages) == 4


def test_export_pdf_paints_page_background_when_theme_declares_one(
    tab, tmp_path
):
    tab.set_initial_text("# Title\n\nBody.\n", path=None)
    tab.set_theme_css(":root { --bg: #f0f0f0; }", "#f0f0f0")
    tab.view = _FakeTabView(pages=1)
    done = []
    out = tmp_path / "out.pdf"
    tab.export_pdf(out, on_done=lambda target, ok: done.append((target, ok)))
    _pump_until(lambda: done)
    assert done == [(out, True)]
    assert out.is_file()


def test_export_pdf_gives_up_waiting_for_paged_js_after_timeout(
    tab, tmp_path, monkeypatch
):
    """window._paged_done never reports true; the export still completes
    (prints anyway) once the timeout is exceeded rather than hanging
    forever. The real timeout (60s) is shortened so the test does not
    have to wait it out.
    """
    monkeypatch.setattr(tab_mod, "_PAGED_TIMEOUT_MS", 10)
    tab.set_initial_text("# Title\n\nBody.\n", path=None)
    # paged_done_after larger than any realistic poll count: it never
    # reports ready before the (shortened) timeout gives up.
    tab.view = _FakeTabView(pages=1, paged_done_after=10_000)
    done = []
    out = tmp_path / "out.pdf"
    tab.export_pdf(out, on_done=lambda target, ok: done.append((target, ok)))
    _pump_until(lambda: done, timeout=10)
    assert done == [(out, True)]


def test_export_pdf_finalize_error_reports_not_ok(tab, tmp_path, monkeypatch):
    """A stamping failure (add_metadata raising) is caught, reported as
    not-ok, and still cleans up the temp dir / restores the preview."""
    import epy_export

    def _raise(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(epy_export, "add_metadata", _raise)
    tab.set_initial_text("# Title\n\nBody.\n", path=None)
    tab.view = _FakeTabView(pages=1)
    done = []
    out = tmp_path / "out.pdf"
    tab.export_pdf(out, on_done=lambda target, ok: done.append((target, ok)))
    _pump_until(lambda: done)
    assert done == [(out, False)]


def test_export_pdf_paged_ready_poll_retries(tab, tmp_path):
    """window._paged_done reporting "not yet" once still completes the
    export (the _wait_for_export_ready retry loop)."""
    tab.set_initial_text("# Title\n\nBody.\n", path=None)
    tab.view = _FakeTabView(pages=1, paged_done_after=2)
    done = []
    out = tmp_path / "out.pdf"
    tab.export_pdf(out, on_done=lambda target, ok: done.append((target, ok)))
    _pump_until(lambda: done)
    assert done == [(out, True)]


def test_export_pdf_stamps_watermark_header_footer_and_metadata(
    tab, tmp_path
):
    watermark = tmp_path / "wm.png"
    watermark.write_bytes(
        base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
            "YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
        )
    )
    doc = tmp_path / "doc.md"
    source = (
        "---\n"
        'title: "Report"\n'
        'author: "A. Navarro"\n'
        'watermark: "wm.png"\n'
        'header: ["Left", "Right"]\n'
        'footer: "Confidential"\n'
        "page-numbers: true\n"
        "---\n\n# T\n\nBody.\n"
    )
    tab.set_initial_text(source, path=doc)
    tab.view = _FakeTabView(pages=2)
    done = []
    out = tmp_path / "out.pdf"
    tab.export_pdf(out, on_done=lambda target, ok: done.append((target, ok)))
    _pump_until(lambda: done)
    assert done == [(out, True)]
    import pypdf

    reader = pypdf.PdfReader(str(out))
    assert reader.metadata.title == "Report"
    assert reader.metadata.author == "A. Navarro"
