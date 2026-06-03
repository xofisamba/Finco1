"""Phase 54C — Design system tokens and copy guardrails.

Verifies:
- doc and JSON exist
- 9 component vocabulary entries
- 4 Runtime Impact chip states
- 11 state banner copy entries
- Forbidden claims list present
- Safe UI terms list present
- Component token table present
- 12 sub-reason tooltips documented
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC = REPO_ROOT / "docs" / "phase54c_design_system_tokens_copy_guardrails.md"
JSON_RPT = REPO_ROOT / "reports" / "phase54c_design_system_tokens_copy_guardrails.json"


class TestDeliverablesExist:
    def test_doc_exists(self):
        assert DOC.exists()

    def test_json_report_exists(self):
        assert JSON_RPT.exists()

    def test_phase_field_is_54c(self):
        data = json.loads(JSON_RPT.read_text())
        assert data["phase"] == "54C"

    def test_recommended_next_step_is_54d(self):
        data = json.loads(JSON_RPT.read_text())
        assert "54D" in data["recommended_next_step"]


class TestComponentVocabulary:
    EXPECTED = ["chip", "badge", "banner", "card", "grid", "section",
                "status_pill", "tooltip", "validation_marker"]

    @pytest.mark.parametrize("component", EXPECTED)
    def test_component_in_vocabulary(self, component):
        data = json.loads(JSON_RPT.read_text())
        comps = [c["name"] for c in data["component_vocabulary"]]
        assert component in comps

    def test_vocabulary_has_9_components(self):
        data = json.loads(JSON_RPT.read_text())
        n = len(data["component_vocabulary"])
        assert n == 9


class TestRuntimeImpactChipSpec:
    EXPECTED_STATES = ["Drives model", "Display only", "Pending", "Needs review"]

    @pytest.mark.parametrize("state", EXPECTED_STATES)
    def test_state_in_chip_spec(self, state):
        data = json.loads(JSON_RPT.read_text())
        states = [s["name"] for s in data["runtime_impact_chip_spec"]["states"]]
        assert state in states

    def test_each_state_has_full_spec(self):
        data = json.loads(JSON_RPT.read_text())
        for s in data["runtime_impact_chip_spec"]["states"]:
            for key in ["name", "chip_label", "color", "icon", "tooltip"]:
                assert key in s, f"State {s.get('name')} missing {key}"

    def test_sub_reasons_documented(self):
        data = json.loads(JSON_RPT.read_text())
        sub = data["runtime_impact_chip_spec"]["sub_reasons"]
        # Should have at least 10 sub-reasons
        assert len(sub) >= 10


class TestStateBannerCopy:
    EXPECTED_CONTEXTS = [
        "Factory template", "User-created project", "Active scenario",
        "Saved scenario", "Browser draft", "Dirty state", "Stale result",
        "Last run", "Validation failed", "Display-only row",
        "Pending runtime source"
    ]

    @pytest.mark.parametrize("context", EXPECTED_CONTEXTS)
    def test_context_in_banner_copy(self, context):
        data = json.loads(JSON_RPT.read_text())
        contexts = [b["context"] for b in data["state_banner_copy"]]
        assert context in contexts

    def test_11_banner_contexts(self):
        data = json.loads(JSON_RPT.read_text())
        n = len(data["state_banner_copy"])
        assert n == 11

    def test_each_banner_has_required_fields(self):
        data = json.loads(JSON_RPT.read_text())
        for b in data["state_banner_copy"]:
            for key in ["context", "title", "tone", "description"]:
                assert key in b, f"Banner {b.get('context')} missing {key}"


class TestForbiddenClaims:
    EXPECTED_FORBIDDEN = [
        "bankable", "bank-grade", "lender-ready", "certified",
        "audit-ready", "validated (alone)", "investor-ready",
        "SaaS-ready", "production-ready", "external validation",
        "customer reference", "investment advice", "guaranteed returns"
    ]

    def test_forbidden_claims_list_present(self):
        data = json.loads(JSON_RPT.read_text())
        forbidden = data["forbidden_ui_claims"]
        assert len(forbidden) >= 10

    def test_bankable_is_forbidden(self):
        data = json.loads(JSON_RPT.read_text())
        forbidden = data["forbidden_ui_claims"]
        assert "bankable" in forbidden

    def test_lender_ready_is_forbidden(self):
        data = json.loads(JSON_RPT.read_text())
        forbidden = data["forbidden_ui_claims"]
        assert "lender-ready" in forbidden

    def test_audit_ready_is_forbidden(self):
        data = json.loads(JSON_RPT.read_text())
        forbidden = data["forbidden_ui_claims"]
        assert "audit-ready" in forbidden


class TestSafeTerms:
    EXPECTED_SAFE = [
        "model evidence", "reconciliation", "audit trail",
        "validation checks", "review status", "internal confidence",
        "controlled pilot", "source mapping", "model provenance"
    ]

    def test_safe_terms_list_present(self):
        data = json.loads(JSON_RPT.read_text())
        safe = data["safe_ui_terms"]
        assert len(safe) >= 7

    def test_controlled_pilot_is_safe(self):
        data = json.loads(JSON_RPT.read_text())
        safe = data["safe_ui_terms"]
        assert "controlled pilot" in safe

    def test_audit_trail_is_safe(self):
        data = json.loads(JSON_RPT.read_text())
        safe = data["safe_ui_terms"]
        assert "audit trail" in safe


class TestComponentTokenTable:
    EXPECTED_TOKENS = [
        "--chip-padding-y", "--chip-radius", "--badge-padding-y",
        "--banner-padding", "--card-padding", "--grid-cell-padding-y",
        "--grid-border", "--grid-header-bg"
    ]

    @pytest.mark.parametrize("token", EXPECTED_TOKENS)
    def test_token_in_table(self, token):
        data = json.loads(JSON_RPT.read_text())
        tokens = data["component_token_table"]
        assert token in tokens, f"Token {token} missing from component_token_table"


class TestDesignTokensPresent:
    def test_color_palette_present(self):
        data = json.loads(JSON_RPT.read_text())
        palette = data["design_tokens"]["color_palette"]
        for k in ["base", "primary_navy", "accent_blue", "clean_energy_green",
                  "status_semantic", "text"]:
            assert k in palette, f"Color group {k} missing"

    def test_typography_present(self):
        data = json.loads(JSON_RPT.read_text())
        typo = data["design_tokens"]["typography"]
        for k in ["body_font", "monospace_font", "tabular_numeric",
                  "sizes"]:
            assert k in typo, f"Typography key {k} missing"

    def test_spacing_present(self):
        data = json.loads(JSON_RPT.read_text())
        spacing = data["design_tokens"]["spacing"]
        for k in ["1", "2", "3", "4", "6", "8"]:
            assert k in spacing, f"Spacing key {k} missing"
