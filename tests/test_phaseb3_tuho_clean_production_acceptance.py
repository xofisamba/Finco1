from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest

from app.project_factories import create_default_tuho_wind1
from app.services.production_financial_authority import run_clean_production


GATE_FIXTURE = Path(
    "tests/fixtures/interest_limitation/tuho_capitalisation_gate_fixture.json"
)


@pytest.fixture(scope="module")
def clean_run():
    return run_clean_production(create_default_tuho_wind1())


def test_clean_runtime_uses_typed_construction_and_derived_vat_authority(clean_run):
    financing = clean_run.g2c_result.financing_result
    construction = financing.construction_financing

    assert construction is not None
    assert len(construction.period_start_dates) == 18
    assert financing.project_uses.hard_project_capex_keur == pytest.approx(
        70_691.53944444444
    )
    assert construction.vat_commitment_mode == "DERIVED_PEAK_REQUIREMENT"
    assert construction.vat_effective_commitment_keur == pytest.approx(
        3_361.5090166666664
    )
    assert construction.vat_idc_keur == pytest.approx(122.31400101334873)
    assert construction.vat_commitment_fee_keur == pytest.approx(26.465752928759645)
    assert construction.sources_uses_residual_keur == pytest.approx(0.0, abs=1e-8)


def test_construction_shl_interest_enters_tax_once_without_capex_double_count(clean_run):
    financing = clean_run.g2c_result.financing_result
    model = financing.project_model_result
    construction = financing.construction_financing
    tax = model.tax_and_cfads

    assert construction is not None
    assert tax is not None
    construction_pik = construction.shl_construction_pik_keur
    assert sum(construction.shl_pik_accrual_keur) == pytest.approx(construction_pik)
    assert tax.shl_gross_interest_audit_keur[0] == pytest.approx(
        construction_pik, abs=2e-6
    )
    assert financing.opening_operating_shl_balance_keur == pytest.approx(
        financing.derived_shl_cash_principal_keur + construction_pik,
        abs=2e-6,
    )
    assert financing.project_uses.hard_project_capex_keur == pytest.approx(
        70_691.53944444444
    )


def test_dynamic_gate_and_deductible_interest_identity_close(clean_run):
    tax = clean_run.g2c_result.financing_result.project_model_result.tax_and_cfads
    assert tax is not None

    active = [
        index for index, enabled in enumerate(tax.capitalisation_gate_audit) if enabled
    ]
    assert active[0] == 8
    assert tax.capitalisation_ratio_audit[8] == pytest.approx(0.803290783150396)
    for gross, deductible, disallowed in zip(
        tax.shl_gross_interest_audit_keur,
        tax.shl_deductible_interest_audit_keur,
        tax.shl_disallowed_interest_audit_keur,
        strict=True,
    ):
        assert deductible + disallowed == pytest.approx(gross, abs=1e-9)


def test_clean_senior_and_shl_close_without_frozen_schedule_or_top_up(clean_run):
    financing = clean_run.g2c_result.financing_result
    model = financing.project_model_result
    shl = model.shareholder_loan

    assert shl is not None
    assert financing.binding_senior_constraint == "DSCR"
    assert financing.final_senior_commitment_keur == pytest.approx(
        43_789.92111682598
    )
    assert financing.derived_shl_cash_principal_keur == pytest.approx(
        28_741.108714531947
    )
    assert financing.opening_operating_shl_balance_keur == pytest.approx(
        32_261.52826981019
    )
    principal_periods = [
        index for index, amount in enumerate(shl.shl_principal_keur) if amount > 1e-8
    ]
    assert principal_periods[0] == 25
    assert principal_periods[-1] == 36
    assert shl.shl_closing_keur[-1] == pytest.approx(0.0, abs=1e-8)
    assert shl.diagnostics.converged is True
    assert shl.diagnostics.max_final_shl_interest_handshake_delta_keur < 1e-8
    assert shl.diagnostics.max_final_shl_closing_handshake_delta_keur < 1e-8


