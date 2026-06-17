"""Build a Debian .deb package for epy_mdr.

This script is a pure-Python, cross-platform .deb assembler — it can be run
on Windows (to build a .deb for Linux) or directly on a Debian/Ubuntu host.

A .deb is an ar(1) archive with three members in this exact order:
    debian-binary   — "2.0\n"
    control.tar.gz  — DEBIAN/ control files
    data.tar.gz     — the actual payload (usr/bin, usr/lib, ...)

The ar format uses fixed 60-byte ASCII headers; see ar(5).

Run from the project root:
    python installer/linux/build_deb.py

Output:
    installer/dist/epy-mdr_0.2.0_all.deb

The script prints a verification listing of the ar members at the end.
"""

from __future__ import annotations

import io
import os
import shutil
import struct
import sys
import tarfile
import textwrap
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PKG_NAME = "epy-mdr"
PKG_VERSION = "0.4.0"
PKG_ARCH = "all"
MAINTAINER = "Ing. Angel Navarro-Mora M.Sc. <ahnavarro@anmingenieria.com>"
DESCRIPTION_SHORT = "Quarto/Markdown editor with live preview and PDF/DOCX export"
DESCRIPTION_LONG = """\
 epy_mdr is a desktop Markdown and Quarto (.qmd) editor built with PySide6.
 .
 Features:
  * Live side-by-side preview rendered by pandoc
  * Multiple output formats: HTML, PDF (via pandoc), DOCX
  * Epyson theme system (academic, corporate, technical, …)
  * Bibliography / citation support
  * Registers itself as a handler for .md, .markdown, and .qmd files
 .
 Installation note: system-wide MIME defaults require the user to run
 "xdg-mime default epy_mdr.desktop text/markdown" in their own session,
 or to select epy_mdr in their file manager's "Open With" dialog.
 The postinst script updates system MIME and desktop caches and adds
 epy_mdr to /usr/share/applications/defaults.list as a best-effort hint."""

DEPENDS = "python3 (>= 3.10), pandoc"

ROOT = Path(__file__).resolve().parent.parent.parent
OUT_DIR = ROOT / "installer" / "dist"

# Source tree roots
SRC_PKG = ROOT / "src" / "epy_mdr"

# pypandoc location — pure-Python files only (no binaries)
import pypandoc as _pypandoc
PYPANDOC_SRC = Path(_pypandoc.__file__).parent

# ---------------------------------------------------------------------------
# ar(5) helper — fixed 60-byte header format
# ---------------------------------------------------------------------------
AR_MAGIC = b"!<arch>\n"

def _ar_header(name: str, size: int, mode: int = 0o100644) -> bytes:
    """Build one 60-byte ar member header."""
    # Field widths: name(16) mtime(12) uid(6) gid(6) mode(8) size(10) fmag(2)
    header = (
        f"{name:<16}"      # file identifier, space-padded to 16
        f"0           "    # mtime (12 chars)
        f"0     "          # uid (6)
        f"0     "          # gid (6)
        f"{mode:<8o}"      # mode octal (8)
        f"{size:<10}"      # size decimal (10)
        "\x60\n"           # fmag (2)
    )
    encoded = header.encode("ascii")
    assert len(encoded) == 60, f"ar header wrong length: {len(encoded)}"
    return encoded


def _ar_pad(data: bytes) -> bytes:
    """Pad data to an even byte boundary (ar requires this)."""
    if len(data) % 2 == 1:
        return data + b"\n"
    return data


# ---------------------------------------------------------------------------
# Tar helpers
# ---------------------------------------------------------------------------

def _tar_add_data(tf: tarfile.TarFile, arcname: str, data: bytes,
                  mode: int = 0o644) -> None:
    """Add raw bytes as a file entry in a TarFile."""
    info = tarfile.TarInfo(name=arcname)
    info.size = len(data)
    info.mode = mode
    tf.addfile(info, io.BytesIO(data))


def _tar_add_dir(tf: tarfile.TarFile, arcname: str,
                 mode: int = 0o755) -> None:
    """Add a directory entry in a TarFile."""
    info = tarfile.TarInfo(name=arcname)
    info.type = tarfile.DIRTYPE
    info.mode = mode
    tf.addfile(info)


def _tar_add_tree(tf: tarfile.TarFile, src_dir: Path,
                  dst_prefix: str, skip_pycache: bool = True) -> None:
    """Recursively add all files from src_dir into dst_prefix/."""
    for path in sorted(src_dir.rglob("*")):
        if skip_pycache and ("__pycache__" in path.parts or
                             path.suffix == ".pyc"):
            continue
        rel = path.relative_to(src_dir)
        arcname = f"{dst_prefix}/{rel}".replace("\\", "/")
        if path.is_dir():
            _tar_add_dir(tf, arcname)
        else:
            data = path.read_bytes()
            _tar_add_data(tf, arcname, data)


