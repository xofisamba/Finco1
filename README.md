# FincoGPT - Project Finance Screening Tool

**FincoGPT** is an internal project-finance screening tool for renewable energy review. It computes Project IRR, Equity IRR, DSCR, waterfall outputs, and Excel exports for controlled pilot use.

> Warning: This is an internal screening tool, not a full bank model. Use it for first-pass review and follow-up finance analysis, not as investment advice.

---

## What is this?

FincoGPT is a single-user internal pilot for renewable energy project finance review. It models:

- **Revenue** - PPA tariff with escalation, optional merchant post-PPA exposure, and project-specific CO2 handling where explicitly wired
- **Debt sizing** - DSCR-sculpted senior debt with optional SHL support on the documented frozen-template path
- **Cash flow waterfall** - CFADS -> debt service -> DSRA -> distributions
- **Returns** - Project IRR, Equity IRR, Sponsor IRR, NPV
- **Tax** - CIT with LCF, ATAD EBITDA limitation, withholding taxes
- **Scenarios** - saved scenario workflow with backend-authoritative runs

## Scope boundaries

- **TUHO and Oborovo** are frozen-template parity references with documented Excel evidence.
- **Generic Solar/Wind** remain exploratory until separately validated.
- **BESS / Hybrid / Portfolio** are not production-ready and must not be presented as external-ready workflows.
- **Current deployment mode** is single-user / internal pilot, not enterprise SaaS.
- **Outputs require finance review** and are not investment advice.

### Supported project types

| Type | Status |
|------|--------|
| TUHO / Oborovo frozen-template references | Frozen-template parity evidence |
| Generic Solar | Exploratory screening path |
| Generic Wind | Exploratory screening path |
| BESS | Revenue-only path; broader model path not production-ready |
| Solar+BESS | Revenue-only path; broader model path not production-ready |
| Wind+BESS | Revenue-only path; broader model path not production-ready |
| Portfolio | Experimental reference path |

---

## What this is NOT

- **Not a bank model** - FincoGPT does not replace due diligence, credit, or lender review
- **Not an enterprise SaaS product** - no multi-tenant isolation, RBAC, or external-readiness claim
- **Not a construction model** - simplified construction schedule; no granular delay-risk modelling
- **Not a legal model** - PPA enforceability, offtaker credit, and counterparty risk are not modelled
- **Not a grid study** - grid connection capacity is assumed, not verified
- **Not tax advice** - consult a tax adviser for complex structures (ATAD, hybrid instruments, treaty networks)
- **Not investment advice** - outputs support internal screening and still require finance review

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the current web app locally
uvicorn main_web:app --reload
```

For a production-style process manager, the deployed service runs:

```bash
gunicorn main_web:app
```

Navigate to `http://localhost:8000`, sign in, select a project, save a scenario, and click **Run Model**.

## Legacy Streamlit Note

FincoGPT production is no longer a Streamlit app. Any retained Streamlit files are legacy or archive-only and are not required for the current FastAPI/HTMX runtime.

---

## Example Output

```text
Project: Solar Utility Example (55 MWp, Spain)
Project IRR: 11.2%  |  Equity IRR: 14.8%
Min DSCR: 1.31x     |  Avg DSCR: 1.52x
Senior Debt: EUR 31.5M  |  Tenor: 15 years
Tariff: EUR 65/MWh     |  PPA Term: 15 years
```

Scenarios automatically adjust yield, CapEx, OpEx, degradation, and tariff.

---

## Project Structure

```text
finco1_new/
|-- main_web.py             # Current FastAPI / HTMX entrypoint
|-- streamlit_app.py        # Legacy Streamlit shell retained for archive/reference only
|-- app/
|   |-- ui_runner.py        # Project factory and run orchestrator
|   |-- excel_export.py     # Excel workbook export (values-only)
|   |-- demo_presets.py     # Internal Solar/Wind screening presets
|   |-- output_tables.py    # Bridge: engine results -> DataFrames
|   `-- scenarios.py        # Base/Downside/Upside scenario engine
|-- domain/
|   |-- waterfall/          # Core waterfall engine
|   |-- debt/               # Debt sizing and service
|   |-- returns/            # XIRR / XNPV calculations
|   |-- tax/                # CIT, ATAD, WHT
|   `-- presets.py          # Project presets (Oborovo, TUHO)
`-- docs/
    `-- demo_script.md      # Internal demo walkthrough
```

---

## Demo Presets

Two internal reference presets are available via `app.demo_presets`:

```python
from app.demo_presets import get_demo_presets

presets = get_demo_presets()
solar = presets["Solar_Utility_Example"]   # 55 MWp, EUR 45M capex
wind = presets["Wind_Onshore_Example"]     # 72 MW, EUR 85M capex
```

These presets are useful for internal screening demonstrations. They are not a claim of generic Solar/Wind external validation.

## Limitations

- TUHO and Oborovo are the only frozen-template parity references in current trusted pilot scope.
- Generic Solar/Wind remain exploratory and unvalidated until separately reviewed.
- BESS / Hybrid / Portfolio remain limited-scope paths and are not production-ready.
- All outputs require finance review before any external reliance.
