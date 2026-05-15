"""Runtime adapter for the OPEX line-item engine.

This module bridges the new OpexItem/OpexGroup schema to the existing runtime.
It is imported only when use_opex_line_item_engine=True.

Adapter must NOT import from domain.waterfall (to avoid circular deps).
"""
from __future__ import annotations
from typing import Optional

from domain.inputs import ProjectInputs
from domain.opex.templates.tuho import build_tuho_opex_template
from domain.opex.engine import compute_annual_opex


def opex_line_item_adapter(
    inputs: ProjectInputs,
    capacity_mw: float,
    production_mwh_by_year: Optional[list[float]] = None,
    revenue_keur_by_year: Optional[list[float]] = None,
) -> dict[int, float]:
    """Compute OPEX using the line-item engine.

    Args:
        inputs: project inputs (used to detect TUHO template)
        capacity_mw: project capacity in MW
        production_mwh_by_year: optional annual production per year
        revenue_keur_by_year: optional annual revenue per year

    Returns:
        dict[year_index, opex_keur] — annual OPEX schedule (1-based years)
    """
    horizon = inputs.info.horizon_years

    # Build template — currently only TUHO is supported
    # TODO: extend to other project templates
    template = build_tuho_opex_template()

    result = compute_annual_opex(
        template,
        years=horizon,
        capacity_mw=capacity_mw,
        production_mwh_by_year=production_mwh_by_year,
        revenue_keur_by_year=revenue_keur_by_year,
    )

    return {year: result.total_for_year(year) for year in result.years}


__all__ = ["opex_line_item_adapter"]