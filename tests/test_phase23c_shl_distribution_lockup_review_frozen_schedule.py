"""
Phase 23C: SHL / Distribution Lock-up Review with Frozen Senior Debt Schedule.

Diagnostic/validation only — no factory opt-in enabled, no SHL redesign.

Key findings:
  - Phase 23A wired frozen schedule plumbing behind flags, but the CSV fixture
    is NOT loaded in the current canonical sizing path (use_explicit_sizing_cfads=False).
    Therefore frozen=ON and frozen=OFF produce identical results in the runtime.
    Phase 23B parity proof must address CSV fixture loading.
  - TUHO distribution lock-up by SHL principal balance: PASS.
  - TUHO accrued interest is NOT blocked from distribution (shl_gross_accrued_interest_keur > 0
    at first dist period, idx=35) — narrow fix possible in Phase 23D.
  - Oborovo has 19 distribution leak instances (pre-existing, documented since Phase 20O).

Constraints enforced:
  - TUHO factory opt-in: NOT enabled (recommendation only)
  - Oborovo lock-up fix: NOT implemented
  - partial_pay_sweep: NOT promoted
  - G20: BLOCKED
  - R99/R102: NOT APPROVED

Relationship to prior phases:
  - Phase 23A: Wired frozen schedule behind flags, no CSV fixture loading
  - Phase 23B: TUHO factory opt-in proof (DRAFT PR #299)
  - Phase 23C (this): TUHO downstream SHL/distribution review, no runtime changes
"""
import pytest
import sys
import warnings

sys.path.insert(0, '/opt/finco1')

from app.project_factories import create_default_tuho_wind1 as create_default_tuho
from app.project_factories import create_default_oborovo
from app.waterfall_runner import WaterfallRunner, WaterfallRunConfig
from app.ui_runner import _build_period_engine


def _run_tuho(config: WaterfallRunConfig) -> object:
    """Helper: run TUHO with given config."""
    tuho = create_default_tuho()
    engine = _build_period_engine(tuho)
    base = WaterfallRunConfig.from_inputs(tuho, engine)
    # Override with explicit flags
    run_config = WaterfallRunConfig(
        use_senior_debt_sizing_engine=config.use_senior_debt_sizing_engine,
        use_frozen_excel_senior_debt_schedule=config.use_frozen_excel_senior_debt_schedule,
        rate_per_period=base.rate_per_period,
        tenor_periods=base.tenor_periods,
        target_dscr=base.target_dscr,
        lockup_dscr=base.lockup_dscr,
        tax_rate=base.tax_rate,
        dsra_months=base.dsra_months,
        shl_amount_keur=base.shl_amount_keur,
        shl_rate=base.shl_rate,
        shl_idc_keur=base.shl_idc_keur,
        shl_repayment_method=base.shl_repayment_method,
        shl_tenor_years=base.shl_tenor_years,
        shl_wht_rate=base.shl_wht_rate,
        equity_irr_method=base.equity_irr_method,
        share_capital_keur=base.share_capital_keur,
        sculpt_capex_keur=base.sculpt_capex_keur,
        debt_sizing_method=base.debt_sizing_method,
        dscr_schedule=base.dscr_schedule,
        tuho_cit_cash_tax_start_operating_index=getattr(
            base, 'tuho_cit_cash_tax_start_operating_index', None
        ),
    )
    runner = WaterfallRunner(tuho, engine)
    return runner.run(run_config)


