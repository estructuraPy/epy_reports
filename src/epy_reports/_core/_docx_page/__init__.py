"""Apply the document's page size to a Pandoc-generated ``.docx``.

Pandoc's docx writer takes the page geometry from the reference
document, which ships in one fixed size — the front-matter
``page-size:`` (letter / a4 / legal) never reached the Word export and
an A4 report silently came out Letter. Worse, without a reference doc
Pandoc emits a ``<w:sectPr>`` with no ``<w:pgSz>`` at all, so the page
size becomes whatever the *reader's* Word locale defaults to. This
rewrites the ``<w:pgSz>`` of every section after the conversion —
inserting one where it is missing — using only the standard library
(``zipfile`` + regex on ``word/document.xml``); margins are left to the
reference document.
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

# Page sizes in twentieths of a point (twips): width, height.
_PAGE_TWIPS = {"letter": (12240, 15840), "a4": (11906, 16838), "legal": (12240, 20160)}

_PGSZ_RE = re.compile(rb"<w:pgSz [^>/]*/>")
_SECTPR_RE = re.compile(rb"(<w:sectPr[^>/]*>)(.*?)(</w:sectPr>)", re.S)


def _retag_document(data: bytes, width: int, height: int) -> bytes:
    """Rewrite (or insert) the ``<w:pgSz>`` of every section."""

    def _rewrite(match: re.Match[bytes]) -> bytes:
        tag = match.group(0)
        tag = re.sub(rb'w:w="\d+"', b'w:w="%d"' % width, tag)
        tag = re.sub(rb'w:h="\d+"', b'w:h="%d"' % height, tag)
        return tag

    new = _PGSZ_RE.sub(_rewrite, data)

    def _fill(match: re.Match[bytes]) -> bytes:
        open_tag, body, close_tag = match.groups()
        if b"pgSz" in body:
            return match.group(0)
        pg_sz = b'<w:pgSz w:w="%d" w:h="%d" />' % (width, height)
        # Schema order puts pgSz right before pgMar; append at the end
        # of the section otherwise (pandoc emits nothing after it).
        idx = body.find(b"<w:pgMar")
        if idx >= 0:
            body = body[:idx] + pg_sz + body[idx:]
        else:
            body = body + pg_sz
        return open_tag + body + close_tag

    return _SECTPR_RE.sub(_fill, new)


def apply_page_size(path: Path, page_size: str) -> None:
    """Set every section of ``path`` to ``page_size``, in place.

    Existing ``<w:pgSz>`` tags are rewritten (attributes other than
    ``w:w`` / ``w:h``, e.g. ``w:orient``, are preserved); sections that
    declare no page size get one inserted. Unknown sizes are ignored.
    """
    size = _PAGE_TWIPS.get((page_size or "").strip().lower())
    if size is None or not path.is_file():
        return
    width, height = size

    with zipfile.ZipFile(path) as zin:
        entries = [(item, zin.read(item.filename)) for item in zin.infolist()]
    changed = False
    rewritten: list[tuple[zipfile.ZipInfo, bytes]] = []
    for item, data in entries:
        if item.filename == "word/document.xml":
            new = _retag_document(data, width, height)
            changed = changed or new != data
            rewritten.append((item, new))
        else:
            rewritten.append((item, data))
    if not changed:
        return
    tmp = path.with_suffix(".pgsz.tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item, data in rewritten:
            zout.writestr(item, data)
    tmp.replace(path)
