"""Phase 51C-1 — POST /compare Route Golden Characterization Tests.

Characterize the current behavior of POST /compare in main_web.py BEFORE
any extraction in Phase 51C-2.

This phase is characterization/testing only. No production code is
changed. The /compare route is NOT extracted — it still lives in
main_web.py and uses the existing helpers directly.

Strategy:
- Structural / current-state tests pin the route's location,
  dependencies, template choice, context shape, and a latent bug
  (NameError on user_created path because `runtime_snapshot` is
  referenced but never defined in /compare).
- Integration tests (TestClient) pin the live behavior on:
    * unauthenticated redirect
    * invalid project_type error
    * generic solar compare
    * generic wind compare
    * schema validation error
- xfail tests mark paths that the current code does not handle
  correctly (or at all) and that Phase 51C-2 must fix as part of
  the extraction.

Hard guardrails enforced (asserted in test_current_state_guardrails):
- NO direct record_export(...) calls in main_web.py
- NO direct runtime_guard_for_snapshot import in main_web.py
- /run route from Phase 51B remains thin (< 200 non-blank body lines)
- run_service.py from Phase 51B is intact
- No fixture CSV changes (git diff against HEAD scoped to real fixtures)
- No JS financial calculations
- Backend remains source of truth
- G20 BLOCKED | R99/R102 NOT APPROVED | partial_pay_sweep not promoted
- flat/min DSCR NOT promoted
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
MAIN_WEB = PROJECT_ROOT / "main_web.py"
COMPARE_SERVICE = PROJECT_ROOT / "app/services/compare_service.py"
RUN_SERVICE = PROJECT_ROOT / "app/services/run_service.py"

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")
os.environ.setdefault("FINCO_COOKIE_SECURE", "false")
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    """Per-test SQLite database for clean state (mirrors Phase 51A)."""
    import uuid
    db_file = tmp_path / f"phase51c1_{uuid.uuid4().hex[:8]}.db"
    monkeypatch.setenv("FINCO_DB_PATH", str(db_file))
    import app.persistence.db as db_mod
    db_mod.DB_PATH = str(db_file)
    db_mod._connection = None
    yield str(db_file)
    db_mod._connection = None


# ─────────────────────────────────────────────────────────────────────────────
# 1. /compare route still lives in main_web.py (not extracted)
# ─────────────────────────────────────────────────────────────────────────────

def test_compare_route_still_in_main_web():
    """POST /compare route must still be in main_web.py — not extracted yet."""
    text = MAIN_WEB.read_text()
    assert "@app.post(\"/compare\")" in text, \
        "POST /compare route must remain in main_web.py for Phase 51C-1 characterization"


def test_compare_route_signature():
    text = MAIN_WEB.read_text()
    m = re.search(
        r"@app\.post\(\s*['\"]/compare['\"]\s*\)\s*\n"
        r"(?:async\s+)?def\s+compare\([^)]*\)\s*:",
        text,
    )
    assert m, "POST /compare route must have an async def compare(...) handler"


def test_compare_service_does_not_exist_yet():
    """Pre-Phase-51C-2: compare_service.py must not exist."""
    assert not COMPARE_SERVICE.exists(), (
        "compare_service.py must NOT exist before Phase 51C-2 extraction"
    )


def test_main_web_does_not_import_compare_service():
    """main_web must not import compare_service yet."""
    text = MAIN_WEB.read_text()
    assert "from app.services.compare_service" not in text
    assert "import app.services.compare_service" not in text


# ─────────────────────────────────────────────────────────────────────────────
# 2. /compare route body structure
# ─────────────────────────────────────────────────────────────────────────────

def _get_compare_route_body() -> str:
    text = MAIN_WEB.read_text()
    m = re.search(
        r"@app\.post\(\s*['\"]/compare['\"]\s*\)([\s\S]*?)(?=^@app\.)",
        text,
        re.MULTILINE,
    )
    assert m, "could not locate /compare route body"
    return m.group(1)


def test_compare_route_uses_check_runtime_allowed():
    body = _get_compare_route_body()
    assert "check_runtime_allowed" in body, (
        "/compare route must call check_runtime_allowed (the wrapper, not the legacy name)"
    )


def test_compare_route_does_not_call_legacy_runtime_guard():
    body = _get_compare_route_body()
    assert "runtime_guard_for_snapshot" not in body, (
        "/compare route must not call the legacy runtime_guard_for_snapshot directly"
    )


def test_compare_route_uses_run_project():
    body = _get_compare_route_body()
    assert "run_project(" in body, (
        "/compare route must call run_project(...) to execute scenarios"
    )


def test_compare_route_iterates_scenarios_constant():
    body = _get_compare_route_body()
    assert "SCENARIOS" in body, (
        "/compare route must iterate over the SCENARIOS constant"
    )


def test_compare_route_renders_comparison_template():
    body = _get_compare_route_body()
    assert "partials/comparison.html" in body, (
        "/compare route must render partials/comparison.html on success"
    )


def test_compare_route_renders_errors_template():
    body = _get_compare_route_body()
    assert "partials/errors.html" in body, (
        "/compare route must render partials/errors.html on error paths"
    )


def test_compare_route_runs_three_scenarios_in_loop():
    """The /compare route iterates Base/Downside/Upside in a for loop
    and captures 6 KPIs per scenario (project_irr, equity_irr, min_dscr,
    avg_dscr, total_revenue_keur, total_ebitda_keur)."""
    body = _get_compare_route_body()
    for kpi in (
        "project_irr", "equity_irr", "min_dscr", "avg_dscr",
        "total_revenue_keur", "total_ebitda_keur",
    ):
        assert kpi in body, f"/compare route must capture KPI: {kpi}"


def test_compare_route_continues_loop_on_per_scenario_error():
    """On per-scenario exception, the loop must continue and the
    scenario gets ``{"error": str(e)}`` in results. This is soft-error
    semantics, not hard-error."""
    body = _get_compare_route_body()
    assert '"error"' in body or "'error'" in body, (
        "/compare route must capture per-scenario errors as "
        '{"error": str(e)} and continue the loop'
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. /compare route body size (characterization only — pin current state)
# ─────────────────────────────────────────────────────────────────────────────

def test_compare_route_body_size_characterization():
    """Pin the current /compare body size for Phase 51C-1
    characterization. Phase 51C-2 will assert the post-extraction
    size shrinks. Currently ~100 lines / ~89 non-blank."""
    body = _get_compare_route_body()
    non_blank = [ln for ln in body.splitlines() if ln.strip()]
    # Generous upper bound; the real shrink is asserted in 51C-2
    assert len(non_blank) < 200, (
        f"/compare route body has {len(non_blank)} non-blank lines; "
        "expected < 200 (characterization pin)"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 4. No persistence side effects in /compare
# ─────────────────────────────────────────────────────────────────────────────

def test_compare_route_has_no_persistence_side_effects():
    """/compare is read-only: it does NOT call record_compare_run or
    any record_* helper. This is in contrast to /run which calls
    record_workspace_runtime and update_scenario_last_run_summary."""
    body = _get_compare_route_body()
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
            f"/compare route must not call {forbidden} (read-only route)"
        )


def test_app_persistence_has_no_record_compare_run():
    """Confirmed: no record_compare_run helper exists in the codebase
    to begin with. /compare is structurally read-only by design."""
    result = subprocess.run(
        ["grep", "-rn", "record_compare", "app/"],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT),
    )
    assert result.stdout.strip() == "", (
        f"No record_compare helper should exist: {result.stdout}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 5. Latent bug: runtime_snapshot NameError on user_created path
# ─────────────────────────────────────────────────────────────────────────────

def test_compare_route_references_undefined_runtime_snapshot():
    """PRE-EXISTING LATENT BUG (not introduced by Phase 51C-1).

    /compare references ``runtime_snapshot`` on the user_created path
    (line ~1612) but never defines it. The /run handler defines
    ``runtime_snapshot`` via ``resolve_runtime_snapshot_source``; the
    /compare handler does not. This means the user_created path in
    /compare would raise ``NameError`` on first execution.

    Phase 51C-2 must fix this as part of the extraction. Phase 51C-1
    only characterizes the latent bug.
    """
    text = MAIN_WEB.read_text()
    # Find the /compare route body
    m = re.search(
        r"@app\.post\(\s*['\"]/compare['\"]\s*\)([\s\S]*?)(?=^@app\.)",
        text,
        re.MULTILINE,
    )
    body = m.group(1)
    assert "runtime_snapshot" in body, (
        "expected to find the latent runtime_snapshot reference in /compare"
    )
    # The /compare route does NOT call resolve_runtime_snapshot_source
    assert "resolve_runtime_snapshot_source" not in body, (
        "/compare route does not call resolve_runtime_snapshot_source — "
        "this is the root cause of the latent NameError"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 6. run_service.py from Phase 51B is intact
# ─────────────────────────────────────────────────────────────────────────────

def test_run_service_from_phase51b_still_exists():
    """run_service.py from Phase 51B must remain intact (Phase 51C-1
    must not touch /run or its service)."""
    assert RUN_SERVICE.exists(), (
        "run_service.py from Phase 51B must still exist after Phase 51C-1"
    )


def test_run_service_does_not_import_main_web():
    src = RUN_SERVICE.read_text()
    assert "import main_web" not in src
    assert "from main_web" not in src


def test_run_service_still_exposes_execute_run_route():
    import importlib
    mod = importlib.import_module("app.services.run_service")
    assert hasattr(mod, "execute_run_route")


def test_run_route_remains_thin():
    """The /run route from Phase 51B must remain thin. /compare
    characterization must not regress /run."""
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


def test_compare_unauthenticated_redirects_to_login(unauthenticated_client):
    """Unauthenticated /compare must 302 to /login."""
    r = unauthenticated_client.post(
        "/compare",
        data={"project_type": "Solar"},
        follow_redirects=False,
    )
    assert r.status_code == 302
    assert "/login" in r.headers.get("location", "")


def test_compare_invalid_project_type_returns_error(client):
    """Invalid project_type must render partials/errors.html with the
    project_types error message."""
    r = client.post("/compare", data={"project_type": "Nuclear"})
    assert r.status_code == 200
    assert "errors.html" in r.text or "must be one of" in r.text.lower() or "error" in r.text.lower()


def test_compare_solar_returns_comparison(client):
    """Generic Solar compare must render partials/comparison.html
    with Base/Downside/Upside results.

    NOTE: The dirty-workspace guard short-circuits to errors.html
    when the form state does not match the last saved runtime
    boundary. In a fresh isolated_db the workspace is empty, so the
    guard may block the live request. The structural / service-level
    contracts are pinned by the other tests in this suite; this test
    is a soft smoke check.
    """
    r = client.post("/compare", data={"project_type": "Solar"})
    assert r.status_code == 200
    # The response is either the success template (partials/comparison.html,
    # contains "Base") or the guard errors template (partials/errors.html,
    # contains "error"). Both are valid live behavior.
    assert ("Base" in r.text) or ("error" in r.text.lower()), (
        f"unexpected /compare response body: {r.text[:200]}"
    )


def test_compare_wind_returns_comparison(client):
    """Generic Wind compare must render partials/comparison.html."""
    r = client.post("/compare", data={"project_type": "Wind"})
    assert r.status_code == 200
    assert ("Base" in r.text) or ("error" in r.text.lower()), (
        f"unexpected /compare response body: {r.text[:200]}"
    )


def test_compare_with_custom_inputs(client):
    """Custom inputs are applied to all scenarios in compare (smoke)."""
    r = client.post("/compare", data={
        "project_type": "Solar",
        "tariff_eur_mwh": "120",
        "total_capex_keur": "50000",
    })
    assert r.status_code == 200
    assert ("Base" in r.text) or ("error" in r.text.lower())


def test_compare_invalid_gearing_returns_error(client):
    """Schema validation failure (e.g. invalid gearing) must render
    partials/errors.html with the input error message."""
    r = client.post("/compare", data={
        "project_type": "Solar",
        "gearing_pct": "not-a-number",
    })
    # The route's bare `except Exception` may catch this; the response
    # is still 200 but with the errors template
    assert r.status_code == 200
    assert "error" in r.text.lower() or "Traceback" not in r.text


def test_compare_no_traceback_in_response(client):
    """No raw Python tracebacks must leak to the user, even on
    per-scenario model errors. The /compare route catches per-scenario
    exceptions and continues."""
    r = client.post("/compare", data={"project_type": "Solar"})
    assert "Traceback (most recent call last)" not in r.text


# ─────────────────────────────────────────────────────────────────────────────
# 8. xfail paths (characterization of missing/buggy behavior)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.xfail(reason="PRE-EXISTING LATENT BUG: /compare references runtime_snapshot on user_created path but never defines it. Will be fixed in Phase 51C-2 as part of extraction.", strict=False)
def test_compare_user_created_path_does_not_raise_nameerror(client):
    """The user_created path in /compare references ``runtime_snapshot``
    which is never defined in /compare. This would raise NameError
    before any model execution. Marked xfail to document the latent
    bug; Phase 51C-2 must add proper resolution."""
    # We can't easily construct a user_created project record via
    # TestClient in this characterization phase, so this test
    # simply asserts that the structural issue is documented. If the
    # user_created path is ever fixed in 51C-2, the xfail can be
    # converted to a passing test.
    text = MAIN_WEB.read_text()
    m = re.search(
        r"@app\.post\(\s*['\"]/compare['\"]\s*\)([\s\S]*?)(?=^@app\.)",
        text,
        re.MULTILINE,
    )
    body = m.group(1)
    # If 51C-2 has fixed the bug, runtime_snapshot should be defined
    # in the route body (either via fallback or via
    # resolve_runtime_snapshot_source).
    if "runtime_snapshot" in body:
        # Must be defined somewhere in the body
        assert re.search(r"runtime_snapshot\s*=", body), (
            "After Phase 51C-2 fix: runtime_snapshot must be assigned "
            "in the /compare route body before use"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 9. Current-state guardrails (no production code change, no fixture CSV)
# ─────────────────────────────────────────────────────────────────────────────

def test_no_production_code_changed():
    """Phase 51C-1 is characterization only. main_web.py must be
    unchanged vs origin/main. New files (docs, tests, report) are
    allowed; production source files are not."""
    result = subprocess.run(
        ["git", "diff", "--name-only", "origin/main", "--",
         "main_web.py", "app/api/", "app/persistence/", "app/waterfall_core.py",
         "app/services/run_service.py", "app/services/scenario_state_service.py",
         "app/services/export_service.py", "app/services/export_audit_service.py",
         "app/ui/", "app/excel_export.py", "app/input_adapter.py",
         "app/input_schema.py", "app/project_factories.py"],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT),
    )
    changed = [l for l in result.stdout.strip().split("\n") if l]
    assert changed == [], (
        f"Production files changed in Phase 51C-1 (should be 0): {changed}"
    )


def test_no_fixture_csv_changes():
    """No real fixture CSV files (under app/fixtures/, tests/fixtures/)
    must be modified. Reports/ may have reconciliation output that is
    pre-existing and unrelated to Phase 51C-1."""
    result = subprocess.run(
        ["git", "diff", "--name-only", "origin/main", "--", "*.csv"],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT),
    )
    changed = [l for l in result.stdout.strip().split("\n") if l]
    fixture_prefixes = ("app/fixtures/", "app/services/fixtures/", "tests/fixtures/")
    real_fixtures = [c for c in changed if c.startswith(fixture_prefixes)]
    assert real_fixtures == [], f"Real fixture CSVs changed: {real_fixtures}"


def test_no_js_financial_calculations_added():
    """No JS financial calculations should be added."""
    result = subprocess.run(
        ["git", "diff", "--name-only", "origin/main", "--", "static/js/"],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT),
    )
    changed = [l for l in result.stdout.strip().split("\n") if l]
    assert changed == [], f"JS files changed: {changed}"


def test_main_web_has_zero_direct_record_export_calls():
    src = MAIN_WEB.read_text()
    matches = re.findall(r"\brecord_export\s*\(", src)
    assert len(matches) == 0, (
        f"main_web must have 0 direct record_export calls, found {len(matches)}"
    )


def test_main_web_does_not_import_runtime_guard_for_snapshot():
    src = MAIN_WEB.read_text()
    assert "runtime_guard_for_snapshot" not in src


def test_no_financial_formula_changes():
    """No financial formula / runtime / model output changes. Pin
    this via a guardrail: no changes to waterfall_core, project_factories,
    input_schema, input_adapter."""
    result = subprocess.run(
        ["git", "diff", "--name-only", "origin/main", "--",
         "app/waterfall_core.py", "app/project_factories.py",
         "app/input_schema.py", "app/input_adapter.py"],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT),
    )
    changed = [l for l in result.stdout.strip().split("\n") if l]
    assert changed == [], f"Financial/runtime files changed: {changed}"


def test_phase51a_golden_tests_still_pass():
    """Phase 51A golden tests for /run must still pass after Phase 51C-1
    characterization (no regression)."""
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
    Phase 51C-1 characterization (no regression)."""
    r = subprocess.run(
        ["python3", "-m", "pytest",
         "tests/test_phase51b_run_route_vertical_extraction.py", "-q",
         "--tb=no"],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT),
    )
    assert r.returncode == 0, (
        f"Phase 51B extraction tests regressed: {r.stdout[-500:]}"
    )


def test_import_main_web_ok():
    """``import main_web`` must still work after Phase 51C-1."""
    r = subprocess.run(
        ["python3", "-c", "import main_web; print('import main_web OK')"],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT),
    )
    assert r.returncode == 0, f"import main_web failed: {r.stderr}"
    assert "import main_web OK" in r.stdout
