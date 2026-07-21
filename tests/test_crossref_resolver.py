"""Tests for the _resolve_crossrefs cross-reference preprocessor.

All tests import the private helper directly; no Qt, no pytest.skip.
One integration test exercises render_markdown end-to-end via real
pypandoc (Pandoc must be on PATH).
"""

from __future__ import annotations

from epy_reports._core.renderer import _resolve_crossrefs, render_markdown

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def resolve(source: str, lang: str = "en") -> str:
    return _resolve_crossrefs(source, lang=lang)


# ---------------------------------------------------------------------------
# Single figure: caption prefix + reference replacement
# ---------------------------------------------------------------------------


def test_single_figure_caption_and_ref():
    src = (
        "![Capacity curve](cap.png){#fig-capacity}\n\n"
        "See @fig-capacity for details.\n"
    )
    out = resolve(src)
    assert "Figure 1: Capacity curve" in out
    assert "[Figure 1](#fig-capacity)" in out
    assert "@fig-capacity" not in out


# ---------------------------------------------------------------------------
# Independent counters: fig and tbl both start at 1
# ---------------------------------------------------------------------------


def test_independent_counters():
    src = (
        "![A fig](a.png){#fig-alpha}\n\n"
        ": A table {#tbl-beta}\n\n"
        "Ref @fig-alpha and @tbl-beta.\n"
    )
    out = resolve(src)
    assert "[Figure 1](#fig-alpha)" in out
    assert "[Table 1](#tbl-beta)" in out


# ---------------------------------------------------------------------------
# Two figures — numbered in document order
# ---------------------------------------------------------------------------


def test_two_figures_ordered():
    src = (
        "![First](a.png){#fig-one}\n\n"
        "![Second](b.png){#fig-two}\n\n"
        "@fig-one then @fig-two.\n"
    )
    out = resolve(src)
    assert "Figure 1: First" in out
    assert "Figure 2: Second" in out
    assert "[Figure 1](#fig-one)" in out
    assert "[Figure 2](#fig-two)" in out


# ---------------------------------------------------------------------------
# Spanish localisation
# ---------------------------------------------------------------------------


def test_spanish_lang():
    src = (
        "![Gráfica](g.png){#fig-g}\n\n"
        ": Resultados {#tbl-r}\n\n"
        "$$\nE=mc^2\n$$ {#eq-e}\n\n"
        "## Intro {#sec-intro}\n\n"
        "@fig-g, @tbl-r, @eq-e, @sec-intro.\n"
    )
    out = resolve(src, lang="es")
    assert "Figura 1" in out
    assert "Tabla 1" in out
    assert "Ecuación 1" in out
    assert "[Sección 1](#sec-intro)" in out


# ---------------------------------------------------------------------------
# Real citation @navarro2020 must NOT be touched
# ---------------------------------------------------------------------------


def test_real_citation_untouched():
    src = (
        "![Fig](f.png){#fig-f}\n\n"
        "See @navarro2020 and @fig-f.\n"
    )
    out = resolve(src)
    assert "@navarro2020" in out
    assert "[Figure 1](#fig-f)" in out


# ---------------------------------------------------------------------------
# Unknown label — left raw
# ---------------------------------------------------------------------------


def test_unknown_ref_left_raw():
    src = "Refer to @fig-missing for the diagram.\n"
    out = resolve(src)
    assert "@fig-missing" in out


# ---------------------------------------------------------------------------
# Content inside fenced code block is NOT transformed
# ---------------------------------------------------------------------------


def test_fenced_code_block_untouched():
    src = (
        "![Cap](img.png){#fig-real}\n\n"
        "```\n"
        "@fig-real should not be replaced\n"
        "![Alt](x.png){#fig-inside}\n"
        "```\n\n"
        "@fig-real outside.\n"
    )
    out = resolve(src)
    # Inside the fence — must stay verbatim.
    assert "@fig-real should not be replaced" in out
    assert "![Alt](x.png){#fig-inside}" in out
    # Outside the fence — must be replaced.
    assert "[Figure 1](#fig-real)" in out


# ---------------------------------------------------------------------------
# Inline code span is NOT transformed
# ---------------------------------------------------------------------------


def test_inline_code_span_untouched():
    src = (
        "![Cap](img.png){#fig-ic}\n\n"
        "Use `@fig-ic` as a literal, but see @fig-ic in prose.\n"
    )
    out = resolve(src)
    assert "`@fig-ic`" in out
    assert "[Figure 1](#fig-ic)" in out


# ---------------------------------------------------------------------------
# Equation: \tag{N} injected, reference resolved
# ---------------------------------------------------------------------------


def test_equation_tag_and_ref():
    src = (
        "$$\n"
        "E = mc^2\n"
        "$$ {#eq-einstein}\n\n"
        "From @eq-einstein we get energy.\n"
    )
    out = resolve(src)
    assert r"\tag{1}" in out
    assert "[Equation 1](#eq-einstein)" in out
    assert "@eq-einstein" not in out


