"""Tests for the MarkdownWindow main window and the CLI entry points.

The window is built headlessly with a module-scoped QApplication, the
same pattern the dialog tests use. File / message dialogs are patched so
the command methods run end to end without blocking on real modal UI.
"""

from __future__ import annotations

import importlib.resources
from pathlib import Path
from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from epy_reports import app as app_mod
from epy_reports._core import _i18n as i18n
from epy_reports._ui.tab import MarkdownTab
from epy_reports.app import MarkdownWindow

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


class _ScratchSettings:
    """In-memory QSettings stand-in shared per test invocation."""

    _store: dict[str, object] = {}

    def __init__(self, *_args, **_kwargs):
        self._store = _ScratchSettings._store

    def value(self, key, default=None, _type=None):
        return self._store.get(key, default)

    def setValue(self, key, value):  # noqa: N802 - Qt API name
        self._store[key] = value

    def sync(self):
        return True


def _teardown_window(win, qapp) -> None:
    """Reset language and flush the deferred delete for a scratch window.

    Without a running event loop the window (and its WebEngine preview)
    would linger until interpreter exit and crash Qt's native teardown
    (0xC0000005).
    """
    i18n.set_language("en")
    win.deleteLater()
    from PySide6.QtCore import QEvent

    qapp.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    qapp.processEvents()


@pytest.fixture
def window(qapp, monkeypatch):
    """Build a fresh MarkdownWindow and tear it down afterwards.

    ``app_mod.QSettings`` is patched to an in-memory stand-in so the
    preference tests never touch the real "ANM Ingeniería" registry scope.
    """
    monkeypatch.setattr(app_mod, "QSettings", _ScratchSettings)
    win = MarkdownWindow()
    try:
        yield win
    finally:
        _teardown_window(win, qapp)


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_window_builds_with_welcome_tab(window):
    """A new window opens with exactly one welcome tab."""
    assert window.tabs.count() == 1
    assert isinstance(window._current_tab(), MarkdownTab)


def test_window_title_is_app_name_family(window):
    """The window title carries the app name."""
    assert app_mod.APP_NAME in window.windowTitle()


def test_welcome_text_is_loaded():
    """The bundled welcome document is loaded at import time."""
    assert app_mod.WELCOME_TEXT
    assert "__EPY_LOGO__" not in app_mod.WELCOME_TEXT


def test_theme_actions_cover_every_theme(window):
    """One radio action exists per registered theme."""
    from epy_reports._core import themes

    assert set(window.theme_actions) == set(themes.THEMES)


# ---------------------------------------------------------------------------
# Tab management
# ---------------------------------------------------------------------------


def test_new_tab_adds_a_tab(window):
    """``_new_tab`` adds and focuses an empty tab."""
    before = window.tabs.count()
    tab = window._new_tab()
    assert window.tabs.count() == before + 1
    assert window._current_tab() is tab
    assert tab.text() == ""


def test_open_path_rejects_missing_file(window, tmp_path):
    """Opening a non-existent path warns and does not add a tab."""
    before = window.tabs.count()
    with patch.object(QMessageBox, "warning") as warn:
        window.open_path(tmp_path / "missing.md")
    warn.assert_called_once()
    assert window.tabs.count() == before


def test_open_path_loads_file_into_tab(window, tmp_path):
    """A real file is loaded and its path recorded on the tab."""
    doc = tmp_path / "doc.md"
    doc.write_text("# Hello\n", encoding="utf-8")
    window.open_path(doc)
    tab = window._current_tab()
    assert tab is not None
    assert tab.path is not None
    assert tab.path.resolve() == doc.resolve()


def test_open_path_focuses_already_open_tab(window, tmp_path):
    """Re-opening the same path focuses the existing tab, no duplicate."""
    doc = tmp_path / "dup.md"
    doc.write_text("# Dup\n", encoding="utf-8")
    window.open_path(doc)
    count_after_first = window.tabs.count()
    window._new_tab()
    window.open_path(doc)
    assert window.tabs.count() == count_after_first + 1  # only the new_tab
    assert window._current_tab().path.resolve() == doc.resolve()


def test_close_tab_reopens_welcome_when_last(window):
    """Closing the only tab repopulates a welcome tab."""
    while window.tabs.count() > 1:
        window.tabs.removeTab(0)
    window._close_tab_at(0)
    assert window.tabs.count() == 1


# ---------------------------------------------------------------------------
# File save / reload (dialogs patched)
# ---------------------------------------------------------------------------


def test_save_current_as_writes_file(window, tmp_path):
    """``_save_current_as`` writes the buffer to the chosen path."""
    tab = window._current_tab()
    tab.editor.setPlainText("# Saved content\n")
    target = tmp_path / "out.md"
    with patch.object(
        app_mod.QFileDialog, "getSaveFileName",
        return_value=(str(target), ""),
    ):
        assert window._save_current_as() is True
    assert target.read_text(encoding="utf-8").startswith("# Saved content")


def test_save_current_as_appends_md_suffix(window, tmp_path):
    """A path without a suffix gets ``.md`` appended."""
    tab = window._current_tab()
    tab.editor.setPlainText("body\n")
    target = tmp_path / "nosuffix"
    with patch.object(
        app_mod.QFileDialog, "getSaveFileName",
        return_value=(str(target), ""),
    ):
        window._save_current_as()
    assert (tmp_path / "nosuffix.md").exists()


def test_save_current_as_cancel_returns_false(window):
    """Cancelling the Save As dialog returns False."""
    with patch.object(
        app_mod.QFileDialog, "getSaveFileName", return_value=("", "")
    ):
        assert window._save_current_as() is False


def test_save_current_falls_back_to_save_as(window, tmp_path):
    """An untitled tab routes Save through Save As."""
    tab = window._current_tab()
    tab.set_initial_text("# Untitled body\n", path=None)
    target = tmp_path / "viasave.md"
    with patch.object(
        app_mod.QFileDialog, "getSaveFileName",
        return_value=(str(target), ""),
    ):
        assert window._save_current() is True
    assert target.exists()


def test_reload_current_discards_changes(window, tmp_path):
    """Reload restores on-disk content after a confirmed discard."""
    doc = tmp_path / "reload.md"
    doc.write_text("original\n", encoding="utf-8")
    window.open_path(doc)
    tab = window._current_tab()
    tab.editor.setPlainText("dirty edit")
    with patch.object(
        QMessageBox, "question",
        return_value=QMessageBox.StandardButton.Yes,
    ):
        window._reload_current()
    assert tab.text().strip() == "original"


# ---------------------------------------------------------------------------
# Front-matter writing commands
# ---------------------------------------------------------------------------


def test_set_page_size_writes_front_matter(window):
    """``_set_page_size`` injects ``page-size`` into the buffer."""
    tab = window._new_tab()
    tab.editor.setPlainText("# Title\n")
    window._set_page_size("a4")
    assert "page-size: a4" in tab.editor.toPlainText()


def test_set_csl_style_writes_front_matter(window):
    """``_set_csl_style`` injects the ``csl`` field."""
    tab = window._new_tab()
    tab.editor.setPlainText("# Title\n")
    window._set_csl_style("apa")
    assert "csl: apa" in tab.editor.toPlainText()


def test_current_page_size_reads_front_matter(window):
    """The current page size reflects the document front matter."""
    tab = window._new_tab()
    tab.editor.setPlainText("---\npage-size: legal\n---\n\nBody\n")
    assert window._current_page_size_from_tab() == "legal"


def test_current_csl_key_defaults_to_ieee(window):
    """A document without a csl field reports the IEEE default."""
    from epy_reports._core.renderer import DEFAULT_CSL_STYLE

    tab = window._new_tab()
    tab.editor.setPlainText("# No csl here\n")
    assert window._current_csl_key_from_tab(tab) == DEFAULT_CSL_STYLE


def test_insert_cross_ref_name_inserts_at_caret(window):
    """Selecting a reference inserts ``@name`` into the editor."""
    tab = window._new_tab()
    tab.editor.setPlainText("")
    window._insert_cross_ref_name("fig-foo")
    assert "@fig-foo" in tab.editor.toPlainText()


# ---------------------------------------------------------------------------
# References menu population
# ---------------------------------------------------------------------------


def test_references_menu_lists_labels(window):
    """Buffer labels are grouped into the References menu."""
    tab = window._new_tab()
    tab.editor.setPlainText(
        "## Section {#sec-intro}\n\n"
        "![cap](x.png){#fig-one}\n"
    )
    window._populate_references_menu()
    titles = [m.title() for m in window.references_menu.findChildren(type(
        window.references_menu))]
    # At least the Figures and Sections submenus exist.
    assert any("Fig" in t or "Sec" in t for t in titles)


def test_references_menu_placeholder_when_no_labels(window):
    """An empty buffer shows the no-labels placeholder (disabled)."""
    i18n.set_language("en")
    tab = window._new_tab()
    tab.editor.setPlainText("plain text, no labels\n")
    window._populate_references_menu()
    texts = [a.text() for a in window.references_menu.actions()]
    assert any("no labels" in t.lower() for t in texts)


# ---------------------------------------------------------------------------
# Theme switching
# ---------------------------------------------------------------------------


def test_apply_theme_switches_current(window):
    """Applying a theme updates the active theme reference."""
    from epy_reports._core import themes

    target = next(iter(themes.THEMES))
    window._apply_theme(target, persist=False)
    assert window._current_theme.id == target


