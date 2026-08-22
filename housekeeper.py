#!/usr/bin/env python3
"""Minimal housekeeper — ePy Suite (auto-generated).

Usage:
    python housekeeper.py                # dry-run: report only
    python housekeeper.py --apply        # delete temp/cache
    python housekeeper.py --quality      # ruff + pyright + coverage report
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

# ── Root of THIS library ──────────────────────────────────────────────
LIB_ROOT = Path(__file__).resolve().parent

def _find_pkg_dir(lib_root: Path) -> Path | None:
    """Locate src/<pkg>/. Returns None if no src/ exists or no inner package found."""
    src = lib_root / "src"
    if not src.is_dir():
        return None
    for child in src.iterdir():
        if child.is_dir() and (child / "__init__.py").exists():
            return child
    return None


# ── Quality check (shared module) ─────────────────────────────────────
_QUALITY_CHECK_AVAILABLE = False
try:
    _repo_root = LIB_ROOT.parent
    _qc_path = _repo_root / "_packaging" / "quality_check.py"
    if _qc_path.is_file():
        import importlib.util
        _spec = importlib.util.spec_from_file_location("_quality_check", _qc_path)
        if _spec and _spec.loader:
            _mod = importlib.util.module_from_spec(_spec)
            _spec.loader.exec_module(_mod)
            _run_qc = _mod.run_quality_check
            _print_qr = _mod.print_report
            _QUALITY_CHECK_AVAILABLE = True
except Exception:
    pass

DIRS_TO_DELETE = {"__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache"}
EXTENSIONS_TO_DELETE = {".pyc", ".pyo"}
PROTECTED = {"src", "tests", "docs", "pyproject.toml", "CLAUDE.md", "README.md",
             "LICENSE", ".gitignore", ".git", ".venv", "housekeeper.py"}


def collect_targets(root: Path) -> list[Path]:
    targets = []
    for path in root.rglob("*"):
        if any(part.startswith(".") and part in DIRS_TO_DELETE for part in path.parts):
            if path.is_dir() and path.name in DIRS_TO_DELETE:
                targets.append(path)
        elif path.suffix in EXTENSIONS_TO_DELETE:
            targets.append(path)
    return targets


def audit_tests_layout(lib_root: Path) -> list[str]:
    """Audit tests/ against the canonical mirror-of-src layout (EPY_SUITE_RULES.md Sec.9).

    Allowed directories at tests/ root = {every top-level dir name actually
    present under src/<pkg>/} UNION {"_benchmarks"} -- derived DYNAMICALLY from
    src/ so the same rule works for every domain folder name (_design,
    _analysis, ...) without hardcoding one. Loose test_*.py files at tests/
    root are package-surface tests and are always allowed, same as
    conftest.py and __init__.py. Returns a list of violation strings (empty
    = compliant).
    """
    pkg = _find_pkg_dir(lib_root)
    if pkg is None:
        return []
    tests_root = lib_root / "tests"
    if not tests_root.is_dir():
        return []

    allowed_dirs = {"_benchmarks"}
    for child in pkg.iterdir():
        if child.is_dir() and child.name != "__pycache__":
            allowed_dirs.add(child.name)

    violations: list[str] = []
    for child in sorted(tests_root.iterdir()):
        if child.name in {"__pycache__", ".pytest_cache"}:
            continue
        if child.is_file():
            continue
        if child.is_dir() and child.name not in allowed_dirs:
            violations.append(
                f"tests/{child.name}/ has no matching src/{pkg.name}/{child.name}/ "
                f"and is not the sanctioned tests/_benchmarks/ exception -- forbidden "
                f"non-mirror folder (EPY_SUITE_RULES.md Sec.9)."
            )
    return violations


def report_tests_layout(violations: list[str]) -> None:
    if not violations:
        print("\n  Tests layout: OK (mirrors src/<pkg>/ + sanctioned _benchmarks/ exception)")
        return
    print(f"\n  TESTS-LAYOUT VIOLATIONS ({len(violations)} total):")
    for v in violations:
        print(f"    [!] {v}")


def _is_mirror_exempt(rel: str) -> bool:
    """Whether ``rel`` is not a unit-test target.

    Integration / packaging / schema / showcase modules are exempt.

    SYNCED from _packaging/_tooling/module_mirror_block.py -- edit it THERE
    and re-run add_hk_module_mirror_xsuite.py --apply. A local edit here is
    overwritten by the next sync.
    """
    name = rel.rsplit("/", 1)[-1]
    # No blanket exemption for ``epy_suite_connect/``, and none for
    # adapters: measured across the suite, 96 of the 110 adapter modules
    # already ship a mirroring test, so "integration code is not a
    # unit-test target" is not the convention here -- it was a licence for
    # the gate to go blind on whole packages. The clause that used to sit
    # here exempted ``adapters/`` (six repos spell it that way, five spell
    # it ``_adapters/``), and what it hid was the one adapter nobody
    # tests: ``_export_estrulab.py``, byte-identical in seven repos.
    if "/_packaging/" in rel or name in (
        "download_wheels.py",
        "install_offline.py",
        "__main__.py",
    ):
        return True
    if "_schemas/" in rel:
        return True
    return name in ("_famous.py", "_demo.py", "_showcase.py")


def _mirror_import_roots(src: Path) -> set[str]:
    """Top-level import roots this repo ships under ``src/``.

    Every directory directly under ``src/`` is a root, with or without an
    ``__init__.py``: PEP 420 namespace packages are importable too, and a
    root filter that demanded ``__init__.py`` would simply stop checking
    whatever lives in one.
    """
    if not src.is_dir():
        return set()
    return {
        c.name
        for c in src.iterdir()
        if c.is_dir() and c.name != "__pycache__"
    }


def _mirror_module_exists(src: Path, dotted: str) -> bool:
    """Whether ``dotted`` resolves to a real module or package under src/.

    PEP 420 aware ON PURPOSE. A directory WITHOUT ``__init__.py`` is a
    legitimate namespace package and imports fine; an earlier probe that
    required ``__init__.py`` reported 20 false positives on exactly those
    directories. The three accepted shapes are therefore ``<path>.py``,
    ``<path>/__init__.py``, and a bare ``<path>/`` directory.
    """
    target = src.joinpath(*dotted.split("."))
    if target.with_suffix(".py").is_file():
        return True
    return target.is_dir()


def _mirror_dead_imports(
    test_path: Path, src: Path, roots: set[str]
) -> list[str]:
    """Dotted imports in ``test_path`` naming no module under ``src/``.

    THE REASON THIS RULE EXISTS. The mirror gate used to be pure PRESENCE:
    it collected the NAME of every ``tests/**/test_*.py`` into a flat set
    and never opened the file. The file
    ``epy_buildings/tests/_core/test_optimization.py`` imported
    ``epy_buildings._core._optimization``, which does not exist -- the
    module is at ``_design/_optimization.py``. Every pytest collection of
    that repo raised ModuleNotFoundError from 2026-07-23 to 2026-08-20,
    and this gate counted the broken file as coverage the whole time.

    Only imports rooted in a package this repo ships are checked; a sibling
    library's module is not on this repo's disk and is none of this gate's
    business. Relative imports are skipped -- resolving them needs the
    test's own package identity, which the flat-name convention that this
    gate is built on does not pin down.
    """
    import ast as _ast

    try:
        source = test_path.read_text(encoding="utf-8", errors="replace")
        tree = _ast.parse(source)
    except SyntaxError as e:
        return [f"does not parse, so its imports cannot be verified - {e}"]

    dead: list[str] = []
    seen: set[str] = set()
    for node in _ast.walk(tree):
        dotted_names: list[str] = []
        if isinstance(node, _ast.Import):
            dotted_names = [a.name for a in node.names]
        elif isinstance(node, _ast.ImportFrom):
            if node.level or not node.module:
                continue
            dotted_names = [node.module]
        for dotted in dotted_names:
            if dotted in seen or dotted.split(".")[0] not in roots:
                continue
            seen.add(dotted)
            if not _mirror_module_exists(src, dotted):
                dead.append(f"imports `{dotted}`, which does not exist")
    return dead


def _mirror_advisory(store: list[str] | None = None) -> list[str]:
    """Carry the path-parity advisory from the audit to the report.

    ``report_module_mirror(violations)`` is called with exactly one
    argument in all twenty-nine housekeepers; widening that signature would
    make this sync rewrite twenty-nine call sites in ``main()`` as well. A
    tiny accessor keeps the wiring untouched and keeps the advisory out of
    the ``--strict`` failure tuple, which is the point: path parity is a
    WARNING, never a failure.
    """
    if store is not None:
        _mirror_advisory.lines = list(store)
    return getattr(_mirror_advisory, "lines", [])


def audit_module_mirror(lib_root: Path) -> list[str]:
    """Every real src module needs a mirroring test whose imports RESOLVE.

    Two checks, both failures:

    1. PRESENCE -- a ``test_<stem>.py`` or ``test_<stem>_*.py`` exists
       somewhere under ``tests/``. Closes the gap left by the folder-level
       tests-layout audit, which reports OK even when a module has no test.
    2. IMPORTABILITY -- every crediting test parses, and every dotted
       import it makes into a package this repo ships resolves to a real
       module or package on disk. A test that cannot be imported is not
       coverage, and for a month one of them was counted as coverage.

    Path parity -- does the test sit at the MIRRORED path? -- is
    deliberately NOT a failure. Measured 2026-08-21 across the suite: 359
    mirrors, 26% of them, live at a non-mirrored path, and the bulk of
    those follow two conventions the suite chose on purpose. It is
    reported as an advisory instead; see ``report_module_mirror``.

    SYNCED from _packaging/_tooling/module_mirror_block.py -- edit it THERE
    and re-run add_hk_module_mirror_xsuite.py --apply. A local edit here is
    overwritten by the next sync.
    """
    pkg = _find_pkg_dir(lib_root)
    if pkg is None:
        return [
            f"src/<pkg>/ not found under {lib_root} -- cannot audit "
            f"module mirror."
        ]
    src = pkg.parent
    roots = _mirror_import_roots(src)

    tests = lib_root / "tests"
    # stem -> the test files carrying that stem. The old gate kept only the
    # NAMES, in a flat set, and threw the paths away -- which is why it
    # could neither open the file nor say where the mirror actually lived.
    by_name: dict[str, list[Path]] = {}
    if tests.is_dir():
        for p in tests.rglob("test_*.py"):
            if "__pycache__" not in p.parts:
                by_name.setdefault(p.name, []).append(p)

    violations: list[str] = []
    crediting: dict[Path, None] = {}
    off_mirror: list[tuple[str, str]] = []

    for m in sorted(pkg.rglob("*.py")):
        if "__pycache__" in m.parts or m.name == "__init__.py":
            continue
        rel = m.relative_to(pkg).as_posix()
        if _is_mirror_exempt(rel):
            continue
        bare = m.name[:-3].lstrip("_")
        if bare in ("utils", "types", "constants", "typing", "protocols"):
            continue
        mirrors = list(by_name.get(f"test_{bare}.py", []))
        for name, paths in by_name.items():
            if name.startswith(f"test_{bare}_") and name.endswith(".py"):
                mirrors.extend(paths)
        if not mirrors:
            violations.append(
                f"src module without mirroring test: "
                f"src/{pkg.name}/{rel} -- add tests/.../test_{bare}.py "
                f"(suite-wide tests-mirror DNA)."
            )
            continue
        for t in mirrors:
            crediting[t] = None
        # Path parity, advisory only. The mirrored home of
        # src/<pkg>/a/b/c.py is tests/a/b/test_c.py.
        want_dir = (tests / rel).parent
        if not any(t.parent == want_dir for t in mirrors):
            where = mirrors[0].relative_to(lib_root).parent.as_posix()
            off_mirror.append((rel, where))

    for t in sorted(crediting):
        where = t.relative_to(lib_root).as_posix()
        for problem in _mirror_dead_imports(t, src, roots):
            violations.append(
                f"mirroring test {where} {problem} -- it cannot be "
                f"collected, so it is not coverage; point it at the real "
                f"module or delete it."
            )

    # Two conventions the suite adopted deliberately. They are named here
    # so the advisory does NOT advise against them.
    flat_connect = sum(
        1 for rel, _ in off_mirror if "epy_suite_connect/" in rel
    )
    root_designer = sum(
        1
        for rel, _ in off_mirror
        if "/" not in rel and rel.endswith("_designer.py")
    )
    advisory: list[str] = []
    if off_mirror:
        residual = len(off_mirror) - flat_connect - root_designer
        advisory.append(
            f"{len(off_mirror)} mirroring test(s) sit at a non-mirrored "
            f"path ({flat_connect} flat epy_suite_connect, "
            f"{root_designer} root designer, {residual} other). Advisory "
            f"only -- the mirror is credited either way."
        )
        for rel, where in off_mirror[:8]:
            advisory.append(f"src/{pkg.name}/{rel} -> {where}/")
        if len(off_mirror) > 8:
            advisory.append(f"... and {len(off_mirror) - 8} more")
    _mirror_advisory(advisory)
    return violations


def report_module_mirror(violations: list[str]) -> None:
    """Print the module-mirror result, then the path-parity advisory.

    The advisory prints separately and never enters the ``--strict``
    failure tuple. The two conventions it names are SANCTIONED, and must
    not be "fixed":

    * the flat ``tests/epy_suite_connect/test_*.py`` layout mirroring
      ``epy_suite_connect/{adapters,_adapters,_contract}/*.py``;
    * root designer modules ``src/<pkg>/<x>_designer.py`` tested from
      ``tests/_design/``.
    """
    if not violations:
        print(
            "\n  Module mirror: OK (every real src module has a mirroring "
            "test, and every one of them imports)"
        )
    else:
        print(f"\n  MODULE-MIRROR VIOLATIONS ({len(violations)} total):")
        for v in violations:
            print(f"    - {v}")
    advisory = _mirror_advisory()
    if advisory:
        print(
            f"\n  Module mirror path parity (advisory, NOT a failure): "
            f"{advisory[0]}"
        )
        for line in advisory[1:]:
            print(f"    . {line}")


# ============================================================
#                    TUTORIALS LAYOUT (3 categories)
# ============================================================

# The only three tutorial categories the suite recognises. A library
# teaches at three levels and nothing else: undergraduate, professional
# practice, research.
TUTORIAL_CATEGORIES = ("educational", "professional", "research")


def audit_tutorials_layout(lib_root: Path) -> list[str]:
    """``tutorials/`` holds exactly the three canonical categories.

    Infrastructure directories (leading ``_`` or ``.``) are exempt: they
    are not tutorial categories. Everything else is a violation.
    ``pedagogical/``, ``validation/``, ``api/``, ``case/``, ``examples/``
    and the numbered tracks were folded into the three during ORDER O4,
    and without this gate nothing stops them coming back.

    Empty list = compliant. A repo with no ``tutorials/`` is compliant.
    """
    tutorials = lib_root / "tutorials"
    if not tutorials.is_dir():
        return []
    present = {c.name for c in tutorials.iterdir() if c.is_dir()}
    if not present & set(TUTORIAL_CATEGORIES):
        # A repo publishing none of the three is a different family: a
        # book (epy_docs: chapters/, images/), a paper, an app.
        # STRUCTURE_STANDARD Sec.1 forbids cross-applying one family's
        # layout rules to another, so the law binds only a repo that
        # teaches at these levels at all.
        return []
    violations: list[str] = []
    for child in sorted(tutorials.iterdir()):
        if not child.is_dir():
            continue
        name = child.name
        if name.startswith(("_", ".")):
            continue
        if name in TUTORIAL_CATEGORIES:
            continue
        violations.append(
            f"tutorials/{name}/ is not a tutorial category -- tutorials/ "
            f"holds exactly {', '.join(TUTORIAL_CATEGORIES)}. Move its "
            f"contents into one of them (STRUCTURE_STANDARD.md Sec.2.7)."
        )
    return violations


def report_tutorials_layout(violations: list[str]) -> None:
    """Print the tutorials-layout verdict."""
    if not violations:
        print("\n  Tutorials layout: OK (the three categories only)")
    else:
        print(f"\n  TUTORIALS-LAYOUT VIOLATIONS ({len(violations)} total):")
        for v in violations:
            print(f"    - {v}")


# --- documented standard ids (referential integrity) -------------------------
# Imported from the ONE canonical source rather than copied: Rule 13 was rolled
# out by injection and its copies drifted apart, so the same rule behaved
# differently per library. See _packaging/_tooling/doc_standard_refs_block.py.
_DOC_REFS_BLOCK = (
    Path(__file__).resolve().parent.parent / "_packaging" / "_tooling"
    / "doc_standard_refs_block.py"
)
if _DOC_REFS_BLOCK.exists():
    import importlib.util as _ilu

    _spec = _ilu.spec_from_file_location("_doc_standard_refs_block", _DOC_REFS_BLOCK)
    _mod = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    audit_doc_standard_refs_strict = _mod.audit_doc_standard_refs_strict
    report_doc_standard_refs = _mod.report_doc_standard_refs
else:  # pragma: no cover - only when the tooling repo is absent

    def audit_doc_standard_refs_strict(lib_root):
        return [
            "doc-standard-refs: _packaging/_tooling/doc_standard_refs_block.py "
            "is missing, so documented standard ids were NOT checked. This is a "
            "loud failure on purpose: a silently skipped rule is worse than none."
        ]

    def report_doc_standard_refs(violations):
        print("\n" + "=" * 70)
        print("  DOCUMENTED STANDARD IDS (referential integrity)")
        print("=" * 70)
        for _v in violations:
            print(f"    - {_v}")


# ----------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="ePy Suite Minimal Housekeeper")
    parser.add_argument("--apply", action="store_true", help="Delete temp/cache files")
    parser.add_argument("--quality", action="store_true", help="Run ruff + pyright + coverage checks")
    parser.add_argument(
        "--audit", action="store_true", help="Run only the read-only audits (tests layout, etc.)"
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="Exit code 1 if the module-mirror audit reports violations.",
    )
    args = parser.parse_args()

    lib_name = LIB_ROOT.name
    print("=" * 60)
    print(f"  Housekeeper: {lib_name}")
    print(f"  Root: {LIB_ROOT}")
    print("=" * 60)

    # ── Cleanup ───────────────────────────────────────────────────────
    targets = collect_targets(LIB_ROOT)
    if targets:
        for t in targets:
            print(f"    {t.relative_to(LIB_ROOT)}")
        print(f"\n  Total items: {len(targets)}")
        if args.apply:
            for t in targets:
                if t.is_dir():
                    shutil.rmtree(t, ignore_errors=True)
                else:
                    t.unlink(missing_ok=True)
            print("  DONE — removed.")
        else:
            print("  Re-run with --apply to delete.")
    else:
        print("\n  Library is clean.")

    # ── Quality check ─────────────────────────────────────────────────
    if args.quality:
        if _QUALITY_CHECK_AVAILABLE:
            qc_result = _run_qc(LIB_ROOT)
            _print_qr(qc_result, lib_name)
        else:
            print("\n  --quality requires _packaging/quality_check.py")

    # ── Structure audit (basic) ───────────────────────────────────────
    src_dir = LIB_ROOT / "src"
    if not src_dir.is_dir():
        print("\n  WARNING: no src/ directory (library may not be built yet)")

    # ── Tests layout audit (mirrors src/<pkg>/ + sanctioned _benchmarks/ exception) ──
    tests_layout_violations = audit_tests_layout(LIB_ROOT)
    report_tests_layout(tests_layout_violations)

    # Module-level tests-mirror audit (every real src module has a
    # mirroring test -- suite-wide DNA).
    module_mirror_violations = audit_module_mirror(LIB_ROOT)
    report_module_mirror(module_mirror_violations)

    tutorials_layout_violations = audit_tutorials_layout(LIB_ROOT)
    report_tutorials_layout(tutorials_layout_violations)

    # Documented standard ids must name a catalogued document
    doc_ref_violations = audit_doc_standard_refs_strict(LIB_ROOT)
    report_doc_standard_refs(doc_ref_violations)

    if args.strict and (
        doc_ref_violations
        or         module_mirror_violations or tutorials_layout_violations
    ):
        sys.exit(1)

    print()


if __name__ == "__main__":
    main()
