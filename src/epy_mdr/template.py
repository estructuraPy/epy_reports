"""HTML document template used for previewing and PDF export."""

from __future__ import annotations

from importlib import resources
from pathlib import Path

_FOOTNOTE_REFLOW_SCRIPT = """
<script>
(function () {
  var BLOCK_TAGS = ['P','LI','BLOCKQUOTE','DIV','H1','H2','H3','H4','H5','H6','TD','TH','FIGCAPTION'];
  function reflowFootnotes() {
    var fnSection = document.querySelector('section.footnotes');
    if (!fnSection) return;
    var refs = document.querySelectorAll('a.footnote-ref');
    refs.forEach(function (ref) {
      var href = ref.getAttribute('href');
      var fnId = href ? href.replace(/^#/, '') : null;
      if (!fnId) return;
      var fnEl = document.getElementById(fnId);
      if (!fnEl) return;

      // Clone content; strip the back-link arrow.
      var clone = fnEl.cloneNode(true);
      clone.querySelectorAll('.footnote-back').forEach(function (el) { el.remove(); });

      // Walk up to the nearest block-level ancestor.
      var anchor = ref;
      while (anchor.parentElement && !BLOCK_TAGS.includes(anchor.parentElement.tagName)) {
        anchor = anchor.parentElement;
      }
      var blockParent = anchor.parentElement || ref.parentElement;

      // Build inline footnote block.
      var block = document.createElement('div');
      block.className = 'fn-inline-block';
      var numSup = document.createElement('sup');
      numSup.className = 'fn-number';
      numSup.textContent = ref.textContent.trim();
      block.appendChild(numSup);
      block.appendChild(document.createTextNode(' '));
      var pEl = clone.querySelector('p');
      var source = pEl || clone;
      while (source.firstChild) { block.appendChild(source.firstChild); }

      if (blockParent && blockParent.parentElement) {
        blockParent.parentElement.insertBefore(block, blockParent.nextSibling);
      }
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', reflowFootnotes);
  } else {
    reflowFootnotes();
  }
})();
</script>
"""

_MATHJAX_CONFIG = """
<script>
window.MathJax = {
  tex: {
    inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
    displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']],
    processEscapes: true,
    tags: 'none'
  },
  svg: { fontCache: 'global' },
  startup: {
    ready() {
      MathJax.startup.defaultReady();
      MathJax.startup.promise.then(() => {
        window._mathjax_done = true;
      });
    }
  }
};
</script>
"""


def _load_base_css() -> str:
    """Load the bundled base stylesheet from package assets."""
    return (
        resources.files("epy_mdr.assets")
        .joinpath("style.css")
        .read_text(encoding="utf-8")
    )


def _load_mathjax_script() -> str:
    r"""Return the inline MathJax v3 bundle (tex-svg-full, ~2 MB).

    Embedded inline so the preview, PDF and HTML export all work
    offline. The CDN copy that lived here before is fragile when the
    machine has no internet or the print fires before the script
    finishes downloading — which manifested as ``\[ ... \]`` shown
    as raw text in every export format.
    """
    js = (
        resources.files("epy_mdr.assets")
        .joinpath("mathjax")
        .joinpath("tex-svg-full.js")
        .read_text(encoding="utf-8")
    )
    return f"<script>{js}</script>"


def _base_href(base_dir: Path | None) -> str:
    """Build a ``<base>`` tag so relative images and links resolve."""
    if base_dir is None:
        return ""
    uri = base_dir.resolve().as_uri()
    if not uri.endswith("/"):
        uri += "/"
    return f'<base href="{uri}">'


# Valid paged-preview size keys. Kept local to avoid importing from
# ``renderer`` (which imports this module) — the canonical source of
# truth for dimensions lives in ``renderer.PAGE_SIZES``.
_PAGE_SIZE_KEYS = {"letter", "a4", "legal"}

_TRUTHY_VALUES = {"true", "yes", "1", "on"}


def is_truthy(value: str | None) -> bool:
    """Interpret a YAML-ish scalar string as a boolean.

    Treats ``"true"``, ``"yes"``, ``"1"`` and ``"on"`` (case-insensitive,
    surrounding whitespace ignored) as ``True``; everything else,
    including ``None`` and the empty string, is ``False``.

    Args:
        value: Raw metadata string, or ``None`` when the key is absent.

    Returns:
        ``True`` when the value reads as an affirmative boolean.
    """
    if value is None:
        return False
    return value.strip().lower() in _TRUTHY_VALUES


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


def _cover_page_block(metadata: dict[str, str]) -> str:
    """Render a dedicated cover page section from front matter.

    Emitted only when the ``cover`` key is truthy. Renders, in order,
    the optional logo image, the title, subtitle, author and date,
    followed by a page break so the body starts on the next printed
    page. The logo path resolves through the document's ``<base href>``,
    so relative paths work in both preview and export.
    """
    logo = metadata.get("logo")
    title = metadata.get("title")
    subtitle = metadata.get("subtitle")
    author = metadata.get("author")
    date = metadata.get("date")
    parts: list[str] = ['<section class="cover-page">']
    if logo:
        parts.append(
            f'<img class="cover-logo" src="{logo}" alt="">'
        )
    if title:
        parts.append(f'<h1 class="cover-title">{title}</h1>')
    if subtitle:
        parts.append(f'<p class="cover-subtitle">{subtitle}</p>')
    if author:
        parts.append(f'<p class="cover-author">{author}</p>')
    if date:
        parts.append(f'<p class="cover-date">{date}</p>')
    parts.append("</section>")
    parts.append('<div class="page-break"></div>')
    return "\n".join(parts)


def build_html_document(
    body: str,
    base_dir: Path | None,
    title: str,
    metadata: dict[str, str] | None = None,
    theme_css: str = "",
    *,
    paged: bool = False,
    page_size: str = "letter",
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
        paged: When ``True``, mark the ``<body>`` with the ``paged``
            class so the preview renders the content as a page sheet.
            Preview-only; it must not be set for any export.
        page_size: Page-size key (``letter`` / ``a4`` / ``legal``).
            Emitted as a ``size-<key>`` body class so the paged-preview
            CSS picks the right sheet dimensions. Unknown or missing
            values fall back to Letter. The class is always emitted (it
            is harmless when not paged).

    Returns:
        A complete, self-contained HTML5 document.
    """
    base_css = _load_base_css()
    meta = metadata or {}
    if is_truthy(meta.get("cover")):
        header = _cover_page_block(meta)
    else:
        header = _front_matter_block(meta)
    size_key = (page_size or "").strip().lower()
    if size_key not in _PAGE_SIZE_KEYS:
        size_key = "letter"
    classes = ["paged"] if paged else []
    classes.append(f"size-{size_key}")
    body_class = f' class="{" ".join(classes)}"'
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
        f"{_FOOTNOTE_REFLOW_SCRIPT}\n"
        f"{_MATHJAX_CONFIG}\n"
        f"{_load_mathjax_script()}\n"
        "</head>\n"
        f"<body{body_class}>\n"
        '<main class="doc-content">\n'
        f"{header}\n"
        f"{body}\n"
        "</main>\n"
        "</body>\n"
        "</html>\n"
    )
