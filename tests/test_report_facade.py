"""Behavioural tests for the Report scriptable facade (epy_reports package).

``tests/test_api_formal.py`` only checks that the methods exist and are
callable; this file actually invokes them and asserts on the files/values
they produce. ``to_pdf`` delegates to ``_core._export_pdf.render_report_pdf``
(a heavy Qt WebEngine flow tested on its own in
``tests/test_export_pdf.py``), so here we only verify ``Report.to_pdf``
wires the right arguments to it.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from epy_reports import Report

SAMPLE_MD = "# Title\n\nSome **bold** body text.\n"


# ---------------------------------------------------------------------------
# _theme / _theme_css
# ---------------------------------------------------------------------------


def test_theme_resolves_the_requested_theme_object():
    """_theme() returns the Theme registered under theme_id."""
    from epy_reports._core import themes

    report = Report(SAMPLE_MD, theme="minimal")
    assert report._theme().id == "minimal"
    assert report._theme() is themes.get("minimal")


def test_theme_falls_back_for_unknown_theme_id():
    """An unregistered theme id still resolves via the safe fallback."""
    from epy_reports._core import themes

    report = Report(SAMPLE_MD, theme="not-a-real-theme")
    assert report._theme().id == themes.DEFAULT_THEME_ID


def test_theme_css_returns_document_css_for_the_theme():
    """_theme_css() matches _core._design.document_css(theme)."""
    from epy_reports._core._design import document_css

    report = Report(SAMPLE_MD, theme="corporate")
    assert report._theme_css() == document_css(report._theme())


# ---------------------------------------------------------------------------
# to_html
# ---------------------------------------------------------------------------


def test_to_html_writes_a_self_contained_document(tmp_path: Path):
    """to_html renders real markdown and writes it to the given path."""
    out = tmp_path / "out.html"
    report = Report(SAMPLE_MD, base_dir=tmp_path, theme="corporate")
    result = report.to_html(out)
    assert result == out
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "<!doctype html>" in text
    assert "<h1" in text
    assert "Title" in text


def test_to_html_continuous_true_is_the_default(tmp_path: Path):
    """Default continuous=True hides page-break structure (web reading)."""
    out = tmp_path / "continuous.html"
    report = Report(SAMPLE_MD, base_dir=tmp_path)
    report.to_html(out)
    text = out.read_text(encoding="utf-8")
    assert ".page-break { display: none !important; }" in text


def test_to_html_continuous_false_keeps_page_structure(tmp_path: Path):
    """continuous=False threads through render_markdown's paged-preview path.

    Counter-example to the default above: turning continuous off must
    actually change the rendered document, not just accept the flag.
    """
    out = tmp_path / "paged.html"
    report = Report(SAMPLE_MD, base_dir=tmp_path)
    report.to_html(out, continuous=False)
    text = out.read_text(encoding="utf-8")
    assert ".page-break { display: none !important; }" not in text


# ---------------------------------------------------------------------------
# _reference_doc
# ---------------------------------------------------------------------------


def test_reference_doc_resolves_a_bundled_theme_template():
    """A real theme id resolves to its bundled .docx reference file."""
    report = Report(SAMPLE_MD, theme="corporate")
    ref = report._reference_doc()
    assert ref is not None
    assert ref.is_file()
    assert ref.name == "corporate.docx"


def test_reference_doc_returns_none_for_unknown_theme_id():
    """A theme id with no matching .docx resource returns None."""
    report = Report(SAMPLE_MD, theme="not-a-real-theme")
    assert report._reference_doc() is None


def test_reference_doc_returns_none_when_resources_raise(monkeypatch):
    """A resource-lookup failure is absorbed rather than propagated.

    Simulates a broken/frozen install (missing package data) by making
    importlib.resources.files raise; _reference_doc must degrade to None
    like any other "no template available" case, not crash the export.
    """
    import importlib.resources

    def _raise(*args, **kwargs):
        raise ModuleNotFoundError("resource package missing")

    monkeypatch.setattr(importlib.resources, "files", _raise)
    report = Report(SAMPLE_MD, theme="corporate")
    assert report._reference_doc() is None


# ---------------------------------------------------------------------------
# to_docx
# ---------------------------------------------------------------------------


def test_to_docx_writes_a_real_word_document(tmp_path: Path):
    """to_docx runs a real Pandoc conversion with the theme reference doc."""
    out = tmp_path / "out.docx"
    report = Report(SAMPLE_MD, base_dir=tmp_path, theme="corporate")
    result = report.to_docx(out)
    assert result == out
    assert out.exists()
    assert out.stat().st_size > 1_000


# ---------------------------------------------------------------------------
# to_pdf
# ---------------------------------------------------------------------------


def test_to_pdf_forwards_source_and_theme_to_render_report_pdf(
    tmp_path: Path,
):
    """to_pdf calls render_report_pdf with the report's own state."""
    out = tmp_path / "out.pdf"
    report = Report(SAMPLE_MD, base_dir=tmp_path, theme="corporate")

    with patch(
        "epy_reports._core._export_pdf.render_report_pdf"
    ) as fake_render:
        result = report.to_pdf(out, timeout_ms=1234)

    assert result == out
    fake_render.assert_called_once()
    _args, kwargs = fake_render.call_args
    assert _args[0] == SAMPLE_MD
    assert _args[1] == out
    assert kwargs["base_dir"] == tmp_path
    assert kwargs["theme_css"] == report._theme_css()
    assert kwargs["page_bg"] == report._theme().css_vars.get("bg", "")
    assert kwargs["timeout_ms"] == 1234


def test_to_pdf_default_timeout_is_sixty_seconds(tmp_path: Path):
    """The documented default timeout (60000ms) is actually passed through."""
    out = tmp_path / "out.pdf"
    report = Report(SAMPLE_MD, base_dir=tmp_path)

    with patch(
        "epy_reports._core._export_pdf.render_report_pdf"
    ) as fake_render:
        report.to_pdf(out)

    assert fake_render.call_args.kwargs["timeout_ms"] == 60000
