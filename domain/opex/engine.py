"""OPEX calculation engine — annual-first line-item engine.

compute_annual_opex() is the main entry point.

Two-pass calculation for contingency groups:
  Pass 1: Compute all normal groups/items (including contingency items' base)
  Pass 2: Compute contingency items using selected groups' totals from Pass 1

Manual override hierarchy (applied in order):
  1. Inactive flag → final = 0
  2. Manual override exists → final = override (not inflated)
  3. Otherwise → final = calculated amount (with inflation)

Step change semantics:
  Step takes effect at step_year. The new base is used from step_year onward.
  Inflation exponent counts from step_year (not from Y1).
  i.e. at year Y >= step_year: calculated = new_base × (1 + infl)^(Y - step_year)

WTH treatment:
  WTH is an addition to cost (not deducted from base).
  final = calculated or override
  wth_keur = final × wth_rate
  total_keur = final + wth_keur
  WTH is exposed in result but not fed into broader tax engine in O2.

Basis calculation:
  fixed_annual_keur / fixed_period_keur: base = budget_keur
  eur_per_mw_year: base = budget_keur × capacity_mw / 1000 → kEUR/year
  eur_per_mwh: base = budget_keur × production_mwh / 1000 → kEUR
  pct_of_revenue: base = revenue_keur × budget_keur (budget = decimal fraction)
  pct_of_group: base = group_total_keur × budget_keur (budget = decimal fraction)
  pct_of_selected_groups: base = sum(selected_groups' totals) × budget_keur
  explicit_schedule: base = explicit_schedule_keur[year_index-1]; no inflation
  inactive: base = 0
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from domain.opex.line_items import OpexBasis, OpexGroup, OpexItem
from domain.opex.result import OpexAnnualResult, OpexGroupAnnualResult, OpexItemAnnualResult


# Internal: working item result before WTH
@dataclass
class _ItemWorking:
    base: float          # pre-inflation base
    calculated: float    # after inflation
    override_used: Optional[float] = None  # if manual override was used
    wth_keur: float = 0.0


def compute_annual_opex(
    groups: list[OpexGroup],
    *,
    years: int,
    capacity_mw: float = 0.0,
    production_mwh_by_year: Optional[list[float]] = None,
    revenue_keur_by_year: Optional[list[float]] = None,
) -> OpexAnnualResult:
    """Compute annual OPEX across all groups and years.

    Args:
        groups: list of OpexGroup (all groups in the project)
        years: number of operating years to compute
        capacity_mw: project capacity in MW (for eur_per_mw_year basis)
        production_mwh_by_year: list of annual production in MWh (index 0 = Y1).
            Required if any item uses eur_per_mwh basis.
        revenue_keur_by_year: list of annual revenue in kEUR (index 0 = Y1).
            Required if any item uses pct_of_revenue basis.

    Returns:
        OpexAnnualResult with per-year, per-group, per-item breakdown

    Raises:
        ValueError: if required inputs missing for a given basis type
    """
    if production_mwh_by_year is None:
        production_mwh_by_year = [0.0] * years
    if revenue_keur_by_year is None:
        revenue_keur_by_year = [0.0] * years

    year_indices = tuple(range(1, years + 1))

    # ── PASS 1: Compute all groups/items, track contingency group needs ──────

    # group_results[year][group_code] = OpexGroupAnnualResult (partial, contingency=0)
    group_results: list[OpexGroupAnnualResult] = []
    total_by_year: list[float] = [0.0] * years

    # Map of group_code → list of item totals per year (for pct_of_group references)
    group_totals: dict[str, list[float]] = {}

    for group in groups:
        if not group.items:
            # Empty group — skip but still produce empty result for each year
            for y_idx, year in enumerate(year_indices):
                group_results.append(OpexGroupAnnualResult(
                    year_index=year,
                    group_code=group.code,
                    group_name=group.name,
                    item_results=(),
                    group_total_keur=0.0,
                    contingency_from_groups_keur=0.0,
                ))
            continue

        group_totals[group.code] = [0.0] * years

        for y_idx, year in enumerate(year_indices):
            item_results: list[OpexItemAnnualResult] = []
            group_total = 0.0

            for item in group.items:
                # Determine effective inflation (item > group)
                eff_infl = item.inflation_rate if item.inflation_rate is not None else group.inflation_rate

                # Check active flag
                if not item.is_active(year):
                    # Inactive → 0
                    wth = item.wth_rate if item.wth_rate > 0 else group.wth_rate
                    wth_keur = 0.0  # 0 × wth_rate = 0
                    item_results.append(OpexItemAnnualResult(
                        year_index=year,
                        group_code=group.code,
                        group_name=group.name,
                        item_code=item.code,
                        item_name=item.name,
                        active=False,
                        basis=item.basis.value,
                        budget_keur=item.budget_keur,
                        calculated_keur=0.0,
                        manual_override_keur=None,
                        inflation_rate=eff_infl,
                        wth_rate=wth,
                        wth_keur=0.0,
                        total_keur=0.0,
                        is_manual_override=False,
                    ))
                    continue

                # Check manual override
                override = item.override_for(year)
                if override is not None:
                    # Override used as-is (not inflated)
                    final = override.value_keur
                    wth = item.wth_rate if item.wth_rate > 0 else group.wth_rate
                    wth_keur = final * wth
                    total = final + wth_keur

                    # Calculate what the formula would have given (for comparison)
                    calc = _compute_item_base(item, group, year, eff_infl,
                                              capacity_mw, production_mwh_by_year,
                                              revenue_keur_by_year, group_totals)
                    calc_with_infl = _apply_inflation(calc, eff_infl, year, item)

                    item_results.append(OpexItemAnnualResult(
                        year_index=year,
                        group_code=group.code,
                        group_name=group.name,
                        item_code=item.code,
                        item_name=item.name,
                        active=True,
                        basis=item.basis.value,
                        budget_keur=item.budget_keur,
                        calculated_keur=calc_with_infl,
                        manual_override_keur=override.value_keur,
                        inflation_rate=eff_infl,
                        wth_rate=wth,
                        wth_keur=wth_keur,
                        total_keur=total,
                        is_manual_override=True,
                    ))
                    group_total += total
                    continue

                # Normal calculation
                calc = _compute_item_base(item, group, year, eff_infl,
                                          capacity_mw, production_mwh_by_year,
                                          revenue_keur_by_year, group_totals)
                calc_with_infl = _apply_inflation(calc, eff_infl, year, item)
                final = calc_with_infl
                wth = item.wth_rate if item.wth_rate > 0 else group.wth_rate
                wth_keur = final * wth
                total = final + wth_keur

                item_results.append(OpexItemAnnualResult(
                    year_index=year,
                    group_code=group.code,
                    group_name=group.name,
                    item_code=item.code,
                    item_name=item.name,
                    active=True,
                    basis=item.basis.value,
                    budget_keur=item.budget_keur,
                    calculated_keur=calc_with_infl,
                    manual_override_keur=None,
                    inflation_rate=eff_infl,
                    wth_rate=wth,
                    wth_keur=wth_keur,
                    total_keur=total,
                    is_manual_override=False,
                ))
                group_total += total

            group_results.append(OpexGroupAnnualResult(
                year_index=year,
                group_code=group.code,
                group_name=group.name,
                item_results=tuple(item_results),
                group_total_keur=group_total,
                contingency_from_groups_keur=0.0,
            ))
            group_totals[group.code][y_idx] = group_total
            total_by_year[y_idx] += group_total

    # ── PASS 2: Compute contingency items using group totals from Pass 1 ──────

    contingency_groups = [g for g in groups if g.contingency_pct > 0]

    for cg in contingency_groups:
        for y_idx, year in enumerate(year_indices):
            # Find the group result from Pass 1 for this year/cg
            pass1_idx = next(
                (i for i, gr in enumerate(group_results)
                 if gr.year_index == year and gr.group_code == cg.code),
                None
            )
            if pass1_idx is None:
                continue

            pass1_gr = group_results[pass1_idx]

            # Build updated item list from Pass 1 results (will modify in place)
            updated_items_list = list(pass1_gr.item_results)

            # Contingency amount = contingency_pct × sum(selected groups' totals)
            # selected groups are determined by the contingency item's selected_group_codes
            contingency_amount = 0.0

            for item in cg.items:
                if item.basis != OpexBasis.PCT_OF_SELECTED_GROUPS:
                    continue

                if not item.is_active(year):
                    continue

                override = item.override_for(year)
                if override is not None:
                    final = override.value_keur
                    wth_keur = final * (item.wth_rate or cg.wth_rate)
                    total = final + wth_keur
                    contingency_amount += total

                    # Update item result with manual override
                    existing_item_idx = next(
                        (j for j, ir in enumerate(updated_items_list)
                         if ir.item_code == item.code),
                        None
                    )
                    if existing_item_idx is not None:
                        updated_items_list[existing_item_idx] = OpexItemAnnualResult(
                            year_index=year,
                            group_code=cg.code,
                            group_name=cg.name,
                            item_code=item.code,
                            item_name=item.name,
                            active=True,
                            basis=item.basis.value,
                            budget_keur=item.budget_keur,
                            calculated_keur=0.0,
                            manual_override_keur=override.value_keur,
                            inflation_rate=item.inflation_rate or cg.inflation_rate,
                            wth_rate=item.wth_rate or cg.wth_rate,
                            wth_keur=wth_keur,
                            total_keur=total,
                            is_manual_override=True,
                        )
                    continue

                # selected_group_codes: groups whose totals to sum
                selected_total = sum(
                    group_totals[gc][y_idx]
                    for gc in item.selected_group_codes
                    if gc in group_totals
                )
                base = selected_total * item.budget_keur / 100.0  # budget = decimal %

                eff_infl = item.inflation_rate if item.inflation_rate is not None else cg.inflation_rate
                with_infl = _apply_inflation(base, eff_infl, year, item) if eff_infl else base
                final = with_infl
                wth_rate = item.wth_rate if item.wth_rate > 0 else cg.wth_rate
                wth_keur = final * wth_rate
                total = final + wth_keur
                contingency_amount += total

                # Update item result to reflect actual computed amount (base × pct, not just budget)
                existing_item_idx = next(
                    (j for j, ir in enumerate(updated_items_list)
                     if ir.item_code == item.code),
                    None
                )
                if existing_item_idx is not None:
                    updated_items_list[existing_item_idx] = OpexItemAnnualResult(
                        year_index=year,
                        group_code=cg.code,
                        group_name=cg.name,
                        item_code=item.code,
                        item_name=item.name,
                        active=True,
                        basis=item.basis.value,
                        budget_keur=item.budget_keur,
                        calculated_keur=total,  # actual amount (base × pct + WTH)
                        manual_override_keur=None,
                        inflation_rate=eff_infl,
                        wth_rate=wth_rate,
                        wth_keur=wth_keur,
                        total_keur=total,
                        is_manual_override=False,
                    )

            if contingency_amount == 0.0:
                continue

            # Update group result with contingency amount and finalized item list
            group_results[pass1_idx] = OpexGroupAnnualResult(
                year_index=year,
                group_code=cg.code,
                group_name=cg.name,
                item_results=tuple(updated_items_list),
                group_total_keur=pass1_gr.group_total_keur + contingency_amount,
                contingency_from_groups_keur=contingency_amount,
            )
            total_by_year[y_idx] += contingency_amount

    grand_total = sum(total_by_year)

    return OpexAnnualResult(
        years=year_indices,
        group_results=tuple(group_results),
        total_by_year_keur=tuple(total_by_year),
        grand_total_keur=grand_total,
    )


def _compute_item_base(
    item: OpexItem,
    group: OpexGroup,
    year: int,
    eff_infl: float,
    capacity_mw: float,
    production_mwh_by_year: list[float],
    revenue_keur_by_year: list[float],
    group_totals: dict[str, list[float]],
) -> float:
    """Compute pre-inflation base for an item (before active/override check)."""
    y_idx = year - 1

    if item.basis == OpexBasis.INACTIVE:
        return 0.0

    if item.basis == OpexBasis.EXPLICIT_SCHEDULE:
        if y_idx < len(item.explicit_schedule_keur):
            return item.explicit_schedule_keur[y_idx]
        return 0.0

    if item.basis == OpexBasis.EUR_PER_MW_YEAR:
        return item.budget_keur * capacity_mw / 1000.0  # EUR/MW/year → kEUR

    if item.basis == OpexBasis.EUR_PER_MWH:
        prod = production_mwh_by_year[y_idx] if y_idx < len(production_mwh_by_year) else 0.0
        return item.budget_keur * prod / 1000.0  # EUR/MWh → kEUR

    if item.basis == OpexBasis.PCT_OF_REVENUE:
        rev = revenue_keur_by_year[y_idx] if y_idx < len(revenue_keur_by_year) else 0.0
        return rev * item.budget_keur  # budget = decimal fraction

    if item.basis == OpexBasis.PCT_OF_GROUP:
        # budget = decimal fraction × named group total
        # selected_group_codes[0] = group code to reference
        if item.selected_group_codes and item.selected_group_codes[0] in group_totals:
            return group_totals[item.selected_group_codes[0]][y_idx] * item.budget_keur
        return 0.0

    # fixed_annual_keur, fixed_period_keur
    return item.effective_budget(year)


def _apply_inflation(base: float, infl_rate: float, year: int, item: OpexItem) -> float:
    """Apply inflation to base amount.

    For step changes: inflation exponent counts from step year (not Y1).
    For normal items: exponent = year - 1.
    """
    if infl_rate == 0.0:
        return base

    # Check if there's a step at this year (meaning inflation resets from step year)
    step = item.step_at_or_before(year)
    if step:
        # Inflation counts from step year
        exponent = year - step.year_index
    else:
        exponent = year - 1

    return base * (1 + infl_rate) ** exponent