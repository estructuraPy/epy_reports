"""Generate epy_mdr application icons.

Produces:
  assets_build/epy_mdr.ico  — multi-size ICO (16, 32, 48, 256 px)
  assets_build/epy_mdr.png  — 256 x 256 PNG

Design: rounded-square dark-slate background (#2d3142), white "M↓" monogram,
flat design, bold weight.

Run from the project root:
    python installer/make_icon.py
"""

from __future__ import annotations

import math
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError as exc:
    raise SystemExit("Pillow is required: pip install pillow") from exc

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BG_COLOR = (0x2D, 0x31, 0x42, 255)   # dark-slate #2d3142
FG_COLOR = (255, 255, 255, 255)       # white
CORNER_RATIO = 0.18                    # corner radius / icon size
SIZES = [16, 32, 48, 256]

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "assets_build"


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

def _rounded_rect_mask(size: int, radius: int) -> Image.Image:
    """Return an RGBA mask with a rounded-rectangle shape."""
    img = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    return img


def _draw_arrow(draw: ImageDraw.ImageDraw, cx: float, cy: float,
                arrow_w: float, arrow_h: float, color: tuple) -> None:
    """Draw a downward-pointing arrow centred at (cx, cy).

    The arrow has a rectangular shaft on top and a triangular head below.
    """
    shaft_w = arrow_w * 0.38
    shaft_h = arrow_h * 0.50
    head_w = arrow_w
    head_h = arrow_h * 0.50

    # Shaft (rectangle): top-left corner
    sx = cx - shaft_w / 2
    sy = cy - arrow_h / 2

    # Head (triangle): sits below shaft
    hx_left = cx - head_w / 2
    hx_right = cx + head_w / 2
    hy_top = sy + shaft_h
    hy_bottom = cy + arrow_h / 2

    draw.rectangle([sx, sy, sx + shaft_w, hy_top], fill=color)
    draw.polygon(
        [(hx_left, hy_top), (hx_right, hy_top), (cx, hy_bottom)],
        fill=color,
    )


def _make_icon_at_size(size: int) -> Image.Image:
    """Render a single icon frame at ``size`` x ``size`` pixels."""
    radius = max(2, round(size * CORNER_RATIO))
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background rounded square
    mask = _rounded_rect_mask(size, radius)
    bg = Image.new("RGBA", (size, size), BG_COLOR)
    img.paste(bg, mask=mask)

    if size <= 16:
        # At 16 px just draw a solid "M" letter — no room for layout
        font_size = max(8, size - 4)
        try:
            font = ImageFont.truetype("arialbd.ttf", font_size)
        except OSError:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), "M", font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        tx = (size - tw) / 2 - bbox[0]
        ty = (size - th) / 2 - bbox[1]
        draw.text((tx, ty), "M", font=font, fill=FG_COLOR)
        return img

    # --- Layout for sizes >= 32 ---
    # Divide icon vertically: top 55% = "M" letter, bottom 45% = arrow
    padding = size * 0.10
    content_w = size - 2 * padding
    content_h = size - 2 * padding

    letter_h = content_h * 0.52
    arrow_zone_h = content_h * 0.42
    gap = content_h * 0.06

    # "M" letter — choose font size so it fills the letter zone well
    target_font_size = int(letter_h * 0.95)
    font = None
    for face in ("arialbd.ttf", "Arial_Bold.ttf", "DejaVuSans-Bold.ttf",
                 "LiberationSans-Bold.ttf"):
        try:
            font = ImageFont.truetype(face, target_font_size)
            break
        except OSError:
            continue
    if font is None:
        font = ImageFont.load_default()

    letter = "M"
    bbox = draw.textbbox((0, 0), letter, font=font)
    lw = bbox[2] - bbox[0]
    lh = bbox[3] - bbox[1]

    lx = (size - lw) / 2 - bbox[0]
    ly = padding - bbox[1]
    draw.text((lx, ly), letter, font=font, fill=FG_COLOR)

    # Down-arrow centred below the letter
    arrow_w = content_w * 0.52
    arrow_h = arrow_zone_h * 0.85
    cx = size / 2
    cy = padding + letter_h + gap + arrow_zone_h / 2
    _draw_arrow(draw, cx, cy, arrow_w, arrow_h, FG_COLOR)

    return img


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def generate() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    frames: list[Image.Image] = [_make_icon_at_size(s) for s in SIZES]

    # PNG (256 px)
    png_path = OUT_DIR / "epy_mdr.png"
    frames[-1].save(png_path, format="PNG")
    print(f"  PNG -> {png_path}  ({png_path.stat().st_size:,} bytes)")

    # ICO — multi-size (manual binary writer)
    # Pillow's built-in ICO encoder only writes one size per file.
    # We write a proper ICO manually: 6-byte header + N*16-byte directory
    # entries + N PNG blobs (PNG-compressed entries are valid since Vista).
    import io
    import struct

    ico_path = OUT_DIR / "epy_mdr.ico"
    png_blobs: list[bytes] = []
    for frame in frames:
        buf = io.BytesIO()
        frame.convert("RGBA").save(buf, format="PNG")
        png_blobs.append(buf.getvalue())

    n = len(png_blobs)
    header = struct.pack("<HHH", 0, 1, n)          # reserved, type=1(ICO), count
    dir_offset = 6 + n * 16
    entries = b""
    image_data = b""
    cur_offset = dir_offset
    for idx, (size, blob) in enumerate(zip(SIZES, png_blobs)):
        # width/height: 0 means 256
        w = 0 if size == 256 else size
        h = 0 if size == 256 else size
        entries += struct.pack(
            "<BBBBHHII",
            w, h,        # width, height
            0,           # color count (0 = no palette)
            0,           # reserved
            1,           # color planes
            32,          # bits per pixel
            len(blob),   # size of image data
            cur_offset,  # offset of image data
        )
        image_data += blob
        cur_offset += len(blob)

    with open(ico_path, "wb") as fh:
        fh.write(header + entries + image_data)
    print(f"  ICO -> {ico_path}  ({ico_path.stat().st_size:,} bytes, {n} sizes: {SIZES})")


if __name__ == "__main__":
    print("Generating epy_mdr icons...")
    generate()
    print("Done.")