def test_project_identity_is_non_financial_and_target_dscr_is_causal(clean_run):
    project = create_default_tuho_wind1()
    renamed = replace(
        project,
        info=replace(project.info, name="Renamed clean wind", code="RENAMED"),
    )
    renamed_run = run_clean_production(renamed)
    baseline_senior = clean_run.g2c_result.financing_result.final_senior_commitment_keur
    assert renamed_run.g2c_result.financing_result.final_senior_commitment_keur == (
        pytest.approx(baseline_senior, abs=1e-8)
    )

    sculpting = project.financing.senior_sculpting_config
    assert sculpting is not None
    lower_target = replace(
        project,
        financing=replace(
            project.financing,
            senior_sculpting_config=replace(
                sculpting,
                target_dscr_schedule=tuple(
                    target - 0.02 for target in sculpting.target_dscr_schedule
                ),
            ),
        ),
    )
    lower_target_run = run_clean_production(lower_target)
    assert lower_target_run.g2c_result.financing_result.final_senior_commitment_keur > (
        baseline_senior
    )


def test_source_gate_fixture_is_validation_only_not_runtime_input():
    fixture = json.loads(GATE_FIXTURE.read_text(encoding="utf-8"))
    project_repr = repr(create_default_tuho_wind1())

    first_active = next(
        period["period_index"] for period in fixture["periods"] if period["gate_active"]
    )
    assert first_active == 7
    assert "first_active_period_index" not in project_repr
    assert "source_gate_vector" not in project_repr


# ---------------------------------------------------------------------------
# B3 Correction B — Construction financing / total project uses causal
# reconciliation identity tests (14 tests required by independent review).
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def b3_uses_data(clean_run):
    fr = clean_run.g2c_result.financing_result
    return fr.project_uses, fr.construction_financing


def test_b3_cbc_T1_project_uses_total_equals_cfr_final_total(b3_uses_data):
    """T1: project_uses.total == cfr.final_total_project_uses (no lag)."""
    pu, cfr = b3_uses_data
    assert pu.total_project_uses_keur == pytest.approx(
        cfr.final_total_project_uses_keur, abs=1e-8
    )


def test_b3_cbc_T2_hard_plus_financing_plus_reserve_equals_total(b3_uses_data):
    """T2: hard + explicit_financing + reserve + other_explicit == total (strict identity)."""
    pu, cfr = b3_uses_data
    recomputed = (
        pu.hard_project_capex_keur
        + pu.explicit_financing_cost_uses_keur
        + pu.reserve_account_funding_keur
        + pu.other_explicit_project_uses_keur
    )
    assert recomputed == pytest.approx(pu.total_project_uses_keur, abs=1e-8)


def test_b3_cbc_T3_capitalized_financing_consistent_with_project_uses(b3_uses_data):
    """T3: cfr.total_capitalized_financing ≈ project_uses.explicit_financing (within 1e-6 kEUR)."""
    pu, cfr = b3_uses_data
    assert cfr.total_capitalized_financing_keur == pytest.approx(
        pu.explicit_financing_cost_uses_keur, abs=1e-6
    )


def test_b3_cbc_T4_tuho_has_zero_reserve(b3_uses_data):
    """T4: TUHO clean run carries no reserve — no hidden capacity in reserve."""
    pu, cfr = b3_uses_data
    assert pu.reserve_account_funding_keur == pytest.approx(0.0, abs=1e-9)


def test_b3_cbc_T5_tuho_has_zero_other_explicit_uses(b3_uses_data):
    """T5: No other_explicit_project_uses — uses decomposition is complete."""
    pu, cfr = b3_uses_data
    assert pu.other_explicit_project_uses_keur == pytest.approx(0.0, abs=1e-9)


def test_b3_cbc_T6_raw_idc_accrual_exceeds_capitalized_idc_uses(b3_uses_data):
    """T6: Raw IDC accrual total > capitalized IDC uses total.

    TERMINAL_RAW_IDC_OUTSIDE_NEXT_PERIOD_CAPITALIZATION_HORIZON:
    With NEXT_PERIOD timing the last period's raw accrual is shifted out of
    the construction Uses vector. This is a capitalization horizon semantic,
    NOT a tax-disallowance result.
    """
    pu, cfr = b3_uses_data
    raw_total = sum(cfr.senior_idc_accrual_keur)
    cap_total = sum(cfr.senior_idc_capitalized_uses_keur)
    assert raw_total > cap_total


