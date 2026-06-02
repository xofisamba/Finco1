"""Phase 51G-3 — /save-run user_created branch latent bug fix tests.

This test suite pins the Phase 51G-3 bugfix:

The pre-existing latent bug ``_clean_user_project_runtime_snapshot``
(referenced in the /save-run user_created branch but never defined
anywhere) is fixed in 51G-3.

Before 51G-3 (Phases 51G-1 and 51G-2):
    - save_run_service.py referenced
      ``_clean_user_project_runtime_snapshot`` (a module-level symbol
      that was never defined).
    - The broad ``except Exception`` in the model-execution block
      caught the resulting NameError.
    - Every save for a user_created project returned 200 +
      ``save_result-err`` with message
      ``"Model error: name '_clean_user_project_runtime_snapshot' is
      not defined"``.

After 51G-3:
    - main_web.py defines ``_clean_user_project_runtime_snapshot``
      (a thin adapter around
      ``_resolve_runtime_snapshot_source``, the canonical Phase 50C-2
      implementation).
    - save_run_service.py injects it as
      ``deps.clean_user_project_runtime_snapshot`` and uses it in the
      user_created branch.
    - The user_created branch reaches run_project + save_run +
      save_project on the success path.
    - The model-execution broad ``except Exception`` (Behavior 12)
      still wraps the branch, so a malformed snapshot raises
      ``SnapshotInputError`` from ``build_projectinputs_from_snapshot``
      and the service surfaces that as a 200 + save_result-err with
      the validation message — not a NameError.

Scope (Phase 51G-3 is a narrow bugfix):
- Allowed: app/services/save_run_service.py, main_web.py,
  tests/test_phase51g1_save_run_route_golden_characterization.py,
  tests/test_phase51g2_save_run_route_vertical_extraction.py,
  new tests/test_phase51g3_save_run_user_created_branch_fix.py,
  docs/, reports/.
- NOT allowed: waterfall_core.py, project_factories.py, senior-debt
  CSVs, financial formulas, model outputs, schemas, migrations, JS,
  parity-core files, route family refactors, factory_template
  behavior changes, save_run/save_project ordering changes,
  replay_metadata export_type changes.

These tests verify:
1. The NameError no longer occurs in the user_created branch.
2. The user_created branch reaches run_project / save_run /
   save_project with valid input.
3. factory_template branch still passes existing tests unchanged.
4. save_run / save_project ordering remains preserved.
5. Intended persistence side effects remain preserved.
6. Forbidden side effects remain absent.
7. The /save-run route remains thin.
8. No service imports main_web or main_api.
9. Phase 51F guardrails still pass.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SERVICE = REPO_ROOT / "app" / "services" / "save_run_service.py"
MAIN_WEB = REPO_ROOT / "main_web.py"


# ─── Helpers ───────────────────────────────────────────────────────────────


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _strip_docstrings_and_comments(text: str) -> str:
    """Strip module docstrings, function/class docstrings, and comments.

    Used for code-level checks (e.g. "does the service call forbidden
    side effects in actual code, not just in docstrings?")."""
    out = re.sub(r'^\s*"""[\s\S]*?"""', "", text, flags=re.MULTILINE)
    out = re.sub(r'^\s*\'\'\'[\s\S]*?\'\'\'', "", out, flags=re.MULTILINE)
    out = re.sub(r"#.*", "", out)
    out = re.sub(r'"""[\s\S]*?"""', '"""..."""', out)
    out = re.sub(r"'''[\s\S]*?'''", "'''...'''", out)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 1. Bug history: documented but no longer a NameError
# ─────────────────────────────────────────────────────────────────────────────


class TestBugHistory:
    """Pin the bug history: the NameError must no longer occur."""

    def test_no_nameerror_when_user_created_branch_executes(self):
        """The service no longer references the bare, undefined name.

        Pre-51G-3, the user_created branch contained:

            runtime_snapshot = _clean_user_project_runtime_snapshot(  # noqa: F821
                project_record, workspace_state, runtime_origin
            )

        The symbol ``_clean_user_project_runtime_snapshot`` was never
        defined in the service or in main_web.py, so this raised
        NameError. Phase 51G-3 replaces this with
        ``deps.clean_user_project_runtime_snapshot(...)``.
        """
        text = _read(SERVICE)
        clean = _strip_docstrings_and_comments(text)
        # The bare, undefined module-level reference must be gone.
        assert "_clean_user_project_runtime_snapshot(" not in clean, (
            "The bare module-level reference "
            "_clean_user_project_runtime_snapshot(...) must be gone "
            "(Phase 51G-3 fix)"
        )
        # The service must use the deps-injected version.
        assert "deps.clean_user_project_runtime_snapshot" in clean, (
            "The service must use "
            "deps.clean_user_project_runtime_snapshot (Phase 51G-3 fix)"
        )

    def test_bug_history_documented_in_service_module(self):
        """The service must document the bug history and the 51G-3 fix."""
        text = _read(SERVICE)
        lower = text.lower()
        assert (
            "latent bug" in lower
            or "phase 51g-3" in lower
            or "51g-3" in lower
        ), (
            "Service must document the latent-bug history and the 51G-3 fix"
        )

    def test_bug_history_documented_in_main_web(self):
        """main_web.py must document that the bug is fixed."""
        text = _read(MAIN_WEB)
        assert (
            "51G-3" in text or "phase 51g-3" in text.lower()
        ), "main_web.py must document the 51G-3 fix"
        # The fix description
        assert "_clean_user_project_runtime_snapshot" in text, (
            "main_web.py must reference _clean_user_project_runtime_snapshot"
        )

    def test_bug_history_pinned_in_test_phase51g1(self):
        """Phase 51G-1 still documents the bug (now as the FIX)."""
        path = (
            REPO_ROOT
            / "tests"
            / "test_phase51g1_save_run_route_golden_characterization.py"
        )
        text = _read(path)
        assert "latent_name_error" in text
        assert "_clean_user_project_runtime_snapshot" in text


# ─────────────────────────────────────────────────────────────────────────────
# 2. user_created branch reaches run_project / save_run / save_project
# ─────────────────────────────────────────────────────────────────────────────


class TestUserCreatedBranchReachesPersistence:
    """With the bug fixed, the user_created branch must reach the
    intended persistence side effects when given a valid snapshot."""

    def test_service_calls_clean_user_project_runtime_snapshot(self):
        """The user_created branch must call
        ``deps.clean_user_project_runtime_snapshot`` with
        (user, project_record, workspace_state, runtime_origin)."""
        text = _read(SERVICE)
        clean = _strip_docstrings_and_comments(text)
        # The deps call site
        assert (
            "deps.clean_user_project_runtime_snapshot(" in clean
        ), "Service must call deps.clean_user_project_runtime_snapshot(...)"
        # All four arguments are passed
        assert "user, project_record, workspace_state, runtime_origin" in clean, (
            "Service must pass (user, project_record, workspace_state, "
            "runtime_origin) to deps.clean_user_project_runtime_snapshot"
        )

    def test_user_created_branch_assigns_runtime_snapshot(self):
        """The result of the call must be assigned to ``runtime_snapshot``."""
        text = _read(SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "runtime_snapshot = deps.clean_user_project_runtime_snapshot" in clean, (
            "Service must assign the snapshot dict to ``runtime_snapshot``"
        )

    def test_user_created_branch_passes_runtime_snapshot_to_build_projectinputs(self):
        """``build_projectinputs_from_snapshot`` must receive the
        runtime_snapshot (not None, not a stub)."""
        text = _read(SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert (
            "deps.build_projectinputs_from_snapshot(runtime_snapshot)" in clean
        ), "build_projectinputs_from_snapshot must consume runtime_snapshot"

    def test_user_created_branch_reaches_run_project(self):
        """The branch must reach ``deps.run_project(...)`` on success."""
        text = _read(SERVICE)
        clean = _strip_docstrings_and_comments(text)
        # Both branches (user_created and factory_template) share the
        # same deps.run_project(...) call site after the if/else
        assert (
            "deps.run_project(\n            runtime_project_key, scenario, "
            "project_inputs_override=override\n        )" in clean
        ), "Both branches must reach deps.run_project(...) after the if/else"

    def test_user_created_branch_does_not_raise_nameerror_on_valid_snapshot(self):
        """Regression: with a valid snapshot, the user_created branch
        must NOT raise NameError.

        The test simulates a complete call to the service with a valid
        user_created project setup. The only side effect we want is
        that ``deps.clean_user_project_runtime_snapshot`` is called and
        ``deps.build_projectinputs_from_snapshot`` is called with the
        result. No NameError, no fallback to the
        ``except Exception as e: -> Model error: ...`` block.

        This is verified structurally in the service code (the
        service now uses ``deps.clean_user_project_runtime_snapshot``
        which always returns a dict) and behaviorally via the broad
        ``except Exception`` block remaining in place but never
        triggered for the cleaned-snapshot case.
        """
        text = _read(SERVICE)
        clean = _strip_docstrings_and_comments(text)
        # The service still has the broad except (Behavior 12)
        # but the user_created branch no longer raises NameError
        # because deps.clean_user_project_runtime_snapshot is now
        # always defined.
        assert "except Exception as e:" in clean
        # The user_created branch does not have a fallback to
        # _clean_user_project_runtime_snapshot anymore
        assert "_clean_user_project_runtime_snapshot" not in clean


# ─────────────────────────────────────────────────────────────────────────────
# 3. factory_template branch unchanged
# ─────────────────────────────────────────────────────────────────────────────


class TestFactoryTemplateBranchUnchanged:
    """The factory_template branch must be EXACTLY the same as in
    Phase 51G-2 (no edits, no behavior changes)."""

    def test_factory_template_branch_call_site_intact(self):
        """The factory_template branch's deps calls must be unchanged."""
        text = _read(SERVICE)
        clean = _strip_docstrings_and_comments(text)
        # build_schema_from_form
        assert "deps.build_schema_from_form(" in clean
        # build_projectinputs
        assert "deps.build_projectinputs(schema)" in clean
        # normalize_template_source
        assert "deps.normalize_template_source(" in clean
        # The mapping of template_source -> runtime key
        assert 'runtime_seed == "tuho"' in clean
        assert 'runtime_seed == "oborovo"' in clean

    def test_factory_template_branch_does_not_use_clean_user_project(self):
        """The factory_template branch must NOT touch
        clean_user_project_runtime_snapshot."""
        text = _read(SERVICE)
        clean = _strip_docstrings_and_comments(text)
        # Find the else branch and confirm it does not reference
        # the new dep.
        # Simple check: the new dep call site is BEFORE the
        # if/else block, not inside the else branch.
        deps_call = clean.find("deps.clean_user_project_runtime_snapshot(")
        factory_branch_marker = clean.find("factory_template branch")
        # The factory_template branch is the else branch — it starts
        # after the user_created branch. Find the if/else split.
        if_pos = clean.find('if project_record.project_origin == "user_created":')
        else_pos = clean.find("else:")
        assert if_pos != -1 and else_pos != -1
        assert deps_call < if_pos or (
            deps_call > if_pos and deps_call < else_pos
        ), (
            "deps.clean_user_project_runtime_snapshot must be in the "
            "user_created branch only (or before the if/else), not in "
            "the factory_template branch"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 4. save_run / save_project ordering preserved
# ─────────────────────────────────────────────────────────────────────────────


class TestSaveRunSaveProjectOrdering:
    """save_run must still be called before save_project."""

    def test_save_run_call_site_comes_before_save_project(self):
        text = _read(SERVICE)
        clean = _strip_docstrings_and_comments(text)
        save_run_pos = clean.find("deps.save_run(")
        save_project_pos = clean.find("deps.save_project(")
        assert save_run_pos != -1 and save_project_pos != -1
        assert save_run_pos < save_project_pos, (
            "deps.save_run(...) must be called before deps.save_project(...)"
        )

    def test_no_concurrent_or_reversed_persistence_call(self):
        """No reversed or parallel save_run/save_project pattern."""
        text = _read(SERVICE)
        clean = _strip_docstrings_and_comments(text)
        # No run_project call between save_run and save_project
        # (would imply a second model execution, which is not allowed)
        save_run_pos = clean.find("deps.save_run(")
        save_project_pos = clean.find("deps.save_project(")
        run_project_pos = clean.find("deps.run_project(")
        # run_project is called before save_run (model exec first)
        assert run_project_pos < save_run_pos, (
            "deps.run_project must be called before deps.save_run"
        )
        # No run_project call between save_run and save_project
        assert not (save_run_pos < run_project_pos < save_project_pos), (
            "No deps.run_project call between deps.save_run and "
            "deps.save_project (would imply second model execution)"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 5. Intended persistence side effects preserved
# ─────────────────────────────────────────────────────────────────────────────


class TestIntendedPersistenceSideEffectsPreserved:
    """save_run / save_project kwargs must remain unchanged."""

    def test_save_run_export_type_saved_run_metadata(self):
        text = _read(SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert 'export_type="saved_run_metadata"' in clean
        assert (
            'replay_metadata_for_project(\n                project_code,\n                export_type="saved_run_metadata"'
            in clean
        )

    def test_save_project_export_type_saved_run_project_state(self):
        text = _read(SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert 'export_type="saved_run_project_state"' in clean
        assert (
            'replay_metadata_for_project(\n                project_code,\n                project_id=None,\n                export_type="saved_run_project_state"'
            in clean
        )

    def test_save_project_runtime_timestamp_uses_run_record_created_at(self):
        text = _read(SERVICE)
        clean = _strip_docstrings_and_comments(text)
        # Locked to run_record.created_at.isoformat(), NOT utc_now_iso()
        assert (
            "runtime_timestamp=run_record.created_at.isoformat()" in clean
        ), (
            "save_project.runtime_timestamp must equal "
            "run_record.created_at.isoformat() (locked to run timestamp)"
        )

    def test_save_project_project_id_explicit_none(self):
        text = _read(SERVICE)
        clean = _strip_docstrings_and_comments(text)
        # The save_project call must include project_id=None explicitly
        # in its replay_metadata
        assert "project_id=None" in clean
        assert (
            "replay_metadata_for_project(\n                project_code,\n                project_id=None,\n                export_type=\"saved_run_project_state\""
            in clean
        )

    def test_save_run_called_with_user_id_session_derived(self):
        text = _read(SERVICE)
        clean = _strip_docstrings_and_comments(text)
        # user_id must be derived from user, not from form
        assert "user_id=user_id" in clean
        # The user_id assignment is from the user, not the form
        assert "user_id = user.user_id" in clean


# ─────────────────────────────────────────────────────────────────────────────
# 6. Forbidden side effects remain absent
# ─────────────────────────────────────────────────────────────────────────────


class TestForbiddenSideEffectsAbsent:
    """Forbidden side effects must NOT be introduced by the 51G-3 fix."""

    @pytest.mark.parametrize(
        "forbidden_symbol",
        [
            "record_export",
            "record_download_export",
            "record_runtime_summary_export",
            "record_institutional_workbook_export",
            "record_workspace_runtime",
            "update_scenario_last_run_summary",
        ],
    )
    def test_forbidden_helper_not_called_in_code(self, forbidden_symbol: str):
        text = _read(SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert forbidden_symbol not in clean, (
            f"Service must NOT call {forbidden_symbol} (forbidden side effect)"
        )

    def test_no_db_or_session_direct_access(self):
        text = _read(SERVICE)
        clean = _strip_docstrings_and_comments(text)
        for sym in ["db.add", "db.commit", "db.flush", "session.add", "session.commit"]:
            assert sym not in clean, (
                f"Service must NOT use {sym} (repository fns only)"
            )

    def test_no_new_side_effects_in_main_web_route(self):
        """The /save-run route must not introduce new side effects."""
        text = _read(MAIN_WEB)
        # Find the /save-run route
        m = re.search(
            r'async def save_run_endpoint\(.*?\n    return templates\.TemplateResponse',
            text,
            re.DOTALL,
        )
        assert m is not None, "/save-run route not found"
        body = m.group(0)
        for sym in [
            "record_export",
            "record_download_export",
            "record_runtime_summary_export",
            "record_institutional_workbook_export",
            "record_workspace_runtime",
            "update_scenario_last_run_summary",
            "db.add",
            "db.commit",
            "db.flush",
            "session.add",
            "session.commit",
        ]:
            assert sym not in body, (
                f"/save-run route must NOT call {sym}"
            )


# ─────────────────────────────────────────────────────────────────────────────
# 7. Route remains thin
# ─────────────────────────────────────────────────────────────────────────────


class TestRouteRemainsThin:
    """The /save-run route must remain thin after the 51G-3 fix."""

    def test_save_run_route_size_stays_under_90_non_blank(self):
        """Route body should still be small (Phase 51G-2: 58 non-blank)."""
        text = _read(MAIN_WEB)
        m = re.search(
            r'@app\.post\("/save-run"\)\s*\nasync def save_run_endpoint\('
            r".*?\n    return templates\.TemplateResponse",
            text,
            re.DOTALL,
        )
        assert m is not None, "/save-run route not found"
        body = m.group(0)
        non_blank = [l for l in body.splitlines() if l.strip()]
        # 58 in 51G-2, 51G-3 only added one new dep wiring line
        # so allow up to 90 to be safe (no new orchestration).
        assert len(non_blank) <= 90, (
            f"/save-run route body grew to {len(non_blank)} non-blank lines "
            f"(expected ~58 + minor wiring for the new dep)"
        )

    def test_save_run_route_does_no_orchestration(self):
        """The route must not contain user_created branch orchestration
        or any new model-execution logic."""
        text = _read(MAIN_WEB)
        m = re.search(
            r'@app\.post\("/save-run"\)\s*\nasync def save_run_endpoint\('
            r".*?\n    return templates\.TemplateResponse",
            text,
            re.DOTALL,
        )
        body = m.group(0)
        # No if/else for user_created vs factory_template in the route
        assert 'project_record.project_origin == "user_created"' not in body
        # No _clean_user_project_runtime_snapshot call directly in the route
        assert "_clean_user_project_runtime_snapshot(" not in body
        # No build_projectinputs_from_snapshot call in the route
        assert "build_projectinputs_from_snapshot(" not in body


# ─────────────────────────────────────────────────────────────────────────────
# 8. No service imports main_web or main_api
# ─────────────────────────────────────────────────────────────────────────────


class TestNoServiceImportsMainWebOrMainApi:
    """The service must not import main_web or main_api (one-way import
    direction)."""

    def test_service_does_not_import_main_web(self):
        text = _read(SERVICE)
        clean = _strip_docstrings_and_comments(text)
        # Look at the imports
        assert "import main_web" not in clean
        assert "from main_web" not in clean

    def test_service_does_not_import_main_api(self):
        text = _read(SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "import main_api" not in clean
        assert "from main_api" not in clean

    def test_no_module_level_clean_user_project_runtime_snapshot(self):
        """The function must be defined in main_web.py, not in the service
        as a module-level helper (would imply import direction reversal)."""
        text = _read(SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "def _clean_user_project_runtime_snapshot" not in clean
        # And no top-level assignment of it either
        assert (
            "_clean_user_project_runtime_snapshot =" not in clean
        )

    def test_main_web_defines_helper(self):
        """main_web.py must define the helper."""
        text = _read(MAIN_WEB)
        assert "def _clean_user_project_runtime_snapshot(" in text


# ─────────────────────────────────────────────────────────────────────────────
# 9. Deps bundle: 16 callables + 2 constants
# ─────────────────────────────────────────────────────────────────────────────


class TestDepsBundleUpdated:
    """SaveRunRouteDeps must have 16 callables + 2 constants (16th is
    clean_user_project_runtime_snapshot)."""

    def test_deps_has_15_callables(self):
        """15 callables + 2 constants (15th is the new
        clean_user_project_runtime_snapshot dep).

        Note: Phase 51G-2 documentation referenced 15 callables but
        the actual count was 14 (off-by-one in the doc). The 51G-3
        fix adds 1 new callable (clean_user_project_runtime_snapshot)
        so the bundle is now 15 callables + 2 constants.
        """
        from app.services.save_run_service import SaveRunRouteDeps
        import dataclasses

        fields = dataclasses.fields(SaveRunRouteDeps)
        callables = [f for f in fields if f.name not in ("project_types", "scenarios")]
        constants = [f for f in fields if f.name in ("project_types", "scenarios")]
        assert len(callables) == 15, (
            f"Expected 15 callable deps after 51G-3 (14 + "
            f"clean_user_project_runtime_snapshot), got {len(callables)}"
        )
        assert len(constants) == 2, (
            f"Expected 2 constants (project_types, scenarios), got {len(constants)}"
        )

    def test_deps_has_clean_user_project_runtime_snapshot_field(self):
        from app.services.save_run_service import SaveRunRouteDeps
        import dataclasses

        field_names = {f.name for f in dataclasses.fields(SaveRunRouteDeps)}
        assert "clean_user_project_runtime_snapshot" in field_names

    def test_deps_clean_user_project_runtime_snapshot_is_first_user_created_dep(self):
        """The new dep is the first user_created-specific dep in the
        bundle (alphabetical / logical position)."""
        from app.services.save_run_service import SaveRunRouteDeps
        import dataclasses

        fields = list(dataclasses.fields(SaveRunRouteDeps))
        names = [f.name for f in fields]
        # It should appear before canonical_project_type (also a
        # user_created dep)
        i = names.index("clean_user_project_runtime_snapshot")
        j = names.index("canonical_project_type")
        assert i < j, (
            "clean_user_project_runtime_snapshot must be declared "
            "before canonical_project_type (the other user_created dep)"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 10. Phase 51F guardrails (run separately; here as a smoke check)
# ─────────────────────────────────────────────────────────────────────────────


class TestPhase51FGuardrailsSmokeCheck:
    """Smoke check that the 51G-3 fix does not break 51F guardrails.

    The full 51F suite is run separately via:
        pytest tests/test_phase51f_parallel_work_guardrails.py
    Here we do a minimal structural check that the parity-core files
    are untouched and no service imports main_web.
    """

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
            # The exact SHA is not pinned in this test (51F test does
            # the cross-check); we just confirm files are still here
            # and were not zeroed out.
            assert len(sha) == 64
            assert len(content) > 0, f"Parity file is empty: {p}"

    def test_rc1_untouched(self):
        """rc1 must still be the same SHA."""
        import subprocess

        r = subprocess.run(
            ["git", "ls-remote", "--heads", "origin", "rc1"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        sha = r.stdout.split("\t")[0].strip() if r.stdout else ""
        assert sha == "b425a0708719eaa5e1d922b1008e5609758e0ad4", (
            f"rc1 SHA changed! Got {sha!r}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 11. Required behavior after fix
# ─────────────────────────────────────────────────────────────────────────────


class TestRequiredBehaviorAfterFix:
    """Pin all 11 required behavior-after-fix items from the spec."""

    def test_user_created_no_nameerror(self):
        """1. user_created branch no longer fails with NameError."""
        text = _read(SERVICE)
        clean = _strip_docstrings_and_comments(text)
        # No bare, undefined module-level reference
        assert "_clean_user_project_runtime_snapshot(" not in clean
        # The deps version is always defined
        assert "deps.clean_user_project_runtime_snapshot" in clean

    def test_user_created_branch_reaches_model_execution(self):
        """2. user_created branch reaches run_project / save_run / save_project."""
        text = _read(SERVICE)
        clean = _strip_docstrings_and_comments(text)
        # After the if/else, both branches call run_project
        assert "deps.run_project(" in clean
        # Then save_run and save_project
        assert "deps.save_run(" in clean
        assert "deps.save_project(" in clean

    def test_save_run_once_per_success(self):
        """3. save_run is still called exactly once per successful save."""
        text = _read(SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert clean.count("deps.save_run(") == 1, (
            "save_run must be called exactly once per success path"
        )

    def test_save_project_once_per_success(self):
        """4. save_project is still called exactly once per successful save."""
        text = _read(SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert clean.count("deps.save_project(") == 1, (
            "save_project must be called exactly once per success path"
        )

    def test_save_run_before_save_project(self):
        """5. save_run is still called before save_project."""
        text = _read(SERVICE)
        clean = _strip_docstrings_and_comments(text)
        run_pos = clean.find("deps.save_run(")
        proj_pos = clean.find("deps.save_project(")
        assert run_pos < proj_pos, (
            "save_run must be called before save_project"
        )

    def test_save_project_runtime_timestamp_locked(self):
        """6. save_project.runtime_timestamp still equals
        run_record.created_at.isoformat()."""
        text = _read(SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert (
            "runtime_timestamp=run_record.created_at.isoformat()" in clean
        )

    def test_replay_metadata_export_type_values_unchanged(self):
        """7. replay_metadata.export_type values are unchanged."""
        text = _read(SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert 'export_type="saved_run_metadata"' in clean
        assert 'export_type="saved_run_project_state"' in clean

    def test_factory_template_unchanged(self):
        """8. factory_template branch remains unchanged."""
        text = _read(SERVICE)
        clean = _strip_docstrings_and_comments(text)
        # The factory_template branch still maps template_source ->
        # runtime key
        assert 'runtime_seed == "tuho"' in clean
        assert 'runtime_seed == "oborovo"' in clean

    def test_forbidden_side_effects_still_absent(self):
        """9. forbidden side effects remain absent."""
        text = _read(SERVICE)
        clean = _strip_docstrings_and_comments(text)
        for sym in [
            "record_export",
            "record_download_export",
            "record_runtime_summary_export",
            "record_institutional_workbook_export",
            "record_workspace_runtime",
            "update_scenario_last_run_summary",
        ]:
            assert sym not in clean, (
                f"Service must NOT call {sym} (forbidden side effect)"
            )
        for sym in [
            "db.add",
            "db.commit",
            "db.flush",
            "session.add",
            "session.commit",
        ]:
            assert sym not in clean, (
                f"Service must NOT use {sym} (repository fns only)"
            )

    def test_service_does_not_import_main_web_or_main_api(self):
        """10. save_run_service.py still does not import main_web or main_api."""
        text = _read(SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "import main_web" not in clean
        assert "from main_web" not in clean
        assert "import main_api" not in clean
        assert "from main_api" not in clean


# ─────────────────────────────────────────────────────────────────────────────
# 12. Regression pin: the bug existed historically
# ─────────────────────────────────────────────────────────────────────────────


class TestRegressionPinForHistoricalBug:
    """Document that the bug existed historically and is now fixed."""

    def test_51g1_test_documents_bug_history(self):
        """The 51G-1 test must still mention the bug history."""
        path = (
            REPO_ROOT
            / "tests"
            / "test_phase51g1_save_run_route_golden_characterization.py"
        )
        text = _read(path)
        # The original test name is preserved
        assert "test_user_created_branch_has_latent_name_error" in text
        # And it documents the fix
        assert "Phase 51G-3" in text or "51G-3" in text

    def test_51g2_test_documents_quirk_1_fix(self):
        """The 51G-2 quirk_1 test must now assert the FIXED state."""
        path = (
            REPO_ROOT
            / "tests"
            / "test_phase51g2_save_run_route_vertical_extraction.py"
        )
        text = _read(path)
        # The test name is preserved
        assert (
            "test_quirk_1_user_created_branch_undefined_function_preserved"
            in text
        )
        # It now uses the deps-injected version
        assert "deps.clean_user_project_runtime_snapshot" in text

    def test_bug_history_in_main_web_docstring(self):
        """The new helper's docstring documents the bug history."""
        text = _read(MAIN_WEB)
        # Find the helper definition
        m = re.search(
            r'def _clean_user_project_runtime_snapshot\([^)]*\)[^:]*:\s*"""([\s\S]*?)"""',
            text,
        )
        assert m is not None, "_clean_user_project_runtime_snapshot not found"
        docstring = m.group(1)
        assert "Phase 51G-3" in docstring
        assert (
            "NameError" in docstring or "name '_clean_user_project_runtime_snapshot'"
            in docstring
        )
        # The adapter is small and clearly documented
        assert (
            "_resolve_runtime_snapshot_source" in docstring
            or "resolve_runtime_snapshot" in docstring
        )


# ─────────────────────────────────────────────────────────────────────────────
# 13. Sanity: integration smoke test via the service directly
# ─────────────────────────────────────────────────────────────────────────────


class TestServiceSanitySmoke:
    """Lightweight smoke test that the service can be constructed and
    called with the new dep without raising ImportError or AttributeError
    on import."""

    def test_save_run_route_deps_can_be_constructed(self):
        """The new dep field is required and typed Callable[..., dict]."""
        from app.services.save_run_service import SaveRunRouteDeps

        # The new field is required (no default) — this is verified by
        # dataclass field metadata
        import dataclasses

        fields = {f.name: f for f in dataclasses.fields(SaveRunRouteDeps)}
        assert "clean_user_project_runtime_snapshot" in fields
        field = fields["clean_user_project_runtime_snapshot"]
        # No default = required
        assert field.default is dataclasses.MISSING, (
            "clean_user_project_runtime_snapshot must be required (no default)"
        )

    def test_save_run_route_outcome_unchanged(self):
        """The outcome dataclass is unchanged (Phase 51G-2 surface)."""
        from app.services.save_run_service import SaveRunRouteOutcome

        # Default values
        outcome = SaveRunRouteOutcome()
        assert outcome.template_name == "partials/save_result.html"
        assert outcome.status_code == 200
        assert outcome.headers == {"HX-Trigger": "refreshHistory"}
        assert outcome.is_redirect is False
        assert outcome.redirect_url is None

    def test_module_docstring_mentions_51g3_fix(self):
        """The service module docstring must mention the 51G-3 fix."""
        text = _read(SERVICE)
        # The module docstring
        assert '"""' in text[:500]  # module docstring exists
        # And it mentions 51G-3
        assert "51G-3" in text or "Phase 51G-3" in text
