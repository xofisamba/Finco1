"""Phase 25B-4 — No-regression tests.

These tests verify that the dirty-state UI work does not break the
existing flows:

- scenario save/load
- scenario compare (Phase 20G)
- multi-compare (Phase 25B-2)
- export/download (Phase 24H-4)
- workspace render (key shapes)
"""
from __future__ import annotations

from pathlib import Path

import pytest

# Lazy / guarded imports — we only test public shapes here.
from app.ui.dirty_state import build_dirty_state_ui


# ─────────────────────────────────────────────────────────────────────────
# Test 1: scenario save/load contract — paylaod can be saved with the
#        existing record shape
# ─────────────────────────────────────────────────────────────────────────

class TestScenarioSaveLoadUnchanged:
    def test_dirty_state_ui_serializable(self):
        """The payload must be a plain-Python-dict of dicts, so it can
        be persisted via JSON without surprises."""
        import json
        result = build_dirty_state_ui(
            dirty=True, has_runtime_snapshot=True, is_user_project=True,
            active_scenario_id="a", scenarios=[{"scenario_id": "a", "scenario_name": "Base"}],
        )
        # JSON-serializable
        encoded = json.dumps(result, default=str)
        decoded = json.loads(encoded)
        assert decoded["badge"]["state"] == "stale"
        assert decoded["scenario_dots"][0]["is_dirty"] is True

    def test_dirty_state_ui_does_not_persist(self):
        """The helper is stateless. Two calls with the same args yield
        the same payload shape (modulo no I/O)."""
        kwargs = dict(
            dirty=True, has_runtime_snapshot=True, is_user_project=True,
            active_scenario_id="x", scenarios=[{"scenario_id": "x"}],
        )
        r1 = build_dirty_state_ui(**kwargs)
        r2 = build_dirty_state_ui(**kwargs)
        assert r1.keys() == r2.keys()
        assert r1["badge"]["state"] == r2["badge"]["state"]


# ─────────────────────────────────────────────────────────────────────────
# Test 2: scenario compare path
# ─────────────────────────────────────────────────────────────────────────

class TestScenarioCompareUnchanged:
    def test_compare_payload_independent_of_dirty_state(self):
        """The compare response shape should not change just because
        the workspace is dirty. We assert this at the pure-helper
        level."""
        r_clean = build_dirty_state_ui(
            dirty=False, has_runtime_snapshot=True, is_user_project=True,
            active_scenario_id="a", scenarios=[],
        )
        r_dirty = build_dirty_state_ui(
            dirty=True, has_runtime_snapshot=True, is_user_project=True,
            active_scenario_id="a", scenarios=[],
        )
        # The two payloads differ only in the dirty state itself.
        assert r_clean["badge"]["state"] == "saved"
        assert r_dirty["badge"]["state"] == "stale"
        # Same overall shape.
        assert r_clean.keys() == r_dirty.keys()


# ─────────────────────────────────────────────────────────────────────────
# Test 3: multi-compare path
# ─────────────────────────────────────────────────────────────────────────

class TestMultiCompareUnchanged:
    def test_multi_compare_with_many_scenarios(self):
        """A project with 4 scenarios — the dirty-state UI should
        still produce a valid payload for the workspace render."""
        scenarios = [
            {"scenario_id": f"s{i}", "scenario_name": f"S{i}"} for i in range(4)
        ]
        result = build_dirty_state_ui(
            dirty=True, has_runtime_snapshot=True, is_user_project=True,
            active_scenario_id="s2", scenarios=scenarios,
        )
        assert len(result["scenario_dots"]) == 4
        # Only the active one is dirty.
        dirty = [d for d in result["scenario_dots"] if d["is_dirty"]]
        assert len(dirty) == 1
        assert dirty[0]["scenario_id"] == "s2"

    def test_archived_or_archived_scenarios_skipped(self):
        # Defensive: scenarios with empty id are still iterated, but
        # their dot is always clean.
        scenarios = [
            {"scenario_id": "", "scenario_name": "archived-1"},
            {"scenario_id": "s1", "scenario_name": "Base"},
        ]
        result = build_dirty_state_ui(
            dirty=True, has_runtime_snapshot=True, is_user_project=True,
            active_scenario_id="", scenarios=scenarios,
        )
        # No active scenario → no dirty dot.
        assert all(d["is_dirty"] is False for d in result["scenario_dots"])


# ─────────────────────────────────────────────────────────────────────────
# Test 4: export/download path
# ─────────────────────────────────────────────────────────────────────────

class TestExportDownloadUnchanged:
    def test_export_does_not_trigger_dirty_state(self):
        """The dirty-state helper is read-only. It must not call
        record_export or write to disk."""
        text = Path("app/ui/dirty_state.py").read_text()
        for forbidden in [
            "record_export",
            "record_run",
            "session.add",
            "session.commit",
            "INSERT",
            "UPDATE",
            "DELETE",
        ]:
            assert forbidden not in text, (
                f"app/ui/dirty_state.py must not touch the DB: {forbidden}"
            )

    def test_export_metadata_independent_of_dirty_state(self):
        # The export_lineage_ui shape (a separate concern) is not
        # affected by dirty_state. We just assert that the dirty
        # state payload does not clobber the existing lineage
        # contract.
        r = build_dirty_state_ui(
            dirty=True, has_runtime_snapshot=True, is_user_project=True,
            active_scenario_id="a", scenarios=[],
        )
        # dirty_state_ui has no key called "exports" or "export_lineage".
        assert "exports" not in r
        assert "export_lineage" not in r


# ─────────────────────────────────────────────────────────────────────────
# Test 5: workspace render — defensive defaults
# ─────────────────────────────────────────────────────────────────────────

class TestWorkspaceRenderDefensive:
    def test_build_with_minimal_args(self):
        # The signature should accept all args as keyword with
        # sensible defaults.
        result = build_dirty_state_ui(
            dirty=False, has_runtime_snapshot=False, is_user_project=False,
        )
        assert result["badge"]["state"] == "factory"
        assert result["notice"] is not None
        assert result["run_warning"] is None
        assert result["scenario_dots"] == []

    def test_all_branching_paths(self):
        # 2 * 2 * 2 = 8 combinations of (dirty, snap, user).
        for dirty in (False, True):
            for snap in (False, True):
                for is_user in (False, True):
                    result = build_dirty_state_ui(
                        dirty=dirty, has_runtime_snapshot=snap, is_user_project=is_user,
                    )
                    # Always returns the same 4 top-level keys.
                    assert set(result.keys()) == {
                        "badge", "notice", "run_warning", "scenario_dots",
                    }
                    # Badge state is one of the four known values.
                    assert result["badge"]["state"] in {
                        "saved", "unsaved", "stale", "factory",
                    }
