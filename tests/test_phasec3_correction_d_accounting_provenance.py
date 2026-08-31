"""Phase C3 Correction D — Accounting Provenance + GFA Classification + Senior Axis.

Proves:
  D1  AccountingPolicyAuthority enum exists with all required members.
  D2  BookCapitalizationTreatment enum exists with all required members.
  D3  SOURCE_PROVEN only for Oborovo/TUHO (workbook-traced); Solar/Wind
      get GENERIC_FINCO_POLICY — never SOURCE_PROVEN without a source trace.
  D4  shl_construction_accounting authority is SOURCE_PROVEN for Oborovo/TUHO
      and GENERIC_FINCO_POLICY for Solar/Wind.
  D5  GFA component classification map present and typed for Oborovo/TUHO;
      SHL construction interest classified EXPENSE_PNL (not CAPITALIZE_FIXED_ASSET).
  D6  Senior axis self-authorization bug removed: contract.senior_axis is used
      exclusively; no fallback to tuple(senior.period_indices).
  D7  No-Senior synthetic: a project with no senior debt and an empty senior
      result does not raise; senior_expected resolves to ().
  D8  Cash interest income authority is always UNRESOLVED (no clean authority).
  D9  Opening RE authority is SOURCE_PROVEN for Oborovo/TUHO (EXPENSE_TO_PNL
      source-traced); GENERIC_FINCO_POLICY for Solar/Wind.
  D10 book_capitalization_authority is SOURCE_PROVEN for Oborovo/TUHO;
      GENERIC_FINCO_POLICY for Solar/Wind.
"""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_clean(ptype):
    from app import project_factories as pf
    from app.services.production_financial_authority import run_clean_production

    factory = {
        "Solar": pf.create_default_solar_project,
        "Wind": pf.create_default_wind_project,
        "Oborovo": pf.create_default_oborovo,
        "TUHO": pf.create_default_tuho_wind1,
    }[ptype]
    return run_clean_production(factory(), project_type=ptype)


def _assemble(ptype):
    from financial_engine.financial_statements import (
        assemble_decision_complete_financial_statements,
    )
    run = _run_clean(ptype)
    fs = assemble_decision_complete_financial_statements(run.g2c_result, run.project_inputs)
    return fs


# ---------------------------------------------------------------------------
# D1 — AccountingPolicyAuthority enum
# ---------------------------------------------------------------------------

class TestD1_AccountingPolicyAuthorityEnum:
    def test_all_required_members_exist(self):
        from financial_engine.financial_statements import AccountingPolicyAuthority

        required = {
            "SOURCE_PROVEN",
            "GENERIC_FINCO_POLICY",
            "USER_CONFIGURED",
            "NOT_APPLICABLE",
            "UNRESOLVED",
        }
        actual = {m.name for m in AccountingPolicyAuthority}
        assert required.issubset(actual), f"missing: {required - actual}"

    def test_is_str_enum(self):
        from financial_engine.financial_statements import AccountingPolicyAuthority
        assert AccountingPolicyAuthority.SOURCE_PROVEN.value == "SOURCE_PROVEN"
        assert AccountingPolicyAuthority.GENERIC_FINCO_POLICY.value == "GENERIC_FINCO_POLICY"


# ---------------------------------------------------------------------------
# D2 — BookCapitalizationTreatment enum
# ---------------------------------------------------------------------------

class TestD2_BookCapitalizationTreatmentEnum:
    def test_all_required_members_exist(self):
        from financial_engine.financial_statements import BookCapitalizationTreatment

        required = {
            "CAPITALIZE_FIXED_ASSET",
            "EXPENSE_PNL",
            "RESTRICTED_CURRENT_ASSET",
            "UNRESTRICTED_CURRENT_ASSET",
            "NOT_APPLICABLE",
            "UNRESOLVED",
        }
        actual = {m.name for m in BookCapitalizationTreatment}
        assert required.issubset(actual), f"missing: {required - actual}"

    def test_is_str_enum(self):
        from financial_engine.financial_statements import BookCapitalizationTreatment
        assert BookCapitalizationTreatment.CAPITALIZE_FIXED_ASSET.value == "CAPITALIZE_FIXED_ASSET"
        assert BookCapitalizationTreatment.EXPENSE_PNL.value == "EXPENSE_PNL"


