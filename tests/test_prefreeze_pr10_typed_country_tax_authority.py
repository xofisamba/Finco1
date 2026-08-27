"""PR-10 typed country-tax resolution and opening-loss authority tests."""
from __future__ import annotations

from dataclasses import replace
from datetime import date
from types import SimpleNamespace

import pytest

from app.project_factories import (
    create_default_solar_project,
    create_default_tuho_wind1_legacy_calibration,
)
from finco_core.inputs import (
    OpeningTaxLossVintageParams,
    ShlInterestDeductibilityMode,
    TaxParams,
    project_inputs_from_dict,
    project_inputs_to_dict,
)
from financial_engine.adapters.tax_inputs import build_tax_contract_from_project_inputs
from financial_engine.inputs import PeriodInterestInput, PeriodTaxAdjustmentInput
from financial_engine.tax.engine import calculate_tax
from tests.pr5_ebitda_guard import assert_only_approved_pr5_domain_diff


SOURCE_OPENING_LOSS_KEUR = 3568.6878026481627
SOURCE_POLICY_ID = "HR-approved-source-model-2026-v1"


def _project(*, rate_override: float | None = None, loss_years: int = 5):
    base = create_default_solar_project()
    tax = replace(
        base.tax,
        country_tax_policy_id=SOURCE_POLICY_ID,
        corporate_rate=0.18,
        corporate_rate_override=rate_override,
        loss_carryforward_years=loss_years,
    )
    return replace(base, info=replace(base.info, country_iso="HR"), tax=tax)


def _period(*, ebitda: float = 1000.0, depreciation: float = 100.0):
    return SimpleNamespace(
        period_index=0,
        period_start=date(2031, 1, 1),
        period_end=date(2032, 1, 1),
        is_operation=True,
        ebitda_keur=ebitda,
        tax_depreciation_keur=depreciation,
    )


def _calculate(project, *, interest=(), adjustments=()):
    contract = build_tax_contract_from_project_inputs(
        project,
        complete_financing_interest_will_be_injected=bool(interest),
    )
    contract = replace(
        contract,
        period_interest=tuple(interest),
        period_adjustments=tuple(adjustments),
    )
    return calculate_tax((_period(),), contract)


def test_explicit_country_policy_default_then_project_override():
    default_contract = build_tax_contract_from_project_inputs(_project())
    override_contract = build_tax_contract_from_project_inputs(
        _project(rate_override=0.21)
    )

    assert default_contract.policy.policy_id == SOURCE_POLICY_ID
    assert default_contract.policy.corporate_rate == pytest.approx(0.18)
    assert override_contract.policy.corporate_rate == pytest.approx(0.21)


def test_country_metadata_does_not_activate_illustrative_registry():
    base = create_default_solar_project()
    country_only = replace(base, info=replace(base.info, country_iso="HR"))

    contract = build_tax_contract_from_project_inputs(country_only)

    assert contract.policy.policy_id == "clean-project-tax-v1"
    assert contract.policy.corporate_rate == pytest.approx(0.25)


def test_policy_country_mismatch_and_legacy_rate_conflict_fail_closed():
    base = create_default_solar_project()
    mismatch = replace(
        base,
        tax=replace(base.tax, country_tax_policy_id=SOURCE_POLICY_ID),
    )
    with pytest.raises(ValueError, match="COUNTRY_TAX_POLICY_COUNTRY_MISMATCH"):
        build_tax_contract_from_project_inputs(mismatch)

    conflict = replace(_project(), tax=replace(_project().tax, corporate_rate=0.17))
    with pytest.raises(ValueError, match="COUNTRY_TAX_LEGACY_FIELD_CONFLICT"):
        build_tax_contract_from_project_inputs(conflict)


def test_opening_vintages_are_serialized_and_mapped_without_scalar_authority():
    vintage = OpeningTaxLossVintageParams(
        origin_tax_year=2029,
        opening_amount_keur=SOURCE_OPENING_LOSS_KEUR,
        source_label="TUHO P&L!G35 -> H36",
    )
    project = _project()
    project = replace(
        project,
        tax=replace(project.tax, opening_tax_loss_vintages=(vintage,)),
    )

    restored = project_inputs_from_dict(project_inputs_to_dict(project))
    contract = build_tax_contract_from_project_inputs(restored)

    assert restored.tax.opening_tax_loss_vintages == (vintage,)
    assert contract.opening_loss_vintages[0].origin_tax_year == 2029
    assert contract.opening_loss_vintages[0].amount_keur == pytest.approx(
        SOURCE_OPENING_LOSS_KEUR
    )


def test_nonzero_legacy_scalar_without_vintage_evidence_fails_closed():
    project = _project()
    project = replace(project, tax=replace(project.tax, prior_tax_loss_keur=5000.0))

    with pytest.raises(NotImplementedError, match="non-zero legacy"):
        build_tax_contract_from_project_inputs(project)


def test_vintage_expiry_changes_with_explicit_lcf_policy():
    vintage = OpeningTaxLossVintageParams(2025, 500.0, "synthetic opening loss")
    short = _project(loss_years=5)
    long = _project(loss_years=10)
    short = replace(short, tax=replace(short.tax, opening_tax_loss_vintages=(vintage,)))
    long = replace(long, tax=replace(long.tax, opening_tax_loss_vintages=(vintage,)))

    short_result = _calculate(short)
    long_result = _calculate(long)

    assert short_result.annual_results[0].loss_expired_keur == pytest.approx(500.0)
    assert long_result.annual_results[0].loss_used_keur == pytest.approx(500.0)
    assert long_result.annual_results[0].current_tax_liability_keur < (
        short_result.annual_results[0].current_tax_liability_keur
    )


