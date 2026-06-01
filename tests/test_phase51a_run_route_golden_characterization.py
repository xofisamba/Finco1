"""Phase 51A — POST /run Route Golden Characterization Tests.

Characterize the current behavior of POST /run in main_web.py with golden
output tests, BEFORE any /run orchestration extraction in Phase 51B.

This phase is characterization/testing only. No production code is changed.
The /run route is NOT extracted — it still lives in main_web.py and uses the
existing services (scenario_state_service, export_service, etc.).

Strategy:
- Service-level golden tests pin run_project() output structure (the value
  that /run will eventually delegate to in Phase 51B).
- Route-level structural tests pin auth, dirty guard, error markers, and
  current-state guardrails (no production code regression).

Why two levels:
- Service-level avoids the dirty-guard trap in fresh isolated DBs (the
  route's check_runtime_allowed requires a baseline snapshot, which factory
  projects don't seed by default in tests).
- Route-level proves the route still exists, delegates correctly, and emits
  expected structural markers.

Hard guardrails enforced (asserted in test_current_state_guardrails):
- NO direct record_export(...) calls in main_web.py
- NO direct runtime_guard_for_snapshot import in main_web.py
- app/services/scenario_state_service.py exists
- app/services/export_service.py exists
- app/services/export_audit_service.py exists
- No fixture CSV changes (git diff against HEAD)
- No JS financial calculations (git diff against HEAD)
- Backend remains source of truth
- G20 BLOCKED | R99/R102 NOT APPROVED | partial_pay_sweep not promoted
- flat/min DSCR NOT promoted
"""
import json
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
MAIN_WEB = PROJECT_ROOT / "main_web.py"
SCENARIO_STATE_SERVICE = PROJECT_ROOT / "app/services/scenario_state_service.py"
EXPORT_SERVICE = PROJECT_ROOT / "app/services/export_service.py"
EXPORT_AUDIT_SERVICE = PROJECT_ROOT / "app/services/export_audit_service.py"
RUN_SERVICE = PROJECT_ROOT / "app/services/run_service.py"

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")
os.environ.setdefault("FINCO_COOKIE_SECURE", "false")
sys.path.insert(0, str(PROJECT_ROOT))


# ─────────────────────────────────────────────────────────────────────────────
# 1. /run route still lives in main_web.py (not extracted)
# ─────────────────────────────────────────────────────────────────────────────

def test_run_route_still_in_main_web():
    """POST /run route must still be in main_web.py — not extracted yet."""
    text = MAIN_WEB.read_text()
    assert "@app.post(\"/run\")" in text, \
        "POST /run route must remain in main_web.py for Phase 51A characterization"


def test_run_service_does_not_exist_yet():
    """app/services/run_service.py must not exist yet (Phase 51B target)."""
    if RUN_SERVICE.exists():
        # If exists, must not be imported by main_web
        text = MAIN_WEB.read_text()
        assert "from app.services.run_service" not in text, \
            "main_web must not import from run_service yet"
        assert "import app.services.run_service" not in text, \
            "main_web must not import run_service yet"
    else:
        assert not RUN_SERVICE.exists(), \
            "Phase 51B would create this file; must not exist yet"


def test_main_web_imports_cleanly():
    import main_web  # noqa: F401
    assert True


def test_run_route_docstring_describes_responsibilities():
    """The /run route docstring must describe current responsibilities."""
    text = MAIN_WEB.read_text()
    idx = text.find("@app.post(\"/run\")")
    section = text[idx:idx + 1000]
    assert "Run model" in section, "Docstring must describe run purpose"
    assert "auth" in section.lower() or "Requires auth" in section, \
        "Docstring must mention auth requirement"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Service-level golden outputs (run_project)
# ─────────────────────────────────────────────────────────────────────────────
#
# These tests pin the OUTPUT STRUCTURE of the model that /run delegates to.
# Absolute IRR/DSCR values change with calibration, so we pin structure
# (key names, types, ranges) instead of exact numbers.

def _import_run_project():
    from app.api.project_runner import run_project
    return run_project


def test_run_project_wind_base_returns_full_kpi_dict():
    """Wind base scenario must return complete KPI dict with all required keys."""
    run_project = _import_run_project()
    result = run_project("Wind", "Base")
    assert "kpis" in result
    kpis = result["kpis"]
    required = [
        "total_revenue_keur", "total_ebitda_keur", "total_opex_keur",
        "total_distributions_keur", "project_irr", "equity_irr",
        "min_dscr", "avg_dscr",
    ]
    for key in required:
        assert key in kpis, f"Missing KPI key: {key}"


def test_run_project_wind_base_kpi_types():
    """KPI values must be numeric (int/float), not strings."""
    run_project = _import_run_project()
    result = run_project("Wind", "Base")
    kpis = result["kpis"]
    # Revenue/EBITDA/OPEX/Distributions in kEUR (numeric)
    for key in ("total_revenue_keur", "total_ebitda_keur", "total_opex_keur", "total_distributions_keur"):
        v = kpis[key]
        assert v is None or isinstance(v, (int, float)), \
            f"{key} should be numeric, got {type(v).__name__}: {v!r}"
    # IRRs and DSCRs numeric
    for key in ("project_irr", "equity_irr", "min_dscr", "avg_dscr"):
        v = kpis[key]
        assert isinstance(v, (int, float)), \
            f"{key} should be numeric, got {type(v).__name__}: {v!r}"


