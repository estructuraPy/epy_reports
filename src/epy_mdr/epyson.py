"""Build :class:`Theme` objects from epy_docs ``.epyson`` layouts.

Each layout file in ``assets/themes/*.epyson`` defines a font stack,
typography scale, palette and per-callout palette mappings. This
module loads them at import time and exposes a ``Theme`` per layout
so the GUI can offer the *same* themes the document pipeline uses.
"""

from __future__ import annotations

import json
from importlib import resources
from typing import Any

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from epy_mdr.themes_base import Theme

ASSETS_PACKAGE = "epy_mdr.assets.themes"

# Files in the themes/ folder that are not themable layouts.
_NON_LAYOUTS = {"colors.epyson", "translations.epyson"}


# ---------------------------------------------------------------- utils


def _rgb_to_hex(arr: list[int] | tuple[int, int, int]) -> str:
    """Convert an ``[r, g, b]`` triplet (0-255 ints) to ``#RRGGBB``."""
    r, g, b = (int(arr[0]), int(arr[1]), int(arr[2]))
    return f"#{r:02X}{g:02X}{b:02X}"


def _contrast_text(bg_hex: str) -> str:
    """Pick black or white text for ``bg_hex`` using WCAG luminance."""
    r = int(bg_hex[1:3], 16) / 255
    g = int(bg_hex[3:5], 16) / 255
    b = int(bg_hex[5:7], 16) / 255
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return "#000000" if luminance > 0.55 else "#FFFFFF"


def _read_json(filename: str) -> dict[str, Any]:
    """Load ``filename`` from the bundled themes asset folder."""
    text = (
        resources.files(ASSETS_PACKAGE)
        .joinpath(filename)
        .read_text(encoding="utf-8")
    )
    return json.loads(text)


# ---------------------------------------------------------------- load


def _load_palettes() -> dict[str, dict[str, Any]]:
    """Parse ``colors.epyson`` once and cache its palettes by name."""
    try:
        data = _read_json("colors.epyson")
    except FileNotFoundError:
        return {}
    return data.get("color_palettes", {})


_PALETTES_CACHE: dict[str, dict[str, Any]] | None = None


def _palettes() -> dict[str, dict[str, Any]]:
    """Memoised accessor for the colour palettes."""
    global _PALETTES_CACHE
    if _PALETTES_CACHE is None:
        _PALETTES_CACHE = _load_palettes()
    return _PALETTES_CACHE


def _font_stack(family: dict[str, Any]) -> str:
    """Build a CSS ``font-family`` value from an epyson ``font_families``."""
    primary = family.get("primary", "Calibri")
    fallback = family.get("fallback", "Arial, sans-serif")
    return f'"{primary}", {fallback}'


def _pt(scales: dict[str, Any], role: str, default_size: float) -> tuple[
    str, str
]:
    """Return ``("Npt", "weight")`` from a typography ``scales`` entry."""
    entry = scales.get(role, {})
    size = entry.get("size", default_size)
    weight = str(entry.get("weight", "400"))
    return f"{float(size):g}pt", weight


def _callout_vars(
    callouts: dict[str, Any], palettes: dict[str, dict[str, Any]]
) -> dict[str, str]:
    """Resolve per-callout palette references into background/border CSS."""
    out: dict[str, str] = {}
    types = callouts.get("types", {}) if callouts else {}
    fallback = {
        "note":      "blues",
        "tip":       "greens",
        "warning":   "oranges",
        "important": "reds",
        "caution":   "oranges",
    }
    for kind in ("note", "tip", "warning", "important", "caution"):
        pal_name = (
            types.get(kind, {}).get("palette") or fallback[kind]
        )
        pdef = palettes.get(pal_name) or palettes.get(fallback[kind], {})
        # The 6-step palettes go from saturated (primary) to faint
        # (quinary). We use the lightest as the background and the
        # darkest accent (senary, fall back to primary) as the border.
        bg_rgb = pdef.get("quinary") or pdef.get("quaternary")
        border_rgb = pdef.get("senary") or pdef.get("primary")
        if bg_rgb and border_rgb:
            out[f"callout-{kind}-bg"] = _rgb_to_hex(bg_rgb)
            out[f"callout-{kind}-border"] = _rgb_to_hex(border_rgb)
    return out


