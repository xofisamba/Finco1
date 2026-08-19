"""test_pr1_tax_loss_utilisation_gate_propagation.py

PR-1 / P0-2 MISSING_ADAPTER_PROPAGATION fix tests.

Three tests:

  A. TAXABLE_INCOME_POSITIVE gate propagates through adapter (baseline).
  B. EBT_POSITIVE gate propagates through adapter (would fail on pre-fix main
     where TaxPolicy.loss_utilisation_gate always defaulted to TAXABLE_INCOME_POSITIVE).
  C. Behavioral discrimination: synthetic causal inputs prove the propagated policy
     reaches the actual calculate_tax() execution path and is not merely stored.

Test C construction:
  - Real OperatingPeriodResult tuple from Oborovo operating model.
  - Synthetic SHL interest injected via period_interest: large enough so
      EBT_gate = ebitda - tax_dep - total_interest - shl_non_deductible < 0
      while taxable_before_lcf = ebitda - tax_dep > 0
    This is the discriminating case (ATAD=False → deductible_interest=0).
  - Opening loss vintage injected: 200_000 kEUR from tax year 0.
  - Under TAXABLE_INCOME_POSITIVE: loss consumed (taxable_before > 0), lower CIT.
  - Under EBT_POSITIVE: loss blocked (EBT_gate < 0), full taxable income taxed, higher CIT.
  - The numerical difference confirms gate reaches calculate_tax() execution path.

Governance (PR-1):
  - No project-name dispatch.
  - No output fitting. No expected_delta balancing.
  - No source Senior/SHL injection.
  - No KUPI source totals as expected outputs.
  - Production scope: financial_engine/adapters/tax_inputs.py only.
"""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _oborovo_with_gate(gate_value):
    """Return a copy of the default Oborovo ProjectInputs with the given gate."""
    from dataclasses import replace
    from app.project_factories import create_default_oborovo
    from finco_core.inputs._models import TaxLossUtilisationGate

    proj = create_default_oborovo()
    new_tax = replace(proj.tax, tax_loss_utilisation_gate=gate_value)
    return replace(proj, tax=new_tax)


def _build_contract(proj):
    from financial_engine.adapters.tax_inputs import build_tax_contract_from_project_inputs
    return build_tax_contract_from_project_inputs(proj)


# ---------------------------------------------------------------------------
# Test A: TAXABLE_INCOME_POSITIVE gate propagates
# ---------------------------------------------------------------------------

class TestGateA_TaxableIncomePositive:
    """A. Adapter propagates TAXABLE_INCOME_POSITIVE gate to TaxPolicy."""

    def test_taxable_income_positive_gate_propagated(self):
        from finco_core.inputs._models import TaxLossUtilisationGate
        from financial_engine.policies.tax import TaxLossUtilisationGate as EngineTaxLossUtilisationGate

        proj = _oborovo_with_gate(TaxLossUtilisationGate.TAXABLE_INCOME_POSITIVE)
        contract = _build_contract(proj)

        assert (
            contract.policy.loss_utilisation_gate
            == EngineTaxLossUtilisationGate.TAXABLE_INCOME_POSITIVE
        ), (
            f"Expected TAXABLE_INCOME_POSITIVE gate in TaxPolicy, "
            f"got {contract.policy.loss_utilisation_gate!r}"
        )


# ---------------------------------------------------------------------------
# Test B: EBT_POSITIVE gate propagates
# ---------------------------------------------------------------------------

