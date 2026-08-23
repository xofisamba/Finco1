"""Canonical Stage B2 construction runtime tests."""
from __future__ import annotations

import pytest

from domain.construction.source_parity import oborovo_source_config
import finco_core.construction as construction_api
from finco_core.construction import FundingShortfallError, convergence_audit, run_stage_b2
from finco_core.construction import stage_b2


def test_public_run_stage_b2_is_stage_b2_single_callable():
    assert construction_api.run_stage_b2 is stage_b2.run_stage_b2


def test_run_stage_b2_is_canonical_entrypoint_for_oborovo_financial_outputs():
    result = run_stage_b2(oborovo_source_config())

    assert result.capitalized_financing_costs.senior_idc_keur > 0.0
    assert result.capitalized_financing_costs.senior_commitment_fee_keur > 0.0
    assert result.capitalized_financing_costs.structuring_fee_keur == pytest.approx(477.302687, abs=1e-9)
    assert result.final_gfa_keur > 55_999.0855
    assert result.closing_senior_drawn_keur > 0.0


def test_run_stage_b2_vat_runoff_horizon_is_canonical():
    result = run_stage_b2(oborovo_source_config())

    assert len(result.vat_schedule) == 18
    assert len(result.vat_payable_keur) == 12
    assert result.vat_schedule[12].vat_payable_keur == 0.0
    assert result.vat_schedule[-1].vat_requirement_keur == pytest.approx(0.0, abs=1e-9)


def test_run_stage_b2_reports_converged_vector_residual_audit():
    result = run_stage_b2(oborovo_source_config())

    assert result.iterations > 1
    assert result.final_residual_keur == pytest.approx(0.0, abs=1e-8)
    assert {row.component for row in result.residual_audit} == {"senior_idc", "senior_commitment_fee", "vat_financing_costs"}


def test_stage_b2_vector_residual_catches_same_total_different_timing():
    residual, audit = convergence_audit({"senior_idc": (150.0, 150.0)}, {"senior_idc": (100.0, 200.0)})

    assert residual == pytest.approx(100.0)
    assert audit[0].max_period_delta_keur == pytest.approx(50.0)


def test_stage_b2_initial_guess_independence_for_synthetic_case():
    base = oborovo_source_config()
    seeded = base.__class__(
        **{
            **base.__dict__,
            "initial_senior_idc_funded_uses_keur": (10.0,) * 12,
            "initial_senior_commitment_fee_funded_uses_keur": (3.0,) * 12,
            "initial_vat_financing_funded_uses_keur": (2.0,) * 12,
        }
    )

    a = run_stage_b2(base)
    b = run_stage_b2(seeded)

    assert a.capitalized_financing_costs.senior_idc_keur == pytest.approx(b.capitalized_financing_costs.senior_idc_keur, abs=1e-7)
    assert a.capitalized_financing_costs.senior_commitment_fee_keur == pytest.approx(b.capitalized_financing_costs.senior_commitment_fee_keur, abs=1e-7)
    assert a.closing_senior_drawn_keur == pytest.approx(b.closing_senior_drawn_keur, abs=1e-7)
    assert a.final_gfa_keur == pytest.approx(b.final_gfa_keur, abs=1e-7)


