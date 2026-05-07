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
    COOKIE_NAME,
)

# ── FastAPI app ────────────────────────────────────────────────────────────
app = FastAPI(title="FincoGPT Internal Demo")

# ── Template setup ──────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "app", "templates"))
templates.env.globals["htmx"] = True

# ── Static files ────────────────────────────────────────────────────────────
if os.path.exists(os.path.join(BASE_DIR, "static")):
    app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

# ── Shared caveats (visible in UI) ─────────────────────────────────────────
CAVEATS = [
    "TUHO CO2 revenue missing (611 kEUR Y1) — model understates revenue",
    "Oborovo OpEx duplication (+660 kEUR Y1) — model overstates OpEx",
    "Model outputs are screening-grade — not audited financial advice",
]

# ── KPI names ───────────────────────────────────────────────────────────────
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

# ── Auth dependency ─────────────────────────────────────────────────────────

def get_current_user(request: Request):
    """Extract session from cookie. Returns None if not authenticated."""
    cookies = request.cookies
    token = cookies.get(COOKIE_NAME)
    if not token:
        return None
    return decode_session_token(token)

def require_auth(request: Request):
    """Require auth — returns user or raises redirect to /login."""
    user = get_current_user(request)
    if not user:
        # Return redirect URL for caller to use (avoiding async issues)
        raise HTTPException(status_code=302)
    return user

# ── Helpers ─────────────────────────────────────────────────────────────────

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
    
    Blank optional fields → None → factory defaults preserved.
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
            return None, f"{name} must be ≤ {max_val}"
        return f, None
    except ValueError:
        return None, f"{name} must be a number"


def _format_kpis(kpis: dict) -> list[dict]:
    """Convert raw KPI dict into label/value pairs for template."""
    rows = []
    for key, label in KPI_LABELS.items():
        val = kpis.get(key)
        if val is None:
            display = "—"
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


# ── Auth Routes ─────────────────────────────────────────────────────────────

@app.get("/login")
async def login_get(request: Request):
    """Login page."""
    user = get_current_user(request)
    if user:
        return RedirectResponse(url="/", status_code=302)

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={},
    )


@app.post("/login")
async def login_post(request: Request, username: str = Form(...), password: str = Form(...)):
    """Process login. Set session cookie on success."""
    if verify_login(username, password):
        token = create_session_token()
        cookie = make_session_cookie(token)
        response = RedirectResponse(url="/", status_code=302)
        response.set_cookie(**cookie)
        return response

    # Failed login
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": "Invalid username or password."},
        status_code=401,
    )


@app.post("/logout")
async def logout():
    """Clear session cookie and redirect to login."""
    response = RedirectResponse(url="/login", status_code=302)
    cookie = clear_session_cookie()
    response.set_cookie(**cookie)
    return response


# ── Public Routes ───────────────────────────────────────────────────────────

@app.get("/public-health")
async def public_health():
    """Public health check — no auth required."""
    return {
        "status": "ok",
        "app": "fincogpt",
        "mode": "internal-demo",
    }


@app.get("/health")
async def health(request: Request):
    """Private health check — requires auth."""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"status": "unauthenticated", "detail": "Login required"}, status_code=401)
    return JSONResponse({"status": "ok"})


# ── Protected Routes ────────────────────────────────────────────────────────

@app.get("/")
async def index(request: Request):
    """Main input form. Requires auth."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

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
    """Run model with custom inputs. Requires auth."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    form = await request.form()
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
        return StreamingResponse(
            iter([excel_bytes]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        return HTMLResponse(
            content=f"<html><body><h2>Excel generation failed</h2><p>{str(e)}</p><a href='/'>Back</a></body></html>",
            status_code=500,
        )


@app.get("/download")
async def download_get(request: Request, project_type: str = "Solar", scenario: str = "Base"):
    """Generate Excel export (GET — uses factory defaults). Requires auth."""
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
        return StreamingResponse(
            iter([excel_bytes]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        return HTMLResponse(
            content=f"<html><body><h2>Excel generation failed</h2><p>{str(e)}</p><a href='/'>Back</a></body></html>",
            status_code=500,
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765)