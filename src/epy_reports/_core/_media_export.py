"""Maximise Word/DOCX fidelity for design components and diagrams.

Pandoc's DOCX writer ignores the CSS that styles the design components
(cards, big stats, timelines …) and has no diagram engine, so a raw export
would flatten components to anonymous text and print diagrams as source
code. This module rewrites the components into native Word structures (a
numbers-over-labels table, bold-titled blocks, plain lists) and rasterizes
each Mermaid / nomnoml diagram to a themed PNG the same way the live preview
does — an offscreen Qt WebEngine page.

The diagram rasterizer is best-effort: with no running ``QApplication`` (or
on any error) it returns ``None`` for that diagram and the export falls back
to the source text, so it never breaks a headless conversion.
"""

from __future__ import annotations

import re
from pathlib import Path

# --------------------------------------------------------------------------
# Design components → native Word structures
# --------------------------------------------------------------------------

_FENCE_RE = re.compile(r"^[ \t]*(```|~~~)")
_DIV_OPEN_RE = re.compile(r"^[ \t]*:::+[ \t]*\{")
_DIV_CLOSE_RE = re.compile(r"^[ \t]*:::+[ \t]*$")
_COMPONENT_OPEN_RE = re.compile(
    r"^[ \t]*:::+[ \t]*\{[^}]*\.(?P<cls>"
    r"stats|stat|cards|card|timeline|agenda|lead|muted|accent"
    r"|verdict|checklist)\b[^}]*\}"
    r"[ \t]*$"
)
_BOLD_RE = re.compile(r"\*\*(?P<text>.+?)\*\*")
_STAT_LABEL_RE = re.compile(r"\[(?P<text>[^\]]+)\]\{\.stat-label\}")
_CARD_HEAD_RE = re.compile(r"^[ \t]*#{1,6}[ \t]+(?P<text>.+?)[ \t]*$")


def _collect_div(lines: list[str], start: int) -> tuple[list[str], int]:
    """Return the inner lines of the fenced div opened at ``start``."""
    body: list[str] = []
    depth = 1
    j = start + 1
    while j < len(lines):
        line = lines[j]
        if _DIV_OPEN_RE.match(line):
            depth += 1
            body.append(line)
        elif _DIV_CLOSE_RE.match(line):
            depth -= 1
            if depth == 0:
                return body, j + 1
            body.append(line)
        else:
            body.append(line)
        j += 1
    return body, j


def _stats_to_table(inner: list[str]) -> list[str]:
    """Render a ``.stats`` block as a 2-row pipe table (numbers / labels)."""
    numbers: list[str] = []
    labels: list[str] = []
    i = 0
    while i < len(inner):
        if _COMPONENT_OPEN_RE.match(inner[i]) and ".stat" in inner[i]:
            body, i = _collect_div(inner, i)
            num = next(
                (m.group("text") for m in map(_BOLD_RE.search, body) if m),
                "",
            )
            label = ""
            for line in body:
                lm = _STAT_LABEL_RE.search(line)
                if lm:
                    label = lm.group("text")
                    break
                stripped = line.strip()
                if stripped and not _BOLD_RE.fullmatch(stripped):
                    label = stripped
            numbers.append(f"**{num}**" if num else "")
            labels.append(label)
        else:
            i += 1
    if not numbers:
        return []
    header = "| " + " | ".join(numbers) + " |"
    sep = "|" + "|".join([":--:"] * len(numbers)) + "|"
    label_row = "| " + " | ".join(labels) + " |"
    return ["", header, sep, label_row, ""]


def _cards_to_blocks(inner: list[str]) -> list[str]:
    """Render a ``.cards`` block as bold-titled paragraphs, one per card."""
    out: list[str] = []
    i = 0
    while i < len(inner):
        if _COMPONENT_OPEN_RE.match(inner[i]) and ".card" in inner[i]:
            body, i = _collect_div(inner, i)
            out.append("")
            for line in body:
                hm = _CARD_HEAD_RE.match(line)
                if hm:
                    out.append(f"**{hm.group('text')}**")
                    out.append("")
                else:
                    out.append(line)
            out.append("")
        else:
            i += 1
    return out


def simplify_components_for_export(source: str) -> str:
    """Rewrite design components into Word-friendly structures.

    Big stats become a numbers-over-labels table, cards become bold-titled
    blocks, and the remaining component wrappers (timeline, agenda …) are
    unwrapped so their list or text survives. Callouts and other fenced
    divs are left untouched.
    """
    lines = source.splitlines()
    out: list[str] = []
    in_fence = False
    i = 0
    while i < len(lines):
        line = lines[i]
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            out.append(line)
            i += 1
            continue
        if in_fence:
            out.append(line)
            i += 1
            continue
        m = _COMPONENT_OPEN_RE.match(line)
        if m:
            cls = m.group("cls")
            inner, i = _collect_div(lines, i)
            if cls == "stats":
                out.extend(_stats_to_table(inner))
            elif cls == "cards":
                out.extend(_cards_to_blocks(inner))
            else:
                out.extend(inner)
            continue
        out.append(line)
        i += 1
    return "\n".join(out) + ("\n" if source.endswith("\n") else "")


# --------------------------------------------------------------------------
# Mermaid / nomnoml diagrams → themed PNG
# --------------------------------------------------------------------------

_ANY_DIAGRAM_RE = re.compile(
    r"^[ \t]*`{3,}[ \t]*\{?\.?(?P<engine>mermaid|nomnoml)[^\n}]*\}?[ \t]*\n"
    r"(?P<body>.*?)\n[ \t]*`{3,}[ \t]*$",
    re.MULTILINE | re.DOTALL,
)


