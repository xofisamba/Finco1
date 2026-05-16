"""Runtime adapter for offline construction schedule diagnostics.

The adapter is intentionally diagnostic-only in this PR. It selects a supported
offline construction template and returns the computed construction schedule,
but it does not mutate project inputs and does not import the waterfall domain.
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.construction.engine import compute_construction_schedule
from domain.construction.result import ConstructionMonthlyEntry, ConstructionScheduleResult
from domain.construction.templates.oborovo import build_oborovo_construction_config
from domain.construction.templates.tuho import build_tuho_construction_config


SUPPORTED_PROJECT_CODES = {"TUHO-WIND-1", "Oborovo", "OBR-001"}


@dataclass(frozen=True)
class ConstructionRuntimeResult:
    """Diagnostic construction runtime bridge result."""

    project_code: str
    construction_months: int
    total_uses_keur: float
    equity_draw_keur: float
    shl_principal_draw_keur: float
    junior_draw_keur: float
    senior_principal_draw_keur: float
    shl_idc_keur: float
    senior_idc_keur: float
    opening_shl_balance_keur: float
    opening_senior_balance_keur: float
    uses_funding_delta_keur: float
    senior_idc_delta_to_target_keur: float | None
    monthly_entries: tuple[ConstructionMonthlyEntry, ...]
    validation_notes: tuple[str, ...]
    source_result: ConstructionScheduleResult


def build_runtime_construction_schedule(inputs) -> ConstructionRuntimeResult:
    """Build diagnostic construction outputs for a supported project."""

    project_code = getattr(getattr(inputs, "info", None), "code", "")
    if project_code == "TUHO-WIND-1":
        config = build_tuho_construction_config()
    elif project_code in {"Oborovo", "OBR-001"}:
        config = build_oborovo_construction_config()
    else:
        raise ValueError(
            "Construction schedule runtime engine is only supported for "
            f"TUHO-WIND-1 and Oborovo/OBR-001; got project code {project_code!r}."
        )

    result = compute_construction_schedule(config)
    notes = _build_validation_notes(inputs, result)
    return ConstructionRuntimeResult(
        project_code=project_code,
        construction_months=len(result.monthly_entries),
        total_uses_keur=result.total_uses_keur,
        equity_draw_keur=result.total_equity_draw_keur,
        shl_principal_draw_keur=result.total_shl_draw_keur,
        junior_draw_keur=result.total_junior_draw_keur,
        senior_principal_draw_keur=result.total_senior_draw_keur,
        shl_idc_keur=result.total_shl_idc_keur,
        senior_idc_keur=result.total_senior_idc_keur,
        opening_shl_balance_keur=result.opening_shl_balance_keur,
        opening_senior_balance_keur=result.opening_senior_balance_keur,
        uses_funding_delta_keur=result.uses_funding_delta_keur,
        senior_idc_delta_to_target_keur=result.senior_idc_delta_to_target_keur,
        monthly_entries=result.monthly_entries,
        validation_notes=tuple(notes),
        source_result=result,
    )


def _build_validation_notes(inputs, result: ConstructionScheduleResult) -> list[str]:
    notes = [
        "diagnostic_only: construction outputs are not routed into waterfall cash flows",
        "manual_precedence: existing project inputs remain authoritative for runtime balances",
    ]
    financing = getattr(inputs, "financing", None)
    if financing is None:
        return notes

    manual_shl_principal = float(getattr(financing, "shl_amount_keur", 0.0) or 0.0)
    manual_shl_idc = float(getattr(financing, "shl_idc_keur", 0.0) or 0.0)
    manual_senior_debt = float(
        getattr(financing, "fixed_debt_keur", None)
        or getattr(financing, "senior_debt_amount_keur", 0.0)
        or 0.0
    )

    if abs(manual_shl_principal - result.total_shl_draw_keur) > 0.01:
        notes.append(
            "manual_mismatch: shl_amount_keur differs from computed SHL principal draw"
        )
    if abs(manual_shl_idc - result.total_shl_idc_keur) > 0.01:
        notes.append(
            "manual_mismatch: shl_idc_keur differs from computed SHL IDC; computed IDC remains diagnostic"
        )
    if abs(manual_senior_debt - result.total_senior_draw_keur) > 0.01:
        notes.append(
            "manual_mismatch: senior debt input differs from computed senior principal draw"
        )
    notes.append(
        "double_count_guard: computed IDC is not added on top of manual SHL or senior debt inputs"
    )
    return notes


__all__ = ["ConstructionRuntimeResult", "build_runtime_construction_schedule"]