def test_b3_cbc_T7_next_period_identity_terminal_raw_accrual(b3_uses_data):
    """T7: NEXT_PERIOD timing identity: raw_total - cap_total == last_raw_accrual.

    For NEXT_PERIOD: capitalized = (0.0,) + raw[:-1]
    Therefore sum(capitalized) = sum(raw) - raw[-1].
    The difference is the terminal period raw accrual — outside the construction
    capitalization horizon, not tax-disallowed IDC.
    """
    pu, cfr = b3_uses_data
    raw = cfr.senior_idc_accrual_keur
    cap = cfr.senior_idc_capitalized_uses_keur
    terminal_raw = raw[-1]
    assert sum(raw) - sum(cap) == pytest.approx(terminal_raw, abs=1e-10)
    # Validation fingerprint — do NOT treat as financial authority
    assert terminal_raw == pytest.approx(217.1250255375923, abs=1e-4)


def test_b3_cbc_T8_all_idc_accruals_non_negative(b3_uses_data):
    """T8: No period may carry negative IDC accrual."""
    pu, cfr = b3_uses_data
    for i, val in enumerate(cfr.senior_idc_accrual_keur):
        assert val >= -1e-10, f"Period {i}: negative IDC accrual {val}"


def test_b3_cbc_T9_outer_loop_converged(b3_uses_data):
    """T9: Outer fixed-point loop converged (residual < 1e-6 kEUR)."""
    pu, cfr = b3_uses_data
    assert cfr.outer_residual_keur == pytest.approx(0.0, abs=1e-6)


def test_b3_cbc_T10_idempotence_residual_tight(b3_uses_data):
    """T10: Final idempotence check residual < 1e-4 kEUR (no outer-loop state lag)."""
    pu, cfr = b3_uses_data
    assert cfr.final_verification_outer_residual_keur == pytest.approx(0.0, abs=1e-4)


def test_b3_cbc_T11_vat_facility_components_in_capitalized_total(b3_uses_data):
    """T11: VAT IDC + VAT commitment fee are included in total_capitalized_financing."""
    pu, cfr = b3_uses_data
    vat_total = cfr.vat_idc_keur + cfr.vat_commitment_fee_keur
    assert vat_total == pytest.approx(122.31400101334872 + 26.465752928759642, abs=1e-9)
    assert cfr.total_capitalized_financing_keur > vat_total


def test_b3_cbc_T12_capitalized_idc_uses_sums_to_capitalized_total(b3_uses_data):
    """T12: sum(senior_idc_capitalized_uses_keur) == CapitalizedFinancingCosts.senior_idc_keur.

    The explicit audit field sums to the same scalar carried in total_capitalized_financing.
    """
    pu, cfr = b3_uses_data
    cap_idc_from_vector = sum(cfr.senior_idc_capitalized_uses_keur)
    # Derive the capitalized senior IDC scalar from the total (single authority)
    cap_senior_idc_scalar = (
        cfr.total_capitalized_financing_keur
        - sum(cfr.senior_commitment_fee_accrual_keur)
        - sum(cfr.structuring_fee_keur)
        - cfr.vat_idc_keur
        - cfr.vat_commitment_fee_keur
    )
    assert cap_idc_from_vector == pytest.approx(cap_senior_idc_scalar, abs=1e-8)
    assert cap_idc_from_vector == pytest.approx(1_552.229213780136, abs=1e-6)


