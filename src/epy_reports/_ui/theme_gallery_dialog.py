"""A gallery dialog that previews every theme as a colour/typography swatch.

Complements the text-only ``View → Theme`` radio menu: the gallery shows each
theme as a live :func:`theme_preview` swatch so the visual identity is visible
before applying it. Bundled and user-created themes appear side by side; custom
themes get a swatch automatically from their palette.

Shared design with epy_slides and epy_papers so the three apps feel identical.
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

from epy_reports._core import _i18n as i18n
from epy_reports._core._previews import THEME_THUMB, theme_preview
from epy_reports._ui import themes

_THEME_ROLE = 0x0100  # Qt.UserRole


class ThemeGalleryDialog(QDialog):
    """Pick a theme from a grid of live preview swatches."""

    def __init__(
        self, parent: QWidget | None = None, *, current_id: str | None = None
    ) -> None:
        """Build the swatch grid and pre-select ``current_id`` if given."""
        super().__init__(parent)
        self.setWindowTitle("Themes")
        self.setMinimumSize(620, 440)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Choose a theme:"))

        self._list = QListWidget(self)
        self._list.setViewMode(QListWidget.ViewMode.IconMode)
        self._list.setIconSize(THEME_THUMB)
        self._list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self._list.setMovement(QListWidget.Movement.Static)
        self._list.setSpacing(14)
        self._list.setWordWrap(True)
        self._list.setUniformItemSizes(True)
        self._list.itemDoubleClicked.connect(lambda _item: self.accept())

        for theme in themes.THEMES.values():
            item = QListWidgetItem(theme.display_name)
            item.setIcon(QIcon(theme_preview(theme)))
            item.setData(_THEME_ROLE, theme.id)
            item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
            self._list.addItem(item)
            if theme.id == current_id:
                self._list.setCurrentItem(item)
        if self._list.currentItem() is None and self._list.count():
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

    def selected_theme_id(self) -> str | None:
        """Return the id of the highlighted theme, or ``None``."""
        item = self._list.currentItem()
        return item.data(_THEME_ROLE) if item is not None else None