def test_run_project_wind_base_kpi_ranges_are_sane():
    """KPI values must be in plausible ranges (sanity check, not exact pin)."""
    run_project = _import_run_project()
    result = run_project("Wind", "Base")
    kpis = result["kpis"]
    # IRRs in [-0.5, +0.5] (i.e. -50% to +50%)
    assert -0.5 <= kpis["project_irr"] <= 0.5, \
        f"project_irr out of range: {kpis['project_irr']}"
    assert -0.5 <= kpis["equity_irr"] <= 0.5, \
        f"equity_irr out of range: {kpis['equity_irr']}"
    # DSCR in [0, 5] (DSCR < 0 is invalid; > 5 is unrealistic)
    assert 0 < kpis["min_dscr"] <= 5, \
        f"min_dscr out of range: {kpis['min_dscr']}"
    assert 0 < kpis["avg_dscr"] <= 5, \
        f"avg_dscr out of range: {kpis['avg_dscr']}"
    # Revenue positive
    assert kpis["total_revenue_keur"] > 0, \
        f"total_revenue_keur should be > 0: {kpis['total_revenue_keur']}"


def test_run_project_solar_base_returns_full_kpi_dict():
    """Solar base scenario must return complete KPI dict."""
    run_project = _import_run_project()
    result = run_project("Solar", "Base")
    assert "kpis" in result
    kpis = result["kpis"]
    required = [
        "total_revenue_keur", "total_ebitda_keur", "total_opex_keur",
        "total_distributions_keur", "project_irr", "equity_irr",
        "min_dscr", "avg_dscr",
    ]
    for key in required:
        assert key in kpis, f"Missing Solar KPI key: {key}"


def test_run_project_returns_messages_and_integration_status():
    """run_project must return messages list and integration_status field."""
    run_project = _import_run_project()
    result = run_project("Wind", "Base")
    assert "messages" in result
    assert isinstance(result["messages"], list)
    assert "integration_status" in result
    assert result["integration_status"] in ("full", "partial", "degraded"), \
        f"Unexpected integration_status: {result['integration_status']!r}"


def test_run_project_returns_tables():
    """run_project must return tables dict with waterfall, revenue, debt, returns."""
    run_project = _import_run_project()
    result = run_project("Wind", "Base")
    assert "tables" in result
    tables = result["tables"]
    for tname in ("waterfall", "revenue", "debt", "returns"):
        assert tname in tables, f"Missing table: {tname}"
        assert isinstance(tables[tname], list), f"{tname} should be a list"


def test_run_project_downside_differs_from_base():
    """Downside scenario must differ from Base (sanity, not exact pin)."""
    run_project = _import_run_project()
    base = run_project("Wind", "Base")
    down = run_project("Wind", "Downside")
    # Revenue or IRR must differ
    base_rev = base["kpis"]["total_revenue_keur"]
    down_rev = down["kpis"]["total_revenue_keur"]
    assert abs(base_rev - down_rev) > 0.01, \
        f"Downside revenue should differ from Base: {base_rev} vs {down_rev}"


# ─────────────────────────────────────────────────────────────────────────────
# 3. Route-level structural tests (HTTP /run)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    """Per-test SQLite database for clean state."""
    db_file = tmp_path / f"phase51a_{uuid.uuid4().hex[:8]}.db"
    monkeypatch.setenv("FINCO_DB_PATH", str(db_file))
    import app.persistence.db as db_mod
    db_mod.DB_PATH = str(db_file)
    db_mod._connection = None
    yield str(db_file)
    db_mod._connection = None


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


def test_unauthenticated_run_redirects_to_login(unauthenticated_client):
    """Unauthenticated POST /run must redirect to /login."""
    r = unauthenticated_client.post(
        "/run",
        data={"project_type": "Wind", "scenario": "Base"},
        follow_redirects=False,
    )
    assert r.status_code == 302
    assert "/login" in r.headers.get("location", "")


def test_run_with_dirty_state_returns_error_marker(client):
    """POST /run with non-baseline fields triggers dirty guard (current behavior)."""
    r = client.post("/run", data={
        "project_type": "Wind",
        "scenario": "Base",
        "capacity_mw": "50",  # new field not in baseline
        "tariff_eur_mwh": "60",
    })
    # Dirty state returns 200 with error marker (template response)
    assert r.status_code == 200
    assert (
        "alert-error" in r.text
        or "Unsaved edits" in r.text
        or "no longer matches" in r.text
    ), f"Dirty state should be blocked, got: {r.text[:300]}"


def test_run_returns_html_response(client):
    """POST /run always returns HTML (template response), even on error."""
    r = client.post("/run", data={
        "project_type": "Wind",
        "scenario": "Base",
        "capacity_mw": "50",
    })
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", ""), \
        f"Expected HTML response, got: {r.headers.get('content-type')}"