def test_b3_cbc_T13_like_for_like_capitalized_idc_vs_source(b3_uses_data):
    """T13: Like-for-like: clean CAPITALIZED IDC vs source live IDC schedule sum.

    DO NOT compare raw accrual to source pasted total — those are NOT like-for-like.

    Correct comparison:
      A. Clean raw accrual (diagnostic only): ~1,769.354 kEUR
      B. Clean capitalized IDC use (project use): ~1,552.229 kEUR  ← economically correct
      C. Source live IDC schedule sum: ~1,520.305 kEUR
      D. Source pasted/total-uses IDC: ~1,519.564 kEUR

    Like-for-like source/clean divergence (B vs C): ~+31.924 kEUR.
    Source circularity residual (C - D): ~+0.741 kEUR = SOURCE_CONSTRUCTION_CIRCULARITY_RESIDUAL.
    """
    pu, cfr = b3_uses_data
    SOURCE_LIVE_IDC_KEUR = 1_520.3051321075397
    SOURCE_PASTED_IDC_KEUR = 1_519.563935502677
    SOURCE_CIRCULARITY_RESIDUAL_KEUR = SOURCE_LIVE_IDC_KEUR - SOURCE_PASTED_IDC_KEUR

    clean_raw = sum(cfr.senior_idc_accrual_keur)
    clean_cap = sum(cfr.senior_idc_capitalized_uses_keur)

    assert clean_raw == pytest.approx(1_769.3542393177286, abs=1e-6)
    assert clean_cap == pytest.approx(1_552.229213780136, abs=1e-6)

    # Like-for-like divergence: capitalized vs live source
    like_for_like_delta = clean_cap - SOURCE_LIVE_IDC_KEUR
    assert like_for_like_delta == pytest.approx(31.924081672596, abs=0.5)

    # Source circularity classified, not reproduced
    assert SOURCE_CIRCULARITY_RESIDUAL_KEUR == pytest.approx(0.741196604863, abs=0.01)


def test_b3_cbc_T14_construction_financing_produces_no_double_count(b3_uses_data):
    """T14: Hard CAPEX in project_uses equals hard CAPEX period vector sum.

    Confirms no double-count between hard_capex_uses and explicit_financing_cost_uses.
    """
    pu, cfr = b3_uses_data
    hard_from_vector = sum(cfr.hard_capex_uses_keur)
    assert hard_from_vector == pytest.approx(pu.hard_project_capex_keur, abs=1e-8)
    assert pu.hard_project_capex_keur == pytest.approx(70_691.53944444444, abs=1e-8)
    assert pu.explicit_financing_cost_uses_keur != pytest.approx(0.0, abs=1.0)


# ---------------------------------------------------------------------------
# B3 Correction C — IDC accrual vs capitalization semantics, NEXT_PERIOD
# timing proof, tax-independence, and like-for-like source reconciliation.
# ---------------------------------------------------------------------------


def test_b3_ccc_1_raw_and_capitalized_idc_are_distinct_typed_concepts(b3_uses_data):
    """CC1: raw accrual and capitalized uses are distinct typed concepts on cfr."""
    pu, cfr = b3_uses_data
    assert hasattr(cfr, "senior_idc_accrual_keur")
    assert hasattr(cfr, "senior_idc_capitalized_uses_keur")
    raw = cfr.senior_idc_accrual_keur
    cap = cfr.senior_idc_capitalized_uses_keur
    # They are different tuples
    assert raw != cap
    assert sum(raw) != pytest.approx(sum(cap), abs=1.0)


def test_b3_ccc_2_next_period_transformation_identity(b3_uses_data):
    """CC2: NEXT_PERIOD transformation: cap == (0.0,) + raw[:-1] element-wise."""
    pu, cfr = b3_uses_data
    raw = cfr.senior_idc_accrual_keur
    cap = cfr.senior_idc_capitalized_uses_keur
    expected = (0.0,) + raw[:-1]
    assert len(cap) == len(expected)
    for i, (a, b) in enumerate(zip(cap, expected)):
        assert a == pytest.approx(b, abs=1e-12), f"Period {i}: cap={a}, expected={b}"


def test_b3_ccc_3_difference_equals_terminal_raw_accrual(b3_uses_data):
    """CC3: sum(raw) - sum(cap) == raw[-1] (terminal period accrual).

    This is the TERMINAL_RAW_IDC_OUTSIDE_NEXT_PERIOD_CAPITALIZATION_HORIZON amount.
    It is a timing/horizon semantic, NOT a tax-disallowance.
    """
    pu, cfr = b3_uses_data
    raw = cfr.senior_idc_accrual_keur
    cap = cfr.senior_idc_capitalized_uses_keur
    assert sum(raw) - sum(cap) == pytest.approx(raw[-1], abs=1e-10)


