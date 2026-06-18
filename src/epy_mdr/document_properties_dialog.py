"""Modal dialog to edit a document's front matter from a form.

Gathers the publishing front-matter keys — title/subtitle/author/date,
the cover page, the running header (a 2x3 grid of cells), the footer,
page numbers and page size — and returns them as a list of
``(field, value, raw)`` updates the caller writes into the YAML front
matter with :func:`epy_mdr.snippets.set_metadata_field`.
"""

from __future__ import annotations

import json

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from epy_mdr import _i18n as i18n
from epy_mdr import snippets

_PAGE_SIZES = ["letter", "a4", "legal"]
_PAGE_SIZE_LABELS = {"letter": "Letter", "a4": "A4", "legal": "Legal"}


def _is_truthy(value: str) -> bool:
    """Return True for the YAML-ish truthy strings."""
    return value.strip().lower() in ("true", "yes", "1", "on")


class DocumentPropertiesDialog(QDialog):
    """Form for the cover, header, footer and page front-matter keys."""

    def __init__(
        self, parent=None, meta: dict[str, str] | None = None
    ) -> None:
        """Build the form and pre-fill it from ``meta``.

        Args:
            parent: Optional parent widget.
            meta: Front-matter values of the current document (as parsed
                by :func:`epy_mdr.snippets.parse_front_matter`).
        """
        super().__init__(parent)
        self.setWindowTitle("Document properties")
        self.setMinimumWidth(560)
        self._orig = dict(meta or {})

        # --- Title block --------------------------------------------------
        self.title_edit = QLineEdit(self._orig.get("title", ""))
        self.subtitle_edit = QLineEdit(self._orig.get("subtitle", ""))
        self.author_edit = QLineEdit(self._orig.get("author", ""))
        self.date_edit = QLineEdit(self._orig.get("date", ""))

        self.page_size_combo = QComboBox()
        for key in _PAGE_SIZES:
            self.page_size_combo.addItem(_PAGE_SIZE_LABELS[key], key)
        cur_size = (self._orig.get("page-size", "letter") or "letter").lower()
        if cur_size in _PAGE_SIZES:
            self.page_size_combo.setCurrentIndex(_PAGE_SIZES.index(cur_size))

        title_box = QGroupBox("Title block")
        title_grid = QGridLayout(title_box)
        title_grid.addWidget(QLabel("Title:"), 0, 0)
        title_grid.addWidget(self.title_edit, 0, 1, 1, 3)
        title_grid.addWidget(QLabel("Subtitle:"), 1, 0)
        title_grid.addWidget(self.subtitle_edit, 1, 1, 1, 3)
        title_grid.addWidget(QLabel("Author:"), 2, 0)
        title_grid.addWidget(self.author_edit, 2, 1)
        title_grid.addWidget(QLabel("Date:"), 2, 2)
        title_grid.addWidget(self.date_edit, 2, 3)
        title_grid.addWidget(QLabel("Page size:"), 3, 0)
        title_grid.addWidget(self.page_size_combo, 3, 1)

        # --- Cover page ---------------------------------------------------
        self.cover_check = QCheckBox("Render a dedicated cover page")
        self.cover_check.setChecked(_is_truthy(self._orig.get("cover", "")))
        self.logo_edit = QLineEdit(self._orig.get("logo", ""))
        logo_btn = QPushButton("Browse…")
        logo_btn.clicked.connect(self._pick_logo)
        cover_box = QGroupBox("Cover page")
        cover_v = QVBoxLayout(cover_box)
        cover_v.addWidget(self.cover_check)
        logo_row = QHBoxLayout()
        logo_row.addWidget(QLabel("Logo:"))
        logo_row.addWidget(self.logo_edit)
        logo_row.addWidget(logo_btn)
        cover_v.addLayout(logo_row)

        # Grayscale watermark drawn faintly behind every page.
        self.watermark_edit = QLineEdit(self._orig.get("watermark", ""))
        wm_btn = QPushButton("Browse…")
        wm_btn.clicked.connect(self._pick_watermark)
        wm_row = QHBoxLayout()
        wm_row.addWidget(QLabel("Watermark:"))
        wm_row.addWidget(self.watermark_edit)
        wm_row.addWidget(wm_btn)
        cover_v.addLayout(wm_row)

        # --- Running header (2 rows x 3 columns) --------------------------
        cells = snippets.parse_header_cells(self._orig.get("header", ""))[:6]
        cells += [""] * (6 - len(cells))
        self.header_edits = [QLineEdit(cells[i]) for i in range(6)]
        placeholders = [
            "top-left", "top-center", "top-right",
            "bottom-left", "bottom-center", "bottom-right",
        ]
        for edit, ph in zip(self.header_edits, placeholders, strict=True):
            edit.setPlaceholderText(ph)
        header_box = QGroupBox("Running header (up to 6 cells)")
        header_grid = QGridLayout(header_box)
        for i, edit in enumerate(self.header_edits):
            header_grid.addWidget(edit, i // 3, i % 3)

        # --- Footer -------------------------------------------------------
        self.footer_edit = QLineEdit(self._orig.get("footer", ""))
        self.page_numbers_check = QCheckBox('Stamp "Page X of Y"')
        self.page_numbers_check.setChecked(
            _is_truthy(self._orig.get("page-numbers", ""))
        )
        footer_box = QGroupBox("Footer")
        footer_grid = QGridLayout(footer_box)
        footer_grid.addWidget(QLabel("Text:"), 0, 0)
        footer_grid.addWidget(self.footer_edit, 0, 1)
        footer_grid.addWidget(self.page_numbers_check, 1, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(title_box)
        layout.addWidget(cover_box)
        layout.addWidget(header_box)
        layout.addWidget(footer_box)
        layout.addWidget(buttons)
        i18n.translate_widget(self)

    def _pick_logo(self) -> None:
        """Open a file picker for the cover logo image."""
        path, _ = QFileDialog.getOpenFileName(
            self, i18n.tr("Choose logo image"), "",
            "Images (*.png *.jpg *.jpeg *.svg);;All files (*)",
        )
        if path:
            self.logo_edit.setText(path)

    def _pick_watermark(self) -> None:
        """Open a file picker for the page watermark image."""
        path, _ = QFileDialog.getOpenFileName(
            self, i18n.tr("Choose watermark image"), "",
            "Images (*.png *.jpg *.jpeg *.svg *.webp);;All files (*)",
        )
        if path:
            self.watermark_edit.setText(path)

    def updates(self) -> list[tuple[str, str, bool]]:
        """Return the front-matter updates as ``(field, value, raw)``.

        A text field is included when it has a value or when it previously
        existed (so clearing it writes an empty value). Booleans are always
        written; the header is written as a YAML flow sequence.
        """
        out: list[tuple[str, str, bool]] = []

        def add_text(field: str, value: str) -> None:
            value = value.strip()
            if value or field in self._orig:
                out.append((field, value, False))

        add_text("title", self.title_edit.text())
        add_text("subtitle", self.subtitle_edit.text())
        add_text("author", self.author_edit.text())
        add_text("date", self.date_edit.text())
        add_text("logo", self.logo_edit.text())
        add_text("watermark", self.watermark_edit.text())
        add_text("footer", self.footer_edit.text())

        def yn(checked: bool) -> str:
            return "true" if checked else "false"

        out.append(("page-size", self.page_size_combo.currentData(), False))
        out.append(("cover", yn(self.cover_check.isChecked()), False))
        out.append(
            ("page-numbers", yn(self.page_numbers_check.isChecked()), False)
        )

        cells = [e.text().strip() for e in self.header_edits]
        # Trim trailing empty cells so the sequence stays compact.
        while cells and not cells[-1]:
            cells.pop()
        if cells:
            out.append(("header", json.dumps(cells, ensure_ascii=False), True))
        elif "header" in self._orig:
            out.append(("header", "[]", True))

        return out
