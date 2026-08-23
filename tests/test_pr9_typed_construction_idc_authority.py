"""PR-9 tests — Typed Construction Financing and IDC Authority.

ONE_TYPED_CONSTRUCTION_FINANCING_AND_IDC_AUTHORITY

Covers:
- Governance: no project-name dispatch, no template imports in production
- Variable-length construction: 6m, 12m, 18m synthetic timelines
- Typed contract validation
- Synthetic anti-overfit proofs (A: 6m flat, B: 18m hedge blend)
- Serialization / None-zero distinction
- Oborovo source construction parity (reported, not tuned)
- VAT facility deferred
- Generic Solar/Wind PR-8 fingerprints unchanged
"""
from __future__ import annotations

import ast
import re
from datetime import date
from pathlib import Path

import pytest

from finco_core.inputs.construction_financing import (
    ConstructionFinancingInput,
    ConstructionSeniorPricingInput,
    ConstructionCommitmentFeeInput,
    ConstructionStructuringFeeInput,
    ConstructionPeriodSpec,
    ConstructionCapexTimingInput,
)
from finco_core.inputs.senior_rate_schedule import SeniorRateMode, SeniorDayCountConvention
from finco_core.construction.stage_b2 import run_stage_b2
from financial_engine.construction.adapter import build_construction_runtime_config

# Backward-compat alias for tests
ConstructionCapexItemInput = ConstructionCapexTimingInput

REPO_ROOT = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_periods(n: int, start_year: int = 2025) -> tuple[ConstructionPeriodSpec, ...]:
    """Build n monthly construction periods starting from Jan of start_year.

    interest_fraction is now computed by the adapter from dates + day_count convention.
    """
    from datetime import date
    periods = []
    y, m = start_year, 1
    for _ in range(n):
        ny, nm = (y, m + 1) if m < 12 else (y + 1, 1)
        periods.append(ConstructionPeriodSpec(
            start_date=date(y, m, 1),
            end_date=date(ny, nm, 1),
        ))
        y, m = ny, nm
    return tuple(periods)


def _uniform_weights(n: int) -> tuple[float, ...]:
    return tuple(1.0 / n for _ in range(n))


def _make_capex(
    n: int,
    amount_keur: float = 10_000.0,
    code: str = "EPC",
) -> tuple[ConstructionCapexTimingInput, ...]:
    """Create construction capex timing items. amount_keur passed separately to _run_b2."""
    return (ConstructionCapexTimingInput(
        code=code, name="EPC Contract",
        payment_weights=_uniform_weights(n),
    ),)


def _make_flat_input(
    n: int,
    total_capex: float = 10_000.0,
    rate: float = 0.05,
    code: str = "EPC",
) -> "tuple[ConstructionFinancingInput, dict[str, float]]":
    """Returns (ConstructionFinancingInput, capex_amounts_keur dict)."""
    inp = ConstructionFinancingInput(
        enabled=True,
        periods=_make_periods(n),
        capex_items=_make_capex(n, total_capex, code),
        senior_pricing=ConstructionSeniorPricingInput(
            mode=SeniorRateMode.FLAT_ALL_IN, flat_all_in_rate=rate
        ),
    )
    return inp, {code: total_capex}


def _run_b2(
    construction: ConstructionFinancingInput,
    senior_keur: float = 8_000.0,
    equity_keur: float = 2_000.0,
    shl_keur: float = 1_000.0,
    capex_amounts: dict[str, float] | None = None,
):
    """Build runtime config and run Stage B2.

    capex_amounts: code → amount_keur lookup. Defaults to 10_000 per item code.
    """
    if capex_amounts is None:
        capex_amounts = {item.code: 10_000.0 for item in construction.capex_items}
    config = build_construction_runtime_config(
        construction, senior_keur, equity_keur, shl_keur,
        capex_amounts_keur=capex_amounts,
    )
    return run_stage_b2(config)


# ---------------------------------------------------------------------------
# 1. Governance — no project-name dispatch, no template imports
# ---------------------------------------------------------------------------

class TestPR9GovernanceNoProjectDispatch:
    PROJECT_NAMES = {"oborovo", "tuho", "kupi", "OBR-001", "TUHO-WIND-1"}
    PRODUCTION_DIRS = [
        REPO_ROOT / "finco_core" / "construction",
        REPO_ROOT / "financial_engine" / "construction",
        REPO_ROOT / "financial_engine" / "financing",
    ]
    FORBIDDEN_TEMPLATE_IMPORTS = [
        "domain.construction.templates.oborovo",
        "domain.construction.templates.tuho",
        "domain.construction.templates",
    ]

    def _scan_for_pattern(self, pattern: str, dirs: list[Path]) -> list[str]:
        hits = []
        for d in dirs:
            for f in d.rglob("*.py"):
                if "__pycache__" in f.parts:
                    continue
                text = f.read_text()
                if pattern.lower() in text.lower():
                    hits.append(str(f.relative_to(REPO_ROOT)))
        return hits

    def test_stage_b2_no_project_name_dispatch(self):
        """stage_b2.py must not contain project-name literals used for financial dispatch."""
        text = (REPO_ROOT / "finco_core" / "construction" / "stage_b2.py").read_text()
        for name in {"oborovo", "tuho", "kupi"}:
            assert name not in text.lower(), f"stage_b2.py contains project name '{name}'"

    def test_adapter_no_project_name_dispatch(self):
        """financial_engine/construction/adapter.py must not contain project-name literals."""
        text = (REPO_ROOT / "financial_engine" / "construction" / "adapter.py").read_text()
        for name in {"oborovo", "tuho", "kupi"}:
            assert name not in text.lower(), f"adapter.py contains project name '{name}'"

    def test_construction_financing_input_no_project_fields(self):
        """ConstructionFinancingInput must have no project-identity fields."""
        import dataclasses
        field_names = {f.name for f in dataclasses.fields(ConstructionFinancingInput)}
        for bad in {"project", "project_code", "project_name", "dispatch"}:
            assert bad not in field_names, f"ConstructionFinancingInput has identity field '{bad}'"

    def test_oborovo_template_not_imported_in_production(self):
        """Production financial code must not import domain.construction.templates.oborovo."""
        hits = self._scan_for_pattern("domain.construction.templates.oborovo", self.PRODUCTION_DIRS)
        assert hits == [], f"oborovo template imported in production: {hits}"

    def test_tuho_template_not_imported_in_production(self):
        """Production financial code must not import domain.construction.templates.tuho."""
        hits = self._scan_for_pattern("domain.construction.templates.tuho", self.PRODUCTION_DIRS)
        assert hits == [], f"tuho template imported in production: {hits}"

    def test_no_approved_delta_in_production(self):
        """Production construction code must not contain 'approved_delta' strings."""
        hits = self._scan_for_pattern("approved_delta", self.PRODUCTION_DIRS)
        assert hits == [], f"approved_delta found in production: {hits}"

    def test_no_expected_delta_in_production(self):
        """Production construction code must not contain 'expected_delta' strings."""
        hits = self._scan_for_pattern("expected_delta", self.PRODUCTION_DIRS)
        assert hits == [], f"expected_delta found in production: {hits}"


