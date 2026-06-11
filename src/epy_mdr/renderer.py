"""Render Quarto / Pandoc Markdown to a styled HTML document.

The actual conversion is delegated to Pandoc (bundled by
``pypandoc-binary``). A small Quarto preprocessor expands titled
fenced callouts so they render with a visible header.
"""

from __future__ import annotations

import re
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


def export_docx(
    source: str,
    target: Path,
    base_dir: Path | None = None,
    reference_doc: Path | None = None,
) -> None:
    """Convert Quarto/Pandoc Markdown ``source`` to a ``.docx`` file.

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
    prepared = _expand_quarto_callouts(source)

    # tango matches the HTML preview so code chunks keep colored
    # tokens in Word; the reference-doc supplies the monospace
    # "Source Code" paragraph style.
    extra_args = ["--wrap=preserve", "--syntax-highlighting=tango"]
    if base_dir is not None:
        extra_args.append(f"--resource-path={base_dir}")
    extra_args += _bibliography_args(metadata, base_dir)
    if reference_doc is not None and reference_doc.is_file():
        extra_args.append(f"--reference-doc={reference_doc}")

    pypandoc.convert_text(
        prepared,
        to="docx",
        format=PANDOC_FORMAT,
        outputfile=str(target),
        extra_args=extra_args,
    )


def render_markdown(
    source: str,
    base_dir: Path | None = None,
    *,
    title: str = "epy_mdr",
    theme_css: str = "",
) -> str:
    """Render Quarto/Pandoc Markdown ``source`` to a full HTML page.

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

    prepared = _expand_quarto_callouts(source)

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
