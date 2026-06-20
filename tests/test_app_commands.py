"""Additional MarkdownWindow command coverage (dialogs patched).

Targets the theme-editor, custom-theme delete, manual/about, bibliography
entry, epy_docs export worker wiring, print, PDF export and close-handling
paths that the core test_app.py does not reach.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from epy_reports import _i18n as i18n
from epy_reports import app as app_mod
from epy_reports.app import MarkdownWindow

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
    """Build and tear down a MarkdownWindow."""
    win = MarkdownWindow()
    try:
        yield win
    finally:
        i18n.set_language("en")
        win.deleteLater()


# ---------------------------------------------------------------------------
# Theme editor + custom-theme management
# ---------------------------------------------------------------------------


def test_open_theme_editor_saves_and_selects(window, monkeypatch):
    """Accepting the editor saves the payload and selects the new theme."""
    from epy_reports import themes

    payload = {"display_name": "Brand New"}

    class _FakeEditor:
        def __init__(self, *a, **k):
            pass

        def exec(self):
            return QDialog.DialogCode.Accepted

        def epyson_payload(self):
            return payload

        def theme_name(self):
            return "Brand New"

    captured = {}

    def _save(p):
        captured["payload"] = p
        return "brand-new"

    def _refresh(select_id=None):
        captured["select"] = select_id

    monkeypatch.setattr(themes, "save_user_theme", _save)
    monkeypatch.setattr(window, "_refresh_themes", _refresh)
    with patch(
        "epy_reports.theme_editor_dialog.ThemeEditorDialog", _FakeEditor
    ):
        window._open_theme_editor(edit_id=None)
    assert captured["payload"] is payload
    assert captured["select"] == "brand-new"


def test_open_theme_editor_cancel_does_nothing(window):
    """Cancelling the editor saves nothing."""
    class _FakeEditor:
        def __init__(self, *a, **k):
            pass

        def exec(self):
            return QDialog.DialogCode.Rejected

    with patch(
        "epy_reports.theme_editor_dialog.ThemeEditorDialog", _FakeEditor
    ), patch("epy_reports.themes.save_user_theme") as save:
        window._open_theme_editor()
    save.assert_not_called()


def test_edit_current_theme_routes_to_editor(window, monkeypatch):
    """Editing the current theme opens the editor with an edit id or None."""
    seen = {}
    monkeypatch.setattr(
        window, "_open_theme_editor",
        lambda edit_id=None: seen.setdefault("edit", edit_id),
    )
    window._edit_current_theme()
    assert "edit" in seen


def test_delete_custom_theme_none_available(window, monkeypatch):
    """With no custom themes, the user is informed and nothing is deleted."""
    from epy_reports import themes

    monkeypatch.setattr(themes, "user_theme_ids", set)
    with patch.object(QMessageBox, "information") as info:
        window._delete_custom_theme()
    info.assert_called_once()


def test_delete_custom_theme_confirmed(window, monkeypatch):
    """A confirmed delete removes the chosen custom theme."""
    from epy_reports import themes

    monkeypatch.setattr(themes, "user_theme_ids", lambda: {"mine"})
    monkeypatch.setitem(
        themes.THEMES, "mine",
        themes.Theme("mine", "Mine", {}, {}),
    )
    deleted = {}
    monkeypatch.setattr(
        themes, "delete_user_theme",
        lambda tid: deleted.setdefault("id", tid),
    )
    monkeypatch.setattr(window, "_refresh_themes", lambda select_id=None: None)
    with patch(
        "PySide6.QtWidgets.QInputDialog.getItem",
        return_value=("Mine", True),
    ), patch.object(
        QMessageBox, "question",
        return_value=QMessageBox.StandardButton.Yes,
    ):
        window._delete_custom_theme()
    assert deleted["id"] == "mine"


def test_refresh_themes_rebuilds_actions(window):
    """Refreshing themes rebuilds the radio actions without raising."""
    window._refresh_themes()
    from epy_reports import themes

    assert set(window.theme_actions) == set(themes.THEMES)


# ---------------------------------------------------------------------------
# Manuals + about
# ---------------------------------------------------------------------------


def test_open_manual_adds_tab(window):
    """Opening the English manual creates a new tab."""
    before = window.tabs.count()
    window._open_manual("welcome.md")
    assert window.tabs.count() == before + 1


def test_open_manual_missing_warns(window):
    """A missing manual file warns and adds no tab."""
    before = window.tabs.count()
    with patch.object(
        app_mod, "_load_manual_text", side_effect=FileNotFoundError
    ), patch.object(QMessageBox, "warning") as warn:
        window._open_manual("nope.md")
    warn.assert_called_once()
    assert window.tabs.count() == before


def test_show_about_execs_dialog(window):
    """The About action opens and execs the dialog."""
    fake = MagicMock()
    with patch("epy_reports.about_dialog.AboutDialog", return_value=fake):
        window._show_about()
    fake.exec.assert_called_once()


# ---------------------------------------------------------------------------
# Bibliography entry creation
# ---------------------------------------------------------------------------


def test_new_bib_entry_appends_to_linked_file(window, tmp_path):
    """Accepting the bib dialog appends the draft to the linked file."""
    from epy_reports.bib import BibEntryDraft

    doc = tmp_path / "doc.md"
    doc.write_text("# Doc\n", encoding="utf-8")
    window.open_path(doc)
    tab = window._current_tab()
    bib_file = tmp_path / "refs.bib"
    tab.link_bibliography(bib_file)

    draft = BibEntryDraft(
        type="misc", key="newkey", title="A note",
    )

    class _FakeBibDialog:
        DialogCode = QDialog.DialogCode

        def __init__(self, *a, **k):
            pass

        def exec(self):
            return QDialog.DialogCode.Accepted

        def build_draft(self):
            return draft

    with patch("epy_reports.bib_dialog.BibEntryDialog", _FakeBibDialog):
        window._new_bib_entry()
    assert "newkey" in bib_file.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# PDF export
# ---------------------------------------------------------------------------


def test_export_pdf_invokes_tab_export(window, tmp_path):
    """``_export_pdf`` forwards the target to the tab's exporter."""
    tab = window._new_tab()
    tab.editor.setPlainText("# PDF\n")
    target = tmp_path / "out.pdf"
    with patch.object(
        app_mod.QFileDialog, "getSaveFileName",
        return_value=(str(target), ""),
    ), patch.object(tab, "export_pdf") as exp:
        window._export_pdf()
    exp.assert_called_once()
    assert exp.call_args.args[0] == target


