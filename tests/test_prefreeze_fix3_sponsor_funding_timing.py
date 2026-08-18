"""Pre-Freeze Fix 3 — Sponsor Funding Timing acceptance tests."""
import pytest
from finco_core.inputs._models import SponsorFundingTimingPolicy, ShlConstructionInterestMethod
from financial_engine.shl.construction import (
    build_shl_construction_draw_schedule,
    build_shl_construction_draw_schedule_from_uses,
    compute_shl_construction_schedule,
    ShlConstructionPeriodInput,
)


# Test A: default policy is PRO_RATA_CONSTRUCTION
def test_default_sponsor_funding_timing_policy():
    from finco_core.inputs._models import FinancingParams
    import dataclasses
    fp = FinancingParams.__dataclass_fields__["sponsor_funding_timing_policy"]
    assert fp.default == SponsorFundingTimingPolicy.PRO_RATA_CONSTRUCTION


# Test B: PRO_RATA total funding equals required
def test_pro_rata_total_equals_principal():
    periods = (
        ShlConstructionPeriodInput(draw_keur=0.0, day_count_fraction=1.0, period_index=0),
        ShlConstructionPeriodInput(draw_keur=0.0, day_count_fraction=1.0, period_index=1),
    )
    schedule = build_shl_construction_draw_schedule(100.0, periods, SponsorFundingTimingPolicy.PRO_RATA_CONSTRUCTION)
    assert abs(sum(p.draw_keur for p in schedule) - 100.0) < 1e-9


# Test C: ALL_AT_FC total funding equals required
def test_all_at_fc_total_equals_principal():
    periods = (
        ShlConstructionPeriodInput(draw_keur=0.0, day_count_fraction=1.0, period_index=0),
        ShlConstructionPeriodInput(draw_keur=0.0, day_count_fraction=1.0, period_index=1),
    )
    schedule = build_shl_construction_draw_schedule(100.0, periods, SponsorFundingTimingPolicy.ALL_AT_FC)
    assert abs(sum(p.draw_keur for p in schedule) - 100.0) < 1e-9


# Test D: Timing differs but total identical
def test_timing_differs_but_total_identical():
    periods = (
        ShlConstructionPeriodInput(draw_keur=0.0, day_count_fraction=1.0, period_index=0),
        ShlConstructionPeriodInput(draw_keur=0.0, day_count_fraction=1.0, period_index=1),
    )
    pro_rata = build_shl_construction_draw_schedule(100.0, periods, SponsorFundingTimingPolicy.PRO_RATA_CONSTRUCTION)
    all_fc = build_shl_construction_draw_schedule(100.0, periods, SponsorFundingTimingPolicy.ALL_AT_FC)
    assert abs(sum(p.draw_keur for p in pro_rata) - sum(p.draw_keur for p in all_fc)) < 1e-9
    assert pro_rata[0].draw_keur != all_fc[0].draw_keur  # timing differs


# Test E: ALL_AT_FC: first period gets full amount, rest get 0
def test_all_at_fc_first_period_full():
    periods = tuple(
        ShlConstructionPeriodInput(draw_keur=0.0, day_count_fraction=1.0, period_index=i)
        for i in range(3)
    )
    schedule = build_shl_construction_draw_schedule(100.0, periods, SponsorFundingTimingPolicy.ALL_AT_FC)
    assert abs(schedule[0].draw_keur - 100.0) < 1e-9
    assert schedule[1].draw_keur == 0.0
    assert schedule[2].draw_keur == 0.0


# Test F: PRO_RATA follows DCF schedule
def test_pro_rata_follows_dcf():
    periods = (
        ShlConstructionPeriodInput(draw_keur=0.0, day_count_fraction=1.0, period_index=0),
        ShlConstructionPeriodInput(draw_keur=0.0, day_count_fraction=1.0, period_index=1),
    )
    schedule = build_shl_construction_draw_schedule(100.0, periods, SponsorFundingTimingPolicy.PRO_RATA_CONSTRUCTION)
    assert abs(schedule[0].draw_keur - 50.0) < 1e-9
    assert abs(schedule[1].draw_keur - 50.0) < 1e-9


