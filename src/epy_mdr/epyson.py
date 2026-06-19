"""Build :class:`Theme` objects from epy_docs ``.epyson`` layouts.

Each layout file in ``assets/themes/*.epyson`` defines a font stack,
typography scale, palette and per-callout palette mappings. This
module loads them at import time and exposes a ``Theme`` per layout
so the GUI can offer the *same* themes the document pipeline uses.
"""

from __future__ import annotations

import json
import re
from importlib import resources
from pathlib import Path
from typing import Any

from PySide6.QtGui import QColor, QFont, QPalette
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


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert ``#RRGGBB`` to an ``(r, g, b)`` int triplet."""
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _coerce_hex(value: str | list[int]) -> str:
    """Return ``#RRGGBB`` from either a hex string or an ``[r, g, b]`` list."""
    if isinstance(value, str):
        return value if value.startswith("#") else f"#{value}"
    return _rgb_to_hex(value)


def _mix(c1: str, c2: str, t: float) -> str:
    """Linear blend: ``t=0`` is ``c1``, ``t=1`` is ``c2``.

    Args:
        c1: Source hex color.
        c2: Target hex color.
        t: Blend weight toward ``c2`` in [0, 1].

    Returns:
        Blended ``#RRGGBB`` hex string.
    """
    r1, g1, b1 = _hex_to_rgb(c1)
    r2, g2, b2 = _hex_to_rgb(c2)
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return f"#{r:02X}{g:02X}{b:02X}"


def _lighten(c: str, t: float) -> str:
    """Mix ``c`` toward white by factor ``t`` in [0, 1]."""
    return _mix(c, "#FFFFFF", t)


def _darken(c: str, t: float) -> str:
    """Mix ``c`` toward black by factor ``t`` in [0, 1]."""
    return _mix(c, "#000000", t)


def _is_dark(c: str) -> bool:
    """Return True if ``c`` has WCAG relative luminance below 0.5."""
    r, g, b = (v / 255 for v in _hex_to_rgb(c))
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) < 0.5


def _contrast_text(bg_hex: str) -> str:
    """Pick black or white text for ``bg_hex`` using WCAG luminance."""
    return "#000000" if not _is_dark(bg_hex) else "#FFFFFF"


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
        tdef = types.get(kind, {})
        # Direct bg/border colors (used by the theme editor) win over a
        # named-palette reference.
        bg_direct = tdef.get("bg")
        border_direct = tdef.get("border")
        if bg_direct and border_direct:
            out[f"callout-{kind}-bg"] = _coerce_hex(bg_direct)
            out[f"callout-{kind}-border"] = _coerce_hex(border_direct)
            continue
        pal_name = tdef.get("palette") or fallback[kind]
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
    """Build a :class:`Theme` from one bundled layout ``.epyson`` file."""
    raw = _read_json(filename)
    return _theme_from_raw(raw, filename.rsplit(".", 1)[0])


def _theme_from_raw(raw: dict[str, Any], default_id: str) -> Theme:
    """Build a :class:`Theme` from a parsed ``.epyson`` mapping.

    Shared by the bundled-layout loader and the user-theme loader. An
    explicit ``display_name`` in the file is honoured (so editor-generated
    themes keep their exact name); otherwise it is derived from the id.
    """
    palettes = _palettes()

    layout_id = raw.get("layout_name") or default_id
    display_name = (
        raw.get("display_name")
        or layout_id.replace("-", " ").replace("_", " ").title()
    )

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


# ----------------------------------------------- user (custom) themes

_SAFE_STEM_RE = re.compile(r"[^A-Za-z0-9_-]+")


def user_themes_dir() -> Path:
    """Return the writable directory holding user-generated themes.

    Lives under ``QStandardPaths.AppConfigLocation`` so custom themes
    persist across sessions and are writable even from the frozen build
    (the bundled ``assets/themes`` are read-only).
    """
    from PySide6.QtCore import QStandardPaths  # noqa: PLC0415

    root = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppConfigLocation
    )
    return Path(root) / "epy_mdr" / "themes"


