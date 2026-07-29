"""Lightweight BibTeX parser and writer used by the References dropdown.

The reader side is intentionally minimal — just enough to expose a
list of citation keys, types and short metadata so the GUI can show
what is available in the linked ``.bib`` file. The writer side ships
a draft dataclass and a serializer so the editor can generate new
canonical entries and append them to the linked file. The actual
citation rendering at export time is handled by Pandoc's bundled
citeproc.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterator
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


# ---------------------------------------------------------------------------
# Writer side: draft → canonical BibTeX text → file append.
# ---------------------------------------------------------------------------


ENTRY_TYPES: tuple[str, ...] = (
    "article",
    "book",
    "booklet",
    "inproceedings",
    "incollection",
    "techreport",
    "mastersthesis",
    "phdthesis",
    "manual",
    "misc",
    "online",
)


REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "article":       ("author", "title", "journal", "year"),
    "book":          ("author", "title", "publisher", "year"),
    "booklet":       ("title",),
    "inproceedings": ("author", "title", "booktitle", "year"),
    "incollection":  ("author", "title", "booktitle", "publisher", "year"),
    "techreport":    ("author", "title", "institution", "year"),
    "mastersthesis": ("author", "title", "school", "year"),
    "phdthesis":     ("author", "title", "school", "year"),
    "manual":        ("title",),
    "misc":          (),
    "online":        ("title", "url", "year"),
}


_FIELD_ORDER: tuple[str, ...] = (
    "author", "editor", "title",
    "journal", "booktitle", "publisher", "institution", "school",
    "organization", "year", "month",
    "volume", "number", "pages", "edition", "chapter",
    "address", "howpublished",
    "doi", "url", "urldate", "isbn", "note",
)


_ASCII_FOLD_RE = re.compile(r"[^a-z0-9]+")


@dataclass
class BibEntryDraft:
    """Mutable draft of a BibTeX entry built by the editor dialog.

    Every field maps directly to a canonical BibTeX field name. Empty
    fields are skipped by :func:`serialize_draft`, so callers fill
    only what is relevant to the chosen :attr:`type`.
    """

    type: str = "article"
    key: str = ""
    author: str = ""
    editor: str = ""
    title: str = ""
    journal: str = ""
    booktitle: str = ""
    publisher: str = ""
    institution: str = ""
    school: str = ""
    organization: str = ""
    year: str = ""
    month: str = ""
    volume: str = ""
    number: str = ""
    pages: str = ""
    edition: str = ""
    chapter: str = ""
    address: str = ""
    howpublished: str = ""
    doi: str = ""
    url: str = ""
    urldate: str = ""
    isbn: str = ""
    note: str = ""

    def iter_filled_fields(self) -> Iterator[tuple[str, str]]:
        """Yield ``(name, value)`` for every non-empty field.

        Fields are yielded in canonical order.
        """
        for name in _FIELD_ORDER:
            value = getattr(self, name, "").strip()
            if value:
                yield name, value

    def missing_required(self) -> list[str]:
        """Return the names of required fields that are still empty."""
        required = REQUIRED_FIELDS.get(self.type, ())
        missing: list[str] = []
        if not self.key.strip():
            missing.append("key")
        for name in required:
            if not getattr(self, name, "").strip():
                missing.append(name)
        return missing


def suggest_key(author: str, year: str) -> str:
    """Generate a canonical BibTeX key from author and year.

    Takes the family name of the first author, lowercases and
    ASCII-folds it, and appends the year. Returns an empty string
    when both inputs are blank, so the caller can defer suggestion
    until the user has typed something.
    """
    cleaned_year = year.strip()
    cleaned_author = author.strip()
    if not cleaned_author and not cleaned_year:
        return ""
    first = cleaned_author.split(" and ")[0].strip() if cleaned_author else ""
    if "," in first:
        family = first.split(",", 1)[0].strip()
    else:
        family = first.split()[-1] if first else ""
    family_norm = unicodedata.normalize("NFKD", family)
    family_ascii = family_norm.encode("ascii", "ignore").decode("ascii")
    family_slug = _ASCII_FOLD_RE.sub("", family_ascii.lower())
    return f"{family_slug}{cleaned_year}".strip()


def serialize_draft(draft: BibEntryDraft) -> str:
    """Render *draft* as a canonical BibTeX entry string.

    Output uses two-space indentation, aligned ``=`` signs at column
    14, brace-delimited values, and a trailing newline so multiple
    entries concatenate cleanly. Empty fields are skipped.
    """
    width = max(
        (len(name) for name, _ in draft.iter_filled_fields()),
        default=0,
    )
    lines = [f"@{draft.type}{{{draft.key.strip()},"]
    body_lines: list[str] = []
    for name, value in draft.iter_filled_fields():
        body_lines.append(f"  {name:<{width}} = {{{value}}}")
    lines.append(",\n".join(body_lines))
    lines.append("}")
    return "\n".join(lines) + "\n"


def keys_in_file(path: Path) -> set[str]:
    """Return the set of citation keys already defined in ``path``."""
    return {entry.key for entry in parse_bib_file(path)}


def append_entry_to_file(path: Path, draft: BibEntryDraft) -> None:
    """Append *draft* (serialized) to ``path``, creating the file if needed.

    A blank line is inserted between the existing content and the new
    entry when the file ends without one, so adjacent entries stay
    visually separated.
    """
    entry_text = serialize_draft(draft)
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        separator = "" if existing.endswith("\n\n") else (
            "\n" if existing.endswith("\n") else "\n\n"
        )
        path.write_text(existing + separator + entry_text, encoding="utf-8")
    else:
        path.write_text(entry_text, encoding="utf-8")


# Re-export the writer-side public surface alongside the reader API
# already used by app.py / tab.py.
__all__ = [
    "BibEntry",
    "BibEntryDraft",
    "ENTRY_TYPES",
    "REQUIRED_FIELDS",
    "append_entry_to_file",
    "keys_in_file",
    "parse_bib_file",
    "parse_bib_text",
    "serialize_draft",
    "suggest_key",
]
