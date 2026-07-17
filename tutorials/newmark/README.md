# Newmark — full-feature example

A real, publication-style document that exercises **every** epy_reports feature in
one file, so you can see what the editor produces end to end.

The document is a technical biography of **Nathan M. Newmark (1910–1981)**,
available in English (`newmark.md`) and Spanish (`newmark_es.md`). It uses:

- YAML front matter (`title`, `subtitle`, `author`, `abstract`, `date`)
- An IEEE bibliography (`bibliography: newmark.bib`, `csl: ieee`) with `@key`
  citations resolved by citeproc
- Quarto cross-references — `@sec-`, `@fig-`, `@eq-` — numbered and linked in
  the preview and every export, no Quarto install required
- Titled callouts (`callout-important`, `callout-note`)
- Figures with captions and width (`{#fig-portrait width=40%}`), including SVG
- Tables with captions
- Display equations (the Newmark-β time-integration method) typeset by MathJax
- An interactive Plotly figure (`{.plotly fallback=figs/drift.png}`), a
  `::: {.verdict .pass}` banner, a `::: {.checklist}` block and inline
  `[PASS]{.badge .pass}` / `[FAIL]{.badge .fail}` status pills

## Files

| File | Role |
|------|------|
| `newmark.md` | The source document (English) |
| `newmark_es.md` | The same document in Spanish |
| `newmark.bib` | BibTeX bibliography |
| `newmark_portrait.jpg`, `sdof.svg`, `beta_assumptions.svg` | Figures |
| `figs/drift.png` | Static fallback for the interactive Plotly figure (PDF/DOCX export) |
| `render_all_themes.py` | Renders the document once per theme to HTML + PDF, in both languages |

## A note on the interactive figure (WebGL / PDF)

The verification section near the end of the report embeds a live Plotly.js
chart via a ```` ```{.plotly fallback=figs/drift.png} ```` fence. Plotly
renders bar/scatter charts like this one through WebGL canvases, which:

- **render correctly** in the live preview and in the HTML export (`Ctrl+Shift+P`)
  — the chart is fully interactive, including the `updatemenus` dropdown;
- **do not print** through Chromium's `printToPdf` (used for the paginated
  PDF export) or through Pandoc's DOCX writer — neither has a WebGL
  renderer. For those two exports, epy_reports substitutes the fence's
  declared `fallback=` image (`figs/drift.png`, generated once with
  matplotlib) instead of the live chart.

This is why every `{.plotly ...}` fence used for anything that might be
printed should declare a `fallback=` image; a fence without one stays
interactive in the PDF export "best effort" (the WebGL canvas is simply
absent from the printed page).

## Render it across every theme

```bash
pip install -e ".[build]"   # from the repo root, once
cd tutorials/newmark
python render_all_themes.py
```

Output lands in `tutorials/newmark/_render/themes/` (git-ignored):
`newmark_<theme>.html` and `newmark_<theme>.pdf` for each of the nine themes —
`academic`, `classic`, `corporate`, `creative`, `handwritten`, `minimal`,
`professional`, `scientific`, `technical`. Both languages are rendered: the
English files are `newmark_<theme>.*` and the Spanish ones carry an `_es` suffix
(`newmark_<theme>_es.*`).

Pre-rendered PDFs for all nine themes are attached to the
[latest release](https://github.com/estructuraPy/epy_reports/releases/latest) so
you can compare them without rendering locally.

## A note on typography

Each theme requests a specific set of fonts. Those fonts are applied **only
when the corresponding families are installed on the machine doing the
render**. On a PC that is missing a given family, Qt and Pandoc fall back to
the nearest available font, so the same document can look slightly different
from one computer to another. Everything else the theme defines — layout,
colors, spacing, heading hierarchy, callout styling — is stable across
machines; only the exact glyph shapes depend on locally available fonts.

## Languages / Idiomas

The report ships in **English** (`newmark.md`) and **Spanish** (`newmark_es.md`),
following the repo convention (`<name>.md` English, `<name>_es.md` Spanish).
`render_all_themes.py` renders both.

## Disclaimer / Aviso

This example is provided **for demonstration purposes only**. Its content
(historical, technical and numerical) is illustrative and has not been reviewed
in detail; it must not be used as a basis for engineering or any other
decisions. Provided as is, without warranty of any kind.

Este ejemplo se proporciona **únicamente con fines demostrativos**. Su contenido
(histórico, técnico y numérico) es ilustrativo y no ha sido revisado en detalle;
no debe usarse como base para decisiones de ingeniería ni de ningún otro tipo.
Se entrega tal cual, sin garantía de ningún tipo.
