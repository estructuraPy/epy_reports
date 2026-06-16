"""Render Quarto / Pandoc Markdown to a styled HTML document.

The actual conversion is delegated to Pandoc (bundled by
``pypandoc-binary``). A small Quarto preprocessor expands titled
fenced callouts so they render with a visible header. A second
preprocessor resolves Quarto-style cross-references
(``@fig-x``, ``@tbl-x``, ``@eq-x``, ``@sec-x``) before Pandoc
sees the source, so they render correctly even without a Quarto
installation.
"""

from __future__ import annotations

import re
import shutil
import tempfile
from pathlib import Path

import pypandoc

from epy_mdr.snippets import parse_front_matter
from epy_mdr.template import build_html_document

PANDOC_FORMAT = (
    "markdown"
    "+fenced_divs"
    "+bracketed_spans"
    "+fenced_code_attributes"
    "+link_attributes"
    "+inline_code_attributes"
    "+definition_lists"
    "+tex_math_dollars"
    "+tex_math_single_backslash"
    "+inline_notes"
    "+yaml_metadata_block"
    "+pipe_tables"
    "+grid_tables"
    "+raw_html"
    "+raw_attribute"
    "+implicit_figures"
    "+task_lists"
    "+fancy_lists"
    "+startnum"
    "+example_lists"
    "+citations"
    "+abbreviations"
    "+smart"
    "+autolink_bare_uris"
    "+strikeout"
    "+subscript"
    "+superscript"
)

PANDOC_ARGS = [
    "--mathjax",
    "--syntax-highlighting=tango",
    "--section-divs",
    "--wrap=preserve",
]

CALLOUT_KINDS = ("note", "tip", "warning", "important", "caution")


_CALLOUT_OPEN_RE = re.compile(
    r"^:::+\s*\{\.callout-(?P<kind>"
    + "|".join(CALLOUT_KINDS)
    + r")"
    r"(?:\s+(?P<attrs>[^}]*))?\}\s*$",
    re.MULTILINE,
)

_TITLE_ATTR_RE = re.compile(r'title="([^"]*)"')


def _resolve_doc_path(value: str, base_dir: Path | None) -> Path | None:
    """Resolve a path declared in YAML metadata.

    ``value`` is interpreted relative to ``base_dir`` (the directory of
    the .qmd file) unless it is absolute. Returns ``None`` when the
    resolved path does not exist on disk.
    """
    candidate = Path(value)
    if not candidate.is_absolute() and base_dir is not None:
        candidate = (base_dir / candidate).resolve()
    return candidate if candidate.is_file() else None


def _bibliography_args(
    metadata: dict[str, str], base_dir: Path | None
) -> list[str]:
    """Build the ``--citeproc`` / ``--bibliography`` Pandoc arguments.

    If the YAML front matter declares ``bibliography`` and the file
    resolves on disk, citeproc is enabled. ``csl`` is optional.
    """
    bib_value = metadata.get("bibliography")
    if not bib_value:
        return []
    bib_path = _resolve_doc_path(bib_value, base_dir)
    if bib_path is None:
        return []
    extra: list[str] = [
        "--citeproc",
        f"--bibliography={bib_path}",
    ]
    csl_value = metadata.get("csl")
    if csl_value:
        csl_path = _resolve_doc_path(csl_value, base_dir)
        if csl_path is not None:
            extra.append(f"--csl={csl_path}")
    return extra


