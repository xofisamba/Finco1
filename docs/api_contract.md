# FincoGPT API Contract

## Purpose
Thin FastAPI wrapper around the FincoGPT model runner. Additive layer — Streamlit remains the primary demo UI.

```
┌──────────────┐     ┌─────────────────────────────────────────────────────┐
│  HTTP Client │────▶│ FastAPI  /api/v1/*                                  │
└──────────────┘     │                                                     │
                      │  POST /run  →  run_project()                        │
                      │                    ├── run_demo_project()          │
                      │                    └── waterfall_core / tables      │
                      │                                                     │
                      │  GET /project-types, /scenarios  (static lists)   │
                      └─────────────────────────────────────────────────────┘
                                                │
                                    Streamlit stays as-is (separate)
```

## Status
**Experimental / proof-of-concept. Not for production use.**

What "not for production" means:
- No authentication or authorization
- No request rate limiting
- No persistence (no database, no saved state)
- No Excel export endpoint
- In-memory waterfall result computed fresh per request
- No SLAs; subject to change or removal without notice

## Running locally
```bash
cd /root/.openclaw/workspace/finco1_new
uvicorn main_api:app --reload --port 8000
```

## Endpoints

### GET /health
Health check. No authentication required.

**Example response:**
```json
{"status": "ok", "service": "fincogpt-api"}
```

---

### GET /api/v1/project-types
Returns the list of supported project types.

**Example curl:**
```bash
curl http://localhost:8000/api/v1/project-types
```

**Example response:**
```json
{
  "project_types": ["Solar", "Wind", "BESS", "Solar+BESS", "Wind+BESS", "Portfolio"]
}
```

---

### GET /api/v1/scenarios
Returns the list of supported economic scenarios.

**Example curl:**
```bash
curl http://localhost:8000/api/v1/scenarios
```

**Example response:**
```json
{
  "scenarios": ["Base", "Downside", "Upside"]
}
```

---

### POST /api/v1/run
Run a project model and return KPIs + tabulated results.

**Example curl:**
```bash
curl -X POST http://localhost:8000/api/v1/run \
  -H "Content-Type: application/json" \
  -d '{"project_type": "Solar", "scenario": "Base", "period_view": "Semiannual"}'
```

**Request body:**
```json
{
  "project_type": "Solar",   # required; one of project-types list
  "scenario": "Base",         # required; one of scenarios list
  "period_view": "Semiannual", # optional; "Semiannual" (default) or "Annual"
  "inputs": {                 # optional; custom project JSON
    "project_type": "Solar", # must match outer project_type
    "scenario": "Base",       # must match outer scenario
    "capacity_mw": 75,
    "revenue": {"tariff_eur_mwh": 72},
    "capex": {"total_capex_keur": 45000}
  }
}
```

**`inputs` field rules:**
- `project_type` / `scenario` in `inputs` JSON must match the outer request fields
- Mismatch returns `400` with descriptive message
- `scenario` is optional in `inputs` (defaults to `Base` if omitted)
- `total_capex_keur` must be greater than the fixed other capex items (~10,000 kEUR for Solar)
  - Too-low values return `400` error: `"total_capex_keur (X) must be greater than other capex items (Y keur)"`

**Example response (Solar Base):**
```json
{
  "project_type": "Solar",
  "scenario": "Base",
  "period_view": "Semiannual",
  "integration_status": "full",
  "messages": [],
  "kpis": {
    "total_revenue_keur": 119531.69,
    "total_ebitda_keur": 107361.21,
    "project_irr": 0.1040,
    "equity_irr": 0.1358,
    "min_dscr": 1.442,
    "avg_dscr": 1.650
  },
  "tables": {
    "waterfall": [
      {"P1": 8939.56, "P2": 9032.31, ...},
      {"P1": 2149.46, "P2": 2171.63, ...},
      ...
    ],
    "revenue": [...],
    "debt": [...],
    "returns": [...]
  }
}
```

**KPIs reference:**

| Field | Description |
|---|---|
| `total_revenue_keur` | Lifetime revenue in kEUR |
| `total_ebitda_keur` | Lifetime EBITDA in kEUR |
| `project_irr` | Project IRR (unlevered) as decimal |
| `equity_irr` | Equity IRR (levered) as decimal |
| `min_dscr` | Minimum debt service coverage ratio achieved |
| `avg_dscr` | Average DSCR across all debt periods |

**Error responses:**

| Status | Condition | Example detail |
|---|---|---|
| `400` | Unsupported `project_type`, `scenario`, or `period_view` | `"Unsupported project_type: Foo"` |
| `400` | `inputs.project_type` / `inputs.scenario` mismatch | `"inputs.project_type 'Wind' does not match request.project_type 'Solar'"` |
| `400` | `total_capex_keur` too low (≤ other capex items) | `"total_capex_keur (100) must be greater than other capex items (10000 keur)"` |
| `501` | BESS, Solar+BESS, Wind+BESS, or Portfolio (not yet supported) | `"BESS not yet supported via API"` |
| `500` | Internal error (model computation failed) | `"..."` |

---

## Limitations

| Limitation | Note |
|---|---|
| BESS / Hybrid / Portfolio | Return `501` — waterfall integration in progress |
| Auth | None — any client can call any endpoint |
| Rate limiting | None — abuse possible |
| Persistence | None — each request is stateless |
| Excel export | Not available via API |
| Custom project inputs | Supported via JSON body (`inputs` field); YAML planned |

---

## Design Note
Streamlit is the primary demo/internal UI. The FastAPI layer is additive and does not replace Streamlit. Both can run simultaneously.
