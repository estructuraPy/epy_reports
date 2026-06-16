"""Generate epy_mdr application icons.

Produces:
  assets_build/epy_mdr.ico  — multi-size ICO (16, 32, 48, 256 px)

The source image is assets_build/epy_mdr.png (user-supplied logo, 704x524).
Each ICO frame letterboxes the logo onto a square transparent canvas,
preserving aspect ratio (centered).  epy_mdr.png is NOT overwritten.

Run from the project root:
    python installer/make_icon.py
"""

from __future__ import annotations

import io
import struct
from pathlib import Path

try:
    from PIL import Image
except ImportError as exc:
    raise SystemExit("Pillow is required: pip install pillow") from exc

SIZES = [16, 32, 48, 256]

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "assets_build"
SRC_PNG = OUT_DIR / "epy_mdr.png"


# ---------------------------------------------------------------------------
# Frame builder
# ---------------------------------------------------------------------------

def _letterbox(src: Image.Image, size: int) -> Image.Image:
    """Return a square RGBA canvas with the source image letterboxed.

    The canvas is ``size`` x ``size`` pixels (transparent background).
    The source is scaled to fit, preserving aspect ratio, and centered.
    """
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    thumb = src.copy()
    thumb.thumbnail((size, size), Image.LANCZOS)
    x = (size - thumb.width) // 2
    y = (size - thumb.height) // 2
    canvas.paste(thumb, (x, y), mask=thumb if thumb.mode == "RGBA" else None)
    return canvas


# ---------------------------------------------------------------------------
# Multi-size ICO writer
# ---------------------------------------------------------------------------

def _write_ico(frames: list[Image.Image], ico_path: Path) -> None:
    """Write a multi-size ICO file using PNG-compressed entries.

    PNG-compressed ICO entries are valid from Windows Vista onward.
    The binary layout is:
        6-byte ICONDIR header
        N * 16-byte ICONDIRENTRY records
        N PNG blobs
    """
    png_blobs: list[bytes] = []
    for frame in frames:
        buf = io.BytesIO()
        frame.convert("RGBA").save(buf, format="PNG")
        png_blobs.append(buf.getvalue())

    n = len(png_blobs)
    header = struct.pack("<HHH", 0, 1, n)   # reserved=0, type=1(ICO), count
    dir_offset = 6 + n * 16
    entries = b""
    image_data = b""
    cur_offset = dir_offset

    for size, blob in zip(SIZES, png_blobs, strict=True):
        w = 0 if size == 256 else size  # 0 encodes 256 in ICONDIRENTRY
        h = 0 if size == 256 else size
        entries += struct.pack(
            "<BBBBHHII",
            w, h,       # width, height (0 means 256)
            0,          # color count (0 = no palette)
            0,          # reserved
            1,          # color planes
            32,         # bits per pixel
            len(blob),  # size of image data in bytes
            cur_offset, # offset of image data from start of file
        )
        image_data += blob
        cur_offset += len(blob)

    with open(ico_path, "wb") as fh:
        fh.write(header + entries + image_data)


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def _verify_ico(ico_path: Path) -> int:
    """Parse the ICO header and return the number of sizes recorded."""
    with open(ico_path, "rb") as fh:
        _reserved, _type, count = struct.unpack("<HHH", fh.read(6))
    return count


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def generate() -> None:
    """Load the source PNG and produce a multi-size ICO."""
    if not SRC_PNG.exists():
        raise SystemExit(f"Source image not found: {SRC_PNG}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    src = Image.open(SRC_PNG).convert("RGBA")
    frames = [_letterbox(src, s) for s in SIZES]

    ico_path = OUT_DIR / "epy_mdr.ico"
    _write_ico(frames, ico_path)

    count = _verify_ico(ico_path)
    print(
        f"  ICO -> {ico_path}  "
        f"({ico_path.stat().st_size:,} bytes, {count} sizes: {SIZES})"
    )
    assert count == len(SIZES), (
        f"ICO size count mismatch: expected {len(SIZES)}, got {count}"
    )


if __name__ == "__main__":
    print("Generating epy_mdr icons...")
    generate()
    print("Done.")
