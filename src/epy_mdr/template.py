"""HTML document template used for previewing and PDF export."""

from __future__ import annotations

import html
from functools import lru_cache
from importlib import resources
from pathlib import Path

_PAGEDJS_RUNNER = """
<script>
(function () {
  window._paged_done = false;
  function setupFootnotes() {
    var section = document.querySelector('section.footnotes');
    if (!section) return;
    document.querySelectorAll('a.footnote-ref').forEach(function (ref) {
      var fnId = (ref.getAttribute('href') || '').replace(/^#/, '');
      var fnEl = fnId ? document.getElementById(fnId) : null;
      if (!fnEl) return;
      var clone = fnEl.cloneNode(true);
      clone.querySelectorAll('.footnote-back').forEach(function (e) {
        e.remove();
      });
      var span = document.createElement('span');
      span.className = 'footnote';
      var p = clone.querySelector('p');
      var src = p || clone;
      while (src.firstChild) { span.appendChild(src.firstChild); }
      if (ref.parentNode) { ref.parentNode.replaceChild(span, ref); }
    });
    section.remove();
  }
  function run() {
    setupFootnotes();
    if (!window.PagedPolyfill) { window._paged_done = true; return; }
    window.PagedPolyfill.preview().then(function () {
      window._paged_done = true;
    }).catch(function () { window._paged_done = true; });
  }
  function waitMathThenRun() {
    if (window._mathjax_done && window._diagrams_done !== false) { run(); }
    else { setTimeout(waitMathThenRun, 100); }
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', waitMathThenRun);
  } else {
    waitMathThenRun();
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


@lru_cache(maxsize=1)
def _load_base_css() -> str:
    """Load the bundled base stylesheet from package assets (cached).

    The CSS is read once on first call and reused for every subsequent
    render, avoiding a filesystem round-trip per document update.
    """
    return (
        resources.files("epy_mdr.assets")
        .joinpath("style.css")
        .read_text(encoding="utf-8")
    )


@lru_cache(maxsize=1)
def _load_mathjax_script() -> str:
    r"""Return the inline MathJax v3 bundle (tex-svg-full, ~2 MB), cached.

    Embedded inline so the preview, PDF and HTML export all work
    offline. The CDN copy that lived here before is fragile when the
    machine has no internet or the print fires before the script
    finishes downloading — which manifested as ``\[ ... \]`` shown
    as raw text in every export format.

    The result is cached after the first load to avoid re-reading ~2 MB
    on every render call.
    """
    js = (
        resources.files("epy_mdr.assets")
        .joinpath("mathjax")
        .joinpath("tex-svg-full.js")
        .read_text(encoding="utf-8")
    )
    return f"<script>{js}</script>"


_DIAGRAM_PKG = {
    "mermaid": [("epy_mdr.assets.mermaid", "mermaid.min.js")],
    "nomnoml": [
        ("epy_mdr.assets.nomnoml", "graphre.js"),
        ("epy_mdr.assets.nomnoml", "nomnoml.js"),
    ],
}


@lru_cache(maxsize=4)
def _load_diagram_script(engine: str) -> str:
    """Return the bundled engine file(s) wrapped in ``<script>`` (cached)."""
    parts: list[str] = []
    for pkg, name in _DIAGRAM_PKG[engine]:
        js = resources.files(pkg).joinpath(name).read_text(encoding="utf-8")
        parts.append(f"<script>{js}</script>")
    return "".join(parts)


_MERMAID_CONFIG = """
<script>
window._epy_init_mermaid = function () {
  if (!window.mermaid) return Promise.resolve();
  var cs = getComputedStyle(document.documentElement);
  function v(n, d) { return (cs.getPropertyValue(n) || d).trim(); }
  mermaid.initialize({
    startOnLoad: false, securityLevel: 'loose', theme: 'base',
    themeVariables: {
      background: v('--epy-bg', '#ffffff'),
      primaryColor: v('--epy-soft', '#eeeeee'),
      primaryTextColor: v('--epy-fg', '#222222'),
      primaryBorderColor: v('--epy-primary', '#2a76dd'),
      lineColor: v('--epy-primary', '#2a76dd'),
      secondaryColor: v('--epy-bg', '#ffffff'),
      tertiaryColor: v('--epy-bg', '#ffffff')
    }
  });
  return mermaid.run({ querySelector: '.mermaid' });
};
</script>
"""

_NOMNOML_CONFIG = """
<script>
window._epy_init_nomnoml = function () {
  if (!window.nomnoml) return Promise.resolve();
  var cs = getComputedStyle(document.documentElement);
  function v(n, d) { return (cs.getPropertyValue(n) || d).trim(); }
  var head = '#stroke: ' + v('--epy-primary', '#2a76dd') + '\\n' +
             '#fill: ' + v('--epy-soft', '#eeeeee') + '\\n';
  document.querySelectorAll('pre.nomnoml').forEach(function (el) {
    try {
      var wrap = document.createElement('div');
      wrap.className = 'nomnoml';
      wrap.innerHTML = nomnoml.renderSvg(head + el.textContent);
      el.replaceWith(wrap);
    } catch (e) { el.textContent = 'nomnoml: ' + e.message; }
  });
  return Promise.resolve();
};
</script>
"""


def _diagram_block(diagrams: frozenset[str]) -> str:
    """Return the diagram bundles + a load-time runner.

    The runner renders the engines and sets ``window._diagrams_done`` so the
    Paged.js export waits for the diagrams before paginating.
    """
    if not diagrams:
        return ""
    head = ""
    inits: list[str] = []
    if "mermaid" in diagrams:
        head += _load_diagram_script("mermaid") + _MERMAID_CONFIG
        inits.append("window._epy_init_mermaid()")
    if "nomnoml" in diagrams:
        head += _load_diagram_script("nomnoml") + _NOMNOML_CONFIG
        inits.append("window._epy_init_nomnoml()")
    runner = (
        "<script>\n"
        "window._diagrams_done = false;\n"
        "document.addEventListener('DOMContentLoaded', function () {\n"
        "  Promise.all([" + ", ".join(inits) + "])"
        ".then(function () { window._diagrams_done = true; })\n"
        ".catch(function () { window._diagrams_done = true; });\n"
        "});\n"
        "</script>\n"
    )
    return head + runner


# Page sizes as CSS ``@page { size }`` keywords.
_PAGE_SIZE_CSS = {"letter": "letter", "a4": "A4", "legal": "legal"}


def _pagedjs_head(page_size: str) -> str:
    """Return the export-only Paged.js block: page CSS, polyfill and runner.

    Used only for PDF export. ``window.PagedConfig.auto = false`` is set
    *before* the polyfill loads so pagination is triggered manually by the
    runner once MathJax has finished. Paged.js honours the ``@page`` margin
    on every page, places each ``float: footnote`` at the foot of its page,
    and reserves the space so notes never overlap the body.
    """
    size_key = (page_size or "").strip().lower()
    size_css = _PAGE_SIZE_CSS.get(size_key, "letter")
    css = (
        "<style>\n"
        f"@page {{ size: {size_css}; margin: 25mm; }}\n"
        ".footnote { float: footnote; }\n"
        ".pagedjs_footnote_area { font-size: var(--caption-size, 10pt); }\n"
        ".pagedjs_footnote_area > div { padding-top: 0.4em; }\n"
        "</style>\n"
    )
    polyfill = (
        resources.files("epy_mdr.assets")
        .joinpath("pagedjs")
        .joinpath("paged.polyfill.min.js")
        .read_text(encoding="utf-8")
    )
    return (
        f"{css}"
        "<script>window.PagedConfig = { auto: false };</script>\n"
        f"<script>{polyfill}</script>\n"
        f"{_PAGEDJS_RUNNER}\n"
    )


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
    """Render YAML front matter as a small header above the body.

    All metadata values are HTML-escaped before interpolation to prevent
    XSS injection from a crafted YAML front-matter block.
    """
    title = metadata.get("title")
    author = metadata.get("author")
    date = metadata.get("date")
    if not (title or author or date):
        return ""
    parts: list[str] = ['<header class="doc-meta">']
    if title:
        parts.append(f"<h1 class='doc-title'>{html.escape(title)}</h1>")
    if author:
        parts.append(f"<p class='doc-author'>{html.escape(author)}</p>")
    if date:
        parts.append(f"<p class='doc-date'>{html.escape(date)}</p>")
    parts.append("</header>")
    return "\n".join(parts)


def _cover_page_block(metadata: dict[str, str]) -> str:
    """Render a dedicated cover page section from front matter.

    Emitted only when the ``cover`` key is truthy. Renders, in order,
    the optional logo image, the title, subtitle, author and date,
    followed by a page break so the body starts on the next printed
    page. The logo path resolves through the document's ``<base href>``,
    so relative paths work in both preview and export.

    All metadata values are HTML-escaped before interpolation to prevent
    XSS injection from a crafted YAML front-matter block.
    """
    logo = metadata.get("logo")
    title = metadata.get("title")
    subtitle = metadata.get("subtitle")
    author = metadata.get("author")
    date = metadata.get("date")
    parts: list[str] = ['<section class="cover-page">']
    if logo:
        # src is a file path — escape attribute value to block injection.
        parts.append(
            f'<img class="cover-logo" src="{html.escape(logo, quote=True)}" alt="">'
        )
    if title:
        parts.append(f'<h1 class="cover-title">{html.escape(title)}</h1>')
    if subtitle:
        parts.append(f'<p class="cover-subtitle">{html.escape(subtitle)}</p>')
    if author:
        parts.append(f'<p class="cover-author">{html.escape(author)}</p>')
    if date:
        parts.append(f'<p class="cover-date">{html.escape(date)}</p>')
    parts.append("</section>")
    parts.append('<div class="page-break"></div>')
    return "\n".join(parts)


_CONTINUOUS_CSS = """
/* Continuous HTML export: hide the print/page structure so the document
   reads as one continuous web page — no page breaks and no page-number
   leaders in the indexes (those only make sense in the paginated PDF). */