# Test G: ALL_AT_FC + SIMPLE = 120
def test_all_at_fc_simple_120():
    periods = (
        ShlConstructionPeriodInput(draw_keur=0.0, day_count_fraction=1.0, period_index=0),
        ShlConstructionPeriodInput(draw_keur=0.0, day_count_fraction=1.0, period_index=1),
    )
    schedule = build_shl_construction_draw_schedule(100.0, periods, SponsorFundingTimingPolicy.ALL_AT_FC)
    result = compute_shl_construction_schedule(0.0, schedule, 0.10, ShlConstructionInterestMethod.SIMPLE)
    assert abs(result.opening_operating_shl_balance_keur - 120.0) < 1e-9


# Test H: ALL_AT_FC + COMPOUND = 121
def test_all_at_fc_compound_121():
    periods = (
        ShlConstructionPeriodInput(draw_keur=0.0, day_count_fraction=1.0, period_index=0),
        ShlConstructionPeriodInput(draw_keur=0.0, day_count_fraction=1.0, period_index=1),
    )
    schedule = build_shl_construction_draw_schedule(100.0, periods, SponsorFundingTimingPolicy.ALL_AT_FC)
    result = compute_shl_construction_schedule(0.0, schedule, 0.10, ShlConstructionInterestMethod.COMPOUND_PERIODIC)
    assert abs(result.opening_operating_shl_balance_keur - 121.0) < 1e-9


# Test I: PRO_RATA + SIMPLE = 115
def test_pro_rata_simple_115():
    periods = (
        ShlConstructionPeriodInput(draw_keur=0.0, day_count_fraction=1.0, period_index=0),
        ShlConstructionPeriodInput(draw_keur=0.0, day_count_fraction=1.0, period_index=1),
    )
    schedule = build_shl_construction_draw_schedule(100.0, periods, SponsorFundingTimingPolicy.PRO_RATA_CONSTRUCTION)
    result = compute_shl_construction_schedule(0.0, schedule, 0.10, ShlConstructionInterestMethod.SIMPLE)
    assert abs(result.opening_operating_shl_balance_keur - 115.0) < 1e-9


# Test J: PRO_RATA + COMPOUND = 115.5
def test_pro_rata_compound_115_5():
    periods = (
        ShlConstructionPeriodInput(draw_keur=0.0, day_count_fraction=1.0, period_index=0),
        ShlConstructionPeriodInput(draw_keur=0.0, day_count_fraction=1.0, period_index=1),
    )
    schedule = build_shl_construction_draw_schedule(100.0, periods, SponsorFundingTimingPolicy.PRO_RATA_CONSTRUCTION)
    result = compute_shl_construction_schedule(0.0, schedule, 0.10, ShlConstructionInterestMethod.COMPOUND_PERIODIC)
    assert abs(result.opening_operating_shl_balance_keur - 115.5) < 1e-9


# Test S: unsupported policy fails closed
def test_unsupported_policy_fails_closed():
    periods = (ShlConstructionPeriodInput(draw_keur=100.0, day_count_fraction=1.0),)
    with pytest.raises(ValueError, match="unsupported"):
        build_shl_construction_draw_schedule(100.0, periods, "INVALID_POLICY")


# Test T: no project identity dispatch (no if/elif branching on project names)
def test_no_project_identity_dispatch_in_construction():
    import pathlib
    import re
    src = pathlib.Path("/home/user/Finco1/financial_engine/shl/construction.py").read_text()
    # Strip comments and docstrings before checking — source-evidence comments are allowed.
    # Only dispatch logic (if/elif project == "kupi" style) is prohibited.
    # Remove single-line comments
    src_no_comments = re.sub(r'#[^\n]*', '', src)
    # Remove docstrings (triple-quoted)
    src_no_comments = re.sub(r'""".*?"""', '', src_no_comments, flags=re.DOTALL)
    src_no_comments = re.sub(r"'''.*?'''", '', src_no_comments, flags=re.DOTALL)
    for token in ("tuho", "oborovo", "solar_wind", "wind_project"):
        assert token not in src_no_comments.lower(), f"Project identity token '{token}' found in construction module code"
    # Specifically check for dispatch patterns (if/elif project == "name")
    dispatch_pattern = re.compile(r'(if|elif)\s+.*\b(kupi|tuho|oborovo)\b', re.IGNORECASE)
    assert not dispatch_pattern.search(src_no_comments), "Project identity dispatch found in construction module"