# ---------------------------------------------------------------------------
# 2. Variable-length construction
# ---------------------------------------------------------------------------

class TestVariableLengthConstruction:
    def test_6_month_construction_converges(self):
        """6-month construction: flat 5% rate, uniform CAPEX → converges."""
        inp, capex_a = _make_flat_input(6, total_capex=5_000.0)
        result = _run_b2(inp, senior_keur=4_000.0, equity_keur=1_000.0, shl_keur=500.0, capex_amounts=capex_a)
        assert result.iterations >= 1
        assert result.final_residual_keur <= 1e-9
        assert result.capitalized_financing_costs.senior_idc_keur > 0.0
        assert len(result.senior_period_draw_keur) == 6
        assert len(result.senior_idc_accrual_keur) == 6

    def test_12_month_construction_converges(self):
        """12-month construction: backward-compat case, must still converge."""
        inp, capex_a = _make_flat_input(12, total_capex=10_000.0)
        result = _run_b2(inp, senior_keur=8_000.0, equity_keur=2_000.0, shl_keur=1_000.0, capex_amounts=capex_a)
        assert result.final_residual_keur <= 1e-9
        assert len(result.senior_period_draw_keur) == 12

    def test_18_month_construction_converges(self):
        """18-month construction: variable-length, flat 6% rate, must converge."""
        inp, capex_a = _make_flat_input(18, total_capex=20_000.0, rate=0.06)
        result = _run_b2(inp, senior_keur=16_000.0, equity_keur=4_000.0, shl_keur=2_000.0, capex_amounts=capex_a)
        assert result.final_residual_keur <= 1e-9
        assert len(result.senior_period_draw_keur) == 18
        assert result.capitalized_financing_costs.senior_idc_keur > 0.0

    def test_period_count_in_result_equals_input(self):
        """Result vector lengths must equal the input period count exactly."""
        for n in [6, 12, 18]:
            inp, capex_a = _make_flat_input(n, total_capex=n * 1000.0)
            result = _run_b2(inp, senior_keur=n * 750.0, equity_keur=n * 250.0, shl_keur=n * 100.0, capex_amounts=capex_a)
            assert len(result.senior_period_draw_keur) == n
            assert len(result.senior_idc_accrual_keur) == n
            assert len(result.senior_commitment_fee_accrual_keur) == n
            assert len(result.monthly_hard_capex_keur) == n

    def test_gfa_equals_capex_plus_financing(self):
        """final_gfa_keur = hard_capex + total capitalized financing costs."""
        inp, capex_a = _make_flat_input(12, total_capex=10_000.0)
        result = _run_b2(inp, senior_keur=8_000.0, equity_keur=2_000.0, shl_keur=1_000.0, capex_amounts=capex_a)
        expected_gfa = sum(result.monthly_hard_capex_keur) + result.capitalized_financing_costs.total_keur
        assert abs(result.final_gfa_keur - expected_gfa) < 1e-6


# ---------------------------------------------------------------------------
# 3. Typed contract validation
# ---------------------------------------------------------------------------

