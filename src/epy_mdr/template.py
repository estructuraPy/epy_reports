"""HTML document template used for previewing and PDF export."""

from __future__ import annotations

from importlib import resources
from pathlib import Path

_MATHJAX = """
<script>
window.MathJax = {
  tex: {
    inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
    displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']],
    processEscapes: true
  },
  svg: { fontCache: 'global' }
};
</script>
<script async
  src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js">
</script>
"""


def _load_base_css() -> str:
    """Load the bundled base stylesheet from package assets."""
    return (
        resources.files("epy_mdr.assets")
        .joinpath("style.css")
        .read_text(encoding="utf-8")
    )


def _base_href(base_dir: Path | None) -> str:
    """Build a ``<base>`` tag so relative images and links resolve."""
    if base_dir is None:
        return ""
    uri = base_dir.resolve().as_uri()
    if not uri.endswith("/"):
        uri += "/"
    return f'<base href="{uri}">'


def _front_matter_block(metadata: dict[str, str]) -> str:
    """Render YAML front matter as a small header above the body."""
    title = metadata.get("title")
    author = metadata.get("author")
    date = metadata.get("date")
    if not (title or author or date):
        return ""
    parts: list[str] = ['<header class="doc-meta">']
    if title:
        parts.append(f"<h1 class='doc-title'>{title}</h1>")
    if author:
        parts.append(f"<p class='doc-author'>{author}</p>")
    if date:
        parts.append(f"<p class='doc-date'>{date}</p>")
    parts.append("</header>")
    return "\n".join(parts)


def build_html_document(
    body: str,
    base_dir: Path | None,
    title: str,
    metadata: dict[str, str] | None = None,
    theme_css: str = "",
) -> str:
    """Assemble the final HTML document around a rendered body.

    Args:
        body: HTML fragment produced by Pandoc.
        base_dir: Optional directory used as the HTML ``<base>`` URL.
        title: Document title shown in ``<title>``.
        metadata: YAML front matter values. Used to emit a small
            title/author/date block before ``body``.
        theme_css: Optional ``:root { … }`` block that overrides the
            base stylesheet's custom properties. Empty for the Light
            theme (the base stylesheet already encodes its values).

    Returns:
        A complete, self-contained HTML5 document.
    """
    base_css = _load_base_css()
    header = _front_matter_block(metadata or {})
    return (
        "<!doctype html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        f"{_base_href(base_dir)}\n"
        f"<title>{title}</title>\n"
        "<style>\n"
        f"{base_css}\n"
        f"{theme_css}\n"
        "</style>\n"
        f"{_MATHJAX}\n"
        "</head>\n"
        "<body>\n"
        f"{header}\n"
        f"{body}\n"
        "</body>\n"
        "</html>\n"
    )
