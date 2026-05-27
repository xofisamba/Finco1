"""Phase 20P — Revenue / OPEX / CFADS Diagnostic Bridge.

This module provides diagnostic tools to compare Excel anchor values against
Python runtime outputs period-by-period. It is purely diagnostic — it does not
change any runtime calculations or model outputs.

Diagnostic status conventions:
    PASS  — python value within tolerance of Excel anchor
    WARN  — outside tolerance but documented known cause
    FAIL  — significant unexplained gap
    MISSING — metric not exposed by current runtime
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class DiagnosticStatus(Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    MISSING = "MISSING"


@dataclass(frozen=True)
class DiagnosticRow:
    """Single metric comparison row."""
    project_code: str
    period_index: int          # 0-based waterfall period index
    period_label: str          # e.g. "P4" or "Y2-H1"
    metric: str
    excel_value: Optional[float]
    python_value: Optional[float]
    delta: Optional[float]     # python - excel
    tolerance: float            # absolute tolerance in kEUR (or fraction for %)
    status: DiagnosticStatus
    likely_cause: str = ""
    source_reference: str = ""
    notes: str = ""

    def is_pass(self) -> bool:
        return self.status == DiagnosticStatus.PASS

    def is_fail(self) -> bool:
        return self.status == DiagnosticStatus.FAIL

    def is_missing(self) -> bool:
        return self.status == DiagnosticStatus.MISSING


@dataclass
class DiagnosticTable:
    """Collection of diagnostic rows for a project."""
    rows: list[DiagnosticRow] = field(default_factory=list)
    project_code: str = ""
    period_index: int = 0
    period_label: str = ""

    def add(self, row: DiagnosticRow) -> None:
        self.rows.append(row)

    def pass_count(self) -> int:
        return sum(1 for r in self.rows if r.status == DiagnosticStatus.PASS)

    def fail_count(self) -> int:
        return sum(1 for r in self.rows if r.status == DiagnosticStatus.FAIL)

    def missing_count(self) -> int:
        return sum(1 for r in self.rows if r.status == DiagnosticStatus.MISSING)

    def warn_count(self) -> int:
        return sum(1 for r in self.rows if r.status == DiagnosticStatus.WARN)

    def summary(self) -> dict:
        return {
            "project": self.project_code,
            "period": self.period_label,
            "total": len(self.rows),
            "pass": self.pass_count(),
            "fail": self.fail_count(),
            "warn": self.warn_count(),
            "missing": self.missing_count(),
        }


def make_row(
    project_code: str,
    period_index: int,
    period_label: str,
    metric: str,
    excel_value: Optional[float],
    python_value: Optional[float],
    tolerance: float,
    likely_cause: str = "",
    source_reference: str = "",
    notes: str = "",
) -> DiagnosticRow:
    if python_value is None or excel_value is None:
        status = DiagnosticStatus.MISSING
        delta = None
    else:
        delta = python_value - excel_value
        if abs(delta) <= tolerance:
            status = DiagnosticStatus.PASS
        else:
            status = DiagnosticStatus.FAIL

    return DiagnosticRow(
        project_code=project_code,
        period_index=period_index,
        period_label=period_label,
        metric=metric,
        excel_value=excel_value,
        python_value=python_value,
        delta=delta,
        tolerance=tolerance,
        status=status,
        likely_cause=likely_cause,
        source_reference=source_reference,
        notes=notes,
    )


# ─── Excel anchor values (from Claude review / Phase 20N) ───────────────────

TUHO_P4_ANCHORS: dict[str, float] = {
    "production_mwh":        73_468.93,
    "ppa_revenue_keur":      4_186.48,   # operating revenue (net after balancing)
    "co2_revenue_keur":          307.91,   # part of ppa_revenue in Excel
    "balancing_cost_keur":       577.75,   # Excel balancing magnitude (low)
    "opex_keur":             -1_023.26,   # negative in Excel
    "ebitda_keur":            3_163.22,
    "cfads_keur":             3_163.22,   # = EBITDA since no cash tax in TUHO construction
    "senior_service_keur":   2_180.24,
    "senior_interest_keur":  1_240.28,
    "senior_principal_keur":    939.96,
    "shl_sweep_keur":          982.99,
    "net_dividends_keur":        0.0,
}

OBOROVO_P4_ANCHORS: dict[str, float] = {
    "production_mwh":        54_580.16,
    "ppa_revenue_keur":      3_255.16,
    "co2_revenue_keur":         82.0,    # approximate from Phase 20N
    "balancing_cost_keur":        0.0,
    "opex_keur":              -644.34,
    "ebitda_keur":           2_610.82,
    "cfads_keur":            2_610.82,
    "senior_service_keur":  2_270.28,
    "shl_sweep_keur":          340.54,
    "net_dividends_keur":        0.0,
}


# ─── Diagnostic builder ─────────────────────────────────────────────────────

def build_tuho_p4_diagnostic(
    python_generation_mwh: float,
    python_ppa_revenue_keur: float,
    python_co2_revenue_keur: float,
    python_balancing_keur: float,
    python_net_revenue_keur: float,
    python_opex_keur: float,
    python_ebitda_keur: float,
    python_cfads_keur: float,
    python_senior_ds_keur: float,
    python_senior_interest_keur: float,
    python_senior_principal_keur: float,
    python_shl_sweep_keur: float,
    python_distribution_keur: float,
    period_label: str = "P4",
) -> DiagnosticTable:
    """Build TUHO P4 diagnostic table comparing Excel anchors vs Python runtime."""
    table = DiagnosticTable(project_code="TUHO", period_index=3, period_label=period_label)

    def row(metric, excel_val, python_val, tol, cause="", ref="", notes=""):
        table.add(make_row(
            project_code="TUHO",
            period_index=3,
            period_label=period_label,
            metric=metric,
            excel_value=excel_val,
            python_value=python_val,
            tolerance=tol,
            likely_cause=cause,
            source_reference=ref,
            notes=notes,
        ))

    row("production_mwh",         TUHO_P4_ANCHORS["production_mwh"],        python_generation_mwh,        0.5,       "Production from P50 hourly * availability * degradation")
    row("ppa_revenue_keur",       TUHO_P4_ANCHORS["ppa_revenue_keur"],      python_net_revenue_keur,      5.0,       "Net after balancing — check balancing rate vs Excel")
    row("co2_revenue_keur",       TUHO_P4_ANCHORS["co2_revenue_keur"],       python_co2_revenue_keur,      1.0,       "CO2 schedule declining from ~4.2 EUR/MWh")
    row("balancing_cost_keur",   TUHO_P4_ANCHORS["balancing_cost_keur"],   python_balancing_keur,        5.0,       "Excel uses low balancing rate; Python uses 8 EUR/MWh")
    row("opex_keur",             TUHO_P4_ANCHORS["opex_keur"],               python_opex_keur,             5.0,       "OPEX Y1=1,998 kEUR; P4 slightly higher due to inflation")
    row("ebitda_keur",           TUHO_P4_ANCHORS["ebitda_keur"],             python_ebitda_keur,           5.0,       "EBITDA = revenue + CO2 - balancing - OPEX")
    row("cfads_keur",            TUHO_P4_ANCHORS["cfads_keur"],              python_cfads_keur,            5.0,       "CFADS = EBITDA (TUHO has no cash tax in P4)")
    row("senior_service_keur",   TUHO_P4_ANCHORS["senior_service_keur"],     python_senior_ds_keur,       5.0,       "senior_interest + senior_principal")
    row("senior_interest_keur",  TUHO_P4_ANCHORS["senior_interest_keur"],    python_senior_interest_keur, 5.0,       "Interest on opening senior balance")
    row("senior_principal_keur", TUHO_P4_ANCHORS["senior_principal_keur"],   python_senior_principal_keur, 5.0,       "Sculpted principal — divisor=1.20 in PPA period")
    row("shl_sweep_keur",        TUHO_P4_ANCHORS["shl_sweep_keur"],         python_shl_sweep_keur,       5.0,       "SHL cash sweep after senior — P4 may not have sweep trigger")
    row("net_dividends_keur",    TUHO_P4_ANCHORS["net_dividends_keur"],     python_distribution_keur,     1.0,       "Distribution 0 during lockup")

    return table


def build_oborovo_p4_diagnostic(
    python_generation_mwh: float,
    python_ppa_revenue_keur: float,
    python_co2_revenue_keur: float,
    python_balancing_keur: float,
    python_net_revenue_keur: float,
    python_opex_keur: float,
    python_ebitda_keur: float,
    python_cfads_keur: float,
    python_senior_ds_keur: float,
    python_shl_sweep_keur: float,
    python_distribution_keur: float,
    period_label: str = "P4",
) -> DiagnosticTable:
    """Build Oborovo P4 diagnostic table comparing Excel anchors vs Python runtime."""
    table = DiagnosticTable(project_code="Oborovo", period_index=3, period_label=period_label)

    def row(metric, excel_val, python_val, tol, cause="", ref="", notes=""):
        table.add(make_row(
            project_code="Oborovo",
            period_index=3,
            period_label=period_label,
            metric=metric,
            excel_value=excel_val,
            python_value=python_val,
            tolerance=tol,
            likely_cause=cause,
            source_reference=ref,
            notes=notes,
        ))

    row("production_mwh",        OBOROVO_P4_ANCHORS["production_mwh"],       python_generation_mwh,       0.5,    "Production from P50 hourly * availability")
    row("ppa_revenue_keur",      OBOROVO_P4_ANCHORS["ppa_revenue_keur"],     python_net_revenue_keur,     5.0,    "Net after balancing — Oborovo balancing=0")
    row("co2_revenue_keur",      OBOROVO_P4_ANCHORS["co2_revenue_keur"],     python_co2_revenue_keur,     2.0,    "CO2 flat 1.5 EUR/MWh — may vary slightly with rounding")
    row("balancing_cost_keur",   OBOROVO_P4_ANCHORS["balancing_cost_keur"],  python_balancing_keur,       0.5,    "Oborovo balancing=0 confirmed")
    row("opex_keur",            OBOROVO_P4_ANCHORS["opex_keur"],             python_opex_keur,            5.0,    "OPEX Y1=1,338 kEUR; P4 inflation-adjusted")
    row("ebitda_keur",          OBOROVO_P4_ANCHORS["ebitda_keur"],           python_ebitda_keur,          5.0,    "EBITDA = net revenue - OPEX")
    row("cfads_keur",           OBOROVO_P4_ANCHORS["cfads_keur"],            python_cfads_keur,           5.0,    "CFADS = EBITDA (Oborovo has 0 tax in model)")
    row("senior_service_keur",   OBOROVO_P4_ANCHORS["senior_service_keur"],  python_senior_ds_keur,       5.0,    "senior_interest + senior_principal")
    row("shl_sweep_keur",        OBOROVO_P4_ANCHORS["shl_sweep_keur"],       python_shl_sweep_keur,       5.0,    "SHL sweep from R99 cash after senior DS — P4 may be 0")
    row("net_dividends_keur",    OBOROVO_P4_ANCHORS["net_dividends_keur"],   python_distribution_keur,    1.0,    "Distribution 0 during lockup")

    return table


def diagnostic_table_to_list(table: DiagnosticTable) -> list[dict]:
    """Convert DiagnosticTable to list of dicts for JSON/CSV export."""
    return [
        {
            "project_code": r.project_code,
            "period_label": r.period_label,
            "metric": r.metric,
            "excel_value": r.excel_value,
            "python_value": r.python_value,
            "delta": r.delta,
            "tolerance": r.tolerance,
            "status": r.status.value,
            "likely_cause": r.likely_cause,
            "source_reference": r.source_reference,
            "notes": r.notes,
        }
        for r in table.rows
    ]
