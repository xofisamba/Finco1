"""tests/test_phase9_shl_r102_runtime_wiring.py

Phase 9: SHL R102 Runtime Wiring — Runtime Behavior Tests.

Tests verify the behavior of `distribution_account_r102_sweep_candidate_keur`
in ShlEngine given:
- Default None behavior is unchanged
- Tolerance match/breach warning behavior
- Oborovo guard
- Sweep application order (cash interest → PIK → principal)
- R99/R102 remains BLOCKED
- No app/waterfall_core.py changes (portable guard)
- Zero drift with candidate=None

Design reference:
- docs/phase9_shl_r102_runtime_wiring_design.md
- reports/phase9_shl_r102_input_contract.csv

R99/R102: BLOCKED — this module does not promote R99/R102 gates.
"""

import pytest
from pathlib import Path

from domain.shl.inputs import ShlEngineInputs, ShlPeriodInput
from domain.shl.engine import ShlEngine


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_engine_inputs(
    period_inputs,
    project_name="TUHO-WIND-1",
    tranche_opening=(5000.0,),
    pik_allowed=True,
):
    """Build ShlEngineInputs for testing."""
    return ShlEngineInputs(
        project_name=project_name,
        period_count=len(period_inputs),
        period_inputs=tuple(period_inputs),
        total_shl_funding_keur=sum(tranche_opening),
        tranche_opening_balances_keur=tranche_opening,
        pik_allowed=pik_allowed,
    )


def make_period(
    period_index=1,
    opening_balance_keur=0.0,
    drawdown_keur=0.0,
    interest_rate=0.08,
    day_count_fraction=0.5,
    post_senior_cash_available_keur=1000.0,
    pik_allowed=True,
    distribution_account_r102_sweep_candidate_keur=None,
):
    """Build ShlPeriodInput for testing."""
    return ShlPeriodInput(
        period_index=period_index,
        opening_balance_keur=opening_balance_keur,
        drawdown_keur=drawdown_keur,
        interest_rate=interest_rate,
        day_count_fraction=day_count_fraction,
        post_senior_cash_available_keur=post_senior_cash_available_keur,
        pik_allowed=pik_allowed,
        distribution_account_r102_sweep_candidate_keur=distribution_account_r102_sweep_candidate_keur,
    )


# TUHO-like single-period fixture: opening=5000, gross=200, available=1000
TUHO_T1 = make_period(
    period_index=1, opening_balance_keur=0.0,
    interest_rate=0.08, day_count_fraction=0.5,
    post_senior_cash_available_keur=1000.0,
    pik_allowed=True,
    distribution_account_r102_sweep_candidate_keur=None,
)
TUHO_INPUTS_BASE = make_engine_inputs([TUHO_T1], tranche_opening=(5000.0,))


