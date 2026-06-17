"""A single editor/preview tab used by the epy_mdr window."""

from __future__ import annotations

import re
import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QMarginsF, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import (
    QFont,
    QFontDatabase,
    QPageLayout,
    QPageSize,
    QTextCursor,
)
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
from epy_mdr.checklist_dialog import ChecklistDialog
from epy_mdr.equation_dialog import EquationDialog
from epy_mdr.figure_dialog import FigureDialog
from epy_mdr.footnote_dialog import FootnoteDialog
from epy_mdr.renderer import normalize_page_size, render_markdown
from epy_mdr.table_dialog import TableDialog
from epy_mdr.template import is_truthy
from epy_mdr.xref_dialog import CrossRefDialog

RENDER_DEBOUNCE_MS = 250
UNTITLED = "untitled.md"

# Matches the integer suffix of a ``[^fn-N]`` footnote marker.
_FOOTNOTE_RE = re.compile(r"\[\^fn-(\d+)\]")

# MathJax typeset-completion poll: how long to wait before giving up.
_MATHJAX_TIMEOUT_MS = 20_000
_MATHJAX_POLL_MS = 100


def next_label_suffix(text: str, kind: str) -> str:
    """Return the next sequential integer suffix for ``kind`` labels.

    Scans all Quarto labels of the given kind in ``text`` (e.g.
    ``fig``, ``tbl``, ``eq``, ``sec``).  Among suffixes that are pure
    integers, returns ``str(max + 1)``.  When no integer suffix exists
    the function returns ``"1"``.

    Args:
        text: Full Markdown buffer contents.
        kind: Label kind — one of ``fig``, ``tbl``, ``eq``, ``sec``.

    Returns:
        Short sequential string, e.g. ``"3"`` when ``{#fig-1}`` and
        ``{#fig-2}`` are already present.
    """
    labels = snippets.find_labels(text)
    ints: list[int] = []
    prefix = f"{kind}-"
    for label in labels:
        if label.kind != kind:
            continue
        suffix = label.name[len(prefix):]
        if suffix.isdigit():
            ints.append(int(suffix))
    return str(max(ints) + 1) if ints else "1"


