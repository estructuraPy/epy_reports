# Newmark — full-feature example

A real, publication-style document that exercises **every** epy_reports feature in
one file, so you can see what the editor produces end to end.

The document is a technical biography of **Nathan M. Newmark (1910–1981)**,
written in Spanish (`lang: es`). It uses:

- YAML front matter (`title`, `subtitle`, `author`, `abstract`, `date`)
- An IEEE bibliography (`bibliography: newmark.bib`, `csl: ieee`) with `@key`
  citations resolved by citeproc
- Quarto cross-references — `@sec-`, `@fig-`, `@eq-` — numbered and linked in
  the preview and every export, no Quarto install required
- Titled callouts (`callout-important`, `callout-note`)
- Figures with captions and width (`{#fig-portrait width=40%}`), including SVG
- Tables with captions
- Display equations (the Newmark-β time-integration method) typeset by MathJax

## Files

| File | Role |
|------|------|
| `newmark.md` | The source document |
| `newmark.bib` | BibTeX bibliography |
| `newmark_portrait.jpg`, `sdof.svg`, `beta_assumptions.svg` | Figures |
| `render_all_themes.py` | Renders the document once per theme to HTML + PDF |

## Render it across every theme

```bash
pip install -e ".[build]"   # from the repo root, once
cd examples/newmark
python render_all_themes.py
```

Output lands in `examples/newmark/_render/themes/` (git-ignored):
`newmark_<theme>.html` and `newmark_<theme>.pdf` for each of the nine themes —
`academic`, `classic`, `corporate`, `creative`, `handwritten`, `minimal`,
`professional`, `scientific`, `technical`.

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
