"""Tests for epy_reports._ui.bib_dialog.BibEntryDialog.

Mirrors ``src/epy_reports/_ui/bib_dialog.py`` per housekeeper.py's
``audit_module_mirror`` (module-level tests-mirror DNA).
``test_app_commands.py`` exercises the app's *usage* of this dialog
with a fake stand-in; this file exercises the real dialog's own
field model, key auto-suggestion, and accept-time validation.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

from epy_reports._ui.bib_dialog import BibEntryDialog

_app: QApplication | None = None


@pytest.fixture(scope="module")
def qapp() -> QApplication:
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


def test_default_type_is_preselected(qapp):
    dlg = BibEntryDialog(default_type="book")
    assert dlg.type_combo.currentText() == "book"


def test_unknown_default_type_falls_back_to_combo_default(qapp):
    dlg = BibEntryDialog(default_type="not-a-real-type")
    assert dlg.type_combo.currentText() == "article"


def test_required_label_lists_required_fields_for_type(qapp):
    dlg = BibEntryDialog(default_type="article")
    assert "author" in dlg.required_label.text()
    assert "title" in dlg.required_label.text()
    assert "journal" in dlg.required_label.text()


def test_build_draft_reflects_field_edits(qapp):
    dlg = BibEntryDialog(default_type="misc")
    dlg._field_edits["title"].setText("A Paper Title")
    draft = dlg.build_draft()
    assert draft.type == "misc"
    assert draft.title == "A Paper Title"


def test_build_bibtex_matches_serialize_draft(qapp):
    from epy_reports._core.bib import serialize_draft

    dlg = BibEntryDialog(default_type="misc")
    dlg._field_edits["title"].setText("A Paper Title")
    assert dlg.build_bibtex() == serialize_draft(dlg.build_draft())


def test_key_autosuggested_from_author_and_year(qapp):
    dlg = BibEntryDialog(default_type="article")
    dlg._field_edits["author"].setText("Navarro-Mora, Angel")
    dlg._field_edits["year"].setText("2026")
    assert dlg._field_edits["key"].text() == "navarromora2026"


def test_manual_key_edit_stops_autosuggestion(qapp):
    dlg = BibEntryDialog(default_type="article")
    dlg._field_edits["key"].setText("mykey2026")
    dlg._field_edits["key"].textEdited.emit("mykey2026")
    dlg._field_edits["author"].setText("Someone, Else")
    dlg._field_edits["year"].setText("2020")
    assert dlg._field_edits["key"].text() == "mykey2026"


def test_accept_blocked_when_required_fields_missing(qapp):
    dlg = BibEntryDialog(default_type="article")
    with patch.object(QMessageBox, "warning") as mock_warn:
        dlg._accept()
    mock_warn.assert_called_once()
    assert dlg.result() != dlg.DialogCode.Accepted


def test_accept_succeeds_when_required_fields_present(qapp):
    # ``key`` is always required (BibEntryDraft.missing_required), on top
    # of whatever REQUIRED_FIELDS[type] adds -- "misc" adds nothing more.
    dlg = BibEntryDialog(default_type="misc")
    dlg._field_edits["key"].setText("misc2026")
    dlg._field_edits["title"].setText("Enough for misc")
    dlg._accept()
    assert dlg.result() == dlg.DialogCode.Accepted


def test_duplicate_key_prompts_and_blocks_on_no(qapp):
    dlg = BibEntryDialog(
        default_type="misc", existing_keys={"dupe2026"}
    )
    dlg._field_edits["title"].setText("Title")
    dlg._field_edits["key"].setText("dupe2026")
    with patch.object(
        QMessageBox, "question", return_value=QMessageBox.StandardButton.No
    ) as mock_q:
        dlg._accept()
    mock_q.assert_called_once()
    assert dlg.result() != dlg.DialogCode.Accepted


def test_duplicate_key_accepted_on_yes(qapp):
    dlg = BibEntryDialog(
        default_type="misc", existing_keys={"dupe2026"}
    )
    dlg._field_edits["title"].setText("Title")
    dlg._field_edits["key"].setText("dupe2026")
    with patch.object(
        QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes
    ):
        dlg._accept()
    assert dlg.result() == dlg.DialogCode.Accepted
