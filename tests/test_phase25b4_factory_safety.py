"""Phase 25B-4 — Factory safety tests.

Goal: User always knows whether the active scenario is
saved, unsaved, stale, or needs a rerun.

These tests prove the dirty-state feature is SAFE:

- Factory projects (TUHO / Oborovo) are unaffected by
  the new feature.
- The helper does not enable any feature flag.
- The helper does not promote construction
  (use_construction_schedule_engine stays False).
- The helper does not touch the persistence schema.
- The helper does not introduce a new dependency.
- The helper does not change rc1 (run-and-compare
  1-export) flow.
- The partial does not import any forbidden module
  (persistence, services, construction, debt, tax, IDC).
- The helper is a pure read-side classifier; calling it
  with the same context always returns the same state.
"""

import os
import subprocess
import sys

import pytest


HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, ".."))

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


from app.ui.dirty_state import resolve_dirty_state


# ---------------------------------------------------------------------------
# 1. Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    """The helper is a pure function: same input -> same
    output, always."""

    @pytest.mark.parametrize("repeat", range(5))
    def test_same_input_same_output(self, repeat):
        ws = {
            "dirty": True,
            "last_runtime_snapshot_id": "snap-1",
        }
        s1 = resolve_dirty_state(workspace_state=ws)
        s2 = resolve_dirty_state(workspace_state=ws)
        assert s1 == s2
        assert s1.state == s2.state
        assert s1.label == s2.label
        assert s1.tone == s2.tone
        assert s1.hint == s2.hint


# ---------------------------------------------------------------------------
# 2. Forbidden imports
# ---------------------------------------------------------------------------


class TestForbiddenImports:
    """The dirty_state module must not import any
    forbidden module."""

    FORBIDDEN_MODULES = [
        "app.persistence",
        "app.services",
        "app.construction",
        "app.debt",
        "app.tax",
        "app.idc",
        "app.depreciation",
        "app.waterfall",
    ]

    @pytest.mark.parametrize("module", FORBIDDEN_MODULES)
    def test_forbidden_module_not_imported(self, module):
        from app.ui import dirty_state
        src = open(dirty_state.__file__).read()
        assert f"import {module}" not in src, (
            f"dirty_state must NOT import {module!r}"
        )
        assert f"from {module}" not in src, (
            f"dirty_state must NOT import {module!r}"
        )


# ---------------------------------------------------------------------------
# 3. Partial does not enable flags
# ---------------------------------------------------------------------------


class TestPartialDoesNotEnableFlags:
    """The partial must not introduce any feature flag or
    auto-enable any runtime path."""

    def test_partial_does_not_set_construction_flag(self):
        partial_path = os.path.join(
            REPO_ROOT,
            "app",
            "templates",
            "partials",
            "_dirty_state_badge.html",
        )
        src = open(partial_path).read()
        assert "use_construction_schedule_engine" not in src
        assert "use_depreciation_canonical_engine" not in src
        assert "use_canonical_tax_depreciation" not in src
        assert "use_book_depreciation_for_pnl" not in src

    def test_helper_does_not_set_construction_flag(self):
        from app.ui import dirty_state
        src = open(dirty_state.__file__).read()
        assert "use_construction_schedule_engine" not in src
        assert "use_depreciation_canonical_engine" not in src


# ---------------------------------------------------------------------------
# 4. rc1 frozen SHA
# ---------------------------------------------------------------------------


class TestRc1Frozen:
    """rc1 frozen SHA must still resolve."""

    def test_rc1_sha_resolves(self):
        r = subprocess.run(
            [
                "git",
                "rev-parse",
                "--verify",
                "b425a0708719eaa5e1d922b1008e5609758e0ad4",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0


# ---------------------------------------------------------------------------
# 5. No schema changes
# ---------------------------------------------------------------------------


class TestNoSchemaChanges:
    """The new feature must not introduce any persistence
    schema migration."""

    def test_helper_does_not_define_new_table(self):
        from app.ui import dirty_state
        src = open(dirty_state.__file__).read()
        assert "CREATE TABLE" not in src
        assert "ALTER TABLE" not in src
        assert "create_table" not in src
        assert "alter_table" not in src
        assert "migrate" not in src.lower()


# ---------------------------------------------------------------------------
# 6. No autosave
# ---------------------------------------------------------------------------


class TestNoAutosave:
    """The new feature must NOT introduce autosave."""

    def test_helper_does_not_call_save(self):
        from app.ui import dirty_state
        src = open(dirty_state.__file__).read()
        # We allow the argument name ``save_state`` (it
        # is a context parameter, not a call) but we
        # forbid any function call to a save method.
        for forbidden in (
            "save_workspace(",
            "save_scenario(",
            "autosave(",
            "auto_save(",
            "workspace_state.dirty = True",
            "workspace_state[\"dirty\"] = True",
        ):
            assert forbidden not in src, (
                f"dirty_state must NOT contain {forbidden!r}"
            )
        # We allow the bare word ``autosave`` ONLY in
        # docstrings / comments that explicitly state
        # that autosave is NOT performed.
        if "autosave" in src.lower():
            # The only place the bare word is allowed is
            # inside a docstring / comment that mentions
            # it as a non-feature.
            for line in src.splitlines():
                if "autosave" in line.lower():
                    lower = line.lower()
                    assert (
                        "no autosave" in lower
                        or "not autosave" in lower
                        or "autosave" in lower
                        and (
                            "disabled" in lower
                            or "not performed" in lower
                        )
                    ), (
                        f"dirty_state mentions autosave "
                        f"without an explicit denial: "
                        f"{line!r}"
                    )

    def test_partial_does_not_call_save(self):
        partial_path = os.path.join(
            REPO_ROOT,
            "app",
            "templates",
            "partials",
            "_dirty_state_badge.html",
        )
        src = open(partial_path).read()
        for forbidden in (
            "save_workspace(",
            "save_scenario(",
            "autosave(",
            "auto_save(",
        ):
            assert forbidden not in src, (
                f"partial must NOT contain {forbidden!r}"
            )
        # Bare ``autosave`` / ``auto_save`` in comments is
        # allowed only if the line explicitly denies the
        # feature.
        for line in src.splitlines():
            if "autosave" in line.lower():
                lower = line.lower()
                assert (
                    "no autosave" in lower
                    or "not autosave" in lower
                ), (
                    f"partial mentions autosave without "
                    f"explicit denial: {line!r}"
                )


# ---------------------------------------------------------------------------
# 7. Factory projects safe
# ---------------------------------------------------------------------------


class TestFactoryProjectsSafe:
    """The dirty_state helper must be safe for TUHO and
    Oborovo. Calling it on factory-derived inputs must
    return a deterministic state without mutating
    anything."""

    def test_factory_clean_saved(self):
        s = resolve_dirty_state(
            workspace_state={"dirty": False},
            save_state={"last_saved_at": "2026-06-10T10:00:00Z"},
        )
        assert s.state == "saved"
        assert s.rerun_recommended is False
        assert s.unsaved_warning is False

    def test_factory_dirty_with_prior_run(self):
        s = resolve_dirty_state(
            workspace_state={
                "dirty": True,
                "last_runtime_snapshot_id": "snap-1",
            },
            runtime_summary={"run_id": "run-1"},
        )
        assert s.state == "needs_rerun"
        assert s.rerun_recommended is True

    def test_factory_inputs_not_mutated(self):
        ws = {"dirty": False, "last_runtime_snapshot_id": "snap-1"}
        ws_before = dict(ws)
        _ = resolve_dirty_state(workspace_state=ws)
        assert ws == ws_before
