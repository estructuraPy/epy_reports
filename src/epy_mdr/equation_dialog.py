"""Modal dialog for inserting a display equation with a reference ID."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from epy_mdr.latex_catalog import CATALOG, LatexEntry


class EquationDialog(QDialog):
    """Ask the user for LaTeX body and a short reference ID.

    A categorised LaTeX palette sits below the editor: clicking a button
    inserts the corresponding LaTeX command at the current caret
    position. The catalog covers Greek letters, operators and
    relations, calculus, structural notation, matrices and vectors,
    sets and logic, common functions, and structural-engineering
    shortcuts.
    """

    def __init__(
        self, parent=None, default_id: str = "1"
    ) -> None:
        """Build the dialog widgets.

        Args:
            parent: Optional parent widget.
            default_id: Suffix pre-filled in the Reference ID field.
        """
        super().__init__(parent)
        self.setWindowTitle("Insert equation")
        self.setMinimumSize(720, 540)
        self._default_id = default_id

        self.body_edit = QPlainTextEdit(self)
        self.body_edit.setPlainText("y = f(x)")
        self.body_edit.setMinimumHeight(110)

        self.id_edit = QLineEdit(self)
        self.id_edit.setText(default_id)
        self.id_edit.setPlaceholderText("e.g. 1, euler-beam")

        form = QFormLayout()
        form.addRow("LaTeX body:", self.body_edit)
        form.addRow("Reference ID:", self.id_edit)

        self.catalog_tabs = QTabWidget(self)
        for category, entries in CATALOG.items():
            self.catalog_tabs.addTab(
                self._build_catalog_tab(entries), category
            )

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.catalog_tabs, stretch=1)
        layout.addWidget(buttons)

    def _build_catalog_tab(self, entries: list[LatexEntry]) -> QWidget:
        """Build a scroll-area + grid of insertion buttons for one tab."""
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        inner = QWidget()
        grid = QGridLayout(inner)
        grid.setSpacing(4)
        grid.setContentsMargins(6, 6, 6, 6)
        cols = 6
        for index, entry in enumerate(entries):
            btn = QPushButton(entry.label, inner)
            btn.setToolTip(f"{entry.tooltip}\n{entry.latex}")
            btn.setMinimumWidth(78)
            btn.clicked.connect(
                lambda _checked=False, latex=entry.latex: self._insert(latex)
            )
            grid.addWidget(btn, index // cols, index % cols)
        grid.setRowStretch(grid.rowCount(), 1)
        scroll.setWidget(inner)
        return scroll

    def _insert(self, latex: str) -> None:
        """Insert *latex* at the body_edit caret position."""
        cursor = self.body_edit.textCursor()
        cursor.insertText(latex)
        self.body_edit.setFocus()

    @property
    def body(self) -> str:
        """LaTeX body text, stripped."""
        return self.body_edit.toPlainText().strip()

    @property
    def reference_id(self) -> str:
        """Reference ID suffix, stripped; falls back to default_id."""
        value = self.id_edit.text().strip()
        return value if value else self._default_id

    def build_markdown(self) -> str:
        r"""Return the Quarto display-equation Markdown string.

        Returns:
            A string of the form ``$$\n<body>\n$$ {#eq-id}``.
        """
        body = self.body or "y = f(x)"
        return f"$$\n{body}\n$$ {{#eq-{self.reference_id}}}"
