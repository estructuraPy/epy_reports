"""HTML document template used for previewing and PDF export."""

from __future__ import annotations

import base64
import html
import re
from functools import lru_cache
from importlib import resources
from pathlib import Path
from urllib.parse import unquote

# Front-matter semantics, which is epy_export's charter. The two
# copies differed only in how much of the rule their docstring
# wrote down; the accepted spellings were already the same.
from epy_export import is_truthy

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
    if (window._mathjax_done && window._diagrams_done !== false
        && window._plotly_done !== false) { run(); }
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
        resources.files("epy_reports._config._assets")
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
        resources.files("epy_reports._config._assets")
        .joinpath("mathjax")
        .joinpath("tex-svg-full.js")
        .read_text(encoding="utf-8")
    )
    return f"<script>{js}</script>"


@lru_cache(maxsize=1)
def _load_plotly_script() -> str:
    """Return the bundled Plotly.js engine wrapped in ``<script>`` (cached).

    Embedded inline (like MathJax and the diagram engines) so the preview,
    PDF and HTML export all work offline.
    """
    js = (
        resources.files("epy_reports._config._assets.plotly")
        .joinpath("plotly.min.js")
        .read_text(encoding="utf-8")
    )
    return f"<script>{js}</script>"


#: Lazy WebGL renderer for interactive plotly figures (preview + HTML export
#: only -- never the PDF export, which prints without scrolling and needs
#: every figure drawn eagerly).
#:
#: Browsers cap the number of LIVE WebGL contexts per page (~16) and silently
#: BLANK the oldest canvas beyond that; every 3D plotly figure (mesh3d,
#: scatter3d, surface, ...) holds one context. A report with dozens of 3D
#: twins therefore loses its earlier scenes as later ones draw -- the reader
#: scrolls back up to empty boxes. The shim traps the ``window.Plotly``
#: assignment (the bundle may arrive AFTER this script, inlined inside a
#: figure fragment in the body), wraps ``newPlot`` so every figure is queued
#: instead of drawn at parse time, draws a figure when it nears the viewport
#: (IntersectionObserver), and purges far-away WebGL figures back to the
#: queue so the live-context count stays bounded. SVG figures also draw
#: lazily (a large report pays its draw cost per scroll, not at load) but
#: are never purged -- they hold no GL context. ``addFrames`` on a not-yet
#: -drawn figure is stashed and replayed after the real draw, because
#: plotly.py chains it on the newPlot promise, which the queue resolves
#: immediately.
_PLOTLY_LAZY_SHIM = r"""
<script>
(function () {
  'use strict';
  // Budgeted in CONTEXTS, not figures: a subplot grid of gl3d scenes opens
  // one WebGL context PER SCENE in a single draw (measured: an epy_lab
  // virtual-test twin created 12 at once), so counting figures lets one
  // figure blow straight past the browser's ~16-context cap.
  var GL_BUDGET = 10;
  var GL_TYPE = /^(scatter3d|mesh3d|surface|cone|streamtube|volume|isosurface|scattergl|heatmapgl|splom|parcoords|pointcloud)$/;
  var queued = new Map(), frames = new Map(), anims = new Map();
  var liveGl = [], animatedLive = [], visible = new Set();
  var real = null, realNewPlot = null, realAddFrames = null,
      realAnimate = null, io = null;
  // Draws run STRICTLY one at a time. A fast scroll fires a burst of
  // intersections; concurrent newPlot calls each open their GL context
  // DURING the draw, so a burst blows past the cap before any accounting
  // runs. Serialized, the live count can exceed the budget by at most one.
  var chain = Promise.resolve();

  function elOf(x) { return typeof x === 'string' ? document.getElementById(x) : x; }
  function hasGl(data) {
    if (!data) { return false; }
    for (var i = 0; i < data.length; i++) {
      if (data[i] && GL_TYPE.test(data[i].type || '')) { return true; }
    }
    return false;
  }
  function glCount(args) {
    if (!hasGl(args[1])) { return 0; }
    var layout = args[2] || {}, n = 0;
    for (var k in layout) { if (/^scene\d*$/.test(k)) { n += 1; } }
    return n || 1;  // gl2d traces hold one context with no scene key
  }
  function totalGl() {
    var n = 0, i;
    for (i = 0; i < liveGl.length; i++) { n += liveGl[i]._epyGlN || 1; }
    for (i = 0; i < animatedLive.length; i++) { n += animatedLive[i]._epyGlN || 1; }
    return n;
  }
  function purgeSafe(el) {
    // An auto-playing animation still owns a render loop; purging under it
    // dereferences the destroyed scene ('gl' of null). Cancel first.
    try {
      if (el._transitionData) { realAnimate.call(real, el, null, { mode: 'immediate' }); }
    } catch (e) { /* already settled */ }
    // purge alone leaves the GL context to garbage collection; the browser
    // counts it as ACTIVE until then and force-loses the oldest context
    // past its cap -- possibly one still on screen. Release explicitly,
    // but only AFTER purge: the webglcontextlost event dispatches
    // asynchronously, and fired before purge it lands on a scene purge
    // already destroyed ('gl' of null). Purge detaches plotly's handlers;
    // the canvases stay reachable through this snapshot even once purge
    // removes them from the DOM.
    var canvases = Array.prototype.slice.call(el.getElementsByTagName('canvas'));
    try { real.purge(el); } catch (e) { /* never poison the draw chain */ }
    for (var i = 0; i < canvases.length; i++) {
      try {
        var gl = canvases[i].getContext('webgl2') || canvases[i].getContext('webgl');
        var ext = gl && gl.getExtension('WEBGL_lose_context');
        if (ext) { ext.loseContext(); }
      } catch (e) { /* 2d canvas or context already lost */ }
    }
  }
  function evictFor(incoming) {
    for (var i = 0; totalGl() + incoming > GL_BUDGET && i < liveGl.length;) {
      var cand = liveGl[i];
      // A 3D scene keeps scheduling deferred init passes (camera fit,
      // redraw) for a moment after newPlot resolves; purging under them
      // dereferences the destroyed scene. Let a scene settle before it is
      // eligible -- the budget overshoots transiently during a fast sweep,
      // still under the browser cap since contexts release explicitly.
      var settled = (performance.now() - (cand._epyDrawnAt || 0)) > 2000;
      if (visible.has(cand) || !settled) { i += 1; continue; }
      liveGl.splice(i, 1);
      queued.set(cand, cand._epyLazyArgs);
      purgeSafe(cand);
    }
    if (totalGl() > GL_BUDGET && !evictFor._epyTimer) {
      // Everything over budget was too young or on screen: try again once
      // the youngest has settled, so the last figures of a sweep still
      // evict with no further scroll events to trigger it.
      evictFor._epyTimer = setTimeout(function () {
        evictFor._epyTimer = null;
        evictFor(0);
      }, 2200);
    }
  }
  function drawOne(el) {
    var args = queued.get(el);
    // Skipped when already drawn, or when the reader scrolled past before
    // this figure's turn came -- it stays queued and re-pumps on re-entry.
    if (!args || !visible.has(el)) { return undefined; }
    queued.delete(el);
    evictFor(glCount(args));
    return realNewPlot.apply(real, args).then(function () {
      var fr = frames.get(el);
      var next = fr ? realAddFrames.call(real, el, fr) : undefined;
      frames.delete(el);
      var an = anims.get(el);
      if (an) {
        anims.delete(el);
        (next || Promise.resolve()).then(function () {
          if (el._fullData) { realAnimate.apply(real, an); }
        });
      }
      // Animated figures (those that ever received addFrames) are EXEMPT
      // from eviction: their auto-play render loop races a purge (the frame
      // sub-chain outlives this draw's turn) and dereferences the destroyed
      // scene. They still COUNT against the context budget, so their
      // standing contexts squeeze everything else out instead of silently
      // overflowing the browser cap.
      if (hasGl(args[1])) {
        el._epyGlN = glCount(args);
        el._epyDrawnAt = performance.now();
        if (el._epyAnimated) {
          if (animatedLive.indexOf(el) === -1) { animatedLive.push(el); }
        } else {
          el._epyLazyArgs = args;
          liveGl.push(el);
        }
        evictFor(0);
      }
    });
  }
  function pump(el) {
    chain = chain
      .then(function () { return drawOne(el); })
      .catch(function () {});
  }
  function observer() {
    if (io) { return io; }
    io = new IntersectionObserver(function (entries) {
      for (var i = 0; i < entries.length; i++) {
        var en = entries[i];
        if (en.isIntersecting) { visible.add(en.target); pump(en.target); }
        else { visible.delete(en.target); evictFor(0); }
      }
    }, { rootMargin: '500px 0px' });
    return io;
  }
  Object.defineProperty(window, 'Plotly', {
    configurable: true,
    get: function () { return real; },
    set: function (v) {
      real = v;
      if (!v || typeof v.newPlot !== 'function' || v.newPlot._epyLazy) { return; }
      realNewPlot = v.newPlot;
      realAddFrames = v.addFrames;
      realAnimate = v.animate;
      var lazyNewPlot = function (div, data, layout, config) {
        var el = elOf(div);
        if (!el) { return realNewPlot.apply(real, arguments); }
        queued.set(el, [el, data, layout, config]);
        observer().observe(el);
        return Promise.resolve(el);
      };
      lazyNewPlot._epyLazy = true;
      v.newPlot = lazyNewPlot;
      v.addFrames = function (div, fr) {
        var el = elOf(div);
        if (el) { el._epyAnimated = true; }
        if (el && queued.has(el)) { frames.set(el, fr); return Promise.resolve(el); }
        return realAddFrames.apply(real, arguments);
      };
      v.animate = function (div) {
        var el = elOf(div);
        if (el && queued.has(el)) {
          anims.set(el, Array.prototype.slice.call(arguments));
          return Promise.resolve(el);
        }
        return realAnimate.apply(real, arguments);
      };
    }
  });
})();
</script>
"""


