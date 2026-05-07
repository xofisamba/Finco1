# HTMX Production Plan

**Status:** Preparation only — do NOT implement production HTMX yet.

## Pre-Production Prerequisites

1. ✅ Excel depreciation disclosure sheets (this sprint)
2. ✅ Auth system (FastAPI + JWT/session)
3. ✅ Persistence layer (project save/load)
4. ⬜ Contabo deployment target confirmed

---

## Architecture

### Stack
- **Backend:** FastAPI + HTMX + Jinja2
- **Frontend:** TailwindCSS + vanilla JS
- **Web Server:** Nginx (reverse proxy + static files)
- **Deployment:** Contabo VPS (Ubuntu 22.04)

### Auth Requirement
- Session-based or JWT authentication
- No public anonymous access to financial data
- Role-based: viewer vs editor

### Persistence Requirement
- Projects saved to filesystem/DB with unique IDs
- Version history / audit trail
- Excel import/export for project data

---

## Features Planned

| Feature | Priority | Notes |
|---------|----------|-------|
| Project CRUD | P0 | Create, read, update, delete projects |
| Scenario comparison | P1 | Side-by-side Base/Downside/Upside |
| CAPEX/OPEX matrix | P1 | Editable line-item tables |
| Excel export button | P0 | Already works via Excel export |
| Scenario manager | P1 | Apply scenario overrides |

---

## Why Streamlit Remains Internal Fallback

- Streamlit requires Python runtime on client
- No auth out of the box
- Not designed for multi-user persistence
- Good for rapid prototyping, not production
- Keep Streamlit on internal ports (8501-8503, 8508) for internal use

---

## Security Caveats

- All financial data visible to authenticated users only
- Input validation on all user-supplied values
- Rate limiting on API endpoints
- Audit log for all project modifications
- No PII stored in project names
