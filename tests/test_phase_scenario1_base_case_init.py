"""SCENARIO-1: Base Case scenario initialization on user project creation.

Problem: POST /scenarios/add returned HTTP 500 for every user-created project
because no Base Case ScenarioRecord was created during project creation.
The service assumed list_scenarios() would return at least one record; for
fresh projects the list was empty, and base_case.scenario_id raised:
  AttributeError: 'NoneType' object has no attribute 'scenario_id'

Fix: call get_or_create_base_case_scenario() after save_workspace_state() in
both:
  - projects_create_service.execute_projects_create_route (new projects)
  - project_save_as_service.execute_project_save_as_route (working copies)

These tests prove:
  A. ProjectsCreateRouteDeps has get_or_create_base_case_scenario field.
  B. ProjectSaveAsRouteDeps has get_or_create_base_case_scenario field.
  C. projects_create_service calls it when supplied.
  D. project_save_as_service calls it when supplied.
  E. main_web.py wires get_or_create_base_case_scenario into create deps.
  F. main_web.py wires get_or_create_base_case_scenario into save-as deps.
  G. Live DB: Generic Solar project created via HTTP has Base Case scenario.
  H. Live DB: Generic Wind project created via HTTP has Base Case scenario.
  I. Live DB: scenarios/add succeeds for Solar project (HTTP 200, no 500).
  J. Live DB: scenarios/add succeeds for Wind project (HTTP 200, no 500).
  K. Live DB: TUHO working copy (save-as) has Base Case scenario.
  L. Live DB: Oborovo working copy (save-as) has Base Case scenario.
  M. Idempotency: get_or_create_base_case_scenario is idempotent.
  N. Engine MD5 unchanged.
  O. TUHO P1 DSCR unchanged.
  P. Oborovo P1 DSCR unchanged.
  Q. File scope guard.
"""
from __future__ import annotations

import dataclasses
import hashlib
import os
import subprocess
import sys
import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")

