"""Project Library router.

Routes
------
GET  /library                          — full project library page
GET  /library/list                     — HTMX partial: paginated project list
POST /library/clone/{source_project_id} — create working copy, redirect to workbook

Project Library Open / Clone destination is flag-aware. The single
authoritative helper ``workbook_destination(project_code)`` chooses
between the legacy workspace and the Workbook V2 route based on
``FINCO_WORKBOOK_V2``. Truthy values are exactly:

    "1" | "true" | "yes" | "on"

Anything else (including unset, "0", "false", "no", "off", empty)
falls back to the legacy workspace.

This helper is the only place that decides the Open / Clone target.
The same helper is used for:

* Project Library Open link (``GET /library`` and ``GET /library/list``)
* Working-copy clone redirect (``POST /library/clone/{id}``)
* HTMX ``HX-Redirect`` for the clone handler
* Non-HTMX 303 ``Location`` for the clone handler

A Project Library Open link must NEVER point at an unmounted route,
even when the operator sets ``FINCO_WORKBOOK_V2=1`` but the V2
router failed to import. In that pathological case the helper falls
back to the legacy workspace.
"""
from __future__ import annotations

import math
import os
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

router = APIRouter()

PAGE_SIZE = 20

# ---------------------------------------------------------------------------
# Workbook destination helper
# ---------------------------------------------------------------------------

_TRUTHY_VALUES = frozenset({"1", "true", "yes", "on"})


def _is_v2_router_mounted() -> bool:
    """Return True iff the exact ``/v2/workbook`` route is
    mounted on the FastAPI app. A route such as
    ``/v2/capex/line/add`` or ``/v2/opex/line/add`` does NOT
    alone prove that ``/v2/workbook`` is mounted; the probe
    checks the exact path. The probe walks nested
    ``APIRouter`` includes because FastAPI's
    ``include_router`` wraps sub-routers in ``_IncludedRouter``
    entries whose own ``path`` is empty. Best-effort: any
    introspection failure returns False so the helper falls
    back to the legacy workspace.
    """
    try:
        from main_web import app  # local import to avoid cycles
    except Exception:
        return False
    try:
        target = "/v2/workbook"

        def _walk(routes, prefix: str) -> bool:
            for route in routes:
                # FastAPI include_router wraps the sub-router
                # in a _IncludedRouter entry whose own path
                # is empty. The include prefix is held in
                # route.include_context.prefix and the
                # APIRouter itself in
                # route.include_context.included_router.
                ctx = getattr(route, "include_context", None)
                if ctx is not None:
                    sub_prefix = getattr(ctx, "prefix", "") or ""
                    inner = getattr(ctx, "included_router", None)
                    if inner is not None:
                        if _walk(
                            getattr(inner, "routes", []) or [],
                            prefix + sub_prefix,
                        ):
                            return True
                    continue
                # A regular APIRoute: combine prefix with
                # path. Mount entries (static files) are
                # skipped.
                own_path = getattr(route, "path", None)
                if not own_path:
                    continue
                full = prefix + own_path
                if full == target:
                    return True
            return False

        return _walk(app.routes, "")
    except Exception:
        return False


def workbook_v2_enabled() -> bool:
    """Return True iff the operator has explicitly enabled
    Workbook V2 with a canonical truthy value AND the V2 router
    is actually mounted on the app."""
    flag = os.environ.get("FINCO_WORKBOOK_V2", "").strip().lower()
    if flag not in _TRUTHY_VALUES:
        return False
    return _is_v2_router_mounted()


def workbook_destination(project_code: str) -> str:
    """Return the navigation target for opening a project from
    the Project Library. Uses Workbook V2 iff enabled AND mounted;
    otherwise falls back to the legacy workspace.
    """
    code = quote((project_code or "").strip(), safe="")
    if workbook_v2_enabled():
        return f"/v2/workbook?project={code}"
    return f"/?project={code}"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_current_user(request: Request):
    from main_web import get_current_user
    return get_current_user(request)