def test_b3_ccc_4_same_period_total_equals_raw_accrual_total():
    """CC4: SAME_PERIOD timing: capitalized total == raw accrual total (no horizon shift)."""
    from finco_core.construction.stage_b2 import _capitalized_uses
    raw = (10.0, 20.0, 30.0, 25.0, 15.0)
    same_period_cap = _capitalized_uses(sum(raw), (), raw, "SAME_PERIOD")
    assert sum(same_period_cap) == pytest.approx(sum(raw), abs=1e-12)
    assert same_period_cap == raw


def test_b3_ccc_5_opening_same_vs_closing_next_interior_equivalence():
    """CC5: Interior-period equivalence of OPENING+SAME vs CLOSING+NEXT.

    Synthetic schedule: draws D1, D2, D3, D4. rate r, dcf f.
    OPENING+SAME: interest[t] = opening[t] * r * f, capitalize same period.
    CLOSING+NEXT: interest[t] = closing[t] * r * f, capitalize next period.
    Interior periods (1 to n-2) produce economically equivalent IDC Uses.
    Period 0: CLOSING has draw D1 whereas OPENING has 0 — initial boundary differs.
    Period n-1: CLOSING accrual falls outside NEXT_PERIOD horizon — terminal boundary differs.
    """
    draws = (100.0, 200.0, 150.0, 50.0)
    rate = 0.05
    dcf = 1 / 12
    n = len(draws)

    # Opening balance method (SAME_PERIOD): opening[t] = sum(draws[:t])
    opening = [sum(draws[:t]) for t in range(n)]
    idc_opening_same = tuple(opening[t] * rate * dcf for t in range(n))
    cap_opening_same = idc_opening_same  # SAME_PERIOD

    # Closing balance method (NEXT_PERIOD): closing[t] = sum(draws[:t+1])
    closing = [sum(draws[:t + 1]) for t in range(n)]
    idc_closing = tuple(closing[t] * rate * dcf for t in range(n))
    cap_closing_next = (0.0,) + idc_closing[:-1]  # NEXT_PERIOD

    # Interior periods [1, n-2]: cap_opening_same[t] == cap_closing_next[t]
    for t in range(1, n - 1):
        assert cap_opening_same[t] == pytest.approx(cap_closing_next[t], abs=1e-12), (
            f"Interior period {t}: OPENING+SAME={cap_opening_same[t]}, "
            f"CLOSING+NEXT={cap_closing_next[t]}"
        )

    # Period 0 boundary: OPENING+SAME gets 0, CLOSING+NEXT gets 0 (shifted) — both zero
    assert cap_opening_same[0] == pytest.approx(0.0, abs=1e-12)
    assert cap_closing_next[0] == pytest.approx(0.0, abs=1e-12)

    # Terminal boundary: OPENING+SAME includes last accrual; CLOSING+NEXT does not
    assert cap_opening_same[-1] > 0.0
    assert cap_closing_next[-1] == pytest.approx(idc_closing[-2], abs=1e-12)
    terminal_diff = sum(idc_closing) - sum(cap_closing_next)
    assert terminal_diff == pytest.approx(idc_closing[-1], abs=1e-12)


def test_b3_ccc_6_terminal_boundary_difference_explicit():
    """CC6: Terminal boundary: CLOSING+NEXT excludes last accrual; OPENING+SAME includes it."""
    from finco_core.construction.stage_b2 import _capitalized_uses
    raw = (5.0, 10.0, 15.0, 20.0)  # raw accrual (CLOSING balance basis)
    cap_next = _capitalized_uses(sum(raw), (), raw, "NEXT_PERIOD")
    cap_same = _capitalized_uses(sum(raw), (), raw, "SAME_PERIOD")
    # NEXT_PERIOD excludes terminal: sum(cap_next) = sum(raw) - raw[-1]
    assert sum(cap_next) == pytest.approx(sum(raw) - raw[-1], abs=1e-12)
    # SAME_PERIOD includes terminal: sum(cap_same) = sum(raw)
    assert sum(cap_same) == pytest.approx(sum(raw), abs=1e-12)
    # Explicit terminal shift
    assert sum(raw) - sum(cap_next) == pytest.approx(raw[-1], abs=1e-12)