def test_sync_page_size_menu_checks_radio(window):
    """The page-size submenu syncs the radio to the document."""
    tab = window._new_tab()
    tab.editor.setPlainText("---\npage-size: a4\n---\n\nBody\n")
    window._sync_page_size_menu()
    assert window.page_size_actions["a4"].isChecked()


# ---------------------------------------------------------------------------
# Language switching
# ---------------------------------------------------------------------------


def test_set_language_switches_and_retranslates(window):
    """Switching to Spanish relabels a known action."""
    window._set_language("es")
    assert i18n.current_language() == "es"
    assert window.act_new.text() == "Nuevo"
    window._set_language("en")
    assert window.act_new.text() == "New"


def test_sync_language_menu_checks_active(window):
    """The language radio reflects the active language."""
    window._set_language("en")
    window._sync_language_menu()
    assert window.lang_actions["en"].isChecked()


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------


def test_save_and_apply_template(window, tmp_path, monkeypatch):
    """A saved template round-trips through apply (theme + front matter)."""
    from epy_reports._core import templates

    base = tmp_path / "templates"
    monkeypatch.setattr(templates, "_config_base_dir", lambda: base)

    tab = window._new_tab()
    tab.editor.setPlainText(
        "---\ncsl: apa\nfooter: ACME\n---\n\nBody\n"
    )
    with patch(
        "PySide6.QtWidgets.QInputDialog.getText",
        return_value=("House Style", True),
    ):
        window._save_template()
    assert "House Style" in templates.list_templates(base_dir=base)

    # Apply onto a fresh, bare buffer.
    fresh = window._new_tab()
    fresh.editor.setPlainText("# Fresh\n")
    window._apply_template("House Style")
    assert "csl: apa" in fresh.editor.toPlainText()
    assert "footer: ACME" in fresh.editor.toPlainText()


def test_delete_template_confirmed(window, tmp_path, monkeypatch):
    """A confirmed delete removes the template file."""
    from epy_reports._core import templates

    base = tmp_path / "templates"
    monkeypatch.setattr(templates, "_config_base_dir", lambda: base)
    templates.save_template("Temp", {"theme": "corporate"}, base_dir=base)

    with patch.object(
        QMessageBox, "question",
        return_value=QMessageBox.StandardButton.Yes,
    ):
        window._delete_template("Temp")
    assert templates.list_templates(base_dir=base) == []


# ---------------------------------------------------------------------------
# Document properties + bibliography (dialogs patched)
# ---------------------------------------------------------------------------


def test_edit_document_properties_writes_updates(window):
    """Accepting the properties dialog writes the front matter."""
    tab = window._new_tab()
    tab.editor.setPlainText("# Doc\n")

    class _FakeDialog:
        def __init__(self, *a, **k):
            pass

        def exec(self):
            return QDialog.DialogCode.Accepted

        def updates(self):
            return [("title", "My Title", False),
                    ("page-size", "a4", False)]

    with patch(
        "epy_reports._ui.document_properties_dialog"
        ".DocumentPropertiesDialog",
        _FakeDialog,
    ):
        window._edit_document_properties()
    text = tab.editor.toPlainText()
    assert "title: My Title" in text
    assert "page-size: a4" in text


def test_link_bibliography_writes_field(window, tmp_path):
    """Linking a .bib writes the bibliography front-matter field."""
    bib_file = tmp_path / "refs.bib"
    bib_file.write_text("@article{a,\n title={A}\n}\n", encoding="utf-8")
    tab = window._new_tab()
    tab.editor.setPlainText("# Doc\n")
    with patch.object(
        app_mod.QFileDialog, "getOpenFileName",
        return_value=(str(bib_file), ""),
    ):
        window._link_bibliography()
    assert tab.bib_path() is not None
    assert tab.bib_path().resolve() == bib_file.resolve()


def test_localize_asset_copies_into_figures(window, tmp_path):
    """A picked image is copied into the document's figures/ folder."""
    doc = tmp_path / "doc.md"
    doc.write_text("# Doc\n", encoding="utf-8")
    window.open_path(doc)
    tab = window._current_tab()
    logo = tmp_path / "logo.png"
    logo.write_bytes(b"\x89PNG\r\n\x1a\n")
    rel = MarkdownWindow._localize_asset(tab, str(logo))
    assert rel == "figures/logo.png"
    assert (tmp_path / "figures" / "logo.png").exists()


def test_localize_asset_passthrough_for_relative(window):
    """A relative value is returned unchanged."""
    tab = window._new_tab()
    assert MarkdownWindow._localize_asset(tab, "figures/x.png") == (
        "figures/x.png"
    )


# ---------------------------------------------------------------------------
# Export helpers
# ---------------------------------------------------------------------------


def test_resolve_reference_doc_returns_path_or_none(window):
    """The DOCX reference template resolves for a bundled theme."""
    result = window._resolve_reference_doc("corporate")
    assert result is None or isinstance(result, Path)


def test_export_html_writes_file(window, tmp_path):
    """``_export_html`` renders the buffer to a standalone HTML file."""
    tab = window._new_tab()
    tab.editor.setPlainText("# HTML export\n\nBody.\n")
    target = tmp_path / "out.html"
    with patch.object(
        app_mod.QFileDialog, "getSaveFileName",
        return_value=(str(target), ""),
    ):
        window._export_html()
    html = target.read_text(encoding="utf-8")
    assert "HTML export" in html


def test_export_html_failure_is_reported_not_swallowed(
    window, tmp_path
):
    """A render failure pops a modal and reports it in the status bar."""
    tab = window._new_tab()
    tab.editor.setPlainText("# HTML export\n")
    target = tmp_path / "out.html"
    # What breaks: a failed export looks exactly like a successful one.
    with patch.object(
        app_mod.QFileDialog, "getSaveFileName",
        return_value=(str(target), ""),
    ), patch.object(
        app_mod, "render_markdown",
        side_effect=RuntimeError("boom"),
    ), patch.object(
        app_mod.QMessageBox, "critical",
    ) as crit:
        window._export_html()

    assert crit.call_count == 1
    title = crit.call_args.args[1]
    assert "failed" in title.lower()
    assert "Export failed" in window.statusBar().currentMessage()
    assert not target.exists()
    assert window._exports_in_flight == 0


def test_export_docx_failure_reaches_the_status_bar(
    window, tmp_path
):
    """A DOCX failure shows up on the status bar after the modal."""
    tab = window._new_tab()
    tab.editor.setPlainText("# DOCX export\n")
    target = tmp_path / "out.docx"
    # What breaks: a failed export looks exactly like a successful one.
    with patch.object(
        app_mod.QFileDialog, "getSaveFileName",
        return_value=(str(target), ""),
    ), patch.object(
        app_mod, "export_docx",
        side_effect=OSError("read-only"),
    ), patch.object(
        app_mod.QMessageBox, "critical",
    ) as crit:
        window._export_docx()

    assert crit.call_count == 1
    assert "Export failed" in window.statusBar().currentMessage()
    assert window._exports_in_flight == 0


def test_export_html_success_says_nothing_about_failure(
    window, tmp_path
):
    """A successful HTML export stays away from failure language."""
    tab = window._new_tab()
    tab.editor.setPlainText("# HTML export\n\nBody.\n")
    target = tmp_path / "ok.html"
    # What breaks: the success path would show a failure notice.
    with patch.object(
        app_mod.QFileDialog, "getSaveFileName",
        return_value=(str(target), ""),
    ), patch.object(
        app_mod.QMessageBox, "critical",
    ) as crit:
        window._export_html()

    assert target.exists()
    status = window.statusBar().currentMessage()
    assert "failed" not in status.lower()
    crit.assert_not_called()


def test_export_html_cancel_writes_nothing(window, tmp_path):
    """Cancelling the HTML dialog produces no file."""
    tab = window._new_tab()
    tab.editor.setPlainText("# x\n")
    with patch.object(
        app_mod.QFileDialog, "getSaveFileName", return_value=("", "")
    ):
        window._export_html()
    assert not list(tmp_path.glob("*.html"))


def test_export_docx_invokes_export(window, tmp_path):
    """``_export_docx`` calls export_docx with the chosen target."""
    tab = window._new_tab()
    tab.editor.setPlainText("# DOCX\n")
    target = tmp_path / "out.docx"
    with patch.object(
        app_mod.QFileDialog, "getSaveFileName",
        return_value=(str(target), ""),
    ), patch.object(app_mod, "export_docx") as exp:
        window._export_docx()
    exp.assert_called_once()
    assert exp.call_args.args[1] == target


def test_on_pdf_done_success_and_failure(window):
    """The PDF-done callback handles both outcomes without raising."""
    window._on_pdf_done(Path("ok.pdf"), True)
    with patch.object(QMessageBox, "warning") as warn:
        window._on_pdf_done(Path("bad.pdf"), False)
    warn.assert_called_once()


# ---------------------------------------------------------------------------
# Autosave
# ---------------------------------------------------------------------------


def test_autosave_off_default_does_not_write(window, tmp_path):
    """Autosave is off by default; firing the slot leaves disk unchanged."""
    doc = tmp_path / "autosave_off.md"
    doc.write_text("original\n", encoding="utf-8")
    window.open_path(doc)
    tab = window._current_tab()
    assert tab is not None
    tab.editor.setPlainText("# edited\n")
    assert tab.dirty

    assert not window.act_autosave.isChecked()
    window._autosave_current()

    assert doc.read_text(encoding="utf-8") == "original\n"
    assert tab.dirty


