"""The malformed-SVG branch of ``renderer._rasterize_svgs_for_docx``.

When Qt's SVG renderer raises (an unreadable / malformed SVG), the DOCX path
must leave the original ``.svg`` reference untouched so Pandoc can try its own
fallback -- silently dropping the figure is the defect this guard prevents.
"""

from __future__ import annotations

from epy_reports._core import renderer


def test_malformed_svg_leaves_the_reference_unchanged(monkeypatch, tmp_path):
    from PySide6 import QtSvg

    svg = tmp_path / "figure.svg"
    svg.write_text("<svg/>", encoding="utf-8")
    source = "![figure](figure.svg)\n"

    class _Boom:
        def __init__(self, path):
            raise RuntimeError("cannot parse svg")

    monkeypatch.setattr(QtSvg, "QSvgRenderer", _Boom)

    out, tmp_dir = renderer._rasterize_svgs_for_docx(source, tmp_path)

    assert out == source  # reference left untouched
    assert tmp_dir is not None  # the temp dir was still created