def test_larger_opening_loss_reduces_early_cit_and_reconciles_closing_ledger():
    project = _project(loss_years=10)
    small = replace(
        project,
        tax=replace(
            project.tax,
            opening_tax_loss_vintages=(OpeningTaxLossVintageParams(2029, 100.0),),
        ),
    )
    large = replace(
        project,
        tax=replace(
            project.tax,
            opening_tax_loss_vintages=(OpeningTaxLossVintageParams(2029, 200.0),),
        ),
    )

    small_annual = _calculate(small).annual_results[0]
    large_annual = _calculate(large).annual_results[0]

    assert large_annual.current_tax_liability_keur < small_annual.current_tax_liability_keur
    ledger = large_annual.ledger_entry
    assert (
        ledger.opening_loss_pre_expiry_keur
        + ledger.loss_generated_keur
        - ledger.loss_used_keur
        - ledger.loss_expired_keur
    ) == pytest.approx(ledger.closing_loss_keur)


def test_different_typed_interest_limit_changes_deductible_interest():
    unrestricted = _project()
    limited = replace(
        unrestricted,
        tax=replace(
            unrestricted.tax,
            atad_enabled=True,
            atad_ebitda_limit=0.30,
            atad_min_interest_keur=0.0,
        ),
    )
    interest = (PeriodInterestInput(0, senior_interest_keur=500.0),)

    unrestricted_annual = _calculate(unrestricted, interest=interest).annual_results[0]
    limited_annual = _calculate(limited, interest=interest).annual_results[0]

    assert unrestricted_annual.deductible_interest_keur == pytest.approx(500.0)
    assert limited_annual.deductible_interest_keur == pytest.approx(300.0)
    assert limited_annual.disallowed_interest_keur == pytest.approx(200.0)


def test_causal_rate_depreciation_interest_and_reintegration_grid():
    base = _calculate(_project())
    higher_rate = _calculate(_project(rate_override=0.19))
    higher_dep_contract = build_tax_contract_from_project_inputs(_project())
    higher_dep = calculate_tax(
        (_period(depreciation=200.0),), higher_dep_contract
    )
    deductible_interest = _calculate(
        _project(), interest=(PeriodInterestInput(0, senior_interest_keur=100.0),)
    )
    reintegrated = _calculate(
        _project(), adjustments=(PeriodTaxAdjustmentInput(0, 50.0),)
    )

    base_annual = base.annual_results[0]
    assert higher_rate.annual_results[0].current_tax_liability_keur > (
        base_annual.current_tax_liability_keur
    )
    assert higher_dep.annual_results[0].taxable_income_before_lcf_keur == pytest.approx(
        base_annual.taxable_income_before_lcf_keur - 100.0
    )
    assert deductible_interest.annual_results[0].taxable_income_before_lcf_keur == pytest.approx(
        base_annual.taxable_income_before_lcf_keur - 100.0
    )
    assert reintegrated.annual_results[0].taxable_income_before_lcf_keur == pytest.approx(
        base_annual.taxable_income_before_lcf_keur + 50.0
    )


def test_fully_non_deductible_shl_does_not_reduce_taxable_income():
    project = _project()
    project = replace(
        project,
        tax=replace(
            project.tax,
            shl_interest_deductibility=(
                ShlInterestDeductibilityMode.FULLY_NON_DEDUCTIBLE
            ),
        ),
    )
    result = _calculate(
        project,
        interest=(PeriodInterestInput(0, shl_interest_keur=100.0),),
    )

    assert result.annual_results[0].deductible_interest_keur == pytest.approx(0.0)
    assert result.annual_results[0].taxable_income_before_lcf_keur == pytest.approx(900.0)


def test_identity_change_with_same_typed_policy_has_zero_financial_effect():
    project = _project()
    renamed = replace(
        project,
        info=replace(project.info, name="Unrelated Name", code="UNRELATED-CODE"),
    )

    assert _calculate(project) == _calculate(renamed)


def test_tuho_source_variant_maps_exact_vintage_then_stops_at_g2c_boundary():
    """Correction G: TUHO maps vintage exactly, but MUST fail closed at runtime.

    TUHO has thin_cap_enabled=True + atad_enabled=True + SUBJECT_TO_LIMITATIONS.
    The runtime capability gate must raise SHL_THIN_CAP_RUNTIME_NOT_IMPLEMENTED
    before any tax output is produced. This is a capability-driven check — NOT an
    identity check. The thin-cap formula is not implemented.
    """
    tuho = create_default_tuho_wind1_legacy_calibration()
    assert tuho.tax.prior_tax_loss_keur == pytest.approx(25_000.0)

    source_variant = replace(
        tuho,
        tax=replace(
            tuho.tax,
            country_tax_policy_id=SOURCE_POLICY_ID,
            prior_tax_loss_keur=0.0,
            opening_tax_loss_vintages=(
                OpeningTaxLossVintageParams(
                    2029,
                    SOURCE_OPENING_LOSS_KEUR,
                    "20260330_TUHO_BP.xlsm P&L!G35 -> H36",
                ),
            ),
            clean_cash_tax_timing_enabled=True,
        ),
    )
    contract = build_tax_contract_from_project_inputs(
        source_variant,
        complete_financing_interest_will_be_injected=True,
    )

    assert contract.opening_loss_vintages[0].amount_keur == pytest.approx(
        SOURCE_OPENING_LOSS_KEUR
    )
    # Correction G: TUHO has thin_cap_enabled=True. The runtime gate must fire.
    # shl_tax_deductible_fraction() must raise SHL_THIN_CAP_RUNTIME_NOT_IMPLEMENTED
    # — no fraction, no partial result.
    assert contract.policy.thin_cap_enabled is True, (
        "TUHO source variant must carry thin_cap_enabled=True (source metadata)"
    )
    with pytest.raises(NotImplementedError, match="SHL_THIN_CAP_RUNTIME_NOT_IMPLEMENTED"):
        contract.policy.shl_tax_deductible_fraction()


