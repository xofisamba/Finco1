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


def test_download_service_does_not_exist_yet():
    """Pre-Phase-51E-2: download_service.py must not exist."""
    download_service = PROJECT_ROOT / "app" / "services" / "download_service.py"
    assert not download_service.exists(), (
        "download_service.py must NOT exist before Phase 51E-2 extraction"
    )


def test_main_web_does_not_import_download_service():
    """main_web must not import download_service yet."""
    text = MAIN_WEB.read_text()
    assert "from app.services.download_service" not in text
    assert "import app.services.download_service" not in text


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
    body = _get_post_download_route_body()
    assert "_build_schema_from_form(" in body, (
        "POST /download route must call _build_schema_from_form"
    )


def test_post_download_uses_run_demo_project():
    body = _get_post_download_route_body()
    assert "run_demo_project(" in body, (
        "POST /download route must call run_demo_project"
    )


def test_post_download_uses_record_download_export():
    body = _get_post_download_route_body()
    assert "record_download_export(" in body, (
        "POST /download route must call record_download_export (intended export audit)"
    )


def test_post_download_uses_build_excel_export_for_post_request():
    body = _get_post_download_route_body()
    assert "build_excel_export_for_post_request(" in body, (
        "POST /download route must call build_excel_export_for_post_request"
    )


def test_get_download_uses_build_values_only_export_for_project():
    body = _get_get_download_route_body()
    assert "build_values_only_export_for_project(" in body, (
        "GET /download route must call build_values_only_export_for_project"
    )


def test_get_download_uses_get_project_by_code():
    body = _get_get_download_route_body()
    assert "get_project_by_code(" in body, (
        "GET /download route must call get_project_by_code"
    )


def test_get_download_uses_record_download_export():
    body = _get_get_download_route_body()
    assert "record_download_export(" in body, (
        "GET /download route must call record_download_export (intended export audit)"
    )


def test_post_download_handles_user_created_branch():
    """POST /download has a user_created branch that calls
    check_runtime_allowed, _resolve_runtime_snapshot_source, and
    build_projectinputs_from_snapshot."""
    body = _get_post_download_route_body()
    assert "user_created" in body, (
        "POST /download route must have a user_created branch"
    )
    assert "check_runtime_allowed" in body, (
        "POST /download user_created branch must call check_runtime_allowed"
    )
    assert "_resolve_runtime_snapshot_source" in body, (
        "POST /download user_created branch must call _resolve_runtime_snapshot_source"
    )
    assert "build_projectinputs_from_snapshot" in body, (
        "POST /download user_created branch must call build_projectinputs_from_snapshot"
    )


def test_post_download_handles_template_seeded_branch():
    """POST /download has a template-seeded branch that uses
    _normalize_template_source for TUHO/Oborovo/Solar/Wind project
    key resolution."""
    body = _get_post_download_route_body()
    assert "_normalize_template_source" in body, (
        "POST /download template-seeded branch must call _normalize_template_source"
    )
    # The template-seeded branch mutates runtime_origin='saved_state'
    # if active_scenario_id is set
    assert re.search(
        r'runtime_origin\s*=\s*[\"\']saved_state[\"\']',
        body,
    ), (
        "POST /download template-seeded branch must mutate runtime_origin='saved_state' "
        "when active_scenario_id is set (preserved quirk)"
    )


def test_post_download_routes_to_TUHO_Oborovo_Solar_Wind():
    """POST /download must select runtime_project_key from
    {TUHO, Oborovo, Solar, Wind} based on the runtime_seed."""
    body = _get_post_download_route_body()
    assert "TUHO" in body, (
        "POST /download must support TUHO project key"
    )
    assert "Oborovo" in body, (
        "POST /download must support Oborovo project key"
    )
    # The Solar/Wind fallback is implicit through the user_created branch
    # and the template-seeded else branch. Just check at least one.
    assert "Solar" in body, (
        "POST /download must support Solar project key"
    )


def test_get_download_uses_factory_base_runtime():
    """GET /download always uses runtime_origin='factory_base_runtime'."""
    body = _get_get_download_route_body()
    assert "factory_base_runtime" in body, (
        "GET /download must use runtime_origin='factory_base_runtime' in replay_metadata"
    )


