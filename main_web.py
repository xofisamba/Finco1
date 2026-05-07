"""HTMX prototype web server for FincoGPT.

Run: python3 main_web.py
Access: http://localhost:8765
"""
from fastapi import FastAPI, Request, Form
from starlette.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

from app.api.project_runner import run_project
from app.input_schema import ProjectInputsSchema
from app.input_adapter import build_projectinputs

app = FastAPI(title="FincoGPT HTMX Prototype")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return HTMLResponse(templates.get_template("index.html").render())


@app.post("/validate")
async def validate(request: Request,
                   project_type: str = Form(...),
                   scenario: str = Form(...),
                   tariff_eur_mwh: float = Form(None),
                   p50_hours: float = Form(None),
                   degradation_pct: float = Form(None),
                   total_capex_keur: float = Form(None),
                   opex_y1_keur: float = Form(None),
                   gearing_pct: float = Form(None)):
    try:
        inputs = {}
        if tariff_eur_mwh:
            inputs.setdefault("revenue", {})["tariff_eur_mwh"] = tariff_eur_mwh
        if p50_hours:
            inputs.setdefault("revenue", {})["p50_hours"] = p50_hours
        if degradation_pct:
            inputs.setdefault("revenue", {})["degradation_pct"] = degradation_pct
        if total_capex_keur:
            inputs.setdefault("capex", {})["total_capex_keur"] = total_capex_keur
        if opex_y1_keur:
            inputs.setdefault("opex", {})["opex_y1_keur"] = opex_y1_keur
        if gearing_pct:
            inputs.setdefault("debt", {})["gearing_pct"] = gearing_pct

        if inputs:
            schema = ProjectInputsSchema(project_type=project_type, **inputs)
            proj = build_projectinputs(schema)
            result = run_project(project_type, scenario, project_inputs_override=proj)
        else:
            result = run_project(project_type, scenario)

        kpis = result.get("kpis", {})
        return HTMLResponse(templates.get_template("partials/kpis.html").render(
            kpis=kpis, error=None
        ))
    except Exception as e:
        return HTMLResponse(templates.get_template("partials/kpis.html").render(
            kpis={}, error=str(e)
        ))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8765)
