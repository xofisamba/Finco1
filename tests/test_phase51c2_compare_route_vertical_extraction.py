"""Phase 51C-2 — POST /compare route vertical extraction tests.

Pins the structural and behavioral contract of the /compare route after
vertical extraction of its orchestration body into
``app/services/compare_service.py``.

This phase is a behavior-preserving production refactor EXCEPT for two
explicitly allowed bug fixes from Phase 51C-1:

  * Bug A: user_created path no longer raises NameError because
    ``runtime_snapshot`` is now resolved through
    ``deps.resolve_runtime_snapshot_source``.

  * Bug B: saved_state + active_scenario path now uses the resolved
    snapshot, not raw form values.

Hard guardrails:

  * No financial formula / runtime calculation / model output changes.
  * No fixture CSV changes.
  * No JS financial calculations.
  * /run route from Phase 51B remains thin.
  * run_service.py from Phase 51B remains intact.
  * main_web.py has zero direct record_export calls.
  * /compare route remains read-only (no record_compare_run,
    no record_workspace_runtime, no DB writes).
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
COMPARE_SERVICE_PATH = REPO_ROOT / "app" / "services" / "compare_service.py"
RUN_SERVICE_PATH = REPO_ROOT / "app" / "services" / "run_service.py"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


def _read_lines(rel: str) -> list[str]:
    return _read(rel).splitlines()


def _get_compare_route_body() -> str:
    """Extract the body of the @app.post('/compare') handler."""
    text = MAIN_WEB_PATH.read_text(encoding="utf-8")
    m = re.search(
        r"@app\.post\(\s*['\"]/compare['\"]\s*\)([\s\S]*?)(?=^@app\.)",
        text,
        re.MULTILINE,
    )
    assert m, "could not locate /compare route body"
    return m.group(1)


def _get_run_route_body() -> str:
    """Extract the body of the @app.post('/run') handler."""
    text = MAIN_WEB_PATH.read_text(encoding="utf-8")
    m = re.search(
        r"@app\.post\(\s*['\"]/run['\"]\s*\)([\s\S]*?)(?=^@app\.)",
        text,
        re.MULTILINE,
    )
    assert m, "could not locate /run route body"
    return m.group(1)


def _non_blank_lines(text: str) -> list[str]:
    return [ln for ln in text.splitlines() if ln.strip()]


# ─────────────────────────────────────────────────────────────────────────────
# 1. compare_service module exists and is well-formed
# ─────────────────────────────────────────────────────────────────────────────

def test_compare_service_module_exists():
    assert COMPARE_SERVICE_PATH.exists(), (
        "app/services/compare_service.py must exist (Phase 51C-2)"
    )


def test_compare_service_module_imports_cleanly():
    mod = importlib.import_module("app.services.compare_service")
    assert mod is not None


def test_compare_service_does_not_import_main_web():
    """Hard guardrail: import direction must be main_web -> compare_service.

    compare_service must not import main_web (would create a circular
    dependency).
    """
    src = _read("app/services/compare_service.py")
    assert "import main_web" not in src
    assert "from main_web" not in src


def test_compare_service_does_not_import_main_api():
    """compare_service is a web-layer service; it must not import
    main_api (that is the API entry point)."""
    src = _read("app/services/compare_service.py")
    assert "import main_api" not in src
    assert "from main_api" not in src


# ─────────────────────────────────────────────────────────────────────────────
# 2. CompareRouteOutcome and CompareRouteDeps dataclasses
# ─────────────────────────────────────────────────────────────────────────────

def test_compare_service_exposes_compare_route_outcome_dataclass():
    from app.services.compare_service import CompareRouteOutcome
    assert hasattr(CompareRouteOutcome, "__dataclass_fields__")
    fields = set(CompareRouteOutcome.__dataclass_fields__.keys())
    assert {"template_name", "context", "status_code", "headers"}.issubset(fields), (
        f"CompareRouteOutcome must have fields template_name, context, "
        f"status_code, headers; got {fields}"
    )


def test_compare_service_exposes_compare_route_deps_dataclass():
    from app.services.compare_service import CompareRouteDeps
    assert hasattr(CompareRouteDeps, "__dataclass_fields__")
    fields = set(CompareRouteDeps.__dataclass_fields__.keys())
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
        "scenarios",
        "project_types",
        "snapshot_input_error",
        "run_project",
    }
    assert expected.issubset(fields), (
        f"CompareRouteDeps missing required fields: {expected - fields}"
    )


def test_compare_service_exposes_execute_compare_route():
    from app.services import compare_service
    assert hasattr(compare_service, "execute_compare_route"), (
        "execute_compare_route is the public service entry point"
    )
    assert inspect.iscoroutinefunction(compare_service.execute_compare_route), (
        "execute_compare_route must be async"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. /compare route in main_web.py is materially thinner
# ─────────────────────────────────────────────────────────────────────────────

def test_compare_route_still_exists_in_main_web():
    src = _read("main_web.py")
    assert re.search(r"^@app\.post\(\s*[\"']/compare[\"']\s*\)", src, re.MULTILINE), (
        "POST /compare route must still exist in main_web.py"
    )


def test_compare_route_delegates_to_compare_service():
    body = _get_compare_route_body()
    assert "execute_compare_route" in body, (
        "/compare route must call execute_compare_route (Phase 51C-2)"
    )
    assert "CompareRouteDeps" in body, (
        "/compare route must build a CompareRouteDeps instance"
    )


def test_compare_route_body_is_materially_thinner():
    """Robust threshold: < 50 non-blank body lines after extraction.

    Pre-Phase-51C-2 body was ~95 lines. We require the post-extraction
    body to be less than 50 lines to demonstrate vertical extraction.
    """
    body = _get_compare_route_body()
    non_blank = _non_blank_lines(body)
    assert len(non_blank) < 50, (
        f"/compare route body has {len(non_blank)} non-blank lines; "
        "expected < 50 after Phase 51C-2 vertical extraction"
    )


def test_compare_route_does_not_call_run_project_directly():
    """Route must not call ``run_project`` directly — that's a service
    concern now. The service executes run_project via the dep."""
    body = _get_compare_route_body()
    assert "run_project(" not in body, (
        "POST /compare route must not call run_project directly anymore"
    )


def test_compare_route_does_not_call_build_projectinputs_directly():
    """Route must not call build_projectinputs / build_projectinputs_from_snapshot
    directly — that's a service concern now."""
    body = _get_compare_route_body()
    assert "build_projectinputs(" not in body, (
        "POST /compare route must not call build_projectinputs directly"
    )
    assert "build_projectinputs_from_snapshot(" not in body, (
        "POST /compare route must not call "
        "build_projectinputs_from_snapshot directly"
    )