def _expand_quarto_callouts(source: str) -> str:
    """Rewrite Quarto-titled callouts into nested Pandoc fenced divs.

    Quarto allows::

        ::: {.callout-note title="Heads up"}
        body
        :::

    Pandoc's ``fenced_divs`` keeps ``title`` only as an HTML attribute,
    so the heading would not be visible. We rewrite the opening fence
    into nested divs (``callout`` + ``callout-titled`` + an inner
    ``callout-title`` div containing the title text) and let CSS take
    care of the styling.
    """

    def replace(match: re.Match[str]) -> str:
        kind = match.group("kind")
        attrs = match.group("attrs") or ""
        title_match = _TITLE_ATTR_RE.search(attrs)
        classes = f".callout .callout-{kind}"
        if not title_match:
            return f"::: {{{classes}}}"
        title_text = title_match.group(1).strip()
        return (
            f"::: {{{classes} .callout-titled}}\n"
            f"::: {{.callout-title}}\n"
            f"{title_text}\n"
            f":::"
        )

    return _CALLOUT_OPEN_RE.sub(replace, source)


# ---------------------------------------------------------------------------
# Cross-reference resolver
# ---------------------------------------------------------------------------

# Matches a Quarto label definition like {#fig-x} or {#tbl-y width=80%}.
_XREF_DEF_RE = re.compile(
    r"\{#(?P<label>(?P<kind>fig|tbl|eq|sec)-[A-Za-z0-9_-]+)[^}]*\}"
)

# Matches a cross-reference like @fig-x, @tbl-y, @eq-z, @sec-w.
# Deliberately restricted to the four Quarto kinds so that bibliography
# citations like @navarro2020 pass through unchanged.
_XREF_REF_RE = re.compile(
    r"@(?P<label>(?:fig|tbl|eq|sec)-[A-Za-z0-9_-]+)"
)

# Figure caption: ![CAP](path){#fig-x ...}
_FIG_CAP_RE = re.compile(
    r"(!\[)((?!(?:[A-Z][a-záéíóúüñA-Z]+ )+\d+:)[^]]*)"
    r"(\]\([^)]*\)\{#(?P<label>fig-[A-Za-z0-9_-]+)[^}]*\})"
)

# Table caption: `: CAP {#tbl-x ...}`  (Pandoc table caption syntax)
_TBL_CAP_RE = re.compile(
    r"^(:\s+)((?!(?:[A-Z][a-záéíóúüñA-Z]+ )+\d+:).+?)"
    r"(\s+\{#(?P<label>tbl-[A-Za-z0-9_-]+)[^}]*\}\s*)$"
)

# Equation block closing: optional whitespace before `$$` then `{#eq-x}`
# Handles both  `$$ {#eq-x}`  and  `$$  {#eq-x}`  on the same line.
_EQ_CLOSE_RE = re.compile(
    r"(\$\$)\s+(\{#(?P<label>eq-[A-Za-z0-9_-]+)[^}]*\})"
)

# Localised words for the four kinds.
_WORDS: dict[str, dict[str, str]] = {
    "en": {
        "fig": "Figure",
        "tbl": "Table",
        "eq": "Equation",
        "sec": "Section",
    },
    "es": {
        "fig": "Figura",
        "tbl": "Tabla",
        "eq": "Ecuación",
        "sec": "Sección",
    },
}

# Fence-start / end detector (``` or ~~~, any leading spaces).
_FENCE_RE = re.compile(r"^\s*(```|~~~)")

# Standalone display-math delimiter: a line with only $$ (and whitespace).
_DMATH_LINE_RE = re.compile(r"^\s*\$\$\s*$")

# One or more backtick runs — used to strip inline code spans.
_INLINE_CODE_RE = re.compile(r"`+[^`]*`+")


def _strip_code_spans(text: str) -> list[tuple[str, bool]]:
    """Split *text* into ``(segment, is_code)`` pairs.

    Non-code segments are the prose the resolver may transform; code
    segments must be returned verbatim.
    """
    result: list[tuple[str, bool]] = []
    last = 0
    for m in _INLINE_CODE_RE.finditer(text):
        if m.start() > last:
            result.append((text[last : m.start()], False))
        result.append((m.group(), True))
        last = m.end()
    if last < len(text):
        result.append((text[last:], False))
    return result