def test_autosave_skips_a_clean_tab_even_when_enabled(window, tmp_path):
    """A tab with no unsaved changes is left alone -- autosave has
    nothing to write, and must not touch the file's mtime/content."""
    doc = tmp_path / "clean.md"
    doc.write_text("already saved\n", encoding="utf-8")
    window.open_path(doc)
    tab = window._current_tab()
    assert tab is not None
    assert tab.dirty is False
    window.act_autosave.setChecked(True)

    window._autosave_current()  # must return early, not touch the file

    assert doc.read_text(encoding="utf-8") == "already saved\n"


def test_autosave_writes_dirty_tab_with_path(window, tmp_path):
    """With autosave on, a dirty saved tab is written and marked clean."""
    doc = tmp_path / "autosave_on.md"
    doc.write_text("# before\n", encoding="utf-8")
    window.open_path(doc)
    tab = window._current_tab()
    assert tab is not None
    tab.editor.setPlainText("# after\n")
    window.act_autosave.setChecked(True)

    window._autosave_current()

    assert doc.read_text(encoding="utf-8") == "# after\n"
    assert tab.dirty is False


def test_autosave_untitled_never_opens_dialog(window):
    """Untitled dirty buffers autosave silently without a Save As dialog."""
    tab = window._new_tab()
    tab.editor.setPlainText("# unsaved\n")
    window.act_autosave.setChecked(True)

    def _fail_dialog(*args, **kwargs):
        raise AssertionError("a dialog opened")

    with patch.object(
        app_mod.QFileDialog, "getSaveFileName", side_effect=_fail_dialog
    ):
        window._autosave_current()

    assert tab.dirty is True


def test_autosave_skips_when_export_in_flight(window, tmp_path):
    """Autosave yields while an export is in flight."""
    doc = tmp_path / "inflight.md"
    doc.write_text("original\n", encoding="utf-8")
    window.open_path(doc)
    tab = window._current_tab()
    assert tab is not None
    tab.editor.setPlainText("# edited\n")
    window.act_autosave.setChecked(True)
    window._exports_in_flight = 1

    try:
        window._autosave_current()
    finally:
        window._exports_in_flight = 0

    assert doc.read_text(encoding="utf-8") == "original\n"
    assert tab.dirty is True


def test_exports_in_flight_decrements_after_docs_error(window):
    """A failed epy_docs export releases the autosave counter."""
    window._exports_in_flight = 1
    with patch.object(QMessageBox, "critical"):
        window._on_docs_done_err("boom")
    assert window._exports_in_flight == 0


def test_autosave_preference_persists(window, qapp):
    """The Autosave checkable preference is restored from settings."""
    window.act_autosave.setChecked(True)

    second = None
    try:
        second = MarkdownWindow()
        assert second.act_autosave.isChecked() is True
    finally:
        if second is not None:
            second.deleteLater()
            from PySide6.QtCore import QEvent

            qapp.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            qapp.processEvents()


# ---------------------------------------------------------------------------
# _load_manual_text: Spanish screenshot resolution + broken placeholder
# ---------------------------------------------------------------------------


def test_load_manual_text_spanish_uses_localized_screenshots():
    """The Spanish manual swaps in *_es.png screenshots where they exist."""
    text = app_mod._load_manual_text("welcome_es.md")
    assert "__EPY_LOGO__" not in text
    assert "__SHOT_EDITOR__" not in text
    assert "file://" in text


def test_load_manual_text_broken_placeholder_becomes_empty(monkeypatch):
    """A resource that cannot be turned into a URI degrades to an empty
    string instead of crashing the manual load."""

    def _raise(self):
        raise ValueError("cannot resolve")

    monkeypatch.setattr(Path, "as_uri", _raise)
    text = app_mod._load_manual_text("welcome.md")
    assert "__EPY_LOGO__" not in text
    assert "file://" not in text


# ---------------------------------------------------------------------------
# Actions requiring no current tab (window starts with the welcome tab, so
# every one of these closes it first to reach the "no tab" guard).
# ---------------------------------------------------------------------------


def _close_every_tab(window) -> None:
    """Drop every open tab WITHOUT the confirm-close / welcome-reopen
    logic, so _current_tab() genuinely returns None."""
    while window.tabs.count() > 0:
        window.tabs.removeTab(0)


def test_on_active_tab_noop_without_a_tab(window):
    _close_every_tab(window)
    window._on_active_tab("set_heading_level", 1)  # must not raise


def test_insert_cross_ref_name_noop_without_a_tab(window):
    _close_every_tab(window)
    window._insert_cross_ref_name("fig-x")  # must not raise


def test_apply_paged_noop_without_a_tab(window):
    _close_every_tab(window)
    window._apply_paged(True)  # must not raise (empty loop)


def test_current_page_size_defaults_without_a_tab(window):
    from epy_reports._core.renderer import DEFAULT_PAGE_SIZE

    _close_every_tab(window)
    assert window._current_page_size_from_tab() == DEFAULT_PAGE_SIZE


def test_set_page_size_noop_without_a_tab(window):
    _close_every_tab(window)
    window._set_page_size("a4")  # must not raise


def test_set_page_size_no_change_shows_status(window):
    """Re-applying the same page size is a no-op that still reports it."""
    tab = window._new_tab()
    tab.editor.setPlainText("---\npage-size: a4\n---\n\nBody\n")
    window._set_page_size("a4")
    assert "no change" in window.statusBar().currentMessage().lower()


def test_current_csl_key_defaults_without_a_tab(window):
    from epy_reports._core.renderer import DEFAULT_CSL_STYLE

    assert window._current_csl_key_from_tab(None) == DEFAULT_CSL_STYLE


def test_set_csl_style_noop_without_a_tab(window):
    _close_every_tab(window)
    window._set_csl_style("apa")  # must not raise


def test_set_csl_style_no_change_shows_status(window):
    tab = window._new_tab()
    tab.editor.setPlainText("---\ncsl: apa\n---\n\nBody\n")
    window._set_csl_style("apa")
    assert "no change" in window.statusBar().currentMessage().lower()


def test_edit_document_properties_noop_without_a_tab(window):
    _close_every_tab(window)
    window._edit_document_properties()  # must not raise


def test_link_bibliography_noop_without_a_tab(window):
    _close_every_tab(window)
    window._link_bibliography()  # must not raise


def test_link_bibliography_cancelled_leaves_buffer(window):
    tab = window._new_tab()
    tab.editor.setPlainText("# Doc\n")
    with patch.object(
        app_mod.QFileDialog, "getOpenFileName", return_value=("", "")
    ):
        window._link_bibliography()
    assert tab.editor.toPlainText() == "# Doc\n"


def test_export_docx_noop_without_a_tab(window):
    _close_every_tab(window)
    window._export_docx()  # must not raise
    assert window._exports_in_flight == 0


def test_export_docx_cancel_writes_nothing(window, tmp_path):
    tab = window._new_tab()
    tab.editor.setPlainText("# x\n")
    with patch.object(
        app_mod.QFileDialog, "getSaveFileName", return_value=("", "")
    ):
        window._export_docx()
    assert not list(tmp_path.glob("*.docx"))
    assert window._exports_in_flight == 0


def test_export_docx_appends_suffix_when_missing(window, tmp_path):
    tab = window._new_tab()
    tab.editor.setPlainText("# x\n")
    target = tmp_path / "nosuffix"
    with patch.object(
        app_mod.QFileDialog, "getSaveFileName",
        return_value=(str(target), ""),
    ), patch.object(app_mod, "export_docx") as exp:
        window._export_docx()
    assert exp.call_args.args[1] == tmp_path / "nosuffix.docx"


def test_export_html_noop_without_a_tab(window):
    _close_every_tab(window)
    window._export_html()  # must not raise
    assert window._exports_in_flight == 0


def test_export_pdf_noop_without_a_tab(window):
    _close_every_tab(window)
    window._export_pdf()  # must not raise
    assert window._exports_in_flight == 0


def test_export_pdf_cancel_starts_nothing(window):
    tab = window._new_tab()
    tab.editor.setPlainText("# x\n")
    with patch.object(
        app_mod.QFileDialog, "getSaveFileName", return_value=("", "")
    ):
        window._export_pdf()
    assert window._exports_in_flight == 0


def test_export_pdf_appends_suffix_when_missing(window, tmp_path):
    tab = window._new_tab()
    tab.editor.setPlainText("# x\n")
    target = tmp_path / "nosuffix"
    with patch.object(
        app_mod.QFileDialog, "getSaveFileName",
        return_value=(str(target), ""),
    ), patch.object(MarkdownTab, "export_pdf") as exp:
        window._export_pdf()
    assert exp.call_args.args[0] == tmp_path / "nosuffix.pdf"
    # export "started" (on_done was never invoked by the mock).
    assert window._exports_in_flight == 1


def test_export_pdf_bad_attachment_warns_and_stops(window, tmp_path):
    """A cover/annex path that resolve_pdf_attachments rejects is shown
    to the user verbatim instead of the generic failure message."""
    tab = window._new_tab()
    tab.editor.setPlainText("# x\n")
    target = tmp_path / "out.pdf"
    with patch.object(
        app_mod.QFileDialog, "getSaveFileName",
        return_value=(str(target), ""),
    ), patch.object(
        MarkdownTab, "export_pdf",
        side_effect=FileNotFoundError("ghost.pdf"),
    ), patch.object(app_mod.QMessageBox, "warning") as warn:
        window._export_pdf()
    warn.assert_called_once()
    assert window._exports_in_flight == 0