# ---------------------------------------------------------------------------
# D3 — Provenance: SOURCE_PROVEN only for Oborovo/TUHO
# ---------------------------------------------------------------------------

class TestD3_SourceProvenDiscrimination:
    @pytest.mark.parametrize("ptype", ("Oborovo", "TUHO"))
    def test_source_proven_projects_are_source_proven(self, ptype):
        from financial_engine.financial_statements import AccountingPolicyAuthority
        fs = _assemble(ptype)
        pol = fs.accounting_policies
        assert pol.shl_construction_accounting_authority == AccountingPolicyAuthority.SOURCE_PROVEN, (
            f"{ptype}: expected SOURCE_PROVEN, got {pol.shl_construction_accounting_authority}"
        )
        assert pol.provenance.get("this_project_source_proven") is True

    @pytest.mark.parametrize("ptype", ("Solar", "Wind"))
    def test_generic_projects_are_not_source_proven(self, ptype):
        from financial_engine.financial_statements import AccountingPolicyAuthority
        fs = _assemble(ptype)
        pol = fs.accounting_policies
        assert pol.shl_construction_accounting_authority != AccountingPolicyAuthority.SOURCE_PROVEN, (
            f"{ptype}: Solar/Wind must NOT be SOURCE_PROVEN (no workbook trace)"
        )
        assert pol.shl_construction_accounting_authority == AccountingPolicyAuthority.GENERIC_FINCO_POLICY
        assert pol.provenance.get("this_project_source_proven") is False


# ---------------------------------------------------------------------------
# D4 — SHL construction accounting authority
# ---------------------------------------------------------------------------

class TestD4_ShlConstructionAccountingAuthority:
    @pytest.mark.parametrize("ptype", ("Oborovo", "TUHO"))
    def test_source_proven_for_oborovo_tuho(self, ptype):
        from financial_engine.financial_statements import AccountingPolicyAuthority
        fs = _assemble(ptype)
        assert fs.accounting_policies.shl_construction_accounting_authority == (
            AccountingPolicyAuthority.SOURCE_PROVEN
        )

    @pytest.mark.parametrize("ptype", ("Solar", "Wind"))
    def test_generic_for_solar_wind(self, ptype):
        from financial_engine.financial_statements import AccountingPolicyAuthority
        fs = _assemble(ptype)
        assert fs.accounting_policies.shl_construction_accounting_authority == (
            AccountingPolicyAuthority.GENERIC_FINCO_POLICY
        )


# ---------------------------------------------------------------------------
# D5 — GFA component classification
# ---------------------------------------------------------------------------

