"""Build a portable epy_mdr executable with PyInstaller.

Run from the project root:

    python build.py              # onedir build  -> dist/epy_mdr/
    python build.py --onefile    # single .exe   -> dist/epy_mdr.exe
    python build.py --zip        # also zip the onedir folder for sharing

The onedir build is recommended: Qt WebEngine ships several support
processes and resource files that work best when laid out next to the
launcher in a folder. The onefile variant is convenient but has slower
cold-start because it extracts to a temp dir on launch.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
BUILD = ROOT / "build"
SPEC = ROOT / "epy_mdr.spec"
ENTRY = ROOT / "src" / "epy_mdr" / "__main__.py"
APP_NAME = "epy_mdr"


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


def _build_onefile() -> Path:
    """Run PyInstaller in --onefile mode without using the spec."""
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name",
        APP_NAME,
        "--paths",
        "src",
        "--collect-data",
        "pypandoc",
        "--collect-data",
        "epy_mdr",
        "--collect-submodules",
        "pypandoc",
        "--exclude-module",
        "tkinter",
        str(ENTRY),
    ]
    _run(cmd)
    target = DIST / f"{APP_NAME}.exe"
    if not target.exists():
        sys.exit(f"PyInstaller did not produce {target}")
    return target


def _zip_folder(folder: Path) -> Path:
    """Zip the produced onedir folder for easy distribution."""
    archive = DIST / f"{APP_NAME}-portable.zip"
    if archive.exists():
        archive.unlink()
    print(f"creating {archive}")
    with zipfile.ZipFile(
        archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6
    ) as zf:
        for path in folder.rglob("*"):
            zf.write(path, path.relative_to(folder.parent))
    return archive


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
        "--onefile",
        action="store_true",
        help="Produce a single .exe instead of a portable folder.",
    )
    parser.add_argument(
        "--zip",
        action="store_true",
        help="Zip the resulting folder (onedir mode only).",
    )
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

    if args.onefile:
        produced = _build_onefile()
    else:
        produced = _build_onedir()

    if not args.keep_build:
        _purge_build_artifacts()

    if args.onefile:
        print(f"\nDone. Portable executable: {produced}")
        if args.zip:
            print(
                "warning: --zip has no effect with --onefile; "
                "the file is already a single artifact."
            )
        return 0

    print(f"\nDone. Portable folder: {produced}")
    print(
        "Tip: copy or zip the folder above and drop it on any "
        "Windows machine — no Python required."
    )
    if args.zip:
        archive = _zip_folder(produced)
        print(f"Archive: {archive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