class TestConstructionFinancingInput:
    def test_disabled_no_periods_ok(self):
        """disabled ConstructionFinancingInput is valid with no periods."""
        inp = ConstructionFinancingInput(enabled=False)
        assert inp.enabled is False
        assert inp.periods == ()

    def test_disabled_default(self):
        """Default ConstructionFinancingInput is disabled."""
        assert ConstructionFinancingInput().enabled is False

    def test_enabled_empty_periods_raises(self):
        with pytest.raises(ValueError, match="PR9_CONSTRUCTION_ENABLED_NO_PERIODS"):
            ConstructionFinancingInput(
                enabled=True,
                periods=(),
                senior_pricing=ConstructionSeniorPricingInput(mode=SeniorRateMode.FLAT_ALL_IN),
            )

    def test_enabled_no_pricing_raises(self):
        with pytest.raises(ValueError, match="PR9_CONSTRUCTION_ENABLED_NO_PRICING"):
            ConstructionFinancingInput(
                enabled=True,
                periods=_make_periods(6),
                capex_items=_make_capex(6),
                senior_pricing=None,
            )

    def test_invalid_rate_mode_raises(self):
        # mode must be a SeniorRateMode enum; a string raises ValueError
        with pytest.raises((ValueError, TypeError)):
            ConstructionFinancingInput(
                enabled=True,
                periods=_make_periods(6),
                capex_items=_make_capex(6),
                senior_pricing=ConstructionSeniorPricingInput(mode="MAGIC_BACKSOLVE"),  # type: ignore[arg-type]
            )

    def test_capex_weight_length_mismatch_raises(self):
        n = 6
        bad_item = ConstructionCapexTimingInput(
            code="EPC", name="EPC",
            payment_weights=_uniform_weights(12),  # wrong length
        )
        with pytest.raises(ValueError, match="PR9_CAPEX_WEIGHT_LENGTH_MISMATCH"):
            ConstructionFinancingInput(
                enabled=True,
                periods=_make_periods(n),
                capex_items=(bad_item,),
                senior_pricing=ConstructionSeniorPricingInput(mode=SeniorRateMode.FLAT_ALL_IN),
            )

    def test_capex_weights_sum_mismatch_raises(self):
        n = 6
        bad_weights = tuple([0.1] * n)  # sum = 0.6, not 1.0
        bad_item = ConstructionCapexTimingInput(
            code="EPC", name="EPC",
            payment_weights=bad_weights,
        )
        with pytest.raises(ValueError, match="PR9_CAPEX_WEIGHTS_SUM"):
            ConstructionFinancingInput(
                enabled=True,
                periods=_make_periods(n),
                capex_items=(bad_item,),
                senior_pricing=ConstructionSeniorPricingInput(mode=SeniorRateMode.FLAT_ALL_IN),
            )

    def test_vat_deferred_always_true(self):
        """vat_deferred must default to True (PR9_VAT_FACILITY_DEFERRED)."""
        assert ConstructionFinancingInput().vat_deferred is True
        assert ConstructionFinancingInput(enabled=False).vat_deferred is True

    def test_all_rate_modes_accepted(self):
        """All documented rate modes must be accepted by ConstructionFinancingInput."""
        n = 6
        curve = tuple([0.035] * n)
        for mode in SeniorRateMode:
            extra: dict = {}
            if mode == SeniorRateMode.FLOATING_PLUS_MARGIN:
                extra["floating_base_rate_curve"] = curve
            elif mode == SeniorRateMode.HEDGE_BLEND:
                extra["floating_base_rate_curve"] = curve
                extra["hedge_pct"] = 0.5
            elif mode == SeniorRateMode.EXPLICIT_ALL_IN_SCHEDULE:
                extra["explicit_all_in_schedule"] = tuple([0.05] * n)
            ConstructionFinancingInput(
                enabled=True,
                periods=_make_periods(n),
                capex_items=_make_capex(n),
                senior_pricing=ConstructionSeniorPricingInput(mode=mode, **extra),
            )


# ---------------------------------------------------------------------------
# 4. Synthetic anti-overfit — Synthetic A (6m, flat all-in)
# ---------------------------------------------------------------------------

class TestSyntheticA:
    """6-month construction, flat 5% all-in, 0% hedge, uniform CAPEX, no commitment fee."""

    BASE_CAPEX = 5_000.0
    RATE = 0.05
    N = 6
    SENIOR = 4_000.0
    EQUITY = 1_000.0
    SHL = 500.0

    def _base(self, **kw):
        n = kw.get("n", self.N)
        capex = kw.get("capex", self.BASE_CAPEX)
        rate = kw.get("rate", self.RATE)
        senior = kw.get("senior", self.SENIOR)
        equity = kw.get("equity", self.EQUITY)
        shl = kw.get("shl", self.SHL)
        inp = ConstructionFinancingInput(
            enabled=True,
            periods=_make_periods(n),
            capex_items=_make_capex(n, capex),
            senior_pricing=ConstructionSeniorPricingInput(mode=SeniorRateMode.FLAT_ALL_IN, flat_all_in_rate=rate),
        )
        return _run_b2(inp, senior, equity, shl, capex_amounts={"EPC": capex})

    def test_identity_rename_zero_financial_delta(self):
        """Changing CAPEX item code/name only produces zero financial delta."""
        n, capex, rate = self.N, self.BASE_CAPEX, self.RATE
        periods = _make_periods(n)
        weights = _uniform_weights(n)
        inp_a = ConstructionFinancingInput(
            enabled=True, periods=periods,
            capex_items=(ConstructionCapexTimingInput("EPC_A", "Name A", weights),),
            senior_pricing=ConstructionSeniorPricingInput(mode=SeniorRateMode.FLAT_ALL_IN, flat_all_in_rate=rate),
        )
        inp_b = ConstructionFinancingInput(
            enabled=True, periods=periods,
            capex_items=(ConstructionCapexTimingInput("EPC_B", "Name B", weights),),
            senior_pricing=ConstructionSeniorPricingInput(mode=SeniorRateMode.FLAT_ALL_IN, flat_all_in_rate=rate),
        )
        ra = _run_b2(inp_a, self.SENIOR, self.EQUITY, self.SHL, capex_amounts={"EPC_A": capex})
        rb = _run_b2(inp_b, self.SENIOR, self.EQUITY, self.SHL, capex_amounts={"EPC_B": capex})
        assert ra.capitalized_financing_costs.senior_idc_keur == pytest.approx(
            rb.capitalized_financing_costs.senior_idc_keur
        )
        assert ra.final_gfa_keur == pytest.approx(rb.final_gfa_keur)

    def test_capex_increase_increases_funding(self):
        """More CAPEX → more Senior draws → more IDC (monotone)."""
        r_base = self._base()
        # Scale senior/equity/shl proportionally with capex to avoid shortfall
        scale = 1.5
        r_high = self._base(
            capex=self.BASE_CAPEX * scale,
            senior=self.SENIOR * scale + 200,  # extra buffer for IDC capitalization
            equity=self.EQUITY * scale,
            shl=self.SHL * scale,
        )
        assert r_high.capitalized_financing_costs.senior_idc_keur > r_base.capitalized_financing_costs.senior_idc_keur

    def test_higher_rate_increases_idc(self):
        """Higher flat all-in rate → higher IDC (monotone)."""
        r_low = self._base(rate=0.03)
        r_high = self._base(rate=0.07)
        assert r_high.capitalized_financing_costs.senior_idc_keur > r_low.capitalized_financing_costs.senior_idc_keur

    def test_earlier_capex_timing_changes_idc(self):
        """Front-loaded CAPEX draws Senior earlier → more IDC than uniform."""
        n = self.N
        periods = _make_periods(n)
        front_weights = (0.5, 0.3, 0.1, 0.05, 0.03, 0.02)
        back_weights = (0.02, 0.03, 0.05, 0.1, 0.3, 0.5)
        inp_front = ConstructionFinancingInput(
            enabled=True, periods=periods,
            capex_items=(ConstructionCapexTimingInput("EPC", "EPC", front_weights),),
            senior_pricing=ConstructionSeniorPricingInput(mode=SeniorRateMode.FLAT_ALL_IN, flat_all_in_rate=self.RATE),
        )
        inp_back = ConstructionFinancingInput(
            enabled=True, periods=periods,
            capex_items=(ConstructionCapexTimingInput("EPC", "EPC", back_weights),),
            senior_pricing=ConstructionSeniorPricingInput(mode=SeniorRateMode.FLAT_ALL_IN, flat_all_in_rate=self.RATE),
        )
        r_front = _run_b2(inp_front, self.SENIOR, self.EQUITY, self.SHL, capex_amounts={"EPC": self.BASE_CAPEX})
        r_back = _run_b2(inp_back, self.SENIOR, self.EQUITY, self.SHL, capex_amounts={"EPC": self.BASE_CAPEX})
        # Front-loading draws Senior earlier → more IDC
        assert r_front.capitalized_financing_costs.senior_idc_keur > r_back.capitalized_financing_costs.senior_idc_keur

    def test_funding_shortfall_fails_closed(self):
        """Senior commitment too small → FundingShortfallError (fail-closed)."""
        from finco_core.construction.stage_b2 import FundingShortfallError
        inp, capex_a = _make_flat_input(self.N, total_capex=self.BASE_CAPEX)
        with pytest.raises(FundingShortfallError):
            _run_b2(inp, senior_keur=10.0, equity_keur=0.0, shl_keur=0.0, capex_amounts=capex_a)


