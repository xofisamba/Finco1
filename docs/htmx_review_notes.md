# HTMX Prototype — Review Notes

## DO NOT MERGE

This branch is for prototype review only. No merge into main.

---

## Architecture Strengths

1. **Lightweight** — FastAPI + vanilla HTMX, no Streamlit dependency
2. **Uses existing API** — `run_project()` from `app.api.project_runner` is the compute engine
3. **Partial updates work** — HTMX swap on `/validate` endpoint, no full page reload
4. **Minimal code** — `main_web.py` is 80 lines, templates are simple Jinja2

---

## What Must NOT Be Merged Yet

| Item | Reason |
|------|--------|
| No authentication | Exposes financial KPIs without auth |
| No persistence | Every reload loses project state |
| No Excel export | Must be added with proper validation |
| No CAPEX/OPEX matrix | UI is basic form only |
| Single-project view | No scenario comparison |
| Local-only deployment | No Nginx/production config |

---

## Production Path (When Ready)

1. Add authentication (JWT/session)
2. Add DB persistence (project save/load)
3. Add Excel export via `build_excel_export()`
4. Expand form with CAPEX/OPEX matrix
5. Add scenario comparison tab
6. Deploy with Nginx + Gunicorn on Contabo VPS

---

## Test Results

```
pytest tests/test_web_prototype.py: 4 passed ✅
```

### Smoke Test
```bash
python3 main_web.py  # runs on port 8765
curl -X POST http://localhost:8765/validate -d "project_type=Solar&scenario=Base"
```

---

## Recommendation

**Hold — prototype only.** Ready for internal demo use. Not suitable for B2B pilot until auth + persistence are added.
