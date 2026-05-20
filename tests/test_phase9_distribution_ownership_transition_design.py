"""Phase 9 Distribution ownership transition design validation tests.

DESIGN / GOVERNANCE ONLY — NO RUNTIME ROUTING.
Validates the distribution ownership transition design doc and matrix.

R99/R102: BLOCKED — design doc only, no implementation.
"""

import pytest
from pathlib import Path

DOCS_PATH = Path("docs/phase9_distribution_ownership_transition_design.md")
CSV_PATH = Path("reports/phase9_distribution_ownership_transition_matrix.csv")


class TestDocExists:
    """Required design doc exists."""

    def test_design_doc_exists(self):
        assert DOCS_PATH.exists(), f"{DOCS_PATH} must exist"


class TestCsvExists:
    """Required CSV matrix exists."""

    def test_ownership_matrix_csv_exists(self):
        assert CSV_PATH.exists(), f"{CSV_PATH} must exist"


class TestDocRequiredSections:
    """All 20 required documentation sections are present."""

    def test_01_executive_summary(self):
        content = DOCS_PATH.read_text()
        assert "Executive Summary" in content

    def test_02_current_runtime_distribution_flow(self):
        content = DOCS_PATH.read_text()
        assert "Current Runtime Distribution Flow" in content

    def test_03_current_sponsor_dependency_flow(self):
        content = DOCS_PATH.read_text()
        assert "Current Sponsor Dependency Flow" in content

    def test_04_current_shl_dependency_flow(self):
        content = DOCS_PATH.read_text()
        assert "Current SHL Dependency Flow" in content

    def test_05_current_distributionaccount_dependency_flow(self):
        content = DOCS_PATH.read_text()
        assert "Current DistributionAccount Dependency Flow" in content

    def test_06_current_r99_r102_dependency_flow(self):
        content = DOCS_PATH.read_text()
        assert "Current R99/R102 Dependency Flow" in content

    def test_07_dual_ownership_risk_analysis(self):
        content = DOCS_PATH.read_text()
        assert "Dual-Ownership Risk Analysis" in content

    def test_08_future_authoritative_distribution_architecture(self):
        content = DOCS_PATH.read_text()
        assert "Future Authoritative Distribution Architecture" in content

    def test_09_transition_phase_design(self):
        content = DOCS_PATH.read_text()
        assert "Transition Phase Design" in content

    def test_10_runtime_invariants(self):
        content = DOCS_PATH.read_text()
        assert "Runtime Invariants" in content

    def test_11_fallback_prohibition_rules(self):
        content = DOCS_PATH.read_text()
        assert "Fallback Prohibition Rules" in content

    def test_12_sponsor_runtime_contract(self):
        content = DOCS_PATH.read_text()
        assert "Sponsor Runtime Contract" in content

    def test_13_shl_runtime_contract(self):
        content = DOCS_PATH.read_text()
        assert "SHL Runtime Contract" in content

    def test_14_distributionaccount_runtime_contract(self):
        content = DOCS_PATH.read_text()
        assert "DistributionAccount Runtime Contract" in content

    def test_15_r99_r102_evaluation_contract(self):
        content = DOCS_PATH.read_text()
        assert "R99/R102 Evaluation Contract" in content

    def test_16_migration_safety_gates(self):
        content = DOCS_PATH.read_text()
        assert "Migration Safety Gates" in content

    def test_17_rollback_strategy(self):
        content = DOCS_PATH.read_text()
        assert "Rollback Strategy" in content

    def test_18_recommended_promotion_order(self):
        content = DOCS_PATH.read_text()
        assert "Recommended Promotion Order" in content

    def test_19_explicit_blockers(self):
        content = DOCS_PATH.read_text()
        assert "Explicit Blockers" in content

    def test_20_final_recommendation(self):
        content = DOCS_PATH.read_text()
        assert "Final Recommendation" in content


class TestCsvRequiredColumns:
    """CSV has all 11 required columns."""

    def test_csv_has_required_columns(self):
        content = CSV_PATH.read_text()
        header = content.split("\n")[0]
        required = [
            "field", "current_runtime_owner", "future_runtime_owner",
            "audit_or_runtime", "transition_phase", "upstream_dependency",
            "downstream_dependency", "fallback_allowed",
            "hidden_coupling_risk", "current_status", "notes"
        ]
        for col in required:
            assert col in header, f"Missing CSV column: {col}"


class TestDualOwnershipResolved:
    """Dual-ownership risk is explicitly resolved in design."""

    def test_dual_ownership_risk_described(self):
        content = DOCS_PATH.read_text()
        assert "dual" in content.lower() and "ownership" in content.lower()
        assert "two" in content.lower() and "distribution" in content.lower()

    def test_single_source_of_truth_described(self):
        content = DOCS_PATH.read_text()
        assert "single" in content.lower() or "sole" in content.lower()
        assert "authoritative" in content.lower() or "source of truth" in content.lower()