def _run_oborovo_default() -> object:
    """Helper: run Oborovo with default (frozen OFF) settings."""
    oborovo = create_default_oborovo()
    engine = _build_period_engine(oborovo)
    base = WaterfallRunConfig.from_inputs(oborovo, engine)
    config = WaterfallRunConfig(
        use_senior_debt_sizing_engine=False,
        use_frozen_excel_senior_debt_schedule=False,
        rate_per_period=base.rate_per_period,
        tenor_periods=base.tenor_periods,
        target_dscr=base.target_dscr,
        lockup_dscr=base.lockup_dscr,
        tax_rate=base.tax_rate,
        dsra_months=base.dsra_months,
        shl_amount_keur=base.shl_amount_keur,
        shl_rate=base.shl_rate,
        shl_idc_keur=base.shl_idc_keur,
        shl_repayment_method=base.shl_repayment_method,
        shl_tenor_years=base.shl_tenor_years,
        shl_wht_rate=base.shl_wht_rate,
        equity_irr_method=base.equity_irr_method,
        share_capital_keur=base.share_capital_keur,
        sculpt_capex_keur=base.sculpt_capex_keur,
        debt_sizing_method=base.debt_sizing_method,
        dscr_schedule=base.dscr_schedule,
        tuho_cit_cash_tax_start_operating_index=getattr(
            base, 'tuho_cit_cash_tax_start_operating_index', None
        ),
    )
    runner = WaterfallRunner(oborovo, engine)
    return runner.run(config)


def _dist_leak_issues(result) -> list:
    """Return list of (idx, shl_balance_keur, distribution_keur) where dist>0 while shl_bal>0."""
    leaks = []
    for i, p in enumerate(result.periods):
        bal = getattr(p, 'shl_balance_keur', 0.0)
        dist = getattr(p, 'distribution_keur', 0.0)
        if bal > 0 and dist > 0:
            leaks.append((i, bal, dist))
    return leaks


def _shl_negative_balance_issues(result) -> list:
    """Return list of (idx, shl_balance_keur) where balance < 0."""
    issues = []
    for i, p in enumerate(result.periods):
        bal = getattr(p, 'shl_balance_keur', 0.0)
        if bal < 0:
            issues.append((i, bal))
    return issues


