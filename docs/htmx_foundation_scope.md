# HTMX Production Foundation Scope

**Date:** 2026-05-07
**Status:** DO NOT IMPLEMENT — documentation only for Phase 4 prep
**Target:** Contabo VPS deployment

---

## Context

Streamlit remains the internal admin tool.
HTMX is the planned production UI for external/investor-facing use.
This document defines the scope for the first production HTMX milestone.

**Do not implement HTMX yet** — this document is for planning and review only.

---

## Why HTMX (not Streamlit for production)

| Factor | Streamlit | HTMX |
|--------|-----------|------|
| User target | Internal admin | External/investor |
| Page reloads | Full reload | Partial swap |
| State management | Python server session | Stateless per request |
| Auth complexity | Built-in (but heavy) | Manual session-based |
| Deployment | `streamlit run` | FastAPI + HTMX |
| Investor UX | Too "developer" | Clean, minimal |
| Contabo suitability | Heavy (Python, cache, ports) | Light (FastAPI, single port) |

---

## First Production HTMX Milestone

**Goal:** Investor-facing project screening tool (read-only Excel export + scenario comparison)

**Not in scope for v1:**
- Auth (Phase 5)
- Persistent storage (Phase 5)
- Multi-user sessions
- Write operations
- Real-time collaboration

---

## Required Endpoints

### 1. `GET /validate`

Validate project inputs without running full model.

```
Query params:
  project_type: Solar | Wind
  scenario: Base | Stress | Custom
  country: HR | BA

Response (JSON):
{
  "valid": true/false,
  "errors": ["field: error message"],
  "warnings": ["field: warning"],
  "capex_summary_keur": 45000,
  "depr_profile": "solar_croatia_ibl"
}
```

### 2. `POST /run`

Run model with provided inputs. Returns summary JSON (not Excel yet).

```
Body (JSON):
{
  "project_type": "Solar",
  "scenario": "Base",
  "country": "HR",
  "horizon_years": 25,
  "cod_date": "2029-12-30"
}

Response (JSON):
{
  "status": "success",
  "equity_irr": 0.1161,
  "project_irr": 0.0947,
  "debt_keur": 43359,
  "avg_dscr": 1.451,
  "total_distributions_keur": 118314,
  "warnings": []
}
```

### 3. `GET /download`

Generate and download Excel export.

```
Query params:
  project_type: Solar | Wind
  scenario: Base | Stress
  include_advanced_capex: true | false

Response: 
  Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
  Content-Disposition: attachment; filename="Finco1_Solar_Base_<timestamp>.xlsx"
```

### 4. `GET /compare`

Compare two scenarios side-by-side.

```
Query params:
  scenario_a: Base
  scenario_b: Stress

Response (JSON):
{
  "equity_irr_a": 0.1161,
  "equity_irr_b": 0.0987,
  "dscr_a": 1.451,
  "dscr_b": 1.287,
  "delta_irr": -0.0174,
  "delta_dscr": -0.164
}
```

---

## Excel Export Workflow (HTMX)

```
User: clicks "Run Model"
  → POST /run → returns JSON summary
  → HTMX: swaps summary section with results

User: clicks "Download Excel"
  → GET /download → returns xlsx
  → Browser: triggers download
```

No server-side file storage needed — Excel generated on-demand, streamed to client.

---

## Scenario Comparison Workflow

```
User: selects scenario A (Base) and scenario B (Stress)
  → GET /compare?scenario_a=Base&scenario_b=Stress
  → HTMX: replaces comparison panel with delta table
```

---

## Save/Load Architecture

**Phase 1 (this milestone):** No persistent save/load.
- User downloads Excel as their record
- No server-side state

**Phase 5:** If needed later:
- PostgreSQL for user accounts + saved scenarios
- Redis for session state
- S3 for uploaded files

---

## Contabo Deployment Target

**VM:** Contabo VPS (Ubuntu 22.04, 4 vCPU, 8GB RAM)

**Stack:**
```
FastAPI (uvicorn)
HTMX (jinja2 templates)
No database (Phase 1)
No auth (Phase 1)
```

**Ports:** 8000 (FastAPI) — no Streamlit, no Streamlit cache

**Deployment:** Docker-based
- `Dockerfile` for FastAPI app
- `docker-compose.yml` for local dev
- GitHub Actions for CI/CD to Contabo

**Memory footprint:** FastAPI + HTMX ~100MB vs Streamlit ~500MB+

---

## Auth/Persistence Requirements

**Phase 5 (future, not this milestone):**

| Requirement | Implementation |
|------------|---------------|
| User auth | Session cookies + bcrypt hashed passwords |
| Scenario storage | PostgreSQL (per user) |
| File storage | S3 or local filesystem |
| Session management | Redis |
| Rate limiting | Middleware |

**For now:** Single admin deploy, no auth.

---

## Streamlit — Internal Admin Tool

Streamlit remains for:
- Internal model development and testing
- Rapid iteration on model logic
- Debugging with `st.write()` / `st.dataframe()`
- Local dev only (ports 8501-8503, 8508)

It is NOT production-ready for investor use because:
- Heavy memory footprint
- Complex caching layer (potential collision)
- Not designed for external access
- "Developer tool" UX

---

## What This Document Does NOT Cover

- Specific Jinja2 templates
- CSS/styling decisions
- Specific FastAPI route implementations
- Database schema (Phase 5)
- CI/CD pipeline details
- Monitoring/alerting

These will be defined when Phase 4 implementation begins.

---

## Next Steps

1. Review this document with stakeholders ✅ (this session)
2. Confirm scope for first HTMX milestone
3. Begin Phase 4 implementation (auth + persistence first — needed before HTMX)
4. Or: proceed directly to HTMX if auth/persistence deferred

---

## Related Documents

- `docs/main_post_merge_status.md` — current model status
- `docs/htmx_production_plan.md` — broader HTMX roadmap
- `docs/release_checkpoint.md` — v1.4.1 advisory-ready
