"""Tests for the DOCX/diagram media-export internals.

Covers the offscreen diagram page builder and the component-simplification
branches the existing test_media_export.py does not reach.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from PySide6 import QtWebEngineWidgets
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication

from epy_reports._core import _media_export as media_export
from epy_reports._core._media_export import (
    _diagram_page_html,
    collect_diagrams,
    render_diagram_pngs,
    simplify_components_for_export,
)

_app: QApplication | None = None


@pytest.fixture(scope="module")
def qapp():
    """Provide a module-scoped QApplication instance.

    render_diagram_pngs's real code path (past the "no QApplication"
    early return) needs one to exist -- this file has none of its own
    otherwise, since every other test here is pure string/regex logic.
    """
    global _app
    if _app is None:
        _instance = QApplication.instance()
        _app = (
            _instance
            if isinstance(_instance, QApplication)
            else QApplication([])
        )
    return _app


# ---------------------------------------------------------------------------
# simplify_components_for_export — extra branches
# ---------------------------------------------------------------------------


def test_timeline_wrapper_is_unwrapped():
    """A timeline component keeps its list but drops the wrapper."""
    src = (
        "::: {.timeline}\n"
        "- First\n- Second\n"
        ":::\n"
    )
    out = simplify_components_for_export(src)
    assert "- First" in out
    assert ".timeline" not in out


def test_agenda_wrapper_is_unwrapped():
    """An agenda component keeps its list but drops the wrapper."""
    src = "::: {.agenda}\n- Item A\n- Item B\n:::\n"
    out = simplify_components_for_export(src)
    assert "- Item A" in out
    assert ".agenda" not in out


def test_fenced_code_is_passed_through_untouched():
    """Content inside a code fence is never rewritten."""
    src = "```text\n::: {.cards}\n:::\n```\n"
    out = simplify_components_for_export(src)
    assert "::: {.cards}" in out  # untouched because it is inside a fence


def test_trailing_newline_preserved():
    """A source ending in a newline keeps it after rewriting."""
    src = "plain paragraph\n"
    assert simplify_components_for_export(src).endswith("\n")


def test_unterminated_div_collects_to_end_of_document():
    """A component div missing its closing ':::' still yields its body.

    _collect_div's while loop falls off the end of ``lines`` (no closing
    fence found) rather than raising -- a malformed document degrades to
    "everything after the opener is the body" instead of crashing export.
    """
    src = "::: {.timeline}\n- Only item\n"  # no closing ':::'
    out = simplify_components_for_export(src)
    assert "- Only item" in out


def test_stats_block_with_no_stat_children_yields_nothing():
    """A .stats wrapper with no nested .stat divs renders as empty.

    Exercises simplify_components_for_export's ``if not numbers: return
    []`` branch in _stats_to_table.
    """
    src = ":::: {.stats}\nJust a stray paragraph, no .stat children.\n::::\n"
    out = simplify_components_for_export(src)
    assert "stray paragraph" not in out
    assert "|" not in out


def test_stats_label_falls_back_to_plain_text_line():
    """Without a [...]{.stat-label} span, a plain non-bold line is the label.

    Counter-example to STATS in test_media_export.py, which always uses
    the explicit .stat-label span.
    """
    src = (
        ":::: {.stats}\n"
        "::: {.stat}\n**99%**\n\npass rate\n:::\n"
        "::::\n"
    )
    out = simplify_components_for_export(src)
    assert "| **99%** |" in out
    assert "| pass rate |" in out


def test_cards_block_skips_stray_lines_between_cards():
    """Non-.card content between/around cards is skipped, not emitted.

    Exercises _cards_to_blocks' ``else: i += 1`` branch (a line inside
    the .cards wrapper that does not open a nested .card div).
    """
    src = (
        ":::: {.cards}\n"
        "A stray line that is not a card.\n"
        "::: {.card}\n#### Real Card\nBody.\n:::\n"
        "::::\n"
    )
    out = simplify_components_for_export(src)
    assert "**Real Card**" in out
    assert "stray line" not in out


# ---------------------------------------------------------------------------
# _diagram_page_html
# ---------------------------------------------------------------------------


def test_diagram_page_html_embeds_mermaid_engine():
    """A mermaid diagram pulls in the mermaid init + a themed pre."""
    diagrams = [("mermaid", "flowchart LR\nA-->B")]
    html = _diagram_page_html(diagrams, theme_css="body{color:red}")
    assert "window._epy_init_mermaid()" in html
    assert '<pre class="mermaid">' in html
    assert "body{color:red}" in html


def test_diagram_page_html_embeds_nomnoml_engine():
    """A nomnoml diagram pulls in the nomnoml init."""
    diagrams = [("nomnoml", "[A] -> [B]")]
    html = _diagram_page_html(diagrams, theme_css="")
    assert "window._epy_init_nomnoml()" in html
    assert '<pre class="nomnoml">' in html


def test_diagram_page_html_escapes_body():
    """Diagram bodies are HTML-escaped inside the page."""
    diagrams = [("mermaid", "A & <B>")]
    html = _diagram_page_html(diagrams, theme_css="")
    assert "&amp;" in html
    assert "&lt;B&gt;" in html


def test_collect_diagrams_handles_attribute_fences():
    """An attribute-style ```{.mermaid} fence is recognised."""
    src = "```{.mermaid}\nflowchart LR\nA-->B\n```\n"
    assert collect_diagrams(src) == [("mermaid", "flowchart LR\nA-->B")]


# ---------------------------------------------------------------------------
# render_diagram_pngs — early-return paths (no event loop driven)
# ---------------------------------------------------------------------------


def test_render_diagram_pngs_empty_returns_empty(tmp_path: Path):
    """No diagrams yields no PNG results."""
    assert render_diagram_pngs([], tmp_path) == []


def test_render_diagram_pngs_without_qapplication(tmp_path, monkeypatch):
    """With no running QApplication every diagram returns None."""
    from PySide6.QtWidgets import QApplication

    monkeypatch.setattr(QApplication, "instance", staticmethod(
        lambda: None
    ))
    out = render_diagram_pngs(
        [("mermaid", "flowchart LR\nA-->B")], tmp_path
    )
    assert out == [None]


def test_render_diagram_pngs_without_webengine_module(tmp_path, monkeypatch):
    """A missing QtWebEngineWidgets (e.g. a minimal PySide6 install) is
    absorbed the same way as no QApplication: every diagram returns None.

    ``None`` in sys.modules for a dotted import target is Python's own
    documented way to force ImportError on that import without actually
    uninstalling anything.
    """
    monkeypatch.setitem(sys.modules, "PySide6.QtWebEngineWidgets", None)
    out = render_diagram_pngs(
        [("mermaid", "flowchart LR\nA-->B")], tmp_path
    )
    assert out == [None]


class _FakeSignal:
    """Minimal Qt-signal stand-in: connect() + a deferred (timer-based) emit.

    Firing via ``QTimer.singleShot`` (rather than synchronously, inline)
    means the caller's own ``while not ready: app.processEvents()``
    busy-wait loop actually has to spin at least once before the value
    shows up -- the same shape a REAL asynchronous WebEngine signal has,
    and the only way to exercise those polling-loop bodies at all.
    """

    def __init__(self) -> None:
        self._slot = None

    def connect(self, slot):
        self._slot = slot

    def emit_later(self, *args, delay_ms: int = 10):
        from PySide6.QtCore import QTimer

        QTimer.singleShot(delay_ms, lambda: self._fire(*args))

    def _fire(self, *args):
        if self._slot is not None:
            self._slot(*args)


class _FakePage:
    """Answers runJavaScript asynchronously from a canned response map.

    The ``window._md === true`` probe reports "not ready" the first time
    it is asked and "ready" from then on, so render_diagram_pngs's outer
    retry loop (``while js(...) is not True: pump(...)``) genuinely
    retries once, the same way it would while a real diagram is still
    rendering.
    """

    def __init__(self, responses: dict[str, object]) -> None:
        self._responses = responses
        self._md_calls = 0

    def runJavaScript(self, expr, callback):  # noqa: N802 - Qt API name
        from PySide6.QtCore import QTimer

        if expr == "window._md === true":
            self._md_calls += 1
            value = self._responses[expr] if self._md_calls >= 2 else False
        else:
            value = self._responses.get(expr)
        QTimer.singleShot(10, lambda: callback(value))


class _FakeWebView:
    """Stands in for QWebEngineView so no real page load/JS engine runs.

    A real offscreen WebEngine view can be slow or flaky to load a page
    and run its JS engine in a test environment; this fake answers the
    same signals/callbacks render_diagram_pngs waits on, but from a
    timer instead of a real page load, so the function's own Python-side
    logic (polling, scaling, cropping, saving) is exercised
    deterministically and quickly.
    """

    def __init__(self, responses: dict[str, object]) -> None:
        self.loadFinished = _FakeSignal()
        self._page = _FakePage(responses)
        self._pixmap = QPixmap(400, 300)
        self._pixmap.fill()

    def setAttribute(self, *_a):  # noqa: N802 - Qt API name
        pass

    def resize(self, *_a):
        pass

    def show(self):
        pass

    def load(self, _url):
        self.loadFinished.emit_later(True)

    def page(self):
        return self._page

    def width(self):
        return 400

    def grab(self):
        return self._pixmap

    def deleteLater(self):  # noqa: N802 - Qt API name
        pass


def test_render_diagram_pngs_happy_path_saves_a_png(
    qapp, tmp_path, monkeypatch
):
    """A successful render crops a real PNG per diagram from the page grab."""
    diagrams = [("mermaid", "flowchart LR\nA-->B")]
    responses = {
        "window._md === true": True,
        media_export._RECTS_JS: json.dumps([[10, 10, 100, 80]]),
    }
    monkeypatch.setattr(
        QtWebEngineWidgets, "QWebEngineView", lambda: _FakeWebView(responses)
    )
    out = render_diagram_pngs(diagrams, tmp_path)
    assert len(out) == 1
    assert out[0] is not None
    assert out[0].is_file()
    assert out[0].stat().st_size > 0


def test_render_diagram_pngs_skips_a_too_small_rect(
    qapp, tmp_path, monkeypatch
):
    """A rect narrower/shorter than 2px is skipped (result stays None).

    Counter-example to the happy path: not every reported rect becomes a
    saved PNG.
    """
    diagrams = [("mermaid", "flowchart LR\nA-->B")]
    responses = {
        "window._md === true": True,
        media_export._RECTS_JS: json.dumps([[0, 0, 1, 1]]),
    }
    monkeypatch.setattr(
        QtWebEngineWidgets, "QWebEngineView", lambda: _FakeWebView(responses)
    )
    out = render_diagram_pngs(diagrams, tmp_path)
    assert out == [None]


def test_render_diagram_pngs_ignores_rects_past_the_diagram_count(
    qapp, tmp_path, monkeypatch
):
    """Extra rects beyond len(diagrams) are ignored, not indexed into.

    Exercises the ``if i >= len(diagrams): break`` guard.
    """
    diagrams = [("mermaid", "flowchart LR\nA-->B")]
    responses = {
        "window._md === true": True,
        media_export._RECTS_JS: json.dumps(
            [[0, 0, 50, 50], [0, 0, 50, 50]]
        ),
    }
    monkeypatch.setattr(
        QtWebEngineWidgets, "QWebEngineView", lambda: _FakeWebView(responses)
    )
    out = render_diagram_pngs(diagrams, tmp_path)
    assert len(out) == 1


def test_render_diagram_pngs_malformed_rects_json_is_absorbed(
    qapp, tmp_path, monkeypatch
):
    """Malformed JSON from the rects probe is caught, not propagated.

    Exercises the ``except (OSError, RuntimeError, ValueError)`` branch:
    json.loads raises json.JSONDecodeError (a ValueError subclass) on the
    non-JSON string, and the function must still return cleanly.
    """
    diagrams = [("mermaid", "flowchart LR\nA-->B")]
    responses = {
        "window._md === true": True,
        media_export._RECTS_JS: "not valid json",
    }
    monkeypatch.setattr(
        QtWebEngineWidgets, "QWebEngineView", lambda: _FakeWebView(responses)
    )
    out = render_diagram_pngs(diagrams, tmp_path)
    assert out == [None]
