"""Tests for the Windows HKCU file-association helpers.

Pure path/command helpers are tested directly. The register/unregister
round-trip runs against the real per-user hive (HKCU) because every key
it touches is app-specific (``epy_reports.Document.1``,
``Applications\\epy_reports.exe``, ``Software\\epy_reports``) and is removed
again in a ``finally`` block, so the test leaves no trace.
"""

from __future__ import annotations

import shutil
import sys

import pytest

from epy_reports._core import winreg_assoc as wa

# ---------------------------------------------------------------------------
# Pure helpers (cross-platform)
# ---------------------------------------------------------------------------


def test_is_windows_matches_platform():
    """``_is_windows`` agrees with sys.platform."""
    assert wa._is_windows() == (sys.platform == "win32")


def test_is_frozen_false_under_pytest():
    """Running under the interpreter is not a frozen bundle."""
    assert wa._is_frozen() is False


def test_open_command_quotes_argument():
    """The open command always passes ``"%1"`` for the file argument."""
    cmd = wa._open_command()
    assert cmd.endswith('"%1"')


def test_icon_source_has_index():
    """The icon source ends with a comma + index."""
    icon = wa._icon_source()
    assert icon.rstrip().endswith(",0")


def test_launcher_path_is_nonempty():
    """A launcher string is always derivable."""
    assert wa._launcher_path()


def test_extensions_are_the_documented_three():
    """The handled extensions are exactly .md / .markdown / .qmd."""
    assert wa.EXTENSIONS == (".md", ".markdown", ".qmd")


# ---------------------------------------------------------------------------
# _launcher_path / _icon_source / _open_command — frozen and not-found paths
# ---------------------------------------------------------------------------


def test_launcher_path_frozen_uses_sys_executable(monkeypatch):
    """A PyInstaller build points the launcher at its own executable."""
    monkeypatch.setattr(wa, "_is_frozen", lambda: True)
    assert wa._launcher_path() == sys.executable


def test_launcher_path_not_installed_falls_back_to_python_module(
    monkeypatch,
):
    """No console script on PATH falls back to '<python> -m epy_reports'."""
    monkeypatch.setattr(wa, "_is_frozen", lambda: False)
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    assert wa._launcher_path() == f'"{sys.executable}" -m {wa.APP_NAME}'


def test_icon_source_frozen_uses_sys_executable(monkeypatch):
    """A frozen build's icon comes from its own executable."""
    monkeypatch.setattr(wa, "_is_frozen", lambda: True)
    assert wa._icon_source() == f'"{sys.executable}",0'


def test_icon_source_not_installed_falls_back_to_pythonw(monkeypatch):
    """No console script on PATH falls back to the pythonw.exe icon."""
    monkeypatch.setattr(wa, "_is_frozen", lambda: False)
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    icon = wa._icon_source()
    assert icon.endswith('pythonw.exe",0')


def test_open_command_quotes_a_launcher_that_is_already_quoted(monkeypatch):
    """A launcher path that already carries quotes is not double-quoted.

    Counter-example to the un-quoted case in
    ``test_open_command_quotes_argument``: the fallback launcher form
    (``"<python>" -m epy_reports``) already starts with a quote, so the
    command must be built by appending, not by wrapping again.
    """
    quoted = f'"{sys.executable}" -m {wa.APP_NAME}'
    monkeypatch.setattr(wa, "_launcher_path", lambda: quoted)
    assert wa._open_command() == f'{quoted} "%1"'


# ---------------------------------------------------------------------------
# Non-Windows guard branches
# ---------------------------------------------------------------------------


def test_register_raises_off_windows(monkeypatch):
    """``register`` refuses to run on non-Windows platforms."""
    monkeypatch.setattr(wa, "_is_windows", lambda: False)
    with pytest.raises(RuntimeError):
        wa.register()


def test_unregister_raises_off_windows(monkeypatch):
    """``unregister`` refuses to run on non-Windows platforms."""
    monkeypatch.setattr(wa, "_is_windows", lambda: False)
    with pytest.raises(RuntimeError):
        wa.unregister()


def test_open_default_apps_settings_false_off_windows(monkeypatch):
    """Off Windows the Settings launcher reports False."""
    monkeypatch.setattr(wa, "_is_windows", lambda: False)
    assert wa.open_default_apps_settings() is False


