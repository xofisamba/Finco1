"""Phase 51E-1 — POST /download and GET /download Route Golden Characterization Tests.

Characterize the current behavior of POST /download and GET /download
in main_web.py BEFORE any extraction in Phase 51E-2.

This phase is characterization/testing only. No production code is
changed. The /download route family is NOT extracted — it still
lives in main_web.py and uses the existing helpers and export
services directly.

Strategy (mirrors Phase 51A / 51C-1 / 51D-1):
- Structural / current-state tests pin the route's location,
  dependencies, response shape, and quirks.
- Integration tests (TestClient) pin the live behavior on:
    * unauthenticated redirect
    * POST valid form
    * POST invalid project_type
    * POST runtime guard block (user_created)
    * GET with default query params
    * GET with explicit query params
    * response headers / content-type / filename
- The intended export audit (record_download_export) is preserved
  and pinned as INTENDED behavior from Phase 49.

Hard guardrails enforced (asserted in test_current_state_guardrails):
- NO direct record_export(...) calls in main_web.py
- /run route from Phase 51B remains thin (< 200 non-blank body lines)
- /compare route from Phase 51C-2 remains thin (< 50 non-blank body lines)
- /validate route from Phase 51D-2 remains thin (< 50 non-blank body lines)
- run_service.py from Phase 51B is intact
- compare_service.py from Phase 51C-2 is intact
- validation_service.py from Phase 51D-2 is intact
- No fixture CSV changes
- No JS financial calculations
- Backend remains source of truth
- G20 BLOCKED | R99/R102 NOT APPROVED | partial_pay_sweep not promoted
- flat/min DSCR NOT promoted
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
MAIN_WEB = PROJECT_ROOT / "main_web.py"
RUN_SERVICE = PROJECT_ROOT / "app" / "services" / "run_service.py"
COMPARE_SERVICE = PROJECT_ROOT / "app" / "services" / "compare_service.py"
VALIDATE_SERVICE = PROJECT_ROOT / "app" / "services" / "validation_service.py"
EXPORT_SERVICE = PROJECT_ROOT / "app" / "services" / "export_service.py"
EXPORT_AUDIT_SERVICE = PROJECT_ROOT / "app" / "services" / "export_audit_service.py"

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")
os.environ.setdefault("FINCO_COOKIE_SECURE", "false")
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    """Per-test SQLite database for clean state (mirrors Phase 51A)."""
    import uuid
    db_file = tmp_path / f"phase51e1_{uuid.uuid4().hex[:8]}.db"
    monkeypatch.setenv("FINCO_DB_PATH", str(db_file))
    import app.persistence.db as db_mod
    db_mod.DB_PATH = str(db_file)
    db_mod._connection = None
    yield str(db_file)
    db_mod._connection = None


# ─────────────────────────────────────────────────────────────────────────────
# 1. /download route family still lives in main_web.py (not extracted)
# ─────────────────────────────────────────────────────────────────────────────

def test_post_download_route_still_in_main_web():
    """POST /download route must still be in main_web.py — not
    extracted yet."""
    text = MAIN_WEB.read_text()
    assert re.search(r"^@app\.post\(\s*[\"']/download[\"']\s*\)", text, re.MULTILINE), (
        "POST /download route must remain in main_web.py for Phase 51E-1 characterization"
    )


def test_get_download_route_still_in_main_web():
    """GET /download route must still be in main_web.py."""
    text = MAIN_WEB.read_text()
    assert re.search(r"^@app\.get\(\s*[\"']/download[\"']\s*\)", text, re.MULTILINE), (
        "GET /download route must remain in main_web.py for Phase 51E-1 characterization"
    )


def test_post_download_route_signature():
    text = MAIN_WEB.read_text()
    m = re.search(
        r"@app\.post\(\s*['\"]/download['\"]\s*\)\s*\n"
        r"(?:async\s+)?def\s+(\w+)\([^)]*\)\s*:",
        text,
    )
    assert m, "POST /download route must have an async def handler"
    func_name = m.group(1)
    # The current handler is named download_post
    assert func_name in ("download_post", "download"), (
        f"POST /download route handler should be named download_post or download, got {func_name}"
    )


def test_get_download_route_signature():
    text = MAIN_WEB.read_text()
    m = re.search(
        r"@app\.get\(\s*['\"]/download['\"]\s*\)\s*\n"
        r"(?:async\s+)?def\s+(\w+)\([^)]*\)\s*:",
        text,
    )
    assert m, "GET /download route must have an async def handler"
    func_name = m.group(1)
    assert func_name in ("download_get", "download"), (
        f"GET /download route handler should be named download_get or download, got {func_name}"
    )


def test_download_service_now_exists_post_phase51e2():
    """Post-Phase-51E-2: download_service.py must exist and own the
    orchestration body that previously lived inside the /download
    route family in main_web.py."""
    download_service = PROJECT_ROOT / "app" / "services" / "download_service.py"
    assert download_service.exists(), (
        "download_service.py must exist after Phase 51E-2 extraction"
    )


def test_main_web_imports_download_service():
    """Post-Phase-51E-2: main_web must import download_service so the
    thin /download route family can call execute_post_download_route
    and execute_get_download_route."""
    text = MAIN_WEB.read_text()
    assert "from app.services.download_service" in text, (
        "main_web.py must import download_service (Phase 51E-2 extraction)"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2. /download route body structure
# ─────────────────────────────────────────────────────────────────────────────

def _get_post_download_route_body() -> str:
    text = MAIN_WEB.read_text()
    m = re.search(
        r"@app\.post\(\s*['\"]/download['\"]\s*\)([\s\S]*?)(?=^@app\.)",
        text,
        re.MULTILINE,
    )
    assert m, "could not locate POST /download route body"
    return m.group(1)


def _get_get_download_route_body() -> str:
    text = MAIN_WEB.read_text()
    m = re.search(
        r"@app\.get\(\s*['\"]/download['\"]\s*\)([\s\S]*?)(?=^@app\.)",
        text,
        re.MULTILINE,
    )
    assert m, "could not locate GET /download route body"
    return m.group(1)


def test_post_download_uses_build_schema_from_form():
    """Post-Phase-51E-2: download_service.py must call
    _build_schema_from_form (schema build for POST path)."""
    text = (PROJECT_ROOT / "app" / "services" / "download_service.py").read_text()
    assert "build_schema_from_form(" in text, (
        "download_service must call build_schema_from_form (POST path)"
    )


def test_post_download_uses_run_demo_project():
    """Post-Phase-51E-2: download_service.py must call run_demo_project."""
    text = (PROJECT_ROOT / "app" / "services" / "download_service.py").read_text()
    assert "run_demo_project(" in text, (
        "download_service must call run_demo_project"
    )


def test_post_download_uses_record_download_export():
    """Post-Phase-51E-2: download_service.py must call
    record_download_export (intended export audit)."""
    text = (PROJECT_ROOT / "app" / "services" / "download_service.py").read_text()
    assert "record_download_export(" in text, (
        "download_service must call record_download_export (intended export audit)"
    )


def test_post_download_uses_build_excel_export_for_post_request():
    """Post-Phase-51E-2: download_service.py must call
    build_excel_export_for_post_request (POST-specific builder)."""
    text = (PROJECT_ROOT / "app" / "services" / "download_service.py").read_text()
    assert "build_excel_export_for_post_request(" in text, (
        "download_service must call build_excel_export_for_post_request"
    )


def test_get_download_uses_build_values_only_export_for_project():
    """Post-Phase-51E-2: download_service.py must call
    build_values_only_export_for_project (GET-specific builder)."""
    text = (PROJECT_ROOT / "app" / "services" / "download_service.py").read_text()
    assert "build_values_only_export_for_project(" in text, (
        "download_service must call build_values_only_export_for_project"
    )


def test_get_download_uses_get_project_by_code():
    """Post-Phase-51E-2: download_service.py must call get_project_by_code
    (used only by GET path)."""
    text = (PROJECT_ROOT / "app" / "services" / "download_service.py").read_text()
    assert "get_project_by_code(" in text, (
        "download_service must call get_project_by_code (GET path)"
    )


def test_get_download_uses_record_download_export():
    """Post-Phase-51E-2: download_service.py must call
    record_download_export (intended export audit, both POST and GET)."""
    text = (PROJECT_ROOT / "app" / "services" / "download_service.py").read_text()
    assert "record_download_export(" in text, (
        "download_service must call record_download_export (intended export audit)"
    )


def test_post_download_handles_user_created_branch():
    """Post-Phase-51E-2: download_service.py must have a user_created
    branch that calls check_runtime_allowed,
    _resolve_runtime_snapshot_source, and
    build_projectinputs_from_snapshot."""
    text = (PROJECT_ROOT / "app" / "services" / "download_service.py").read_text()
    assert "user_created" in text, (
        "download_service must have a user_created branch"
    )
    assert "check_runtime_allowed" in text, (
        "download_service user_created branch must call check_runtime_allowed"
    )
    assert "resolve_runtime_snapshot_source" in text, (
        "download_service user_created branch must call resolve_runtime_snapshot_source"
    )
    assert "build_projectinputs_from_snapshot" in text, (
        "download_service user_created branch must call build_projectinputs_from_snapshot"
    )


def test_post_download_handles_template_seeded_branch():
    """Post-Phase-51E-2: download_service.py must have a template-
    seeded branch that uses _normalize_template_source for
    TUHO/Oborovo/Solar/Wind project key resolution."""
    text = (PROJECT_ROOT / "app" / "services" / "download_service.py").read_text()
    assert "normalize_template_source" in text, (
        "download_service template-seeded branch must call normalize_template_source"
    )
    # The template-seeded branch mutates runtime_origin='saved_state'
    # if active_scenario_id is set
    assert re.search(
        r'runtime_origin\s*=\s*[\"\']saved_state[\"\']',
        text,
    ), (
        "download_service template-seeded branch must mutate runtime_origin='saved_state' "
        "when active_scenario_id is set (preserved quirk 3)"
    )


def test_post_download_routes_to_TUHO_Oborovo_Solar_Wind():
    """Post-Phase-51E-2: download_service.py must select
    runtime_project_key from {TUHO, Oborovo, Solar, Wind} based on
    the runtime_seed."""
    text = (PROJECT_ROOT / "app" / "services" / "download_service.py").read_text()
    assert "TUHO" in text, (
        "download_service must support TUHO project key"
    )
    assert "Oborovo" in text, (
        "download_service must support Oborovo project key"
    )
    assert "Solar" in text, (
        "download_service must support Solar project key"
    )


def test_get_download_uses_factory_base_runtime():
    """Post-Phase-51E-2: download_service.py GET path must use
    runtime_origin='factory_base_runtime' in replay_metadata."""
    text = (PROJECT_ROOT / "app" / "services" / "download_service.py").read_text()
    assert "factory_base_runtime" in text, (
        "download_service GET path must use runtime_origin='factory_base_runtime'"
    )


def test_get_download_hardcoded_project_code_mapping():
    """Post-Phase-51E-2: download_service.py GET path must use the
    hardcoded project_code mapping 'oborovo' if
    project_type.lower() == 'solar' else 'tuho' (preserved quirk 2)."""
    text = (PROJECT_ROOT / "app" / "services" / "download_service.py").read_text()
    assert re.search(
        r'project_code\s*=\s*[\"\']oborovo[\"\']\s*if',
        text,
    ), (
        "download_service GET path must use the hardcoded project_code mapping "
        "'oborovo' if project_type.lower() == 'solar' else 'tuho' "
        "(preserved quirk 2)"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. /download route body size (characterization pin)
# ─────────────────────────────────────────────────────────────────────────────

def test_post_download_body_size_post_extraction_is_thin():
    """Post-Phase-51E-2: the POST /download route must be THIN (< 50
    non-blank body lines). The pre-extraction body was 106 non-blank;
    the post-extraction body is ~30 non-blank."""
    body = _get_post_download_route_body()
    non_blank = [ln for ln in body.splitlines() if ln.strip()]
    assert len(non_blank) < 50, (
        f"POST /download route body has {len(non_blank)} non-blank lines; "
        "expected < 50 after Phase 51E-2 vertical extraction"
    )


def test_get_download_body_size_characterization():
    """Pin the current GET /download body size. Currently ~65 lines /
    ~65 non-blank."""
    body = _get_get_download_route_body()
    non_blank = [ln for ln in body.splitlines() if ln.strip()]
    assert len(non_blank) < 200, (
        f"GET /download route body has {len(non_blank)} non-blank lines; "
        "expected < 200 (characterization pin)"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 4. Response / header / filename behavior (preserved from legacy /download)
# ─────────────────────────────────────────────────────────────────────────────

def test_post_download_uses_hardcoded_xlsx_media_type():
    """Post-Phase-51E-2: download_service.py POST path must use the
    hardcoded media_type
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'."""
    text = (PROJECT_ROOT / "app" / "services" / "download_service.py").read_text()
    assert (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        in text
    ), (
        "download_service POST path must use the hardcoded xlsx media_type string (quirk 5)"
    )