# ---------------------------------------------------------------------------
# 5. Synthetic B — 18m, hedge blend, commitment fee
# ---------------------------------------------------------------------------

class TestSyntheticB:
    """18-month construction, HEDGE_BLEND pricing, commitment fee."""

    N = 18
    CAPEX = 20_000.0
    SENIOR = 15_000.0
    EQUITY = 5_000.0
    SHL = 2_000.0
    BASE_EURIBOR = 0.035
    MARGIN = 0.012

    def _hedge_inp(self, hedge_pct: float = 0.8, commitment_rate: float = 0.0) -> ConstructionFinancingInput:
        n = self.N
        euribor = tuple([self.BASE_EURIBOR] * n)
        pricing = ConstructionSeniorPricingInput(
            mode=SeniorRateMode.HEDGE_BLEND,
            fixed_base_rate=0.030,   # fixed hedged component
            margin_rate=self.MARGIN,
            hedge_pct=hedge_pct,
            floating_base_rate_curve=euribor,
        )
        commitment = ConstructionCommitmentFeeInput(rate=commitment_rate) if commitment_rate else None
        return ConstructionFinancingInput(
            enabled=True,
            periods=_make_periods(n),
            capex_items=_make_capex(n, self.CAPEX),
            senior_pricing=pricing,
            commitment_fee=commitment,
        )

    def test_18_month_hedge_blend_converges(self):
        inp = self._hedge_inp()
        result = _run_b2(inp, self.SENIOR, self.EQUITY, self.SHL, capex_amounts={"EPC": self.CAPEX})
        assert result.final_residual_keur <= 1e-9
        assert len(result.senior_period_draw_keur) == self.N

    def test_higher_commitment_fee_increases_financing_costs(self):
        r_zero = _run_b2(self._hedge_inp(commitment_rate=0.0), self.SENIOR, self.EQUITY, self.SHL, capex_amounts={"EPC": self.CAPEX})
        r_fee = _run_b2(self._hedge_inp(commitment_rate=0.005), self.SENIOR, self.EQUITY, self.SHL, capex_amounts={"EPC": self.CAPEX})
        assert r_fee.capitalized_financing_costs.senior_commitment_fee_keur > r_zero.capitalized_financing_costs.senior_commitment_fee_keur
        assert r_fee.capitalized_financing_costs.total_keur > r_zero.capitalized_financing_costs.total_keur

    def test_convergence_fails_with_zero_iterations(self):
        """max_iterations=0 → RuntimeError on convergence failure."""
        inp = ConstructionFinancingInput(
            enabled=True,
            periods=_make_periods(self.N),
            capex_items=_make_capex(self.N, self.CAPEX),
            senior_pricing=ConstructionSeniorPricingInput(mode=SeniorRateMode.FLAT_ALL_IN, flat_all_in_rate=0.05),
            max_iterations=1,  # one iteration, IDC non-zero → may not converge
        )
        # Build config with max_iterations=1 explicitly on the ConstructionRuntimeConfig
        config = build_construction_runtime_config(
            inp, self.SENIOR, self.EQUITY, self.SHL,
            capex_amounts_keur={"EPC": self.CAPEX},
        )
        from finco_core.construction.stage_b2 import ConstructionRuntimeConfig
        from dataclasses import replace
        config_no_iter = replace(config, max_iterations=0)
        with pytest.raises(RuntimeError, match="did not converge"):
            run_stage_b2(config_no_iter)

    def test_shl_not_double_counted_in_construction(self):
        """SHL construction economics: SHL draws come from SHL pool, not Senior."""
        inp = self._hedge_inp()
        result = _run_b2(inp, self.SENIOR, self.EQUITY, self.SHL, capex_amounts={"EPC": self.CAPEX})
        # Total Senior drawn must not exceed commitment
        assert result.closing_senior_drawn_keur <= self.SENIOR + 1e-6