def test_reload_current_noop_without_a_path(window):
    window._new_tab()
    window._reload_current()  # untitled tab: must not raise


def test_reload_current_declined_keeps_dirty_buffer(window, tmp_path):
    doc = tmp_path / "reload.md"
    doc.write_text("original\n", encoding="utf-8")
    window.open_path(doc)
    tab = window._current_tab()
    tab.editor.setPlainText("dirty edit")
    with patch.object(
        QMessageBox, "question",
        return_value=QMessageBox.StandardButton.No,
    ):
        window._reload_current()
    assert tab.text() == "dirty edit"


def test_save_current_writes_directly_when_path_is_set(window, tmp_path):
    """A tab that already has a path saves without opening Save As."""
    doc = tmp_path / "existing.md"
    doc.write_text("old\n", encoding="utf-8")
    window.open_path(doc)
    tab = window._current_tab()
    tab.editor.setPlainText("new content\n")

    def _fail_dialog(*args, **kwargs):
        raise AssertionError("Save As should not open")

    with patch.object(
        app_mod.QFileDialog, "getSaveFileName", side_effect=_fail_dialog
    ):
        assert window._save_current() is True
    assert doc.read_text(encoding="utf-8") == "new content\n"
    assert "Saved" in window.statusBar().currentMessage()


def test_save_current_as_noop_without_a_tab(window):
    _close_every_tab(window)
    assert window._save_current_as() is False


def test_new_bib_entry_noop_without_a_tab(window):
    _close_every_tab(window)
    window._new_bib_entry()  # must not raise


def test_new_bib_entry_links_a_fresh_bib_when_none_set(window, tmp_path):
    """No linked .bib yet: the save-target dialog runs, and its choice
    becomes the new bibliography: link."""
    doc = tmp_path / "doc.md"
    doc.write_text("# Doc\n", encoding="utf-8")
    window.open_path(doc)
    tab = window._current_tab()
    bib_target = tmp_path / "new.bib"

    class _FakeBibDialog:
        DialogCode = QDialog.DialogCode

        def __init__(self, *a, **k):
            pass

        def exec(self):
            return QDialog.DialogCode.Rejected  # stop right after linking

    with patch.object(
        app_mod.QFileDialog, "getSaveFileName",
        return_value=(str(bib_target), ""),
    ), patch(
        "epy_reports._ui.bib_dialog.BibEntryDialog", _FakeBibDialog
    ):
        window._new_bib_entry()
    assert tab.bib_path() is not None
    assert tab.bib_path().resolve() == bib_target.resolve()


def test_new_bib_entry_cancelled_target_picker_is_a_noop(window, tmp_path):
    doc = tmp_path / "doc.md"
    doc.write_text("# Doc\n", encoding="utf-8")
    window.open_path(doc)
    tab = window._current_tab()
    with patch.object(
        app_mod.QFileDialog, "getSaveFileName", return_value=("", "")
    ):
        window._new_bib_entry()
    assert tab.bib_path() is None


def test_new_bib_entry_dialog_cancelled_appends_nothing(window, tmp_path):
    doc = tmp_path / "doc.md"
    doc.write_text("# Doc\n", encoding="utf-8")
    window.open_path(doc)
    tab = window._current_tab()
    bib_file = tmp_path / "refs.bib"
    bib_file.write_text("@misc{a, title={A}}\n", encoding="utf-8")
    tab.link_bibliography(bib_file)

    class _FakeBibDialog:
        DialogCode = QDialog.DialogCode

        def __init__(self, *a, **k):
            pass

        def exec(self):
            return QDialog.DialogCode.Rejected

    with patch(
        "epy_reports._ui.bib_dialog.BibEntryDialog", _FakeBibDialog
    ):
        window._new_bib_entry()
    assert bib_file.read_text(encoding="utf-8") == "@misc{a, title={A}}\n"


def test_resolve_reference_doc_returns_none_on_lookup_failure(
    window, monkeypatch
):
    monkeypatch.setattr(
        importlib.resources, "files",
        lambda *a, **k: (_ for _ in ()).throw(ModuleNotFoundError("x")),
    )
    assert window._resolve_reference_doc("corporate") is None


# ---------------------------------------------------------------------------
# Themes: gallery / design-block picker / editor / delete
# ---------------------------------------------------------------------------


def test_refresh_themes_selects_the_given_id(window):
    from epy_reports._core import themes

    target = next(iter(themes.THEMES))
    window._refresh_themes(select_id=target)
    assert window._current_theme.id == target


def test_open_theme_gallery_applies_the_chosen_theme(window):
    from epy_reports._core import themes

    target = next(
        tid for tid in themes.THEMES if tid != window._current_theme.id
    )

    class _FakeGallery:
        def __init__(self, *a, **k):
            pass

        def exec(self):
            return QDialog.DialogCode.Accepted

        def selected_theme_id(self):
            return target

    with patch(
        "epy_reports._ui.theme_gallery_dialog.ThemeGalleryDialog",
        _FakeGallery,
    ):
        window._open_theme_gallery()
    assert window._current_theme.id == target


def test_open_theme_gallery_cancelled_keeps_current_theme(window):
    current = window._current_theme.id

    class _FakeGallery:
        def __init__(self, *a, **k):
            pass

        def exec(self):
            return QDialog.DialogCode.Rejected

    with patch(
        "epy_reports._ui.theme_gallery_dialog.ThemeGalleryDialog",
        _FakeGallery,
    ):
        window._open_theme_gallery()
    assert window._current_theme.id == current


def test_open_design_block_picker_inserts_the_chosen_block(window):
    tab = window._new_tab()
    tab.editor.setPlainText("")

    class _FakePicker:
        def __init__(self, *a, **k):
            pass

        def exec(self):
            return QDialog.DialogCode.Accepted

        def selected_kind(self):
            return "stat"

    with patch(
        "epy_reports._ui.design_block_dialog.DesignBlockDialog",
        _FakePicker,
    ):
        window._open_design_block_picker()
    assert "::: {.stat}" in tab.editor.toPlainText()


def test_open_design_block_picker_cancelled_inserts_nothing(window):
    tab = window._new_tab()
    tab.editor.setPlainText("")

    class _FakePicker:
        def __init__(self, *a, **k):
            pass

        def exec(self):
            return QDialog.DialogCode.Rejected

    with patch(
        "epy_reports._ui.design_block_dialog.DesignBlockDialog",
        _FakePicker,
    ):
        window._open_design_block_picker()
    assert tab.editor.toPlainText() == ""


def test_open_theme_editor_save_failure_warns(window):
    """A save_user_theme OSError (e.g. a read-only config dir) is shown
    to the user instead of propagating."""
    from epy_reports._core import themes

    class _FakeEditor:
        def __init__(self, *a, **k):
            pass

        def exec(self):
            return QDialog.DialogCode.Accepted

        def epyson_payload(self):
            return {}

        def theme_name(self):
            return "Broken"

    with patch(
        "epy_reports._ui.theme_editor_dialog.ThemeEditorDialog", _FakeEditor
    ), patch.object(
        themes, "save_user_theme",
        side_effect=OSError("disk full"),
    ), patch.object(app_mod.QMessageBox, "warning") as warn:
        window._open_theme_editor()
    warn.assert_called_once()


def test_delete_custom_theme_no_custom_themes_informs(window):
    with patch.object(app_mod.QMessageBox, "information") as info:
        window._delete_custom_theme()
    info.assert_called_once()


def test_delete_custom_theme_picker_cancelled(window, tmp_path, monkeypatch):
    from epy_reports._core import epyson, themes

    monkeypatch.setattr(epyson, "user_themes_dir", lambda: tmp_path)
    theme_id = themes.save_user_theme(
        epyson.build_epyson(
            {
                "display_name": "Mine",
                "page_bg": "#ffffff", "text": "#000000",
                "heading": "#000000",
                "primary": "#000000", "secondary": "#000000",
                "border": "#cccccc",
                "code_bg": "#eeeeee", "mark": "#ffff00",
                "text_font": "Arial", "code_font": "Consolas",
                "scales": {
                    role: {"size": 12.0, "weight": "400"}
                    for role in (
                        "h1", "h2", "h3", "h4", "h5", "h6",
                        "text", "caption",
                    )
                },
                "callouts": {
                    kind: {"bg": "#eeeeee", "border": "#000000"}
                    for kind in (
                        "note", "tip", "warning", "important", "caution"
                    )
                },
            }
        )
    )
    themes.reload()
    try:
        from PySide6.QtWidgets import QInputDialog

        with patch.object(
            QInputDialog, "getItem", return_value=("Mine", False)
        ):
            window._delete_custom_theme()
        assert theme_id in themes.user_theme_ids()
    finally:
        themes.delete_user_theme(theme_id)
        themes.reload()