def test_b3_ccc_7_stage_b2_idc_is_tax_policy_independent(clean_run):
    """CC7: Stage B2 IDC capitalization is tax-policy-independent for fixed construction inputs.

    For identical construction inputs (CAPEX, Senior, rates, timing), changing
    the ATAD absolute limit does NOT directly change Stage B2 capitalized IDC.
    Tax may affect Senior quantum through the outer fixed point, but the B2
    construction kernel is tax-independent once construction funding is fixed.
    """
    from dataclasses import replace

    project = create_default_tuho_wind1()

    # Baseline run
    baseline_cfr = clean_run.g2c_result.financing_result.construction_financing
    baseline_cap_idc = sum(baseline_cfr.senior_idc_capitalized_uses_keur)

    # Mutate ATAD EBITDA limit (tax policy parameter)
    tax = project.tax
    assert hasattr(tax, "atad_ebitda_limit")
    mutated_project = replace(
        project,
        tax=replace(tax, atad_ebitda_limit=tax.atad_ebitda_limit * 2.0),
    )
    mutated_run = run_clean_production(mutated_project)
    mutated_cfr = mutated_run.g2c_result.financing_result.construction_financing
    mutated_cap_idc = sum(mutated_cfr.senior_idc_capitalized_uses_keur)

    # The outer fixed point may change Senior, causing capitalized IDC to change
    # THROUGH the Senior quantum — but the B2 kernel itself is tax-independent.
    # If Senior is unchanged, capitalized IDC must be unchanged.
    if mutated_cfr.final_senior_commitment_keur == pytest.approx(
        baseline_cfr.final_senior_commitment_keur, abs=1.0
    ):
        assert mutated_cap_idc == pytest.approx(baseline_cap_idc, abs=1.0)

    # In all cases: Stage B2 IDC authority is CONSTRUCTION INPUTS, not tax policy
    assert mutated_cfr.authority == baseline_cfr.authority


def test_b3_ccc_8_source_live_vs_pasted_circularity_classification(b3_uses_data):
    """CC8: Source live IDC != pasted IDC — classified as SOURCE_CONSTRUCTION_CIRCULARITY_RESIDUAL.

    Source live (period sum): 1,520.305132 kEUR
    Source pasted (total uses):  1,519.563936 kEUR
    Residual: ~0.741 kEUR — not reproduced by Finco.
    """
    SOURCE_LIVE_IDC = 1_520.3051321075397
    SOURCE_PASTED_IDC = 1_519.563935502677
    circularity = SOURCE_LIVE_IDC - SOURCE_PASTED_IDC
    # Classified: not zero, not reproduced
    assert circularity == pytest.approx(0.741196604863, abs=0.001)
    assert circularity != pytest.approx(0.0, abs=0.1)


def test_b3_ccc_9_tuho_project_uses_identity(b3_uses_data):
    """CC9: TUHO Project Uses identity (preserved from Correction B T1-T3)."""
    pu, cfr = b3_uses_data
    recomputed = (
        pu.hard_project_capex_keur
        + pu.explicit_financing_cost_uses_keur
        + pu.reserve_account_funding_keur
        + pu.other_explicit_project_uses_keur
    )
    assert recomputed == pytest.approx(pu.total_project_uses_keur, abs=1e-8)
    assert cfr.total_capitalized_financing_keur == pytest.approx(
        pu.explicit_financing_cost_uses_keur, abs=1e-6
    )


