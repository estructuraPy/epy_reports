"""Cross-reference picker used by the editor's ``Insert @ref`` action."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from epy_mdr import _i18n as i18n
from epy_mdr.bib import BibEntry
from epy_mdr.snippets import KIND_DESCRIPTIONS, Label

CITE_DESCRIPTION = "Citation"


class CrossRefDialog(QDialog):
    """List Quarto labels and return the one selected by the user."""

    def __init__(
        self,
        labels: list[Label],
        parent: QWidget | None = None,
        bib_lookup: dict[str, BibEntry] | None = None,
    ) -> None:
        """Show ``labels`` in a filterable list.

        ``bib_lookup`` maps citation keys to :class:`BibEntry` so the
        dialog can show the author / year / title next to ``@key``.
        """
        super().__init__(parent)
        self.setWindowTitle("Insert cross-reference")
        self.resize(520, 420)
        self._all_labels = labels
        self._bib_lookup = bib_lookup or {}

        layout = QVBoxLayout(self)

        info = QLabel(
            "Pick a label to insert as <code>@label</code>. "
            "Type to filter.",
            self,
        )
        info.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(info)

        self.filter_edit = QLineEdit(self)
        self.filter_edit.setPlaceholderText(
            "Filter: fig, tbl, eq, sec, or any substring"
        )
        self.filter_edit.textChanged.connect(self._refilter)
        layout.addWidget(self.filter_edit)

        self.list_widget = QListWidget(self)
        self.list_widget.itemActivated.connect(
            lambda _item: self.accept()
        )
        layout.addWidget(self.list_widget, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._populate(labels)
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)
        self.filter_edit.setFocus()
        i18n.translate_widget(self)

    def _populate(self, labels: list[Label]) -> None:
        """Refill the list widget with the current filtered labels."""
        self.list_widget.clear()
        for label in labels:
            if label.kind == "cite":
                kind = CITE_DESCRIPTION
                entry = self._bib_lookup.get(label.name)
                detail = entry.short_label() if entry else f"@{label.name}"
            else:
                kind = KIND_DESCRIPTIONS.get(label.kind, label.kind)
                detail = f"@{label.name}"
            item = QListWidgetItem(f"[{kind:8s}]  {detail}")
            item.setData(Qt.ItemDataRole.UserRole, label)
            self.list_widget.addItem(item)

    def _refilter(self, text: str) -> None:
        """Update the visible list to match the current filter text."""
        query = text.strip().lower()
        if not query:
            visible = self._all_labels
        else:
            visible = [
                label
                for label in self._all_labels
                if query in label.name.lower() or query == label.kind
            ]
        self._populate(visible)
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    def selected_label(self) -> Label | None:
        """Return the currently highlighted ``Label``, or ``None``."""
        item = self.list_widget.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)
