"""Plotly fenced-block handling shared by the preview and exports.

Mirrors :mod:`epy_reports._diagrams`: a ```` ```{.plotly ...} ```` (or
```` ```plotly ````) fenced code block holding a hand-written Plotly figure
spec (``{"data": [...], "layout": {...}}``) is converted into an
``<div class="epy-plotly">`` placeholder plus a sibling
``<script type="application/json">`` payload that the bundled Plotly.js
engine renders at load time (see ``template._plotly_block``).

Two fence attributes are recognized:

* ``fallback=path/to/image.png`` — a pre-rendered static image used
  whenever the interactive figure cannot be shown (PDF export, DOCX).
* ``height=420px`` — the CSS height of the figure container (defaults to
  :data:`DEFAULT_HEIGHT`).

WebGL canvases do not print reliably (Chromium's ``printToPdf`` and
Pandoc's DOCX writer have no WebGL renderer), so both static exports
degrade a fence to its ``fallback=`` image when one is declared.
"""

from __future__ import annotations

import re

_PLOTLY_FENCE_RE = re.compile(
    r"^[ \t]*`{3,}[ \t]*\{?\.?plotly(?P<attrs>[^\n}]*)\}?[ \t]*\n"
    r"(?P<body>.*?)\n"
    r"[ \t]*`{3,}[ \t]*$",
    re.MULTILINE | re.DOTALL,
)

_FALLBACK_ATTR_RE = re.compile(r"fallback=(?P<value>\S+)")
_HEIGHT_ATTR_RE = re.compile(r"height=(?P<value>\S+)")

DEFAULT_HEIGHT = "420px"

_MISSING_FALLBACK_NOTE = "Interactive figure — see the HTML edition."


def _parse_attrs(attrs: str) -> dict[str, str]:
    """Extract ``fallback=`` and ``height=`` from a fence attribute string.

    Values may be bare (``fallback=figs/x.png``) or quoted
    (``fallback="figs/x.png"``); surrounding quotes are stripped.
    """
    out: dict[str, str] = {}
    fallback = _FALLBACK_ATTR_RE.search(attrs)
    if fallback:
        out["fallback"] = fallback.group("value").strip("'\"")
    height = _HEIGHT_ATTR_RE.search(attrs)
    if height:
        out["height"] = height.group("value").strip("'\"")
    return out


def _escape_script_close(payload: str) -> str:
    """Escape ``</`` so embedded JSON cannot close the surrounding script."""
    return payload.replace("</", "<\\/")


def expand_plotly(source: str, *, static: bool = False) -> str:
    """Convert ```` ```{.plotly ...} ```` fences to divs or static images.

    Args:
        source: Markdown source containing zero or more plotly fences.
        static: When ``True`` (PDF export — WebGL canvases do not print
            reliably), a fence carrying a ``fallback=`` image is replaced
            by that image instead of the interactive div/script pair. A
            fence without a fallback is left interactive (best effort);
            such figures are expected to be avoided in printed documents.

    Returns:
        The source with plotly fences expanded. Each interactive figure
        gets a stable, zero-based ``epy-plotly-{i}`` id in document order.
    """
    index = [0]

    def repl(match: re.Match[str]) -> str:
        attrs = _parse_attrs(match.group("attrs") or "")
        fallback = attrs.get("fallback")
        if static and fallback:
            return f"\n![]({fallback})\n"
        i = index[0]
        index[0] += 1
        div_id = f"epy-plotly-{i}"
        height = attrs.get("height", DEFAULT_HEIGHT)
        payload = _escape_script_close(match.group("body").strip())
        return (
            "\n```{=html}\n"
            f'<div class="epy-plotly" id="{div_id}" '
            f'style="height: {height};"></div>\n'
            f'<script type="application/json" data-plotly-for="{div_id}">'
            f"{payload}</script>\n"
            "```\n"
        )

    return _PLOTLY_FENCE_RE.sub(repl, source)


def has_plotly(source: str) -> bool:
    """Return ``True`` when *source* still holds an interactive plotly div.

    Call this after :func:`expand_plotly`: a static (PDF) export may have
    replaced every fence with its fallback image, in which case the
    Plotly.js bundle should not be injected into the document head.
    """
    return 'class="epy-plotly"' in source


def strip_plotly_for_export(source: str) -> str:
    """Replace every plotly fence with a DOCX-friendly substitute.

    Word has no WebGL/Plotly renderer, so each fence becomes its declared
    ``fallback=`` image, or — when no fallback was given — a short italic
    note so the reader knows an interactive figure was omitted.
    """

    def repl(match: re.Match[str]) -> str:
        attrs = _parse_attrs(match.group("attrs") or "")
        fallback = attrs.get("fallback")
        if fallback:
            return f"\n![]({fallback})\n"
        return f"\n*{_MISSING_FALLBACK_NOTE}*\n"

    return _PLOTLY_FENCE_RE.sub(repl, source)