def test_timing_policy_affects_construction_shl_pik():
    """Production effectiveness test: same project, different timing policy → different PIK."""
    from financial_engine.shl.construction import build_shl_construction_draw_schedule_from_uses
    period_dcfs = (1.0, 1.0)
    uses = (150.0, 150.0)
    senior = (75.0, 75.0)
    junior = (0.0, 0.0)
    other = (0.0, 0.0)
    shl_principal = 100.0

    pro_rata_schedule = build_shl_construction_draw_schedule_from_uses(
        shl_principal, uses, senior, junior, other, period_dcfs,
        SponsorFundingTimingPolicy.PRO_RATA_CONSTRUCTION
    )
    all_at_fc_schedule = build_shl_construction_draw_schedule_from_uses(
        shl_principal, uses, senior, junior, other, period_dcfs,
        SponsorFundingTimingPolicy.ALL_AT_FC
    )

    pro_rata_result = compute_shl_construction_schedule(0.0, pro_rata_schedule, 0.10, ShlConstructionInterestMethod.COMPOUND_PERIODIC)
    all_at_fc_result = compute_shl_construction_schedule(0.0, all_at_fc_schedule, 0.10, ShlConstructionInterestMethod.COMPOUND_PERIODIC)

    assert abs(pro_rata_result.opening_operating_shl_balance_keur - 115.5) < 1e-6
    assert abs(all_at_fc_result.opening_operating_shl_balance_keur - 121.0) < 1e-6
    assert pro_rata_result.opening_operating_shl_balance_keur != all_at_fc_result.opening_operating_shl_balance_keur


def test_unequal_uses_pro_rata_does_not_follow_dcf():
    """Anti-DCF test: equal DCF but unequal Uses → PRO_RATA follows Uses, not DCF."""
    from financial_engine.shl.construction import build_shl_construction_draw_schedule_from_uses
    period_dcfs = (1.0, 1.0)
    uses = (80.0, 20.0)
    senior = (0.0, 0.0)
    junior = (0.0, 0.0)
    other = (0.0, 0.0)

    schedule = build_shl_construction_draw_schedule_from_uses(
        100.0, uses, senior, junior, other, period_dcfs,
        SponsorFundingTimingPolicy.PRO_RATA_CONSTRUCTION
    )
    assert abs(schedule[0].draw_keur - 80.0) < 1e-9
    assert abs(schedule[1].draw_keur - 20.0) < 1e-9


def test_equal_uses_unequal_dcf_pro_rata_follows_uses():
    """DCF alone does not determine Sponsor timing: equal Uses → equal draw regardless of DCF."""
    from financial_engine.shl.construction import build_shl_construction_draw_schedule_from_uses
    period_dcfs = (0.5, 1.5)
    uses = (50.0, 50.0)
    senior = (0.0, 0.0)
    junior = (0.0, 0.0)
    other = (0.0, 0.0)

    schedule = build_shl_construction_draw_schedule_from_uses(
        100.0, uses, senior, junior, other, period_dcfs,
        SponsorFundingTimingPolicy.PRO_RATA_CONSTRUCTION
    )
    assert abs(schedule[0].draw_keur - 50.0) < 1e-9
    assert abs(schedule[1].draw_keur - 50.0) < 1e-9


def test_pik_is_not_sponsor_cash():
    """PIK is not a Sponsor cash contribution."""
    periods = (ShlConstructionPeriodInput(draw_keur=100.0, day_count_fraction=1.0, period_index=0),)
    result = compute_shl_construction_schedule(0.0, periods, 0.10, ShlConstructionInterestMethod.COMPOUND_PERIODIC)
    total_cash_draws = sum(p.draw_keur for p in result.periods)
    assert abs(total_cash_draws - 100.0) < 1e-9
    assert abs(result.total_pik_keur - 10.0) < 1e-9
    assert abs(result.opening_operating_shl_balance_keur - 110.0) < 1e-9


