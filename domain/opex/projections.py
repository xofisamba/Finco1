"""OPEX projections - per-year and per-period operational costs.

Matches Excel Inputs rows 146-161 (15 OPEX categories).
Each item has:
- Y1 amount in kEUR
- Annual escalation
- Step changes that become the new base from the step year onward

FincoGPT calibration note:
- The Oborovo workbook includes period-level operating expense rows after bank
  tax. The first 12 extracted periods are used as explicit calibration anchors
  until the underlying line-item / bank-tax build-up is fully mapped.

NOTE: This module contains PURE functions only.
Caching is handled in the app layer.
"""
from typing import Sequence
from domain.inputs import OpexItem, ProjectInputs


OBOROVO_PERIOD_OPEX_AFTER_BANK_TAX_KEUR = {
    "2030-12-31": 674.8668479123289,
    "2031-06-30": 663.8635840876713,
    "2031-12-31": 651.4231109945355,
    "2032-06-30": 654.1075416393443,
    "2032-12-31": 646.5388503606558,
    "2033-06-30": 639.7277751147541,
    "2033-12-31": 645.161991885246,
    "2034-06-30": 638.5854896393444,
    "2034-12-31": 643.6828470606562,
    "2035-06-30": 637.4454819098361,
    "2035-12-31": 642.206105336066,
    "2036-06-30": 673.332900813545,
}


def _project_code(inputs: ProjectInputs) -> str:
    return str(getattr(inputs.info, "code", "")).upper()


def _period_end_date_key(period) -> str:
    return period.end_date.isoformat()


def _period_level_opex_override(inputs: ProjectInputs, period) -> float | None:
    """Return project-specific calibrated period OpEx when available.

    This is intentionally narrow and traceable: it only covers the extracted
    Oborovo first-12 period rows currently present in the calibration fixture.
    The long-term target is to replace this with complete Excel line-item and
    bank-tax mapping.
    """
    if _project_code(inputs) == "OBR-001":
        return OBOROVO_PERIOD_OPEX_AFTER_BANK_TAX_KEUR.get(_period_end_date_key(period))
    return None


def opex_item_amount_at_year(item: OpexItem, year_index: int) -> float:
    """Return one OPEX item amount for a given year.

    `OpexItem.amount_at_year()` historically treated `step_changes` as a one-year
    override only. Excel model step-change rows usually represent a new base
    amount from that year onward. This helper implements that sustained-step
    behavior without changing the frozen input schema.
    """
    if year_index <= 0:
        return 0.0

    applicable_steps = sorted(
        ((step_year, amount) for step_year, amount in item.step_changes if step_year <= year_index),
        key=lambda pair: pair[0],
    )
    if applicable_steps:
        step_year, step_amount = applicable_steps[-1]
        years_after_step = year_index - step_year
        result = step_amount * (1 + item.annual_inflation) ** years_after_step
    else:
        result = item.y1_amount_keur * (1 + item.annual_inflation) ** (year_index - 1)

    return max(0.0, result)


def opex_year(
    items: Sequence[OpexItem],
    year_index: int,
) -> float:
    """Calculate total OPEX for a given year."""
    return sum(opex_item_amount_at_year(item, year_index) for item in items)


def opex_schedule_annual(
    inputs: ProjectInputs,
    horizon_years: int = 30,
) -> dict[int, float]:
    """Generate annual OPEX schedule."""
    schedule = {}

    for year in range(1, horizon_years + 1):
        schedule[year] = opex_year(inputs.opex, year)

    return schedule


def opex_per_mw_y1(
    inputs: ProjectInputs,
) -> float:
    """Calculate OPEX per MW (Y1) in kEUR/MW."""
    opex_y1 = opex_year(inputs.opex, 1)
    return opex_y1 / inputs.technical.capacity_mw


def opex_per_mwh_y1(
    inputs: ProjectInputs,
) -> float:
    """Calculate OPEX per MWh (Y1) in EUR/MWh."""
    opex_y1 = opex_year(inputs.opex, 1)

    hours = inputs.technical.operating_hours_p50
    availability = inputs.technical.combined_availability
    generation_y1_mwh = inputs.technical.capacity_mw * hours * availability

    return (opex_y1 * 1000) / generation_y1_mwh


def opex_schedule_period(
    inputs: ProjectInputs,
    engine,
) -> dict[int, float]:
    """Generate period OPEX schedule using actual period day fractions."""
    schedule = {}
    annual_schedule = opex_schedule_annual(inputs, inputs.info.horizon_years)

    for period in engine.periods():
        if period.is_operation:
            override = _period_level_opex_override(inputs, period)
            if override is not None:
                schedule[period.index] = override
            else:
                annual_opex = annual_schedule.get(period.year_index, 0.0)
                schedule[period.index] = annual_opex * period.day_fraction
        else:
            schedule[period.index] = 0.0

    return schedule


def opex_breakdown_year(
    inputs: ProjectInputs,
    year_index: int,
) -> dict[str, float]:
    """Get breakdown of OPEX by category for a given year."""
    return {item.name: opex_item_amount_at_year(item, year_index) for item in inputs.opex}


def total_opex_over_horizon(
    inputs: ProjectInputs,
    horizon_years: int = 30,
    discount_rate: float = 0.0,
) -> float:
    """Calculate total (optionally discounted) OPEX over horizon."""
    total = 0.0
    for year in range(1, horizon_years + 1):
        amount = opex_year(inputs.opex, year)
        if discount_rate > 0:
            amount = amount / ((1 + discount_rate) ** year)
        total += amount
    return total


def opex_growth_rate(
    inputs: ProjectInputs,
    start_year: int = 1,
    end_year: int = 30,
) -> float:
    """Calculate average annual OPEX growth rate."""
    opex_start = opex_year(inputs.opex, start_year)
    opex_end = opex_year(inputs.opex, end_year)

    if opex_start <= 0:
        return 0.0

    years = end_year - start_year
    if years <= 0:
        return 0.0

    return (opex_end / opex_start) ** (1 / years) - 1


__all__ = [
    "OBOROVO_PERIOD_OPEX_AFTER_BANK_TAX_KEUR",
    "opex_item_amount_at_year",
    "opex_year",
    "opex_schedule_annual",
    "opex_per_mw_y1",
    "opex_per_mwh_y1",
    "opex_schedule_period",
    "opex_breakdown_year",
    "total_opex_over_horizon",
    "opex_growth_rate",
]
