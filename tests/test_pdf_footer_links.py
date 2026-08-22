"""Stampers must preserve hyperlinks and named destinations.

Regression tests for the exported-PDF navigation: Chromium's print
emits link annotations whose targets are named destinations in the
document catalog. Rebuilding the PDF page-by-page through a fresh
``PdfWriter()`` drops that catalog, leaving every internal link (TOC,
index lists, cross-references) present but dead. The stampers clone the
document instead, so both the annotations and their destinations
survive every stamping pass.
"""

from __future__ import annotations

import pytest

from epy_reports._core._pdf_footer import (
    add_footer,
    add_header,
    add_metadata,
    add_page_background,
    add_watermark,
)


def _make_linked_pdf(path) -> None:
    """Two pages mirroring Chromium's print output structure.

    Page 1 carries a URI link and an internal link whose ``/Dest`` is a
    *name string*; the catalog holds the matching named destination on
    page 2 — exactly how ``printToPdf`` wires TOC/cross-reference links.
    """
    from pypdf import PdfWriter
    from pypdf.annotations import Link
    from pypdf.generic import (
        ArrayObject,
        DictionaryObject,
        NameObject,
        NumberObject,
        TextStringObject,
    )
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    pdf = canvas.Canvas(str(path), pagesize=A4)
    pdf.drawString(72, 720, "See the target")
    pdf.showPage()
    pdf.drawString(72, 720, "The target")
    pdf.showPage()
    pdf.save()

    writer = PdfWriter(clone_from=str(path))
    writer.add_named_destination("target", 1)
    internal = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Annot"),
            NameObject("/Subtype"): NameObject("/Link"),
            NameObject("/Rect"): ArrayObject(
                [NumberObject(v) for v in (70, 710, 200, 730)]
            ),
            NameObject("/Border"): ArrayObject(
                [NumberObject(0) for _ in range(3)]
            ),
            NameObject("/Dest"): TextStringObject("target"),
        }
    )
    # pypdf's add_annotation() cannot express a name-string /Dest (it
    # expects its own Link-builder dict), so attach both annotations to
    # the page's /Annots array directly.
    writer.pages[0][NameObject("/Annots")] = ArrayObject(
        [internal, Link(rect=(70, 680, 200, 700), url="https://example.com")]
    )
    with open(path, "wb") as handle:
        writer.write(handle)


def _links_and_dests(path) -> tuple[int, int, list[str]]:
    """Return (link annotation count, URI count, named destination list)."""
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    links = uris = 0
    for page in reader.pages:
        for annot in page.get("/Annots") or []:
            obj = annot.get_object()
            if obj.get("/Subtype") != "/Link":
                continue
            links += 1
            action = obj.get("/A")
            if action is not None and action.get_object().get("/S") == "/URI":
                uris += 1
    return links, uris, [d.lstrip("/") for d in reader.named_destinations]


def _make_watermark(tmp_path):
    from PIL import Image

    img = tmp_path / "wm.png"
    Image.new("RGBA", (40, 40), (30, 30, 30, 255)).save(img)
    return img


@pytest.mark.parametrize(
    "stamp",
    [
        pytest.param(
            lambda p, tmp: add_footer(p, "footer", page_numbers=True),
            id="footer",
        ),
        pytest.param(
            lambda p, tmp: add_header(p, ["a", "b", "c"]), id="header"
        ),
        pytest.param(
            lambda p, tmp: add_page_background(p, "#f5f0e6"), id="background"
        ),
        pytest.param(
            lambda p, tmp: add_watermark(p, _make_watermark(tmp)),
            id="watermark",
        ),
        pytest.param(
            lambda p, tmp: add_metadata(p, title="t", author="a"),
            id="metadata",
        ),
    ],
)
def test_stamper_preserves_links_and_destinations(tmp_path, stamp):
    pdf_path = tmp_path / "doc.pdf"
    _make_linked_pdf(pdf_path)
    links_before, uris_before, dests_before = _links_and_dests(pdf_path)
    assert links_before == 2
    assert uris_before == 1
    assert "target" in dests_before

    stamp(pdf_path, tmp_path)

    links, uris, dests = _links_and_dests(pdf_path)
    assert links == links_before
    assert uris == uris_before
    assert "target" in dests


def test_full_stamping_chain_preserves_navigation(tmp_path):
    """The whole export chain (bg + header + footer + wm + metadata)."""
    pdf_path = tmp_path / "doc.pdf"
    _make_linked_pdf(pdf_path)
    add_page_background(pdf_path, "#ffffff")
    add_watermark(pdf_path, _make_watermark(tmp_path))
    add_header(pdf_path, ["x", "", "y"])
    add_footer(pdf_path, "chain", page_numbers=True)
    add_metadata(pdf_path, title="chain")

    links, uris, dests = _links_and_dests(pdf_path)
    assert links == 2
    assert uris == 1
    assert "target" in dests
