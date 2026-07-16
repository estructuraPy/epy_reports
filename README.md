# epy_reports

Lightweight **Quarto / Markdown** editor with live preview, BibTeX-aware cross-references, snippets, and one-click PDF / HTML export. Standalone GUI of the **ePy Suite**.

## Download

Pre-built installers ship with every tagged release on the
**[Releases page](https://github.com/estructuraPy/epy_reports/releases/latest)** —
no Python toolchain required:

| Platform | Asset | Install |
|----------|-------|---------|
| Windows | `epy_reports-setup-<version>.exe` | Run the Inno Setup installer |
| Debian / Ubuntu | `epy-reports_<version>_all.deb` | `sudo dpkg -i epy-reports_<version>_all.deb` |

## Features

| Area | What it does |
|------|--------------|
| Editor | Multi-tab, drag-and-drop open, `.md` / `.markdown` / `.qmd` |
| Preview | Live HTML preview via Pandoc (`pypandoc-binary`) |
| Themes | 9 layout presets — academic, classic, corporate, creative, handwritten, minimal, professional, scientific, technical |
| References | BibTeX `bibliography:` injection, `@key` picker, `{#sec-/fig-/tbl-/eq-}` cross-refs resolved in preview & exports (Figure 1, Table 1, …) |
| Snippets | Section / figure / table / equation / code block / callout / two-column block / three-column block — each element gets a short editable Reference ID, separate from its caption |
| Export | PDF (`Ctrl+P`), HTML (`Ctrl+Shift+P`), DOCX (`Ctrl+Shift+D`), Print (`Ctrl+Alt+P`), epy_docs |
| Packaging | Frozen `.exe` build via PyInstaller (`build.py` + `epy_reports.spec`) |
| Windows | Optional shell association via `winreg_assoc.py` |

## Install (dev)

```bash
pip install -e .
```

## Run

```bash
epy_reports            # via gui-script entry point
python -m epy_reports  # equivalent
```

## Build frozen .exe (Windows)

```bash
pip install -e ".[build]"
python build.py
# output -> dist/epy_reports/epy_reports.exe
```

## Export via epy_docs (commercial add-on)

The **Export → Export via epy_docs…** action renders the current document
through the **epy_docs** typesetting engine, which produces
publication-quality PDF / HTML / DOCX output using Quarto and professional
layout templates.

epy_docs is a **commercial, privately distributed package by
[ANM Ingeniería](https://www.anmingenieria.com/)** — it is not available on
PyPI. epy_reports detects it at runtime: when it is not installed the action is
simply disabled (greyed out with a tooltip) and **every other feature of the
editor works normally**.

For licensing and access to the epy_docs backend contact
[ahnavarro@anmingenieria.com](mailto:ahnavarro@anmingenieria.com).

**Requirements (licensed users):** `epy_docs >= 0.2.0` and Quarto installed.

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
- `Ctrl+Shift+2` two-column block · `Ctrl+Shift+3` three-column block
- `Ctrl+R` cross-reference picker · `Ctrl+Shift+B` link `.bib`
- `Ctrl+P` PDF · `Ctrl+Shift+P` HTML · `Ctrl+Shift+D` DOCX · `Ctrl+Alt+P` print

## Theme-aware exports

HTML (`Ctrl+Shift+P`) and DOCX (`Ctrl+Shift+D`) exports preserve the active theme:

- **HTML** — the exported file embeds the same `:root { … }` CSS custom-property block
  used by the live preview, so fonts, heading colours, code backgrounds, and all other
  theme tokens are reproduced faithfully when the file is opened in a browser.

- **DOCX** — Pandoc is invoked with a `--reference-doc` argument pointing to a bundled
  Word template for the active theme (one `.docx` file per theme, stored under
  `_config/_assets/reference_docx/`).  The reference template carries the theme's fonts and
  paragraph styles, so headings and body text match the on-screen layout.  If a
  template file is missing the export falls back to Pandoc's default styles.

## Project layout

```
src/epy_reports/
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
└── _config/
    └── _assets/
        ├── style.css
        └── themes/*.epyson
```

## License

The epy_reports **source code** is MIT — see [LICENSE](LICENSE).

The bundled **brand images, layout themes and Word reference templates**
are proprietary assets of ANM Ingeniería, licensed only for use within
epy_reports; the bundled Pandoc executable is GPL and Qt is LGPL. See
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for the full picture.