def test_tuho_runtime_gate_is_capability_driven_not_identity():
    """Correction G: TUHO runtime failure is capability-driven, NOT identity-based.

    Renaming the project (different name/code) produces the SAME error because
    the gate fires on thin_cap_enabled=True, not on project identity.
    """
    tuho = create_default_tuho_wind1_legacy_calibration()
    renamed = replace(
        tuho,
        info=replace(tuho.info, name="Unrelated Wind Farm", code="UNRELATED-CODE"),
        tax=replace(
            tuho.tax,
            clean_cash_tax_timing_enabled=True,
            prior_tax_loss_keur=0.0,  # clear legacy scalar so adapter accepts
        ),
    )
    contract = build_tax_contract_from_project_inputs(
        renamed,
        complete_financing_interest_will_be_injected=True,
    )
    # Same error for renamed project — identity does not matter
    assert contract.policy.thin_cap_enabled is True
    with pytest.raises(NotImplementedError, match="SHL_THIN_CAP_RUNTIME_NOT_IMPLEMENTED"):
        contract.policy.shl_tax_deductible_fraction()


def test_generic_atad_only_stl_executes_without_error():
    """Correction G: ATAD-only STL project (thin_cap_enabled=False) executes cleanly.

    A purpose-built project with thin_cap_enabled=False, atad_enabled=True,
    SUBJECT_TO_LIMITATIONS returns fraction=1.0 from shl_tax_deductible_fraction().
    """
    from finco_core.inputs import TaxParams, ShlInterestDeductibilityMode
    from financial_engine.policies.tax import (
        CashTaxTiming,
        ShlInterestDeductibilityMode as PolicyMode,
        TaxPolicy,
    )

    policy = TaxPolicy(
        policy_id="generic-atad-only-stl",
        policy_version="1.0.0",
        corporate_rate=0.20,
        periods_per_tax_year=2,
        loss_carryforward_years=5,
        atad_enabled=True,
        atad_ebitda_limit=0.30,
        atad_de_minimis_threshold_keur_annual=3000.0,
        cash_tax_timing=CashTaxTiming.TAX_YEAR_LAST_PERIOD,
        shl_interest_tax_treatment_enabled=True,
        shl_interest_deductibility=PolicyMode.SUBJECT_TO_LIMITATIONS,
        thin_cap_enabled=False,  # ATAD-only: no thin-cap
    )
    # Must not raise; thin_cap_enabled=False + atad_enabled=True → ATAD path
    frac = policy.shl_tax_deductible_fraction()
    assert frac == pytest.approx(1.0), (
        f"ATAD-only STL: fraction must be 1.0, got {frac}"
    )


def test_input_validation_rejects_competing_opening_loss_authorities():
    with pytest.raises(ValueError, match="conflicting authorities"):
        TaxParams(
            prior_tax_loss_keur=1.0,
            opening_tax_loss_vintages=(
                OpeningTaxLossVintageParams(2029, 1.0),
            ),
        )


def test_pr5_guard_scopes_formula_lock_to_pr5_sizing_files():
    unrelated_domain_facade = "\n".join(
        (
            "diff --git a/domain/inputs.py b/domain/inputs.py",
            "--- a/domain/inputs.py",
            "+++ b/domain/inputs.py",
            "+    OpeningTaxLossVintageParams,",
        )
    )
    assert_only_approved_pr5_domain_diff(unrelated_domain_facade)

    sizing_change = "\n".join(
        (
            "diff --git a/domain/senior_debt_sizing/engine.py "
            "b/domain/senior_debt_sizing/engine.py",
            "--- a/domain/senior_debt_sizing/engine.py",
            "+++ b/domain/senior_debt_sizing/engine.py",
            "+                capacity = cfads / dscr",
        )
    )
    with pytest.raises(AssertionError, match="beyond the source-approved"):
        assert_only_approved_pr5_domain_diff(sizing_change)


# ---------------------------------------------------------------------------
# PR-10 Correction A: Adversarial test matrix (A–L)
# ---------------------------------------------------------------------------