def test_delete_custom_theme_confirmed_removes_it(
    window, tmp_path, monkeypatch
):
    from epy_reports._core import epyson, themes

    monkeypatch.setattr(epyson, "user_themes_dir", lambda: tmp_path)
    theme_id = themes.save_user_theme(
        epyson.build_epyson(
            {
                "display_name": "Mine2",
                "page_bg": "#ffffff", "text": "#000000",
                "heading": "#000000",
                "primary": "#000000", "secondary": "#000000",
                "border": "#cccccc",
                "code_bg": "#eeeeee", "mark": "#ffff00",
                "text_font": "Arial", "code_font": "Consolas",
                "scales": {
                    role: {"size": 12.0, "weight": "400"}
                    for role in (
                        "h1", "h2", "h3", "h4", "h5", "h6",
                        "text", "caption",
                    )
                },
                "callouts": {
                    kind: {"bg": "#eeeeee", "border": "#000000"}
                    for kind in (
                        "note", "tip", "warning", "important", "caution"
                    )
                },
            }
        )
    )
    themes.reload()
    window._refresh_themes()
    from PySide6.QtWidgets import QInputDialog

    with patch.object(
        QInputDialog, "getItem", return_value=("Mine2", True)
    ), patch.object(
        QMessageBox, "question",
        return_value=QMessageBox.StandardButton.Yes,
    ):
        window._delete_custom_theme()
    assert theme_id not in themes.user_theme_ids()


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------


def test_populate_apply_template_menu_lists_saved_templates(
    window, tmp_path, monkeypatch
):
    from epy_reports._core import templates

    monkeypatch.setattr(templates, "_config_base_dir", lambda: tmp_path)
    templates.save_template("My Template", {"theme": "corporate"})
    window._build_templates_menu()
    window._populate_apply_template_menu()
    texts = [a.text() for a in window.apply_template_menu.actions()]
    assert "My Template" in texts


def test_populate_apply_template_menu_empty_shows_placeholder(
    window, tmp_path, monkeypatch
):
    from epy_reports._core import templates

    monkeypatch.setattr(templates, "_config_base_dir", lambda: tmp_path)
    window._build_templates_menu()
    window._populate_apply_template_menu()
    texts = [a.text() for a in window.apply_template_menu.actions()]
    assert any("no templates" in t.lower() for t in texts)


def test_populate_delete_template_menu_lists_saved_templates(
    window, tmp_path, monkeypatch
):
    from epy_reports._core import templates

    monkeypatch.setattr(templates, "_config_base_dir", lambda: tmp_path)
    templates.save_template("Deletable", {"theme": "corporate"})
    window._build_templates_menu()
    window._populate_delete_template_menu()
    texts = [a.text() for a in window.delete_template_menu.actions()]
    assert "Deletable" in texts


def test_populate_delete_template_menu_empty_shows_placeholder(
    window, tmp_path, monkeypatch
):
    from epy_reports._core import templates

    monkeypatch.setattr(templates, "_config_base_dir", lambda: tmp_path)
    window._build_templates_menu()
    window._populate_delete_template_menu()
    texts = [a.text() for a in window.delete_template_menu.actions()]
    assert any("no templates" in t.lower() for t in texts)


def test_save_template_cancelled_saves_nothing(window, tmp_path, monkeypatch):
    from epy_reports._core import templates

    monkeypatch.setattr(templates, "_config_base_dir", lambda: tmp_path)
    with patch(
        "PySide6.QtWidgets.QInputDialog.getText",
        return_value=("", False),
    ):
        window._save_template()
    assert templates.list_templates() == []


def test_save_template_failure_warns(window, tmp_path, monkeypatch):
    from epy_reports._core import templates

    monkeypatch.setattr(templates, "_config_base_dir", lambda: tmp_path)
    with patch(
        "PySide6.QtWidgets.QInputDialog.getText",
        return_value=("Bad", True),
    ), patch.object(
        templates, "save_template",
        side_effect=OSError("disk full"),
    ), patch.object(app_mod.QMessageBox, "warning") as warn:
        window._save_template()
    warn.assert_called_once()


def test_apply_template_load_failure_warns(window, monkeypatch):
    from epy_reports._core import templates

    with patch.object(
        templates, "load_template",
        side_effect=FileNotFoundError("no such template"),
    ), patch.object(app_mod.QMessageBox, "warning") as warn:
        window._apply_template("ghost")
    warn.assert_called_once()


def test_apply_template_noop_without_a_tab(window, tmp_path, monkeypatch):
    from epy_reports._core import templates

    monkeypatch.setattr(templates, "_config_base_dir", lambda: tmp_path)
    templates.save_template("NoTab", {"theme": "corporate"})
    _close_every_tab(window)
    window._apply_template("NoTab")  # must not raise past the theme switch


def test_apply_template_writes_header_as_raw_flow_sequence(
    window, tmp_path, monkeypatch
):
    from epy_reports._core import templates

    monkeypatch.setattr(templates, "_config_base_dir", lambda: tmp_path)
    templates.save_template(
        "WithHeader", {"theme": "corporate", "header": '["Left", "Right"]'}
    )
    tab = window._new_tab()
    tab.editor.setPlainText("# Body\n")
    window._apply_template("WithHeader")
    assert 'header: ["Left", "Right"]' in tab.editor.toPlainText()


def test_delete_template_declined_keeps_it(window, tmp_path, monkeypatch):
    from epy_reports._core import templates

    monkeypatch.setattr(templates, "_config_base_dir", lambda: tmp_path)
    templates.save_template("Keep", {"theme": "corporate"})
    with patch.object(
        QMessageBox, "question",
        return_value=QMessageBox.StandardButton.No,
    ):
        window._delete_template("Keep")
    assert "Keep" in templates.list_templates()


# ---------------------------------------------------------------------------
# epy_docs export path
# ---------------------------------------------------------------------------


def test_docs_export_action_disabled_without_epy_docs(qapp, monkeypatch):
    """_build_actions disables the docs-export action and sets a tooltip
    when the optional epy_docs package is not installed."""
    monkeypatch.setattr(app_mod, "QSettings", _ScratchSettings)
    monkeypatch.setattr(app_mod, "epy_docs_available", lambda: False)
    win = MarkdownWindow()
    try:
        assert win.act_docs_export.isEnabled() is False
        assert win.act_docs_export.toolTip() == (
            "Requires the epy-docs package"
        )
    finally:
        _teardown_window(win, qapp)


def test_export_via_docs_noop_without_a_tab(window):
    _close_every_tab(window)
    window._export_via_docs()  # must not raise
    assert window._exports_in_flight == 0


def test_export_via_docs_prompts_to_save_dirty_untitled_buffer(window):
    """A dirty/untitled buffer prompts Save before the docs dialog opens;
    declining aborts without ever building the dialog."""
    tab = window._new_tab()
    tab.editor.setPlainText("# dirty\n")
    with patch.object(
        QMessageBox, "question",
        return_value=QMessageBox.StandardButton.Cancel,
    ), patch(
        "epy_reports._ui.docs_export_dialog.DocsExportDialog"
    ) as dlg_cls:
        window._export_via_docs()
    dlg_cls.assert_not_called()
    assert window._exports_in_flight == 0


def test_export_via_docs_dialog_cancelled(window, tmp_path):
    doc = tmp_path / "doc.md"
    doc.write_text("# Doc\n", encoding="utf-8")
    window.open_path(doc)

    class _FakeDialog:
        DialogCode = QDialog.DialogCode

        def __init__(self, *a, **k):
            pass

        def exec(self):
            return QDialog.DialogCode.Rejected

    with patch(
        "epy_reports._ui.docs_export_dialog.DocsExportDialog", _FakeDialog
    ):
        window._export_via_docs()
    assert window._exports_in_flight == 0


# ---------------------------------------------------------------------------
# Printing
# ---------------------------------------------------------------------------


def test_print_document_noop_without_a_tab(window):
    _close_every_tab(window)
    window._print_document()  # must not raise


def test_print_document_cancelled_dialog_does_not_print(window):
    from PySide6.QtPrintSupport import QPrintDialog

    with patch.object(
        QPrintDialog, "exec",
        return_value=QPrintDialog.DialogCode.Rejected,
    ):
        window._print_document()
    assert getattr(window, "_active_printer", None) is None


def test_print_document_accepted_starts_an_async_print(window):
    """Accepting the print dialog starts an async print and remembers the
    QPrinter until the completion callback fires.

    The tab's REAL QWebEnginePage.print(...) is patched directly (rather
    than swapping out MarkdownTab.view, a real QWebEngineView) so this
    stays a behavioural test of the window's own async bookkeeping.
    """
    from PySide6.QtPrintSupport import QPrintDialog

    printed = []
    tab = window._current_tab()
    real_page = tab.view.page()
    with patch.object(
        QPrintDialog, "exec",
        return_value=QPrintDialog.DialogCode.Accepted,
    ), patch.object(
        type(real_page), "print",
        lambda self, printer, cb: printed.append((printer, cb)),
        create=True,  # QWebEnginePage.print is a runtime-only Qt addon
        # method (registered when QtPrintSupport loads); it is not a
        # real class attribute until then, so plain patch.object would
        # refuse it with AttributeError.
    ):
        window._print_document()
    assert len(printed) == 1
    assert window._active_printer is not None
    # Simulate Qt invoking the completion callback.
    printed[0][1](True)
    assert window._active_printer is None


# ---------------------------------------------------------------------------
# Tab lifecycle: close / closeEvent / drag-drop
# ---------------------------------------------------------------------------


