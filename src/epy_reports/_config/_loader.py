"""Canonical ``.epyson`` loader for epy_reports's bundled theme assets.

Every raw read of a theme layout, palette, or user-saved theme
``.epyson`` file goes through this module -- no other module should
hand-build a ``Path``/``importlib.resources`` lookup and call
``json.load``/``read_text`` directly for these assets. Business logic
(Theme construction, color math, Qt styling) lives in
``epy_reports._core.epyson``, which consumes these loaders.
"""
from __future__ import annotations

import json
from importlib import resources
from pathlib import Path
from typing import Any

ASSETS_PACKAGE = "epy_reports._config._assets.themes"

# Files in the themes/ asset folder that are not themable layouts.
NON_LAYOUT_FILES = frozenset({"colors.epyson", "translations.epyson"})


def read_asset_json(filename: str) -> dict[str, Any]:
    """Load and parse ``filename`` from the bundled themes asset package.

    Args:
        filename: Asset filename (e.g. ``"corporate.epyson"``,
            ``"colors.epyson"``).

    Returns:
        Parsed JSON content.

    Raises:
        FileNotFoundError: If ``filename`` does not exist in the bundled
            asset package -- a broken/incomplete install, never silently
            substituted with an empty mapping.
    """
    asset = resources.files(ASSETS_PACKAGE).joinpath(filename)
    try:
        text = asset.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"epy_reports theme asset '{filename}' not found in package "
            f"'{ASSETS_PACKAGE}'. Reinstall epy_reports or check the "
            f"bundled _config/_assets/themes/ folder -- no fallback data "
            f"exists."
        ) from exc
    return json.loads(text)


def load_color_palettes() -> dict[str, dict[str, Any]]:
    """Load the named colour palettes from the bundled ``colors.epyson``.

    Returns:
        ``color_palettes`` mapping: palette name -> RGB triplets by tier
        (``primary``..``senary``).

    Raises:
        FileNotFoundError: If ``colors.epyson`` is missing from the
            bundled asset package. Callout colors are visual/normative
            data with no safe empty substitute -- a missing catalog must
            surface, not silently degrade every callout to uncolored
            defaults.
    """
    data = read_asset_json("colors.epyson")
    return data.get("color_palettes", {})


def list_bundled_layout_files() -> list[str]:
    """Return bundled theme layout filenames.

    Excludes ``colors.epyson``/``translations.epyson`` (shared data, not
    themable layouts).
    """
    pkg = resources.files(ASSETS_PACKAGE)
    return sorted(
        entry.name
        for entry in pkg.iterdir()
        if entry.name.endswith(".epyson")
        and entry.name not in NON_LAYOUT_FILES
    )


def read_user_theme_json(path: Path) -> dict[str, Any]:
    """Load and parse a user theme ``.epyson`` file from disk.

    Args:
        path: Path to the user theme file.

    Returns:
        Parsed JSON content.

    Raises:
        OSError: If ``path`` cannot be read.
        json.JSONDecodeError: If ``path`` does not contain valid JSON.
    """
    return json.loads(path.read_text(encoding="utf-8"))


def write_user_theme_json(path: Path, payload: dict[str, Any]) -> None:
    """Serialize ``payload`` as pretty JSON and write it to ``path``."""
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def list_user_theme_files(directory: Path) -> list[Path]:
    """Return user theme ``.epyson`` file paths under ``directory``.

    Returns an empty list (not an error) when ``directory`` does not
    exist yet -- "no user themes saved" is a genuinely optional state,
    unlike a missing bundled asset.
    """
    if not directory.is_dir():
        return []
    return sorted(directory.glob("*.epyson"))
