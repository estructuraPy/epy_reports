"""Tests for the MarkdownWindow main window and the CLI entry points.

The window is built headlessly with a module-scoped QApplication, the
same pattern the dialog tests use. File / message dialogs are patched so
the command methods run end to end without blocking on real modal UI.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from epy_reports import _i18n as i18n
from epy_reports import app as app_mod
from epy_reports.app import MarkdownWindow
from epy_reports.tab import MarkdownTab

_app: QApplication | None = None


@pytest.fixture(scope="module")
def qapp():
    """Provide a module-scoped QApplication instance."""
    global _app
    if _app is None:
        _app = QApplication.instance() or QApplication([])
    return _app


@pytest.fixture
def window(qapp):
    """Build a fresh MarkdownWindow and tear it down afterwards."""
    win = MarkdownWindow()
    try:
        yield win
    finally:
        # Reset language so other tests/modules see the English default.
        i18n.set_language("en")
        win.deleteLater()


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
    from epy_reports import themes

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
    from epy_reports.renderer import DEFAULT_CSL_STYLE

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
    from epy_reports import themes

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
    from epy_reports import templates

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
    from epy_reports import templates

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
        "epy_reports.document_properties_dialog.DocumentPropertiesDialog",
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
    from epy_reports import winreg_assoc

    monkeypatch.setattr(
        winreg_assoc, "register", lambda make_default=False: ["did a thing"]
    )
    monkeypatch.setattr(
        winreg_assoc, "open_default_apps_settings", lambda: True
    )
    assert app_mod._run_register(make_default=False) == 0


def test_run_unregister_reports_nothing(monkeypatch):
    """``_run_unregister`` reports when there was nothing to remove."""
    from epy_reports import winreg_assoc

    monkeypatch.setattr(winreg_assoc, "unregister", lambda: [])
    assert app_mod._run_unregister() == 0


def test_run_set_default_failure_returns_2(monkeypatch):
    """A failed Settings launch returns exit code 2."""
    from epy_reports import winreg_assoc

    monkeypatch.setattr(
        winreg_assoc, "open_default_apps_settings", lambda: False
    )
    assert app_mod._run_set_default() == 2