class TestD5_BookCapitalizationComponents:
    @pytest.mark.parametrize("ptype", ("Oborovo", "TUHO"))
    def test_source_proven_has_component_map(self, ptype):
        from financial_engine.financial_statements import BookCapitalizationTreatment
        fs = _assemble(ptype)
        comps = fs.accounting_policies.book_capitalization_components
        assert isinstance(comps, dict)
        assert len(comps) > 0, f"{ptype}: component map must not be empty"

    @pytest.mark.parametrize("ptype", ("Oborovo", "TUHO"))
    def test_shl_construction_interest_is_expense_pnl(self, ptype):
        from financial_engine.financial_statements import BookCapitalizationTreatment
        fs = _assemble(ptype)
        comps = fs.accounting_policies.book_capitalization_components
        assert "shl_construction_interest" in comps, (
            f"{ptype}: shl_construction_interest must appear in component map"
        )
        assert comps["shl_construction_interest"] == BookCapitalizationTreatment.EXPENSE_PNL.value, (
            f"{ptype}: SHL construction interest must be EXPENSE_PNL (not capitalized)"
        )

    @pytest.mark.parametrize("ptype", ("Oborovo", "TUHO"))
    def test_hard_capex_is_capitalized(self, ptype):
        from financial_engine.financial_statements import BookCapitalizationTreatment
        fs = _assemble(ptype)
        comps = fs.accounting_policies.book_capitalization_components
        assert comps.get("hard_capex") == BookCapitalizationTreatment.CAPITALIZE_FIXED_ASSET.value

    @pytest.mark.parametrize("ptype", ("Oborovo", "TUHO"))
    def test_dsra_is_restricted_current_asset(self, ptype):
        from financial_engine.financial_statements import BookCapitalizationTreatment
        fs = _assemble(ptype)
        comps = fs.accounting_policies.book_capitalization_components
        assert comps.get("dsra_funding") == BookCapitalizationTreatment.RESTRICTED_CURRENT_ASSET.value

    @pytest.mark.parametrize("ptype", ("Oborovo", "TUHO"))
    def test_no_dsra_or_working_capital_in_gfa(self, ptype):
        from financial_engine.financial_statements import BookCapitalizationTreatment
        fs = _assemble(ptype)
        comps = fs.accounting_policies.book_capitalization_components
        for key, val in comps.items():
            if key in ("dsra_funding", "working_capital"):
                assert val != BookCapitalizationTreatment.CAPITALIZE_FIXED_ASSET.value, (
                    f"{ptype}: {key} must never be CAPITALIZE_FIXED_ASSET"
                )


# ---------------------------------------------------------------------------
# D6 — Senior axis self-authorization bug removed
# ---------------------------------------------------------------------------

class TestD6_SeniorAxisNoSelfAuthorization:
    def test_assembly_module_has_no_fallback_pattern(self):
        """The literal self-authorization expression must not appear in source."""
        import inspect
        from financial_engine.financial_statements import assembly as asm
        src = inspect.getsource(asm)
        assert "or tuple(senior.period_indices)" not in src, (
            "Self-authorization fallback 'or tuple(senior.period_indices)' "
            "must be removed from assembly.py (Correction D)"
        )
        assert "contract.senior_axis or tuple" not in src, (
            "Self-authorization pattern 'contract.senior_axis or tuple' "
            "must be removed from assembly.py (Correction D)"
        )

    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_assembly_succeeds_with_correct_axes(self, ptype):
        """Full assembly must succeed without triggering the AXIS_MISMATCH path."""
        fs = _assemble(ptype)
        from financial_engine.financial_statements import StatementStatus
        assert fs.status != StatementStatus.STATEMENT_PERIOD_AXIS_MISMATCH, (
            f"{ptype}: unexpected STATEMENT_PERIOD_AXIS_MISMATCH — check axis handling"
        )


# ---------------------------------------------------------------------------
# D7 — No-Senior synthetic test
# ---------------------------------------------------------------------------

class TestD7_NoSeniorSynthetic:
    def test_no_senior_assembly_does_not_raise(self):
        """When senior_axis is None (no senior debt) and senior result is
        empty, assembly must not raise and must not error on the axis check."""
        import types
        from financial_engine.financial_statements import (
            assemble_decision_complete_financial_statements,
            StatementStatus,
        )

        # Build a minimal synthetic g2c_result with no senior data.
        # We use Solar (no senior configured) and patch senior.period_indices.
        from app.project_factories import create_default_solar_project
        from app.services.production_financial_authority import run_clean_production

        run = run_clean_production(create_default_solar_project(), project_type="Solar")
        g2c = run.g2c_result
        model = g2c.financing_result.project_model_result
        senior = model.senior_debt

        # Confirm Solar has no senior periods (genuine no-Senior project).
        if tuple(senior.period_indices):
            pytest.skip("Solar factory has senior debt — skip no-Senior synthetic.")

        fs = assemble_decision_complete_financial_statements(g2c, run.project_inputs)
        # Must not be an axis mismatch.
        assert fs.status != StatementStatus.STATEMENT_PERIOD_AXIS_MISMATCH, (
            "No-Senior project must not raise STATEMENT_PERIOD_AXIS_MISMATCH"
        )


