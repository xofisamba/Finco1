import json
"""HTMX internal demo web interface for Finco1 model."""
import os
from fastapi import FastAPI, Request, Form, Response, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Optional

# Import existing model logic (no changes to these)
from app.api.project_runner import run_project
from app.excel_export import build_excel_export
from app.ui_runner import run_demo_project
from app.capex_engine import build_capex_line_items_from_defaults

# Import schema and adapter for custom inputs
from app.input_schema import ProjectInputsSchema, RevenueInput, CapexInput, OpexInput, DebtInput
from app.input_adapter import build_projectinputs

# Import auth
from app.auth import (
    verify_login,
    create_session_token,
    decode_session_token,
    make_session_cookie,
    clear_session_cookie,
    generate_csrf_token,
    validate_csrf_token,
    _check_rate_limit,
    _record_failed_login,
    _clear_failed_logins,
    COOKIE_NAME,
)

# Import persistence
from app.persistence.repository import (
    archive_scenario,
    count_runs,
    delete_run,
    duplicate_scenario,
    get_project_by_code,
    get_run,
    get_scenario,
    list_exports,
    list_runs,
    list_scenarios,
    record_export,
    rename_scenario,
    save_project,
    save_run,
    save_scenario,
)
from app.ui.project_context import get_project_context, all_project_ids
from app.ui.runtime_summary import runtime_summary_to_dict, build_runtime_summary, NOT_AVAILABLE
from app.export.runtime_summary import build_runtime_summary_csv
from app.export.institutional_workbook import export_institutional_workbook_skeleton

# -- FastAPI app --------------------------------------------------------------
app = FastAPI(title="FincoGPT Internal Demo")

# -- Template setup -----------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "app", "templates"))
templates.env.globals["htmx"] = True

# -- Static files -------------------------------------------------------------
if os.path.exists(os.path.join(BASE_DIR, "static")):
    app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

# -- Observability middleware -------------------------------------------------
# Import only if middleware files exist (graceful degradation)
try:
    from app.logging_config import configure_logging
    configure_logging()
except Exception:
    pass

try:
    from app.middleware.security_headers import SecurityHeadersMiddleware
    from app.middleware.request_logging import RequestLoggingMiddleware
    from app.middleware.exception_handler import ExceptionHandlerMiddleware

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    # ExceptionHandlerMiddleware must be last (catches all remaining errors)
    app.add_middleware(ExceptionHandlerMiddleware)
except Exception:
    pass  # middleware registration failure should not break the app

# -- Shared caveats (visible in UI) -------------------------------------------
CAVEATS = [
    "TUHO CO2 revenue missing (611 kEUR Y1) - model understates revenue",
    "Oborovo OpEx duplication (+660 kEUR Y1) - model overstates OpEx",
    "Model outputs are screening-grade - not audited financial advice",
]

# -- KPI names ----------------------------------------------------------------
KPI_LABELS = {
    "project_irr": "Project IRR",
    "equity_irr": "Equity IRR",
    "min_dscr": "Min DSCR",
    "avg_dscr": "Avg DSCR",
    "total_revenue_keur": "Total Revenue (kEUR)",
    "total_ebitda_keur": "Total EBITDA (kEUR)",
}

SCENARIOS = ["Base", "Downside", "Upside"]
PROJECT_TYPES = ["Solar", "Wind"]

# -- Auth dependency ----------------------------------------------------------

def get_current_user(request: Request):
    """Extract session from cookie. Returns None if not authenticated."""
    cookies = request.cookies
    token = cookies.get(COOKIE_NAME)
    if not token:
        return None
    return decode_session_token(token)

def require_auth(request: Request):
    """Require auth - returns user or raises redirect to /login."""
    user = get_current_user(request)
    if not user:
        # Return redirect URL for caller to use (avoiding async issues)
        raise HTTPException(status_code=302)
    return user


def _governance_snapshot(project_code: str | None = None) -> dict:
    project_label = (project_code or "").upper() or "GENERAL"
    return {
        "project_code": project_label,
        "g20_status": "BLOCKED",
        "r99_r102_status": "NOT APPROVED",
        "accepted_conventions_state": "Phase 10 closeout baseline",
        "evidence_posture_summary": "Runtime vs governance distinction preserved",
    }


def _collect_form_snapshot(form) -> dict:
    fields = [
        "active_project",
        "project_type",
        "scenario",
        "capacity_mw",
        "tariff_eur_mwh",
        "p50_hours",
        "total_capex_keur",
        "opex_y1_keur",
        "gearing_pct",
        "target_dscr",
        "interest_rate_pct",
        "tenor_years",
        "cod_date",
        "construction_months",
        "horizon_years",
        "capacity_factor",
        "ppa_term_years",
    ]
    return {field: form.get(field, "") for field in fields}