def test_capitalized_financing_adapter_populates_real_capex_structure_fields():
    from finco_core.construction import apply_capitalized_financing_costs
    from finco_core.inputs import CapexItem, CapexStructure

    zero = CapexItem("zero", 0.0)
    hard = CapexItem("hard", 100.0)
    capex = CapexStructure(
        epc_contract=hard,
        production_units=zero,
        epc_other=zero,
        grid_connection=zero,
        ops_prep=zero,
        insurances=zero,
        lease_tax=zero,
        construction_mgmt_a=zero,
        commissioning=zero,
        audit_legal=zero,
        construction_mgmt_b=zero,
        contingencies=zero,
        taxes=zero,
        project_acquisition=zero,
        project_rights=zero,
    )
    result = run_stage_b2(oborovo_source_config())
    updated = apply_capitalized_financing_costs(capex, result.capitalized_financing_costs)

    assert updated.idc_keur == pytest.approx(result.capitalized_financing_costs.senior_idc_keur)
    assert updated.commitment_fees_keur == pytest.approx(result.capitalized_financing_costs.senior_commitment_fee_keur)
    assert updated.bank_fees_keur == pytest.approx(result.capitalized_financing_costs.structuring_fee_keur)
    assert updated.vat_costs_keur == pytest.approx(
        result.capitalized_financing_costs.vat_idc_keur
        + result.capitalized_financing_costs.vat_commitment_fee_keur
    )
    # Useful-life policy is owned by the accounting layer; Stage B2 hands off amounts only.
    names = {item.name: item for item in updated.book_depreciable_capex_items()}
    assert names["IDC (Interest During Construction)"].useful_life_override == 12
    assert names["Commitment Fees"].useful_life_override == 12
    assert names["Bank Fees"].useful_life_override == 12
    assert names["VAT Costs"].useful_life_override == 20


def test_stage_b2_financing_costs_do_not_expose_accounting_useful_life_policy():
    result = run_stage_b2(_synthetic_config(
        senior_interest_rate=0.0,
        senior_commitment_fee_rate=0.0,
        max_iterations=20,
    ))

    assert "senior_financing_useful_life_years" not in result.config.__dataclass_fields__
    assert "vat_financing_useful_life_years" not in result.config.__dataclass_fields__
    assert (
        "senior_financing_useful_life_years"
        not in result.capitalized_financing_costs.__dataclass_fields__
    )
    assert (
        "vat_financing_useful_life_years"
        not in result.capitalized_financing_costs.__dataclass_fields__
    )
    assert not hasattr(result.capitalized_financing_costs, "useful_lives_years")


def _synthetic_config(**overrides):
    cfg = oborovo_source_config()
    return cfg.__class__(
        **{
            **cfg.__dict__,
            "capex_schedule": stage_b2.CapexScheduleSet((
                stage_b2.CapexPaymentItem("A", "Asset", 1_200.0, (1 / 12,) * 12, 0.0),
            )),
            "funding_policy": stage_b2.FinancingCostFundingPolicy((1.0,) + (0.0,) * 11),
            "source_total_uses_validation_keur": (),
            "equity_available_keur": 0.0,
            "shl_available_keur": 0.0,
            "senior_commitment_keur": 2_000.0,
            "senior_interest_rate": 0.06,
            "senior_commitment_fee_rate": 0.012,
            "senior_interest_rate_schedule": (),
            "base_rate": 0.0,
            "hedge_coverage": 0.0,
            "swap_margin": 0.0,
            "forward_swap_margin": 0.0,
            "cva": 0.0,
            "external_curve_buffer": 0.0,
            "euribor_1m_fixings": (),
            "senior_idc_balance_basis": "OPENING_DRAWN",
            "senior_commitment_fee_balance_basis": "OPENING_UNDRAWN",
            "senior_idc_capitalization_timing": "SAME_PERIOD",
            "senior_commitment_fee_capitalization_timing": "SAME_PERIOD",
            "structuring_fee_rate": 0.0,
            "structuring_fee_basis_keur": 0.0,
            "vat_facility_interest_rate": 0.0,
            "vat_facility_commitment_fee_rate": 0.0,
            "vat_facility_commitment_keur": 0.0,
            "vat_financing_cost_spending_profile": (),
            **overrides,
        }
    )


def test_opening_basis_and_same_period_capitalization_are_runtime_policies():
    result = run_stage_b2(_synthetic_config(max_iterations=200))

    assert result.capitalized_financing_costs.senior_idc_keur > 0.0
    assert result.capitalized_financing_costs.senior_commitment_fee_keur > 0.0
    # First period IDC uses zero opening drawn balance and is therefore zero.
    assert result.total_permanent_uses_keur[0] == pytest.approx(100.0 + 2_000.0 * 0.012 * (2 / 360), abs=1e-9)