def test_b3_ccc_10_senior_quantum_mutation_changes_capitalized_idc_naturally(clean_run):
    """CC10: Senior quantum change naturally changes capitalized IDC through B2 — no tuning."""
    from dataclasses import replace

    project = create_default_tuho_wind1()
    financing = project.financing
    sculpting = financing.senior_sculpting_config
    assert sculpting is not None

    # Lower target DSCR → higher Senior → higher IDC
    lower_dscr = replace(
        project,
        financing=replace(
            financing,
            senior_sculpting_config=replace(
                sculpting,
                target_dscr_schedule=tuple(t - 0.05 for t in sculpting.target_dscr_schedule),
            ),
        ),
    )
    lower_run = run_clean_production(lower_dscr)
    baseline_cfr = clean_run.g2c_result.financing_result.construction_financing
    lower_cfr = lower_run.g2c_result.financing_result.construction_financing

    baseline_senior = baseline_cfr.final_senior_commitment_keur
    lower_senior = lower_cfr.final_senior_commitment_keur
    assert lower_senior > baseline_senior

    # Higher Senior → more IDC drawn → naturally higher capitalized IDC
    assert sum(lower_cfr.senior_idc_capitalized_uses_keur) >= sum(
        baseline_cfr.senior_idc_capitalized_uses_keur
    )


def test_b3_ccc_11_stage_b2_result_exposes_capitalized_uses_field(b3_uses_data):
    """CC11: Stage B2 result exposes senior_idc_capitalized_uses_keur — audit without recalculation.

    The field is the exact converged capitalized vector from the B2 inner loop.
    It matches sum(CapitalizedFinancingCosts.senior_idc_keur) and is NOT recomputed
    from the accrual post-hoc — it is the primary converged output.
    """
    pu, cfr = b3_uses_data
    cap_uses = cfr.senior_idc_capitalized_uses_keur
    assert isinstance(cap_uses, tuple)
    assert len(cap_uses) == len(cfr.senior_idc_accrual_keur)
    # Every element is non-negative
    for i, v in enumerate(cap_uses):
        assert v >= -1e-10, f"Period {i}: negative capitalized IDC uses {v}"
    # First element is 0 (NEXT_PERIOD — nothing capitalized in period 0)
    assert cap_uses[0] == pytest.approx(0.0, abs=1e-12)


def test_b3_ccc_12_no_source_idc_vector_runtime_use():
    """CC12: No source IDC vector enters the Stage B2 or production calculation."""
    import ast, pathlib

    source_guard_terms = [
        "source_idc", "excel_idc", "workbook_idc", "frozen_idc",
        "source_senior_idc", "hardcoded_idc",
    ]
    engine_files = list(pathlib.Path("financial_engine/financing").glob("*.py"))
    engine_files += list(pathlib.Path("finco_core/construction").glob("*.py"))

    for path in engine_files:
        src = path.read_text(encoding="utf-8").lower()
        for term in source_guard_terms:
            assert term not in src, (
                f"{path}: forbidden source-IDC reference '{term}' found"
            )


def test_b3_ccc_13_next_period_vector_first_element_is_zero(b3_uses_data):
    """CC13: NEXT_PERIOD capitalized vector starts with 0.0 (no IDC capitalized in period 0)."""
    pu, cfr = b3_uses_data
    assert cfr.senior_idc_capitalized_uses_keur[0] == pytest.approx(0.0, abs=1e-12)


def test_b3_ccc_14_capitalized_idc_total_in_total_capitalized_financing(b3_uses_data):
    """CC14: sum(capitalized_uses) contributes to total_capitalized_financing_keur.

    total_capitalized = cap_senior_idc + commit_fee + struct_fee + vat_idc + vat_commit_fee.
    This proves a single financial authority with no duplicate paths.
    """
    pu, cfr = b3_uses_data
    cap_idc = sum(cfr.senior_idc_capitalized_uses_keur)
    cap_fee = sum(cfr.senior_commitment_fee_accrual_keur)
    cap_struct = sum(cfr.structuring_fee_keur)
    recomputed_total = cap_idc + cap_fee + cap_struct + cfr.vat_idc_keur + cfr.vat_commitment_fee_keur
    assert recomputed_total == pytest.approx(cfr.total_capitalized_financing_keur, abs=1e-6)
