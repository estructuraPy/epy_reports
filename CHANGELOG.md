# Changelog

All notable changes to `epy_mdr` are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.0] — 2026-06-17

### Added
- **Page numbers in index blocks.** TOC, LOF, LOT and LOE entries now show the
  page number of the referenced content. Numbers are resolved via a two-pass
  PDF export: pass 1 extracts the anchor→page mapping from the PDF's named
  destinations (Qt WebEngine preserves HTML `id` attributes), pass 2 injects
  the numbers and re-exports.
- **6-cell running page header.** Documents can declare a `header:` list of up
  to 6 strings in YAML front matter. The header is stamped as a 2-row × 3-column
  grid (left / center / right columns) in the top margin of every page using
  a `reportlab` overlay — the same pipeline already used for footers.
- **Cover page isolation.** When `cover: true` is set, the cover page is
  excluded from the header and footer overlay (`start_page: 2`). The cover
  remains a standalone page with no running elements.

### Fixed
- **PDF page sizing.** The render script was using `paged=True` (preview mode),
  which produces a wide continuous layout unsuitable for `printToPdf`. Switched
  to `paged=False` so the page layout matches the app's own PDF export.
- **`{.unnumbered}` and other Pandoc class attributes leaked as literal text**
  in rendered headings and TOC entries. The heading scanner now strips all
  `{…}` attribute blocks from the collected text and merges any existing
  attributes with the injected `{#toc-h-N}` id into a single block so Pandoc
  parses it correctly.
- **IEEE (and all CSL) bibliography entries were split across two lines.** Pandoc
  generates `<div class="csl-left-margin">` (bracket number) and
  `<div class="csl-right-inline">` (reference text) as sibling block elements.
  Added `display: flex` on `div.csl-entry` so number and text appear side by
  side on the same line. `div.csl-indent` is also handled for APA/Chicago
  hanging-indent styles.

## [0.5.0] — 2026-06-17

### Added
- **Elements > Indexes** submenu with one-click insertion of all four index
  markers: Table of contents (`Ctrl+Shift+U`), List of figures, List of tables,
  List of equations. Previously these had to be typed manually.
- **Visible page breaks in paged view.** When Page view is active, `[[pagebreak]]`
  markers now render as a gray inter-page gap with a "page break" label — exactly
  like the space between sheets in Word or Google Docs. In normal mode and PDF
  export the element remains invisible (`break-after: page`).

### Changed
- Newmark example (`examples/newmark/`) updated to demonstrate the full
  publishing pipeline: cover page, TOC + LOF + LOT + LOE indexes, per-chapter
  `[[pagebreak]]` markers, two footnotes, Letter page size, footer and page
  numbers. The render script now outputs paged HTML and Letter-size PDFs.

## [0.4.1] — 2026-06-17

### Fixed
- Ubuntu `.deb` launcher now calls the system interpreter explicitly
  (`/usr/bin/python3`) so it no longer fails when a virtualenv without
  PySide6 is active on `PATH`.
- Pandoc code highlighting uses `--highlight-style`, which is accepted by
  both older pandoc (e.g. the `apt` package on Ubuntu) and pandoc 3.x, so
  exports work across the pandoc versions found on Windows and Ubuntu.

### Changed
- Installer docs: dropped `apt-get install -f` from the `.deb` steps
  (`dpkg -i` is sufficient; the `postinst` pip-installs the Python deps).

## [0.4.0] — 2026-06-17

### Added
- Auto-generated document indexes. Type a marker on its own line and it
  expands at render time (preview and every export): `[[toc]]` (table of
  contents), `[[lof]]` (list of figures), `[[lot]]` (list of tables),
  `[[loe]]` (list of equations). Entries reuse the existing cross-reference
  numbering and link to their anchors; titles are localized to the document
  `lang:` (English / Spanish).
- Page breaks via a `[[pagebreak]]` marker (Insert menu, `Ctrl+Shift+G`),
  rendered as a `break-after: page` element honored by the PDF export.
- PDF footers. When the front matter declares `footer:` text and/or
  `page-numbers: true`, every exported PDF page is stamped with the footer
  text and a localized "Page X of Y" / "Pág. X de Y" page number. Stamping
  uses `pypdf` + `reportlab` (both BSD-licensed).
- Footnote quick-insert dialog (Insert menu, `Ctrl+Shift+O`): enter the note
  text and it inserts the `[^fn-N]` reference plus its definition.
- Cover page. With `cover: true` the document opens with a dedicated cover
  page (optional company `logo:`, plus title, `subtitle:`, author and date)
  followed by a page break.
- Configuration templates. Save the current theme + publishing settings
  (CSL, footer, page numbers, cover, logo) as a named template and apply it
  to any document in one click (Templates menu). Templates are stored as
  JSON under the user config directory.
- Selectable page size via the `page-size:` front matter and a View > Page
  size menu (Letter — the default — A4, Legal). It drives both the exported
  PDF page layout and the page-view sheet.
- Page view: a View menu toggle (`Ctrl+Shift+A`) that previews the document
  as a paper sheet at the selected page size (width and margins). Preview
  only — the exported PDF is never affected by it.
- The image quick-insert (`Ctrl+Shift+I`) now prompts for the image width
  (default `80%`) so figures can be sized as they are inserted.
- The PDF export now waits for MathJax to finish typesetting and prints with
  an explicit page layout at the selected size, so equations render reliably
  in the output.

## [0.3.1] — 2026-06-11

