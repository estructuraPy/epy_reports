"""One application's Studio identity, stated from the application side.

The values here are the same ones ``epy_studio``'s ``apps.epyson``
carries for this application -- the same ``id``, the same ``display``,
the same ``register`` mode. The duplication is deliberate and temporary:
until Studio reads this package, the launcher's catalog stays the single
source of the list, and a build can assert the two agree rather than let
them drift. Stating it here is what makes the contract reviewable from
the application's own repository.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

__all__ = ["MANIFEST", "StudioManifest", "manifest"]

_REGISTER_MODES = frozenset({"default", "openwith", "none"})


@dataclass(frozen=True)
class StudioManifest:
    """What Studio needs to know about one application.

    Attributes:
        app_id: Executable stem, and the package it is built from.
        display: What a person reads in the selector.
        description: One line saying what the application is for.
        component: The Inno Setup component that installs it.
        register: One of ``"default"``, ``"openwith"`` or ``"none"``.
            An application that authors no document type claims nothing.
        document_types: The extensions it would handle, when it claims
            any. Empty when ``register`` is ``"none"``.
        icon: The executable's icon, relative to the package root.
        entry_point: The module Studio runs to open the window.
    """

    app_id: str
    display: str
    description: str
    component: str
    register: str
    document_types: tuple[str, ...] = ()
    icon: str = ""
    entry_point: str = ""

    def __post_init__(self) -> None:
        """Refuse a register mode nobody handles, or an implied claim."""
        if self.register not in _REGISTER_MODES:
            raise ValueError(
                f"{self.app_id}: register is {self.register!r}, which is "
                f"none of {sorted(_REGISTER_MODES)}. A mode nobody "
                f"handles would register nothing and say nothing."
            )
        if self.register == "none" and self.document_types:
            raise ValueError(
                f"{self.app_id}: register is 'none' but document_types is "
                f"not empty. An application that claims nothing must "
                f"claim no document type."
            )

    @property
    def claims_default(self) -> bool:
        """Whether this application may register as the default handler."""
        return self.register == "default"

    @property
    def registers(self) -> bool:
        """Whether this application registers any document type at all."""
        return self.register != "none"

    def as_dict(self) -> dict[str, Any]:
        """Return the JSON-ready mapping Studio would read."""
        return {
            "id": self.app_id,
            "display": self.display,
            "description": self.description,
            "component": self.component,
            "register": self.register,
            "document_types": list(self.document_types),
            "icon": self.icon,
            "entry_point": self.entry_point,
        }


MANIFEST = StudioManifest(
    app_id="epy_reports",
    display="ePy Reports",
    description=(
        "Technical reports - live preview, exports to PDF, Word and "
        "HTML"
    ),
    component="reports",
    register="default",
    document_types=("md", "markdown", "qmd",),
    icon="_core/_packaging/assets_build/epy_reports.ico",
    entry_point="epy_reports.app",
)
"""ePy Reports's identity as ePy Studio's selector sees it."""


def manifest() -> StudioManifest:
    """Return this application's Studio manifest."""
    return MANIFEST
