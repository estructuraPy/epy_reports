r"""Windows file-association helpers (HKCU only, no admin required).

Two parts:

* ``register(make_default=False)`` — advertise the app in HKCU so it
  appears under "Open with..." for ``.md`` / ``.markdown`` / ``.qmd``
  and as a registered application in *Settings → Default apps*.
* ``register(make_default=True)`` — also writes the legacy default
  handler. **Note:** since Windows 8 the actual default is gated by
  a per-user ``UserChoice`` key signed with a cryptographic hash that
  only Windows itself can produce. No third-party app can set the
  default silently; the user must confirm via the Settings UI or the
  *Open with → Always* dialog. See :func:`open_default_apps_settings`.

All keys live under ``HKEY_CURRENT_USER`` (``Software\Classes``,
``Software\epy_reports`` and ``Software\RegisteredApplications``), so
``unregister`` removes them without touching anything else.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

PROGID = "epy_reports.Document.1"
APP_NAME = "epy_reports"
APP_DESCRIPTION = (
    "Quarto/Markdown editor with live preview and PDF export."
)
APP_KEY = f"Applications\\{APP_NAME}.exe"
EXTENSIONS = (".md", ".markdown", ".qmd")
EXT_DESCRIPTION = "Markdown/Quarto Document"


def _is_windows() -> bool:
    """Return True when running on Windows."""
    return sys.platform == "win32"


def _is_frozen() -> bool:
    """Return True when running from a PyInstaller bundle."""
    return bool(getattr(sys, "frozen", False))


def _launcher_path() -> str:
    """Locate the installed ``epy_reports`` launcher executable.

    Falls back to ``python -m epy_reports`` if no console script was
    installed (e.g. running from a checkout without ``pip install``).
    """
    if _is_frozen():
        return sys.executable
    exe = shutil.which(APP_NAME)
    if exe:
        return exe
    return f'"{sys.executable}" -m {APP_NAME}'


def _icon_source() -> str:
    """Return a ``"path",index`` icon source for the registry."""
    if _is_frozen():
        return f'"{sys.executable}",0'
    exe = shutil.which(APP_NAME)
    if exe:
        return f'"{exe}",0'
    return f'"{Path(sys.executable).with_name("pythonw.exe")}",0'


def _open_command() -> str:
    """Build the shell ``open`` command string for the registry."""
    launcher = _launcher_path()
    if launcher.startswith('"'):
        return f'{launcher} "%1"'
    return f'"{launcher}" "%1"'


def _set_value(key, name, value: str) -> None:
    """Wrapper around ``winreg.SetValueEx`` for REG_SZ string values."""
    import winreg

    winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)


def register(make_default: bool = False) -> list[str]:
    """Register epy_reports for ``.md`` / ``.markdown`` / ``.qmd`` in HKCU.

    Args:
        make_default: When ``True``, write the legacy default handler
            in addition to the Capabilities-based registration.
            **Windows 10/11 will only honour the new default after the
            user confirms it via Settings → Default apps or the Open
            with → "Always use this app" dialog.**

    Returns:
        A list of human-readable lines describing what was changed.

    Raises:
        RuntimeError: If invoked on a non-Windows platform.
    """
    if not _is_windows():
        raise RuntimeError(
            "File association is only supported on Windows."
        )
    import winreg

    cmd = _open_command()
    icon = _icon_source()
    changes: list[str] = []

    # ------------------------------------------------------------------
    # 1. Application entry: shows up in the "Open with" picker.
    # ------------------------------------------------------------------
    app_root = f"Software\\Classes\\{APP_KEY}"
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, app_root) as k:
        _set_value(k, "FriendlyAppName", APP_NAME)
        _set_value(k, "ApplicationName", APP_NAME)
        _set_value(k, "ApplicationDescription", APP_DESCRIPTION)
    with winreg.CreateKey(
        winreg.HKEY_CURRENT_USER, app_root + "\\DefaultIcon"
    ) as k:
        _set_value(k, None, icon)
    with winreg.CreateKey(
        winreg.HKEY_CURRENT_USER, app_root + "\\shell\\open\\command"
    ) as k:
        _set_value(k, None, cmd)
    with winreg.CreateKey(
        winreg.HKEY_CURRENT_USER, app_root + "\\SupportedTypes"
    ) as k:
        for ext in EXTENSIONS:
            _set_value(k, ext, "")
    changes.append(f"Registered application: {app_root}")

    # ------------------------------------------------------------------
    # 2. ProgID: describes how to open documents handled by this app.
    # ------------------------------------------------------------------
    progid_root = f"Software\\Classes\\{PROGID}"
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, progid_root) as k:
        _set_value(k, None, EXT_DESCRIPTION)
        _set_value(k, "FriendlyTypeName", EXT_DESCRIPTION)
    with winreg.CreateKey(
        winreg.HKEY_CURRENT_USER, progid_root + "\\DefaultIcon"
    ) as k:
        _set_value(k, None, icon)
    with winreg.CreateKey(
        winreg.HKEY_CURRENT_USER,
        progid_root + "\\shell\\open\\command",
    ) as k:
        _set_value(k, None, cmd)
    changes.append(f"Registered ProgID: {progid_root}")

    # ------------------------------------------------------------------
    # 3. Capabilities + RegisteredApplications. This is what makes the
    #    app appear in Settings → Default apps as a manageable
    #    application on Windows 10/11.
    # ------------------------------------------------------------------
    caps_root = f"Software\\{APP_NAME}\\Capabilities"
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, caps_root) as k:
        _set_value(k, "ApplicationName", APP_NAME)
        _set_value(k, "ApplicationDescription", APP_DESCRIPTION)
        _set_value(k, "ApplicationIcon", icon)
    with winreg.CreateKey(
        winreg.HKEY_CURRENT_USER, caps_root + "\\FileAssociations"
    ) as k:
        for ext in EXTENSIONS:
            _set_value(k, ext, PROGID)
    with winreg.CreateKey(
        winreg.HKEY_CURRENT_USER,
        "Software\\RegisteredApplications",
    ) as k:
        _set_value(k, APP_NAME, caps_root)
    changes.append(f"Registered application capabilities: {caps_root}")
    changes.append(
        "Listed under Software\\RegisteredApplications "
        f"(value={APP_NAME})"
    )

    # ------------------------------------------------------------------
    # 4. Extensions: advertise via OpenWithProgids (non-invasive)
    #    plus, when requested, the legacy default handler.
    # ------------------------------------------------------------------
    for ext in EXTENSIONS:
        ext_root = f"Software\\Classes\\{ext}"
        owp = ext_root + "\\OpenWithProgids"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, owp) as k:
            _set_value(k, PROGID, "")
        changes.append(
            f"Added {PROGID} to OpenWithProgids for {ext}"
        )

        if make_default:
            with winreg.CreateKey(
                winreg.HKEY_CURRENT_USER, ext_root
            ) as k:
                _set_value(k, None, PROGID)
            changes.append(
                f"Wrote legacy default for {ext} → {PROGID} "
                "(Windows may still require user confirmation)."
            )

    return changes


def open_default_apps_settings() -> bool:
    """Open *Settings → Apps → Default apps* on this app's page.

    Returns:
        ``True`` if the Settings URI was launched, ``False`` on
        non-Windows or when the OS cannot resolve the URI.
    """
    if not _is_windows():
        return False
    # On Win11 this opens the per-app default-app page. On Win10 it
    # opens the global "Default apps" pane.
    uri_specific = (
        f"ms-settings:defaultapps?registeredAppMachineKey="
        f"Software\\RegisteredApplications\\{APP_NAME}"
    )
    uri_fallback = "ms-settings:defaultapps"
    for uri in (uri_specific, uri_fallback):
        try:
            os.startfile(uri)
            return True
        except OSError:
            continue
    return False


def _delete_tree(root, path: str) -> bool:
    """Recursively delete a registry key. Return True on success."""
    import winreg

    try:
        with winreg.OpenKey(root, path) as key:
            while True:
                try:
                    sub = winreg.EnumKey(key, 0)
                except OSError:
                    break
                _delete_tree(root, f"{path}\\{sub}")
        winreg.DeleteKey(root, path)
        return True
    except FileNotFoundError:
        return False


def unregister() -> list[str]:
    """Remove every key created by :func:`register`.

    Returns:
        Human-readable lines describing what was removed.
    """
    if not _is_windows():
        raise RuntimeError(
            "File association is only supported on Windows."
        )
    import winreg

    root = winreg.HKEY_CURRENT_USER
    changes: list[str] = []

    if _delete_tree(root, f"Software\\Classes\\{APP_KEY}"):
        changes.append(f"Removed application key: {APP_KEY}")
    if _delete_tree(root, f"Software\\Classes\\{PROGID}"):
        changes.append(f"Removed ProgID: {PROGID}")
    if _delete_tree(root, f"Software\\{APP_NAME}"):
        changes.append(f"Removed capabilities tree: Software\\{APP_NAME}")

    # Drop the RegisteredApplications value (the key itself is shared).
    try:
        with winreg.OpenKey(
            root,
            "Software\\RegisteredApplications",
            0,
            winreg.KEY_SET_VALUE,
        ) as k:
            winreg.DeleteValue(k, APP_NAME)
        changes.append(
            f"Removed Software\\RegisteredApplications\\{APP_NAME}"
        )
    except FileNotFoundError:
        pass

    for ext in EXTENSIONS:
        owp = f"Software\\Classes\\{ext}\\OpenWithProgids"
        try:
            with winreg.OpenKey(
                root, owp, 0, winreg.KEY_SET_VALUE
            ) as k:
                winreg.DeleteValue(k, PROGID)
            changes.append(
                f"Removed {PROGID} from OpenWithProgids for {ext}"
            )
        except FileNotFoundError:
            pass

        # If we had set the legacy default to PROGID, clear it.
        ext_root = f"Software\\Classes\\{ext}"
        try:
            with winreg.OpenKey(
                root, ext_root, 0, winreg.KEY_READ
            ) as k:
                value, _ = winreg.QueryValueEx(k, None)
        except (FileNotFoundError, OSError):
            value = None
        if value == PROGID:
            with winreg.OpenKey(
                root, ext_root, 0, winreg.KEY_SET_VALUE
            ) as k:
                winreg.DeleteValue(k, None)
            changes.append(f"Cleared legacy default for {ext}")

    return changes