def test_close_tab_at_non_tab_widget_is_a_noop(window):
    """An index whose widget is not a MarkdownTab (defensive) is ignored."""
    before = window.tabs.count()
    window.tabs.addTab(app_mod.QMainWindow(), "not a tab")
    last_index = window.tabs.count() - 1
    window._close_tab_at(last_index)
    assert window.tabs.count() == before + 1  # untouched, only appended


def test_close_tab_at_declined_confirm_keeps_the_tab(window):
    tab = window._current_tab()
    tab.editor.setPlainText("dirty")
    index = window.tabs.indexOf(tab)
    with patch.object(
        QMessageBox, "question",
        return_value=QMessageBox.StandardButton.Cancel,
    ):
        window._close_tab_at(index)
    assert window.tabs.indexOf(tab) == index  # still there


def test_close_current_tab_with_no_selection_is_a_noop(window):
    window.tabs.setCurrentIndex(-1)
    before = window.tabs.count()
    window._close_current_tab()
    assert window.tabs.count() == before


def test_close_event_accepts_when_every_tab_is_clean(window):
    tab = window._current_tab()
    assert tab.dirty is False

    class _FakeEvent:
        def __init__(self):
            self.accepted = False
            self.ignored = False

        def accept(self):
            self.accepted = True

        def ignore(self):
            self.ignored = True

    event = _FakeEvent()
    window.closeEvent(event)
    assert event.accepted is True
    assert event.ignored is False


def test_close_event_ignores_when_a_tab_declines_close(window):
    tab = window._current_tab()
    tab.editor.setPlainText("dirty")

    class _FakeEvent:
        def __init__(self):
            self.accepted = False
            self.ignored = False

        def accept(self):
            self.accepted = True

        def ignore(self):
            self.ignored = True

    event = _FakeEvent()
    with patch.object(
        QMessageBox, "question",
        return_value=QMessageBox.StandardButton.Cancel,
    ):
        window.closeEvent(event)
    assert event.ignored is True
    assert event.accepted is False


def test_confirm_close_save_choice_delegates_to_save_current(
    window, tmp_path
):
    doc = tmp_path / "confirm.md"
    doc.write_text("old\n", encoding="utf-8")
    window.open_path(doc)
    tab = window._current_tab()
    tab.editor.setPlainText("new\n")
    with patch.object(
        QMessageBox, "question",
        return_value=QMessageBox.StandardButton.Save,
    ):
        assert window._confirm_close(tab) is True
    assert doc.read_text(encoding="utf-8") == "new\n"


def test_drag_enter_event_accepts_url_drags(window):
    class _FakeMime:
        def hasUrls(self):  # noqa: N802 - Qt API name
            return True

    class _FakeEvent:
        def __init__(self):
            self.accepted = False

        def mimeData(self):  # noqa: N802 - Qt API name
            return _FakeMime()

        def acceptProposedAction(self):  # noqa: N802 - Qt API name
            self.accepted = True

    event = _FakeEvent()
    window.dragEnterEvent(event)
    assert event.accepted is True


def test_drag_enter_event_ignores_non_url_drags(window):
    class _FakeMime:
        def hasUrls(self):  # noqa: N802 - Qt API name
            return False

    class _FakeEvent:
        def __init__(self):
            self.accepted = False

        def mimeData(self):  # noqa: N802 - Qt API name
            return _FakeMime()

        def acceptProposedAction(self):  # noqa: N802 - Qt API name
            self.accepted = True

    event = _FakeEvent()
    window.dragEnterEvent(event)
    assert event.accepted is False


def test_drop_event_opens_supported_files_only(window, tmp_path):
    md = tmp_path / "dropped.md"
    md.write_text("# Dropped\n", encoding="utf-8")
    other = tmp_path / "ignored.txt"
    other.write_text("nope", encoding="utf-8")

    from PySide6.QtCore import QUrl

    class _FakeMime:
        def urls(self):
            return [
                QUrl.fromLocalFile(str(md)),
                QUrl.fromLocalFile(str(other)),
            ]

    class _FakeEvent:
        def mimeData(self):  # noqa: N802 - Qt API name
            return _FakeMime()

    window.dropEvent(_FakeEvent())
    tab = window._current_tab()
    assert tab.path is not None
    assert tab.path.resolve() == md.resolve()


# ---------------------------------------------------------------------------
# refresh_tab_title: stale index guard
# ---------------------------------------------------------------------------


def test_refresh_tab_title_ignores_a_removed_tab(window):
    tab = window._new_tab()
    window.tabs.removeTab(window.tabs.indexOf(tab))
    window._refresh_tab_title(tab)  # must not raise (index < 0)


# ---------------------------------------------------------------------------
# CLI entry points
# ---------------------------------------------------------------------------


def test_build_parser_accepts_files_and_flags():
    """The argparse parser exposes the documented options."""
    parser = app_mod._build_parser()
    args = parser.parse_args(["a.md", "--register", "--as-default"])
    assert args.files == ["a.md"]
    assert args.register is True
    assert args.as_default is True


def test_main_dispatches_to_register(monkeypatch):
    """``main --register`` routes to the register runner."""
    called = {}

    def _fake(make_default):
        called["default"] = make_default
        return 0

    monkeypatch.setattr(app_mod, "_run_register", _fake)
    assert app_mod.main(["--register", "--as-default"]) == 0
    assert called["default"] is True


def test_main_dispatches_to_unregister(monkeypatch):
    """``main --unregister`` routes to the unregister runner."""
    monkeypatch.setattr(app_mod, "_run_unregister", lambda: 7)
    assert app_mod.main(["--unregister"]) == 7


def test_main_dispatches_to_set_default(monkeypatch):
    """``main --set-default`` routes to the set-default runner."""
    monkeypatch.setattr(app_mod, "_run_set_default", lambda: 3)
    assert app_mod.main(["--set-default"]) == 3


def test_main_dispatches_to_gui(monkeypatch):
    """Bare ``main`` routes to the GUI runner with the file list."""
    seen = {}

    def _fake(files):
        seen["files"] = files
        return 0

    monkeypatch.setattr(app_mod, "_run_gui", _fake)
    assert app_mod.main(["x.md", "y.qmd"]) == 0
    assert seen["files"] == ["x.md", "y.qmd"]


def test_ensure_utf8_streams_is_safe():
    """Reconfiguring the streams never raises."""
    app_mod._ensure_utf8_streams()


def test_run_register_uses_winreg(monkeypatch):
    """``_run_register`` prints the changes returned by winreg_assoc."""
    from epy_reports._core import winreg_assoc

    monkeypatch.setattr(
        winreg_assoc, "register", lambda make_default=False: ["did a thing"]
    )
    monkeypatch.setattr(
        winreg_assoc, "open_default_apps_settings", lambda: True
    )
    assert app_mod._run_register(make_default=False) == 0


def test_run_unregister_reports_nothing(monkeypatch):
    """``_run_unregister`` reports when there was nothing to remove."""
    from epy_reports._core import winreg_assoc

    monkeypatch.setattr(winreg_assoc, "unregister", lambda: [])
    assert app_mod._run_unregister() == 0


def test_run_set_default_failure_returns_2(monkeypatch):
    """A failed Settings launch returns exit code 2."""
    from epy_reports._core import winreg_assoc

    monkeypatch.setattr(
        winreg_assoc, "open_default_apps_settings", lambda: False
    )
    assert app_mod._run_set_default() == 2


def test_run_set_default_success_returns_0(monkeypatch):
    from epy_reports._core import winreg_assoc

    monkeypatch.setattr(
        winreg_assoc, "open_default_apps_settings", lambda: True
    )
    assert app_mod._run_set_default() == 0


def test_run_register_make_default_opens_settings(monkeypatch):
    """--register --as-default also opens the Default apps Settings page."""
    from epy_reports._core import winreg_assoc

    opened = []
    monkeypatch.setattr(
        winreg_assoc, "register", lambda make_default=False: ["did a thing"]
    )
    monkeypatch.setattr(
        winreg_assoc, "open_default_apps_settings",
        lambda: opened.append(1),
    )
    assert app_mod._run_register(make_default=True) == 0
    assert opened == [1]


def test_run_register_runtime_error_returns_2(monkeypatch, capsys):
    from epy_reports._core import winreg_assoc

    def _raise(make_default=False):
        raise RuntimeError("Windows only")

    monkeypatch.setattr(winreg_assoc, "register", _raise)
    assert app_mod._run_register(make_default=False) == 2
    assert "error:" in capsys.readouterr().err


def test_run_unregister_runtime_error_returns_2(monkeypatch, capsys):
    from epy_reports._core import winreg_assoc

    def _raise():
        raise RuntimeError("Windows only")

    monkeypatch.setattr(winreg_assoc, "unregister", _raise)
    assert app_mod._run_unregister() == 2
    assert "error:" in capsys.readouterr().err


def test_run_unregister_prints_each_removed_change(monkeypatch, capsys):
    from epy_reports._core import winreg_assoc

    monkeypatch.setattr(
        winreg_assoc, "unregister", lambda: ["Removed X", "Removed Y"]
    )
    assert app_mod._run_unregister() == 0
    out = capsys.readouterr().out
    assert "Removed X" in out
    assert "Removed Y" in out