_PLOTLY_INIT_SCRIPT = """
<script>
window._epy_init_plotly = function () {
  if (!window.Plotly) return Promise.resolve();
  var cs = getComputedStyle(document.documentElement);
  function v(n, d) { return (cs.getPropertyValue(n) || d).trim(); }
  var themeLayout = {
    paper_bgcolor: v('--epy-bg', '#ffffff'),
    plot_bgcolor: v('--epy-bg', '#ffffff'),
    font: {
      color: v('--epy-fg', '#222222'),
      family: v('--font-family-text', 'sans-serif')
    },
    colorway: [
      v('--epy-primary', '#2a76dd'),
      v('--epy-soft', '#eeeeee')
    ]
  };
  function isPlainObject(x) {
    return x !== null && typeof x === 'object' && !Array.isArray(x);
  }
  // Deep-merge with the AUTHOR's spec winning on every conflicting key;
  // the theme only fills in what the author left unset.
  function deepMerge(base, override) {
    if (!isPlainObject(base)) { return override; }
    if (!isPlainObject(override)) {
      return override === undefined ? base : override;
    }
    var out = {};
    Object.keys(base).forEach(function (k) { out[k] = base[k]; });
    Object.keys(override).forEach(function (k) {
      out[k] = deepMerge(base[k], override[k]);
    });
    return out;
  }
  var els = Array.prototype.slice.call(
    document.querySelectorAll('.epy-plotly')
  );
  var tasks = els.map(function (el) {
    var script = document.querySelector(
      'script[data-plotly-for="' + el.id + '"]'
    );
    if (!script) { return Promise.resolve(); }
    var spec;
    try {
      spec = JSON.parse(script.textContent);
    } catch (e) {
      el.textContent = 'plotly: invalid JSON (' + e.message + ')';
      return Promise.resolve();
    }
    var layout = deepMerge(themeLayout, spec.layout || {});
    var config = Object.assign(
      { responsive: true, displaylogo: false }, spec.config || {}
    );
    return Plotly.newPlot(el, spec.data || [], layout, config);
  });
  return Promise.all(tasks);
};
</script>
"""