def collect_diagrams(source: str) -> list[tuple[str, str]]:
    """Return ``(engine, body)`` for each diagram in document order."""
    return [
        (m.group("engine"), m.group("body"))
        for m in _ANY_DIAGRAM_RE.finditer(source)
    ]


def _diagram_page_html(
    diagrams: list[tuple[str, str]], theme_css: str
) -> str:
    """Build a minimal offscreen page that renders every diagram, themed."""
    from epy_reports._core.template import (  # noqa: PLC0415
        _MERMAID_CONFIG,
        _NOMNOML_CONFIG,
        _load_diagram_script,
    )

    engines = {e for e, _ in diagrams}
    head = ""
    inits = []
    if "mermaid" in engines:
        head += _load_diagram_script("mermaid") + _MERMAID_CONFIG
        inits.append("window._epy_init_mermaid()")
    if "nomnoml" in engines:
        head += _load_diagram_script("nomnoml") + _NOMNOML_CONFIG
        inits.append("window._epy_init_nomnoml()")

    blocks = []
    for i, (engine, body) in enumerate(diagrams):
        esc = (
            body.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        blocks.append(
            f'<div class="diagram" id="d{i}">'
            f'<pre class="{engine}">\n{esc}\n</pre></div>'
        )
    runner = (
        "<script>window._md = false;\n"
        "Promise.all([" + ", ".join(inits) + "])"
        ".then(function () { window._md = true; })"
        ".catch(function () { window._md = true; });</script>"
    )
    return (
        "<!doctype html><html><head><meta charset='utf-8'>\n"
        "<style>\n"
        f"{theme_css}\n"
        "body { margin: 0; background: #ffffff; }\n"
        ".diagram { display: inline-block; padding: 14px; }\n"
        ".diagram svg { display: block; }\n"
        "</style>\n"
        f"{head}\n</head><body>\n"
        + "\n".join(blocks)
        + f"\n{runner}\n</body></html>"
    )


_RECTS_JS = (
    "(function () {"
    "  var out = [];"
    "  document.querySelectorAll('.diagram').forEach(function (d) {"
    "    var svg = d.querySelector('svg') || d;"
    "    var r = svg.getBoundingClientRect();"
    "    out.push([r.left, r.top, r.width, r.height]);"
    "  });"
    "  return JSON.stringify(out);"
    "})()"
)


def render_diagram_pngs(
    diagrams: list[tuple[str, str]],
    out_dir: Path,
    *,
    theme_css: str = "",
    timeout_ms: int = 10000,
) -> list[Path | None]:
    """Render each diagram to a PNG in ``out_dir``; ``None`` on failure."""
    if not diagrams:
        return []
    try:
        import json  # noqa: PLC0415

        from PySide6.QtCore import (  # noqa: PLC0415
            QElapsedTimer,
            QEventLoop,
            QRect,
            Qt,
            QUrl,
        )
        from PySide6.QtWebEngineWidgets import (  # noqa: PLC0415
            QWebEngineView,
        )
        from PySide6.QtWidgets import QApplication  # noqa: PLC0415
    except ImportError:
        return [None] * len(diagrams)

    app = QApplication.instance()
    if app is None:
        return [None] * len(diagrams)

    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[Path | None] = [None] * len(diagrams)
    view = QWebEngineView()
    view.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    view.resize(1400, 2200)
    view.show()

    def pump(ms: int) -> None:
        timer = QElapsedTimer()
        timer.start()
        while timer.elapsed() < ms:
            app.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 30)

    def js(expr: str) -> object:
        box: dict[str, object] = {"v": None}
        view.page().runJavaScript(expr, lambda v: box.__setitem__("v", v))
        timer = QElapsedTimer()
        timer.start()
        while box["v"] is None and timer.elapsed() < 4000:
            app.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 30)
        return box["v"]

    try:
        loaded: dict[str, bool] = {"ok": False}
        view.loadFinished.connect(lambda ok: loaded.__setitem__("ok", ok))
        page_file = out_dir / "_diagram_page.html"
        page_file.write_text(
            _diagram_page_html(diagrams, theme_css), encoding="utf-8"
        )
        view.load(QUrl.fromLocalFile(str(page_file.resolve())))
        timer = QElapsedTimer()
        timer.start()
        while not loaded["ok"] and timer.elapsed() < timeout_ms:
            app.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 30)
        while (
            js("window._md === true") is not True
            and timer.elapsed() < timeout_ms
        ):
            pump(100)
        pump(250)

        raw = js(_RECTS_JS)
        rects = json.loads(raw) if isinstance(raw, str) else []
        pix = view.grab()
        scale = pix.width() / max(1, view.width())
        for i, rect in enumerate(rects):
            if i >= len(diagrams):
                break
            x, y, w, h = (v * scale for v in rect)
            if w < 2 or h < 2:
                continue
            crop = pix.copy(QRect(round(x), round(y), round(w), round(h)))
            png = out_dir / f"diagram_{i}.png"
            if crop.save(str(png)):
                results[i] = png
    except (OSError, RuntimeError, ValueError):
        pass
    finally:
        view.deleteLater()
        pump(20)
    return results


def substitute_diagram_images(
    source: str, pngs: list[Path | None]
) -> str:
    """Replace each diagram fence with an image link to its rendered PNG."""
    index = [0]

    def repl(match: re.Match[str]) -> str:
        i = index[0]
        index[0] += 1
        png = pngs[i] if i < len(pngs) else None
        if png is None:
            return match.group(0)
        return f"![]({png.as_posix()})"

    return _ANY_DIAGRAM_RE.sub(repl, source)
