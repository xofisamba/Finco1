"""
KUPI K0-K3 Causal Grid — Post-Fix3 diagnostic.

DIAGNOSTIC ONLY. Not production logic. All results are engine-derived.
No source Senior or SHL injected as production inputs.

Project: KUPI Wind (144 MW, Bosnia & Herzegovina)
  FC:              2028-06-30
  Construction:    24 months (4 semiannual periods)
  COD:             2030-06-30
  Operating life:  30 years, semiannual
  P50:             509.04 GWh  (3535.0 operating hours)
  P90:             440.352 GWh (3058.0 operating hours)
  PPA:             63 EUR/MWh, 12 years, 2% indexation, 100% offtake
  Balancing:       5 EUR/MWh (P0/K0-K3); 0 EUR/MWh (D0 — bank sizing diagnostic)
  SHL rate:        8%, shl_construction_day_count_fraction=2.0

Source anchors (comparison, NOT production targets, NOT injected as inputs):
  Source Senior:            147,150.442 kEUR
  Source SHL cash principal: 68,152.996 kEUR
  Source PIK:                11,340.658 kEUR
  Source Opening SHL:        79,493.654 kEUR
  Total Uses:               215,803.438 kEUR

Tax audit for KUPI (Bosnia & Herzegovina):
  STATUS: SOURCE_TAX_MECHANIC_UNRESOLVED
  - BA corporate rate: 10% (statutory — confirmed by BA CIT law)
  - SHL interest deductibility mode: UNKNOWN (no KUPI-specific source proof)
  - Thin-cap / ATAD applicability: UNKNOWN for KUPI
  - Depreciation rates and tax base: UNKNOWN (no proven BA tax asset register)
  - Loss carry-forward duration: UNKNOWN (BA statutory is 5 years, unverified for source)
  - Generic BA tax (BA_GENERIC_MVP_V1) profile exists but carries PROVENANCE_GENERIC_MVP_POLICY
    marker — not source-proven for this project.
  K1 and K3 are therefore run with GENERIC BA tax (same as K0/K2) and labeled
  SOURCE_TAX_MECHANIC_UNRESOLVED until KUPI-specific tax mechanics are proven.

Factorial design:
  P0 — CURRENT_PRODUCTION_GENERIC:
       balancing=5, generic tax, ALL_AT_FC + COMPOUND_PERIODIC (post-Fix3 default)
  D0 — BANK_BALANCING_OMISSION_DIAGNOSTIC:
       balancing=0 for bank sizing, generic tax, ALL_AT_FC + COMPOUND_PERIODIC
  K0 — control: D0 + GENERIC tax + PRO_RATA + SIMPLE
  K1 — tax effect: D0 + SOURCE-COMPATIBLE tax + PRO_RATA + SIMPLE
       (SOURCE_TAX_MECHANIC_UNRESOLVED → same as generic; labeled for audit)
  K2 — SHL effect: D0 + GENERIC tax + ALL_AT_FC + COMPOUND_PERIODIC
  K3 — combined: D0 + SOURCE-COMPATIBLE tax + ALL_AT_FC + COMPOUND_PERIODIC
       (SOURCE_TAX_MECHANIC_UNRESOLVED → same as generic; labeled for audit)

Causal decompositions (Senior):
  TAX_MAIN_EFFECT    = Senior(K1) - Senior(K0)
  SHL_MAIN_EFFECT    = Senior(K2) - Senior(K0)
  COMBINED_EFFECT    = Senior(K3) - Senior(K0)
  INTERACTION_EFFECT = Senior(K3) - Senior(K1) - Senior(K2) + Senior(K0)
  K3_RESIDUAL        = 147,150.442 - Senior(K3)   [source anchor comparison only]
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from typing import NamedTuple

from domain.inputs import (
    AssetClass,
    CapexItem,
    CapexStructure,
    EquityIRRMethod,
    FinancingParams,
    OpexItem,
    PeriodFrequency,
    ProjectInfo,
    ProjectInputs,
    RevenueParams,
    TaxParams,
    TechnicalParams,
    DebtSizingMethod,
)
from finco_core.inputs._models import (
    DebtSizingMode,
    GearingBasisMode,
    ShlConstructionInterestMethod,
    SponsorFundingMode,
    SponsorFundingTimingPolicy,
    ShlInterestDeductibilityMode,
)
from finco_core.inputs.senior_rate_schedule import (
    SeniorDayCountConvention,
    SeniorDebtInterestConfig,
    SeniorRateMode,
    SeniorRateSchedule,
)
from financial_engine.financing import run_project_financing_model
from financial_engine.financing.contracts import ProjectFinancingResult


# ---------------------------------------------------------------------------
# SOURCE ANCHOR CONSTANTS — comparison only, NEVER injected as production inputs
# ---------------------------------------------------------------------------
SOURCE_SENIOR_KEUR = 147_150.442           # comparison anchor
SOURCE_SHL_PRINCIPAL_KEUR = 68_152.996     # comparison anchor
SOURCE_PIK_KEUR = 11_340.658               # comparison anchor
SOURCE_OPENING_SHL_KEUR = 79_493.654       # comparison anchor
SOURCE_TOTAL_USES_KEUR = 215_803.438       # comparison anchor

# BA corporate tax rate (statutory)
BA_CORPORATE_RATE = 0.10


# ---------------------------------------------------------------------------
# KUPI PROJECT INPUT FACTORY
# ---------------------------------------------------------------------------

def _kupi_senior_interest_config(tenor_years: int = 15) -> SeniorDebtInterestConfig:
    """Generic clean senior rate for KUPI — 3% base + 250bps = 5.5% all-in."""
    annual_all_in_rate = 0.03 + 250 / 10_000  # 5.5%
    return SeniorDebtInterestConfig(
        enabled=True,
        rate_schedule=SeniorRateSchedule(
            mode=SeniorRateMode.EXPLICIT_ALL_IN_SCHEDULE,
            explicit_all_in_rates=(annual_all_in_rate,) * (tenor_years * 2),
        ),
        day_count=SeniorDayCountConvention.ACT_360,
    )


def build_kupi_project_inputs(
    *,
    shl_construction_interest_method: ShlConstructionInterestMethod = ShlConstructionInterestMethod.COMPOUND_PERIODIC,
    sponsor_funding_timing_policy: SponsorFundingTimingPolicy = SponsorFundingTimingPolicy.ALL_AT_FC,
    bank_balancing_cost_eur_mwh: float = 5.0,
    source_tax_mechanic_override: bool = False,  # K1/K3 flag — currently UNRESOLVED, no runtime change
) -> ProjectInputs:
    """Build KUPI Wind project inputs (Bosnia & Herzegovina, 144 MW).

    All Senior and SHL values are engine-derived via the fixed-point solver.
    Source Senior/SHL anchors are NOT injected. See module docstring for source comparison values.

    Parameters
    ----------
    shl_construction_interest_method:
        SIMPLE for K0/K1; COMPOUND_PERIODIC for K2/K3/P0/D0.
    sponsor_funding_timing_policy:
        PRO_RATA_CONSTRUCTION for K0/K1; ALL_AT_FC for K2/K3/P0/D0.
    bank_balancing_cost_eur_mwh:
        5.0 for P0/K0-K3 (actual project economics).
        0.0 for D0 (KUPI_SOURCE_BANK_BALANCING_OMISSION_DIAGNOSTIC).
    source_tax_mechanic_override:
        True for K1/K3. Currently SOURCE_TAX_MECHANIC_UNRESOLVED — no runtime
        change is applied. Tax remains generic BA until KUPI-specific proof exists.
    """
    z = CapexItem(name="Unused", amount_keur=0.0, asset_class=AssetClass.CIVIL_GRID)

    # KUPI capex structure — 144 MW wind, Bosnia.
    # Hard capex estimated from project scale (~1,500 EUR/kW for BA wind).
    # Total Uses is engine-derived from capex + DSRA; no forced target.
    turbines = CapexItem(
        name="Wind Turbines",
        amount_keur=160_000.0,
        y0_share=0.5,
        spending_profile=(0.25, 0.25),   # 4 semiannual construction periods
        asset_class=AssetClass.WIND_TURBINES,
    )
    civil = CapexItem(
        name="Civil Works",
        amount_keur=25_000.0,
        y0_share=0.3,
        spending_profile=(0.35, 0.35),
        asset_class=AssetClass.CIVIL_GRID,
    )
    grid = CapexItem(
        name="Grid Connection",
        amount_keur=10_000.0,
        y0_share=0.3,
        spending_profile=(0.35, 0.35),
        asset_class=AssetClass.CIVIL_GRID,
    )
    soft = CapexItem(
        name="Soft Costs",
        amount_keur=8_000.0,
        y0_share=1.0,
        asset_class=AssetClass.SOFT_COSTS,
    )

    capex = CapexStructure(
        epc_contract=turbines,
        production_units=z,
        epc_other=civil,
        grid_connection=grid,
        ops_prep=z,
        insurances=z,
        lease_tax=z,
        construction_mgmt_a=z,
        commissioning=z,
        audit_legal=soft,
        construction_mgmt_b=z,
        contingencies=z,
        taxes=z,
        project_acquisition=z,
        project_rights=z,
        idc_keur=0.0,
        bank_fees_keur=0.0,
    )

    opex = [
        OpexItem(name="Technical Management",  y1_amount_keur=800.0,  annual_inflation=0.02),
        OpexItem(name="Insurance",             y1_amount_keur=500.0,  annual_inflation=0.02),
        OpexItem(name="Maintenance",           y1_amount_keur=600.0,  annual_inflation=0.02),
        OpexItem(name="Lease & Tax",           y1_amount_keur=300.0,  annual_inflation=0.02),
    ]

    info = ProjectInfo(
        name="KUPI Wind — K0-K3 Diagnostic",
        company="KUPI DiagCo",
        code="KUPI-DIAG-001",
        country_iso="BA",
        financial_close=date(2028, 6, 30),
        construction_months=24,
        cod_date=date(2030, 6, 30),
        horizon_years=30,
        period_frequency=PeriodFrequency.SEMESTRIAL,
    )

    # P50: 509.04 GWh = 509,040 MWh / 144 MW = 3535.0 hrs
    # P90: 440.352 GWh = 440,352 MWh / 144 MW = 3058.0 hrs
    technical = TechnicalParams(
        capacity_mw=144.0,
        yield_scenario="P_50",
        operating_hours_p50=3535.0,
        operating_hours_p90_10y=3058.0,
        pv_degradation=0.0,
        bess_enabled=False,
    )

    # PPA: 63 EUR/MWh, 12 years, 2% indexation, 100% of energy sold under PPA.
    # Balancing deduction: bank_balancing_cost_eur_mwh (5 for P0/K-cases, 0 for D0).
    # No market curve needed for this diagnostic — all energy covered by PPA or merchant.
    # Use a flat merchant curve at PPA price for post-PPA periods.
    merchant_curve = tuple(63.0 * (1.02 ** i) for i in range(35))

    revenue = RevenueParams(
        ppa_base_tariff=63.0,
        ppa_term_years=12,
        ppa_index=0.02,
        market_scenario="Central",
        market_prices_curve=merchant_curve,
        market_inflation=0.02,
        balancing_cost_wind_eur_mwh=bank_balancing_cost_eur_mwh,
        co2_enabled=False,
        co2_price_eur=0.0,
        balancing_cost_pv=0.0,
    )

    # Tax: generic BA.
    # SOURCE_TAX_MECHANIC_UNRESOLVED — KUPI-specific tax mechanics not yet proven.
    # K1/K3 use source_tax_mechanic_override=True as a label flag only;
    # runtime tax remains generic until proof exists.
    tax = TaxParams(
        corporate_rate=BA_CORPORATE_RATE,  # BA statutory 10%
        loss_carryforward_years=5,
        loss_carryforward_cap=1.0,
        atad_ebitda_limit=0.30,
        atad_min_interest_keur=3000.0,
        clean_cash_tax_timing_enabled=True,
        shl_interest_deductibility=ShlInterestDeductibilityMode.FULLY_DEDUCTIBLE,
        # SOURCE_TAX_MECHANIC_UNRESOLVED: no KUPI-specific deductibility proof.
        # Remaining generic until K1/K3 source mechanic is proven.
    )

    # Gearing: use 0.80 with target_dscr=2.0 to ensure DSCR is the binding constraint.
    # Gearing cap (0.80 × 203,000 = 162,400) exceeds DSCR capacity (~128,785) at dscr=2.0,
    # so Senior is DSCR-determined. This reveals the causal SHL/tax effects on Senior.
    # Note: source implied gearing ≈ 68.18% (147,150 / 215,803); exact capex calibration
    # is out of scope for this diagnostic grid.
    gearing_ratio = 0.80  # generous cap; DSCR is binding at target_dscr=2.0

    financing = FinancingParams(
        share_capital_keur=500.0,
        shl_amount_keur=68_152.996,   # legacy field for compatibility; G2A derives principal
        shl_rate=0.08,
        gearing_ratio=gearing_ratio,
        senior_tenor_years=15,
        base_rate=0.03,
        margin_bps=250,
        floating_share=0.3,
        fixed_share=0.7,
        hedge_coverage=0.8,
        target_dscr=2.0,    # Elevated to ensure DSCR is binding; reveals SHL/tax causal effects
        lockup_dscr=1.10,
        dsra_months=6,
        equity_irr_method=EquityIRRMethod.EQUITY_ONLY.value,
        debt_sizing_method=DebtSizingMethod.DSCR_SCULPT.value,
        debt_sizing_mode=DebtSizingMode.FLAT_DSCR_SCULPTED,
        sponsor_funding_mode=SponsorFundingMode.SHARE_CAPITAL_THEN_SHL,
        gearing_basis_mode=GearingBasisMode.TOTAL_PROJECT_USES,
        senior_debt_interest_config=_kupi_senior_interest_config(tenor_years=15),
        clean_shl_principal_keur=68_152.996,   # legacy compat; G2A fixed-point derives actual
        clean_shl_repayment_method="bullet",
        shl_day_count_convention="PERIOD_AXIS_ACTUAL_YEAR",
        # Construction SHL: 24-month construction, semiannual = DCF=2.0 (2 annual periods)
        shl_construction_day_count_fraction=2.0,
        shl_construction_interest_method=shl_construction_interest_method,
        sponsor_funding_timing_policy=sponsor_funding_timing_policy,
        # PRO_RATA with multi-period construction requires explicit uses vector.
        # 2 construction periods: 6 months (P0) + 18 months (P1) = 24 months.
        # Equal split (diagnostic approximation); total must match total_project_uses_keur.
        # ALL_AT_FC cases: field is accepted but not used by the timing waterfall.
        construction_period_uses_keur=(101_500.0, 101_500.0),
    )

    return ProjectInputs(
        info=info,
        technical=technical,
        capex=capex,
        opex=tuple(opex),
        revenue=revenue,
        financing=financing,
        tax=tax,
    )


# ---------------------------------------------------------------------------
# RUN FUNCTIONS — P0, D0, K0-K3
# ---------------------------------------------------------------------------

def run_p0_current_generic() -> ProjectFinancingResult:
    """P0 — CURRENT_PRODUCTION_GENERIC.

    Post-Fix3 defaults: ALL_AT_FC + COMPOUND_PERIODIC, balancing=5 EUR/MWh.
    Engine-derived Senior and SHL.
    """
    return run_project_financing_model(
        build_kupi_project_inputs(
            shl_construction_interest_method=ShlConstructionInterestMethod.COMPOUND_PERIODIC,
            sponsor_funding_timing_policy=SponsorFundingTimingPolicy.ALL_AT_FC,
            bank_balancing_cost_eur_mwh=5.0,
        ),
        source_id="KUPI_P0_CURRENT_GENERIC",
    )


def run_d0_bank_balancing_diagnostic() -> ProjectFinancingResult:
    """D0 — BANK_BALANCING_OMISSION_DIAGNOSTIC.

    # KUPI_SOURCE_BANK_BALANCING_OMISSION_DIAGNOSTIC
    Diagnostic override: balancing_cost=0 EUR/MWh for bank CFADS sizing.
    This is NOT production logic. It tests whether the source Senior can be
    explained by an omission of the 5 EUR/MWh balancing deduction in bank sizing.
    Post-Fix3 defaults otherwise: ALL_AT_FC + COMPOUND_PERIODIC.
    """
    # KUPI_SOURCE_BANK_BALANCING_OMISSION_DIAGNOSTIC
    return run_project_financing_model(
        build_kupi_project_inputs(
            shl_construction_interest_method=ShlConstructionInterestMethod.COMPOUND_PERIODIC,
            sponsor_funding_timing_policy=SponsorFundingTimingPolicy.ALL_AT_FC,
            bank_balancing_cost_eur_mwh=0.0,  # DIAGNOSTIC: omit balancing for bank CFADS
        ),
        source_id="KUPI_D0_BANK_BALANCING_OMISSION_DIAGNOSTIC",
    )


def run_k0_control() -> ProjectFinancingResult:
    """K0 — Control: D0 bank revenue + GENERIC tax + PRO_RATA + SIMPLE."""
    return run_project_financing_model(
        build_kupi_project_inputs(
            shl_construction_interest_method=ShlConstructionInterestMethod.SIMPLE,
            sponsor_funding_timing_policy=SponsorFundingTimingPolicy.PRO_RATA_CONSTRUCTION,
            bank_balancing_cost_eur_mwh=0.0,  # D0 bank revenue treatment
        ),
        source_id="KUPI_K0_CONTROL",
    )


def run_k1_source_tax() -> ProjectFinancingResult:
    """K1 — Tax effect: D0 + SOURCE-COMPATIBLE tax + PRO_RATA + SIMPLE.

    SOURCE_TAX_MECHANIC_UNRESOLVED: KUPI-specific tax mechanics not proven.
    K1 runs with generic BA tax (same as K0). When KUPI tax is proven, update
    build_kupi_project_inputs with source_tax_mechanic_override=True to apply
    the proven mechanics. TAX_MAIN_EFFECT = Senior(K1) - Senior(K0) will be 0
    until tax mechanics are resolved.
    """
    return run_project_financing_model(
        build_kupi_project_inputs(
            shl_construction_interest_method=ShlConstructionInterestMethod.SIMPLE,
            sponsor_funding_timing_policy=SponsorFundingTimingPolicy.PRO_RATA_CONSTRUCTION,
            bank_balancing_cost_eur_mwh=0.0,  # D0 bank revenue treatment
            source_tax_mechanic_override=True,  # SOURCE_TAX_MECHANIC_UNRESOLVED — label only
        ),
        source_id="KUPI_K1_SOURCE_TAX_UNRESOLVED",
    )


def run_k2_source_shl() -> ProjectFinancingResult:
    """K2 — SHL effect: D0 + GENERIC tax + ALL_AT_FC + COMPOUND_PERIODIC."""
    return run_project_financing_model(
        build_kupi_project_inputs(
            shl_construction_interest_method=ShlConstructionInterestMethod.COMPOUND_PERIODIC,
            sponsor_funding_timing_policy=SponsorFundingTimingPolicy.ALL_AT_FC,
            bank_balancing_cost_eur_mwh=0.0,  # D0 bank revenue treatment
        ),
        source_id="KUPI_K2_SOURCE_SHL",
    )


def run_k3_combined() -> ProjectFinancingResult:
    """K3 — Combined: D0 + SOURCE-COMPATIBLE tax + ALL_AT_FC + COMPOUND_PERIODIC.

    SOURCE_TAX_MECHANIC_UNRESOLVED: K3 = K2 in practice until tax is proven.
    """
    return run_project_financing_model(
        build_kupi_project_inputs(
            shl_construction_interest_method=ShlConstructionInterestMethod.COMPOUND_PERIODIC,
            sponsor_funding_timing_policy=SponsorFundingTimingPolicy.ALL_AT_FC,
            bank_balancing_cost_eur_mwh=0.0,  # D0 bank revenue treatment
            source_tax_mechanic_override=True,  # SOURCE_TAX_MECHANIC_UNRESOLVED — label only
        ),
        source_id="KUPI_K3_COMBINED",
    )


# ---------------------------------------------------------------------------
# CAUSAL DECOMPOSITION
# ---------------------------------------------------------------------------

class KupiCausalGrid(NamedTuple):
    """Results and causal decompositions for the KUPI K0-K3 factorial."""
    p0: ProjectFinancingResult
    d0: ProjectFinancingResult
    k0: ProjectFinancingResult
    k1: ProjectFinancingResult
    k2: ProjectFinancingResult
    k3: ProjectFinancingResult

    @property
    def senior_p0(self) -> float:
        return self.p0.final_senior_commitment_keur

    @property
    def senior_d0(self) -> float:
        return self.d0.final_senior_commitment_keur

    @property
    def senior_k0(self) -> float:
        return self.k0.final_senior_commitment_keur

    @property
    def senior_k1(self) -> float:
        return self.k1.final_senior_commitment_keur

    @property
    def senior_k2(self) -> float:
        return self.k2.final_senior_commitment_keur

    @property
    def senior_k3(self) -> float:
        return self.k3.final_senior_commitment_keur

    @property
    def delta_d0_vs_p0(self) -> float:
        """D0 - P0: Senior uplift from removing balancing cost for bank sizing."""
        return self.senior_d0 - self.senior_p0

    @property
    def tax_main_effect(self) -> float:
        """K1 - K0: Marginal impact of source-compatible tax (UNRESOLVED → 0)."""
        return self.senior_k1 - self.senior_k0

    @property
    def shl_main_effect(self) -> float:
        """K2 - K0: Marginal impact of ALL_AT_FC + COMPOUND vs PRO_RATA + SIMPLE."""
        return self.senior_k2 - self.senior_k0

    @property
    def combined_effect(self) -> float:
        """K3 - K0: Combined effect of both dimensions."""
        return self.senior_k3 - self.senior_k0

    @property
    def interaction_effect(self) -> float:
        """Interaction: K3 - K1 - K2 + K0."""
        return self.senior_k3 - self.senior_k1 - self.senior_k2 + self.senior_k0

    @property
    def k3_residual_vs_source(self) -> float:
        """Source anchor comparison: 147,150.442 - Senior(K3). NOT a target."""
        return SOURCE_SENIOR_KEUR - self.senior_k3

    def print_report(self) -> None:
        """Print the causal grid report to stdout."""
        print("\n" + "=" * 70)
        print("KUPI K0-K3 CAUSAL GRID — Post-Fix3 Diagnostic")
        print("=" * 70)
        print(f"\n{'Case':<8} {'Senior (kEUR)':>16} {'SHL Cash (kEUR)':>16} {'PIK (kEUR)':>12} {'Opening SHL (kEUR)':>18}")
        print("-" * 74)
        for label, res in [("P0", self.p0), ("D0", self.d0), ("K0", self.k0),
                            ("K1", self.k1), ("K2", self.k2), ("K3", self.k3)]:
            print(f"{label:<8} {res.final_senior_commitment_keur:>16.3f} "
                  f"{res.derived_shl_cash_principal_keur:>16.3f} "
                  f"{res.shl_construction_pik_keur:>12.3f} "
                  f"{res.opening_operating_shl_balance_keur:>18.3f}")
        print("-" * 74)
        print(f"\n{'SOURCE':8} {SOURCE_SENIOR_KEUR:>16.3f} {SOURCE_SHL_PRINCIPAL_KEUR:>16.3f} "
              f"{SOURCE_PIK_KEUR:>12.3f} {SOURCE_OPENING_SHL_KEUR:>18.3f}")
        print("\n--- Causal Decomposition (Senior, kEUR) ---")
        print(f"  D0 - P0  (balancing omission diagnostic): {self.delta_d0_vs_p0:+.3f}")
        print(f"  TAX_MAIN_EFFECT    K1-K0:                 {self.tax_main_effect:+.3f}  [SOURCE_TAX_MECHANIC_UNRESOLVED]")
        print(f"  SHL_MAIN_EFFECT    K2-K0:                 {self.shl_main_effect:+.3f}")
        print(f"  COMBINED_EFFECT    K3-K0:                 {self.combined_effect:+.3f}")
        print(f"  INTERACTION_EFFECT K3-K1-K2+K0:          {self.interaction_effect:+.3f}")
        print(f"  K3_RESIDUAL vs source anchor:             {self.k3_residual_vs_source:+.3f}")
        print("=" * 70)


def run_full_grid() -> KupiCausalGrid:
    """Run all 6 cases and return the causal grid."""
    p0 = run_p0_current_generic()
    d0 = run_d0_bank_balancing_diagnostic()
    k0 = run_k0_control()
    k1 = run_k1_source_tax()
    k2 = run_k2_source_shl()
    k3 = run_k3_combined()
    return KupiCausalGrid(p0=p0, d0=d0, k0=k0, k1=k1, k2=k2, k3=k3)


if __name__ == "__main__":
    grid = run_full_grid()
    grid.print_report()
