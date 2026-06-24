"""A visual picker for the shared design blocks (cards, big stats, ...).

The same dialog ships in epy_slides, epy_reports and epy_papers (only the
imports differ) so inserting a design block feels identical in all three. Each
block is shown as a neutral :func:`_previews.layout_preview` schematic so the
user reads the block TYPE before inserting it.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from epy_reports import _i18n as i18n
from epy_reports._design import DESIGN_BLOCK_LABELS, DESIGN_BLOCKS
from epy_reports._previews import LAYOUT_THUMB, layout_preview

_KIND_ROLE = 0x0100  # Qt.UserRole

# One-line descriptions per block (English; translated at display time).
_BLOCK_DESC = {
    "lead": "A lead sentence that frames the section.",
    "badge": "A small pill label.",
    "card": "A bordered card with a title and body.",
    "cards": "A responsive grid of cards.",
    "stat": "A single big number with a caption.",
    "stats": "A row of big numbers with captions.",
    "timeline": "A vertical timeline over a list.",
    "agenda": "A numbered agenda over a list.",
    "disclosure": "An insertable disclosure note (e.g. an AI-use disclosure).",
}


class DesignBlockDialog(QDialog):
    """Pick a design block from a grid of schematic previews."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Build the design-block picker grid."""
        super().__init__(parent)
        self.setWindowTitle("Design block")
        self.setMinimumSize(560, 420)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Choose a design block:"))

        self._list = QListWidget(self)
        self._list.setViewMode(QListWidget.ViewMode.IconMode)
        self._list.setIconSize(LAYOUT_THUMB)
        self._list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self._list.setMovement(QListWidget.Movement.Static)
        self._list.setSpacing(12)
        self._list.setWordWrap(True)
        self._list.setUniformItemSizes(True)
        self._list.itemDoubleClicked.connect(lambda _item: self.accept())

        for kind in DESIGN_BLOCKS:
            label = DESIGN_BLOCK_LABELS.get(kind, kind.title())
            item = QListWidgetItem(label)
            item.setIcon(QIcon(layout_preview(kind)))
            item.setData(_KIND_ROLE, kind)
            item.setToolTip(i18n.tr(_BLOCK_DESC.get(kind, "")))
            item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
            self._list.addItem(item)
        self._list.setCurrentRow(0)
        layout.addWidget(self._list)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        i18n.translate_widget(self)

    def selected_kind(self) -> str | None:
        """Return the id of the highlighted design block, or ``None``."""
        item = self._list.currentItem()
        return item.data(_KIND_ROLE) if item is not None else None
