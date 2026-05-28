"""Phase 20T — Oborovo DSCR / Cash Base Diagnostic.

This module provides diagnostic tools to explain why Oborovo still differs
materially from Excel after Phase 20S.

The core question: Why does Python produce a materially different cash base
for Oborovo than Excel?

Excel Oborovo P4 anchors:
  - Production          = 54,580.16 MWh
  - Operating Revenue   = 3,255.16 kEUR
  - OPEX                = -644.34 kEUR
  - EBITDA              = 2,610.82 kEUR
  - CFADS               = 2,610.82 kEUR
  - Senior Service      = 2,270.28 kEUR
  - SHL Sweep           = 340.54 kEUR
  - Distribution         = 0

Python Oborovo P4 (current default):
  - Production          = 54,580.16 MWh ✅
  - Revenue (waterfall) = 3,255.16 kEUR ✅
  - OPEX                = 676.79 kEUR ❌ (+32.45 kEUR)
  - EBITDA              = 2,578.37 kEUR ❌ (-32.45 kEUR)
  - Senior Service      = 2,057.91 kEUR ❌ (-212.37 kEUR)
  - SHL Sweep           = 0.00 kEUR ❌ (default: no sweep)
  - Distribution        = 64.97 kEUR ❌ (leakage vs Excel 0)

This is purely diagnostic — it does not change any runtime calculations.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class DiagnosticStatus(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    MISSING = "MISSING"
    UNRESOLVED = "UNRESOLVED"


# ─── Excel anchor values for Oborovo P4 ─────────────────────────────────────

EXCEL_P4_ANCHORS = {
    "production_mwh":            54_580.16,
    "operating_revenue_keur":    3_255.16,   # electricity + CO2 gross revenue
    "opex_keur":                   -644.34,   # negative in Excel
    "ebitda_keur":                2_610.82,
    "cfads_keur":                 2_610.82,
    "senior_service_keur":        2_270.28,
    "senior_interest_keur":           None,   # not independently anchored
    "senior_principal_keur":          None,   # not independently anchored
    "shl_sweep_keur":               340.54,
    "distribution_keur":                0.0,
    "cash_after_senior_keur":         None,   # = cfads - senior_service = 340.54
    "cash_for_shl_keur":              None,   # = cash_after_senior (no DSRA in lockup)
}

# Python Oborovo P4 values (from waterfall run on default config)
PYTHON_P4_VALUES = {
    "production_mwh":            54_580.16,
    "operating_revenue_keur":    3_255.16,   # = p4.revenue_keur (matches Excel)
    "opex_keur":                   676.79,   # abs value; Excel is -644.34
    "ebitda_keur":                2_578.37,
    "cfads_keur":                2_578.37,   # = EBITDA (no cash tax in model)
    "senior_service_keur":       2_057.91,
    "senior_interest_keur":      1_137.03,
    "senior_principal_keur":       920.87,
    "shl_sweep_keur":                  0.0,  # default: no sweep trigger
    "distribution_keur":             64.97,  # leakage vs Excel 0
    "cash_after_senior_keur":       520.46, # cf_after_tax - senior_ds
    "cash_for_shl_keur":            520.46, # same in default config
}

# Python with partial_pay_sweep opt-in
PYTHON_P4_PARTIAL_PAY_SWEEP = {
    "shl_sweep_keur":             66.59,
    "distribution_keur":              0.0,   # leakage fixed in opt-in mode
    "cash_for_shl_keur":           520.46,
}

# ─── CO2 Status ──────────────────────────────────────────────────────────────

CO2_STATUS = {
    "excel_status":          "UNRESOLVED",   # flat 1.5 or declining curve?
    "python_status":         "FLAT",
    "python_rate_eur_mwh":    1.50,
    "python_p4_co2_keur":     81.97,
    "note": (
        "Python CO2 is flat 1.5 EUR/MWh across all operating periods. "
        "Phase 20S report stated Excel has 'actual declining curve' — this "
        "contradiction is unresolved. Need Excel source verification. "
        "If Excel is flat, Python matches. If Excel declines, Python needs fixing."
    ),
}


# ─── Diagnostic Row ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class CashBaseRow:
    """Single metric comparison row for Oborovo cash base diagnostic."""
    project_code: str = "OBOROVO"
    period_index: int = 3
    period_label: str = "P4"
    metric: str = ""
    excel_value: Optional[float] = None
    python_value: Optional[float] = None
    delta: Optional[float] = None          # python - excel
    tolerance: float = 0.0
    status: DiagnosticStatus = DiagnosticStatus.MISSING
    upstream_of_shl: bool = False           # True = issue is before SHL waterfall
    likely_cause: str = ""
    source_reference: str = ""
    notes: str = ""


@dataclass
class CashBaseDiagnosticTable:
    """Collection of cash base diagnostic rows."""
    rows: list[CashBaseRow] = field(default_factory=list)
    project_code: str = "OBOROVO"
    period_index: int = 3
    period_label: str = "P4"

    def add(self, row: CashBaseRow) -> None:
        self.rows.append(row)

    def failed_rows(self) -> list[CashBaseRow]:
        return [r for r in self.rows if r.status == DiagnosticStatus.FAIL]

    def upstream_failures(self) -> list[CashBaseRow]:
        return [r for r in self.failed_rows() if r.upstream_of_shl]

    def shl_scope_failures(self) -> list[CashBaseRow]:
        return [r for r in self.failed_rows() if not r.upstream_of_shl]


# ─── Builder ─────────────────────────────────────────────────────────────────

def build_oborovo_p4_cash_base_diagnostic(
    python_production_mwh: float,
    python_revenue_keur: float,
    python_opex_keur: float,
    python_ebitda_keur: float,
    python_cfads_keur: float,
    python_senior_interest_keur: float,
    python_senior_principal_keur: float,
    python_senior_ds_keur: float,
    python_cf_after_senior_keur: float,
    python_shl_sweep_keur: float,
    python_distribution_keur: float,
    python_dscr: float,
    use_partial_pay_sweep: bool = False,
) -> CashBaseDiagnosticTable:
    """Build Oborovo P4 cash base diagnostic comparing Excel anchors vs Python runtime.

    Args:
        use_partial_pay_sweep: If True, use partial_pay_sweep values for SHL metrics.
    """
    table = CashBaseDiagnosticTable()

    def add_row(
        metric: str,
        excel_val: Optional[float],
        python_val: Optional[float],
        tol: float,
        upstream: bool,
        cause: str = "",
        ref: str = "",
        notes: str = "",
    ) -> None:
        if python_val is None or excel_val is None:
            status = DiagnosticStatus.MISSING
            delta = None
        else:
            delta = python_val - excel_val
            status = DiagnosticStatus.PASS if abs(delta) <= tol else DiagnosticStatus.FAIL

        table.add(CashBaseRow(
            metric=metric,
            excel_value=excel_val,
            python_value=python_val,
            delta=delta,
            tolerance=tol,
            status=status,
            upstream_of_shl=upstream,
            likely_cause=cause,
            source_reference=ref,
            notes=notes,
        ))

    # Revenue
    add_row(
        "production_mwh",
        54580.16, python_production_mwh, 0.5,
        upstream=True,
        cause="Production from P50 hourly * availability; matches Excel",
    )
    add_row(
        "operating_revenue_keur",
        3255.16, python_revenue_keur, 1.0,
        upstream=True,
        cause="Waterfall revenue = revenue_schedule (matches Excel gross revenue)",
    )
    add_row(
        "opex_keur",
        -644.34, python_opex_keur, 5.0,
        upstream=True,
        cause="OPEX gap of +32.45 kEUR — investigation required: inflation basis, "
              "period fraction, or line-item aggregation issue",
    )
    add_row(
        "ebitda_keur",
        2610.82, python_ebitda_keur, 5.0,
        upstream=True,
        cause="EBITDA = revenue - OPEX. Delta driven by OPEX gap.",
    )
    add_row(
        "cfads_keur",
        2610.82, python_cfads_keur, 5.0,
        upstream=True,
        cause="CFADS = EBITDA (Python model has no cash tax in this period)",
    )
    add_row(
        "senior_service_keur",
        2270.28, python_senior_ds_keur, 5.0,
        upstream=True,
        cause="Senior DS gap of -212.37 kEUR — root cause likely in senior debt "
              "opening balance, frozen schedule alignment, or interest rate basis. "
              "DSCR = 1.2529 (Python) vs 1.147 (Excel avg). Python avg DSCR=1.15 "
              "matches because it is input-constrained to frozen schedule.",
    )
    add_row(
        "senior_interest_keur",
        None, python_senior_interest_keur, 0.0,
        upstream=True,
        cause="Senior interest = opening_balance * period_rate. "
              "Delta driven by opening balance difference vs Excel.",
    )
    add_row(
        "senior_principal_keur",
        None, python_senior_principal_keur, 0.0,
        upstream=True,
        cause="Principal = fixed_DS - interest. "
              "Excel fixed DS = 2270.28, Python = 2057.91.",
    )
    add_row(
        "dscr",
        1.147, python_dscr, 0.05,
        upstream=True,
        cause="Python avg DSCR = 1.15 (frozen schedule input). "
              "P4 DSCR = 1.2529. Excel avg = 1.147. "
              "Gap is due to individual period DSCR differences, "
              "not average formula. Frozen schedule constrains avg to target.",
    )
    add_row(
        "cash_after_senior_keur",
        340.54, python_cf_after_senior_keur, 5.0,
        upstream=True,
        cause="cash_after_senior = cfads - senior_ds. "
              "Python = 2578.37 - 2057.91 = 520.46. "
              "Excel = 2610.82 - 2270.28 = 340.54. "
              "Gap of 179.92 kEUR driven by OPEX and senior DS deltas.",
    )
    # SHL scope
    shl_sweep = PYTHON_P4_PARTIAL_PAY_SWEEP["shl_sweep_keur"] if use_partial_pay_sweep else python_shl_sweep_keur
    dist = PYTHON_P4_PARTIAL_PAY_SWEEP["distribution_keur"] if use_partial_pay_sweep else python_distribution_keur

    add_row(
        "shl_sweep_keur",
        340.54, shl_sweep, 5.0,
        upstream=False,
        cause="Default: 0 (no sweep trigger). "
              "partial_pay_sweep opt-in: 66.59 kEUR (still below Excel 340.54). "
              "Gap of ~274 kEUR indicates insufficient cash_after_senior. "
              "Root cause is upstream (senior DS too low → cash_after_senior too high "
              "in Python, paradoxically; but absolute CFADS - senior_ds = 520 vs 340 "
              "means Python has more cash for SHL but Excel uses more of it for SHL). "
              "Likely Excel has different SHL sweep routing / priority rules.",
    )
    add_row(
        "distribution_keur",
        0.0, dist, 1.0,
        upstream=False,
        cause="Default: 64.97 kEUR leakage. "
              "partial_pay_sweep opt-in: 0 kEUR (leakage eliminated). "
              "Leakage cause: default SHL method does not block distribution when "
              "SHL balance is alive. partial_pay_sweep fixes this.",
    )
    add_row(
        "cash_for_shl_keur",
        340.54, python_cf_after_senior_keur, 5.0,
        upstream=False,
        cause="cash_for_shl = cash_after_senior. "
              "Python = 520.46, Excel = 340.54. "
              "Excel route: 340.54 goes to SHL sweep (100%). "
              "Python default route: 64.97 to distribution, rest to ??? "
              "partial_pay_sweep: 66.59 to SHL sweep, 0 to distribution. "
              "Remaining gap = insufficient SHL sweep despite more cash — "
              "sweep routing / waterfall priority differs from Excel.",
    )

    return table


def cash_base_summary(table: CashBaseDiagnosticTable) -> dict:
    """Return a summary dict of the cash base diagnostic."""
    failed = table.failed_rows()
    upstream = table.upstream_failures()
    shl_scope = table.shl_scope_failures()
    return {
        "project": table.project_code,
        "period": table.period_label,
        "total_rows": len(table.rows),
        "failed": len(failed),
        "upstream_failures": len(upstream),
        "shl_scope_failures": len(shl_scope),
        "upstream_metrics": [r.metric for r in upstream],
        "shl_scope_metrics": [r.metric for r in shl_scope],
    }
