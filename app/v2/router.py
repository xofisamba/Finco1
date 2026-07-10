"""
app.v2.router — Workbook V2 feature-flagged routes.

Mounted at ``/v2`` in main_web.py when ``FINCO_WORKBOOK_V2`` is truthy.
All routes require the same authentication as the legacy stack.

Current routes
--------------
GET /v2/workbook
    Single-sheet workbook shell.  Accepts the same ``?project=`` query
    parameter as the legacy ``GET /``.  Returns a minimal HTML page built
    from the V2 template skeleton.  Schedule data is hydrated via the
    RuntimeResult sessionStorage script so the page loads without a model
    re-run.

Scope constraints
-----------------
- No engine calls, no formula logic, no parity changes.
- No DB writes; reads WorkspaceStateRecord via the existing repository
  layer only.
- No sheet migration (PR 6).
- No legacy ``_collect_form_snapshot`` / ``_strip_empty_fields`` helpers.
"""
from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.workbook.service import WorkbookService

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "app", "templates", "v2"))


def _get_current_user(request: Request):
    """Return the authenticated user from session, or None."""
    return getattr(request.state, "user", None) or request.session.get("user")


@router.get("/workbook", response_class=HTMLResponse)
async def v2_workbook(request: Request, project: Optional[str] = None):
    """Workbook V2 shell page.

    Renders the V2 template skeleton and injects a sessionStorage hydration
    script from the persisted RuntimeResult (if one exists), so schedule
    data is available to the page on load without a model re-run.

    Query parameters
    ----------------
    project : str, optional
        Project code (e.g. ``tuho``, ``oborovo``).  When absent, redirects
        to the project home.
    """
    user = _get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    if not project:
        return RedirectResponse(url="/", status_code=302)

    # Resolve workspace state via the existing repository layer.
    # Import here (TYPE_CHECKING-safe) to avoid circular imports at module load.
    from app.persistence.repository import get_workspace_state

    ws = await get_workspace_state(user_id=user["id"], project_code=project)
    if ws is None:
        return RedirectResponse(url="/", status_code=302)

    # Build the draft input set — UI display path, not a run boundary.
    pis = WorkbookService.build_draft_input_set_from_workspace(ws)

    # Build the sessionStorage hydration script from persisted RuntimeResult.
    hydration_script = WorkbookService.runtime_hydration_script(ws)

    context = {
        "request": request,
        "project_code": project,
        "workbook_version": pis.workbook_version,
        "content_hash": pis.content_hash,
        "template_source": pis.template_source,
        "hydration_script": hydration_script,
        "user": user,
    }
    return _templates.TemplateResponse("workbook.html", context)