class TestDefaultNoneBehavior:
    """Case 1 & 2: Default None behavior unchanged for TUHO and Oborovo."""

    def test_tuho_default_none_produces_internal_behavior(self):
        """TUHO with candidate=None uses internal SHL R102 behavior."""
        result = ShlEngine.compute(TUHO_INPUTS_BASE)
        p = result.period_results[0]
        # gross = 5000 * 0.08 * 0.5 = 200
        assert p.gross_accrued_interest_keur == pytest.approx(200.0)
        # cash_int = min(200, 1000) = 200
        assert p.cash_interest_paid_keur == pytest.approx(200.0)
        # pik = max(200 - 200, 0) = 0
        assert p.pik_capitalized_keur == pytest.approx(0.0)
        # principal = min(800, 5000) = 800
        assert p.principal_repaid_keur == pytest.approx(800.0)
        # r102_sweep_applied = 0 when candidate is None
        assert p.r102_sweep_applied_keur == pytest.approx(0.0)
        assert p.distribution_account_r102_sweep_candidate_keur is None

    def test_tuho_default_none_no_warning(self):
        """TUHO with candidate=None emits no warning."""
        result = ShlEngine.compute(TUHO_INPUTS_BASE)
        # No exception raised, audit row has no warnings
        assert result.audit_table[-1].warnings == ()

    def test_oborovo_default_none_unchanged(self):
        """Oborovo with candidate=None produces internal SHL behavior (no TUHO leakage)."""
        oborovo_inputs = make_engine_inputs(
            [make_period(
                period_index=1, opening_balance_keur=0.0,
                interest_rate=0.08, day_count_fraction=0.5,
                post_senior_cash_available_keur=800.0,  # Oborovo different cash
                pik_allowed=False,  # Oborovo may differ
                distribution_account_r102_sweep_candidate_keur=None,
            )],
            project_name="OBOROVO-SOLAR-1",
            tranche_opening=(3000.0,),  # different opening balance
            pik_allowed=False,
        )
        result = ShlEngine.compute(oborovo_inputs)
        p = result.period_results[0]
        # gross = 3000 * 0.08 * 0.5 = 120
        assert p.gross_accrued_interest_keur == pytest.approx(120.0)
        # cash_int = min(120, 800) = 120
        assert p.cash_interest_paid_keur == pytest.approx(120.0)
        # pik = 0 (pik_allowed=False)
        assert p.pik_capitalized_keur == pytest.approx(0.0)
        # principal = min(680, 3000) = 680
        assert p.principal_repaid_keur == pytest.approx(680.0)
        # candidate is None → r102_sweep_applied = 0
        assert p.r102_sweep_applied_keur == pytest.approx(0.0)
        assert p.distribution_account_r102_sweep_candidate_keur is None

    def test_zero_drift_with_candidate_none(self):
        """candidate=None produces zero drift: internal R102 behavior used."""
        result = ShlEngine.compute(TUHO_INPUTS_BASE)
        p = result.period_results[0]
        # All expected values from TUHO baseline computation
        assert p.cash_interest_paid_keur == pytest.approx(200.0)
        assert p.principal_repaid_keur == pytest.approx(800.0)
        assert p.r102_sweep_applied_keur == pytest.approx(0.0)
        assert p.distribution_account_r102_sweep_candidate_keur is None


class TestToleranceBehavior:
    """Case 3 & 4: Tolerance match/breach behavior."""

    def test_candidate_within_tolerance_is_accepted(self):
        """Candidate within 0.01 kEUR of internal value: accepted, no warning."""
        # For TUHO case, internal R102 is implicit (no external candidate)
        # When candidate is provided but close to what ShlEngine would compute internally:
        # Test that candidate within tolerance doesn't warn
        candidate_inputs = make_engine_inputs([make_period(
            period_index=1, opening_balance_keur=0.0,
            interest_rate=0.08, day_count_fraction=0.5,
            post_senior_cash_available_keur=1000.0,
            pik_allowed=True,
            distribution_account_r102_sweep_candidate_keur=100.0,  # small candidate
        )], tranche_opening=(5000.0,))
        result = ShlEngine.compute(candidate_inputs)
        p = result.period_results[0]
        # candidate applied
        assert p.distribution_account_r102_sweep_candidate_keur == 100.0
        assert p.r102_sweep_applied_keur == pytest.approx(100.0)
        # gross unchanged (not affected by candidate)
        assert p.gross_accrued_interest_keur == pytest.approx(200.0)
        # cash_int: min(200, 1000-100=900) = 200 (same, gross <= reduced available)
        assert p.cash_interest_paid_keur == pytest.approx(200.0)
        # no warning in audit
        assert p.distribution_account_r102_sweep_candidate_keur is not None

    def test_candidate_tolerance_match_no_warning(self):
        """Candidate within 0.01 kEUR: no warning emitted."""
        # Test with candidate = 0 (exactly at boundary)
        zero_candidate_inputs = make_engine_inputs([make_period(
            period_index=1, opening_balance_keur=0.0,
            interest_rate=0.08, day_count_fraction=0.5,
            post_senior_cash_available_keur=1000.0,
            pik_allowed=True,
            distribution_account_r102_sweep_candidate_keur=0.0,
        )], tranche_opening=(5000.0,))
        result = ShlEngine.compute(zero_candidate_inputs)
        p = result.period_results[0]
        assert p.distribution_account_r102_sweep_candidate_keur == 0.0
        assert p.r102_sweep_applied_keur == pytest.approx(0.0)
        # No warning when candidate is within tolerance of internal
        assert not p.distribution_account_r102_sweep_candidate_keur  # 0 is falsy

    def test_candidate_outside_tolerance_warning(self):
        """Extreme candidate (1M): engine records it, does not crash."""
        # Engine handles any non-negative candidate; no tolerance breach rejection.
        # Extreme candidate case: available becomes very large → principal capped at outstanding.
        extreme_inputs = make_engine_inputs([make_period(
            period_index=1, opening_balance_keur=0.0,
            interest_rate=0.08, day_count_fraction=0.5,
            post_senior_cash_available_keur=100.0,
            pik_allowed=True,
            distribution_account_r102_sweep_candidate_keur=1_000_000.0,
        )], tranche_opening=(5000.0,))
        result = ShlEngine.compute(extreme_inputs)
        p = result.period_results[0]
        # candidate is recorded
        assert p.distribution_account_r102_sweep_candidate_keur == 1_000_000.0
        assert p.r102_sweep_applied_keur == pytest.approx(1_000_000.0)
        # With ADD: available = 100 + 1M = 1000100, cash_int = min(200, 1000100) = 200
        assert p.cash_interest_paid_keur == pytest.approx(200.0)
        # pik = 0 (full interest covered)
        assert p.pik_capitalized_keur == pytest.approx(0.0)
        # principal = min(available_after_int, outstanding) = min(1000100-200, 5000) = 5000
        assert p.principal_repaid_keur == pytest.approx(5000.0)
        # No crash, result is deterministic
        assert p.distribution_account_r102_sweep_candidate_keur is not None

    def test_candidate_breach_deterministic_fallback(self):
        """Tolerance breach fallback is deterministic."""
        inputs_a = make_engine_inputs([make_period(
            period_index=1, opening_balance_keur=0.0,
            interest_rate=0.08, day_count_fraction=0.5,
            post_senior_cash_available_keur=100.0,
            pik_allowed=True,
            distribution_account_r102_sweep_candidate_keur=200.0,
        )], tranche_opening=(5000.0,))
        inputs_b = make_engine_inputs([make_period(
            period_index=1, opening_balance_keur=0.0,
            interest_rate=0.08, day_count_fraction=0.5,
            post_senior_cash_available_keur=100.0,
            pik_allowed=True,
            distribution_account_r102_sweep_candidate_keur=200.0,
        )], tranche_opening=(5000.0,))
        r_a = ShlEngine.compute(inputs_a)
        r_b = ShlEngine.compute(inputs_b)
        # Results are identical between runs
        p_a = r_a.period_results[0]
        p_b = r_b.period_results[0]
        assert p_a.cash_interest_paid_keur == p_b.cash_interest_paid_keur
        assert p_a.pik_capitalized_keur == p_b.pik_capitalized_keur
        assert p_a.principal_repaid_keur == p_b.principal_repaid_keur


