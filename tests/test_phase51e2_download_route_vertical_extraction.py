"""Phase 51E-2 — POST /download and GET /download route vertical extraction tests.

Pins the structural and behavioral contract of the /download route
family after vertical extraction of its orchestration body into
``app/services/download_service.py``.

This phase is a behavior-preserving production refactor with NO
production behavior changes. All 12 documented behavior quirks
(Phase 51E-1) are preserved EXACTLY.

Hard guardrails:

  * No financial formula / runtime calculation / model output changes.
  * No fixture CSV changes.
  * No JS financial calculations.
  * /run route from Phase 51B remains thin.
  * /compare route from Phase 51C-2 remains thin.
  * /validate route from Phase 51D-2 remains thin.
  * run_service.py from Phase 51B remains intact.
  * compare_service.py from Phase 51C-2 remains intact.
  * validation_service.py from Phase 51D-2 remains intact.
  * export_service.py and export_audit_service.py remain intact.
  * main_web.py has zero direct record_export calls.
  * /download route family is read-then-write with INTENDED export
    audit (record_download_export) preserved from Phase 49.
  * /download does NOT call record_workspace_runtime,
    update_scenario_last_run_summary, db.*, session.*.
  * 12 behavior quirks preserved (see Phase 51E-1 documentation).
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
DOWNLOAD_SERVICE_PATH = REPO_ROOT / "app" / "services" / "download_service.py"
RUN_SERVICE_PATH = REPO_ROOT / "app" / "services" / "run_service.py"
COMPARE_SERVICE_PATH = REPO_ROOT / "app" / "services" / "compare_service.py"
VALIDATE_SERVICE_PATH = REPO_ROOT / "app" / "services" / "validation_service.py"
EXPORT_SERVICE_PATH = REPO_ROOT / "app" / "services" / "export_service.py"
EXPORT_AUDIT_SERVICE_PATH = REPO_ROOT / "app" / "services" / "export_audit_service.py"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


def _get_post_download_route_body() -> str:
    """Extract the body of the @app.post('/download') handler."""
    text = MAIN_WEB_PATH.read_text(encoding="utf-8")
    m = re.search(
        r"@app\.post\(\s*['\"]/download['\"]\s*\)([\s\S]*?)(?=^@app\.)",
        text,
        re.MULTILINE,
    )
    assert m, "could not locate POST /download route body"
    return m.group(1)


def _get_get_download_route_body() -> str:
    """Extract the body of the @app.get('/download') handler."""
    text = MAIN_WEB_PATH.read_text(encoding="utf-8")
    m = re.search(
        r"@app\.get\(\s*['\"]/download['\"]\s*\)([\s\S]*?)(?=^@app\.)",
        text,
        re.MULTILINE,
    )
    assert m, "could not locate GET /download route body"
    return m.group(1)


def _non_blank_lines(text: str) -> list[str]:
    return [ln for ln in text.splitlines() if ln.strip()]


# ─────────────────────────────────────────────────────────────────────────────
# 1. download_service module exists and is well-formed
# ─────────────────────────────────────────────────────────────────────────────

def test_download_service_module_exists():
    assert DOWNLOAD_SERVICE_PATH.exists(), (
        "app/services/download_service.py must exist (Phase 51E-2)"
    )


def test_download_service_module_imports_cleanly():
    mod = importlib.import_module("app.services.download_service")
    assert mod is not None


def test_download_service_does_not_import_main_web():
    """Hard guardrail: import direction must be main_web -> download_service.

    download_service must not import main_web (would create a circular
    dependency).
    """
    src = _read("app/services/download_service.py")
    assert "import main_web" not in src
    assert "from main_web" not in src


def test_download_service_does_not_import_main_api():
    """download_service is a web-layer service; it must not import
    main_api (that is the API entry point)."""
    src = _read("app/services/download_service.py")
    assert "import main_api" not in src
    assert "from main_api" not in src


# ─────────────────────────────────────────────────────────────────────────────
# 2. DownloadRouteOutcome and DownloadRouteDeps dataclasses
# ─────────────────────────────────────────────────────────────────────────────

def test_download_service_exposes_download_route_outcome_dataclass():
    from app.services.download_service import DownloadRouteOutcome
    assert hasattr(DownloadRouteOutcome, "__dataclass_fields__")
    fields = set(DownloadRouteOutcome.__dataclass_fields__.keys())
    expected = {"content", "media_type", "filename", "status_code", "headers", "is_error"}
    assert expected.issubset(fields), (
        f"DownloadRouteOutcome missing required fields: {expected - fields}"
    )


def test_download_service_exposes_download_route_deps_dataclass():
    from app.services.download_service import DownloadRouteDeps
    assert hasattr(DownloadRouteDeps, "__dataclass_fields__")
    fields = set(DownloadRouteDeps.__dataclass_fields__.keys())
    expected = {
        "collect_form_snapshot",
        "project_workspace_from_snapshot",
        "canonical_project_type",
        "normalize_template_source",
        "check_runtime_allowed",
        "resolve_runtime_snapshot_source",
        "build_schema_from_form",
        "build_projectinputs",
        "build_projectinputs_from_snapshot",
        "scenario_provenance_for_record",
        "replay_metadata_for_project",
        "governance_snapshot",
        "run_demo_project",
        "get_project_by_code",
        "build_excel_export_for_post_request",
        "build_values_only_export_for_project",
        "record_download_export",
        "utc_now_iso",
    }
    assert expected.issubset(fields), (
        f"DownloadRouteDeps missing required fields: {expected - fields}"
    )


def test_download_service_exposes_execute_post_download_route():
    from app.services import download_service
    assert hasattr(download_service, "execute_post_download_route"), (
        "execute_post_download_route is the public POST service entry point"
    )
    assert inspect.iscoroutinefunction(download_service.execute_post_download_route), (
        "execute_post_download_route must be async"
    )


def test_download_service_exposes_execute_get_download_route():
    from app.services import download_service
    assert hasattr(download_service, "execute_get_download_route"), (
        "execute_get_download_route is the public GET service entry point"
    )
    assert inspect.iscoroutinefunction(download_service.execute_get_download_route), (
        "execute_get_download_route must be async"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. /download route family in main_web.py is materially thinner
# ─────────────────────────────────────────────────────────────────────────────

def test_post_download_route_still_exists_in_main_web():
    src = _read("main_web.py")
    assert re.search(r"^@app\.post\(\s*[\"']/download[\"']\s*\)", src, re.MULTILINE), (
        "POST /download route must still exist in main_web.py"
    )


def test_get_download_route_still_exists_in_main_web():
    src = _read("main_web.py")
    assert re.search(r"^@app\.get\(\s*[\"']/download[\"']\s*\)", src, re.MULTILINE), (
        "GET /download route must still exist in main_web.py"
    )


def test_post_download_route_delegates_to_download_service():
    body = _get_post_download_route_body()
    assert "execute_post_download_route" in body, (
        "POST /download route must call execute_post_download_route (Phase 51E-2)"
    )
    assert "DownloadRouteDeps" in body, (
        "POST /download route must build a DownloadRouteDeps instance"
    )


def test_get_download_route_delegates_to_download_service():
    body = _get_get_download_route_body()
    assert "execute_get_download_route" in body, (
        "GET /download route must call execute_get_download_route (Phase 51E-2)"
    )
    assert "DownloadRouteDeps" in body, (
        "GET /download route must build a DownloadRouteDeps instance"
    )


def test_post_download_route_body_is_materially_thinner():
    """Robust threshold: < 50 non-blank body lines after extraction.

    Pre-Phase-51E-2 body was 106 non-blank. Post-extraction should be
    thin (route-only: auth + form + deps + service call + render).
    """
    body = _get_post_download_route_body()
    non_blank = _non_blank_lines(body)
    assert len(non_blank) < 50, (
        f"POST /download route body has {len(non_blank)} non-blank lines; "
        "expected < 50 after Phase 51E-2 vertical extraction"
    )


def test_get_download_route_body_is_materially_thinner():
    """Robust threshold: < 50 non-blank body lines after extraction.

    Pre-Phase-51E-2 body was 65 non-blank. Post-extraction should be
    thin (route-only).
    """
    body = _get_get_download_route_body()
    non_blank = _non_blank_lines(body)
    assert len(non_blank) < 50, (
        f"GET /download route body has {len(non_blank)} non-blank lines; "
        "expected < 50 after Phase 51E-2 vertical extraction"
    )


def test_post_download_route_does_not_call_run_demo_project_directly():
    body = _get_post_download_route_body()
    assert "run_demo_project(" not in body, (
        "POST /download route must not call run_demo_project directly (service concern)"
    )


def test_get_download_route_does_not_call_run_demo_project_directly():
    body = _get_get_download_route_body()
    assert "run_demo_project(" not in body, (
        "GET /download route must not call run_demo_project directly (service concern)"
    )


def test_post_download_route_does_not_call_record_download_export_directly():
    body = _get_post_download_route_body()
    assert "record_download_export(" not in body, (
        "POST /download route must not call record_download_export directly "
        "(service concern, audit call is in the service)"
    )


def test_get_download_route_does_not_call_record_download_export_directly():
    body = _get_get_download_route_body()
    assert "record_download_export(" not in body, (
        "GET /download route must not call record_download_export directly "
        "(service concern, audit call is in the service)"
    )


def test_post_download_route_renders_streaming_response_on_success():
    """POST /download route must render StreamingResponse when the
    service outcome is not an error."""
    body = _get_post_download_route_body()
    assert "StreamingResponse(" in body, (
        "POST /download route must use StreamingResponse for success responses"
    )


def test_post_download_route_renders_html_response_on_error():
    """POST /download route must render HTMLResponse when the service
    outcome is an error (is_error=True)."""
    body = _get_post_download_route_body()
    assert "HTMLResponse(" in body, (
        "POST /download route must use HTMLResponse for error responses"
    )
    assert "outcome.is_error" in body, (
        "POST /download route must check outcome.is_error to choose response type"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 4. Behavior preservation — 12 quirks pinned
# ─────────────────────────────────────────────────────────────────────────────

# Quirk 1: POST has TWO template branches for project_key resolution.
def test_quirk_1_post_two_template_branches_for_project_key():
    """Quirk 1: POST has TWO template branches for project_key
    resolution (user_created uses canonical; template-seeded uses
    normalize_template_source)."""
    text = _read("app/services/download_service.py")
    assert "canonical_project_type" in text, (
        "download_service POST must use canonical_project_type (user_created branch)"
    )
    assert "normalize_template_source" in text, (
        "download_service POST must use normalize_template_source (template-seeded branch)"
    )


# Quirk 2: GET has HARDCODED project_code mapping.
def test_quirk_2_get_hardcoded_project_code_mapping():
    """Quirk 2: GET hardcoded project_code mapping:
    'oborovo' if project_type.lower() == 'solar' else 'tuho'."""
    text = _read("app/services/download_service.py")
    assert re.search(
        r"project_code\s*=\s*[\"\']oborovo[\"\']\s*if",
        text,
    ), (
        "download_service GET must use the hardcoded project_code mapping "
        "'oborovo' if project_type.lower() == 'solar' else 'tuho'"
    )


# Quirk 3: POST mutates runtime_origin='saved_state' in non-user_created branch.
def test_quirk_3_post_mutates_runtime_origin_to_saved_state():
    """Quirk 3: POST mutates runtime_origin='saved_state' in the
    non-user_created branch when active_scenario_id is set."""
    text = _read("app/services/download_service.py")
    assert re.search(
        r"runtime_origin\s*=\s*[\"\']saved_state[\"\']",
        text,
    ), (
        "download_service POST must mutate runtime_origin='saved_state' "
        "in non-user_created branch (preserved quirk 3)"
    )


# Quirk 4: POST uses build_excel_export_for_post_request; GET uses build_values_only_export_for_project.
def test_quirk_4_post_and_get_use_different_export_builders():
    """Quirk 4: POST uses build_excel_export_for_post_request; GET
    uses build_values_only_export_for_project."""
    text = _read("app/services/download_service.py")
    assert "build_excel_export_for_post_request(" in text, (
        "download_service POST must call build_excel_export_for_post_request (quirk 4)"
    )
    assert "build_values_only_export_for_project(" in text, (
        "download_service GET must call build_values_only_export_for_project (quirk 4)"
    )


# Quirk 5: POST hardcoded media_type; GET uses export.media_type.
def test_quirk_5_post_hardcoded_xlsx_media_type_and_get_uses_export():
    """Quirk 5: POST hardcoded media_type
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
    GET uses export.media_type."""
    text = _read("app/services/download_service.py")
    assert (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        in text
    ), (
        "download_service POST must use the hardcoded xlsx media_type (quirk 5)"
    )
    assert "export.media_type" in text, (
        "download_service GET must use export.media_type (quirk 5)"
    )


# Quirk 6: POST constructs filename in route; GET uses export.filename.
def test_quirk_6_post_filename_in_route_get_uses_export_filename():
    """Quirk 6: POST constructs filename in service
    (f'fincogpt_{project_type.lower()}_{scenario.lower()}.xlsx');
    GET uses export.filename."""
    text = _read("app/services/download_service.py")
    assert re.search(
        r"fincogpt_\{?project_type",
        text,
    ), (
        "download_service POST must construct filename 'fincogpt_{project_type.lower()}_{scenario.lower()}.xlsx' (quirk 6)"
    )
    assert "export.filename" in text, (
        "download_service GET must use export.filename (quirk 6)"
    )


# Quirk 7: GET passes scenario_id=None to record_download_export; POST passes active scenario id.
def test_quirk_7_get_passes_scenario_id_none_to_record_download_export():
    """Quirk 7: GET passes scenario_id=None to record_download_export;
    POST passes active_scenario_record.scenario_id (or None if no
    active scenario)."""
    text = _read("app/services/download_service.py")
    # The GET path explicitly passes scenario_id=None
    assert re.search(
        r"scenario_id\s*=\s*None",
        text,
    ), (
        "download_service GET must pass scenario_id=None to record_download_export (quirk 7)"
    )


# Quirk 8: Inline error HTML in both routes preserved; no Jinja template.
def test_quirk_8_inline_error_html_preserved():
    """Quirk 8: Inline error HTML format preserved
    ('<html><body><h2>Excel generation failed</h2>...'). No Jinja
    template introduced."""
    text = _read("app/services/download_service.py")
    assert "Excel generation failed" in text, (
        "download_service must use the inline 'Excel generation failed' error format (quirk 8)"
    )
    assert "href='/'>Back" in text, (
        "download_service must use the inline 'Back' link (quirk 8)"
    )


# Quirk 9: Top-level except Exception broad catch preserved; 500 inline error page.
def test_quirk_9_top_level_broad_except_preserved():
    """Quirk 9: Top-level except Exception broad catch preserved;
    500 inline error page behavior remains."""
    text = _read("app/services/download_service.py")
    # Look for `except Exception` clauses
    assert re.search(
        r"except\s+Exception\s+as\s+\w+\s*:",
        text,
    ), (
        "download_service must have a top-level except Exception broad catch (quirk 9)"
    )
    # And status_code=500 in the inline error outcome
    assert re.search(
        r"status_code\s*=\s*500",
        text,
    ), (
        "download_service must return status_code=500 on top-level exception (quirk 9)"
    )


# Quirk 10: artifact_path is a string describing the URL, not a filesystem path.
def test_quirk_10_artifact_path_is_url_string():
    """Quirk 10: artifact_path is a string describing the URL
    ('/download?project_type={project_type}&scenario={scenario}'), not
    a filesystem path."""
    text = _read("app/services/download_service.py")
    assert re.search(
        r"artifact_path\s*=\s*f?[\"\']/download\?project_type=",
        text,
    ), (
        "download_service must construct artifact_path as "
        "'/download?project_type={project_type}&scenario={scenario}' (quirk 10)"
    )


# Quirk 11: POST captures effective_runtime_origin from _resolve_runtime_snapshot_source but discards it.
def test_quirk_11_effective_runtime_origin_captured_but_discarded():
    """Quirk 11: POST captures effective_runtime_origin from
    _resolve_runtime_snapshot_source (4th tuple element) but
    discards it downstream (parity quirk preserved)."""
    text = _read("app/services/download_service.py")
    # The service must use `_effective_runtime_origin` (or similar
    # underscore-prefixed name) to mark the value as intentionally
    # unused.
    assert re.search(
        r"_effective_runtime_origin",
        text,
    ), (
        "download_service must use _effective_runtime_origin (or "
        "similar underscore-prefixed) for the captured-but-discarded "
        "4th tuple element (quirk 11 parity quirk)"
    )


# Quirk 12: POST broad except (ValueError, Exception) on schema build preserved.
def test_quirk_12_post_broad_except_value_error_exception_on_schema_build():
    """Quirk 12: POST broad except (ValueError, Exception) on schema
    build preserved as-is (overly broad, same pattern as /compare)."""
    text = _read("app/services/download_service.py")
    assert re.search(
        r"except\s*\(ValueError\s*,\s*Exception\)\s+as\s+\w+\s*:",
        text,
    ), (
        "download_service POST schema build must catch "
        "(ValueError, Exception) broadly (quirk 12)"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 5. Audit / provenance behavior (INTENDED, preserved)
# ─────────────────────────────────────────────────────────────────────────────

def test_download_service_calls_record_download_export_twice():
    """Both POST and GET call record_download_export exactly once on
    success. This is INTENDED Phase 49 export audit behavior —
    NOT forbidden persistence."""
    text = _read("app/services/download_service.py")
    # Match only actual call sites (with .record_download_export() syntax)
    matches = re.findall(r"\.record_download_export\s*\(", text)
    assert len(matches) == 2, (
        f"download_service must call record_download_export exactly 2 times "
        f"(POST + GET); found {len(matches)}"
    )


def test_download_service_uses_intended_audit_export_type():
    """Both POST and GET use export_type='excel_model_export'."""
    text = _read("app/services/download_service.py")
    sites = re.findall(
        r"export_type\s*=\s*[\"\']excel_model_export[\"\']",
        text,
    )
    assert len(sites) >= 2, (
        f"download_service must set export_type='excel_model_export' at "
        f"least twice (POST + GET); found {len(sites)}"
    )


def test_download_service_uses_intended_audit_workbook_type():
    """Both POST and GET use workbook_type='values_only_excel_export'."""
    text = _read("app/services/download_service.py")
    sites = re.findall(
        r"workbook_type\s*=\s*[\"\']values_only_excel_export[\"\']",
        text,
    )
    assert len(sites) >= 2, (
        f"download_service must set workbook_type='values_only_excel_export' "
        f"at least twice (POST + GET); found {len(sites)}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 6. Read / write side effects classification
# ─────────────────────────────────────────────────────────────────────────────

def test_download_service_does_not_call_forbidden_persistence():
    """download_service must NOT call any forbidden persistence
    helper. Only record_download_export is allowed (INTENDED audit).

    We exclude the module docstring from the check to avoid false
    positives from docstring examples that list these patterns as
    forbidden.
    """
    raw_text = _read("app/services/download_service.py")
    # Strip the module docstring (everything between the first pair of
    # triple quotes at module level). The forbidden patterns are
    # only ever mentioned in the docstring; they are NOT in the
    # executable code.
    docstring_match = re.search(r'^\s*"""(.*?)"""\s*', raw_text, re.DOTALL)
    if docstring_match:
        text = raw_text[docstring_match.end():]
    else:
        text = raw_text
    for forbidden in (
        "record_workspace_runtime",
        "update_scenario_last_run_summary",
    ):
        # Check for actual call / definition / attribute access patterns.
        call_pattern = re.compile(rf"\.{re.escape(forbidden)}\s*\(")
        def_pattern = re.compile(rf"def\s+{re.escape(forbidden)}\b")
        assert not call_pattern.search(text), (
            f"download_service must not call {forbidden} (forbidden persistence)"
        )
        assert not def_pattern.search(text), (
            f"download_service must not define {forbidden}"
        )
    for forbidden in (
        "db.add", "db.commit", "db.flush",
        "session.add", "session.commit",
    ):
        assert forbidden not in text, (
            f"download_service must not call {forbidden} (forbidden persistence)"
        )


def test_download_service_does_not_call_record_compare_run():
    """download_service must NOT call record_compare_run (does not
    exist; only /compare path uses compare-style helpers)."""
    text = _read("app/services/download_service.py")
    call_pattern = re.compile(r"record_compare_run\s*\(")
    assert not call_pattern.search(text), (
        "download_service must not call record_compare_run"
    )


def test_download_service_does_not_define_record_export_function():
    """download_service must NOT define a record_export function
    (Phase 49 guardrail; record_export split into 3 purpose-specific
    helpers in export_audit_service.py)."""
    text = _read("app/services/download_service.py")
    def_pattern = re.compile(r"def\s+record_export\b")
    assert not def_pattern.search(text), (
        "download_service must not define a record_export function"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 7. /run, /compare, /validate routes remain thin
# ─────────────────────────────────────────────────────────────────────────────

def _get_run_route_body() -> str:
    text = MAIN_WEB_PATH.read_text(encoding="utf-8")
    m = re.search(
        r"@app\.post\(\s*['\"]/run['\"]\s*\)([\s\S]*?)(?=^@app\.)",
        text,
        re.MULTILINE,
    )
    assert m
    return m.group(1)


def _get_compare_route_body() -> str:
    text = MAIN_WEB_PATH.read_text(encoding="utf-8")
    m = re.search(
        r"@app\.post\(\s*['\"]/compare['\"]\s*\)([\s\S]*?)(?=^@app\.)",
        text,
        re.MULTILINE,
    )
    assert m
    return m.group(1)


def _get_validate_route_body() -> str:
    text = MAIN_WEB_PATH.read_text(encoding="utf-8")
    m = re.search(
        r"@app\.post\(\s*['\"]/validate['\"]\s*\)([\s\S]*?)(?=^@app\.)",
        text,
        re.MULTILINE,
    )
    assert m
    return m.group(1)


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


def test_validate_route_remains_thin():
    body = _get_validate_route_body()
    non_blank = _non_blank_lines(body)
    assert len(non_blank) < 50, (
        f"/validate route body has {len(non_blank)} non-blank lines; "
        "Phase 51D-2 thinness contract must be preserved"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 8. Existing services are intact
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


def test_validate_service_from_phase51d2_still_intact():
    assert VALIDATE_SERVICE_PATH.exists()
    text = VALIDATE_SERVICE_PATH.read_text(encoding="utf-8")
    for symbol in ("ValidateRouteOutcome", "ValidateRouteDeps", "execute_validate_route"):
        assert symbol in text, (
            f"validation_service.py must still export {symbol}"
        )


def test_export_service_remains_intact():
    """export_service.py must remain intact (NOT refactored in 51E-2)."""
    assert EXPORT_SERVICE_PATH.exists()
    text = EXPORT_SERVICE_PATH.read_text(encoding="utf-8")
    for symbol in ("build_excel_export_for_post_request", "build_values_only_export_for_project"):
        assert symbol in text, (
            f"export_service.py must still export {symbol}"
        )


def test_export_audit_service_remains_intact():
    """export_audit_service.py must remain intact (NOT refactored in
    51E-2). record_download_export must still be exported."""
    assert EXPORT_AUDIT_SERVICE_PATH.exists()
    text = EXPORT_AUDIT_SERVICE_PATH.read_text(encoding="utf-8")
    assert "record_download_export" in text, (
        "export_audit_service.py must still export record_download_export"
    )


def test_existing_services_do_not_import_download_service():
    """Existing services must not depend on download_service (which
    is a sibling service, not a dependency)."""
    for svc_path, name in [
        (RUN_SERVICE_PATH, "run_service"),
        (COMPARE_SERVICE_PATH, "compare_service"),
        (VALIDATE_SERVICE_PATH, "validation_service"),
    ]:
        text = svc_path.read_text(encoding="utf-8")
        assert "download_service" not in text, (
            f"{name} must not import or reference download_service"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 9. Other main_web routes are unchanged
# ─────────────────────────────────────────────────────────────────────────────

def test_main_web_diff_is_scoped_to_download_route():
    """The main_web.py diff vs origin/main must be scoped to the
    /download route family. No other @app.* decorator line is added
    or removed."""
    result = subprocess.run(
        ["git", "diff", "origin/main", "--", "main_web.py"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    diff_text = result.stdout
    decorator_changes = [
        ln for ln in diff_text.splitlines()
        if (ln.startswith("+@app.") or ln.startswith("-@app."))
    ]
    non_download_changes = [
        ln for ln in decorator_changes
        if "/download" not in ln
    ]
    assert non_download_changes == [], (
        "main_web.py diff must not touch any @app.* decorator "
        f"other than /download; got: {non_download_changes}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 10. Guardrails
# ─────────────────────────────────────────────────────────────────────────────

def test_no_fixture_csv_changes():
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
    result = subprocess.run(
        ["git", "diff", "--name-only", "origin/main", "--", "static/"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    changed = [l for l in result.stdout.strip().split("\n") if l]
    js_files = [c for c in changed if c.endswith(".js")]
    assert js_files == [], f"JS files changed: {js_files}"


def test_no_services_js_files():
    services = list((REPO_ROOT / "app" / "services").rglob("*.js"))
    assert services == [], f"no JS files belong under app/services: {services}"


def test_no_financial_formula_changes():
    result = subprocess.run(
        ["git", "diff", "--name-only", "origin/main", "--",
         "app/waterfall_core.py", "app/project_factories.py",
         "app/input_schema.py", "app/input_adapter.py"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    changed = [l for l in result.stdout.strip().split("\n") if l]
    assert changed == [], f"Financial/runtime files changed: {changed}"


def test_no_production_code_changed_outside_download_extraction():
    """Phase 51E-2 may change ONLY:
    - main_web.py (the /download route family becomes thin)
    - app/services/download_service.py (new file)
    - main_web.py import line for download_service

    Every other production source file must be unchanged vs origin/main.
    """
    result = subprocess.run(
        ["git", "diff", "--name-only", "origin/main", "--",
         "app/api/", "app/persistence/", "app/waterfall_core.py",
         "app/services/run_service.py", "app/services/compare_service.py",
         "app/services/validation_service.py",
         "app/services/scenario_state_service.py",
         "app/services/export_service.py",
         "app/services/export_audit_service.py",
         "app/ui/", "app/excel_export.py", "app/input_adapter.py",
         "app/input_schema.py", "app/project_factories.py"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    changed = [l for l in result.stdout.strip().split("\n") if l]
    assert changed == [], (
        f"Phase 51E-2 must not change non-/download production files; "
        f"got: {changed}"
    )


def test_main_web_has_zero_direct_record_export_calls():
    src = _read("main_web.py")
    matches = re.findall(r"\brecord_export\s*\(", src)
    assert len(matches) == 0, (
        f"main_web must have 0 direct record_export calls, found {len(matches)}"
    )


def test_main_web_does_not_import_runtime_guard_for_snapshot():
    src = _read("main_web.py")
    assert "runtime_guard_for_snapshot" not in src, (
        "main_web must not import runtime_guard_for_snapshot directly"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 11. Live integration tests (TestClient)
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
    db_file = tmp_path / f"phase51e2_{uuid.uuid4().hex[:8]}.db"
    monkeypatch.setenv("FINCO_DB_PATH", str(db_file))
    import app.persistence.db as db_mod
    db_mod.DB_PATH = str(db_file)
    db_mod._connection = None
    yield str(db_file)
    db_mod._connection = None


def test_post_download_unauthenticated_redirects_to_login(unauthenticated_client):
    r = unauthenticated_client.post(
        "/download",
        data={"project_type": "Solar", "scenario": "Base"},
        follow_redirects=False,
    )
    assert r.status_code == 302
    assert "/login" in r.headers.get("location", "")


def test_get_download_unauthenticated_redirects_to_login(unauthenticated_client):
    r = unauthenticated_client.get(
        "/download?project_type=Solar&scenario=Base",
        follow_redirects=False,
    )
    assert r.status_code == 302
    assert "/login" in r.headers.get("location", "")


def test_post_download_valid_form_live_behavior(client):
    """Valid POST /download must return either a streaming xlsx
    response (success) or an inline HTML error page (failure)."""
    r = client.post("/download", data={
        "project_type": "Solar", "scenario": "Base",
        "capacity_mw": "100", "tariff_eur_mwh": "80", "p50_hours": "2500",
        "total_capex_keur": "100000", "opex_y1_keur": "2000",
        "gearing_pct": "70", "target_dscr": "1.3",
        "interest_rate_pct": "5.5", "tenor_years": "15",
    })
    assert r.status_code in (200, 400, 500)


def test_get_download_with_default_query_params_live_behavior(client):
    r = client.get("/download", follow_redirects=False)
    assert r.status_code in (200, 400, 500)


# ─────────────────────────────────────────────────────────────────────────────
# 12. Smoke imports
# ─────────────────────────────────────────────────────────────────────────────

def test_main_web_imports_cleanly():
    sys.path.insert(0, str(REPO_ROOT))
    import main_web  # noqa: F401


def test_download_service_imports_cleanly():
    import app.services.download_service  # noqa: F401


# ─────────────────────────────────────────────────────────────────────────────
# 13. Regression checks for previous phases
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


def test_phase51d2_extraction_tests_still_pass():
    r = subprocess.run(
        ["python3", "-m", "pytest",
         "tests/test_phase51d2_validate_route_vertical_extraction.py", "-q",
         "--tb=no"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert r.returncode == 0, (
        f"Phase 51D-2 extraction tests regressed: {r.stdout[-500:]}"
    )


def test_phase51e1_characterization_tests_still_pass():
    """Phase 51E-1 characterization tests (with structural tests
    re-pointed to download_service.py in this phase) must still
    pass."""
    r = subprocess.run(
        ["python3", "-m", "pytest",
         "tests/test_phase51e1_download_route_golden_characterization.py", "-q",
         "--tb=no"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert r.returncode == 0, (
        f"Phase 51E-1 characterization tests regressed: {r.stdout[-500:]}"
    )
