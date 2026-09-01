"""Every call into the shared stamping engine passes what it requires.

`epy_export.add_metadata` takes `creator` and `producer` as required
keywords with NO default: the shared engine refuses to guess which
application produced a document, because a PDF that claims the wrong
producer is worse than one that claims none.

Required keywords are added upstream, in another repository, and a call
site that misses one fails only when that line is REACHED. This one was
`_ui/tab.py` -- the PDF export of the window itself -- so the defect
shipped: every export from the interface raised TypeError, and the
`except (OSError, RuntimeError)` around it does not even catch that.

Reading the calls rather than running them is the point. The window's
export path needs a rendered document, a Qt web engine and a real file
on disk; this check costs milliseconds and would have caught it.
"""

from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"

REQUIRED = {
    "add_metadata": {"creator", "producer"},
}
"""Function name -> keywords it will not default for the caller."""


def _calls(tree: ast.AST) -> list[ast.Call]:
    return [node for node in ast.walk(tree) if isinstance(node, ast.Call)]


def _called_name(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return ""


def test_every_stamping_call_passes_the_keywords_it_must() -> None:
    missing: list[str] = []
    for path in sorted(SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
        for call in _calls(tree):
            name = _called_name(call)
            needed = REQUIRED.get(name)
            if needed is None:
                continue
            given = {kw.arg for kw in call.keywords if kw.arg}
            absent = needed - given
            if absent:
                where = path.relative_to(SRC)
                missing.append(
                    f"{where}:{call.lineno} calls {name} without "
                    f"{', '.join(sorted(absent))}"
                )
    assert not missing, "\n".join(missing)


def test_the_check_can_actually_see_a_missing_keyword() -> None:
    # The control. Without it, a walker that found no calls at all --
    # a wrong root, a changed attribute shape -- would pass the test
    # above forever while checking nothing.
    tree = ast.parse("stamp.add_metadata(path, title='t', creator='c')")
    call = _calls(tree)[0]
    given = {kw.arg for kw in call.keywords if kw.arg}
    assert REQUIRED["add_metadata"] - given == {"producer"}


def test_the_check_actually_reaches_the_real_call_sites() -> None:
    # The second control: prove the walk FINDS the calls it is meant to
    # guard. A green run over zero call sites is not a green run.
    found = 0
    for path in sorted(SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
        found += sum(
            1 for call in _calls(tree) if _called_name(call) in REQUIRED
        )
    assert found >= 2, f"only {found} stamping call site(s) seen"