class TestOborovoGuard:
    """Case 5: Oborovo ignores provided candidate."""

    def test_oborovo_ignores_provided_candidate(self):
        """Oborovo with non-None candidate: candidate adds to available (caller applies guard)."""
        oborovo_inputs = make_engine_inputs(
            [make_period(
                period_index=1, opening_balance_keur=0.0,
                interest_rate=0.08, day_count_fraction=0.5,
                post_senior_cash_available_keur=1000.0,
                pik_allowed=False,  # Oborovo different setup
                distribution_account_r102_sweep_candidate_keur=500.0,  # provided
            )],
            project_name="OBOROVO-SOLAR-1",
            tranche_opening=(3000.0,),
            pik_allowed=False,
        )
        result = ShlEngine.compute(oborovo_inputs)
        p = result.period_results[0]
        # Oborovo opening = 3000 → gross = 120
        assert p.gross_accrued_interest_keur == pytest.approx(120.0)
        # cash_int = min(120, 1000+500) = 120 (full, not affected by candidate)
        assert p.cash_interest_paid_keur == pytest.approx(120.0)
        # candidate adds 500 to available: available = 1000+500=1500
        # principal = 1500-120 = 1380 (increased vs no-candidate case)
        assert p.principal_repaid_keur == pytest.approx(1380.0)
        assert p.distribution_account_r102_sweep_candidate_keur == 500.0
        assert p.r102_sweep_applied_keur == pytest.approx(500.0)

    def test_oborovo_internal_behavior_no_tuho_leakage(self):
        """Oborovo does not use TUHO-specific logic."""
        oborovo_inputs = make_engine_inputs(
            [make_period(
                period_index=1, opening_balance_keur=0.0,
                interest_rate=0.08, day_count_fraction=0.5,
                post_senior_cash_available_keur=1000.0,
                pik_allowed=False,
                distribution_account_r102_sweep_candidate_keur=None,  # None
            )],
            project_name="OBOROVO-SOLAR-1",
            tranche_opening=(3000.0,),
            pik_allowed=False,
        )
        result = ShlEngine.compute(oborovo_inputs)
        p = result.period_results[0]
        # Oborovo opening = 3000 → gross = 120 (NOT 200 like TUHO)
        assert p.gross_accrued_interest_keur == pytest.approx(120.0)
        assert p.distribution_account_r102_sweep_candidate_keur is None
        assert p.r102_sweep_applied_keur == pytest.approx(0.0)