def test_export_pdf_cancel_noop(window):
    """Cancelling the PDF dialog does not call the exporter."""
    tab = window._new_tab()
    tab.editor.setPlainText("# x\n")
    with patch.object(
        app_mod.QFileDialog, "getSaveFileName", return_value=("", "")
    ), patch.object(tab, "export_pdf") as exp:
        window._export_pdf()
    exp.assert_not_called()


# ---------------------------------------------------------------------------
# epy_docs export wiring
# ---------------------------------------------------------------------------


def test_export_via_docs_starts_worker(window, tmp_path, monkeypatch):
    """A saved doc + accepted dialog starts a render worker."""
    doc = tmp_path / "doc.md"
    doc.write_text("# Doc\n", encoding="utf-8")
    window.open_path(doc)
    tab = window._current_tab()
    tab._set_dirty(False) if hasattr(tab, "_set_dirty") else None

    class _FakeDialog:
        DialogCode = QDialog.DialogCode

        def __init__(self, *a, **k):
            pass

        def exec(self):
            return QDialog.DialogCode.Accepted

        def persist_settings(self):
            pass

        layout_name = "corporate"
        document_type = "report"
        output_dir = tmp_path / "out"
        export_pdf = True
        export_html = False
        export_docx = False

    started = {}

    class _FakeWorker:
        def __init__(self, **kw):
            started["kw"] = kw
            self.finished_ok = MagicMock()
            self.finished_err = MagicMock()

        def start(self):
            started["started"] = True

    monkeypatch.setattr(
        "epy_reports.docs_export_dialog.DocsExportDialog", _FakeDialog
    )
    monkeypatch.setattr(
        "epy_reports.docs_export_dialog._RenderWorker", _FakeWorker
    )
    window._export_via_docs()
    assert started.get("started") is True
    assert started["kw"]["layout"] == "corporate"


def test_on_docs_done_ok_updates_status(window):
    """The docs-done OK handler runs and restores the cursor."""
    window._on_docs_done_ok(str(Path("out")))


def test_on_docs_done_err_shows_error(window):
    """The docs-done error handler surfaces a critical message box."""
    with patch.object(QMessageBox, "critical") as crit:
        window._on_docs_done_err("boom")
    crit.assert_called_once()


# ---------------------------------------------------------------------------
# Close handling + drag/drop
# ---------------------------------------------------------------------------


def test_confirm_close_clean_tab_returns_true(window):
    """A clean tab closes without prompting."""
    tab = window._new_tab()
    tab.set_initial_text("clean", path=None)
    assert window._confirm_close(tab) is True


def test_confirm_close_discard_returns_true(window):
    """Choosing Discard on a dirty tab allows the close."""
    tab = window._new_tab()
    tab.set_initial_text("body", path=None)
    tab.editor.setPlainText("dirty")
    with patch.object(
        QMessageBox, "question",
        return_value=QMessageBox.StandardButton.Discard,
    ):
        assert window._confirm_close(tab) is True


def test_confirm_close_cancel_returns_false(window):
    """Choosing Cancel aborts the close."""
    tab = window._new_tab()
    tab.set_initial_text("body", path=None)
    tab.editor.setPlainText("dirty")
    with patch.object(
        QMessageBox, "question",
        return_value=QMessageBox.StandardButton.Cancel,
    ):
        assert window._confirm_close(tab) is False


def test_drop_event_opens_supported_files(window, tmp_path):
    """A dropped .md file is opened in a tab."""
    doc = tmp_path / "dropped.md"
    doc.write_text("# Dropped\n", encoding="utf-8")
    from PySide6.QtCore import QMimeData, QPointF, Qt
    from PySide6.QtGui import QDropEvent

    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(doc))])

    event = QDropEvent(
        QPointF(0, 0), Qt.DropAction.CopyAction, mime,
        Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
    )
    opened = {}
    with patch.object(
        window, "open_path",
        lambda p: opened.setdefault("path", p),
    ):
        window.dropEvent(event)
    assert opened["path"].name == "dropped.md"


def test_on_active_tab_forwards_to_tab(window):
    """``_on_active_tab`` forwards a named action to the active tab."""
    tab = window._new_tab()
    tab.set_initial_text("", path=None)
    window._on_active_tab("insert_page_break")
    assert "[[pagebreak]]" in tab.text()
