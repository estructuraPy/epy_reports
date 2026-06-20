"""Modal dialog for inserting a figure with caption and reference ID."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from epy_reports import _i18n as i18n

_IMAGE_FILTER = (
    "Images (*.png *.jpg *.jpeg *.gif *.svg *.webp *.bmp)"
    ";;All files (*)"
)


class FigureDialog(QDialog):
    """Ask the user for image path, caption, width, and reference ID."""

    def __init__(
        self, parent=None, default_id: str = "1"
    ) -> None:
        """Build the dialog widgets.

        Args:
            parent: Optional parent widget.
            default_id: Suffix pre-filled in the Reference ID field.
        """
        super().__init__(parent)
        self.setWindowTitle("Insert figure")
        self.setMinimumWidth(380)
        self._default_id = default_id

        self.path_edit = QLineEdit(self)
        self.path_edit.setPlaceholderText("path/to/image.png")

        self.browse_btn = QPushButton("Browse...", self)
        self.browse_btn.clicked.connect(self._browse)

        path_row = QHBoxLayout()
        path_row.addWidget(self.path_edit)
        path_row.addWidget(self.browse_btn)

        self.caption_edit = QLineEdit(self)
        self.caption_edit.setPlaceholderText("Figure caption")

        self.width_edit = QLineEdit(self)
        self.width_edit.setText("80%")

        self.id_edit = QLineEdit(self)
        self.id_edit.setText(default_id)
        self.id_edit.setPlaceholderText("e.g. 1, beam-section")

        form = QFormLayout()
        form.addRow("Path:", path_row)
        form.addRow("Caption:", self.caption_edit)
        form.addRow("Width:", self.width_edit)
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
        i18n.translate_widget(self)

    def _browse(self) -> None:
        """Open a file picker and populate the path field."""
        filename, _ = QFileDialog.getOpenFileName(
            self, i18n.tr("Select image"), "", _IMAGE_FILTER
        )
        if filename:
            self.path_edit.setText(filename)

    @property
    def path(self) -> str:
        """Image path as entered, stripped."""
        return self.path_edit.text().strip()

    @property
    def caption(self) -> str:
        """Caption text, stripped."""
        return self.caption_edit.text().strip()

    @property
    def width(self) -> str:
        """Width string, stripped; falls back to '80%' when empty."""
        value = self.width_edit.text().strip()
        return value if value else "80%"

    @property
    def reference_id(self) -> str:
        """Reference ID suffix, stripped; falls back to default_id."""
        value = self.id_edit.text().strip()
        return value if value else self._default_id

    def build_markdown(self) -> str:
        """Return the Quarto figure Markdown string.

        Returns:
            A string of the form
            ``![caption](path){#fig-id width=80%}``.
        """
        cap = self.caption or "Caption"
        pth = self.path or "path/to/image.png"
        return (
            f"![{cap}]({pth})"
            f"{{#fig-{self.reference_id} width={self.width}}}"
        )