def _project_persistence_metadata(project_ctx, form_snapshot: dict | None = None) -> tuple[str, str]:
    if project_ctx is not None:
        return project_ctx.id, project_ctx.name
    active_project = (form_snapshot or {}).get("active_project", "").strip().lower()
    if active_project == "oborovo":
        return "oborovo", "Oborovo Solar PV"
    return "tuho", "TUHO Wind 1"


def _current_project_workspace(user, project_ctx):
    project_code, project_name = _project_persistence_metadata(project_ctx)
    project_record = save_project(
        user_id=user.user_id,
        project_code=project_code,
        project_name=project_name,
        source_project_template=project_code,
        governance_state=_governance_snapshot(project_code),
        last_run_summary={},
    )
    scenarios = list_scenarios(user.user_id, project_id=project_record.project_id, include_archived=False, limit=12)
    exports = list_exports(user.user_id, project_id=project_record.project_id, limit=8)
    return project_record, scenarios, exports


def _render_scenario_workspace(request: Request, user, project_record, scenarios, exports, message: str | None = None):
    return templates.TemplateResponse(
        request=request,
        name="partials/scenario_workspace.html",
        context={
            "user": user,
            "project_record": project_record,
            "scenario_records": scenarios,
            "export_records": exports,
            "workspace_message": message,
        },
    )

# -- Helpers ------------------------------------------------------------------

def _build_schema_from_form(
    project_type: str,
    scenario: str,
    capacity_mw: Optional[str] = None,
    tariff_eur_mwh: Optional[str] = None,
    p50_hours: Optional[str] = None,
    total_capex_keur: Optional[str] = None,
    opex_y1_keur: Optional[str] = None,
    gearing_pct: Optional[str] = None,
    target_dscr: Optional[str] = None,
    interest_rate_pct: Optional[str] = None,
    tenor_years: Optional[str] = None,
) -> ProjectInputsSchema:
    """Build ProjectInputsSchema from form fields.
    
    Blank optional fields -> None -> factory defaults preserved.
    Raises ValueError for invalid numeric values.
    """
    def _float(val: Optional[str]) -> Optional[float]:
        if val is None or val.strip() == "":
            return None
        f = float(val)
        if f < 0:
            raise ValueError(f"{val} must be non-negative")
        return f

    def _int(val: Optional[str]) -> Optional[int]:
        if val is None or val.strip() == "":
            return None
        i = int(float(val))
        if i < 0:
            raise ValueError(f"{val} must be non-negative")
        return i

    revenue = None
    if tariff_eur_mwh or p50_hours:
        revenue = RevenueInput(
            tariff_eur_mwh=_float(tariff_eur_mwh),
            p50_hours=_float(p50_hours),
        )

    capex = None
    if total_capex_keur:
        capex = CapexInput(total_capex_keur=_float(total_capex_keur))

    opex = None
    if opex_y1_keur:
        opex = OpexInput(opex_y1_keur=_float(opex_y1_keur))

    debt = None
    if any([gearing_pct, target_dscr, interest_rate_pct, tenor_years]):
        debt = DebtInput(
            gearing_pct=_float(gearing_pct) if gearing_pct else None,
            target_dscr=_float(target_dscr) if target_dscr else None,
            interest_rate_pct=_float(interest_rate_pct) if interest_rate_pct else None,
            tenor_years=_int(tenor_years) if tenor_years else None,
        )

    return ProjectInputsSchema(
        project_type=project_type,
        scenario=scenario,
        capacity_mw=_float(capacity_mw) if capacity_mw else None,
        revenue=revenue,
        capex=capex,
        opex=opex,
        debt=debt,
    )


def _validate_form(project_type: str, scenario: str, errors: list[str]) -> bool:
    """Perform basic form validation. Returns True if valid."""
    if project_type not in PROJECT_TYPES:
        errors.append(f"project_type must be one of {PROJECT_TYPES}")
    if scenario not in SCENARIOS:
        errors.append(f"scenario must be one of {SCENARIOS}")
    return len(errors) == 0


def _validate_numeric_field(name: str, val: Optional[str], max_val: Optional[float] = None):
    """Validate a numeric form field. Returns (value, error_message)."""
    if not val or val.strip() == "":
        return None, None
    try:
        f = float(val)
        if f < 0:
            return None, f"{name} must be non-negative"
        if max_val is not None and f > max_val:
            return None, f"{name} must be <= {max_val}"
        return f, None
    except ValueError:
        return None, f"{name} must be a number"