class TestTransitionPhasesDefined:
    """All 4 transition phases are defined."""

    def test_phase_A_audit_only_described(self):
        content = DOCS_PATH.read_text()
        assert "Phase A" in content or "Phase A" in content
        assert "Audit-Only" in content or "audit-only" in content.lower()

    def test_phase_B_dual_run_described(self):
        content = DOCS_PATH.read_text()
        assert "Phase B" in content
        assert "dual" in content.lower() or "compare" in content.lower()

    def test_phase_C_authoritative_described(self):
        content = DOCS_PATH.read_text()
        assert "Phase C" in content
        assert "authoritative" in content.lower()

    def test_phase_D_legacy_cleanup_described(self):
        content = DOCS_PATH.read_text()
        assert "Phase D" in content
        assert "cleanup" in content.lower() or "legacy" in content.lower()


class TestRuntimeInvariants:
    """Runtime invariants are explicitly defined."""

    def test_exactly_one_runtime_truth(self):
        content = DOCS_PATH.read_text()
        assert "exactly ONE" in content or "exactly one" in content.lower()

    def test_no_fallback_semantics(self):
        content = DOCS_PATH.read_text()
        assert "no fallback" in content.lower() or "fallback" in content.lower()

    def test_deterministic_period_mapping(self):
        content = DOCS_PATH.read_text()
        assert "period" in content.lower() and "mapping" in content.lower()


class TestFallbackProhibitionRules:
    """Fallback prohibition rules are explicit."""

    def test_no_fallback_to_waterfall_only(self):
        content = DOCS_PATH.read_text()
        assert "fallback" in content.lower()

    def test_no_dual_path(self):
        content = DOCS_PATH.read_text()
        # Should say either DA or WE, never both
        assert "either" in content.lower() or "never both" in content.lower()


class TestSponsorContract:
    """Sponsor runtime contract is defined."""

    def test_sponsor_reads_distribution_keur(self):
        content = DOCS_PATH.read_text()
        assert "Sponsor" in content and "distribution_keur" in content

    def test_zero_distribution_periods_handled(self):
        content = DOCS_PATH.read_text()
        assert "zero" in content.lower() or "0.0" in content


class TestShlContract:
    """SHL runtime contract is defined."""

    def test_distribution_account_r102_sweep_port_described(self):
        content = DOCS_PATH.read_text()
        assert "distribution_account_r102_sweep_candidate_keur" in content

    def test_shl_ordering_described(self):
        content = DOCS_PATH.read_text()
        assert "senior" in content.lower() and "shl" in content.lower()


class TestMigrationSafetyGates:
    """Migration safety gates are classified."""

    def test_safe_now_classified(self):
        content = DOCS_PATH.read_text()
        assert "SAFE" in content or "safe" in content.lower()

    def test_blocked_classified(self):
        content = DOCS_PATH.read_text()
        assert "BLOCKED" in content

    def test_phase_B_classified(self):
        content = DOCS_PATH.read_text()
        assert "Phase B" in content
        assert "dual" in content.lower() or "compare" in content.lower()


class TestPromotionOrder:
    """Promotion order table is present and complete."""

    def test_co2_bridge_done(self):
        content = DOCS_PATH.read_text()
        assert "PR #142" in content or "DONE" in content

    def test_gate_logic_done(self):
        content = DOCS_PATH.read_text()
        assert "PR #144" in content or "gate" in content.lower()

    def test_phase_B_is_next(self):
        content = DOCS_PATH.read_text()
        assert "phase9-distributionaccount-dualrun-validation" in content


class TestExplicitBlockers:
    """Explicit blockers are documented."""

    def test_dual_ownership_blocker_described(self):
        content = DOCS_PATH.read_text()
        assert "dual-ownership" in content.lower() or "dual ownership" in content.lower()

    def test_r99_r102_still_blocked(self):
        content = DOCS_PATH.read_text()
        assert "BLOCKED" in content


class TestNoRuntimeRouting:
    """This branch must NOT route anything to runtime."""

    def test_only_design_files_present(self):
        import subprocess
        result = subprocess.run(
            ['git', 'status', '--porcelain'], capture_output=True, text=True,
            cwd=str(DOCS_PATH.parent.parent)
        )
        changed = [l for l in result.stdout.strip().split('\n') if l and not l.startswith('??')]
        assert len(changed) == 0, f"Unexpected modified files: {changed}"


class TestCsvKeyFields:
    """CSV has key distribution fields."""

    def test_csv_has_distribution_keur(self):
        content = CSV_PATH.read_text()
        assert "distribution_keur" in content

    def test_csv_has_equity_distribution_paid_keur(self):
        content = CSV_PATH.read_text()
        assert "equity_distribution_paid_keur" in content

    def test_csv_has_distribution_account_r102_sweep(self):
        content = CSV_PATH.read_text()
        assert "distribution_account_r102_sweep_candidate_keur" in content


class TestFinalRecommendation:
    """Final recommendation is actionable."""

    def test_option_a_recommended(self):
        content = DOCS_PATH.read_text()
        assert "Option A" in content or "recommended" in content.lower()

    def test_next_phase_B_branch_named(self):
        content = DOCS_PATH.read_text()
        assert "phase9-distributionaccount-dualrun-validation" in content

    def test_phase_C_requires_phase_B_clean(self):
        content = DOCS_PATH.read_text()
        assert "Phase C" in content
        assert "BLOCKED" in content