class TestCorrectionAAdversarialMatrix:
    """Fail-closed authority tests for PR-10 Correction A.

    Each test corresponds to one lettered item in the adversarial matrix
    specification.
    """

    # ── A. Future opening vintage raises immediately ─────────────────────
    def test_A_future_vintage_raises_tax_opening_loss_future_vintage(self):
        """A vintage whose origin is beyond the first modelled year must raise."""
        from financial_engine.inputs import OpeningTaxLossVintageInput
        from financial_engine.tax.loss_ledger import run_annual_fifo_ledger

        future_vintage = OpeningTaxLossVintageInput(
            origin_tax_year=2040,
            amount_keur=1000.0,
            source_label="future",
        )
        with pytest.raises(ValueError, match="TAX_OPENING_LOSS_FUTURE_VINTAGE"):
            run_annual_fifo_ledger(
                taxable_income_before_lcf=(5000.0,),
                tax_year_indices=(2030,),
                opening_inputs=(future_vintage,),
                loss_carryforward_years=5,
            )

    def test_A_same_year_vintage_is_allowed(self):
        """A vintage with origin_tax_year == first_tax_year is not future: allowed."""
        from financial_engine.inputs import OpeningTaxLossVintageInput
        from financial_engine.tax.loss_ledger import run_annual_fifo_ledger

        same_year = OpeningTaxLossVintageInput(
            origin_tax_year=2030,
            amount_keur=500.0,
            source_label="same_year",
        )
        entries = run_annual_fifo_ledger(
            taxable_income_before_lcf=(5000.0,),
            tax_year_indices=(2030,),
            opening_inputs=(same_year,),
            loss_carryforward_years=5,
        )
        assert len(entries) == 1
        assert entries[0].loss_used_keur == pytest.approx(500.0)

    # ── B. FIFO order: oldest consumed first regardless of tuple order ───
    def test_B_newest_first_tuple_still_consumes_oldest_first(self):
        """Supplying vintages newest-first must still consume the oldest first."""
        from financial_engine.inputs import OpeningTaxLossVintageInput
        from financial_engine.tax.loss_ledger import run_annual_fifo_ledger

        old_vintage = OpeningTaxLossVintageInput(2020, 300.0, "old")
        new_vintage = OpeningTaxLossVintageInput(2025, 400.0, "new")

        # Supply newest first (anti-FIFO order)
        entries = run_annual_fifo_ledger(
            taxable_income_before_lcf=(200.0,),
            tax_year_indices=(2030,),
            opening_inputs=(new_vintage, old_vintage),  # reversed
            loss_carryforward_years=15,
        )
        entry = entries[0]
        # Only 200 kEUR income to shelter → should come from origin=2020 vintage
        old_used = sum(
            v.used_keur for v in entry.used_vintages if v.origin_tax_year == 2020
        )
        new_used = sum(
            v.used_keur for v in entry.used_vintages if v.origin_tax_year == 2025
        )
        assert old_used == pytest.approx(200.0), "oldest vintage must be consumed first"
        assert new_used == pytest.approx(0.0), "newer vintage untouched"

    # ── C. Financial result invariant to input tuple order ───────────────
    def test_C_result_independent_of_tuple_order(self):
        """Financial outputs must be identical regardless of caller tuple order."""
        from financial_engine.inputs import OpeningTaxLossVintageInput
        from financial_engine.tax.loss_ledger import run_annual_fifo_ledger

        v2020 = OpeningTaxLossVintageInput(2020, 300.0, "old")
        v2023 = OpeningTaxLossVintageInput(2023, 200.0, "mid")
        v2025 = OpeningTaxLossVintageInput(2025, 100.0, "new")

        incomes = (150.0, 250.0, 500.0)
        years = (2030, 2031, 2032)

        entries_fwd = run_annual_fifo_ledger(
            taxable_income_before_lcf=incomes,
            tax_year_indices=years,
            opening_inputs=(v2020, v2023, v2025),
            loss_carryforward_years=15,
        )
        entries_rev = run_annual_fifo_ledger(
            taxable_income_before_lcf=incomes,
            tax_year_indices=years,
            opening_inputs=(v2025, v2023, v2020),  # reversed
            loss_carryforward_years=15,
        )

        for ef, er in zip(entries_fwd, entries_rev):
            assert ef.loss_used_keur == pytest.approx(er.loss_used_keur)
            assert ef.closing_loss_keur == pytest.approx(er.closing_loss_keur)
            assert ef.taxable_income_after_lcf_keur == pytest.approx(
                er.taxable_income_after_lcf_keur
            )

    # ── D. Same-year duplicates: deterministic stable ordering ───────────
    def test_D_same_year_duplicates_consume_in_input_order(self):
        """Two vintages from the same origin year retain relative input order (stable sort)."""
        from financial_engine.inputs import OpeningTaxLossVintageInput
        from financial_engine.tax.loss_ledger import run_annual_fifo_ledger

        v_a = OpeningTaxLossVintageInput(2020, 100.0, "first")
        v_b = OpeningTaxLossVintageInput(2020, 400.0, "second")

        entries = run_annual_fifo_ledger(
            taxable_income_before_lcf=(50.0,),
            tax_year_indices=(2030,),
            opening_inputs=(v_a, v_b),
            loss_carryforward_years=15,
        )
        entry = entries[0]
        # v_a (first, 100) should be consumed before v_b (second, 400)
        # Only 50 available → entirely from v_a
        used_labels = [v.source_label for v in entry.used_vintages if v.used_keur > 0]
        assert "first" in used_labels
        assert "second" not in used_labels

    # ── E. Exact expiry boundary ─────────────────────────────────────────
    def test_E_vintage_usable_in_boundary_year_expired_one_year_later(self):
        """With LCF=5, origin=2029: last_usable=2034 (active), expired at 2035."""
        from financial_engine.inputs import OpeningTaxLossVintageInput
        from financial_engine.tax.loss_ledger import run_annual_fifo_ledger

        v = OpeningTaxLossVintageInput(2029, 500.0, "boundary")

        # 2034 = last usable year → still available (not expired)
        entries_ok = run_annual_fifo_ledger(
            taxable_income_before_lcf=(200.0,),
            tax_year_indices=(2034,),
            opening_inputs=(v,),
            loss_carryforward_years=5,
        )
        assert entries_ok[0].loss_used_keur == pytest.approx(200.0)
        assert entries_ok[0].loss_expired_keur == pytest.approx(0.0)

        # 2035 = one year beyond → expired before use
        entries_exp = run_annual_fifo_ledger(
            taxable_income_before_lcf=(200.0,),
            tax_year_indices=(2035,),
            opening_inputs=(v,),
            loss_carryforward_years=5,
        )
        assert entries_exp[0].loss_expired_keur == pytest.approx(500.0)
        assert entries_exp[0].loss_used_keur == pytest.approx(0.0)

    # ── F. OpeningTaxLossVintageInput amount validation ──────────────────
    @pytest.mark.parametrize("bad_amount,match", [
        (True,    "must be numeric, not bool"),
        ("500",   "must be a real numeric"),
        (float("nan"),  "must be finite"),
        (float("inf"),  "must be finite"),
        (float("-inf"), "must be finite"),
        (-1.0,    "must be non-negative"),
        (-0.001,  "must be non-negative"),
    ])
    def test_F_opening_vintage_input_rejects_invalid_amount(self, bad_amount, match):
        from financial_engine.inputs import OpeningTaxLossVintageInput

        with pytest.raises(ValueError, match=match):
            OpeningTaxLossVintageInput(origin_tax_year=2020, amount_keur=bad_amount)

    def test_F_zero_amount_is_accepted(self):
        from financial_engine.inputs import OpeningTaxLossVintageInput

        v = OpeningTaxLossVintageInput(origin_tax_year=2020, amount_keur=0.0)
        assert v.amount_keur == 0.0

    def test_F_bool_origin_year_rejected(self):
        from financial_engine.inputs import OpeningTaxLossVintageInput

        with pytest.raises(ValueError, match="must be an integer"):
            OpeningTaxLossVintageInput(origin_tax_year=True, amount_keur=100.0)

    def test_F_non_string_label_rejected(self):
        from financial_engine.inputs import OpeningTaxLossVintageInput

        with pytest.raises(ValueError, match="source_label must be a string"):
            OpeningTaxLossVintageInput(origin_tax_year=2020, amount_keur=100.0,
                                       source_label=42)

    # ── G. OpeningTaxLossVintageParams amount validation ─────────────────
    @pytest.mark.parametrize("bad_amount,match", [
        (True,        "must be numeric"),
        ("100",       "must be a real numeric"),
        (float("nan"), "must be finite"),
        (float("inf"), "must be finite"),
        (-1.0,         "non-negative"),
    ])
    def test_G_opening_vintage_params_rejects_invalid_amount(self, bad_amount, match):
        with pytest.raises((ValueError, TypeError), match=match):
            OpeningTaxLossVintageParams(origin_tax_year=2020, opening_amount_keur=bad_amount)

    def test_G_valid_params_accepted(self):
        v = OpeningTaxLossVintageParams(origin_tax_year=2020, opening_amount_keur=1000.0)
        assert v.opening_amount_keur == pytest.approx(1000.0)

    # ── H. corporate_rate_override invalid types ──────────────────────────
    @pytest.mark.parametrize("bad_rate,match", [
        (True,         "corporate_rate_override"),
        ("0.18",       "corporate_rate_override"),
        (float("nan"), "must be finite"),
        (float("inf"), "must be finite"),
    ])
    def test_H_corporate_rate_override_rejects_invalid(self, bad_rate, match):
        with pytest.raises(ValueError, match=match):
            TaxParams(corporate_rate_override=bad_rate)

    # ── I. corporate_rate_override boundary values accepted ──────────────
    @pytest.mark.parametrize("valid_rate", [0.0, 1.0, 0.18, 0.25])
    def test_I_corporate_rate_override_boundary_accepted(self, valid_rate):
        t = TaxParams(
            country_tax_policy_id=SOURCE_POLICY_ID,
            corporate_rate_override=valid_rate,
        )
        assert t.corporate_rate_override == pytest.approx(valid_rate)

    def test_I_corporate_rate_override_none_accepted(self):
        t = TaxParams(corporate_rate_override=None)
        assert t.corporate_rate_override is None

    # ── J. country_tax_policy_id validation ──────────────────────────────
    def test_J_none_policy_id_accepted(self):
        t = TaxParams(country_tax_policy_id=None)
        assert t.country_tax_policy_id is None

    def test_J_valid_string_accepted(self):
        t = TaxParams(country_tax_policy_id="HR-approved-source-model-2026-v1")
        assert t.country_tax_policy_id == "HR-approved-source-model-2026-v1"

    @pytest.mark.parametrize("bad_id,match", [
        ("",    "must be non-empty"),
        ("   ", "must be non-empty"),
        (True,  "must be a string"),
        (42,    "must be a string"),
        ([],    "must be a string"),
    ])
    def test_J_invalid_policy_id_rejected(self, bad_id, match):
        with pytest.raises(ValueError, match=match):
            TaxParams(country_tax_policy_id=bad_id)

    # ── K. Dual loss authority: non-zero legacy + vintage → fail ─────────
    def test_K_nonzero_legacy_plus_vintage_fails_closed(self):
        with pytest.raises(ValueError, match="conflicting authorities"):
            TaxParams(
                prior_tax_loss_keur=100.0,
                opening_tax_loss_vintages=(
                    OpeningTaxLossVintageParams(2025, 500.0),
                ),
            )

    def test_K_zero_legacy_with_vintage_is_allowed(self):
        """Zero legacy scalar is neutral — not a competing authority."""
        t = TaxParams(
            prior_tax_loss_keur=0.0,
            opening_tax_loss_vintages=(
                OpeningTaxLossVintageParams(2025, 500.0),
            ),
        )
        assert len(t.opening_tax_loss_vintages) == 1

    # ── L. TUHO source: exact vintage maps, stops at G2C boundary ────────
    def _tuho_source_variant(self):
        """Return TUHO source variant with vintage-based opening loss."""
        tuho = create_default_tuho_wind1_legacy_calibration()
        return replace(
            tuho,
            tax=replace(
                tuho.tax,
                country_tax_policy_id=SOURCE_POLICY_ID,
                prior_tax_loss_keur=0.0,
                opening_tax_loss_vintages=(
                    OpeningTaxLossVintageParams(
                        2029,
                        SOURCE_OPENING_LOSS_KEUR,
                        "20260330_TUHO_BP.xlsm P&L!G35 -> H36",
                    ),
                ),
                clean_cash_tax_timing_enabled=True,
            ),
        )

    def test_L_tuho_vintage_maps_exact_amount(self):
        """TUHO opening vintage maps SOURCE_OPENING_LOSS_KEUR exactly via adapter."""
        source_variant = self._tuho_source_variant()
        contract = build_tax_contract_from_project_inputs(
            source_variant,
            complete_financing_interest_will_be_injected=True,
        )
        assert contract.opening_loss_vintages[0].amount_keur == pytest.approx(
            SOURCE_OPENING_LOSS_KEUR
        )

    def test_L_tuho_stl_runtime_blocked_by_thin_cap(self):
        """TUHO SHL policy (SUBJECT_TO_LIMITATIONS) is blocked at runtime.

        Correction G: TUHO has thin_cap_enabled=True. The runtime capability gate
        fires in shl_tax_deductible_fraction() before any tax output is produced.
        Error code SHL_THIN_CAP_RUNTIME_NOT_IMPLEMENTED — capability-driven, not identity.
        """
        source_variant = self._tuho_source_variant()
        contract = build_tax_contract_from_project_inputs(
            source_variant,
            complete_financing_interest_will_be_injected=True,
        )
        # thin_cap_enabled must be forwarded from TaxParams
        assert contract.policy.thin_cap_enabled is True
        # Runtime gate must fire — no fraction returned
        with pytest.raises(NotImplementedError, match="SHL_THIN_CAP_RUNTIME_NOT_IMPLEMENTED"):
            contract.policy.shl_tax_deductible_fraction()


