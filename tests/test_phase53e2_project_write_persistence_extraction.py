"""Phase 53E-2 — Project writes persistence extraction structural tests.

Verifies that the 7 top-level Group A-2 functions are present in
app/persistence/projects_repository.py and re-exported from
app/persistence/repository.py for backward compatibility.

Also verifies that the 53E-1 P0 pin still passes.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PROJECTS_PY = REPO_ROOT / "app" / "persistence" / "projects_repository.py"
REPOSITORY_PY = REPO_ROOT / "app" / "persistence" / "repository.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


GROUP_A2_TOP_LEVEL = [
    "save_project",
    "create_project_record",
    "update_project_record",
    "seed_baseline_projects_if_needed",
    "_compute_baseline_snapshot",
    "_build_default_snapshot",
    "_fill_missing_defaults",
]


# ----------------------------- Module existence ----------------------------


class TestProjectsModuleContent:
    @pytest.mark.parametrize("name", GROUP_A2_TOP_LEVEL)
    def test_projects_module_defines(self, name):
        text = _read(PROJECTS_PY)
        assert re.search(rf"^def {re.escape(name)}\(", text, re.MULTILINE), \
            f"projects_repository.py does not define {name}"

    def test_projects_module_has_save_project(self):
        text = _read(PROJECTS_PY)
        assert "def save_project(" in text

    def test_projects_module_has_compute_baseline(self):
        text = _read(PROJECTS_PY)
        assert "def _compute_baseline_snapshot(" in text

    def test_projects_module_has_seed_baseline(self):
        text = _read(PROJECTS_PY)
        assert "def seed_baseline_projects_if_needed(" in text


# ----------------------------- Repository compatibility façade ----------------------------


class TestRepositoryFacade:
    @pytest.mark.parametrize("name", GROUP_A2_TOP_LEVEL)
    def test_repository_re_exports(self, name):
        from app.persistence import repository
        assert hasattr(repository, name), f"repository.py missing re-export of {name}"

    @pytest.mark.parametrize("name", GROUP_A2_TOP_LEVEL)
    def test_repository_and_projects_share_same_object(self, name):
        from app.persistence import repository
        from app.persistence import projects_repository
        assert getattr(repository, name) is getattr(projects_repository, name), \
            f"repository.{name} is not the same object as projects_repository.{name}"

    def test_repository_has_import_block_for_projects_a2(self):
        text = _read(REPOSITORY_PY)
        assert "from app.persistence.projects_repository import" in text
        # The A-2 names are in this import block
        for name in ("save_project", "create_project_record", "update_project_record", "seed_baseline_projects_if_needed"):
            assert name in text


# ----------------------------- save_project home ----------------------------


class TestSaveProjectNewHome:
    def test_save_project_defined_in_projects_repository(self):
        text = _read(PROJECTS_PY)
        assert "def save_project(" in text

    def test_save_project_module_origin(self):
        from app.persistence import repository
        # save_project is now defined in projects_repository, not in repository
        assert repository.save_project.__module__ == "app.persistence.projects_repository", \
            f"save_project.__module__ is {repository.save_project.__module__}, expected app.persistence.projects_repository"

    def test_save_project_not_defined_in_repository_body(self):
        # save_project is now re-exported from projects_repository; the
        # function body should NOT be in repository.py anymore
        text = _read(REPOSITORY_PY)
        # The def line should be absent (only the re-export import line)
        assert "def save_project(" not in text, \
            "save_project should not be defined in repository.py body (moved to projects_repository.py)"


# ----------------------------- 53E-1 P0 pin still passes ----------------------------


class TestP0PinStillPasses:
    """The Phase 53E-1 P0 pin (41 tests) must still pass after the extraction."""

    def test_e1e1_pin_module_exists(self):
        path = REPO_ROOT / "tests" / "test_phase53e1_save_project_p0_behavior_pin.py"
        assert path.exists()

    def test_e1e1_pin_runs(self):
        import subprocess
        result = subprocess.run(
            ["python3", "-m", "pytest", str(REPO_ROOT / "tests" / "test_phase53e1_save_project_p0_behavior_pin.py"), "-q", "--tb=no"],
            capture_output=True, text=True, timeout=60
        )
        assert result.returncode == 0, f"53E-1 pin failed:\n{result.stdout}\n{result.stderr}"


# ----------------------------- Other high-risk writes NOT touched ----------------------------


class TestOtherHighRiskWritesUntouched:
    """These 3 high-risk writes are NOT in Group A-2 and must remain in repository.py.
    save_workspace_state was moved to workspace_repository in Phase 53F-2.
    save_scenario was moved to scenarios_repository in Phase 53G-4."""

    @pytest.mark.parametrize("fn_name", [
        "get_or_create_base_case_scenario",
    ])
    def test_other_high_risk_write_still_in_repository_body(self, fn_name):
        from app.persistence import repository
        assert hasattr(repository, fn_name)
        text = _read(REPOSITORY_PY)
        assert f"def {fn_name}" in text, f"{fn_name} not defined in repository.py"


# ----------------------------- _sum_opex nested helper moved ----------------------------


class TestSumOpexMoved:
    """_sum_opex is a NESTED function inside _compute_baseline_snapshot. It moves with it."""

    def test_sum_opex_only_in_projects_repository(self):
        # The nested function should not be at top level
        text = _read(PROJECTS_PY)
        # It appears inside _compute_baseline_snapshot
        assert "def _sum_opex" in text
        # It's nested (indented 8 spaces or more)
        for line in text.splitlines():
            if "def _sum_opex" in line:
                # If it's at the top level, it would be `def _sum_opex(...)` (no indent)
                # If nested, it would be `        def _sum_opex(...)` or `            def _sum_opex(...)`
                # We expect 4+ spaces of indent (it's nested inside _compute_baseline_snapshot)
                assert line.startswith("    def _sum_opex") or line.startswith("        def _sum_opex") or line.startswith("            def _sum_opex"), \
                    f"_sum_opex should be nested (indented), got: {line!r}"


# ----------------------------- repository.py LOC check ----------------------------


class TestRepositoryPyShrank:
    def test_repository_py_smaller_than_before(self):
        # Before 53E-2: 1452 lines
        # After 53E-2: 1100 lines
        with REPOSITORY_PY.open() as f:
            n = sum(1 for _ in f)
        assert n < 1452, f"repository.py should have shrunk after 53E-2, but is {n} lines"
        assert n <= 1200, f"repository.py should be ~1100 lines after 53E-2, but is {n} lines"


# ----------------------------- Public import path ----------------------------


class TestPublicImportPath:
    def test_save_project_via_repository_facade(self):
        from app.persistence.repository import save_project
        assert save_project is not None

    def test_save_project_via_projects_repository_direct(self):
        from app.persistence.projects_repository import save_project
        assert save_project is not None

    def test_both_paths_return_same_function(self):
        from app.persistence.repository import save_project as a
        from app.persistence.projects_repository import save_project as b
        assert a is b
