"""Small QPainter previews for the slide-layout picker and theme gallery.

No web rendering is involved: a *layout* preview is a neutral schematic of the
slide regions (so the user reads the slide TYPE at a glance), and a *theme*
preview is a colour/typography swatch built straight from the :class:`Theme`
palette (so the user reads the visual STYLE). Both are cheap QPainter draws
that need only a running ``QApplication``, so the pickers stay instant and the
previews are unit-testable offscreen.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap

from epy_reports.themes_base import Theme

# Default thumbnail sizes used by the pickers.
LAYOUT_THUMB = QSize(104, 64)
THEME_THUMB = QSize(176, 108)

# Neutral schematic palette — theme-agnostic on purpose: the layout picker
# chooses a *type*, not a *style*, so the schematic stays calm and legible.
_CARD_BG = QColor("#ffffff")
_CARD_BORDER = QColor("#c8ced6")
_INK = QColor("#c2c8d0")  # generic body-text bars
_INK_STRONG = QColor("#9aa3ad")
_ACCENT = QColor("#4c6ef5")  # title / active region
_PANEL = QColor("#e4e8ee")  # image placeholder
_PANEL_DARK = QColor("#2b3138")  # code block
_MUTED = QColor("#d7dce2")
_CODE_TOKENS = (QColor("#7aa2f7"), QColor("#9ece6a"), QColor("#e0af68"))


# --------------------------------------------------------------------------- #
# Drawing primitives
# --------------------------------------------------------------------------- #
def _rounded(
    p: QPainter, rect: QRectF, color: QColor, radius: float = 3.0
) -> None:
    """Fill a rounded rectangle with ``color`` (no outline)."""
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(color)
    p.drawRoundedRect(rect, radius, radius)


def _bars(
    p: QPainter,
    x: float,
    y: float,
    w: float,
    *,
    n: int,
    color: QColor,
    h: float = 3.0,
    gap: float = 4.0,
    shrink_last: bool = True,
) -> None:
    """Draw ``n`` stacked text bars; the last one is shorter when asked."""
    for i in range(n):
        bw = w * (0.6 if (shrink_last and i == n - 1) else 1.0)
        _rounded(p, QRectF(x, y + i * (h + gap), bw, h), color, 1.5)


def _draw_layout_body(p: QPainter, c: QRectF, layout_id: str) -> None:
    """Draw the schematic body for ``layout_id`` inside content rect ``c``."""
    x, y, w, h = c.x(), c.y(), c.width(), c.height()
    body_top = y + 11.0
    body_h = h - (body_top - y) - 2.0

    def title(frac: float = 0.62) -> None:
        _rounded(p, QRectF(x, y, w * frac, 5.0), _ACCENT, 2.0)

    if layout_id == "section":
        _rounded(
            p, QRectF(x + w * 0.12, y + h * 0.36, w * 0.76, 7.0), _ACCENT, 3.0
        )
        _rounded(
            p, QRectF(x + w * 0.28, y + h * 0.58, w * 0.44, 4.0), _INK, 2.0
        )
    elif layout_id == "two-column":
        title()
        cw = (w - 6.0) / 2.0
        _rounded(p, QRectF(x, body_top, cw, body_h), _MUTED, 2.0)
        _rounded(p, QRectF(x + cw + 6.0, body_top, cw, body_h), _MUTED, 2.0)
        _bars(p, x + 3, body_top + 3, cw - 6, n=3, color=_INK, h=2.5, gap=3.5)
        _bars(
            p,
            x + cw + 9,
            body_top + 3,
            cw - 6,
            n=3,
            color=_INK,
            h=2.5,
            gap=3.5,
        )
    elif layout_id == "comparison":
        title()
        cw = (w - 6.0) / 2.0
        for cx in (x, x + cw + 6.0):
            _rounded(p, QRectF(cx, body_top, cw, 4.0), _ACCENT, 2.0)
            _bars(p, cx, body_top + 8, cw, n=2, color=_INK, h=2.5, gap=3.5)
    elif layout_id == "image-caption":
        title()
        _rounded(
            p,
            QRectF(x + w * 0.18, body_top, w * 0.64, body_h - 6),
            _PANEL,
            3.0,
        )
        _rounded(p, QRectF(x + w * 0.30, y + h - 5, w * 0.40, 3.0), _INK, 1.5)
    elif layout_id == "image-fullbleed":
        _rounded(p, QRectF(x - 3, y - 3, w + 6, h + 6), _PANEL, 3.0)
        _rounded(p, QRectF(x, y + h * 0.70, w * 0.5, 5.0), _CARD_BG, 2.0)
    elif layout_id == "quote":
        f = QFont()
        f.setPixelSize(max(12, int(h * 0.45)))
        f.setBold(True)
        p.setFont(f)
        p.setPen(_MUTED)
        p.drawText(
            QRectF(x, y - 3, 16, 18), int(Qt.AlignmentFlag.AlignLeft), "“"
        )
        _rounded(
            p,
            QRectF(x + w * 0.10, y + h * 0.42, w * 0.80, 4.0),
            _INK_STRONG,
            2.0,
        )
        _rounded(
            p, QRectF(x + w * 0.20, y + h * 0.58, w * 0.60, 4.0), _INK, 2.0
        )
        _rounded(
            p, QRectF(x + w * 0.55, y + h * 0.78, w * 0.25, 3.0), _ACCENT, 1.5
        )
    elif layout_id == "code":
        title()
        _rounded(p, QRectF(x, body_top, w, body_h), _PANEL_DARK, 3.0)
        for i in range(3):
            _rounded(
                p,
                QRectF(x + 5, body_top + 4 + i * 6, w * (0.5 - i * 0.1), 2.5),
                _CODE_TOKENS[i],
                1.0,
            )
    elif layout_id == "blank":
        pen = QPen(_MUTED)
        pen.setStyle(Qt.PenStyle.DashLine)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(x, y, w, h), 3.0, 3.0)
    elif layout_id in ("big-stat", "stats"):
        title(0.45)
        bw = (w - 12.0) / 3.0
        for i in range(3):
            bx = x + i * (bw + 6.0)
            _rounded(
                p,
                QRectF(bx, body_top + 2, bw, 9.0),
                _ACCENT if i == 1 else _INK_STRONG,
                2.0,
            )
            _rounded(
                p,
                QRectF(bx + bw * 0.15, body_top + 14, bw * 0.7, 3.0),
                _INK,
                1.5,
            )
    elif layout_id == "stat":
        title(0.45)
        bw = w * 0.5
        _rounded(
            p, QRectF(x + (w - bw) / 2, body_top + 2, bw, 11.0), _ACCENT, 2.0
        )
        _rounded(
            p, QRectF(x + w * 0.30, body_top + 16, w * 0.40, 3.0), _INK, 1.5
        )
    elif layout_id == "lead":
        _rounded(
            p, QRectF(x, y + h * 0.24, w * 0.92, 6.0), _INK_STRONG, 2.5
        )
        _rounded(p, QRectF(x, y + h * 0.46, w * 0.80, 4.0), _INK, 2.0)
        _rounded(p, QRectF(x, y + h * 0.62, w * 0.55, 4.0), _INK, 2.0)
    elif layout_id == "badge":
        title(0.55)
        _rounded(p, QRectF(x, body_top + 4, w * 0.28, 7.0), _ACCENT, 3.5)
        _rounded(
            p, QRectF(x + w * 0.32, body_top + 5, w * 0.50, 5.0), _INK, 2.0
        )
    elif layout_id == "card":
        _rounded(p, QRectF(x, body_top - 4, w, body_h + 4), _MUTED, 3.0)
        _rounded(p, QRectF(x + 4, body_top, w * 0.55, 4.0), _ACCENT, 2.0)
        _bars(p, x + 4, body_top + 8, w - 8, n=2, color=_INK, h=2.5, gap=3.5)
    elif layout_id == "agenda":
        title(0.40)
        for i in range(3):
            yy = body_top + i * 7.0
            _rounded(p, QRectF(x, yy, 5.0, 5.0), _ACCENT, 1.5)
            _rounded(p, QRectF(x + 8, yy + 1, w * 0.7, 3.0), _INK, 1.5)
    elif layout_id == "cards":
        title(0.45)
        cw = (w - 12.0) / 3.0
        for i in range(3):
            bx = x + i * (cw + 6.0)
            _rounded(p, QRectF(bx, body_top, cw, body_h), _MUTED, 3.0)
            _rounded(
                p, QRectF(bx + 3, body_top + 3, cw - 6, 3.0), _ACCENT, 1.5
            )
    elif layout_id == "timeline":
        title(0.40)
        lx = x + 4.0
        pen = QPen(_MUTED)
        pen.setWidthF(2.0)
        p.setPen(pen)
        p.drawLine(QPointF(lx, body_top), QPointF(lx, y + h - 2))
        for i in range(3):
            yy = body_top + i * 8.0
            _rounded(p, QRectF(lx - 2, yy, 5.0, 5.0), _ACCENT, 2.5)
            _rounded(p, QRectF(lx + 9, yy + 1, w * 0.6, 3.0), _INK, 1.5)
    elif layout_id == "image-left":
        title()
        iw = w * 0.40
        _rounded(p, QRectF(x, body_top, iw, body_h), _PANEL, 3.0)
        _bars(
            p,
            x + iw + 6,
            body_top + 1,
            w - iw - 6,
            n=3,
            color=_INK,
            h=2.5,
            gap=4.0,
        )
    elif layout_id == "image-right":
        title()
        iw = w * 0.40
        _bars(p, x, body_top + 1, w - iw - 6, n=3, color=_INK, h=2.5, gap=4.0)
        _rounded(p, QRectF(x + w - iw, body_top, iw, body_h), _PANEL, 3.0)
    elif layout_id == "quote-portrait":
        pw = w * 0.30
        _rounded(p, QRectF(x, y, pw, h), _PANEL, 3.0)
        tw = w - pw - 6.0
        _rounded(
            p, QRectF(x + pw + 6, y + h * 0.20, tw, 4.0), _INK_STRONG, 2.0
        )
        _rounded(p, QRectF(x + pw + 6, y + h * 0.40, tw * 0.8, 4.0), _INK, 2.0)
        _rounded(
            p, QRectF(x + pw + 6, y + h * 0.62, tw * 0.5, 3.0), _ACCENT, 1.5
        )
    else:  # "title-content" and any unknown id → title + bullets
        title()
        _bars(p, x, body_top, w * 0.85, n=3, color=_INK)


def layout_preview(layout_id: str, size: QSize = LAYOUT_THUMB) -> QPixmap:
    """Return a neutral schematic thumbnail of ``layout_id`` (slide type)."""
    pix = QPixmap(size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    try:
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w, h = float(size.width()), float(size.height())
        m = 3.0
        card = QRectF(m, m, w - 2 * m, h - 2 * m)
        _rounded(p, card, _CARD_BG, 5.0)
        _draw_layout_body(p, card.adjusted(7, 6, -7, -6), layout_id)
        pen = QPen(_CARD_BORDER)
        pen.setWidthF(1.0)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(card, 5.0, 5.0)
    finally:
        p.end()
    return pix


# --------------------------------------------------------------------------- #
# Theme swatch
# --------------------------------------------------------------------------- #
def _color(value: str | None, fallback: str | QColor) -> QColor:
    """Return a valid ``QColor`` from ``value`` (hex) or ``fallback``."""
    if value:
        c = QColor(value)
        if c.isValid():
            return c
    return fallback if isinstance(fallback, QColor) else QColor(fallback)


def _primary_family(stack: str | None) -> str:
    """Return the first family from a CSS ``font-family`` stack string."""
    if not stack:
        return ""
    return stack.split(",")[0].strip().strip('"').strip("'")


def theme_preview(theme: Theme, size: QSize = THEME_THUMB) -> QPixmap:
    """Return a colour/typography swatch thumbnail for ``theme``."""
    cv = theme.css_vars
    qp = theme.qt_palette
    bg = _color(cv.get("bg") or qp.get("Window"), "#ffffff")
    fg = _color(cv.get("fg") or qp.get("WindowText"), "#222222")
    muted = _color(cv.get("fg-muted"), fg)
    heading = _color(cv.get("heading-color") or qp.get("WindowText"), fg)
    accent = _color(cv.get("link") or qp.get("Highlight"), "#4c6ef5")
    border = _color(cv.get("border"), "#cccccc")
    code_bg = _color(cv.get("bg-soft") or cv.get("code-bg"), "#f0f0f0")
    head_family = _primary_family(
        cv.get("font-family-headings") or cv.get("font-family-text")
    )

    pix = QPixmap(size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    try:
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w, h = float(size.width()), float(size.height())
        m = 3.0
        card = QRectF(m, m, w - 2 * m, h - 2 * m)
        _rounded(p, card, bg, 7.0)

        inner = card.adjusted(11, 14, -11, -10)
        x, y, iw, ih = inner.x(), inner.y(), inner.width(), inner.height()

        font = QFont(head_family) if head_family else QFont()
        font.setPixelSize(max(12, int(ih * 0.42)))
        font.setBold(True)
        p.setFont(font)
        p.setPen(heading)
        p.drawText(
            QRectF(x, y, iw, ih * 0.5),
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop),
            "Aa",
        )
        _rounded(p, QRectF(x, y + ih * 0.50, iw * 0.42, 3.0), accent, 1.5)
        _rounded(p, QRectF(x, y + ih * 0.64, iw * 0.90, 3.5), muted, 1.5)
        _rounded(p, QRectF(x, y + ih * 0.76, iw * 0.72, 3.5), muted, 1.5)
        _rounded(p, QRectF(x, y + ih * 0.88, iw * 0.30, 6.0), code_bg, 2.0)

        dots = [accent, heading, _color(cv.get("table-header-bg"), accent)]
        for i, col in enumerate(dots):
            _rounded(
                p,
                QRectF(card.right() - 13 - i * 9, card.y() + 9, 6.0, 6.0),
                col,
                3.0,
            )

        pen = QPen(border)
        pen.setWidthF(1.0)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(card, 7.0, 7.0)
    finally:
        p.end()
    return pix
