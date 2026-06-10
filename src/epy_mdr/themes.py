"""Theme catalogue assembled from the ePy_docs layouts (``.epyson``).

Every theme — for both the Qt chrome and the rendered preview — is
derived from a layout file under ``assets/themes/*.epyson`` so that
``epy_mdr`` mirrors the visual identities defined by the document
pipeline.

Public API:

* :data:`THEMES` — ``dict[id, Theme]`` keyed by ``layout_name``.
* :data:`DEFAULT_THEME_ID` — fallback theme used on first launch.
* :func:`get` — look up a theme by id with a safe fallback.
* :func:`apply_palette` — repaint the Qt application using a theme.
* :func:`qss_for` — build a Qt stylesheet for a theme so widgets
  beyond what ``QPalette`` reaches still follow the visual identity.
"""

from __future__ import annotations

from epy_mdr.epyson import apply_palette, load_all_themes, qss_for
from epy_mdr.themes_base import Theme

DEFAULT_THEME_ID = "corporate"

THEMES: dict[str, Theme] = load_all_themes()


def get(theme_id: str | None) -> Theme:
    """Return the theme for ``theme_id`` with a safe fallback.

    The fallback order is: requested id → :data:`DEFAULT_THEME_ID` →
    any registered theme. The function never raises so the GUI can
    boot even if every layout file is corrupt.
    """
    if theme_id and theme_id in THEMES:
        return THEMES[theme_id]
    if DEFAULT_THEME_ID in THEMES:
        return THEMES[DEFAULT_THEME_ID]
    if THEMES:
        return next(iter(THEMES.values()))
    # Last resort: an empty theme. Lets the app boot without colours.
    return Theme(
        id="fallback",
        display_name="Fallback",
        qt_palette={},
        css_vars={},
    )


__all__ = [
    "DEFAULT_THEME_ID",
    "THEMES",
    "Theme",
    "apply_palette",
    "get",
    "qss_for",
]