def _plotly_block(has_plotly_flag: bool) -> str:
    """Return the Plotly.js bundle + a load-time runner, or an empty string.

    Injected only when the document actually contains an interactive
    plotly figure (``has_plotly_flag``) so a document with none — or a
    static PDF export where every fence degraded to its fallback image —
    never pays for the ~4 MB bundle. Sets ``window._plotly_done`` so the
    Paged.js runner and the live-preview scroll restore both wait for
    every figure to finish drawing before proceeding.
    """
    if not has_plotly_flag:
        return ""
    return (
        _load_plotly_script()
        + _PLOTLY_INIT_SCRIPT
        + "<script>\n"
        "window._plotly_done = false;\n"
        "document.addEventListener('DOMContentLoaded', function () {\n"
        "  window._epy_init_plotly()"
        ".then(function () { window._plotly_done = true; })\n"
        "    .catch(function () { window._plotly_done = true; });\n"
        "});\n"
        "</script>\n"
    )


_DIAGRAM_PKG = {
    "mermaid": [("epy_reports._config._assets.mermaid", "mermaid.min.js")],
    "nomnoml": [
        ("epy_reports._config._assets.nomnoml", "graphre.js"),
        ("epy_reports._config._assets.nomnoml", "nomnoml.js"),
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
  // Use mermaid.render() (measures in its own container on <body>) instead
  // of mermaid.run() so a diagram inside a hidden/paged element still
  // renders at full size.
  var els = Array.prototype.slice.call(
    document.querySelectorAll('pre.mermaid, .mermaid')
  );
  return Promise.all(els.map(function (el, i) {
    var src = el.textContent;
    return mermaid.render('epy-mermaid-' + i, src).then(function (out) {
      var div = document.createElement('div');
      div.className = 'mermaid';
      div.innerHTML = out.svg;
      var svg = div.querySelector('svg');
      if (svg) {
        var vb = (svg.getAttribute('viewBox') || '').split(/\\s+/);
        var w = parseFloat(vb[2]) || 0, h = parseFloat(vb[3]) || 0;
        svg.removeAttribute('width');
        svg.removeAttribute('height');
        svg.style.maxWidth = '100%';
        svg.style.height = 'auto';
        if (w) { svg.style.width = w + 'px'; }
        if (w && h) { svg.setAttribute('viewBox', '0 0 ' + w + ' ' + h); }
      }
      el.replaceWith(div);
    }).catch(function (e) {
      el.textContent = 'mermaid: ' + ((e && e.message) || e);
    });
  }));
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

# Default page margin shared by the paged preview and the PDF export.
# Overridable from the front matter ``margin:`` key.
DEFAULT_PAGE_MARGIN = "25mm"
_MARGIN_RE = re.compile(r"^\d+(?:\.\d+)?(mm|cm|in|px|pt|pc|em|rem)?$")


def read_page_margin(metadata: dict[str, str]) -> str:
    """Return a sanitised CSS length for the page margin.

    Accepts a CSS length such as ``20mm`` / ``1in`` / ``2.5cm``; a bare
    number is read as millimetres. Unrecognised input falls back to
    :data:`DEFAULT_PAGE_MARGIN`, so the value is always safe to inline into
    CSS without escaping.
    """
    raw = (metadata.get("margin") or "").strip().lower()
    if not raw:
        return DEFAULT_PAGE_MARGIN
    match = _MARGIN_RE.match(raw)
    if not match:
        return DEFAULT_PAGE_MARGIN
    return raw if match.group(1) else f"{raw}mm"


def _margin_var_css(metadata: dict[str, str]) -> str:
    """Emit the ``--page-margin`` custom property for the paged preview."""
    return f":root {{ --page-margin: {read_page_margin(metadata)}; }}\n"


def _pagedjs_head(page_size: str, margin: str = DEFAULT_PAGE_MARGIN) -> str:
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
        f"@page {{ size: {size_css}; margin: {margin}; }}\n"
        ".footnote { float: footnote; }\n"
        ".pagedjs_footnote_area { font-size: var(--caption-size, 10pt); }\n"
        ".pagedjs_footnote_area > div { padding-top: 0.4em; }\n"
        "</style>\n"
    )
    polyfill = (
        resources.files("epy_reports._config._assets")
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


_IMG_SRC_RE = re.compile(r'(<img\b[^>]*?\bsrc=")([^"]+)(")', re.IGNORECASE)

_IMG_MIME = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".gif": "image/gif", ".svg": "image/svg+xml", ".webp": "image/webp",
    ".bmp": "image/bmp",
}


def _embed_local_images(fragment: str, base_dir: Path | None) -> str:
    """Rewrite local ``<img src>`` references in ``fragment`` as ``data:`` URIs.

    Remote (``http(s)://``, protocol-relative) and already-embedded
    (``data:``) sources pass through untouched. Relative paths resolve
    against ``base_dir``; a source that cannot be resolved, read, or
    MIME-typed is left as-is rather than failing the render — a broken
    reference in the output is diagnosable, a crashed export is not.
    """
    def _sub(match: re.Match[str]) -> str:
        src = match.group(2)
        if src.startswith(("data:", "http://", "https://", "//")):
            return match.group(0)
        raw = unquote(src)
        if raw.startswith("file:///"):
            raw = raw[len("file:///"):]
        path = Path(raw)
        if not path.is_absolute():
            if base_dir is None:
                return match.group(0)
            path = base_dir / path
        mime = _IMG_MIME.get(path.suffix.lower())
        if mime is None or not path.is_file():
            return match.group(0)
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"{match.group(1)}data:{mime};base64,{data}{match.group(3)}"

    return _IMG_SRC_RE.sub(_sub, fragment)


# Valid paged-preview size keys. Kept local to avoid importing from
# ``renderer`` (which imports this module) — the canonical source of
# truth for dimensions lives in ``renderer.PAGE_SIZES``.
_PAGE_SIZE_KEYS = {"letter", "a4", "legal"}

_TRUTHY_VALUES = {"true", "yes", "1", "on"}
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


# Restores the scroll position the preview had before a re-render. The live
# preview reloads the whole document on every edit, which would otherwise jump
# back to the top; the editor appends ``#epypos=s:<ratio>`` to the preview URL
# and this hook scrolls there once MathJax (and any diagrams) have settled, so
# the layout height is final. Export URLs carry no hash, so it is a no-op.
_PREVIEW_RESTORE = """
<script>
(function () {
  window._epyRestore = function () {
    try {
      var m = (location.hash || '').match(/epypos=([^&]+)/);
      if (!m) return;
      var val = decodeURIComponent(m[1]);
      if (val.charAt(0) === 's') {
        var r = parseFloat(val.slice(2)) || 0;
        var el = document.scrollingElement || document.documentElement;
        if (el) el.scrollTop = r * (el.scrollHeight - el.clientHeight);
      }
    } catch (e) {}
  };
  function ready() {
    return window._mathjax_done && window._diagrams_done !== false
        && window._plotly_done !== false;
  }
  function tryRestore() {
    if (ready()) { window._epyRestore(); }
    else { setTimeout(tryRestore, 100); }
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', tryRestore);
  } else { tryRestore(); }
})();
</script>
"""

# In-page anchor navigation for documents that carry a <base href>. A plain
# href="#id" resolves AGAINST THE BASE (the document's directory), so clicking
# a TOC entry or a "Figura 3" cross-reference would navigate the preview away
# instead of jumping. This hook intercepts anchor-only links, scrolls to the
# target, and records each jump in the session history together with the
# scroll offset it left from — so Back returns to the exact previous position
# and Forward replays the jump.
_ANCHOR_NAV = """
<script>
(function () {
  function scrollingEl() {
    return document.scrollingElement || document.documentElement;
  }
  function targetFor(id) {
    var el = document.getElementById(id);
    if (el) return el;
    var byName = document.getElementsByName(id);
    return byName.length ? byName[0] : null;
  }
  function selfUrl(hash) {
    return location.href.split('#')[0] + (hash ? '#' + hash : '');
  }
  document.addEventListener('click', function (ev) {
    var node = ev.target;
    while (node && node.nodeType === 1 && node.tagName !== 'A') {
      node = node.parentNode;
    }
    if (!node || node.nodeType !== 1) return;
    var href = node.getAttribute('href') || '';
    if (href.charAt(0) !== '#') return;
    ev.preventDefault();
    var id = decodeURIComponent(href.slice(1));
    var el = targetFor(id);
    if (!el) return;
    try {
      history.replaceState({ epyScroll: scrollingEl().scrollTop }, '',
                           selfUrl(location.hash.slice(1)));
      history.pushState({ epyAnchor: id }, '', selfUrl(id));
    } catch (e) { /* degraded: jump without history */ }
    el.scrollIntoView({ block: 'start' });
  }, true);
  window.addEventListener('popstate', function (ev) {
    var st = ev.state || {};
    if (typeof st.epyScroll === 'number') {
      scrollingEl().scrollTop = st.epyScroll;
      return;
    }
    if (st.epyAnchor) {
      var el = targetFor(st.epyAnchor);
      if (el) el.scrollIntoView({ block: 'start' });
    }
  });
})();
</script>
"""

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
    export; the PDF export stamps its own watermark via ``epy_export`` so it
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
    plotly: bool = False,
    embed_images: bool = False,
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
        plotly: When ``True``, the document contains at least one
            interactive plotly figure; the bundled Plotly.js engine and
            its load-time runner are injected after the diagram block.
        embed_images: When ``True``, local ``<img>`` sources in the
            header and body are inlined as base64 ``data:`` URIs and NO
            ``<base>`` tag is emitted — a relocatable document must not
            anchor relative URLs (images OR ``#fragment`` index links,
            which ``<base>`` also captures) to a machine-specific path.

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
    # the MathJax bundle so the runner can wait for typesetting first. The
    # margin comes from the front matter and is shared with the preview via
    # the ``--page-margin`` custom property below.
    page_margin = read_page_margin(meta)
    pagedjs = _pagedjs_head(size_key, page_margin) if for_export else ""
    # The live preview restores its scroll position after a re-render; the
    # export paths (Paged.js PDF, standalone continuous HTML) carry no
    # restore hash, so the hook is preview-only.
    preview_restore = "" if (for_export or continuous) else _PREVIEW_RESTORE
    if embed_images:
        header = _embed_local_images(header, base_dir)
        body = _embed_local_images(body, base_dir)
    base_tag = "" if embed_images else _base_href(base_dir)
    # Anchor links break exactly when a <base> is present (it captures
    # #fragment hrefs); the interceptor ships if and only if the base does.
    anchor_nav = _ANCHOR_NAV if base_tag else ""
    return (
        "<!doctype html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        f"{base_tag}\n"
        f"<title>{html.escape(title)}</title>\n"
        "<style>\n"
        f"{base_css}\n"
        f"{theme_css}\n"
        f"{_margin_var_css(meta)}"
        f"{_CONTINUOUS_CSS if continuous else ''}\n"
        f"{_watermark_css(meta)}"
        "</style>\n"
        f"{_MATHJAX_CONFIG}\n"
        f"{_load_mathjax_script()}\n"
        f"{_diagram_block(diagrams)}"
        # The lazy-WebGL shim precedes ANY Plotly assignment (head bundle or
        # a fragment-inlined bundle in the body) and is deliberately NOT
        # gated on ``plotly`` -- a pandoc body can carry raw plotly.py
        # fragments with their own inlined bundle that the fence detector
        # never sees. The PDF export prints without scrolling, so it keeps
        # the eager path.
        f"{'' if for_export else _PLOTLY_LAZY_SHIM}"
        f"{_plotly_block(plotly)}"
        f"{pagedjs}"
        "</head>\n"
        f"<body{body_class}>\n"
        '<main class="doc-content">\n'
        f"{header}\n"
        f"{body}\n"
        "</main>\n"
        f"{anchor_nav}"
        f"{preview_restore}"
        "</body>\n"
        "</html>\n"
    )
