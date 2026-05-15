"""OPEX calculation engine — annual-first line-item engine.

compute_annual_opex() is the main entry point.

Two-pass calculation for contingency groups:
  Pass 1: Compute all normal groups/items (PCT_OF_SELECTED_GROUPS items skip, contribute 0)
  Pass 2: Compute PCT_OF_SELECTED_GROUPS items using group_totals from Pass 1

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
  pct_of_selected_groups: base = sum(selected groups' totals) × budget_keur
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
    total_by_year: list[float] = [0.0] * years

    # group_totals[group_code][y_idx] = group total for that year
    group_totals: dict[str, list[float]] = {}
    # group_results: one entry per (group × year) in order
    group_results: list[OpexGroupAnnualResult] = []

    # ── PASS 1: Compute all groups/items (skip PCT_OF_SELECTED_GROUPS) ──────
    for group in groups:
        if not group.items:
            for y_idx, year in enumerate(year_indices):
                group_results.append(OpexGroupAnnualResult(
                    year_index=year, group_code=group.code, group_name=group.name,
                    item_results=(), group_total_keur=0.0,
                    contingency_from_groups_keur=0.0,
                ))
            group_totals[group.code] = [0.0] * years
            continue

        group_totals[group.code] = [0.0] * years

        for y_idx, year in enumerate(year_indices):
            item_results_list: list[OpexItemAnnualResult] = []
            group_total = 0.0

            for item in group.items:
                eff_infl = item.inflation_rate if item.inflation_rate is not None else group.inflation_rate

                if not item.is_active(year):
                    wth = item.wth_rate if item.wth_rate > 0 else group.wth_rate
                    item_results_list.append(OpexItemAnnualResult(
                        year_index=year, group_code=group.code, group_name=group.name,
                        item_code=item.code, item_name=item.name,
                        active=False, basis=item.basis.value,
                        budget_keur=item.budget_keur,
                        calculated_keur=0.0, manual_override_keur=None,
                        inflation_rate=eff_infl or 0.0, wth_rate=wth,
                        wth_keur=0.0, total_keur=0.0,
                        is_manual_override=False,
                    ))
                    continue

                override = item.override_for(year)
                if override is not None:
                    final = override.value_keur
                    wth = item.wth_rate if item.wth_rate > 0 else group.wth_rate
                    wth_keur = final * wth
                    total = final + wth_keur
                    # calculated_keur = what formula would have given
                    base = _compute_item_base(item, group, year, eff_infl,
                                              capacity_mw, production_mwh_by_year,
                                              revenue_keur_by_year, group_totals)
                    calc_with_infl = _apply_inflation(base, eff_infl, year, item)
                    item_results_list.append(OpexItemAnnualResult(
                        year_index=year, group_code=group.code, group_name=group.name,
                        item_code=item.code, item_name=item.name,
                        active=True, basis=item.basis.value,
                        budget_keur=item.budget_keur,
                        calculated_keur=calc_with_infl, manual_override_keur=final,
                        inflation_rate=eff_infl or 0.0, wth_rate=wth,
                        wth_keur=wth_keur, total_keur=total,
                        is_manual_override=True,
                    ))
                    group_total += total
                    continue

                # Skip PCT_OF_SELECTED_GROUPS in pass 1
                if item.basis == OpexBasis.PCT_OF_SELECTED_GROUPS:
                    wth = item.wth_rate if item.wth_rate > 0 else group.wth_rate
                    item_results_list.append(OpexItemAnnualResult(
                        year_index=year, group_code=group.code, group_name=group.name,
                        item_code=item.code, item_name=item.name,
                        active=True, basis=item.basis.value,
                        budget_keur=item.budget_keur,
                        calculated_keur=0.0, manual_override_keur=None,
                        inflation_rate=eff_infl or 0.0, wth_rate=wth,
                        wth_keur=0.0, total_keur=0.0,
                        is_manual_override=False,
                    ))
                    # group_total NOT updated — pct item contributes 0 in pass 1
                    continue

                base = _compute_item_base(item, group, year, eff_infl,
                                          capacity_mw, production_mwh_by_year,
                                          revenue_keur_by_year, group_totals)
                calc_with_infl = _apply_inflation(base, eff_infl, year, item)
                wth = item.wth_rate if item.wth_rate > 0 else group.wth_rate
                wth_keur = calc_with_infl * wth
                total = calc_with_infl + wth_keur

                item_results_list.append(OpexItemAnnualResult(
                    year_index=year, group_code=group.code, group_name=group.name,
                    item_code=item.code, item_name=item.name,
                    active=True, basis=item.basis.value,
                    budget_keur=item.budget_keur,
                    calculated_keur=calc_with_infl, manual_override_keur=None,
                    inflation_rate=eff_infl or 0.0, wth_rate=wth,
                    wth_keur=wth_keur, total_keur=total,
                    is_manual_override=False,
                ))
                group_total += total

            group_results.append(OpexGroupAnnualResult(
                year_index=year, group_code=group.code, group_name=group.name,
                item_results=tuple(item_results_list),
                group_total_keur=group_total,
                contingency_from_groups_keur=0.0,
            ))
            group_totals[group.code][y_idx] = group_total
            total_by_year[y_idx] += group_total

    # ── PASS 2: Compute PCT_OF_SELECTED_GROUPS items using pass 1 group_totals ──
    for group in groups:
        for y_idx, year in enumerate(year_indices):
            pass1_idx = next(
                (i for i, gr in enumerate(group_results)
                 if gr.year_index == year and gr.group_code == group.code),
                None
            )
            if pass1_idx is None:
                continue

            pass1_gr = group_results[pass1_idx]
            updated_items_list = list(pass1_gr.item_results)
            pct_amount = 0.0

            for item in group.items:
                if item.basis != OpexBasis.PCT_OF_SELECTED_GROUPS:
                    continue

                if not item.is_active(year):
                    continue

                override = item.override_for(year)
                if override is not None:
                    final = override.value_keur
                    wth = item.wth_rate if item.wth_rate > 0 else group.wth_rate
                    wth_keur = final * wth
                    total = final + wth_keur
                    pct_amount += total

                    existing_item_idx = next(
                        (j for j, ir in enumerate(updated_items_list)
                         if ir.item_code == item.code),
                        None
                    )
                    if existing_item_idx is not None:
                        updated_items_list[existing_item_idx] = OpexItemAnnualResult(
                            year_index=year, group_code=group.code, group_name=group.name,
                            item_code=item.code, item_name=item.name,
                            active=True, basis=item.basis.value,
                            budget_keur=item.budget_keur,
                            calculated_keur=total, manual_override_keur=final,
                            inflation_rate=0.0, wth_rate=wth,
                            wth_keur=wth_keur, total_keur=total,
                            is_manual_override=True,
                        )
                    continue

                # Calculate base using group_totals from pass 1
                selected_total = sum(
                    group_totals[gc][y_idx]
                    for gc in item.selected_group_codes
                    if gc in group_totals
                )
                base = selected_total * item.budget_keur / 100.0  # budget = decimal %

                eff_infl = item.inflation_rate if item.inflation_rate is not None else group.inflation_rate
                final = _apply_inflation(base, eff_infl, year, item) if eff_infl else base
                wth = item.wth_rate if item.wth_rate > 0 else group.wth_rate
                wth_keur = final * wth
                total = final + wth_keur
                pct_amount += total

                existing_item_idx = next(
                    (j for j, ir in enumerate(updated_items_list)
                     if ir.item_code == item.code),
                    None
                )
                if existing_item_idx is not None:
                    updated_items_list[existing_item_idx] = OpexItemAnnualResult(
                        year_index=year, group_code=group.code, group_name=group.name,
                        item_code=item.code, item_name=item.name,
                        active=True, basis=item.basis.value,
                        budget_keur=item.budget_keur,
                        calculated_keur=total, manual_override_keur=None,
                        inflation_rate=eff_infl or 0.0, wth_rate=wth,
                        wth_keur=wth_keur, total_keur=total,
                        is_manual_override=False,
                    )

            if pct_amount == 0.0:
                continue

            # contingency_pct > 0 means pct amount IS the contingency label
            is_contingency_group = group.contingency_pct > 0
            contingency_add = pct_amount if is_contingency_group else 0.0

            group_results[pass1_idx] = OpexGroupAnnualResult(
                year_index=year, group_code=group.code, group_name=group.name,
                item_results=tuple(updated_items_list),
                group_total_keur=pass1_gr.group_total_keur + pct_amount,
                contingency_from_groups_keur=pass1_gr.contingency_from_groups_keur + contingency_add,
            )
            total_by_year[y_idx] += pct_amount

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

    if item.basis == OpexBasis.PCT_OF_SELECTED_GROUPS:
        # budget_keur = decimal percentage (e.g. 6.0 = 6%)
        selected_total = sum(
            group_totals[gc][y_idx]
            for gc in item.selected_group_codes
            if gc in group_totals
        )
        return selected_total * item.budget_keur / 100.0

    if item.basis == OpexBasis.PCT_OF_GROUP:
        if item.selected_group_codes and item.selected_group_codes[0] in group_totals:
            return group_totals[item.selected_group_codes[0]][y_idx] * item.budget_keur
        return 0.0

    # fixed_annual_keur, fixed_period_keur
    return item.effective_budget(year)


def _apply_inflation(base: float, infl_rate: float, year: int, item: OpexItem) -> float:
    """Apply inflation to base amount.

    For step changes: inflation exponent counts from step year (not Y1).
    For normal items: exponent = year - 1 + item.inflation_start_exponent.

    EXPLICIT_SCHEDULE items: no inflation applied — values are already final.
    """
    if infl_rate == 0.0:
        return base

    # Explicit schedule values are already the final annual amounts
    if item.basis == OpexBasis.EXPLICIT_SCHEDULE:
        return base

    # Check if there's a step at this year (meaning inflation resets from step year)
    step = item.step_at_or_before(year)
    if step:
        # Inflation counts from step year
        exponent = year - step.year_index
    else:
        exponent = year - 1 + item.inflation_start_exponent

    return base * (1 + infl_rate) ** exponent


__all__ = [
    "compute_annual_opex",
]