"""Phase 51D-2 — POST /validate route vertical extraction tests.

Pins the structural and behavioral contract of the /validate route
after vertical extraction of its orchestration body into
``app/services/validation_service.py``.

This phase is a behavior-preserving production refactor with NO
production behavior changes. The runtime-snapshot parity call
documented in Phase 51D-1 is preserved EXACTLY.

Hard guardrails:

  * No financial formula / runtime calculation / model output changes.
  * No fixture CSV changes.
  * No JS financial calculations.
  * /run route from Phase 51B remains thin.
  * /compare route from Phase 51C-2 remains thin.
  * run_service.py from Phase 51B remains intact.
  * compare_service.py from Phase 51C-2 remains intact.
  * main_web.py has zero direct record_export calls.
  * /validate route remains read-only (no record_*, no DB writes).
  * Stage A -> B -> C order preserved.
  * Stage C only runs if Stage A and B have no errors.
  * Stage C catches ValueError specifically (not bare Exception).
  * All 9 numeric max values preserved.
  * Runtime-snapshot parity call preserved.
"""
from __future__ import annotations

import importlib
import inspect
import re
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
MAIN_WEB_PATH = REPO_ROOT / "main_web.py"
VALIDATE_SERVICE_PATH = REPO_ROOT / "app" / "services" / "validation_service.py"
RUN_SERVICE_PATH = REPO_ROOT / "app" / "services" / "run_service.py"
COMPARE_SERVICE_PATH = REPO_ROOT / "app" / "services" / "compare_service.py"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


def _read_lines(rel: str) -> list[str]:
    return _read(rel).splitlines()


def _get_validate_route_body() -> str:
    """Extract the body of the @app.post('/validate') handler."""
    text = MAIN_WEB_PATH.read_text(encoding="utf-8")
    m = re.search(
        r"@app\.post\(\s*['\"]/validate['\"]\s*\)([\s\S]*?)(?=^@app\.)",
        text,
        re.MULTILINE,
    )
    assert m, "could not locate /validate route body"
    return m.group(1)


def _get_run_route_body() -> str:
    text = MAIN_WEB_PATH.read_text(encoding="utf-8")
    m = re.search(
        r"@app\.post\(\s*['\"]/run['\"]\s*\)([\s\S]*?)(?=^@app\.)",
        text,
        re.MULTILINE,
    )
    assert m, "could not locate /run route body"
    return m.group(1)


def _get_compare_route_body() -> str:
    text = MAIN_WEB_PATH.read_text(encoding="utf-8")
    m = re.search(
        r"@app\.post\(\s*['\"]/compare['\"]\s*\)([\s\S]*?)(?=^@app\.)",
        text,
        re.MULTILINE,
    )
    assert m, "could not locate /compare route body"
    return m.group(1)


def _non_blank_lines(text: str) -> list[str]:
    return [ln for ln in text.splitlines() if ln.strip()]


# ─────────────────────────────────────────────────────────────────────────────
# 1. validation_service module exists and is well-formed
# ─────────────────────────────────────────────────────────────────────────────

def test_validate_service_module_exists():
    assert VALIDATE_SERVICE_PATH.exists(), (
        "app/services/validation_service.py must exist (Phase 51D-2)"
    )


def test_validate_service_module_imports_cleanly():
    mod = importlib.import_module("app.services.validation_service")
    assert mod is not None


def test_validate_service_does_not_import_main_web():
    """Hard guardrail: import direction must be main_web -> validation_service."""
    src = _read("app/services/validation_service.py")
    assert "import main_web" not in src
    assert "from main_web" not in src


def test_validate_service_does_not_import_main_api():
    """validation_service is a web-layer service; it must not import
    main_api (that is the API entry point)."""
    src = _read("app/services/validation_service.py")
    assert "import main_api" not in src
    assert "from main_api" not in src


# ─────────────────────────────────────────────────────────────────────────────
# 2. ValidateRouteOutcome and ValidateRouteDeps dataclasses
# ─────────────────────────────────────────────────────────────────────────────