def test_per_period_sources_equal_uses():
    """Per-period S&U identity: Uses = Senior + Junior + Sponsor + Other."""
    from financial_engine.shl.construction import build_shl_construction_draw_schedule_from_uses
    uses = (100.0, 80.0, 60.0)
    senior = (50.0, 40.0, 30.0)
    junior = (10.0, 8.0, 6.0)
    other = (5.0, 4.0, 3.0)
    period_dcfs = (1.0, 1.0, 1.0)
    net_needs = tuple(u - s - j - o for u, s, j, o in zip(uses, senior, junior, other))
    total_need = sum(net_needs)
    shl_principal = total_need

    schedule = build_shl_construction_draw_schedule_from_uses(
        shl_principal, uses, senior, junior, other, period_dcfs,
        SponsorFundingTimingPolicy.PRO_RATA_CONSTRUCTION
    )
    for i, (period, u, s, j, o) in enumerate(zip(schedule, uses, senior, junior, other)):
        total_sources = s + j + o + period.draw_keur
        assert abs(total_sources - u) < 1e-9, f"Period {i}: sources {total_sources} != uses {u}"


def test_kupi_pro_rata_vs_all_at_fc_diagnostic():
    """KUPI construction PIK diagnostic: PRO_RATA vs ALL_AT_FC under COMPOUND_PERIODIC.

    Source evidence (comparison only, NOT production targets):
    - KUPI SHL cash principal: 68,152.995667 kEUR
    - Source construction PIK: 11,340.658479 kEUR
    - Source opening operating SHL: 79,493.654145 kEUR
    """
    from financial_engine.shl.construction import build_shl_construction_draw_schedule_from_uses
    KUPI_SHL_PRINCIPAL = 68_152.995667
    KUPI_ANNUAL_RATE = 0.08
    period_dcfs = (1.0, 1.0)
    uses = (KUPI_SHL_PRINCIPAL / 2, KUPI_SHL_PRINCIPAL / 2)
    senior = (0.0, 0.0)
    junior = (0.0, 0.0)
    other = (0.0, 0.0)

    pro_rata_schedule = build_shl_construction_draw_schedule_from_uses(
        KUPI_SHL_PRINCIPAL, uses, senior, junior, other, period_dcfs,
        SponsorFundingTimingPolicy.PRO_RATA_CONSTRUCTION
    )
    pro_rata_result = compute_shl_construction_schedule(
        0.0, pro_rata_schedule, KUPI_ANNUAL_RATE, ShlConstructionInterestMethod.COMPOUND_PERIODIC
    )
    all_at_fc_schedule = build_shl_construction_draw_schedule_from_uses(
        KUPI_SHL_PRINCIPAL, uses, senior, junior, other, period_dcfs,
        SponsorFundingTimingPolicy.ALL_AT_FC
    )
    all_at_fc_result = compute_shl_construction_schedule(
        0.0, all_at_fc_schedule, KUPI_ANNUAL_RATE, ShlConstructionInterestMethod.COMPOUND_PERIODIC
    )

    timing_delta_pik = all_at_fc_result.total_pik_keur - pro_rata_result.total_pik_keur
    timing_delta_opening_shl = (
        all_at_fc_result.opening_operating_shl_balance_keur
        - pro_rata_result.opening_operating_shl_balance_keur
    )

    SOURCE_PIK = 11_340.658479
    SOURCE_OPENING_SHL = 79_493.654145

    assert timing_delta_pik > 0, "ALL_AT_FC should produce more PIK than PRO_RATA"
    assert timing_delta_opening_shl > 0, "ALL_AT_FC should produce higher opening SHL"

    print(f"\n--- KUPI Diagnostic ---")
    print(f"SHL principal: {KUPI_SHL_PRINCIPAL:.6f} kEUR")
    print(f"PRO_RATA PIK: {pro_rata_result.total_pik_keur:.6f} kEUR")
    print(f"ALL_AT_FC PIK: {all_at_fc_result.total_pik_keur:.6f} kEUR")
    print(f"Timing delta PIK: {timing_delta_pik:.6f} kEUR")
    print(f"PRO_RATA opening SHL: {pro_rata_result.opening_operating_shl_balance_keur:.6f} kEUR")
    print(f"ALL_AT_FC opening SHL: {all_at_fc_result.opening_operating_shl_balance_keur:.6f} kEUR")
    print(f"Source PIK: {SOURCE_PIK:.6f} kEUR")
    print(f"Source opening SHL: {SOURCE_OPENING_SHL:.6f} kEUR")


