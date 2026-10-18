"""The per-app contract with ePy Studio.

The sibling of ``epy_suite_connect``: that package speaks to the other
LIBRARIES, this one speaks to the LAUNCHER. Where ``epy_studio``'s own
``apps.epyson`` says WHICH applications a bundle carries, this package
says, from the application's own side, HOW it connects to Studio --
which document types it claims, which entry point it opens with, and what
hint it wants on launch.

Studio reads nothing here at run time yet; ``apps.epyson`` remains the
single source of the application list. This package is the contract every
sibling now carries, so the knowledge stops living only in the launcher's
catalog, and ``epy_studio_connect.manifest()`` is the one place an
application states its own Studio identity.

Nothing here imports Qt: registration runs on a machine where nothing
needs a display, before any toolkit loads.
"""

from __future__ import annotations

from epy_reports.epy_studio_connect._manifest import (
    StudioManifest,
    manifest,
)
from epy_reports.epy_studio_connect._registration import (
    launch_hint,
    register,
    unregister,
)

__all__ = [
    "StudioManifest",
    "launch_hint",
    "manifest",
    "register",
    "unregister",
]
