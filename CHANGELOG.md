# Changelog

All notable changes to `epy_mdr` are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
