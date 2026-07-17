"""Tests for export_docx with reference-doc support.

Covers:
- reference_doc arg is forwarded to pypandoc when the file exists.
- reference_doc arg is omitted when None or when the file is missing.
- One real Pandoc conversion with the corporate reference template.
"""

from __future__ import annotations

import importlib.resources
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from epy_reports.renderer import export_docx

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_MD = (
    "# Test document\n\n"
    "Some **bold** text and a table:\n\n"
    "| Column A | Column B |\n"
    "| --- | --- |\n"
    "| 1 | 2 |\n"
)


def _capture_extra_args(md: str, ref: Path | None) -> list[str]:
    """Run export_docx with a mocked pypandoc and return extra_args."""
    captured: list[list[str]] = []

    def fake_convert(
        source,
        to,
        format,
        outputfile,
        extra_args=None,
    ):
        captured.append(list(extra_args or []))

    with patch("epy_reports.renderer.pypandoc.convert_text", fake_convert):
        export_docx(
            md,
            Path("/fake/out.docx"),
            reference_doc=ref,
        )

    assert len(captured) == 1
    return captured[0]


# ---------------------------------------------------------------------------
# Unit tests — reference_doc wiring
# ---------------------------------------------------------------------------


def test_reference_doc_appended_when_file_exists(tmp_path: Path):
    """--reference-doc= is added when reference_doc points to a file."""
    ref = tmp_path / "template.docx"
    ref.write_bytes(b"PK\x03\x04")  # minimal non-empty file

    extra = _capture_extra_args(SAMPLE_MD, ref)
    ref_args = [a for a in extra if a.startswith("--reference-doc=")]
    assert len(ref_args) == 1
    assert ref_args[0] == f"--reference-doc={ref}"


def test_reference_doc_omitted_when_none():
    """--reference-doc= is NOT added when reference_doc is None."""
    extra = _capture_extra_args(SAMPLE_MD, None)
    ref_args = [a for a in extra if a.startswith("--reference-doc=")]
    assert not ref_args


def test_reference_doc_omitted_when_file_missing(tmp_path: Path):
    """--reference-doc= is NOT added when the path does not exist."""
    ghost = tmp_path / "nonexistent.docx"
    extra = _capture_extra_args(SAMPLE_MD, ghost)
    ref_args = [a for a in extra if a.startswith("--reference-doc=")]
    assert not ref_args


def test_wrap_preserve_always_present():
    """--wrap=preserve must always appear in extra_args."""
    extra = _capture_extra_args(SAMPLE_MD, None)
    assert "--wrap=preserve" in extra


# ---------------------------------------------------------------------------
# Plotly fences — stripped to a fallback image or a note before Pandoc runs.
# ---------------------------------------------------------------------------


def _capture_source(md: str) -> str:
    """Run export_docx with a mocked pypandoc and return the source text."""
    captured: list[str] = []

    def fake_convert(source, to, format, outputfile, extra_args=None):
        captured.append(source)

    with patch("epy_reports.renderer.pypandoc.convert_text", fake_convert):
        export_docx(md, Path("/fake/out.docx"))

    assert len(captured) == 1
    return captured[0]


def test_export_docx_strips_plotly_fence_to_fallback_image():
    """A plotly fence with fallback= becomes a plain image before Pandoc."""
    md = (
        "# Report\n\n"
        "```{.plotly fallback=figs/drift.png}\n"
        '{"data": [], "layout": {}}\n'
        "```\n"
    )
    source = _capture_source(md)
    assert "![](figs/drift.png)" in source
    assert "epy-plotly" not in source
    assert "```{.plotly" not in source


def test_export_docx_strips_plotly_fence_without_fallback_to_note():
    """A fallback-less plotly fence becomes a note paragraph before Pandoc."""
    md = "# Report\n\n```plotly\n" '{"data": [], "layout": {}}\n' "```\n"
    source = _capture_source(md)
    assert "Interactive figure" in source
    assert "epy-plotly" not in source


# ---------------------------------------------------------------------------
# Integration test — real Pandoc conversion with corporate template
# ---------------------------------------------------------------------------


def test_real_export_corporate_template(tmp_path: Path):
    """Real Pandoc + corporate reference template embeds the theme styles."""
    pytest.importorskip("pypandoc", reason="pypandoc not available")

    # Resolve the bundled corporate template via importlib.resources.
    try:
        pkg = importlib.resources.files(
            "epy_reports._config._assets.reference_docx"
        )
        ref_resource = pkg / "corporate.docx"
        with importlib.resources.as_file(ref_resource) as ref_path:
            assert ref_path.is_file(), (
                "corporate.docx not found in _config/_assets/reference_docx"
            )
            out = tmp_path / "out_corporate.docx"
            export_docx(SAMPLE_MD, out, reference_doc=ref_path)

    except (FileNotFoundError, ModuleNotFoundError) as exc:
        pytest.skip(f"reference_docx assets not available: {exc}")

    assert out.exists(), "Output .docx was not created"
    # The clean, theme-styled reference embeds the named styles but no logo
    # image (the old ANM-branded template bloated the file past 50 KB with an
    # embedded PNG). A styled export still lands well above the no-reference
    # baseline; assert the reference's styles actually came through.
    size = out.stat().st_size
    assert size > 12_000, (
        f"Output .docx is only {size} bytes — expected the reference "
        "template's styles to be embedded"
    )
    with zipfile.ZipFile(out) as zf:
        styles = zf.read("word/styles.xml").decode("utf-8", "ignore")
    assert "Heading1" in styles, "reference heading styles were not embedded"


def test_real_export_no_reference(tmp_path: Path):
    """Real Pandoc export without reference_doc still works."""
    pytest.importorskip("pypandoc", reason="pypandoc not available")

    out = tmp_path / "out_plain.docx"
    export_docx(SAMPLE_MD, out)
    assert out.exists()
    assert out.stat().st_size > 1_000