def _format_kpis(kpis: dict) -> list[dict]:
    """Convert raw KPI dict into label/value pairs for template."""
    rows = []
    for key, label in KPI_LABELS.items():
        val = kpis.get(key)
        if val is None:
            display = "-"
        elif key in ("project_irr", "equity_irr"):
            display = f"{val * 100:.2f}%"
        elif key in ("min_dscr", "avg_dscr"):
            display = f"{val:.3f}x"
        elif key in ("total_revenue_keur", "total_ebitda_keur"):
            display = f"{val:,.0f}"
        else:
            display = str(val)
        rows.append({"label": label, "key": key, "value": display})
    return rows


# -- Auth Routes --------------------------------------------------------------

def _get_client_ip(request: Request) -> str:
    """Extract client IP from request, checking X-Forwarded-For first."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@app.get("/login")
async def login_get(request: Request):
    """Login page."""
    user = get_current_user(request)
    if user:
        return RedirectResponse(url="/", status_code=302)

    csrf_token = generate_csrf_token()
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"csrf_token": csrf_token},
    )


@app.post("/login")
async def login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(...),
):
    """Process login. Set session cookie on success. Validates CSRF + rate limit."""
    ip = _get_client_ip(request)

    # Rate limit check
    allowed, seconds_left = _check_rate_limit(ip)
    if not allowed:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "error": f"Too many failed attempts. Try again in {seconds_left}s.",
                "csrf_token": generate_csrf_token(),
            },
            status_code=429,
        )

    # CSRF validation
    if not validate_csrf_token(csrf_token):
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "error": "Invalid or expired form. Please try again.",
                "csrf_token": generate_csrf_token(),
            },
            status_code=403,
        )

    if verify_login(username, password):
        _clear_failed_logins(ip)
        token = create_session_token()
        cookie = make_session_cookie(token)
        response = RedirectResponse(url="/", status_code=302)
        response.set_cookie(**cookie)
        return response

    # Failed login
    _record_failed_login(ip)
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "error": "Invalid username or password.",
            "csrf_token": generate_csrf_token(),
        },
        status_code=401,
    )


@app.post("/logout")
async def logout():
    """Clear session cookie and redirect to login."""
    response = RedirectResponse(url="/login", status_code=302)
    cookie = clear_session_cookie()
    response.set_cookie(**cookie)
    return response


# -- Public Routes ------------------------------------------------------------

@app.get("/public-health")
async def public_health():
    """Public health check - no auth required."""
    return {
        "status": "ok",
        "app": "fincogpt",
        "mode": "internal-demo",
    }


@app.get("/health")
async def health(request: Request):
    """Private health check - requires auth."""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"status": "unauthenticated", "detail": "Login required"}, status_code=401)
    return JSONResponse({"status": "ok"})


# -- Protected Routes ---------------------------------------------------------

@app.get("/")
async def index(request: Request, project: str | None = None):
    """Main input form. Requires auth. Supports ?project=tuho|oborovo."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    ctx = get_project_context(project)
    available_projects = all_project_ids()
    project_record, scenario_records, export_records = _current_project_workspace(user, ctx)

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "project_types": PROJECT_TYPES,
            "scenarios": SCENARIOS,
            "caveats": CAVEATS,
            "form_data": {},
            "validation_errors": [],
            "success_message": None,
            "user": user,
            "project_ctx": ctx,
            "available_projects": available_projects,
            "project_record": project_record,
            "scenario_records": scenario_records,
            "export_records": export_records,
            "workspace_message": None,
        },
    )


