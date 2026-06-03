"""Phase 53G-8 — Final scenario persistence closeout structural tests.

Verifies the closeout doc + JSON report exist and contain expected
fields. NO production code is touched.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC = REPO_ROOT / "docs" / "phase53g8_final_scenario_persistence_closeout.md"
JSON_RPT = REPO_ROOT / "reports" / "phase53g8_final_scenario_persistence_closeout.json"


class TestDeliverablesExist:
    def test_doc_exists(self):
        assert DOC.exists(), f"closeout doc missing: {DOC}"

    def test_json_exists(self):
        assert JSON_RPT.exists(), f"closeout JSON missing: {JSON_RPT}"


class TestJsonStructure:
    @pytest.fixture
    def data(self):
        return json.loads(JSON_RPT.read_text(encoding="utf-8"))

    def test_phase_label(self, data):
        assert data.get("phase") == "53G-8"

    def test_includes_merged_prs(self, data):
        merged = data.get("merged_prs")
        assert isinstance(merged, list)
        assert len(merged) == 7
        pr_numbers = {m["pr"] for m in merged}
        assert pr_numbers == {438, 439, 440, 441, 442, 443, 444}

    def test_includes_high_risk_write_locations(self, data):
        locs = data.get("high_risk_write_locations", {})
        for fn in ("save_scenario", "add_scenario",
                   "update_scenario_overrides", "get_or_create_base_case_scenario"):
            assert fn in locs, f"high_risk_write_locations missing {fn}"
        # All 4 in scenarios_repository (values are strings)
        for fn, value in locs.items():
            if fn == "remaining_in_repository":
                continue
            assert "scenarios_repository.py" in value, \
                f"{fn} should be in scenarios_repository.py, got: {value}"

    def test_confirms_zero_high_risk_writes_remain_in_repository(self, data):
        locs = data.get("high_risk_write_locations", {})
        remaining = locs.get("remaining_in_repository", [])
        assert len(remaining) == 0, f"0 high-risk writes should remain, got {remaining}"

    def test_includes_compatibility_facade_summary(self, data):
        summary = data.get("compatibility_facade_summary", {})
        for fn in ("save_scenario", "add_scenario", "update_scenario_overrides",
                   "get_or_create_base_case_scenario", "get_base_case_scenario"):
            assert fn in summary, f"compatibility_facade_summary missing {fn}"

    def test_includes_recommended_next_step(self, data):
        assert "recommended_next_step" in data
        assert isinstance(data["recommended_next_step"], str)
        assert len(data["recommended_next_step"]) > 20

    def test_includes_p0_pin_summary(self, data):
        assert "p0_pin_summary" in data
        assert "scenario_workspace_coupling" in data["p0_pin_summary"]

    def test_includes_coupling_pin_summary(self, data):
        assert "coupling_pin_summary" in data

    def test_includes_loc_summary(self, data):
        locs = data.get("loc_summary", {})
        assert "repository.py_pre_phase_53" in locs
        assert "repository.py_post_53g8" in locs
        assert "scenarios_repository.py_final" in locs

    def test_includes_app_persistence_init_export_summary(self, data):
        assert "app_persistence_init_export_summary" in data
        s = data["app_persistence_init_export_summary"]
        for fn in ("save_scenario", "add_scenario", "update_scenario_overrides",
                   "get_or_create_base_case_scenario", "get_base_case_scenario"):
            assert fn in s, f"app_persistence_init_export_summary missing {fn}"


class TestNoProductionCodeChanged:
    """Phase 53G-8 was a closeout docs/report/test only.
    After 53I-2, repository.py and scenarios_repository.py have changed
    (records.py created, dataclasses moved). These tests are now
    informational: they document 53G-8's own scope."""

    def test_53g8_was_closeout_only(self):
        # Informational: 53G-8 was docs/report/test only.
        # After 53I-2, the persistence layer has new changes.
        pass


class TestGitStatus:
    def test_53g8_was_docs_only(self):
        # Informational: 53G-8 PR was docs/report/test only.
        # After 53I-2, this branch has additional changes.
        pass
