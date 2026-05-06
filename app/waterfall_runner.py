"""WaterfallRunner — orchestrator for clean waterfall invocation.

S2-2: Encapsulates all waterfall computation logic.
UI pages call WaterfallRunner.run(), not run_waterfall() directly.
This makes testing easier and keeps UI layer thin.

FincoGPT update: WaterfallRunner now calls the uncached calculation core.
Streamlit caching remains in app/cache.py only.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Optional

from app.waterfall_core import run_waterfall_v3_core
from domain.inputs import EquityIRRMethod, DebtSizingMethod, SHLRepaymentMethod

if TYPE_CHECKING:
    from app.depreciation_engine import DepreciationSchedule


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
    fixed_ds_keur: Optional[float] = None     # Fixed DS per period (fixed debt service)

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

    # Advanced OPEX line items (None = use legacy OpexItem path)
    advanced_opex_line_items: Optional[tuple] = None

    # Advanced CAPEX line items — total computed from CapexLineItems tuple
    advanced_capex_line_items: Optional[tuple] = None

    # Advanced CAPEX depreciation schedule — from app.depreciation_engine
    # When provided, uses per-asset-class depreciable lives instead of legacy
    # CapexItem path. Must be a DepreciationSchedule object.
    advanced_capex_depreciation_schedule: "DepreciationSchedule | None" = None

    def cache_key(self) -> str:
        """Generate cache key from config parameters."""
        return f"wf_{self.rate_per_period:.6f}_{self.tenor_periods}_{self.target_dscr:.3f}_{self.shl_amount_keur:.0f}"

    @classmethod
    def from_inputs(cls, inputs: "ProjectInputs", engine: "PeriodEngine") -> "WaterfallRunConfig":
        """Build a config derived from project inputs and period engine.

        Maps financing, tax, SHL, and equity params from ProjectInputs into
        a WaterfallRunConfig so the UI need not hardcode defaults.
        """
        # Count operating periods
        periods = list(engine.periods())
        op_periods = [p for p in periods if p.is_operation]
        tenor_periods = inputs.financing.senior_tenor_years * 2
        if tenor_periods == 0:
            tenor_periods = len(op_periods) if op_periods else len(periods)

        # Determine all-in rate per period
        fin = inputs.financing
        if hasattr(fin, "all_in_rate") and fin.all_in_rate:
            rate_per_period = fin.all_in_rate / 2
        elif hasattr(fin, "base_rate") and hasattr(fin, "margin_bps"):
            rate_per_period = (fin.base_rate + fin.margin_bps / 10000.0) / 2
        else:
            rate_per_period = cls.rate_per_period  # use default

        # Map SHL repayment method — FinancingParams may use str or enum
        shl_repayment = fin.shl_repayment_method
        if isinstance(shl_repayment, str):
            from domain.inputs import SHLRepaymentMethod
            shl_repayment = SHLRepaymentMethod(shl_repayment)

        # Map equity_irr_method — FinancingParams stores as str, config expects enum
        from domain.inputs import EquityIRRMethod
        eq_irr = fin.equity_irr_method
        if isinstance(eq_irr, str):
            eq_irr = EquityIRRMethod(eq_irr)

        # Map debt_sizing_method — FinancingParams stores as str, config expects enum
        from domain.inputs import DebtSizingMethod
        ds_method = fin.debt_sizing_method
        if isinstance(ds_method, str):
            ds_method = DebtSizingMethod(ds_method)

        return cls(
            rate_per_period=rate_per_period,
            tenor_periods=tenor_periods,
            target_dscr=fin.target_dscr,
            lockup_dscr=fin.lockup_dscr,
            tax_rate=inputs.tax.corporate_rate,
            dsra_months=fin.dsra_months,
            shl_amount_keur=fin.shl_amount_keur,
            shl_rate=fin.shl_rate,
            shl_idc_keur=fin.shl_idc_keur,
            shl_repayment_method=shl_repayment,
            shl_tenor_years=fin.shl_tenor_years,
            equity_irr_method=eq_irr,
            share_capital_keur=fin.share_capital_keur,
            sculpt_capex_keur=inputs.capex.sculpt_capex_keur,
            debt_sizing_method=ds_method,
            fixed_debt_keur=fin.fixed_debt_keur,
            dscr_schedule=fin.dscr_schedule,
        )


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

        # S4-1: Use sculpt_capex_keur from inputs.capex when config does not override it.
        sculpt_capex = (
            self.inputs.capex.sculpt_capex_keur
            if config.sculpt_capex_keur == 0.0
            else config.sculpt_capex_keur
        )

        # FincoGPT: call the uncached calculation core. app/cache.py is the only
        # module that should wrap this with Streamlit @st.cache_data.
        return run_waterfall_v3_core(
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
            sculpt_capex_keur=sculpt_capex,
            debt_sizing_method=config.debt_sizing_method.value,
            dscr_schedule=config.dscr_schedule,
            advanced_opex_line_items=config.advanced_opex_line_items,
            advanced_capex_line_items=config.advanced_capex_line_items,
            advanced_capex_depreciation_schedule=config.advanced_capex_depreciation_schedule,
        )

    def run_with_defaults(self) -> object:
        """DEPRECATED: Use WaterfallRunConfig.from_inputs() + run(config) instead.

        This method uses hardcoded defaults rather than project-specific financing
        assumptions. It exists only for backward compatibility with legacy calls.
        """
        import warnings
        warnings.warn(
            "WaterfallRunner.run_with_defaults() is deprecated. "
            "Use WaterfallRunConfig.from_inputs(inputs, engine) + runner.run(config) instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.run(WaterfallRunConfig())

    def invalidate_cache(self) -> None:
        """Invalidate all Streamlit cached computations for this project.

        Imported lazily so this runner remains importable in headless contexts.
        """
        from app.cache import clear_all_caches

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
            if not hasattr(base_config, param_name):
                raise ValueError(f"Unknown sensitivity parameter: {param_name}")

            config = replace(base_config, **{param_name: value})
            runner = WaterfallRunner(self.inputs, self.engine)
            result = runner.run(config)
            results.append(result)

        return results


__all__ = [
    "WaterfallRunConfig",
    "WaterfallRunner",
    "ScenarioRunner",
]
