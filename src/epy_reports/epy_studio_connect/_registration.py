"""Registration and launch hint, stated by the application itself.

Studio's installer calls ``--register`` on every application that claims a
document type. An application that authors no document type claims
nothing, and this module says so out loud rather than returning silence:
"register ran and did nothing" and "register never ran" must not look the
same from the installer's log.

Nothing here imports Qt, and nothing here writes the registry: building
the entries is pure string work, so the whole contract is testable without
a display and without touching a real machine.
"""

from __future__ import annotations

from typing import Any

from epy_reports.epy_studio_connect._manifest import manifest

__all__ = ["launch_hint", "register", "unregister"]


def register(argv: list[str] | None = None) -> list[str]:
    """Register this application's document types, or say it claims none.

    Args:
        argv: The installer's arguments, inspected for ``--as-default``.

    Returns:
        One line per thing done, for the installer to print. An
        application that claims nothing returns a single line saying so.
    """
    context = list(argv or [])
    entry = manifest()
    if not entry.registers:
        return [
            f"{entry.app_id}: claims no document type; nothing to "
            f"register."
        ]
    as_default = "--as-default" in context
    mode = "default" if as_default and entry.claims_default else "openwith"
    lines = [
        f"{entry.app_id}: registers {','.join(entry.document_types)} as "
        f"{mode}."
    ]
    lines.extend(
        f"  .{ext} -> {entry.app_id}" for ext in entry.document_types
    )
    return lines


def unregister() -> list[str]:
    """Remove this application's registration, or say there is none.

    Returns:
        One line per thing removed. An application that claims nothing
        returns a single line saying so, so a caller can tell an absent
        registration from a failed one.
    """
    entry = manifest()
    if not entry.registers:
        return [
            f"{entry.app_id}: claims no document type; nothing was "
            f"registered to remove."
        ]
    return [
        f"{entry.app_id}: registration removed for "
        f"{','.join(entry.document_types)}."
    ]


def launch_hint() -> dict[str, Any]:
    """Return the launch hint this application wants Studio to pass.

    An application that needs no environment hint returns a small mapping
    naming itself and its entry point; the launcher then starts it
    exactly as any other, and the mapping is JSON-ready so the launcher
    forwards it without importing anything from this package.
    """
    entry = manifest()
    return {
        "app_id": entry.app_id,
        "entry_point": entry.entry_point,
    }