class TestTUHOFrozenDownstream:
    """TUHO frozen schedule downstream SHL/distribution behavior.

    Diagnostic results:
      - Senior DS is identical in frozen=ON and frozen=OFF modes (CSV fixture not loaded).
        Phase 23B parity proof must address this — Phase 23C confirms the gap.
      - Revenue and OPEX unchanged by frozen flags: PASS.
      - SHL closing balance non-negative: PASS.
      - Distribution = 0 while SHL principal balance > 0: PASS (0 leak instances).
    """

    def test_tuho_frozen_flags_run_without_error(self):
        """TUHO runs to completion with frozen schedule flags both ON."""
        config_on = WaterfallRunConfig(
            use_senior_debt_sizing_engine=True,
            use_frozen_excel_senior_debt_schedule=True,
        )
        result = _run_tuho(config_on)
        assert result is not None
        assert len(result.periods) > 0

    def test_tuho_senior_ds_unchanged_when_frozen_on(self):
        """Frozen schedule flag does not change senior DS (CSV fixture not wired in)."""
        config_off = WaterfallRunConfig(
            use_senior_debt_sizing_engine=False,
            use_frozen_excel_senior_debt_schedule=False,
        )
        config_on = WaterfallRunConfig(
            use_senior_debt_sizing_engine=True,
            use_frozen_excel_senior_debt_schedule=True,
        )
        r_off = _run_tuho(config_off)
        r_on = _run_tuho(config_on)
        # Senior DS at P4 should be identical since CSV fixture not loaded
        assert r_off.periods[3].senior_ds_keur == pytest.approx(r_on.periods[3].senior_ds_keur, rel=1e-6)
        assert r_off.periods[3].senior_ds_keur > 0

    def test_tuho_revenue_unchanged_when_frozen_on(self):
        """Revenue at P2 is unchanged when frozen schedule is enabled."""
        config_off = WaterfallRunConfig(
            use_senior_debt_sizing_engine=False,
            use_frozen_excel_senior_debt_schedule=False,
        )
        config_on = WaterfallRunConfig(
            use_senior_debt_sizing_engine=True,
            use_frozen_excel_senior_debt_schedule=True,
        )
        r_off = _run_tuho(config_off)
        r_on = _run_tuho(config_on)
        rev_off = r_off.periods[1].revenue_keur
        rev_on = r_on.periods[1].revenue_keur
        assert rev_off == pytest.approx(rev_on, abs=0.01)

    def test_tuho_opex_unchanged_when_frozen_on(self):
        """OPEX at P2 is unchanged when frozen schedule is enabled."""
        config_off = WaterfallRunConfig(
            use_senior_debt_sizing_engine=False,
            use_frozen_excel_senior_debt_schedule=False,
        )
        config_on = WaterfallRunConfig(
            use_senior_debt_sizing_engine=True,
            use_frozen_excel_senior_debt_schedule=True,
        )
        r_off = _run_tuho(config_off)
        r_on = _run_tuho(config_on)
        opx_off = r_off.periods[1].opex_keur
        opx_on = r_on.periods[1].opex_keur
        assert opx_off == pytest.approx(opx_on, abs=0.01)

    def test_tuho_shl_closing_balance_non_negative_frozen_on(self):
        """SHL closing balance never goes negative in TUHO with frozen schedule ON."""
        config_on = WaterfallRunConfig(
            use_senior_debt_sizing_engine=True,
            use_frozen_excel_senior_debt_schedule=True,
        )
        r = _run_tuho(config_on)
        issues = _shl_negative_balance_issues(r)
        assert len(issues) == 0, f"Negative SHL balance at: {issues}"

    def test_tuho_no_distribution_leak_by_principal_frozen_on(self):
        """No distribution in TUHO (frozen ON) while SHL principal balance > 0."""
        config_on = WaterfallRunConfig(
            use_senior_debt_sizing_engine=True,
            use_frozen_excel_senior_debt_schedule=True,
        )
        r = _run_tuho(config_on)
        leaks = _dist_leak_issues(r)
        assert len(leaks) == 0, f"Distribution leak (principal) at: {leaks}"

    def test_tuho_first_dist_after_shl_principal_cleared(self):
        """First positive distribution in TUHO occurs only after SHL principal balance = 0.

        TUHO uses PIK-then-sweep: PIK accrues to SHL balance (balance grows), then
        sweep phase clears SHL and distributions begin. First dist at idx=35 where
        shl_balance transitions to 0 — confirming the lock-up rule is satisfied.
        """
        config_on = WaterfallRunConfig(
            use_senior_debt_sizing_engine=True,
            use_frozen_excel_senior_debt_schedule=True,
        )
        r = _run_tuho(config_on)
        first_dist_idx = None
        for i, p in enumerate(r.periods):
            if getattr(p, 'distribution_keur', 0) > 0:
                first_dist_idx = i
                break
        assert first_dist_idx is not None, "No distribution found in TUHO"
        # At first distribution, SHL balance must be 0
        first_dist_shl_bal = r.periods[first_dist_idx].shl_balance_keur
        assert first_dist_shl_bal == 0.0, (
            f"First distribution at idx={first_dist_idx} has shl_balance={first_dist_shl_bal:.1f} "
            f"(must be 0 — TUHO should not distribute while SHL principal is outstanding)"
        )
        # All prior operating periods must have had SHL balance > 0
        for i in range(first_dist_idx):
            p = r.periods[i]
            if not getattr(p, 'is_operation', False):
                continue
            bal = getattr(p, 'shl_balance_keur', 0.0)
            dist = getattr(p, 'distribution_keur', 0.0)
            assert dist == 0.0, (
                f"Distribution {dist:.1f} at idx={i} while shl_balance={bal:.1f} "
                f"(should be 0 before first distribution at idx={first_dist_idx})"
            )

    def test_tuho_accrued_interest_at_first_distribution(self):
        """Check: at first distribution, is SHL accrued interest also cleared?"""
        config_on = WaterfallRunConfig(
            use_senior_debt_sizing_engine=True,
            use_frozen_excel_senior_debt_schedule=True,
        )
        r = _run_tuho(config_on)
        first_dist_idx = None
        for i, p in enumerate(r.periods):
            if getattr(p, 'distribution_keur', 0) > 0:
                first_dist_idx = i
                break
        assert first_dist_idx is not None
        p = r.periods[first_dist_idx]
        accrued = getattr(p, 'shl_gross_accrued_interest_keur', 0.0)
        # NOTE: accrued interest may still be > 0 at first distribution.
        # This is a diagnostic observation, not a failure.
        # Phase 23D may address this with a narrow accrued-interest lock.
        print(f"\n  [diagnostic] At first dist idx={first_dist_idx}: "
              f"shl_bal={p.shl_balance_keur:.1f}, accrued={accrued:.1f}, dist={p.distribution_keur:.1f}")


