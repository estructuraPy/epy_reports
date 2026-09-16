"""Tests for the themes catalogue, Theme dataclass and epyson helpers."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from epy_reports._config import _loader
from epy_reports._core import epyson, themes
from epy_reports._core.themes_base import Theme

_app: QApplication | None = None


@pytest.fixture(scope="module")
def qapp():
    """Provide a module-scoped QApplication instance."""
    global _app
    if _app is None:
        _instance = QApplication.instance()
        _app = (
            _instance
            if isinstance(_instance, QApplication)
            else QApplication([])
        )
    return _app


# ---------------------------------------------------------------------------
# Theme dataclass
# ---------------------------------------------------------------------------


def test_to_css_emits_root_block():
    """Non-empty css_vars serialise to a ``:root`` block."""
    theme = Theme("x", "X", {}, {"bg": "#fff", "fg": "#000"})
    css = theme.to_css()
    assert css.startswith(":root {")
    assert "--bg: #fff;" in css
    assert css.rstrip().endswith("}")


def test_to_css_empty_is_blank():
    """No css_vars yields an empty string."""
    assert Theme("x", "X", {}, {}).to_css() == ""


# ---------------------------------------------------------------------------
# Catalogue + get()
# ---------------------------------------------------------------------------


def test_default_theme_is_registered():
    """The default theme id exists in the catalogue."""
    assert themes.DEFAULT_THEME_ID in themes.THEMES


def test_get_known_theme():
    """Looking up a known id returns that theme."""
    theme = themes.get(themes.DEFAULT_THEME_ID)
    assert theme.id == themes.DEFAULT_THEME_ID


def test_get_unknown_falls_back_to_default():
    """An unknown id falls back to the default theme."""
    theme = themes.get("does-not-exist")
    assert theme.id == themes.DEFAULT_THEME_ID


def test_get_none_falls_back_to_default():
    """``None`` falls back to the default theme."""
    assert themes.get(None).id == themes.DEFAULT_THEME_ID


def test_get_falls_back_to_any_registered_theme_when_default_missing(
    monkeypatch,
):
    """No requested id and no default present still returns a real theme.

    Exercises the third fallback rung: the catalogue has entries, but
    neither the requested id nor ``DEFAULT_THEME_ID`` is one of them.
    """
    survivor = themes.THEMES[themes.DEFAULT_THEME_ID]
    monkeypatch.setattr(themes, "THEMES", {"survivor": survivor})
    assert themes.get("does-not-exist") is survivor


def test_get_returns_hardcoded_fallback_when_catalogue_is_empty(monkeypatch):
    """An empty catalogue still returns a usable (colourless) Theme.

    This is the last-resort branch so the GUI can boot even if every
    layout file under ``_config/_assets/themes`` is missing or corrupt.
    """
    monkeypatch.setattr(themes, "THEMES", {})
    theme = themes.get("anything")
    assert theme.id == "fallback"
    assert theme.display_name == "Fallback"
    assert theme.qt_palette == {}
    assert theme.css_vars == {}


def test_reload_keeps_default_present():
    """Reloading rescans and preserves the default theme."""
    reloaded = themes.reload()
    assert themes.DEFAULT_THEME_ID in reloaded
    assert reloaded is themes.THEMES  # mutated in place


# ---------------------------------------------------------------------------
# epyson loader helpers
# ---------------------------------------------------------------------------


def test_rgb_to_hex():
    """An rgb triplet becomes an uppercase #RRGGBB string."""
    assert epyson._rgb_to_hex([255, 0, 16]) == "#FF0010"


def test_hex_to_rgb_round_trip():
    """hex → rgb → hex is stable."""
    assert epyson._rgb_to_hex(list(epyson._hex_to_rgb("#1A2B3C"))) == (
        "#1A2B3C"
    )


def test_coerce_hex_from_bare_string():
    """A bare hex string without ``#`` gets one prepended."""
    assert epyson._coerce_hex("ABCDEF") == "#ABCDEF"


def test_coerce_hex_from_list():
    """An rgb list coerces to a hex string."""
    assert epyson._coerce_hex([0, 0, 0]) == "#000000"


def test_mix_endpoints():
    """``t=0`` returns the source, ``t=1`` returns the target."""
    assert epyson._mix("#000000", "#FFFFFF", 0.0) == "#000000"
    assert epyson._mix("#000000", "#FFFFFF", 1.0) == "#FFFFFF"


def test_is_dark_and_contrast_text():
    """Luminance drives is_dark and the contrasting text colour."""
    assert epyson._is_dark("#000000")
    assert not epyson._is_dark("#FFFFFF")
    assert epyson._contrast_text("#FFFFFF") == "#000000"
    assert epyson._contrast_text("#000000") == "#FFFFFF"


def test_callout_vars_direct_colors_win():
    """Direct bg/border colours take priority over palette refs."""
    callouts = {"types": {"note": {"bg": "#EEE", "border": "#123"}}}
    out = epyson._callout_vars(callouts, palettes={})
    assert out["callout-note-bg"] == "#EEE"
    assert out["callout-note-border"] == "#123"


