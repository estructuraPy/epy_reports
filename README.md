# epy_mdr

Lightweight **Quarto / Markdown** editor with live preview, BibTeX-aware cross-references, snippets, and one-click PDF / HTML export. Standalone GUI of the **ePy Suite**.

## Features

| Area | What it does |
|------|--------------|
| Editor | Multi-tab, drag-and-drop open, `.md` / `.markdown` / `.qmd` |
| Preview | Live HTML preview via Pandoc (`pypandoc-binary`) |
| Themes | 9 layout presets — academic, classic, corporate, creative, handwritten, minimal, professional, scientific, technical |
| References | BibTeX `bibliography:` injection, `@key` picker, `{#sec-/fig-/tbl-/eq-}` cross-refs |
| Snippets | Section / figure / table / equation / code block / callout |
| Export | PDF (`Ctrl+P`), HTML (`Ctrl+Shift+P`), Print (`Ctrl+Alt+P`), epy_docs |
| Packaging | Frozen `.exe` build via PyInstaller (`build.py` + `epy_mdr.spec`) |
| Windows | Optional shell association via `winreg_assoc.py` |

## Install (dev)

```bash
pip install -e .
```

## Run

```bash
epy_mdr            # via gui-script entry point
python -m epy_mdr  # equivalent
```

## Build frozen .exe (Windows)

```bash
pip install -e ".[build]"
python build.py
# output -> dist/epy_mdr/epy_mdr.exe
```

## Export via epy_docs

The **Export → Export via epy_docs…** action renders the current document through
the [epy_docs](https://pypi.org/project/epy-docs/) typesetting engine, which
produces publication-quality PDF and HTML output using Quarto and corporate
layout templates.

**Requirements:** `epy_docs >= 0.2.0` and Quarto installed.  The action is
disabled (greyed out with a tooltip) when `epy_docs` is not found, so the
rest of the editor works without it.

**Install the optional backend:**

```bash
pip install -e ".[docs]"
# or
pip install epy-docs
```

**Dialog options:**

| Control | Default | Description |
|---------|---------|-------------|
| Layout | `corporate` | Any layout from `epy_docs.available_layouts()` |
| Document type | `report` | Any type from `epy_docs.available_document_types()` |
| Output directory | `<file-dir>/results` | Where the rendered files land |
| PDF / HTML | both checked | Select which formats to generate |

The last-used values persist in `QSettings` (`docs_layout`, `docs_doctype`,
`docs_outdir`).  The document must be saved before exporting; if there are
unsaved changes you will be prompted to save first.

## Key shortcuts

- `Ctrl+N` new · `Ctrl+O` open · `Ctrl+S` save · `Ctrl+W` close · `F5` reload
- `Ctrl+1`–`Ctrl+6` heading levels · `Ctrl+0` strip heading
- `Ctrl+B` bold · `Ctrl+I` italic · `Ctrl+E` code · `Ctrl+K` link
- `Ctrl+Shift+H/F/T/Q/K/C` section / figure / table / equation / fenced code / callout
- `Ctrl+R` cross-reference picker · `Ctrl+Shift+B` link `.bib`
- `Ctrl+P` PDF · `Ctrl+Shift+P` HTML · `Ctrl+Alt+P` print

## Project layout

```
src/epy_mdr/
├── __init__.py        ← __version__
├── __main__.py        ← python -m entrypoint
├── app.py             ← MarkdownWindow (main GUI)
├── tab.py             ← MarkdownTab (per-file editor + preview)
├── renderer.py        ← Pandoc bridge
├── template.py        ← HTML/PDF templates
├── themes.py          ← layout presets
├── themes_base.py     ← theme model
├── epyson.py          ← .epyson loader
├── bib.py             ← BibTeX parsing
├── snippets.py        ← editor snippets
├── xref_dialog.py     ← cross-reference picker
├── winreg_assoc.py    ← Windows shell association
└── assets/
    ├── style.css
    └── themes/*.epyson
```

## License

MIT — see [LICENSE](LICENSE).