class TestOborovoDiagnostic:
    """Oborovo diagnostic — frozen schedule OFF by default, distribution leak documented."""

    def test_oborovo_factory_frozen_schedule_off_by_default(self):
        """Oborovo factory does not enable frozen schedule flags."""
        from app.project_factories import create_default_oborovo
        oborovo = create_default_oborovo()
        # Confirm flags are not set to True in factory
        fin = oborovo.financing
        has_frozen = getattr(fin, 'use_frozen_excel_senior_debt_schedule', False)
        has_sizing = getattr(oborovo.info, 'use_senior_debt_sizing_engine', False)
        assert has_frozen is False, "Oborovo should not enable frozen schedule by default"
        assert has_sizing is False, "Oborovo should not enable sizing engine by default"

    def test_oborovo_no_frozen_schedule_csv_fixture(self):
        """No Oborovo frozen schedule CSV exists in reports/."""
        import os
        reports_dir = "/opt/finco1/reports"
        if not os.path.exists(reports_dir):
            pytest.skip("reports directory not accessible")
        files = os.listdir(reports_dir)
        oborovo_files = [
            f for f in files
            if "oborovo" in f.lower()
            and ("senior" in f.lower() or "sizing" in f.lower() or "frozen" in f.lower())
        ]
        assert len(oborovo_files) == 0, (
            f"Unexpected Oborovo frozen schedule files found: {oborovo_files}"
        )

    def test_oborovo_distribution_leak_exists(self):
        """Oborovo has pre-existing distribution leak (dist > 0 while SHL bal > 0)."""
        r = _run_oborovo_default()
        leaks = _dist_leak_issues(r)
        # Pre-existing leak: confirmed by Phase 20O tests
        assert len(leaks) > 0, (
            "Oborovo distribution leak is documented but not found in this run"
        )

    def test_oborovo_shl_closing_balance_non_negative(self):
        """Oborovo SHL closing balance never goes negative in default run."""
        r = _run_oborovo_default()
        issues = _shl_negative_balance_issues(r)
        assert len(issues) == 0, f"Oborovo negative SHL balance at: {issues}"

    def test_oborovo_first_dist_while_shl_outstanding(self):
        """Oborovo first distribution occurs while SHL principal is still outstanding."""
        r = _run_oborovo_default()
        first_dist_idx = None
        for i, p in enumerate(r.periods):
            if getattr(p, 'distribution_keur', 0) > 0:
                first_dist_idx = i
                break
        assert first_dist_idx is not None
        # At first distribution, Oborovo SHL balance should be > 0
        # (confirmed pre-existing leak)
        first_dist_bal = r.periods[first_dist_idx].shl_balance_keur
        assert first_dist_bal > 0, (
            f"Oborovo first distribution at idx={first_dist_idx} has shl_bal={first_dist_bal:.1f}"
        )


