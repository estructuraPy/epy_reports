"""Modal dialog for inserting a footnote with text and reference ID."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
)


class FootnoteDialog(QDialog):
    """Ask the user for footnote text and a short reference ID."""

    def __init__(
        self, parent=None, default_id: str = "1"
    ) -> None:
        """Build the dialog widgets.

        Args:
            parent: Optional parent widget.
            default_id: Suffix pre-filled in the Reference ID field.
        """
        super().__init__(parent)
        self.setWindowTitle("Insert footnote")
        self.setMinimumWidth(420)
        self._default_id = default_id

        self.note_edit = QPlainTextEdit(self)
        self.note_edit.setPlaceholderText("Footnote text")
        self.note_edit.setMinimumHeight(90)

        self.id_edit = QLineEdit(self)
        self.id_edit.setText(default_id)
        self.id_edit.setPlaceholderText("e.g. 1, source-note")

        form = QFormLayout()
        form.addRow("Note text:", self.note_edit)
        form.addRow("Reference ID:", self.id_edit)

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
    def note_text(self) -> str:
        """Footnote text, stripped; falls back to a placeholder."""
        value = self.note_edit.toPlainText().strip()
        return value if value else "Footnote text"

    @property
    def reference_id(self) -> str:
        """Reference ID suffix, stripped; falls back to default_id."""
        value = self.id_edit.text().strip()
        return value if value else self._default_id

    def build_parts(self) -> tuple[str, str]:
        """Return the inline marker and the definition line.

        Returns:
            A ``(marker, definition)`` tuple, e.g.
            ``("[^fn-1]", "[^fn-1]: Footnote text")``. The caller
            inserts the marker at the caret and appends the definition
            to the end of the buffer.
        """
        marker = f"[^fn-{self.reference_id}]"
        definition = f"{marker}: {self.note_text}"
        return marker, definition