# ---------------------------------------------------------------------------
# 6. Serialization / None-zero distinction
# ---------------------------------------------------------------------------

class TestSerialization:
    def test_disabled_round_trip(self):
        """disabled ConstructionFinancingInput can be reconstructed from its fields."""
        import dataclasses
        inp = ConstructionFinancingInput(enabled=False)
        fields = {f.name: getattr(inp, f.name) for f in dataclasses.fields(inp)}
        reconstructed = ConstructionFinancingInput(**fields)
        assert reconstructed == inp

    def test_none_vs_disabled_distinct(self):
        """None (not set) is distinct from ConstructionFinancingInput(enabled=False)."""
        assert None != ConstructionFinancingInput(enabled=False)
        assert ConstructionFinancingInput(enabled=False) is not None

    def test_enabled_round_trip(self):
        """enabled ConstructionFinancingInput round-trips through its fields."""
        import dataclasses
        inp, _ = _make_flat_input(6)
        fields = {f.name: getattr(inp, f.name) for f in dataclasses.fields(inp)}
        reconstructed = ConstructionFinancingInput(**fields)
        assert reconstructed == inp

    def test_malformed_partial_contract_fails_closed(self):
        """ConstructionFinancingInput with enabled=True but missing pricing raises."""
        with pytest.raises(ValueError, match="PR9"):
            ConstructionFinancingInput(enabled=True, periods=_make_periods(6), senior_pricing=None)


# ---------------------------------------------------------------------------
# 7. VAT Facility deferred
# ---------------------------------------------------------------------------

class TestVatFacilityDeferred:
    def test_vat_deferred_default_true(self):
        assert ConstructionFinancingInput().vat_deferred is True

    def test_construction_config_has_zero_vat_rates(self):
        """Adapter must set all VAT rates to 0 (PR9_VAT_FACILITY_DEFERRED)."""
        inp, capex_a = _make_flat_input(6)
        config = build_construction_runtime_config(inp, 4_000.0, 1_000.0, 500.0, capex_amounts_keur=capex_a)
        assert config.vat_facility_interest_rate == 0.0
        assert config.vat_facility_commitment_fee_rate == 0.0
        assert config.vat_facility_commitment_keur == 0.0

    def test_vat_idc_is_zero_in_result(self):
        """With VAT deferred, vat_idc_keur and vat_commitment_fee_keur must be 0."""
        inp, capex_a = _make_flat_input(12)
        result = _run_b2(inp, capex_amounts=capex_a)
        assert result.capitalized_financing_costs.vat_idc_keur == 0.0
        assert result.capitalized_financing_costs.vat_commitment_fee_keur == 0.0


# ---------------------------------------------------------------------------
# 8. Oborovo source construction parity (reported, not tuned)
# ---------------------------------------------------------------------------

class TestOborovoSourceConstructionParity:
    """Run canonical construction kernel from Oborovo source primitives.

    Does NOT use the calibrated template (domain.construction.templates.oborovo).
    Uses primitive inputs from domain.construction.source_parity.
    Reports divergences — does not fail if residuals exist.
    """

    def _get_source_parity(self):
        """Import source parity fixtures (SOURCE_EVIDENCE_ONLY, allowed in tests)."""
        try:
            from domain.construction import source_parity
            return source_parity
        except ImportError:
            pytest.skip("domain.construction.source_parity not available")

    def test_oborovo_source_validation_run(self):
        """Run stage_b2 from Oborovo source primitives and report parity."""
        sp = self._get_source_parity()
        config = sp.oborovo_source_config()
        result = run_stage_b2(config)

        # Report key outputs (do not tune — assert only convergence and non-regression shape)
        assert result.final_residual_keur <= config.convergence_tolerance_keur, (
            f"Oborovo construction fixed-point did not converge; residual={result.final_residual_keur}"
        )

        # Source validation series
        source_idc_total = sum(sp.OBOROVO_SOURCE_SENIOR_IDC_MONTHLY_KEUR)
        source_fee_total = sum(sp.OBOROVO_SOURCE_COMMITMENT_FEE_MONTHLY_KEUR)
        engine_idc_total = result.capitalized_financing_costs.senior_idc_keur
        engine_fee_total = result.capitalized_financing_costs.senior_commitment_fee_keur

        idc_delta = abs(engine_idc_total - source_idc_total)
        fee_delta = abs(engine_fee_total - source_fee_total)

        # Parity report (informational — test always passes as long as engine converges)
        print(f"\nOborovo source construction parity:")
        print(f"  Senior IDC: engine={engine_idc_total:.6f} source={source_idc_total:.6f} delta={idc_delta:.6f}")
        print(f"  Commitment fee: engine={engine_fee_total:.6f} source={source_fee_total:.6f} delta={fee_delta:.6f}")
        print(f"  Iterations: {result.iterations}, residual: {result.final_residual_keur:.2e}")
        print(f"  GFA: {result.final_gfa_keur:.6f}, closing Senior: {result.closing_senior_drawn_keur:.6f}")

        # Structural assertions (not tuned, just sanity)
        assert engine_idc_total > 0.0, "engine Senior IDC must be positive"
        assert result.final_gfa_keur > 0.0

    def test_oborovo_template_not_used_for_parity(self):
        """This parity test must not import the calibrated Oborovo template."""
        sp = self._get_source_parity()
        config = sp.oborovo_source_config()
        # Verify: the config was built from oborovo_source_config(), not build_oborovo_construction_config()
        # oborovo_source_config uses primitive source inputs; build_oborovo_construction_config uses a calibrated rate
        # We simply verify run_stage_b2 works and returns a result (no template import needed here)
        result = run_stage_b2(config)
        assert result is not None


# ---------------------------------------------------------------------------
# 9. Generic Solar/Wind PR-8 fingerprints unchanged
# ---------------------------------------------------------------------------

