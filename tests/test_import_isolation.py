"""Import-isolation gate (headless / no-GUI-toolkit contract).

``epy_reports``'s root package facade (``Report``) imports only ``pathlib``
at module level; every Qt-dependent submodule (``themes``, ``_design``,
``renderer``, ``_export_pdf``) is a lazy, point-of-use import inside a
method body. Only ``Report.to_pdf`` genuinely needs ``PySide6`` (it renders
via a headless ``QWebEngineView``); ``to_html``/``to_docx`` must stay usable
with no Qt binding installed at all. The hook runs in a fresh subprocess
BEFORE anything imports epy_reports, so a cached module can never mask a
regression.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

_SRC_DIR = str(Path(__file__).resolve().parent.parent / "src")


def _run_isolated(blocked_modules: tuple[str, ...], probe: str) -> subprocess.CompletedProcess:
    header = (
        "import builtins\n"
        "_real_import = builtins.__import__\n"
        f"_blocked = {blocked_modules!r}\n"
        "\n"
        "def _fake_import(name, *args, **kwargs):\n"
        "    if any(name == b or name.startswith(b + '.') for b in _blocked):\n"
        "        raise ImportError('blocked for isolation test: ' + name)\n"
        "    return _real_import(name, *args, **kwargs)\n"
        "\n"
        "builtins.__import__ = _fake_import\n"
        "\n"
    )
    script = header + textwrap.dedent(probe).strip() + "\n"
    env = dict(os.environ)
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = _SRC_DIR + (os.pathsep + existing if existing else "")
    return subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True, text=True, timeout=120, env=env,
    )


class TestImportWithoutPySide6:
    def test_import_succeeds(self):
        result = _run_isolated(("PySide6", "PyQt6", "PyQt5", "PySide2"), "import epy_reports\nprint('OK')")
        assert result.returncode == 0, result.stderr
        assert "OK" in result.stdout

    def test_report_class_still_available(self):
        probe = """
            import epy_reports
            assert hasattr(epy_reports, "Report")
            print('OK')
        """
        result = _run_isolated(("PySide6", "PyQt6", "PyQt5", "PySide2"), probe)
        assert result.returncode == 0, result.stderr
        assert "OK" in result.stdout

    def test_report_to_html_works_without_qt(self, tmp_path):
        # to_html() never touches Qt (only to_pdf() does) — must work headless
        # (e.g. CI/CLI usage) with no Qt binding present at all.
        out_path = (tmp_path / "isolated_report.html").as_posix()
        probe = f"""
            import epy_reports
            report = epy_reports.Report("# Title\\n\\nBody text.")
            out_path = {out_path!r}
            report.to_html(out_path)
            import os
            assert os.path.isfile(out_path)
            print('OK')
        """
        result = _run_isolated(("PySide6", "PyQt6", "PyQt5", "PySide2"), probe)
        assert result.returncode == 0, result.stderr
        assert "OK" in result.stdout