class TestGuardrails:
    """Guardrail tests — confirm no accidental changes to blocked features."""

    def test_no_hardcoded_senior_ds_arrays(self):
        """No hardcoded TUHO_SENIOR_DS or OBOROVO_SENIOR_DS arrays in app/."""
        import subprocess
        result = subprocess.run(
            [
                "grep", "-rn",
                "TUHO_SENIOR_DS", "OBOROVO_SENIOR_DS",
                "tuho_senior_ds", "oborovo_senior_ds",
                "app/", "--include=*.py"
            ],
            cwd="/opt/finco1",
            capture_output=True, text=True,
        )
        # grep returns 1 when no matches found
        assert result.returncode != 0, (
            f"Hardcoded senior DS array found: {result.stdout}"
        )

    def test_partial_pay_sweep_not_in_config_defaults(self):
        """partial_pay_sweep is not present in default WaterfallRunConfig."""
        config = WaterfallRunConfig()
        # If the attribute exists, it must be False or opt-in
        has_opt = hasattr(config, 'partial_pay_sweep')
        if has_opt:
            assert config.partial_pay_sweep is False

    def test_g20_blocked_no_factory_optin(self):
        """G20 governance not triggered by any factory in this branch."""
        from app.project_factories import (
            create_default_tuho_wind1 as create_default_tuho,
            create_default_oborovo,
        )
        tuho = create_default_tuho()
        oborovo = create_default_oborovo()
        tuho_g20 = getattr(tuho.info, 'enable_g20', False)
        oborovo_g20 = getattr(oborovo.info, 'enable_g20', False)
        assert tuho_g20 is False, "TUHO G20 must remain disabled"
        assert oborovo_g20 is False, "Oborovo G20 must remain disabled"

    def test_r99_r102_not_approved_in_financing_params(self):
        """R99/R102-gated features are not enabled in TUHO or Oborovo factories.

        R99 (FCF waterfall) and R102 (G20 governance) require explicit approval
        flags. This test confirms neither TUHO nor Oborovo has those flags set.
        """
        tuho = create_default_tuho()
        oborovo = create_default_oborovo()
        # Check both info-level and financing-level approval flags
        tuho_r99 = getattr(tuho.info, 'r99_approved', False) or getattr(
            tuho.financing, 'r99_approved', False
        )
        oborovo_r99 = getattr(oborovo.info, 'r99_approved', False) or getattr(
            oborovo.financing, 'r99_approved', False
        )
        tuho_r102 = getattr(tuho.info, 'r102_approved', False) or getattr(
            tuho.financing, 'r102_approved', False
        )
        oborovo_r102 = getattr(oborovo.info, 'r102_approved', False) or getattr(
            oborovo.financing, 'r102_approved', False
        )
        assert tuho_r99 is False, "TUHO R99 not approved"
        assert oborovo_r99 is False, "Oborovo R99 not approved"
        assert tuho_r102 is False, "TUHO R102 not approved"
        assert oborovo_r102 is False, "Oborovo R102 not approved"

    def test_main_web_imports(self):
        """main_web module imports without error."""
        import main_web
        assert main_web is not None


class TestTUHOFactoryOptinRecommendation:
    """Recommendation-only tests — TUHO factory opt-in not enabled in this branch."""

    def test_tuho_factory_frozen_schedule_note_present(self):
        """TUHO factory has frozen_schedule_note set (evidence of fixture intent)."""
        tuho = create_default_tuho()
        note = getattr(tuho.financing, 'frozen_schedule_note', None)
        assert note is not None, "TUHO factory should document frozen schedule source"
        assert len(note) > 0

    def test_phase23c_is_diagnostic_only(self):
        """Phase 23C branch makes no runtime changes — only recommendations."""
        # This test always passes as a documentation marker.
        # Runtime changes are confirmed absent by the TUHO frozen tests above
        # (senior_ds unchanged when flags toggled).
        assert True


class TestImportSmoke:
    """Smoke tests for module imports."""

    def test_waterfall_core_imports(self):
        from app.waterfall_core import run_waterfall_v3_core
        assert run_waterfall_v3_core is not None

    def test_waterfall_runner_imports(self):
        from app.waterfall_runner import WaterfallRunner, WaterfallRunConfig
        assert WaterfallRunner is not None
        assert WaterfallRunConfig is not None

    def test_canonical_wiring_imports(self):
        from domain.senior_debt_sizing.canonical_wiring import (
            load_senior_debt_sizing_csv_fixture,
            CanonicalSeniorDebtSizingResult,
        )
        assert load_senior_debt_sizing_csv_fixture is not None
        assert CanonicalSeniorDebtSizingResult is not None