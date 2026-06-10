"""Lightweight BibTeX parser used by the editor's References dropdown.

This is intentionally minimal — just enough to expose a list of
citation keys (and an optional title) so the GUI can show what is
available in the linked ``.bib`` file. The actual citation rendering
is handled by Pandoc's bundled citeproc when the document is built.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_ENTRY_RE = re.compile(
    r"@(?P<type>[A-Za-z]+)\s*\{\s*(?P<key>[^,\s\}]+)\s*,",
    re.MULTILINE,
)
_TITLE_RE = re.compile(
    r"title\s*=\s*[\{\"](?P<title>[^\}\"]*)",
    re.IGNORECASE,
)
_AUTHOR_RE = re.compile(
    r"author\s*=\s*[\{\"](?P<author>[^\}\"]*)",
    re.IGNORECASE,
)
_YEAR_RE = re.compile(
    r"year\s*=\s*[\{\"]?(?P<year>\d{4})",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class BibEntry:
    """A single BibTeX entry minimally parsed for display in the UI."""

    key: str
    type: str
    title: str = ""
    author: str = ""
    year: str = ""

    def short_label(self) -> str:
        """Return a compact label suitable for menu/list display."""
        parts: list[str] = [f"@{self.key}"]
        meta_bits: list[str] = []
        if self.author:
            first = self.author.split(" and ")[0].strip()
            # Use the family name (everything before a comma or the
            # last token) so the menu stays compact.
            if "," in first:
                first = first.split(",", 1)[0].strip()
            else:
                first = first.split()[-1] if first.split() else first
            meta_bits.append(first)
        if self.year:
            meta_bits.append(self.year)
        if self.title:
            title = self.title.strip()
            if len(title) > 60:
                title = title[:57] + "..."
            meta_bits.append(title)
        if meta_bits:
            parts.append("  — " + " · ".join(meta_bits))
        return "".join(parts)


def parse_bib_text(text: str) -> list[BibEntry]:
    """Parse the raw contents of a BibTeX file into :class:`BibEntry`."""
    matches = list(_ENTRY_RE.finditer(text))
    entries: list[BibEntry] = []
    for index, match in enumerate(matches):
        body_start = match.end()
        body_end = (
            matches[index + 1].start()
            if index + 1 < len(matches)
            else len(text)
        )
        body = text[body_start:body_end]
        title_match = _TITLE_RE.search(body)
        author_match = _AUTHOR_RE.search(body)
        year_match = _YEAR_RE.search(body)
        entries.append(
            BibEntry(
                key=match.group("key"),
                type=match.group("type").lower(),
                title=(
                    title_match.group("title").strip()
                    if title_match
                    else ""
                ),
                author=(
                    author_match.group("author").strip()
                    if author_match
                    else ""
                ),
                year=(
                    year_match.group("year").strip()
                    if year_match
                    else ""
                ),
            )
        )
    return entries


def parse_bib_file(path: Path) -> list[BibEntry]:
    """Read ``path`` and return its parsed BibTeX entries."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    return parse_bib_text(text)