# ---------------------------------------------------------------------------
# Build control.tar.gz
# ---------------------------------------------------------------------------

def _build_control_tar() -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        # control
        control = (
            f"Package: {PKG_NAME}\n"
            f"Version: {PKG_VERSION}\n"
            f"Architecture: {PKG_ARCH}\n"
            f"Maintainer: {MAINTAINER}\n"
            f"Depends: {DEPENDS}\n"
            "Section: editors\n"
            "Priority: optional\n"
            f"Description: {DESCRIPTION_SHORT}\n"
            f"{DESCRIPTION_LONG}\n"
        )
        _tar_add_data(tf, "./control", control.encode(), mode=0o644)

        # postinst
        postinst = textwrap.dedent("""\
            #!/bin/sh
            set -e

            # Install the pip-only runtime dependencies (not available as
            # system packages on Ubuntu 24.04+): PySide6 (GUI), and pypdf +
            # reportlab (PDF footer / page-number stamping).
            if command -v pip3 >/dev/null 2>&1; then
                pip3 install PySide6 pypdf reportlab
            else
                echo "WARNING: pip3 not found — install the runtime deps manually" >&2
                echo "  Run: sudo apt install python3-pip && sudo pip3 install PySide6 pypdf reportlab" >&2
            fi

            # Update system MIME database so .qmd type is recognized.
            if command -v update-mime-database >/dev/null 2>&1; then
                update-mime-database /usr/share/mime || true
            fi

            # Refresh the desktop file cache so epy_mdr appears in menus.
            if command -v update-desktop-database >/dev/null 2>&1; then
                update-desktop-database /usr/share/applications || true
            fi

            # Register epy_mdr in /usr/share/applications/defaults.list as a
            # best-effort system-wide hint.  Desktop environments that honour
            # defaults.list (GNOME/XFCE/LXDE) will offer epy_mdr when the
            # user first opens a .md/.markdown/.qmd file.
            #
            # NOTE: xdg-mime called here as root only sets the root user's
            # mimeapps.list, NOT individual users' defaults.  Each user must
            # run "xdg-mime default epy_mdr.desktop text/markdown" in their
            # own session to make epy_mdr their personal default, or simply
            # choose "Open with > epy_mdr > Always" in their file manager.
            DEFAULTS="/usr/share/applications/defaults.list"
            if [ ! -f "$DEFAULTS" ]; then
                echo "[Default Applications]" > "$DEFAULTS"
            fi
            for mime in text/markdown text/x-markdown text/x-quarto-markdown; do
                if ! grep -q "^${mime}=" "$DEFAULTS" 2>/dev/null; then
                    echo "${mime}=epy_mdr.desktop" >> "$DEFAULTS"
                fi
            done

            exit 0
        """)
        _tar_add_data(tf, "./postinst", postinst.encode(), mode=0o755)

        # prerm
        prerm = textwrap.dedent("""\
            #!/bin/sh
            set -e

            # Remove epy_mdr entries from /usr/share/applications/defaults.list
            DEFAULTS="/usr/share/applications/defaults.list"
            if [ -f "$DEFAULTS" ]; then
                sed -i '/^text\\/markdown=epy_mdr.desktop$/d' "$DEFAULTS" || true
                sed -i '/^text\\/x-markdown=epy_mdr.desktop$/d' "$DEFAULTS" || true
                sed -i '/^text\\/x-quarto-markdown=epy_mdr.desktop$/d' "$DEFAULTS" || true
            fi

            exit 0
        """)
        _tar_add_data(tf, "./prerm", prerm.encode(), mode=0o755)

    return buf.getvalue()


# ---------------------------------------------------------------------------
# Build data.tar.gz
# ---------------------------------------------------------------------------

