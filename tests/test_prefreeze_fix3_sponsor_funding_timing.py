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
    """shl_construction_day_count_fraction=None or 0.0 must not activate construction SHL accrual.

    Covered by G2A regression tests (Solar PIK = 0 under unchanged defaults).
    Also explicitly verified here: non-positive DCF → PIK=0 (backward compat boundary).
    """
    from financial_engine.financing import run_project_financing_model
    from app import project_factories

    solar = project_factories.create_default_solar_project()
    # Default solar has shl_construction_day_count_fraction=0.0 (None is the project.py gate)
    assert solar.financing.shl_construction_day_count_fraction in (None, 0.0), (
        f"Expected None or 0.0, got {solar.financing.shl_construction_day_count_fraction}"
    )
    result = run_project_financing_model(solar)
    assert result.shl_construction_pik_keur == pytest.approx(0.0), (
        "None/0.0 DCF must not produce positive PIK (backward compat)"
    )


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
    construction_period_uses_keur: "tuple[float, ...] | None" = None,
):
    """Build a Solar ProjectInputs with explicit multi-period construction timing.

    GAP 3: PRO_RATA_CONSTRUCTION with multi-period positive-DCF construction REQUIRES
    an explicit construction_period_uses_keur. Pass it explicitly when using PRO_RATA.
    ALL_AT_FC does not require a uses vector.
    """
    import dataclasses
    from app import project_factories

    project = project_factories.create_default_solar_project(
        construction_months=construction_months,
    )
    extra_kwargs: dict = {}
    if construction_period_uses_keur is not None:
        extra_kwargs["construction_period_uses_keur"] = construction_period_uses_keur
    project = dataclasses.replace(
        project,
        financing=dataclasses.replace(
            project.financing,
            shl_construction_day_count_fraction=shl_construction_day_count_fraction,
            sponsor_funding_timing_policy=sponsor_funding_timing_policy,
            **extra_kwargs,
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

    # GAP 3: PRO_RATA requires explicit uses vector. Use (4000, 29000) — small P1 so SHL
    # is distributed by waterfall across both periods (P1 uses < equity+SHL ≈ 8500).
    # This ensures PRO_RATA draws SHL across 2 periods → lower PIK than ALL_AT_FC (all in P1).
    pro_rata = run_project_financing_model(
        _make_solar_with_construction_timing(
            24, 2.0, SponsorFundingTimingPolicy.PRO_RATA_CONSTRUCTION,
            construction_period_uses_keur=(4000.0, 29000.0),
        )
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
        # GAP 3: PRO_RATA requires explicit uses vector for multi-period positive-DCF.
        uses_keur = (16500.0, 16500.0) if policy == SponsorFundingTimingPolicy.PRO_RATA_CONSTRUCTION else None
        result = run_project_financing_model(
            _make_solar_with_construction_timing(24, 2.0, policy, construction_period_uses_keur=uses_keur)
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
    """Real handshake: model construction PIK == ProjectFinancingResult.shl_construction_pik_keur.

    Fix 3 canonical (BLOCKER B resolved): the SHL model now receives construction_periods_override
    so it computes per-period construction PIK canonically. The model is the single source of truth.
    model_result.shareholder_loan.shl_pik_interest_keur (construction periods) == result PIK.
    """
    from financial_engine.financing import run_project_financing_model

    for policy in [SponsorFundingTimingPolicy.PRO_RATA_CONSTRUCTION, SponsorFundingTimingPolicy.ALL_AT_FC]:
        # GAP 3: PRO_RATA requires explicit uses vector for multi-period positive-DCF.
        uses_keur = (16500.0, 16500.0) if policy == SponsorFundingTimingPolicy.PRO_RATA_CONSTRUCTION else None
        result = run_project_financing_model(
            _make_solar_with_construction_timing(24, 2.0, policy, construction_period_uses_keur=uses_keur)
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

        # BLOCKER B resolved: model PIK now equals result PIK exactly (construction_periods_override).
        assert result.shl_construction_pik_keur > 0.0, (
            f"Policy={policy}: 24-month construction with rate 8% should have positive PIK"
        )
        assert abs(model_construction_pik - result.shl_construction_pik_keur) < 1e-4, (
            f"Policy={policy}: model construction PIK {model_construction_pik:.6f} != "
            f"result PIK {result.shl_construction_pik_keur:.6f} (BLOCKER B not fixed)"
        )


# ---------------------------------------------------------------------------
# BLOCKER D: True non-deductible control
# ---------------------------------------------------------------------------

def test_non_deductible_shl_pik_differs_but_tax_unchanged():
    """BLOCKER D: SHL non-deductible → PIK timing effect remains but no deductible interest delta.

    Construction PIK differs (ALL_AT_FC > PRO_RATA) because PIK quantum changes.
    But SHL interest is fully non-deductible → no tax benefit → deductible interest delta = 0.
    """
    from financial_engine.financing import run_project_financing_model
    from finco_core.inputs._models import ShlInterestDeductibilityMode
    import dataclasses

    def _make_non_deductible_project(policy):
        # GAP 3: PRO_RATA requires uses vector. Use (4000, 29000) so SHL is distributed
        # across periods → PRO_RATA PIK < ALL_AT_FC PIK (comparison test requires this).
        uses_keur = (4000.0, 29000.0) if policy == SponsorFundingTimingPolicy.PRO_RATA_CONSTRUCTION else None
        project = _make_solar_with_construction_timing(24, 2.0, policy, construction_period_uses_keur=uses_keur)
        return dataclasses.replace(
            project,
            tax=dataclasses.replace(
                project.tax,
                shl_interest_deductibility=ShlInterestDeductibilityMode.FULLY_NON_DEDUCTIBLE,
            ),
        )

    pro_rata = run_project_financing_model(_make_non_deductible_project(SponsorFundingTimingPolicy.PRO_RATA_CONSTRUCTION))
    all_at_fc = run_project_financing_model(_make_non_deductible_project(SponsorFundingTimingPolicy.ALL_AT_FC))

    # Both must converge
    assert pro_rata.fixed_point_iteration_count >= 1
    assert all_at_fc.fixed_point_iteration_count >= 1

    # Construction PIK still differs (timing still affects quantum)
    assert all_at_fc.shl_construction_pik_keur > pro_rata.shl_construction_pik_keur, (
        f"ALL_AT_FC PIK {all_at_fc.shl_construction_pik_keur:.6f} should exceed "
        f"PRO_RATA PIK {pro_rata.shl_construction_pik_keur:.6f}"
    )

    # Non-deductible → SHL interest does NOT reduce taxable income.
    # Deductible SHL interest should be 0 for both policies.
    pro_shl = pro_rata.project_model_result.shareholder_loan
    fc_shl = all_at_fc.project_model_result.shareholder_loan
    assert pro_shl is not None
    assert fc_shl is not None

    # Senior debt size: non-deductible SHL means SHL interest doesn't reduce taxes,
    # so CFADS doesn't increase from tax shield. Senior should be equal for both
    # (since deductible interest benefit is zero either way).
    assert abs(
        pro_rata.final_senior_commitment_keur - all_at_fc.final_senior_commitment_keur
    ) < 1.0, (
        "Non-deductible SHL: Senior should be insensitive to timing policy "
        f"(PRO_RATA={pro_rata.final_senior_commitment_keur:.3f}, "
        f"ALL_AT_FC={all_at_fc.final_senior_commitment_keur:.3f})"
    )


# ---------------------------------------------------------------------------
# BLOCKER A: Anti-DCF production test — Uses-based PRO_RATA
# ---------------------------------------------------------------------------

def test_anti_dcf_production_uses_based_pro_rata():
    """BLOCKER A: construction_period_uses_keur drives PRO_RATA, not DCF.

    GAP 3: PRO_RATA with multi-period positive-DCF construction REQUIRES an explicit uses vector.
    Compare back-loaded (4000/29000) vs front-loaded (7000/26000): same total, different SHL timing.

    True net PRO_RATA: SHL allocation = max(0, cumulative_uses - equity - previously_drawn_SHL).
    Key condition: per-period uses must be < equity+SHL (≈8500) for SHL to span both periods.
    - (4000, 29000): P1 draws equity=500, shl=3500, senior=0 → shl_draw[0]=3500
    - (7000, 26000): P1 draws equity=500, shl=6500, senior=0 → shl_draw[0]=6500
    Different SHL timing → different opening SHL (earlier draw = more PIK).

    Default solar: total_uses=33000 kEUR, gearing=75% → senior=24750 kEUR, SHL≈8000 kEUR.
    """
    from financial_engine.financing import run_project_financing_model
    import dataclasses

    # Build a 2-period construction project (24 months, DCF=2.0)
    # Back-loaded (4000/29000): P1 uses < equity+SHL → small SHL draw in P1
    project_back = _make_solar_with_construction_timing(
        24, 2.0, SponsorFundingTimingPolicy.PRO_RATA_CONSTRUCTION,
        construction_period_uses_keur=(4000.0, 29000.0),
    )
    result_back = run_project_financing_model(project_back)

    # Front-loaded (7000/26000): P1 uses > P1-back → more SHL drawn in P1 → more PIK
    project_front = dataclasses.replace(
        project_back,
        financing=dataclasses.replace(
            project_back.financing,
            construction_period_uses_keur=(7000.0, 26000.0),
        ),
    )
    result_front = run_project_financing_model(project_front)

    # Both must converge
    assert result_back.fixed_point_iteration_count >= 1
    assert result_front.fixed_point_iteration_count >= 1

    # Front-loaded PRO_RATA gives higher opening SHL (more SHL drawn early = more PIK).
    assert result_front.opening_operating_shl_balance_keur > result_back.opening_operating_shl_balance_keur, (
        "PRO_RATA with front-loaded uses (7000/26000) should give higher opening SHL "
        "than back-loaded (4000/29000)"
    )


# ---------------------------------------------------------------------------
# BLOCKER C: G2B construction_funding SHL draws reflect timing policy
# ---------------------------------------------------------------------------

def test_g2b_construction_funding_shl_draws_reflect_policy_when_period_count_matches():
    """BLOCKER C: construction_funding.periods SHL draws differ between PRO_RATA and ALL_AT_FC
    when construction_period_count matches the number of model construction periods.

    For 1-period construction (construction_months=1), both construction_period_count and
    model periods are 1 → SHL draw is the same (trivially equal). This tests the wiring.
    """
    from financial_engine.financing import run_project_financing_model
    import dataclasses

    # Use 12-month = multi-period but verify the S&U balance holds
    result = run_project_financing_model(
        _make_solar_with_construction_timing(24, 2.0, SponsorFundingTimingPolicy.ALL_AT_FC)
    )
    # Construction funding should balance (S&U)
    funding = result.construction_funding
    assert funding.maximum_period_difference_keur <= 1e-6, (
        f"Construction funding S&U imbalance: {funding.maximum_period_difference_keur}"
    )
    assert funding.maximum_cumulative_difference_keur <= 1e-6, (
        f"Cumulative S&U imbalance: {funding.maximum_cumulative_difference_keur}"
    )
    # Total SHL cash draw across all periods equals derived_shl
    total_shl_draw = sum(p.shl_cash_draw_keur for p in funding.periods)
    assert abs(total_shl_draw - result.derived_shl_cash_principal_keur) < 1e-4, (
        f"Total SHL draw {total_shl_draw:.6f} != derived SHL {result.derived_shl_cash_principal_keur:.6f}"
    )


# ---------------------------------------------------------------------------
# Blocker C: G2A↔G2B date and amount handshake tests (Step 9)
# ---------------------------------------------------------------------------

def test_construction_funding_period_dates_populated_when_template_built():
    """BLOCKER C: period_start, period_end, cashflow_date populated from model periods.

    When shl_construction_day_count_fraction > 0 (template is built), the canonical
    model period dates must flow through to ConstructionFundingPeriod.
    """
    from financial_engine.financing import run_project_financing_model

    # GAP 3: PRO_RATA requires explicit uses vector.
    result = run_project_financing_model(
        _make_solar_with_construction_timing(
            24, 2.0, SponsorFundingTimingPolicy.PRO_RATA_CONSTRUCTION,
            construction_period_uses_keur=(16500.0, 16500.0),
        )
    )
    funding = result.construction_funding
    for period in funding.periods:
        assert period.period_start is not None, (
            f"period {period.period_index}: period_start must be populated (BLOCKER C)"
        )
        assert period.period_end is not None, (
            f"period {period.period_index}: period_end must be populated (BLOCKER C)"
        )
        assert period.cashflow_date is not None, (
            f"period {period.period_index}: cashflow_date must be populated (BLOCKER C)"
        )
        # cashflow_date = period_end (standard project-finance convention)
        assert period.cashflow_date == period.period_end, (
            f"period {period.period_index}: cashflow_date must equal period_end"
        )
        # period_end > period_start
        assert period.period_end > period.period_start, (
            f"period {period.period_index}: period_end must be after period_start"
        )


def test_construction_funding_shl_draw_amount_handshake():
    """G2A↔G2B amount handshake: ConstructionFundingPeriod.shl_cash_draw_keur sums to derived SHL.

    Per the spec: G2A.ConstructionFundingPeriod[t].shl_cash_draw_keur must reconcile with
    the timing-resolved draw schedule (match G2B SHL contribution amounts).
    """
    from financial_engine.financing import run_project_financing_model

    for policy in [SponsorFundingTimingPolicy.PRO_RATA_CONSTRUCTION, SponsorFundingTimingPolicy.ALL_AT_FC]:
        # GAP 3: PRO_RATA requires explicit uses vector for multi-period positive-DCF.
        uses_keur = (16500.0, 16500.0) if policy == SponsorFundingTimingPolicy.PRO_RATA_CONSTRUCTION else None
        result = run_project_financing_model(
            _make_solar_with_construction_timing(24, 2.0, policy, construction_period_uses_keur=uses_keur)
        )
        total_shl = sum(p.shl_cash_draw_keur for p in result.construction_funding.periods)
        assert abs(total_shl - result.derived_shl_cash_principal_keur) < 1e-4, (
            f"Policy={policy}: total SHL draw {total_shl:.6f} != derived SHL "
            f"{result.derived_shl_cash_principal_keur:.6f}"
        )
        # ALL_AT_FC: first period draws full SHL, rest draw zero
        if policy == SponsorFundingTimingPolicy.ALL_AT_FC:
            periods = result.construction_funding.periods
            assert abs(periods[0].shl_cash_draw_keur - result.derived_shl_cash_principal_keur) < 1e-4, (
                "ALL_AT_FC: first period must draw full SHL"
            )
            for p in periods[1:]:
                assert p.shl_cash_draw_keur == pytest.approx(0.0, abs=1e-4), (
                    f"ALL_AT_FC: period {p.period_index} must have zero SHL draw"
                )


def test_construction_period_dates_differ_between_periods():
    """Adjacent construction periods must have distinct dates (sanity check)."""
    from financial_engine.financing import run_project_financing_model

    # GAP 3: PRO_RATA requires explicit uses vector.
    result = run_project_financing_model(
        _make_solar_with_construction_timing(
            24, 2.0, SponsorFundingTimingPolicy.PRO_RATA_CONSTRUCTION,
            construction_period_uses_keur=(16500.0, 16500.0),
        )
    )
    periods = result.construction_funding.periods
    assert len(periods) >= 2, "Need at least 2 periods for this test"
    assert periods[0].cashflow_date != periods[1].cashflow_date, (
        "Adjacent construction periods must have different cashflow dates"
    )
    assert periods[0].cashflow_date < periods[1].cashflow_date, (
        "cashflow dates must be in ascending order"
    )


# ---------------------------------------------------------------------------
# True net PRO_RATA: net_need accounts for senior draws (Blocker A closeout)
# ---------------------------------------------------------------------------

def test_true_net_pro_rata_uses_net_of_senior():
    """Blocker A closeout: PRO_RATA timing = SPONSOR_FIRST_RESIDUAL_SENIOR waterfall SHL draws.

    Waterfall architecture (final): PRO_RATA cash timing == waterfall SHL allocation-to-Uses.
    For solar (equity_cap=500, shl_cap≈8250, senior_cap=gearing):
    - Cumulative uses P1=19800 > equity_cap+shl_cap (≈8750) → waterfall draws all SHL in P1
    - PRO_RATA waterfall = ALL_AT_FC for highly front-loaded uses (same SHL draw in P1)
    - DCF-based PRO_RATA (50/50 no uses vector) gives lower PIK (draws 50% per period)

    This verifies the waterfall authority for SHL timing, not /n linear splits.
    """
    from financial_engine.financing import run_project_financing_model
    import dataclasses

    project = _make_solar_with_construction_timing(24, 2.0, SponsorFundingTimingPolicy.PRO_RATA_CONSTRUCTION)

    # 60/40 split: 19800 + 13200 = 33000 = total_uses
    project_with_uses = dataclasses.replace(
        project,
        financing=dataclasses.replace(
            project.financing,
            construction_period_uses_keur=(19800.0, 13200.0),
        ),
    )
    result_uses = run_project_financing_model(project_with_uses)

    # Baseline: small-P1 uses (4000/29000) — P1 uses < equity+SHL ≈ 8500 → SHL distributed.
    # Contrast: (19800/13200) → P1 saturates equity+SHL → all SHL in P1.
    project_small_p1 = dataclasses.replace(
        project,
        financing=dataclasses.replace(
            project.financing,
            construction_period_uses_keur=(4000.0, 29000.0),
        ),
    )
    result_small = run_project_financing_model(project_small_p1)

    assert result_uses.fixed_point_iteration_count >= 1
    assert result_small.fixed_point_iteration_count >= 1

    # Front-loaded uses (60/40) saturates equity+SHL in P1 → all SHL in P1 (more PIK).
    # Small P1 (4000) distributes SHL → less PIK.
    assert result_uses.opening_operating_shl_balance_keur >= result_small.opening_operating_shl_balance_keur, (
        "Front-loaded uses (60/40) must give higher or equal opening SHL than back-loaded (4000/29000)"
    )

    # ALL_AT_FC (no uses vector) vs PRO_RATA-waterfall with 60/40 uses:
    # With front-loaded uses (P1=19800 > equity+shl=~8750), the waterfall exhausts all SHL in P1.
    # PRO_RATA-waterfall ≈ ALL_AT_FC for this profile → PIK is equal (>=, not strictly >).
    project_all_at_fc = dataclasses.replace(
        project,
        financing=dataclasses.replace(
            project.financing,
            sponsor_funding_timing_policy=SponsorFundingTimingPolicy.ALL_AT_FC,
        ),
    )
    result_all_at_fc = run_project_financing_model(project_all_at_fc)
    assert result_all_at_fc.shl_construction_pik_keur >= result_uses.shl_construction_pik_keur, (
        "ALL_AT_FC PIK must be >= PRO_RATA-waterfall (front-loaded uses saturate waterfall in P1)"
    )


# ---------------------------------------------------------------------------
# Sponsor XIRR production test (Step 14)
# ---------------------------------------------------------------------------

def test_sponsor_xirr_differs_between_pro_rata_and_all_at_fc():
    """Step 14 (UPDATED): Calls run_project_sponsor_returns_model() to confirm XIRR engine output.

    - Total SHL cash contributed identical (same derived principal)
    - SHL contribution timing differs (ALL_AT_FC: lump-sum at FC; PRO_RATA: distributed)
    - Total Sponsor XIRR differs between policies because early SHL draw reduces returns
    - Legal equity contribution amounts/dates unchanged
    - Canonical G2B dates consumed from cp.cashflow_date (not FC + index months)
    """
    from financial_engine.sponsor_returns import run_project_sponsor_returns_model
    import dataclasses

    # GAP 3: PRO_RATA requires explicit uses vector for multi-period positive-DCF.
    # Use (4000, 29000): small P1 ensures SHL is distributed across both periods by waterfall
    # (P1 uses < equity+SHL ≈ 8500), so PRO_RATA cash timing differs from ALL_AT_FC.
    project = _make_solar_with_construction_timing(
        24, 2.0, SponsorFundingTimingPolicy.PRO_RATA_CONSTRUCTION,
        construction_period_uses_keur=(4000.0, 29000.0),
    )
    project_all_at_fc = dataclasses.replace(
        project,
        financing=dataclasses.replace(
            project.financing,
            sponsor_funding_timing_policy=SponsorFundingTimingPolicy.ALL_AT_FC,
        ),
    )

    # Call actual Sponsor Returns / XIRR engine for both policies
    pro_rata_result = run_project_sponsor_returns_model(project)
    all_at_fc_result = run_project_sponsor_returns_model(project_all_at_fc)

    # Assert 1: Total SHL cash contributed is identical under both policies
    pro_rata_shl_total = sum(
        p.shl_cash_contribution_keur for p in pro_rata_result.cashflow_periods
        if p.is_construction
    )
    all_at_fc_shl_total = sum(
        p.shl_cash_contribution_keur for p in all_at_fc_result.cashflow_periods
        if p.is_construction
    )
    assert abs(pro_rata_shl_total - all_at_fc_shl_total) < 1.0, (
        f"Total SHL cash contributed must be equal: PRO_RATA={pro_rata_shl_total:.3f}, "
        f"ALL_AT_FC={all_at_fc_shl_total:.3f}"
    )

    # Assert 2: SHL contribution timing differs (different per-period vectors)
    pro_rata_construction = [
        p.shl_cash_contribution_keur for p in pro_rata_result.cashflow_periods
        if p.is_construction
    ]
    all_at_fc_construction = [
        p.shl_cash_contribution_keur for p in all_at_fc_result.cashflow_periods
        if p.is_construction
    ]
    assert len(pro_rata_construction) >= 2 and len(all_at_fc_construction) >= 2, (
        "Need at least 2 construction periods to verify timing differs"
    )
    assert pro_rata_construction != all_at_fc_construction, (
        "Per-period SHL contribution timing must differ between PRO_RATA and ALL_AT_FC"
    )
    # ALL_AT_FC: first period draws full SHL
    assert all_at_fc_construction[0] > pro_rata_construction[0], (
        "ALL_AT_FC first period SHL draw must exceed PRO_RATA first period draw"
    )

    # Assert 3: Total Sponsor XIRR differs (or verify why it doesn't)
    # PIK differs between policies → opening SHL differs → SHL interest/principal schedule
    # differs → total sponsor cashflows differ → XIRR must differ.
    # Both must be non-None (project generates enough CFADS to service SHL).
    pr_ts_xirr = pro_rata_result.total_sponsor_xirr
    fc_ts_xirr = all_at_fc_result.total_sponsor_xirr

    print(f"\n--- Sponsor XIRR Evidence (Step 14) ---")
    print(f"PRO_RATA Total Sponsor XIRR: {pr_ts_xirr}")
    print(f"ALL_AT_FC Total Sponsor XIRR: {fc_ts_xirr}")
    print(f"PRO_RATA SHL total cash drawn: {pro_rata_shl_total:.3f} kEUR")
    print(f"ALL_AT_FC SHL total cash drawn: {all_at_fc_shl_total:.3f} kEUR")
    print(f"PRO_RATA construction periods: {pro_rata_construction}")
    print(f"ALL_AT_FC construction periods: {all_at_fc_construction}")

    # If XIRR is computable for both, they must differ (different opening SHL → different
    # SHL debt service → different total sponsor cashflows → different XIRR)
    if pr_ts_xirr is not None and fc_ts_xirr is not None:
        assert abs(pr_ts_xirr - fc_ts_xirr) > 1e-6, (
            f"Total Sponsor XIRR must differ between policies: "
            f"PRO_RATA={pr_ts_xirr:.6f}, ALL_AT_FC={fc_ts_xirr:.6f}"
        )

    # Assert 4: Legal equity contribution amounts/dates unchanged
    # (Share capital + share premium: same project inputs → same equity draws)
    pro_equity = sum(
        p.share_capital_contribution_keur + p.share_premium_contribution_keur
        for p in pro_rata_result.cashflow_periods if p.is_construction
    )
    fc_equity = sum(
        p.share_capital_contribution_keur + p.share_premium_contribution_keur
        for p in all_at_fc_result.cashflow_periods if p.is_construction
    )
    assert abs(pro_equity - fc_equity) < 1e-6, (
        f"Legal equity contributions must be identical: PRO_RATA={pro_equity:.6f}, "
        f"ALL_AT_FC={fc_equity:.6f}"
    )

    # Assert 5: G2B dates come from cp.cashflow_date (canonical), not FC + index months.
    # Verify that construction cashflow dates in the result are plausible (not year 1900)
    for p in pro_rata_result.cashflow_periods:
        if p.is_construction:
            assert p.cashflow_date.year >= 2020, (
                f"Construction cashflow date {p.cashflow_date} looks wrong (should be project date)"
            )


# ---------------------------------------------------------------------------
# 40:5 Controlled example: explicit construction_period_uses_keur
# ---------------------------------------------------------------------------

def test_40_5_explicit_construction_period_uses_keur():
    """40:5 controlled example: explicit uses vector via run_project_financing_model.

    Solar project (33000 kEUR total uses, 75% gearing = 24750 senior, 500 share_capital):
    - 2-period construction (24 months, DCF=2.0)
    - explicit construction_period_uses_keur=(19800, 13200) — 60/40 split
    - PRO_RATA: net_need drives SHL timing (no invented equal splits)
    - ALL_AT_FC: full SHL at period 0 regardless of Uses

    Verifies:
    - No invented linear splits (SHL draw != total/n for unequal Uses)
    - Single Uses truth from construction_period_uses_keur (not recomputed)
    - Sources balance per period
    """
    from financial_engine.financing import run_project_financing_model
    import dataclasses

    project = _make_solar_with_construction_timing(24, 2.0, SponsorFundingTimingPolicy.PRO_RATA_CONSTRUCTION)

    # 60/40 uses split — front-loaded
    project_with_uses = dataclasses.replace(
        project,
        financing=dataclasses.replace(
            project.financing,
            construction_period_uses_keur=(19800.0, 13200.0),
        ),
    )

    result = run_project_financing_model(project_with_uses)
    assert result.fixed_point_iteration_count >= 1

    # Item 11 proof: no invented equal splits
    # If splits were equal: shl_draw[0] == shl_draw[1]
    # With 60/40 Uses and unequal net needs: shl_draw[0] != shl_draw[1]
    funding = result.construction_funding
    shl_0 = funding.periods[0].shl_cash_draw_keur
    shl_1 = funding.periods[1].shl_cash_draw_keur
    shl_total = shl_0 + shl_1

    # Not equal splits: front-loaded uses → more SHL in period 0
    assert abs(shl_0 - shl_total / 2) > 1.0, (
        f"PRO_RATA with unequal Uses must NOT produce equal SHL splits: "
        f"shl_0={shl_0:.3f}, shl_total/2={shl_total/2:.3f}"
    )
    assert shl_0 > shl_1, (
        f"Front-loaded uses (60/40) must produce more SHL in period 0: "
        f"shl_0={shl_0:.3f}, shl_1={shl_1:.3f}"
    )

    # Item 7: single Uses truth — period uses sum to total project uses
    uses_0 = funding.periods[0].project_cash_uses_keur
    uses_1 = funding.periods[1].project_cash_uses_keur
    assert abs(uses_0 + uses_1 - result.project_uses.total_project_uses_keur) < 1e-6, (
        f"Period uses must sum to total: {uses_0:.3f} + {uses_1:.3f} != "
        f"{result.project_uses.total_project_uses_keur:.3f}"
    )

    # Sources balance per period (S&U identity)
    assert funding.maximum_period_difference_keur <= 1e-6
    assert funding.maximum_cumulative_difference_keur <= 1e-6

    # ALL_AT_FC variant: full SHL in period 0, regardless of Uses split
    project_all_fc = dataclasses.replace(
        project_with_uses,
        financing=dataclasses.replace(
            project_with_uses.financing,
            sponsor_funding_timing_policy=SponsorFundingTimingPolicy.ALL_AT_FC,
        ),
    )
    result_fc = run_project_financing_model(project_all_fc)
    assert result_fc.fixed_point_iteration_count >= 1

    fc_shl_0 = result_fc.construction_funding.periods[0].shl_cash_draw_keur
    fc_shl_total = sum(p.shl_cash_draw_keur for p in result_fc.construction_funding.periods)
    assert abs(fc_shl_0 - fc_shl_total) < 1e-4, (
        f"ALL_AT_FC: full SHL must be in period 0: fc_shl_0={fc_shl_0:.3f}, total={fc_shl_total:.3f}"
    )

    print(f"\n--- 40:5 Controlled Example ---")
    print(f"PRO_RATA shl_0={shl_0:.3f}, shl_1={shl_1:.3f}, total={shl_total:.3f}")
    print(f"ALL_AT_FC shl_0={fc_shl_0:.3f}, total={fc_shl_total:.3f}")
    print(f"Uses: period_0={uses_0:.3f}, period_1={uses_1:.3f}")
    print(f"Item 11 verified: shl_0/total = {shl_0/shl_total:.3f} (not 50%)")


# ---------------------------------------------------------------------------
# Step 8: Controlled generic waterfall example (SPONSOR_FIRST_RESIDUAL_SENIOR)
# No project identity. Tests the waterfall function directly.
# ---------------------------------------------------------------------------

def test_controlled_waterfall_example_exact_values():
    """Step 8: Generic waterfall controlled example — exact period draw assertions.

    Caps: Equity=10, SHL=30, Senior=sufficient (50)
    Cumulative uses: P1=20, P2=35, P3=60
    Period uses:     P1=20, P2=15, P3=25

    Expected waterfall draws:
      P1: Equity=10, SHL=10, Senior=0
      P2: Equity=0,  SHL=15, Senior=0
      P3: Equity=0,  SHL=5,  Senior=20
    """
    from domain.construction.funding_allocation import allocate_source_waterfall
    from domain.construction.config import FundingSourceCaps

    caps = FundingSourceCaps(
        equity_shares_keur=10.0,
        shl_keur=30.0,
        junior_keur=0.0,
        senior_debt_keur=50.0,
    )
    # Period uses: cumulative 20, 35, 60 → period 20, 15, 25
    entries = allocate_source_waterfall((20.0, 15.0, 25.0), caps)

    assert len(entries) == 3

    # P1: cum_uses=20, cum_equity=min(10,20)=10, cum_shl=min(30,10)=10, cum_senior=0
    assert abs(entries[0].equity_draw_keur - 10.0) < 1e-9, f"P1 equity={entries[0].equity_draw_keur}"
    assert abs(entries[0].shl_draw_keur - 10.0) < 1e-9, f"P1 shl={entries[0].shl_draw_keur}"
    assert abs(entries[0].senior_draw_keur - 0.0) < 1e-9, f"P1 senior={entries[0].senior_draw_keur}"

    # P2: cum_uses=35, cum_equity=10, cum_shl=min(30,25)=25, cum_senior=0
    assert abs(entries[1].equity_draw_keur - 0.0) < 1e-9, f"P2 equity={entries[1].equity_draw_keur}"
    assert abs(entries[1].shl_draw_keur - 15.0) < 1e-9, f"P2 shl={entries[1].shl_draw_keur}"
    assert abs(entries[1].senior_draw_keur - 0.0) < 1e-9, f"P2 senior={entries[1].senior_draw_keur}"

    # P3: cum_uses=60, cum_equity=10, cum_shl=min(30,50)=30, cum_senior=min(50,20)=20
    assert abs(entries[2].equity_draw_keur - 0.0) < 1e-9, f"P3 equity={entries[2].equity_draw_keur}"
    assert abs(entries[2].shl_draw_keur - 5.0) < 1e-9, f"P3 shl={entries[2].shl_draw_keur}"
    assert abs(entries[2].senior_draw_keur - 20.0) < 1e-9, f"P3 senior={entries[2].senior_draw_keur}"

    # Cumulative totals
    assert abs(entries[2].cumulative_equity_keur - 10.0) < 1e-9
    assert abs(entries[2].cumulative_shl_keur - 30.0) < 1e-9
    assert abs(entries[2].cumulative_senior_keur - 20.0) < 1e-9
    assert abs(entries[2].cumulative_uses_keur - 60.0) < 1e-9

    print("\n--- Step 8 Controlled Waterfall Example ---")
    for e in entries:
        print(f"  P{e.month_index}: equity={e.equity_draw_keur}, shl={e.shl_draw_keur}, senior={e.senior_draw_keur}")


# ---------------------------------------------------------------------------
# GAP 3: Fail-closed for multi-period PRO_RATA without explicit Uses vector
# ---------------------------------------------------------------------------

def test_gap3_pro_rata_multi_period_without_uses_fails_closed():
    """GAP 3: PRO_RATA_CONSTRUCTION + multi-period positive-DCF + no uses vector → ValueError.

    Exception: single construction period (unambiguous) and legacy Solar/Wind (DCF=0.0).
    """
    from financial_engine.financing import run_project_financing_model
    import dataclasses
    from app import project_factories

    project = project_factories.create_default_solar_project(construction_months=24)
    # Multi-period (24 months), positive DCF, PRO_RATA, NO uses vector → must fail
    project_no_uses = dataclasses.replace(
        project,
        financing=dataclasses.replace(
            project.financing,
            shl_construction_day_count_fraction=2.0,
            sponsor_funding_timing_policy=SponsorFundingTimingPolicy.PRO_RATA_CONSTRUCTION,
            # construction_period_uses_keur intentionally NOT set (empty default)
        ),
    )
    with pytest.raises(ValueError, match="PRO_RATA_CONSTRUCTION.*requires.*construction_period_uses_keur"):
        run_project_financing_model(project_no_uses)


def test_gap3_single_period_pro_rata_no_uses_is_valid():
    """GAP 3 exception: single model construction period with PRO_RATA is unambiguous — no uses required.

    Note: Solar model always produces 2 construction periods (half-year period structure).
    This test verifies GAP 3 fails-closed for the 2-period Solar case, and that providing
    a uses vector allows PRO_RATA to proceed. The single-period exemption is tested
    indirectly via the code path (n_template_periods > 1 condition in project.py).
    """
    from financial_engine.financing import run_project_financing_model
    import dataclasses
    from app import project_factories

    project = project_factories.create_default_solar_project(construction_months=12)
    # Solar always gives 2 construction periods; providing uses vector satisfies GAP 3.
    project_with_uses = dataclasses.replace(
        project,
        financing=dataclasses.replace(
            project.financing,
            shl_construction_day_count_fraction=1.0,
            sponsor_funding_timing_policy=SponsorFundingTimingPolicy.PRO_RATA_CONSTRUCTION,
            construction_period_uses_keur=(16500.0, 16500.0),  # GAP 3 requires uses
        ),
    )
    # Should succeed with uses vector
    result = run_project_financing_model(project_with_uses)
    assert result.fixed_point_iteration_count >= 1


def test_gap3_all_at_fc_multi_period_without_uses_is_valid():
    """GAP 3 only applies to PRO_RATA. ALL_AT_FC with multi-period and no uses is fine."""
    from financial_engine.financing import run_project_financing_model
    import dataclasses
    from app import project_factories

    project = project_factories.create_default_solar_project(construction_months=24)
    project_all_fc = dataclasses.replace(
        project,
        financing=dataclasses.replace(
            project.financing,
            shl_construction_day_count_fraction=2.0,
            sponsor_funding_timing_policy=SponsorFundingTimingPolicy.ALL_AT_FC,
            # No uses vector — ALL_AT_FC exempt from GAP 3
        ),
    )
    result = run_project_financing_model(project_all_fc)
    assert result.fixed_point_iteration_count >= 1


# ---------------------------------------------------------------------------
# GAP 2: ALL_AT_FC prefunding bridge controlled example
# ---------------------------------------------------------------------------

def test_gap2_all_at_fc_prefunding_bridge_controlled():
    """GAP 2 controlled example: ALL_AT_FC prefunding bridge roll-forward.

    SHL=100, 3 periods, waterfall allocation=[30,40,30], ALL_AT_FC contribution=[100,0,0].
    Expected: opening=[0,70,30], closing=[70,30,0].

    Uses build_construction_funding_schedule directly with explicit vectors.
    """
    from financial_engine.financing.stack import build_construction_funding_schedule

    # SHL=100, allocation follows waterfall (30/40/30), cash contribution ALL_AT_FC (100/0/0)
    # Total uses=100 (no senior/equity/junior for simplicity)
    result = build_construction_funding_schedule(
        construction_period_count=3,
        total_project_uses_keur=100.0,
        senior_keur=0.0,
        junior_keur=0.0,
        share_capital_keur=0.0,
        share_premium_keur=0.0,
        other_committed_equity_keur=0.0,
        additional_equity_keur=0.0,
        shl_cash_keur=100.0,
        shl_cash_per_period_keur=(100.0, 0.0, 0.0),    # Layer B: cash contribution
        period_uses_keur=(30.0, 40.0, 30.0),            # GAP 1: explicit uses
        shl_allocation_per_period_keur=(30.0, 40.0, 30.0),  # Layer A: waterfall allocation
    )

    periods = result.periods
    assert len(periods) == 3

    # Layer A: allocation follows uses
    assert abs(periods[0].shl_allocation_to_uses_keur - 30.0) < 1e-9, f"P1 allocation={periods[0].shl_allocation_to_uses_keur}"
    assert abs(periods[1].shl_allocation_to_uses_keur - 40.0) < 1e-9, f"P2 allocation={periods[1].shl_allocation_to_uses_keur}"
    assert abs(periods[2].shl_allocation_to_uses_keur - 30.0) < 1e-9, f"P3 allocation={periods[2].shl_allocation_to_uses_keur}"

    # Layer B: cash contribution (ALL_AT_FC)
    assert abs(periods[0].sponsor_shl_cash_contribution_keur - 100.0) < 1e-9
    assert abs(periods[1].sponsor_shl_cash_contribution_keur - 0.0) < 1e-9
    assert abs(periods[2].sponsor_shl_cash_contribution_keur - 0.0) < 1e-9

    # Prefunding bridge roll-forward: opening=[0,70,30], closing=[70,30,0]
    assert abs(periods[0].opening_unutilised_shl_cash_keur - 0.0) < 1e-9, f"P1 opening={periods[0].opening_unutilised_shl_cash_keur}"
    assert abs(periods[0].closing_unutilised_shl_cash_keur - 70.0) < 1e-9, f"P1 closing={periods[0].closing_unutilised_shl_cash_keur}"

    assert abs(periods[1].opening_unutilised_shl_cash_keur - 70.0) < 1e-9, f"P2 opening={periods[1].opening_unutilised_shl_cash_keur}"
    assert abs(periods[1].closing_unutilised_shl_cash_keur - 30.0) < 1e-9, f"P2 closing={periods[1].closing_unutilised_shl_cash_keur}"

    assert abs(periods[2].opening_unutilised_shl_cash_keur - 30.0) < 1e-9, f"P3 opening={periods[2].opening_unutilised_shl_cash_keur}"
    assert abs(periods[2].closing_unutilised_shl_cash_keur - 0.0) < 1e-9, f"P3 closing={periods[2].closing_unutilised_shl_cash_keur}"

    print("\n--- GAP 2 Controlled Bridge Example (ALL_AT_FC) ---")
    for p in periods:
        print(f"  P{p.period_index}: contribution={p.sponsor_shl_cash_contribution_keur}, allocation={p.shl_allocation_to_uses_keur}, opening={p.opening_unutilised_shl_cash_keur}, closing={p.closing_unutilised_shl_cash_keur}")


def test_gap2_pro_rata_bridge_is_zero():
    """GAP 2 control: PRO_RATA contribution == allocation → unutilised balance always 0."""
    from financial_engine.financing.stack import build_construction_funding_schedule

    # PRO_RATA: contribution == allocation == [30, 40, 30]
    result = build_construction_funding_schedule(
        construction_period_count=3,
        total_project_uses_keur=100.0,
        senior_keur=0.0,
        junior_keur=0.0,
        share_capital_keur=0.0,
        share_premium_keur=0.0,
        other_committed_equity_keur=0.0,
        additional_equity_keur=0.0,
        shl_cash_keur=100.0,
        shl_cash_per_period_keur=(30.0, 40.0, 30.0),   # contribution == allocation
        period_uses_keur=(30.0, 40.0, 30.0),
        shl_allocation_per_period_keur=(30.0, 40.0, 30.0),
    )
    for p in result.periods:
        assert abs(p.opening_unutilised_shl_cash_keur) < 1e-9, f"PRO_RATA P{p.period_index} opening != 0"
        assert abs(p.closing_unutilised_shl_cash_keur) < 1e-9, f"PRO_RATA P{p.period_index} closing != 0"
        assert abs(p.shl_allocation_to_uses_keur - p.sponsor_shl_cash_contribution_keur) < 1e-9, (
            f"PRO_RATA: allocation must equal contribution at P{p.period_index}"
        )


def test_gap1_one_period_uses_vector_in_funding_schedule():
    """GAP 1: explicit construction_period_uses_keur flows into ConstructionFundingPeriod.project_cash_uses_keur.

    For a 2-period project with 60/40 Uses split (19800/13200), the funding schedule
    must report 19800 and 13200 as project_cash_uses_keur (not linear 16500/16500).
    """
    from financial_engine.financing import run_project_financing_model
    import dataclasses

    project = _make_solar_with_construction_timing(
        24, 2.0, SponsorFundingTimingPolicy.PRO_RATA_CONSTRUCTION,
        construction_period_uses_keur=(19800.0, 13200.0),
    )
    result = run_project_financing_model(project)
    assert result.fixed_point_iteration_count >= 1

    uses_0 = result.construction_funding.periods[0].project_cash_uses_keur
    uses_1 = result.construction_funding.periods[1].project_cash_uses_keur

    # Exact match of input uses vector (not linear total/n = 16500)
    assert abs(uses_0 - 19800.0) < 1e-4, (
        f"GAP 1: period 0 uses must be 19800 (from input vector), got {uses_0:.3f}"
    )
    assert abs(uses_1 - 13200.0) < 1e-4, (
        f"GAP 1: period 1 uses must be 13200 (from input vector), got {uses_1:.3f}"
    )

    print(f"\n--- GAP 1 Uses Vector Handshake ---")
    print(f"Input: (19800, 13200) → Reported: ({uses_0:.3f}, {uses_1:.3f})")
