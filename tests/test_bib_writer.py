"""Tests for the writer side of bib.py and the BibEntryDialog."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from epy_mdr import bib
from epy_mdr.bib import (
    ENTRY_TYPES,
    REQUIRED_FIELDS,
    BibEntryDraft,
    append_entry_to_file,
    keys_in_file,
    parse_bib_text,
    serialize_draft,
    suggest_key,
)
from epy_mdr.bib_dialog import BibEntryDialog

_app: QApplication | None = None


@pytest.fixture(scope="module")
def qapp():
    """Provide a module-scoped QApplication instance."""
    global _app
    if _app is None:
        _app = QApplication.instance() or QApplication([])
    return _app


# ---------------------------------------------------------------------------
# suggest_key
# ---------------------------------------------------------------------------


def test_suggest_key_basic():
    assert suggest_key("John Smith", "2024") == "smith2024"


def test_suggest_key_comma_form():
    assert suggest_key("Smith, John", "2024") == "smith2024"


def test_suggest_key_multiple_authors_first_wins():
    assert (
        suggest_key("Smith, John and Doe, Jane", "2024") == "smith2024"
    )


def test_suggest_key_strips_accents():
    assert suggest_key("Pérez, Andrés", "2025") == "perez2025"


def test_suggest_key_empty_inputs_returns_empty():
    assert suggest_key("", "") == ""


def test_suggest_key_year_only_returns_year():
    assert suggest_key("", "2024") == "2024"


# ---------------------------------------------------------------------------
# serialize_draft
# ---------------------------------------------------------------------------


def test_serialize_article_round_trips():
    draft = BibEntryDraft(
        type="article",
        key="smith2020",
        author="Smith, John",
        title="On Something",
        journal="Journal of X",
        year="2020",
        volume="10",
        pages="123--145",
    )
    text = serialize_draft(draft)
    parsed = parse_bib_text(text)
    assert len(parsed) == 1
    assert parsed[0].key == "smith2020"
    assert parsed[0].type == "article"
    assert parsed[0].title == "On Something"
    assert parsed[0].author == "Smith, John"
    assert parsed[0].year == "2020"


def test_serialize_skips_empty_fields():
    draft = BibEntryDraft(
        type="misc", key="k", title="Just a title",
    )
    text = serialize_draft(draft)
    assert "title" in text
    assert "journal" not in text
    assert "publisher" not in text


def test_serialize_starts_with_at_type_and_brace():
    draft = BibEntryDraft(type="book", key="abc", title="X", year="2020")
    assert serialize_draft(draft).startswith("@book{abc,\n")


def test_serialize_closes_with_brace_newline():
    draft = BibEntryDraft(type="book", key="abc", title="X", year="2020")
    assert serialize_draft(draft).endswith("}\n")


def test_serialize_aligns_equals_signs():
    """Visual alignment makes the file easier to read."""
    draft = BibEntryDraft(
        type="article",
        key="k",
        author="A",
        title="T",
        journal="J",
        year="2020",
    )
    text = serialize_draft(draft)
    field_lines = [
        line for line in text.splitlines()
        if line.startswith("  ") and "=" in line
    ]
    equals_positions = {line.index("=") for line in field_lines}
    assert len(equals_positions) == 1


# ---------------------------------------------------------------------------
# Required fields
# ---------------------------------------------------------------------------


def test_every_entry_type_has_required_mapping():
    for entry_type in ENTRY_TYPES:
        assert entry_type in REQUIRED_FIELDS


def test_missing_required_flags_empty_key():
    draft = BibEntryDraft(type="misc", key="")
    assert "key" in draft.missing_required()


def test_missing_required_flags_missing_journal_on_article():
    draft = BibEntryDraft(
        type="article", key="k", author="A", title="T", year="2024",
    )
    assert "journal" in draft.missing_required()


def test_missing_required_empty_when_all_present():
    draft = BibEntryDraft(
        type="article", key="k", author="A", title="T",
        journal="J", year="2024",
    )
    assert draft.missing_required() == []


# ---------------------------------------------------------------------------
# append_entry_to_file + keys_in_file
# ---------------------------------------------------------------------------


def test_append_creates_file_when_missing(tmp_path: Path):
    target = tmp_path / "refs.bib"
    draft = BibEntryDraft(
        type="article", key="smith2020", author="Smith, J",
        title="T", journal="J", year="2020",
    )
    append_entry_to_file(target, draft)
    assert target.exists()
    assert "smith2020" in target.read_text(encoding="utf-8")


def test_append_to_existing_keeps_old_entries(tmp_path: Path):
    target = tmp_path / "refs.bib"
    target.write_text(
        "@article{a2019,\n  title = {Old},\n  year = {2019}\n}\n",
        encoding="utf-8",
    )
    draft = BibEntryDraft(
        type="article", key="b2020", author="X", title="T",
        journal="J", year="2020",
    )
    append_entry_to_file(target, draft)
    text = target.read_text(encoding="utf-8")
    assert "a2019" in text
    assert "b2020" in text


def test_append_separates_entries_with_blank_line(tmp_path: Path):
    target = tmp_path / "refs.bib"
    target.write_text(
        "@misc{first,\n  title = {x}\n}\n",
        encoding="utf-8",
    )
    draft = BibEntryDraft(type="misc", key="second", title="y")
    append_entry_to_file(target, draft)
    text = target.read_text(encoding="utf-8")
    assert "}\n\n@misc{second" in text


def test_keys_in_file_reads_existing(tmp_path: Path):
    target = tmp_path / "refs.bib"
    target.write_text(
        "@article{a,\n  title = {A}\n}\n\n"
        "@book{b,\n  title = {B}\n}\n",
        encoding="utf-8",
    )
    assert keys_in_file(target) == {"a", "b"}


def test_keys_in_file_missing_returns_empty(tmp_path: Path):
    assert keys_in_file(tmp_path / "no-such-file.bib") == set()


# ---------------------------------------------------------------------------
# BibEntryDialog
# ---------------------------------------------------------------------------


def test_dialog_lists_every_entry_type(qapp):
    dlg = BibEntryDialog()
    assert dlg.type_combo.count() == len(ENTRY_TYPES)


def test_dialog_autosuggests_key_from_author_and_year(qapp):
    dlg = BibEntryDialog()
    dlg._field_edits["author"].setText("García, Ana")
    dlg._field_edits["year"].setText("2024")
    assert dlg._field_edits["key"].text() == "garcia2024"


def test_dialog_does_not_overwrite_user_key(qapp):
    dlg = BibEntryDialog()
    dlg._field_edits["key"].setText("my-custom-key")
    dlg._user_typed_key = True
    dlg._field_edits["author"].setText("Smith, John")
    dlg._field_edits["year"].setText("2020")
    assert dlg._field_edits["key"].text() == "my-custom-key"


def test_dialog_build_draft_collects_fields(qapp):
    dlg = BibEntryDialog(default_type="book")
    dlg._field_edits["key"].setText("rivero2020")
    dlg._field_edits["author"].setText("Rivero, J")
    dlg._field_edits["title"].setText("Mechanics")
    dlg._field_edits["publisher"].setText("Springer")
    dlg._field_edits["year"].setText("2020")
    draft = dlg.build_draft()
    assert draft.type == "book"
    assert draft.key == "rivero2020"
    assert draft.publisher == "Springer"


def test_dialog_build_bibtex_matches_serializer(qapp):
    dlg = BibEntryDialog(default_type="misc")
    dlg._field_edits["key"].setText("note1")
    dlg._field_edits["title"].setText("A note")
    expected = serialize_draft(dlg.build_draft())
    assert dlg.build_bibtex() == expected


def test_dialog_preview_starts_with_at_type(qapp):
    dlg = BibEntryDialog(default_type="article")
    dlg._field_edits["key"].setText("k")
    dlg._refresh_preview()
    assert dlg.preview.toPlainText().startswith("@article{k,\n")


def test_dialog_round_trip_via_parse_bib_text(qapp):
    """End-to-end: dialog → bib text → parser yields same key/type.

    Sets author/year first (the order a real user follows) and then a
    custom key — and flags ``_user_typed_key`` to mimic ``textEdited``,
    which only fires for keyboard input, not programmatic setText.
    """
    dlg = BibEntryDialog(default_type="techreport")
    dlg._field_edits["author"].setText("Newmark, N M")
    dlg._field_edits["title"].setText("Seismic design")
    dlg._field_edits["institution"].setText("UIUC")
    dlg._field_edits["year"].setText("2019")
    dlg._user_typed_key = True
    dlg._field_edits["key"].setText("nrc-2019-01")
    text = dlg.build_bibtex()
    parsed = bib.parse_bib_text(text)
    assert len(parsed) == 1
    assert parsed[0].key == "nrc-2019-01"
    assert parsed[0].type == "techreport"