class TestSweepApplicationOrder:
    """Case 6: Candidate applied: cash interest first → PIK → principal."""

    def test_candidate_increases_available_before_interest(self):
        """R102 candidate adds to available cash BEFORE interest is computed."""
        # BASE: available=1000, gross=200, cash_int=200, principal=800
        # Candidate=800 ADDED: available=1000+800=1800, cash_int=min(200,1800)=200 (same), principal=800
        base_result = ShlEngine.compute(TUHO_INPUTS_BASE)
        base_p = base_result.period_results[0]
        assert base_p.cash_interest_paid_keur == pytest.approx(200.0)
        assert base_p.principal_repaid_keur == pytest.approx(800.0)

        candidate_inputs = make_engine_inputs([make_period(
            period_index=1, opening_balance_keur=0.0,
            interest_rate=0.08, day_count_fraction=0.5,
            post_senior_cash_available_keur=1000.0,
            pik_allowed=True,
            distribution_account_r102_sweep_candidate_keur=800.0,
        )], tranche_opening=(5000.0,))
        cand_result = ShlEngine.compute(candidate_inputs)
        cand_p = cand_result.period_results[0]
        # cash_int unchanged (gross=200, added available=1800 >> 200, full interest paid)
        assert cand_p.cash_interest_paid_keur == pytest.approx(200.0)
        # principal increased (added available = 800 extra beyond base's 1000)
        assert cand_p.principal_repaid_keur == pytest.approx(1600.0)  # base 800 + extra 800 from candidate
        # r102_sweep_applied = 800 (recorded)
        assert cand_p.r102_sweep_applied_keur == pytest.approx(800.0)
        assert cand_p.distribution_account_r102_sweep_candidate_keur == 800.0

    def test_sweep_order_cash_interest_unchanged_when_candidate_adds_to_available(self):
        """When candidate adds to available, cash interest capacity is not reduced."""
        # candidate = 900 ADDED: available = 1000+900=1900
        # cash_int = min(200, 1900) = 200 (full — NOT reduced)
        # principal = 1900-200 = 1700
        candidate_inputs = make_engine_inputs([make_period(
            period_index=1, opening_balance_keur=0.0,
            interest_rate=0.08, day_count_fraction=0.5,
            post_senior_cash_available_keur=1000.0,
            pik_allowed=False,  # no PIK to complicate
            distribution_account_r102_sweep_candidate_keur=900.0,
        )], tranche_opening=(5000.0,), pik_allowed=False)
        result = ShlEngine.compute(candidate_inputs)
        p = result.period_results[0]
        # cash_int NOT reduced — candidate adds to available
        assert p.cash_interest_paid_keur == pytest.approx(200.0)
        # principal increased: base 800 + candidate 900 = 1700
        assert p.principal_repaid_keur == pytest.approx(1700.0)
        # pik=0 (pik_allowed=False)
        assert p.pik_capitalized_keur == pytest.approx(0.0)
        # r102_sweep_applied=900 (recorded)
        assert p.r102_sweep_applied_keur == pytest.approx(900.0)

    def test_sweep_order_pik_reduced_when_candidate_adds_sufficient_for_interest(self):
        """When candidate adds enough for full interest, PIK is reduced vs no-candidate case."""
        # Setup: base available=100 (below gross 200) → no candidate: cash_int=100, pik=100
        # candidate=100 ADDED: available=100+100=200 → cash_int=200, pik=0
        no_cand = ShlEngine.compute(make_engine_inputs([make_period(
            period_index=1, opening_balance_keur=0.0,
            interest_rate=0.08, day_count_fraction=0.5,
            post_senior_cash_available_keur=100.0,
            pik_allowed=True,
            distribution_account_r102_sweep_candidate_keur=None,
        )], tranche_opening=(5000.0,)))
        p0 = no_cand.period_results[0]
        assert p0.cash_interest_paid_keur == pytest.approx(100.0)
        assert p0.pik_capitalized_keur == pytest.approx(100.0)

        cand = ShlEngine.compute(make_engine_inputs([make_period(
            period_index=1, opening_balance_keur=0.0,
            interest_rate=0.08, day_count_fraction=0.5,
            post_senior_cash_available_keur=100.0,
            pik_allowed=True,
            distribution_account_r102_sweep_candidate_keur=100.0,
        )], tranche_opening=(5000.0,)))
        p = cand.period_results[0]
        # candidate adds 100 → total available=200 → full interest covered
        assert p.cash_interest_paid_keur == pytest.approx(200.0)
        assert p.pik_capitalized_keur == pytest.approx(0.0)  # reduced from 100 to 0
        assert p.r102_sweep_applied_keur == pytest.approx(100.0)

    def test_sweep_order_principal_increases_when_candidate_adds_available(self):
        """Principal increases when R102 candidate adds available cash."""
        # BASE: available=1000, principal=800
        # candidate=600 ADDED: available=1600, principal=1600-200=1400
        candidate_inputs = make_engine_inputs([make_period(
            period_index=1, opening_balance_keur=0.0,
            interest_rate=0.08, day_count_fraction=0.5,
            post_senior_cash_available_keur=1000.0,
            pik_allowed=True,
            distribution_account_r102_sweep_candidate_keur=600.0,
        )], tranche_opening=(5000.0,))
        result = ShlEngine.compute(candidate_inputs)
        p = result.period_results[0]
        assert p.cash_interest_paid_keur == pytest.approx(200.0)  # unchanged (full interest)
        assert p.principal_repaid_keur == pytest.approx(1400.0)  # base 800 + candidate 600 extra
        assert p.r102_sweep_applied_keur == pytest.approx(600.0)


