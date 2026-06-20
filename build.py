"""Build the epy_reports application bundle for the installer.

Run from the project root:

    python build.py              # build dist/epy_reports/ (installer input)

This produces the PyInstaller onedir layout under ``dist/epy_reports/``,
which is the staging folder packaged by the Windows installer
(``installer/windows/epy_reports.iss``) and the Linux ``.deb`` builder.
It is an intermediate build artifact, not a distributable app — the
shipped deliverables are the ``setup.exe`` and the ``.deb``.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
BUILD = ROOT / "build"
SPEC = ROOT / "epy_reports.spec"
APP_NAME = "epy_reports"


def _run(cmd: list[str]) -> None:
    """Run a subprocess and abort with its exit code on failure."""
    print("$", " ".join(cmd))
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        sys.exit(result.returncode)


def _clean() -> None:
    """Remove previous build and dist directories."""
    for path in (BUILD, DIST):
        if path.exists():
            print(f"removing {path}")
            shutil.rmtree(path)


def _build_onedir() -> Path:
    """Run PyInstaller via the project spec. Returns the dist folder."""
    _run([sys.executable, "-m", "PyInstaller", "--noconfirm", str(SPEC)])
    target = DIST / APP_NAME
    if not target.exists():
        sys.exit(f"PyInstaller did not produce {target}")
    return target


def _purge_build_artifacts() -> None:
    """Remove PyInstaller's staging ``build/`` after a successful run.

    ``build/`` is intermediate (cache + warning logs + PYZ slices) and
    only useful for incremental rebuilds. Deleting it after each run
    keeps the project root clean. ``--keep-build`` skips this step
    when you actually want the staging tree for debugging.
    """
    if BUILD.exists():
        print(f"cleaning {BUILD}")
        shutil.rmtree(BUILD, ignore_errors=True)


def main() -> int:
    """CLI entry point for the build script."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--keep",
        action="store_true",
        help="Skip the initial cleanup of build/ and dist/.",
    )
    parser.add_argument(
        "--keep-build",
        action="store_true",
        help=(
            "Do not delete the build/ staging dir after a "
            "successful build (debug only)."
        ),
    )
    args = parser.parse_args()

    if not args.keep:
        _clean()

    produced = _build_onedir()

    if not args.keep_build:
        _purge_build_artifacts()

    print(f"\nDone. Installer input: {produced}")
    print("Next: build the installer (installer/windows/epy_reports.iss).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
