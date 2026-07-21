"""Modal dialog for inserting a Markdown task-list (checklist)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
)

from epy_reports._core import _i18n as i18n


class ChecklistDialog(QDialog):
    """Ask the user for item count and an optional title."""

    def __init__(self, parent=None) -> None:
        """Build the dialog widgets (item count, title field)."""
        super().__init__(parent)
        self.setWindowTitle("Insert checklist")
        self.setMinimumWidth(300)

        self.items_spin = QSpinBox(self)
        self.items_spin.setRange(1, 50)
        self.items_spin.setValue(3)

        self.title_edit = QLineEdit(self)
        self.title_edit.setPlaceholderText("Optional title…")

        form = QFormLayout()
        form.addRow("Items:", self.items_spin)
        form.addRow("Title:", self.title_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)
        i18n.translate_widget(self)

    @property
    def item_count(self) -> int:
        """Number of checklist items chosen by the user."""
        return self.items_spin.value()

    @property
    def title(self) -> str:
        """Title text, stripped; empty string when not provided."""
        return self.title_edit.text().strip()

    def build_markdown(self) -> str:
        """Generate task-list Markdown from the dialog choices.

        Returns a string that starts with a blank line (so it separates
        cleanly from any preceding paragraph) followed by an optional
        bold title line and N ``- [ ] Item n`` lines, ending with a
        trailing newline.
        """
        lines: list[str] = [""]
        if self.title:
            lines.append(f"**{self.title}**")
            lines.append("")
        for n in range(1, self.item_count + 1):
            lines.append(f"- [ ] Item {n}")
        lines.append("")
        return "\n".join(lines)