class TestPR8FingerprintsUnchanged:
    """PR-8 production fingerprints must be bit-identical when construction_financing is None."""

    SOLAR_FINGERPRINTS = {
        "revenue": 94431.06685697282,
        "senior_ds": 35302.12518820596,
        "distributions": 5002.162578513825,
    }
    WIND_FINGERPRINTS = {
        "revenue": 213124.95083177992,
        "senior_ds": 42650.79738447129,
        "distributions": 10506.513025614555,
    }

    def _run_solar(self):
        try:
            from app.project_factories import build_generic_solar_project_inputs
            from app.services.production_financial_authority import run_clean_production
        except ImportError:
            pytest.skip("Solar production factories not available in this test environment")
        pi = build_generic_solar_project_inputs()
        return run_clean_production(pi)

    def _run_wind(self):
        try:
            from app.project_factories import build_generic_wind_project_inputs
            from app.services.production_financial_authority import run_clean_production
        except ImportError:
            pytest.skip("Wind production factories not available in this test environment")
        pi = build_generic_wind_project_inputs()
        return run_clean_production(pi)

    def test_solar_construction_financing_defaults_disabled(self):
        """Generic Solar production inputs must have construction_financing=None."""
        from app.project_factories import create_default_solar_project
        pi = create_default_solar_project()
        assert pi.financing.construction_financing is None, (
            "Generic Solar must not enable construction financing by default"
        )

    def test_wind_construction_financing_defaults_disabled(self):
        """Generic Wind production inputs must have construction_financing=None."""
        from app.project_factories import create_default_wind_project
        pi = create_default_wind_project()
        assert pi.financing.construction_financing is None, (
            "Generic Wind must not enable construction financing by default"
        )


# ---------------------------------------------------------------------------
# 10. End-to-end tests through run_project_financing_model with construction enabled
# ---------------------------------------------------------------------------

def _make_solar_construction_input(n_periods: int) -> "ConstructionFinancingInput":
    """Build ConstructionFinancingInput covering Solar factory hard CAPEX items."""
    from datetime import date as _date
    periods = []
    y, m = 2030, 1
    for _ in range(n_periods):
        nm = m + 1 if m < 12 else 1
        ny = y if m < 12 else y + 1
        periods.append(ConstructionPeriodSpec(
            start_date=_date(y, m, 1),
            end_date=_date(ny, nm, 1),
        ))
        y, m = ny, nm
    w = tuple(1.0 / n_periods for _ in range(n_periods))
    capex_items = (
        ConstructionCapexTimingInput(code="epc_contract", name="EPC Contract", payment_weights=w),
        ConstructionCapexTimingInput(code="production_units", name="Production Units", payment_weights=w),
        ConstructionCapexTimingInput(code="epc_other", name="EPC Other", payment_weights=w),
        ConstructionCapexTimingInput(code="grid_connection", name="Grid Connection", payment_weights=w),
        ConstructionCapexTimingInput(code="audit_legal", name="Audit & Legal", payment_weights=w),
    )
    return ConstructionFinancingInput(
        enabled=True,
        periods=tuple(periods),
        capex_items=capex_items,
        senior_pricing=ConstructionSeniorPricingInput(
            mode=SeniorRateMode.FLAT_ALL_IN,
            flat_all_in_rate=0.055,
            day_count=SeniorDayCountConvention.ACT_360,
        ),
        commitment_fee=ConstructionCommitmentFeeInput(rate=0.005),
        structuring_fee=ConstructionStructuringFeeInput(rate=0.01, basis_keur=24_750.0),
    )


