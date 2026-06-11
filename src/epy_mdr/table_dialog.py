"""Modal dialog for inserting a pipe table (size, header, caption)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
)


class TableDialog(QDialog):
    """Ask the user for table dimensions, header option, and caption."""

    def __init__(self, parent=None) -> None:
        """Build the dialog widgets (spinboxes, header toggle, caption)."""
        super().__init__(parent)
        self.setWindowTitle("Insert table")
        self.setMinimumWidth(300)

        self.cols_spin = QSpinBox(self)
        self.cols_spin.setRange(1, 20)
        self.cols_spin.setValue(3)

        self.rows_spin = QSpinBox(self)
        self.rows_spin.setRange(1, 50)
        self.rows_spin.setValue(2)

        self.header_cb = QCheckBox("Include header row", self)
        self.header_cb.setChecked(True)

        self.caption_edit = QLineEdit(self)
        self.caption_edit.setPlaceholderText("Optional caption…")

        form = QFormLayout()
        form.addRow("Columns:", self.cols_spin)
        form.addRow("Data rows:", self.rows_spin)
        form.addRow("", self.header_cb)
        form.addRow("Caption:", self.caption_edit)

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

    @property
    def columns(self) -> int:
        """Number of table columns chosen by the user."""
        return self.cols_spin.value()

    @property
    def rows(self) -> int:
        """Number of data rows chosen by the user."""
        return self.rows_spin.value()

    @property
    def has_header(self) -> bool:
        """Whether the table includes a header row."""
        return self.header_cb.isChecked()

    @property
    def caption(self) -> str:
        """Caption text, stripped; empty string when not provided."""
        return self.caption_edit.text().strip()

    def build_markdown(self, label: str) -> str:
        """Generate pipe-table Markdown from the dialog choices."""
        cols = self.columns
        data_rows = self.rows
        header_row = self.has_header

        header = "| " + " | ".join(f"Header {c+1}" for c in range(cols)) + " |"
        sep = "| " + " | ".join("---" for _ in range(cols)) + " |"
        body = "\n".join(
            "| " + " | ".join("" for _ in range(cols)) + " |"
            for _ in range(data_rows)
        )

        lines = [header] if header_row else []
        lines.append(sep)
        if body:
            lines.append(body)

        if self.caption:
            lines.append("")
            lines.append(f": {self.caption} {{{label}}}")

        return "\n".join(lines) + "\n"
