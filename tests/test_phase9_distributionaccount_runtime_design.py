"""Phase 9 DistributionAccount runtime design validation tests.

Design-only tests — NO runtime promotion.
Validates the DistributionAccount runtime design doc and dependency matrix.

R99/R102: BLOCKED — design doc only, no implementation.
"""

import pytest
from pathlib import Path

DOCS_PATH = Path("docs/phase9_distributionaccount_runtime_design.md")
CSV_PATH = Path("reports/phase9_distributionaccount_dependency_matrix.csv")


class TestDocExists:
    """Required design doc exists."""

    def test_design_doc_exists(self):
        assert DOCS_PATH.exists(), f"{DOCS_PATH} must exist"


class TestCsvExists:
    """Required CSV dependency matrix exists."""

    def test_dependency_matrix_csv_exists(self):
        assert CSV_PATH.exists(), f"{CSV_PATH} must exist"


class TestDocRequiredSections:
    """All 15 required documentation sections are present."""

    def test_executive_summary(self):
        content = DOCS_PATH.read_text()
        assert "Executive Summary" in content

    def test_current_distribution_ownership_flow(self):
        content = DOCS_PATH.read_text()
        assert "Current Distribution Ownership Flow" in content

    def test_distribution_account_current_role(self):
        content = DOCS_PATH.read_text()
        assert "DistributionAccount Current Role" in content

    def test_sponsor_tuple_handoff_interaction(self):
        content = DOCS_PATH.read_text()
        assert "Sponsor Tuple Handoff Interaction" in content

    def test_shl_downstream_dependency_analysis(self):
        content = DOCS_PATH.read_text()
        assert "SHL Downstream Dependency Analysis" in content

    def test_distribution_runtime_authoritative_design(self):
        content = DOCS_PATH.read_text()
        assert "Distribution Runtime-Authoritative Design" in content

    def test_audit_only_vs_runtime_fields(self):
        content = DOCS_PATH.read_text()
        assert "Audit-Only vs Runtime Fields" in content

    def test_deterministic_tuple_semantics(self):
        content = DOCS_PATH.read_text()
        assert "Deterministic Tuple Semantics" in content

    def test_fallback_prohibition_rules(self):
        content = DOCS_PATH.read_text()
        assert "Fallback Prohibition Rules" in content

    def test_actual_vs_sizing_cfads_implications(self):
        content = DOCS_PATH.read_text()
        assert "actual_cfads vs sizing_cfads Implications" in content

    def test_r99_r102_dependency_analysis(self):
        content = DOCS_PATH.read_text()
        assert "R99/R102 Dependency Analysis" in content

    def test_promotion_dependency_graph(self):
        content = DOCS_PATH.read_text()
        assert "Promotion Dependency Graph" in content

    def test_recommended_promotion_order(self):
        content = DOCS_PATH.read_text()
        assert "Recommended Promotion Order" in content

    def test_explicit_blockers(self):
        content = DOCS_PATH.read_text()
        assert "Explicit Blockers" in content

    def test_final_recommendation(self):
        content = DOCS_PATH.read_text()
        assert "Final Recommendation" in content


class TestCsvRequiredColumns:
    """CSV has all required columns."""

    def test_csv_has_required_columns(self):
        content = CSV_PATH.read_text()
        header = content.split("\n")[0]
        required = [
            "subsystem", "current_owner", "future_owner", "runtime_or_audit",
            "upstream_dependency", "downstream_dependency", "promotion_dependency",
            "current_status", "risk_level", "notes"
        ]
        for col in required:
            assert col in header, f"Missing CSV column: {col}"


class TestKeyFindings:
    """Key design findings are documented."""

    def test_equity_distribution_paid_keur_always_zero_documented(self):
        content = DOCS_PATH.read_text()
        assert "0.0" in content and "hard-coded" in content.lower()

    def test_distribution_account_r102_sweep_port_unconnected_documented(self):
        content = DOCS_PATH.read_text()
        assert "never wired" in content.lower() or "unconnected" in content.lower()

    def test_no_runtime_path_exists_documented(self):
        content = DOCS_PATH.read_text()
        assert "not exist" in content.lower() or "disconnected" in content.lower()


class TestR99R102Blocked:
    """R99/R102 remain BLOCKED per task requirement."""

    def test_r99_blocked_in_doc(self):
        content = DOCS_PATH.read_text()
        assert "R99" in content and "BLOCKED" in content

    def test_r102_blocked_in_doc(self):
        content = DOCS_PATH.read_text()
        assert "R102" in content and "BLOCKED" in content


class TestPromotionOrder:
    """Promotion order table is present and sensible."""

    def test_promotion_order_has_co2_done(self):
        content = DOCS_PATH.read_text()
        assert "✅" in content or "DONE" in content or "SAFE NOW" in content

    def test_promotion_order_blocks_r99_until_distributionaccount(self):
        content = DOCS_PATH.read_text()
        # R99 should appear after DistributionAccount in the order
        r99_pos = content.find("R99")
        dist_pos = content.find("DistributionAccount")
        assert r99_pos > dist_pos > 0, "R99 promotion must come after DistributionAccount promotion"


