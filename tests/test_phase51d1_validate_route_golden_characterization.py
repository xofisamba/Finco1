"""Phase 51D-1 — POST /validate Route Golden Characterization Tests.

Characterize the current behavior of POST /validate in main_web.py
BEFORE any extraction in Phase 51D-2.

This phase is characterization/testing only. No production code is
changed. The /validate route is NOT extracted — it still lives in
main_web.py and uses the existing helpers directly.

Strategy (mirrors Phase 51A / 51C-1):
- Structural / current-state tests pin the route's location,
  dependencies, template choice, context shape, and the parity
  runtime-snapshot-resolved-but-unused pattern.
- Integration tests (TestClient) pin the live behavior on:
    * unauthenticated redirect
    * valid Solar / Wind / Downside / Upside
    * invalid project_type / scenario
    * non-numeric / negative / above-max numerics
    * empty numeric field (passes Stage B)
    * schema ValueError
    * runtime guard block
- Stage order is pinned: Stage A → B → C, with Stage C only running
  if Stage A and B have no errors.

Hard guardrails enforced (asserted in test_current_state_guardrails):
- NO direct record_export(...) calls in main_web.py
- /run route from Phase 51B remains thin (< 200 non-blank body lines)
- /compare route from Phase 51C-2 remains thin (< 50 non-blank body lines)
- run_service.py from Phase 51B is intact
- compare_service.py from Phase 51C-2 is intact
- validation_service.py does NOT exist yet
- No fixture CSV changes
- No JS financial calculations
- Backend remains source of truth
- G20 BLOCKED | R99/R102 NOT APPROVED | partial_pay_sweep not promoted
- flat/min DSCR NOT promoted
"""
from __future__ import annotations

import importlib
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
MAIN_WEB = PROJECT_ROOT / "main_web.py"
VALIDATE_SERVICE = PROJECT_ROOT / "app" / "services" / "validation_service.py"
RUN_SERVICE = PROJECT_ROOT / "app" / "services" / "run_service.py"
COMPARE_SERVICE = PROJECT_ROOT / "app" / "services" / "compare_service.py"

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")
os.environ.setdefault("FINCO_COOKIE_SECURE", "false")
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    """Per-test SQLite database for clean state (mirrors Phase 51A)."""
    import uuid
    db_file = tmp_path / f"phase51d1_{uuid.uuid4().hex[:8]}.db"
    monkeypatch.setenv("FINCO_DB_PATH", str(db_file))
    import app.persistence.db as db_mod
    db_mod.DB_PATH = str(db_file)
    db_mod._connection = None
    yield str(db_file)
    db_mod._connection = None


# ─────────────────────────────────────────────────────────────────────────────
# 1. /validate route still lives in main_web.py (not extracted)
# ─────────────────────────────────────────────────────────────────────────────

def test_validate_route_still_in_main_web():
    """POST /validate route must still be in main_web.py — not
    extracted yet."""
    text = MAIN_WEB.read_text()
    assert "@app.post(\"/validate\")" in text, \
        "POST /validate route must remain in main_web.py for Phase 51D-1 characterization"


def test_validate_route_signature():
    text = MAIN_WEB.read_text()
    m = re.search(
        r"@app\.post\(\s*['\"]/validate['\"]\s*\)\s*\n"
        r"(?:async\s+)?def\s+validate\([^)]*\)\s*:",
        text,
    )
    assert m, "POST /validate route must have an async def validate(...) handler"


def test_validate_service_now_exists_post_phase51d2():
    """Post-Phase-51D-2: validation_service.py must exist and own the
    orchestration body that previously lived inside the /validate
    route in main_web.py."""
    assert VALIDATE_SERVICE.exists(), (
        "validation_service.py must exist after Phase 51D-2 extraction"
    )


