"""Tests for financial formula correctness in the waterfall engine."""
import pytest


def test_dscr_uses_cfads_not_ebitda():
    """DSCR numerator must be CFADS (= EBITDA - tax), NOT EBITDA alone.

    The industrial standard is:
        DSCR = CFADS / Senior Debt Service
        CFADS = EBITDA - Taxes (paid before debt service)

    This test verifies the formula by checking that a tax-rate change affects
    the DSCR values — proving that taxes are subtracted before the DSCR ratio.
    """
    from app.project_factories import create_default_solar_project
    from app.ui_runner import run_demo_project
    from app.input_forms import apply_project_overrides

    proj = create_default_solar_project()
    base = run_demo_project("Solar", project_inputs_override=proj)
    assert base.result is not None, f"No result: {base.messages}"

    base_periods = base.result.periods

    # Increase tax rate by 50%
    higher_proj = apply_project_overrides(proj, {'tax': {'corporate_rate': proj.tax.corporate_rate * 1.5}})
    higher = run_demo_project("Solar", project_inputs_override=higher_proj)
    assert higher.result is not None
    higher_periods = higher.result.periods

    # DSCR must be different when tax rate changes (proving tax is in numerator)
    # Find first period where both have non-zero debt service
    dscr_pairs = []
    for bp, hp in zip(base_periods, higher_periods):
        if hasattr(bp, 'dscr') and bp.dscr and bp.dscr != float('inf'):
            dscr_pairs.append((bp.dscr, hp.dscr if hasattr(hp, 'dscr') else None))

    changed = sum(1 for b, h in dscr_pairs if h is not None and abs(b - h) > 1e-6)
    assert changed > 0, (
        "DSCR values are identical after tax-rate change — "
        "DSCR numerator may be EBITDA instead of CFADS (EBITDA - tax)"
    )


def test_taxable_income_includes_depreciation():
    """Taxable income calculation must subtract depreciation before tax.

    Standard project finance:
        Taxable Profit = EBITDA - Depreciation - Interest + ATAD addbacks
        Tax = max(0, Taxable Profit) * tax_rate

    This test verifies that when depreciation is non-zero, taxable income
    is lower than EBITDA (i.e. depreciation is subtracted).
    """
    from app.project_factories import create_default_solar_project
    from app.ui_runner import run_demo_project

    result = run_demo_project("Solar")
    assert result.result is not None, f"No result: {result.messages}"

    for p in result.result.periods:
        # EBITDA = revenue - opex
        # taxable_profit <= ebitda (depreciation reduces it, interest further reduces)
        # If depreciation exists and period is in tenor, taxable_profit should be < ebitda
        if hasattr(p, 'ebitda_keur') and p.ebitda_keur and p.ebitda_keur > 0:
            if hasattr(p, 'depreciation_keur') and p.depreciation_keur > 0:
                taxable = getattr(p, 'taxable_profit_keur', None)
                if taxable is not None:
                    # taxable profit should be less than ebitda (depreciation subtracted first)
                    assert taxable < p.ebitda_keur, (
                        f"Period {getattr(p, 'period', '?')}: "
                        f"taxable_profit ({taxable:.0f}) should be < ebitda ({p.ebitda_keur:.0f}) "
                        f"because depreciation is deducted before tax"
                    )
                    break  # Just need one valid example


def test_depreciation_affects_tax():
    """Depreciation is a tax shield — higher depreciation reduces taxable income.

    This test checks the relationship by verifying that removing depreciation
    would increase tax (we can't easily run without depreciation, so we check
    that the model's tax is consistent with depreciation being subtracted).
    """
    from app.project_factories import create_default_solar_project
    from app.ui_runner import run_demo_project

    result = run_demo_project("Solar")
    assert result.result is not None, f"No result: {result.messages}"

    # Collect periods where we can verify: tax > 0, depreciation > 0, ebitda > 0
    # This confirms depreciation is subtracted before tax
    taxable_less_than_ebitda = 0
    for p in result.result.periods:
        ebitda = getattr(p, 'ebitda_keur', None)
        dep = getattr(p, 'depreciation_keur', 0)
        taxable = getattr(p, 'taxable_profit_keur', None)
        tax = getattr(p, 'tax_keur', 0)
        interest = getattr(p, 'interest_senior_keur', 0) + getattr(p, 'interest_shl_keur', 0)

        if ebitda and ebitda > 0 and dep and dep > 0 and taxable is not None and tax is not None:
            # taxable_profit should be < EBITDA - depreciation (i.e. interest also reduced it)
            # The relationship: taxable <= ebitda - dep - interest (approximately)
            if taxable < ebitda - dep:
                taxable_less_than_ebitda += 1

    assert taxable_less_than_ebitda > 0, (
        "In all periods, taxable_profit >= ebitda - depreciation. "
        "This suggests depreciation is NOT being subtracted from taxable income."
    )