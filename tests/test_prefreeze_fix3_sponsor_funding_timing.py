"""Pre-Freeze Fix 3 — Sponsor Funding Timing acceptance tests."""
import pytest
from finco_core.inputs._models import SponsorFundingTimingPolicy, ShlConstructionInterestMethod
from financial_engine.shl.construction import (
    build_shl_construction_draw_schedule,
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
