# Release Checkpoint: post-rc1-platform-merge

## Purpose
Checkpoint marking successful merge of platform foundation branches:
- post-rc1-structure-roadmap (stabilization + new features)
- feature/cli-runner (CLI runner layer)
- feature/api-wrapper (FastAPI layer)

## Architecture Summary
Three supported interfaces over shared `run_demo_project()` core:
- **Streamlit** (`streamlit_app.py`) — interactive web UI
- **CLI** (`app/cli/`) — `python -m app.cli run` for JSON/XLSX export
- **FastAPI** (`main_api.py`, `app/api/`) — REST API with /health, /project-types, /scenarios, /run

## Supported Interfaces
| Interface | Entry point | Output formats |
|-----------|-------------|----------------|
| Streamlit | `streamlit_app.py` | Web UI, Excel export |
| CLI | `python -m app.cli run` | JSON, XLSX |
| FastAPI | `uvicorn main_api:app` | JSON |

## Test Status
- Full suite: **1057 passed, 1 xfailed**
- API tests: 16 passed
- CLI tests: 5 passed
- OPEX scenario scaling tests: 8 passed
- FP determinism tests: 4 passed

## Known Limitations
- CAPEX depreciation gap (CapexLineItem matrix doesn't feed per-asset-class depreciation)
- BESS partial (revenue-only, no full cost + hybrid optimization)
- Portfolio experimental (not independently validated)
- rc1 remains frozen

## Roadmap Handoff
Next phase: **Custom Input Schema**
- Define `ProjectInputsSchema` for API/CLI request validation
- Support YAML/JSON project files via CLI `--input` flag
- Phase out hardcoded demo-only flow

Recommended checkpoint name: **post-rc1-platform-merge**

---

# Release Checkpoint: v1.2-custom-input-foundation

## Purpose
Checkpoint marking successful merge of `feature/custom-input-schema` into `main`.
Enables custom project inputs via API `POST /run` (optional `inputs` dict) and CLI `--input JSON`.

## Merged Branch
`feature/custom-input-schema` → `main` (fast-forward, 2026-05-06)

## New Capabilities
- `ProjectInputsSchema` (Pydantic DTO) — minimal input validation for Solar/Wind
- API `POST /run` accepts optional `inputs` dict with project_type mismatch guard
- API `POST /validate` endpoint for input-only validation
- CLI `--input FILE.json` flag for custom inputs
- `examples/custom_solar.json`, `examples/custom_wind.json` as reference inputs

## Test Status
- Full suite: **1099 passed, 1 xfailed**
- API smoke: old Solar Base, custom JSON, mismatch detection — all OK
- CLI smoke: old Solar Base, custom JSON → JSON, custom JSON → XLSX — all OK
- Financial smoke: tariff change correctly propagates to revenue — OK

## Known Limitations (frozen scope)
- YAML input not yet supported
- `project_name` not propagated to project info in outputs
- CAPEX depreciation gap (CapexLineItem → total CAPEX correct; per-asset-class depreciation still uses legacy path)
- BESS/Portfolio custom inputs not supported via API
- CAPEX total must exceed ~10,000 kEUR (fixed other capex)

## Freeze Status
**main:** short stabilization freeze — bugfix/docs/smoke-test fixes only
**Forbidden:** CAPEX depreciation, HTMX, BESS full cost, Portfolio validation, Sponsor IRR, FX

## Recommended Checkpoint Name
**v1.2-custom-input-foundation**