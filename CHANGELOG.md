# Changelog

All notable changes to `epy_reports` are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] — 2026-07-17

### Added
- **Unbreakable lists forwarding.** `docs_bridge.render_document()` accepts
  `keep_lists_together=True` (default) and forwards it to
  `epy_docs.DocumentWriter`: PDF exports keep bullet/numbered lists on one
  page — the whole list, with its intro line, moves to the next page instead
  of splitting. Requires epy_docs >= 1.1.0; affects PDF only (epy_docs DOCX
  templates keep lists together unconditionally).

## [0.2.0] — 2026-07-16

### Added
- **Plotly figures.** A ```` ```{.plotly ...} ```` fenced block renders as
  an interactive Plotly.js figure in the live preview and the continuous
  HTML export, themed automatically from the active document palette
  (author layout settings inside the fence always win over the derived
  theme defaults). `fallback=path/to/image.png` supplies a static image
  used for the paginated PDF export — WebGL canvases do not print
  reliably — and for the Word/DOCX export, which has no interactive
  renderer at all; `height=` sets the figure's CSS height (defaults to
  `420px`). Ships `plotly.js` v2.32.0 (MIT) as a bundled, offline asset,
  injected only into documents that actually use it.
- **Verdict banner, checklist and status pills.** `::: {.verdict
  .pass|.fail|.warn}` renders a headline PASS/FAIL/WARN banner; `:::
  {.checklist}` styles a task list as a review punch-list; `[text]{.badge
  .pass|.fail|.warn}` colors an inline status pill from the same
  pass/fail/warn palette (aliased to the callout tip/caution/warning
  colors via `--epy-pass`/`--epy-fail`/`--epy-warn`). Both new blocks
  join the *Insert ▸ Design block* picker alongside cards and big stats.
- **Graduated heading colors.** Every theme now computes `--h1-color`
  through `--h6-color` by mixing the theme's header color toward its
  muted text color (h1 boldest, h6 quietest), so the heading hierarchy
  reads as one coordinated ramp instead of six flat, identically
  colored levels.
- **Table and typography polish.** Table headers carry an accented
  underline (`--heading-rule`), numeric columns use `tabular-nums`, and
  a wide table is wrapped in a horizontally-scrolling `.table-wrap` box
  instead of overflowing the page or shrinking unreadably. Figure
  captions are now italicized and use a dedicated `--caption-color`
  variable. Callouts use an 8px border radius. The cover page carries a
  short accent bar under the title.
- **Sticky table of contents.** On a screen at least 1200px wide, the
  first `[[toc]]` block becomes a fixed left navigation rail (its dotted
  leaders and page-number column are hidden there); the paginated PDF
  export and the paged preview are unaffected.
- **Small-screen responsive tuning.** A `max-width: 640px` breakpoint
  tightens spacing and scales headings and table cells down for narrow
  viewports.

### Changed
- `build_html_document` gained a `plotly: bool` parameter (injected
  after the diagram block); the Plotly.js bundle and its
  `window._plotly_done` load gate — joined into the same wait condition
  as `window._mathjax_done` / `window._diagrams_done` — are only
  injected when the document actually contains an interactive figure.
- New runtime dependencies **plotly** (`>=5.15`) and **matplotlib**
  (`>=3.5`), used by the bundled tutorial example to generate a static
  figure fallback.

## [0.1.6] — 2026-06-27

### Fixed
- Live preview no longer crashes on a Pandoc conversion error; a stale
  deprecated CLI flag was also dropped.
- `export_docx` now strips YAML front matter before invoking Pandoc and
  passes document metadata (title/author/date) through explicitly.
- The academic layout's palette description no longer carries leftover
  third-party branding text.

### Changed
- Repository housekeeping: bundled assets moved under `_config/_assets`,
  build/release tooling consolidated under `_core/_packaging`, and a
  `housekeeper` tests-layout audit script was added.

## [0.1.5] — 2026-06-24

### Changed
- **Example footer.** The Newmark example footer now reads *ANM Ingeniería* in
  both languages (the English deck previously read "ANM Engineering").

## [0.1.4] — 2026-06-23

### Added
- **Insert ▸ Disclosure.** A typed disclosure note — AI assistance, document
  integrity, confidentiality or draft — inserted from the *Elements ▸ Disclosure*
  submenu and styled by the theme. The example report now carries an AI-use
  disclosure inserted with this block.
- **Adjustable page margin.** *Document properties ▸ Margin* sets the
  front-matter `margin:` key (a CSS length such as `20mm`, `1in` or a bare
  number read as millimetres). The same value drives the paged preview and
  the PDF `@page` margin, so the preview matches the export. Defaults to
  `25mm`.
- **Two-column and three-column content blocks.** *Elements ▸ Two-column
  block* (`Ctrl+Shift+2`) and *Elements ▸ Three-column block* (`Ctrl+Shift+3`)
  insert a Pandoc fenced-div layout (`:::: {.columns}` / `::: {.column
  width="…"}`). A dialog lets you set the column widths before inserting; the
  default is 50/50 and 33/33/34 respectively. The bundled CSS renders the
  blocks side by side in HTML and PDF output.

### Changed
- **HTML export is now continuous.** The exported HTML hides the print/page
  structure (page breaks and the page-number leaders in the indexes) so the
  document reads as one continuous web page. The PDF export is unchanged.

## [0.5.0] — 2026-06-18

### Added
- **Theme editor.** *View ▸ Theme ▸ New theme…* opens a full editor:
  clone any bundled theme, then set the base colors, the text/code fonts,
  the h1–h6 typography scale and the five callout colors, with a live
  preview. Everything else (the Qt chrome palette, syntax-highlighting
  colors, contrast) is derived automatically. Saved themes persist in the
  user config directory, appear next to the built-in ones in *View ▸
  Theme*, and can be edited or deleted from the same menu.
- **Section breaks with Roman / Arabic numbering.** `[[section-roman]]`
  and `[[section-arabic]]` (also under *Elements ▸ Section break*) force a
  page break and restart the page numbering in the chosen style — front
  matter in i, ii, iii and the body in 1, 2, 3, the classic academic
  convention.
- **Watermark.** A `watermark:` front-matter image (or the field in
  *Document properties*) is desaturated to grayscale and drawn faintly
  behind every page, so it never clashes with the document's colors.

### Changed
- New runtime dependency **Pillow** (grayscale watermark). The Ubuntu
  `.deb` installs it into its PEP 668-safe virtualenv.

## [0.4.4] — 2026-06-18

### Added
- **The Spanish manual shows Spanish screenshots.** Every screenshot in the
  user manual now matches the manual's language: the Spanish manual embeds
  Spanish captures of the editor and of all insertion dialogs (figure,
  table, equation, checklist, footnote, cross-reference, bibliography,
  Document properties). The loader resolves `*_es.png` variants for the
  Spanish manual automatically; the English manual is unchanged.

### Changed
- **Completed the Spanish localization of every dialog.** The bibliography
  entry dialog (all field labels, group titles, the required-fields hint
  and validation messages) and the epy_docs export dialog are now fully
  translated. Field placeholders and file-picker titles localize too.

## [0.4.3] — 2026-06-18

### Added
- **In-app language switcher (English / Spanish).** *View ▸ Language*
  switches the whole interface — menus, toolbar, dialogs — live, with no
  restart, and the choice is remembered across sessions. Built on a small
  dictionary-based translator (`_i18n.py`); English is the source language
  and untranslated strings fall back to it gracefully.
- **PDF exports embed document metadata.** Every exported PDF now carries
  its title, author, subject, keywords, creator/producer and a copyright
  notice in the PDF metadata, so authorship and rights travel with the
  file. The notice comes from a new `copyright:` front-matter key, or is
  derived as "© <year> <author>" when omitted.

### Changed
- **Templates now capture the full appearance.** A saved template stores
  the theme plus the running `header`, `footer`, `cover`, `logo`,
  `page-numbers`, `page-size` and `csl` — so a house style (header/footer
  layout and theme included) can be captured once and re-applied. Document
  content (title, author, date) is intentionally not stored.

## [0.4.2] — 2026-06-18

### Added
- **Bilingual user manual, openable from Help.** The bundled user manual
  now ships in English and Spanish. *Help ▸ User manual (English)* and
  *Help ▸ User manual (Spanish)* each open the full manual in a new tab,
  with its cover, logo, screenshots and figures resolved. (Replaces the
  earlier mini sample documents.)
- **Step-by-step "how to insert" guidance.** Every content type in the
  manual now documents exactly how to insert it — the menu path and the
  keyboard shortcut (e.g. *Elements ▸ Table*, `Ctrl+Shift+T`) — so the
  reader can reproduce it.
- **Screenshots of every insertion dialog.** The manual embeds captured
  screenshots of the figure, table, equation, checklist, footnote,
  cross-reference and bibliography-entry dialogs, generated from the real
  widgets.

### Changed
- The Spanish manual uses neutral/professional Spanish.



### Added
- **Sample documents in the Help menu.** *Help ▸ Open sample document
  (English / Spanish)* opens a bundled, self-contained example report
  (`assets/samples/`) in a new tab — a realistic starting point that
  exercises the cover page, headings, a captioned table, a cross-referenced
  equation, a callout, a code block, a footnote and a checklist. The
  Spanish sample (`lang: es`) also shows the localized cross-references and
  page-number wording.

## [0.4.0] — 2026-06-18

A consolidated release that folds the publishing pipeline into one
version. (Supersedes the same-day 0.4.0-0.6.10 point releases.)

### PDF export
- Paginated with **Paged.js** (bundled, MIT): **footnotes sit at the foot
  of the page** where they are referenced, with their space reserved so
  they never overlap the body.
- The **theme page background prints edge to edge** (a full-sheet backdrop
  is drawn behind every page); consistent 25 mm page margins.
- Cover page with logo, a 2x3 running **header**, a footer with localized
  **"Page X of Y"**, and selectable page size (Letter / A4 / Legal).
- Auto-generated **TOC / LOF / LOT / LOE** indexes with resolved page
  numbers (two-pass export).

### Authoring
- **Document properties dialog** (*Document ▸ Document properties…*,
  `Ctrl+Shift+Y`): a form for the title block, cover + logo, header cells,
  footer, page numbers and page size that writes the YAML front matter.
- Cross-references (`@fig-`/`@tbl-`/`@eq-`/`@sec-`), citations (BibTeX +
  CSL: IEEE/APA/Chicago), five callout types, tables/figures/equations
  with captions, footnotes, task lists (interactive in HTML export) and
  syntax-highlighted code.
- Nine themes; HTML / PDF / DOCX export; optional epy_docs backend.

### Packaging & docs
- Windows (`.exe`, per-user) and Ubuntu (`.deb`) installers; the `.deb`
  builds an isolated virtualenv for its runtime deps (PEP 668-safe).
- The preloaded welcome tab is a full **user manual** that demonstrates
  every content type with its syntax, documents the Python API, and
  includes screenshots of the editor and the Document properties dialog.

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
  epy_reports fully functional when `epy_docs` is not installed.  Public API:
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
- Official branding: app icon/logo from `assets_build/epy_reports.png`;
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
- PyInstaller packaging via `build.py` + `epy_reports.spec` (frozen `.exe`).
- Optional Windows shell association via `winreg_assoc.py`.
- Persistent theme selection via `QSettings("ANM Ingeniería", "epy_reports")`.
- Public entry points: `epy_reports` (gui-script) and `python -m epy_reports`.
