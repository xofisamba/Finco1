"""TUHO wind reference scenario golden validation fixtures.

Fixture name: tuho
Technology: Wind, 72 MW
Source: tests/fixtures/tuho_wind1_golden.json (metadata + outputs sections)
Model: semiannual periods, ~30 years
Schema version: 1.0
"""
from __future__ import annotations

# TUHO scalar golden values with tolerances
TUHO_SCALARS: dict[str, dict] = {
    "total_capex_keur": {
        "value": 72993.71,
        "tolerance": {"type": "pct", "value": 0.005},
        "description": "Total CAPEX including contingency",
        "unit": "kEUR",
    },
    "total_debt_keur": {
        "value": 43359.27,
        "tolerance": {"type": "pct", "value": 0.005},
        "description": "Senior debt at financial close",
        "unit": "kEUR",
    },
    "revenue_y1_keur": {
        "value": 8189.29,
        "tolerance": {"type": "pct", "value": 0.005},
        "description": "Year 1 revenue (first 2 semiannual periods)",
        "unit": "kEUR",
    },
    "project_irr_30y": {
        "value": 0.0947,
        "tolerance": {"type": "bps", "value": 10},
        "description": "Unlevered project IRR over 30-year model period",
        "unit": "fraction",
    },
    "equity_irr_30y": {
        "value": 0.1161,
        "tolerance": {"type": "bps", "value": 10},
        "description": "Equity IRR over 30-year model period",
        "unit": "fraction",
    },
    "avg_dscr": {
        "value": 1.3713,
        "tolerance": {"type": "abs", "value": 0.002},
        "description": "Average semi-annual DSCR over model life",
        "unit": "ratio",
    },
    "project_npv_30y_keur": {
        "value": None,  # TBD — requires discount rate
        "tolerance": {"type": "pct", "value": 0.02},
        "description": "Project NPV over 30 years (requires discount rate; placeholder)",
        "unit": "kEUR",
    },
}

# TUHO period-series golden values with per-period tolerances
# Full period series not yet committed — stub for future use
TUHO_SERIES: dict[str, dict] = {
    "revenue_schedule_keur": {
        "values": tuple(),  # TBD — requires full model extract
        "per_period_tolerance": {"type": "pct", "value": 0.005},
        "description": "Revenue per semiannual period — placeholder (not yet extracted)",
        "unit": "kEUR",
        "period_count": 0,
    },
}

TUHO_METADATA = {
    "fixture_name": "tuho",
    "technology": "wind",
    "source_workbook": "20260330_TUHO_BP.xlsm",
    "extraction_date": "2026-03-30",
    "model_period": "semiannual",
    "period_count": 60,
    "schema_version": "1.0",
    "notes": [
        "Golden values extracted from tests/fixtures/tuho_wind1_golden.json.",
        "Period-series fixtures are stubs — full extraction TBD.",
        "project_npv_30y_keur is a placeholder; actual NPV requires discount rate input.",
    ],
}

TUHO_GOLDEN = {
    "_comment": "TUHO wind reference scenario golden fixture — read-only",
    "metadata": TUHO_METADATA,
    "scalars": TUHO_SCALARS,
    "series": TUHO_SERIES,
}