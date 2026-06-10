"""Markdown/Quarto snippets, label parsing and YAML front-matter helpers.

Each template embeds plain placeholder tokens (``LABEL``, ``CAPTION``,
``URL``, ``TEXT``...) so the editor can drop the snippet at the
caret and pre-select the most relevant token for the user to type
their replacement right away.

The module also exposes minimal helpers for the YAML front matter
(``parse_front_matter``, ``set_metadata_field``) so other components
can read or update the document's metadata without dragging a YAML
library into the bundle.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Captures Quarto cross-ref labels: {#fig-foo}, {#tbl-bar width=80%}, etc.
_LABEL_RE = re.compile(
    r"\{#(?P<label>(?P<kind>fig|tbl|eq|sec)-[A-Za-z0-9_-]+)[^}]*\}"
)

KIND_DESCRIPTIONS: dict[str, str] = {
    "fig": "Figure",
    "tbl": "Table",
    "eq": "Equation",
    "sec": "Section",
}


@dataclass(frozen=True)
class Label:
    """A Quarto cross-reference label extracted from a buffer."""

    kind: str  # one of fig / tbl / eq / sec
    name: str  # full label, e.g. ``fig-capacity``


def find_labels(text: str) -> list[Label]:
    """Extract every Quarto label in document order, de-duplicated."""
    seen: set[str] = set()
    out: list[Label] = []
    for match in _LABEL_RE.finditer(text):
        name = match.group("label")
        if name in seen:
            continue
        seen.add(name)
        out.append(Label(kind=match.group("kind"), name=name))
    return out


# ----------------------------------------------------------------------
# Insert-block templates. The token in caps (LABEL / TEXT / URL / ...)
# is what the editor pre-selects after insertion.
# ----------------------------------------------------------------------

FIGURE_TEMPLATE = (
    "![CAPTION](path/to/image.png){#fig-LABEL width=80%}"
)

TABLE_TEMPLATE = (
    "| Header 1 | Header 2 | Header 3 |\n"
    "| -------- | -------- | -------- |\n"
    "|          |          |          |\n"
    "|          |          |          |\n"
    "\n"
    ": CAPTION {#tbl-LABEL}"
)

EQUATION_TEMPLATE = (
    "$$\n"
    "y = f(x)\n"
    "$$ {#eq-LABEL}"
)

CODE_BLOCK_TEMPLATE = "```python\nCODE\n```"

LINK_TEMPLATE = "[TEXT](URL)"

SECTION_HEADING_TEMPLATE = "## Section title {#sec-LABEL}"

CALLOUT_TEMPLATES: dict[str, str] = {
    "note":      "::: {.callout-note}\nBODY\n:::",
    "tip":       '::: {.callout-tip title="TITLE"}\nBODY\n:::',
    "warning":   '::: {.callout-warning title="TITLE"}\nBODY\n:::',
    "important": '::: {.callout-important title="TITLE"}\nBODY\n:::',
    "caution":   '::: {.callout-caution title="TITLE"}\nBODY\n:::',
}

# Tokens to select after inserting each template (first hit wins).
PRIMARY_PLACEHOLDER: dict[str, str] = {
    "figure":     "LABEL",
    "table":      "LABEL",
    "equation":   "LABEL",
    "code":       "CODE",
    "link":       "TEXT",
    "callout":    "TITLE",  # falls back to BODY for the .note variant
}


# ----------------------------------------------------------------------
# YAML front matter helpers (top-level scalars only).
# ----------------------------------------------------------------------


def parse_front_matter(text: str) -> dict[str, str]:
    """Extract top-level ``key: value`` pairs from a YAML block.

    Nested mappings, lists and multi-line scalars are skipped. The
    result is good enough for fields like ``title``, ``author``,
    ``date``, ``bibliography`` and ``csl`` — which is all the editor
    needs at runtime.
    """
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    block = text[3:end]
    meta: dict[str, str] = {}
    for raw in block.splitlines():
        if not raw or raw.startswith("#") or raw.startswith(" "):
            continue
        if ":" not in raw:
            continue
        key, _, value = raw.partition(":")
        meta[key.strip()] = value.strip().strip("\"'")
    return meta


def _format_yaml_value(value: str) -> str:
    """Quote ``value`` if it would be ambiguous as a YAML scalar."""
    needs_quotes = (
        value == ""
        or value[0] in "!&*?|>%@`"
        or value.strip() != value
        or any(ch in value for ch in ":#")
    )
    if needs_quotes:
        escaped = value.replace('"', '\\"')
        return f'"{escaped}"'
    return value


def set_metadata_field(text: str, field: str, value: str) -> str:
    """Insert or replace a top-level YAML ``field`` in ``text``.

    Creates a front-matter block at the top of the buffer when none
    exists. When the field is already present, its value is replaced
    in place; otherwise the field is appended to the existing block.
    """
    formatted = _format_yaml_value(value)
    line = f"{field}: {formatted}"

    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end >= 0:
            head = text[:3]  # opening '---'
            block = text[3:end]
            tail = text[end:]
            pattern = re.compile(
                rf"^{re.escape(field)}\s*:.*$", re.MULTILINE
            )
            if pattern.search(block):
                block = pattern.sub(line, block, count=1)
            else:
                if not block.endswith("\n"):
                    block += "\n"
                block += line + "\n"
            return head + block + tail

    # No usable front matter — prepend a fresh block.
    return f"---\n{line}\n---\n\n{text}"
