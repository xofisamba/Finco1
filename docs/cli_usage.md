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
| `--input` | No | Custom project JSON file (optional) |

## Architecture
CLI uses the same `run_demo_project()` as Streamlit and FastAPI. No waterfall logic is duplicated.

## Custom Input Mode

### Supported formats
- JSON only (YAML future)

### Request structure
- `project_type` / `scenario` in outer request/CLI flags are **source of truth**
- `inputs.project_type` / `inputs.scenario` in JSON must **match** outer values
- Mismatch returns 400 error

### CAPEX override constraint
- `total_capex_keur` must be greater than the other capex items (~10,000 kEUR for Solar)
- If too low, returns clear error: `total_capex_keur (X) must be greater than other capex items (Y keur)`

### Example
```bash
python -m app.cli run --project Solar --scenario Base --input custom.json
```

```json
// custom.json
{
  "project_type": "Solar",
  "scenario": "Base",
  "capacity_mw": 75,
  "revenue": {"tariff_eur_mwh": 72},
  "capex": {"total_capex_keur": 45000}
}
```

## Limitations
- Advanced OPEX/CAPEX not yet exposed via CLI
- Excel export via CLI uses default project CAPEX/OPEX
- No authentication