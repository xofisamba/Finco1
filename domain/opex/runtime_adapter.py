"""OPEX runtime adapter — bridges compute_annual_opex to the runtime.

This module provides the runtime integration point for the new OPEX
line-item engine. It is ONLY activated when inputs.info.use_opex_line_item_engine=True.

When the flag is False, existing opex_schedule_annual path is used unchanged.
When the flag is True, compute_annual_opex with the appropriate template is used.

This file is intentionally isolated — no revenue changes.
"""
from __future__ import annotations

from domain.inputs import ProjectInputs
from domain.opex.engine import compute_annual_opex
from domain.opex.templates.tuho import build_tuho_opex_template


def opex_line_item_adapter(inputs: ProjectInputs) -> dict[int, float]:
    """Build annual OPEX schedule using the new line-item engine.

    This is ONLY called when inputs.info.use_opex_line_item_engine=True.
    For default (False), the existing opex_schedule_annual path is used.

    Currently supports TUHO Wind 1 only (project code = "TUHO-WIND-1").

    Args:
        inputs: ProjectInputs instance

    Returns:
        Dict mapping year_index (1-based) → annual OPEX in kEUR

    Raises:
        ValueError: if use_opex_line_item_engine=True but project not supported
    """
    project_code = inputs.info.code

    if project_code == "TUHO-WIND-1":
        groups = build_tuho_opex_template()
        result = compute_annual_opex(
            groups,
            years=inputs.info.horizon_years,
            capacity_mw=inputs.technical.capacity_mw,
        )
        return {y: result.total_for_year(y) for y in range(1, inputs.info.horizon_years + 1)}
    else:
        raise ValueError(
            f"use_opex_line_item_engine=True but project '{project_code}' "
            f"not supported by opex_line_item_adapter. "
            f"Only 'TUHO-WIND-1' is currently supported."
        )


def build_opex_schedule_annual_from_line_items(inputs: ProjectInputs) -> dict[int, float]:
    """Public adapter alias — mirrors opex_schedule_annual interface.

    Use this function in waterfall_engine when the flag is True.
    It delegates to opex_line_item_adapter for supported projects.

    Args:
        inputs: ProjectInputs instance

    Returns:
        Dict mapping year_index → annual OPEX in kEUR
    """
    return opex_line_item_adapter(inputs)