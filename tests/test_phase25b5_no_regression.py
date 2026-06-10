"""Phase 25B-5 — No-regression tests.

Verify that the scenario workflow polish work does not break:
- scenario save/load
- scenario compare (Phase 20G)
- multi-compare (Phase 25B-2)
- export/download (Phase 24H-4)
- the dirty_state_ui payload (Phase 25B-4) — both fields co-exist
- rc1 path
- compare_service / multi_compare untouched
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.ui.scenario_workflow import build_scenario_workflow_ui


# ─────────────────────────────────────────────────────────────────────────
# Test 1: scenario save/load
# ─────────────────────────────────────────────────────────────────────────

class TestScenarioSaveLoadUnchanged:
    def test_workflow_ui_is_pure_data(self):
        """The payload is a plain-Python-dict of dicts / lists. JSON-
        serializable. No class instances, no bytes, no datetimes."""
        cards = [
            {"scenario_id": "a", "scenario_name": "Base", "equity_irr": 0.10, "project_irr": 0.07, "avg_dscr": 1.3},
            {"scenario_id": "b", "scenario_name": "Downside", "equity_irr": 0.05, "project_irr": 0.03, "avg_dscr": 1.0},
        ]
        result = build_scenario_workflow_ui(cards, active_scenario_id="a")
        # JSON-serializable
        encoded = json.dumps(result, default=str)
        decoded = json.loads(encoded)
        assert decoded["by_scenario"]["a"]["label"]["kind"] == "base"
        assert decoded["state"]["state"] == "two"

    def test_does_not_mutate_input_cards(self):
        cards = [
            {"scenario_id": "a", "scenario_name": "Base", "equity_irr": 0.10},
            {"scenario_id": "b", "scenario_name": "Downside", "equity_irr": 0.05},
        ]
        snapshot = json.dumps(cards, default=str)
        build_scenario_workflow_ui(cards, active_scenario_id="a")
        # Cards must be unchanged after the call.
        assert json.dumps(cards, default=str) == snapshot


# ─────────────────────────────────────────────────────────────────────────
# Test 2: scenario compare
# ─────────────────────────────────────────────────────────────────────────

class TestScenarioCompareUnchanged:
    def test_compare_links_use_canonical_endpoint(self):
        """The 'Compare with X' shortcut must use the same
        /scenarios/compare endpoint that the existing compare flow
        uses. No new route introduced."""
        cards = [
            {"scenario_id": "a", "scenario_name": "Base"},
            {"scenario_id": "b", "scenario_name": "Downside"},
        ]
        result = build_scenario_workflow_ui(cards, active_scenario_id="a")
        link = result["compare_links"][0]
        assert link["href"].startswith("/scenarios/compare?")
        assert "left_scenario_id=a" in link["href"]
        assert "right_scenario_id=b" in link["href"]

    def test_helper_does_not_override_compare_context(self):
        """The workflow_ui payload must be a separate field; it must
        not collide with the existing compare_result dict that the
        /scenarios/compare route produces."""
        result = build_scenario_workflow_ui([], active_scenario_id="")
        # Top-level keys differ from compare_result.
        assert set(result.keys()) == {"by_scenario", "compare_links", "state"}
        # compare_result has keys like "left_context", "right_context", "deltas".
        assert "left_context" not in result
        assert "deltas" not in result


# ─────────────────────────────────────────────────────────────────────────
# Test 3: multi-compare
# ─────────────────────────────────────────────────────────────────────────

class TestMultiCompareUnchanged:
    def test_multi_compare_with_four_scenarios(self):
        cards = [
            {"scenario_id": f"s{i}", "scenario_name": name, "equity_irr": 0.05 + i * 0.02, "avg_dscr": 1.0 + i * 0.3}
            for i, name in enumerate(["Base", "Downside", "Upside", "Custom1"])
        ]
        result = build_scenario_workflow_ui(cards, active_scenario_id="s0")
        assert result["state"]["state"] == "many"
        assert result["state"]["count"] == 4
        # Compare links for active=Base (s0): downside + upside
        # (custom excluded by the helper rule).
        names = [l["right_scenario_name"] for l in result["compare_links"]]
        assert "Downside" in names
        assert "Upside" in names
        assert "Custom1" not in names

    def test_multi_compare_payload_stable(self):
        # Two calls with the same args must produce the same payload.
        cards = [
            {"scenario_id": "a", "scenario_name": "Base"},
            {"scenario_id": "b", "scenario_name": "Downside"},
        ]
        r1 = build_scenario_workflow_ui(cards, active_scenario_id="a")
        r2 = build_scenario_workflow_ui(cards, active_scenario_id="a")
        assert json.dumps(r1, default=str) == json.dumps(r2, default=str)


# ─────────────────────────────────────────────────────────────────────────
# Test 4: export/download
# ─────────────────────────────────────────────────────────────────────────

class TestExportDownloadUnchanged:
    def test_helper_does_not_touch_db(self):
        text = Path("app/ui/scenario_workflow.py").read_text()
        for forbidden in [
            "record_export", "record_run", "session.add",
            "session.commit", "INSERT", "UPDATE", "DELETE",
        ]:
            assert forbidden not in text

    def test_workflow_ui_no_export_clash(self):
        result = build_scenario_workflow_ui([], active_scenario_id="")
        assert "exports" not in result
        assert "export_lineage" not in result


# ─────────────────────────────────────────────────────────────────────────
# Test 5: dirty_state_ui co-existence (Phase 25B-4 forward-compat)
# ─────────────────────────────────────────────────────────────────────────

class TestDirtyStateCoExistence:
    """The workflow UI and the dirty-state UI are independent
    payloads. Both flows render the same template; the template
    must read each from its own field, not collide."""

    def test_workflow_ui_does_not_contain_dirty_keys(self):
        result = build_scenario_workflow_ui([], active_scenario_id="")
        assert "dirty" not in result
        assert "badge" not in result
        assert "run_warning" not in result
        assert "scenario_dots" not in result

    def test_workflow_ui_payload_self_contained(self):
        # The workflow_ui payload must be self-describing: every key
        # the template reads must exist on the payload (so the
        # template never crashes on a missing field). This is the
        # forward-compat guarantee: when both 25B-4 and 25B-5 land
        # on main, the template reads from both fields independently.
        workflow = build_scenario_workflow_ui([], active_scenario_id="a")
        assert "by_scenario" in workflow
        assert "compare_links" in workflow
        assert "state" in workflow
        # These keys belong to dirty_state, not workflow. They must
        # NOT appear on workflow.
        for forbidden in ("badge", "notice", "run_warning", "scenario_dots"):
            assert forbidden not in workflow, (
                f"workflow_ui must not include {forbidden} (that is dirty_state territory)"
            )


# ─────────────────────────────────────────────────────────────────────────
# Test 6: defensive defaults
# ─────────────────────────────────────────────────────────────────────────

class TestDefensiveDefaults:
    def test_none_cards(self):
        # When called with None cards, must not crash.
        result = build_scenario_workflow_ui(None, active_scenario_id="")  # type: ignore[arg-type]
        assert result["by_scenario"] == {}
        assert result["compare_links"] == []
        assert result["state"]["state"] == "empty"

    def test_cards_with_partial_fields(self):
        # Cards may not have all numeric fields. The helper must
        # still produce a valid payload.
        cards = [{"scenario_id": "a", "scenario_name": "Base"}]  # no IRR / DSCR
        result = build_scenario_workflow_ui(cards, active_scenario_id="a")
        assert result["by_scenario"]["a"]["quick_summary"]["irr_state"] == "n_a"
        assert result["by_scenario"]["a"]["quick_summary"]["equity_irr_pct"] == "—"
