"""WaterfallRunner — orchestrator for clean waterfall invocation.

S2-2: Encapsulates all waterfall computation logic.
UI pages call WaterfallRunner.run(), not run_waterfall() directly.
This makes testing easier and keeps UI layer thin.
"""
from dataclasses import dataclass, field
from typing import Optional

from app.cache import cached_run_waterfall_v3, clear_all_caches
from domain.inputs import EquityIRRMethod, DebtSizingMethod, SHLRepaymentMethod


@dataclass(frozen=True)
class WaterfallRunConfig:
    """Configuration for a waterfall run.

    All parameters needed to run the waterfall are encapsulated here.
    This makes it easy to pass configuration around and to cache results.
    """
    # Rate and tenor
    rate_per_period: float = 0.02825        # Semi-annual rate (5.65% / 2)
    tenor_periods: int = 28                 # 14 years × 2 periods

    # DSCR settings
    target_dscr: float = 1.15              # Target DSCR for sculpting
    lockup_dscr: float = 1.10              # Lockup threshold

    # Tax
    tax_rate: float = 0.10                 # Corporate tax rate

    # DSRA
    dsra_months: int = 6                   # DSRA reserve months

    # SHL (Subordinated Hybrid Loan)
    shl_amount_keur: float = 0.0
    shl_rate: float = 0.0
    shl_idc_keur: float = 0.0
    shl_repayment_method: SHLRepaymentMethod = SHLRepaymentMethod.BULLET
    shl_tenor_years: int = 0               # 0 = bullet at senior maturity
    shl_wht_rate: float = 0.0              # WHT on SHL interest

    # Returns
    discount_rate_project: float = 0.0641
    discount_rate_equity: float = 0.0965

    # Debt overrides
    fixed_debt_keur: Optional[float] = None   # Override sculpted debt
    fixed_ds_keur: Optional[float] = None     # Fixed DS per period (TUHO)

    # Rate schedule
    rate_schedule: Optional[list[float]] = None  # Per-period Euribor curve

    # Equity IRR method
    equity_irr_method: EquityIRRMethod = EquityIRRMethod.EQUITY_ONLY
    share_capital_keur: float = 0.0          # Only for "combined" method
    sculpt_capex_keur: float = 0.0            # CAPEX for equity base

    # Debt sizing
    debt_sizing_method: DebtSizingMethod = DebtSizingMethod.DSCR_SCULPT

    # Per-period DSCR targets (dual-DSCR sculpting)
    dscr_schedule: Optional[list[float]] = None

    def cache_key(self) -> str:
        """Generate cache key from config parameters."""
        return f"wf_{self.rate_per_period:.6f}_{self.tenor_periods}_{self.target_dscr:.3f}_{self.shl_amount_keur:.0f}"


@dataclass
class WaterfallRunner:
    """Orchestrator for waterfall computation.

    Usage:
        runner = WaterfallRunner(inputs, engine)
        config = WaterfallRunConfig(
            target_dscr=1.15,
            lockup_dscr=1.10,
            shl_amount_keur=29_135,
            shl_rate=0.03965,
            shl_repayment_method=SHLRepaymentMethod.PIK_THEN_SWEEP,
        )
        result = runner.run(config)
    """
    inputs: object  # ProjectInputs
    engine: object  # PeriodEngine

    def __post_init__(self):
        # Inputs validation
        if not hasattr(self.inputs, 'capex'):
            raise ValueError("inputs must have 'capex' attribute")

    def run(self, config: Optional[WaterfallRunConfig] = None) -> object:
        """Run waterfall with given configuration.

        Args:
            config: WaterfallRunConfig. If None, uses defaults.

        Returns:
            WaterfallResult from run_waterfall
        """
        if config is None:
            config = WaterfallRunConfig()

        # Use cached waterfall computation
        return cached_run_waterfall_v3(
            inputs=self.inputs,
            engine=self.engine,
            rate_per_period=config.rate_per_period,
            tenor_periods=config.tenor_periods,
            target_dscr=config.target_dscr,
            lockup_dscr=config.lockup_dscr,
            tax_rate=config.tax_rate,
            dsra_months=config.dsra_months,
            shl_amount=config.shl_amount_keur,
            shl_rate=config.shl_rate,
            shl_idc_keur=config.shl_idc_keur,
            shl_repayment_method=config.shl_repayment_method.value,
            shl_tenor_years=config.shl_tenor_years,
            shl_wht_rate=config.shl_wht_rate,
            discount_rate_project=config.discount_rate_project,
            discount_rate_equity=config.discount_rate_equity,
            fixed_debt_keur=config.fixed_debt_keur,
            fixed_ds_keur=config.fixed_ds_keur,
            rate_schedule=config.rate_schedule,
            equity_irr_method=config.equity_irr_method.value,
            share_capital_keur=config.share_capital_keur,
            sculpt_capex_keur=config.sculpt_capex_keur,
            debt_sizing_method=config.debt_sizing_method.value,
            dscr_schedule=config.dscr_schedule,
        )

    def run_with_defaults(self) -> object:
        """Run waterfall with default configuration."""
        return self.run(WaterfallRunConfig())

    def invalidate_cache(self) -> None:
        """Invalidate all cached computations for this project."""
        clear_all_caches()


@dataclass
class ScenarioRunner:
    """Runner for multiple scenarios (sensitivity, Monte Carlo, etc.).

    Encapsulates the logic for running multiple waterfall configurations
    and collecting results.
    """
    inputs: object  # ProjectInputs
    engine: object  # PeriodEngine

    def run_sensitivity(
        self,
        base_config: WaterfallRunConfig,
        param_name: str,
        param_values: list[float],
    ) -> list[object]:
        """Run sensitivity analysis over parameter values.

        Args:
            base_config: Base configuration to modify
            param_name: Name of parameter to vary
            param_values: List of values to test

        Returns:
            List of WaterfallResult (one per value)
        """
        results = []
        for value in param_values:
            config = WaterfallRunConfig(
                rate_per_period=base_config.rate_per_period,
                tenor_periods=base_config.tenor_periods,
                target_dscr=base_config.target_dscr,
                lockup_dscr=base_config.lockup_dscr,
                tax_rate=base_config.tax_rate,
                dsra_months=base_config.dsra_months,
                shl_amount_keur=base_config.shl_amount_keur,
                shl_rate=base_config.shl_rate,
                shl_idc_keur=base_config.shl_idc_keur,
                shl_repayment_method=base_config.shl_repayment_method,
                shl_tenor_years=base_config.shl_tenor_years,
                shl_wht_rate=base_config.shl_wht_rate,
                discount_rate_project=base_config.discount_rate_project,
                discount_rate_equity=base_config.discount_rate_equity,
                fixed_debt_keur=base_config.fixed_debt_keur,
                fixed_ds_keur=base_config.fixed_ds_keur,
                rate_schedule=base_config.rate_schedule,
                equity_irr_method=base_config.equity_irr_method,
                share_capital_keur=base_config.share_capital_keur,
                sculpt_capex_keur=base_config.sculpt_capex_keur,
                debt_sizing_method=base_config.debt_sizing_method,
                dscr_schedule=base_config.dscr_schedule,
            )
            # Set the parameter being tested
            if hasattr(config, param_name):
                setattr(config, param_name, value)

            runner = WaterfallRunner(self.inputs, self.engine)
            result = runner.run(config)
            results.append(result)

        return results


__all__ = [
    "WaterfallRunConfig",
    "WaterfallRunner",
    "ScenarioRunner",
]