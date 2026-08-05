"""Tests for the lazy-WebGL plotly shim.

Browsers cap the number of live WebGL contexts per page (~16) and silently
blank the oldest canvas beyond that; every 3D plotly figure holds one
context, so a report with dozens of 3D twins loses its earlier scenes as
later ones draw. The template injects a shim that queues every figure at
parse time, draws it near the viewport, and purges far-away WebGL figures
-- for the preview and the HTML export only. The PDF export prints without
scrolling and MUST keep the eager path.
"""

from __future__ import annotations

from epy_reports._core.template import build_html_document

_MARKER = "GL_BUDGET"


def test_preview_ships_the_lazy_shim(tmp_path):
    html = build_html_document(body="<p>x</p>", base_dir=tmp_path, title="T")
    assert _MARKER in html


def test_html_export_ships_the_lazy_shim(tmp_path):
    html = build_html_document(
        body="<p>x</p>", base_dir=tmp_path, title="T", continuous=True,
        embed_images=True,
    )
    assert _MARKER in html


def test_pdf_export_stays_eager(tmp_path):
    html = build_html_document(
        body="<p>x</p>", base_dir=tmp_path, title="T", for_export=True,
    )
    assert _MARKER not in html


def test_shim_is_not_gated_on_the_fence_detector(tmp_path):
    """A pandoc body can carry raw plotly.py fragments (their own inlined
    bundle) that the ``plotly`` fence flag never sees -- the shim must ship
    regardless, and it must precede the body so the ``window.Plotly`` setter
    trap exists before any fragment assigns it."""
    html = build_html_document(
        body="<div class='plotly-graph-div'></div>", base_dir=tmp_path,
        title="T", plotly=False,
    )
    assert _MARKER in html
    assert html.index(_MARKER) < html.index("plotly-graph-div")


def test_shim_precedes_the_head_bundle_when_fences_exist(tmp_path):
    html = build_html_document(
        body="<p>x</p>", base_dir=tmp_path, title="T", plotly=True,
    )
    assert html.index(_MARKER) < html.index("_epy_init_plotly")