# ---------------------------------------------------------------------------
# open_default_apps_settings — real-Windows branches (os.startfile mocked
# so no Settings window actually opens during the test run)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only API")
def test_open_default_apps_settings_succeeds_on_first_uri(monkeypatch):
    """The per-app URI succeeding returns True without trying the fallback."""
    calls = []
    monkeypatch.setattr(wa.os, "startfile", lambda uri: calls.append(uri))
    assert wa.open_default_apps_settings() is True
    assert len(calls) == 1
    assert "registeredAppMachineKey" in calls[0]


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only API")
def test_open_default_apps_settings_falls_back_on_first_failure(
    monkeypatch,
):
    """A failing per-app URI falls back to the generic Default apps pane."""
    calls = []

    def fake_startfile(uri):
        calls.append(uri)
        if len(calls) == 1:
            raise OSError("no handler")

    monkeypatch.setattr(wa.os, "startfile", fake_startfile)
    assert wa.open_default_apps_settings() is True
    assert calls == [
        (
            "ms-settings:defaultapps?registeredAppMachineKey="
            f"Software\\RegisteredApplications\\{wa.APP_NAME}"
        ),
        "ms-settings:defaultapps",
    ]


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only API")
def test_open_default_apps_settings_false_when_both_uris_fail(monkeypatch):
    """When neither URI can be resolved, the function reports False."""

    def fake_startfile(uri):
        raise OSError("no handler")

    monkeypatch.setattr(wa.os, "startfile", fake_startfile)
    assert wa.open_default_apps_settings() is False


# ---------------------------------------------------------------------------
# Real HKCU round-trip (self-cleaning)
# ---------------------------------------------------------------------------


def test_register_then_unregister_round_trip():
    """register writes the documented keys; unregister removes them.

    Off Windows there is no registry, so the documented contract is the
    RuntimeError instead -- asserted here against the REAL platform,
    which the monkeypatched contract tests above cannot reach.
    """
    if sys.platform != "win32":
        with pytest.raises(RuntimeError):
            wa.register(make_default=False)
        return

    import winreg

    try:
        changes = wa.register(make_default=False)
        assert changes
        # The application key is now present and readable.
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            f"Software\\Classes\\{wa.APP_KEY}",
        ) as key:
            friendly, _ = winreg.QueryValueEx(key, "FriendlyAppName")
        assert friendly == wa.APP_NAME

        # The ProgID open command was written.
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            f"Software\\Classes\\{wa.PROGID}\\shell\\open\\command",
        ) as key:
            cmd, _ = winreg.QueryValueEx(key, None)  # pyright: ignore[reportArgumentType] - winreg uses None for the key's default value; the stub types the parameter as str
        assert "%1" in cmd
    finally:
        removed = wa.unregister()
        assert removed

    # After unregister the ProgID key is gone.
    with pytest.raises(FileNotFoundError):
        winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{wa.PROGID}"
        )


class _FakeKey:
    """A registry-key handle for :class:`_FakeRegistry` (path + hive only)."""

    def __init__(self, path: str) -> None:
        self.path = path

    def __enter__(self) -> _FakeKey:
        return self

    def __exit__(self, *exc_info: object) -> bool:
        return False


class _FakeRegistry:
    """An in-memory stand-in for the pieces of ``winreg`` this module uses.

    ``register(make_default=True)`` overwrites the REAL per-user default
    handler for ``.md``/``.markdown``/``.qmd`` — on this machine that key
    is shared with whatever the user actually uses to open Markdown files
    (VS Code, Typora, ...), and ``unregister`` does not restore the prior
    value, only clears its own. Running that against the real HKCU hive
    would silently change the developer's real default app. This fake
    exercises the exact same code paths (CreateKey/OpenKey/SetValueEx/
    QueryValueEx/DeleteValue/EnumKey/DeleteKey) against a throwaway dict
    tree instead.
    """

    def __init__(self) -> None:
        self.keys: set[str] = set()
        self.values: dict[str, dict[object, str]] = {}

    def create_key(self, _hive: object, path: str) -> _FakeKey:
        parts = path.split("\\")
        for i in range(1, len(parts) + 1):
            self.keys.add("\\".join(parts[:i]))
        self.values.setdefault(path, {})
        return _FakeKey(path)

    def open_key(self, _hive: object, path: str, *_args: object) -> _FakeKey:
        if path not in self.keys:
            raise FileNotFoundError(path)
        return _FakeKey(path)

    def set_value_ex(
        self, key: _FakeKey, name: object, _reserved: int, _type: int,
        value: str,
    ) -> None:
        self.values.setdefault(key.path, {})[name] = value

    def query_value_ex(
        self, key: _FakeKey, name: object
    ) -> tuple[str, int]:
        entry = self.values.get(key.path, {})
        if name not in entry:
            raise FileNotFoundError((key.path, name))
        return entry[name], 1

    def delete_value(self, key: _FakeKey, name: object) -> None:
        entry = self.values.get(key.path, {})
        if name not in entry:
            raise FileNotFoundError((key.path, name))
        del entry[name]

    def enum_key(self, key: _FakeKey, index: int) -> str:
        prefix = key.path + "\\"
        subs = sorted(
            {
                k[len(prefix):].split("\\")[0]
                for k in self.keys
                if k.startswith(prefix) and k != key.path
            }
        )
        if index >= len(subs):
            raise OSError("no more data is available")
        return subs[index]

    def delete_key(self, _hive: object, path: str) -> None:
        if path not in self.keys:
            raise FileNotFoundError(path)
        self.keys.discard(path)
        self.values.pop(path, None)