def _safe_stem(name: str) -> str:
    """Slugify a theme name into a safe ``.epyson`` file stem."""
    slug = _SAFE_STEM_RE.sub("-", name.strip().lower()).strip("-")
    return slug or "custom-theme"


def load_user_theme(path: Path) -> Theme:
    """Build a :class:`Theme` from a user ``.epyson`` file on disk."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    return _theme_from_raw(raw, path.stem)


def user_theme_ids() -> set[str]:
    """Return the ids of themes that live in the user directory."""
    directory = user_themes_dir()
    if not directory.is_dir():
        return set()
    ids: set[str] = set()
    for path in directory.glob("*.epyson"):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        ids.add(raw.get("layout_name") or path.stem)
    return ids


def save_user_theme(payload: dict[str, Any]) -> str:
    """Persist an ``.epyson`` ``payload`` as a user theme; return its id.

    The file stem and the ``layout_name`` are both set from the slugified
    name so the saved id is stable and matches the filename.
    """
    layout_id = payload.get("layout_name") or _safe_stem(
        payload.get("display_name", "custom-theme")
    )
    layout_id = _safe_stem(layout_id)
    payload = {**payload, "layout_name": layout_id}
    directory = user_themes_dir()
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{layout_id}.epyson").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return layout_id


def delete_user_theme(theme_id: str) -> None:
    """Delete a user theme by id (no-op if it does not exist)."""
    (user_themes_dir() / f"{theme_id}.epyson").unlink(missing_ok=True)


def build_epyson(values: dict[str, Any]) -> dict[str, Any]:
    """Assemble an ``.epyson`` payload from theme-editor form values.

    ``values`` keys: ``display_name``; the hex colors ``page_bg``,
    ``text``, ``heading``, ``primary``, ``secondary``, ``border``,
    ``code_bg``, ``mark``; the font family names ``text_font`` and
    ``code_font``; ``scales`` (``role -> {"size": float, "weight": str}``
    for h1..h6, text, caption); and ``callouts``
    (``kind -> {"bg": hex, "border": hex}``).
    """
    def rgb(hex_color: str) -> list[int]:
        return list(_hex_to_rgb(hex_color))

    return {
        "display_name": values["display_name"],
        "font_family_ref": "default",
        "font_families": {
            "default": {"primary": values["text_font"],
                        "fallback": "Arial, sans-serif"},
            "mono_code": {"primary": values["code_font"],
                          "fallback": "monospace"},
        },
        "typography": {"scales": {
            role: {"size": spec["size"], "weight": spec["weight"]}
            for role, spec in values["scales"].items()
        }},
        "palette": {
            "page": {"background": rgb(values["page_bg"]),
                     "text": rgb(values["text"]),
                     "header_color": rgb(values["heading"])},
            "code": {"background": rgb(values["code_bg"]),
                     "text": rgb(values["text"])},
            "border_color": rgb(values["border"]),
            "caption_color": rgb(values["text"]),
            "colors": {"primary": rgb(values["primary"]),
                       "secondary": rgb(values["secondary"]),
                       "quaternary": rgb(values["mark"])},
        },
        "callouts": {"types": {
            kind: {"bg": spec["bg"], "border": spec["border"]}
            for kind, spec in values["callouts"].items()
        }},
    }


# ------------------------------------------------------- catalogue


def load_all_themes() -> dict[str, Theme]:
    """Return every theme, keyed by id (bundled layouts + user themes)."""
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

    # User-generated themes (override bundled ids of the same name).
    directory = user_themes_dir()
    if directory.is_dir():
        for path in sorted(directory.glob("*.epyson")):
            try:
                theme = load_user_theme(path)
            except (json.JSONDecodeError, OSError, KeyError):
                continue
            discovered[theme.id] = theme
    return discovered


# ----------------------------------------------------- application

def apply_palette(app: QApplication, theme: Theme) -> None:
    """Apply ``theme.qt_palette`` to the running Qt application."""
    app.setStyle("Fusion")
    # Fluent-style typography: a clean system sans for the chrome. The
    # editor keeps its own monospace font (set explicitly per widget).
    chrome_font = QFont("Segoe UI Variable Text")
    if "segoe ui variable" not in chrome_font.family().lower():
        chrome_font = QFont("Segoe UI")
    chrome_font.setPointSize(10)
    app.setFont(chrome_font)
    palette = QPalette()
    for role_name, hex_color in theme.qt_palette.items():
        role = getattr(QPalette.ColorRole, role_name, None)
        if role is None:
            continue
        palette.setColor(role, QColor(hex_color))
    app.setPalette(palette)


def _tonal_variants(
    bg: str, accent: str, is_dark_theme: bool
) -> dict[str, str]:
    """Derive subtle tonal variants from ``bg`` and ``accent``.

    Args:
        bg: Window background hex color.
        accent: Primary accent (link/highlight) hex color.
        is_dark_theme: True when the palette background is dark.

    Returns:
        Dict with keys: bg_toolbar, bg_statusbar, bg_panel,
        bg_menu, accent_soft, accent_strong, scrollbar_handle.
    """
    if is_dark_theme:
        bg_toolbar = _lighten(bg, 0.08)
        bg_statusbar = _darken(bg, 0.06)
        bg_panel = _lighten(bg, 0.05)
        bg_menu = _lighten(bg, 0.06)
    else:
        bg_toolbar = _darken(bg, 0.06)
        bg_statusbar = _darken(bg, 0.04)
        bg_panel = _darken(bg, 0.03)
        bg_menu = _darken(bg, 0.02)

    accent_soft = _mix(accent, bg, 0.82)
    accent_strong = _mix(accent, bg, 0.55)
    # Scrollbar handle: mid-tone between fg and bg
    scrollbar_handle = _mix(accent, bg, 0.70)
    return {
        "bg_toolbar": bg_toolbar,
        "bg_statusbar": bg_statusbar,
        "bg_panel": bg_panel,
        "bg_menu": bg_menu,
        "accent_soft": accent_soft,
        "accent_strong": accent_strong,
        "scrollbar_handle": scrollbar_handle,
    }


def qss_for(theme: Theme) -> str:
    """Build a Qt stylesheet that covers widgets beyond ``QPalette``.

    Derives subtle tonal variants from the theme palette so each zone
    (toolbar, statusbar, menus, tabs, scrollbars) has a visibly distinct
    but harmonious tone.
    """
    p = theme.qt_palette
    window = p.get("Window", "#ffffff")
    text = p.get("WindowText", "#000000")
    base = p.get("Base", window)
    highlight = p.get("Highlight", "#0969da")
    highlight_text = p.get("HighlightedText", "#ffffff")
    border = theme.css_vars.get("border", "#cccccc")

    # Fluent-style tones: flat surfaces, subtle neutral hover fills, with
    # the accent reserved for the active tab, focus and default button.
    subtle = _mix(text, window, 0.94)
    subtle_strong = _mix(text, window, 0.88)
    accent_tint = _mix(highlight, window, 0.86)
    accent_tint_text = _contrast_text(accent_tint)
    accent_hover = _darken(highlight, 0.12)
    hairline = _mix(border, window, 0.55)
    muted_text = _mix(text, window, 0.40)

    return f"""
    QMainWindow, QDialog {{ background: {window}; color: {text}; }}

    QToolBar {{
        background: {window}; color: {text};
        border: 0; border-bottom: 1px solid {hairline};
        spacing: 2px; padding: 6px 8px;
    }}
    QToolBar::separator {{
        background: {hairline}; width: 1px; margin: 7px 6px;
    }}
    QToolButton {{
        background: transparent; color: {text};
        padding: 6px 12px; border-radius: 6px; border: none;
    }}
    QToolButton:hover {{ background: {subtle}; }}
    QToolButton:pressed {{ background: {subtle_strong}; }}
    QToolButton:checked {{
        background: {accent_tint}; color: {accent_tint_text};
    }}
    QToolButton::menu-indicator {{ image: none; width: 0; }}

    QMenuBar {{ background: {window}; color: {text}; border: 0; }}
    QMenuBar::item {{
        padding: 6px 10px; border-radius: 6px; background: transparent;
    }}
    QMenuBar::item:selected {{ background: {subtle}; }}

    QMenu {{
        background: {window}; color: {text};
        border: 1px solid {hairline}; border-radius: 8px; padding: 6px;
    }}
    QMenu::item {{ padding: 6px 28px 6px 14px; border-radius: 6px; }}
    QMenu::item:selected {{ background: {subtle}; }}
    QMenu::separator {{
        height: 1px; background: {hairline}; margin: 6px 10px;
    }}

    QTabWidget::pane {{
        background: {base}; border: 1px solid {hairline};
        border-radius: 8px;
    }}
    QTabBar {{ qproperty-drawBase: 0; }}
    QTabBar::tab {{
        background: transparent; color: {muted_text};
        padding: 8px 16px; border: 0; margin-right: 2px;
        border-top-left-radius: 8px; border-top-right-radius: 8px;
    }}
    QTabBar::tab:hover:!selected {{ background: {subtle}; color: {text}; }}
    QTabBar::tab:selected {{
        background: {base}; color: {text};
        border-bottom: 2px solid {highlight};
    }}

    QPlainTextEdit, QTextEdit, QLineEdit, QListWidget,
    QComboBox, QSpinBox, QDoubleSpinBox {{
        background: {base}; color: {text};
        border: 1px solid {hairline}; border-radius: 8px; padding: 6px 8px;
        selection-background-color: {accent_tint}; selection-color: {text};
    }}
    QPlainTextEdit:focus, QTextEdit:focus, QLineEdit:focus,
    QListWidget:focus, QComboBox:focus, QSpinBox:focus,
    QDoubleSpinBox:focus {{ border: 1px solid {highlight}; }}
    QComboBox::drop-down {{ border: 0; width: 22px; }}

    QGroupBox {{
        border: 1px solid {hairline}; border-radius: 8px;
        margin-top: 10px; padding: 10px 8px 8px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin; left: 10px; padding: 0 4px;
        color: {muted_text};
    }}
    QCheckBox, QRadioButton, QLabel {{
        color: {text}; background: transparent;
    }}

    QStatusBar {{
        background: {window}; color: {muted_text};
        border-top: 1px solid {hairline};
    }}
    QStatusBar::item {{ border: 0; }}

    QSplitter::handle {{ background: transparent; }}
    QSplitter::handle:hover {{ background: {subtle}; }}

    QScrollBar:vertical {{
        background: transparent; border: 0; width: 12px; margin: 0;
    }}
    QScrollBar:horizontal {{
        background: transparent; border: 0; height: 12px; margin: 0;
    }}
    QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
        background: {subtle_strong}; border-radius: 5px; margin: 3px;
        min-height: 32px; min-width: 32px;
    }}
    QScrollBar::handle:hover {{ background: {muted_text}; }}
    QScrollBar::add-line, QScrollBar::sub-line {{
        background: transparent; border: 0; width: 0; height: 0;
    }}
    QScrollBar::add-page, QScrollBar::sub-page {{
        background: transparent;
    }}

    QPushButton {{
        background: {subtle}; color: {text};
        border: 1px solid {hairline}; border-radius: 6px;
        padding: 6px 16px;
    }}
    QPushButton:hover {{ background: {subtle_strong}; }}
    QPushButton:pressed {{ background: {subtle_strong}; }}
    QPushButton:default {{
        background: {highlight}; color: {highlight_text};
        border-color: {highlight};
    }}
    QPushButton:default:hover {{
        background: {accent_hover}; border-color: {accent_hover};
    }}

    QToolTip {{
        background: {window}; color: {text};
        border: 1px solid {hairline}; border-radius: 6px; padding: 4px 8px;
    }}
    """