def _resolve_crossrefs(source: str, lang: str = "en") -> str:
    """Resolve Quarto cross-references in *source* before Pandoc sees it.

    Scans for ``{#fig-x}``, ``{#tbl-x}``, ``{#eq-x}``, ``{#sec-x}``
    label definitions and assigns sequential numbers per kind. Then
    prefixes figure/table captions and equation tags at definition sites
    and replaces ``@fig-x`` / ``@tbl-x`` / ``@eq-x`` / ``@sec-x``
    references with ``[Word N](#label)`` links.

    Only the four Quarto cross-ref prefixes are touched — bibliography
    citations (``@author2020``) pass through unchanged. Content inside
    fenced code blocks (``` / ~~~) and inline code spans is never
    transformed.

    Args:
        source: Raw Markdown / Quarto source text.
        lang: Two-letter BCP-47 language tag. ``"es"`` selects Spanish
            caption words; anything else uses English.

    Returns:
        Preprocessed source with numbered captions and resolved refs.
    """
    lang_key = lang[:2].lower() if lang else "en"
    words = _WORDS.get(lang_key, _WORDS["en"])

    # ------------------------------------------------------------------
    # PASS A — number every label definition in document order.
    # Definitions inside fenced code blocks are skipped.
    # ------------------------------------------------------------------
    numbers: dict[str, int] = {}
    counters: dict[str, int] = {"fig": 0, "tbl": 0, "eq": 0, "sec": 0}

    lines = source.splitlines(keepends=True)
    in_fence = False
    for line in lines:
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for m in _XREF_DEF_RE.finditer(line):
            label = m.group("label")
            kind = m.group("kind")
            if label not in numbers:
                counters[kind] += 1
                numbers[label] = counters[kind]

    # ------------------------------------------------------------------
    # PASS B + C — transform lines outside fenced blocks.
    # For each non-fence line: protect inline-code spans, apply caption
    # prefixing (B) and reference replacement (C) only to prose parts.
    # ------------------------------------------------------------------

    def _prefix_fig(line: str) -> str:
        """Prefix figure captions at their definition site."""

        def repl(m: re.Match[str]) -> str:
            label = m.group("label")
            n = numbers.get(label)
            if n is None:
                return m.group(0)
            word = words["fig"]
            return f"{m.group(1)}{word} {n}: {m.group(2)}{m.group(3)}"

        return _FIG_CAP_RE.sub(repl, line)

    def _prefix_tbl(line: str) -> str:
        """Prefix table captions at their definition site."""

        def repl(m: re.Match[str]) -> str:
            label = m.group("label")
            n = numbers.get(label)
            if n is None:
                return m.group(0)
            word = words["tbl"]
            return (
                f"{m.group(1)}{word} {n}: {m.group(2)}{m.group(3)}"
            )

        return _TBL_CAP_RE.sub(repl, line)

    def _replace_refs(text: str) -> str:
        """Replace @kind-label refs with [Word N](#label) links."""

        def repl(m: re.Match[str]) -> str:
            label = m.group("label")
            n = numbers.get(label)
            if n is None:
                return m.group(0)  # unknown label — leave raw
            kind = label.split("-", 1)[0]
            word = words[kind]
            return f"[{word} {n}](#{label})"

        return _XREF_REF_RE.sub(repl, text)

    def _transform_prose(text: str) -> str:
        """Apply ref replacement to prose, preserving inline code."""
        parts = _strip_code_spans(text)
        out: list[str] = []
        for segment, is_code in parts:
            out.append(segment if is_code else _replace_refs(segment))
        return "".join(out)

    # State for equation block tracking (detect pre-existing \tag).
    # eq_state[0] = True  →  current eq block already has a \tag.
    # Reset on each opening $$ line (outside a fence).
    eq_state = [False]  # mutable so nested _tag_eq can read it

    def _tag_eq(line: str) -> str:
        r"""Inject ``\tag{N}`` and an anchor span on the eq closing line.

        Replaces ``$$ {#eq-x}`` with ``\tag{N} $$ []{#eq-x}``. The
        bracketed span (``+bracketed_spans``) becomes
        ``<span id="eq-x"></span>`` in the rendered output, so prose
        references like ``[Equation N](#eq-x)`` resolve to a real
        anchor. Without it the label would leak as visible text and
        the link target would not exist.
        """

        def repl(m: re.Match[str]) -> str:
            label = m.group("label")
            n = numbers.get(label)
            if n is None:
                return m.group(0)
            anchor = f"[]{{#{label}}}"
            if eq_state[0]:
                # \tag already in the body — only inject the anchor.
                return f"{m.group(1)} {anchor}"
            return f"\\tag{{{n}}} {m.group(1)} {anchor}"

        return _EQ_CLOSE_RE.sub(repl, line)

    out_lines: list[str] = []
    in_fence = False
    in_eq_block = False
    for line in lines:
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            out_lines.append(line)
            continue
        if in_fence:
            out_lines.append(line)
            continue
        # Track display-math blocks to detect pre-existing \tag.
        if _DMATH_LINE_RE.match(line):
            if not in_eq_block:
                # Opening $$ — reset block tag state.
                in_eq_block = True
                eq_state[0] = False
            else:
                in_eq_block = False
        elif in_eq_block and "\\tag{" in line:
            eq_state[0] = True
        # Apply caption prefixes (operate on the full line; labels are
        # not inside inline-code spans in practice, and the regexes are
        # specific enough not to mis-fire on code-looking prose).
        line = _prefix_fig(line)
        line = _prefix_tbl(line)
        line = _tag_eq(line)
        # Replace prose references, protecting inline code spans.
        line = _transform_prose(line)
        out_lines.append(line)

    return "".join(out_lines)


