# FincoGPT — Project Finance Screening Tool

**FincoGPT** is a fast project-finance screening model for solar and wind energy assets. It computes Project IRR, Equity IRR, DSCR, and full waterfall schedules in seconds, and exports results to Excel.

> ⚠️ **This is a screening model, not a full bank model.** Use it for the first-pass question: _"Is this project worth spending more time on?"_

---

## What is this?

FincoGPT is an investor-grade screening tool for renewable energy project finance. It models:

- **Revenue** — PPA tariff with escalation + optional merchant post-PPA exposure + CO2 certificates
- **Debt sizing** — DSCR-sculpted senior debt + optional SHL (subordinated hybrid loan)
- **Cash flow waterfall** — CFADS → debt service → DSRA → distributions
- **Returns** — Project IRR, Equity IRR, Sponsor IRR, NPV
- **Tax** — CIT with LCF, ATAD EBITDA limitation, withholding taxes
- **Scenarios** — Base / Downside / Upside applied automatically

### Supported project types
| Type | Status |
|------|--------|
| Solar | ✅ Full model |
| Wind | ✅ Full model |
| BESS | ⚠️ Revenue-only (waterfall in progress) |
| Solar+BESS | ⚠️ Revenue-only (waterfall in progress) |
| Wind+BESS | ⚠️ Revenue-only (waterfall in progress) |
| Portfolio | 🧪 Experimental |

---

## What this is NOT

- **Not a bank model** — FincoGPT does not replace a full due diligence process
- **Not a construction model** — simplified construction schedule; no granular delay-risk modelling
- **Not a legal model** — PPA enforceability, offtaker credit, and counterparty risk are not modelled
- **Not a grid study** — grid connection capacity is assumed, not verified
- **Not tax advice** — consult a tax adviser for complex structures (ATAD, hybrid instruments, treaty networks)

---

## Quick Start

```bash
# Install dependencies
pip install -e .

# Run the Streamlit UI
streamlit run streamlit_app.py
```

Navigate to `http://localhost:8501`, select a project type, choose a scenario, and click **Run Model**.

---

## Example Output

```
Project: Solar Utility Example (55 MWp, Spain)
Project IRR: 11.2%  |  Equity IRR: 14.8%
Min DSCR: 1.31x     |  Avg DSCR: 1.52x
Senior Debt: EUR 31.5M  |  Tenor: 15 years
Tariff: EUR 65/MWh     |  PPA Term: 15 years
```

Scenarios automatically adjust yield, CapEx, OpEx, degradation, and tariff.

---

## Project Structure

```
finco1_new/
├── streamlit_app.py        # UI entrypoint
├── app/
│   ├── ui_runner.py       # Project factory & run orchestrator
│   ├── excel_export.py    # Excel workbook export (values-only)
│   ├── demo_presets.py    # Investor-ready Solar/Wind presets
│   ├── output_tables.py   # Bridge: engine results → DataFrames
│   └── scenarios.py       # Base/Downside/Upside scenario engine
├── domain/
│   ├── waterfall/         # Core waterfall engine
│   ├── debt/              # Debt sizing and service
│   ├── returns/           # XIRR / XNPV calculations
│   ├── tax/               # CIT, ATAD, WHT
│   └── presets.py         # Project presets (Oborovo, TUHO)
└── docs/
    └── demo_script.md     # Investor demo walkthrough
```

---

## Demo Presets

Two investor-ready presets are available via `app.demo_presets`:

```python
from app.demo_presets import get_demo_presets

presets = get_demo_presets()
solar = presets["Solar_Utility_Example"]   # 55 MWp, EUR 45M capex
wind  = presets["Wind_Onshore_Example"]    # 72 MW, EUR 85M capex
```

Both are calibrated to produce:
- **Project IRR**: 8–15%
- **Min DSCR**: > 1.2x

## Limitations

1. **Construction** — simplified schedule, not a full delay-risk model
2. **Revenue** — PPA assumed fully contracted; merchant uses a simple price curve
3. **DSCR sculpting** — fixed-repayment structures need separate verification
4. **Tax** — complex structures (ATAD+, hybrid instruments) require manual review
5. **Portfolio** — experimental; sponsor IRR is a placeholder until aggregation is complete
6. **BESS/hybrid** — revenue-only shown; full waterfall integration is in progress

---

## Documentation

- [Demo Smoke Test Checklist](docs/demo_smoke_test_checklist.md) — pre-demo verification steps
- [Release 1 Readiness](docs/release1_readiness.md) — what's in scope and what's not
- [Demo Script](docs/demo_script.md) — investor walkthrough and talking points
- [Phase 3 Roadmap](docs/phase3_roadmap.md) — what's next after Release 1
- [Test Hygiene Report](docs/test_hygiene_report.md) — test quality audit
- [Legacy Cleanup Inventory](docs/legacy_cleanup_inventory.md) — planned cleanup

## Validation & Enterprise Roadmap

- [Validation Framework](app/validation_framework.py) — run cases, compare results, generate reports
- [Phase 3 Roadmap](docs/phase3_roadmap.md) — Sponsor IRR, Portfolio hardening, BESS, deployment
- [Validation Reconciliation Template](docs/validation_reconciliation_template.md) — compare model vs reference
- [Enterprise Data Model](docs/enterprise_data_model.md) — Project, Run, Result, Assumptions schema
- [Excel Versioning Design](docs/excel_versioning_design.md) — file naming, metadata, reproducibility
- [Demo Smoke Test Checklist](docs/demo_smoke_test_checklist.md) — pre-demo verification
# Phase 10 human-readable calibration workbook
