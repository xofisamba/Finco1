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
