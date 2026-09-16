"""Tests for the ThemeEditorDialog form and its epyson payload output."""

from __future__ import annotations

import pytest
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QColorDialog, QMessageBox

from epy_reports._core import epyson, themes
from epy_reports._ui.theme_editor_dialog import (
    ThemeEditorDialog,
    _ColorButton,
    _contrast,
    _font_primary,
    _pt_value,
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
# Pure helpers
# ---------------------------------------------------------------------------


def test_contrast_dark_on_light():
    """Light backgrounds get black text."""
    assert _contrast("#FFFFFF") == "#000000"


def test_contrast_light_on_dark():
    """Dark backgrounds get white text."""
    assert _contrast("#000000") == "#FFFFFF"


def test_contrast_invalid_length_defaults_black():
    """A malformed hex string yields black."""
    assert _contrast("#FFF") == "#000000"


def test_font_primary_extracts_first_family():
    """The primary family is the first entry of the stack."""
    assert _font_primary('"Calibri", Arial, sans-serif') == "Calibri"


def test_font_primary_empty_defaults_calibri():
    """An empty stack falls back to Calibri."""
    assert _font_primary("") == "Calibri"


def test_pt_value_parses_points():
    """A ``"12pt"`` string parses to 12.0."""
    assert _pt_value("12pt") == 12.0


def test_pt_value_invalid_defaults_to_12():
    """A non-numeric value (no digits survive stripping) defaults to 12.0."""
    assert _pt_value("abc") == 12.0


def test_pt_value_malformed_number_defaults_to_12():
    """Digits/dots that survive stripping but don't parse hit the except.

    ``"abc"`` above leaves an EMPTY cleaned string, which takes the
    ternary's else branch, not the except. A value like ``"1.2.3pt"``
    strips to ``"1.2.3"`` -- non-empty, but not a valid float -- so this
    is the case that actually exercises the ``except ValueError`` path.
    """
    assert _pt_value("1.2.3pt") == 12.0


# ---------------------------------------------------------------------------
# Dialog construction and payload
# ---------------------------------------------------------------------------


def test_dialog_lists_every_base_theme(qapp):
    """The base combo has one entry per registered theme."""
    dlg = ThemeEditorDialog()
    assert dlg.base_combo.count() == len(themes.THEMES)


def test_dialog_default_name_is_empty(qapp):
    """A fresh dialog has no name yet."""
    dlg = ThemeEditorDialog()
    assert dlg.theme_name() == ""


def test_dialog_name_is_stripped(qapp):
    """The reported name is whitespace-stripped."""
    dlg = ThemeEditorDialog()
    dlg.name_edit.setText("  My Theme  ")
    assert dlg.theme_name() == "My Theme"


def test_epyson_payload_round_trips_through_loader(qapp):
    """The payload builds a coherent Theme via the loader."""
    dlg = ThemeEditorDialog()
    dlg.name_edit.setText("Round Trip")
    payload = dlg.epyson_payload()
    assert payload["display_name"] == "Round Trip"
    theme = epyson._theme_from_raw(payload, "round-trip")
    # The loader must produce the colour vars we fed in.
    assert theme.css_vars["bg"] == dlg._colors["page_bg"].color()
    assert theme.display_name == "Round Trip"


def test_changing_base_reloads_colors(qapp):
    """Selecting a different base reloads its palette into the form."""
    dlg = ThemeEditorDialog()
    first = dlg._colors["page_bg"].color()
    # Find a base whose page background differs, if one exists.
    for theme in themes.THEMES.values():
        idx = dlg.base_combo.findData(theme.id)
        dlg.base_combo.setCurrentIndex(idx)
        if dlg._colors["page_bg"].color() != first:
            break
    # Whatever ended selected, the form colour matches that theme's bg.
    chosen = themes.get(dlg.base_combo.currentData())
    assert dlg._colors["page_bg"].color() == chosen.css_vars.get(
        "bg", "#FFFFFF"
    ).upper()


def test_color_button_set_color_uppercases(qapp):
    """The colour button normalises hex to uppercase."""
    dlg = ThemeEditorDialog()
    btn = dlg._colors["text"]
    btn.set_color("#abcdef")
    assert btn.color() == "#ABCDEF"


def test_edit_id_prefills_the_existing_display_name(qapp):
    """Editing a registered theme pre-fills its saved display name."""
    theme_id = themes.DEFAULT_THEME_ID
    expected = themes.THEMES[theme_id].display_name
    dlg = ThemeEditorDialog(edit_id=theme_id)
    assert dlg.name_edit.text() == expected


def test_edit_id_unknown_leaves_name_blank(qapp):
    """An edit_id absent from the catalogue is not treated as a real edit.

    Counter-example to the prefill above: a stale/unknown id must not
    crash the dialog or invent a name.
    """
    dlg = ThemeEditorDialog(edit_id="not-a-real-theme")
    assert dlg.name_edit.text() == ""


# ---------------------------------------------------------------------------
# _ColorButton._pick
# ---------------------------------------------------------------------------


def test_color_button_pick_applies_a_valid_choice(qapp, monkeypatch):
    """Picking a valid colour updates the button and emits changed."""
    monkeypatch.setattr(
        QColorDialog,
        "getColor",
        staticmethod(lambda *a, **k: QColor("#112233")),
    )
    btn = _ColorButton("#000000")
    fired = []
    btn.changed.connect(lambda: fired.append(1))
    btn._pick()
    assert btn.color() == "#112233"
    assert fired == [1]


def test_color_button_pick_cancelled_keeps_the_old_color(qapp, monkeypatch):
    """Cancelling the picker (an invalid QColor) changes nothing."""
    monkeypatch.setattr(
        QColorDialog,
        "getColor",
        staticmethod(lambda *a, **k: QColor()),  # invalid/default
    )
    btn = _ColorButton("#445566")
    fired = []
    btn.changed.connect(lambda: fired.append(1))
    btn._pick()
    assert btn.color() == "#445566"
    assert fired == []


# ---------------------------------------------------------------------------
# _on_save
# ---------------------------------------------------------------------------


def test_on_save_blank_name_warns_and_does_not_accept(qapp, monkeypatch):
    """An empty theme name is refused with a warning, dialog stays open."""
    warned = []
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        staticmethod(lambda *a, **k: warned.append(a)),
    )
    dlg = ThemeEditorDialog()
    accepted = []
    dlg.accepted.connect(lambda: accepted.append(1))
    dlg._on_save()
    assert warned, "expected a warning dialog for a blank name"
    assert accepted == []


def test_on_save_with_a_name_accepts(qapp, monkeypatch):
    """A non-blank theme name accepts the dialog without warning."""
    warned = []
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        staticmethod(lambda *a, **k: warned.append(a)),
    )
    dlg = ThemeEditorDialog()
    dlg.name_edit.setText("My Custom Theme")
    accepted = []
    dlg.accepted.connect(lambda: accepted.append(1))
    dlg._on_save()
    assert warned == []
    assert accepted == [1]
