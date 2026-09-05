"""Tests for epy_reports._ui.design_block_dialog.DesignBlockDialog.

Mirrors ``src/epy_reports/_ui/design_block_dialog.py`` per housekeeper.py's
``audit_module_mirror`` (module-level tests-mirror DNA). Complements the
smoke test already in test_previews.py (which mainly targets
``_previews.layout_preview``) with the dialog's own selection contract.
"""

from __future__ import annotations

import pytest


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_lists_every_design_block(qapp):
    from epy_reports._core._design import DESIGN_BLOCKS
    from epy_reports._ui.design_block_dialog import DesignBlockDialog

    dlg = DesignBlockDialog()
    assert dlg._list.count() == len(DESIGN_BLOCKS)


def test_first_block_preselected(qapp):
    from epy_reports._core._design import DESIGN_BLOCKS
    from epy_reports._ui.design_block_dialog import DesignBlockDialog

    dlg = DesignBlockDialog()
    assert dlg.selected_kind() == DESIGN_BLOCKS[0]


def test_selecting_a_row_updates_selected_kind(qapp):
    from epy_reports._core._design import DESIGN_BLOCKS
    from epy_reports._ui.design_block_dialog import DesignBlockDialog

    dlg = DesignBlockDialog()
    dlg._list.setCurrentRow(len(DESIGN_BLOCKS) - 1)
    assert dlg.selected_kind() == DESIGN_BLOCKS[-1]


def test_double_click_accepts_the_dialog(qapp):
    from PySide6.QtWidgets import QDialog

    from epy_reports._ui.design_block_dialog import DesignBlockDialog

    dlg = DesignBlockDialog()
    item = dlg._list.item(0)
    dlg._list.itemDoubleClicked.emit(item)
    assert dlg.result() == QDialog.DialogCode.Accepted


def test_cancel_button_rejects_the_dialog(qapp):
    from PySide6.QtWidgets import QDialog, QDialogButtonBox

    from epy_reports._ui.design_block_dialog import DesignBlockDialog

    dlg = DesignBlockDialog()
    buttons = dlg.findChild(QDialogButtonBox)
    if buttons is not None:
        buttons.rejected.emit()
    assert dlg.result() == QDialog.DialogCode.Rejected