def _templates():
    from main_web import templates
    return templates


# ---------------------------------------------------------------------------
# GET /library — full page
# ---------------------------------------------------------------------------

@router.get("/library", response_class=HTMLResponse)
async def project_library_page(
    request: Request,
    search: Optional[str] = None,
    role: Optional[str] = None,
    page: int = 1,
    project: Optional[str] = None,
):
    user = _get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    from app.persistence.projects_repository import (
        list_projects_paged,
        get_reference_projects,
    )
    from app.services.project_library_service import ensure_reference_models

    ensure_reference_models()

    page = max(1, page)
    records, total = list_projects_paged(
        user_id=user.user_id,
        page=page,
        page_size=PAGE_SIZE,
        search=search or None,
        role_filter=role or None,
    )
    total_pages = max(1, math.ceil(total / PAGE_SIZE))

    ctx = {
        "user": user,
        "projects": records,
        "search": search or "",
        "role_filter": role or "",
        "page": page,
        "page_size": PAGE_SIZE,
        "total": total,
        "total_pages": total_pages,
        "has_prev": page > 1,
        "has_next": page < total_pages,
        "selected_project": project or "",
        # sidebar context — no active project on the library page
        "project_record": None,
        "project_ctx": None,
        "workspace_state": None,
        "runtime_summary": None,
        "user_project_records": [],
        "factory_template_projects": [],
        "active_project_code": None,
        "workbook_destination_fn": workbook_destination,
        "workbook_v2_enabled_flag": workbook_v2_enabled(),
    }
    return _templates().TemplateResponse(request=request, name="library/project_library.html", context=ctx)


# ---------------------------------------------------------------------------
# GET /library/list — HTMX partial (paginated list only)
# ---------------------------------------------------------------------------

@router.get("/library/list", response_class=HTMLResponse)
async def project_library_list(
    request: Request,
    search: Optional[str] = None,
    role: Optional[str] = None,
    page: int = 1,
    project: Optional[str] = None,
):
    user = _get_current_user(request)
    if not user:
        return JSONResponse({"error": "Login required"}, status_code=401)

    from app.persistence.projects_repository import list_projects_paged

    page = max(1, page)
    records, total = list_projects_paged(
        user_id=user.user_id,
        page=page,
        page_size=PAGE_SIZE,
        search=search or None,
        role_filter=role or None,
    )
    total_pages = max(1, math.ceil(total / PAGE_SIZE))

    ctx = {
        "user": user,
        "projects": records,
        "search": search or "",
        "role_filter": role or "",
        "page": page,
        "page_size": PAGE_SIZE,
        "total": total,
        "total_pages": total_pages,
        "has_prev": page > 1,
        "has_next": page < total_pages,
        "selected_project": project or "",
        "workbook_destination_fn": workbook_destination,
        "workbook_v2_enabled_flag": workbook_v2_enabled(),
    }
    return _templates().TemplateResponse(request=request, name="library/project_library_list.html", context=ctx)


# ---------------------------------------------------------------------------
# POST /library/clone/{source_project_id} — create working copy
# ---------------------------------------------------------------------------

@router.post("/library/clone/{source_project_id}")
async def project_library_clone(
    request: Request,
    source_project_id: str,
    requested_name: Optional[str] = Form(default=None),
):
    user = _get_current_user(request)
    if not user:
        return JSONResponse({"error": "Login required"}, status_code=401)

    from app.services.project_library_service import (
        create_working_copy,
        ProtectedProjectError,
    )

    try:
        new_project = create_working_copy(
            user_id=user.user_id,
            source_reference_id=source_project_id,
            requested_name=requested_name or None,
        )
    except (ValueError, ProtectedProjectError) as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)

    dest = workbook_destination(new_project.project_code)
    is_htmx = request.headers.get("HX-Request") == "true"
    if is_htmx:
        from fastapi.responses import Response
        resp = Response(status_code=204)
        resp.headers["HX-Redirect"] = dest
        return resp
    return RedirectResponse(url=dest, status_code=303)