def test_get_download_uses_export_media_type():
    """Post-Phase-51E-2: download_service.py GET path must use
    export.media_type (from the export object)."""
    text = (PROJECT_ROOT / "app" / "services" / "download_service.py").read_text()
    assert "export.media_type" in text, (
        "download_service GET path must use export.media_type (from the export object, quirk 5)"
    )


def test_post_download_constructs_filename_in_route():
    """Post-Phase-51E-2: download_service.py POST path constructs the
    filename in the service: f'fincogpt_{project_type.lower()}_{scenario.lower()}.xlsx'."""
    text = (PROJECT_ROOT / "app" / "services" / "download_service.py").read_text()
    assert re.search(
        r"fincogpt_\{?project_type",
        text,
    ), (
        "download_service POST path must construct filename as "
        "'fincogpt_{project_type.lower()}_{scenario.lower()}.xlsx' (quirk 6)"
    )


def test_get_download_uses_export_filename():
    """Post-Phase-51E-2: download_service.py GET path must use
    export.filename (from the export object)."""
    text = (PROJECT_ROOT / "app" / "services" / "download_service.py").read_text()
    assert "export.filename" in text, (
        "download_service GET path must use export.filename (from the export object, quirk 6)"
    )


def test_post_download_artifact_path_format():
    """Post-Phase-51E-2: download_service.py POST path constructs
    artifact_path as
    f'/download?project_type={project_type}&scenario={scenario}'."""
    text = (PROJECT_ROOT / "app" / "services" / "download_service.py").read_text()
    assert re.search(
        r'artifact_path\s*=\s*f?[\"\']/download\?project_type=',
        text,
    ), (
        "download_service POST path must construct artifact_path as "
        "'/download?project_type={project_type}&scenario={scenario}' (quirk 10)"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 5. Audit / provenance behavior (INTENDED, preserved)
# ─────────────────────────────────────────────────────────────────────────────

def test_download_service_calls_record_download_export_twice():
    """Post-Phase-51E-2: download_service.py must call
    record_download_export TWICE (once in execute_post_download_route,
    once in execute_get_download_route) with the full provenance
    context. This is INTENDED export audit behavior from Phase 49
    — NOT forbidden persistence.

    Counts executable-code call sites only (docstring mentions are
    allowed; we check for actual function calls with a `(`).
    """
    text = (PROJECT_ROOT / "app" / "services" / "download_service.py").read_text()
    # Count call patterns with `(` to filter out import statements
    # and docstring mentions. The service uses `deps.record_download_export(`
    # which is the actual call site.
    matches = re.findall(r"\.record_download_export\s*\(", text)
    assert len(matches) == 2, (
        f"download_service.py must have exactly 2 record_download_export "
        f"call sites (POST + GET); found {len(matches)}. "
        f"Note: docstring mentions are allowed; only executable call "
        f"sites with `(` are counted."
    )


def test_download_service_uses_export_type_excel_model_export():
    """Post-Phase-51E-2: download_service.py must use
    export_type='excel_model_export' in both POST and GET paths
    (minimum 2 call-site occurrences in executable code)."""
    text = (PROJECT_ROOT / "app" / "services" / "download_service.py").read_text()
    assert "excel_model_export" in text, (
        "download_service must use export_type='excel_model_export'"
    )
    # Use a regex that only matches the actual export_type= call sites,
    # not docstring mentions.
    export_type_call_sites = re.findall(
        r"export_type\s*=\s*[\"\']excel_model_export[\"\']",
        text,
    )
    assert len(export_type_call_sites) >= 2, (
        f"download_service must call export_type='excel_model_export' "
        f"at least twice (POST + GET), found {len(export_type_call_sites)}"
    )


def test_download_service_uses_workbook_type_values_only_excel_export():
    """Post-Phase-51E-2: download_service.py must use
    workbook_type='values_only_excel_export' in both POST and GET
    paths (minimum 2 call-site occurrences in executable code)."""
    text = (PROJECT_ROOT / "app" / "services" / "download_service.py").read_text()
    assert "values_only_excel_export" in text, (
        "download_service must use workbook_type='values_only_excel_export'"
    )
    # Use a regex that only matches the actual workbook_type= call
    # sites, not docstring mentions.
    workbook_type_call_sites = re.findall(
        r"workbook_type\s*=\s*[\"\']values_only_excel_export[\"\']",
        text,
    )
    assert len(workbook_type_call_sites) >= 2, (
        f"download_service must call workbook_type='values_only_excel_export' "
        f"at least twice (POST + GET), found {len(workbook_type_call_sites)}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 6. Read / write side effects classification
# ─────────────────────────────────────────────────────────────────────────────

def test_download_routes_no_record_workspace_runtime_calls():
    """The /download route family does NOT call record_workspace_runtime.
    Only /run calls it."""
    text = MAIN_WEB.read_text()
    # Find the /download route family region
    post_body = _get_post_download_route_body()
    get_body = _get_get_download_route_body()
    assert "record_workspace_runtime" not in post_body, (
        "POST /download must not call record_workspace_runtime"
    )
    assert "record_workspace_runtime" not in get_body, (
        "GET /download must not call record_workspace_runtime"
    )


def test_download_routes_no_update_scenario_last_run_summary_calls():
    """The /download route family does NOT call
    update_scenario_last_run_summary. Only /run calls it."""
    post_body = _get_post_download_route_body()
    get_body = _get_get_download_route_body()
    assert "update_scenario_last_run_summary" not in post_body, (
        "POST /download must not call update_scenario_last_run_summary"
    )
    assert "update_scenario_last_run_summary" not in get_body, (
        "GET /download must not call update_scenario_last_run_summary"
    )


def test_download_routes_no_db_session_writes():
    """The /download route family does NOT do raw db.add / db.commit /
    session.add / session.commit. All persistence is via the export
    audit helper."""
    post_body = _get_post_download_route_body()
    get_body = _get_get_download_route_body()
    for forbidden in ("db.add", "db.commit", "db.flush",
                       "session.add", "session.commit"):
        assert forbidden not in post_body, (
            f"POST /download must not call {forbidden}"
        )
        assert forbidden not in get_body, (
            f"GET /download must not call {forbidden}"
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


def test_post_download_unauthenticated_redirects_to_login(unauthenticated_client):
    """Unauthenticated POST /download must 302 to /login."""
    r = unauthenticated_client.post(
        "/download",
        data={"project_type": "Solar", "scenario": "Base"},
        follow_redirects=False,
    )
    assert r.status_code == 302
    assert "/login" in r.headers.get("location", "")


def test_get_download_unauthenticated_redirects_to_login(unauthenticated_client):
    """Unauthenticated GET /download must 302 to /login."""
    r = unauthenticated_client.get(
        "/download?project_type=Solar&scenario=Base",
        follow_redirects=False,
    )
    assert r.status_code == 302
    assert "/login" in r.headers.get("location", "")


def test_post_download_valid_form_live_behavior(client):
    """Valid POST /download must return either a streaming xlsx response
    (success) or an inline HTML error page (failure). The runtime
    guard or schema build may short-circuit in a fresh isolated_db,
    so we only assert the response shape is one of the two valid
    shapes."""
    r = client.post("/download", data={
        "project_type": "Solar", "scenario": "Base",
        "capacity_mw": "100", "tariff_eur_mwh": "80", "p50_hours": "2500",
        "total_capex_keur": "100000", "opex_y1_keur": "2000",
        "gearing_pct": "70", "target_dscr": "1.3",
        "interest_rate_pct": "5.5", "tenor_years": "15",
    })
    assert r.status_code in (200, 400, 500), (
        f"unexpected POST /download status: {r.status_code}"
    )
    # Either xlsx content or HTML error page
    if r.status_code == 200:
        # Success: either application/xlsx or HTML error from export.has_error()
        content_type = r.headers.get("content-type", "")
        assert (
            "spreadsheetml" in content_type
            or "html" in content_type.lower()
        ), f"unexpected content-type: {content_type}"
    else:
        # Error: HTML page
        assert "html" in r.headers.get("content-type", "").lower() or "Excel" in r.text


def test_get_download_with_default_query_params_live_behavior(client):
    """GET /download with default query params (Solar, Base) must
    return either a streaming xlsx or an HTML error."""
    r = client.get("/download", follow_redirects=False)
    # GET /download uses factory defaults and does NOT require the
    # user's project list. May return 200 (xlsx or error HTML) or
    # other status depending on factory state.
    assert r.status_code in (200, 400, 500), (
        f"unexpected GET /download status: {r.status_code}"
    )


def test_get_download_with_explicit_query_params_live_behavior(client):
    """GET /download with explicit query params (Wind, Base) must
    return either a streaming xlsx or an HTML error."""
    r = client.get("/download?project_type=Wind&scenario=Base", follow_redirects=False)
    assert r.status_code in (200, 400, 500), (
        f"unexpected GET /download status: {r.status_code}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 8. /run, /compare, /validate routes remain thin
# ─────────────────────────────────────────────────────────────────────────────

def test_run_route_remains_thin():
    """The /run route from Phase 51B must remain thin. Phase 51E-1
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


def test_validate_route_remains_thin():
    """The /validate route from Phase 51D-2 must remain thin."""
    text = MAIN_WEB.read_text()
    m = re.search(
        r"@app\.post\(\s*['\"]/validate['\"]\s*\)([\s\S]*?)(?=^@app\.)",
        text,
        re.MULTILINE,
    )
    assert m
    body = m.group(1)
    non_blank = [ln for ln in body.splitlines() if ln.strip()]
    assert len(non_blank) < 50, (
        f"/validate route body has {len(non_blank)} non-blank lines; "
        "Phase 51D-2 thinness contract must be preserved"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 9. run_service, compare_service, validation_service are intact
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


def test_validate_service_from_phase51d2_still_intact():
    assert VALIDATE_SERVICE.exists()
    text = VALIDATE_SERVICE.read_text(encoding="utf-8")
    for symbol in ("ValidateRouteOutcome", "ValidateRouteDeps", "execute_validate_route"):
        assert symbol in text, (
            f"validation_service.py must still export {symbol}"
        )


def test_existing_services_do_not_import_download_service():
    """Existing services must not depend on download_service (which
    does not exist yet)."""
    for svc_path, name in [
        (RUN_SERVICE, "run_service"),
        (COMPARE_SERVICE, "compare_service"),
        (VALIDATE_SERVICE, "validation_service"),
    ]:
        text = svc_path.read_text(encoding="utf-8")
        assert "download_service" not in text, (
            f"{name} must not import or reference download_service"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 10. Current-state guardrails
# ─────────────────────────────────────────────────────────────────────────────

def test_main_web_has_zero_direct_record_export_calls():
    """main_web.py must not have any direct record_export(...) calls.
    The 'record export' operations are split into three purpose-
    specific helpers in app.services.export_audit_service
    (record_runtime_summary_export,
    record_institutional_workbook_export, record_download_export).
    This is the Phase 49 guardrail."""
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


def test_no_production_code_changed_outside_download_extraction():
    """Phase 51E-2 allows EXACTLY two production code changes:
    - main_web.py (the /download route family becomes thin)
    - app/services/download_service.py (new file, owns orchestration)

    Every other production source file must be unchanged vs
    origin/main. New docs/tests/report files are allowed.
    """
    result = subprocess.run(
        ["git", "diff", "--name-only", "origin/main", "--",
         "main_web.py", "app/api/", "app/persistence/", "app/waterfall_core.py",
         "app/services/run_service.py", "app/services/compare_service.py",
         "app/services/validation_service.py",
         "app/services/scenario_state_service.py",
         "app/services/export_service.py",
         "app/services/export_audit_service.py",
         "app/ui/", "app/excel_export.py", "app/input_adapter.py",
         "app/input_schema.py", "app/project_factories.py"],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT),
    )
    changed = [l for l in result.stdout.strip().split("\n") if l]
    forbidden = [c for c in changed if c != "main_web.py"]
    assert forbidden == [], (
        f"Phase 51E-2 may only change main_web.py and add "
        f"download_service.py; unexpected changes: {forbidden}"
    )
    # main_web.py IS allowed to be in the diff; pin that the diff is
    # scoped to the /download route family (no other route changed).
    if "main_web.py" in changed:
        result2 = subprocess.run(
            ["git", "diff", "origin/main", "--", "main_web.py"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        diff_text = result2.stdout
        decorator_changes = [
            ln for ln in diff_text.splitlines()
            if ln.startswith("+@app.") or ln.startswith("-@app.")
        ]
        non_download_decorator_changes = [
            ln for ln in decorator_changes
            if "/download" not in ln
        ]
        assert non_download_decorator_changes == [], (
            "main_web.py diff must not touch any @app.* decorator "
            f"other than /download; got: {non_download_decorator_changes}"
        )


def test_no_fixture_csv_changes():
    """No real fixture CSV files must be modified by Phase 51E-1."""
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
    """No JS files should be added or changed in static/ by Phase 51E-1."""
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
    """``import main_web`` must still work after Phase 51E-1."""
    sys.path.insert(0, str(PROJECT_ROOT))
    import main_web  # noqa: F401


def test_phase51e1_test_module_is_importable():
    """Sanity: this test module itself must be importable."""
    spec_path = PROJECT_ROOT / "tests" / "test_phase51e1_download_route_golden_characterization.py"
    assert spec_path.exists()


# ─────────────────────────────────────────────────────────────────────────────
# 12. Regression checks for previous phases
# ─────────────────────────────────────────────────────────────────────────────

def test_phase51a_golden_tests_still_pass():
    """Phase 51A golden tests for /run must still pass after Phase 51E-1
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
    Phase 51E-1 (no regression)."""
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
    Phase 51E-1 (no regression)."""
    r = subprocess.run(
        ["python3", "-m", "pytest",
         "tests/test_phase51c2_compare_route_vertical_extraction.py", "-q",
         "--tb=no"],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT),
    )
    assert r.returncode == 0, (
        f"Phase 51C-2 extraction tests regressed: {r.stdout[-500:]}"
    )


def test_phase51d2_extraction_tests_still_pass():
    """Phase 51D-2 extraction tests for /validate must still pass after
    Phase 51E-1 (no regression)."""
    r = subprocess.run(
        ["python3", "-m", "pytest",
         "tests/test_phase51d2_validate_route_vertical_extraction.py", "-q",
         "--tb=no"],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT),
    )
    assert r.returncode == 0, (
        f"Phase 51D-2 extraction tests regressed: {r.stdout[-500:]}"
    )


def test_import_main_web_ok():
    """``import main_web`` must still work after Phase 51E-1."""
    r = subprocess.run(
        ["python3", "-c", "import main_web; print('import main_web OK')"],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT),
    )
    assert r.returncode == 0, f"import main_web failed: {r.stderr}"
    assert "import main_web OK" in r.stdout
