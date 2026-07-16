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


def main() -> None:
    parser = argparse.ArgumentParser(description="ePy Suite Minimal Housekeeper")
    parser.add_argument("--apply", action="store_true", help="Delete temp/cache files")
    parser.add_argument("--quality", action="store_true", help="Run ruff + pyright + coverage checks")
    parser.add_argument(
        "--audit", action="store_true", help="Run only the read-only audits (tests layout, etc.)"
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

    print()


if __name__ == "__main__":
    main()