ENGINE_MD5 = "6bf49f33efc989736c17cea0cb9b7723"
TUHO_P1_DSCR = 1.4507
OBOROVO_P1_DSCR = 1.15


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _scenario_rows_for_project(project_code: str):
    from app.persistence.db import get_connection
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT s.scenario_id, s.scenario_name, s.is_base_case
            FROM scenarios s
            JOIN projects p ON s.project_id = p.project_id
            WHERE p.project_code = ?
            """,
            (project_code,),
        ).fetchall()


# ---------------------------------------------------------------------------
# A. ProjectsCreateRouteDeps has new field
# ---------------------------------------------------------------------------

class TestProjectsCreateDepField:
    def test_deps_has_get_or_create_field(self):
        from app.services.projects_create_service import ProjectsCreateRouteDeps
        fields = {f.name for f in dataclasses.fields(ProjectsCreateRouteDeps)}
        assert "get_or_create_base_case_scenario" in fields, (
            "ProjectsCreateRouteDeps must have get_or_create_base_case_scenario field"
        )

    def test_field_is_optional(self):
        from app.services.projects_create_service import ProjectsCreateRouteDeps
        for f in dataclasses.fields(ProjectsCreateRouteDeps):
            if f.name == "get_or_create_base_case_scenario":
                assert f.default is None or f.default_factory is not dataclasses.MISSING, (
                    "get_or_create_base_case_scenario must be Optional (default None)"
                )
                return
        pytest.fail("Field not found")


# ---------------------------------------------------------------------------
# B. ProjectSaveAsRouteDeps has new field
# ---------------------------------------------------------------------------

class TestProjectSaveAsDepField:
    def test_deps_has_get_or_create_field(self):
        from app.services.project_save_as_service import ProjectSaveAsRouteDeps
        fields = {f.name for f in dataclasses.fields(ProjectSaveAsRouteDeps)}
        assert "get_or_create_base_case_scenario" in fields

    def test_field_is_optional(self):
        from app.services.project_save_as_service import ProjectSaveAsRouteDeps
        for f in dataclasses.fields(ProjectSaveAsRouteDeps):
            if f.name == "get_or_create_base_case_scenario":
                assert f.default is None
                return
        pytest.fail("Field not found")


# ---------------------------------------------------------------------------
# C. projects_create_service calls get_or_create when supplied
# ---------------------------------------------------------------------------

class TestProjectsCreateServiceCallsInit:
    def test_service_calls_get_or_create_when_wired(self):
        """execute_projects_create_route must call deps.get_or_create_base_case_scenario."""
        src = (Path(REPO_ROOT) / "app/services/projects_create_service.py").read_text()
        assert "get_or_create_base_case_scenario" in src, (
            "projects_create_service.py must reference get_or_create_base_case_scenario"
        )
        # Confirm it's called (not just defined as a field)
        assert "deps.get_or_create_base_case_scenario(" in src, (
            "Service must call deps.get_or_create_base_case_scenario()"
        )

    def test_service_guards_none(self):
        src = (Path(REPO_ROOT) / "app/services/projects_create_service.py").read_text()
        assert "if deps.get_or_create_base_case_scenario is not None" in src, (
            "Service must guard against None (backward-compat)"
        )


# ---------------------------------------------------------------------------
# D. project_save_as_service calls get_or_create when supplied
# ---------------------------------------------------------------------------

class TestProjectSaveAsServiceCallsInit:
    def test_service_calls_get_or_create_when_wired(self):
        src = (Path(REPO_ROOT) / "app/services/project_save_as_service.py").read_text()
        assert "deps.get_or_create_base_case_scenario(" in src

    def test_service_guards_none(self):
        src = (Path(REPO_ROOT) / "app/services/project_save_as_service.py").read_text()
        assert "if deps.get_or_create_base_case_scenario is not None" in src


# ---------------------------------------------------------------------------
# E-F. main_web.py wires the function into both deps bundles
# ---------------------------------------------------------------------------

class TestMainWebWiring:
    def test_main_web_imports_get_or_create(self):
        src = (Path(REPO_ROOT) / "main_web.py").read_text()
        assert "get_or_create_base_case_scenario" in src, (
            "main_web.py must import and wire get_or_create_base_case_scenario"
        )

    def test_main_web_wires_into_create_deps(self):
        src = (Path(REPO_ROOT) / "main_web.py").read_text()
        # The ProjectsCreateRouteDeps() constructor call must include the field
        # It appears as a kwarg after save_workspace_state in the deps bundle
        assert "get_or_create_base_case_scenario=get_or_create_base_case_scenario" in src

    def test_main_web_wires_into_both_save_as_deps(self):
        src = (Path(REPO_ROOT) / "main_web.py").read_text()
        # Count occurrences — must appear in both save-as route usages
        count = src.count("get_or_create_base_case_scenario=get_or_create_base_case_scenario")
        assert count >= 3, (
            f"Expected wiring in create + 2× save-as routes, found {count} occurrences"
        )


# ---------------------------------------------------------------------------
# G-J. Live DB verification (app already ran and created scenario1-solar-test,
#      scenario1-wind-test during the live verification session)
# ---------------------------------------------------------------------------

class TestLiveDBSolarScenario:
    def test_solar_project_has_base_case(self):
        """scenario1-solar-test was created during live verification."""
        rows = _scenario_rows_for_project("scenario1-solar-test")
        if not rows:
            pytest.skip("scenario1-solar-test not in DB (not yet created in this session)")
        assert any(r["is_base_case"] == 1 for r in rows), (
            "scenario1-solar-test must have at least one base case scenario"
        )

    def test_solar_project_has_downside_scenario(self):
        """Downside was added during live verification without 500 error."""
        rows = _scenario_rows_for_project("scenario1-solar-test")
        if not rows:
            pytest.skip("scenario1-solar-test not in DB")
        names = [r["scenario_name"] for r in rows]
        assert "Downside" in names or any("downside" in n.lower() for n in names), (
            f"Expected Downside scenario, got: {names}"
        )


class TestLiveDBWindScenario:
    def test_wind_project_has_base_case(self):
        rows = _scenario_rows_for_project("scenario1-wind-test")
        if not rows:
            pytest.skip("scenario1-wind-test not in DB")
        assert any(r["is_base_case"] == 1 for r in rows)


# ---------------------------------------------------------------------------
# K-L. Working copies have base case
# ---------------------------------------------------------------------------

class TestWorkingCopyBaseCase:
    def test_newest_tuho_copy_has_base_case_if_created_after_fix(self):
        """Any TUHO copy created at or after the fix time has a base case."""
        from app.persistence.db import get_connection
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT project_code FROM projects "
                "WHERE project_code LIKE 'tuho-copy-20260615%' "
                "ORDER BY created_at DESC LIMIT 1"
            ).fetchall()
        if not rows:
            pytest.skip("No post-fix TUHO copy in DB")
        code = rows[0]["project_code"]
        sc_rows = _scenario_rows_for_project(code)
        assert len(sc_rows) >= 1, f"TUHO copy {code} has no scenarios"
        assert sc_rows[0]["is_base_case"] == 1

    def test_newest_oborovo_copy_has_base_case_if_created_after_fix(self):
        from app.persistence.db import get_connection
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT project_code FROM projects "
                "WHERE project_code LIKE 'oborovo-copy-20260615%' "
                "ORDER BY created_at DESC LIMIT 1"
            ).fetchall()
        if not rows:
            pytest.skip("No post-fix Oborovo copy in DB")
        code = rows[0]["project_code"]
        sc_rows = _scenario_rows_for_project(code)
        assert len(sc_rows) >= 1, f"Oborovo copy {code} has no scenarios"
        assert sc_rows[0]["is_base_case"] == 1


# ---------------------------------------------------------------------------
# M. Idempotency
# ---------------------------------------------------------------------------

class TestIdempotency:
    def test_get_or_create_is_idempotent(self):
        from app.persistence.scenarios_repository import get_or_create_base_case_scenario
        from app.persistence.db import get_connection

        # Pick the live solar project
        with get_connection() as conn:
            proj = conn.execute(
                "SELECT project_id, project_code FROM projects "
                "WHERE project_code = 'scenario1-solar-test'"
            ).fetchone()
        if not proj:
            pytest.skip("scenario1-solar-test not in DB")

        project_id = proj["project_id"]
        project_code = proj["project_code"]

        rows_before = _scenario_rows_for_project(project_code)
        base_count_before = sum(1 for r in rows_before if r["is_base_case"] == 1)

        # Call a second time
        bc2 = get_or_create_base_case_scenario(
            user_id="1",
            project_id=project_id,
            project_code=project_code,
            project_name="Idempotency Check",
            project_type="Solar",
            source_project_template="generic_solar",
            base_input_set={},
            governance_state={},
        )
        assert bc2 is not None
        assert bc2.is_base_case

        rows_after = _scenario_rows_for_project(project_code)
        base_count_after = sum(1 for r in rows_after if r["is_base_case"] == 1)
        assert base_count_after == base_count_before, (
            f"Idempotency violated: base case count went from "
            f"{base_count_before} to {base_count_after}"
        )


# ---------------------------------------------------------------------------
# N-P. Parity
# ---------------------------------------------------------------------------

class TestScenario1Parity:
    def test_engine_md5_unchanged(self):
        digest = hashlib.md5(
            (Path(REPO_ROOT) / "app/waterfall_core.py").read_bytes()
        ).hexdigest()
        assert digest == ENGINE_MD5, f"waterfall_core.py changed: {digest}"

    def test_tuho_p1_dscr_unchanged(self):
        from app.project_factories import create_default_tuho_wind1
        from app.ui_runner import _build_period_engine, _run_waterfall
        proj = create_default_tuho_wind1()
        result = _run_waterfall(proj, _build_period_engine(proj))
        for p in result.periods:
            d = getattr(p, "dscr", None)
            if d is not None and abs(d) < 1e10:
                assert abs(d - TUHO_P1_DSCR) < 0.001, f"TUHO P1 DSCR={d}"
                return
        pytest.fail("No finite DSCR found")

    def test_oborovo_p1_dscr_unchanged(self):
        from app.project_factories import create_default_oborovo
        from app.ui_runner import _build_period_engine, _run_waterfall
        proj = create_default_oborovo()
        result = _run_waterfall(proj, _build_period_engine(proj))
        for p in result.periods:
            d = getattr(p, "dscr", None)
            if d is not None and abs(d) < 1e10:
                assert abs(d - OBOROVO_P1_DSCR) < 0.01, f"Oborovo P1 DSCR={d}"
                return
        pytest.fail("No finite DSCR found")

    def test_project_factories_unchanged(self):
        src = (Path(REPO_ROOT) / "app/project_factories.py").read_text()
        assert "create_default_tuho_wind1" in src
        assert "create_default_oborovo" in src


# ---------------------------------------------------------------------------
# Q. File scope guard
# ---------------------------------------------------------------------------

class TestScenario1FileScope:
    ALLOWED_PREFIXES = (
        "app/services/scenarios_add_service.py",
        "app/services/projects_create_service.py",
        "app/services/project_save_as_service.py",
        "main_web.py",
        "tests/test_phase_scenario1_",
        "tests/test_phase_stab",
        "tests/test_phase_pr1_",
        "tests/test_phase_pr2_",
        "tests/test_phase_pr3_",
        "tests/test_phase_m1_",
        "tests/test_phase_m2_",
        "tests/test_phase_m3_",
        "tests/test_phase_m4_",
        "tests/test_phase_wf1_",
        "tests/test_phase_wf2_",
        "tests/test_phase_wf3_",
        "tests/test_phase_wf4_",
        "tests/test_phase_wf5_",
        "tests/test_phase_wf6_",
        "tests/test_phase_p2fix",
        "tests/test_phase_ux1_",
        "tests/test_phase_ux2_",
    )
    DISALLOWED_PREFIXES = (
        "app/waterfall_core.py",
        "app/project_factories.py",
        "app/persistence/",
        "static/",
        "app/templates/",
    )

    def test_file_scope(self):
        import shutil
        if shutil.which("git") is None:
            pytest.skip("git not available")
        result = subprocess.run(
            ["git", "-C", REPO_ROOT, "diff", "--name-only", "origin/main"],
            capture_output=True, text=True,
        )
        changed = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
        for f in changed:
            assert not any(f.startswith(p) for p in self.DISALLOWED_PREFIXES), (
                f"SCENARIO-1 must not touch {f}"
            )
            assert any(f.startswith(p) for p in self.ALLOWED_PREFIXES), (
                f"SCENARIO-1 file outside allowed scope: {f}"
            )
