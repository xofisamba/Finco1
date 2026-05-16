"""Offline annual-first OPEX line-item engine."""

from __future__ import annotations

from domain.opex.line_items import OpexBasis, OpexGroup, OpexItem
from domain.opex.result import (
    OpexAnnualResult,
    OpexGroupAnnualResult,
    OpexItemAnnualResult,
)


def compute_annual_opex(
    groups: list[OpexGroup],
    *,
    years: int,
    capacity_mw: float = 0.0,
    production_mwh_by_year: list[float] | tuple[float, ...] | None = None,
    revenue_keur_by_year: list[float] | tuple[float, ...] | None = None,
) -> OpexAnnualResult:
    """Compute annual OPEX without wiring results into runtime cash flow."""

    production = list(production_mwh_by_year or [0.0] * years)
    revenue = list(revenue_keur_by_year or [0.0] * years)
    year_indices = tuple(range(1, years + 1))
    totals_by_year = [0.0] * years
    group_totals: dict[str, list[float]] = {group.code: [0.0] * years for group in groups}
    group_results: list[OpexGroupAnnualResult] = []

    for group in groups:
        for pos, year in enumerate(year_indices):
            item_results: list[OpexItemAnnualResult] = []
            group_total = 0.0
            for item in group.items:
                result = _compute_item_result(
                    item,
                    group,
                    year,
                    pos,
                    capacity_mw,
                    production,
                    revenue,
                    group_totals,
                    defer_selected_groups=True,
                )
                item_results.append(result)
                group_total += result.total_keur

            group_totals[group.code][pos] = group_total
            totals_by_year[pos] += group_total
            group_results.append(
                OpexGroupAnnualResult(
                    year_index=year,
                    group_code=group.code,
                    group_name=group.name,
                    item_results=tuple(item_results),
                    group_total_keur=group_total,
                )
            )

    for group in groups:
        selected_items = [
            item for item in group.items if item.basis == OpexBasis.PCT_OF_SELECTED_GROUPS
        ]
        if not selected_items:
            continue

        for pos, year in enumerate(year_indices):
            index = next(
                idx
                for idx, result in enumerate(group_results)
                if result.group_code == group.code and result.year_index == year
            )
            original = group_results[index]
            updated_items = list(original.item_results)
            added_total = 0.0

            for item in selected_items:
                result = _compute_item_result(
                    item,
                    group,
                    year,
                    pos,
                    capacity_mw,
                    production,
                    revenue,
                    group_totals,
                    defer_selected_groups=False,
                )
                item_index = next(
                    idx for idx, existing in enumerate(updated_items) if existing.item_code == item.code
                )
                added_total += result.total_keur - updated_items[item_index].total_keur
                updated_items[item_index] = result

            group_totals[group.code][pos] += added_total
            totals_by_year[pos] += added_total
            group_results[index] = OpexGroupAnnualResult(
                year_index=year,
                group_code=group.code,
                group_name=group.name,
                item_results=tuple(updated_items),
                group_total_keur=original.group_total_keur + added_total,
                contingency_from_groups_keur=added_total if group.contingency_pct else 0.0,
            )

    return OpexAnnualResult(
        years=year_indices,
        group_results=tuple(group_results),
        total_by_year_keur=tuple(totals_by_year),
        grand_total_keur=sum(totals_by_year),
    )


def _compute_item_result(
    item: OpexItem,
    group: OpexGroup,
    year: int,
    pos: int,
    capacity_mw: float,
    production: list[float],
    revenue: list[float],
    group_totals: dict[str, list[float]],
    *,
    defer_selected_groups: bool,
) -> OpexItemAnnualResult:
    effective_inflation = item.inflation_rate
    if effective_inflation is None:
        effective_inflation = group.inflation_rate
    effective_wth = group.wth_rate if item.wth_rate is None else item.wth_rate

    if not item.is_active(year) or item.basis == OpexBasis.INACTIVE:
        return _item_result(item, group, year, False, 0.0, None, effective_inflation, effective_wth, 0.0)

    if defer_selected_groups and item.basis == OpexBasis.PCT_OF_SELECTED_GROUPS:
        return _item_result(item, group, year, True, 0.0, None, effective_inflation, effective_wth, 0.0)

    calculated = _apply_inflation(
        _item_base(item, year, pos, capacity_mw, production, revenue, group_totals),
        effective_inflation,
        year,
        item,
    )

    override = item.override_for(year)
    final_before_wth = override.value_keur if override else calculated
    wth_keur = final_before_wth * effective_wth
    return _item_result(
        item,
        group,
        year,
        True,
        calculated,
        override.value_keur if override else None,
        effective_inflation,
        effective_wth,
        wth_keur,
    )


def _item_result(
    item: OpexItem,
    group: OpexGroup,
    year: int,
    active: bool,
    calculated: float,
    override: float | None,
    inflation: float,
    wth: float,
    wth_keur: float,
) -> OpexItemAnnualResult:
    base_total = override if override is not None else calculated
    return OpexItemAnnualResult(
        year_index=year,
        group_code=group.code,
        group_name=group.name,
        item_code=item.code,
        item_name=item.name,
        active=active,
        basis=item.basis.value,
        budget_keur=item.budget_keur,
        calculated_keur=calculated,
        manual_override_keur=override,
        inflation_rate=inflation,
        wth_rate=wth,
        wth_keur=wth_keur,
        total_keur=base_total + wth_keur,
        is_manual_override=override is not None,
    )


def _item_base(
    item: OpexItem,
    year: int,
    pos: int,
    capacity_mw: float,
    production: list[float],
    revenue: list[float],
    group_totals: dict[str, list[float]],
) -> float:
    if item.basis == OpexBasis.EXPLICIT_SCHEDULE:
        return item.explicit_schedule_keur[pos] if pos < len(item.explicit_schedule_keur) else 0.0
    if item.basis == OpexBasis.EUR_PER_MW_YEAR:
        return item.budget_keur * capacity_mw / 1000.0
    if item.basis == OpexBasis.EUR_PER_MWH:
        return item.budget_keur * (production[pos] if pos < len(production) else 0.0) / 1000.0
    if item.basis == OpexBasis.PCT_OF_REVENUE:
        return item.budget_keur * (revenue[pos] if pos < len(revenue) else 0.0)
    if item.basis == OpexBasis.PCT_OF_GROUP:
        if not item.selected_group_codes:
            return 0.0
        return item.budget_keur * group_totals.get(item.selected_group_codes[0], [0.0])[pos]
    if item.basis == OpexBasis.PCT_OF_SELECTED_GROUPS:
        return item.budget_keur / 100.0 * sum(
            group_totals[group_code][pos]
            for group_code in item.selected_group_codes
            if group_code in group_totals
        )
    return item.effective_budget(year)


def _apply_inflation(base: float, inflation: float, year: int, item: OpexItem) -> float:
    if inflation == 0.0 or item.basis == OpexBasis.EXPLICIT_SCHEDULE:
        return base
    step = item.step_at_or_before(year)
    exponent = year - step.year_index if step else year - 1 + item.inflation_start_exponent
    return base * (1 + inflation) ** exponent


__all__ = ["compute_annual_opex"]
