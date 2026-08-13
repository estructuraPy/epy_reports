"""Tests for epy_reports._ui.theme_gallery_dialog.ThemeGalleryDialog.

Mirrors ``src/epy_reports/_ui/theme_gallery_dialog.py`` per housekeeper.py's
``audit_module_mirror`` (module-level tests-mirror DNA). Complements the
smoke test already in test_previews.py (which mainly targets
``_previews.theme_preview``) with the dialog's own selection contract.
"""

from __future__ import annotations

import pytest


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_lists_every_theme(qapp):
    from epy_reports._core import themes
    from epy_reports._ui.theme_gallery_dialog import ThemeGalleryDialog

    dlg = ThemeGalleryDialog()
    assert dlg._list.count() == len(themes.THEMES)


def test_current_id_is_preselected(qapp):
    from epy_reports._core import themes
    from epy_reports._ui.theme_gallery_dialog import ThemeGalleryDialog

    theme_ids = list(themes.THEMES)
    target = theme_ids[-1]
    dlg = ThemeGalleryDialog(current_id=target)
    assert dlg.selected_theme_id() == target


def test_unknown_current_id_falls_back_to_first_row(qapp):
    from epy_reports._core import themes
    from epy_reports._ui.theme_gallery_dialog import ThemeGalleryDialog

    dlg = ThemeGalleryDialog(current_id="not-a-real-theme-id")
    assert dlg.selected_theme_id() == next(iter(themes.THEMES))


def test_no_current_id_selects_first_row(qapp):
    from epy_reports._core import themes
    from epy_reports._ui.theme_gallery_dialog import ThemeGalleryDialog

    dlg = ThemeGalleryDialog()
    assert dlg.selected_theme_id() == next(iter(themes.THEMES))


def test_double_click_accepts_the_dialog(qapp):
    from PySide6.QtWidgets import QDialog

    from epy_reports._ui.theme_gallery_dialog import ThemeGalleryDialog

    dlg = ThemeGalleryDialog()
    item = dlg._list.item(0)
    dlg._list.itemDoubleClicked.emit(item)
    assert dlg.result() == QDialog.DialogCode.Accepted
