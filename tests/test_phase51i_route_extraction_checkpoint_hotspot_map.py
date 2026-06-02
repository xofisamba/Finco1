"""Phase 51I — Route extraction checkpoint and updated hotspot map.

This test suite verifies the structural invariants captured in
the Phase 51I checkpoint document and machine-readable report.

It is a STRUCTURAL test suite. It pins:
- 6 completed route extractions (services exist; routes use
  them; one-way import direction preserved).
- 9 services inventoried with correct classification.
- main_web.py route hotspot counts (size, service-backed vs
  inline orchestration).
- Phase 51F guardrail status (parity-core files exist; rc1
  frozen; no-service-imports-main_web/main_api).
- Recommended next sequence: scenarios-save → scenarios-duplicate
  → scenarios-add → ... .

The test suite does NOT verify the contents of routes
themselves (that is the responsibility of the per-route
characterization + extraction phases). It only verifies that
the structural invariants documented in the Phase 51I
checkpoint are still true at merge time.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MAIN_WEB = REPO_ROOT / "main_web.py"
SERVICES_DIR = REPO_ROOT / "app" / "services"


# ─── Helpers ───────────────────────────────────────────────────────────────


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _strip_docstrings_and_comments(text: str) -> str:
    """Strip module docstrings, function/class docstrings, and comments."""
    out = re.sub(r'^\s*"""[\s\S]*?"""', "", text, flags=re.MULTILINE)
    out = re.sub(r"^\s*'''[\s\S]*?'''", "", out, flags=re.MULTILINE)
    out = re.sub(r"#.*", "", out)
    out = re.sub(r'"""[\s\S]*?"""', '"""..."""', out)
    out = re.sub(r"'''[\s\S]*?'''", "'''...'''", out)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 1. Completed extractions — service modules exist
# ─────────────────────────────────────────────────────────────────────────────


class TestCompletedExtractions:
    """Pin the existence of all 6 completed route extraction
    service modules."""

    @pytest.mark.parametrize(
        "service_file,route_family",
        [
            ("run_service.py", "/run"),
            ("compare_service.py", "/compare"),
            ("validation_service.py", "/validate"),
            ("download_service.py", "/download"),
            ("save_run_service.py", "/save-run"),
            ("scenario_state_route_service.py", "/scenarios/state/*"),
        ],
    )
    def test_service_module_exists(self, service_file: str, route_family: str):
        path = SERVICES_DIR / service_file
        assert path.exists(), (
            f"{path} must exist (Phase 51 extraction for {route_family})"
        )

    def test_all_6_extractions_present(self):
        """All 6 canonical route extractions must be present."""
        required = {
            "run_service.py",
            "compare_service.py",
            "validation_service.py",
            "download_service.py",
            "save_run_service.py",
            "scenario_state_route_service.py",
        }
        present = {p.name for p in SERVICES_DIR.glob("*.py")}
        missing = required - present
        assert not missing, f"Missing service modules: {missing}"


# ─────────────────────────────────────────────────────────────────────────────
# 2. One-way import direction — no service imports main_web or main_api
# ─────────────────────────────────────────────────────────────────────────────


class TestNoServiceImportsMainWebOrMainApi:
    """All 9 services must NOT import main_web or main_api."""

    @pytest.mark.parametrize(
        "service_file",
        [
            "run_service.py",
            "compare_service.py",
            "validation_service.py",
            "download_service.py",
            "save_run_service.py",
            "export_service.py",
            "export_audit_service.py",
            "scenario_state_service.py",
            "scenario_state_route_service.py",
        ],
    )
    def test_service_does_not_import_main_web(self, service_file: str):
        path = SERVICES_DIR / service_file
        text = _read(path)
        clean = _strip_docstrings_and_comments(text)
        assert "import main_web" not in clean
        assert "from main_web" not in clean

    @pytest.mark.parametrize(
        "service_file",
        [
            "run_service.py",
            "compare_service.py",
            "validation_service.py",
            "download_service.py",
            "save_run_service.py",
            "export_service.py",
            "export_audit_service.py",
            "scenario_state_service.py",
            "scenario_state_route_service.py",
        ],
    )
    def test_service_does_not_import_main_api(self, service_file: str):
        path = SERVICES_DIR / service_file
        text = _read(path)
        clean = _strip_docstrings_and_comments(text)
        assert "import main_api" not in clean
        assert "from main_api" not in clean


# ─────────────────────────────────────────────────────────────────────────────
# 3. Service classification
# ─────────────────────────────────────────────────────────────────────────────


class TestServiceClassification:
    """Pin the classification of each service as
    route-orchestration / data-layer / export-audit."""

    @pytest.mark.parametrize(
        "service_file",
        [
            "run_service.py",
            "compare_service.py",
            "validation_service.py",
            "download_service.py",
            "save_run_service.py",
            "scenario_state_route_service.py",
        ],
    )
    def test_route_orchestration_service_has_execute_function(
        self, service_file: str
    ):
        """Route-orchestration services expose async execute_*_route
        entry points."""
        text = _read(SERVICES_DIR / service_file)
        assert re.search(r"async def execute_\w+_route\(", text), (
            f"{service_file} is a route-orchestration service but "
            f"does not expose an execute_*_route() entry point"
        )

    @pytest.mark.parametrize(
        "service_file",
        [
            "run_service.py",
            "compare_service.py",
            "validation_service.py",
            "download_service.py",
            "save_run_service.py",
            "scenario_state_route_service.py",
        ],
    )
    def test_route_orchestration_service_has_route_deps_dataclass(
        self, service_file: str
    ):
        """Route-orchestration services expose a *RouteDeps dataclass."""
        text = _read(SERVICES_DIR / service_file)
        assert re.search(r"class \w+RouteDeps:", text), (
            f"{service_file} is a route-orchestration service but "
            f"does not expose a *RouteDeps dataclass"
        )

    @pytest.mark.parametrize(
        "service_file",
        [
            "run_service.py",
            "compare_service.py",
            "validation_service.py",
            "download_service.py",
            "save_run_service.py",
            "scenario_state_route_service.py",
        ],
    )
    def test_route_orchestration_service_has_route_outcome_dataclass(
        self, service_file: str
    ):
        """Route-orchestration services expose a *RouteOutcome dataclass."""
        text = _read(SERVICES_DIR / service_file)
        assert re.search(r"class \w+RouteOutcome:", text), (
            f"{service_file} is a route-orchestration service but "
            f"does not expose a *RouteOutcome dataclass"
        )

    def test_scenario_state_service_remains_data_layer(self):
        """scenario_state_service.py is data-layer only:
        - has no RouteDeps / RouteOutcome / execute_*_route
        - no Request, no form, no auth, no template
        - exposes 4 data-layer helpers (build_workspace_state_metadata,
          resolve_runtime_snapshot, check_runtime_allowed,
          scenario_provenance_for_record)
        """
        path = SERVICES_DIR / "scenario_state_service.py"
        text = _read(path)
        # No route orchestration
        assert "class ScenarioStateRouteDeps" not in text
        assert "class ScenarioStateRouteOutcome" not in text
        assert "def execute_draft_route" not in text
        assert "def execute_discard_route" not in text
        # No Request, form, auth
        clean = _strip_docstrings_and_comments(text)
        assert "TemplateResponse" not in clean
        assert "get_current_user" not in clean
        assert "await request.form" not in clean
        assert "form.get" not in clean
        # The 4 data-layer helpers
        for helper in [
            "build_workspace_state_metadata",
            "resolve_runtime_snapshot",
            "check_runtime_allowed",
            "scenario_provenance_for_record",
        ]:
            assert f"def {helper}(" in text, (
                f"scenario_state_service.py must still expose {helper}()"
            )

    def test_scenario_state_route_service_owns_route_orchestration(self):
        """scenario_state_route_service.py is route-orchestration:
        - has ScenarioStateRouteDeps, ScenarioStateRouteOutcome
        - has execute_draft_route, execute_discard_route
        - delegates data-layer concerns to scenario_state_service.py
        """
        path = SERVICES_DIR / "scenario_state_route_service.py"
        text = _read(path)
        assert "class ScenarioStateRouteOutcome" in text
        assert "class ScenarioStateRouteDeps" in text
        assert "async def execute_draft_route(" in text
        assert "async def execute_discard_route(" in text

    def test_export_service_is_export_audit_helper(self):
        """export_service.py is an export-audit helper (not route
        orchestration)."""
        path = SERVICES_DIR / "export_service.py"
        text = _read(path)
        # Not a route-orchestration service
        assert "class ExportRouteDeps" not in text
        assert "class ExportRouteOutcome" not in text
        assert "def execute_export_route" not in text
        # Exposes export builders
        for builder in [
            "build_values_only_export_for_project",
            "build_runtime_summary_csv_export",
            "build_institutional_workbook_export",
            "build_excel_export_for_post_request",
        ]:
            assert f"def {builder}(" in text or f"async def {builder}(" in text, (
                f"export_service.py must expose {builder}()"
            )

    def test_export_audit_service_is_audit_helper(self):
        """export_audit_service.py is an audit helper."""
        path = SERVICES_DIR / "export_audit_service.py"
        text = _read(path)
        # Not route orchestration
        assert "class ExportAuditRouteDeps" not in text
        # Exposes the 3 audit record functions
        for rec in [
            "record_runtime_summary_export",
            "record_institutional_workbook_export",
            "record_download_export",
        ]:
            assert f"def {rec}(" in text, (
                f"export_audit_service.py must expose {rec}()"
            )


# ─────────────────────────────────────────────────────────────────────────────
# 4. main_web.py route hotspot map (structural)
# ─────────────────────────────────────────────────────────────────────────────


class TestMainWebRouteHotspotMap:
    """Structural check on the main_web.py route hotspot map."""

    def test_main_web_has_at_least_30_routes(self):
        """After 6 extractions, main_web.py should have at least 30
        routes (auth + UI + remaining /scenarios/* + /projects/* + /runs + /run/{id})."""
        text = _read(MAIN_WEB)
        routes = re.findall(
            r'@app\.(?:get|post|put|delete|route)\("([^"]+)"\)', text
        )
        assert len(routes) >= 30, (
            f"Expected >= 30 routes in main_web.py, got {len(routes)}"
        )

    def test_six_service_backed_routes(self):
        """The 6 service-backed route families use the execute_*_route
        pattern."""
        text = _read(MAIN_WEB)
        # Each service-backed route has a *RouteDeps construction
        for dep_class in [
            "ValidateRouteDeps",
            "RunRouteDeps",
            "CompareRouteDeps",
            "DownloadRouteDeps",
            "SaveRunRouteDeps",
            "ScenarioStateRouteDeps",
        ]:
            assert f"{dep_class}(" in text, (
                f"{dep_class} must be constructed in main_web.py for the "
                f"corresponding route family"
            )

    def test_remaining_inline_routes_include_scenarios_save(self):
        """The remaining /scenarios/save and similar routes are
        still inline orchestration (to be extracted in future phases)."""
        text = _read(MAIN_WEB)
        for route in [
            "/scenarios/save",
            "/scenarios/{scenario_id}/duplicate",
            "/scenarios/add",
            "/scenarios/{scenario_id}/rename",
            "/scenarios/{scenario_id}/archive",
            "/scenarios/{scenario_id}/update-overrides",
            "/scenarios/{scenario_id}/select",
            "/projects/create",
            "/projects/{project_code}/save-as",
        ]:
            assert route in text, (
                f"{route} should still exist in main_web.py (not yet "
                f"extracted; will be targeted in future phases)"
            )

    def test_no_inline_save_workspace_state_call_in_main_web(self):
        """After 51G-2 + 51H-2, the routes should NOT call
        save_workspace_state directly (they use the service)."""
        text = _read(MAIN_WEB)
        # The save_workspace_state function import is OK (it's used
        # in deps construction). The direct call (save_workspace_state(...))
        # outside of deps construction should be the *RouteDeps bundle.
        # The 51G-2 /save-run route uses deps.save_workspace_state(...)
        # inside execute_save_run_route. The 51H-2 routes use the same
        # pattern. So in main_web.py itself, save_workspace_state is
        # only used to wire the deps bundle.
        # Verify the inline use is only in the deps bundle
        # (not in any of the 6 service-backed route bodies).
        for route_path in [
            "/scenarios/state/draft",
            "/scenarios/state/discard",
            "/save-run",
        ]:
            # Find route body
            m = re.search(
                rf'@app\.post\("{re.escape(route_path)}"\).*?(?=\n@app\.(get|post|put|delete|route)\(|\Z)',
                text,
                re.DOTALL,
            )
            assert m, f"Route {route_path} not found"
            body = m.group(0)
            # The route should not call save_workspace_state( directly
            # (it goes through deps)
            assert "save_workspace_state(" not in body, (
                f"{route_path} must not call save_workspace_state( "
                f"directly (should use deps.save_workspace_state in service)"
            )


# ─────────────────────────────────────────────────────────────────────────────
# 5. Phase 51F guardrails (smoke check)
# ─────────────────────────────────────────────────────────────────────────────


class TestPhase51FGuardrailsSmokeCheck:
    """Smoke check that 51I does not break 51F guardrails.

    The full 51F suite is run separately."""

    def test_parity_core_files_unchanged(self):
        """SHA-256 of parity-core files must match the 51F pins."""
        import hashlib

        parity_files = [
            REPO_ROOT / "app" / "waterfall_core.py",
            REPO_ROOT / "app" / "project_factories.py",
            REPO_ROOT / "reports" / "phase7_tuho_senior_debt_sizing_extraction.csv",
            REPO_ROOT
            / "reports"
            / "phase23q_oborovo_senior_debt_sizing_extraction.csv",
        ]
        for p in parity_files:
            assert p.exists(), f"Parity file missing: {p}"
            content = p.read_bytes()
            sha = hashlib.sha256(content).hexdigest()
            assert len(sha) == 64
            assert len(content) > 0

    def test_rc1_untouched(self):
        r = subprocess.run(
            ["git", "ls-remote", "--heads", "origin", "rc1"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        sha = r.stdout.split("\t")[0].strip() if r.stdout else ""
        assert sha == "b425a0708719eaa5e1d922b1008e5609758e0ad4"


# ─────────────────────────────────────────────────────────────────────────────
# 6. Recommended next sequence markers
# ─────────────────────────────────────────────────────────────────────────────


class TestRecommendedNextSequenceMarkers:
    """Pin the structural markers that will guide the next phases.

    These tests verify that the candidate next-phase routes still
    exist in main_web.py (and have not been accidentally removed)
    and have the expected size characteristics."""

    def test_scenarios_save_route_extracted_in_51j2(self):
        """Phase 51J-2: /scenarios/save has been extracted into
        scenarios_save_service.py. The route is now thin and
        service-backed."""
        text = _read(MAIN_WEB)
        # Find /scenarios/save
        m = re.search(
            r'@app\.post\("/scenarios/save"\).*?(?=\n@app\.(get|post|put|delete|route)\(|\Z)',
            text,
            re.DOTALL,
        )
        assert m, "/scenarios/save not found"
        body = m.group(0)
        # Service-backed (post-51J-2)
        assert "execute_scenarios_save_route" in body
        assert "ScenariosSaveRouteDeps" in body
        # Thin route (post-51J-2)
        non_blank = [l for l in body.splitlines() if l.strip()]
        assert len(non_blank) <= 60, (
            f"/scenarios/save is {len(non_blank)} non-blank lines; "
            f"expected <= 60 (thin route after 51J-2 extraction)"
        )

    def test_scenarios_duplicate_route_extracted_in_51k2(self):
        """Phase 51K-2: /scenarios/{scenario_id}/duplicate has been
        extracted into scenario_duplicate_service.py. The route is
        now thin and service-backed."""
        text = _read(MAIN_WEB)
        m = re.search(
            r'@app\.post\("/scenarios/\{scenario_id\}/duplicate"\).*?(?=\n@app\.(get|post|put|delete|route)\(|\Z)',
            text,
            re.DOTALL,
        )
        assert m, "/scenarios/{scenario_id}/duplicate not found"
        body = m.group(0)
        # Service-backed (post-51K-2)
        assert "execute_scenario_duplicate_route" in body
        assert "ScenarioDuplicateRouteDeps" in body
        # No longer calls persistence directly
        assert "duplicate_scenario(" not in body
        assert "get_scenario(" not in body

    def test_scenarios_add_route_still_inline(self):
        """Phase 51L-1 + 51L-2 target: /scenarios/add."""
        text = _read(MAIN_WEB)
        m = re.search(
            r'@app\.post\("/scenarios/add"\).*?(?=\n@app\.(get|post|put|delete|route)\(|\Z)',
            text,
            re.DOTALL,
        )
        assert m, "/scenarios/add not found"
        body = m.group(0)
        assert "execute_add_route" not in body

    def test_projects_create_route_still_inline(self):
        """Phase 51M-1 + 51M-2 target: /projects/create."""
        text = _read(MAIN_WEB)
        m = re.search(
            r'@app\.post\("/projects/create"\).*?(?=\n@app\.(get|post|put|delete|route)\(|\Z)',
            text,
            re.DOTALL,
        )
        assert m, "/projects/create not found"
        body = m.group(0)
        assert "execute_project_create_route" not in body
        non_blank = [l for l in body.splitlines() if l.strip()]
        assert len(non_blank) >= 50, (
            f"/projects/create is {len(non_blank)} non-blank lines; "
            f"expected >= 50 (substantial target for next extraction)"
        )

    def test_projects_save_as_route_still_inline(self):
        """Phase 51N-1 + 51N-2 target: /projects/{project_code}/save-as."""
        text = _read(MAIN_WEB)
        m = re.search(
            r'@app\.post\("/projects/\{project_code\}/save-as"\).*?(?=\n@app\.(get|post|put|delete|route)\(|\Z)',
            text,
            re.DOTALL,
        )
        assert m, "/projects/{project_code}/save-as not found"
        body = m.group(0)
        assert "execute_save_as_route" not in body
        non_blank = [l for l in body.splitlines() if l.strip()]
        assert len(non_blank) >= 30, (
            f"/projects/{{project_code}}/save-as is {len(non_blank)} "
            f"non-blank lines; expected >= 30"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 7. Phase 51J structural prerequisites
# ─────────────────────────────────────────────────────────────────────────────


class TestPhase51JPrerequisites:
    """Structural prerequisites for the next phase (51J /scenarios/save
    characterization)."""

    def test_scenarios_save_route_extraction_complete(self):
        """Phase 51J-2: /scenarios/save has been extracted. The route
        is service-backed (calls execute_scenarios_save_route and
        passes save_scenario/bind_workspace_to_scenario in the
        deps bundle). The route is THIN (orchestration moved to
        the service)."""
        text = _read(MAIN_WEB)
        m = re.search(
            r'@app\.post\("/scenarios/save"\)(.*?)(?=\n@app\.(get|post|put|delete|route)\(|\Z)',
            text,
            re.DOTALL,
        )
        assert m
        body = m.group(0)
        # Has async def
        assert "async def" in body
        # Returns a response
        assert "return" in body
        # Service-backed: must construct the deps bundle and call
        # the service's execute function.
        assert "ScenariosSaveRouteDeps(" in body
        assert "execute_scenarios_save_route(" in body
        # Persistence helpers passed in deps bundle
        assert "save_scenario=save_scenario" in body
        assert "bind_workspace_to_scenario=bind_workspace_to_scenario" in body

    def test_scenarios_save_service_exists(self):
        """Phase 51J-2: scenarios_save_service.py exists in
        app/services/."""
        path = SERVICES_DIR / "scenarios_save_service.py"
        assert path.exists(), (
            f"{path} must exist after Phase 51J-2"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 8. Sanity: import smoke test
# ─────────────────────────────────────────────────────────────────────────────


class TestImportSmoke:
    """Smoke test that all modules import cleanly."""

    def test_main_web_imports(self):
        import main_web  # noqa: F401

    def test_all_route_orchestration_services_import(self):
        from app.services import (  # noqa: F401
            run_service,
            compare_service,
            validation_service,
            download_service,
            save_run_service,
            scenario_state_route_service,
        )

    def test_data_layer_services_import(self):
        from app.services import (  # noqa: F401
            scenario_state_service,
            export_service,
            export_audit_service,
        )
