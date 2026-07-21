"""Tests for self-contained HTML export (``_embed_local_images`` + the
``embed_images`` flag through ``render_markdown``/``build_html_document``).

A report written next to its ``figs/`` directory must survive being moved
or shared as a single file: local ``<img>`` references become ``data:``
URIs and no ``<base>`` tag pins relative URLs (images or ``#fragment``
index links) to the machine path it was rendered on.
"""

from __future__ import annotations

import base64
from pathlib import Path

from epy_reports.renderer import render_markdown
from epy_reports.template import _embed_local_images

# Smallest valid PNG (1x1 transparent pixel).
_PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
    "YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


def _write_fig(tmp_path: Path) -> Path:
    figs = tmp_path / "figs"
    figs.mkdir()
    (figs / "beam.png").write_bytes(_PNG_BYTES)
    return tmp_path


class TestEmbedLocalImages:
    def test_relative_src_becomes_data_uri(self, tmp_path):
        base = _write_fig(tmp_path)
        out = _embed_local_images('<img src="figs/beam.png" alt="b" />', base)
        assert 'src="data:image/png;base64,' in out
        assert "figs/beam.png" not in out

    def test_remote_and_data_sources_untouched(self, tmp_path):
        for src in ("https://x.test/a.png", "http://x.test/a.png",
                    "//x.test/a.png", "data:image/png;base64,AAAA"):
            frag = f'<img src="{src}" />'
            assert _embed_local_images(frag, tmp_path) == frag

    def test_missing_file_left_as_is(self, tmp_path):
        frag = '<img src="figs/nope.png" />'
        assert _embed_local_images(frag, tmp_path) == frag

    def test_relative_src_without_base_dir_left_as_is(self):
        frag = '<img src="figs/beam.png" />'
        assert _embed_local_images(frag, None) == frag

    def test_absolute_src_resolves_without_base_dir(self, tmp_path):
        base = _write_fig(tmp_path)
        frag = f'<img src="{(base / "figs" / "beam.png").as_posix()}" />'
        assert 'data:image/png;base64,' in _embed_local_images(frag, None)


class TestRenderMarkdownEmbedImages:
    def test_embed_inlines_images_and_drops_base(self, tmp_path):
        base = _write_fig(tmp_path)
        html = render_markdown(
            "![Beam](figs/beam.png)", base_dir=base, embed_images=True
        )
        assert 'src="data:image/png;base64,' in html
        assert "<base " not in html

    def test_default_keeps_base_and_relative_src(self, tmp_path):
        base = _write_fig(tmp_path)
        html = render_markdown("![Beam](figs/beam.png)", base_dir=base)
        assert 'src="figs/beam.png"' in html
        assert "<base " in html
