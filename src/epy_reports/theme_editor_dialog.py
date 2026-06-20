"""Modal dialog to create or edit a custom visual theme.

The form edits a small set of inputs — name, a handful of base colors, the
text/code fonts, the h1-h6 typography scale and the five callout colors —
and writes an ``.epyson`` payload (via
:func:`epy_reports.themes.build_epyson`).
Everything else in the theme (the Qt chrome palette, syntax-token colors,
contrast text) is derived from these inputs by the theme loader, so a few
fields produce a fully coherent theme. A live widget preview reflects the
current colors and fonts as they change.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from epy_reports import _i18n as i18n
from epy_reports import themes

# Color form fields: key -> English label.
_COLOR_FIELDS = [
    ("page_bg", "Page background"),
    ("text", "Text"),
    ("heading", "Headings"),
    ("primary", "Primary / accent"),
    ("secondary", "Link / secondary"),
    ("border", "Border"),
    ("code_bg", "Code background"),
    ("mark", "Highlight"),
]

# Typography roles: key -> English label, with a weight selector for headings.
_SCALE_ROLES = [
    ("h1", "Heading 1", True),
    ("h2", "Heading 2", True),
    ("h3", "Heading 3", True),
    ("h4", "Heading 4", True),
    ("h5", "Heading 5", True),
    ("h6", "Heading 6", True),
    ("text", "Body", False),
    ("caption", "Caption", False),
]

_CALLOUTS = ["note", "tip", "warning", "important", "caution"]
_CALLOUT_LABELS = {
    "note": "Note", "tip": "Tip", "warning": "Warning",
    "important": "Important", "caution": "Caution",
}
_WEIGHTS = ["400", "600", "700"]
_COMMON_FONTS = [
    "Calibri", "Arial", "Helvetica", "Georgia", "Times New Roman",
    "Cambria", "Garamond", "Verdana", "Segoe UI",
]
_COMMON_MONO = ["Consolas", "Fira Code", "Cascadia Code", "Courier New",
                "Menlo", "Monaco", "DejaVu Sans Mono"]


def _contrast(hex_color: str) -> str:
    """Return black or white for readable text over ``hex_color``."""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return "#000000"
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return "#000000" if luminance >= 0.5 else "#FFFFFF"


def _font_primary(stack: str) -> str:
    """Extract the primary family name from a CSS font-family stack."""
    first = stack.split(",")[0].strip().strip('"').strip("'")
    return first or "Calibri"


def _pt_value(text: str) -> float:
    """Parse a ``"12pt"`` style CSS size into a float (point) value."""
    cleaned = "".join(c for c in text if c.isdigit() or c == ".")
    try:
        return float(cleaned) if cleaned else 12.0
    except ValueError:
        return 12.0


class _ColorButton(QPushButton):
    """A swatch button that opens a color picker and remembers the hex."""

    changed = Signal()

    def __init__(self, color: str = "#000000", parent=None) -> None:
        super().__init__(parent)
        self._color = color
        self.setFixedWidth(96)
        self.clicked.connect(self._pick)
        self._refresh()

    def color(self) -> str:
        return self._color

    def set_color(self, color: str) -> None:
        self._color = color.upper()
        self._refresh()

    def _refresh(self) -> None:
        self.setText(self._color)
        self.setStyleSheet(
            f"background:{self._color}; color:{_contrast(self._color)};"
            "border:1px solid #888; padding:4px;"
        )

    def _pick(self) -> None:
        chosen = QColorDialog.getColor(
            QColor(self._color), self, i18n.tr("Pick a color")
        )
        if chosen.isValid():
            self.set_color(chosen.name())
            self.changed.emit()


class ThemeEditorDialog(QDialog):
    """Create or edit a custom theme and return its ``.epyson`` payload."""

    def __init__(
        self, parent=None, base_theme_id: str | None = None,
        edit_id: str | None = None,
    ) -> None:
        """Build the editor.

        Args:
            parent: Optional parent widget.
            base_theme_id: Theme to clone as the starting point.
            edit_id: When editing an existing custom theme, its id (the
                name is pre-filled and saving overwrites it).
        """
        super().__init__(parent)
        self.setWindowTitle("Theme editor")
        self.setMinimumWidth(720)
        self._edit_id = edit_id

        self.name_edit = QLineEdit(self)
        self.name_edit.setPlaceholderText("My theme")

        self.base_combo = QComboBox(self)
        for theme in themes.THEMES.values():
            self.base_combo.addItem(theme.display_name, theme.id)

        self._colors: dict[str, _ColorButton] = {}
        self._fonts: dict[str, QComboBox] = {}
        self._sizes: dict[str, QDoubleSpinBox] = {}
        self._weights: dict[str, QComboBox] = {}
        self._callouts: dict[str, tuple[_ColorButton, _ColorButton]] = {}

        layout = QVBoxLayout(self)

        # --- Identity ---------------------------------------------------
        ident = QFormLayout()
        ident.addRow(QLabel(i18n.tr("Name:"), self), self.name_edit)
        ident.addRow(QLabel(i18n.tr("Based on:"), self), self.base_combo)
        layout.addLayout(ident)

        body = QHBoxLayout()
        layout.addLayout(body, 1)
        left = QVBoxLayout()
        right = QVBoxLayout()
        body.addLayout(left)
        body.addLayout(right, 1)

        # --- Colors -----------------------------------------------------
        colors_box = QGroupBox(i18n.tr("Colors"), self)
        colors_grid = QFormLayout(colors_box)
        for key, label in _COLOR_FIELDS:
            btn = _ColorButton(parent=self)
            btn.changed.connect(self._update_preview)
            self._colors[key] = btn
            colors_grid.addRow(QLabel(i18n.tr(label) + ":", self), btn)
        left.addWidget(colors_box)

        # --- Fonts ------------------------------------------------------
        fonts_box = QGroupBox(i18n.tr("Fonts"), self)
        fonts_form = QFormLayout(fonts_box)
        text_font = QComboBox(self)
        text_font.setEditable(True)
        text_font.addItems(_COMMON_FONTS)
        code_font = QComboBox(self)
        code_font.setEditable(True)
        code_font.addItems(_COMMON_MONO)
        self._fonts["text"] = text_font
        self._fonts["code"] = code_font
        text_font.currentTextChanged.connect(self._update_preview)
        code_font.currentTextChanged.connect(self._update_preview)
        fonts_form.addRow(QLabel(i18n.tr("Text font:"), self), text_font)
        fonts_form.addRow(QLabel(i18n.tr("Code font:"), self), code_font)
        left.addWidget(fonts_box)
        left.addStretch(1)

        # --- Typography -------------------------------------------------
        type_box = QGroupBox(i18n.tr("Typography (pt)"), self)
        type_grid = QGridLayout(type_box)
        for row, (key, label, has_weight) in enumerate(_SCALE_ROLES):
            type_grid.addWidget(QLabel(i18n.tr(label), self), row, 0)
            size = QDoubleSpinBox(self)
            size.setRange(6.0, 96.0)
            size.setDecimals(1)
            size.setSingleStep(0.5)
            size.valueChanged.connect(self._update_preview)
            self._sizes[key] = size
            type_grid.addWidget(size, row, 1)
            if has_weight:
                weight = QComboBox(self)
                weight.addItems(_WEIGHTS)
                self._weights[key] = weight
                type_grid.addWidget(weight, row, 2)
        right.addWidget(type_box)

        # --- Callouts ---------------------------------------------------
        callout_box = QGroupBox(i18n.tr("Callout colors"), self)
        callout_grid = QGridLayout(callout_box)
        callout_grid.addWidget(QLabel(i18n.tr("Background"), self), 0, 1)
        callout_grid.addWidget(QLabel(i18n.tr("Border"), self), 0, 2)
        for row, kind in enumerate(_CALLOUTS, start=1):
            callout_grid.addWidget(
                QLabel(i18n.tr(_CALLOUT_LABELS[kind]), self), row, 0
            )
            bg = _ColorButton(parent=self)
            border = _ColorButton(parent=self)
            bg.changed.connect(self._update_preview)
            border.changed.connect(self._update_preview)
            self._callouts[kind] = (bg, border)
            callout_grid.addWidget(bg, row, 1)
            callout_grid.addWidget(border, row, 2)
        right.addWidget(callout_box)
        right.addStretch(1)

        # --- Preview ----------------------------------------------------
        self.preview_box = QGroupBox(i18n.tr("Preview"), self)
        pv = QVBoxLayout(self.preview_box)
        self._pv_heading = QLabel("Heading")
        self._pv_body = QLabel(
            "Body text with a <a href='#'>link</a> and "
            "<code>inline code</code>."
        )
        self._pv_body.setTextFormat(Qt.TextFormat.RichText)
        self._pv_callout = QLabel("Note callout")
        self._pv_callout.setMargin(8)
        self._pv_code = QLabel("def f(x): return x")
        self._pv_code.setMargin(6)
        for w in (self._pv_heading, self._pv_body, self._pv_callout,
                  self._pv_code):
            pv.addWidget(w)
        layout.addWidget(self.preview_box)

        # --- Buttons ----------------------------------------------------
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # --- Initial state ---------------------------------------------
        start_id = edit_id or base_theme_id or themes.DEFAULT_THEME_ID
        index = self.base_combo.findData(start_id)
        if index >= 0:
            self.base_combo.setCurrentIndex(index)
        self._load_from_theme(start_id)
        if edit_id and edit_id in themes.THEMES:
            self.name_edit.setText(themes.THEMES[edit_id].display_name)
        self.base_combo.currentIndexChanged.connect(self._on_base_changed)
        self._update_preview()
        i18n.translate_widget(self)

    # --------------------------------------------------------------- data

    def _load_from_theme(self, theme_id: str) -> None:
        """Pre-fill every field from an existing theme's css variables."""
        theme = themes.get(theme_id)
        cv = theme.css_vars
        mapping = {
            "page_bg": cv.get("bg", "#FFFFFF"),
            "text": cv.get("fg", "#1A1A1A"),
            "heading": cv.get("heading-color", "#00217E"),
            "primary": cv.get("link-hover", "#00217E"),
            "secondary": cv.get("link", "#0969DA"),
            "border": cv.get("border", "#C8C8C8"),
            "code_bg": cv.get("code-bg", "#F5F5F5"),
            "mark": cv.get("mark-bg", "#CA9A24"),
        }
        for key, value in mapping.items():
            self._colors[key].set_color(value)
        self._fonts["text"].setCurrentText(
            _font_primary(cv.get("font-family-text", "Calibri"))
        )
        self._fonts["code"].setCurrentText(
            _font_primary(cv.get("font-family-code", "Consolas"))
        )
        for key, _label, has_weight in _SCALE_ROLES:
            size_key = "body-size" if key == "text" else f"{key}-size"
            self._sizes[key].setValue(_pt_value(cv.get(size_key, "12pt")))
            if has_weight:
                self._weights[key].setCurrentText(
                    cv.get(f"{key}-weight", "700")
                )
        for kind in _CALLOUTS:
            bg, border = self._callouts[kind]
            bg.set_color(cv.get(f"callout-{kind}-bg", "#EAF2FB"))
            border.set_color(cv.get(f"callout-{kind}-border", "#2F6FBF"))

    def _on_base_changed(self) -> None:
        """Reload colors/fonts/typography from the newly chosen base."""
        self._load_from_theme(self.base_combo.currentData())
        self._update_preview()

    def _values(self) -> dict:
        """Collect the form into the dict expected by ``build_epyson``."""
        scales = {}
        for key, _label, has_weight in _SCALE_ROLES:
            scales[key] = {
                "size": self._sizes[key].value(),
                "weight": (self._weights[key].currentText()
                           if has_weight else "400"),
            }
        callouts = {
            kind: {"bg": bg.color(), "border": border.color()}
            for kind, (bg, border) in self._callouts.items()
        }
        return {
            "display_name": self.theme_name(),
            "page_bg": self._colors["page_bg"].color(),
            "text": self._colors["text"].color(),
            "heading": self._colors["heading"].color(),
            "primary": self._colors["primary"].color(),
            "secondary": self._colors["secondary"].color(),
            "border": self._colors["border"].color(),
            "code_bg": self._colors["code_bg"].color(),
            "mark": self._colors["mark"].color(),
            "text_font": (self._fonts["text"].currentText().strip()
                          or "Calibri"),
            "code_font": (self._fonts["code"].currentText().strip()
                          or "Consolas"),
            "scales": scales,
            "callouts": callouts,
        }

    def theme_name(self) -> str:
        """The chosen display name, stripped."""
        return self.name_edit.text().strip()

    def epyson_payload(self) -> dict:
        """Return the ``.epyson`` payload for the current form values."""
        return themes.build_epyson(self._values())

    # ------------------------------------------------------------ preview

    def _update_preview(self) -> None:
        """Restyle the preview widgets from the current form values."""
        page = self._colors["page_bg"].color()
        text = self._colors["text"].color()
        heading = self._colors["heading"].color()
        code_bg = self._colors["code_bg"].color()
        note_bg, note_border = (c.color() for c in self._callouts["note"])
        text_font = self._fonts["text"].currentText() or "sans-serif"
        code_font = self._fonts["code"].currentText() or "monospace"
        h1 = self._sizes["h1"].value()
        body = self._sizes["text"].value()

        self.preview_box.setStyleSheet(
            f"QGroupBox {{ background:{page}; }}"
        )
        self._pv_heading.setStyleSheet(
            f"color:{heading}; font-family:'{text_font}';"
            f"font-size:{h1:g}pt; font-weight:700;"
        )
        self._pv_body.setStyleSheet(
            f"color:{text}; font-family:'{text_font}'; font-size:{body:g}pt;"
            f"background:{page};"
        )
        self._pv_callout.setStyleSheet(
            f"background:{note_bg}; border-left:4px solid {note_border};"
            f"color:{text}; font-family:'{text_font}'; font-size:{body:g}pt;"
        )
        self._pv_code.setStyleSheet(
            f"background:{code_bg}; color:{text};"
            f"font-family:'{code_font}'; font-size:{body:g}pt;"
        )

    # -------------------------------------------------------------- save

    def _on_save(self) -> None:
        """Validate the name before accepting."""
        from PySide6.QtWidgets import QMessageBox  # noqa: PLC0415

        if not self.theme_name():
            QMessageBox.warning(
                self, i18n.tr("Theme editor"),
                i18n.tr("Please enter a name for the theme."),
            )
            return
        self.accept()