# ---------------------------------------------------------------------------
# PR-10 Correction B: numbers.Real contract proof
# ---------------------------------------------------------------------------

class TestCorrectionBRealNumericContract:
    """Prove numbers.Real is used — not the narrower (int, float) pair.

    Tests for OpeningTaxLossVintageInput.amount_keur,
    OpeningTaxLossVintageParams.opening_amount_keur, and
    TaxParams.corporate_rate_override.
    """

    # ── fractions.Fraction is a numbers.Real and must be accepted ────────
    def test_fraction_amount_accepted_in_vintage_input(self):
        from fractions import Fraction
        from financial_engine.inputs import OpeningTaxLossVintageInput

        v = OpeningTaxLossVintageInput(origin_tax_year=2020, amount_keur=Fraction(1, 2))
        assert float(v.amount_keur) == pytest.approx(0.5)

    def test_fraction_zero_accepted_in_vintage_input(self):
        from fractions import Fraction
        from financial_engine.inputs import OpeningTaxLossVintageInput

        v = OpeningTaxLossVintageInput(origin_tax_year=2020, amount_keur=Fraction(0))
        assert v.amount_keur == 0

    def test_fraction_amount_accepted_in_vintage_params(self):
        from fractions import Fraction

        v = OpeningTaxLossVintageParams(
            origin_tax_year=2020, opening_amount_keur=Fraction(3, 4)
        )
        assert float(v.opening_amount_keur) == pytest.approx(0.75)

    def test_fraction_rate_accepted_in_tax_params(self):
        from fractions import Fraction

        t = TaxParams(
            country_tax_policy_id=SOURCE_POLICY_ID,
            corporate_rate_override=Fraction(18, 100),
        )
        assert float(t.corporate_rate_override) == pytest.approx(0.18)

    def test_fraction_rate_zero_accepted(self):
        from fractions import Fraction

        t = TaxParams(
            country_tax_policy_id=SOURCE_POLICY_ID,
            corporate_rate_override=Fraction(0),
        )
        assert t.corporate_rate_override == 0

    def test_fraction_rate_one_accepted(self):
        from fractions import Fraction

        t = TaxParams(
            country_tax_policy_id=SOURCE_POLICY_ID,
            corporate_rate_override=Fraction(1),
        )
        assert t.corporate_rate_override == 1

    # ── bool still rejected (bool is a subclass of int, which is Real) ───
    def test_bool_rejected_vintage_input(self):
        from financial_engine.inputs import OpeningTaxLossVintageInput
        with pytest.raises(ValueError, match="not bool"):
            OpeningTaxLossVintageInput(origin_tax_year=2020, amount_keur=True)

    def test_bool_rejected_vintage_params(self):
        with pytest.raises(ValueError, match="not bool"):
            OpeningTaxLossVintageParams(origin_tax_year=2020, opening_amount_keur=False)

    def test_bool_rejected_rate_override(self):
        with pytest.raises(ValueError, match="not bool"):
            TaxParams(country_tax_policy_id=SOURCE_POLICY_ID, corporate_rate_override=True)

    # ── numeric strings rejected ──────────────────────────────────────────
    def test_numeric_string_rejected_vintage_input(self):
        from financial_engine.inputs import OpeningTaxLossVintageInput
        with pytest.raises(ValueError, match="real numeric"):
            OpeningTaxLossVintageInput(origin_tax_year=2020, amount_keur="500.0")

    def test_numeric_string_rejected_vintage_params(self):
        with pytest.raises(ValueError, match="real numeric"):
            OpeningTaxLossVintageParams(origin_tax_year=2020, opening_amount_keur="500")

    def test_numeric_string_rejected_rate_override(self):
        with pytest.raises(ValueError, match="real numeric"):
            TaxParams(country_tax_policy_id=SOURCE_POLICY_ID, corporate_rate_override="0.18")

    # ── complex values rejected ───────────────────────────────────────────
    def test_complex_rejected_vintage_input(self):
        from financial_engine.inputs import OpeningTaxLossVintageInput
        with pytest.raises(ValueError, match="real numeric"):
            OpeningTaxLossVintageInput(origin_tax_year=2020, amount_keur=complex(1, 0))

    def test_complex_rejected_vintage_params(self):
        with pytest.raises(ValueError, match="real numeric"):
            OpeningTaxLossVintageParams(origin_tax_year=2020, opening_amount_keur=complex(1, 0))

    def test_complex_rejected_rate_override(self):
        with pytest.raises(ValueError, match="real numeric"):
            TaxParams(country_tax_policy_id=SOURCE_POLICY_ID, corporate_rate_override=complex(0.18, 0))

    # ── NaN / ±Inf rejected ───────────────────────────────────────────────
    def test_nan_rejected_vintage_input(self):
        from financial_engine.inputs import OpeningTaxLossVintageInput
        with pytest.raises(ValueError, match="must be finite"):
            OpeningTaxLossVintageInput(origin_tax_year=2020, amount_keur=float("nan"))

    def test_inf_rejected_vintage_params(self):
        with pytest.raises(ValueError, match="non-negative"):
            OpeningTaxLossVintageParams(origin_tax_year=2020, opening_amount_keur=float("inf"))

    def test_nan_rejected_rate_override(self):
        with pytest.raises(ValueError, match="must be finite"):
            TaxParams(country_tax_policy_id=SOURCE_POLICY_ID, corporate_rate_override=float("nan"))

    # ── exact zero preserved ──────────────────────────────────────────────
    def test_zero_preserved_vintage_input(self):
        from financial_engine.inputs import OpeningTaxLossVintageInput
        v = OpeningTaxLossVintageInput(origin_tax_year=2020, amount_keur=0)
        assert v.amount_keur == 0

    def test_zero_preserved_vintage_params(self):
        v = OpeningTaxLossVintageParams(origin_tax_year=2020, opening_amount_keur=0.0)
        assert v.opening_amount_keur == 0.0

    # ── corporate_rate 0 and 1 boundaries ────────────────────────────────
    def test_rate_zero_accepted(self):
        t = TaxParams(country_tax_policy_id=SOURCE_POLICY_ID, corporate_rate_override=0.0)
        assert t.corporate_rate_override == pytest.approx(0.0)

    def test_rate_one_accepted(self):
        t = TaxParams(country_tax_policy_id=SOURCE_POLICY_ID, corporate_rate_override=1.0)
        assert t.corporate_rate_override == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# PR-10 Correction B: Production-adapter / E2E future-vintage proof