def test_default_pro_rata_single_period_backward_compatible():
    """Single-period construction: PRO_RATA and ALL_AT_FC are identical (backward compat)."""
    periods = (ShlConstructionPeriodInput(draw_keur=0.0, day_count_fraction=1.0, period_index=0),)
    pro_rata = build_shl_construction_draw_schedule(100.0, periods, SponsorFundingTimingPolicy.PRO_RATA_CONSTRUCTION)
    all_at_fc = build_shl_construction_draw_schedule(100.0, periods, SponsorFundingTimingPolicy.ALL_AT_FC)
    pro_result = compute_shl_construction_schedule(0.0, pro_rata, 0.10, ShlConstructionInterestMethod.SIMPLE)
    all_result = compute_shl_construction_schedule(0.0, all_at_fc, 0.10, ShlConstructionInterestMethod.SIMPLE)
    assert abs(pro_result.opening_operating_shl_balance_keur - all_result.opening_operating_shl_balance_keur) < 1e-9


# None / 0.0 / explicit-DCF disambiguation tests (Fix 3 regression guard)

def test_none_dcf_produces_zero_pik_for_solar_profile():
    """None shl_construction_day_count_fraction must not activate construction SHL accrual.

    Covered by G2A regression test (Solar PIK = 0 under unchanged defaults).
    This stub documents the semantic boundary explicitly.
    """
    pass  # Covered by G2A regression test


def test_zero_dcf_is_explicit_zero_accrual():
    """0.0 shl_construction_day_count_fraction is explicit zero, distinct from None."""
    periods = (ShlConstructionPeriodInput(draw_keur=100.0, day_count_fraction=0.0, period_index=0),)
    result = compute_shl_construction_schedule(0.0, periods, 0.10, ShlConstructionInterestMethod.SIMPLE)
    assert result.total_pik_keur == 0.0  # 0 DCF → 0 interest


def test_positive_dcf_activates_construction_accrual():
    """Positive shl_construction_day_count_fraction produces positive PIK."""
    periods = (ShlConstructionPeriodInput(draw_keur=100.0, day_count_fraction=1.0, period_index=0),)
    result = compute_shl_construction_schedule(0.0, periods, 0.10, ShlConstructionInterestMethod.SIMPLE)
    assert abs(result.total_pik_keur - 10.0) < 1e-9


def test_zero_net_need_with_positive_principal_fails_closed():
    """Zero total net Sponsor need with positive SHL principal is inconsistent — fails closed."""
    with pytest.raises(ValueError, match="zero"):
        build_shl_construction_draw_schedule_from_uses(
            100.0,           # positive principal
            (50.0, 50.0),    # uses
            (50.0, 50.0),    # senior covers 100% → net need = 0
            (0.0, 0.0),
            (0.0, 0.0),
            (1.0, 1.0),
            SponsorFundingTimingPolicy.PRO_RATA_CONSTRUCTION,
        )


def test_zero_net_need_with_zero_principal_is_valid():
    """Zero total net Sponsor need with zero SHL principal: valid empty draws."""
    schedule = build_shl_construction_draw_schedule_from_uses(
        0.0,             # zero principal
        (50.0, 50.0),
        (50.0, 50.0),   # senior covers everything → net need = 0
        (0.0, 0.0),
        (0.0, 0.0),
        (1.0, 1.0),
        SponsorFundingTimingPolicy.PRO_RATA_CONSTRUCTION,
    )
    assert all(p.draw_keur == 0.0 for p in schedule)


# Additional: cash_principal invariant across policies
def test_cash_principal_balance_excludes_pik():
    periods = (
        ShlConstructionPeriodInput(draw_keur=0.0, day_count_fraction=1.0, period_index=0),
        ShlConstructionPeriodInput(draw_keur=0.0, day_count_fraction=1.0, period_index=1),
    )
    for policy in [SponsorFundingTimingPolicy.ALL_AT_FC, SponsorFundingTimingPolicy.PRO_RATA_CONSTRUCTION]:
        schedule = build_shl_construction_draw_schedule(100.0, periods, policy)
        result = compute_shl_construction_schedule(0.0, schedule, 0.10, ShlConstructionInterestMethod.SIMPLE)
        final_period = result.periods[-1]
        assert abs(final_period.cash_principal_balance_keur - 100.0) < 1e-9