@pytest.fixture
def fake_winreg(monkeypatch):
    """Redirect every winreg call this module makes to an in-memory fake."""
    if sys.platform != "win32":
        pytest.skip("winreg is Windows-only")
    import winreg

    fake = _FakeRegistry()
    monkeypatch.setattr(winreg, "CreateKey", fake.create_key)
    monkeypatch.setattr(winreg, "OpenKey", fake.open_key)
    monkeypatch.setattr(winreg, "SetValueEx", fake.set_value_ex)
    monkeypatch.setattr(winreg, "QueryValueEx", fake.query_value_ex)
    monkeypatch.setattr(winreg, "DeleteValue", fake.delete_value)
    monkeypatch.setattr(winreg, "EnumKey", fake.enum_key)
    monkeypatch.setattr(winreg, "DeleteKey", fake.delete_key)
    return fake


def test_register_make_default_writes_legacy_default(fake_winreg):
    """make_default=True writes the legacy per-extension default handler.

    This is the only path that reaches the ``if make_default:`` branch
    in ``register``. Run against the fake registry (see ``fake_winreg``)
    rather than the real HKCU, because this call overwrites the real
    per-user default handler for ``.md``/``.markdown``/``.qmd``.
    """
    changes = wa.register(make_default=True)
    assert any("legacy default" in c for c in changes)
    ext_root = f"Software\\Classes\\{wa.EXTENSIONS[0]}"
    assert fake_winreg.values[ext_root][None] == wa.PROGID


def test_unregister_clears_a_legacy_default_that_points_at_progid(
    fake_winreg,
):
    """unregister() clears the legacy default value when it is our PROGID.

    Exercises the ``if value == PROGID`` branch: seed the fake registry
    as ``register(make_default=True)`` would leave it, then confirm
    ``unregister`` reports the clean-up and the value is actually gone.
    """
    wa.register(make_default=True)
    removed = wa.unregister()
    assert any("Cleared legacy default" in c for c in removed)
    ext_root = f"Software\\Classes\\{wa.EXTENSIONS[0]}"
    assert None not in fake_winreg.values.get(ext_root, {})


def test_unregister_leaves_a_legacy_default_pointing_elsewhere(fake_winreg):
    """A default handler for another app is not touched or reported.

    Counter-example to the clear-out above: unregister must only ever
    remove a legacy default that is its OWN progid, never someone else's
    file association.
    """
    wa.register(make_default=False)
    ext_root = f"Software\\Classes\\{wa.EXTENSIONS[0]}"
    fake_winreg.values.setdefault(ext_root, {})[None] = "SomeOtherApp.md"
    removed = wa.unregister()
    assert not any("Cleared legacy default" in c for c in removed)
    assert fake_winreg.values[ext_root][None] == "SomeOtherApp.md"


def test_unregister_is_idempotent():
    """A second unregister on a clean hive removes nothing more.

    Off Windows the same call raises by contract, so both platforms
    assert a concrete result rather than merely not crashing.
    """
    if sys.platform != "win32":
        with pytest.raises(RuntimeError):
            wa.unregister()
        return

    wa.unregister()
    # Nothing is left to remove, so the second pass reports an empty list.
    assert wa.unregister() == []