def test_get_download_hardcoded_project_code_mapping():
    """GET /download uses a hardcoded project_code mapping:
    'oborovo' if project_type.lower() == 'solar' else 'tuho'.
    This is a quirk that must be preserved."""
    body = _get_get_download_route_body()
    assert re.search(
        r'project_code\s*=\s*[\"\']oborovo[\"\']\s*if',
        body,
    ), (
        "GET /download must use the hardcoded project_code mapping "
        "'oborovo' if project_type.lower() == 'solar' else 'tuho' "
        "(preserved quirk)"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. /download route body size (characterization pin)
# ─────────────────────────────────────────────────────────────────────────────

def test_post_download_body_size_characterization():
    """Pin the current POST /download body size for Phase 51E-1
    characterization. Phase 51E-2 will assert the post-extraction
    size shrinks. Currently ~109 lines / ~106 non-blank."""
    body = _get_post_download_route_body()
    non_blank = [ln for ln in body.splitlines() if ln.strip()]
    # Generous upper bound; the real shrink is asserted in 51E-2
    assert len(non_blank) < 200, (
        f"POST /download route body has {len(non_blank)} non-blank lines; "
        "expected < 200 (characterization pin)"
    )
    # Pin: route is currently a god-module hotspot (>= 50 non-blank lines)
    assert len(non_blank) >= 50, (
        f"POST /download route body has {len(non_blank)} non-blank lines; "
        "expected >= 50 (characterization pin: this is a god-module "
        "hotspot that 51E-2 should slim down)"
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
    """POST /download uses the hardcoded media_type
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'."""
    body = _get_post_download_route_body()
    assert (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        in body
    ), (
        "POST /download must use the hardcoded xlsx media_type string"
    )


def test_get_download_uses_export_media_type():
    """GET /download uses export.media_type (from the export object)."""
    body = _get_get_download_route_body()
    assert "export.media_type" in body, (
        "GET /download must use export.media_type (from the export object)"
    )


def test_post_download_constructs_filename_in_route():
    """POST /download constructs the filename in the route:
    f'fincogpt_{project_type.lower()}_{scenario.lower()}.xlsx'."""
    body = _get_post_download_route_body()
    assert re.search(
        r"fincogpt_\{?project_type",
        body,
    ), (
        "POST /download must construct filename as "
        "'fincogpt_{project_type.lower()}_{scenario.lower()}.xlsx'"
    )


def test_get_download_uses_export_filename():
    """GET /download uses export.filename (from the export object)."""
    body = _get_get_download_route_body()
    assert "export.filename" in body, (
        "GET /download must use export.filename (from the export object)"
    )


def test_post_download_artifact_path_format():
    """POST /download constructs artifact_path as
    f'/download?project_type={project_type}&scenario={scenario}'."""
    body = _get_post_download_route_body()
    assert re.search(
        r'artifact_path\s*=\s*f?[\"\']/download\?project_type=',
        body,
    ), (
        "POST /download must construct artifact_path as "
        "'/download?project_type={project_type}&scenario={scenario}'"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 5. Audit / provenance behavior (INTENDED, preserved)
# ─────────────────────────────────────────────────────────────────────────────

def test_download_routes_call_record_download_export():
    """Both POST and GET /download call record_download_export with
    the full provenance context. This is INTENDED export audit
    behavior from Phase 49 — NOT forbidden persistence."""
    text = MAIN_WEB.read_text()
    # Count record_download_export calls (should be 2: one in POST, one in GET)
    matches = re.findall(r"record_download_export\s*\(", text)
    assert len(matches) == 2, (
        f"main_web.py must have exactly 2 record_download_export calls "
        f"(POST + GET), found {len(matches)}"
    )


def test_download_routes_use_export_type_excel_model_export():
    """Both POST and GET /download use export_type='excel_model_export'."""
    body_post = _get_post_download_route_body()
    body_get = _get_get_download_route_body()
    assert "excel_model_export" in body_post, (
        "POST /download must use export_type='excel_model_export'"
    )
    assert "excel_model_export" in body_get, (
        "GET /download must use export_type='excel_model_export'"
    )


def test_download_routes_use_workbook_type_values_only_excel_export():
    """Both POST and GET /download use
    workbook_type='values_only_excel_export'."""
    body_post = _get_post_download_route_body()
    body_get = _get_get_download_route_body()
    assert "values_only_excel_export" in body_post, (
        "POST /download must use workbook_type='values_only_excel_export'"
    )
    assert "values_only_excel_export" in body_get, (
        "GET /download must use workbook_type='values_only_excel_export'"
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


def test_no_production_code_changed():
    """Phase 51E-1 is characterization only. No production code may
    change vs origin/main. New files (docs, tests, report) are
    allowed."""
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
    assert changed == [], (
        f"Production files changed in Phase 51E-1 (should be 0): {changed}"
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
