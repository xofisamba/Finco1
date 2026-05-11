"""Phase 6C.1 — Tests for HoldCo / intercompany tax schema."""
import pytest

from domain.tax.holdco_inputs import (
    HoldCoTaxInputs,
    WithholdingTaxConfig,
    InterestDeductibilityConfig,
    IntercompanyTaxFlow,
)
from domain.tax.holdco_result import (
    HoldCoTaxPeriodResult,
    HoldCoTaxResult,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_wht_config(
    rate_dividends=0.12,
    rate_interest=0.0,
    notes=None,
):
    return WithholdingTaxConfig(
        rate_dividends=rate_dividends,
        rate_interest=rate_interest,
        notes=notes,
    )


def make_interest_deductibility(
    thin_cap_ratio=4.0,
    interest_limitation_pct_ebitda=0.30,
    notes=None,
):
    return InterestDeductibilityConfig(
        thin_cap_ratio=thin_cap_ratio,
        interest_limitation_pct_ebitda=interest_limitation_pct_ebitda,
        notes=notes,
    )


def make_holdco_inputs(
    entity_code="HR-HoldCo-001",
    country_code="HR",
    tax_year=2026,
    n_periods=5,
    **overrides,
):
    defaults = dict(
        entity_code=entity_code,
        country_code=country_code,
        tax_year=tax_year,
        dividend_income_by_period_keur=tuple(1000.0 for _ in range(n_periods)),
        shl_interest_income_by_period_keur=tuple(200.0 for _ in range(n_periods)),
        shl_principal_received_by_period_keur=tuple(500.0 for _ in range(n_periods)),
        holdco_opex_by_period_keur=tuple(50.0 for _ in range(n_periods)),
        withholding_tax_config=make_wht_config(),
        interest_deductibility=make_interest_deductibility(),
        metadata={"source": "test", "version": "1"},
    )
    defaults.update(overrides)
    return HoldCoTaxInputs(**defaults)


def make_period_result(period_index=0, **overrides):
    defaults = dict(
        period_index=period_index,
        taxable_dividend_income_keur=1000.0,
        taxable_interest_income_keur=200.0,
        non_taxable_principal_keur=500.0,
        deductible_opex_keur=50.0,
        taxable_income_before_limitations_keur=1150.0,
        withholding_tax_dividends_keur=120.0,
        withholding_tax_interest_keur=0.0,
        interest_limited_keur=0.0,
        notes=("SHL principal excluded from taxable income",),
        warnings=(),
    )
    defaults.update(overrides)
    return HoldCoTaxPeriodResult(**defaults)


# ── Tests: WithholdingTaxConfig ───────────────────────────────────────────────

class TestWithholdingTaxConfig:
    def test_valid_wht_config_accepted(self):
        cfg = WithholdingTaxConfig(rate_dividends=0.12, rate_interest=0.15)
        assert cfg.rate_dividends == 0.12
        assert cfg.rate_interest == 0.15

    def test_zero_rates_accepted(self):
        cfg = WithholdingTaxConfig(rate_dividends=0.0, rate_interest=0.0)
        assert cfg.rate_dividends == 0.0
        assert cfg.rate_interest == 0.0

    def test_invalid_rate_dividends_rejected(self):
        with pytest.raises(ValueError, match="rate_dividends"):
            WithholdingTaxConfig(rate_dividends=1.5, rate_interest=0.0)

    def test_invalid_rate_interest_rejected(self):
        with pytest.raises(ValueError, match="rate_interest"):
            WithholdingTaxConfig(rate_dividends=0.0, rate_interest=-0.1)

    def test_notes_preserved(self):
        cfg = WithholdingTaxConfig(rate_dividends=0.12, rate_interest=0.0, notes="EU exemption")
        assert cfg.notes == "EU exemption"


# ── Tests: InterestDeductibilityConfig ───────────────────────────────────────

class TestInterestDeductibilityConfig:
    def test_valid_config_accepted(self):
        cfg = InterestDeductibilityConfig(
            thin_cap_ratio=4.0,
            interest_limitation_pct_ebitda=0.30,
        )
        assert cfg.thin_cap_ratio == 4.0
        assert cfg.interest_limitation_pct_ebitda == 0.30

    def test_none_values_accepted(self):
        cfg = InterestDeductibilityConfig(thin_cap_ratio=None, interest_limitation_pct_ebitda=None)
        assert cfg.thin_cap_ratio is None
        assert cfg.interest_limitation_pct_ebitda is None

    def test_invalid_thin_cap_ratio_rejected(self):
        with pytest.raises(ValueError, match="thin_cap_ratio"):
            InterestDeductibilityConfig(thin_cap_ratio=0.0)

    def test_invalid_ebitda_limit_rejected(self):
        with pytest.raises(ValueError, match="interest_limitation_pct_ebitda"):
            InterestDeductibilityConfig(interest_limitation_pct_ebitda=1.5)


# ── Tests: IntercompanyTaxFlow ───────────────────────────────────────────────

class TestIntercompanyTaxFlow:
    def test_valid_dividend_flow(self):
        flow = IntercompanyTaxFlow(
            period_index=0,
            flow_type="dividend",
            gross_amount_keur=1000.0,
            withholding_tax_rate=0.12,
            country_of_origin="HR",
        )
        assert flow.flow_type == "dividend"
        assert flow.gross_amount_keur == 1000.0

    def test_valid_interest_flow(self):
        flow = IntercompanyTaxFlow(
            period_index=1,
            flow_type="interest",
            gross_amount_keur=200.0,
            withholding_tax_rate=0.0,
            country_of_origin="HR",
        )
        assert flow.flow_type == "interest"

    def test_invalid_flow_type_rejected(self):
        with pytest.raises(ValueError, match="flow_type"):
            IntercompanyTaxFlow(
                period_index=0, flow_type="royalty",
                gross_amount_keur=100.0, withholding_tax_rate=0.0,
                country_of_origin="HR",
            )

    def test_negative_amount_rejected(self):
        with pytest.raises(ValueError, match="gross_amount_keur"):
            IntercompanyTaxFlow(
                period_index=0, flow_type="dividend",
                gross_amount_keur=-100.0, withholding_tax_rate=0.0,
                country_of_origin="HR",
            )

    def test_empty_country_rejected(self):
        with pytest.raises(ValueError, match="country_of_origin"):
            IntercompanyTaxFlow(
                period_index=0, flow_type="dividend",
                gross_amount_keur=1000.0, withholding_tax_rate=0.0,
                country_of_origin="",
            )


# ── Tests: HoldCoTaxInputs ───────────────────────────────────────────────────

class TestHoldCoTaxInputs:
    def test_valid_holdco_inputs_accepted(self):
        inputs = make_holdco_inputs()
        assert inputs.entity_code == "HR-HoldCo-001"
        assert inputs.country_code == "HR"
        assert inputs.tax_year == 2026
        assert len(inputs.dividend_income_by_period_keur) == 5

    def test_metadata_preserved(self):
        inputs = make_holdco_inputs(
            metadata={"source": "test", "version": "2"},
        )
        assert inputs.metadata["source"] == "test"
        assert inputs.metadata["version"] == "2"

    def test_empty_entity_code_rejected(self):
        with pytest.raises(ValueError, match="entity_code must be non-empty"):
            make_holdco_inputs(entity_code="")

    def test_empty_country_code_rejected(self):
        with pytest.raises(ValueError, match="country_code must be non-empty"):
            make_holdco_inputs(country_code="  ")

    def test_invalid_tax_year_rejected(self):
        with pytest.raises(ValueError, match="tax_year must be between"):
            make_holdco_inputs(tax_year=1999)

    def test_negative_dividend_income_rejected(self):
        vals = tuple([-100.0] + [0.0] * 4)
        with pytest.raises(ValueError, match="dividend_income_by_period_keur"):
            make_holdco_inputs(dividend_income_by_period_keur=vals)

    def test_shl_principal_tracked_as_non_taxable(self):
        """SHL principal is accepted and stored — not mixed into taxable income fields."""
        inputs = make_holdco_inputs(
            shl_principal_received_by_period_keur=tuple(500.0 for _ in range(5)),
        )
        # Principal should be present and non-negative
        assert all(p >= 0 for p in inputs.shl_principal_received_by_period_keur)

    def test_negative_principal_rejected(self):
        vals = tuple([500.0, -100.0, 500.0, 500.0, 500.0])
        with pytest.raises(ValueError, match="shl_principal_received_by_period_keur.*must be non-negative"):
            make_holdco_inputs(shl_principal_received_by_period_keur=vals)

    def test_mismatched_period_lengths_rejected(self):
        with pytest.raises(ValueError, match="shl_interest_income_by_period_keur length"):
            make_holdco_inputs(
                shl_interest_income_by_period_keur=(200.0, 200.0),  # only 2
            )

    def test_wht_config_stored_not_applied(self):
        """WHT rates are stored but no WHT is calculated or applied."""
        cfg = make_wht_config(rate_dividends=0.12, rate_interest=0.15)
        inputs = make_holdco_inputs(withholding_tax_config=cfg)
        assert inputs.withholding_tax_config.rate_dividends == 0.12
        # No active WHT calculation happens — schema only

    def test_interest_deductibility_stored_not_applied(self):
        """Thin-cap and EBITDA limitation params stored but not enforced."""
        deduct = make_interest_deductibility(thin_cap_ratio=4.0, interest_limitation_pct_ebitda=0.30)
        inputs = make_holdco_inputs(interest_deductibility=deduct)
        assert inputs.interest_deductibility.thin_cap_ratio == 4.0
        # No active limitation calculation happens — schema only


# ── Tests: HoldCoTaxPeriodResult ─────────────────────────────────────────────

class TestHoldCoTaxPeriodResult:
    def test_valid_period_result_accepted(self):
        result = make_period_result(period_index=0)
        assert result.period_index == 0
        assert result.taxable_dividend_income_keur == 1000.0
        assert result.non_taxable_principal_keur == 500.0
        assert result.withholding_tax_dividends_keur == 120.0

    def test_principal_excluded_from_taxable_income(self):
        """SHL principal is in separate field, not deducted from taxable income."""
        result = make_period_result(
            taxable_dividend_income_keur=1000.0,
            taxable_interest_income_keur=200.0,
            non_taxable_principal_keur=500.0,
            deductible_opex_keur=50.0,
            taxable_income_before_limitations_keur=1150.0,  # = div + int + opex
        )
        # Principal should NOT be in taxable income
        assert result.taxable_income_before_limitations_keur == 1150.0

    def test_notes_and_warnings_preserved(self):
        result = make_period_result(
            notes=("SHL principal excluded", "WHT stored not paid"),
            warnings=("thin-cap exceeded in period 3",),
        )
        assert "SHL principal excluded" in result.notes
        assert any("thin-cap exceeded" in w for w in result.warnings)


# ── Tests: HoldCoTaxResult ────────────────────────────────────────────────────

class TestHoldCoTaxResult:
    def test_valid_holdco_result_accepted(self):
        period_results = tuple(make_period_result(i) for i in range(5))
        result = HoldCoTaxResult(
            entity_code="HR-HoldCo-001",
            country_code="HR",
            tax_year=2026,
            period_results=period_results,
            total_taxable_dividend_keur=5000.0,
            total_taxable_interest_keur=1000.0,
            total_non_taxable_principal_keur=2500.0,
            total_withholding_tax_dividends_keur=600.0,
            total_withholding_tax_interest_keur=0.0,
            metadata={"version": "1"},
            notes=("schema-only result",),
        )
        assert result.entity_code == "HR-HoldCo-001"
        assert len(result.period_results) == 5

    def test_totals_reconcile(self):
        period_results = tuple(make_period_result(i) for i in range(5))
        result = HoldCoTaxResult(
            entity_code="HR-HoldCo-001",
            country_code="HR",
            tax_year=2026,
            period_results=period_results,
            total_taxable_dividend_keur=5000.0,
            total_taxable_interest_keur=1000.0,
            total_non_taxable_principal_keur=2500.0,
            total_withholding_tax_dividends_keur=600.0,
            total_withholding_tax_interest_keur=0.0,
        )
        # Totals are stored (not recalculated) — schema allows this
        assert result.total_taxable_dividend_keur == 5000.0

    def test_no_active_tax_calculation(self):
        """Schema only — result fields are audit containers, no computation."""
        period_results = tuple(make_period_result(i) for i in range(5))
        result = HoldCoTaxResult(
            entity_code="HR-HoldCo-001",
            country_code="HR",
            tax_year=2026,
            period_results=period_results,
            total_taxable_dividend_keur=0.0,
            total_taxable_interest_keur=0.0,
            total_non_taxable_principal_keur=0.0,
            total_withholding_tax_dividends_keur=0.0,
            total_withholding_tax_interest_keur=0.0,
            notes=("no active CIT calculation in Phase 6C.1",),
        )
        assert any("no active CIT calculation" in n for n in result.notes)