def load_layout_theme(filename: str) -> Theme:
    """Build a :class:`Theme` from one layout ``.epyson`` file."""
    raw = _read_json(filename)
    palettes = _palettes()

    layout_id = (
        raw.get("layout_name") or filename.rsplit(".", 1)[0]
    )
    display_name = layout_id.replace("-", " ").replace("_", " ").title()

    # ---- fonts ------------------------------------------------------
    families = raw.get("font_families", {})
    text_family = families.get(
        raw.get("font_family_ref", "default"), families.get("default", {})
    )
    mono_family = families.get("mono_code", {})
    fam_text = _font_stack(text_family)
    fam_code = _font_stack(
        mono_family
        or {"primary": "Consolas", "fallback": "monospace"}
    )

    # ---- typography -------------------------------------------------
    scales = raw.get("typography", {}).get("scales", {})
    h1s, h1w = _pt(scales, "h1", 24)
    h2s, h2w = _pt(scales, "h2", 20)
    h3s, h3w = _pt(scales, "h3", 18)
    h4s, h4w = _pt(scales, "h4", 16)
    h5s, h5w = _pt(scales, "h5", 14)
    h6s, h6w = _pt(scales, "h6", 12)
    body_size, body_weight = _pt(scales, "text", 12)
    caption_size, _ = _pt(scales, "caption", 10)

    # ---- palette ----------------------------------------------------
    pal = raw.get("palette", {})
    page = pal.get("page", {})
    code_pal = pal.get("code", {})
    tbl = pal.get("table", {})
    colors = pal.get("colors", {})

    bg = _rgb_to_hex(page.get("background", [255, 255, 255]))
    fg = _rgb_to_hex(page.get("text", [0, 0, 0]))
    header_color = _rgb_to_hex(
        page.get("header_color", page.get("text", [0, 0, 0]))
    )
    border = _rgb_to_hex(pal.get("border_color", [200, 200, 200]))
    caption_color = _rgb_to_hex(
        pal.get("caption_color", [96, 96, 96])
    )
    code_bg = _rgb_to_hex(code_pal.get("background", [245, 245, 245]))
    code_fg = _rgb_to_hex(code_pal.get("text", page.get("text", [0, 0, 0])))

    table_header_bg = _rgb_to_hex(tbl.get("header", code_pal.get(
        "background", [240, 240, 240])))
    table_header_text = _rgb_to_hex(tbl.get("header_text", [0, 0, 0]))
    table_stripe_bg = _rgb_to_hex(tbl.get("stripe", [250, 250, 250]))

    primary_rgb = colors.get("primary", [0, 33, 126])
    secondary_rgb = colors.get("secondary", primary_rgb)
    accent_strong = _rgb_to_hex(primary_rgb)
    accent_link = _rgb_to_hex(secondary_rgb)
    accent_yellow = _rgb_to_hex(
        colors.get("quaternary", [202, 154, 36])
    )

    # ---- CSS variables ---------------------------------------------
    css_vars: dict[str, str] = {
        "fg": fg,
        "fg-muted": caption_color,
        "bg": bg,
        "bg-soft": code_bg,
        "bg-stripe": table_stripe_bg,
        "bg-quote": code_bg,
        "border": border,
        "border-soft": border,
        "link": accent_link,
        "link-hover": accent_strong,
        "mark-bg": accent_yellow,
        "kbd-bg": code_bg,
        "heading-color": header_color,
        "heading-rule": accent_link,
        "quote-rule": accent_link,
        "table-header-bg": table_header_bg,
        "table-header-text": table_header_text,
        "code-bg": code_bg,
        "code-fg": code_fg,
        "font-family-text": fam_text,
        "font-family-headings": fam_text,
        "font-family-code": fam_code,
        "body-size": body_size,
        "body-weight": body_weight,
        "h1-size": h1s, "h1-weight": h1w,
        "h2-size": h2s, "h2-weight": h2w,
        "h3-size": h3s, "h3-weight": h3w,
        "h4-size": h4s, "h4-weight": h4w,
        "h5-size": h5s, "h5-weight": h5w,
        "h6-size": h6s, "h6-weight": h6w,
        "caption-size": caption_size,
        # Token colours adopt the page text and the strong accent so
        # syntax highlighting tracks the layout palette automatically.
        "tok-kw":  accent_strong,
        "tok-cf":  accent_strong,
        "tok-dt":  accent_link,
        "tok-bu":  accent_link,
        "tok-fu":  accent_link,
        "tok-va":  fg,
        "tok-st":  caption_color,
        "tok-ch":  caption_color,
        "tok-sc":  caption_color,
        "tok-num": accent_yellow,
        "tok-co":  caption_color,
        "tok-an":  accent_yellow,
        "tok-al":  accent_strong,
        "tok-er":  accent_strong,
        "tok-op":  caption_color,
        "tok-pp":  accent_strong,
        "tok-ot":  accent_link,
        "tok-at":  accent_yellow,
    }
    css_vars.update(_callout_vars(raw.get("callouts", {}), palettes))

    # ---- Qt palette -------------------------------------------------
    qt_palette: dict[str, str] = {
        "Window":          bg,
        "WindowText":      fg,
        "Base":            bg,
        "AlternateBase":   code_bg,
        "Text":            fg,
        "PlaceholderText": caption_color,
        "Button":          code_bg,
        "ButtonText":      fg,
        "Highlight":       accent_link,
        "HighlightedText": _contrast_text(accent_link),
        "ToolTipBase":     fg,
        "ToolTipText":     bg,
        "Link":            accent_link,
        "LinkVisited":     accent_strong,
    }

    return Theme(
        id=layout_id,
        display_name=display_name,
        qt_palette=qt_palette,
        css_vars=css_vars,
    )