class TestGateB_EbtPositive:
    """B. Adapter propagates EBT_POSITIVE gate to TaxPolicy.

    This test would fail on pre-PR-1 main because the adapter did not read
    tax.tax_loss_utilisation_gate; TaxPolicy.loss_utilisation_gate would have
    defaulted to TAXABLE_INCOME_POSITIVE regardless of the ProjectInputs field.
    """

    def test_ebt_positive_gate_propagated(self):
        from finco_core.inputs._models import TaxLossUtilisationGate
        from financial_engine.policies.tax import TaxLossUtilisationGate as EngineTaxLossUtilisationGate

        proj = _oborovo_with_gate(TaxLossUtilisationGate.EBT_POSITIVE)
        contract = _build_contract(proj)

        assert (
            contract.policy.loss_utilisation_gate
            == EngineTaxLossUtilisationGate.EBT_POSITIVE
        ), (
            f"Expected EBT_POSITIVE gate in TaxPolicy, "
            f"got {contract.policy.loss_utilisation_gate!r}. "
            "This fails on pre-PR-1 main where the adapter did not forward "
            "tax.tax_loss_utilisation_gate."
        )


# ---------------------------------------------------------------------------
# Fixtures for Test C
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def _oborovo_operating_periods():
    """Real OperatingPeriodResult tuple from Oborovo operating model.

    Used by Test C to get genuine period geometry (dates, EBITDA, tax_dep).
    """
    from app.project_factories import create_default_oborovo
    from financial_engine.adapters.project_inputs import from_project_inputs
    from financial_engine.orchestrator import run_operating_model

    proj = create_default_oborovo()
    op_input = from_project_inputs(proj)
    result = run_operating_model(op_input)
    # Return only operation periods (exclude construction)
    return tuple(p for p in result.periods if p.is_operation)


# ---------------------------------------------------------------------------
# Test C: Behavioral discrimination via synthetic causal inputs
# ---------------------------------------------------------------------------