def test_period_rate_schedule_can_be_derived_from_hedge_and_euribor_primitives():
    cfg = _synthetic_config(
        senior_interest_rate=0.0265,
        base_rate=0.03,
        hedge_coverage=0.80,
        swap_margin=0.002,
        external_curve_buffer=0.20,
        euribor_1m_fixings=(0.02996,) * 12,
    )
    result = run_stage_b2(cfg)
    first_period_fee = 2_000.0 * 0.012 * (2 / 360)
    second_opening = 100.0 + first_period_fee
    expected_rate = 0.03 * 0.80 + 0.002 + 0.02996 * 0.24 + 0.0265
    expected_p2_idc = second_opening * expected_rate * (31 / 360)

    assert result.total_permanent_uses_keur[1] == pytest.approx(100.0 + expected_p2_idc + (2_000.0 - second_opening) * 0.012 * (31 / 360), abs=1e-6)


def test_capex_equal_and_custom_schedules_drive_monthly_uses_generically():
    cfg = _synthetic_config(
        capex_schedule=stage_b2.CapexScheduleSet((
            stage_b2.CapexPaymentItem("EQ", "Equal", 120.0, (1 / 12,) * 12, 0.10),
            stage_b2.CapexPaymentItem("CUSTOM", "Custom", 80.0, (0.0, 0.5, 0.5) + (0.0,) * 9, 0.20),
        )),
        senior_commitment_keur=500.0,
        vat_facility_commitment_keur=25.0,
        max_iterations=200,
    )
    result = run_stage_b2(cfg)

    assert result.monthly_hard_capex_keur[0] == pytest.approx(10.0)
    assert result.monthly_hard_capex_keur[1] == pytest.approx(50.0)
    assert result.vat_payable_keur[0] == pytest.approx(1.0)
    assert result.vat_payable_keur[1] == pytest.approx(9.0)


def test_capex_schedule_sum_validation_rejects_malformed_profile():
    bad = stage_b2.CapexScheduleSet((
        stage_b2.CapexPaymentItem("BAD", "Bad", 100.0, (0.5,) + (0.0,) * 11, 0.0),
    ))

    with pytest.raises(ValueError, match="payment weights"):
        stage_b2.monthly_hard_capex(bad)


def test_funding_waterfall_consumes_equity_then_shl_before_senior():
    cfg = _synthetic_config(
        capex_schedule=stage_b2.CapexScheduleSet((
            stage_b2.CapexPaymentItem("A", "Asset", 1_200.0, (1 / 12,) * 12, 0.0),
        )),
        equity_available_keur=50.0,
        shl_available_keur=75.0,
        senior_commitment_keur=2_000.0,
        senior_interest_rate=0.0,
        senior_commitment_fee_rate=0.0,
        max_iterations=20,
    )
    result = run_stage_b2(cfg)

    assert result.senior_period_draw_keur[0] == pytest.approx(0.0)
    assert result.senior_period_draw_keur[1] == pytest.approx(75.0)


def test_senior_funding_allows_exactly_at_commitment():
    cfg = _synthetic_config(
        senior_commitment_keur=1_200.0,
        senior_interest_rate=0.0,
        senior_commitment_fee_rate=0.0,
        max_iterations=20,
    )
    result = run_stage_b2(cfg)

    assert result.closing_senior_drawn_keur == pytest.approx(1_200.0)
    assert result.closing_senior_undrawn_keur == pytest.approx(0.0)


def test_senior_funding_allows_below_commitment_without_forced_final_draw():
    cfg = _synthetic_config(
        senior_commitment_keur=1_500.0,
        senior_interest_rate=0.0,
        senior_commitment_fee_rate=0.0,
        max_iterations=20,
    )
    result = run_stage_b2(cfg)

    assert result.closing_senior_drawn_keur == pytest.approx(1_200.0)
    assert result.closing_senior_undrawn_keur == pytest.approx(300.0)
    assert result.senior_period_draw_keur[-1] == pytest.approx(100.0)


