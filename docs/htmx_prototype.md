# HTMX Prototype

## How to Run
```bash
cd /root/.openclaw/workspace/finco1_new
python3 main_web.py
# Access: http://localhost:8765
```

## What Works
- Project type + scenario selection
- Custom inputs (tariff, CAPEX, OPEX, gearing)
- KPI calculation via HTMX (no full page reload)
- Results displayed in card grid
- Error handling visible in form

## What Is Prototype-Only
- No authentication
- No persistence (every reload loses state)
- No Excel export
- No full CAPEX/OPEX matrix
- No scenario comparison
- No deployment (Contabo VPS) — local only

## What Is Deferred
- Auth / multi-tenancy
- Database persistence
- Full CAPEX/OPEX matrix editor
- Advanced scenario comparison
- Excel export integration
- Deployment on Contabo VPS with Nginx

## File Structure
```
main_web.py           — FastAPI + HTMX entry point
app/web/router.py     — Web routing module
app/templates/        — Jinja2 HTML templates
static/styles.css     — Minimal CSS
tests/test_web_prototype.py — Web tests
```
