"""DOCX export honors the front-matter page-size (letter / a4 / legal)."""

from __future__ import annotations

import re
import zipfile

import pytest

from epy_reports._core._docx_page import apply_page_size
from epy_reports._core.renderer import export_docx

_SOURCE = """---
title: Page size probe
page-size: {size}
---

# Section

Body text.
"""


def _pgsz_any(xml: str) -> list[tuple[int, int]]:
    out = []
    for tag in re.findall(r"<w:pgSz [^>]*/>", xml):
        w = re.search(r'w:w="(\d+)"', tag)
        h = re.search(r'w:h="(\d+)"', tag)
        if w and h:
            out.append((int(w.group(1)), int(h.group(1))))
    return out


@pytest.mark.parametrize(
    ("declared", "expected"),
    [
        ("a4", (11906, 16838)),
        ("legal", (12240, 20160)),
        ("letter", (12240, 15840)),
    ],
)
def test_export_docx_applies_page_size(tmp_path, declared, expected):
    out = tmp_path / f"{declared}.docx"
    export_docx(_SOURCE.format(size=declared), out)
    sizes = _pgsz_any(zipfile.ZipFile(out).read("word/document.xml").decode())
    assert sizes, "document must declare a page size"
    assert all(size == expected for size in sizes)


def test_export_docx_with_reference_doc_rewrites_page_size(tmp_path):
    import epy_reports

    report = epy_reports.Report(_SOURCE.format(size="a4"))
    out = tmp_path / "themed.docx"
    export_docx(
        _SOURCE.format(size="a4"), out, reference_doc=report._reference_doc()
    )
    sizes = _pgsz_any(zipfile.ZipFile(out).read("word/document.xml").decode())
    assert sizes
    assert all(size == (11906, 16838) for size in sizes)


def test_apply_page_size_ignores_unknown(tmp_path):
    out = tmp_path / "doc.docx"
    export_docx(_SOURCE.format(size="letter"), out)
    before = out.read_bytes()
    apply_page_size(out, "tabloid")
    assert out.read_bytes() == before


def test_apply_page_size_preserves_other_attributes(tmp_path):
    doc = tmp_path / "synthetic.docx"
    xml = (
        '<w:document xmlns:w="http://schemas.openxmlformats.org/'
        'wordprocessingml/2006/main"><w:body><w:sectPr>'
        '<w:pgSz w:h="15840" w:w="12240" w:orient="portrait" />'
        "</w:sectPr></w:body></w:document>"
    )
    with zipfile.ZipFile(doc, "w") as z:
        z.writestr("word/document.xml", xml)
    apply_page_size(doc, "a4")
    text = zipfile.ZipFile(doc).read("word/document.xml").decode()
    assert 'w:w="11906"' in text
    assert 'w:h="16838"' in text
    assert 'w:orient="portrait"' in text
