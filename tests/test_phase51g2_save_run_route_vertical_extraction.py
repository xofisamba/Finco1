"""Phase 51G-2 — POST /save-run vertical extraction test suite.

Verifies that the /save-run route has been extracted from main_web.py
into app/services/save_run_service.py following the Phase 51B/51C-2/
51D-2/51E-2 canonical pattern:

- main_web.py route is thin (auth + form + snapshot + deps + service
  call + render)
- service owns orchestration
- deps bundle injects helpers from main_web module scope
- service does NOT import main_web or main_api
- backend remains source of truth
- all 15 characterized behaviors preserved
- all 7 quirks preserved
- save_run → save_project ordering preserved
- save_project.runtime_timestamp = run_record.created_at.isoformat()
  preserved
- _clean_user_project_runtime_snapshot latent bug NOT fixed in 51G-2
- Phase 51F guardrails still green
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
MAIN_WEB = REPO_ROOT / "main_web.py"
SERVICE = REPO_ROOT / "app" / "services" / "save_run_service.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _route_body(name: str) -> str:
    """Extract the body of a named async def route from main_web.py."""
    src = _read(MAIN_WEB)
    pattern = re.compile(
        rf"@app\.\w+\(\"{re.escape(name)}\"\)\s*\nasync def \w+\([^)]*\):.*?(?=\n@app\.|\Z)",
        re.DOTALL,
    )
    m = pattern.search(src)
    assert m, f"Route {name} not found in main_web.py"
    return m.group(0)


def _strip_docstrings_and_comments(text: str) -> str:
    """Strip docstrings and # comments to avoid false positives in
    substring assertions.
    """
    # Strip triple-quoted strings (docstrings + module-level)
    text = re.sub(r'"""[\s\S]*?"""', '', text)
    # Strip single-line # comments
    out_lines = []
    for line in text.splitlines():
        if not line.lstrip().startswith("#"):
            out_lines.append(line)
    return "\n".join(out_lines)


# ═══════════════════════════════════════════════════════════════════════════
# 1. Service file exists
# ═══════════════════════════════════════════════════════════════════════════

class TestServiceFileExists:
    """The save_run_service module must exist and be importable."""

    def test_save_run_service_file_exists(self):
        assert SERVICE.is_file(), (
            f"Service module {SERVICE} must exist after Phase 51G-2"
        )

    def test_save_run_service_module_importable(self):
        from app.services.save_run_service import (
            SaveRunRouteOutcome,
            SaveRunRouteDeps,
            execute_save_run_route,
        )
        assert SaveRunRouteOutcome is not None
        assert SaveRunRouteDeps is not None
        assert execute_save_run_route is not None

    def test_save_run_service_documented_as_phase_51g2(self):
        """The service file's top-level docstring must reference
        Phase 51G-2."""
        text = _read(SERVICE)
        assert "Phase 51G-2" in text, (
            "save_run_service module docstring must reference Phase 51G-2"
        )


# ═══════════════════════════════════════════════════════════════════════════
# 2. Service does NOT import main_web or main_api
# ═══════════════════════════════════════════════════════════════════════════

class TestServiceImportDirection:
    """One-way import direction: main_web -> service, never reverse."""

    def test_service_does_not_import_main_web(self):
        text = _read(SERVICE)
        for pattern in (r"^import main_web\b", r"^from main_web\b"):
            assert not re.search(pattern, text, re.MULTILINE), (
                f"save_run_service must not {pattern} (one-way import)"
            )

    def test_service_does_not_import_main_api(self):
        text = _read(SERVICE)
        for pattern in (r"^import main_api\b", r"^from main_api\b"):
            assert not re.search(pattern, text, re.MULTILINE), (
                f"save_run_service must not {pattern} (one-way import)"
            )

    def test_service_docstring_explains_one_way_import(self):
        """The service docstring must explain the one-way import rule."""
        text = _read(SERVICE)
        assert "does NOT import ``main_web``" in text or "does NOT import main_web" in text, (
            "Service docstring must explain one-way import direction"
        )


# ═══════════════════════════════════════════════════════════════════════════
# 3. Route is thin after extraction
# ═══════════════════════════════════════════════════════════════════════════

class TestRouteIsThin:
    """The /save-run route in main_web.py must be thin."""

    def test_route_imports_save_run_service(self):
        body = _route_body("/save-run")
        assert "from app.services.save_run_service import" in body, (
            "After 51G-2, /save-run route must import save_run_service"
        )

    def test_route_constructs_save_run_route_deps(self):
        body = _route_body("/save-run")
        assert "SaveRunRouteDeps(" in body, (
            "Route must construct SaveRunRouteDeps bundle"
        )

    def test_route_calls_execute_save_run_route(self):
        body = _route_body("/save-run")
        assert "execute_save_run_route(" in body, (
            "Route must call execute_save_run_route"
        )

    def test_route_size_after_extraction(self):
        """Post-extraction, /save-run route is ~58 non-blank lines
        (down from 127). It must NOT grow back.
        """
        body = _route_body("/save-run")
        non_blank = sum(1 for line in body.splitlines() if line.strip())
        assert 40 <= non_blank <= 90, (
            f"/save-run route should be thin after 51G-2: "
            f"got {non_blank} non-blank lines, expected 40-90"
        )

    def test_route_does_not_inline_save_run_or_save_project(self):
        """The route must NOT call save_run/save_project directly —
        those calls are in the service.
        """
        body = _route_body("/save-run")
        body_clean = _strip_docstrings_and_comments(body)
        # Route should not have `save_run(` (as a call) or
        # `save_project(` (as a call) — only the deps construction
        # uses those names.
        assert "save_run(" not in body_clean, (
            "/save-run route must not call save_run(...) — that's "
            "the service's job"
        )
        assert "save_project(" not in body_clean, (
            "/save-run route must not call save_project(...) — that's "
            "the service's job"
        )


# ═══════════════════════════════════════════════════════════════════════════
# 4. Service API surface
# ═══════════════════════════════════════════════════════════════════════════

class TestServiceAPISurface:
    """The service exposes a clean dataclass-style API."""

    def test_save_run_route_outcome_dataclass(self):
        from app.services.save_run_service import SaveRunRouteOutcome
        o = SaveRunRouteOutcome()
        assert o.template_name == "partials/save_result.html"
        assert o.status_code == 200
        assert o.is_redirect is False
        assert o.redirect_url is None
        # HX-Trigger default
        assert o.headers.get("HX-Trigger") == "refreshHistory"

    def test_save_run_route_deps_dataclass_has_required_fields(self):
        from app.services.save_run_service import SaveRunRouteDeps
        import dataclasses
        fields = {f.name for f in dataclasses.fields(SaveRunRouteDeps)}
        required = {
            "project_workspace_from_snapshot",
            "check_runtime_allowed",
            "validate_form",
            "project_types",
            "scenarios",
            "canonical_project_type",
            "build_projectinputs_from_snapshot",
            "build_schema_from_form",
            "build_projectinputs",
            "normalize_template_source",
            "run_project",
            "save_run",
            "save_project",
            "replay_metadata_for_project",
            "governance_snapshot",
            "utc_now_iso",
        }
        missing = required - fields
        assert not missing, (
            f"SaveRunRouteDeps missing required fields: {missing}"
        )

    def test_execute_save_run_route_is_async(self):
        from app.services import save_run_service
        import inspect
        assert inspect.iscoroutinefunction(save_run_service.execute_save_run_route), (
            "execute_save_run_route must be async"
        )


# ═══════════════════════════════════════════════════════════════════════════
# 5. Behaviors preserved (subset — full coverage is in 51G-1 tests)
# ═══════════════════════════════════════════════════════════════════════════

class TestBehaviorsPreserved:
    """All 15 characterized behaviors from Phase 51G-1 must remain
    preserved after the service extraction.
    """

    def test_behavior_1_post_save_run_exists_in_main_web(self):
        assert '@app.post("/save-run")' in _read(MAIN_WEB)

    def test_behavior_5_user_id_derived_from_session_in_service(self):
        """Behavior 5: user_id = user.user_id (NEVER from form)."""
        text = _read(SERVICE)
        # Strip docstring
        clean = _strip_docstrings_and_comments(text)
        assert "user_id = user.user_id" in clean
        assert 'form.get("user_id' not in clean

    def test_behavior_6_exact_9_input_fields(self):
        """Behavior 6: exactly 9 input fields."""
        text = _read(SERVICE)
        clean = _strip_docstrings_and_comments(text)
        for field in [
            "capacity_mw", "tariff_eur_mwh", "p50_hours",
            "total_capex_keur", "opex_y1_keur", "gearing_pct",
            "target_dscr", "interest_rate_pct", "tenor_years",
        ]:
            assert f'"{field}"' in clean, (
                f"save_run_service must read form field {field!r}"
            )

    def test_behavior_9_check_runtime_allowed_3_tuple(self):
        """Behavior 9: unpack 3-tuple from check_runtime_allowed."""
        text = _read(SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "allow_run, runtime_origin, guard_message" in clean

    def test_behavior_10_two_branches_user_created_factory_template(self):
        """Behavior 10: branch on project_origin."""
        text = _read(SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert 'project_record.project_origin == "user_created"' in clean
        # Else branch implicit (no explicit `else` is fine)

    def test_behavior_11_factory_template_maps_template_source(self):
        """Behavior 11: factory_template branch maps template_source
        to runtime key (tuho / oborovo / Solar / Wind)."""
        text = _read(SERVICE)
        clean = _strip_docstrings_and_comments(text)
        # In the service, the helper is invoked as
        # ``deps.normalize_template_source(...)`` (deps-bundle style).
        assert "normalize_template_source" in clean
        assert 'runtime_seed == "tuho"' in clean
        assert 'runtime_seed == "oborovo"' in clean

    def test_behavior_12_model_execution_broad_except(self):
        """Behavior 12: model execution wrapped in broad except Exception."""
        text = _read(SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "except Exception as e:" in clean
        assert "Model error:" in clean

    def test_behavior_15_all_responses_save_result_html_with_hx_trigger(self):
        """Behavior 15: all non-auth responses use save_result.html +
        HX-Trigger: refreshHistory."""
        # The service uses partials/save_result.html as default template
        # and HX-Trigger: refreshHistory as default header.
        from app.services.save_run_service import SaveRunRouteOutcome
        o = SaveRunRouteOutcome()
        assert o.template_name == "partials/save_result.html"
        assert o.headers["HX-Trigger"] == "refreshHistory"


# ═══════════════════════════════════════════════════════════════════════════
# 6. Quirks preserved
# ═══════════════════════════════════════════════════════════════════════════

class TestQuirksPreserved:
    """All 7 characterized quirks from Phase 51G-1 must remain
    preserved after the service extraction.
    """

    def test_quirk_1_user_created_branch_undefined_function_preserved(self):
        """Quirk 1: user_created branch references
        _clean_user_project_runtime_snapshot which is NOT defined.

        The bug is preserved in 51G-2 (NOT fixed)."""
        text = _read(SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "_clean_user_project_runtime_snapshot" in clean, (
            "save_run_service must still reference the undefined "
            "_clean_user_project_runtime_snapshot (preserved latent bug)"
        )
        # The function must STILL NOT be defined in the service
        assert "def _clean_user_project_runtime_snapshot" not in clean, (
            "_clean_user_project_runtime_snapshot must NOT be defined — "
            "the latent bug is preserved, not fixed in 51G-2"
        )

    def test_quirk_2_runtime_origin_captured_but_not_mutated(self):
        """Quirk 2: runtime_origin is captured but not used to mutate state."""
        text = _read(SERVICE)
        clean = _strip_docstrings_and_comments(text)
        # The 3-tuple unpacks runtime_origin
        assert "allow_run, runtime_origin, guard_message" in clean
        # runtime_origin is passed to the latent bug function
        # (which raises NameError) — not used to mutate state directly
        # before the bug call
        # (the only references to runtime_origin are the unpack and the
        # call to _clean_user_project_runtime_snapshot)
        assert clean.count("runtime_origin") >= 2

    def test_quirk_3_save_project_runtime_timestamp_locked_to_run(self):
        """Quirk 3: save_project.runtime_timestamp = run_record.created_at
        (NOT utc_now_iso)."""
        text = _read(SERVICE)
        clean = _strip_docstrings_and_comments(text)
        # The save_project call must use run_record.created_at.isoformat()
        assert "run_record.created_at.isoformat()" in clean
        # And the save_run call uses deps.utc_now_iso() (not run_record...)
        # The two are different timestamps but the project is locked
        # to the run's timestamp.
        assert "deps.utc_now_iso()" in clean

    def test_quirk_4_save_project_project_id_explicit_none(self):
        """Quirk 4: save_project.replay_metadata.project_id is explicitly None."""
        text = _read(SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "project_id=None" in clean

    def test_quirk_5_all_non_auth_responses_use_same_template(self):
        """Quirk 5: all 4 non-auth responses use partials/save_result.html."""
        from app.services.save_run_service import SaveRunRouteOutcome
        o = SaveRunRouteOutcome()
        assert o.template_name == "partials/save_result.html"

    def test_quirk_6_validate_form_uses_static_sets(self):
        """Quirk 6: _validate_form uses hardcoded PROJECT_TYPES / SCENARIOS."""
        # The deps bundle carries project_types and scenarios as lists
        from app.services.save_run_service import SaveRunRouteDeps
        import dataclasses
        fields = {f.name for f in dataclasses.fields(SaveRunRouteDeps)}
        assert "project_types" in fields
        assert "scenarios" in fields

    def test_quirk_7_save_run_before_save_project(self):
        """Quirk 7: save_run called before save_project (ordering pinned)."""
        text = _read(SERVICE)
        clean = _strip_docstrings_and_comments(text)
        run_pos = clean.find("deps.save_run(")
        proj_pos = clean.find("deps.save_project(")
        assert run_pos != -1
        assert proj_pos != -1
        assert run_pos < proj_pos, (
            "save_run must be called before save_project in the service"
        )


# ═══════════════════════════════════════════════════════════════════════════
# 7. Intended persistence side effects preserved
# ═══════════════════════════════════════════════════════════════════════════

class TestIntendedPersistencePreserved:
    """Intended runtime persistence writes (NOT forbidden) are preserved."""

    def test_save_run_called_with_correct_kwargs(self):
        text = _read(SERVICE)
        clean = _strip_docstrings_and_comments(text)
        # The save_run call must use these kwargs
        for kw in [
            "user_id=user_id",
            "project_type=effective_project_type",
            "scenario=scenario",
            "inputs=inputs",
            "kpis=kpis",
        ]:
            assert kw in clean, f"save_run call must use {kw}"

    def test_save_run_replay_metadata_export_type(self):
        """save_run.replay_metadata.export_type = 'saved_run_metadata'."""
        text = _read(SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert '"saved_run_metadata"' in clean

    def test_save_project_called_with_correct_kwargs(self):
        text = _read(SERVICE)
        clean = _strip_docstrings_and_comments(text)
        for kw in [
            "user_id=user_id",
            "project_code=project_code",
            "project_name=project_name",
            "source_project_template=project_code",
            "last_run_summary=kpis",
        ]:
            assert kw in clean, f"save_project call must use {kw}"

    def test_save_project_replay_metadata_export_type(self):
        """save_project.replay_metadata.export_type = 'saved_run_project_state'."""
        text = _read(SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert '"saved_run_project_state"' in clean

    def test_save_run_in_service_count_is_one(self):
        """save_run(...) call appears exactly once in the service."""
        text = _read(SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert clean.count("deps.save_run(") == 1, (
            f"save_run call count is {clean.count('deps.save_run(')}, expected 1"
        )

    def test_save_project_in_service_count_is_one(self):
        """save_project(...) call appears exactly once in the service."""
        text = _read(SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert clean.count("deps.save_project(") == 1, (
            f"save_project call count is {clean.count('deps.save_project(')}, expected 1"
        )


# ═══════════════════════════════════════════════════════════════════════════
# 8. Forbidden side effects remain absent
# ═══════════════════════════════════════════════════════════════════════════

class TestForbiddenSideEffectsAbsent:
    """Forbidden side effects (Phase 51G-1 documented) must not be
    introduced by the service extraction.
    """

    FORBIDDEN = [
        "record_export",
        "record_download_export",
        "record_runtime_summary_export",
        "record_institutional_workbook_export",
        "record_workspace_runtime",
        "update_scenario_last_run_summary",
    ]

    @pytest.mark.parametrize(
        "forbidden",
        FORBIDDEN,
        ids=lambda v: v if isinstance(v, str) else v[0],
    )
    def test_service_does_not_call_forbidden_helper(self, forbidden):
        text = _read(SERVICE)
        clean = _strip_docstrings_and_comments(text)
        # Check for actual call (not just docstring/comment)
        # A call is `forbidden_name(` or `forbidden_name.`
        call_pattern = re.compile(rf"\.?{re.escape(forbidden)}\s*\(")
        assert not call_pattern.search(clean), (
            f"save_run_service must not call {forbidden} (forbidden side effect)"
        )

    def test_service_does_not_use_db_or_session(self):
        text = _read(SERVICE)
        clean = _strip_docstrings_and_comments(text)
        for forbidden in ("db.add", "db.commit", "db.flush",
                          "session.add", "session.commit"):
            assert forbidden not in clean, (
                f"save_run_service must not use {forbidden} (uses repository fns)"
            )


# ═══════════════════════════════════════════════════════════════════════════
# 9. Phase 51F guardrails remain green
# ═══════════════════════════════════════════════════════════════════════════

class TestPhase51FGuardrails:
    """Phase 51F guardrails must remain green after 51G-2."""

    def test_phase51f_guardrails_test_module_exists(self):
        path = REPO_ROOT / "tests" / "test_phase51f_parallel_work_guardrails.py"
        assert path.is_file()

    def test_no_service_imports_main_web_or_main_api(self):
        """All app/services/*.py must not import main_web/main_api."""
        # This is the Phase 51F guardrail #3; re-verified here.
        import ast
        services_dir = REPO_ROOT / "app" / "services"
        offenders = []
        for path in sorted(services_dir.glob("*.py")):
            src = path.read_text()
            tree = ast.parse(src)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.split(".")[0] in ("main_web", "main_api"):
                            offenders.append(
                                f"{path.relative_to(REPO_ROOT)}:{node.lineno}: import {alias.name}"
                            )
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.module.split(".")[0] in ("main_web", "main_api"):
                        offenders.append(
                            f"{path.relative_to(REPO_ROOT)}:{node.lineno}: from {node.module}"
                        )
        assert not offenders, (
            "No service may import main_web or main_api:\n  " +
            "\n  ".join(offenders)
        )

    def test_parity_core_files_unchanged(self):
        """Parity-core files (4 locked) must not have changed SHA-256."""
        import hashlib
        expected = {
            "app/waterfall_core.py": "d8ab56fdb5c01847be605f68a3710c14ddf91f097db86a107e2073eebff21a63",
            "app/project_factories.py": "1b795b96bfaf3e2795d6e5c389c447cd8c157de720e13ebab0484949b387258a",
            "reports/phase7_tuho_senior_debt_sizing_extraction.csv": "80e79977f039310158b084e2613ae17251a86916b970d4fda1985467bbde3442",
            "reports/phase23q_oborovo_senior_debt_sizing_extraction.csv": "8afdad21025df890b2103c73e40423bb6e4a99f755a94c9fec7b68f1cc3f58f6",
        }
        for relpath, expected_sha in expected.items():
            actual_sha = hashlib.sha256(
                (REPO_ROOT / relpath).read_bytes()
            ).hexdigest()
            assert actual_sha == expected_sha, (
                f"Parity-core file {relpath} SHA-256 changed: "
                f"expected {expected_sha}, got {actual_sha}"
            )


# ═══════════════════════════════════════════════════════════════════════════
# 10. Latent bug NOT fixed
# ═══════════════════════════════════════════════════════════════════════════

class TestLatentBugNotFixed:
    """_clean_user_project_runtime_snapshot latent bug is preserved
    (NOT fixed in 51G-2). A separate Phase 51G-3 bugfix PR is
    recommended with explicit user sign-off.
    """

    def test_service_does_not_define_clean_user_project_runtime_snapshot(self):
        text = _read(SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "def _clean_user_project_runtime_snapshot" not in clean, (
            "Latent bug fix is NOT in scope for 51G-2. The function "
            "must remain undefined in the service (preserved as "
            "pre-existing latent bug)."
        )

    def test_service_does_not_inject_a_stub_for_clean_user_project_runtime(self):
        """No stub like lambda *_: {} or returning {}"""
        text = _read(SERVICE)
        clean = _strip_docstrings_and_comments(text)
        # If a stub were injected, we would see a deps field for it.
        # We do not want a stub.
        from app.services.save_run_service import SaveRunRouteDeps
        import dataclasses
        fields = {f.name for f in dataclasses.fields(SaveRunRouteDeps)}
        assert "clean_user_project_runtime_snapshot" not in fields, (
            "Latent bug stub is NOT in scope for 51G-2. The deps bundle "
            "must NOT include a clean_user_project_runtime_snapshot "
            "field."
        )

    def test_latent_bug_documented_in_service_module(self):
        """The service module must document the latent bug."""
        text = _read(SERVICE)
        # Documentation can be in the module docstring
        assert "latent bug" in text.lower() or "preserved as" in text.lower(), (
            "Service must document the latent bug preservation in 51G-2"
        )

    def test_latent_bug_pinned_in_test_phase51g1(self):
        """The latent bug must still be pinned by Phase 51G-1 tests."""
        text = _read(REPO_ROOT / "tests" / "test_phase51g1_save_run_route_golden_characterization.py")
        assert "latent_name_error" in text
        assert "_clean_user_project_runtime_snapshot" in text


# ═══════════════════════════════════════════════════════════════════════════
# 11. Other services remain intact
# ═══════════════════════════════════════════════════════════════════════════

class TestOtherServicesIntact:
    """Other extracted services must remain unchanged by 51G-2."""

    @pytest.mark.parametrize(
        "service_file",
        [
            "run_service.py",
            "compare_service.py",
            "validation_service.py",
            "download_service.py",
        ],
    )
    def test_other_service_files_still_exist(self, service_file):
        path = REPO_ROOT / "app" / "services" / service_file
        assert path.is_file(), f"Service {service_file} must still exist"


# ═══════════════════════════════════════════════════════════════════════════
# 12. Phase 51G-1 golden characterization still passes (smoke)
# ═══════════════════════════════════════════════════════════════════════════

class TestPhase51G1Smoke:
    """Smoke: Phase 51G-1 test module must still be importable and
    pass after the 51G-2 re-pointing.
    """

    def test_phase51g1_test_module_exists(self):
        path = REPO_ROOT / "tests" / "test_phase51g1_save_run_route_golden_characterization.py"
        assert path.is_file()

    def test_phase51g1_test_module_runs_cleanly(self):
        """The 51G-1 test module must be runnable. We do a smoke
        import only (full run is in CI).
        """
        import importlib
        mod = importlib.import_module("tests.test_phase51g1_save_run_route_golden_characterization")
        assert mod is not None


# ═══════════════════════════════════════════════════════════════════════════
# 13. Phase 51G-2 self-inventory
# ═══════════════════════════════════════════════════════════════════════════

class TestPhase51G2SelfInventory:
    """The Phase 51G-2 deliverables must all be present."""

    def test_phase51g2_docs_exists(self):
        path = REPO_ROOT / "docs" / "phase51g2_save_run_route_vertical_extraction.md"
        assert path.is_file(), f"Required docs file {path} not found"

    def test_phase51g2_summary_json_exists(self):
        path = REPO_ROOT / "reports" / "phase51g2_save_run_route_vertical_extraction_summary.json"
        assert path.is_file(), f"Required summary file {path} not found"

    def test_phase51g2_docs_mention_route_size(self):
        path = REPO_ROOT / "docs" / "phase51g2_save_run_route_vertical_extraction.md"
        text = _read(path)
        # Should mention the route's new size
        assert "58" in text or "non-blank" in text.lower(), (
            "Docs must mention /save-run route size after extraction"
        )

    def test_phase51g2_docs_mention_latent_bug(self):
        path = REPO_ROOT / "docs" / "phase51g2_save_run_route_vertical_extraction.md"
        text = _read(path)
        # Must mention the latent bug preservation
        assert "latent" in text.lower() or "_clean_user_project_runtime_snapshot" in text, (
            "Docs must mention the latent bug preservation"
        )