def test_run_gui_boots_app_shows_window_and_opens_existing_files(
    monkeypatch, tmp_path
):
    """_run_gui's own orchestration: build the QApplication, set its
    icon, create+show the window, open only the files that exist, and
    return app.exec()'s value. QApplication and MarkdownWindow are both
    replaced with lightweight fakes -- a second real QApplication cannot
    coexist with the session's real one, and a real MarkdownWindow is
    exercised at length elsewhere in this file.
    """
    calls: dict[str, object] = {}

    class _FakeApp:
        def __init__(self, argv):
            calls["argv"] = argv

        def setWindowIcon(self, icon):  # noqa: N802 - Qt API name
            calls["icon"] = icon

        def exec(self):
            return 42

    class _FakeWindow:
        def __init__(self):
            self.opened: list[Path] = []
            calls["window_created"] = True

        def show(self):
            calls["shown"] = True

        def open_path(self, path):
            self.opened.append(path)

    windows: list[_FakeWindow] = []

    def _make_window():
        w = _FakeWindow()
        windows.append(w)
        return w

    monkeypatch.setattr(app_mod, "QApplication", _FakeApp)
    monkeypatch.setattr(app_mod, "MarkdownWindow", _make_window)

    existing = tmp_path / "a.md"
    existing.write_text("x", encoding="utf-8")
    missing = tmp_path / "ghost.md"

    result = app_mod._run_gui([str(existing), str(missing)])

    assert result == 42
    assert calls["shown"] is True
    assert windows[0].opened == [existing]


# ---------------------------------------------------------------------------
# _ensure_utf8_streams: streams with no reconfigure / a None stream
# ---------------------------------------------------------------------------


def test_ensure_utf8_streams_skips_a_none_stream(monkeypatch):
    """A None stdout (frozen GUI with no console) is skipped, not crashed
    on."""
    monkeypatch.setattr(app_mod.sys, "stdout", None)
    app_mod._ensure_utf8_streams()  # must not raise


def test_ensure_utf8_streams_skips_a_stream_without_reconfigure(
    monkeypatch,
):
    class _NoReconfigure:
        pass

    monkeypatch.setattr(app_mod.sys, "stdout", _NoReconfigure())
    app_mod._ensure_utf8_streams()  # must not raise


# ---------------------------------------------------------------------------
# _load_manual_text: OSError from the Spanish-screenshot existence check
# ---------------------------------------------------------------------------


def test_load_manual_text_es_screenshot_check_absorbs_oserror(monkeypatch):
    """A resource backend that raises OSError on is_file() (e.g. a broken
    frozen bundle) is absorbed; the manual still loads (English
    screenshots are kept when the Spanish existence check itself fails).

    ``importlib.resources.files(...)`` resolves to a plain
    ``pathlib.WindowsPath`` for a real source install (verified directly:
    its ``is_file`` IS ``pathlib.Path.is_file``), so that is the method
    patched here -- scoped to only ``*_es.png`` targets so every other
    ``is_file()`` call in the same test (fixtures, Qt internals) still
    behaves normally.
    """
    real_is_file = Path.is_file

    def _fake_is_file(self):
        if self.name.endswith("_es.png"):
            raise OSError("broken bundle")
        return real_is_file(self)

    monkeypatch.setattr(Path, "is_file", _fake_is_file)
    text = app_mod._load_manual_text("welcome_es.md")
    assert "__EPY_LOGO__" not in text


# ---------------------------------------------------------------------------
# Window construction: persisted Spanish language preference
# ---------------------------------------------------------------------------


def test_window_restores_persisted_spanish_language(qapp, monkeypatch):
    class _SpanishSettings(_ScratchSettings):
        def value(self, key, default=None, _type=None):
            if key == "language":
                return "es"
            return super().value(key, default, _type)

    monkeypatch.setattr(app_mod, "QSettings", _SpanishSettings)
    win = MarkdownWindow()
    try:
        assert i18n.current_language() == "es"
        assert win.act_new.text() == "Nuevo"
    finally:
        _teardown_window(win, qapp)


# ---------------------------------------------------------------------------
# References menu: citations from a linked, non-empty bibliography
# ---------------------------------------------------------------------------


def test_references_menu_lists_citations_from_linked_bib(window, tmp_path):
    tab = window._new_tab()
    doc = tmp_path / "doc.md"
    tab.set_initial_text("Body\n", path=doc)
    bib_file = tmp_path / "refs.bib"
    bib_file.write_text(
        "@article{smith2020, title={A Title}, author={Smith}}\n",
        encoding="utf-8",
    )
    tab.link_bibliography(bib_file)
    window._populate_references_menu()
    titles = [
        m.title()
        for m in window.references_menu.findChildren(
            type(window.references_menu)
        )
    ]
    assert any("Citations" in t for t in titles)


# ---------------------------------------------------------------------------
# Theme submenu language sync + edit-current-theme
# ---------------------------------------------------------------------------


def test_refresh_themes_retranslates_when_language_is_spanish(window):
    window._set_language("es")
    try:
        window._refresh_themes()  # must not raise while relabeling
        assert window.act_theme_gallery.text() != ""
    finally:
        window._set_language("en")


def test_edit_current_theme_opens_editor_for_a_bundled_theme(window):
    """A bundled (non-custom) theme is edited as a NEW theme (edit_id is
    None), so the editor is opened without an existing custom id."""
    seen = {}

    class _FakeEditor:
        def __init__(self, *a, **k):
            seen["edit_id"] = k.get("edit_id")

        def exec(self):
            return QDialog.DialogCode.Rejected

    with patch(
        "epy_reports._ui.theme_editor_dialog.ThemeEditorDialog", _FakeEditor
    ):
        window._edit_current_theme()
    assert seen["edit_id"] is None


def test_open_theme_editor_cancelled_saves_nothing(window):
    class _FakeEditor:
        def __init__(self, *a, **k):
            pass

        def exec(self):
            return QDialog.DialogCode.Rejected

    with patch(
        "epy_reports._ui.theme_editor_dialog.ThemeEditorDialog", _FakeEditor
    ):
        window._open_theme_editor()  # must not raise


def test_open_theme_editor_save_success_refreshes_and_selects(
    window, tmp_path, monkeypatch
):
    from epy_reports._core import epyson, themes

    monkeypatch.setattr(epyson, "user_themes_dir", lambda: tmp_path)
    payload = epyson.build_epyson(
        {
            "display_name": "Saved OK",
            "page_bg": "#ffffff", "text": "#000000", "heading": "#000000",
            "primary": "#000000", "secondary": "#000000",
            "border": "#cccccc",
            "code_bg": "#eeeeee", "mark": "#ffff00",
            "text_font": "Arial", "code_font": "Consolas",
            "scales": {
                role: {"size": 12.0, "weight": "400"}
                for role in (
                    "h1", "h2", "h3", "h4", "h5", "h6", "text", "caption",
                )
            },
            "callouts": {
                kind: {"bg": "#eeeeee", "border": "#000000"}
                for kind in (
                    "note", "tip", "warning", "important", "caution"
                )
            },
        }
    )

    class _FakeEditor:
        def __init__(self, *a, **k):
            pass

        def exec(self):
            return QDialog.DialogCode.Accepted

        def epyson_payload(self):
            return payload

        def theme_name(self):
            return "Saved OK"

    try:
        with patch(
            "epy_reports._ui.theme_editor_dialog.ThemeEditorDialog",
            _FakeEditor,
        ):
            window._open_theme_editor()
        assert window._current_theme.display_name == "Saved OK"
        assert "Theme saved" in window.statusBar().currentMessage()
    finally:
        for theme_id in list(themes.user_theme_ids()):
            themes.delete_user_theme(theme_id)
        themes.reload()


def test_delete_custom_theme_confirm_declined_keeps_it(
    window, tmp_path, monkeypatch
):
    from epy_reports._core import epyson, themes

    monkeypatch.setattr(epyson, "user_themes_dir", lambda: tmp_path)
    theme_id = themes.save_user_theme(
        epyson.build_epyson(
            {
                "display_name": "KeepMe",
                "page_bg": "#ffffff", "text": "#000000",
                "heading": "#000000",
                "primary": "#000000", "secondary": "#000000",
                "border": "#cccccc",
                "code_bg": "#eeeeee", "mark": "#ffff00",
                "text_font": "Arial", "code_font": "Consolas",
                "scales": {
                    role: {"size": 12.0, "weight": "400"}
                    for role in (
                        "h1", "h2", "h3", "h4", "h5", "h6",
                        "text", "caption",
                    )
                },
                "callouts": {
                    kind: {"bg": "#eeeeee", "border": "#000000"}
                    for kind in (
                        "note", "tip", "warning", "important", "caution"
                    )
                },
            }
        )
    )
    themes.reload()
    try:
        from PySide6.QtWidgets import QInputDialog

        with patch.object(
            QInputDialog, "getItem", return_value=("KeepMe", True)
        ), patch.object(
            QMessageBox, "question",
            return_value=QMessageBox.StandardButton.No,
        ):
            window._delete_custom_theme()
        assert theme_id in themes.user_theme_ids()
    finally:
        themes.delete_user_theme(theme_id)
        themes.reload()


# ---------------------------------------------------------------------------
# Page view / autosave toggles
# ---------------------------------------------------------------------------


def test_toggle_page_view_on_applies_to_open_tabs(window):
    tab = window._current_tab()
    window._toggle_page_view(True)
    assert window._paged_enabled is True
    assert tab._paged is True
    assert "on" in window.statusBar().currentMessage().lower()