.page-break { display: none !important; }
.toc-dots, .page-num { display: none !important; }
"""


def _watermark_css(metadata: dict[str, str]) -> str:
    """Return CSS painting a faint grayscale watermark behind the document.

    Restricted to screen media so it shows live in the preview and the HTML
    export; the PDF export stamps its own watermark via ``_pdf_footer`` so it
    prints reliably on every page.
    """
    watermark = (metadata.get("watermark") or "").strip()
    if not watermark:
        return ""
    src = html.escape(watermark, quote=True)
    return (
        "@media screen {\n"
        "body::after {\n"
        '  content: ""; position: fixed; inset: 0;\n'
        f'  background: url("{src}") center / 40% no-repeat;\n'
        "  opacity: 0.08; filter: grayscale(1);\n"
        "  pointer-events: none; z-index: -1;\n"
        "}\n}\n"
    )


def build_html_document(
    body: str,
    base_dir: Path | None,
    title: str,
    metadata: dict[str, str] | None = None,
    theme_css: str = "",
    *,
    paged: bool = False,
    page_size: str = "letter",
    for_export: bool = False,
    continuous: bool = False,
    diagrams: frozenset[str] = frozenset(),
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
        for_export: When ``True``, inject the Paged.js engine and an
            ``@page`` rule so the document is paginated for PDF export
            (per-page margins, footnotes at the foot of their page). The
            live preview leaves this off.
        continuous: When ``True``, hide the print/page structure (page
            breaks and index page numbers) so the HTML reads as one
            continuous web page. Used by the HTML export.
        diagrams: Diagram engines used (``mermaid`` / ``nomnoml``); their
            bundles and a load-time runner are injected when present.

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
    # Paged.js (and its @page rule) is injected only for PDF export, after
    # the MathJax bundle so the runner can wait for typesetting first.
    pagedjs = _pagedjs_head(size_key) if for_export else ""
    return (
        "<!doctype html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        f"{_base_href(base_dir)}\n"
        f"<title>{html.escape(title)}</title>\n"
        "<style>\n"
        f"{base_css}\n"
        f"{theme_css}\n"
        f"{_CONTINUOUS_CSS if continuous else ''}\n"
        f"{_watermark_css(meta)}"
        "</style>\n"
        f"{_MATHJAX_CONFIG}\n"
        f"{_load_mathjax_script()}\n"
        f"{_diagram_block(diagrams)}"
        f"{pagedjs}"
        "</head>\n"
        f"<body{body_class}>\n"
        '<main class="doc-content">\n'
        f"{header}\n"
        f"{body}\n"
        "</main>\n"
        "</body>\n"
        "</html>\n"
    )
