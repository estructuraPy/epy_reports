"""epy_mdr GUI: multi-tab Quarto/Markdown editor with PDF export."""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QMenu,
    QMessageBox,
    QStatusBar,
    QTabWidget,
    QToolBar,
    QToolButton,
)

from epy_mdr import bib, snippets, themes
from epy_mdr.renderer import render_markdown
from epy_mdr.tab import MarkdownTab

APP_NAME = "epy_mdr"

SUPPORTED_EXTENSIONS = {".md", ".markdown", ".qmd"}

FILE_FILTER = "Markdown / Quarto (*.md *.markdown *.qmd);;All files (*)"

WELCOME_TEXT = (
    "# epy_mdr\n\n"
    "A small **Quarto / Markdown** editor with live preview and "
    "one-click PDF export.\n\n"
    "## File\n\n"
    "- `Ctrl+N` — new tab\n"
    "- `Ctrl+O` — open a file (`.qmd`, `.md`, `.markdown`)\n"
    "- `Ctrl+S` — save (`Ctrl+Shift+S` to save as)\n"
    "- `Ctrl+W` — close the current tab\n"
    "- `F5`     — reload from disk (discards unsaved changes)\n\n"
    "## Text\n\n"
    "- `Ctrl+1` … `Ctrl+6` — heading levels H1–H6 on current line\n"
    "- `Ctrl+0` — strip heading on current line\n"
    "- `Ctrl+B` — **bold**\n"
    "- `Ctrl+I` — *italic*\n"
    "- `Ctrl+E` — `inline code`\n"
    "- `Ctrl+K` — link `[text](url)`\n\n"
    "## Elements\n\n"
    "- `Ctrl+Shift+H` — Section heading with `{#sec-...}` label\n"
    "- `Ctrl+Shift+F` — Figure with `{#fig-...}` label\n"
    "- `Ctrl+Shift+T` — Table with caption and `{#tbl-...}` label\n"
    "- `Ctrl+Shift+Q` — Display equation with `{#eq-...}` label\n"
    "- `Ctrl+Shift+K` — Fenced code block\n"
    "- `Ctrl+Shift+C` — Callout (note variant; more in Elements menu)\n\n"
    "## References\n\n"
    "- `Ctrl+R` — Open the cross-reference picker (`@label`)\n"
    "- `Ctrl+Shift+B` — Link a BibTeX file (writes `bibliography:` "
    "into the YAML front matter, Quarto-style)\n"
    "- Once linked, the *References* dropdown shows the buffer "
    "labels and a *Citations* submenu with every entry from "
    "the `.bib` — click to insert `@key`. The rendered preview "
    "and the PDF/HTML export add the bibliography at the end "
    "automatically via Pandoc's citeproc.\n\n"
    "## Export\n\n"
    "- `Ctrl+P`       — Export as PDF\n"
    "- `Ctrl+Shift+P` — Export as HTML\n"
    "- `Ctrl+Alt+P`   — Print\n\n"
    "> Drop `.qmd` / `.md` files anywhere on the window to open "
    "them as tabs.\n"
)


