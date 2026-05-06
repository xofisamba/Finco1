# FincoGPT CLI Usage

## Overview
Command-line interface for running FincoGPT project models. Additive layer — does not replace Streamlit.

## Usage

```bash
# Run Solar Base and save JSON
python -m app.cli run --project Solar --scenario Base --json output.json

# Run Wind Downside and export Excel
python -m app.cli run --project Wind --scenario Downside --output results.xlsx

# Run Solar Base Annual with both outputs
python -m app.cli run --project Solar --scenario Base --period-view Annual --output out.xlsx --json out.json
```

## Options

| Option | Required | Description |
|--------|----------|-------------|
| `--project` | Yes | `Solar` or `Wind` |
| `--scenario` | Yes | `Base`, `Downside`, or `Upside` |
| `--period-view` | No | `Semiannual` (default) or `Annual` |
| `--output` | No | Excel output file path |
| `--json` | No | JSON output file path |

## Architecture
CLI uses the same `run_demo_project()` as Streamlit and FastAPI. No waterfall logic is duplicated.

## Limitations
- Advanced OPEX/CAPEX not yet exposed via CLI
- Excel export via CLI uses default project CAPEX/OPEX
- No authentication