def load_all_themes() -> dict[str, Theme]:
    """Return every layout-derived theme, keyed by ``layout_name``."""
    discovered: dict[str, Theme] = {}
    pkg = resources.files(ASSETS_PACKAGE)
    for entry in sorted(pkg.iterdir(), key=lambda p: p.name):
        if not entry.name.endswith(".epyson"):
            continue
        if entry.name in _NON_LAYOUTS:
            continue
        try:
            theme = load_layout_theme(entry.name)
        except (json.JSONDecodeError, OSError, KeyError):
            continue
        discovered[theme.id] = theme
    return discovered


# ----------------------------------------------------- application

def apply_palette(app: QApplication, theme: Theme) -> None:
    """Apply ``theme.qt_palette`` to the running Qt application."""
    app.setStyle("Fusion")
    palette = QPalette()
    for role_name, hex_color in theme.qt_palette.items():
        role = getattr(QPalette.ColorRole, role_name, None)
        if role is None:
            continue
        palette.setColor(role, QColor(hex_color))
    app.setPalette(palette)


def qss_for(theme: Theme) -> str:
    """Build a Qt stylesheet that covers widgets beyond ``QPalette``."""
    p = theme.qt_palette
    window = p.get("Window", "#ffffff")
    text = p.get("WindowText", "#000000")
    base = p.get("Base", window)
    alt = p.get("AlternateBase", base)
    button = p.get("Button", alt)
    highlight = p.get("Highlight", "#0969da")
    highlight_text = p.get("HighlightedText", "#ffffff")
    border = theme.css_vars.get("border", "#cccccc")
    return f"""
    QMainWindow, QDialog {{
        background: {window}; color: {text};
    }}
    QToolBar {{
        background: {window}; color: {text};
        border: 0; spacing: 4px; padding: 4px;
    }}
    QToolBar::separator {{
        background: {border}; width: 1px; margin: 4px 6px;
    }}
    QToolButton {{
        background: transparent; color: {text};
        padding: 5px 10px; border-radius: 4px;
    }}
    QToolButton:hover {{ background: {alt}; }}
    QToolButton::menu-indicator {{
        subcontrol-position: right center; right: 4px;
    }}
    QMenuBar {{ background: {window}; color: {text}; }}
    QMenuBar::item {{ padding: 4px 10px; }}
    QMenuBar::item:selected {{
        background: {highlight}; color: {highlight_text};
    }}
    QMenu {{
        background: {base}; color: {text};
        border: 1px solid {border}; padding: 4px;
    }}
    QMenu::item {{ padding: 4px 18px; border-radius: 3px; }}
    QMenu::item:selected {{
        background: {highlight}; color: {highlight_text};
    }}
    QMenu::separator {{
        height: 1px; background: {border}; margin: 4px 8px;
    }}
    QTabWidget::pane {{
        background: {base}; border: 1px solid {border};
    }}
    QTabBar::tab {{
        background: {alt}; color: {text};
        padding: 6px 14px; border: 1px solid {border};
        border-bottom: none;
        border-top-left-radius: 6px; border-top-right-radius: 6px;
        margin-right: 2px;
    }}
    QTabBar::tab:selected {{ background: {base}; }}
    QTabBar::tab:hover {{ background: {button}; }}
    QPlainTextEdit, QTextEdit {{
        background: {base}; color: {text};
        selection-background-color: {highlight};
        selection-color: {highlight_text};
        border: 1px solid {border};
    }}
    QStatusBar {{ background: {window}; color: {text}; }}
    QSplitter::handle {{ background: {alt}; }}
    QSplitter::handle:hover {{ background: {border}; }}
    QScrollBar:vertical, QScrollBar:horizontal {{
        background: {base}; border: 0; width: 12px; height: 12px;
    }}
    QScrollBar::handle:vertical,
    QScrollBar::handle:horizontal {{
        background: {alt}; border-radius: 5px; margin: 2px;
    }}
    QScrollBar::handle:hover {{ background: {border}; }}
    QScrollBar::add-line, QScrollBar::sub-line {{
        background: transparent; border: 0; width: 0; height: 0;
    }}
    QLineEdit, QListWidget {{
        background: {base}; color: {text};
        border: 1px solid {border}; padding: 4px;
        selection-background-color: {highlight};
        selection-color: {highlight_text};
    }}
    QDialogButtonBox QPushButton {{
        background: {button}; color: {text};
        border: 1px solid {border};
        padding: 5px 14px; border-radius: 4px;
    }}
    QDialogButtonBox QPushButton:hover {{ background: {alt}; }}
    QDialogButtonBox QPushButton:default {{
        background: {highlight}; color: {highlight_text};
        border-color: {highlight};
    }}
    """
