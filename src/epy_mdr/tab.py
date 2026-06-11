"""A single editor/preview tab used by the epy_mdr window."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QFont, QFontDatabase, QTextCursor
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QInputDialog,
    QMessageBox,
    QPlainTextEdit,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from epy_mdr import snippets
from epy_mdr.renderer import render_markdown
from epy_mdr.xref_dialog import CrossRefDialog

RENDER_DEBOUNCE_MS = 250
UNTITLED = "untitled.md"


class MarkdownTab(QWidget):
    """Editor + live preview for one Markdown buffer.

    Signals:
        pathChanged: Emitted when the on-disk path is set or changed.
        dirtyChanged: Emitted with the new dirty flag when it flips.
    """

    pathChanged = Signal()  # noqa: N815 (Qt signal naming convention)
    dirtyChanged = Signal(bool)  # noqa: N815 (Qt signal naming)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Build the editor, the web preview and the debounce timer."""
        super().__init__(parent)

        self._path: Path | None = None
        self._dirty = False
        self._suppress_change = False
        self._theme_css: str = ""

        self.editor = QPlainTextEdit(self)
        self._setup_editor()

        self.view = QWebEngineView(self)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.addWidget(self.editor)
        splitter.addWidget(self.view)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([520, 600])

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter)

        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.setInterval(RENDER_DEBOUNCE_MS)
        self._render_timer.timeout.connect(self._render)

        self.editor.textChanged.connect(self._on_text_changed)

    def _setup_editor(self) -> None:
        """Configure the editor with monospace font and 4-space tabs."""
        font = QFontDatabase.systemFont(
            QFontDatabase.SystemFont.FixedFont
        )
        if font.pointSize() < 1:
            font = QFont("Consolas")
        font.setPointSize(11)
        self.editor.setFont(font)
        metrics = self.editor.fontMetrics()
        self.editor.setTabStopDistance(4 * metrics.horizontalAdvance(" "))
        self.editor.setLineWrapMode(
            QPlainTextEdit.LineWrapMode.WidgetWidth
        )
        self.editor.setPlaceholderText(
            "Type Markdown here. Preview updates on the right."
        )

    # ------------------------------------------------------------- API

    @property
    def path(self) -> Path | None:
        """Return the on-disk path, or ``None`` for unsaved buffers."""
        return self._path

    @property
    def dirty(self) -> bool:
        """Return ``True`` if the buffer has unsaved changes."""
        return self._dirty

    def title(self) -> str:
        """Return the tab title, suffixed with ``*`` when dirty."""
        base = self._path.name if self._path is not None else UNTITLED
        return f"{base} *" if self._dirty else base

    def text(self) -> str:
        """Return the current editor text."""
        return self.editor.toPlainText()

    def set_initial_text(
        self, text: str, path: Path | None = None
    ) -> None:
        """Populate the buffer from disk or a template, then render.

        Args:
            text: Initial buffer contents.
            path: Optional path that ``text`` was loaded from.
        """
        self._suppress_change = True
        self.editor.setPlainText(text)
        self._suppress_change = False
        self._path = path
        self._set_dirty(False)
        self._render_now()
        self.pathChanged.emit()

    def load_file(self, path: Path) -> None:
        """Load a Markdown file from disk into this tab."""
        text = path.read_text(encoding="utf-8")
        self.set_initial_text(text, path)

    def save(self) -> bool:
        """Save the buffer to its current path.

        Returns:
            ``True`` if the buffer was written, ``False`` when no path
            is associated with the tab (caller should fall back to
            *Save As*).
        """
        if self._path is None:
            return False
        self._path.write_text(self.editor.toPlainText(), encoding="utf-8")
        self._set_dirty(False)
        return True

    def save_as(self, path: Path) -> None:
        """Save the buffer to ``path`` and adopt it as current path."""
        path.write_text(self.editor.toPlainText(), encoding="utf-8")
        self._path = path
        self._set_dirty(False)
        self.pathChanged.emit()
        # Re-render so the preview's <base> uses the new directory.
        self._render_now()

    def reload(self) -> None:
        """Reload the buffer from disk, discarding in-memory changes."""
        if self._path is None:
            return
        self.load_file(self._path)

    def set_theme_css(self, css: str) -> None:
        """Update the preview's theme CSS and re-render immediately."""
        self._theme_css = css
        self._render_now()

    def export_pdf(self, target: Path) -> None:
        """Print the current preview to ``target`` as a PDF file."""
        self.view.page().printToPdf(str(target))

    # ------------------------------------------------- editor actions

    def toggle_bold(self) -> None:
        """Wrap the current selection (or caret) in ``**...**``."""
        self._wrap_selection("**", "**", placeholder="bold")

    def toggle_italic(self) -> None:
        """Wrap the current selection (or caret) in ``*...*``."""
        self._wrap_selection("*", "*", placeholder="italic")

    def toggle_inline_code(self) -> None:
        """Wrap the current selection (or caret) in ``` `...` ```."""
        self._wrap_selection("`", "`", placeholder="code")

    def set_heading_level(self, level: int) -> None:
        """Replace the current line's heading prefix to ``level``.

        Args:
            level: ``1``-``6`` to apply that ``#``-level prefix; ``0``
                to strip any existing prefix (turn the line back into
                a paragraph).
        """
        cursor = self.editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.movePosition(
            QTextCursor.MoveOperation.EndOfBlock,
            QTextCursor.MoveMode.KeepAnchor,
        )
        line = cursor.selectedText()
        stripped = line.lstrip("#").lstrip(" ")
        if level <= 0:
            new_line = stripped
        else:
            level = max(1, min(level, 6))
            prefix = "#" * level
            new_line = f"{prefix} {stripped}" if stripped else f"{prefix} "
        cursor.insertText(new_line)
        # Place the caret at the end of the new line.
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
        self.editor.setTextCursor(cursor)
        self.editor.setFocus()

    def insert_section_heading(self) -> None:
        """Insert ``## Section title {#sec-LABEL}`` and select label."""
        self._insert_template(
            snippets.SECTION_HEADING_TEMPLATE, "LABEL"
        )

    def insert_link(self) -> None:
        """Insert ``[text](url)``; uses the current selection as text."""
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            text = cursor.selectedText()
            inserted = f"[{text}](URL)"
            cursor.insertText(inserted)
            end = cursor.position()
            cursor.setPosition(end - 4)
            cursor.setPosition(
                end - 1, QTextCursor.MoveMode.KeepAnchor
            )
            self.editor.setTextCursor(cursor)
        else:
            self._insert_template(snippets.LINK_TEMPLATE, "TEXT")
        self.editor.setFocus()

    def insert_figure(self) -> None:
        """Insert a Quarto figure skeleton and select its label."""
        self._insert_template(snippets.FIGURE_TEMPLATE, "LABEL")

    def insert_image_from_dialog(self) -> None:
        """Pick an image file, copy to figures/, insert at cursor."""
        start_dir = (
            str(self._path.parent)
            if self._path is not None
            else ""
        )
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Insert image",
            start_dir,
            "Images (*.png *.jpg *.jpeg *.gif *.svg *.webp *.bmp);;All files (*)",
        )
        if not filename:
            return

        src = Path(filename)

        # Determine figures/ directory
        if self._path is not None:
            figures_dir = self._path.parent / "figures"
        else:
            figures_dir = Path.cwd() / "figures"
        figures_dir.mkdir(parents=True, exist_ok=True)

        # Resolve name collision
        dst = figures_dir / src.name
        if dst.exists():
            stem = src.stem
            suffix = src.suffix
            counter = 1
            while dst.exists():
                dst = figures_dir / f"{stem}-{counter}{suffix}"
                counter += 1

        shutil.copy2(str(src), str(dst))

        # Build relative path for markdown
        if self._path is not None:
            rel = dst.relative_to(self._path.parent)
        else:
            rel = dst
        md_path = str(rel).replace("\\", "/")

        # Auto-generate label from filename
        label = re.sub(r"[^a-z0-9-]+", "-", src.stem.lower()).strip("-")
        if not label:
            label = "image"

        # Caption: prompt user with filename as default
        caption, ok = QInputDialog.getText(
            self,
            "Image caption",
            "Caption:",
            text=src.stem,
        )
        if not ok:
            caption = src.stem
        caption = caption or src.stem

        md = snippets.IMAGE_MARKDOWN.format(
            caption=caption, path=md_path, label=label
        )

        cursor = self.editor.textCursor()
        if cursor.positionInBlock() != 0:
            cursor.insertText("\n")
        cursor.insertText(md + "\n")
        self.editor.setFocus()

    def insert_table(self) -> None:
        """Insert a 3-column pipe table with caption and select label."""
        self._insert_template(snippets.TABLE_TEMPLATE, "LABEL")

    def insert_equation(self) -> None:
        """Insert a display equation with a ``{#eq-...}`` label."""
        self._insert_template(snippets.EQUATION_TEMPLATE, "LABEL")

    def insert_code_block(self) -> None:
        """Insert a fenced Python code block skeleton."""
        self._insert_template(snippets.CODE_BLOCK_TEMPLATE, "CODE")

    def insert_callout(self, kind: str = "note") -> None:
        """Insert a Quarto fenced callout of the given ``kind``."""
        template = snippets.CALLOUT_TEMPLATES.get(
            kind, snippets.CALLOUT_TEMPLATES["note"]
        )
        token = "TITLE" if "TITLE" in template else "BODY"
        self._insert_template(template, token)

    def insert_cross_reference(self) -> None:
        """Open the cross-ref picker and insert ``@label`` on confirm.

        The picker is fed with both buffer labels (figure / table /
        equation / section) and BibTeX entries from the linked
        ``bibliography:`` file, so a single shortcut can cite
        anything.
        """
        text = self.editor.toPlainText()
        labels = snippets.find_labels(text)
        bib_entries = self._bib_entries_for_buffer(text)
        cite_labels = [
            snippets.Label(kind="cite", name=entry.key)
            for entry in bib_entries
        ]
        combined = labels + cite_labels
        if not combined:
            QMessageBox.information(
                self,
                "Cross-reference",
                "Nothing to cite yet. Add a figure / table / "
                "equation / section heading, or link a "
                "bibliography (.bib).",
            )
            return
        # Pre-fetch bib metadata for nicer labels in the picker.
        bib_lookup = {e.key: e for e in bib_entries}
        dialog = CrossRefDialog(
            combined, parent=self, bib_lookup=bib_lookup
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        chosen = dialog.selected_label()
        if chosen is None:
            return
        cursor = self.editor.textCursor()
        cursor.insertText(f"@{chosen.name}")
        self.editor.setFocus()

    # ------------------------------------------- bibliography link

    def link_bibliography(self, bib_path: Path) -> None:
        """Write ``bibliography: <path>`` into the YAML front matter.

        The path is stored relative to the file's directory when the
        document already lives on disk, so the link travels with the
        project. A new YAML block is created at the top of the buffer
        if none exists.
        """
        text = self.editor.toPlainText()
        value = self._relative_to_doc(bib_path)
        updated = snippets.set_metadata_field(text, "bibliography", value)
        if updated == text:
            return
        self._apply_buffer_replacement(updated)

    def bib_entries(self) -> list:
        """Return the parsed BibTeX entries for the linked bib file."""
        return self._bib_entries_for_buffer(self.editor.toPlainText())

    # ------------------------------------------------- internals

    def _bib_entries_for_buffer(self, text: str) -> list:
        """Resolve the ``bibliography:`` field and parse the .bib."""
        from epy_mdr import bib

        meta = snippets.parse_front_matter(text)
        value = meta.get("bibliography")
        if not value:
            return []
        bib_path = Path(value)
        if not bib_path.is_absolute() and self._path is not None:
            bib_path = (self._path.parent / bib_path).resolve()
        if not bib_path.is_file():
            return []
        return bib.parse_bib_file(bib_path)

    def _relative_to_doc(self, target: Path) -> str:
        """Return ``target`` relative to the file directory if possible."""
        target = target.resolve()
        if self._path is None:
            return str(target).replace("\\", "/")
        base = self._path.parent.resolve()
        try:
            rel = target.relative_to(base)
            return str(rel).replace("\\", "/")
        except ValueError:
            return str(target).replace("\\", "/")

    def _apply_buffer_replacement(self, new_text: str) -> None:
        """Replace the entire buffer atomically and update state."""
        cursor = self.editor.textCursor()
        cursor.beginEditBlock()
        try:
            cursor.select(QTextCursor.SelectionType.Document)
            cursor.insertText(new_text)
        finally:
            cursor.endEditBlock()
        self._set_dirty(True)
        self._render_now()

    # -------------------------------------------- editor primitives

    def _wrap_selection(
        self, left: str, right: str, placeholder: str = ""
    ) -> None:
        """Wrap the selection in ``left``/``right`` or insert markers.

        Without a selection, ``placeholder`` is inserted between the
        markers and pre-selected so the user can type over it.
        """
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            text = cursor.selectedText()
            cursor.insertText(f"{left}{text}{right}")
        else:
            cursor.insertText(f"{left}{placeholder}{right}")
            end = cursor.position()
            cursor.setPosition(end - len(right) - len(placeholder))
            cursor.setPosition(
                end - len(right),
                QTextCursor.MoveMode.KeepAnchor,
            )
            self.editor.setTextCursor(cursor)
        self.editor.setFocus()

    def _insert_template(self, template: str, select_token: str) -> None:
        """Insert ``template`` at the caret and select ``select_token``.

        Block-level templates get a leading newline when the caret is
        not already at the start of a line, so the inserted Markdown
        does not glue to the previous paragraph.
        """
        cursor = self.editor.textCursor()
        block_template = "\n" in template
        if block_template and cursor.positionInBlock() != 0:
            cursor.insertText("\n")
        start = cursor.position()
        cursor.insertText(template)
        index = template.find(select_token)
        if index >= 0:
            cursor.setPosition(start + index)
            cursor.setPosition(
                start + index + len(select_token),
                QTextCursor.MoveMode.KeepAnchor,
            )
            self.editor.setTextCursor(cursor)
        self.editor.setFocus()

    # ----------------------------------------------------- internals

    def _set_dirty(self, value: bool) -> None:
        """Update the dirty flag and notify listeners on change."""
        if self._dirty != value:
            self._dirty = value
            self.dirtyChanged.emit(value)

    def _on_text_changed(self) -> None:
        """React to user edits: flag dirty and schedule a re-render."""
        if self._suppress_change:
            return
        if not self._dirty:
            self._set_dirty(True)
        self._render_timer.start()

    def _render(self) -> None:
        """Render the current buffer into the preview pane."""
        self._render_now()

    def _render_now(self) -> None:
        """Render synchronously (called on load and after Save As)."""
        text = self.editor.toPlainText()
        base_dir = self._path.parent if self._path is not None else None
        title = (
            self._path.name if self._path is not None else UNTITLED
        )
        html = render_markdown(
            text,
            base_dir=base_dir,
            title=title,
            theme_css=self._theme_css,
        )
        if base_dir is not None:
            base_url = QUrl.fromLocalFile(str(base_dir) + "/")
        else:
            base_url = QUrl()
        self.view.setHtml(html, base_url)