@app.post("/validate")
async def validate(request: Request):
    """Validate form inputs. Requires auth."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    # Parse form data
    form = await request.form()
    active_project = form.get("active_project", "").strip().lower()
    project_type = form.get("project_type", "")
    scenario = form.get("scenario", "")
    capacity_mw = form.get("capacity_mw", "")
    tariff_eur_mwh = form.get("tariff_eur_mwh", "")
    p50_hours = form.get("p50_hours", "")
    total_capex_keur = form.get("total_capex_keur", "")
    opex_y1_keur = form.get("opex_y1_keur", "")
    gearing_pct = form.get("gearing_pct", "")
    target_dscr = form.get("target_dscr", "")
    interest_rate_pct = form.get("interest_rate_pct", "")
    tenor_years = form.get("tenor_years", "")

    errors = []

    if project_type not in PROJECT_TYPES:
        errors.append(f"project_type must be one of {PROJECT_TYPES}")
    if scenario not in SCENARIOS:
        errors.append(f"scenario must be one of {SCENARIOS}")

    numeric_checks = [
        ("capacity_mw", capacity_mw, 2000.0),
        ("tariff_eur_mwh", tariff_eur_mwh, 1000.0),
        ("p50_hours", p50_hours, 10000.0),
        ("total_capex_keur", total_capex_keur, 1_000_000.0),
        ("opex_y1_keur", opex_y1_keur, 500_000.0),
        ("gearing_pct", gearing_pct, 100.0),
        ("target_dscr", target_dscr, 10.0),
        ("interest_rate_pct", interest_rate_pct, 30.0),
        ("tenor_years", tenor_years, 50.0),
    ]
    for fname, fval, max_val in numeric_checks:
        _, err = _validate_numeric_field(fname, fval, max_val)
        if err:
            errors.append(err)

    if not errors:
        try:
            schema = _build_schema_from_form(
                project_type, scenario,
                capacity_mw, tariff_eur_mwh, p50_hours,
                total_capex_keur, opex_y1_keur,
                gearing_pct, target_dscr, interest_rate_pct, tenor_years,
            )
        except ValueError as ve:
            errors.append(str(ve))

    return templates.TemplateResponse(
        request=request,
        name="partials/validation.html",
        context={
            "valid": len(errors) == 0,
            "errors": errors,
            "form_data": {"project_type": project_type, "scenario": scenario},
        },
    )


@app.post("/run")
async def run(request: Request):
    """Run model with custom inputs. Requires auth.

    Accepts optional active_project field from form (hidden input set by JS).
    If active_project is set, runs the named project (TUHO/Oborovo) instead of
    building a schema from arbitrary form inputs.
    """
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    form = await request.form()
    active_project = form.get("active_project", "").strip().lower()
    project_type = form.get("project_type", "")
    scenario = form.get("scenario", "")
    capacity_mw = form.get("capacity_mw", "")
    tariff_eur_mwh = form.get("tariff_eur_mwh", "")
    p50_hours = form.get("p50_hours", "")
    total_capex_keur = form.get("total_capex_keur", "")
    opex_y1_keur = form.get("opex_y1_keur", "")
    gearing_pct = form.get("gearing_pct", "")
    target_dscr = form.get("target_dscr", "")
    interest_rate_pct = form.get("interest_rate_pct", "")
    tenor_years = form.get("tenor_years", "")

    # -- Phase 9.5: Named project binding -------------------------------------
    # If active_project is set, run the named project factory directly.
    # This bypasses arbitrary form inputs and uses factory defaults.
    if active_project in ("tuho", "oborovo"):
        ctx = get_project_context(active_project)
        project_name = ctx.name
        try:
            project_key = "TUHO" if active_project == "tuho" else "Oborovo"
            result = run_project(project_key, "Base")
            kpis = _format_kpis(result["kpis"])
            runtime_summary = runtime_summary_to_dict(result, active_project, project_name)
            # Persist to sessionStorage so output tabs can read it on next page load
            runtime_html = templates.TemplateResponse(
                request=request,
                name="partials/runtime_summary.html",
                context={
                    "kpis": kpis,
                    "runtime_summary": runtime_summary,
                    "run_data": {"project_type": active_project, "scenario": "Base"},
                    "messages": result.get("messages", []),
                    "integration_status": result.get("integration_status", "full"),
                },
            )
            # Prepend sessionStorage save script
            from fastapi.responses import HTMLResponse
            body = runtime_html.body
            body_str = body.decode("utf-8")
            save_tag = (
                '<script>'
                'sessionStorage.setItem("lastRuntimeSummary", ' + json.dumps(runtime_summary) + ');'
                'window._populateRuntimeBlock && window._populateRuntimeBlock();'
                '</script>'
            )
            if body_str.startswith("<!DOCTYPE"):
                # Inject after <head> or at start of <body>
                body_str = body_str.replace(
                    "<body",
                    save_tag + "<body"
                )
            else:
                body_str = save_tag + body_str
            return HTMLResponse(content=body_str, status_code=runtime_html.status_code)
        except Exception as e:
            return templates.TemplateResponse(
                request=request,
                name="partials/errors.html",
                context={"errors": [f"Model error ({active_project}): {str(e)}"]},
            )
    # -- Standard form-based run (no active_project) --------------------------

    errors = []
    if not _validate_form(project_type, scenario, errors):
        return templates.TemplateResponse(
            request=request,
            name="partials/errors.html",
            context={"errors": errors},
        )

    try:
        schema = _build_schema_from_form(
            project_type, scenario,
            capacity_mw, tariff_eur_mwh, p50_hours,
            total_capex_keur, opex_y1_keur,
            gearing_pct, target_dscr, interest_rate_pct, tenor_years,
        )
    except ValueError as ve:
        return templates.TemplateResponse(
            request=request,
            name="partials/errors.html",
            context={"errors": [str(ve)]},
        )

    try:
        override = build_projectinputs(schema)
        result = run_project(project_type, scenario, project_inputs_override=override)
        kpis = _format_kpis(result["kpis"])
        return templates.TemplateResponse(
            request=request,
            name="partials/kpis.html",
            context={
                "kpis": kpis,
                "run_data": {
                    "project_type": project_type,
                    "scenario": scenario,
                    "capacity_mw": capacity_mw,
                    "tariff_eur_mwh": tariff_eur_mwh,
                    "total_capex_keur": total_capex_keur,
                    "gearing_pct": gearing_pct,
                },
                "messages": result.get("messages", []),
                "integration_status": result.get("integration_status", "full"),
            },
        )
    except Exception as e:
        return templates.TemplateResponse(
            request=request,
            name="partials/errors.html",
            context={"errors": [f"Model error: {str(e)}"]},
        )


@app.post("/compare")
async def compare(request: Request):
    """Run Base/Downside/Upside comparison. Requires auth."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    form = await request.form()
    project_type = form.get("project_type", "")
    capacity_mw = form.get("capacity_mw", "")
    tariff_eur_mwh = form.get("tariff_eur_mwh", "")
    p50_hours = form.get("p50_hours", "")
    total_capex_keur = form.get("total_capex_keur", "")
    opex_y1_keur = form.get("opex_y1_keur", "")
    gearing_pct = form.get("gearing_pct", "")
    target_dscr = form.get("target_dscr", "")
    interest_rate_pct = form.get("interest_rate_pct", "")
    tenor_years = form.get("tenor_years", "")

    errors = []
    if project_type not in PROJECT_TYPES:
        errors.append(f"project_type must be one of {PROJECT_TYPES}")
        return templates.TemplateResponse(
            request=request,
            name="partials/errors.html",
            context={"errors": errors},
        )

    try:
        schema = _build_schema_from_form(
            project_type, "Base",
            capacity_mw, tariff_eur_mwh, p50_hours,
            total_capex_keur, opex_y1_keur,
            gearing_pct, target_dscr, interest_rate_pct, tenor_years,
        )
        override = build_projectinputs(schema)
    except (ValueError, Exception) as e:
        return templates.TemplateResponse(
            request=request,
            name="partials/errors.html",
            context={"errors": [f"Invalid input: {str(e)}"]},
        )

    results = {}
    for sc in SCENARIOS:
        try:
            r = run_project(project_type, sc, project_inputs_override=override)
            results[sc] = {
                "project_irr": r["kpis"].get("project_irr"),
                "equity_irr": r["kpis"].get("equity_irr"),
                "min_dscr": r["kpis"].get("min_dscr"),
                "avg_dscr": r["kpis"].get("avg_dscr"),
                "total_revenue_keur": r["kpis"].get("total_revenue_keur"),
                "total_ebitda_keur": r["kpis"].get("total_ebitda_keur"),
            }
        except Exception as e:
            results[sc] = {"error": str(e)}

    return templates.TemplateResponse(
        request=request,
        name="partials/comparison.html",
        context={
            "project_type": project_type,
            "scenarios": SCENARIOS,
            "results": results,
        },
    )


