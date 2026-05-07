# HTMX Internal Demo

**Date:** 2026-05-07
**Status:** Internal demo — NOT production

---

## How to Run

```bash
cd /path/to/Finco1
python main_web.py
```

**Expected URL:** http://localhost:8765

---

## What Works

- ✅ GET `/` — main input form with sidebar controls
- ✅ POST `/validate` — validates project_type + scenario, numeric field checking
- ✅ POST `/run` — runs model, returns KPI partial (Project IRR, Equity IRR, Min/Avg DSCR, Revenue, EBITDA)
- ✅ POST `/compare` — runs Base/Downside/Upside, returns comparison table with deltas
- ✅ GET/POST `/download` — generates Excel with build_excel_export(), streams xlsx
- ✅ GET `/health` — simple health check
- ✅ HTMX partials (validation.html, kpis.html, comparison.html, errors.html)
- ✅ Professional CSS styling (no npm, no build)
- ✅ Model caveats displayed in UI (TUHO CO2, Oborovo OpEx)
- ✅ Excel includes depreciation disclosure sheets (Tax Depreciation, Book Depreciation, Depreciation Assumptions)

---

## What Does NOT Work

- ❌ Auth/persistence — none (single admin deploy)
- ❌ Public access — internal only
- ✅ Custom inputs wired — ProjectInputsSchema + build_projectinputs() (blank fields → factory defaults)
- ❌ Save/load scenarios — no server-side state
- ❌ Multi-user sessions
- ❌ Real-time collaboration

---

## Internal-Only Caveats

- Model outputs are **screening-grade** — not audited financial advice
- TUHO CO2 revenue missing (611 kEUR Y1) — model understates revenue
- Oborovo OpEx duplication (+660 kEUR Y1) — model overstates OpEx
- No auth — anyone with access to port 8765 can run model

---

## No Auth / No Persistence

- No login, no session cookies, no user accounts
- No database — Excel generated on-demand, not stored
- For production: auth/persistence required before public deployment

---

## Streamlit Fallback Remains

Streamlit (`streamlit_app.py`) remains available for internal model development:

```bash
streamlit run streamlit_app.py --server.port 8501
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Web framework | FastAPI |
| Templates | Jinja2 |
| AJAX | HTMX 1.9 |
| Styling | Vanilla CSS |
| No React | ✅ |
| No npm/Node | ✅ |
| No build system | ✅ |

---

## Contabo Private Deployment

For Contabo VPS (Ubuntu 22.04):

```bash
pip install fastapi uvicorn jinja2
python main_web.py
# Binds to 0.0.0.0:8765
```

Memory footprint: ~100MB vs Streamlit ~500MB+

**Not for public access until auth is added.**

---

## Related Docs

- `docs/htmx_foundation_scope.md` — production HTMX scope definition
- `docs/release_checkpoint.md` — v1.4.1 advisory-ready status
- `docs/main_post_merge_status.md` — model status overview