def _build_data_tar(png_path: Path) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        # Directory entries (required for correct dpkg extraction)
        for d in [
            "./usr",
            "./usr/bin",
            "./usr/lib",
            f"./usr/lib/{PKG_NAME}",
            f"./usr/lib/{PKG_NAME}/epy_mdr",
            f"./usr/lib/{PKG_NAME}/pypandoc",
            "./usr/share",
            "./usr/share/applications",
            "./usr/share/mime",
            "./usr/share/mime/packages",
            "./usr/share/icons",
            "./usr/share/icons/hicolor",
            "./usr/share/icons/hicolor/256x256",
            "./usr/share/icons/hicolor/256x256/apps",
        ]:
            _tar_add_dir(tf, d)

        # /usr/bin/epy_mdr launcher shell script
        # Use the system interpreter explicitly: PySide6 is installed by the
        # postinst into /usr/bin/python3's environment.  A bare "python3" would
        # pick up whatever is first on PATH (e.g. an activated virtualenv that
        # lacks PySide6) and fail to launch.
        launcher = textwrap.dedent("""\
            #!/bin/sh
            exec /usr/bin/python3 -c "import sys; sys.path.insert(0, '/usr/lib/epy-mdr'); from epy_mdr.app import main; sys.exit(main())" "$@"
        """)
        _tar_add_data(tf, f"./usr/bin/{PKG_NAME}", launcher.encode(),
                      mode=0o755)

        # epy_mdr Python package
        _tar_add_tree(tf, SRC_PKG,
                      f"./usr/lib/{PKG_NAME}/epy_mdr")

        # pypandoc — pure-Python only; the pandoc binary is NOT vendored
        # because on Ubuntu the `pandoc` apt package is already listed in
        # Depends and is the correct architecture-native binary.
        for path in sorted(PYPANDOC_SRC.rglob("*")):
            if "__pycache__" in path.parts or path.suffix == ".pyc":
                continue
            # Skip any binary executables (pandoc, pandoc.exe, etc.)
            if path.is_file() and path.stem in ("pandoc",):
                continue
            if path.is_file() and path.suffix in (".exe", ".bin", ".so"):
                continue
            rel = path.relative_to(PYPANDOC_SRC)
            arcname = f"./usr/lib/{PKG_NAME}/pypandoc/{rel}".replace("\\", "/")
            if path.is_dir():
                _tar_add_dir(tf, arcname)
            else:
                _tar_add_data(tf, arcname, path.read_bytes())

        # .desktop file
        desktop = textwrap.dedent(f"""\
            [Desktop Entry]
            Version=1.0
            Type=Application
            Name=epy_mdr
            Comment={DESCRIPTION_SHORT}
            Exec=epy-mdr %F
            Icon=epy_mdr
            Terminal=false
            Categories=Office;TextEditor;
            MimeType=text/markdown;text/x-markdown;text/x-quarto-markdown;
            StartupNotify=true
        """)
        _tar_add_data(tf, "./usr/share/applications/epy_mdr.desktop",
                      desktop.encode(), mode=0o644)

        # MIME type definition for text/x-quarto-markdown (*.qmd)
        mime_xml = textwrap.dedent("""\
            <?xml version="1.0" encoding="UTF-8"?>
            <mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">
              <mime-type type="text/x-quarto-markdown">
                <comment>Quarto Markdown document</comment>
                <acronym>QMD</acronym>
                <expanded-acronym>Quarto Markdown Document</expanded-acronym>
                <glob pattern="*.qmd"/>
                <sub-class-of type="text/plain"/>
              </mime-type>
            </mime-info>
        """)
        _tar_add_data(tf, "./usr/share/mime/packages/epy_mdr.xml",
                      mime_xml.encode(), mode=0o644)

        # App icon (256x256 PNG)
        if png_path.exists():
            icon_data = png_path.read_bytes()
            _tar_add_data(
                tf,
                "./usr/share/icons/hicolor/256x256/apps/epy_mdr.png",
                icon_data,
                mode=0o644,
            )
        else:
            print(
                f"  WARNING: {png_path} not found — icon will be missing from .deb.",
                file=sys.stderr,
            )

    return buf.getvalue()


# ---------------------------------------------------------------------------
# ar writer
# ---------------------------------------------------------------------------

def _write_ar(path: Path, members: list[tuple[str, bytes]]) -> None:
    """Write an ar archive to path with the given (name, data) members."""
    with open(path, "wb") as fh:
        fh.write(AR_MAGIC)
        for name, data in members:
            fh.write(_ar_header(name, len(data)))
            fh.write(_ar_pad(data))


# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------

def _verify_deb(path: Path) -> None:
    """Read the ar archive back and print member names + sizes."""
    print(f"\nVerification — ar members in {path.name}:")
    with open(path, "rb") as fh:
        magic = fh.read(8)
        if magic != AR_MAGIC:
            raise ValueError(f"Bad ar magic: {magic!r}")
        while True:
            header = fh.read(60)
            if not header:
                break
            if len(header) < 60:
                raise ValueError("Truncated ar header")
            name = header[0:16].decode("ascii").rstrip()
            size = int(header[48:58].decode("ascii").strip())
            print(f"  {name:<20} {size:>10,} bytes")
            # Skip content (+padding)
            fh.read(size + (size % 2))
    print("  (structure OK)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    png_path = ROOT / "assets_build" / "epy_mdr.png"

    print("Building control.tar.gz ...")
    control_tar = _build_control_tar()

    print("Building data.tar.gz ...")
    data_tar = _build_data_tar(png_path)

    deb_name = f"{PKG_NAME}_{PKG_VERSION}_{PKG_ARCH}.deb"
    deb_path = OUT_DIR / deb_name

    print(f"Writing {deb_path} ...")
    _write_ar(deb_path, [
        ("debian-binary", b"2.0\n"),
        ("control.tar.gz", control_tar),
        ("data.tar.gz", data_tar),
    ])
    size_kb = deb_path.stat().st_size / 1024
    print(f"  -> {deb_path}  ({size_kb:,.1f} KB)")

    _verify_deb(deb_path)


if __name__ == "__main__":
    main()