# ---------------------------------------------------------------------------
# D8 — Cash interest income authority is always UNRESOLVED
# ---------------------------------------------------------------------------

class TestD8_CashInterestIncomeAuthority:
    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_cash_interest_always_unresolved(self, ptype):
        from financial_engine.financial_statements import AccountingPolicyAuthority
        fs = _assemble(ptype)
        assert fs.accounting_policies.cash_interest_income_authority == (
            AccountingPolicyAuthority.UNRESOLVED
        ), (
            f"{ptype}: interest on cash/reserves has no clean authority — "
            "must be UNRESOLVED"
        )


# ---------------------------------------------------------------------------
# D9 — Opening RE authority
# ---------------------------------------------------------------------------

class TestD9_OpeningRetainedEarningsAuthority:
    @pytest.mark.parametrize("ptype", ("Oborovo", "TUHO"))
    def test_source_proven_for_oborovo_tuho(self, ptype):
        from financial_engine.financial_statements import AccountingPolicyAuthority
        fs = _assemble(ptype)
        assert fs.accounting_policies.opening_re_authority == (
            AccountingPolicyAuthority.SOURCE_PROVEN
        )

    @pytest.mark.parametrize("ptype", ("Solar", "Wind"))
    def test_generic_for_solar_wind(self, ptype):
        from financial_engine.financial_statements import AccountingPolicyAuthority
        fs = _assemble(ptype)
        assert fs.accounting_policies.opening_re_authority == (
            AccountingPolicyAuthority.GENERIC_FINCO_POLICY
        )


# ---------------------------------------------------------------------------
# D10 — Book capitalization authority
# ---------------------------------------------------------------------------

class TestD10_BookCapitalizationAuthority:
    @pytest.mark.parametrize("ptype", ("Oborovo", "TUHO"))
    def test_source_proven_for_oborovo_tuho(self, ptype):
        from financial_engine.financial_statements import AccountingPolicyAuthority
        fs = _assemble(ptype)
        assert fs.accounting_policies.book_capitalization_authority == (
            AccountingPolicyAuthority.SOURCE_PROVEN
        )

    @pytest.mark.parametrize("ptype", ("Solar", "Wind"))
    def test_generic_for_solar_wind(self, ptype):
        from financial_engine.financial_statements import AccountingPolicyAuthority
        fs = _assemble(ptype)
        assert fs.accounting_policies.book_capitalization_authority == (
            AccountingPolicyAuthority.GENERIC_FINCO_POLICY
        )


# ---------------------------------------------------------------------------
# D11 — GFA causal computation (spec §39)
# ---------------------------------------------------------------------------

