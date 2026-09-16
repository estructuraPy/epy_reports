"""Tests for the DocumentPropertiesDialog form and its update output."""

from __future__ import annotations

import json

import pytest
from PySide6.QtWidgets import QApplication, QFileDialog

from epy_reports._ui.document_properties_dialog import (
    DocumentPropertiesDialog,
    _is_truthy,
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


# ---------------------------------------------------------------------------
# _is_truthy
# ---------------------------------------------------------------------------


def test_is_truthy_accepts_yaml_truthy():
    """The known truthy spellings all return True."""
    for value in ("true", "Yes", "1", "ON"):
        assert _is_truthy(value)


def test_is_truthy_rejects_other_values():
    """Everything else is falsey."""
    for value in ("false", "no", "", "0", "maybe"):
        assert not _is_truthy(value)


# ---------------------------------------------------------------------------
# Pre-fill from meta
# ---------------------------------------------------------------------------


def test_prefills_title_block(qapp):
    """Existing metadata is loaded into the text fields."""
    meta = {"title": "Report", "author": "ANM", "date": "2026"}
    dlg = DocumentPropertiesDialog(meta=meta)
    assert dlg.title_edit.text() == "Report"
    assert dlg.author_edit.text() == "ANM"
    assert dlg.date_edit.text() == "2026"


def test_prefills_page_size_combo(qapp):
    """A known page-size value selects the matching combo entry."""
    dlg = DocumentPropertiesDialog(meta={"page-size": "a4"})
    assert dlg.page_size_combo.currentData() == "a4"


def test_cover_checkbox_reflects_meta(qapp):
    """A truthy cover value checks the box."""
    dlg = DocumentPropertiesDialog(meta={"cover": "true"})
    assert dlg.cover_check.isChecked()


def test_header_cells_split_into_six(qapp):
    """A header flow sequence is split across the six cell edits."""
    dlg = DocumentPropertiesDialog(meta={"header": '["A", "B", "C"]'})
    assert dlg.header_edits[0].text() == "A"
    assert dlg.header_edits[1].text() == "B"
    assert dlg.header_edits[2].text() == "C"
    assert dlg.header_edits[5].text() == ""


# ---------------------------------------------------------------------------
# updates()
# ---------------------------------------------------------------------------


def test_updates_emit_page_size_and_booleans(qapp):
    """page-size, cover and page-numbers are always emitted."""
    dlg = DocumentPropertiesDialog()
    dlg.page_size_combo.setCurrentIndex(
        dlg.page_size_combo.findData("legal")
    )
    dlg.cover_check.setChecked(True)
    dlg.page_numbers_check.setChecked(False)
    out = dict((f, v) for f, v, _raw in dlg.updates())
    assert out["page-size"] == "legal"
    assert out["cover"] == "true"
    assert out["page-numbers"] == "false"


def test_updates_include_filled_text_fields(qapp):
    """A filled text field is emitted; an empty unseen one is not."""
    dlg = DocumentPropertiesDialog()
    dlg.title_edit.setText("My Title")
    fields = {f for f, _v, _raw in dlg.updates()}
    assert "title" in fields
    # 'subtitle' was never set and was not in the original meta.
    assert "subtitle" not in fields


def test_updates_emit_cleared_field_that_existed(qapp):
    """Clearing a previously present field writes an empty value."""
    dlg = DocumentPropertiesDialog(meta={"footer": "old"})
    dlg.footer_edit.setText("")
    out = dict((f, v) for f, v, _raw in dlg.updates())
    assert out["footer"] == ""


def test_updates_header_serialized_as_flow_sequence(qapp):
    """A filled header is emitted as a raw JSON flow sequence."""
    dlg = DocumentPropertiesDialog()
    dlg.header_edits[0].setText("Left")
    dlg.header_edits[2].setText("Right")
    header = next(
        (v, raw) for f, v, raw in dlg.updates() if f == "header"
    )
    value, raw = header
    assert raw is True
    cells = json.loads(value)
    assert cells == ["Left", "", "Right"]


# ---------------------------------------------------------------------------
# The reader's own PDF pages.
# ---------------------------------------------------------------------------


def test_annexes_prefill_as_a_readable_list(qapp):
    """Whatever form the file holds is shown as one readable line."""
    dlg = DocumentPropertiesDialog(
        meta={"annexes": '["anexos/uno.pdf", "anexos/dos.pdf"]'}
    )
    assert dlg.annexes_edit.text() == "anexos/uno.pdf, anexos/dos.pdf"


def test_annexes_are_written_as_a_flow_sequence(qapp):
    """Quoted, not comma-joined: a path is allowed to contain a comma."""
    dlg = DocumentPropertiesDialog()
    dlg.annexes_edit.setText("uno.pdf, dos.pdf")
    value, raw = next(
        (v, r) for f, v, r in dlg.updates() if f == "annexes"
    )
    assert raw is True
    assert json.loads(value) == ["uno.pdf", "dos.pdf"]


def test_clearing_the_annexes_writes_an_empty_list_not_an_empty_value(
    qapp,
):
    """The one spelling the export does not read as a mistake.

    An empty ``annexes:`` is what a dropped YAML block sequence looks
    like, and the export refuses on it. So a reader who empties this
    field must get ``[]`` written, or every later export would refuse
    with a message about a list they no longer have.
    """
    dlg = DocumentPropertiesDialog(meta={"annexes": '["uno.pdf"]'})
    dlg.annexes_edit.setText("")
    out = dict((f, v) for f, v, _raw in dlg.updates())
    assert out["annexes"] == "[]"


def test_the_cover_pdf_is_a_plain_path(qapp):
    dlg = DocumentPropertiesDialog()
    dlg.cover_pdf_edit.setText("plantilla/portada.pdf")
    out = dict((f, v) for f, v, _raw in dlg.updates())
    assert out["cover-pdf"] == "plantilla/portada.pdf"


# ---------------------------------------------------------------------------
# File pickers (_pick_logo / _pick_watermark / _pick_cover_pdf / _pick_annexes)
# ---------------------------------------------------------------------------


def test_pick_logo_sets_the_field(qapp, monkeypatch):
    """Choosing a file in the native dialog fills the logo field."""
    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileName",
        staticmethod(lambda *a, **k: ("brand/logo.png", "")),
    )
    dlg = DocumentPropertiesDialog()
    dlg._pick_logo()
    assert dlg.logo_edit.text() == "brand/logo.png"


