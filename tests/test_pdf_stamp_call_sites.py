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


# ---------------------------------------------------------------------------
# Imports that name nothing
# ---------------------------------------------------------------------------


def _own_imports(tree: ast.AST, package: str) -> list[str]:
    """Dotted names this file imports from its OWN package.

    Both spellings count. ``import pkg.a.b`` names a module; ``from
    pkg.a import b`` names ``b`` inside ``pkg.a``, and ``b`` may be a
    module that does not exist even though ``pkg.a`` does -- which is
    exactly the half of this that a module-only check misses.
    """
    dotted: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            dotted += [
                alias.name
                for alias in node.names
                if alias.name.split(".")[0] == package
            ]
        elif isinstance(node, ast.ImportFrom):
            if node.level or not node.module:
                continue
            if node.module.split(".")[0] != package:
                continue
            dotted += [f"{node.module}.{a.name}" for a in node.names]
    return dotted


def _resolves(dotted: str) -> bool:
    """Whether ``dotted`` is a module, a package, or a name in one."""
    target = SRC.joinpath(*dotted.split("."))
    if target.with_suffix(".py").is_file() or target.is_dir():
        return True
    # `from pkg.mod import name`: the parent must exist and define it.
    parent = SRC.joinpath(*dotted.split(".")[:-1])
    leaf = dotted.rsplit(".", 1)[-1]
    for candidate in (parent.with_suffix(".py"), parent / "__init__.py"):
        if candidate.is_file():
            source = candidate.read_text(encoding="utf-8", errors="replace")
            return leaf in ast.dump(ast.parse(source))
    return False


def test_no_source_file_imports_a_module_that_does_not_exist() -> None:
    # THE REASON THIS EXISTS. When the PDF stamping moved to epy_export,
    # two call sites in the window's export kept importing the local
    # `_core._pdf_footer` that had gone with it. Both sit inside the
    # export function, so nothing failed at import time and no test
    # reached them -- the export tests patch `export_pdf` and never run
    # its body. Every PDF export from the interface raised
    # ModuleNotFoundError, in a build that had already shipped.
    package = SRC.name if (SRC / "__init__.py").is_file() else None
    if package is None:
        package = next(p.name for p in SRC.iterdir() if p.is_dir())
    dead: list[str] = []
    for path in sorted(SRC.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
        for dotted in _own_imports(tree, package):
            if not _resolves(dotted):
                dead.append(f"{path.relative_to(SRC)} imports {dotted}")
    assert not dead, "imports naming nothing on disk: " + "; ".join(dead)


def test_the_dead_import_check_can_see_a_dead_import() -> None:
    # The control. A resolver that answered True for everything would
    # pass the test above over any amount of rot.
    package = SRC.name if (SRC / "__init__.py").is_file() else None
    if package is None:
        package = next(p.name for p in SRC.iterdir() if p.is_dir())
    tree = ast.parse(f"from {package}._core import _gone_module")
    assert _own_imports(tree, package) == [f"{package}._core._gone_module"]
    assert not _resolves(f"{package}._core._gone_module")