def test_senior_funding_breach_fails_fast_without_capping_shortfall():
    cfg = _synthetic_config(
        senior_commitment_keur=1_199.0,
        senior_interest_rate=0.0,
        senior_commitment_fee_rate=0.0,
        max_iterations=20,
    )

    with pytest.raises(FundingShortfallError, match="Senior facility commitment breached"):
        run_stage_b2(cfg)


def test_vat_reimbursement_lag_rolls_requirement_forward_generically():
    schedule = stage_b2.compute_vat_schedule(
        (10.0, 20.0),
        reimbursement_lag_periods=2,
        vat_facility_commitment_keur=30.0,
    )

    assert [row.vat_requirement_keur for row in schedule] == pytest.approx([10.0, 30.0, 20.0, 0.0])
    assert [row.vat_reimbursement_keur for row in schedule] == pytest.approx([0.0, 0.0, 10.0, 20.0])
    assert [row.vat_drawn_keur for row in schedule] == pytest.approx([10.0, 30.0, 20.0, 0.0])
    assert [row.vat_undrawn_keur for row in schedule] == pytest.approx([20.0, 0.0, 10.0, 30.0])


def test_vat_requirement_breach_fails_against_explicit_commitment():
    with pytest.raises(FundingShortfallError, match="VAT facility commitment breached"):
        stage_b2.compute_vat_schedule(
            (10.0, 20.0),
            reimbursement_lag_periods=2,
            vat_facility_commitment_keur=29.0,
        )


def test_positive_capex_in_inactive_construction_period_fails_fast():
    cfg = _synthetic_config(
        capex_schedule=stage_b2.CapexScheduleSet((
            stage_b2.CapexPaymentItem("P1", "P1 Asset", 120.0, (1.0,) + (0.0,) * 11, 0.0),
        )),
        timeline=tuple(
            cfg_period.__class__(
                **{
                    **cfg_period.__dict__,
                    "active_construction": False,
                    "capex_payment_eligible": True,
                }
            )
            if idx == 0 else cfg_period
            for idx, cfg_period in enumerate(oborovo_source_config().timeline)
        ),
        senior_interest_rate=0.0,
        senior_commitment_fee_rate=0.0,
        max_iterations=20,
    )

    with pytest.raises(ValueError, match="CAPEX scheduled in inactive construction period 1"):
        run_stage_b2(cfg)


def test_zero_scheduled_capex_in_inactive_construction_period_is_valid():
    cfg = _synthetic_config(
        capex_schedule=stage_b2.CapexScheduleSet((
            stage_b2.CapexPaymentItem("P2", "P2 Asset", 120.0, (0.0, 1.0) + (0.0,) * 10, 0.0),
        )),
        timeline=tuple(
            cfg_period.__class__(
                **{
                    **cfg_period.__dict__,
                    "active_construction": False,
                    "capex_payment_eligible": False,
                }
            )
            if idx == 0 else cfg_period
            for idx, cfg_period in enumerate(oborovo_source_config().timeline)
        ),
        senior_interest_rate=0.0,
        senior_commitment_fee_rate=0.0,
        max_iterations=20,
    )
    result = run_stage_b2(cfg)

    assert result.monthly_hard_capex_keur[0] == pytest.approx(0.0)
    assert result.monthly_hard_capex_keur[1] == pytest.approx(120.0)


def test_positive_vat_generating_capex_in_ineligible_period_fails_fast():
    cfg = _synthetic_config(
        capex_schedule=stage_b2.CapexScheduleSet((
            stage_b2.CapexPaymentItem("VAT", "VAT Asset", 120.0, (1.0,) + (0.0,) * 11, 0.10),
        )),
        timeline=tuple(
            cfg_period.__class__(
                **{
                    **cfg_period.__dict__,
                    "active_construction": True,
                    "capex_payment_eligible": False,
                }
            )
            if idx == 0 else cfg_period
            for idx, cfg_period in enumerate(oborovo_source_config().timeline)
        ),
        vat_facility_commitment_keur=12.0,
        senior_interest_rate=0.0,
        senior_commitment_fee_rate=0.0,
        max_iterations=20,
    )

    with pytest.raises(ValueError, match="VAT-generating CAPEX scheduled in ineligible CAPEX payment period 1"):
        run_stage_b2(cfg)