_SVG_IMG_RE = re.compile(
    r"(!\[[^\]]*\]\()([^)\s]+?\.svg)(\)[^\n]*)"
)


def _rasterize_svgs_for_docx(
    source: str, base_dir: Path | None
) -> tuple[str, Path | None]:
    """Convert ``![alt](*.svg)`` refs into PNG copies in a temp dir.

    Pandoc's DOCX writer needs ``rsvg-convert`` on PATH to embed SVG
    images and silently drops them otherwise. Render each referenced
    SVG into a high-resolution PNG via Qt's bundled SVG renderer
    (already a dependency through PySide6) and rewrite the source to
    point at the PNG. The caller is responsible for removing the temp
    directory after Pandoc finishes.
    """
    if base_dir is None or "!" not in source:
        return source, None
    from PySide6.QtCore import QSize  # noqa: PLC0415
    from PySide6.QtGui import QImage, QPainter  # noqa: PLC0415
    from PySide6.QtSvg import QSvgRenderer  # noqa: PLC0415

    tmp_dir = Path(tempfile.mkdtemp(prefix="epy_mdr_svg_"))

    def repl(match: re.Match[str]) -> str:
        prefix, ref, suffix = match.group(1), match.group(2), match.group(3)
        svg_path = (base_dir / ref).resolve()
        if not svg_path.is_file():
            return match.group(0)
        png_path = tmp_dir / (svg_path.stem + ".png")
        try:
            renderer = QSvgRenderer(str(svg_path))
            default = renderer.defaultSize()
            scale = 3  # ~300 DPI raster for crisp print
            size = QSize(default.width() * scale, default.height() * scale)
            image = QImage(size, QImage.Format.Format_ARGB32_Premultiplied)
            image.fill(0xFFFFFFFF)
            painter = QPainter(image)
            renderer.render(painter)
            painter.end()
            image.save(str(png_path), "PNG")
        except Exception:
            return match.group(0)
        return f"{prefix}{png_path.as_posix()}{suffix}"

    return _SVG_IMG_RE.sub(repl, source), tmp_dir


