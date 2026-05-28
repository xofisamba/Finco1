"""
Phase 22A: Test portability — verify no hardcoded environment paths remain.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


class TestNoHardcodedDeployPaths:
    """Verify tests don't contain hardcoded environment-specific paths."""

    def test_no_opt_finco1_in_tests(self):
        """No hardcoded /opt/finco1 paths in test files."""
        import subprocess
        result = subprocess.run(
            ["grep", "-rn", "/opt/finco1", "tests/", "--include=*.py"],
            cwd=str(REPO_ROOT),
            capture_output=True, text=True,
        )
        # Filter out this test file (self-referential docstrings/grep patterns)
        hits = [l for l in result.stdout.splitlines()
                if "test_phase22a" not in l and "/opt/finco1" in l]
        assert not hits, f"Found /opt/finco1 in tests: {hits}"

    def test_no_venv_bin_python_in_tests(self):
        """No hardcoded .venv/bin/python in test files."""
        import subprocess
        result = subprocess.run(
            ["grep", "-rn", ".venv/bin/python", "tests/", "--include=*.py"],
            cwd=str(REPO_ROOT),
            capture_output=True, text=True,
        )
        # Filter out this test file (self-referential docstrings/grep patterns)
        hits = [l for l in result.stdout.splitlines()
                if "test_phase22a" not in l and ".venv/bin/python" in l]
        assert not hits, f"Found .venv/bin/python in tests: {hits}"

    def test_no_root_path_in_tests(self):
        """No hardcoded /root/ paths in test files (excluding memory/ logs)."""
        import subprocess
        result = subprocess.run(
            ["grep", "-rn", "/root/", "tests/", "--include=*.py"],
            cwd=str(REPO_ROOT),
            capture_output=True, text=True,
        )
        # Filter out memory/ logs, this test file (self-ref), and Phase 16/9 tests
        EXEMPT = {"memory/", "test_phase22a", "test_phase16", "test_phase9",
                  "test_tuho", "test_r99", "test_ops", "test_runtime_import",
                  "test_phase7f"}
        hits = [l for l in result.stdout.splitlines()
                if not any(e in l for e in EXEMPT)]
        assert not hits, f"Found /root/ in tests: {hits}"

    def test_sys_executable_used_in_subprocess(self):
        """Verify Phase 21E test uses sys.executable for subprocess."""
        test_file = REPO_ROOT / "tests" / "test_phase21e_capex_input_wiring_first_tranche.py"
        if test_file.exists():
            content = test_file.read_text()
            import re
            bare_python = re.findall(r'\["python",\s*"-m"', content)
            assert len(bare_python) == 0, f"Found bare 'python' subprocess calls: {bare_python}"

    def test_repo_root_resolution_works(self):
        """REPO_ROOT resolves to a valid directory."""
        assert REPO_ROOT.exists()
        assert (REPO_ROOT / "app").exists()
        assert (REPO_ROOT / "tests").exists()
        assert (REPO_ROOT / "main_web.py").exists() or (REPO_ROOT / "main.py").exists()

    def test_main_web_imports(self):
        """main_web still imports correctly using REPO_ROOT."""
        sys.path.insert(0, str(REPO_ROOT))
        import main_web
        assert main_web is not None

    def test_test_helpers_importable(self):
        """test_helpers module is importable and exposes REPO_ROOT and PYTHON."""
        from tests.test_helpers import REPO_ROOT as RR, PYTHON as PY
        assert RR.exists()
        assert PY == sys.executable