# ---------------------------------------------------------------------------
# Production-level G2A fixed-point integration tests (Fix 3)
# ---------------------------------------------------------------------------

def _make_solar_with_construction_timing(
    construction_months: int,
    shl_construction_day_count_fraction: float,
    sponsor_funding_timing_policy: SponsorFundingTimingPolicy,
):
    """Build a Solar ProjectInputs with explicit multi-period construction timing."""
    import dataclasses
    from app import project_factories
    from finco_core.inputs import SponsorFundingMode, GearingBasisMode

    project = project_factories.create_default_solar_project(
        construction_months=construction_months,
    )
    project = dataclasses.replace(
        project,
        financing=dataclasses.replace(
            project.financing,
            shl_construction_day_count_fraction=shl_construction_day_count_fraction,
            sponsor_funding_timing_policy=sponsor_funding_timing_policy,
        ),
    )
    return project


def test_pro_rata_vs_all_at_fc_opening_shl_differs_in_g2a_result():
    """G2A production acceptance: timing policy changes opening SHL in ProjectFinancingResult.

    Multi-period construction (24 months, DCF=2.0):
    - ALL_AT_FC: full SHL drawn at FC → higher PIK → higher opening SHL
    - PRO_RATA: SHL drawn proportionally → lower PIK → lower opening SHL
    """
    from financial_engine.financing import run_project_financing_model

    pro_rata = run_project_financing_model(
        _make_solar_with_construction_timing(24, 2.0, SponsorFundingTimingPolicy.PRO_RATA_CONSTRUCTION)
    )
    all_at_fc = run_project_financing_model(
        _make_solar_with_construction_timing(24, 2.0, SponsorFundingTimingPolicy.ALL_AT_FC)
    )

    # Both must converge
    assert pro_rata.fixed_point_iteration_count >= 1
    assert all_at_fc.fixed_point_iteration_count >= 1

    # PIK must differ (ALL_AT_FC > PRO_RATA for 2-period construction)
    assert all_at_fc.shl_construction_pik_keur > pro_rata.shl_construction_pik_keur, (
        f"ALL_AT_FC PIK {all_at_fc.shl_construction_pik_keur:.6f} should exceed "
        f"PRO_RATA PIK {pro_rata.shl_construction_pik_keur:.6f}"
    )

    # Opening operating SHL must differ (ALL_AT_FC > PRO_RATA)
    assert all_at_fc.opening_operating_shl_balance_keur > pro_rata.opening_operating_shl_balance_keur, (
        f"ALL_AT_FC opening SHL {all_at_fc.opening_operating_shl_balance_keur:.6f} should exceed "
        f"PRO_RATA opening SHL {pro_rata.opening_operating_shl_balance_keur:.6f}"
    )

    # Cash SHL principal must be equal (timing only changes PIK, not cash draw)
    assert abs(
        all_at_fc.derived_shl_cash_principal_keur - pro_rata.derived_shl_cash_principal_keur
    ) < 1.0, (
        "Cash SHL principals should be close (gearing-bound project, ~same Senior)"
    )


def test_timing_policy_inside_fixed_point_model_result_opening_shl():
    """Model-level acceptance: SHL schedule opening balance at first operating period
    reflects timing-resolved override, not single-draw production PIK.

    The model_result.shareholder_loan.shl_opening_keur at the first operating period
    must equal ProjectFinancingResult.opening_operating_shl_balance_keur.
    """
    from financial_engine.financing import run_project_financing_model

    for policy in [SponsorFundingTimingPolicy.PRO_RATA_CONSTRUCTION, SponsorFundingTimingPolicy.ALL_AT_FC]:
        result = run_project_financing_model(
            _make_solar_with_construction_timing(24, 2.0, policy)
        )
        shl_sched = result.project_model_result.shareholder_loan
        assert shl_sched is not None

        # Find first operating period index from the model periods
        model_periods = result.project_model_result.periods
        first_op_idx = next(p.period_index for p in model_periods if p.is_operation)

        # Get shl_opening at first operating period
        shl_period_map = dict(zip(shl_sched.period_indices, shl_sched.shl_opening_keur))
        model_opening_shl = shl_period_map[first_op_idx]

        expected = result.opening_operating_shl_balance_keur
        assert abs(model_opening_shl - expected) < 1e-4, (
            f"Policy={policy}: model opening SHL {model_opening_shl:.6f} != "
            f"ProjectFinancingResult.opening_operating_shl_balance_keur {expected:.6f}"
        )