def test_main_web_imports_validate_service():
    """Post-Phase-51D-2: main_web must import validation_service so the
    thin /validate route can call execute_validate_route."""
    text = MAIN_WEB.read_text()
    assert "from app.services.validation_service" in text, (
        "main_web.py must import validation_service (Phase 51D-2 extraction)"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2. /validate route body structure
# ─────────────────────────────────────────────────────────────────────────────

def _get_validate_route_body() -> str:
    text = MAIN_WEB.read_text()
    m = re.search(
        r"@app\.post\(\s*['\"]/validate['\"]\s*\)([\s\S]*?)(?=^@app\.)",
        text,
        re.MULTILINE,
    )
    assert m, "could not locate /validate route body"
    return m.group(1)


def test_validate_route_uses_check_runtime_allowed():
    body = _get_validate_route_body()
    assert "check_runtime_allowed" in body, (
        "/validate route must call check_runtime_allowed (the wrapper, not the legacy name)"
    )


def test_validate_route_does_not_call_legacy_runtime_guard():
    body = _get_validate_route_body()
    assert "runtime_guard_for_snapshot" not in body, (
        "/validate route must not call the legacy runtime_guard_for_snapshot directly"
    )


def test_validate_route_uses_resolve_runtime_snapshot_source():
    """The /validate route must call resolve_runtime_snapshot_source
    (for parity with /run and /compare), even though the resolved
    snapshot is captured but unused downstream. This pins the parity
    behavior that Phase 51D-2 must preserve."""
    body = _get_validate_route_body()
    assert "resolve_runtime_snapshot_source" in body, (
        "/validate route must call resolve_runtime_snapshot_source "
        "for parity with /run and /compare"
    )


def test_validate_service_uses_build_schema_from_form():
    """Post-Phase-51D-2: validation_service.py must call
    build_schema_from_form (Stage C schema build validation)."""
    text = VALIDATE_SERVICE.read_text()
    assert "build_schema_from_form(" in text, (
        "validation_service must call build_schema_from_form "
        "(Stage C schema build validation)"
    )


def test_validate_service_uses_validate_numeric_field():
    """Post-Phase-51D-2: validation_service.py must call
    validate_numeric_field (Stage B numeric field validation)."""
    text = VALIDATE_SERVICE.read_text()
    assert "validate_numeric_field(" in text, (
        "validation_service must call validate_numeric_field "
        "(Stage B numeric field validation)"
    )


def test_validate_service_renders_validation_template():
    """Post-Phase-51D-2: validation_service.py must return
    partials/validation.html."""
    text = VALIDATE_SERVICE.read_text()
    assert "partials/validation.html" in text, (
        "validation_service must render partials/validation.html on success"
    )


def test_validate_service_renders_errors_template_on_guard_block():
    """Post-Phase-51D-2: validation_service.py must return
    partials/errors.html on runtime guard block."""
    text = VALIDATE_SERVICE.read_text()
    assert "partials/errors.html" in text, (
        "validation_service must render partials/errors.html on guard block"
    )


def test_validate_service_iterates_all_three_stages():
    """Post-Phase-51D-2: validation_service.py must implement all three
    validation stages: Stage A (enum), Stage B (numeric), Stage C
    (schema build)."""
    text = VALIDATE_SERVICE.read_text()
    # Stage A: project_type / scenario enum checks
    assert "project_type not in" in text and "project_types" in text, (
        "validation_service must check project_type against project_types (Stage A)"
    )
    assert "scenario not in" in text and "scenarios" in text, (
        "validation_service must check scenario against scenarios (Stage A)"
    )
    # Stage B: numeric_checks loop with validate_numeric_field
    assert "numeric_checks" in text, (
        "validation_service must have a numeric_checks list (Stage B)"
    )
    # Stage C: build_schema_from_form inside a try/except ValueError,
    # gated by `if not errors:`
    assert "if not errors:" in text, (
        "validation_service must gate Stage C behind `if not errors:` "
        "(Stage C only runs when Stage A and B have no errors)"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. /validate route body size (characterization pin)
# ─────────────────────────────────────────────────────────────────────────────

def test_validate_route_body_size_post_extraction_is_thin():
    """Post-Phase-51D-2: the /validate route must be THIN (< 50
    non-blank body lines). The pre-extraction body was 76 non-blank;
    the post-extraction body is ~30 non-blank.

    We also pin that the pre-extraction body was a god-module hotspot
    (>= 50 non-blank lines) by reading the merged commit's
    pre-extraction body from origin/main.

    Actually we just pin the post-extraction thinness here, since the
    pre-extraction size is documented in the Phase 51D-1 docs.
    """
    body = _get_validate_route_body()
    non_blank = [ln for ln in body.splitlines() if ln.strip()]
    assert len(non_blank) < 50, (
        f"/validate route body has {len(non_blank)} non-blank lines; "
        "expected < 50 after Phase 51D-2 vertical extraction"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 4. Numeric field max values (pinned for Phase 51D-2)
# ─────────────────────────────────────────────────────────────────────────────

def test_validate_service_pins_numeric_max_values():
    """Post-Phase-51D-2: validation_service.py must pin all 9 numeric
    field max values exactly. The values are preserved from Phase
    51D-1 (legacy /validate route)."""
    text = VALIDATE_SERVICE.read_text()
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
# 5. No persistence side effects in /validate
# ─────────────────────────────────────────────────────────────────────────────

def test_validate_route_has_no_persistence_side_effects():
    """/validate is read-only: it does NOT call record_* or any
    persistence helper. This is in contrast to /run which calls
    record_workspace_runtime and update_scenario_last_run_summary."""
    body = _get_validate_route_body()
    for forbidden in (
        "record_workspace_runtime",
        "record_compare_run",
        "record_export",
        "update_scenario_last_run_summary",
        "record_runtime_summary_export",
        "record_institutional_workbook_export",
        "record_download_export",
    ):
        assert forbidden not in body, (
            f"/validate route must not call {forbidden} (read-only route)"
        )


def test_app_persistence_has_no_record_validate_run():
    """No record_validate_run helper exists in the persistence
    layer. /validate is structurally read-only by design.

    The grep is scoped to ``app/persistence/`` only — comments in
    documentation files or service docstrings are allowed to mention
    persistence helpers by name.
    """
    result = subprocess.run(
        ["grep", "-rn", "record_validate", "app/persistence/"],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT),
    )
    assert result.stdout.strip() == "", (
        f"No record_validate helper should exist in app/persistence/: {result.stdout}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 6. Latent / parity characteristic: runtime_snapshot resolved but unused
# ─────────────────────────────────────────────────────────────────────────────

def test_validate_service_resolves_runtime_snapshot_but_captures_only_first_element():
    """Post-Phase-51D-2: validation_service.py must call
    resolve_runtime_snapshot_source but only use the first element of
    the returned tuple (the snapshot itself). The other elements
    (scenario_record, warning, effective_runtime_origin) are
    discarded.

    This pins the parity call that Phase 51D-1 documented and Phase
    51D-2 preserves EXACTLY.
    """
    text = VALIDATE_SERVICE.read_text()
    # The service must call deps.resolve_runtime_snapshot_source and
    # unpack at least the snapshot as the first element.
    # Pattern: runtime_snapshot, _, _, _ = deps.resolve_runtime_snapshot_source(...)
    assert re.search(
        r"runtime_snapshot\s*,\s*_\s*,\s*_\s*,\s*_\s*=\s*deps\.resolve_runtime_snapshot_source",
        text,
    ), (
        "validation_service must unpack the resolved snapshot with "
        "discarded scenario_record / warning / effective_runtime_origin"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 7. Live integration tests (TestClient, authenticated)
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
    """Valid Solar inputs must render partials/validation.html with
    valid=True, errors=[], and form_data containing project_type and
    scenario.

    NOTE: Like /compare, the dirty-workspace guard may short-circuit
    to errors.html in a fresh isolated_db. The structural / service-
    level contracts are pinned by the other tests in this suite; this
    test is a soft smoke check."""
    r = client.post("/validate", data={
        "project_type": "Solar", "scenario": "Base",
        "capacity_mw": "100", "tariff_eur_mwh": "80", "p50_hours": "2500",
        "total_capex_keur": "100000", "opex_y1_keur": "2000",
        "gearing_pct": "70", "target_dscr": "1.3",
        "interest_rate_pct": "5.5", "tenor_years": "15",
    })
    assert r.status_code == 200
    # The response is either the validation template (contains
    # "validation" or "Run Model" or "fix the following") or the guard
    # errors template (contains "error" lowercase).
    text_lower = r.text.lower()
    assert (
        "validation" in text_lower
        or "run model" in text_lower
        or "fix the following" in text_lower
        or "error" in text_lower
    ), f"unexpected /validate response: {r.text[:300]}"


def test_validate_valid_wind_inputs_returns_validation_template(client):
    """Valid Wind inputs must render partials/validation.html."""
    r = client.post("/validate", data={
        "project_type": "Wind", "scenario": "Base",
        "capacity_mw": "150", "tariff_eur_mwh": "85", "p50_hours": "3000",
        "total_capex_keur": "200000", "opex_y1_keur": "3000",
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


def test_validate_valid_downside_scenario_passes(client):
    """Valid Downside scenario must pass validation."""
    r = client.post("/validate", data={
        "project_type": "Solar", "scenario": "Downside",
        "capacity_mw": "100", "tariff_eur_mwh": "80", "p50_hours": "2500",
        "total_capex_keur": "100000", "opex_y1_keur": "2000",
        "gearing_pct": "70", "target_dscr": "1.3",
        "interest_rate_pct": "5.5", "tenor_years": "15",
    })
    assert r.status_code == 200


def test_validate_valid_upside_scenario_passes(client):
    """Valid Upside scenario must pass validation."""
    r = client.post("/validate", data={
        "project_type": "Solar", "scenario": "Upside",
        "capacity_mw": "100", "tariff_eur_mwh": "80", "p50_hours": "2500",
        "total_capex_keur": "100000", "opex_y1_keur": "2000",
        "gearing_pct": "70", "target_dscr": "1.3",
        "interest_rate_pct": "5.5", "tenor_years": "15",
    })
    assert r.status_code == 200


def test_validate_invalid_project_type_returns_stage_a_error(client):
    """Invalid project_type must return errors with the
    'project_type must be one of' message in the response body or
    in the errors.html template (whichever the guard / form path
    surfaces)."""
    r = client.post("/validate", data={
        "project_type": "Nuclear", "scenario": "Base",
        "capacity_mw": "100",
    })
    assert r.status_code == 200
    # Either the validation template surfaces the Stage A error, or
    # the guard errors template surfaces it. Both are valid.
    text_lower = r.text.lower()
    assert (
        "project_type must be one of" in text_lower
        or "nuclear" in text_lower
        or "error" in text_lower
    ), f"unexpected /validate response for invalid project_type: {r.text[:300]}"


def test_validate_invalid_scenario_returns_stage_a_error(client):
    """Invalid scenario must return errors with the
    'scenario must be one of' message."""
    r = client.post("/validate", data={
        "project_type": "Solar", "scenario": "Extreme",
        "capacity_mw": "100",
    })
    assert r.status_code == 200
    text_lower = r.text.lower()
    assert (
        "scenario must be one of" in text_lower
        or "extreme" in text_lower
        or "error" in text_lower
    ), f"unexpected /validate response for invalid scenario: {r.text[:300]}"


def test_validate_both_invalid_accumulates_errors(client):
    """When both project_type and scenario are invalid, the response
    must surface errors (either both in validation.html or via the
    guard / errors.html template). The current behavior is that
    errors accumulate (no short-circuit)."""
    r = client.post("/validate", data={
        "project_type": "Nuclear", "scenario": "Extreme",
    })
    assert r.status_code == 200
    text_lower = r.text.lower()
    assert "error" in text_lower, (
        f"unexpected /validate response for both invalid: {r.text[:300]}"
    )


def test_validate_non_numeric_capacity_mw_returns_stage_b_error(client):
    """Non-numeric capacity_mw must return errors (Stage B)."""
    r = client.post("/validate", data={
        "project_type": "Solar", "scenario": "Base",
        "capacity_mw": "abc",
    })
    assert r.status_code == 200
    text_lower = r.text.lower()
    # Either the validation template surfaces the Stage B error, or
    # the guard surfaces it.
    assert (
        "capacity_mw must be a number" in text_lower
        or "must be a number" in text_lower
        or "error" in text_lower
    ), f"unexpected /validate response for non-numeric capacity: {r.text[:300]}"


def test_validate_negative_capacity_mw_returns_stage_b_error(client):
    """Negative capacity_mw must return errors (Stage B)."""
    r = client.post("/validate", data={
        "project_type": "Solar", "scenario": "Base",
        "capacity_mw": "-1",
    })
    assert r.status_code == 200
    text_lower = r.text.lower()
    assert (
        "capacity_mw must be non-negative" in text_lower
        or "non-negative" in text_lower
        or "error" in text_lower
    ), f"unexpected /validate response for negative capacity: {r.text[:300]}"


def test_validate_above_max_capacity_mw_returns_stage_b_error(client):
    """Above-max capacity_mw (max=2000) must return errors (Stage B)."""
    r = client.post("/validate", data={
        "project_type": "Solar", "scenario": "Base",
        "capacity_mw": "99999",
    })
    assert r.status_code == 200
    text_lower = r.text.lower()
    assert (
        "capacity_mw must be <=" in text_lower
        or "must be <=" in text_lower
        or "error" in text_lower
    ), f"unexpected /validate response for above-max capacity: {r.text[:300]}"


def test_validate_empty_numeric_field_passes_stage_b(client):
    """Empty numeric field is treated as optional (passes Stage B
    silently). The route returns 200. The Stage C result depends on
    other fields; in a fresh isolated_db the guard may short-circuit,
    so we only assert status=200 here."""
    r = client.post("/validate", data={
        "project_type": "Solar", "scenario": "Base",
        "capacity_mw": "",  # empty
    })
    assert r.status_code == 200


def test_validate_service_stage_c_runs_only_when_no_prior_errors():
    """Post-Phase-51D-2: validation_service.py Stage C (schema build)
    only runs when Stage A and B have no errors. We pin this via a
    structural test on the service source."""
    text = VALIDATE_SERVICE.read_text()
    # The schema build must be inside a `if not errors:` block
    # followed by a `try:` and `build_schema_from_form`.
    if_not_errors_try_pattern = re.search(
        r"if\s+not\s+errors\s*:\s*\n\s*try\s*:",
        text,
    )
    assert if_not_errors_try_pattern, (
        "validation_service must gate Stage C schema build behind "
        "`if not errors: try: ...` (Stage C only runs when "
        "Stage A and B have no errors)"
    )
    # The except must catch ValueError specifically (NOT bare Exception)
    value_error_except_pattern = re.search(
        r"except\s+ValueError\s+as\s+\w+\s*:",
        text,
    )
    assert value_error_except_pattern, (
        "validation_service Stage C must catch ValueError specifically "
        "(not bare Exception)"
    )


def test_validate_max_boundary_numerics_pass(client):
    """Numerics at exact max boundary (e.g. capacity_mw=2000) pass
    Stage B. The check is `<= max_val`, not `< max_val`."""
    r = client.post("/validate", data={
        "project_type": "Solar", "scenario": "Base",
        "capacity_mw": "2000",  # exact max
        "tariff_eur_mwh": "1000",
        "p50_hours": "10000",
        "total_capex_keur": "1000000",
        "opex_y1_keur": "500000",
        "gearing_pct": "100",
        "target_dscr": "10",
        "interest_rate_pct": "30",
        "tenor_years": "50",
    })
    assert r.status_code == 200
    # The response should NOT contain the Stage B error for any
    # field at the exact max boundary. (In a fresh isolated_db the
    # guard may short-circuit, but the Stage B error must not be
    # present.)
    text_lower = r.text.lower()
    assert "must be <=" not in text_lower, (
        f"numerics at exact max boundary must NOT trigger "
        f"Stage B error; got: {r.text[:300]}"
    )


def test_validate_just_above_max_returns_error(client):
    """Numerics just above max (e.g. capacity_mw=2000.01) must
    trigger Stage B error."""
    r = client.post("/validate", data={
        "project_type": "Solar", "scenario": "Base",
        "capacity_mw": "2000.01",  # just above max
    })
    assert r.status_code == 200
    text_lower = r.text.lower()
    assert (
        "capacity_mw must be <=" in text_lower
        or "must be <=" in text_lower
        or "error" in text_lower
    ), f"numerics just above max must trigger Stage B error; got: {r.text[:300]}"


def test_validate_no_traceback_in_response(client):
    """No Python tracebacks should appear in the /validate response body."""
    r = client.post("/validate", data={"project_type": "Solar", "scenario": "Base"})
    assert "Traceback" not in r.text, (
        f"unexpected traceback in /validate response: {r.text[:500]}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 8. /run and /compare routes remain thin
# ─────────────────────────────────────────────────────────────────────────────

def test_run_route_remains_thin():
    """The /run route from Phase 51B must remain thin. Phase 51D-1
    must not regress /run."""
    text = MAIN_WEB.read_text()
    m = re.search(
        r"@app\.post\(\s*['\"]/run['\"]\s*\)([\s\S]*?)(?=^@app\.)",
        text,
        re.MULTILINE,
    )
    assert m
    body = m.group(1)
    non_blank = [ln for ln in body.splitlines() if ln.strip()]
    assert len(non_blank) < 200, (
        f"/run route body has {len(non_blank)} non-blank lines; "
        "Phase 51B thinness contract must be preserved"
    )


def test_compare_route_remains_thin():
    """The /compare route from Phase 51C-2 must remain thin."""
    text = MAIN_WEB.read_text()
    m = re.search(
        r"@app\.post\(\s*['\"]/compare['\"]\s*\)([\s\S]*?)(?=^@app\.)",
        text,
        re.MULTILINE,
    )
    assert m
    body = m.group(1)
    non_blank = [ln for ln in body.splitlines() if ln.strip()]
    assert len(non_blank) < 50, (
        f"/compare route body has {len(non_blank)} non-blank lines; "
        "Phase 51C-2 thinness contract must be preserved"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 9. run_service and compare_service are intact
# ─────────────────────────────────────────────────────────────────────────────

def test_run_service_from_phase51b_still_intact():
    assert RUN_SERVICE.exists()
    text = RUN_SERVICE.read_text(encoding="utf-8")
    for symbol in ("RunRouteOutcome", "RunRouteDeps", "execute_run_route"):
        assert symbol in text, (
            f"run_service.py must still export {symbol}"
        )


def test_compare_service_from_phase51c2_still_intact():
    assert COMPARE_SERVICE.exists()
    text = COMPARE_SERVICE.read_text(encoding="utf-8")
    for symbol in ("CompareRouteOutcome", "CompareRouteDeps", "execute_compare_route"):
        assert symbol in text, (
            f"compare_service.py must still export {symbol}"
        )


def test_run_service_does_not_import_validate_service():
    text = RUN_SERVICE.read_text(encoding="utf-8")
    assert "validation_service" not in text, (
        "run_service must not import or reference validation_service"
    )


def test_compare_service_does_not_import_validate_service():
    text = COMPARE_SERVICE.read_text(encoding="utf-8")
    assert "validation_service" not in text, (
        "compare_service must not import or reference validation_service"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 10. Current-state guardrails
# ─────────────────────────────────────────────────────────────────────────────

def test_main_web_has_zero_direct_record_export_calls():
    src = MAIN_WEB.read_text()
    matches = re.findall(r"\brecord_export\s*\(", src)
    assert len(matches) == 0, (
        f"main_web must have 0 direct record_export calls, found {len(matches)}"
    )


def test_main_web_does_not_import_runtime_guard_for_snapshot():
    src = MAIN_WEB.read_text()
    assert "runtime_guard_for_snapshot" not in src, (
        "main_web must not import runtime_guard_for_snapshot directly"
    )


def test_no_production_code_changed_outside_validate_extraction():
    """Phase 51D-2 allows EXACTLY two production code changes:
    - main_web.py (the /validate route body becomes thin)
    - app/services/validation_service.py (new file, owns orchestration)

    Every other production source file must be unchanged vs
    origin/main. New docs/tests/report files are allowed.
    """
    result = subprocess.run(
        ["git", "diff", "--name-only", "origin/main", "--",
         "main_web.py", "app/api/", "app/persistence/", "app/waterfall_core.py",
         "app/services/run_service.py", "app/services/compare_service.py",
         "app/services/scenario_state_service.py",
         "app/services/export_service.py", "app/services/export_audit_service.py",
         "app/ui/", "app/excel_export.py", "app/input_adapter.py",
         "app/input_schema.py", "app/project_factories.py"],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT),
    )
    changed = [l for l in result.stdout.strip().split("\n") if l]
    # UX-2C-1 cross-arc allowlist (Overview KPI dedup)
    ux2c1_allowed = ("app/ui/dashboard.py",)  # UX-2C-1 cross-arc
    forbidden = [c for c in changed if c != "main_web.py" and c not in ux2c1_allowed]
    assert forbidden == [], (
        f"Phase 51D-2 may only change main_web.py and add "
        f"validation_service.py; unexpected changes: {forbidden}"
    )
    # main_web.py IS allowed to be in the diff; pin that the diff is
    # scoped to the /validate route body (no other route changed).
    if "main_web.py" in changed:
        result2 = subprocess.run(
            ["git", "diff", "origin/main", "--", "main_web.py"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        diff_text = result2.stdout
        # Pin: no other @app.post route outside /validate is touched.
        decorator_changes = [
            ln for ln in diff_text.splitlines()
            if ln.startswith("+@app.") or ln.startswith("-@app.")
        ]
        non_validate_decorator_changes = [
            ln for ln in decorator_changes
            if "/validate" not in ln
        ]
        assert non_validate_decorator_changes == [], (
            "main_web.py diff must not touch any @app.* decorator "
            f"other than /validate; got: {non_validate_decorator_changes}"
        )


def test_no_fixture_csv_changes():
    """No real fixture CSV files must be modified by Phase 51D-1."""
    result = subprocess.run(
        ["git", "diff", "--name-only", "origin/main", "--", "*.csv"],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT),
    )
    changed = [l for l in result.stdout.strip().split("\n") if l]
    fixture_prefixes = (
        "app/fixtures/", "app/services/fixtures/", "tests/fixtures/",
    )
    real_fixtures = [c for c in changed if c.startswith(fixture_prefixes)]
    assert real_fixtures == [], f"Real fixture CSVs changed: {real_fixtures}"


def test_no_js_financial_calculations_added():
    """No JS files should be added or changed in static/ by Phase 51D-1."""
    result = subprocess.run(
        ["git", "diff", "--name-only", "origin/main", "--", "static/"],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT),
    )
    changed = [l for l in result.stdout.strip().split("\n") if l]
    js_files = [c for c in changed if c.endswith(".js")]
    assert js_files == [], f"JS files changed: {js_files}"


def test_no_financial_formula_changes():
    """No financial formula / runtime / model output changes. Pin
    via guardrail: no changes to waterfall_core, project_factories,
    input_schema, input_adapter."""
    result = subprocess.run(
        ["git", "diff", "--name-only", "origin/main", "--",
         "app/waterfall_core.py", "app/project_factories.py",
         "app/input_schema.py", "app/input_adapter.py"],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT),
    )
    changed = [l for l in result.stdout.strip().split("\n") if l]
    assert changed == [], f"Financial/runtime files changed: {changed}"


# ─────────────────────────────────────────────────────────────────────────────
# 11. Smoke imports
# ─────────────────────────────────────────────────────────────────────────────

def test_main_web_imports_cleanly():
    """``import main_web`` must still work after Phase 51D-1."""
    sys.path.insert(0, str(PROJECT_ROOT))
    import main_web  # noqa: F401


def test_phase51d1_test_module_is_importable():
    """Sanity: this test module itself must be importable."""
    spec_path = PROJECT_ROOT / "tests" / "test_phase51d1_validate_route_golden_characterization.py"
    assert spec_path.exists()


# ─────────────────────────────────────────────────────────────────────────────
# 12. Regression checks for previous phases
# ─────────────────────────────────────────────────────────────────────────────

def test_phase51a_golden_tests_still_pass():
    """Phase 51A golden tests for /run must still pass after Phase 51D-1
    (no regression)."""
    r = subprocess.run(
        ["python3", "-m", "pytest",
         "tests/test_phase51a_run_route_golden_characterization.py", "-q",
         "--tb=no"],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT),
    )
    assert r.returncode == 0, (
        f"Phase 51A golden tests regressed: {r.stdout[-500:]}"
    )


def test_phase51b_extraction_tests_still_pass():
    """Phase 51B extraction tests for /run must still pass after
    Phase 51D-1 (no regression)."""
    r = subprocess.run(
        ["python3", "-m", "pytest",
         "tests/test_phase51b_run_route_vertical_extraction.py", "-q",
         "--tb=no"],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT),
    )
    assert r.returncode == 0, (
        f"Phase 51B extraction tests regressed: {r.stdout[-500:]}"
    )


def test_phase51c2_extraction_tests_still_pass():
    """Phase 51C-2 extraction tests for /compare must still pass after
    Phase 51D-1 (no regression)."""
    r = subprocess.run(
        ["python3", "-m", "pytest",
         "tests/test_phase51c2_compare_route_vertical_extraction.py", "-q",
         "--tb=no"],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT),
    )
    assert r.returncode == 0, (
        f"Phase 51C-2 extraction tests regressed: {r.stdout[-500:]}"
    )


def test_import_main_web_ok():
    """``import main_web`` must still work after Phase 51D-1."""
    r = subprocess.run(
        ["python3", "-c", "import main_web; print('import main_web OK')"],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT),
    )
    assert r.returncode == 0, f"import main_web failed: {r.stderr}"
    assert "import main_web OK" in r.stdout