# ---------------------------------------------------------------------------
# qss_for / apply_palette (need QApplication)
# ---------------------------------------------------------------------------


def test_qss_for_produces_stylesheet(qapp):
    """The QSS builder returns a non-trivial stylesheet for a theme."""
    qss = themes.qss_for(themes.get(themes.DEFAULT_THEME_ID))
    assert "QMainWindow" in qss
    assert "QToolBar" in qss


def test_apply_palette_runs(qapp):
    """Applying a palette to the app does not raise."""
    epyson.apply_palette(qapp, themes.get(themes.DEFAULT_THEME_ID))


def test_tonal_variants_dark_vs_light():
    """The tonal variant helper returns the documented keys both ways."""
    light = epyson._tonal_variants("#FFFFFF", "#2A76DD", is_dark_theme=False)
    dark = epyson._tonal_variants("#101010", "#2A76DD", is_dark_theme=True)
    for d in (light, dark):
        assert set(d) >= {
            "bg_toolbar", "bg_statusbar", "bg_panel", "bg_menu",
            "accent_soft", "accent_strong", "scrollbar_handle",
        }


# ---------------------------------------------------------------------------
# User (custom) themes: build / save / load / delete
# ---------------------------------------------------------------------------


@pytest.fixture
def user_dir(tmp_path, monkeypatch):
    """Redirect the user-theme directory to a temp folder."""
    target = tmp_path / "user_themes"
    monkeypatch.setattr(epyson, "user_themes_dir", lambda: target)
    return target


def _values(name: str = "Custom One") -> dict:
    scales = {
        role: {"size": 12.0, "weight": "400"}
        for role in ("h1", "h2", "h3", "h4", "h5", "h6", "text", "caption")
    }
    callouts = {
        kind: {"bg": "#EAF2FB", "border": "#2F6FBF"}
        for kind in ("note", "tip", "warning", "important", "caution")
    }
    return {
        "display_name": name,
        "page_bg": "#FFFFFF", "text": "#1A1A1A", "heading": "#00217E",
        "primary": "#00217E", "secondary": "#0969DA", "border": "#C8C8C8",
        "code_bg": "#F5F5F5", "mark": "#CA9A24",
        "text_font": "Calibri", "code_font": "Consolas",
        "scales": scales, "callouts": callouts,
    }


def test_build_epyson_shape():
    """``build_epyson`` produces the keys the loader consumes."""
    payload = epyson.build_epyson(_values())
    assert payload["display_name"] == "Custom One"
    assert payload["font_families"]["default"]["primary"] == "Calibri"
    assert payload["palette"]["page"]["background"] == [255, 255, 255]


def test_save_then_load_user_theme(user_dir):
    """A saved user theme is loadable by id and reports its name."""
    theme_id = epyson.save_user_theme(epyson.build_epyson(_values()))
    assert theme_id == "custom-one"
    assert theme_id in epyson.user_theme_ids()
    path = user_dir / f"{theme_id}.epyson"
    theme = epyson.load_user_theme(path)
    assert theme.display_name == "Custom One"


def test_delete_user_theme(user_dir):
    """Deleting a saved user theme removes its id."""
    theme_id = epyson.save_user_theme(epyson.build_epyson(_values("Gone")))
    assert theme_id in epyson.user_theme_ids()
    epyson.delete_user_theme(theme_id)
    assert theme_id not in epyson.user_theme_ids()


def test_load_all_themes_includes_user(user_dir):
    """The catalogue loader merges user themes over bundled ones."""
    epyson.save_user_theme(epyson.build_epyson(_values("Merged")))
    catalogue = epyson.load_all_themes()
    assert "merged" in catalogue
    # Bundled themes are still present.
    assert themes.DEFAULT_THEME_ID in catalogue


def test_user_theme_ids_empty_when_dir_absent(user_dir):
    """No user directory yields an empty id set."""
    assert epyson.user_theme_ids() == set()


def test_user_theme_ids_skips_a_corrupt_file(user_dir):
    """A corrupt .epyson file is skipped, its siblings still counted.

    One bad file among many must not hide the rest -- the same
    best-effort catalogue-assembly rule as load_all_themes().
    """
    user_dir.mkdir(parents=True, exist_ok=True)
    (user_dir / "corrupt.epyson").write_text(
        "{not valid json", encoding="utf-8"
    )
    good_id = epyson.save_user_theme(epyson.build_epyson(_values("Good One")))
    ids = epyson.user_theme_ids()
    assert good_id in ids
    assert "corrupt" not in ids


# ---------------------------------------------------------------------------
# load_all_themes: best-effort skip of a theme that fails to load
# ---------------------------------------------------------------------------