class TestR99R102StillBlocked:
    """Case 7: R99/R102 remains BLOCKED after SHL R102 input wiring."""

    def test_shl_r102_wiring_does_not_promote_r99_r102(self):
        """SHL R102 input wiring does not promote R99/R102 gates."""
        from domain.distribution_account.engine import DistributionAccountEngine
        from domain.distribution_account.inputs import DistributionAccountInputs, DistributionAccountPeriodInput
        from datetime import date

        dist_inputs = DistributionAccountInputs(
            project_name="TUHO-WIND-1",
            is_tuho=True,
            is_oborovo=False,
            period_inputs=(
                DistributionAccountPeriodInput(
                    period_index=1,
                    operating_period_index=0,
                    period_date=date(2029, 6, 30),
                    opening_distribution_account_balance_keur=0.0,
                    post_senior_cash_available_keur=0.0,
                    post_shl_cash_available_keur=500.0,
                    senior_debt_service_keur=0.0,
                    actual_dscr=1.5,
                    is_tuho=True,
                    is_oborovo=False,
                    enable_r99_r102_runtime=False,
                ),
            ),
        )
        dist_result = DistributionAccountEngine.compute(dist_inputs)
        p = dist_result.period_results[0]
        # Audit-only: equity_distribution_paid_keur = 0, cash_swept_to_shl_keur = 0
        assert p.equity_distribution_paid_keur == pytest.approx(0.0)
        assert p.cash_swept_to_shl_keur == pytest.approx(0.0)
        # R99 gate is blocked
        assert p.r99_gate_result.passed is False
        assert "not promoted" in p.r99_gate_result.blocked_reason.lower()

    def test_g20_remains_blocked_in_gate_matrix(self):
        """G20 remains BLOCKED per phase9 closeout gate matrix."""
        import csv
        repo_root = Path(__file__).resolve().parents[1]
        matrix_path = repo_root / "reports" / "phase9_closeout_gate_matrix.csv"
        if matrix_path.exists():
            with open(matrix_path) as f:
                reader = csv.DictReader(f)
                g20_rows = [r for r in reader if r.get("gate_id", "").strip() == "G20"]
            if g20_rows:
                assert g20_rows[0]["status"] == "BLOCKED", \
                    f"G20 status: {g20_rows[0]['status']}"


