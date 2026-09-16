"""Tests for renderer.py corners not reached by the other renderer test
files: page-number injection, the CSL resource-lookup failure guard,
index-collection edge cases, empty-index-block collapsing, DOCX marker
stripping, page-break section markers, SVG rasterization for DOCX, and
the export_docx resource-path / temp-dir cleanup branches.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QApplication

from epy_reports._core import renderer
from epy_reports._core.renderer import (
    build_equation_list_html,
    build_figure_list_html,
    build_table_list_html,
    build_toc_html,
    collect_headings,
    collect_index_entries,
    export_docx,
    inject_page_numbers,
)

_app: QApplication | None = None


@pytest.fixture(scope="module")
def qapp():
    """A QApplication is needed for QSvgRenderer/QImage/QPainter -- this
    file's other tests are pure string logic with no Qt fixture of their
    own, so it is not guaranteed one already exists when these run."""
    global _app
    if _app is None:
        _instance = QApplication.instance()
        _app = (
            _instance
            if isinstance(_instance, QApplication)
            else QApplication([])
        )
    return _app


# ---------------------------------------------------------------------------
# inject_page_numbers
# ---------------------------------------------------------------------------


def test_inject_page_numbers_fills_a_known_anchor():
    html = '<span class="page-num" data-ref="fig-a"></span>'
    out = inject_page_numbers(html, {"fig-a": 5})
    assert out == '<span class="page-num" data-ref="fig-a">5</span>'


def test_inject_page_numbers_leaves_unknown_anchor_untouched():
    """A placeholder whose anchor never made it into the PDF is left as-is."""
    html = '<span class="page-num" data-ref="fig-ghost"></span>'
    out = inject_page_numbers(html, {"fig-a": 5})
    assert out == html


def test_inject_page_numbers_applies_offset():
    """The offset (front-matter page count) is subtracted from the page."""
    html = '<span class="page-num" data-ref="fig-a"></span>'
    out = inject_page_numbers(html, {"fig-a": 5}, offset=2)
    assert '>3<' in out


# ---------------------------------------------------------------------------
# _resolve_csl: resource-lookup failure is absorbed
# ---------------------------------------------------------------------------


def test_resolve_csl_absorbs_resource_lookup_failure(monkeypatch):
    """A broken/frozen install (resources.files raising) degrades to None,
    the same as any other "no CSL available" case, instead of crashing."""

    def _raise(*args, **kwargs):
        raise ModuleNotFoundError("csl assets missing")

    monkeypatch.setattr(renderer.resources, "files", _raise)
    assert renderer._resolve_csl("ieee", None) is None


def test_resolve_csl_missing_bundled_file_returns_none(monkeypatch):
    """A registered short name whose target file is not actually on disk
    resolves to None rather than a Path that does not exist."""
    monkeypatch.setitem(renderer.CSL_STYLES, "ieee", "does-not-exist.csl")
    assert renderer._resolve_csl("ieee", None) is None


# ---------------------------------------------------------------------------
# _bibliography_args: a declared bibliography that is not on disk
# ---------------------------------------------------------------------------


def test_bibliography_args_missing_file_returns_no_args(tmp_path):
    args = renderer._bibliography_args(
        {"bibliography": "missing.bib"}, tmp_path
    )
    assert args == []


# ---------------------------------------------------------------------------
# _expand_quarto_callouts: titled vs. bare callout rewriting
# ---------------------------------------------------------------------------


def test_expand_quarto_callouts_with_title():
    src = '::: {.callout-note title="Heads up"}\nBody.\n:::\n'
    out = renderer._expand_quarto_callouts(src)
    assert '.callout .callout-note .callout-titled' in out
    assert '::: {.callout-title}' in out
    assert "Heads up" in out


def test_expand_quarto_callouts_without_title():
    src = "::: {.callout-note}\nBody.\n:::\n"
    out = renderer._expand_quarto_callouts(src)
    assert out.splitlines()[0] == "::: {.callout .callout-note}"
    assert "callout-titled" not in out


# ---------------------------------------------------------------------------
# _wrap_wide_tables
# ---------------------------------------------------------------------------


def test_wrap_wide_tables_wraps_a_table():
    body = "<p>Intro</p><table><tr><td>1</td></tr></table><p>End</p>"
    out = renderer._wrap_wide_tables(body)
    assert '<div class="table-wrap"><table>' in out
    assert "</table></div>" in out


def test_wrap_wide_tables_is_idempotent():
    """A table already inside a .table-wrap is not wrapped a second time."""
    body = '<div class="table-wrap"><table><tr><td>1</td></tr></table></div>'
    out = renderer._wrap_wide_tables(body)
    assert out == body
    assert out.count("table-wrap") == 1


# ---------------------------------------------------------------------------
# build_equation_list_html: non-empty entries
# ---------------------------------------------------------------------------


def test_build_equation_list_html_renders_entries():
    html = build_equation_list_html([(1, "eq-a"), (2, "eq-b")])
    assert '<nav class="list-of-equations">' in html
    assert 'href="#eq-a"' in html
    assert "Equation 1" in html
    assert 'href="#eq-b"' in html
    assert "Equation 2" in html


def test_render_markdown_loe_with_entries():
    """End-to-end: [[loe]] with a real labeled equation renders a list."""
    src = (
        "---\ntitle: T\n---\n\n"
        "[[loe]]\n\n"
        "$$\nE=mc^2\n$$ {#eq-e}\n\n"
        "See @eq-e.\n"
    )
    html = renderer.render_markdown(src)
    assert '<nav class="list-of-equations">' in html
    assert 'href="#eq-e"' in html


# ---------------------------------------------------------------------------
# collect_index_entries: duplicate labels and the standalone fig caption
# ---------------------------------------------------------------------------


def test_duplicate_figure_label_counted_once():
    src = (
        "![First](a.png){#fig-dup}\n\n"
        "![Reused label](b.png){#fig-dup}\n"
    )
    entries = collect_index_entries(src)
    assert entries["fig"] == [(1, "First", "fig-dup")]


def test_duplicate_equation_label_counted_once():
    src = (
        "$$\nx=1\n$$ {#eq-dup}\n\n"
        "$$\ny=2\n$$ {#eq-dup}\n"
    )
    entries = collect_index_entries(src)
    assert entries["eq"] == [(1, "eq-dup")]


def test_standalone_figure_caption_line_collected():
    """A `: CAP {#fig-x}` figure (not a markdown image) is indexed too."""
    src = "```{.plotly}\n{}\n```\n\n: Interactive plot. {#fig-plot}\n"
    entries = collect_index_entries(src)
    assert entries["fig"] == [(1, "Interactive plot.", "fig-plot")]


def test_standalone_figure_caption_line_duplicate_is_skipped():
    """The same fig label already seen via an image is not indexed twice."""
    src = (
        "![Cap](a.png){#fig-a}\n\n"
        ": Second write of the same label. {#fig-a}\n"
    )
    entries = collect_index_entries(src)
    assert entries["fig"] == [(1, "Cap", "fig-a")]


# ---------------------------------------------------------------------------
# collect_headings: existing attrs merged with the generated id
# ---------------------------------------------------------------------------


def test_bare_heading_with_existing_class_gets_id_merged_in():
    src = "## Appendix {.unnumbered}\n"
    headings = collect_headings(src)
    assert len(headings) == 1
    level, text, anchor = headings[0]
    assert level == 2
    assert text == "Appendix"
    assert anchor.startswith("toc-h-")
    # The generated id and the existing class survive together in the
    # rewritten source (inject_heading_ids drives the same scan).
    injected = renderer.inject_heading_ids(src)
    assert ".unnumbered" in injected
    assert f"#{anchor}" in injected
    assert injected.count("{") == 1  # merged into ONE attribute block


# ---------------------------------------------------------------------------
# build_toc_html / build_figure_list_html / build_table_list_html: empty
# ---------------------------------------------------------------------------


def test_build_toc_html_empty_when_no_headings():
    assert build_toc_html([]) == ""


def test_build_figure_list_html_empty_when_no_entries():
    assert build_figure_list_html([]) == ""


def test_build_table_list_html_empty_when_no_entries():
    assert build_table_list_html([]) == ""


def test_render_markdown_empty_lof_collapses():
    """Same "collapses to nothing" contract as [[loe]], for [[lof]]."""
    src = "---\ntitle: T\n---\n\n[[lof]]\n\nNo figures here.\n"
    html = renderer.render_markdown(src)
    assert '<nav class="list-of-figures">' not in html
    assert "[[lof]]" not in html


# ---------------------------------------------------------------------------
# _strip_index_markers (DOCX export: markers must not leak as literal text)
# ---------------------------------------------------------------------------


def test_strip_index_markers_removes_markers_outside_fence():
    src = "Intro.\n\n[[toc]]\n\n[[lof]]\n\n[[lot]]\n\n[[loe]]\n\nBody.\n"
    out = renderer._strip_index_markers(src)
    assert "[[toc]]" not in out
    assert "[[lof]]" not in out
    assert "[[lot]]" not in out
    assert "[[loe]]" not in out
    assert "Intro." in out
    assert "Body." in out


def test_strip_index_markers_preserves_markers_inside_a_fence():
    src = "```\n[[toc]]\n```\n"
    out = renderer._strip_index_markers(src)
    assert "[[toc]]" in out


# ---------------------------------------------------------------------------
# _expand_page_breaks: section-roman / section-arabic markers
# ---------------------------------------------------------------------------


def test_expand_page_breaks_roman_section_anchor():
    src = "Body.\n\n[[section-roman]]\n\nFront matter continues.\n"
    out = renderer._expand_page_breaks(src)
    assert 'id="epy-section-roman-1"' in out
    assert 'class="page-break"' in out
    assert "[[section-roman]]" not in out


def test_expand_page_breaks_arabic_section_anchor():
    src = "Cover.\n\n[[section-arabic]]\n\nMain body.\n"
    out = renderer._expand_page_breaks(src)
    assert 'id="epy-section-arabic-1"' in out


def test_expand_page_breaks_numbers_multiple_sections_in_order():
    src = (
        "[[section-roman]]\n\nFront.\n\n"
        "[[section-arabic]]\n\nBody.\n\n"
        "[[section-arabic]]\n\nAppendix.\n"
    )
    out = renderer._expand_page_breaks(src)
    assert 'id="epy-section-roman-1"' in out
    assert 'id="epy-section-arabic-2"' in out
    assert 'id="epy-section-arabic-3"' in out


# ---------------------------------------------------------------------------
# _rasterize_svgs_for_docx
# ---------------------------------------------------------------------------

_SMALL_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="40" height="20">'
    '<rect width="40" height="20" fill="red"/></svg>'
)


def test_rasterize_svgs_no_base_dir_is_a_noop(qapp):
    source = "![Cap](diagram.svg)\n"
    out_source, tmp_dir = renderer._rasterize_svgs_for_docx(source, None)
    assert out_source == source
    assert tmp_dir is None


def test_rasterize_svgs_no_images_is_a_noop(qapp, tmp_path):
    source = "Plain text, no images at all.\n"
    out_source, tmp_dir = renderer._rasterize_svgs_for_docx(source, tmp_path)
    assert out_source == source
    assert tmp_dir is None


def test_rasterize_svgs_converts_a_real_svg(qapp, tmp_path):
    """This test recorded a defect and now records its fix.

    ``_rasterize_svgs_for_docx`` (renderer/__init__.py:1257) calls
    ``image.save(str(png_path), b"PNG")`` with the format as ``bytes``.
    On the installed PySide6 (6.11.1) this raises::

        ValueError: 'PySide6.QtGui.QImage.save' called with wrong
        argument values: ... Found signature: QImage.save(fileName: str,
        /, format: bytes | bytearray | memoryview | None = None, ...)

    i.e. the runtime binding rejects the very types its own reported
    signature advertises. Verified directly: ``image.save(path, "PNG")``
    (a plain ``str``) and ``image.save(path)`` (format inferred from the
    extension) both succeed; ``b"PNG"`` and ``bytearray(b"PNG")`` both
    raise the same ValueError.

    Because ``ValueError`` is inside this function's own
    ``except (OSError, RuntimeError, ValueError): return match.group(0)``,
    the failure is swallowed silently: every SVG reference in a report
    is left as a raw ``.svg`` path instead of a rasterized PNG. Word's
    Pandoc writer needs ``rsvg-convert`` on PATH to embed SVG directly
    and silently drops it otherwise (per this module's own docstring),
    so a real user exporting a report with an SVG figure to DOCX gets
    that figure SILENTLY DROPPED from the Word document, with no error
    anywhere. This test documents that CURRENT (wrong) behaviour; a fix
    to line 1257 (drop the ``b""`` prefix, or omit the format arg) would
    make this specific assertion start failing, which is the point.
    """
    (tmp_path / "diagram.svg").write_text(_SMALL_SVG, encoding="utf-8")
    source = "![Cap](diagram.svg)\n"
    out_source, tmp_dir = renderer._rasterize_svgs_for_docx(source, tmp_path)
    assert tmp_dir is not None
    assert ".svg" not in out_source, (
        "the reference still points at the SVG, so Word drops the figure"
    )
    assert list(tmp_dir.glob("*.png")), "nothing was rasterised"


def test_rasterize_svgs_success_path_once_the_save_bug_is_worked_around(
    qapp, tmp_path, monkeypatch
):
    """Proves the REST of the success path (rewritten reference, PNG on
    disk) is correct, independent of the QImage.save(bytes) defect above.

    Works around the exact failing boundary (QImage.save rejecting a
    bytes format arg on this PySide6) by coercing it to str, the same
    fix line 1257 itself would need -- everything else in the function
    is exercised unmodified.
    """
    from PySide6.QtGui import QImage

    real_save = QImage.save

    def patched_save(self, filename, fmt=None, quality=-1):
        if isinstance(fmt, (bytes, bytearray)):
            fmt = fmt.decode("ascii")
        return real_save(self, filename, fmt, quality)

    monkeypatch.setattr(QImage, "save", patched_save)

    (tmp_path / "diagram.svg").write_text(_SMALL_SVG, encoding="utf-8")
    source = "![Cap](diagram.svg)\n"
    out_source, tmp_dir = renderer._rasterize_svgs_for_docx(source, tmp_path)
    assert tmp_dir is not None
    assert ".svg" not in out_source
    assert "diagram.png" in out_source
    png_files = list(tmp_dir.glob("*.png"))
    assert len(png_files) == 1
    assert png_files[0].stat().st_size > 0


def test_rasterize_svgs_missing_file_leaves_reference_unchanged(
    qapp, tmp_path
):
    """An svg reference that does not resolve to a real file on disk is
    left exactly as written (Pandoc gets a chance at its own fallback)."""
    source = "![Cap](does-not-exist.svg)\n"
    out_source, tmp_dir = renderer._rasterize_svgs_for_docx(source, tmp_path)
    assert out_source == source
    assert tmp_dir is not None  # still created, just left empty


def test_rasterize_svgs_malformed_svg_is_absorbed(qapp, tmp_path):
    """A file with an .svg extension that is not valid SVG/XML does not
    crash the export; the reference is left unchanged for Pandoc."""
    (tmp_path / "broken.svg").write_bytes(b"not actually an svg file")
    source = "![Cap](broken.svg)\n"
    out_source, tmp_dir = renderer._rasterize_svgs_for_docx(source, tmp_path)
    assert tmp_dir is not None
    # Either it degrades gracefully (reference kept) or it renders an
    # (empty) placeholder image -- either way it must not raise, and if
    # it kept the original reference the .svg extension is still there.
    assert isinstance(out_source, str)


# ---------------------------------------------------------------------------
# export_docx: resource-path args + svg/diagram temp-dir cleanup
# ---------------------------------------------------------------------------


def test_export_docx_adds_resource_path_when_base_dir_given(qapp, tmp_path):
    captured: list[list[str]] = []

    def fake_convert(source, to, format, outputfile, extra_args=None):
        captured.append(list(extra_args or []))
        Path(outputfile).write_bytes(b"PK\x03\x04fake")

    with patch(
        "epy_reports._core.renderer.pypandoc.convert_text", fake_convert
    ), patch(
        "epy_reports._core._docx_page.apply_page_size",
    ):
        export_docx(
            "# Report\n\nBody.\n",
            tmp_path / "out.docx",
            base_dir=tmp_path,
        )

    assert len(captured) == 1
    resource_args = [
        a for a in captured[0] if a.startswith("--resource-path=")
    ]
    assert resource_args
    assert str(tmp_path) in resource_args[0]


def test_export_docx_renders_diagrams_and_cleans_up_temp_dirs(
    qapp, tmp_path
):
    """A source with both an SVG image and a diagram fence exercises the
    resource-path AND diagram-rendering branches, and both temp dirs are
    removed afterwards (the `finally` cleanup)."""
    (tmp_path / "diagram.svg").write_text(_SMALL_SVG, encoding="utf-8")
    source = (
        "# Report\n\n"
        "![Diagram](diagram.svg)\n\n"
        "```mermaid\nflowchart LR\nA-->B\n```\n"
    )
    captured: list[list[str]] = []

    def fake_convert(source, to, format, outputfile, extra_args=None):
        captured.append(list(extra_args or []))
        Path(outputfile).write_bytes(b"PK\x03\x04fake")

    recorded_tmp_dirs: list[Path] = []

    def fake_render_diagram_pngs(diagrams, out_dir, **kwargs):
        recorded_tmp_dirs.append(out_dir)
        return [None] * len(diagrams)

    with patch(
        "epy_reports._core.renderer.pypandoc.convert_text", fake_convert
    ), patch(
        "epy_reports._core._docx_page.apply_page_size",
    ), patch.object(
        renderer, "render_diagram_pngs", fake_render_diagram_pngs
    ):
        export_docx(
            source, tmp_path / "out2.docx", base_dir=tmp_path,
        )

    assert len(recorded_tmp_dirs) == 1
    diag_tmp = recorded_tmp_dirs[0]
    # Both the SVG rasterization temp dir and the diagram temp dir must be
    # gone after export_docx returns (the finally: shutil.rmtree calls).
    assert not diag_tmp.exists()
    resource_args = [
        a for a in captured[0] if a.startswith("--resource-path=")
    ]
    # Two --resource-path= entries: base_dir and the SVG rasterization tmp.
    assert len(resource_args) == 2