def test_equation_no_double_tag():
    """A line already containing \\tag{ is left unchanged."""
    src = (
        "$$\n"
        r"E = mc^2 \tag{1}"
        "\n$$ {#eq-e2}\n\n"
        "@eq-e2.\n"
    )
    out = resolve(src)
    # \tag{1} already present — must not become \tag{1} \tag{1}
    assert out.count(r"\tag{") == 1


def test_equation_emits_anchor_span():
    """The closing line must emit a bracketed-span anchor.

    Without it the label leaks as visible prose and prose references
    like [Equation 1](#eq-x) target a non-existent element.
    """
    src = (
        "$$\nE = mc^2\n$$ {#eq-einstein}\n\n"
        "@eq-einstein.\n"
    )
    out = resolve(src)
    assert "[]{#eq-einstein}" in out


def test_render_markdown_equation_anchor_exists():
    """End-to-end: the rendered HTML must contain id=\"eq-x\"."""
    src = (
        "---\ntitle: Test\n---\n\n"
        "$$\nE = mc^2\n$$ {#eq-einstein}\n\n"
        "From @eq-einstein the energy follows.\n"
    )
    html = render_markdown(src)
    assert 'id="eq-einstein"' in html
    assert "{#eq-einstein}" not in html
    assert '<a href="#eq-einstein">Equation 1</a>' in html


# ---------------------------------------------------------------------------
# Reference BEFORE its definition still resolves (PASS A scans all first)
# ---------------------------------------------------------------------------


def test_ref_before_definition():
    src = (
        "See @fig-late for details.\n\n"
        "![Late figure](late.png){#fig-late}\n"
    )
    out = resolve(src)
    assert "[Figure 1](#fig-late)" in out
    assert "@fig-late" not in out


# ---------------------------------------------------------------------------
# Idempotent-ish: already-prefixed caption not double-prefixed
# ---------------------------------------------------------------------------


def test_no_double_prefix():
    src = (
        "![Figure 1: Already done](f.png){#fig-done}\n\n"
        "@fig-done.\n"
    )
    # First call — caption already has the prefix; should not add another.
    out = resolve(src)
    # Must not produce "Figure 1: Figure 1:" or similar.
    assert "Figure 1: Figure 1:" not in out


# ---------------------------------------------------------------------------
# Section reference
# ---------------------------------------------------------------------------


def test_section_ref():
    src = (
        "## Introduction {#sec-intro}\n\n"
        "As discussed in @sec-intro.\n"
    )
    out = resolve(src)
    assert "[Section 1](#sec-intro)" in out
    assert "@sec-intro" not in out


# ---------------------------------------------------------------------------
# Integration: render_markdown produces HTML with "Figure 1", no raw ref
# ---------------------------------------------------------------------------


def test_render_markdown_integration():
    """Real pypandoc pipeline must resolve the cross-reference."""
    src = (
        "---\n"
        "title: Test\n"
        "---\n\n"
        "![A test figure](noexist.png){#fig-test}\n\n"
        "See @fig-test above.\n"
    )
    html = render_markdown(src)
    assert "Figure 1" in html
    assert "@fig-test" not in html


# ---------------------------------------------------------------------------
# Standalone colon figure caption (`: CAP {#fig-x}`) — the non-image figure
# form used by interactive plotly fences and raw-HTML figures.
# ---------------------------------------------------------------------------


def test_colon_figure_caption_numbered_with_anchor():
    src = (
        "```{.plotly fallback=figs/a.png}\n{}\n```\n\n"
        ": Wind force per floor. {#fig-wind}\n\n"
        "See @fig-wind.\n"
    )
    out = resolve(src)
    assert "*Figure 1: Wind force per floor.* []{#fig-wind}" in out
    assert "[Figure 1](#fig-wind)" in out


def test_colon_figure_and_image_share_numbering():
    src = (
        "![First](a.png){#fig-a}\n\n"
        ": Second, interactive. {#fig-b}\n\n"
        "@fig-a and @fig-b.\n"
    )
    out = resolve(src)
    assert "Figure 1: First" in out
    assert "*Figure 2: Second, interactive.*" in out
    assert "[Figure 2](#fig-b)" in out


# ---------------------------------------------------------------------------
# Orphan figure attrs in prose scrub to invisible anchors (the
# "{#fig-x} leaked into the caption" defect).
# ---------------------------------------------------------------------------


def test_orphan_fig_attr_becomes_anchor():
    src = (
        "**Figure.** Hand-written caption paragraph. {#fig-orphan}\n\n"
        "See @fig-orphan.\n"
    )
    out = resolve(src)
    assert "[]{#fig-orphan}" in out
    assert "caption paragraph. {#fig-orphan}" not in out
    assert "[Figure 1](#fig-orphan)" in out


def test_image_attached_fig_attr_not_scrubbed():
    src = "![Cap](p.png){#fig-keep}\n"
    out = resolve(src)
    assert "){#fig-keep}" in out


def test_table_caption_attr_becomes_anchor():
    src = ": A table caption {#tbl-t}\n"
    out = resolve(src)
    assert "Table 1: A table caption []{#tbl-t}" in out
    assert "caption {#tbl-t}" not in out