class MarkdownWindow(QMainWindow):
    """Main window: holds a tab bar with one MarkdownTab per file."""

    def __init__(self) -> None:
        """Build the tab widget, toolbar, menu, and welcome tab."""
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1280, 820)

        self.tabs = QTabWidget(self)
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.setDocumentMode(True)
        self.tabs.tabCloseRequested.connect(self._close_tab_at)
        self.tabs.currentChanged.connect(self._on_current_changed)
        self.setCentralWidget(self.tabs)
        self.setStatusBar(QStatusBar(self))

        self._build_actions()
        self._build_format_actions()
        self._build_insert_actions()
        self._build_menu()
        self._build_toolbar()
        # Every command lives in the toolbar dropdowns; hide the
        # legacy menu bar so we don't show two stacked top rows.
        self.menuBar().hide()

        self.setAcceptDrops(True)

        # Load persisted theme (defaults to EPY when nothing is saved).
        self._settings = QSettings("ANM Ingeniería", "epy_mdr")
        saved_theme = str(
            self._settings.value("theme", themes.DEFAULT_THEME_ID)
        )
        self._current_theme: themes.Theme = themes.get(saved_theme)
        self._apply_theme(self._current_theme.id, persist=False)

        self._open_welcome_tab()

    # ------------------------------------------------- actions/menus

    def _build_actions(self) -> None:
        """Create all QActions used by the menu and the toolbar."""
        self.act_new = QAction("New", self)
        self.act_new.setShortcut(QKeySequence.StandardKey.New)
        self.act_new.triggered.connect(self._new_tab)

        self.act_open = QAction("Open...", self)
        self.act_open.setShortcut(QKeySequence.StandardKey.Open)
        self.act_open.triggered.connect(self._open_dialog)

        self.act_save = QAction("Save", self)
        self.act_save.setShortcut(QKeySequence.StandardKey.Save)
        self.act_save.triggered.connect(self._save_current)

        self.act_save_as = QAction("Save As...", self)
        self.act_save_as.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.act_save_as.triggered.connect(self._save_current_as)

        self.act_reload = QAction("Reload", self)
        self.act_reload.setShortcut("F5")
        self.act_reload.triggered.connect(self._reload_current)

        self.act_close = QAction("Close Tab", self)
        self.act_close.setShortcut(QKeySequence.StandardKey.Close)
        self.act_close.triggered.connect(self._close_current_tab)

        self.act_pdf = QAction("Export as PDF...", self)
        self.act_pdf.setShortcut(QKeySequence("Ctrl+P"))
        self.act_pdf.triggered.connect(self._export_pdf)

        self.act_export_html = QAction("Export as HTML...", self)
        self.act_export_html.setShortcut(QKeySequence("Ctrl+Shift+P"))
        self.act_export_html.triggered.connect(self._export_html)

        self.act_print = QAction("Print...", self)
        self.act_print.setShortcut(QKeySequence("Ctrl+Alt+P"))
        self.act_print.triggered.connect(self._print_document)

        self.act_quit = QAction("Quit", self)
        self.act_quit.setShortcut(QKeySequence.StandardKey.Quit)
        self.act_quit.triggered.connect(self.close)

        # Theme actions (one per registered theme, exclusive group).
        self.theme_group = QActionGroup(self)
        self.theme_group.setExclusive(True)
        self.theme_actions: dict[str, QAction] = {}
        for theme in themes.THEMES.values():
            act = QAction(theme.display_name, self, checkable=True)
            act.setData(theme.id)
            self.theme_group.addAction(act)
            self.theme_actions[theme.id] = act
        self.theme_group.triggered.connect(
            lambda action: self._apply_theme(action.data())
        )

    def _on_active_tab(self, fn_name: str, *args) -> None:
        """Forward an action to the active tab if there is one."""
        tab = self._current_tab()
        if tab is None:
            return
        method = getattr(tab, fn_name)
        method(*args)

    def _build_format_actions(self) -> None:
        """Create text-formatting actions (headings, bold/italic, ...)."""
        self.heading_actions: list[QAction] = []
        for level in range(1, 7):
            act = QAction(f"Heading {level}", self)
            act.setShortcut(QKeySequence(f"Ctrl+{level}"))
            act.triggered.connect(
                lambda checked=False, lv=level: self._on_active_tab(
                    "set_heading_level", lv
                )
            )
            self.heading_actions.append(act)

        self.act_no_heading = QAction("Remove heading", self)
        self.act_no_heading.setShortcut(QKeySequence("Ctrl+0"))
        self.act_no_heading.triggered.connect(
            lambda: self._on_active_tab("set_heading_level", 0)
        )

        self.act_bold = QAction("Bold", self)
        self.act_bold.setShortcut(QKeySequence("Ctrl+B"))
        self.act_bold.triggered.connect(
            lambda: self._on_active_tab("toggle_bold")
        )

        self.act_italic = QAction("Italic", self)
        self.act_italic.setShortcut(QKeySequence("Ctrl+I"))
        self.act_italic.triggered.connect(
            lambda: self._on_active_tab("toggle_italic")
        )

        self.act_inline_code = QAction("Inline code", self)
        self.act_inline_code.setShortcut(QKeySequence("Ctrl+E"))
        self.act_inline_code.triggered.connect(
            lambda: self._on_active_tab("toggle_inline_code")
        )

        self.act_link = QAction("Link...", self)
        self.act_link.setShortcut(QKeySequence("Ctrl+K"))
        self.act_link.triggered.connect(
            lambda: self._on_active_tab("insert_link")
        )

    def _build_insert_actions(self) -> None:
        """Create block-insertion actions (figure/table/eq/callout)."""
        self.act_ins_section = QAction(
            "Section heading with label", self
        )
        self.act_ins_section.setShortcut(QKeySequence("Ctrl+Shift+H"))
        self.act_ins_section.triggered.connect(
            lambda: self._on_active_tab("insert_section_heading")
        )

        self.act_ins_figure = QAction("Figure", self)
        self.act_ins_figure.setShortcut(QKeySequence("Ctrl+Shift+F"))
        self.act_ins_figure.triggered.connect(
            lambda: self._on_active_tab("insert_figure")
        )

        self.act_ins_table = QAction("Table", self)
        self.act_ins_table.setShortcut(QKeySequence("Ctrl+Shift+T"))
        self.act_ins_table.triggered.connect(
            lambda: self._on_active_tab("insert_table")
        )

        self.act_ins_equation = QAction("Equation", self)
        self.act_ins_equation.setShortcut(QKeySequence("Ctrl+Shift+Q"))
        self.act_ins_equation.triggered.connect(
            lambda: self._on_active_tab("insert_equation")
        )

        self.act_ins_code_block = QAction("Code block", self)
        self.act_ins_code_block.setShortcut(QKeySequence("Ctrl+Shift+K"))
        self.act_ins_code_block.triggered.connect(
            lambda: self._on_active_tab("insert_code_block")
        )

        self.callout_actions: list[QAction] = []
        for kind in ("note", "tip", "warning", "important", "caution"):
            act = QAction(f"Callout: {kind.title()}", self)
            act.triggered.connect(
                lambda checked=False, k=kind: self._on_active_tab(
                    "insert_callout", k
                )
            )
            self.callout_actions.append(act)
        # Convenience: Ctrl+Shift+C inserts a basic note callout.
        self.callout_actions[0].setShortcut(QKeySequence("Ctrl+Shift+C"))

        self.act_cross_ref = QAction("Insert reference...", self)
        self.act_cross_ref.setShortcut(QKeySequence("Ctrl+R"))
        self.act_cross_ref.triggered.connect(
            lambda: self._on_active_tab("insert_cross_reference")
        )

        self.act_link_bib = QAction(
            "Link bibliography (.bib)...", self
        )
        self.act_link_bib.setShortcut(QKeySequence("Ctrl+Shift+B"))
        self.act_link_bib.triggered.connect(self._link_bibliography)

    def _build_menu(self) -> None:
        """Build content menus as plain ``QMenu`` objects.

        The toolbar reuses these objects via popup ``QToolButton``s,
        so we deliberately do NOT add them to the native menu bar —
        that would double the top chrome. The native menu bar is
        hidden once everything is built.
        """
        self.file_menu = QMenu("&File", self)
        self.file_menu.addAction(self.act_new)
        self.file_menu.addAction(self.act_open)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.act_save)
        self.file_menu.addAction(self.act_save_as)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.act_reload)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.act_close)
        self.file_menu.addAction(self.act_quit)

        self.text_menu = QMenu("&Text", self)
        heading_sub = self.text_menu.addMenu("Heading")
        for act in self.heading_actions:
            heading_sub.addAction(act)
        heading_sub.addSeparator()
        heading_sub.addAction(self.act_no_heading)
        self.text_menu.addSeparator()
        self.text_menu.addAction(self.act_bold)
        self.text_menu.addAction(self.act_italic)
        self.text_menu.addAction(self.act_inline_code)
        self.text_menu.addSeparator()
        self.text_menu.addAction(self.act_link)

        self.elements_menu = QMenu("&Elements", self)
        self.elements_menu.addAction(self.act_ins_section)
        self.elements_menu.addSeparator()
        self.elements_menu.addAction(self.act_ins_figure)
        self.elements_menu.addAction(self.act_ins_table)
        self.elements_menu.addAction(self.act_ins_equation)
        self.elements_menu.addSeparator()
        self.elements_menu.addAction(self.act_ins_code_block)
        callout_sub = self.elements_menu.addMenu("Callout")
        for act in self.callout_actions:
            callout_sub.addAction(act)

        self.references_menu = QMenu("&References", self)
        self.references_menu.aboutToShow.connect(
            self._populate_references_menu
        )
        self._populate_references_menu()

        self.export_menu = QMenu("E&xport", self)
        self.export_menu.addAction(self.act_pdf)
        self.export_menu.addAction(self.act_export_html)
        self.export_menu.addSeparator()
        self.export_menu.addAction(self.act_print)

        self.view_menu = QMenu("&View", self)
        theme_sub = self.view_menu.addMenu("Theme")
        for act in self.theme_group.actions():
            theme_sub.addAction(act)

    def _build_toolbar(self) -> None:
        """Toolbar: five dropdowns + reload."""
        bar = QToolBar("Main", self)
        bar.setMovable(False)
        self.addToolBar(bar)

        self._add_dropdown(bar, "File", self.file_menu)
        self._add_dropdown(bar, "Text", self.text_menu)
        self._add_dropdown(bar, "Elements", self.elements_menu)
        self._add_dropdown(bar, "References", self.references_menu)
        self._add_dropdown(bar, "Export", self.export_menu)
        self._add_dropdown(bar, "View", self.view_menu)

        bar.addSeparator()
        bar.addAction(self.act_reload)

    def _add_dropdown(
        self, bar: QToolBar, text: str, menu: QMenu
    ) -> None:
        """Add a popup-style QToolButton to ``bar`` that opens ``menu``."""
        btn = QToolButton(self)
        btn.setText(text)
        btn.setMenu(menu)
        btn.setPopupMode(
            QToolButton.ToolButtonPopupMode.InstantPopup
        )
        bar.addWidget(btn)

    # --------------------------------------------- references menu

    def _populate_references_menu(self) -> None:
        """Rebuild the References dropdown from the current buffer.

        The menu has three groups:

        * Buffer labels (figures / tables / equations / sections),
          grouped by kind.
        * Citations from the linked ``bibliography:`` file, when one
          is set in YAML front matter.
        * Actions to link a new ``.bib`` or open the cross-ref
          picker dialog.
        """
        menu = self.references_menu
        menu.clear()
        tab = self._current_tab()
        if tab is None:
            placeholder = menu.addAction("(no document open)")
            placeholder.setEnabled(False)
            menu.addSeparator()
            menu.addAction(self.act_link_bib)
            menu.addAction(self.act_cross_ref)
            return

        text = tab.text()
        labels = snippets.find_labels(text)
        bib_entries = tab.bib_entries()

        if not labels:
            placeholder = menu.addAction("(no labels in this file)")
            placeholder.setEnabled(False)
        else:
            groups: defaultdict[str, list[snippets.Label]] = (
                defaultdict(list)
            )
            for label in labels:
                groups[label.kind].append(label)
            for kind in ("fig", "tbl", "eq", "sec"):
                if kind not in groups:
                    continue
                title = (
                    snippets.KIND_DESCRIPTIONS.get(kind, kind) + "s"
                )
                sub = menu.addMenu(title)
                for label in groups[kind]:
                    act = sub.addAction(f"@{label.name}")
                    act.triggered.connect(
                        lambda checked=False, n=label.name:
                        self._insert_cross_ref_name(n)
                    )

        if bib_entries:
            menu.addSeparator()
            cite_sub = menu.addMenu(f"Citations ({len(bib_entries)})")
            for entry in bib_entries:
                act = cite_sub.addAction(entry.short_label())
                act.setToolTip(
                    f"{entry.type} — {entry.title}"
                    if entry.title
                    else entry.type
                )
                act.triggered.connect(
                    lambda checked=False, k=entry.key:
                    self._insert_cross_ref_name(k)
                )

        menu.addSeparator()
        menu.addAction(self.act_link_bib)
        menu.addAction(self.act_cross_ref)

    def _insert_cross_ref_name(self, name: str) -> None:
        """Insert ``@name`` at the active tab's caret."""
        tab = self._current_tab()
        if tab is None:
            return
        tab.editor.insertPlainText(f"@{name}")
        tab.editor.setFocus()

    # -------------------------------------------------------- themes

    def _apply_theme(self, theme_id: str, *, persist: bool = True) -> None:
        """Switch the application + every tab to ``theme_id``.

        Args:
            theme_id: Identifier from :data:`themes.THEMES`.
            persist: When ``True`` save the choice to QSettings so it
                survives between sessions. ``False`` is used during
                startup so we do not overwrite the same value.
        """
        theme = themes.get(theme_id)
        self._current_theme = theme
        app = QApplication.instance()
        if app is not None:
            themes.apply_palette(app, theme)
            app.setStyleSheet(themes.qss_for(theme))

        css = theme.to_css()
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if isinstance(widget, MarkdownTab):
                widget.set_theme_css(css)

        if theme.id in self.theme_actions:
            self.theme_actions[theme.id].setChecked(True)

        if persist:
            self._settings.setValue("theme", theme.id)
            self.statusBar().showMessage(
                f"Theme: {theme.display_name}", 2000
            )

    def _link_bibliography(self) -> None:
        """Pick a .bib file and write it into the YAML front matter."""
        tab = self._current_tab()
        if tab is None:
            return
        start = (
            str(tab.path.parent)
            if tab.path is not None
            else ""
        )
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Link bibliography",
            start,
            "BibTeX (*.bib);;All files (*)",
        )
        if not filename:
            return
        bib_path = Path(filename)
        tab.link_bibliography(bib_path)
        entries = bib.parse_bib_file(bib_path)
        self.statusBar().showMessage(
            f"Linked {bib_path.name} — {len(entries)} entries", 5000
        )

    # ----------------------------------------------- export helpers

    def _export_html(self) -> None:
        """Save the current preview as a standalone HTML file."""
        tab = self._current_tab()
        if tab is None:
            return
        default = (
            str(tab.path.with_suffix(".html"))
            if tab.path is not None
            else "untitled.html"
        )
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export HTML", default, "HTML (*.html *.htm)"
        )
        if not filename:
            return
        target = Path(filename)
        if target.suffix == "":
            target = target.with_suffix(".html")
        text = tab.editor.toPlainText()
        base_dir = tab.path.parent if tab.path is not None else None
        title = tab.path.name if tab.path is not None else "untitled"
        html = render_markdown(text, base_dir=base_dir, title=title)
        target.write_text(html, encoding="utf-8")
        self.statusBar().showMessage(f"Saved HTML: {target}", 3000)

    def _print_document(self) -> None:
        """Open the system print dialog for the current preview."""
        tab = self._current_tab()
        if tab is None:
            return
        from PySide6.QtPrintSupport import QPrintDialog, QPrinter

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)
        if dialog.exec() != QPrintDialog.DialogCode.Accepted:
            return
        # Keep ``printer`` alive while the async print finishes.
        self._active_printer = printer
        tab.view.page().print(
            printer,
            lambda _ok: setattr(self, "_active_printer", None),
        )

    # ----------------------------------------------- tab management

    def _open_welcome_tab(self) -> None:
        """Create the initial untitled tab shown at startup."""
        tab = self._create_tab()
        tab.set_initial_text(WELCOME_TEXT, path=None)

    def _create_tab(self) -> MarkdownTab:
        """Instantiate a new MarkdownTab and wire its signals."""
        tab = MarkdownTab(self)
        tab.set_theme_css(self._current_theme.to_css())
        tab.dirtyChanged.connect(
            lambda _flag, t=tab: self._refresh_tab_title(t)
        )
        tab.pathChanged.connect(lambda t=tab: self._refresh_tab_title(t))
        index = self.tabs.addTab(tab, tab.title())
        self.tabs.setCurrentIndex(index)
        return tab

    def _refresh_tab_title(self, tab: MarkdownTab) -> None:
        """Update the tab label and window title for ``tab``."""
        index = self.tabs.indexOf(tab)
        if index < 0:
            return
        self.tabs.setTabText(index, tab.title())
        if tab.path is not None:
            self.tabs.setTabToolTip(index, str(tab.path))
        if tab is self._current_tab():
            self._update_window_title()

    def _update_window_title(self) -> None:
        """Reflect the current tab's title in the main window."""
        tab = self._current_tab()
        if tab is None:
            self.setWindowTitle(APP_NAME)
            return
        self.setWindowTitle(f"{APP_NAME} — {tab.title()}")
        if tab.path is not None:
            self.statusBar().showMessage(str(tab.path))
        else:
            self.statusBar().clearMessage()

    def _current_tab(self) -> MarkdownTab | None:
        """Return the currently visible MarkdownTab, if any."""
        widget = self.tabs.currentWidget()
        if isinstance(widget, MarkdownTab):
            return widget
        return None

    def _on_current_changed(self, _index: int) -> None:
        """Refresh window title when the user switches tabs."""
        self._update_window_title()
        # The References dropdown depends on the active buffer; refresh
        # it so its initial state matches the visible tab.
        if hasattr(self, "references_menu"):
            self._populate_references_menu()

    # ------------------------------------------------- file actions

    def _new_tab(self) -> MarkdownTab:
        """Create an empty untitled tab and focus it."""
        tab = self._create_tab()
        tab.set_initial_text("", path=None)
        return tab

    def _open_dialog(self) -> None:
        """Show an open-file dialog and load selected files in tabs."""
        current = self._current_tab()
        start = (
            str(current.path.parent)
            if current is not None and current.path is not None
            else ""
        )
        filenames, _ = QFileDialog.getOpenFileNames(
            self, "Open document", start, FILE_FILTER
        )
        for filename in filenames:
            self.open_path(Path(filename))

    def open_path(self, path: Path) -> None:
        """Open ``path`` in a new tab, or focus the existing tab.

        If ``path`` is already open in some tab, the existing tab is
        focused instead of opening a duplicate. If the current tab is
        the welcome / untitled empty tab, it is reused.
        """
        if not path.is_file():
            QMessageBox.warning(self, APP_NAME, f"Not a file:\n{path}")
            return

        path = path.resolve()
        for i in range(self.tabs.count()):
            existing = self.tabs.widget(i)
            if (
                isinstance(existing, MarkdownTab)
                and existing.path is not None
                and existing.path.resolve() == path
            ):
                self.tabs.setCurrentIndex(i)
                return

        target = self._current_tab()
        if (
            target is None
            or target.path is not None
            or target.dirty
            or target.text().strip()
        ):
            target = self._create_tab()
        target.load_file(path)
        self._refresh_tab_title(target)

    def _save_current(self) -> bool:
        """Save the current tab, falling back to *Save As* if needed."""
        tab = self._current_tab()
        if tab is None:
            return False
        if tab.path is None:
            return self._save_current_as()
        tab.save()
        self._refresh_tab_title(tab)
        self.statusBar().showMessage(f"Saved: {tab.path}", 3000)
        return True

    def _save_current_as(self) -> bool:
        """Prompt for a target path and write the current tab there."""
        tab = self._current_tab()
        if tab is None:
            return False
        default = (
            str(tab.path)
            if tab.path is not None
            else "untitled.md"
        )
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save As", default, FILE_FILTER
        )
        if not filename:
            return False
        target = Path(filename)
        if target.suffix == "":
            target = target.with_suffix(".md")
        tab.save_as(target)
        self._refresh_tab_title(tab)
        self.statusBar().showMessage(f"Saved: {target}", 3000)
        return True

    def _reload_current(self) -> None:
        """Discard buffer changes and reload the current tab from disk."""
        tab = self._current_tab()
        if tab is None or tab.path is None:
            return
        if tab.dirty:
            choice = QMessageBox.question(
                self,
                "Reload",
                "Discard unsaved changes and reload from disk?",
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if choice != QMessageBox.StandardButton.Yes:
                return
        tab.reload()
        self.statusBar().showMessage(f"Reloaded: {tab.path}", 2000)

    def _export_pdf(self) -> None:
        """Export the current tab's preview to a PDF file."""
        tab = self._current_tab()
        if tab is None:
            return
        default = (
            str(tab.path.with_suffix(".pdf"))
            if tab.path is not None
            else "untitled.pdf"
        )
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export PDF", default, "PDF (*.pdf)"
        )
        if not filename:
            return
        target = Path(filename)
        if target.suffix == "":
            target = target.with_suffix(".pdf")
        self.statusBar().showMessage("Exporting PDF...", 0)
        tab.view.page().pdfPrintingFinished.connect(
            self._on_pdf_done,
            Qt.ConnectionType.SingleShotConnection,
        )
        tab.export_pdf(target)

    def _on_pdf_done(self, path: str, ok: bool) -> None:
        """Report the result of an asynchronous PDF export."""
        if ok:
            self.statusBar().showMessage(f"Saved PDF: {path}", 5000)
        else:
            self.statusBar().clearMessage()
            QMessageBox.warning(
                self, APP_NAME, f"Failed to write PDF:\n{path}"
            )

    # ------------------------------------------------ closing logic

    def _confirm_close(self, tab: MarkdownTab) -> bool:
        """Prompt how to handle a dirty tab. Returns False to abort."""
        if not tab.dirty:
            return True
        name = tab.path.name if tab.path is not None else "untitled.md"
        choice = QMessageBox.question(
            self,
            "Unsaved changes",
            f"'{name}' has unsaved changes. Save before closing?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if choice == QMessageBox.StandardButton.Save:
            self.tabs.setCurrentWidget(tab)
            return self._save_current()
        if choice == QMessageBox.StandardButton.Discard:
            return True
        return False

    def _close_tab_at(self, index: int) -> None:
        """Handle the close button on a specific tab."""
        widget = self.tabs.widget(index)
        if not isinstance(widget, MarkdownTab):
            return
        if not self._confirm_close(widget):
            return
        self.tabs.removeTab(index)
        widget.deleteLater()
        if self.tabs.count() == 0:
            self._open_welcome_tab()

    def _close_current_tab(self) -> None:
        """Close the active tab via the ``Ctrl+W`` shortcut."""
        index = self.tabs.currentIndex()
        if index >= 0:
            self._close_tab_at(index)

    def closeEvent(self, event) -> None:  # noqa: N802
        """Prompt to save every dirty tab before exiting."""
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if isinstance(widget, MarkdownTab) and not self._confirm_close(
                widget
            ):
                event.ignore()
                return
        event.accept()

    # -------------------------------------------------- drag & drop

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        """Accept drags that carry file URLs."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # noqa: N802
        """Open every dropped Markdown/Quarto file in its own tab."""
        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            if path.suffix.lower() in SUPPORTED_EXTENSIONS:
                self.open_path(path)


def _run_gui(files: list[str]) -> int:
    """Boot the Qt application and open ``files`` in tabs."""
    app = QApplication(sys.argv)
    window = MarkdownWindow()
    window.show()
    for raw in files:
        candidate = Path(raw)
        if candidate.exists():
            window.open_path(candidate)
    return app.exec()


def _run_register(make_default: bool) -> int:
    """Register the app for ``.md`` / ``.qmd`` on Windows."""
    from epy_mdr import winreg_assoc

    try:
        changes = winreg_assoc.register(make_default=make_default)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    for line in changes:
        print(line)
    print(
        f"\nDone. You can right-click a .md / .markdown / .qmd file "
        f"> Open with > {APP_NAME}."
    )
    if make_default:
        print(
            "\nWindows 10/11 will NOT honour a default app set from\n"
            "the registry alone — it requires you to confirm the\n"
            "choice in Settings (the UserChoice key is hash-signed\n"
            "and only Windows itself can produce a valid hash).\n"
            f"\nOpening Settings → Default apps for {APP_NAME}.\n"
            "Pick each extension (.md, .markdown, .qmd) and select\n"
            f"{APP_NAME} from the list."
        )
        winreg_assoc.open_default_apps_settings()
    return 0


def _run_set_default() -> int:
    """Open Settings → Default apps so the user can pick this app."""
    from epy_mdr import winreg_assoc

    if not winreg_assoc.open_default_apps_settings():
        print(
            "Could not open the Settings page. Open it manually: "
            "Settings → Apps → Default apps → search "
            f"{APP_NAME}.",
            file=sys.stderr,
        )
        return 2
    print(
        f"Opened Settings → Default apps. Pick .md / .markdown / "
        f".qmd and select {APP_NAME} from the list."
    )
    return 0


def _run_unregister() -> int:
    """Remove the file-association keys created by ``--register``."""
    from epy_mdr import winreg_assoc

    try:
        changes = winreg_assoc.unregister()
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if not changes:
        print("Nothing to remove.")
        return 0
    for line in changes:
        print(line)
    return 0


def _build_parser() -> argparse.ArgumentParser:
    """Build the top-level ``argparse`` parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog=APP_NAME,
        description=(
            "Quarto/Markdown editor and viewer with one-click "
            "PDF export."
        ),
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Quarto/Markdown files to open in tabs at startup.",
    )
    parser.add_argument(
        "--register",
        action="store_true",
        help=(
            f"Add an 'Open with {APP_NAME}' entry for .md, .markdown "
            "and .qmd on Windows (HKCU, no admin)."
        ),
    )
    parser.add_argument(
        "--as-default",
        action="store_true",
        help=(
            f"With --register, also set {APP_NAME} as the default "
            "program for the supported extensions."
        ),
    )
    parser.add_argument(
        "--unregister",
        action="store_true",
        help="Remove the keys created by --register.",
    )
    parser.add_argument(
        "--set-default",
        action="store_true",
        help=(
            "Open Settings → Default apps so you can pick "
            f"{APP_NAME} as the handler. Use this after --register "
            "since Windows requires user confirmation."
        ),
    )
    return parser


def _ensure_utf8_streams() -> None:
    """Force stdout/stderr to UTF-8 so non-ASCII help text works.

    PowerShell pipes default to cp1252 on Windows, which makes argparse
    crash when ``--help`` contains characters like ``->`` arrows or
    em-dashes. Reconfiguring the streams is harmless when they are
    already UTF-8 or when stdout is unavailable (frozen GUI).
    """
    import contextlib

    for stream in (sys.stdout, sys.stderr):
        if stream is None:
            continue
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        with contextlib.suppress(ValueError, OSError):
            reconfigure(encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    """Entry point for the ``epy_mdr`` console script."""
    _ensure_utf8_streams()
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.unregister:
        return _run_unregister()
    if args.register:
        return _run_register(make_default=args.as_default)
    if args.set_default:
        return _run_set_default()
    return _run_gui(args.files)


if __name__ == "__main__":
    raise SystemExit(main())
