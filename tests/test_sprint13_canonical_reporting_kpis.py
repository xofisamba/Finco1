"""Sprint 13 reporting KPI source consistency guardrails."""
from __future__ import annotations

import pytest


@pytest.fixture(scope="module")
def tuho_project_and_result():
    from app.project_factories import create_default_tuho_wind1
    from app.ui_runner import _build_period_engine
    from app.waterfall_runner import WaterfallRunner, WaterfallRunConfig

    project = create_default_tuho_wind1()
    engine = _build_period_engine(project)
    result = WaterfallRunner(project, engine).run(
        WaterfallRunConfig.from_inputs(project, engine)
    )
    return project, result


def test_canonical_report_kpis_are_direct_waterfall_result_fields(tuho_project_and_result):
    from app.services.reporting_kpi_sources import (
        CANONICAL_REPORT_KPI_FIELDS,
        build_canonical_report_kpis,
    )

    _, result = tuho_project_and_result
    kpis = build_canonical_report_kpis(result)

    assert set(kpis) == set(CANONICAL_REPORT_KPI_FIELDS)
    for field in CANONICAL_REPORT_KPI_FIELDS:
        assert kpis[field] == getattr(result, field, None)


def test_exec_summary_uses_canonical_report_kpis(tuho_project_and_result):
    from app.services.ic_report_service import build_exec_summary
    from app.services.reporting_kpi_sources import build_canonical_report_kpis

    project, result = tuho_project_and_result
    summary = build_exec_summary(project, result, "Base")
    kpis = build_canonical_report_kpis(result)

    assert summary["project_irr"] == kpis["project_irr"]
    assert summary["equity_irr"] == kpis["equity_irr"]
    assert summary["equity_npv"] == kpis["equity_npv"]
    assert summary["avg_dscr"] == kpis["actual_avg_dscr"]
    assert summary["min_dscr"] == kpis["min_dscr"]
    assert summary["min_llcr"] == kpis["min_llcr"]
    assert summary["total_distribution_keur"] == kpis["total_distribution_keur"]
    assert summary["total_tax_keur"] == kpis["total_tax_keur"]
    assert summary["total_revenue_keur"] == kpis["total_revenue_keur"]
    assert summary["total_ebitda_keur"] == kpis["total_ebitda_keur"]
    assert summary["total_opex_keur"] == kpis["total_opex_keur"]
    assert summary["total_senior_ds_keur"] == kpis["total_senior_ds_keur"]


def test_credit_summary_uses_same_canonical_report_kpis(tuho_project_and_result):
    from app.services.lender_case_service import build_credit_summary
    from app.services.reporting_kpi_sources import build_canonical_report_kpis

    project, result = tuho_project_and_result
    kpis = build_canonical_report_kpis(result)
    credit = build_credit_summary(project, kpis)

    assert credit["project_irr"] == kpis["project_irr"]
    assert credit["equity_irr"] == kpis["equity_irr"]
    assert credit["equity_npv"] == kpis["equity_npv"]
    assert credit["avg_dscr"] == kpis["actual_avg_dscr"]
    assert credit["min_dscr"] == kpis["min_dscr"]
    assert credit["min_llcr"] == kpis["min_llcr"]
    assert credit["total_distribution_keur"] == kpis["total_distribution_keur"]
    assert credit["total_tax_keur"] == kpis["total_tax_keur"]


def test_lender_case_kpis_are_canonical_report_kpis_for_unstressed_case(tuho_project_and_result):
    from app.services.lender_case_service import run_lender_case
    from app.services.reporting_kpi_sources import build_canonical_report_kpis

    project, result = tuho_project_and_result
    lender_case = run_lender_case(project, {})
    canonical = build_canonical_report_kpis(result)

    for field, value in canonical.items():
        if isinstance(value, float):
            assert lender_case["kpis"][field] == pytest.approx(value)
        else:
            assert lender_case["kpis"][field] == value
