"""Tests for the multi-size .ico generator (dev/build tool).

Pure Pillow + struct code, no Qt -- 0% coverage before this file existed
because it is never imported by the shipping application, only run by
hand to refresh the packaged app icon. Every test redirects ``OUT_DIR``/
``SRC_PNG`` to a tmp_path so the real, git-tracked
``_core/_packaging/assets_build/epy_reports.ico`` is never regenerated
by a test run (``tests/test_about_dialog.py::test_ico_has_four_sizes``
asserts on that exact real file).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from epy_reports._core._packaging import make_icon as mi


def _make_source_png(path: Path, size: tuple[int, int] = (704, 524)) -> None:
    img = Image.new("RGBA", size, (10, 20, 30, 255))
    img.save(path)


# ---------------------------------------------------------------------------
# _letterbox
# ---------------------------------------------------------------------------


def test_letterbox_produces_a_square_canvas_of_the_requested_size():
    src = Image.new("RGBA", (704, 524), (255, 0, 0, 255))
    out = mi._letterbox(src, 256)
    assert out.size == (256, 256)
    assert out.mode == "RGBA"


def test_letterbox_preserves_aspect_ratio_centered():
    """A wide source is centered vertically inside the square canvas."""
    src = Image.new("RGBA", (704, 524), (255, 0, 0, 255))
    out = mi._letterbox(src, 100)
    # 704x524 scaled to fit 100x100 -> width=100, height=round(524*100/704).
    expected_h = round(524 * 100 / 704)
    y_margin = (100 - expected_h) // 2
    # Pixel just above the thumbnail (in the letterbox margin) is transparent.
    if y_margin > 0:
        assert out.getpixel((50, 0))[3] == 0  # alpha channel


def test_letterbox_handles_a_non_rgba_source():
    """An RGB (no alpha) source is still letterboxed onto a transparent RGBA
    canvas without raising."""
    src = Image.new("RGB", (200, 100), (0, 128, 255))
    out = mi._letterbox(src, 64)
    assert out.size == (64, 64)


# ---------------------------------------------------------------------------
# _write_ico / _verify_ico
# ---------------------------------------------------------------------------


def test_write_ico_then_verify_reports_all_sizes(tmp_path: Path):
    frames = [
        mi._letterbox(Image.new("RGBA", (704, 524), (1, 2, 3, 255)), s)
        for s in mi.SIZES
    ]
    ico_path = tmp_path / "out.ico"
    mi._write_ico(frames, ico_path)
    assert ico_path.is_file()
    assert mi._verify_ico(ico_path) == len(mi.SIZES)


def test_write_ico_256_entry_encodes_zero_dimension(tmp_path: Path):
    """A 256px frame is encoded as width=0/height=0 per the ICO spec.

    ICONDIRENTRY only has one byte per dimension, so 256 (which does not
    fit) is conventionally encoded as 0 -- readers interpret 0 as 256.
    """
    import struct

    frames = [
        mi._letterbox(Image.new("RGBA", (704, 524), (1, 2, 3, 255)), s)
        for s in mi.SIZES
    ]
    ico_path = tmp_path / "sizes.ico"
    mi._write_ico(frames, ico_path)

    raw = ico_path.read_bytes()
    # One 16-byte ICONDIRENTRY per frame, starting right after the 6-byte
    # ICONDIR header, in the same order as mi.SIZES == [16, 32, 48, 256].
    entries_offset = 6
    widths = []
    for i in range(len(mi.SIZES)):
        entry = raw[entries_offset + i * 16: entries_offset + (i + 1) * 16]
        w, h = struct.unpack("<BB", entry[:2])
        widths.append((w, h))
    assert widths[:3] == [(16, 16), (32, 32), (48, 48)]
    assert widths[3] == (0, 0)  # the 256px frame


# ---------------------------------------------------------------------------
# generate()
# ---------------------------------------------------------------------------


def test_generate_writes_a_valid_multi_size_ico(tmp_path, monkeypatch):
    src_png = tmp_path / "epy_reports.png"
    _make_source_png(src_png)
    out_dir = tmp_path / "assets_build"
    monkeypatch.setattr(mi, "SRC_PNG", src_png)
    monkeypatch.setattr(mi, "OUT_DIR", out_dir)

    mi.generate()

    ico_path = out_dir / "epy_reports.ico"
    assert ico_path.is_file()
    assert mi._verify_ico(ico_path) == 4


def test_generate_raises_systemexit_when_source_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(mi, "SRC_PNG", tmp_path / "does-not-exist.png")
    monkeypatch.setattr(mi, "OUT_DIR", tmp_path / "assets_build")
    with pytest.raises(SystemExit, match="Source image not found"):
        mi.generate()