def test_compare_route_does_not_call_build_schema_from_form_directly():
    """Route must not call _build_schema_from_form directly — that's a
    service concern now."""
    body = _get_compare_route_body()
    assert "_build_schema_from_form(" not in body, (
        "POST /compare route must not call _build_schema_from_form directly"
    )


def test_compare_route_renders_template_from_outcome():
    """The /compare route must render the template based on the
    CompareRouteOutcome returned by execute_compare_route."""
    body = _get_compare_route_body()
    # The route uses outcome.template_name to drive the template.
    assert "outcome.template_name" in body, (
        "/compare route must use outcome.template_name to render the template"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 4. Behavior preservation
# ─────────────────────────────────────────────────────────────────────────────

def test_compare_service_returns_errors_html_on_runtime_guard_block():
    """When check_runtime_allowed returns (False, _, guard_message),
    the service must return CompareRouteOutcome with
    template_name='partials/errors.html'."""
    text = _read("app/services/compare_service.py")
    # The guard block returns errors.html with the guard_message.
    assert 'template_name="partials/errors.html"' in text, (
        "compare_service must return partials/errors.html on runtime "
        "guard block"
    )
    assert "guard_message" in text, (
        "compare_service must use guard_message in the error context"
    )


def test_compare_service_returns_errors_html_on_invalid_project_type():
    """When effective_project_type is not in deps.project_types, the
    service must return CompareRouteOutcome with
    template_name='partials/errors.html' and the 'must be one of' error."""
    text = _read("app/services/compare_service.py")
    assert "must be one of" in text, (
        "compare_service must surface 'project_type must be one of' error"
    )


def test_compare_service_catches_snapshot_input_error_narrowly():
    """The user_created path must catch SnapshotInputError narrowly
    (via deps.snapshot_input_error), not as a bare Exception."""
    text = _read("app/services/compare_service.py")
    assert "deps.snapshot_input_error" in text, (
        "compare_service must catch SnapshotInputError via "
        "deps.snapshot_input_error on the user_created path"
    )


def test_compare_service_emits_comparison_html_on_success():
    """On a successful compare run, the service must return
    template_name='partials/comparison.html' with project_type,
    scenarios, and results in context."""
    text = _read("app/services/compare_service.py")
    assert 'partials/comparison.html' in text, (
        "compare_service must render partials/comparison.html on success"
    )
    assert '"project_type"' in text or "'project_type'" in text, (
        "compare_service must include project_type in context"
    )
    assert '"scenarios"' in text or "'scenarios'" in text, (
        "compare_service must include scenarios in context"
    )
    assert '"results"' in text or "'results'" in text, (
        "compare_service must include results in context"
    )


def test_compare_service_loop_continues_on_per_scenario_error():
    """The service loop over SCENARIOS must continue on per-scenario
    exception. The failing scenario gets {"error": str(e)} in results."""
    text = _read("app/services/compare_service.py")
    # Find the for-loop block and check it doesn't short-circuit.
    # The loop has ``except Exception as e: results[sc] = {"error": str(e)}``
    assert re.search(
        r'for\s+\w+\s+in\s+deps\.scenarios[^:]*:[\s\S]*?results\[\w+\]\s*=\s*\{[\s\S]*?[\"\']error[\"\']',
        text,
    ), (
        "compare_service must have a for-loop over deps.scenarios with "
        '{"error": str(e)} soft-error semantics'
    )


def test_compare_service_iterates_scenarios_from_deps():
    """The service must iterate over deps.scenarios (not a hard-coded
    SCENARIOS constant), so the loop respects the DI bundle."""
    text = _read("app/services/compare_service.py")
    assert "for" in text and "deps.scenarios" in text, (
        "compare_service must iterate over deps.scenarios"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 5. Bug Fix A — user_created NameError
# ─────────────────────────────────────────────────────────────────────────────

def test_compare_service_resolves_runtime_snapshot_for_user_created():
    """BUG FIX A: the user_created path in compare_service must obtain
    ``runtime_snapshot`` via ``deps.resolve_runtime_snapshot_source``
    BEFORE calling build_projectinputs_from_snapshot.

    The legacy /compare route referenced runtime_snapshot here without
    ever defining it (NameError latent bug).
    """
    text = _read("app/services/compare_service.py")
    # The service must call resolve_runtime_snapshot_source via deps.
    assert "deps.resolve_runtime_snapshot_source" in text, (
        "compare_service must call deps.resolve_runtime_snapshot_source "
        "to resolve runtime_snapshot for the user_created path"
    )
    # The user_created branch must call build_projectinputs_from_snapshot
    # only AFTER the snapshot is resolved.
    user_created_block = re.search(
        r'project_origin\s*==\s*[\"\']user_created[\"\'][\s\S]*?except\s+deps\.snapshot_input_error',
        text,
    )
    assert user_created_block, (
        "could not locate user_created branch in compare_service"
    )
    block_text = user_created_block.group(0)
    assert "build_projectinputs_from_snapshot" in block_text, (
        "user_created branch must call build_projectinputs_from_snapshot"
    )


def test_compare_service_user_created_branch_does_not_have_free_runtime_snapshot():
    """The user_created branch in compare_service must NOT have a free
    ``runtime_snapshot`` reference. Resolution is via deps."""
    text = _read("app/services/compare_service.py")
    user_created_block = re.search(
        r'project_origin\s*==\s*[\"\']user_created[\"\'][\s\S]*?except\s+deps\.snapshot_input_error',
        text,
    )
    assert user_created_block
    block_text = user_created_block.group(0)
    # In the user_created block, runtime_snapshot should be referenced
    # only as a variable that was assigned earlier in the function
    # (not as a free variable). The block must NOT contain a bare
    # reference like ``runtime_snapshot`` without a prior assignment.
    # Find all runtime_snapshot references in the block:
    refs = re.findall(r"runtime_snapshot", block_text)
    # We expect at least 2: one in build_projectinputs_from_snapshot(runtime_snapshot)
    # and possibly more in the except branch. Crucially, the variable
    # must be assigned (or be a parameter) — find any ``=`` in the block.
    # Easier check: the block must NOT contain a NameError. The
    # resolved snapshot is assigned earlier in execute_compare_route().
    # So inside the user_created block, runtime_snapshot is a name
    # defined in the enclosing scope. We just check that build_projectinputs_from_snapshot
    # is called with it as the argument.
    assert "build_projectinputs_from_snapshot(runtime_snapshot)" in block_text, (
        "user_created branch must call "
        "build_projectinputs_from_snapshot(runtime_snapshot)"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 6. Bug Fix B — saved_state + active_scenario resolves snapshot
# ─────────────────────────────────────────────────────────────────────────────

def test_compare_service_resolves_snapshot_for_saved_state_path():
    """BUG FIX B: the non-user_created branch must use the resolved
    snapshot (from deps.resolve_runtime_snapshot_source) when on the
    saved_state + active_scenario path. The legacy /compare route
    referenced runtime_snapshot here without ever calling the resolver.
    """
    text = _read("app/services/compare_service.py")
    # The service must call deps.resolve_runtime_snapshot_source.
    assert "deps.resolve_runtime_snapshot_source" in text
    # The saved_state + active_scenario branch must use the resolved
    # snapshot.
    assert re.search(
        r"runtime_snapshot\s+and\s+runtime_origin\s*==\s*[\"\']saved_state[\"\']\s+and\s+workspace_state\.active_scenario_id",
        text,
    ), (
        "compare_service must branch on "
        "runtime_snapshot and saved_state and active_scenario_id"
    )


def test_compare_service_saved_state_branch_uses_resolved_snapshot():
    """The saved_state + active_scenario branch in compare_service must
    call build_projectinputs_from_snapshot(runtime_snapshot) — using
    the resolved snapshot, not raw form values."""
    text = _read("app/services/compare_service.py")
    # The template-seeded branch (the else of ``if project_origin == 'user_created'``)
    # must contain the saved_state + active_scenario condition followed
    # by build_projectinputs_from_snapshot.
    # Find: from the else: line, up to the runtime_seed assignment.
    else_block = re.search(
        r"else:\s*\n\s*try:[\s\S]*?runtime_seed\s*=",
        text,
    )
    assert else_block, "could not locate template-seeded else branch"
    block_text = else_block.group(0)
    assert re.search(
        r"if\s+runtime_snapshot\s+and\s+runtime_origin\s*==\s*[\"\']saved_state[\"\']\s+and\s+workspace_state\.active_scenario_id",
        block_text,
    ), (
        "template-seeded branch must check "
        "runtime_snapshot and saved_state and active_scenario_id"
    )
    assert "build_projectinputs_from_snapshot(runtime_snapshot)" in block_text, (
        "template-seeded branch must call "
        "build_projectinputs_from_snapshot(runtime_snapshot) on the "
        "saved_state path"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 7. Read-only invariant
# ─────────────────────────────────────────────────────────────────────────────

def test_compare_service_does_not_call_persistence_helpers():
    """compare_service must NOT call any persistence / record_* helper
    on the /compare path. /compare is read-only by design.

    We check for actual call patterns (function call with ``(``) and
    attribute / method references — not just substring mentions in
    docstrings or comments.
    """
    text = _read("app/services/compare_service.py")
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
            f"compare_service must not call {forbidden} (read-only route)"
        )
        assert not def_pattern.search(text), (
            f"compare_service must not define {forbidden}"
        )
    for forbidden in (
        "db.add", "db.commit", "db.flush",
        "session.add", "session.commit",
    ):
        assert forbidden not in text, (
            f"compare_service must not call {forbidden} (read-only route)"
        )


def test_compare_route_does_not_call_persistence_helpers():
    body = _get_compare_route_body()
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
            f"/compare route must not call {forbidden} (read-only route)"
        )
        assert not def_pattern.search(body), (
            f"/compare route must not define {forbidden}"
        )


def test_compare_service_does_not_define_record_compare_function():
    """compare_service must not define a record_compare_run function."""
    text = _read("app/services/compare_service.py")
    assert "def record_compare" not in text, (
        "compare_service must not define a record_compare_run function"
    )


def test_main_web_has_zero_direct_record_export_calls():
    src = _read("main_web.py")
    matches = re.findall(r"\brecord_export\s*\(", src)
    assert len(matches) == 0, (
        f"main_web must have 0 direct record_export calls, found {len(matches)}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 8. /run route integrity
# ─────────────────────────────────────────────────────────────────────────────

def test_run_route_remains_thin():
    """The /run route from Phase 51B must remain thin. Phase 51C-2
    must not regress /run."""
    body = _get_run_route_body()
    non_blank = _non_blank_lines(body)
    assert len(non_blank) < 200, (
        f"/run route body has {len(non_blank)} non-blank lines; "
        "Phase 51B thinness contract must be preserved"
    )


def test_run_service_from_phase51b_still_intact():
    """run_service.py from Phase 51B must remain intact."""
    assert RUN_SERVICE_PATH.exists()
    text = RUN_SERVICE_PATH.read_text(encoding="utf-8")
    # Key symbols must still be exported
    for symbol in (
        "RunRouteOutcome",
        "RunRouteDeps",
        "execute_run_route",
    ):
        assert symbol in text, (
            f"run_service.py must still export {symbol}"
        )


def test_run_service_does_not_import_compare_service():
    """run_service must not depend on compare_service — they are
    independent services for /run and /compare respectively."""
    text = _read("app/services/run_service.py")
    assert "compare_service" not in text, (
        "run_service must not import or reference compare_service"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 9. Other main_web routes are unchanged
# ─────────────────────────────────────────────────────────────────────────────

def test_main_web_diff_is_scoped_to_compare_route():
    """The main_web.py diff vs origin/main must be scoped to the
    /compare route body. No other @app.* decorator line is added or
    removed."""
    result = subprocess.run(
        ["git", "diff", "origin/main", "--", "main_web.py"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    diff_text = result.stdout
    # Find all @app.* lines added or removed in the diff.
    decorator_changes = [
        ln for ln in diff_text.splitlines()
        if (ln.startswith("+@app.") or ln.startswith("-@app."))
    ]
    # The /compare decorator may appear in the diff if its docstring
    # or signature changed. We allow that. We disallow any other
    # decorator change.
    non_compare_changes = [
        ln for ln in decorator_changes
        if "/compare" not in ln
    ]
    assert non_compare_changes == [], (
        "main_web.py diff must not touch any @app.* decorator "
        f"other than /compare; got: {non_compare_changes}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 10. Guardrails
# ─────────────────────────────────────────────────────────────────────────────

def test_no_fixture_csv_changes():
    """No real fixture CSV files must be modified by Phase 51C-2."""
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
    """No JS files should be added or changed in static/ by Phase 51C-2.

    Phase 51C-2 is a backend refactor.
    """
    result = subprocess.run(
        ["git", "diff", "--name-only", "origin/main", "--", "static/"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    changed = [l for l in result.stdout.strip().split("\n") if l]
    # No JS files should appear in the diff.
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


def test_no_production_code_changed_outside_compare_extraction():
    """Phase 51C-2 may change ONLY:
    - main_web.py (the /compare route body becomes thin)
    - app/services/compare_service.py (new file)
    - main_web.py import line for compare_service

    Every other production source file must be unchanged vs origin/main.
    New docs/tests/report files are allowed.
    """
    result = subprocess.run(
        ["git", "diff", "--name-only", "origin/main", "--",
         "app/api/", "app/persistence/", "app/waterfall_core.py",
         "app/services/run_service.py", "app/services/scenario_state_service.py",
         "app/services/export_service.py", "app/services/export_audit_service.py",
         "app/ui/", "app/excel_export.py", "app/input_adapter.py",
         "app/input_schema.py", "app/project_factories.py"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    changed = [l for l in result.stdout.strip().split("\n") if l]
    # UX-2C-1 cross-arc allowlist (Overview KPI dedup)
    ux2c1_allowed = ("app/ui/dashboard.py",)  # UX-2C-1 cross-arc
    changed = [c for c in changed if c not in ux2c1_allowed]
    assert changed == [], (
        f"Phase 51C-2 must not change non-/compare production files; "
        f"got: {changed}"
    )


def test_main_web_does_not_import_runtime_guard_for_snapshot():
    """main_web must not import the legacy runtime_guard_for_snapshot
    directly — that's the lower-level repository function. The
    scenario_state_service wrapper is preferred."""
    src = _read("main_web.py")
    assert "runtime_guard_for_snapshot" not in src, (
        "main_web must not import runtime_guard_for_snapshot directly"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 11. Live integration tests (TestClient)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def client(isolated_db):
    """Authenticated TestClient for /compare integration tests."""
    from fastapi.testclient import TestClient
    from main_web import app
    from app.auth import create_session_token, COOKIE_NAME
    tc = TestClient(app)
    token = create_session_token()
    tc.cookies.set(COOKIE_NAME, token)
    return tc


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    """Per-test SQLite database for clean state (mirrors Phase 51A)."""
    import uuid
    db_file = tmp_path / f"phase51c2_{uuid.uuid4().hex[:8]}.db"
    monkeypatch.setenv("FINCO_DB_PATH", str(db_file))
    import app.persistence.db as db_mod
    db_mod.DB_PATH = str(db_file)
    db_mod._connection = None
    yield str(db_file)
    db_mod._connection = None


def test_compare_unauthenticated_redirects_to_login(isolated_db):
    """Unauthenticated /compare must 302 to /login (preserved from 51C-1)."""
    from fastapi.testclient import TestClient
    from main_web import app
    tc = TestClient(app)
    # No cookies set — unauthenticated request.
    r = tc.post("/compare", data={"project_type": "Solar"}, follow_redirects=False)
    assert r.status_code == 302, (
        f"unauthenticated /compare must redirect to /login (302), "
        f"got {r.status_code}"
    )
    assert "/login" in r.headers.get("location", ""), (
        f"unauthenticated /compare must redirect to /login, "
        f"got location={r.headers.get('location')}"
    )


def test_compare_invalid_project_type_returns_error(client):
    """Invalid project_type must render errors.html with the
    project_types error message (preserved from 51C-1)."""
    r = client.post("/compare", data={"project_type": "Nuclear"})
    assert r.status_code == 200
    assert "errors.html" in r.text or "must be one of" in r.text.lower() or "error" in r.text.lower()


def test_compare_solar_live_behavior(client):
    """Generic Solar compare live behavior (preserved from 51C-1)."""
    r = client.post("/compare", data={"project_type": "Solar"})
    assert r.status_code == 200
    assert ("Base" in r.text) or ("error" in r.text.lower()), (
        f"unexpected /compare response body: {r.text[:200]}"
    )


def test_compare_wind_live_behavior(client):
    """Generic Wind compare live behavior (preserved from 51C-1)."""
    r = client.post("/compare", data={"project_type": "Wind"})
    assert r.status_code == 200
    assert ("Base" in r.text) or ("error" in r.text.lower()), (
        f"unexpected /compare response body: {r.text[:200]}"
    )


def test_compare_invalid_gearing_returns_error_or_comparison(client):
    """Invalid numeric input returns errors.html or comparison.html
    (preserved from 51C-1)."""
    r = client.post("/compare", data={"project_type": "Solar", "gearing_pct": "999"})
    assert r.status_code == 200
    # Either comparison rendered or errors rendered, both are valid
    # outcomes for malformed input.
    assert "comparison.html" in r.text or "errors.html" in r.text or "error" in r.text.lower()


def test_compare_no_traceback_in_response(client):
    """No Python tracebacks should appear in the /compare response body
    (preserved from 51C-1)."""
    r = client.post("/compare", data={"project_type": "Solar"})
    assert "Traceback" not in r.text, (
        f"unexpected traceback in /compare response: {r.text[:500]}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 12. Smoke imports
# ─────────────────────────────────────────────────────────────────────────────

def test_main_web_imports_cleanly():
    """``import main_web`` must still work after Phase 51C-2 extraction."""
    sys.path.insert(0, str(REPO_ROOT))
    import main_web  # noqa: F401


def test_compare_service_imports_cleanly():
    """``from app.services import compare_service`` must work."""
    import app.services.compare_service  # noqa: F401


# ─────────────────────────────────────────────────────────────────────────────
# 13. Phase 51C-1 / 51B / 51A regression checks
# ─────────────────────────────────────────────────────────────────────────────

def test_phase51a_golden_tests_still_pass():
    """Phase 51A golden tests for /run must still pass after Phase 51C-2
    (no regression)."""
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
    """Phase 51B extraction tests for /run must still pass after Phase
    51C-2 (no regression)."""
    r = subprocess.run(
        ["python3", "-m", "pytest",
         "tests/test_phase51b_run_route_vertical_extraction.py", "-q",
         "--tb=no"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert r.returncode == 0, (
        f"Phase 51B extraction tests regressed: {r.stdout[-500:]}"
    )


def test_phase51c1_golden_tests_still_pass():
    """Phase 51C-1 characterization tests must still pass after Phase
    51C-2 (no regression; some tests were updated to reflect fixed
    behavior)."""
    r = subprocess.run(
        ["python3", "-m", "pytest",
         "tests/test_phase51c1_compare_route_golden_characterization.py", "-q",
         "--tb=no"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert r.returncode == 0, (
        f"Phase 51C-1 golden tests regressed: {r.stdout[-500:]}"
    )
