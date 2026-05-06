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