@app.post("/download")
async def download_post(request: Request):
    """Generate Excel export with current form values. Requires auth."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    form = await request.form()
    active_project = form.get("active_project", "").strip().lower()
    project_type = form.get("project_type", "")
    scenario = form.get("scenario", "")
    capacity_mw = form.get("capacity_mw", "")
    tariff_eur_mwh = form.get("tariff_eur_mwh", "")
    p50_hours = form.get("p50_hours", "")
    total_capex_keur = form.get("total_capex_keur", "")
    opex_y1_keur = form.get("opex_y1_keur", "")
    gearing_pct = form.get("gearing_pct", "")
    target_dscr = form.get("target_dscr", "")
    interest_rate_pct = form.get("interest_rate_pct", "")
    tenor_years = form.get("tenor_years", "")

    try:
        schema = _build_schema_from_form(
            project_type, scenario,
            capacity_mw, tariff_eur_mwh, p50_hours,
            total_capex_keur, opex_y1_keur,
            gearing_pct, target_dscr, interest_rate_pct, tenor_years,
        )
        override = build_projectinputs(schema)
    except (ValueError, Exception) as e:
        return HTMLResponse(
            content=f"<html><body><h2>Excel generation failed</h2><p>Invalid input: {str(e)}</p><a href='/'>Back</a></body></html>",
            status_code=400,
        )

    try:
        demo = run_demo_project(project_type, scenario, project_inputs_override=override)
        excel_bytes = build_excel_export(
            result=demo.result,
            project_inputs=demo.project_inputs,
        )
        filename = f"fincogpt_{project_type.lower()}_{scenario.lower()}.xlsx"
        project_code = active_project or project_type.lower() or "tuho"
        project_record = get_project_by_code(user.user_id, project_code)
        record_export(
            user_id=user.user_id,
            project_code=project_code,
            export_type="excel_model_export",
            artifact_name=filename,
            artifact_path=f"/download?project_type={project_type}&scenario={scenario}",
            project_id=project_record.project_id if project_record else None,
            governance_state=_governance_snapshot(project_code),
        )
        return StreamingResponse(
            iter([excel_bytes]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(excel_bytes)),
            },
        )
    except Exception as e:
        return HTMLResponse(
            content=f"<html><body><h2>Excel generation failed</h2><p>{str(e)}</p><a href='/'>Back</a></body></html>",
            status_code=500,
        )


@app.get("/download")
async def download_get(request: Request, project_type: str = "Solar", scenario: str = "Base"):
    """Generate Excel export (GET - uses factory defaults). Requires auth."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    try:
        demo = run_demo_project(project_type, scenario)
        excel_bytes = build_excel_export(
            result=demo.result,
            project_inputs=demo.project_inputs,
        )
        filename = f"fincogpt_{project_type.lower()}_{scenario.lower()}.xlsx"
        project_code = project_type.lower() if project_type else "tuho"
        project_record = get_project_by_code(user.user_id, project_code)
        record_export(
            user_id=user.user_id,
            project_code=project_code,
            export_type="excel_model_export",
            artifact_name=filename,
            artifact_path=f"/download?project_type={project_type}&scenario={scenario}",
            project_id=project_record.project_id if project_record else None,
            governance_state=_governance_snapshot(project_code),
        )
        return StreamingResponse(
            iter([excel_bytes]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(excel_bytes)),
            },
        )
    except Exception as e:
        return HTMLResponse(
            content=f"<html><body><h2>Excel generation failed</h2><p>{str(e)}</p><a href='/'>Back</a></body></html>",
            status_code=500,
        )