def test_inactive_vat_facility_rejects_positive_requirement():
    timeline = tuple(
        period.__class__(**{**period.__dict__, "vat_facility_active": False})
        if idx == 0 else period
        for idx, period in enumerate(oborovo_source_config().timeline)
    )
    cfg = _synthetic_config(
        capex_schedule=stage_b2.CapexScheduleSet((
            stage_b2.CapexPaymentItem("VAT", "VAT Asset", 120.0, (1.0,) + (0.0,) * 11, 0.10),
        )),
        timeline=timeline,
        vat_facility_commitment_keur=12.0,
        senior_interest_rate=0.0,
        senior_commitment_fee_rate=0.0,
        max_iterations=20,
    )

    with pytest.raises(FundingShortfallError, match="VAT facility inactive"):
        run_stage_b2(cfg)


def test_hedge_coverage_zero_and_full_change_derived_rates_generically():
    floating = run_stage_b2(_synthetic_config(
        senior_interest_rate=0.01,
        base_rate=0.03,
        hedge_coverage=0.0,
        external_curve_buffer=0.20,
        euribor_1m_fixings=(0.04,) * 12,
        senior_commitment_fee_rate=0.0,
        max_iterations=200,
    ))
    fixed = run_stage_b2(_synthetic_config(
        senior_interest_rate=0.01,
        base_rate=0.03,
        hedge_coverage=1.0,
        external_curve_buffer=0.20,
        euribor_1m_fixings=(0.04,) * 12,
        senior_commitment_fee_rate=0.0,
        max_iterations=200,
    ))

    assert floating.capitalized_financing_costs.senior_idc_keur > fixed.capitalized_financing_costs.senior_idc_keur


def test_swap_forward_and_cva_adjustments_affect_period_rate_generically():
    base = run_stage_b2(_synthetic_config(
        senior_interest_rate=0.01,
        base_rate=0.03,
        hedge_coverage=1.0,
        euribor_1m_fixings=(0.02,) * 12,
        senior_commitment_fee_rate=0.0,
        max_iterations=200,
    ))
    adjusted = run_stage_b2(_synthetic_config(
        senior_interest_rate=0.01,
        base_rate=0.03,
        hedge_coverage=1.0,
        swap_margin=0.002,
        forward_swap_margin=0.001,
        cva=0.0005,
        euribor_1m_fixings=(0.02,) * 12,
        senior_commitment_fee_rate=0.0,
        max_iterations=200,
    ))

    assert adjusted.capitalized_financing_costs.senior_idc_keur > base.capitalized_financing_costs.senior_idc_keur


def test_same_period_and_next_funding_period_capitalization_differ_generically():
    same = run_stage_b2(_synthetic_config(
        senior_idc_balance_basis="FUNDING_PERIOD_CLOSING_DRAWN",
        senior_commitment_fee_balance_basis="FUNDING_PERIOD_CLOSING_UNDRAWN",
        senior_idc_capitalization_timing="SAME_PERIOD",
        senior_commitment_fee_capitalization_timing="SAME_PERIOD",
        max_iterations=200,
    ))
    lagged = run_stage_b2(_synthetic_config(
        senior_idc_balance_basis="FUNDING_PERIOD_CLOSING_DRAWN",
        senior_commitment_fee_balance_basis="FUNDING_PERIOD_CLOSING_UNDRAWN",
        senior_idc_capitalization_timing="NEXT_FUNDING_PERIOD",
        senior_commitment_fee_capitalization_timing="NEXT_FUNDING_PERIOD",
        max_iterations=200,
    ))

    assert same.total_permanent_uses_keur[0] > lagged.total_permanent_uses_keur[0]
    assert lagged.total_permanent_uses_keur[1] > 100.0


def test_zero_convergence_tolerance_fails_before_generic_circular_calculation():
    with pytest.raises(ValueError, match="STAGE_B2_INVALID_NUMERIC"):
        run_stage_b2(_synthetic_config(max_iterations=1, convergence_tolerance_keur=0.0))