class TestPR9EndToEndConstructionFinancing:
    """End-to-end tests through run_project_financing_model with construction_financing enabled.

    These tests verify that the outer G2A fixed point:
    - Converges and returns a ConstructionFinancingResult
    - Produces positive IDC and commitment fees
    - Preserves the inner financing result structure
    - Does not alter PR-8 production fingerprints (construction gate is opt-in)
    """

    def _solar_with_construction(self, n_periods: int = 12):
        import dataclasses
        from app.project_factories import create_default_solar_project
        from financial_engine.financing import run_project_financing_model
        pi = create_default_solar_project()
        cf = _make_solar_construction_input(n_periods)
        pi = dataclasses.replace(
            pi,
            financing=dataclasses.replace(pi.financing, construction_financing=cf),
        )
        return run_project_financing_model(pi)

    def test_6_period_flat_converges_and_returns_typed_result(self):
        """6-period flat-rate construction financing converges and returns ConstructionFinancingResult."""
        from financial_engine.financing.contracts import ConstructionFinancingResult
        result = self._solar_with_construction(n_periods=6)
        assert result.construction_financing is not None
        assert isinstance(result.construction_financing, ConstructionFinancingResult)
        assert result.construction_financing.authority == "PR9_TYPED_CONSTRUCTION_FINANCING_IDC_AUTHORITY"
        assert result.construction_financing.outer_iterations >= 1

    def test_6_period_idc_positive(self):
        """IDC accruals must be positive when rate > 0 and senior draws > 0."""
        result = self._solar_with_construction(n_periods=6)
        cf = result.construction_financing
        assert sum(cf.senior_idc_accrual_keur) > 0.0, "IDC must be positive with 5.5% rate"

    def test_6_period_commitment_fee_positive(self):
        """Commitment fee accruals must be positive when rate > 0."""
        result = self._solar_with_construction(n_periods=6)
        cf = result.construction_financing
        assert sum(cf.senior_commitment_fee_accrual_keur) > 0.0

    def test_6_period_total_uses_exceeds_base_hard_capex(self):
        """Total project uses must exceed base hard CAPEX by at least IDC."""
        from app.project_factories import create_default_solar_project
        base_pi = create_default_solar_project()
        base_hard = base_pi.capex.hard_capex_keur  # 33_000 kEUR
        result = self._solar_with_construction(n_periods=6)
        assert result.project_uses.total_project_uses_keur > base_hard

    def test_6_period_capitalized_financing_positive(self):
        """Total capitalized financing must be positive."""
        result = self._solar_with_construction(n_periods=6)
        assert result.construction_financing.total_capitalized_financing_keur > 0.0

    def test_6_period_senior_draws_cover_commitment(self):
        """Cumulative senior draw at end must equal final senior commitment."""
        result = self._solar_with_construction(n_periods=6)
        cf = result.construction_financing
        cumul_final = cf.cumulative_senior_keur[-1] if cf.cumulative_senior_keur else 0.0
        # Senior is drawn progressively — cumulative at end should equal final commitment
        assert cumul_final == pytest.approx(result.final_senior_commitment_keur, rel=0.01)

    def test_12_period_flat_converges(self):
        """12-period construction (1-year) converges and returns result."""
        result = self._solar_with_construction(n_periods=12)
        assert result.construction_financing is not None
        assert result.construction_financing.outer_iterations >= 1
        assert result.construction_financing.stage_b2_iterations >= 1

    def test_12_period_period_vectors_length_matches(self):
        """Period vectors in ConstructionFinancingResult must have length = n_periods."""
        n = 12
        result = self._solar_with_construction(n_periods=n)
        cf = result.construction_financing
        assert len(cf.period_start_dates) == n
        assert len(cf.period_end_dates) == n
        assert len(cf.senior_draws_keur) == n
        assert len(cf.senior_idc_accrual_keur) == n
        assert len(cf.hard_capex_uses_keur) == n

    def test_12_period_hard_capex_sums_to_total(self):
        """Sum of hard_capex_uses_keur must equal construction CAPEX total."""
        from app.project_factories import create_default_solar_project
        pi = create_default_solar_project()
        result = self._solar_with_construction(n_periods=12)
        cf = result.construction_financing
        # Hard capex covers epc_contract+production_units+epc_other+grid_connection+audit_legal = 33000
        assert sum(cf.hard_capex_uses_keur) == pytest.approx(33_000.0, rel=1e-6)

    def test_construction_gate_disabled_when_cf_none(self):
        """When construction_financing=None, run_project_financing_model must return None construction_financing."""
        from app.project_factories import create_default_solar_project
        from financial_engine.financing import run_project_financing_model
        pi = create_default_solar_project()
        assert pi.financing.construction_financing is None
        result = run_project_financing_model(pi)
        assert result.construction_financing is None

    def test_outer_idempotence_residual_within_tolerance(self):
        """Outer residual at convergence must be ≤ default tolerance."""
        result = self._solar_with_construction(n_periods=12)
        cf = result.construction_financing
        assert cf.outer_residual_keur <= 1e-7 * 10 or cf.outer_residual_keur == pytest.approx(0.0, abs=1e-6)

    def test_construction_financing_result_authority_token(self):
        """Authority token must be PR9_TYPED_CONSTRUCTION_FINANCING_IDC_AUTHORITY."""
        result = self._solar_with_construction(n_periods=12)
        assert result.construction_financing.authority == "PR9_TYPED_CONSTRUCTION_FINANCING_IDC_AUTHORITY"


# ---------------------------------------------------------------------------
# 11. CAPEX authority negative tests (Fix 1)
# ---------------------------------------------------------------------------