def export_docx(
    source: str,
    target: Path,
    base_dir: Path | None = None,
    reference_doc: Path | None = None,
) -> None:
    """Convert Quarto/Pandoc Markdown ``source`` to a ``.docx`` file.

    The pipeline is:

    1. ``_expand_quarto_callouts`` — rewrite titled callout fences.
    2. ``_resolve_crossrefs`` — number and link ``@fig-x`` / ``@tbl-x``
       / ``@eq-x`` / ``@sec-x`` cross-references so they survive Pandoc
       without a Quarto installation.
    3. ``pypandoc.convert_text`` — the actual Markdown → DOCX conversion.

    Args:
        source: Markdown text. Quarto YAML front matter and fenced
            callouts are supported; a linked ``bibliography:`` enables
            citeproc just like the HTML preview.
        target: Destination ``.docx`` path (written by Pandoc).
        base_dir: Directory used to resolve relative image paths.
        reference_doc: Optional Word reference document whose styles
            (fonts, colors, heading levels) Pandoc will copy into the
            output.  When ``None`` or when the file does not exist the
            export proceeds with Pandoc's default styles.
    """
    metadata = parse_front_matter(source)
    lang = metadata.get("lang", "en")
    prepared = _expand_quarto_callouts(source)
    prepared = _resolve_crossrefs(prepared, lang=lang)
    prepared, svg_tmp = _rasterize_svgs_for_docx(prepared, base_dir)

    # tango matches the HTML preview so code chunks keep colored
    # tokens in Word; the reference-doc supplies the monospace
    # "Source Code" paragraph style.
    extra_args = ["--wrap=preserve", "--syntax-highlighting=tango"]
    if base_dir is not None:
        extra_args.append(f"--resource-path={base_dir}")
        if svg_tmp is not None:
            extra_args.append(f"--resource-path={svg_tmp}")
    extra_args += _bibliography_args(metadata, base_dir)
    if reference_doc is not None and reference_doc.is_file():
        extra_args.append(f"--reference-doc={reference_doc}")

    try:
        pypandoc.convert_text(
            prepared,
            to="docx",
            format=PANDOC_FORMAT,
            outputfile=str(target),
            extra_args=extra_args,
        )
    finally:
        if svg_tmp is not None:
            shutil.rmtree(svg_tmp, ignore_errors=True)


def render_markdown(
    source: str,
    base_dir: Path | None = None,
    *,
    title: str = "epy_mdr",
    theme_css: str = "",
) -> str:
    """Render Quarto/Pandoc Markdown ``source`` to a full HTML page.

    The pipeline is:

    1. ``_expand_quarto_callouts`` — rewrite titled callout fences.
    2. ``_resolve_crossrefs`` — number and link ``@fig-x`` / ``@tbl-x``
       / ``@eq-x`` / ``@sec-x`` cross-references so they survive Pandoc
       without a Quarto installation.
    3. ``pypandoc.convert_text`` — the actual Markdown → HTML5 conversion.

    Args:
        source: Markdown text. Quarto YAML front matter and fenced
            callouts are supported.
        base_dir: Directory used as the HTML ``<base>`` so relative
            paths to images and links resolve correctly.
        title: Fallback document title. Overridden by ``title:`` in
            YAML front matter when present.
        theme_css: Optional ``:root { … }`` block that overrides the
            base stylesheet's custom properties — supplied by the
            active visual theme.

    Returns:
        A standalone HTML5 document ready for the preview pane or to
        be written to disk.
    """
    metadata = parse_front_matter(source)
    if metadata.get("title"):
        title = metadata["title"]

    lang = metadata.get("lang", "en")
    prepared = _expand_quarto_callouts(source)
    prepared = _resolve_crossrefs(prepared, lang=lang)

    extra_args = list(PANDOC_ARGS) + _bibliography_args(
        metadata, base_dir
    )

    body = pypandoc.convert_text(
        prepared,
        to="html5",
        format=PANDOC_FORMAT,
        extra_args=extra_args,
    )

    return build_html_document(
        body=body,
        base_dir=base_dir,
        title=title,
        metadata=metadata,
        theme_css=theme_css,
    )