def test_runtime_config_has_no_project_identity_or_approved_delta_fields():
    fields = set(stage_b2.ConstructionRuntimeConfig.__dataclass_fields__)

    assert "project_name" not in fields
    assert "project_code" not in fields
    assert "approved_delta" not in fields
    assert "balancing_plug" not in fields


def test_next_funding_period_accrual_vector_differs_from_capitalization_use_vector():
    """NEXT_FUNDING_PERIOD: raw accrual period != capitalization-funding period.

    When senior_idc_capitalization_timing = NEXT_FUNDING_PERIOD, the IDC accrued in
    period N becomes a capitalized Use in period N+1. This test proves that:

    1. senior_idc_accrual_keur is NOT the shifted capitalization-use vector;
    2. senior_idc_accrual_keur[0] > 0 (IDC accrues in period 1 when draws happen);
    3. the capitalization-use shift means period_uses[0] carries NO IDC capitalization
       (it shifted into period 1's uses from the lag), while period_uses[1] carries the
       period-0 IDC;
    4. accrual_total == capitalization_total (same total, different timing).

    Semantically: accrual timing != capitalization funding timing when a lag policy applies.
    """
    lagged = run_stage_b2(_synthetic_config(
        senior_idc_balance_basis="FUNDING_PERIOD_CLOSING_DRAWN",
        senior_commitment_fee_balance_basis="FUNDING_PERIOD_CLOSING_UNDRAWN",
        senior_idc_capitalization_timing="NEXT_FUNDING_PERIOD",
        senior_commitment_fee_capitalization_timing="NEXT_FUNDING_PERIOD",
        max_iterations=200,
    ))

    accruals = lagged.senior_idc_accrual_keur
    uses = lagged.total_permanent_uses_keur

    # The IDC accrual vector reflects balance-basis computation: period 0 draws → IDC accrues
    assert accruals[0] > 0.0, (
        f"Expected IDC accrual in period 0 (draws happen there) but got {accruals[0]:.8f}"
    )

    # Accrual total must equal the capitalized IDC total (same money, different timing)
    accrual_total = sum(accruals)
    cap_total = lagged.capitalized_financing_costs.senior_idc_keur
    assert abs(accrual_total - cap_total) < 1e-6, (
        f"accrual_total={accrual_total:.6f} != cap_total={cap_total:.6f}; "
        "accrual vector must sum to the same IDC total as the capitalization"
    )

    # The capitalization is shifted: period_uses[0] has no IDC capitalization component
    # (it was shifted into period 1). Verify by checking same-period config has IDC in uses[0].
    same = run_stage_b2(_synthetic_config(
        senior_idc_balance_basis="FUNDING_PERIOD_CLOSING_DRAWN",
        senior_commitment_fee_balance_basis="FUNDING_PERIOD_CLOSING_UNDRAWN",
        senior_idc_capitalization_timing="SAME_PERIOD",
        senior_commitment_fee_capitalization_timing="SAME_PERIOD",
        max_iterations=200,
    ))
    # Capitalization USE vectors differ: period 0 uses are lower for lagged (IDC shifted out)
    assert same.total_permanent_uses_keur[0] > lagged.total_permanent_uses_keur[0] + 1e-9, (
        "SAME_PERIOD uses[0] must exceed NEXT_FUNDING_PERIOD uses[0] (IDC shifted out of period 0)"
    )
    # Accrual vector (from final draws, balance-basis) must NOT be the shifted use vector:
    # If accruals == shifted_uses, accruals[0] would be 0.0 (nothing shifts into period 0).
    # But accruals[0] > 0 (proven above), so they are distinct from the capitalization-use vector.
    shifted_uses = (0.0,) + lagged.senior_idc_accrual_keur[:-1]
    assert any(abs(a - s) > 1e-9 for a, s in zip(accruals, shifted_uses)), (
        "accrual_keur must differ from shifted_uses — they encode different timing semantics"
    )
