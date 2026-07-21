"""Tests for the QPainter preview thumbnails and the visual pickers."""

from __future__ import annotations

import pytest


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_theme_preview_for_every_theme(qapp):
    from epy_reports._core._previews import THEME_THUMB, theme_preview
    from epy_reports._ui import themes

    assert themes.THEMES, "the theme catalogue must not be empty"
    for theme in themes.THEMES.values():
        pix = theme_preview(theme)
        assert not pix.isNull()
        assert pix.size() == THEME_THUMB


def test_layout_preview_for_every_design_block(qapp):
    from epy_reports._core._design import DESIGN_BLOCKS
    from epy_reports._core._previews import LAYOUT_THUMB, layout_preview

    for kind in DESIGN_BLOCKS:
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
    from epy_reports._ui import themes
    from epy_reports._ui.theme_gallery_dialog import ThemeGalleryDialog

    dlg = ThemeGalleryDialog(current_id=themes.DEFAULT_THEME_ID)
    assert dlg._list.count() == len(themes.THEMES)
    assert dlg.selected_theme_id()