def test_toggle_page_view_off_applies_to_open_tabs(window):
    window._toggle_page_view(True)
    window._toggle_page_view(False)
    assert window._paged_enabled is False
    assert "off" in window.statusBar().currentMessage().lower()


def test_toggle_autosave_off_stops_the_timer(window):
    window._toggle_autosave(True)
    assert window._autosave_timer.isActive()
    window._toggle_autosave(False)
    assert not window._autosave_timer.isActive()


# ---------------------------------------------------------------------------
# About dialog
# ---------------------------------------------------------------------------


def test_show_about_opens_and_execs_the_dialog(window):
    from epy_reports._ui.about_dialog import AboutDialog

    with patch.object(AboutDialog, "exec", return_value=0) as exec_mock:
        window._show_about()
    exec_mock.assert_called_once()


# ---------------------------------------------------------------------------
# Document properties: cancel + logo localization
# ---------------------------------------------------------------------------


def test_edit_document_properties_cancelled_writes_nothing(window):
    tab = window._new_tab()
    tab.editor.setPlainText("# Doc\n")

    class _FakeDialog:
        def __init__(self, *a, **k):
            pass

        def exec(self):
            return QDialog.DialogCode.Rejected

    with patch(
        "epy_reports._ui.document_properties_dialog"
        ".DocumentPropertiesDialog",
        _FakeDialog,
    ):
        window._edit_document_properties()
    assert tab.editor.toPlainText() == "# Doc\n"


def test_edit_document_properties_localizes_an_absolute_logo(
    window, tmp_path
):
    doc = tmp_path / "doc.md"
    doc.parent.mkdir(exist_ok=True)
    tab = window._new_tab()
    tab.set_initial_text("# Doc\n", path=doc)
    logo = tmp_path / "logo.png"
    logo.write_bytes(b"\x89PNG\r\n\x1a\n")

    class _FakeDialog:
        def __init__(self, *a, **k):
            pass

        def exec(self):
            return QDialog.DialogCode.Accepted

        def updates(self):
            return [("logo", str(logo), False)]

    with patch(
        "epy_reports._ui.document_properties_dialog"
        ".DocumentPropertiesDialog",
        _FakeDialog,
    ):
        window._edit_document_properties()
    assert "logo: figures/logo.png" in tab.editor.toPlainText()
    assert (tmp_path / "figures" / "logo.png").is_file()


# ---------------------------------------------------------------------------
# _new_bib_entry: the accepted-dialog success path
# ---------------------------------------------------------------------------


def test_new_bib_entry_accepted_appends_and_refreshes_menu(
    window, tmp_path
):
    from epy_reports._core.bib import BibEntryDraft

    doc = tmp_path / "doc.md"
    doc.write_text("# Doc\n", encoding="utf-8")
    window.open_path(doc)
    tab = window._current_tab()
    bib_file = tmp_path / "refs.bib"
    bib_file.write_text("@misc{old, title={Old}}\n", encoding="utf-8")
    tab.link_bibliography(bib_file)

    draft = BibEntryDraft(type="misc", key="new2024", title="New Entry")

    class _FakeBibDialog:
        DialogCode = QDialog.DialogCode

        def __init__(self, *a, **k):
            pass

        def exec(self):
            return QDialog.DialogCode.Accepted

        def build_draft(self):
            return draft

    with patch(
        "epy_reports._ui.bib_dialog.BibEntryDialog", _FakeBibDialog
    ):
        window._new_bib_entry()
    content = bib_file.read_text(encoding="utf-8")
    assert "new2024" in content
    assert "Added @new2024" in window.statusBar().currentMessage()


# ---------------------------------------------------------------------------
# Export HTML: suffix appended when missing
# ---------------------------------------------------------------------------


def test_export_html_appends_suffix_when_missing(window, tmp_path):
    tab = window._new_tab()
    tab.editor.setPlainText("# x\n")
    target = tmp_path / "nosuffix"
    with patch.object(
        app_mod.QFileDialog, "getSaveFileName",
        return_value=(str(target), ""),
    ):
        window._export_html()
    assert (tmp_path / "nosuffix.html").exists()


# ---------------------------------------------------------------------------
# _open_manual
# ---------------------------------------------------------------------------


def test_open_manual_opens_a_new_tab_with_the_manual_text(window):
    before = window.tabs.count()
    window._open_manual("welcome.md")
    assert window.tabs.count() == before + 1
    tab = window._current_tab()
    assert tab.path is None
    assert tab.text() == app_mod.WELCOME_TEXT


def test_open_manual_load_failure_warns_and_opens_no_tab(
    window, monkeypatch
):
    before = window.tabs.count()
    monkeypatch.setattr(
        app_mod, "_load_manual_text",
        lambda filename: (_ for _ in ()).throw(FileNotFoundError("gone")),
    )
    with patch.object(app_mod.QMessageBox, "warning") as warn:
        window._open_manual("welcome_es.md")
    warn.assert_called_once()
    assert window.tabs.count() == before


# ---------------------------------------------------------------------------
# _open_dialog
# ---------------------------------------------------------------------------


def test_open_dialog_opens_every_selected_file(window, tmp_path):
    a = tmp_path / "a.md"
    b = tmp_path / "b.md"
    a.write_text("# A\n", encoding="utf-8")
    b.write_text("# B\n", encoding="utf-8")
    with patch.object(
        app_mod.QFileDialog, "getOpenFileNames",
        return_value=([str(a), str(b)], ""),
    ):
        window._open_dialog()
    paths = {
        window.tabs.widget(i).path.resolve()
        for i in range(window.tabs.count())
        if isinstance(window.tabs.widget(i), MarkdownTab)
        and window.tabs.widget(i).path is not None
    }
    assert a.resolve() in paths
    assert b.resolve() in paths


def test_open_dialog_cancelled_opens_nothing(window):
    before = window.tabs.count()
    with patch.object(
        app_mod.QFileDialog, "getOpenFileNames", return_value=([], "")
    ):
        window._open_dialog()
    assert window.tabs.count() == before


# ---------------------------------------------------------------------------
# _save_current: no-tab guard
# ---------------------------------------------------------------------------


def test_save_current_noop_without_a_tab(window):
    _close_every_tab(window)
    assert window._save_current() is False


# ---------------------------------------------------------------------------
# _export_via_docs: save-before-export branches + success path
# ---------------------------------------------------------------------------


def test_export_via_docs_save_declined_by_dialog_aborts(window):
    """The user agrees to save, but the Save As dialog itself is
    cancelled -- _save_current() returns False, and export aborts."""
    tab = window._new_tab()
    tab.editor.setPlainText("# dirty untitled\n")
    with patch.object(
        QMessageBox, "question",
        return_value=QMessageBox.StandardButton.Save,
    ), patch.object(
        app_mod.QFileDialog, "getSaveFileName", return_value=("", "")
    ), patch(
        "epy_reports._ui.docs_export_dialog.DocsExportDialog"
    ) as dlg_cls:
        window._export_via_docs()
    dlg_cls.assert_not_called()
    assert window._exports_in_flight == 0


def test_export_via_docs_defensive_recheck_after_a_saveless_save(window):
    """Defensive guard: if _save_current() ever reports success WITHOUT
    actually giving the tab a path (a future refactor bug, not today's
    real behaviour -- today's _save_current() only returns True once
    tab.path is set), _export_via_docs must still refuse rather than
    open the docs dialog against no file."""
    tab = window._new_tab()
    tab.editor.setPlainText("# dirty untitled\n")
    assert tab.path is None

    with patch.object(
        QMessageBox, "question",
        return_value=QMessageBox.StandardButton.Save,
    ), patch.object(
        window, "_save_current", return_value=True,
    ), patch(
        "epy_reports._ui.docs_export_dialog.DocsExportDialog"
    ) as dlg_cls:
        window._export_via_docs()
    dlg_cls.assert_not_called()
    assert window._exports_in_flight == 0


def test_export_via_docs_full_success_starts_a_worker(window, tmp_path):
    doc = tmp_path / "doc.md"
    doc.write_text("# Doc\n", encoding="utf-8")
    window.open_path(doc)

    class _FakeDialog:
        DialogCode = QDialog.DialogCode

        def __init__(self, *a, **k):
            pass

        def exec(self):
            return QDialog.DialogCode.Accepted

        def persist_settings(self):
            pass

        layout_name = "default"
        document_type = "report"
        output_dir = tmp_path
        export_pdf = True
        export_html = False
        export_docx = False

    class _FakeWorker:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.finished_ok = _FakeTabSignalForWorker()
            self.finished_err = _FakeTabSignalForWorker()

        def start(self):
            pass

    class _FakeTabSignalForWorker:
        def connect(self, slot):
            pass

    with patch(
        "epy_reports._ui.docs_export_dialog.DocsExportDialog", _FakeDialog
    ), patch(
        "epy_reports._ui.docs_export_dialog._RenderWorker", _FakeWorker
    ):
        window._export_via_docs()
    assert window._exports_in_flight == 1  # started; worker never finished
    assert isinstance(window._docs_worker, _FakeWorker)
    assert window._docs_worker.kwargs["source_path"] == doc.resolve()


def test_on_docs_done_ok_shows_status_and_releases_counter(window):
    window._exports_in_flight = 1
    window._on_docs_done_ok("C:/out")
    assert window._exports_in_flight == 0
    assert "C:/out" in window.statusBar().currentMessage()