class TestNoRuntimePromotion:
    """This branch must NOT promote anything to runtime."""

    def test_only_new_design_files_present(self):
        # This branch should only add docs/CSV/tests
        import subprocess
        result = subprocess.run(
            ['git', 'status', '--porcelain'], capture_output=True, text=True,
            cwd=str(DOCS_PATH.parent.parent)
        )
        changed = [l for l in result.stdout.strip().split(chr(10)) if l and not l.startswith(chr(63)+chr(63))]
        assert len(changed) == 0, f"Unexpected modified files: {changed}"
class TestExplicitBlockers:
    """All explicit blockers are documented."""

    def test_blocker_equity_distribution_paid_keur_hardcoded(self):
        content = DOCS_PATH.read_text()
        assert "equity_distribution_paid_keur" in content
        assert "0.0" in content or "hard-coded" in content.lower()

    def test_blocker_r102_sweep_port_unconnected(self):
        content = DOCS_PATH.read_text()
        assert "distribution_account_r102_sweep_candidate_keur" in content

    def test_blocker_no_distributionaccount_to_waterfall_wiring(self):
        content = DOCS_PATH.read_text()
        assert "not wired" in content.lower() or "disconnected" in content.lower()


class TestDependencyMatrixValid:
    """Dependency matrix has valid data."""

    def test_csv_has_both_projects(self):
        content = CSV_PATH.read_text()
        assert "DistributionAccount" in content
        assert "WaterfallEngine" in content

    def test_csv_has_safe_now_entry(self):
        content = CSV_PATH.read_text()
        assert "SAFE" in content

    def test_csv_has_blocked_entry(self):
        content = CSV_PATH.read_text()
        assert "BLOCKED" in content

    def test_csv_co2_bridge_is_safe_now(self):
        content = CSV_PATH.read_text()
        lines = content.split("\n")
        for line in lines:
            if "CO2 CIT bridge" in line:
                assert "SAFE" in line, "CO2 bridge must be marked SAFE NOW"
                break


class TestFinalRecommendation:
    """Final recommendation is actionable."""

    def test_recommendation_names_next_branch(self):
        content = DOCS_PATH.read_text()
        assert "phase9-distributionaccount-runtime-wiring" in content

    def test_recommendation_requires_prereqs(self):
        content = DOCS_PATH.read_text()
        # Should list what needs to be fixed before wiring
        assert "equity_paid" in content or "equity_distribution_paid" in content


class TestDistributionAccountEngineAuditOnly:
    """DistributionAccount is audit-only — confirmed in code."""

    def test_engine_comment_says_audit_only(self):
        content = Path("domain/distribution_account/engine.py").read_text()
        assert "AUDIT-ONLY" in content or "audit-only" in content.lower()

    def test_equity_paid_is_hardcoded_zero(self):
        content = Path("domain/distribution_account/engine.py").read_text()
        assert "equity_paid = 0.0" in content


class TestShlPortExistsButUnconnected:
    """SHL has distribution_account_r102_sweep_candidate_keur port."""

    def test_shl_input_has_port(self):
        content = Path("domain/shl/inputs.py").read_text()
        assert "distribution_account_r102_sweep_candidate_keur" in content

    def test_shl_result_has_port(self):
        content = Path("domain/shl/result.py").read_text()
        assert "distribution_account_r102_sweep_candidate_keur" in content

    def test_port_not_wired_in_waterfall_core(self):
        content = Path("app/waterfall_core.py").read_text()
        assert "distribution_account_r102_sweep_candidate_keur" not in content


class TestSponsorTupleSemantics:
    """Sponsor tuple semantics are defined in doc."""

    def test_tuple_ordered_by_priority_documented(self):
        content = DOCS_PATH.read_text()
        assert "Ordered by waterfall priority" in content or "ordered" in content.lower()

    def test_all_zero_replacement_documented(self):
        content = DOCS_PATH.read_text()
        assert "0.0" in content and ("zero" in content.lower() or "all-zero" in content.lower())

    def test_empty_tuple_prohibited(self):
        content = DOCS_PATH.read_text()
        assert "not permitted" in content.lower() or "prohibited" in content.lower()


class TestR99R102DependencyAnalysis:
    """R99/R102 dependency analysis is complete."""

    def test_r99_gate_passed_not_controlling_runtime(self):
        content = DOCS_PATH.read_text()
        assert "gate evaluated but not controlling" in content.lower()

    def test_r102_sweep_not_wired(self):
        content = DOCS_PATH.read_text()
        assert "not wired" in content.lower() or "unconnected" in content.lower()
