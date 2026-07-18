"""financial_engine.tax.tax_year — Calendar tax-year period allocator.

Splits model periods into calendar-year fragments and aggregates them into
TaxYearCalculationBasis records.  Periods that cross 31 December are split
on that boundary; the allocation fraction is proportional to the calendar-day
count in each fragment.

Rules
-----
* ``tax_year`` is the 4-digit calendar year of the fragment (e.g. 2030).
* All fragments for a period sum to ``allocation_fraction == 1.0``.
* Fragment ``days`` uses ``(frag_end − frag_start).days`` so the sum equals
  ``(period_end − period_start).days``.  For periods of length 0 the single
  fragment has ``days=0`` and ``allocation_fraction=1.0``.
* EBITDA, tax depreciation, interest and fiscal reintegration are allocated
  proportionally.  Totals are preserved exactly (floating-point arithmetic).

Pure function.  No imports from app, finco_core or any framework.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from financial_engine.inputs import PeriodInterestInput
from financial_engine.tax.models import TaxYearCalculationBasis, TaxYearPeriodFragment


def _split_period(
    period_index: int,
    period_start: date,
    period_end: date,
) -> list[TaxYearPeriodFragment]:
    """Split one period into calendar-year fragments.

    Uses the half-open interval convention [period_start, period_end) so that
    fragment days sum to (period_end − period_start).days.

    Year boundary: fragment for calendar year Y covers
        [max(period_start, Jan 1 Y),  min(period_end, Jan 1 (Y+1)))

    fragment.days = (frag_end - frag_start).days   (consistent with the
    period engine's own days_in_period computation for crossing periods)

    Allocation fraction: frag_days / sum(all_frag_days).  The last fragment's
    fraction is adjusted to ensure exact sum == 1.0.

    Zero-length periods ((period_end - period_start).days == 0) receive a
    single zero-day fragment with allocation_fraction == 1.0.
    """
    total_days = (period_end - period_start).days

    if total_days == 0:
        return [TaxYearPeriodFragment(
            tax_year=period_end.year,
            source_period_index=period_index,
            start_date=period_start,
            end_date=period_end,
            days=0,
            allocation_fraction=1.0,
        )]

    fragments: list[tuple[int, date, date, int]] = []
    cur_start = period_start

    while cur_start < period_end:
        cur_year = cur_start.year
        next_jan1 = date(cur_year + 1, 1, 1)
        frag_end = min(period_end, next_jan1)
        frag_days = (frag_end - cur_start).days
        fragments.append((cur_year, cur_start, frag_end, frag_days))
        cur_start = frag_end  # move to start of next year (= frag_end)

    # Compute fractions; last fraction is adjusted for exact 1.0 sum.
    total_frag_days = sum(fd for _, _, _, fd in fragments)
    assert total_frag_days > 0, (
        f"Internal error: fragments sum to 0 for period {period_index} "
        f"({period_start} → {period_end}, total_days={total_days})"
    )
    fracs = [fd / total_frag_days for _, _, _, fd in fragments]
    fracs[-1] = 1.0 - sum(fracs[:-1])

    return [
        TaxYearPeriodFragment(
            tax_year=yr,
            source_period_index=period_index,
            start_date=fs,
            end_date=fe,
            days=fd,
            allocation_fraction=frac,
        )
        for (yr, fs, fe, fd), frac in zip(fragments, fracs)
    ]


def _payment_period_for_year(
    tax_year: int,
    frags_for_year: tuple[TaxYearPeriodFragment, ...],
    periods_by_index: dict[int, object],
) -> int:
    """Return the period_index that receives TAX_YEAR_LAST_PERIOD cash tax.

    Selects the period whose ``period_end`` falls within ``tax_year`` and has
    the latest period_index.  If no period ends within the tax year (edge case),
    falls back to the period with the maximum allocation fraction.
    """
    candidates: list[int] = []
    for frag in frags_for_year:
        p = periods_by_index.get(frag.source_period_index)
        if p is None:
            continue
        p_end: date = p.period_end  # type: ignore[attr-defined]
        # Under the half-open [start, end) convention, the last calendar day of
        # the period is p_end - 1 day. If that day falls in tax_year, the period
        # "ends" in this tax year and is a payment candidate.
        # This handles both Jun30→Jan1 H2 periods (last day Dec31 = tax_year ✓)
        # and Dec31→Jun30 H1 periods with a 1-day fragment in the prior year (last day Jun29 ✗ correct).
        last_day = p_end - timedelta(days=1)
        if last_day.year == tax_year:
            candidates.append(frag.source_period_index)
    if candidates:
        # latest by period_index (chronological order)
        return max(set(candidates))
    # Fallback: period with maximum total allocation fraction to this year
    period_fracs: dict[int, float] = {}
    for frag in frags_for_year:
        period_fracs[frag.source_period_index] = (
            period_fracs.get(frag.source_period_index, 0.0) + frag.allocation_fraction
        )
    return max(period_fracs, key=lambda k: (period_fracs[k], k))


def build_tax_year_bases(
    periods: tuple,              # tuple[OperatingPeriodResult]
    interest_map: dict[int, PeriodInterestInput],
    adj_map: dict[int, float],
) -> tuple[TaxYearCalculationBasis, ...]:
    """Aggregate period amounts into calendar-year TaxYearCalculationBasis records.

    Periods are split on 31 December when they cross year-end.  Each fragment
    contributes its allocated fraction of the period's EBITDA, tax depreciation,
    interest, and fiscal reintegration to the fragment's calendar year.

    Parameters
    ----------
    periods:
        All model periods (including construction) from the Phase 2A orchestrator.
    interest_map:
        Mapping period_index → PeriodInterestInput.
    adj_map:
        Mapping period_index → other_fiscal_reintegration_keur.

    Returns
    -------
    Tuple of TaxYearCalculationBasis, sorted by ascending calendar year.
    """
    # Accumulate per-year totals and fragments.
    year_fragments: dict[int, list[TaxYearPeriodFragment]] = defaultdict(list)
    year_ebitda: dict[int, float] = defaultdict(float)
    year_tax_dep: dict[int, float] = defaultdict(float)
    year_interest: dict[int, float] = defaultdict(float)
    year_reint: dict[int, float] = defaultdict(float)

    for p in periods:
        idx: int = p.period_index          # type: ignore[attr-defined]
        p_start: date = p.period_start     # type: ignore[attr-defined]
        p_end: date = p.period_end         # type: ignore[attr-defined]
        ebitda: float = p.ebitda_keur      # type: ignore[attr-defined]
        tax_dep: float = p.tax_depreciation_keur  # type: ignore[attr-defined]

        pi_obj = interest_map.get(idx)
        gross_int = pi_obj.total_interest_keur if pi_obj else 0.0
        reint = adj_map.get(idx, 0.0)

        frags = _split_period(idx, p_start, p_end)

        for frag in frags:
            yr = frag.tax_year
            f = frag.allocation_fraction
            year_fragments[yr].append(frag)
            year_ebitda[yr] += ebitda * f
            year_tax_dep[yr] += tax_dep * f
            year_interest[yr] += gross_int * f
            year_reint[yr] += reint * f

    # Build index for payment_period resolution
    periods_by_index: dict[int, object] = {
        p.period_index: p  # type: ignore[attr-defined]
        for p in periods
    }

    # Determine the "primary year" for each period: the calendar year that receives the
    # largest allocation fraction.  For ties, the later year (higher value) wins so that
    # the payment stays with the majority year.
    period_primary_year: dict[int, int] = {}
    period_max_frac: dict[int, float] = {}
    for yr, frags in year_fragments.items():
        for frag in frags:
            idx = frag.source_period_index
            total_frac_in_yr = sum(
                f.allocation_fraction for f in frags if f.source_period_index == idx
            )
            if total_frac_in_yr > period_max_frac.get(idx, -1.0):
                period_primary_year[idx] = yr
                period_max_frac[idx] = total_frac_in_yr
            elif total_frac_in_yr == period_max_frac.get(idx, -1.0) and yr > period_primary_year.get(idx, -1):
                # Tie-break: later year wins (ensures Dec31→Jan1 period belongs to the later year).
                period_primary_year[idx] = yr

    bases: list[TaxYearCalculationBasis] = []
    for yr in sorted(year_fragments.keys()):
        frags_for_year = tuple(year_fragments[yr])
        # period_indices: only periods whose primary year is this year.
        # This ensures each period appears in exactly one year's proration, preventing
        # double-counting for Dec31-start periods that straddle year boundaries.
        period_indices = tuple(dict.fromkeys(
            frag.source_period_index
            for frag in frags_for_year
            if period_primary_year.get(frag.source_period_index) == yr
        ))
        if not period_indices:
            continue
        payment_idx = _payment_period_for_year(yr, frags_for_year, periods_by_index)
        bases.append(TaxYearCalculationBasis(
            tax_year=yr,
            fragments=frags_for_year,
            period_indices=period_indices,
            payment_period_index=payment_idx,
            ebitda_keur=year_ebitda[yr],
            tax_depreciation_keur=year_tax_dep[yr],
            total_interest_keur=year_interest[yr],
            other_fiscal_reintegration_keur=year_reint[yr],
        ))

    return tuple(bases)