@app.get("/exports/runtime-summary.csv")
async def runtime_summary_export(request: Request, project: str = "tuho"):
    """Download standardized Phase 10 runtime summary CSV. Requires auth."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    try:
        csv_text = build_runtime_summary_csv(project)
    except ValueError as exc:
        return HTMLResponse(
            content=f"<html><body><h2>Runtime summary export failed</h2><p>{str(exc)}</p><a href='/'>Back</a></body></html>",
            status_code=400,
        )

    safe_project = project.strip().lower() if project else "tuho"
    filename = f"phase10_{safe_project}_runtime_summary.csv"
    data = csv_text.encode("utf-8")
    project_record = get_project_by_code(user.user_id, safe_project)
    record_export(
        user_id=user.user_id,
        project_code=safe_project,
        export_type="runtime_summary_csv",
        artifact_name=filename,
        artifact_path=f"/exports/runtime-summary.csv?project={safe_project}",
        project_id=project_record.project_id if project_record else None,
        governance_state=_governance_snapshot(safe_project),
    )
    return StreamingResponse(
        iter([data]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(data)),
        },
    )


@app.get("/exports/institutional-workbook.xlsx")
async def institutional_workbook_export(request: Request, project: str = "tuho"):
    """Download Phase 10 institutional workbook skeleton. Requires auth."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    try:
        workbook_bytes = export_institutional_workbook_skeleton(project)
    except ValueError as exc:
        return HTMLResponse(
            content=f"<html><body><h2>Institutional workbook export failed</h2><p>{str(exc)}</p><a href='/'>Back</a></body></html>",
            status_code=400,
        )

    safe_project = project.strip().lower() if project else "tuho"
    filename = f"phase10_{safe_project}_institutional_workbook_skeleton.xlsx"
    project_record = get_project_by_code(user.user_id, safe_project)
    record_export(
        user_id=user.user_id,
        project_code=safe_project,
        export_type="institutional_workbook",
        artifact_name=filename,
        artifact_path=f"/exports/institutional-workbook.xlsx?project={safe_project}",
        project_id=project_record.project_id if project_record else None,
        governance_state=_governance_snapshot(safe_project),
    )
    return StreamingResponse(
        iter([workbook_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(workbook_bytes)),
        },
    )