### Added
- Cross-reference resolution in the preview and every export (HTML, PDF,
  DOCX): `@fig-`, `@tbl-`, `@eq-`, `@sec-` now render as linked
  "Figure 1", "Table 1", etc. instead of raw text. A lightweight
  preprocessor (`_resolve_crossrefs`) numbers definitions per kind and
  rewrites references before Pandoc, so no Quarto install or
  `pandoc-crossref` binary is required. Localized to the document `lang:`
  (English / Spanish). Real bibliography citations are left untouched.
- Dedicated **Reference ID** field in the table, figure and equation
  dialogs (new `FigureDialog`, `EquationDialog`). IDs are now short and
  independent of the caption (auto-numbered `fig-1`, `tbl-1`, `eq-1`,
  editable), replacing the previous caption-slug ids.
- `examples/sample.md` + `examples/sample_diagram.svg`: self-contained
  showcase document that exercises every editor feature (cross-refs,
  figures, tables, equations, callouts, code, citations) and renders
  cleanly out of the box.

### Fixed
- Equation cross-references now create a real anchor and do not leak
  their label. The closing `$$ {#eq-x}` is rewritten as
  `\tag{N} $$ []{#eq-x}`, where the trailing bracketed span becomes
  `<span id="eq-x"></span>` in the HTML, so `[Equation N](#eq-x)`
  links target an actual element. Previously the `{#eq-x}` token
  leaked as visible prose and `id="eq-x"` was never emitted.
- Table captions now render **above** the table (academic convention);
  figure captions remain below. Was a `caption-side: bottom` rule in the
  base stylesheet.

### Known limitations
- Cross-reference numbering is flat (Figure 1, 2, 3…), not chapter-scoped.
- In DOCX the reference text resolves correctly; internal hyperlinks and
  equation numbers may not be live Word fields.

## [0.3.0] — 2026-06-11

### Added
- `docs_bridge.py`: thin optional bridge to `epy_docs`; lazy imports keep
  epy_mdr fully functional when `epy_docs` is not installed.  Public API:
  `epy_docs_available()`, `list_layouts()`, `list_document_types()`,
  `render_document()`.  Raises `BridgeUnavailableError` on missing package.
- `docs_export_dialog.py`: `DocsExportDialog` — modal dialog with Layout /
  Document type combos, output-directory picker, PDF + HTML checkboxes, and
  `QSettings` persistence (`docs_layout`, `docs_doctype`, `docs_outdir`).
  `_RenderWorker` (QThread) runs the epy_docs render off the main thread.
- Export menu: new separator + **Export via epy_docs…** action; disabled with
  tooltip `"Requires the epy-docs package"` when `epy_docs` is absent.
- `tests/test_docs_bridge.py`: 8 pure-Python pytest tests covering
  availability detection, real `list_*` delegation, mocked
  `DocumentWriter` wiring, and `BridgeUnavailableError` error paths.
- `pyproject.toml`: optional extra `dev = ["pytest>=8.0"]`. The
  epy_docs backend is detected at runtime (commercial add-on, not on
  PyPI — no public extra to avoid dependency confusion).
- Windows (.exe, Inno Setup, per-user, registers `.md`/`.markdown`/`.qmd`
  associations) and Ubuntu (.deb) installers with CI workflow
  (`installer/`, `.github/workflows/installers.yml`).
- Theme-aware tonal UI: toolbar, status bar, menus, tab underline and
  hover tints derived from the active theme palette (all 9 layouts).
- Theme-preserving exports: HTML embeds the active theme CSS; DOCX uses
  a per-theme Word reference document (9 templates bundled) and keeps
  tango syntax highlighting in code chunks.
- Native DOCX export (`Ctrl+Shift+D`) via Pandoc with citeproc support.
- Table dialog (`Ctrl+Shift+T`): columns / rows / header / caption.
- Checklist dialog (`Ctrl+Shift+L`): item count + optional bold title.
- Insert image from file dialog; the image is copied into `figures/`.
- Official branding: app icon/logo from `assets_build/epy_mdr.png`;
  window/taskbar icon; Help > About dialog with author credit, mailto,
  LinkedIn and company links, and the ANM Ingeniería / estructuraPy
  logos.
- Guided step-by-step welcome tab with author credit.

### Fixed
- Frozen build: `assets/` subpackages importable in the .exe
  (importlib.resources), PyQt5/heavy-stack exclusions, themes and
  reference documents bundled explicitly.
- Installer: per-user shortcut folders (`autodesktop`/`autoprograms`)
  fix `IPersistFile::Save 0x80070005` on shortcut creation.
- Bumped version to `0.3.0`.

## [0.2.0] — 2026-06-09

### Added
- Initial public release as a standalone ePy Suite library.
- Multi-tab editor (`MarkdownWindow` + `MarkdownTab`) with drag-and-drop open
  for `.md`, `.markdown`, and `.qmd` files.
- Live HTML preview via Pandoc (`pypandoc-binary`).
- 9 layout presets in `assets/themes/`: academic, classic, corporate, creative,
  handwritten, minimal, professional, scientific, technical.
- BibTeX integration: link a `.bib`, auto-inject `bibliography:` into YAML front
  matter, `@key` citation picker, and cross-reference dialog
  (`{#sec-/fig-/tbl-/eq-}`).
- Snippets for section, figure, table, equation, fenced code, and callout.
- Export to PDF (`Ctrl+P`), HTML (`Ctrl+Shift+P`), and Print (`Ctrl+Alt+P`).
- PyInstaller packaging via `build.py` + `epy_mdr.spec` (frozen `.exe`).
- Optional Windows shell association via `winreg_assoc.py`.
- Persistent theme selection via `QSettings("ANM Ingeniería", "epy_mdr")`.
- Public entry points: `epy_mdr` (gui-script) and `python -m epy_mdr`.