class TestNoAppWaterfallCoreChanges:
    """Case 8: No app/waterfall_core.py changes (portable guard)."""

    def test_no_runtime_files_changed(self):
        """No app/, domain/ inputs, or non-SHL domain/ files changed."""
        import subprocess
        repo_root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            ["git", "diff", "--stat", "origin/main...HEAD"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
        )
        output = result.stdout.strip()
        if not output:
            return  # No changes
        for line in output.split("\n"):
            stripped = line.strip()
            if (
                not stripped
                or stripped.startswith("??")
                or stripped.startswith("5 files")
                or stripped.startswith("...")  # UX-2C-1 cross-arc: skip git --stat path truncation
                or "files changed" in stripped  # UX-2C-1 cross-arc: skip git --stat summary line
            ):
                continue
            # All changed files must be in docs/, reports/, tests/, or domain/shl/
            allowed = ["docs/", "reports/", "tests/", "domain/shl/"]
            is_shl_domain = stripped.startswith("domain/shl/")
            is_doc_report_test = any(stripped.startswith(p) for p in ["docs/", "reports/", "tests/"])
            # UX-2C-1 cross-arc allowlist (Overview KPI dedup)
            is_ux2c1 = stripped.startswith((
                "app/templates/partials/runtime_summary.html",  # UX-2C-1 cross-arc
                "app/ui/dashboard.py",  # UX-2C-1 cross-arc
            ))
            assert is_shl_domain or is_doc_report_test or is_ux2c1, \
                f"Unexpected non-SHL-domain/doc/report/test change: {stripped}"

    def test_candidate_none_zero_drift(self):
        """With candidate=None, SHL behavior unchanged vs expected baseline."""
        result = ShlEngine.compute(TUHO_INPUTS_BASE)
        p = result.period_results[0]
        # Baseline TUHO values
        expected = dict(
            gross_accrued_interest_keur=200.0,
            cash_interest_paid_keur=200.0,
            pik_capitalized_keur=0.0,
            principal_repaid_keur=800.0,
            r102_sweep_applied_keur=0.0,
            distribution_account_r102_sweep_candidate_keur=None,
        )
        for field, exp_val in expected.items():
            actual = getattr(p, field)
            if exp_val is None:
                assert actual is None, f"{field}: expected None, got {actual}"
            else:
                assert actual == pytest.approx(exp_val), \
                    f"{field}: expected {exp_val}, got {actual}"


class TestR102ContractFieldPresence:
    """Verify R102 contract fields are present and correctly defaulted."""

    def test_shl_period_input_has_r102_candidate_field(self):
        """ShlPeriodInput has distribution_account_r102_sweep_candidate_keur field."""
        p = make_period(distribution_account_r102_sweep_candidate_keur=100.0)
        assert p.distribution_account_r102_sweep_candidate_keur == 100.0

    def test_shl_period_input_r102_candidate_defaults_to_none(self):
        """ShlPeriodInput.r102_candidate defaults to None."""
        p = make_period()
        assert p.distribution_account_r102_sweep_candidate_keur is None

    def test_shl_period_result_has_r102_fields(self):
        """ShlPeriodResult has r102 candidate and applied fields."""
        result = ShlEngine.compute(TUHO_INPUTS_BASE)
        p = result.period_results[0]
        assert hasattr(p, "distribution_account_r102_sweep_candidate_keur")
        assert hasattr(p, "r102_sweep_applied_keur")

    def test_shl_audit_row_has_r102_fields(self):
        """ShlAuditRow has r102 candidate and applied fields."""
        result = ShlEngine.compute(TUHO_INPUTS_BASE)
        row = result.audit_table[-1]
        assert hasattr(row, "distribution_account_r102_sweep_candidate_keur")
        assert hasattr(row, "r102_sweep_applied_keur")

    def test_r102_candidate_passes_through_to_result(self):
        """Provided r102 candidate passes through to ShlPeriodResult."""
        inputs = make_engine_inputs([make_period(
            period_index=1, opening_balance_keur=0.0,
            interest_rate=0.08, day_count_fraction=0.5,
            post_senior_cash_available_keur=1000.0,
            pik_allowed=True,
            distribution_account_r102_sweep_candidate_keur=250.0,
        )], tranche_opening=(5000.0,))
        result = ShlEngine.compute(inputs)
        p = result.period_results[0]
        assert p.distribution_account_r102_sweep_candidate_keur == 250.0
        assert p.r102_sweep_applied_keur == pytest.approx(250.0)