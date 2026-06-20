"""Modal dialog for inserting two- or three-column content blocks.

Uses Pandoc fenced-div syntax (+fenced_divs):

    :::: {.columns}
    ::: {.column width="50%"}
    Left content
    :::
    ::: {.column width="50%"}
    Right content
    :::
    ::::
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QPlainTextEdit,
    QSpinBox,
    QVBoxLayout,
)

from epy_mdr import _i18n as i18n


class TwoColumnDialog(QDialog):
    """Ask the user for left/right content and a column split percentage."""

    def __init__(self, parent=None) -> None:
        """Build the dialog widgets (split spinbox, left/right text areas)."""
        super().__init__(parent)
        self.setWindowTitle("Insert two-column block")
        self.setMinimumWidth(420)

        self.split_spin = QSpinBox(self)
        self.split_spin.setRange(10, 90)
        self.split_spin.setValue(50)
        self.split_spin.setSuffix(" %")

        self.left_edit = QPlainTextEdit(self)
        self.left_edit.setPlaceholderText("Left column content…")
        self.left_edit.setFixedHeight(80)

        self.right_edit = QPlainTextEdit(self)
        self.right_edit.setPlaceholderText("Right column content…")
        self.right_edit.setFixedHeight(80)

        form = QFormLayout()
        form.addRow("Left column width:", self.split_spin)

        left_box = QGroupBox("Left column")
        left_layout = QVBoxLayout(left_box)
        left_layout.addWidget(self.left_edit)

        right_box = QGroupBox("Right column")
        right_layout = QVBoxLayout(right_box)
        right_layout.addWidget(self.right_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(left_box)
        layout.addWidget(right_box)
        layout.addWidget(buttons)
        i18n.translate_widget(self)

    @property
    def left_text(self) -> str:
        """Left column content, stripped."""
        return self.left_edit.toPlainText().strip()

    @property
    def right_text(self) -> str:
        """Right column content, stripped."""
        return self.right_edit.toPlainText().strip()

    @property
    def left_width(self) -> int:
        """Left column width as an integer percentage (10–90)."""
        return self.split_spin.value()

    def build_markdown(self) -> str:
        """Generate a two-column fenced-div block.

        Returns a string starting with a blank line for clean paragraph
        separation, followed by the ``:::: {.columns}`` block, and ending
        with a trailing newline.

        The width percentages sum to 100; the right column takes the
        remainder.  Both columns are pre-filled with placeholder text when
        the user left the fields empty.
        """
        left_w = self.left_width
        right_w = 100 - left_w
        left_body = self.left_text or "Left column content"
        right_body = self.right_text or "Right column content"

        lines = [
            "",
            ":::: {.columns}",
            f'::: {{.column width="{left_w}%"}}',
            left_body,
            ":::",
            f'::: {{.column width="{right_w}%"}}',
            right_body,
            ":::",
            "::::",
            "",
        ]
        return "\n".join(lines)


class ThreeColumnDialog(QDialog):
    """Ask the user for three column contents; widths default to 33/33/34 %."""

    def __init__(self, parent=None) -> None:
        """Build the dialog widgets (three width spinboxes + text areas)."""
        super().__init__(parent)
        self.setWindowTitle("Insert three-column block")
        self.setMinimumWidth(420)

        self.w1_spin = QSpinBox(self)
        self.w1_spin.setRange(5, 80)
        self.w1_spin.setValue(33)
        self.w1_spin.setSuffix(" %")

        self.w2_spin = QSpinBox(self)
        self.w2_spin.setRange(5, 80)
        self.w2_spin.setValue(33)
        self.w2_spin.setSuffix(" %")

        self.col1_edit = QPlainTextEdit(self)
        self.col1_edit.setPlaceholderText("First column content…")
        self.col1_edit.setFixedHeight(70)

        self.col2_edit = QPlainTextEdit(self)
        self.col2_edit.setPlaceholderText("Second column content…")
        self.col2_edit.setFixedHeight(70)

        self.col3_edit = QPlainTextEdit(self)
        self.col3_edit.setPlaceholderText("Third column content…")
        self.col3_edit.setFixedHeight(70)

        form = QFormLayout()
        form.addRow("Column 1 width:", self.w1_spin)
        form.addRow("Column 2 width:", self.w2_spin)

        col1_box = QGroupBox("Column 1")
        QVBoxLayout(col1_box).addWidget(self.col1_edit)

        col2_box = QGroupBox("Column 2")
        QVBoxLayout(col2_box).addWidget(self.col2_edit)

        col3_box = QGroupBox("Column 3")
        QVBoxLayout(col3_box).addWidget(self.col3_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(col1_box)
        layout.addWidget(col2_box)
        layout.addWidget(col3_box)
        layout.addWidget(buttons)
        i18n.translate_widget(self)

    @property
    def col1_text(self) -> str:
        """First column content, stripped."""
        return self.col1_edit.toPlainText().strip()

    @property
    def col2_text(self) -> str:
        """Second column content, stripped."""
        return self.col2_edit.toPlainText().strip()

    @property
    def col3_text(self) -> str:
        """Third column content, stripped."""
        return self.col3_edit.toPlainText().strip()

    @property
    def width1(self) -> int:
        """First column width percentage."""
        return self.w1_spin.value()

    @property
    def width2(self) -> int:
        """Second column width percentage."""
        return self.w2_spin.value()

    @property
    def width3(self) -> int:
        """Third column width: remainder after columns 1 and 2."""
        return max(5, 100 - self.width1 - self.width2)

    def build_markdown(self) -> str:
        """Generate a three-column fenced-div block.

        Returns a string starting with a blank line for clean paragraph
        separation, followed by the ``:::: {.columns}`` block, and ending
        with a trailing newline.

        The third column width is computed as ``100 - w1 - w2`` (clamped to
        a minimum of 5 %) so the user only needs to specify two values.
        Column bodies fall back to placeholder text when left empty.
        """
        w1 = self.width1
        w2 = self.width2
        w3 = self.width3
        body1 = self.col1_text or "Column 1 content"
        body2 = self.col2_text or "Column 2 content"
        body3 = self.col3_text or "Column 3 content"

        lines = [
            "",
            ":::: {.columns}",
            f'::: {{.column width="{w1}%"}}',
            body1,
            ":::",
            f'::: {{.column width="{w2}%"}}',
            body2,
            ":::",
            f'::: {{.column width="{w3}%"}}',
            body3,
            ":::",
            "::::",
            "",
        ]
        return "\n".join(lines)