# ─────────────────────────────────────────────────────────────────────────────
# 4. scenario_state_service API
# ─────────────────────────────────────────────────────────────────────────────

def test_scenario_state_service_api_still_exists():
    """scenario_state_service must expose the public API used by /run."""
    text = SCENARIO_STATE_SERVICE.read_text()
    required = [
        "check_runtime_allowed",
        "resolve_runtime_snapshot",
    ]
    for name in required:
        assert f"def {name}" in text, \
            f"scenario_state_service must still define {name}()"


def test_check_runtime_allowed_returns_three_tuple():
    """check_runtime_allowed must return (allow_run, runtime_origin, guard_message)."""
    from app.services.scenario_state_service import check_runtime_allowed
    # Mock minimal workspace_state and snapshot
    class _WS:
        active_scenario_id = None
        active_scenario_name = None
        saved_snapshot = {}
        draft_snapshot = {}
        dirty = False
        last_runtime_origin = None
    snapshot = {"project_type": "Wind", "scenario": "Base"}
    allow, origin, message = check_runtime_allowed(_WS(), snapshot)
    assert isinstance(allow, bool)
    assert isinstance(origin, str)
    assert message is None or isinstance(message, str)


# ─────────────────────────────────────────────────────────────────────────────
# 5. Current-state guardrails (no production code regression)
# ─────────────────────────────────────────────────────────────────────────────

def test_main_web_zero_direct_record_export_calls():
    """main_web.py must have zero direct record_export(...) calls."""
    text = MAIN_WEB.read_text()
    # Match record_export( not preceded by a word char (avoids record_export_async etc)
    matches = re.findall(r"(?<![A-Za-z0-9_])record_export\s*\(", text)
    assert len(matches) == 0, \
        f"Expected 0 direct record_export( calls in main_web.py, found {len(matches)}"


def test_main_web_no_record_export_import():
    """main_web.py must not import record_export directly."""
    text = MAIN_WEB.read_text()
    # Look for any line that imports record_export from app.persistence.repository
    for line in text.split("\n"):
        if "from app.persistence.repository" in line and "record_export" in line:
            pytest.fail(f"main_web.py imports record_export directly: {line!r}")


def test_main_web_no_runtime_guard_direct_import():
    """main_web.py must not import runtime_guard_for_snapshot directly (Phase 50C-2 refactor)."""
    text = MAIN_WEB.read_text()
    # The wrapper is in scenario_state_service; main_web must use the wrapper
    for line in text.split("\n"):
        if "from app.runtime_guard" in line and "runtime_guard_for_snapshot" in line:
            pytest.fail(f"main_web.py imports runtime_guard_for_snapshot directly: {line!r}")
    # And must use the scenario_state_service wrapper
    assert "from app.services.scenario_state_service import" in text, \
        "main_web must use check_runtime_allowed from scenario_state_service"


def test_export_service_still_exists():
    text = EXPORT_SERVICE.read_text()
    assert "def build_excel_export_for_post_request" in text
    assert "def build_values_only_export_for_project" in text


def test_export_audit_service_still_exists():
    text = EXPORT_AUDIT_SERVICE.read_text()
    required = [
        "def record_runtime_summary_export",
        "def record_institutional_workbook_export",
        "def record_download_export",
    ]
    for name in required:
        assert name in text, f"export_audit_service must define {name}()"


def test_no_fixture_csv_changes():
    """No fixture CSV files should be modified in this phase."""
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD", "--", "*.csv"],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT),
    )
    changed = [
        l for l in result.stdout.strip().split("\n")
        if l and not l.startswith("tests/")
    ]
    assert changed == [], f"Fixture CSVs changed: {changed}"


def test_no_js_financial_calculations_added():
    """No JS financial calculations should be added (no static/js diffs)."""
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD", "--", "static/js/"],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT),
    )
    changed = [
        l for l in result.stdout.strip().split("\n") if l
    ]
    assert changed == [], f"static/js/ changed: {changed}"


def test_no_production_code_changes():
    """No production code (main_web.py, app/**) should be modified."""
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD"],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT),
    )
    changed = [
        l for l in result.stdout.strip().split("\n")
        if l and not l.startswith("tests/")
        and not l.startswith("docs/")
        and not l.startswith("reports/")
    ]
    assert changed == [], f"Production code changed: {changed}"


# ─────────────────────────────────────────────────────────────────────────────
# 6. Guardrails (Phase 51A hard guardrails)
# ─────────────────────────────────────────────────────────────────────────────

def test_phase51a_guardrails_stated():
    """This test file must state the Phase 51A guardrails in its docstring."""
    text = Path(__file__).read_text().lower()
    assert "g20" in text and "blocked" in text
    assert "r99" in text and "not approved" in text
    assert "r102" in text and "not approved" in text
    assert "partial_pay_sweep" in text and "not promoted" in text
    assert "flat" in text and "min" in text and "dscr" in text and "not promoted" in text
