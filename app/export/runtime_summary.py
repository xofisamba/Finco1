"""Runtime summary CSV export foundation for Phase 10.

This module reads existing runtime outputs and formats them for review. It does
not change waterfall, tax, SHL, DistributionAccount, or R99/R102 behavior.
"""

from __future__ import annotations

from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
import csv
import os

from app.project_factories import create_default_oborovo, create_default_tuho_wind1
from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner
from domain.period_engine import PeriodEngine


RUNTIME_SUMMARY_COLUMNS = [
    "project",
    "metric",
    "value",
    "unit",
    "runtime_or_preview",
    "governance_status",
    "g20_status",
    "r99_r102_status",
    "export_type",
    "generated_at",
    "source_branch",
    "notes",
]


PROJECT_FACTORIES = {
    "tuho": create_default_tuho_wind1,
    "oborovo": create_default_oborovo,
}


def _project_key(project: str) -> str:
    key = (project or "").strip().lower()
    if key not in PROJECT_FACTORIES:
        raise ValueError("project must be one of: tuho, oborovo")
    return key


def _run_project(project: str):
    project_inputs = PROJECT_FACTORIES[_project_key(project)]()
    engine = PeriodEngine(
        financial_close=project_inputs.info.financial_close,
        construction_months=project_inputs.info.construction_months,
        horizon_years=project_inputs.info.horizon_years,
        ppa_years=project_inputs.revenue.ppa_term_years,
    )
    config = WaterfallRunConfig.from_inputs(project_inputs, engine)
    result = WaterfallRunner(project_inputs, engine).run(config)
    return project_inputs, result


def _sum_period_attr(result, attr: str) -> float:
    return sum(float(getattr(period, attr, 0.0) or 0.0) for period in result.periods)


def _source_branch() -> str:
    return os.getenv("GIT_BRANCH") or os.getenv("BRANCH_NAME") or "unknown"


def build_runtime_summary_rows(
    project: str,
    *,
    generated_at: str | None = None,
    source_branch: str | None = None,
) -> list[dict[str, str]]:
    project_inputs, result = _run_project(project)
    project_name = project_inputs.info.name
    timestamp = generated_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    branch = source_branch or _source_branch()
    governance_status = "review_only"
    g20_status = "BLOCKED"
    r99_r102_status = "NOT APPROVED"

    values = [
        ("active_project", project_name, "", "Factory-bound active project runtime output."),
        ("project_irr", result.project_irr, "ratio", "Existing runtime summary value."),
        ("equity_irr", result.equity_irr, "ratio", "Existing runtime summary value."),
        ("total_revenue_keur", result.total_revenue_keur, "kEUR", "Existing runtime total."),
        ("total_ebitda_keur", result.total_ebitda_keur, "kEUR", "Existing runtime total."),
        ("total_opex_keur", result.total_opex_keur, "kEUR", "Existing runtime total."),
        ("avg_dscr", result.actual_avg_dscr, "x", "Existing runtime debt metric."),
        ("min_dscr", result.actual_min_dscr, "x", "Existing runtime debt metric."),
        (
            "total_distributions_keur",
            _sum_period_attr(result, "distribution_keur"),
            "kEUR",
            "Sum of existing period.distribution_keur values.",
        ),
        (
            "total_shl_service_keur",
            _sum_period_attr(result, "shl_interest_keur")
            + _sum_period_attr(result, "shl_principal_keur"),
            "kEUR",
            "Cash SHL interest plus principal from existing period fields.",
        ),
        ("g20_status", g20_status, "", "Governance label only; this export does not approve G20."),
        (
            "r99_r102_status",
            r99_r102_status,
            "",
            "Governance label only; runtime promotion remains not approved.",
        ),
    ]

    rows: list[dict[str, str]] = []
    for metric, value, unit, notes in values:
        rows.append(
            {
                "project": project_name,
                "metric": metric,
                "value": str(value),
                "unit": unit,
                "runtime_or_preview": "runtime",
                "governance_status": governance_status,
                "g20_status": g20_status,
                "r99_r102_status": r99_r102_status,
                "export_type": "runtime_summary_csv",
                "generated_at": timestamp,
                "source_branch": branch,
                "notes": notes,
            }
        )
    return rows


def build_runtime_summary_csv(
    project: str,
    *,
    generated_at: str | None = None,
    source_branch: str | None = None,
) -> str:
    rows = build_runtime_summary_rows(
        project,
        generated_at=generated_at,
        source_branch=source_branch,
    )
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=RUNTIME_SUMMARY_COLUMNS)
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def write_runtime_summary_csv(
    project: str,
    output_path: str | Path,
    *,
    generated_at: str | None = None,
    source_branch: str | None = None,
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        build_runtime_summary_csv(
            project,
            generated_at=generated_at,
            source_branch=source_branch,
        ),
        encoding="utf-8",
    )
    return path
