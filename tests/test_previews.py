"""Tests for the QPainter preview thumbnails and the visual pickers."""

from __future__ import annotations

import pytest


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_theme_preview_for_every_theme(qapp):
    from epy_reports._core import themes
    from epy_reports._ui._previews import THEME_THUMB, theme_preview

    assert themes.THEMES, "the theme catalogue must not be empty"
    for theme in themes.THEMES.values():
        pix = theme_preview(theme)
        assert not pix.isNull()
        assert pix.size() == THEME_THUMB


def test_layout_preview_for_every_design_block(qapp):
    from epy_reports._core._design import DESIGN_BLOCKS
    from epy_reports._ui._previews import LAYOUT_THUMB, layout_preview

    for kind in DESIGN_BLOCKS:
        pix = layout_preview(kind)
        assert not pix.isNull(), kind
        assert pix.size() == LAYOUT_THUMB


# _draw_layout_body recognises a wider set of schematic ids than the
# report-block picker (DESIGN_BLOCKS) ever passes it -- these look like
# slide-layout ids shared with a sibling package (epy_slides). No wiring
# in this app's own UI ever reaches them with these particular strings,
# but layout_preview() is a public function taking a plain layout_id
# str, so calling it directly is a real, direct use of the API, not a
# contortion to touch a line.
_OTHER_LAYOUT_IDS = [
    "section", "two-column", "comparison", "image-caption",
    "image-fullbleed", "quote", "code", "blank", "image-left",
    "image-right", "quote-portrait", "big-stat", "unknown-id-falls-back",
]


@pytest.mark.parametrize("kind", _OTHER_LAYOUT_IDS)
def test_layout_preview_for_every_other_schematic_id(qapp, kind):
    from epy_reports._ui._previews import LAYOUT_THUMB, layout_preview

    pix = layout_preview(kind)
    assert not pix.isNull(), kind
    assert pix.size() == LAYOUT_THUMB


def test_design_block_dialog_lists_all_blocks(qapp):
    from epy_reports._core._design import DESIGN_BLOCKS
    from epy_reports._ui.design_block_dialog import DesignBlockDialog

    dlg = DesignBlockDialog()
    assert dlg._list.count() == len(DESIGN_BLOCKS)
    assert dlg.selected_kind() in DESIGN_BLOCKS


def test_theme_gallery_lists_all_themes(qapp):
    from epy_reports._core import themes
    from epy_reports._ui.theme_gallery_dialog import ThemeGalleryDialog

    dlg = ThemeGalleryDialog(current_id=themes.DEFAULT_THEME_ID)
    assert dlg._list.count() == len(themes.THEMES)
    assert dlg.selected_theme_id()


# ---------------------------------------------------------------------------
# _color / _primary_family -- fallback branches every bundled theme skips
# ---------------------------------------------------------------------------


def test_color_missing_value_returns_a_qcolor_fallback_as_is():
    """No value at all: a QColor fallback is returned unchanged."""
    from PySide6.QtGui import QColor

    from epy_reports._ui._previews import _color

    fallback = QColor("#123456")
    assert _color(None, fallback) is fallback


def test_color_missing_value_wraps_a_string_fallback():
    """No value at all: a string fallback is converted to a QColor."""
    from PySide6.QtGui import QColor

    from epy_reports._ui._previews import _color

    result = _color(None, "#654321")
    assert isinstance(result, QColor)
    assert result.name() == "#654321"


def test_color_invalid_value_falls_back():
    """An invalid colour string (not just a missing one) also falls back.

    Counter-example to the two tests above: this proves the fallback
    triggers on a bad VALUE, not only on ``None``/empty input.
    """
    from epy_reports._ui._previews import _color

    result = _color("not-a-color", "#ffffff")
    assert result.name() == "#ffffff"


def test_color_valid_value_wins_over_fallback():
    """A genuinely valid colour value is used, ignoring the fallback."""
    from epy_reports._ui._previews import _color

    result = _color("#00ff00", "#ffffff")
    assert result.name() == "#00ff00"


def test_primary_family_missing_stack_is_empty_string():
    """No font-family stack at all yields an empty string, not None/error."""
    from epy_reports._ui._previews import _primary_family

    assert _primary_family(None) == ""
    assert _primary_family("") == ""


def test_theme_preview_handles_a_theme_with_no_css_vars(qapp):
    """A bare theme (no css_vars at all) still renders a valid swatch.

    Every BUNDLED theme defines fg-muted and a font-family stack, so
    test_theme_preview_for_every_theme never reaches theme_preview's own
    _color()/_primary_family() fallback branches -- this exercises them
    through the real integration path, not just the unit functions above.
    """
    from epy_reports._core.themes_base import Theme
    from epy_reports._ui._previews import THEME_THUMB, theme_preview

    bare = Theme(id="bare", display_name="Bare", qt_palette={}, css_vars={})
    pix = theme_preview(bare)
    assert not pix.isNull()
    assert pix.size() == THEME_THUMB