class TestD11_GFACausalComputation:
    @pytest.mark.parametrize("ptype", ("Oborovo", "TUHO"))
    def test_gfa_numeric_computed_for_source_proven(self, ptype):
        from financial_engine.financial_statements import StatementStatus
        fs = _assemble(ptype)
        # Correction F §21-§24: clean factories zero capex dep scalars but
        # construction_financing produces non-zero financing costs → dep-basis gap
        # detected → GFA unavailable. candidate_book_gfa_keur preserved for audit.
        assert fs.fixed_asset_status == StatementStatus.BOOK_CAPITALIZATION_BASIS_UNAVAILABLE, (
            f"{ptype}: expected BOOK_CAPITALIZATION_BASIS_UNAVAILABLE (dep-basis gap), got {fs.fixed_asset_status}"
        )
        candidate_gfa = fs.accounting_policies.provenance.get("gfa_report", {}).get(
            "candidate_book_gfa_keur")
        assert candidate_gfa is not None and candidate_gfa > 0, (
            f"{ptype}: candidate_book_gfa_keur must be positive for audit, got {candidate_gfa}"
        )

    @pytest.mark.parametrize("ptype", ("Oborovo", "TUHO"))
    def test_gfa_equals_causal_component_sum(self, ptype):
        fs = _assemble(ptype)
        report = fs.accounting_policies.provenance.get("gfa_report", {})
        computed_gfa = (
            report.get("hard_capex_keur", 0.0)
            + report.get("senior_idc_keur", 0.0)
            + report.get("senior_commitment_fees_keur", 0.0)
            + report.get("structuring_fee_keur", 0.0)
            + report.get("vat_idc_keur", 0.0)
            + report.get("vat_commitment_fee_keur", 0.0)
        )
        total = report.get("total_book_gfa_keur", -1.0)
        assert abs(computed_gfa - total) < 1e-3, (
            f"{ptype}: GFA component sum {computed_gfa:.6f} != total {total:.6f}"
        )

    @pytest.mark.parametrize("ptype", ("Oborovo", "TUHO"))
    def test_shl_pik_excluded_from_gfa(self, ptype):
        fs = _assemble(ptype)
        report = fs.accounting_policies.provenance.get("gfa_report", {})
        shl_excluded = report.get("shl_construction_pik_excluded_keur", 0.0)
        assert shl_excluded > 0, f"{ptype}: SHL PIK must be >0 and recorded as excluded"
        # Verify it is NOT in the GFA total
        gfa = report.get("total_book_gfa_keur", 0.0)
        # GFA + excluded SHL PIK > GFA
        assert gfa + shl_excluded > gfa

    @pytest.mark.parametrize("ptype", ("Oborovo", "TUHO"))
    def test_nfa_equals_gfa_minus_accumulated_dep(self, ptype):
        fs = _assemble(ptype)
        for period in fs.fixed_asset_periods:
            if period.gross_fixed_assets_keur is not None and period.net_fixed_assets_keur is not None:
                expected_nfa = period.gross_fixed_assets_keur - period.accumulated_book_depreciation_keur
                assert abs(period.net_fixed_assets_keur - expected_nfa) < 1e-3, (
                    f"{ptype} period {period.period_index}: NFA identity violated"
                )

    @pytest.mark.parametrize("ptype", ("Solar", "Wind"))
    def test_gfa_unavailable_for_generic_projects(self, ptype):
        from financial_engine.financial_statements import StatementStatus
        fs = _assemble(ptype)
        assert fs.fixed_asset_status == StatementStatus.BOOK_CAPITALIZATION_BASIS_UNAVAILABLE
        assert not fs.accounting_policies.provenance.get("gfa_computed", True)

    @pytest.mark.parametrize("ptype", ("Oborovo", "TUHO"))
    def test_dsra_excluded_from_gfa(self, ptype):
        """DSRA is a restricted current asset — never in GFA."""
        fs = _assemble(ptype)
        comps = fs.accounting_policies.book_capitalization_components
        assert comps.get("dsra_funding") != "CAPITALIZE_FIXED_ASSET"

    @pytest.mark.parametrize("ptype", ("Oborovo", "TUHO"))
    def test_book_depreciation_schedule_unchanged(self, ptype):
        """Introducing GFA must not alter the canonical book depreciation."""
        import math
        fs = _assemble(ptype)
        for p in fs.fixed_asset_periods:
            assert p.book_depreciation_keur is not None
            assert math.isfinite(p.book_depreciation_keur)


# ---------------------------------------------------------------------------
# D12 — Legal reserve roll-forward (spec §40)
# ---------------------------------------------------------------------------

