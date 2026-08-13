"""Tests for the canonical ``.epyson`` loader (``_config._loader``).

Covers the bundled-asset/user-theme read/write primitives and, in
particular, the fail-loud contract for a missing bundled asset -- no
silent empty-dict substitution.
"""

from __future__ import annotations

import json

import pytest

from epy_reports._config import _loader

# ---------------------------------------------------------------------------
# read_asset_json
# ---------------------------------------------------------------------------


def test_read_asset_json_loads_bundled_layout():
    """A real bundled layout parses into a dict with the expected keys."""
    data = _loader.read_asset_json("corporate.epyson")
    assert isinstance(data, dict)
    assert "palette" in data


def test_read_asset_json_missing_file_raises():
    """A missing bundled asset raises FileNotFoundError naming the file."""
    with pytest.raises(FileNotFoundError, match="does_not_exist.epyson"):
        _loader.read_asset_json("does_not_exist.epyson")


# ---------------------------------------------------------------------------
# load_color_palettes
# ---------------------------------------------------------------------------


def test_load_color_palettes_returns_named_palettes():
    """The bundled colors.epyson resolves to a non-empty palette mapping."""
    palettes = _loader.load_color_palettes()
    assert isinstance(palettes, dict)
    assert palettes


def test_load_color_palettes_missing_asset_raises(monkeypatch):
    """A missing colors.epyson raises instead of silently returning {}.

    Regression guard for the fixed anti-pattern: the old
    ``_core.epyson._load_palettes`` caught ``FileNotFoundError`` and
    returned ``{}``, silently emptying every theme's callout colors.
    """
    def _boom(_filename):
        raise FileNotFoundError("simulated missing colors.epyson")

    monkeypatch.setattr(_loader, "read_asset_json", _boom)
    with pytest.raises(FileNotFoundError):
        _loader.load_color_palettes()


# ---------------------------------------------------------------------------
# list_bundled_layout_files
# ---------------------------------------------------------------------------


def test_list_bundled_layout_files_excludes_non_layouts():
    """The palette/translation files are excluded from the layout listing."""
    files = _loader.list_bundled_layout_files()
    assert "colors.epyson" not in files
    assert "translations.epyson" not in files
    assert "corporate.epyson" in files


# ---------------------------------------------------------------------------
# user theme read/write/list
# ---------------------------------------------------------------------------


def test_write_then_read_user_theme_json_round_trips(tmp_path):
    """A written user theme file reads back with the same payload."""
    path = tmp_path / "custom.epyson"
    payload = {"layout_name": "custom", "display_name": "Custom"}
    _loader.write_user_theme_json(path, payload)
    assert _loader.read_user_theme_json(path) == payload


def test_read_user_theme_json_bad_json_raises(tmp_path):
    """Malformed JSON on disk raises JSONDecodeError, not silently ignored."""
    path = tmp_path / "broken.epyson"
    path.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        _loader.read_user_theme_json(path)


def test_list_user_theme_files_empty_dir_absent(tmp_path):
    """A non-existent user-theme dir yields an empty list, not an error."""
    assert _loader.list_user_theme_files(tmp_path / "does_not_exist") == []


def test_list_user_theme_files_lists_epyson_only(tmp_path):
    """Only ``.epyson`` files in the directory are listed, sorted by name."""
    (tmp_path / "b.epyson").write_text("{}", encoding="utf-8")
    (tmp_path / "a.epyson").write_text("{}", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("ignore me", encoding="utf-8")
    files = _loader.list_user_theme_files(tmp_path)
    assert [p.name for p in files] == ["a.epyson", "b.epyson"]