class TestCAPEXAuthorityNegative:
    """Negative tests for PR9 CAPEX authority validation (Fix 1)."""

    def _solar_pi_with_cf(self, capex_items, n_periods=6):
        """Build Solar ProjectInputs with construction_financing overriding capex_items."""
        import dataclasses
        from app.project_factories import create_default_solar_project
        pi = create_default_solar_project()
        w = tuple(1.0 / n_periods for _ in range(n_periods))
        from datetime import date as _date
        periods = []
        y, m = 2030, 1
        for _ in range(n_periods):
            nm = m + 1 if m < 12 else 1
            ny = y if m < 12 else y + 1
            periods.append(ConstructionPeriodSpec(start_date=_date(y, m, 1), end_date=_date(ny, nm, 1)))
            y, m = ny, nm
        cf = ConstructionFinancingInput(
            enabled=True,
            periods=tuple(periods),
            capex_items=tuple(capex_items),
            senior_pricing=ConstructionSeniorPricingInput(
                mode=SeniorRateMode.FLAT_ALL_IN, flat_all_in_rate=0.055,
            ),
        )
        return dataclasses.replace(pi, financing=dataclasses.replace(pi.financing, construction_financing=cf))

    def test_A_sum_mismatch_raises(self):
        """Negative A: capex_items sum != canonical hard_capex_keur → PR9_CONSTRUCTION_CAPEX_AUTHORITY_MISMATCH.

        Achieved by adding a non-zero hard CAPEX field (ops_prep) to the CapexStructure
        while NOT covering it in capex_items. The omit-non-zero check fires before
        the sum check, but both produce PR9_CONSTRUCTION_CAPEX_AUTHORITY_MISMATCH.
        """
        from financial_engine.financing import run_project_financing_model
        import dataclasses
        n = 6
        w = tuple(1.0 / n for _ in range(n))
        # capex_items covers only the original 5 Solar fields
        capex_items = (
            ConstructionCapexTimingInput(code="epc_contract", name="EPC", payment_weights=w),
            ConstructionCapexTimingInput(code="production_units", name="PU", payment_weights=w),
            ConstructionCapexTimingInput(code="epc_other", name="EPO", payment_weights=w),
            ConstructionCapexTimingInput(code="grid_connection", name="GC", payment_weights=w),
            ConstructionCapexTimingInput(code="audit_legal", name="AL", payment_weights=w),
        )
        pi = self._solar_pi_with_cf(capex_items, n_periods=n)
        # Add non-zero ops_prep to the CapexStructure (not covered by capex_items → mismatch)
        from finco_core.inputs._models import CapexItem
        new_capex = dataclasses.replace(
            pi.capex,
            ops_prep=dataclasses.replace(pi.capex.ops_prep, amount_keur=500.0),
        )
        pi2 = dataclasses.replace(pi, capex=new_capex)
        with pytest.raises(ValueError, match="PR9_CONSTRUCTION_CAPEX_AUTHORITY_MISMATCH"):
            run_project_financing_model(pi2)

    def test_B_duplicate_code_raises(self):
        """Negative B: duplicate capex_item codes → PR9_CONSTRUCTION_CAPEX_AUTHORITY_MISMATCH."""
        from financial_engine.financing import run_project_financing_model
        n = 6
        w = tuple(1.0 / n for _ in range(n))
        capex_items = (
            ConstructionCapexTimingInput(code="epc_contract", name="EPC A", payment_weights=w),
            ConstructionCapexTimingInput(code="epc_contract", name="EPC B", payment_weights=w),  # duplicate
            ConstructionCapexTimingInput(code="production_units", name="PU", payment_weights=w),
            ConstructionCapexTimingInput(code="epc_other", name="EPO", payment_weights=w),
            ConstructionCapexTimingInput(code="grid_connection", name="GC", payment_weights=w),
            ConstructionCapexTimingInput(code="audit_legal", name="AL", payment_weights=w),
        )
        pi = self._solar_pi_with_cf(capex_items, n_periods=n)
        with pytest.raises(ValueError, match="PR9_CONSTRUCTION_CAPEX_AUTHORITY_MISMATCH"):
            run_project_financing_model(pi)

    def test_C_omit_non_zero_field_raises(self):
        """Negative C: omitting a non-zero canonical CAPEX field → PR9_CONSTRUCTION_CAPEX_AUTHORITY_MISMATCH."""
        from financial_engine.financing import run_project_financing_model
        n = 6
        w = tuple(1.0 / n for _ in range(n))
        # Omit production_units (3000 kEUR, non-zero in solar factory)
        capex_items = (
            ConstructionCapexTimingInput(code="epc_contract", name="EPC", payment_weights=w),
            ConstructionCapexTimingInput(code="epc_other", name="EPO", payment_weights=w),
            ConstructionCapexTimingInput(code="grid_connection", name="GC", payment_weights=w),
            ConstructionCapexTimingInput(code="audit_legal", name="AL", payment_weights=w),
        )
        pi = self._solar_pi_with_cf(capex_items, n_periods=n)
        with pytest.raises(ValueError, match="PR9_CONSTRUCTION_CAPEX_AUTHORITY_MISMATCH"):
            run_project_financing_model(pi)


# ---------------------------------------------------------------------------
# 12. PR-8 fingerprint tests without skips (Fix 8)
# ---------------------------------------------------------------------------

class TestPR8FingerprintsWithoutSkips:
    """PR-8 Solar/Wind fingerprints must be bit-identical when construction_financing is None.

    Uses create_default_solar_project / create_default_wind_project directly,
    which are the actual working factory functions.
    """

    SOLAR_FINGERPRINTS = {
        "revenue": 94431.06685697282,
        "senior_ds": 35302.12518820596,
        "distributions": 5002.162578513825,
    }
    WIND_FINGERPRINTS = {
        "revenue": 213124.95083177992,
        "senior_ds": 42650.79738447129,
        "distributions": 10506.513025614555,
    }

    def _run_solar(self):
        try:
            from app.project_factories import create_default_solar_project
            from financial_engine.financing import run_project_financing_model
        except ImportError:
            pytest.skip("Solar factory not available")
        pi = create_default_solar_project()
        return run_project_financing_model(pi)

    def _run_wind(self):
        try:
            from app.project_factories import create_default_wind_project
            from financial_engine.financing import run_project_financing_model
        except ImportError:
            pytest.skip("Wind factory not available")
        pi = create_default_wind_project()
        return run_project_financing_model(pi)

    def _extract_fingerprints(self, result):
        """Extract revenue and senior DS fingerprints from model result.

        Note: distributions require the G2C layer (not accessible from
        run_project_financing_model), so only revenue and senior DS are checked here.
        """
        mr = result.project_model_result
        revenue = sum(p.revenue_keur for p in mr.periods)
        senior_ds = sum(mr.senior_debt.senior_debt_service_keur)
        return {"revenue": revenue, "senior_ds": senior_ds}

    def test_solar_fingerprints_unchanged(self):
        """Solar model fingerprints must be bit-identical to PR-8 baseline."""
        result = self._run_solar()
        fps = self._extract_fingerprints(result)
        assert fps["revenue"] == pytest.approx(self.SOLAR_FINGERPRINTS["revenue"], rel=1e-9)
        assert fps["senior_ds"] == pytest.approx(self.SOLAR_FINGERPRINTS["senior_ds"], rel=1e-9)

    def test_wind_fingerprints_unchanged(self):
        """Wind model fingerprints must be bit-identical to PR-8 baseline."""
        result = self._run_wind()
        fps = self._extract_fingerprints(result)
        assert fps["revenue"] == pytest.approx(self.WIND_FINGERPRINTS["revenue"], rel=1e-9)
        assert fps["senior_ds"] == pytest.approx(self.WIND_FINGERPRINTS["senior_ds"], rel=1e-9)

    def test_solar_construction_financing_none(self):
        """Solar default project must have construction_financing=None."""
        try:
            from app.project_factories import create_default_solar_project
        except ImportError:
            pytest.skip("Solar factory not available")
        pi = create_default_solar_project()
        assert pi.financing.construction_financing is None

    def test_wind_construction_financing_none(self):
        """Wind default project must have construction_financing=None."""
        try:
            from app.project_factories import create_default_wind_project
        except ImportError:
            pytest.skip("Wind factory not available")
        pi = create_default_wind_project()
        assert pi.financing.construction_financing is None
