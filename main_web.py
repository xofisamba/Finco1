"""HTMX internal demo web interface for Finco1 model."""
import os
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Optional

# Import existing model logic (no changes to these)
from app.api.project_runner import run_project
from app.excel_export import build_excel_export
from app.ui_runner import run_demo_project
from app.capex_engine import build_capex_line_items_from_defaults

# ── FastAPI app ────────────────────────────────────────────────────────────
app = FastAPI(title="FincoGPT Internal Demo")

# ── Template setup ──────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "app", "templates"))
templates.env.globals["htmx"] = True  # flag for conditional HTMX logic

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

# ── Helpers ─────────────────────────────────────────────────────────────────

def _defaults_for_project(project_type: str) -> dict:
    """Return factory-default CapEx line items for a given project type."""
    items = build_capex_line_items_from_defaults(project_type.lower())
    total = sum(item.amount_keur for item in items if item.asset_class.name != "LAND")
    return {
        "capacity_mw": 50 if project_type == "Solar" else 72,
        "total_capex_keur": round(total),
        "opex_y1_keur": 1200 if project_type == "Solar" else 1400,
        "gearing_pct": 75.0,
        "target_dscr": 1.30,
        "interest_rate_pct": 6.5,
        "tenor_years": 20,
        "tariff_eur_mwh": 85 if project_type == "Solar" else 75,
        "p50_hours": 1600 if project_type == "Solar" else 3800,
    }

def _validate_form(project_type: str, scenario: str, errors: list[str]) -> bool:
    """Perform basic form validation. Returns True if valid."""
    if project_type not in PROJECT_TYPES:
        errors.append(f"project_type must be one of {PROJECT_TYPES}")
    if scenario not in SCENARIOS:
        errors.append(f"scenario must be one of {SCENARIOS}")
    return len(errors) == 0

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

# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main input form."""
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
        },
    )

@app.post("/validate")
async def validate(
    request: Request,
    project_type: str = Form(...),
    scenario: str = Form(...),
    capacity_mw: Optional[str] = Form(""),
    tariff_eur_mwh: Optional[str] = Form(""),
    p50_hours: Optional[str] = Form(""),
    total_capex_keur: Optional[str] = Form(""),
    opex_y1_keur: Optional[str] = Form(""),
    gearing_pct: Optional[str] = Form(""),
    target_dscr: Optional[str] = Form(""),
    interest_rate_pct: Optional[str] = Form(""),
    tenor_years: Optional[str] = Form(""),
):
    """Validate form inputs. Return validation.html partial."""
    errors = []

    # Basic required validation
    if project_type not in PROJECT_TYPES:
        errors.append(f"project_type must be one of {PROJECT_TYPES}")
    if scenario not in SCENARIOS:
        errors.append(f"scenario must be one of {SCENARIOS}")

    # Numeric field validation
    numeric_fields = {
        "capacity_mw": capacity_mw,
        "tariff_eur_mwh": tariff_eur_mwh,
        "p50_hours": p50_hours,
        "total_capex_keur": total_capex_keur,
        "opex_y1_keur": opex_y1_keur,
        "gearing_pct": gearing_pct,
        "target_dscr": target_dscr,
        "interest_rate_pct": interest_rate_pct,
        "tenor_years": tenor_years,
    }
    for fname, fval in numeric_fields.items():
        if fval and fval.strip():
            try:
                float(fval)
            except ValueError:
                errors.append(f"{fname} must be a number")

    defaults = _defaults_for_project(project_type)
    return templates.TemplateResponse(
        request=request,
        name="partials/validation.html",
        context={
            "valid": len(errors) == 0,
            "errors": errors,
            "defaults": defaults,
            "form_data": {
                "project_type": project_type,
                "scenario": scenario,
            },
        },
    )

@app.post("/run")
async def run(
    request: Request,
    project_type: str = Form(...),
    scenario: str = Form(...),
    capacity_mw: Optional[str] = Form(""),
    tariff_eur_mwh: Optional[str] = Form(""),
    p50_hours: Optional[str] = Form(""),
    total_capex_keur: Optional[str] = Form(""),
    opex_y1_keur: Optional[str] = Form(""),
    gearing_pct: Optional[str] = Form(""),
    target_dscr: Optional[str] = Form(""),
    interest_rate_pct: Optional[str] = Form(""),
    tenor_years: Optional[str] = Form(""),
):
    """Run model and return kpis.html partial."""
    errors = []
    if not _validate_form(project_type, scenario, errors):
        return templates.TemplateResponse(
            request=request,
            name="partials/errors.html",
            context={"errors": errors},
        )

    # Use defaults for empty optional fields
    defaults = _defaults_for_project(project_type)
    run_data = {
        "project_type": project_type,
        "scenario": scenario,
        "capacity_mw": capacity_mw or str(defaults["capacity_mw"]),
        "total_capex_keur": total_capex_keur or str(defaults["total_capex_keur"]),
        "opex_y1_keur": opex_y1_keur or str(defaults["opex_y1_keur"]),
        "gearing_pct": gearing_pct or str(defaults["gearing_pct"]),
        "interest_rate_pct": interest_rate_pct or str(defaults["interest_rate_pct"]),
        "tenor_years": tenor_years or str(defaults["tenor_years"]),
        "tariff_eur_mwh": tariff_eur_mwh or str(defaults["tariff_eur_mwh"]),
        "p50_hours": p50_hours or str(defaults["p50_hours"]),
    }

    try:
        result = run_project(project_type, scenario)
        kpis = _format_kpis(result["kpis"])
        return templates.TemplateResponse(
            request=request,
            name="partials/kpis.html",
            context={
                "kpis": kpis,
                "run_data": run_data,
                "messages": result.get("messages", []),
                "integration_status": result.get("integration_status", "full"),
            },
        )
    except Exception as e:
        errors.append(f"Model error: {str(e)}")
        return templates.TemplateResponse(
            request=request,
            name="partials/errors.html",
            context={"errors": errors},
        )

@app.post("/compare")
async def compare(
    request: Request,
    project_type: str = Form(...),
):
    """Run Base/Downside/Upside and return comparison.html partial."""
    errors = []
    if project_type not in PROJECT_TYPES:
        errors.append(f"project_type must be one of {PROJECT_TYPES}")
        return templates.TemplateResponse(
            request=request,
            name="partials/errors.html",
            context={"errors": errors},
        )

    results = {}
    for sc in SCENARIOS:
        try:
            r = run_project(project_type, sc)
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

@app.get("/download")
async def download_get(project_type: str = "Solar", scenario: str = "Base"):
    """Generate Excel export (GET with query params)."""
    return await _download_impl(project_type, scenario)

@app.post("/download")
async def download_post(
    project_type: str = Form(...),
    scenario: str = Form(...),
):
    """Generate Excel export (POST with form data)."""
    return await _download_impl(project_type, scenario)

async def _download_impl(project_type: str, scenario: str):
    """Common Excel generation logic."""
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

@app.get("/health")
async def health():
    """Simple health check."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765)