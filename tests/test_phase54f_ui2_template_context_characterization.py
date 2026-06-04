"""Phase 54F — UI-2 template/context characterization guardrails.

Verifies:
- doc and JSON exist
- 6 UI-2 target items
- context_key_inventory present
- ui2_risk_matrix present
- must_not_change list
- missing_context_keys list
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC = REPO_ROOT / "docs" / "phase54f_ui2_template_context_characterization.md"
JSON_RPT = REPO_ROOT / "reports" / "phase54f_ui2_template_context_characterization.json"


class TestDeliverablesExist:
    def test_doc_exists(self):
        assert DOC.exists()

    def test_json_report_exists(self):
        assert JSON_RPT.exists()

    def test_phase_field_is_54f(self):
        data = json.loads(JSON_RPT.read_text())
        assert data["phase"] == "54F"

    def test_recommended_next_step_is_54g(self):
        data = json.loads(JSON_RPT.read_text())
        assert "54G" in data["recommended_next_step"]

    def test_json_includes_required_keys(self):
        data = json.loads(JSON_RPT.read_text())
        for key in [
            "phase", "base_sha", "head_sha", "target_template_inventory",
            "context_key_inventory", "route_service_context_sources",
            "existing_status_patterns", "missing_context_keys",
            "ui2_risk_matrix", "must_not_change",
            "recommended_next_step", "tests_run", "known_failures"
        ]:
            assert key in data, f"Missing key: {key}"


class TestTargetTemplateInventory:
    EXPECTED_ITEMS = [
        "UI-2.1_state_banner", "UI-2.2_runtime_chip",
        "UI-2.3_validation_summary_bar", "UI-2.4_factory_lock",
        "UI-2.5_stale_warning", "UI-2.6_run_source"
    ]

    @pytest.mark.parametrize("item", EXPECTED_ITEMS)
    def test_item_in_inventory(self, item):
        data = json.loads(JSON_RPT.read_text())
        assert item in data["target_template_inventory"]

    def test_all_items_have_target_templates(self):
        data = json.loads(JSON_RPT.read_text())
        inv = data["target_template_inventory"]
        for item in inv.values():
            assert "target_templates" in item
            assert len(item["target_templates"]) > 0

    def test_all_items_have_tone(self):
        data = json.loads(JSON_RPT.read_text())
        inv = data["target_template_inventory"]
        for item in inv.values():
            assert "tone" in item


class TestContextKeyInventory:
    EXPECTED_TEMPLATES = [
        "index.html", "runtime_summary.html", "sheet_capex_detail.html",
        "audit_reconciliation_tab.html", "workspace_shell.html"
    ]

    @pytest.mark.parametrize("tmpl", EXPECTED_TEMPLATES)
    def test_template_in_context_inventory(self, tmpl):
        data = json.loads(JSON_RPT.read_text())
        assert tmpl in data["context_key_inventory"]


class TestRiskMatrix:
    EXPECTED_ITEMS = [
        "UI-2.1 state banner", "UI-2.2 runtime chip",
        "UI-2.3 validation bar", "UI-2.4 factory lock",
        "UI-2.5 stale warning", "UI-2.6 run-source"
    ]

    @pytest.mark.parametrize("item", EXPECTED_ITEMS)
    def test_item_in_risk_matrix(self, item):
        data = json.loads(JSON_RPT.read_text())
        items = [r["item"] for r in data["ui2_risk_matrix"]]
        assert item in items

    def test_no_auto_merge_eligible(self):
        data = json.loads(JSON_RPT.read_text())
        for r in data["ui2_risk_matrix"]:
            assert r["auto_merge_eligible"] is False


class TestMustNotChange:
    EXPECTED = [
        "rc1 (b425a07) frozen SHA",
        "app/persistence/",
        "app/services/",
        "main_web.py",
        "parity/",
    ]

    @pytest.mark.parametrize("path", EXPECTED)
    def test_must_not_change_present(self, path):
        data = json.loads(JSON_RPT.read_text())
        # Path may appear in a single line with others
        all_text = " ".join(data["must_not_change"])
        assert path in all_text, f"{path} not found in must_not_change"


class TestMissingContextKeys:
    def test_at_least_4_missing_keys(self):
        data = json.loads(JSON_RPT.read_text())
        n = len(data["missing_context_keys"])
        assert n >= 4

    def test_is_factory_template_needed(self):
        data = json.loads(JSON_RPT.read_text())
        keys = [m["key"] for m in data["missing_context_keys"]]
        assert any("is_factory_template" in k for k in keys)

    def test_validation_summary_needed(self):
        data = json.loads(JSON_RPT.read_text())
        keys = [m["key"] for m in data["missing_context_keys"]]
        assert any("validation_summary" in k for k in keys)