# ---------------------------------------------------------------------------

class TestCorrectionBProductionAdapterFutureVintage:
    """Future-vintage rejection must propagate through the full production path.

    Direct ledger rejection (Correction A) is a unit-level guard.
    This proves the guard fires through build_tax_contract_from_project_inputs
    and calculate_tax — the production-facing path.
    """

    def _project_with_vintage(self, origin_year: int, first_tax_year: int) -> object:
        """Project with one explicit opening vintage; first operating year set via period."""
        from dataclasses import replace as _replace
        project = _replace(
            _project(),
            tax=_replace(
                _project().tax,
                opening_tax_loss_vintages=(
                    OpeningTaxLossVintageParams(
                        origin_tax_year=origin_year,
                        opening_amount_keur=1000.0,
                        source_label=f"test_vintage_{origin_year}",
                    ),
                ),
                clean_cash_tax_timing_enabled=True,
            ),
        )
        return project, first_tax_year

    def test_e2e_future_vintage_rejected_via_calculate_tax(self):
        """Future vintage (origin 2040) must be rejected when first tax year is 2031."""
        from dataclasses import replace as _replace
        from financial_engine.tax.engine import calculate_tax
        from types import SimpleNamespace
        from datetime import date

        # Build project with vintage origin_year=2040, first represented tax year=2031
        project = _replace(
            _project(),
            tax=_replace(
                _project().tax,
                opening_tax_loss_vintages=(
                    OpeningTaxLossVintageParams(
                        origin_tax_year=2040,
                        opening_amount_keur=1000.0,
                        source_label="future_vintage_e2e",
                    ),
                ),
                clean_cash_tax_timing_enabled=True,
            ),
        )
        contract = build_tax_contract_from_project_inputs(
            project, complete_financing_interest_will_be_injected=False,
        )
        # Period whose tax year is 2031 — before the vintage origin 2040
        period_2031 = SimpleNamespace(
            period_index=0,
            period_start=date(2031, 1, 1),
            period_end=date(2032, 1, 1),
            is_operation=True,
            ebitda_keur=5000.0,
            tax_depreciation_keur=100.0,
        )
        with pytest.raises(ValueError, match="TAX_OPENING_LOSS_FUTURE_VINTAGE"):
            calculate_tax((period_2031,), contract)

    def test_e2e_future_vintage_does_not_shelter_income(self):
        """Future vintage must not shelter income — rejection is raised, not silently skipped."""
        from dataclasses import replace as _replace
        from financial_engine.tax.engine import calculate_tax
        from types import SimpleNamespace
        from datetime import date

        project = _replace(
            _project(),
            tax=_replace(
                _project().tax,
                opening_tax_loss_vintages=(
                    OpeningTaxLossVintageParams(
                        origin_tax_year=2040,
                        opening_amount_keur=1000.0,
                        source_label="future_shelter_test",
                    ),
                ),
                clean_cash_tax_timing_enabled=True,
            ),
        )
        contract = build_tax_contract_from_project_inputs(
            project, complete_financing_interest_will_be_injected=False,
        )
        period_2031 = SimpleNamespace(
            period_index=0,
            period_start=date(2031, 1, 1),
            period_end=date(2032, 1, 1),
            is_operation=True,
            ebitda_keur=1000.0,
            tax_depreciation_keur=0.0,
        )
        # Must raise — not produce a result with sheltered income
        raised = False
        try:
            calculate_tax((period_2031,), contract)
        except ValueError as exc:
            raised = True
            assert "TAX_OPENING_LOSS_FUTURE_VINTAGE" in str(exc)
        assert raised, "Future vintage must raise, not silently shelter or ignore"

    def test_e2e_same_year_vintage_accepted(self):
        """Vintage with origin == first_tax_year must NOT be rejected (same-year E2E)."""
        from dataclasses import replace as _replace
        from financial_engine.tax.engine import calculate_tax
        from types import SimpleNamespace
        from datetime import date

        project = _replace(
            _project(),
            tax=_replace(
                _project().tax,
                opening_tax_loss_vintages=(
                    OpeningTaxLossVintageParams(
                        origin_tax_year=2031,
                        opening_amount_keur=500.0,
                        source_label="same_year_e2e",
                    ),
                ),
                clean_cash_tax_timing_enabled=True,
            ),
        )
        contract = build_tax_contract_from_project_inputs(
            project, complete_financing_interest_will_be_injected=False,
        )
        period_2031 = SimpleNamespace(
            period_index=0,
            period_start=date(2031, 1, 1),
            period_end=date(2032, 1, 1),
            is_operation=True,
            ebitda_keur=5000.0,
            tax_depreciation_keur=100.0,
        )
        result = calculate_tax((period_2031,), contract)
        # Same-year vintage must be used (not rejected)
        assert result.annual_results[0].loss_used_keur == pytest.approx(500.0)

    def test_e2e_past_vintage_accepted_and_used(self):
        """Vintage clearly in the past (origin 2025, first_year 2031) must be accepted and used."""
        from dataclasses import replace as _replace
        from financial_engine.tax.engine import calculate_tax
        from types import SimpleNamespace
        from datetime import date

        project = _replace(
            _project(loss_years=10),
            tax=_replace(
                _project(loss_years=10).tax,
                opening_tax_loss_vintages=(
                    OpeningTaxLossVintageParams(
                        origin_tax_year=2025,
                        opening_amount_keur=300.0,
                        source_label="past_vintage_e2e",
                    ),
                ),
                clean_cash_tax_timing_enabled=True,
            ),
        )
        contract = build_tax_contract_from_project_inputs(
            project, complete_financing_interest_will_be_injected=False,
        )
        period_2031 = SimpleNamespace(
            period_index=0,
            period_start=date(2031, 1, 1),
            period_end=date(2032, 1, 1),
            is_operation=True,
            ebitda_keur=5000.0,
            tax_depreciation_keur=100.0,
        )
        result = calculate_tax((period_2031,), contract)
        assert result.annual_results[0].loss_used_keur == pytest.approx(300.0)


