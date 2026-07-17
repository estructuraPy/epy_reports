"""Tests for housekeeper.py — the minimal ePy Suite housekeeper.

The module is loaded via importlib.util so it can be exercised without
having it on sys.path as a regular package.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Loader helper
# ---------------------------------------------------------------------------

_HK_PATH = Path(__file__).resolve().parent.parent / "housekeeper.py"


def _load_housekeeper():
    """Load housekeeper.py as a module from its absolute path."""
    spec = importlib.util.spec_from_file_location("housekeeper", _HK_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


# ---------------------------------------------------------------------------
# Sandbox builder
# ---------------------------------------------------------------------------


def _build_sandbox(base: Path) -> dict[str, Path]:
    """Create a fake library tree for housekeeper tests.

    Structure::
        base/
          src/
            mylib/__pycache__/          ← cache dir to collect
              module.cpython-310.pyc   ← .pyc to collect
            mylib/module.py            ← protected source
          tests/
            .pytest_cache/             ← cache dir to collect
          build/
            artifact.pyo               ← .pyo to collect
          .ruff_cache/                 ← cache dir to collect (top-level)
          housekeeper.py               ← protected
          pyproject.toml               ← protected
    """
    paths = {}

    # Protected source
    src = base / "src" / "mylib"
    src.mkdir(parents=True)
    (src / "module.py").write_text("# source")
    paths["source_py"] = src / "module.py"

    # __pycache__ dir + .pyc inside
    pycache = src / "__pycache__"
    pycache.mkdir()
    pyc = pycache / "module.cpython-310.pyc"
    pyc.write_bytes(b"fake")
    paths["pycache_dir"] = pycache
    paths["pyc_file"] = pyc

    # .pytest_cache dir (inside tests/)
    test_dir = base / "tests"
    test_dir.mkdir()
    pytest_cache = test_dir / ".pytest_cache"
    pytest_cache.mkdir()
    paths["pytest_cache"] = pytest_cache

    # .ruff_cache at top level
    ruff_cache = base / ".ruff_cache"
    ruff_cache.mkdir()
    paths["ruff_cache"] = ruff_cache

    # .pyo file inside a build directory
    build_dir = base / "build"
    build_dir.mkdir()
    pyo = build_dir / "artifact.pyo"
    pyo.write_bytes(b"fake")
    paths["pyo_file"] = pyo

    # Protected file at root
    (base / "housekeeper.py").write_text("# housekeeper")
    (base / "pyproject.toml").write_text("[project]")

    return paths


# ---------------------------------------------------------------------------
# TestCollectTargets
# ---------------------------------------------------------------------------


class TestCollectTargets:
    def test_collects_pytest_cache(self, tmp_path):
        """collect_targets finds dotted cache dirs (.pytest_cache, .ruff_cache)."""
        hk = _load_housekeeper()
        _build_sandbox(tmp_path)
        targets = hk.collect_targets(tmp_path)
        names = [t.name for t in targets]
        assert ".pytest_cache" in names

    def test_collects_ruff_cache(self, tmp_path):
        hk = _load_housekeeper()
        _build_sandbox(tmp_path)
        targets = hk.collect_targets(tmp_path)
        names = [t.name for t in targets]
        assert ".ruff_cache" in names

    def test_collects_pyc_file(self, tmp_path):
        """collect_targets picks up .pyc files regardless of parent directory."""
        hk = _load_housekeeper()
        paths = _build_sandbox(tmp_path)
        targets = hk.collect_targets(tmp_path)
        assert paths["pyc_file"] in targets

    def test_collects_pyo_file(self, tmp_path):
        """collect_targets picks up .pyo files."""
        hk = _load_housekeeper()
        paths = _build_sandbox(tmp_path)
        targets = hk.collect_targets(tmp_path)
        assert paths["pyo_file"] in targets

    def test_does_not_collect_source_py(self, tmp_path):
        """collect_targets never collects plain .py source files."""
        hk = _load_housekeeper()
        paths = _build_sandbox(tmp_path)
        targets = hk.collect_targets(tmp_path)
        assert paths["source_py"] not in targets

    def test_empty_dir_returns_empty_list(self, tmp_path):
        hk = _load_housekeeper()
        empty = tmp_path / "empty_lib"
        empty.mkdir()
        assert hk.collect_targets(empty) == []

    def test_returns_list(self, tmp_path):
        hk = _load_housekeeper()
        result = hk.collect_targets(tmp_path)
        assert isinstance(result, list)

    def test_dotted_cache_dirs_collected_as_dirs(self, tmp_path):
        """Dotted DIRS_TO_DELETE entries are collected as directories (not their children)."""
        hk = _load_housekeeper()
        paths = _build_sandbox(tmp_path)
        targets = hk.collect_targets(tmp_path)
        # .pytest_cache dir should be in targets (not just its children)
        assert paths["pytest_cache"] in targets


# ---------------------------------------------------------------------------
# TestMainDryRun
# ---------------------------------------------------------------------------


class TestMainDryRun:
    def _run_main(self, hk, argv: list[str], sandbox: Path) -> None:
        """Patch LIB_ROOT + sys.argv and call main()."""
        hk.LIB_ROOT = sandbox
        original_argv = sys.argv[:]
        sys.argv = ["housekeeper.py"] + argv
        try:
            hk.main()
        finally:
            sys.argv = original_argv

    def test_dry_run_does_not_delete_targets(self, tmp_path, capsys):
        hk = _load_housekeeper()
        paths = _build_sandbox(tmp_path)
        self._run_main(hk, [], tmp_path)
        assert paths["pycache_dir"].exists()
        assert paths["pyc_file"].exists()

    def test_dry_run_prints_items(self, tmp_path, capsys):
        hk = _load_housekeeper()
        _build_sandbox(tmp_path)
        self._run_main(hk, [], tmp_path)
        out = capsys.readouterr().out
        assert "Total items" in out or "__pycache__" in out or ".pyc" in out

    def test_apply_deletes_pyc_file(self, tmp_path, capsys):
        """--apply removes .pyc compilation artifacts."""
        hk = _load_housekeeper()
        paths = _build_sandbox(tmp_path)
        self._run_main(hk, ["--apply"], tmp_path)
        assert not paths["pyc_file"].exists()

    def test_apply_deletes_pytest_cache(self, tmp_path, capsys):
        """--apply removes .pytest_cache directories."""
        hk = _load_housekeeper()
        paths = _build_sandbox(tmp_path)
        self._run_main(hk, ["--apply"], tmp_path)
        assert not paths["pytest_cache"].exists()

    def test_apply_deletes_ruff_cache(self, tmp_path, capsys):
        """--apply removes .ruff_cache directories."""
        hk = _load_housekeeper()
        paths = _build_sandbox(tmp_path)
        self._run_main(hk, ["--apply"], tmp_path)
        assert not paths["ruff_cache"].exists()

    def test_apply_prints_done(self, tmp_path, capsys):
        hk = _load_housekeeper()
        _build_sandbox(tmp_path)
        self._run_main(hk, ["--apply"], tmp_path)
        out = capsys.readouterr().out
        assert "DONE" in out or "removed" in out.lower()

    def test_clean_lib_prints_clean(self, tmp_path, capsys):
        hk = _load_housekeeper()
        # No cache dirs at all
        (tmp_path / "src").mkdir()
        self._run_main(hk, [], tmp_path)
        out = capsys.readouterr().out
        assert "clean" in out.lower()


# ---------------------------------------------------------------------------
# TestMainQualityBranch
# ---------------------------------------------------------------------------


class TestMainQualityBranch:
    def _run_main_no_quality(self, hk, sandbox: Path) -> str:
        """Run main() with --quality when quality module is unavailable."""
        hk.LIB_ROOT = sandbox
        hk._QUALITY_CHECK_AVAILABLE = False
        original_argv = sys.argv[:]
        sys.argv = ["housekeeper.py", "--quality"]
        try:
            hk.main()
            # capsys isn't available here but that's fine — we just confirm it runs
            return "ok"
        finally:
            sys.argv = original_argv

    def test_quality_unavailable_does_not_raise(self, tmp_path, capsys):
        hk = _load_housekeeper()
        hk.LIB_ROOT = tmp_path
        hk._QUALITY_CHECK_AVAILABLE = False
        original_argv = sys.argv[:]
        sys.argv = ["housekeeper.py", "--quality"]
        try:
            hk.main()
        finally:
            sys.argv = original_argv
        # If we got here without exception — pass
        out = capsys.readouterr().out
        assert "--quality requires" in out

    def test_quality_flag_prints_requires_message(self, tmp_path, capsys):
        hk = _load_housekeeper()
        hk.LIB_ROOT = tmp_path
        hk._QUALITY_CHECK_AVAILABLE = False
        original_argv = sys.argv[:]
        sys.argv = ["housekeeper.py", "--quality"]
        try:
            hk.main()
        finally:
            sys.argv = original_argv
        out = capsys.readouterr().out
        assert "quality_check.py" in out

    def test_quality_available_calls_run_qc(self, tmp_path, capsys):
        hk = _load_housekeeper()
        hk.LIB_ROOT = tmp_path

        call_log = []

        def fake_run_qc(root):
            call_log.append(root)
            return {"issues": []}

        def fake_print_qr(result, name):
            pass

        hk._QUALITY_CHECK_AVAILABLE = True
        hk._run_qc = fake_run_qc
        hk._print_qr = fake_print_qr

        original_argv = sys.argv[:]
        sys.argv = ["housekeeper.py", "--quality"]
        try:
            hk.main()
        finally:
            sys.argv = original_argv

        assert len(call_log) == 1

    def test_quality_available_passes_lib_root(self, tmp_path, capsys):
        hk = _load_housekeeper()
        hk.LIB_ROOT = tmp_path

        received = {}

        def fake_run_qc(root):
            received["root"] = root
            return {}

        def fake_print_qr(result, name):
            pass

        hk._QUALITY_CHECK_AVAILABLE = True
        hk._run_qc = fake_run_qc
        hk._print_qr = fake_print_qr

        original_argv = sys.argv[:]
        sys.argv = ["housekeeper.py", "--quality"]
        try:
            hk.main()
        finally:
            sys.argv = original_argv

        assert received["root"] == tmp_path
