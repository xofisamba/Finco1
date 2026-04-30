"""Tests for S1-1: ConstructionPLStatement — deterministic tax loss from construction period.

This test verifies the blueprint requirement:
- ConstructionPLStatement deterministically computes initial_tax_loss_keur
- TaxParams.construction_pl replaces prior_tax_loss_keur manual tuning
- Backward compatibility: prior_tax_loss_keur still works if construction_pl is None
"""
import pytest
from domain.tax.construction_pl import (
    ConstructionPLStatement,
    create_default_construction_pl,
)
from domain.inputs import TaxParams


class TestConstructionPLStatement:
    """Test ConstructionPLStatement dataclass."""

    def test_book_loss_simple(self):
        """Book loss = idc + bank_fees + commitment_fees + preop_opex + other_diff - revenue"""
        pl = ConstructionPLStatement(
            idc_keur=1000,
            bank_fees_keur=200,
            commitment_fees_keur=300,
            pre_operational_opex_keur=0,
            construction_period_revenue_keur=0,
            other_book_tax_difference_keur=0,
        )
        assert pl.book_loss_keur == 1500.0

    def test_book_loss_with_revenue(self):
        """Revenue reduces book loss."""
        pl = ConstructionPLStatement(
            idc_keur=1000,
            bank_fees_keur=200,
            construction_period_revenue_keur=500,
        )
        assert pl.book_loss_keur == 700.0

    def test_initial_tax_loss_positive(self):
        """initial_tax_loss_keur is max(0, book_loss)."""
        pl = ConstructionPLStatement(idc_keur=1000, bank_fees_keur=200)
        assert pl.initial_tax_loss_keur == 1200.0

    def test_initial_tax_loss_capped_at_zero(self):
        """initial_tax_loss_keur cannot be negative."""
        pl = ConstructionPLStatement(
            idc_keur=0,
            bank_fees_keur=0,
            construction_period_revenue_keur=1000,
        )
        assert pl.initial_tax_loss_keur == 0.0

    def test_oborovo_realistic_values(self):
        """Oborovo has ~9,000 kEUR initial tax loss (IDC + fees + timing effects)."""
        pl = ConstructionPLStatement(
            idc_keur=1169,           # Oborovo IDC
            bank_fees_keur=300,      # Bank fees
            commitment_fees_keur=470, # Commitment fees
            # other_book_tax_difference captures construction-period interest
            # that Excel capitalizes but our model doesn't track separately
            other_book_tax_difference_keur=7060,
        )
        assert pl.book_loss_keur == 8999.0
        assert pl.initial_tax_loss_keur == 8999.0

    def test_tuho_realistic_values(self):
        """TUHO has larger construction loss due to 18-month build + SHL IDC."""
        pl = ConstructionPLStatement(
            idc_keur=3569,           # TUHO SHL IDC
            bank_fees_keur=500,      # Higher bank fees
            commitment_fees_keur=800, # Higher commitment fees
            # TUHO construction period interest effects
            other_book_tax_difference_keur=20000,
        )
        assert pl.book_loss_keur == 24869.0
        assert pl.initial_tax_loss_keur == 24869.0

    def test_validation_empty(self):
        """Empty construction PL is valid."""
        pl = ConstructionPLStatement()
        assert pl.validate() == []

    def test_validation_negative_values(self):
        """Negative values are flagged as errors."""
        pl = ConstructionPLStatement(idc_keur=-100)
        errors = pl.validate()
        assert "IDC cannot be negative" in errors

    def test_validation_revenue_negative(self):
        """Negative revenue is flagged."""
        pl = ConstructionPLStatement(construction_period_revenue_keur=-500)
        errors = pl.validate()
        assert "Construction period revenue cannot be negative" in errors


class TestCreateDefaultConstructionPL:
    """Test factory function."""

    def test_factory_with_values(self):
        """Factory creates statement with given values."""
        pl = create_default_construction_pl(
            idc_keur=1000,
            bank_fees_keur=200,
            commitment_fees_keur=300,
        )
        assert pl.idc_keur == 1000
        assert pl.bank_fees_keur == 200
        assert pl.commitment_fees_keur == 300
        assert pl.pre_operational_opex_keur == 0
        assert pl.construction_period_revenue_keur == 0

    def test_factory_defaults(self):
        """Factory with no args creates empty statement."""
        pl = create_default_construction_pl()
        assert pl.idc_keur == 0
        assert pl.book_loss_keur == 0
        assert pl.initial_tax_loss_keur == 0


class TestTaxParamsConstructionPL:
    """Test TaxParams integration with ConstructionPLStatement."""

    def test_tax_params_with_construction_pl(self):
        """TaxParams.initial_tax_loss_keur uses construction_pl when set."""
        pl = ConstructionPLStatement(idc_keur=1169, bank_fees_keur=300)
        params = TaxParams(construction_pl=pl)
        assert params.initial_tax_loss_keur == 1469.0

    def test_tax_params_prior_tax_loss_fallback(self):
        """TaxParams falls back to prior_tax_loss_keur when construction_pl is None."""
        params = TaxParams(prior_tax_loss_keur=25000)
        assert params.initial_tax_loss_keur == 25000.0

    def test_tax_params_construction_pl_takes_precedence(self):
        """construction_pl takes precedence over prior_tax_loss_keur."""
        pl = ConstructionPLStatement(idc_keur=1000)
        params = TaxParams(
            construction_pl=pl,
            prior_tax_loss_keur=25000,  # Should be ignored
        )
        assert params.initial_tax_loss_keur == 1000.0

    def test_tax_params_neither_set(self):
        """Both None/0 gives 0 initial tax loss."""
        params = TaxParams()
        assert params.initial_tax_loss_keur == 0.0

    def test_tax_params_backward_compat_oborovo(self):
        """Backward compat: Oborovo with prior_tax_loss_keur=0 gives correct loss."""
        # Oborovo has no prior_tax_loss set (defaults to 0)
        # But construction_pl would be set for full deterministic calculation
        params = TaxParams(prior_tax_loss_keur=0)
        assert params.initial_tax_loss_keur == 0.0

    def test_tax_params_backward_compat_tuho(self):
        """Backward compat: TUHO with prior_tax_loss_keur=25000 works."""
        params = TaxParams(prior_tax_loss_keur=25000)
        assert params.initial_tax_loss_keur == 25000.0


class TestS1Integration:
    """Integration test: ConstructionPLStatement flows into TaxParams."""

    def test_full_flow_oborovo(self):
        """Full flow for Oborovo: ConstructionPLStatement → TaxParams → waterfall."""
        # Oborovo construction costs
        pl = ConstructionPLStatement(
            idc_keur=1169,
            bank_fees_keur=300,
            commitment_fees_keur=470,
            other_book_tax_difference_keur=7060,  # construction period timing
        )
        
        # Create TaxParams with construction_pl
        tax_params = TaxParams(construction_pl=pl)
        
        # Verify initial loss
        assert tax_params.initial_tax_loss_keur == 8999.0
        
        # This value flows into waterfall's prior_tax_loss_keur parameter
        # via: inputs.tax.prior_tax_loss_keur (backward compat)
        # or: inputs.tax.construction_pl.initial_tax_loss_keur (new path)

    def test_full_flow_tuho(self):
        """Full flow for TUHO: larger construction loss."""
        pl = ConstructionPLStatement(
            idc_keur=3569,  # TUHO has SHL IDC
            bank_fees_keur=500,
            commitment_fees_keur=800,
            other_book_tax_difference_keur=20000,
        )
        tax_params = TaxParams(construction_pl=pl)
        assert tax_params.initial_tax_loss_keur == 24869.0