@app.get("/scenarios")
async def list_scenarios_endpoint(request: Request, project: str = "tuho"):
    """Render the saved scenario and export-history workspace for the active project."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    project_ctx = get_project_context(project)
    project_record, scenarios, exports = _current_project_workspace(user, project_ctx)
    return _render_scenario_workspace(request, user, project_record, scenarios, exports)


@app.post("/scenarios/save")
async def save_scenario_endpoint(request: Request):
    """Persist the current form snapshot as a saved scenario."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    form = await request.form()
    snapshot = _collect_form_snapshot(form)
    project_code, project_name = _project_persistence_metadata(None, snapshot)
    scenario_name = f"{project_name} {snapshot.get('scenario', 'Base')} {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    project_record = save_project(
        user_id=user.user_id,
        project_code=project_code,
        project_name=project_name,
        source_project_template=project_code,
        governance_state=_governance_snapshot(project_code),
        last_run_summary={},
    )
    save_scenario(
        user_id=user.user_id,
        project_id=project_record.project_id,
        scenario_name=scenario_name,
        project_code=project_code,
        source_project_template=project_code,
        snapshot=snapshot,
        governance_state=_governance_snapshot(project_code),
        last_run_summary={},
    )
    scenarios = list_scenarios(user.user_id, project_id=project_record.project_id, include_archived=False, limit=12)
    exports = list_exports(user.user_id, project_id=project_record.project_id, limit=8)
    return _render_scenario_workspace(
        request,
        user,
        project_record,
        scenarios,
        exports,
        message=f"Saved scenario snapshot for {project_name}.",
    )


@app.get("/scenarios/{scenario_id}/load")
async def load_scenario_endpoint(request: Request, scenario_id: str):
    """Load a saved scenario snapshot back into the form."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    record = get_scenario(scenario_id, user.user_id)
    if record is None:
        return JSONResponse({"error": "Scenario not found"}, status_code=404)

    return templates.TemplateResponse(
        request=request,
        name="partials/scenario_load_result.html",
        context={"record": record},
        headers={"HX-Trigger": "scenarioLoaded"},
    )


@app.post("/scenarios/{scenario_id}/duplicate")
async def duplicate_scenario_endpoint(request: Request, scenario_id: str):
    """Duplicate a saved scenario snapshot."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    original = get_scenario(scenario_id, user.user_id)
    if original is None:
        return JSONResponse({"error": "Scenario not found"}, status_code=404)

    duplicate_scenario(user.user_id, scenario_id)
    project_record = get_project_by_code(user.user_id, original.project_code)
    scenarios = list_scenarios(user.user_id, project_id=original.project_id, include_archived=False, limit=12)
    exports = list_exports(user.user_id, project_id=original.project_id, limit=8)
    return _render_scenario_workspace(
        request,
        user,
        project_record,
        scenarios,
        exports,
        message=f"Duplicated {original.scenario_name}.",
    )


@app.post("/scenarios/{scenario_id}/rename")
async def rename_scenario_endpoint(request: Request, scenario_id: str):
    """Rename a saved scenario."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    form = await request.form()
    new_name = (form.get("scenario_name", "") or "").strip()
    if not new_name:
        return JSONResponse({"error": "Scenario name is required"}, status_code=400)

    record = get_scenario(scenario_id, user.user_id)
    if record is None:
        return JSONResponse({"error": "Scenario not found"}, status_code=404)

    rename_scenario(user.user_id, scenario_id, new_name)
    project_record = get_project_by_code(user.user_id, record.project_code)
    scenarios = list_scenarios(user.user_id, project_id=record.project_id, include_archived=False, limit=12)
    exports = list_exports(user.user_id, project_id=record.project_id, limit=8)
    return _render_scenario_workspace(
        request,
        user,
        project_record,
        scenarios,
        exports,
        message=f"Renamed scenario to {new_name}.",
    )


@app.post("/scenarios/{scenario_id}/archive")
async def archive_scenario_endpoint(request: Request, scenario_id: str):
    """Soft-archive a saved scenario."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    record = get_scenario(scenario_id, user.user_id)
    if record is None:
        return JSONResponse({"error": "Scenario not found"}, status_code=404)

    archive_scenario(user.user_id, scenario_id)
    project_record = get_project_by_code(user.user_id, record.project_code)
    scenarios = list_scenarios(user.user_id, project_id=record.project_id, include_archived=False, limit=12)
    exports = list_exports(user.user_id, project_id=record.project_id, limit=8)
    return _render_scenario_workspace(
        request,
        user,
        project_record,
        scenarios,
        exports,
        message=f"Archived {record.scenario_name}.",
    )