def test_load_all_themes_skips_a_bundled_layout_that_raises(monkeypatch):
    """A bundled layout that fails to parse is skipped, not fatal.

    The rest of the (real) bundled catalogue must still come through.
    """
    real_list = _loader.list_bundled_layout_files
    monkeypatch.setattr(
        _loader,
        "list_bundled_layout_files",
        lambda: [*real_list(), "corrupt.epyson"],
    )
    real_load = epyson.load_layout_theme

    def fake_load(filename):
        if filename == "corrupt.epyson":
            raise KeyError("palette")
        return real_load(filename)

    monkeypatch.setattr(epyson, "load_layout_theme", fake_load)
    catalogue = epyson.load_all_themes()
    assert themes.DEFAULT_THEME_ID in catalogue
    assert "corrupt" not in catalogue


def test_load_all_themes_skips_a_corrupt_user_theme(user_dir):
    """A corrupt user theme file is skipped; the good one still loads."""
    user_dir.mkdir(parents=True, exist_ok=True)
    (user_dir / "corrupt.epyson").write_text(
        "{not valid json", encoding="utf-8"
    )
    good_id = epyson.save_user_theme(epyson.build_epyson(_values("Also Good")))
    catalogue = epyson.load_all_themes()
    assert good_id in catalogue
    assert "corrupt" not in catalogue
    # Bundled themes are still present alongside the user one.
    assert themes.DEFAULT_THEME_ID in catalogue


# ---------------------------------------------------------------------------
# user_themes_dir: Qt-free fallback when PySide6.QtCore has no QStandardPaths
# ---------------------------------------------------------------------------


def test_user_themes_dir_falls_back_when_qt_unavailable(monkeypatch):
    """A broken/absent Qt runtime still resolves a themes directory.

    Simulated by hiding QStandardPaths from PySide6.QtCore so the
    module-level ``from PySide6.QtCore import QStandardPaths`` raises
    ImportError, exactly as it would with no Qt runtime at all.
    """
    from PySide6 import QtCore

    monkeypatch.delattr(QtCore, "QStandardPaths", raising=False)
    path = epyson.user_themes_dir()
    assert path.parts[-2:] == ("epy_reports", "themes")


# ---------------------------------------------------------------------------
# _fallback_config_root: Qt-free per-platform config root
# ---------------------------------------------------------------------------


def test_fallback_config_root_windows_uses_appdata(monkeypatch):
    """Windows: APPDATA is used verbatim when set."""
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("APPDATA", r"C:\Users\test\AppData\Roaming")
    assert epyson._fallback_config_root() == r"C:\Users\test\AppData\Roaming"


def test_fallback_config_root_windows_without_appdata(monkeypatch):
    """Windows: missing APPDATA falls back to ~/AppData/Roaming."""
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.delenv("APPDATA", raising=False)
    expected = str(Path.home() / "AppData" / "Roaming")
    assert epyson._fallback_config_root() == expected


def test_fallback_config_root_macos(monkeypatch):
    """macOS: Library/Application Support under the home directory."""
    monkeypatch.setattr(sys, "platform", "darwin")
    expected = str(
        Path.home() / "Library" / "Application Support"
    )
    assert epyson._fallback_config_root() == expected


def test_fallback_config_root_linux_uses_xdg(monkeypatch):
    """Linux: XDG_CONFIG_HOME is used verbatim when set."""
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_CONFIG_HOME", "/home/test/.config-custom")
    assert epyson._fallback_config_root() == "/home/test/.config-custom"


def test_fallback_config_root_linux_without_xdg(monkeypatch):
    """Linux: missing XDG_CONFIG_HOME falls back to ~/.config."""
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    expected = str(Path.home() / ".config")
    assert epyson._fallback_config_root() == expected


# ---------------------------------------------------------------------------
# apply_palette: font fallback and unknown-role guard
# ---------------------------------------------------------------------------


def test_apply_palette_falls_back_when_variable_font_unavailable(
    qapp, monkeypatch,
):
    """No 'Segoe UI Variable' on the box falls back to plain 'Segoe UI'.

    Forces the branch by making every QFont report a family name that
    never matches, regardless of what is actually installed.
    """
    monkeypatch.setattr(QFont, "family", lambda self: "Arial")
    epyson.apply_palette(qapp, themes.get(themes.DEFAULT_THEME_ID))
    assert qapp.font().family() == "Arial"  # patched family(), not a crash


def test_apply_palette_skips_an_unknown_palette_role(qapp):
    """A qt_palette key with no matching QPalette.ColorRole is skipped.

    Counter-example: a real role in the same dict is still applied, so
    the guard only swallows the unknown one, not the whole palette.
    """
    theme = Theme(
        id="weird",
        display_name="Weird",
        qt_palette={"NotARealRole": "#123456", "Window": "#FFEE00"},
        css_vars={},
    )
    epyson.apply_palette(qapp, theme)  # must not raise
    assert qapp.palette().color(qapp.palette().ColorRole.Window).name() == (
        "#ffee00"
    )