def test_validate_service_exposes_validate_route_outcome_dataclass():
    from app.services.validation_service import ValidateRouteOutcome
    assert hasattr(ValidateRouteOutcome, "__dataclass_fields__")
    fields = set(ValidateRouteOutcome.__dataclass_fields__.keys())
    assert {"template_name", "context", "status_code", "headers"}.issubset(fields), (
        f"ValidateRouteOutcome must have fields template_name, context, "
        f"status_code, headers; got {fields}"
    )


def test_validate_service_exposes_validate_route_deps_dataclass():
    from app.services.validation_service import ValidateRouteDeps
    assert hasattr(ValidateRouteDeps, "__dataclass_fields__")
    fields = set(ValidateRouteDeps.__dataclass_fields__.keys())
    expected = {
        "collect_form_snapshot",
        "project_workspace_from_snapshot",
        "canonical_project_type",
        "normalize_template_source",
        "check_runtime_allowed",
        "resolve_runtime_snapshot_source",
        "build_schema_from_form",
        "validate_numeric_field",
        "project_types",
        "scenarios",
        "snapshot_input_error",
    }
    assert expected.issubset(fields), (
        f"ValidateRouteDeps missing required fields: {expected - fields}"
    )


def test_validate_service_exposes_execute_validate_route():
    from app.services import validation_service
    assert hasattr(validation_service, "execute_validate_route"), (
        "execute_validate_route is the public service entry point"
    )
    assert inspect.iscoroutinefunction(validation_service.execute_validate_route), (
        "execute_validate_route must be async"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. /validate route in main_web.py is materially thinner
# ─────────────────────────────────────────────────────────────────────────────

def test_validate_route_still_exists_in_main_web():
    src = _read("main_web.py")
    assert re.search(r"^@app\.post\(\s*[\"']/validate[\"']\s*\)", src, re.MULTILINE), (
        "POST /validate route must still exist in main_web.py"
    )


def test_validate_route_delegates_to_validate_service():
    body = _get_validate_route_body()
    assert "execute_validate_route" in body, (
        "/validate route must call execute_validate_route (Phase 51D-2)"
    )
    assert "ValidateRouteDeps" in body, (
        "/validate route must build a ValidateRouteDeps instance"
    )


def test_validate_route_body_is_materially_thinner():
    """Robust threshold: < 50 non-blank body lines after extraction.

    Pre-Phase-51D-2 body was ~77 lines. We require the post-extraction
    body to be less than 50 lines to demonstrate vertical extraction.
    """
    body = _get_validate_route_body()
    non_blank = _non_blank_lines(body)
    assert len(non_blank) < 50, (
        f"/validate route body has {len(non_blank)} non-blank lines; "
        "expected < 50 after Phase 51D-2 vertical extraction"
    )


def test_validate_route_does_not_call_build_schema_from_form_directly():
    body = _get_validate_route_body()
    assert "build_schema_from_form(" not in body, (
        "POST /validate route must not call build_schema_from_form directly anymore"
    )


def test_validate_route_does_not_call_validate_numeric_field_directly():
    body = _get_validate_route_body()
    assert "validate_numeric_field(" not in body, (
        "POST /validate route must not call validate_numeric_field directly anymore"
    )


def test_validate_route_renders_template_from_outcome():
    """The /validate route must render the template based on the
    ValidateRouteOutcome returned by execute_validate_route."""
    body = _get_validate_route_body()
    # The route uses outcome.template_name to drive the template.
    assert "outcome.template_name" in body, (
        "/validate route must use outcome.template_name to render the template"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 4. Behavior preservation
# ─────────────────────────────────────────────────────────────────────────────

def test_validate_service_returns_errors_html_on_runtime_guard_block():
    """When check_runtime_allowed returns (False, _, guard_message),
    the service must return ValidateRouteOutcome with
    template_name='partials/errors.html'."""
    text = _read("app/services/validation_service.py")
    assert 'template_name="partials/errors.html"' in text, (
        "validation_service must return partials/errors.html on runtime "
        "guard block"
    )
    assert "guard_message" in text, (
        "validation_service must use guard_message in the error context"
    )


def test_validate_service_emits_validation_html_on_success():
    """On a successful validation (no errors), the service must return
    template_name='partials/validation.html' with valid, errors, and
    form_data in context."""
    text = _read("app/services/validation_service.py")
    assert 'partials/validation.html' in text, (
        "validation_service must render partials/validation.html on success"
    )
    assert '"valid"' in text or "'valid'" in text, (
        "validation_service must include valid in context"
    )
    assert '"errors"' in text or "'errors'" in text, (
        "validation_service must include errors in context"
    )
    assert '"form_data"' in text or "'form_data'" in text, (
        "validation_service must include form_data in context"
    )


def test_validate_service_form_data_subset():
    """The form_data context must contain exactly project_type and
    scenario (no other fields)."""
    text = _read("app/services/validation_service.py")
    # Find the form_data dict construction
    m = re.search(r'form_data["\']\s*:\s*\{([^}]+)\}', text)
    assert m, "could not locate form_data dict construction"
    form_data_body = m.group(1)
    assert '"project_type"' in form_data_body or "'project_type'" in form_data_body, (
        "form_data must include project_type"
    )
    assert '"scenario"' in form_data_body or "'scenario'" in form_data_body, (
        "form_data must include scenario"
    )
    # The numeric fields must NOT be in form_data (preserved behavior)
    for forbidden_field in (
        "capacity_mw", "tariff_eur_mwh", "p50_hours",
        "total_capex_keur", "opex_y1_keur", "gearing_pct",
        "target_dscr", "interest_rate_pct", "tenor_years",
    ):
        assert forbidden_field not in form_data_body, (
            f"form_data must not include {forbidden_field} (only project_type and scenario)"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 5. Stage order preservation
# ─────────────────────────────────────────────────────────────────────────────

def test_validate_service_stage_a_enum_validation():
    """Stage A: enum validation of project_type and scenario."""
    text = _read("app/services/validation_service.py")
    assert "project_type not in" in text, (
        "validation_service Stage A must check project_type enum"
    )
    assert "scenario not in" in text, (
        "validation_service Stage A must check scenario enum"
    )
    assert "must be one of" in text, (
        "validation_service Stage A must emit 'must be one of' error message"
    )


def test_validate_service_stage_b_numeric_validation():
    """Stage B: numeric field validation via validate_numeric_field."""
    text = _read("app/services/validation_service.py")
    assert "numeric_checks" in text, (
        "validation_service Stage B must have a numeric_checks list"
    )
    assert "validate_numeric_field(" in text, (
        "validation_service Stage B must call validate_numeric_field"
    )


def test_validate_service_stage_c_gated_by_if_not_errors():
    """Stage C: schema build validation, gated by `if not errors:`
    (only runs when Stage A and B have no errors)."""
    text = _read("app/services/validation_service.py")
    if_not_errors_pattern = re.search(
        r"if\s+not\s+errors\s*:\s*\n\s*try\s*:",
        text,
    )
    assert if_not_errors_pattern, (
        "validation_service Stage C must be gated by `if not errors: try:`"
    )


def test_validate_service_stage_c_catches_value_error_specifically():
    """Stage C must catch ValueError specifically, NOT bare Exception."""
    text = _read("app/services/validation_service.py")
    value_error_catch = re.search(
        r"except\s+ValueError\s+as\s+\w+\s*:",
        text,
    )
    assert value_error_catch, (
        "validation_service Stage C must catch ValueError specifically"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 6. Numeric max values preservation
# ─────────────────────────────────────────────────────────────────────────────

def test_validate_service_pins_all_9_numeric_max_values():
    """All 9 numeric field max values must be pinned exactly. These
    are preserved from the legacy /validate route (Phase 51D-1)."""
    text = _read("app/services/validation_service.py")
    expected_max_values = {
        "2000.0": "capacity_mw",
        "1000.0": "tariff_eur_mwh",
        "10000.0": "p50_hours",
        "1_000_000.0": "total_capex_keur",
        "500_000.0": "opex_y1_keur",
        "100.0": "gearing_pct",
        "10.0": "target_dscr",
        "30.0": "interest_rate_pct",
        "50.0": "tenor_years",
    }
    for max_str, field_name in expected_max_values.items():
        assert max_str in text, (
            f"validation_service must pin max value {max_str} for {field_name}"
        )
    for field_name in expected_max_values.values():
        assert f'"{field_name}"' in text, (
            f"validation_service must reference field {field_name} in numeric_checks"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 7. Runtime-snapshot parity call preservation
# ─────────────────────────────────────────────────────────────────────────────

def test_validate_service_calls_resolve_runtime_snapshot_source():
    """The runtime-snapshot parity call (Phase 51D-1 quirk) must be
    preserved exactly. The service must call
    deps.resolve_runtime_snapshot_source for parity with /run and
    /compare, even though the resolved snapshot is unused downstream.
    """
    text = _read("app/services/validation_service.py")
    assert "deps.resolve_runtime_snapshot_source" in text, (
        "validation_service must call deps.resolve_runtime_snapshot_source "
        "for parity with /run and /compare (Phase 51D-1 quirk preserved)"
    )


def test_validate_service_unpacks_only_first_tuple_element():
    """The runtime-snapshot parity call must unpack only the first
    tuple element (the snapshot itself) and discard the rest
    (scenario_record, warning, effective_runtime_origin)."""
    text = _read("app/services/validation_service.py")
    assert re.search(
        r"runtime_snapshot\s*,\s*_\s*,\s*_\s*,\s*_\s*=\s*deps\.resolve_runtime_snapshot_source",
        text,
    ), (
        "validation_service must unpack only the first element of the "
        "resolved snapshot tuple (parity quirk preserved)"
    )


def test_validate_service_resolves_snapshot_only_under_saved_state_or_user_created():
    """The runtime-snapshot resolution must only be triggered when
    EITHER (saved_state + active_scenario_id) OR (user_created
    project). This is preserved from the legacy /validate route."""
    text = _read("app/services/validation_service.py")
    # Look for the combined condition
    assert "saved_state" in text and "active_scenario_id" in text, (
        "validation_service runtime-snapshot branch must check saved_state + active_scenario_id"
    )
    assert "user_created" in text, (
        "validation_service runtime-snapshot branch must check user_created"
    )


def test_validate_route_does_not_call_resolve_runtime_snapshot_directly():
    """The /validate route must not call resolve_runtime_snapshot_source
    directly — that's a service concern now (parity call lives in the
    service)."""
    body = _get_validate_route_body()
    assert not re.search(r"resolve_runtime_snapshot_source\s*\(", body), (
        "/validate route must not call resolve_runtime_snapshot_source "
        "as a function (parity call lives in the service)"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 8. Read-only invariant
# ─────────────────────────────────────────────────────────────────────────────

def test_validate_service_does_not_call_persistence_helpers():
    """validation_service must NOT call any persistence / record_*
    helper on the /validate path. /validate is read-only by design."""
    text = _read("app/services/validation_service.py")
    for forbidden in (
        "record_compare_run",
        "record_workspace_runtime",
        "record_export",
        "record_runtime_summary_export",
        "record_institutional_workbook_export",
        "record_download_export",
        "update_scenario_last_run_summary",
    ):
        # Check for call / definition / attribute access patterns.
        call_pattern = re.compile(rf"\b{re.escape(forbidden)}\s*\(")
        def_pattern = re.compile(rf"def\s+{re.escape(forbidden)}\b")
        assert not call_pattern.search(text), (
            f"validation_service must not call {forbidden} (read-only route)"
        )
        assert not def_pattern.search(text), (
            f"validation_service must not define {forbidden}"
        )
    for forbidden in (
        "db.add", "db.commit", "db.flush",
        "session.add", "session.commit",
    ):
        assert forbidden not in text, (
            f"validation_service must not call {forbidden} (read-only route)"
        )


def test_validate_route_does_not_call_persistence_helpers():
    body = _get_validate_route_body()
    for forbidden in (
        "record_compare_run",
        "record_workspace_runtime",
        "record_export",
        "record_runtime_summary_export",
        "record_institutional_workbook_export",
        "record_download_export",
        "update_scenario_last_run_summary",
    ):
        call_pattern = re.compile(rf"\b{re.escape(forbidden)}\s*\(")
        def_pattern = re.compile(rf"def\s+{re.escape(forbidden)}\b")
        assert not call_pattern.search(body), (
            f"/validate route must not call {forbidden} (read-only route)"
        )
        assert not def_pattern.search(body), (
            f"/validate route must not define {forbidden}"
        )


def test_main_web_has_zero_direct_record_export_calls():
    src = _read("main_web.py")
    matches = re.findall(r"\brecord_export\s*\(", src)
    assert len(matches) == 0, (
        f"main_web must have 0 direct record_export calls, found {len(matches)}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 9. /run and /compare routes remain thin
# ─────────────────────────────────────────────────────────────────────────────

def test_run_route_remains_thin():
    body = _get_run_route_body()
    non_blank = _non_blank_lines(body)
    assert len(non_blank) < 200, (
        f"/run route body has {len(non_blank)} non-blank lines; "
        "Phase 51B thinness contract must be preserved"
    )


def test_compare_route_remains_thin():
    body = _get_compare_route_body()
    non_blank = _non_blank_lines(body)
    assert len(non_blank) < 50, (
        f"/compare route body has {len(non_blank)} non-blank lines; "
        "Phase 51C-2 thinness contract must be preserved"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 10. run_service and compare_service are intact
# ─────────────────────────────────────────────────────────────────────────────

def test_run_service_from_phase51b_still_intact():
    assert RUN_SERVICE_PATH.exists()
    text = RUN_SERVICE_PATH.read_text(encoding="utf-8")
    for symbol in ("RunRouteOutcome", "RunRouteDeps", "execute_run_route"):
        assert symbol in text, (
            f"run_service.py must still export {symbol}"
        )


def test_compare_service_from_phase51c2_still_intact():
    assert COMPARE_SERVICE_PATH.exists()
    text = COMPARE_SERVICE_PATH.read_text(encoding="utf-8")
    for symbol in ("CompareRouteOutcome", "CompareRouteDeps", "execute_compare_route"):
        assert symbol in text, (
            f"compare_service.py must still export {symbol}"
        )


def test_run_service_does_not_import_validate_service():
    text = RUN_SERVICE_PATH.read_text(encoding="utf-8")
    assert "validation_service" not in text, (
        "run_service must not import or reference validation_service"
    )


def test_compare_service_does_not_import_validate_service():
    text = COMPARE_SERVICE_PATH.read_text(encoding="utf-8")
    assert "validation_service" not in text, (
        "compare_service must not import or reference validation_service"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 11. Other main_web routes are unchanged
# ─────────────────────────────────────────────────────────────────────────────

def test_main_web_diff_is_scoped_to_validate_route():
    """The main_web.py diff vs origin/main must be scoped to the
    /validate route body. No other @app.* decorator line is added or
    removed."""
    result = subprocess.run(
        ["git", "diff", "origin/main", "--", "main_web.py"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    diff_text = result.stdout
    decorator_changes = [
        ln for ln in diff_text.splitlines()
        if (ln.startswith("+@app.") or ln.startswith("-@app."))
    ]
    non_validate_changes = [
        ln for ln in decorator_changes
        if "/validate" not in ln
    ]
    assert non_validate_changes == [], (
        "main_web.py diff must not touch any @app.* decorator "
        f"other than /validate; got: {non_validate_changes}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 12. Guardrails
# ─────────────────────────────────────────────────────────────────────────────

def test_no_fixture_csv_changes():
    """No real fixture CSV files must be modified by Phase 51D-2."""
    result = subprocess.run(
        ["git", "diff", "--name-only", "origin/main", "--", "*.csv"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    changed = [l for l in result.stdout.strip().split("\n") if l]
    fixture_prefixes = (
        "app/fixtures/", "app/services/fixtures/", "tests/fixtures/",
    )
    real_fixtures = [c for c in changed if c.startswith(fixture_prefixes)]
    assert real_fixtures == [], f"Real fixture CSVs changed: {real_fixtures}"


def test_no_javascript_financial_calculations_added():
    """No JS files should be added or changed in static/ by Phase 51D-2."""
    result = subprocess.run(
        ["git", "diff", "--name-only", "origin/main", "--", "static/"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    changed = [l for l in result.stdout.strip().split("\n") if l]
    js_files = [c for c in changed if c.endswith(".js")]
    assert js_files == [], f"JS files changed: {js_files}"


def test_no_services_js_files():
    """No JS files belong under app/services/ (sanity check)."""
    services = list((REPO_ROOT / "app" / "services").rglob("*.js"))
    assert services == [], f"no JS files belong under app/services: {services}"


def test_no_financial_formula_changes():
    """No financial formula / runtime / model output changes. Pin via
    guardrail: no changes to waterfall_core, project_factories,
    input_schema, input_adapter."""
    result = subprocess.run(
        ["git", "diff", "--name-only", "origin/main", "--",
         "app/waterfall_core.py", "app/project_factories.py",
         "app/input_schema.py", "app/input_adapter.py"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    changed = [l for l in result.stdout.strip().split("\n") if l]
    assert changed == [], f"Financial/runtime files changed: {changed}"


def test_no_production_code_changed_outside_validate_extraction():
    """Phase 51D-2 may change ONLY:
    - main_web.py (the /validate route body becomes thin)
    - app/services/validation_service.py (new file)
    - main_web.py import line for validation_service

    Every other production source file must be unchanged vs origin/main.
    """
    result = subprocess.run(
        ["git", "diff", "--name-only", "origin/main", "--",
         "app/api/", "app/persistence/", "app/waterfall_core.py",
         "app/services/run_service.py", "app/services/compare_service.py",
         "app/services/scenario_state_service.py",
         "app/services/export_service.py", "app/services/export_audit_service.py",
         "app/ui/", "app/excel_export.py", "app/input_adapter.py",
         "app/input_schema.py", "app/project_factories.py"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    changed = [l for l in result.stdout.strip().split("\n") if l]
    assert changed == [], (
        f"Phase 51D-2 must not change non-/validate production files; "
        f"got: {changed}"
    )


def test_main_web_does_not_import_runtime_guard_for_snapshot():
    """main_web must not import the legacy runtime_guard_for_snapshot
    directly — that's the lower-level repository function."""
    src = _read("main_web.py")
    assert "runtime_guard_for_snapshot" not in src, (
        "main_web must not import runtime_guard_for_snapshot directly"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 13. Live integration tests (TestClient)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def client(isolated_db):
    from fastapi.testclient import TestClient
    from main_web import app
    from app.auth import create_session_token, COOKIE_NAME
    tc = TestClient(app)
    token = create_session_token()
    tc.cookies.set(COOKIE_NAME, token)
    return tc


@pytest.fixture
def unauthenticated_client(isolated_db):
    from fastapi.testclient import TestClient
    from main_web import app
    return TestClient(app)


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    import uuid
    db_file = tmp_path / f"phase51d2_{uuid.uuid4().hex[:8]}.db"
    monkeypatch.setenv("FINCO_DB_PATH", str(db_file))
    import app.persistence.db as db_mod
    db_mod.DB_PATH = str(db_file)
    db_mod._connection = None
    yield str(db_file)
    db_mod._connection = None


def test_validate_unauthenticated_redirects_to_login(unauthenticated_client):
    """Unauthenticated /validate must 302 to /login."""
    r = unauthenticated_client.post(
        "/validate",
        data={"project_type": "Solar", "scenario": "Base"},
        follow_redirects=False,
    )
    assert r.status_code == 302
    assert "/login" in r.headers.get("location", "")


def test_validate_valid_solar_inputs_returns_validation_template(client):
    """Valid Solar inputs must render partials/validation.html."""
    r = client.post("/validate", data={
        "project_type": "Solar", "scenario": "Base",
        "capacity_mw": "100", "tariff_eur_mwh": "80", "p50_hours": "2500",
        "total_capex_keur": "100000", "opex_y1_keur": "2000",
        "gearing_pct": "70", "target_dscr": "1.3",
        "interest_rate_pct": "5.5", "tenor_years": "15",
    })
    assert r.status_code == 200
    text_lower = r.text.lower()
    assert (
        "validation" in text_lower
        or "run model" in text_lower
        or "fix the following" in text_lower
        or "error" in text_lower
    ), f"unexpected /validate response: {r.text[:300]}"


def test_validate_invalid_project_type_returns_error(client):
    """Invalid project_type must return errors."""
    r = client.post("/validate", data={
        "project_type": "Nuclear", "scenario": "Base",
    })
    assert r.status_code == 200
    text_lower = r.text.lower()
    assert "error" in text_lower, (
        f"unexpected /validate response for invalid project_type: {r.text[:300]}"
    )


def test_validate_above_max_capacity_mw_returns_error(client):
    """Above-max capacity_mw must return errors (Stage B)."""
    r = client.post("/validate", data={
        "project_type": "Solar", "scenario": "Base",
        "capacity_mw": "99999",
    })
    assert r.status_code == 200
    text_lower = r.text.lower()
    assert "error" in text_lower, (
        f"unexpected /validate response for above-max capacity: {r.text[:300]}"
    )


def test_validate_no_traceback_in_response(client):
    """No Python tracebacks should appear in the /validate response body."""
    r = client.post("/validate", data={"project_type": "Solar", "scenario": "Base"})
    assert "Traceback" not in r.text, (
        f"unexpected traceback in /validate response: {r.text[:500]}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 14. Smoke imports
# ─────────────────────────────────────────────────────────────────────────────

def test_main_web_imports_cleanly():
    sys.path.insert(0, str(REPO_ROOT))
    import main_web  # noqa: F401


def test_validate_service_imports_cleanly():
    import app.services.validation_service  # noqa: F401


# ─────────────────────────────────────────────────────────────────────────────
# 15. Regression checks for previous phases
# ─────────────────────────────────────────────────────────────────────────────

def test_phase51a_golden_tests_still_pass():
    r = subprocess.run(
        ["python3", "-m", "pytest",
         "tests/test_phase51a_run_route_golden_characterization.py", "-q",
         "--tb=no"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert r.returncode == 0, (
        f"Phase 51A golden tests regressed: {r.stdout[-500:]}"
    )


def test_phase51b_extraction_tests_still_pass():
    r = subprocess.run(
        ["python3", "-m", "pytest",
         "tests/test_phase51b_run_route_vertical_extraction.py", "-q",
         "--tb=no"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert r.returncode == 0, (
        f"Phase 51B extraction tests regressed: {r.stdout[-500:]}"
    )


def test_phase51c2_extraction_tests_still_pass():
    r = subprocess.run(
        ["python3", "-m", "pytest",
         "tests/test_phase51c2_compare_route_vertical_extraction.py", "-q",
         "--tb=no"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert r.returncode == 0, (
        f"Phase 51C-2 extraction tests regressed: {r.stdout[-500:]}"
    )


def test_phase51d1_characterization_tests_still_pass():
    """Phase 51D-1 characterization tests (with structural tests
    re-pointed to validation_service.py in this phase) must still
    pass."""
    r = subprocess.run(
        ["python3", "-m", "pytest",
         "tests/test_phase51d1_validate_route_golden_characterization.py", "-q",
         "--tb=no"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert r.returncode == 0, (
        f"Phase 51D-1 characterization tests regressed: {r.stdout[-500:]}"
    )