@app.get("/runs")
async def list_runs_endpoint(request: Request):
    """List recent runs for the authenticated user."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    runs = list_runs(user.user_id, limit=20)
    data = [{
        "run_id": r.run_id,
        "project_type": r.project_type,
        "scenario": r.scenario,
        "created_at": r.created_at.isoformat() if hasattr(r.created_at, 'isoformat') else r.created_at,
        "inputs": r.inputs,
        "kpis": r.kpis,
    } for r in runs]
    return templates.TemplateResponse(
        request=request,
        name="partials/run_history.html",
        context={"runs": data, "user": user},
    )


@app.post("/save-run")
async def save_run_endpoint(request: Request):
    """Save current model run to persistence.

    Saves current form state by re-running the model (not a snapshot of the HTML card).
    Returns HTML partial for HTMX consumption.
    """
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    form = await request.form()
    project_type = form.get("project_type", "")
    scenario = form.get("scenario", "")

    # Never trust user_id from client; always derive from session.
    user_id = user.user_id

    # Build inputs dict from form
    inputs = {
        "capacity_mw": form.get("capacity_mw", ""),
        "tariff_eur_mwh": form.get("tariff_eur_mwh", ""),
        "p50_hours": form.get("p50_hours", ""),
        "total_capex_keur": form.get("total_capex_keur", ""),
        "opex_y1_keur": form.get("opex_y1_keur", ""),
        "gearing_pct": form.get("gearing_pct", ""),
        "target_dscr": form.get("target_dscr", ""),
        "interest_rate_pct": form.get("interest_rate_pct", ""),
        "tenor_years": form.get("tenor_years", ""),
    }

    # Validate form
    errors = []
    if not _validate_form(project_type, scenario, errors):
        return templates.TemplateResponse(
            request=request,
            name="partials/save_result.html",
            context={"success": False, "error": errors[0] if errors else "Invalid form"},
            headers={"HX-Trigger": "refreshHistory"},
        )

    # Re-run model to get fresh KPIs (matches current form state)
    try:
        schema = _build_schema_from_form(
            project_type, scenario,
            inputs.get("capacity_mw"), inputs.get("tariff_eur_mwh"),
            inputs.get("p50_hours"), inputs.get("total_capex_keur"),
            inputs.get("opex_y1_keur"), inputs.get("gearing_pct"),
            inputs.get("target_dscr"), inputs.get("interest_rate_pct"),
            inputs.get("tenor_years"),
        )
        override = build_projectinputs(schema)
        result = run_project(project_type, scenario, project_inputs_override=override)
        kpis = result["kpis"]
    except Exception as e:
        return templates.TemplateResponse(
            request=request,
            name="partials/save_result.html",
            context={"success": False, "error": f"Model error: {str(e)}"},
            headers={"HX-Trigger": "refreshHistory"},
        )

    # Persist to DB
    try:
        run_record = save_run(
            user_id=user_id,
            project_type=project_type,
            scenario=scenario,
            inputs=inputs,
            kpis=kpis,
        )
        project_code = active_project or project_type.lower() or "tuho"
        project_name = "TUHO Wind 1" if project_code == "tuho" else "Oborovo Solar PV" if project_code == "oborovo" else project_type
        save_project(
            user_id=user_id,
            project_code=project_code,
            project_name=project_name,
            source_project_template=project_code,
            governance_state=_governance_snapshot(project_code),
            last_run_summary=kpis,
        )
        return templates.TemplateResponse(
            request=request,
            name="partials/save_result.html",
            context={
                "success": True,
                "run_id": run_record.run_id,
                "project_type": project_type,
                "scenario": scenario,
                "created_at": run_record.created_at.isoformat(),
            },
            headers={"HX-Trigger": "refreshHistory"},
        )
    except Exception as e:
        return templates.TemplateResponse(
            request=request,
            name="partials/save_result.html",
            context={"success": False, "error": f"Save failed: {str(e)}"},
            headers={"HX-Trigger": "refreshHistory"},
        )


@app.get("/run/{run_id}")
async def get_run_endpoint(request: Request, run_id: str):
    """Load a saved run by ID."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    record = get_run(run_id, user.user_id)
    if record is None:
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "Run not found"}, status_code=404)

    return templates.TemplateResponse(
        request=request,
        name="partials/kpis.html",
        context={
            "kpis": _format_kpis(record.kpis),
            "run_data": {
                "project_type": record.project_type,
                "scenario": record.scenario,
                "capacity_mw": record.inputs.get("capacity_mw", ""),
                "tariff_eur_mwh": record.inputs.get("tariff_eur_mwh", ""),
                "total_capex_keur": record.inputs.get("total_capex_keur", ""),
                "gearing_pct": record.inputs.get("gearing_pct", ""),
            },
            "messages": [f"Loaded run {run_id} from {record.created_at.strftime('%Y-%m-%d %H:%M')}"] ,
            "integration_status": "full",
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765)
