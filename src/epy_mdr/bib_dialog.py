"""Modal dialog for creating a new BibTeX entry.

Lets the user pick an entry type, fill the canonical fields, and
preview the resulting BibTeX snippet live. The auto-suggested
citation key (``familyYYYY``) is filled in from author and year unless
the user has already typed something different.

The dialog only produces a :class:`~epy_mdr.bib.BibEntryDraft`; the
caller decides where to write it (typically by appending to the
``bibliography:`` file linked from the document's YAML).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from epy_mdr.bib import (
    ENTRY_TYPES,
    REQUIRED_FIELDS,
    BibEntryDraft,
    serialize_draft,
    suggest_key,
)

# Field name → human-readable label shown in the form.
_LABELS: dict[str, str] = {
    "key":          "Citation key *",
    "author":       "Author(s)",
    "editor":       "Editor(s)",
    "title":        "Title",
    "journal":      "Journal",
    "booktitle":    "Book title / proceedings",
    "publisher":    "Publisher",
    "institution":  "Institution",
    "school":       "School / university",
    "organization": "Organization",
    "year":         "Year",
    "month":        "Month",
    "volume":       "Volume",
    "number":       "Number / issue",
    "pages":        "Pages",
    "edition":      "Edition",
    "chapter":      "Chapter",
    "address":      "Address (city)",
    "howpublished": "How published",
    "doi":          "DOI",
    "url":          "URL",
    "urldate":      "URL access date",
    "isbn":         "ISBN",
    "note":         "Note",
}

# Logical groups so the form stays readable on tall dialogs.
_GROUPS: list[tuple[str, list[str]]] = [
    ("Identity",   ["key", "author", "editor", "title"]),
    ("Venue",      ["journal", "booktitle", "publisher",
                    "institution", "school", "organization"]),
    ("Date",       ["year", "month"]),
    ("Details",    ["volume", "number", "pages", "edition", "chapter"]),
    ("Location",   ["address", "howpublished"]),
    ("Identifiers", ["doi", "url", "urldate", "isbn", "note"]),
]


class BibEntryDialog(QDialog):
    """Modal dialog to compose a new BibTeX entry.

    Exposes :meth:`build_draft` returning a populated
    :class:`BibEntryDraft` and :meth:`build_bibtex` returning the
    serialized snippet for inspection or direct insertion.
    """

    def __init__(
        self,
        parent=None,
        existing_keys: set[str] | None = None,
        default_type: str = "article",
    ) -> None:
        """Build the widgets and wire live preview / key suggestion.

        Args:
            parent: Optional parent widget.
            existing_keys: Keys already present in the linked .bib file,
                so the dialog can warn before overwriting them.
            default_type: Entry type pre-selected in the type combo.
        """
        super().__init__(parent)
        self.setWindowTitle("New bibliography entry")
        self.setMinimumSize(620, 640)
        self._existing_keys: set[str] = set(existing_keys or ())
        self._user_typed_key = False

        # Entry-type selector
        self.type_combo = QComboBox(self)
        for entry_type in ENTRY_TYPES:
            self.type_combo.addItem(entry_type)
        if default_type in ENTRY_TYPES:
            self.type_combo.setCurrentText(default_type)
        self.type_combo.currentTextChanged.connect(self._on_type_changed)

        self.required_label = QLabel(self)
        self.required_label.setWordWrap(True)
        self.required_label.setStyleSheet("color: #666;")

        # Field editors
        self._field_edits: dict[str, QLineEdit] = {}
        for name in (*_LABELS.keys(),):
            edit = QLineEdit(self)
            edit.textChanged.connect(self._refresh_preview)
            self._field_edits[name] = edit

        self._field_edits["key"].textEdited.connect(
            self._on_key_text_edited
        )
        self._field_edits["author"].textChanged.connect(
            self._maybe_autosuggest_key
        )
        self._field_edits["year"].textChanged.connect(
            self._maybe_autosuggest_key
        )

        form_groups = QVBoxLayout()
        form_groups.setContentsMargins(0, 0, 0, 0)
        for title, names in _GROUPS:
            box = QGroupBox(title, self)
            layout = QFormLayout(box)
            layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
            for name in names:
                layout.addRow(_LABELS[name], self._field_edits[name])
            form_groups.addWidget(box)

        form_container = QWidget(self)
        form_container.setLayout(form_groups)

        # Scroll area for the form so the dialog stays manageable.
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setWidget(form_container)

        # Live preview
        self.preview = QPlainTextEdit(self)
        self.preview.setReadOnly(True)
        self.preview.setFixedHeight(140)
        self.preview.setStyleSheet(
            "QPlainTextEdit { font-family: Consolas, monospace; "
            "background: #f6f8fa; }"
        )
        preview_label = QLabel("Preview:", self)
        preview_label.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )

        # Top row: entry type + required-fields hint
        top = QHBoxLayout()
        top.addWidget(QLabel("Entry type:", self))
        top.addWidget(self.type_combo)
        top.addStretch(1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.required_label)
        layout.addWidget(scroll, stretch=1)
        layout.addWidget(preview_label)
        layout.addWidget(self.preview)
        layout.addWidget(buttons)

        # Prime
        self._on_type_changed(self.type_combo.currentText())
        self._refresh_preview()

    # ----------------------------------------------------- Field model

    def build_draft(self) -> BibEntryDraft:
        """Snapshot the dialog into a :class:`BibEntryDraft`."""
        draft = BibEntryDraft(type=self.type_combo.currentText())
        for name, edit in self._field_edits.items():
            setattr(draft, name, edit.text().strip())
        return draft

    def build_bibtex(self) -> str:
        """Return the canonical BibTeX text for the current draft."""
        return serialize_draft(self.build_draft())

    # ----------------------------------------------------- Reactions

    def _on_type_changed(self, entry_type: str) -> None:
        """Update the required-fields hint and refresh the preview."""
        required = REQUIRED_FIELDS.get(entry_type, ())
        if required:
            joined = ", ".join(required)
            self.required_label.setText(
                f"Required for @{entry_type}: key, {joined}."
            )
        else:
            self.required_label.setText(
                f"Required for @{entry_type}: key."
            )
        self._refresh_preview()

    def _on_key_text_edited(self, _text: str) -> None:
        """Track manual edits so auto-suggestion stops overwriting them."""
        self._user_typed_key = True

    def _maybe_autosuggest_key(self) -> None:
        """Populate the key from author+year unless the user has typed one."""
        if self._user_typed_key and self._field_edits["key"].text().strip():
            return
        author = self._field_edits["author"].text()
        year = self._field_edits["year"].text()
        suggestion = suggest_key(author, year)
        if suggestion:
            self._field_edits["key"].setText(suggestion)

    def _refresh_preview(self) -> None:
        """Render the current draft into the preview pane."""
        self.preview.setPlainText(self.build_bibtex())

    # ------------------------------------------------------- Validation

    def _accept(self) -> None:
        """Validate required fields and key uniqueness before accepting."""
        draft = self.build_draft()
        missing = draft.missing_required()
        if missing:
            QMessageBox.warning(
                self,
                "Missing required fields",
                "These fields are required for @"
                + draft.type + ": " + ", ".join(missing),
            )
            return
        if draft.key in self._existing_keys:
            reply = QMessageBox.question(
                self,
                "Key already exists",
                f"The key {draft.key!r} is already in the linked "
                ".bib file. Append anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        self.accept()