def test_pick_logo_cancelled_leaves_field_unchanged(qapp, monkeypatch):
    """Cancelling (empty filename) does not touch the field."""
    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileName",
        staticmethod(lambda *a, **k: ("", "")),
    )
    dlg = DocumentPropertiesDialog(meta={"logo": "existing.png"})
    dlg._pick_logo()
    assert dlg.logo_edit.text() == "existing.png"


def test_pick_watermark_sets_the_field(qapp, monkeypatch):
    """Choosing a file in the native dialog fills the watermark field."""
    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileName",
        staticmethod(lambda *a, **k: ("marks/wm.png", "")),
    )
    dlg = DocumentPropertiesDialog()
    dlg._pick_watermark()
    assert dlg.watermark_edit.text() == "marks/wm.png"


def test_pick_cover_pdf_sets_the_field(qapp, monkeypatch):
    """Choosing a file in the native dialog fills the cover-pdf field."""
    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileName",
        staticmethod(lambda *a, **k: ("cover.pdf", "")),
    )
    dlg = DocumentPropertiesDialog()
    dlg._pick_cover_pdf()
    assert dlg.cover_pdf_edit.text() == "cover.pdf"


def test_pick_annexes_joins_chosen_files(qapp, monkeypatch):
    """Choosing several files replaces the field with a joined list."""
    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileNames",
        staticmethod(lambda *a, **k: (["a.pdf", "b.pdf"], "")),
    )
    dlg = DocumentPropertiesDialog()
    dlg.annexes_edit.setText("old.pdf")
    dlg._pick_annexes()
    assert dlg.annexes_edit.text() == "a.pdf, b.pdf"


def test_pick_annexes_cancelled_leaves_field_unchanged(qapp, monkeypatch):
    """Cancelling the multi-file picker (empty list) keeps the old value."""
    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileNames",
        staticmethod(lambda *a, **k: ([], "")),
    )
    dlg = DocumentPropertiesDialog()
    dlg.annexes_edit.setText("kept.pdf")
    dlg._pick_annexes()
    assert dlg.annexes_edit.text() == "kept.pdf"


# ---------------------------------------------------------------------------
# updates() -- header cleared but previously present
# ---------------------------------------------------------------------------


def test_updates_emit_empty_list_for_a_header_that_was_cleared(qapp):
    """Clearing every header cell of an existing header writes '[]'.

    Same shape as the annexes rule: an omitted ``header`` key and an
    empty one are different YAML shapes downstream, so a cleared header
    that used to exist must still be written, as an empty flow sequence.
    """
    dlg = DocumentPropertiesDialog(meta={"header": '["Left", "Right"]'})
    for edit in dlg.header_edits:
        edit.setText("")
    out = dict((f, v) for f, v, _raw in dlg.updates())
    assert out["header"] == "[]"