# ---------------------------------------------------------------------------
# PR-10 Correction B: Effective dual-authority proof (including construction_pl)
# ---------------------------------------------------------------------------

class TestCorrectionBEffectiveDualAuthority:
    """Prove dual-authority guard fires on effective initial_tax_loss_keur.

    The adapter checks tax.initial_tax_loss_keur which may come from
    construction_pl.initial_tax_loss_keur rather than prior_tax_loss_keur
    directly. The guard must fire on both paths.
    """

    def _project_base(self):
        return _project()

    def test_construction_pl_nonzero_plus_vintages_fails_closed(self):
        """Non-zero construction_pl initial loss + explicit vintages → fail closed."""
        from dataclasses import replace as _replace
        from finco_core.tax.construction_pl import ConstructionPLStatement

        project = self._project_base()
        construction_pl = ConstructionPLStatement(
            pre_operational_opex_keur=500.0,  # generates a non-zero initial loss
        )
        project = _replace(
            project,
            tax=_replace(
                project.tax,
                construction_pl=construction_pl,
                prior_tax_loss_keur=0.0,  # legacy scalar neutral
                opening_tax_loss_vintages=(
                    OpeningTaxLossVintageParams(2025, 1000.0, "explicit_vintage"),
                ),
                clean_cash_tax_timing_enabled=True,
            ),
        )
        # Adapter must refuse: effective initial_tax_loss_keur > 0 AND vintages present
        with pytest.raises(NotImplementedError, match="initial_tax_loss_keur"):
            build_tax_contract_from_project_inputs(
                project, complete_financing_interest_will_be_injected=False
            )

    def test_zero_construction_pl_plus_vintages_allowed(self):
        """Zero construction_pl loss + explicit vintages is allowed (neutral scalar)."""
        from dataclasses import replace as _replace
        from finco_core.tax.construction_pl import ConstructionPLStatement

        project = self._project_base()
        zero_construction_pl = ConstructionPLStatement()  # all defaults are 0.0
        project = _replace(
            project,
            tax=_replace(
                project.tax,
                construction_pl=zero_construction_pl,
                prior_tax_loss_keur=0.0,
                opening_tax_loss_vintages=(
                    OpeningTaxLossVintageParams(2025, 1000.0, "explicit_vintage"),
                ),
                clean_cash_tax_timing_enabled=True,
            ),
        )
        contract = build_tax_contract_from_project_inputs(
            project, complete_financing_interest_will_be_injected=False
        )
        # Zero construction_pl produces zero initial loss → adapter allows vintages
        assert len(contract.opening_loss_vintages) == 1
        assert contract.opening_loss_vintages[0].amount_keur == pytest.approx(1000.0)

    def test_nonzero_construction_pl_without_vintages_fails_closed(self):
        """Non-zero construction_pl without explicit vintages must also fail closed.

        The non-zero scalar has no origin year and cannot be the clean vintage authority.
        """
        from dataclasses import replace as _replace
        from finco_core.tax.construction_pl import ConstructionPLStatement

        project = self._project_base()
        construction_pl = ConstructionPLStatement(pre_operational_opex_keur=800.0)
        project = _replace(
            project,
            tax=_replace(
                project.tax,
                construction_pl=construction_pl,
                prior_tax_loss_keur=0.0,
                opening_tax_loss_vintages=(),  # no explicit vintages
                clean_cash_tax_timing_enabled=True,
            ),
        )
        with pytest.raises(NotImplementedError, match="initial_tax_loss_keur"):
            build_tax_contract_from_project_inputs(
                project, complete_financing_interest_will_be_injected=False
            )

    def test_prior_tax_loss_keur_plus_vintages_fails_at_construction(self):
        """prior_tax_loss_keur > 0 + vintages raises at TaxParams construction (conflicting authorities)."""
        from dataclasses import replace as _replace

        base = self._project_base()
        # TaxParams.__post_init__ catches this before the adapter is even reached
        with pytest.raises(ValueError, match="conflicting authorities"):
            _replace(
                base,
                tax=_replace(
                    base.tax,
                    prior_tax_loss_keur=2000.0,
                    opening_tax_loss_vintages=(
                        OpeningTaxLossVintageParams(2025, 500.0, "conflict"),
                    ),
                    clean_cash_tax_timing_enabled=True,
                ),
            )