def next_footnote_suffix(text: str) -> str:
    """Return the next sequential integer suffix for ``[^fn-N]`` markers.

    Scans every ``[^fn-N]`` footnote marker in ``text`` whose suffix is
    a pure integer and returns ``str(max + 1)``. When none exist the
    function returns ``"1"``. Kept module-level so it is unit-testable
    without a widget instance, mirroring :func:`next_label_suffix`.

    Args:
        text: Full Markdown buffer contents.

    Returns:
        Short sequential string, e.g. ``"3"`` when ``[^fn-1]`` and
        ``[^fn-2]`` are already present.
    """
    ints = [int(m) for m in _FOOTNOTE_RE.findall(text)]
    return str(max(ints) + 1) if ints else "1"


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
        self._paged = False

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

    def set_paged(self, value: bool) -> None:
        """Toggle the A4 page-view preview and re-render immediately.

        Preview-only: PDF/HTML/DOCX exports are unaffected. The PDF
        export path forces a non-paged render before printing so the
        gray backdrop never leaks into the exported file.

        Args:
            value: ``True`` to show the content as an A4 sheet.
        """
        self._paged = value
        self._render_now()

    def export_pdf(
        self,
        target: Path,
        on_done: Callable[[Path, bool], None] | None = None,
    ) -> None:
        """Export the current preview to ``target`` as a PDF file.

        The export is a strict improvement over a bare
        ``printToPdf``: it (a) renders a fresh, non-paged export page
        into the view and gates printing on the view's ``loadFinished``
        so the print never fires against a stale page, (b) waits for
        MathJax to finish typesetting so equations are rendered, (c)
        prints with an explicit portrait page layout (page size taken
        from the document's ``page-size`` front matter, default Letter)
        with ~15 mm margins, and (d) when the document front matter
        declares a ``footer`` text or a truthy ``page-numbers`` value,
        stamps every page via :func:`epy_mdr._pdf_footer.add_footer`
        before delivering the final file.

        Args:
            target: Destination ``.pdf`` path.
            on_done: Optional callback ``(target, ok)`` invoked when the
                export finishes (success or failure). ``target`` is the
                final destination path so the caller can report it.
        """
        meta = snippets.parse_front_matter(self.editor.toPlainText())
        footer_text = meta.get("footer", "")
        page_numbers = is_truthy(meta.get("page-numbers"))
        lang = meta.get("lang", "en")
        page_size = normalize_page_size(meta.get("page-size"))

        tmp_dir = Path(tempfile.mkdtemp(prefix="epy_mdr_pdf_"))
        tmp_pdf = tmp_dir / "export.pdf"

        def finalize(_path: str, ok: bool) -> None:
            """Stamp footers, move into place, then notify the caller."""
            result_ok = ok
            try:
                if ok:
                    if footer_text or page_numbers:
                        from epy_mdr import _pdf_footer  # noqa: PLC0415

                        _pdf_footer.add_footer(
                            tmp_pdf,
                            footer_text,
                            page_numbers=page_numbers,
                            lang=lang,
                        )
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(tmp_pdf), str(target))
            except (OSError, RuntimeError):
                result_ok = False
            finally:
                shutil.rmtree(tmp_dir, ignore_errors=True)
                # Always restore the user's live preview (re-applying
                # the current paged + page-size state) on both paths.
                self._render_now()
            if on_done is not None:
                on_done(target, result_ok)

        def do_print() -> None:
            """Print the loaded export page to the temp file."""
            self.view.page().pdfPrintingFinished.connect(
                finalize, Qt.ConnectionType.SingleShotConnection
            )
            self.view.page().printToPdf(
                str(tmp_pdf), self._page_layout(page_size)
            )

        def on_loaded(ok: bool) -> None:
            """Run after the fresh export page finishes loading."""
            if not ok:
                # Load failed — finalize as failure (also restores
                # the live preview via the finalize cleanup path).
                finalize("", False)
                return
            self._wait_for_mathjax(do_print)

        # Always render a FRESH, non-paged export page into the view.
        # Connect the one-shot loadFinished BEFORE loading so the signal
        # can never be missed; SingleShotConnection keeps it from
        # leaking into later preview reloads.
        self.view.loadFinished.connect(
            on_loaded, Qt.ConnectionType.SingleShotConnection
        )
        self._render_into_view(paged=False, page_size=page_size)

    @staticmethod
    def _page_layout(page_size: str) -> QPageLayout:
        """Return a portrait page layout with ~15 mm margins.

        Args:
            page_size: Page-size key (``letter`` / ``a4`` / ``legal``).
                Unknown or missing values fall back to Letter.

        Returns:
            A :class:`QPageLayout` using the matching
            :class:`QPageSize.PageSizeId`.
        """
        ids = {
            "letter": QPageSize.PageSizeId.Letter,
            "a4":     QPageSize.PageSizeId.A4,
            "legal":  QPageSize.PageSizeId.Legal,
        }
        size_id = ids.get(normalize_page_size(page_size), ids["letter"])
        margins = QMarginsF(15.0, 15.0, 15.0, 15.0)
        return QPageLayout(
            QPageSize(size_id),
            QPageLayout.Orientation.Portrait,
            margins,
            QPageLayout.Unit.Millimeter,
        )

    def _wait_for_mathjax(self, then: Callable[[], None]) -> None:
        r"""Poll ``window._mathjax_done`` then run ``then``.

        MathJax sets ``window._mathjax_done`` once typesetting has
        finished (see the template's startup hook). Printing before
        that leaves equations as raw ``\[ … \]`` text. This polls the
        flag and calls ``then`` as soon as it is truthy, or after a
        timeout so a document with no math still prints promptly.
        """
        elapsed = [0]

        def check() -> None:
            def handle(done: object) -> None:
                if done is True:
                    then()
                    return
                elapsed[0] += _MATHJAX_POLL_MS
                if elapsed[0] >= _MATHJAX_TIMEOUT_MS:
                    then()
                    return
                QTimer.singleShot(_MATHJAX_POLL_MS, check)

            self.view.page().runJavaScript(
                "window._mathjax_done === true", handle
            )

        check()

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
        """Prompt for heading text, insert with auto sec-N label."""
        text, ok = QInputDialog.getText(
            self, "Section heading", "Heading text:",
            text="Section title",
        )
        if not ok or not text:
            text = "Section title"
        suffix = self._next_label_suffix("sec")
        md = f"## {text} {{#sec-{suffix}}}"
        cursor = self.editor.textCursor()
        if cursor.positionInBlock() != 0:
            cursor.insertText("\n")
        cursor.insertText(md + "\n")
        self.editor.setFocus()

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

    def _next_label_suffix(self, kind: str) -> str:
        """Return the next sequential integer suffix for ``kind``.

        Delegates to the module-level :func:`next_label_suffix` so
        the logic is unit-testable without a widget instance.
        """
        return next_label_suffix(self.editor.toPlainText(), kind)

    def insert_figure(self) -> None:
        """Open FigureDialog; insert figure Markdown on accept."""
        dialog = FigureDialog(
            self, default_id=self._next_label_suffix("fig")
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        md = dialog.build_markdown()
        cursor = self.editor.textCursor()
        if cursor.positionInBlock() != 0:
            cursor.insertText("\n")
        cursor.insertText(md + "\n")
        self.editor.setFocus()

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
            "Images (*.png *.jpg *.jpeg *.gif *.svg *.webp *.bmp)"
            ";;All files (*)",
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

        # Sequential label independent of filename
        label = self._next_label_suffix("fig")

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

        # Width: prompt the user; blank or cancel falls back to 80%.
        width, ok = QInputDialog.getText(
            self,
            "Image width",
            "Width (e.g. 80%, 300px):",
            text="80%",
        )
        if not ok or not width.strip():
            width = "80%"

        md = snippets.IMAGE_MARKDOWN.format(
            caption=caption, path=md_path, label=label, width=width
        )

        cursor = self.editor.textCursor()
        if cursor.positionInBlock() != 0:
            cursor.insertText("\n")
        cursor.insertText(md + "\n")
        self.editor.setFocus()

    def insert_table(self) -> None:
        """Open table dialog, then insert pipe table with caption."""
        dialog = TableDialog(
            self, default_id=self._next_label_suffix("tbl")
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        md = dialog.build_markdown()
        cursor = self.editor.textCursor()
        if cursor.positionInBlock() != 0:
            cursor.insertText("\n")
        cursor.insertText(md)
        self.editor.setFocus()

    def insert_checklist(self) -> None:
        """Open checklist dialog, then insert task-list items at cursor."""
        dialog = ChecklistDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        md = dialog.build_markdown()
        cursor = self.editor.textCursor()
        # build_markdown already starts with a blank line, so we only
        # need to move to a new line when we are not at the start of
        # the document and the leading blank line is not enough.
        cursor.insertText(md)
        self.editor.setFocus()

    def insert_equation(self) -> None:
        """Open EquationDialog; insert display equation on accept."""
        dialog = EquationDialog(
            self, default_id=self._next_label_suffix("eq")
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        md = dialog.build_markdown()
        cursor = self.editor.textCursor()
        if cursor.positionInBlock() != 0:
            cursor.insertText("\n")
        cursor.insertText(md + "\n")
        self.editor.setFocus()

    def insert_footnote(self) -> None:
        """Open FootnoteDialog; insert marker + append definition.

        The inline marker ``[^fn-N]`` is inserted at the caret and the
        matching definition ``[^fn-N]: ...`` is appended to the end of
        the buffer (footnote definitions may live anywhere; end-of-doc
        keeps the prose clean). The default id is the next sequential
        footnote suffix.
        """
        default_id = next_footnote_suffix(self.editor.toPlainText())
        dialog = FootnoteDialog(self, default_id=default_id)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        marker, definition = dialog.build_parts()
        cursor = self.editor.textCursor()
        cursor.insertText(marker)
        # Append the definition at the very end of the buffer.
        end = self.editor.textCursor()
        end.movePosition(QTextCursor.MoveOperation.End)
        current = self.editor.toPlainText()
        prefix = "" if current.endswith("\n\n") else (
            "\n" if current.endswith("\n") else "\n\n"
        )
        end.insertText(f"{prefix}{definition}\n")
        self.editor.setFocus()

    def insert_page_break(self) -> None:
        """Insert a ``[[pagebreak]]`` marker on its own line."""
        cursor = self.editor.textCursor()
        if cursor.positionInBlock() != 0:
            cursor.insertText("\n")
        cursor.insertText("[[pagebreak]]\n")
        self.editor.setFocus()

    def insert_index_marker(self, kind: str) -> None:
        """Insert a ``[[kind]]`` auto-index marker on its own line."""
        cursor = self.editor.textCursor()
        if cursor.positionInBlock() != 0:
            cursor.insertText("\n")
        cursor.insertText(f"[[{kind}]]\n")
        self.editor.setFocus()

    def insert_code_block(self) -> None:
        """Insert a fenced Python code block skeleton."""
        self._insert_template(snippets.CODE_BLOCK_TEMPLATE, "CODE")

    def insert_callout(self, kind: str = "note") -> None:
        """Insert a Quarto fenced callout, with title prompt if needed."""
        template = snippets.CALLOUT_TEMPLATES.get(
            kind, snippets.CALLOUT_TEMPLATES["note"]
        )
        if "TITLE" in template:
            title, ok = QInputDialog.getText(
                self, "Callout title", "Title:", text=kind.title(),
            )
            if ok and title:
                template = template.replace("TITLE", title)
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

    def bib_path(self) -> Path | None:
        """Return the resolved path of the linked .bib, or ``None``.

        Mirrors the resolution logic used to load the entries — the
        path comes from the ``bibliography:`` YAML field, resolved
        against the document's directory when relative. Existence is
        not enforced; the caller can use the result as the *target*
        of a write operation even when the file does not exist yet.
        """
        meta = snippets.parse_front_matter(self.editor.toPlainText())
        value = meta.get("bibliography")
        if not value:
            return None
        bib_path = Path(value)
        if not bib_path.is_absolute() and self._path is not None:
            bib_path = (self._path.parent / bib_path).resolve()
        return bib_path

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
        r"""Render synchronously via file:// to bypass setHtml's 2 MB cap.

        The HTML embeds the entire MathJax bundle inline (~2 MB) so
        equations render offline. ``setHtml`` truncates anything past
        2 MB, which left MathJax untyped and equations stuck as raw
        ``\[ … \]`` text. Writing to a per-tab temp file and using
        ``view.load()`` removes the cap. The ``<base href>`` tag in
        the rendered HTML still points at the document's directory,
        so relative figures, bib files and links resolve correctly.
        """
        self._render_into_view(paged=self._paged)

    def _render_into_view(
        self, *, paged: bool, page_size: str | None = None
    ) -> None:
        """Render the buffer into the preview, forcing ``paged`` state.

        Shared by the live preview (``_render_now``) and the PDF export
        path, which needs to force a non-paged render before printing.
        The page size comes from the document's ``page-size`` front
        matter (default Letter) unless ``page_size`` overrides it, so
        the preview sheet matches what the export will produce.

        Args:
            paged: Whether to render the paged-preview sheet.
            page_size: Explicit page-size key. ``None`` reads it from
                the buffer's front matter.
        """
        text = self.editor.toPlainText()
        if page_size is None:
            meta = snippets.parse_front_matter(text)
            page_size = normalize_page_size(meta.get("page-size"))
        base_dir = self._path.parent if self._path is not None else None
        title = (
            self._path.name if self._path is not None else UNTITLED
        )
        html = render_markdown(
            text,
            base_dir=base_dir,
            title=title,
            theme_css=self._theme_css,
            paged=paged,
            page_size=page_size,
        )
        if not hasattr(self, "_preview_tmp_dir"):
            self._preview_tmp_dir = Path(
                tempfile.mkdtemp(prefix="epy_mdr_preview_")
            )
        preview_path = self._preview_tmp_dir / "preview.html"
        preview_path.write_text(html, encoding="utf-8")
        self.view.load(QUrl.fromLocalFile(str(preview_path.resolve())))

    def cleanup_preview_tmp(self) -> None:
        """Delete the temp dir backing the live preview (call on close)."""
        tmp = getattr(self, "_preview_tmp_dir", None)
        if tmp is not None:
            shutil.rmtree(tmp, ignore_errors=True)
            self._preview_tmp_dir = None
