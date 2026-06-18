# Changelog

All notable changes to `epy_mdr` are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.10] — 2026-06-18

### Changed
- **The welcome manual now demonstrates the full publishing pipeline, not
  just the content types.** It opens with a real **cover page + logo**, a
  running **header**, a footer with page numbers, and populated
  **TOC / LOF / LOT / LOE** indexes — so the preloaded example shows
  everything epy_mdr can produce.
- **Screenshots added to the manual:** the editor (Markdown source + live
  preview + menu bar) and the Document properties dialog. They are bundled
  under `assets/screenshots/` and resolved to absolute URIs at load time
  (the welcome tab has no file path), so they render in the preview and the
  PDF export.

## [0.6.9] — 2026-06-18

### Added
- **Document properties dialog** (*Document ▸ Document properties…*,
  `Ctrl+Shift+Y`). A form to set the title block, cover page + logo, the
  running header (a 2×3 grid of cells), the footer, page numbers and page
  size — it reads the current YAML front matter and writes your changes
  back, so you no longer have to edit the front matter by hand.

### Fixed
- **`header:` front matter rendered as a single cell.** The list value was
  read as one literal string, so a 6-cell header printed the raw
  `["A", "B", …]` text in one box. It is now parsed into its cells
  (`snippets.parse_header_cells`), so the running-header grid renders
  correctly in the PDF.

### Changed
- The welcome manual now notes that task-list checkboxes are **interactive
  in the HTML export** and points to the new Document properties dialog.

## [0.6.8] — 2026-06-18

### Fixed
- **Enormous PDF margins.** The in-app PDF export still used a 30 mm
  printer margin on top of the 30 mm Paged.js `@page` margin, so exports
  printed with a 60 mm margin. The printer margin is now zero (Paged.js is
  the single source of the page margin), and that margin was trimmed from
  30 mm to a standard 25 mm.

### Changed
- **The preloaded welcome tab is now a full user manual.** It demonstrates
  every content type with its syntax and rendered result — front matter,
  formatting, lists/checklists, callouts, code, tables, figures, equations,
  cross-references, citations, footnotes and layout markers — and documents
  the **Python API** for driving epy_mdr without the GUI (`render_markdown`,
  `themes`, the `_pdf_footer` stamping helpers and the `docs_bridge`). The
  manual lives in `assets/welcome.md` so it can be edited as Markdown.

## [0.6.7] — 2026-06-18

### Changed
- **Footnotes now sit at the foot of the page where they are referenced.**
  PDF export is now paginated with Paged.js (bundled, MIT). Each Pandoc
  footnote becomes a `float: footnote` that Paged.js places at the bottom
  of its page with space reserved, so notes no longer interrupt the
  following paragraph (the previous inline-reflow behaviour) and never
  overlap the body. Paged.js honours the 30 mm `@page` margin on every
  page, so the printer margin is zero and the theme background still
  reaches the paper edges via `add_page_background`.

### Fixed
- **No more blank pages between the cover, the indexes and the body.**
  Page-break markers now use `break-before` (a marker stranded at the foot
  of a full page no longer spills onto a page of its own), and runs of
  adjacent page breaks — an index block's own break next to an explicit
  `[[pagebreak]]` — are collapsed into one.

### Internal
- Paged.js needs a laid-out viewport to measure content; the offscreen
  export view is now shown with `WA_DontShowOnScreen` so pagination works
  headlessly. `examples/newmark/render_all_themes.py` accepts an optional
  theme-id argument to render a single theme.

## [0.6.6] — 2026-06-18

### Fixed
- **PDF page margins are now actually painted with the theme color.** 0.6.5
  added `print-color-adjust: exact` so backgrounds print, but the PDF was
  still exported through a 15 mm printer margin (`QPageLayout`), and Chromium
  never paints that printer-margin band — so colored themes still had white
  edges. The export now prints with zero page margins (`@page { margin: 0 }`)
  so the web viewport fills the whole sheet and the background paints edge to
  edge; the visible content inset moved to the stylesheet's `@media print`
  body padding (30 mm), which clears the 15 mm footer/header overlays.
  Verified by sampling the exported PDF's corner pixels.

## [0.6.5] — 2026-06-18

### Fixed
- **Themed PDF page margins no longer print white.** The 0.6.2 change set
  the page background on the `html` root, but Chromium (and therefore Qt
  WebEngine's `printToPdf`) strips background colors in print output by
  default to save ink, so colored themes still exported with white
  margins. Added `print-color-adjust: exact` on the root — the property is
  inherited, so it forces every themed surface to paint. The full page,
  including the 15 mm physical margins, now carries the theme color.

## [0.6.4] — 2026-06-18

### Fixed
- **Ubuntu `.deb` install no longer fails under PEP 668.** On Debian 12+
  and Ubuntu 23.04+ the system Python is marked externally-managed, so
  the previous `postinst` step `pip3 install PySide6 pypdf reportlab`
  aborted with `externally-managed-environment` and left the package
  half-configured. The `postinst` now builds a dedicated virtual
  environment at `/usr/lib/epy-mdr/venv`, installs the pip-only runtime
  deps into it, and the `/usr/bin/epy-mdr` launcher runs from that venv.
  `python3-venv` is added to `Depends`, and a new `postrm` removes the
  venv on uninstall/purge.

## [0.6.3] — 2026-06-17

### Changed
- **Page numbers now appear only on content pages.** Cover and index
  pages (TOC / LOF / LOT / LOE) are treated as unnumbered front matter:
  page numbering restarts at "1" on the first content page and the
  "of Y" total counts only content pages, matching thesis/report
  convention. The first content page is detected from the PDF's named
  destinations — index blocks emit only links, so the smallest
  destination is the first body page. The index entries are offset by
  the same amount so the TOC numbers match the footer.
- **In-app PDF export is now a two-pass export.** The desktop app
  previously did a single pass and never resolved index page numbers;
  it now mirrors the example pipeline, so exports from the app also fill
  the TOC/LOF/LOT/LOE page numbers and number only content pages.

### Internal
- New shared helpers `renderer.inject_page_numbers` and
  `_pdf_footer.extract_anchor_pages` are the single source of truth for
  the two-pass page-number resolution, used by both the app export and
  the `examples/newmark` render script.

## [0.6.2] — 2026-06-17

### Fixed
- **PDF page margins now match the document background color.** Chromium/Qt
  WebEngine fills the physical paper margins using the `html` element's
  background, not `body`. Added `html { background: var(--bg) }` so colored
  themes (e.g. `technical` with `#F0F5FA`) no longer leave white strips at
  the page edges.

## [0.6.1] — 2026-06-17

### Fixed
- **Footnotes now appear on the page where they are referenced**, not at the
  end of the document. A JavaScript reflow script runs at `DOMContentLoaded`
  and moves each footnote's content into an inline `div.fn-inline-block`
  inserted immediately after the paragraph that contains the reference. In
  `@media print` (PDF export), the original `section.footnotes` is hidden so
  only the per-page inline versions are rendered. Screen view shows both.

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
