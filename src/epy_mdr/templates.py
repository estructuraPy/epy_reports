"""Named configuration templates (presets) persisted as JSON files.

A template bundles a small set of document-publishing settings — the
visual theme plus the front-matter keys ``csl``, ``footer``,
``page-numbers``, ``cover`` and ``logo`` — so a user can capture a
house style once and re-apply it to any document.

Each template is stored as a single JSON file under the user's
application config directory::

    <AppConfigLocation>/epy_mdr/templates/<name>.json

The JSON is written as a single-line leaf object (no pretty-print
indentation), matching the project's data-file house style. The
functions take an optional ``base_dir`` so they can be exercised in
unit tests against a temporary directory.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

# Characters allowed in a template name (used as a file stem).
_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9 _-]+")


def _config_base_dir() -> Path:
    """Return the default templates directory under the config location.

    Resolved via ``QStandardPaths.AppConfigLocation`` so it lands in the
    OS-appropriate per-user config folder.
    """
    from PySide6.QtCore import QStandardPaths  # noqa: PLC0415

    root = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppConfigLocation
    )
    return Path(root) / "epy_mdr" / "templates"


def _resolve_base(base_dir: Path | None) -> Path:
    """Return ``base_dir`` or the default config location."""
    return base_dir if base_dir is not None else _config_base_dir()


def _safe_name(name: str) -> str:
    """Sanitize a template name into a safe file stem.

    Strips characters outside ``[A-Za-z0-9 _-]`` and surrounding
    whitespace so the name maps cleanly to a filename.
    """
    cleaned = _SAFE_NAME_RE.sub("", name).strip()
    return cleaned


def list_templates(base_dir: Path | None = None) -> list[str]:
    """Return the sorted names of saved templates.

    Args:
        base_dir: Optional override of the storage directory; defaults
            to the user config location.

    Returns:
        Sorted list of template names (file stems without ``.json``).
    """
    root = _resolve_base(base_dir)
    if not root.is_dir():
        return []
    return sorted(p.stem for p in root.glob("*.json"))


def load_template(name: str, base_dir: Path | None = None) -> dict:
    """Load a saved template by name.

    Args:
        name: Template name.
        base_dir: Optional override of the storage directory.

    Returns:
        The deserialized template dict.

    Raises:
        FileNotFoundError: When no template with that name exists.
    """
    root = _resolve_base(base_dir)
    path = root / f"{_safe_name(name)}.json"
    if not path.is_file():
        raise FileNotFoundError(f"No template named {name!r}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_template(
    name: str, data: dict, base_dir: Path | None = None
) -> None:
    """Persist ``data`` as a named template.

    The dict is serialized as a single-line JSON object (no indent),
    matching the project's leaf-object data-file convention.

    Args:
        name: Template name (sanitized into a filename).
        data: Leaf dict of settings to store.
        base_dir: Optional override of the storage directory.

    Raises:
        ValueError: When ``name`` sanitizes to an empty string.
    """
    safe = _safe_name(name)
    if not safe:
        raise ValueError("Template name must contain a usable character")
    root = _resolve_base(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(
        data, ensure_ascii=False, separators=(", ", ": ")
    )
    (root / f"{safe}.json").write_text(payload, encoding="utf-8")


def delete_template(name: str, base_dir: Path | None = None) -> None:
    """Delete a saved template by name.

    Silently does nothing when the template does not exist.

    Args:
        name: Template name.
        base_dir: Optional override of the storage directory.
    """
    root = _resolve_base(base_dir)
    path = root / f"{_safe_name(name)}.json"
    path.unlink(missing_ok=True)