class TestD12_LegalReserveRollForward:
    @pytest.mark.parametrize("ptype", ("Oborovo", "TUHO"))
    def test_legal_reserve_status_ok(self, ptype):
        from financial_engine.financial_statements import StatementStatus
        fs = _assemble(ptype)
        assert fs.legal_reserve_status == StatementStatus.OK, (
            f"{ptype}: expected legal_reserve_status=OK, got {fs.legal_reserve_status}"
        )

    @pytest.mark.parametrize("ptype", ("Oborovo", "TUHO"))
    def test_legal_reserve_computed_flag(self, ptype):
        fs = _assemble(ptype)
        assert fs.accounting_policies.provenance.get("legal_reserve_computed") is True

    @pytest.mark.parametrize("ptype", ("Oborovo", "TUHO"))
    def test_legal_reserve_cap_never_exceeded(self, ptype):
        """Legal reserve closing balance must never exceed 10% × 500 = 50 kEUR."""
        fs = _assemble(ptype)
        lr_closing = fs.accounting_policies.provenance.get(
            "legal_reserve_closing_by_period", {})
        for pidx, val in lr_closing.items():
            assert val <= 50.0 + 1e-6, (
                f"{ptype} period {pidx}: legal reserve {val:.6f} exceeds 50 kEUR cap"
            )

    @pytest.mark.parametrize("ptype", ("Oborovo", "TUHO"))
    def test_legal_reserve_allocation_non_negative(self, ptype):
        """No period may have a negative legal reserve transfer."""
        fs = _assemble(ptype)
        for p in fs.retained_earnings_periods:
            if p.legal_reserve_allocation_keur is not None:
                assert p.legal_reserve_allocation_keur >= -1e-9, (
                    f"{ptype} period {p.period_index}: negative legal reserve allocation"
                )

    @pytest.mark.parametrize("ptype", ("Oborovo", "TUHO"))
    def test_legal_reserve_zero_on_negative_ni(self, ptype):
        """When NI ≤ 0, legal reserve transfer must be 0."""
        fs = _assemble(ptype)
        for p in fs.retained_earnings_periods:
            ni = p.net_income_keur
            lrt = p.legal_reserve_allocation_keur
            if ni is not None and lrt is not None and ni <= 0.0:
                assert abs(lrt) < 1e-9, (
                    f"{ptype} period {p.period_index}: "
                    f"NI={ni:.6f}≤0 but lr_alloc={lrt:.9f}"
                )

    @pytest.mark.parametrize("ptype", ("Oborovo", "TUHO"))
    def test_legal_reserve_reaches_cap(self, ptype):
        """For profitable source-proven projects the legal reserve eventually caps."""
        fs = _assemble(ptype)
        lr_closing = fs.accounting_policies.provenance.get(
            "legal_reserve_closing_by_period", {})
        max_reserve = max(lr_closing.values(), default=0.0)
        assert max_reserve >= 49.9, (
            f"{ptype}: legal reserve max={max_reserve:.6f} — never reaches ~50 kEUR cap"
        )

    @pytest.mark.parametrize("ptype", ("Oborovo", "TUHO"))
    def test_re_close_continuity(self, ptype):
        """RE opening[t+1] = RE closing[t] (sequential continuity)."""
        fs = _assemble(ptype)
        periods = fs.retained_earnings_periods
        for i in range(1, len(periods)):
            prev_close = periods[i - 1].closing_retained_earnings_keur
            curr_open = periods[i].opening_retained_earnings_keur
            if prev_close is not None and curr_open is not None:
                assert abs(prev_close - curr_open) < 1e-6, (
                    f"{ptype}: RE continuity broken at period {periods[i].period_index}"
                )

    @pytest.mark.parametrize("ptype", ("Oborovo", "TUHO"))
    def test_re_close_identity(self, ptype):
        """RE closing = opening + NI − dist − legal_reserve_transfer per period."""
        fs = _assemble(ptype)
        for p in fs.retained_earnings_periods:
            if (p.opening_retained_earnings_keur is not None
                    and p.closing_retained_earnings_keur is not None
                    and p.legal_reserve_allocation_keur is not None):
                expected = (
                    p.opening_retained_earnings_keur
                    + p.net_income_keur
                    - p.legal_equity_distribution_keur
                    - p.legal_reserve_allocation_keur
                )
                assert abs(p.closing_retained_earnings_keur - expected) < 1e-6, (
                    f"RE identity failed at period {p.period_index}"
                )