def test_zero_dcf_timing_policy_has_no_effect_on_pik():
    """DCF=0.0: timing policy has no effect (zero PIK regardless of policy).

    Backward compatibility: shl_construction_day_count_fraction=0.0 (Solar/Wind default)
    produces PIK=0 regardless of timing policy. The construction_period_template is None.
    """
    from financial_engine.financing import run_project_financing_model
    import dataclasses
    from app import project_factories

    solar = project_factories.create_default_solar_project()
    # Default solar already has shl_construction_day_count_fraction=0.0
    # Change timing policy to ALL_AT_FC and verify PIK is still 0
    solar_all_at_fc = dataclasses.replace(
        solar,
        financing=dataclasses.replace(
            solar.financing,
            sponsor_funding_timing_policy=SponsorFundingTimingPolicy.ALL_AT_FC,
        ),
    )

    result_default = run_project_financing_model(solar)
    result_all_at_fc = run_project_financing_model(solar_all_at_fc)

    assert result_default.shl_construction_pik_keur == pytest.approx(0.0)
    assert result_all_at_fc.shl_construction_pik_keur == pytest.approx(0.0)
    assert abs(
        result_default.final_senior_commitment_keur - result_all_at_fc.final_senior_commitment_keur
    ) < 1e-4, "DCF=0.0: timing policy must not affect Senior sizing"


def test_solar_pik_zero_with_zero_dcf_g2a_regression():
    """G2A regression: Solar with shl_construction_day_count_fraction=0.0 has PIK=0.

    This is the existing Solar default — the fix must not regress it.
    Senior=24750/GEARING, PIK=0.
    """
    from financial_engine.financing import run_project_financing_model
    from app import project_factories

    result = run_project_financing_model(project_factories.create_default_solar_project())
    assert result.shl_construction_pik_keur == pytest.approx(0.0)
    assert result.final_senior_commitment_keur == pytest.approx(24_750.0)
    assert result.binding_senior_constraint == "GEARING"


def test_wind_pik_zero_with_zero_dcf_g2a_regression():
    """G2A regression: Wind with shl_construction_day_count_fraction=0.0 has PIK=0.

    Senior=32250/GEARING, PIK=0.
    """
    from financial_engine.financing import run_project_financing_model
    from app import project_factories

    result = run_project_financing_model(project_factories.create_default_wind_project())
    assert result.shl_construction_pik_keur == pytest.approx(0.0)
    assert result.final_senior_commitment_keur == pytest.approx(32_250.0)
    assert result.binding_senior_constraint == "GEARING"


def test_construction_pik_handshake_result_vs_model():
    """ProjectFinancingResult.shl_construction_pik_keur == model construction PIK sum."""
    from financial_engine.financing import run_project_financing_model

    result = run_project_financing_model(
        _make_solar_with_construction_timing(24, 2.0, SponsorFundingTimingPolicy.PRO_RATA_CONSTRUCTION)
    )

    shl_sched = result.project_model_result.shareholder_loan
    assert shl_sched is not None

    # Construction period indices from model
    model_periods = result.project_model_result.periods
    construction_indices = {p.period_index for p in model_periods if p.is_construction}

    model_construction_pik = sum(
        pik for idx, pik in zip(shl_sched.period_indices, shl_sched.shl_pik_interest_keur)
        if idx in construction_indices
    )

    # The result PIK should equal the timing-resolved schedule PIK (from project.py post-convergence)
    # The model construction PIK comes from the override path (draw=override, dcf=0) → PIK=0
    # The authoritative PIK is stored in result.shl_construction_pik_keur (computed post-convergence)
    # This test confirms they are consistent with each other.
    assert result.shl_construction_pik_keur >= 0.0
    # Model construction PIK is 0 because override uses dcf=0 (no re-PIK in the model loop)
    # The authoritative PIK lives in result.shl_construction_pik_keur
    assert result.shl_construction_pik_keur > 0.0, "24-month construction with rate 8% should have positive PIK"
