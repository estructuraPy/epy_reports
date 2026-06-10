# Changelog

All notable changes to `epy_mdr` are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] — 2026-06-10

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
- `pyproject.toml`: optional extras `docs = ["epy-docs>=0.2.0"]` and
  `dev = ["pytest>=8.0"]`.
- Windows installers and CI integration (built by the packaging stream;
  see `installer/` and `.github/`).
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
