from fastapi import APIRouter, HTTPException
from app.api.schemas import RunRequest, RunResponse, KPIs
from app.api.project_runner import run_project
from app.input_schema import ProjectInputsSchema, ValidateRequest, ValidateResponse
from app.input_adapter import build_projectinputs
from pydantic import ValidationError

router = APIRouter()

SUPPORTED_PROJECT_TYPES = {"Solar", "Wind", "BESS", "Solar+BESS", "Wind+BESS", "Portfolio"}
SUPPORTED_SCENARIOS = {"Base", "Downside", "Upside"}
SUPPORTED_PERIOD_VIEWS = {"Semiannual", "Annual"}


@router.get("/project-types")
async def get_project_types():
    return {"project_types": list(SUPPORTED_PROJECT_TYPES)}


@router.get("/scenarios")
async def get_scenarios():
    return {"scenarios": list(SUPPORTED_SCENARIOS)}


@router.post("/run")
async def post_run(request: RunRequest):
    if request.project_type not in SUPPORTED_PROJECT_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported project_type: {request.project_type}")
    if request.scenario not in SUPPORTED_SCENARIOS:
        raise HTTPException(status_code=400, detail=f"Unsupported scenario: {request.scenario}")
    if request.period_view not in SUPPORTED_PERIOD_VIEWS:
        raise HTTPException(status_code=400, detail=f"Unsupported period_view: {request.period_view}")

    # BESS/Hybrid/Portfolio guardrails
    if request.project_type in {"BESS", "Solar+BESS", "Wind+BESS"}:
        raise HTTPException(status_code=501, detail=f"{request.project_type} not yet supported via API")
    if request.project_type == "Portfolio":
        raise HTTPException(status_code=501, detail="Portfolio not yet supported via API")

    # ── Enforce project_type / scenario consistency before entering try block ──
    # (so HTTPException is not swallowed by the generic Exception catcher)
    if request.inputs is not None:
        inputs_dict = request.inputs  # dict from Pydantic
        if inputs_dict.get('project_type') is not None and inputs_dict['project_type'] != request.project_type:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"inputs.project_type '{inputs_dict['project_type']}' "
                    f"does not match request.project_type '{request.project_type}'"
                ),
            )
        if inputs_dict.get('scenario') is not None and inputs_dict['scenario'] != request.scenario:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"inputs.scenario '{inputs_dict['scenario']}' "
                    f"does not match request.scenario '{request.scenario}'"
                ),
            )

    try:
        project_inputs_override = None
        if request.inputs is not None:
            schema = ProjectInputsSchema(**request.inputs)
            project_inputs_override = build_projectinputs(schema)

        result = run_project(request.project_type, request.scenario,
                             request.period_view,
                             project_inputs_override=project_inputs_override)
        return result
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate", response_model=ValidateResponse)
async def post_validate(request: ValidateRequest):
    """Validate custom project inputs without running the model."""
    # Pydantic validation already ran on parse; we just return success
    return ValidateResponse(valid=True, errors=[])