class TestGateC_BehavioralDiscrimination:
    """C. Prove the propagated gate reaches calculate_tax() execution path.

    Two TaxCalculationInput objects share the same operating periods and
    the same injected SHL interest, but differ only in loss_utilisation_gate.
    A large opening loss + SHL_non_deductible chosen so that:

      taxable_before_lcf = ebitda - tax_dep + 0 (ATAD=False) > 0  (profit year)
      EBT_gate           = ebitda - tax_dep - shl_nd           < 0 (EBT blocks)

    produces a detectable difference in loss_used and CIT between the two gates.

    No KUPI source totals are used. No expected_delta balancing.
    """

    @pytest.fixture
    def _tax_inputs_pair(self, _oborovo_operating_periods):
        """Build two TaxCalculationInputs: TAXABLE_INCOME_POSITIVE vs EBT_POSITIVE.

        Both share the same Oborovo operating periods and synthetic SHL injection.
        SHL is set FULLY_NON_DEDUCTIBLE so it drives a wedge between:
          - taxable_before_lcf (no SHL term, since ATAD=False and deductible=0)
          - EBT_gate (subtracts full SHL_nd)
        Opening loss is large enough to absorb a profit year's taxable income.
        """
        from dataclasses import replace
        from financial_engine.inputs import (
            TaxCalculationInput,
            OpeningTaxLossVintageInput,
            PeriodInterestInput,
        )
        from financial_engine.policies.tax import (
            CashTaxTiming,
            ShlInterestDeductibilityMode,
            TaxLossUtilisationGate,
            TaxPolicy,
        )

        periods = _oborovo_operating_periods

        # Oborovo first operation period EBITDA minus tax_dep gives taxable_before.
        # Inject SHL_nd large enough to make EBT_gate < 0 in all profit periods.
        # Use 10_000 kEUR per period — well above Oborovo's typical EBITDA-tax_dep spread.
        SHL_PER_PERIOD = 10_000.0  # kEUR — non-deductible SHL interest per period
        # Opening loss = 5_000 kEUR — enough to partially offset one year without zeroing
        # all years, so the gate choice is visible in loss_used.
        OPENING_LOSS = 5_000.0

        period_interest = tuple(
            PeriodInterestInput(
                period_index=p.period_index,
                shl_interest_keur=SHL_PER_PERIOD,
            )
            for p in periods
        )

        # Compute actual first model tax year so the opening loss isn't immediately expired.
        from financial_engine.tax.tax_year import build_tax_year_bases
        from financial_engine.tax.engine import _build_interest_map, _build_adj_map

        # Need a provisional policy for build_tax_year_bases (gate doesn't matter for year discovery)
        from financial_engine.policies.tax import (
            CashTaxTiming as _CTT,
            ShlInterestDeductibilityMode as _SIM,
            TaxLossUtilisationGate as _TLG,
            TaxPolicy as _TP,
        )
        _probe_policy = _TP(
            policy_id="probe", policy_version="1.0.0",
            corporate_rate=0.18, periods_per_tax_year=2, loss_carryforward_years=5,
            atad_enabled=False, atad_ebitda_limit=0.3, atad_de_minimis_threshold_keur_annual=3000.0,
            cash_tax_timing=_CTT.TAX_YEAR_LAST_PERIOD, cash_tax_payment_lag_periods=0,
            shl_interest_tax_treatment_enabled=True,
            shl_interest_deductibility=_SIM.FULLY_NON_DEDUCTIBLE,
            shl_interest_deductible_pct=0.0,
            loss_utilisation_gate=_TLG.TAXABLE_INCOME_POSITIVE,
        )
        _bases = build_tax_year_bases(
            periods, _build_interest_map(period_interest), _build_adj_map(()), _probe_policy
        )
        _first_tax_year = _bases[0].tax_year
        # Opening loss from the year immediately before the first model tax year
        # → within the 5-year carryforward window for the entire model horizon.
        opening = (
            OpeningTaxLossVintageInput(
                origin_tax_year=_first_tax_year - 1,
                amount_keur=OPENING_LOSS,
            ),
        )

        def _make_input(gate: TaxLossUtilisationGate) -> TaxCalculationInput:
            policy = TaxPolicy(
                policy_id="test-pr1-discrimination",
                policy_version="1.0.0",
                corporate_rate=0.18,
                periods_per_tax_year=2,
                loss_carryforward_years=5,
                atad_enabled=False,
                atad_ebitda_limit=0.3,
                atad_de_minimis_threshold_keur_annual=3_000.0,
                cash_tax_timing=CashTaxTiming.TAX_YEAR_LAST_PERIOD,
                cash_tax_payment_lag_periods=0,
                shl_interest_tax_treatment_enabled=True,
                shl_interest_deductibility=ShlInterestDeductibilityMode.FULLY_NON_DEDUCTIBLE,
                shl_interest_deductible_pct=0.0,
                loss_utilisation_gate=gate,
            )
            return TaxCalculationInput(
                policy=policy,
                opening_loss_vintages=opening,
                period_interest=period_interest,
                period_adjustments=(),
            )

        return (
            _make_input(TaxLossUtilisationGate.TAXABLE_INCOME_POSITIVE),
            _make_input(TaxLossUtilisationGate.EBT_POSITIVE),
            periods,
        )

    def test_ebt_gate_value_is_negative_for_discriminating_periods(
        self, _tax_inputs_pair
    ):
        """Prove the synthetic setup actually creates a discriminating case.

        For at least one tax year:
          EBT_gate = ebitda - tax_dep - total_interest - shl_nd < 0
          taxable_before_lcf = ebitda - tax_dep > 0

        This is the structural precondition for gate discrimination.
        """
        from financial_engine.tax.tax_year import build_tax_year_bases
        from financial_engine.tax.engine import _build_interest_map, _build_adj_map

        _ti_contract, _ebt_contract, periods = _tax_inputs_pair
        interest_map = _build_interest_map(_ebt_contract.period_interest)
        adj_map = _build_adj_map(_ebt_contract.period_adjustments)
        bases = build_tax_year_bases(periods, interest_map, adj_map, _ebt_contract.policy)

        at_least_one_discriminating = False
        for basis in bases:
            taxable_before = basis.ebitda_keur - basis.tax_depreciation_keur
            ebt_gate = (
                basis.ebitda_keur
                - basis.tax_depreciation_keur
                - basis.total_interest_keur
                - basis.shl_non_deductible_interest_keur
            )
            if taxable_before > 0 and ebt_gate <= 0:
                at_least_one_discriminating = True
                break

        assert at_least_one_discriminating, (
            "Synthetic setup does not produce a discriminating tax year "
            "(taxable_before > 0 AND ebt_gate ≤ 0). "
            "Increase SHL_PER_PERIOD or verify Oborovo EBITDA > tax_dep in some period."
        )

    def test_taxable_income_gate_uses_opening_loss(self, _tax_inputs_pair):
        """TAXABLE_INCOME_POSITIVE: opening loss consumed (taxable_before > 0 in profit years)."""
        from financial_engine.tax.engine import calculate_tax

        ti_contract, _ebt_contract, periods = _tax_inputs_pair
        result = calculate_tax(periods, ti_contract)

        loss_used_total = sum(r.loss_used_keur for r in result.annual_results)
        assert loss_used_total > 0.0, (
            "TAXABLE_INCOME_POSITIVE gate: opening loss should be utilised "
            f"in years where taxable_before > 0, got loss_used_total={loss_used_total}"
        )

    def test_ebt_gate_blocks_opening_loss(self, _tax_inputs_pair):
        """EBT_POSITIVE: opening loss NOT consumed when EBT_gate ≤ 0.

        Because SHL_nd is large, EBT_gate < 0 in all profit years,
        so the EBT_POSITIVE gate blocks loss utilisation throughout.
        """
        from financial_engine.tax.engine import calculate_tax

        _ti_contract, ebt_contract, periods = _tax_inputs_pair
        result = calculate_tax(periods, ebt_contract)

        loss_used_total = sum(r.loss_used_keur for r in result.annual_results)
        assert loss_used_total == 0.0, (
            "EBT_POSITIVE gate: opening loss should NOT be utilised "
            f"(EBT_gate ≤ 0 in all profit years), "
            f"got loss_used_total={loss_used_total}"
        )

    def test_gate_discrimination_produces_different_cit(self, _tax_inputs_pair):
        """EBT_POSITIVE produces higher CIT than TAXABLE_INCOME_POSITIVE.

        EBT_POSITIVE blocks loss use → more taxable income → more CIT.
        TAXABLE_INCOME_POSITIVE allows loss use → reduced taxable income → less CIT.
        Numerical difference proves gate reached the engine execution path.
        """
        from financial_engine.tax.engine import calculate_tax

        ti_contract, ebt_contract, periods = _tax_inputs_pair
        res_ti = calculate_tax(periods, ti_contract)
        res_ebt = calculate_tax(periods, ebt_contract)

        cit_ti = sum(r.current_tax_liability_keur for r in res_ti.annual_results)
        cit_ebt = sum(r.current_tax_liability_keur for r in res_ebt.annual_results)

        assert cit_ebt > cit_ti, (
            f"Expected EBT_POSITIVE CIT ({cit_ebt:.4f} kEUR) > "
            f"TAXABLE_INCOME_POSITIVE CIT ({cit_ti:.4f} kEUR). "
            "Gate discrimination not confirmed: both gates produced the same CIT."
        )

    def test_adapter_round_trip_gate_reaches_execute_path(self, _oborovo_operating_periods):
        """Adapter round-trip: ProjectInputs gate → adapter → calculate_tax() → different output.

        Uses the adapter (not direct TaxPolicy construction) to confirm end-to-end
        propagation from ProjectInputs through the adapter to the engine.

        TAXABLE_INCOME_POSITIVE: opening loss consumed → lower CIT.
        EBT_POSITIVE: opening loss blocked → higher CIT.
        """
        from dataclasses import replace
        from app.project_factories import create_default_oborovo
        from finco_core.inputs._models import TaxLossUtilisationGate as InputGate
        from financial_engine.adapters.tax_inputs import build_tax_contract_from_project_inputs
        from financial_engine.inputs import (
            OpeningTaxLossVintageInput,
            PeriodInterestInput,
        )
        from financial_engine.tax.engine import calculate_tax

        periods = _oborovo_operating_periods

        SHL_PER_PERIOD = 10_000.0
        OPENING_LOSS = 5_000.0

        period_interest = tuple(
            PeriodInterestInput(
                period_index=p.period_index,
                shl_interest_keur=SHL_PER_PERIOD,
            )
            for p in periods
        )

        # Determine first model tax year to anchor opening loss within the LCF window
        from financial_engine.tax.tax_year import build_tax_year_bases
        from financial_engine.tax.engine import _build_interest_map, _build_adj_map
        from financial_engine.policies.tax import (
            CashTaxTiming as _CTT,
            ShlInterestDeductibilityMode as _SIM,
            TaxLossUtilisationGate as _TLG,
            TaxPolicy as _TP,
        )
        _probe = _TP(
            policy_id="probe", policy_version="1.0.0",
            corporate_rate=0.18, periods_per_tax_year=2, loss_carryforward_years=5,
            atad_enabled=False, atad_ebitda_limit=0.3, atad_de_minimis_threshold_keur_annual=3000.0,
            cash_tax_timing=_CTT.TAX_YEAR_LAST_PERIOD, cash_tax_payment_lag_periods=0,
            shl_interest_tax_treatment_enabled=True,
            shl_interest_deductibility=_SIM.FULLY_NON_DEDUCTIBLE,
            shl_interest_deductible_pct=0.0,
            loss_utilisation_gate=_TLG.TAXABLE_INCOME_POSITIVE,
        )
        _bases = build_tax_year_bases(periods, _build_interest_map(period_interest), _build_adj_map(()), _probe)
        _first_year = _bases[0].tax_year

        opening = (OpeningTaxLossVintageInput(origin_tax_year=_first_year - 1, amount_keur=OPENING_LOSS),)

        proj_base = create_default_oborovo()

        def _contract_via_adapter(gate: InputGate):
            proj = replace(proj_base, tax=replace(proj_base.tax, tax_loss_utilisation_gate=gate))
            # complete_financing_interest_will_be_injected=True so shl_interest_tax_treatment_enabled
            # is True in TaxPolicy → FULLY_NON_DEDUCTIBLE mode → shl_non_deductible = full SHL injection
            contract = build_tax_contract_from_project_inputs(
                proj, complete_financing_interest_will_be_injected=True
            )
            # Inject discriminating interest and opening loss (adapter returns empty stubs)
            return replace(
                contract,
                period_interest=period_interest,
                opening_loss_vintages=opening,
            )

        contract_ti = _contract_via_adapter(InputGate.TAXABLE_INCOME_POSITIVE)
        contract_ebt = _contract_via_adapter(InputGate.EBT_POSITIVE)

        # Confirm adapter forwarded gate correctly before running engine
        from financial_engine.policies.tax import TaxLossUtilisationGate as EngineGate
        assert contract_ti.policy.loss_utilisation_gate == EngineGate.TAXABLE_INCOME_POSITIVE
        assert contract_ebt.policy.loss_utilisation_gate == EngineGate.EBT_POSITIVE

        res_ti = calculate_tax(periods, contract_ti)
        res_ebt = calculate_tax(periods, contract_ebt)

        loss_used_ti = sum(r.loss_used_keur for r in res_ti.annual_results)
        loss_used_ebt = sum(r.loss_used_keur for r in res_ebt.annual_results)
        cit_ti = sum(r.current_tax_liability_keur for r in res_ti.annual_results)
        cit_ebt = sum(r.current_tax_liability_keur for r in res_ebt.annual_results)

        assert loss_used_ti > loss_used_ebt, (
            "Adapter round-trip: TAXABLE_INCOME_POSITIVE should use more loss than EBT_POSITIVE. "
            f"TI loss_used={loss_used_ti:.2f}, EBT loss_used={loss_used_ebt:.2f}"
        )
        assert cit_ebt > cit_ti, (
            "Adapter round-trip: EBT_POSITIVE should produce higher CIT than TAXABLE_INCOME_POSITIVE. "
            f"EBT CIT={cit_ebt:.4f} kEUR, TI CIT={cit_ti:.4f} kEUR"
        )
