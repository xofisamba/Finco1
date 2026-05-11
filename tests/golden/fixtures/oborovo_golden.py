"""Oborovo solar reference scenario golden validation fixtures.

Fixture name: oborovo
Technology: Solar, 53.63 MWp
Source: tests/fixtures/tuho_wind1_golden.json (anchor) + tests/fixtures/excel_golden_oborovo.json
Model: semiannual periods, ~30 years
Schema version: 1.0
"""
from __future__ import annotations

# Oborovo scalar golden values with tolerances
OBOROVO_SCALARS: dict[str, dict] = {
    "total_capex_keur": {
        "value": 57973.05,
        "tolerance": {"type": "pct", "value": 0.005},
        "description": "Total CAPEX including contingency",
        "unit": "kEUR",
    },
    "senior_debt_keur": {
        "value": 42852.27,
        "tolerance": {"type": "pct", "value": 0.005},
        "description": "Senior debt at financial close",
        "unit": "kEUR",
    },
    "project_irr_30y": {
        "value": 0.0828,
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
        "value": 1.147,
        "tolerance": {"type": "abs", "value": 0.002},
        "description": "Average semi-annual DSCR over model life",
        "unit": "ratio",
    },
}

# Oborovo period-series golden values with per-period tolerances
OBOROVO_SERIES: dict[str, dict] = {
    "senior_debt_service_p1_keur": {
        "values": (-2239.133, -2202.626, -2240.525),
        "per_period_tolerance": {"type": "pct", "value": 0.005},
        "description": "First 3 semiannual senior debt service payments (principal + interest)",
        "unit": "kEUR",
        "sign_convention": "negative = cash outflow",
        "period_count": 3,
    },
}

OBOROVO_METADATA = {
    "fixture_name": "oborovo",
    "technology": "solar",
    "source_workbook": "20260414_BP_Oborovo_Sensitivity_FINAL for PPT.xlsm",
    "extraction_date": "2026-04-14",
    "model_period": "semiannual",
    "period_count": 60,
    "schema_version": "1.0",
    "notes": [
        "Golden values extracted from excel_golden_oborovo.json anchors.",
        "Period-series fixtures (debt service) are initial 3-period spot checks.",
        "Full period-series fixtures to be added after complete sheet mapping.",
    ],
}

OBOROVO_GOLDEN = {
    "_comment": "Oborovo solar reference scenario golden fixture — read-only",
    "metadata": OBOROVO_METADATA,
    "scalars": OBOROVO_SCALARS,
    "series": OBOROVO_SERIES,
}