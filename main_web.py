import json
"""HTMX internal demo web interface for Finco1 model."""
import os
import re
from datetime import datetime as dt

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
from app.project_factories import create_default_oborovo, create_default_tuho_wind1
from app.project_factories import create_default_solar_project, create_default_wind_project

# Import schema and adapter for custom inputs
from app.input_schema import ProjectInputsSchema, RevenueInput, CapexInput, OpexInput, DebtInput
from app.input_adapter import SnapshotInputError, build_projectinputs, build_projectinputs_from_snapshot

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
    _now_utc,
    bind_workspace_to_scenario,
    archive_scenario,
    build_export_lineage,
    compare_scenarios,
    create_project_record,
    count_runs,
    delete_run,
    discard_workspace_draft,
    duplicate_scenario,
    get_project_by_code,
    get_project_record,
    get_run,
    get_scenario,
    get_scenario_history,
    get_workspace_state,
    list_exports,
    list_baseline_records,
    list_project_records,
    seed_baseline_projects_if_needed,
    list_runs,
    list_scenarios,
    record_workspace_runtime,
    record_export,
    rename_scenario,
    runtime_guard_for_snapshot,
    save_project,
    save_run,
    save_scenario,
    save_workspace_state,
    snapshots_equal,
    update_project_record,
    update_scenario_last_run_summary,
)
from app.persistence.provenance import build_replay_metadata, utc_now_iso
from app.ui.project_context import build_project_context_for_record, get_project_context
from app.ui.runtime_summary import runtime_summary_to_dict, NOT_AVAILABLE
from app.export.runtime_summary import build_runtime_summary_csv, build_runtime_summary_rows
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
FACTORY_TEMPLATE_OPTIONS = [
    {
        "project_code": "tuho",
        "label": "TUHO Wind 1",
        "meta": "35 MW · Croatia",
        "project_type": "Wind",
        "template_source": "TUHO",
    },
    {
        "project_code": "oborovo",
        "label": "Oborovo Solar PV",
        "meta": "75.26 MW · Croatia",
        "project_type": "Solar",
        "template_source": "Oborovo",
    },
]
NEW_PROJECT_TEMPLATE_OPTIONS = [
    {"value": "generic_wind", "label": "Blank / Generic Wind", "project_type": "Wind"},
    {"value": "generic_solar", "label": "Blank / Generic Solar", "project_type": "Solar"},
    {"value": "tuho", "label": "TUHO template", "project_type": "Wind"},
    {"value": "oborovo", "label": "Oborovo template", "project_type": "Solar"},
]


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


def _slugify_project_code(project_name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", (project_name or "").strip().lower()).strip("-")
    return base or "project"


def _canonical_project_type(project_type: str | None) -> str:
    return "Solar" if (project_type or "").strip().lower() == "solar" else "Wind"


def _normalize_template_source(template_source: str | None, project_type: str | None) -> str:
    source = (template_source or "").strip().lower()
    if source in {"tuho", "oborovo", "generic_wind", "generic_solar"}:
        return source
    return "generic_solar" if _canonical_project_type(project_type) == "Solar" else "generic_wind"


def _template_source_label(template_source: str | None) -> str:
    mapping = {
        "tuho": "TUHO",
        "oborovo": "Oborovo",
        "generic_wind": "Generic Wind",
        "generic_solar": "Generic Solar",
        "none": "none",
    }
    return mapping.get((template_source or "").strip().lower(), "none")


def _project_identity_from_template_source(template_source: str, fallback_project_type: str | None = None) -> tuple[str, str]:
    source = _normalize_template_source(template_source, fallback_project_type)
    if source == "oborovo":
        return "oborovo", "Oborovo Solar PV"
    if source == "tuho":
        return "tuho", "TUHO Wind 1"
    if source == "generic_solar":
        return "generic_solar", "Generic Solar Project"
    return "generic_wind", "Generic Wind Project"


def _collect_form_snapshot(form) -> dict:
    fields = [
        "active_project",
        "project_name",
        "project_type",
        "template_source",
        "country_market",
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


def _project_baseline_snapshot(project_type: str, template_source: str) -> dict:
    canonical_type = _canonical_project_type(project_type)
    normalized_source = _normalize_template_source(template_source, canonical_type)
    identity_code, _ = _project_identity_from_template_source(normalized_source, canonical_type)
    baseline = {
        "active_project": "",
        "project_name": "",
        "project_type": canonical_type,
        "project_origin": "factory_template",
        "template_source": normalized_source,
        "country_market": "",
        "scenario": "Base",
        "capacity_mw": "",
        "tariff_eur_mwh": "",
        "p50_hours": "",
        "total_capex_keur": "",
        "opex_y1_keur": "",
        "gearing_pct": "",
        "target_dscr": "",
        "interest_rate_pct": "",
        "tenor_years": "",
        "cod_date": "",
        "construction_months": "",
        "horizon_years": "",
        "capacity_factor": "",
        "ppa_term_years": "",
    }

    if normalized_source == "tuho":
        project_inputs = create_default_tuho_wind1()
        baseline.update(
            {
                "active_project": "tuho",
                "project_name": project_inputs.info.name,
                "project_type": "Wind",
                "project_origin": "factory_template",
                "template_source": "tuho",
                "country_market": project_inputs.info.country_iso,
                "capacity_mw": str(project_inputs.technical.capacity_mw),
                "tariff_eur_mwh": str(project_inputs.revenue.ppa_base_tariff),
                "p50_hours": str(project_inputs.technical.operating_hours_p50),
                "total_capex_keur": str(project_inputs.capex.total_capex),
                "opex_y1_keur": str(sum(item.y1_amount_keur for item in project_inputs.opex)),
                "target_dscr": str(project_inputs.financing.target_dscr),
                "interest_rate_pct": str(project_inputs.financing.base_rate + project_inputs.financing.margin_bps / 10_000),
                "tenor_years": str(project_inputs.financing.senior_tenor_years),
                "cod_date": str(project_inputs.info.cod_date),
                "construction_months": str(project_inputs.info.construction_months),
                "horizon_years": str(project_inputs.info.horizon_years),
                "capacity_factor": f"{(project_inputs.technical.operating_hours_p50 / 8760) * 100:.2f}",
                "ppa_term_years": str(int(project_inputs.revenue.ppa_term_years)),
            }
        )
        return baseline

    if normalized_source == "oborovo":
        project_inputs = create_default_oborovo()
        baseline.update(
            {
                "active_project": "oborovo",
                "project_name": project_inputs.info.name,
                "project_type": "Solar",
                "project_origin": "factory_template",
                "template_source": "oborovo",
                "country_market": project_inputs.info.country_iso,
                "capacity_mw": str(project_inputs.technical.capacity_mw),
                "tariff_eur_mwh": str(project_inputs.revenue.ppa_base_tariff),
                "p50_hours": str(project_inputs.technical.operating_hours_p50),
                "total_capex_keur": str(project_inputs.capex.total_capex),
                "opex_y1_keur": str(sum(item.y1_amount_keur for item in project_inputs.opex)),
                "gearing_pct": str((getattr(project_inputs.financing, "gearing_ratio", 0.0) or 0.0) * 100),
                "target_dscr": str(project_inputs.financing.target_dscr),
                "interest_rate_pct": str(project_inputs.financing.base_rate + project_inputs.financing.margin_bps / 10_000),
                "tenor_years": str(project_inputs.financing.senior_tenor_years),
                "cod_date": str(project_inputs.info.cod_date),
                "construction_months": str(project_inputs.info.construction_months),
                "horizon_years": str(project_inputs.info.horizon_years),
                "capacity_factor": f"{(project_inputs.technical.operating_hours_p50 / 8760) * 100:.2f}",
                "ppa_term_years": str(int(project_inputs.revenue.ppa_term_years)),
            }
        )
        return baseline

    if normalized_source == "generic_solar":
        project_inputs = create_default_solar_project()
    else:
        project_inputs = create_default_wind_project()
    baseline.update(
        {
            "active_project": identity_code,
            "project_name": project_inputs.info.name,
            "project_type": canonical_type,
            "project_origin": "factory_template",
            "template_source": normalized_source,
            "country_market": project_inputs.info.country_iso,
            "capacity_mw": str(project_inputs.technical.capacity_mw),
            "tariff_eur_mwh": str(project_inputs.revenue.ppa_base_tariff),
            "p50_hours": str(project_inputs.technical.operating_hours_p50),
            "total_capex_keur": str(project_inputs.capex.total_capex),
            "opex_y1_keur": str(sum(item.y1_amount_keur for item in project_inputs.opex)),
            "gearing_pct": str((getattr(project_inputs.financing, "gearing_ratio", 0.0) or 0.0) * 100),
            "target_dscr": str(project_inputs.financing.target_dscr),
            "interest_rate_pct": str(project_inputs.financing.base_rate + project_inputs.financing.margin_bps / 10_000),
            "tenor_years": str(project_inputs.financing.senior_tenor_years),
            "cod_date": str(project_inputs.info.cod_date),
            "construction_months": str(project_inputs.info.construction_months),
            "horizon_years": str(project_inputs.info.horizon_years),
            "capacity_factor": f"{(project_inputs.technical.operating_hours_p50 / 8760) * 100:.2f}",
            "ppa_term_years": str(int(project_inputs.revenue.ppa_term_years)),
        }
    )
    return baseline


def _project_inputs_for_code(project_code: str):
    code = (project_code or "tuho").strip().lower()
    if code == "generic_solar":
        return create_default_solar_project()
    if code == "generic_wind":
        return create_default_wind_project()
    if code == "oborovo":
        return create_default_oborovo()
    return create_default_tuho_wind1()


def _default_workspace_snapshot(project_code: str) -> dict:
    code = (project_code or "tuho").strip().lower()
    project_type = "Solar" if code in {"oborovo", "generic_solar"} else "Wind"
    return _project_baseline_snapshot(project_type, code)


def _project_record_to_context(project_record, baseline_snapshot: dict | None = None):
    return build_project_context_for_record(
        project_code=project_record.project_code,
        project_name=project_record.project_name,
        project_type=project_record.project_type,
        project_origin=project_record.project_origin,
        template_source=project_record.template_source or project_record.source_project_template,
        baseline_snapshot=baseline_snapshot,
    )


def _submitted_new_project_defaults() -> dict[str, str]:
    return {
        "project_name": "",
        "project_type": "Wind",
        "template_source": "generic_wind",
        "country_market": "Croatia",
        "capacity_mw": "",
        "cod_date": "",
        "construction_months": "",
        "horizon_years": "",
        "tariff_eur_mwh": "",
        "ppa_term_years": "",
        "p50_hours": "",
        "opex_y1_keur": "",
        "total_capex_keur": "",
        "gearing_pct": "",
        "interest_rate_pct": "",
        "tenor_years": "",
        "target_dscr": "1.20",
    }


def _coerce_form_text(value: str | None) -> str:
    return (value or "").strip()


def _coerce_form_float(value: str | None) -> float | None:
    text = _coerce_form_text(value)
    if not text:
        return None
    return float(text)


def _coerce_form_int(value: str | None) -> int | None:
    text = _coerce_form_text(value)
    if not text:
        return None
    return int(float(text))


def _format_snapshot_number(value: float | int | None, decimals: int | None = None) -> str:
    if value is None:
        return ""
    if decimals is not None:
        return f"{float(value):.{decimals}f}"
    if isinstance(value, int) or float(value).is_integer():
        return str(int(float(value)))
    return str(float(value))


def _new_project_validation_error_context(submitted: dict[str, str], validation_errors: list[str]) -> dict[str, object]:
    return {
        "project_types": PROJECT_TYPES,
        "template_options": NEW_PROJECT_TEMPLATE_OPTIONS,
        "validation_errors": validation_errors,
        "submitted": submitted,
    }


def _validate_new_project_payload(submitted: dict[str, str]) -> list[str]:
    errors: list[str] = []
    project_name = _coerce_form_text(submitted.get("project_name"))
    project_type = submitted.get("project_type", "")
    country_market = _coerce_form_text(submitted.get("country_market"))

    if not project_name:
        errors.append("Project name is required.")
    if project_type not in PROJECT_TYPES:
        errors.append(f"Project type must be one of {PROJECT_TYPES}.")
    if not country_market:
        errors.append("Country or market is required.")

    def require_float(
        field_name: str,
        label: str,
        *,
        min_value: float | None = None,
        max_value: float | None = None,
        strictly_positive: bool = False,
    ) -> float | None:
        text = _coerce_form_text(submitted.get(field_name))
        if not text:
            errors.append(f"{label} is required.")
            return None
        try:
            value = float(text)
        except ValueError:
            errors.append(f"{label} must be a number.")
            return None
        if strictly_positive and value <= 0:
            errors.append(f"{label} must be > 0.")
        elif min_value is not None and value < min_value:
            errors.append(f"{label} must be >= {min_value}.")
        if max_value is not None and value > max_value:
            errors.append(f"{label} must be <= {max_value}.")
        return value

    def require_int(
        field_name: str,
        label: str,
        *,
        min_value: int | None = None,
        max_value: int | None = None,
        strictly_positive: bool = False,
    ) -> int | None:
        text = _coerce_form_text(submitted.get(field_name))
        if not text:
            errors.append(f"{label} is required.")
            return None
        try:
            value = int(float(text))
        except ValueError:
            errors.append(f"{label} must be a whole number.")
            return None
        if strictly_positive and value <= 0:
            errors.append(f"{label} must be > 0.")
        elif min_value is not None and value < min_value:
            errors.append(f"{label} must be >= {min_value}.")
        if max_value is not None and value > max_value:
            errors.append(f"{label} must be <= {max_value}.")
        return value

    if not _coerce_form_text(submitted.get("cod_date")):
        errors.append("COD date is required.")

    capacity_mw = require_float("capacity_mw", "Capacity (MW)", strictly_positive=True)
    tariff = require_float("tariff_eur_mwh", "Tariff (EUR/MWh)", min_value=0)
    p50_hours = require_float("p50_hours", "P50 hours", strictly_positive=True)
    opex_y1 = require_float("opex_y1_keur", "OPEX Y1 (kEUR)", min_value=0)
    total_capex = require_float("total_capex_keur", "Total CAPEX (kEUR)", strictly_positive=True)
    gearing_pct = require_float("gearing_pct", "Gearing (%)", min_value=0, max_value=100)
    interest_rate_pct = require_float("interest_rate_pct", "Interest rate (%)", min_value=0)
    tenor_years = require_int("tenor_years", "Tenor (years)", strictly_positive=True)
    target_dscr = require_float("target_dscr", "Target DSCR", strictly_positive=True)
    construction_months = require_int("construction_months", "Construction months", strictly_positive=True)
    horizon_years = require_int("horizon_years", "Horizon years", strictly_positive=True)
    ppa_term_years = require_int("ppa_term_years", "PPA term years", strictly_positive=True)

    if (
        ppa_term_years is not None
        and horizon_years is not None
        and ppa_term_years > horizon_years
    ):
        errors.append("PPA term years should be less than or equal to horizon years.")

    return errors


def _apply_new_project_required_inputs(
    baseline_snapshot: dict[str, str],
    *,
    project_name: str,
    project_code: str,
    project_type: str,
    project_origin: str,
    template_source: str,
    submitted: dict[str, str],
) -> dict[str, str]:
    snapshot = dict(baseline_snapshot)
    snapshot.update(
        {
            "active_project": project_code,
            "project_name": project_name,
            "project_type": project_type,
            "project_origin": project_origin,
            "template_source": template_source,
            "country_market": _coerce_form_text(submitted.get("country_market")),
            "capacity_mw": _format_snapshot_number(_coerce_form_float(submitted.get("capacity_mw"))),
            "cod_date": _coerce_form_text(submitted.get("cod_date")),
            "construction_months": _format_snapshot_number(_coerce_form_int(submitted.get("construction_months"))),
            "horizon_years": _format_snapshot_number(_coerce_form_int(submitted.get("horizon_years"))),
            "tariff_eur_mwh": _format_snapshot_number(_coerce_form_float(submitted.get("tariff_eur_mwh"))),
            "ppa_term_years": _format_snapshot_number(_coerce_form_int(submitted.get("ppa_term_years"))),
            "p50_hours": _format_snapshot_number(_coerce_form_float(submitted.get("p50_hours"))),
            "opex_y1_keur": _format_snapshot_number(_coerce_form_float(submitted.get("opex_y1_keur"))),
            "total_capex_keur": _format_snapshot_number(_coerce_form_float(submitted.get("total_capex_keur"))),
            "gearing_pct": _format_snapshot_number(_coerce_form_float(submitted.get("gearing_pct"))),
            "interest_rate_pct": _format_snapshot_number(_coerce_form_float(submitted.get("interest_rate_pct"))),
            "tenor_years": _format_snapshot_number(_coerce_form_int(submitted.get("tenor_years"))),
            "target_dscr": _format_snapshot_number(_coerce_form_float(submitted.get("target_dscr")), decimals=2),
        }
    )
    return snapshot


def _project_persistence_metadata(project_ctx=None, form_snapshot: dict | None = None, project_record=None) -> tuple[str, str]:
    if project_record is not None:
        return project_record.project_code, project_record.project_name
    if project_ctx is not None:
        return project_ctx.id, project_ctx.name
    active_project = (form_snapshot or {}).get("active_project", "").strip().lower()
    if active_project:
        project_code, project_name = _project_identity_from_template_source(active_project, (form_snapshot or {}).get("project_type"))
        return project_code, project_name
    project_type = _canonical_project_type((form_snapshot or {}).get("project_type"))
    default_source = _normalize_template_source((form_snapshot or {}).get("template_source"), project_type)
    project_code, project_name = _project_identity_from_template_source(default_source, project_type)
    return project_code, project_name


def _workspace_state_meta(workspace_state) -> dict:
    if workspace_state is None:
        return {
            "dirty": False,
            "dirty_label": "Clean saved state",
            "active_scenario_id": "",
            "active_scenario_name": "",
            "last_runtime_origin": "",
            "last_runtime_origin_label": "No runtime bound yet",
            "last_runtime_snapshot_id": "",
        }
    runtime_origin = workspace_state.last_runtime_origin or ""
    if runtime_origin == "saved_state":
        runtime_label = "Runtime bound to saved scenario snapshot"
    elif runtime_origin == "workspace_base":
        runtime_label = "Runtime bound to clean workspace base"
    elif runtime_origin == "preview_only":
        runtime_label = "Preview only; runtime not executed"
    else:
        runtime_label = "No runtime bound yet"
    if workspace_state.dirty and workspace_state.last_runtime_snapshot_id:
        runtime_label = f"{runtime_label} (older than current draft)"
    return {
        "dirty": bool(workspace_state.dirty),
        "dirty_label": "Unsaved edits" if workspace_state.dirty else "Clean saved state",
        "active_scenario_id": workspace_state.active_scenario_id or "",
        "active_scenario_name": workspace_state.active_scenario_name or "",
        "last_runtime_origin": runtime_origin,
        "last_runtime_origin_label": runtime_label,
        "last_runtime_snapshot_id": workspace_state.last_runtime_snapshot_id or "",
    }


def _format_ui_timestamp(value) -> str:
    if value is None:
        return "unavailable"
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d %H:%M")
    text = str(value).strip()
    return text or "unavailable"


def _build_export_lineage_ui_context(project_record, workspace_state, export_lineage: list[dict[str, object]]) -> dict[str, object]:
    workspace_meta = _workspace_state_meta(workspace_state)
    project_label = project_record.project_name if project_record else "Workspace Project"
    project_code = project_record.project_code.upper() if project_record else "GENERAL"
    runtime_snapshot_id = workspace_state.last_runtime_snapshot_id if workspace_state else ""
    runtime_generated_at = _format_ui_timestamp(workspace_state.last_runtime_at if workspace_state else None)
    scenario_revision = _format_ui_timestamp(workspace_state.updated_at if workspace_state else None)
    action_note = (
        "Unsaved draft edits are active. Exports remain descriptive only, and runtime-backed artifacts stay tied to the last clean backend snapshot until you save and run again."
        if workspace_meta["dirty"]
        else "Draft and saved state are aligned. Runtime-backed exports reflect the last clean backend snapshot shown in the runtime summary."
    )
    current_context = {
        "project_label": project_label,
        "project_code": project_code,
        "active_scenario_name": workspace_state.active_scenario_name if workspace_state and workspace_state.active_scenario_name else "Workspace Base",
        "active_scenario_id": workspace_state.active_scenario_id if workspace_state and workspace_state.active_scenario_id else "not_applicable",
        "scenario_revision": scenario_revision,
        "runtime_snapshot_id": runtime_snapshot_id or "unavailable",
        "runtime_generated_at": runtime_generated_at,
        "runtime_origin_label": workspace_meta["last_runtime_origin_label"],
        "dirty": workspace_meta["dirty"],
        "dirty_label": workspace_meta["dirty_label"],
        "governance_summary": "G20 remains BLOCKED; R99/R102 remain NOT APPROVED.",
        "action_note": action_note,
    }
    action_cards = [
        {
            "artifact_name": "Values-only Excel export",
            "artifact_type": "excel_model_export",
            "href": "/download",
            "represents": "Submitted form values plus descriptive provenance and reviewer notes.",
            "authority_note": "Descriptive only. This workbook is backend-authored and does not become the calculation engine.",
            "availability_note": (
                "Dirty draft is allowed here because the export reflects submitted workbook values, not a hidden runtime promotion."
                if workspace_meta["dirty"]
                else "Available from the current submitted form state."
            ),
        },
        {
            "artifact_name": "Runtime summary CSV",
            "artifact_type": "runtime_summary_csv",
            "href": f"/exports/runtime-summary.csv?project={project_record.project_code if project_record else 'tuho'}",
            "represents": "Backend runtime metrics and provenance for the active project.",
            "authority_note": "Descriptive only. Reviewer should treat it as a record of backend runtime output, not as a live browser calculation.",
            "availability_note": (
                "Current draft is newer than the last runtime snapshot. Save and run again if you need export lineage to match the current draft."
                if workspace_meta["dirty"]
                else "Uses the last clean backend runtime context for the active project."
            ),
        },
        {
            "artifact_name": "Institutional workbook",
            "artifact_type": "institutional_workbook",
            "href": f"/exports/institutional-workbook.xlsx?project={project_record.project_code if project_record else 'tuho'}",
            "represents": "Reviewer-facing workbook with runtime summary, provenance, cover notes, and governance context.",
            "authority_note": "Descriptive only. Numeric sheets remain tied to backend runtime/export behavior and do not override runtime authority.",
            "availability_note": (
                "Current draft is newer than the last runtime snapshot. Save and run again before sharing if the reviewer needs the latest draft reflected in runtime-backed sections."
                if workspace_meta["dirty"]
                else "Uses the last clean backend runtime context for the active project."
            ),
        },
    ]
    recent_exports = []
    for item in export_lineage:
        replay_metadata = item.get("replay_metadata", {}) if isinstance(item, dict) else {}
        recent_exports.append(
            {
                "artifact_name": item.get("artifact_name", "Export artifact"),
                "export_type": item.get("export_type", "unknown"),
                "scenario_name": item.get("scenario_name", "Workspace export"),
                "created_at": _format_ui_timestamp(item.get("created_at")),
                "scenario_id": replay_metadata.get("scenario_id") or "not_applicable",
                "scenario_revision": replay_metadata.get("scenario_revision") or "unavailable",
                "runtime_snapshot_id": replay_metadata.get("runtime_snapshot_id") or "unavailable",
                "runtime_origin": replay_metadata.get("runtime_origin") or "unavailable",
                "runtime_generated_at": replay_metadata.get("runtime_timestamp") or "unavailable",
                "export_generated_at": replay_metadata.get("export_timestamp") or _format_ui_timestamp(item.get("created_at")),
                "branch_name": replay_metadata.get("branch_name") or "unavailable",
                "commit_sha": replay_metadata.get("commit_sha") or "unavailable",
                "template_origin": replay_metadata.get("template_origin") or "unavailable",
                "runtime_flag_count": replay_metadata.get("runtime_flag_count") or "unavailable",
                "governance_summary": (
                    f"{item.get('governance_state', {}).get('g20_status', 'BLOCKED')} / "
                    f"{item.get('governance_state', {}).get('r99_r102_status', 'NOT APPROVED')}"
                ),
            }
        )
    return {
        "current_context": current_context,
        "action_cards": action_cards,
        "recent_exports": recent_exports,
    }


def _format_compare_value(value) -> str:
    if value in (None, "", "NOT_AVAILABLE"):
        return "pending / unavailable"
    return str(value)


def _format_compare_delta(value) -> str:
    if value is None:
        return "not_applicable"
    return str(value)


def _build_compare_ui_context(compare_result: dict, workspace_state) -> dict:
    workspace_meta = _workspace_state_meta(workspace_state)
    left = compare_result["left"]
    right = compare_result["right"]
    compare_metrics = []
    for row in compare_result["metrics"]:
        compare_metrics.append(
            {
                "metric": row["metric"],
                "left_value": _format_compare_value(row["left_value"]),
                "right_value": _format_compare_value(row["right_value"]),
                "delta": _format_compare_delta(row["delta"]),
            }
        )

    left_replay = dict(left.replay_metadata or {})
    right_replay = dict(right.replay_metadata or {})
    dirty_note = (
        "Current workspace draft has unsaved edits. Those browser-side edits are not part of this comparison; the compare panel only reflects saved scenario snapshots and saved runtime summaries."
        if workspace_meta["dirty"]
        else "Current workspace draft is aligned to the saved boundary, so this comparison is reading saved scenario snapshots without hidden draft drift."
    )
    return {
        "left": left,
        "right": right,
        "metrics": compare_metrics,
        "governance_rows": compare_result["governance_rows"],
        "compare_generated_at": utc_now_iso(),
        "dirty_note": dirty_note,
        "left_context": {
            "scenario_timestamp": _format_ui_timestamp(left.updated_at),
            "runtime_timestamp": left_replay.get("runtime_timestamp") or "unavailable",
            "runtime_snapshot_id": left_replay.get("runtime_snapshot_id") or "unavailable",
            "runtime_origin": left_replay.get("runtime_origin") or "not_applicable",
            "source_label": "saved scenario snapshot with saved runtime summary",
        },
        "right_context": {
            "scenario_timestamp": _format_ui_timestamp(right.updated_at),
            "runtime_timestamp": right_replay.get("runtime_timestamp") or "unavailable",
            "runtime_snapshot_id": right_replay.get("runtime_snapshot_id") or "unavailable",
            "runtime_origin": right_replay.get("runtime_origin") or "not_applicable",
            "source_label": "saved scenario snapshot with saved runtime summary",
        },
        "workspace_dirty": workspace_meta["dirty"],
        "workspace_runtime_origin_label": workspace_meta["last_runtime_origin_label"],
        "governance_summary": "G20 remains BLOCKED. R99/R102 remain NOT APPROVED. Accepted conventions remain explanatory only.",
        "missing_metric_note": "Pending, unavailable, and not_applicable markers are intentional. They do not mean zero unless the source value is actually zero.",
    }


def _replay_metadata_for_project(
    project_code: str,
    *,
    export_type: str | None = None,
    workbook_type: str | None = None,
    export_timestamp: str | None = None,
    runtime_timestamp: str | None = None,
    project_id: str | None = None,
    scenario_id: str | None = None,
    scenario_name: str | None = None,
    scenario_revision: str | None = None,
    runtime_snapshot_id: str | None = None,
    runtime_origin: str | None = None,
    artifact_name: str | None = None,
    project_inputs_override=None,
    template_origin_override: str | None = None,
    baseline_source: bool | None = None,
) -> dict:
    project_inputs = project_inputs_override or _project_inputs_for_code(project_code)
    governance_state = _governance_snapshot(project_code)
    replay_metadata = build_replay_metadata(
        project_key=project_code,
        project_inputs=project_inputs,
        governance_state=governance_state,
        project_id=project_id,
        scenario_id=scenario_id,
        scenario_name=scenario_name,
        scenario_revision=scenario_revision,
        runtime_timestamp=runtime_timestamp,
        export_timestamp=export_timestamp,
        runtime_snapshot_id=runtime_snapshot_id,
        runtime_origin=runtime_origin,
        artifact_name=artifact_name,
        export_type=export_type,
        workbook_type=workbook_type,
        active_project=project_code,
    )
    if template_origin_override:
        replay_metadata["template_origin"] = template_origin_override
    if baseline_source is not None:
        replay_metadata["baseline_source"] = baseline_source
    return replay_metadata


def _user_project_selector_items(user) -> list[dict[str, str]]:
    items = []
    for record in list_project_records(user_id=user.user_id):
        if record.project_origin != "user_created":
            continue
        items.append(
            {
                "project_code": record.project_code,
                "label": record.project_name,
                "meta": f"{record.project_type or 'Unknown'} · {_template_source_label(record.template_source)} seed",
            }
        )
    return items


def _resolve_project_record(user, project_selection: str | None, form_snapshot: dict | None = None):
    selection = (project_selection or "").strip().lower()
    if selection:
        user_project = get_project_record(user_id=user.user_id, project_code=selection)
        if user_project is not None:
            return user_project

    if selection in {"tuho", "oborovo", "generic_wind", "generic_solar"}:
        project_code = selection
        project_name = _project_identity_from_template_source(selection)[1]
        project_type = "Solar" if selection in {"oborovo", "generic_solar"} else "Wind"
        template_source = selection
    else:
        project_code, project_name = _project_persistence_metadata(None, form_snapshot)
        project_type = _canonical_project_type((form_snapshot or {}).get("project_type"))
        template_source = _normalize_template_source(project_code, project_type)

    return save_project(
        user_id=user.user_id,
        project_code=project_code,
        project_name=project_name,
        project_type=project_type,
        project_origin="factory_template",
        source_project_template=template_source,
        template_source=template_source,
        baseline_snapshot=_default_workspace_snapshot(project_code),
        governance_state=_governance_snapshot(project_code),
        last_run_summary={},
        replay_metadata=_replay_metadata_for_project(
            project_code,
            project_id=None,
            export_type="workspace_project_state",
        ),
    )


def _ensure_workspace_for_project(user, project_record):
    workspace_state = get_workspace_state(user.user_id, project_record.project_id)
    if workspace_state is None:
        base_snapshot = project_record.baseline_snapshot or _default_workspace_snapshot(project_record.project_code)
        base_snapshot = dict(base_snapshot)
        base_snapshot["active_project"] = project_record.project_code
        base_snapshot["project_type"] = project_record.project_type or base_snapshot.get("project_type") or "Wind"
        workspace_state = save_workspace_state(
            user_id=user.user_id,
            project_id=project_record.project_id,
            project_code=project_record.project_code,
            draft_snapshot=base_snapshot,
            saved_snapshot=base_snapshot,
            dirty=False,
            governance_state=_governance_snapshot(project_record.project_code),
            replay_metadata=_replay_metadata_for_project(
                project_record.project_code,
                project_id=project_record.project_id,
                export_type="workspace_draft_state",
            ),
        )
    return workspace_state


def _project_workspace_from_snapshot(user, snapshot: dict):
    project_record = _resolve_project_record(user, snapshot.get("active_project"), snapshot)
    workspace_state = _ensure_workspace_for_project(user, project_record)
    return project_record, workspace_state


def _clean_user_project_runtime_snapshot(project_record, workspace_state, runtime_origin: str) -> dict:
    """Return the clean saved source used for user-created project runtime."""
    if runtime_origin == "saved_state" and workspace_state.saved_snapshot:
        source = dict(workspace_state.saved_snapshot)
    else:
        source = dict(project_record.baseline_snapshot or workspace_state.saved_snapshot or {})

    source.setdefault("project_name", project_record.project_name)
    source.setdefault("project_type", project_record.project_type)
    source.setdefault("project_origin", project_record.project_origin)
    source.setdefault("template_source", project_record.template_source or project_record.source_project_template)
    source.setdefault("active_project", project_record.project_code.lower())
    return source


def _current_project_workspace(user, project_record):
    workspace_state = _ensure_workspace_for_project(user, project_record)
    scenarios = list_scenarios(user.user_id, project_id=project_record.project_id, include_archived=False, limit=12)
    history = get_scenario_history(user.user_id, project_id=project_record.project_id, limit=20)
    exports = list_exports(user.user_id, project_id=project_record.project_id, limit=8)
    export_lineage = build_export_lineage(user.user_id, project_id=project_record.project_id, limit=8)
    scenario_summary_cards = []
    export_counts: dict[str, int] = {}
    for entry in export_lineage:
        export_counts[entry["scenario_name"]] = export_counts.get(entry["scenario_name"], 0) + 1
    for item in scenarios:
        summary = item.last_run_summary or {}
        scenario_summary_cards.append(
            {
                "scenario_id": item.scenario_id,
                "scenario_name": item.scenario_name,
                "project_code": item.project_code,
                "updated_at": item.updated_at,
                "copied_from_scenario_id": item.copied_from_scenario_id,
                "project_irr": summary.get("project_irr"),
                "equity_irr": summary.get("equity_irr"),
                "avg_dscr": summary.get("avg_dscr"),
                "export_count": export_counts.get(item.scenario_name, 0),
                "governance_state": item.governance_state,
            }
        )
    return project_record, workspace_state, scenarios, history, exports, export_lineage, scenario_summary_cards


def _render_scenario_workspace(
    request: Request,
    user,
    project_record,
    workspace_state,
    scenarios,
    history,
    exports,
    export_lineage,
    scenario_summary_cards,
    message: str | None = None,
    compare_result: dict | None = None,
):
    return templates.TemplateResponse(
        request=request,
        name="partials/scenario_workspace.html",
        context={
            "user": user,
            "project_record": project_record,
            "workspace_state": workspace_state,
            "workspace_state_meta": _workspace_state_meta(workspace_state),
            "scenario_records": scenarios,
            "scenario_history": history,
            "export_records": exports,
            "export_lineage": export_lineage,
            "export_lineage_ui": _build_export_lineage_ui_context(project_record, workspace_state, export_lineage),
            "scenario_summary_cards": scenario_summary_cards,
            "workspace_message": message,
            "compare_result": compare_result,
            "is_user_project": project_record.project_origin == "user_created",
        },
    )


def _workspace_refresh_payload(user, project_record):
    scenarios = list_scenarios(user.user_id, project_id=project_record.project_id, include_archived=False, limit=12)
    history = get_scenario_history(user.user_id, project_id=project_record.project_id, limit=20)
    exports = list_exports(user.user_id, project_id=project_record.project_id, limit=8)
    export_lineage = build_export_lineage(user.user_id, project_id=project_record.project_id, limit=8)
    export_counts = {}
    for entry in export_lineage:
        export_counts[entry["scenario_name"]] = export_counts.get(entry["scenario_name"], 0) + 1
    scenario_summary_cards = []
    for item in scenarios:
        summary = item.last_run_summary or {}
        scenario_summary_cards.append(
            {
                "scenario_id": item.scenario_id,
                "scenario_name": item.scenario_name,
                "project_code": item.project_code,
                "updated_at": item.updated_at,
                "copied_from_scenario_id": item.copied_from_scenario_id,
                "project_irr": summary.get("project_irr"),
                "equity_irr": summary.get("equity_irr"),
                "avg_dscr": summary.get("avg_dscr"),
                "export_count": export_counts.get(item.scenario_name, 0),
                "governance_state": item.governance_state,
            }
        )
    return scenarios, history, exports, export_lineage, scenario_summary_cards

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

    project_record = _resolve_project_record(user, project)
    (
        project_record,
        workspace_state,
        scenario_records,
        scenario_history,
        export_records,
        export_lineage,
        scenario_summary_cards,
    ) = _current_project_workspace(user, project_record)
    ctx = _project_record_to_context(
        project_record,
        workspace_state.draft_snapshot if workspace_state else project_record.baseline_snapshot,
    )

    # Seed baseline records if not yet present for this user
    baseline_records = seed_baseline_projects_if_needed(user.user_id)
    baseline_project_items = [
        {
            "project_code": r.project_code,
            "label": r.project_name,
            "meta": f"{r.project_type or 'Unknown'} · baseline",
            "is_readonly": r.is_readonly,
        }
        for r in list_baseline_records(user.user_id)
    ]

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "project_types": PROJECT_TYPES,
            "scenarios": SCENARIOS,
            "caveats": CAVEATS,
            "form_data": workspace_state.draft_snapshot if workspace_state else project_record.baseline_snapshot or _default_workspace_snapshot(project_record.project_code),
            "validation_errors": [],
            "success_message": None,
            "user": user,
            "project_ctx": ctx,
            "workspace_state": workspace_state,
            "workspace_state_meta": _workspace_state_meta(workspace_state),
            "active_project_code": project_record.project_code,
            "factory_template_projects": FACTORY_TEMPLATE_OPTIONS,
            "user_project_records": _user_project_selector_items(user),
            "baseline_project_records": baseline_project_items,
            "new_project_template_options": NEW_PROJECT_TEMPLATE_OPTIONS,
            "project_record": project_record,
            "scenario_records": scenario_records,
            "scenario_history": scenario_history,
            "export_records": export_records,
            "export_lineage": export_lineage,
            "export_lineage_ui": _build_export_lineage_ui_context(project_record, workspace_state, export_lineage),
            "scenario_summary_cards": scenario_summary_cards,
            "compare_result": None,
            "workspace_message": None,
            "is_user_project": project_record.project_origin == "user_created",
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
    snapshot = _collect_form_snapshot(form)
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
    project_record, workspace_state = _project_workspace_from_snapshot(user, snapshot)
    project_code = project_record.project_code
    allow_run, runtime_origin, guard_message = runtime_guard_for_snapshot(workspace_state, snapshot)
    if not allow_run:
        return templates.TemplateResponse(
            request=request,
            name="partials/errors.html",
            context={"errors": [guard_message]},
        )

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
    snapshot = _collect_form_snapshot(form)
    project_record, workspace_state = _project_workspace_from_snapshot(user, snapshot)
    project_code = project_record.project_code
    project_name = project_record.project_name
    allow_run, runtime_origin, guard_message = runtime_guard_for_snapshot(workspace_state, snapshot)
    if not allow_run:
        return templates.TemplateResponse(
            request=request,
            name="partials/errors.html",
            context={"errors": [guard_message]},
        )
    runtime_seed = _normalize_template_source(project_record.template_source or project_record.source_project_template, project_record.project_type)

    # -- Snapshot-built runtime binding for user-created projects ------------
    # Phase 17C moves user-created projects off template-seeded primary runtime
    # inputs. The dirty guard above still protects runtime from browser drafts.
    if project_record.project_origin == "user_created":
        try:
            runtime_snapshot = _clean_user_project_runtime_snapshot(project_record, workspace_state, runtime_origin)
            override = build_projectinputs_from_snapshot(runtime_snapshot)
            scenario_name = runtime_snapshot.get("scenario") or snapshot.get("scenario", "") or "Base"
            runtime_project_key = (
                "Solar"
                if (runtime_snapshot.get("project_type") or project_record.project_type or "").strip().lower() == "solar"
                else "Wind"
            )
            result = run_project(runtime_project_key, scenario_name, project_inputs_override=override)
            kpis = _format_kpis(result["kpis"])
            runtime_summary = runtime_summary_to_dict(result, project_code, project_name)
            runtime_snapshot_id = utc_now_iso().replace(":", "").replace("-", "")
            record_workspace_runtime(
                user_id=user.user_id,
                project_id=project_record.project_id,
                project_code=project_code,
                runtime_snapshot=runtime_snapshot,
                runtime_summary=result["kpis"],
                runtime_snapshot_id=runtime_snapshot_id,
                runtime_origin=runtime_origin,
                governance_state=_governance_snapshot(project_code),
                active_scenario_id=workspace_state.active_scenario_id if runtime_origin == "saved_state" else None,
                active_scenario_name=workspace_state.active_scenario_name if runtime_origin == "saved_state" else None,
                replay_metadata=_replay_metadata_for_project(
                    project_code,
                    project_id=project_record.project_id,
                    scenario_id=workspace_state.active_scenario_id if runtime_origin == "saved_state" else None,
                    runtime_timestamp=utc_now_iso(),
                    runtime_snapshot_id=runtime_snapshot_id,
                    export_type="workspace_runtime_state",
                ),
            )
            if runtime_origin == "saved_state" and workspace_state.active_scenario_id:
                update_scenario_last_run_summary(
                    user.user_id,
                    workspace_state.active_scenario_id,
                    result["kpis"],
                    replay_metadata=_replay_metadata_for_project(
                        project_code,
                        project_id=project_record.project_id,
                        scenario_id=workspace_state.active_scenario_id,
                        runtime_timestamp=utc_now_iso(),
                        runtime_snapshot_id=runtime_snapshot_id,
                        export_type="scenario_runtime_summary",
                    ),
                )
            runtime_html = templates.TemplateResponse(
                request=request,
                name="partials/runtime_summary.html",
                context={
                    "kpis": kpis,
                    "runtime_summary": runtime_summary,
                    "run_data": {"project_type": project_record.project_type, "scenario": scenario_name},
                    "messages": result.get("messages", []),
                    "integration_status": result.get("integration_status", "full"),
                },
            )
            from fastapi.responses import HTMLResponse
            body_str = runtime_html.body.decode("utf-8")
            save_tag = (
                '<script>'
                'sessionStorage.setItem("lastRuntimeSummary", ' + json.dumps(runtime_summary) + ');'
                'window.applyWorkspaceStateMeta && window.applyWorkspaceStateMeta(' + json.dumps({
                    "dirty": False,
                    "dirty_label": "Clean saved state" if runtime_origin == "saved_state" else "Clean workspace base",
                    "active_scenario_id": workspace_state.active_scenario_id or "",
                    "active_scenario_name": workspace_state.active_scenario_name or "",
                    "last_runtime_origin": runtime_origin,
                    "last_runtime_origin_label": "Runtime built from saved project assumptions" if runtime_origin == "workspace_base" else "Runtime bound to saved scenario snapshot",
                    "last_runtime_snapshot_id": runtime_snapshot_id,
                }) + ');'
                'window._populateRuntimeBlock && window._populateRuntimeBlock();'
                '</script>'
            )
            return HTMLResponse(content=save_tag + body_str, status_code=runtime_html.status_code)
        except SnapshotInputError as e:
            return templates.TemplateResponse(
                request=request,
                name="partials/errors.html",
                context={"errors": [str(e)]},
            )
        except Exception as e:
            return templates.TemplateResponse(
                request=request,
                name="partials/errors.html",
                context={"errors": [f"Model error ({project_code}): {str(e)}"]},
            )

    # -- Template-seeded runtime binding --------------------------------------
    # Factory templates keep their established TUHO/Oborovo path.
    if runtime_seed in {"tuho", "oborovo"}:
        try:
            project_key = "TUHO" if runtime_seed == "tuho" else "Oborovo"
            scenario_name = snapshot.get("scenario", "") or "Base"
            schema = _build_schema_from_form(
                project_record.project_type or _default_workspace_snapshot(runtime_seed)["project_type"],
                scenario_name,
                capacity_mw, tariff_eur_mwh, p50_hours,
                total_capex_keur, opex_y1_keur,
                gearing_pct, target_dscr, interest_rate_pct, tenor_years,
            )
            override = build_projectinputs(schema)
            result = run_project(project_key, scenario_name, project_inputs_override=override)
            kpis = _format_kpis(result["kpis"])
            runtime_summary = runtime_summary_to_dict(result, project_code, project_name)
            runtime_snapshot_id = utc_now_iso().replace(":", "").replace("-", "")
            record_workspace_runtime(
                user_id=user.user_id,
                project_id=project_record.project_id,
                project_code=project_code,
                runtime_snapshot=snapshot,
                runtime_summary=result["kpis"],
                runtime_snapshot_id=runtime_snapshot_id,
                runtime_origin=runtime_origin,
                governance_state=_governance_snapshot(project_code),
                active_scenario_id=workspace_state.active_scenario_id if runtime_origin == "saved_state" else None,
                active_scenario_name=workspace_state.active_scenario_name if runtime_origin == "saved_state" else None,
                replay_metadata=_replay_metadata_for_project(
                    project_code,
                    project_id=project_record.project_id,
                    scenario_id=workspace_state.active_scenario_id if runtime_origin == "saved_state" else None,
                    runtime_timestamp=utc_now_iso(),
                    runtime_snapshot_id=runtime_snapshot_id,
                    export_type="workspace_runtime_state",
                ),
            )
            if runtime_origin == "saved_state" and workspace_state.active_scenario_id:
                update_scenario_last_run_summary(
                    user.user_id,
                    workspace_state.active_scenario_id,
                    result["kpis"],
                    replay_metadata=_replay_metadata_for_project(
                        project_code,
                        project_id=project_record.project_id,
                        scenario_id=workspace_state.active_scenario_id,
                        runtime_timestamp=utc_now_iso(),
                        runtime_snapshot_id=runtime_snapshot_id,
                        export_type="scenario_runtime_summary",
                    ),
                )
            # Persist to sessionStorage so output tabs can read it on next page load
            runtime_html = templates.TemplateResponse(
                request=request,
                name="partials/runtime_summary.html",
                context={
                    "kpis": kpis,
                    "runtime_summary": runtime_summary,
                    "run_data": {"project_type": project_record.project_type or runtime_seed.title(), "scenario": scenario_name},
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
                'window.applyWorkspaceStateMeta && window.applyWorkspaceStateMeta(' + json.dumps({
                    "dirty": False if runtime_origin in ("saved_state", "workspace_base") else True,
                    "dirty_label": "Clean saved state" if runtime_origin == "saved_state" else ("Clean workspace base" if runtime_origin == "workspace_base" else "Unsaved edits"),
                    "active_scenario_id": workspace_state.active_scenario_id or "",
                    "active_scenario_name": workspace_state.active_scenario_name or "",
                    "last_runtime_origin": runtime_origin,
                    "last_runtime_origin_label": "Runtime bound to saved scenario snapshot" if runtime_origin == "saved_state" else "Runtime bound to clean workspace base",
                    "last_runtime_snapshot_id": runtime_snapshot_id,
                }) + ');'
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
                context={"errors": [f"Model error ({project_code}): {str(e)}"]},
            )
    # -- Generic template-seeded run path ------------------------------------

    errors = []
    effective_project_type = project_record.project_type or project_type
    if not _validate_form(effective_project_type, scenario, errors):
        return templates.TemplateResponse(
            request=request,
            name="partials/errors.html",
            context={"errors": errors},
        )

    try:
        schema = _build_schema_from_form(
            effective_project_type, scenario,
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
        runtime_project_key = "Solar" if _canonical_project_type(effective_project_type) == "Solar" else "Wind"
        result = run_project(runtime_project_key, scenario, project_inputs_override=override)
        kpis = _format_kpis(result["kpis"])
        runtime_snapshot_id = utc_now_iso().replace(":", "").replace("-", "")
        record_workspace_runtime(
            user_id=user.user_id,
            project_id=project_record.project_id,
            project_code=project_code,
            runtime_snapshot=snapshot,
            runtime_summary=result["kpis"],
            runtime_snapshot_id=runtime_snapshot_id,
            runtime_origin=runtime_origin,
            governance_state=_governance_snapshot(project_code),
            active_scenario_id=workspace_state.active_scenario_id if runtime_origin == "saved_state" else None,
            active_scenario_name=workspace_state.active_scenario_name if runtime_origin == "saved_state" else None,
            replay_metadata=_replay_metadata_for_project(
                project_code,
                project_id=project_record.project_id,
                scenario_id=workspace_state.active_scenario_id if runtime_origin == "saved_state" else None,
                runtime_timestamp=utc_now_iso(),
                runtime_snapshot_id=runtime_snapshot_id,
                export_type="workspace_runtime_state",
            ),
        )
        if runtime_origin == "saved_state" and workspace_state.active_scenario_id:
            update_scenario_last_run_summary(
                user.user_id,
                workspace_state.active_scenario_id,
                result["kpis"],
                replay_metadata=_replay_metadata_for_project(
                    project_code,
                    project_id=project_record.project_id,
                    scenario_id=workspace_state.active_scenario_id,
                    runtime_timestamp=utc_now_iso(),
                    runtime_snapshot_id=runtime_snapshot_id,
                    export_type="scenario_runtime_summary",
                ),
            )
        return templates.TemplateResponse(
            request=request,
            name="partials/kpis.html",
            context={
                "kpis": kpis,
                "run_data": {
                    "project_type": effective_project_type,
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
    snapshot = _collect_form_snapshot(form)
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
    project_record, workspace_state = _project_workspace_from_snapshot(user, snapshot)
    project_code = project_record.project_code
    allow_run, runtime_origin, guard_message = runtime_guard_for_snapshot(workspace_state, snapshot)
    if not allow_run:
        return templates.TemplateResponse(
            request=request,
            name="partials/errors.html",
            context={"errors": [guard_message]},
        )

    errors = []
    effective_project_type = project_record.project_type or project_type
    if effective_project_type not in PROJECT_TYPES:
        errors.append(f"project_type must be one of {PROJECT_TYPES}")
        return templates.TemplateResponse(
            request=request,
            name="partials/errors.html",
            context={"errors": errors},
        )

    if project_record.project_origin == "user_created":
        try:
            runtime_snapshot = _clean_user_project_runtime_snapshot(project_record, workspace_state, runtime_origin)
            override = build_projectinputs_from_snapshot(runtime_snapshot)
        except SnapshotInputError as e:
            return templates.TemplateResponse(
                request=request,
                name="partials/errors.html",
                context={"errors": [str(e)]},
            )
        runtime_project_key = "Solar" if _canonical_project_type(effective_project_type) == "Solar" else "Wind"
    else:
        try:
            schema = _build_schema_from_form(
                effective_project_type, "Base",
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

        runtime_seed = _normalize_template_source(project_record.template_source or project_record.source_project_template, effective_project_type)
        if runtime_seed == "tuho":
            runtime_project_key = "TUHO"
        elif runtime_seed == "oborovo":
            runtime_project_key = "Oborovo"
        else:
            runtime_project_key = "Solar" if _canonical_project_type(effective_project_type) == "Solar" else "Wind"
    results = {}
    for sc in SCENARIOS:
        try:
            r = run_project(runtime_project_key, sc, project_inputs_override=override)
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
            "project_type": effective_project_type,
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
        snapshot = _collect_form_snapshot(form)
        project_record, workspace_state = _project_workspace_from_snapshot(user, snapshot)
        project_code = project_record.project_code
        effective_project_type = project_record.project_type or project_type
        runtime_origin = "factory_base_runtime"
        if project_record.project_origin == "user_created":
            allow_run, runtime_origin, guard_message = runtime_guard_for_snapshot(workspace_state, snapshot)
            if not allow_run:
                return HTMLResponse(
                    content=f"<html><body><h2>Excel generation failed</h2><p>{guard_message}</p><a href='/'>Back</a></body></html>",
                    status_code=400,
                )
            runtime_snapshot = _clean_user_project_runtime_snapshot(project_record, workspace_state, runtime_origin)
            override = build_projectinputs_from_snapshot(runtime_snapshot)
            runtime_project_key = "Solar" if _canonical_project_type(effective_project_type) == "Solar" else "Wind"
        else:
            runtime_seed = _normalize_template_source(project_record.template_source or project_record.source_project_template, effective_project_type)
            if runtime_seed == "tuho":
                runtime_project_key = "TUHO"
            elif runtime_seed == "oborovo":
                runtime_project_key = "Oborovo"
            else:
                runtime_project_key = "Solar" if _canonical_project_type(effective_project_type) == "Solar" else "Wind"
        demo = run_demo_project(runtime_project_key, scenario, project_inputs_override=override)
        filename = f"fincogpt_{project_type.lower()}_{scenario.lower()}.xlsx"
        replay_metadata = _replay_metadata_for_project(
            project_code,
            export_type="excel_model_export",
            workbook_type="values_only_excel_export",
            export_timestamp=utc_now_iso(),
            runtime_timestamp=utc_now_iso(),
            project_id=project_record.project_id if project_record else None,
            scenario_id=workspace_state.active_scenario_id if runtime_origin == "saved_state" else None,
            scenario_name=scenario,
            runtime_origin=runtime_origin,
            artifact_name=filename,
            project_inputs_override=demo.project_inputs,
            template_origin_override=(
                "saved_project_assumptions"
                if project_record.project_origin == "user_created"
                else None
            ),
        )
        excel_bytes = build_excel_export(
            result=demo.result,
            project_inputs=demo.project_inputs,
            provenance_metadata=replay_metadata,
        )
        if project_record and project_record.project_origin == "saved_baseline":
            replay_metadata["baseline_source"] = True
        record_export(
            user_id=user.user_id,
            project_code=project_code,
            export_type="excel_model_export",
            artifact_name=filename,
            artifact_path=f"/download?project_type={project_type}&scenario={scenario}",
            project_id=project_record.project_id if project_record else None,
            governance_state=_governance_snapshot(project_code),
            replay_metadata=replay_metadata,
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
        project_code = "oborovo" if project_type.lower() == "solar" else "tuho"
        project_record = get_project_by_code(user.user_id, project_code)
        filename = f"fincogpt_{project_type.lower()}_{scenario.lower()}.xlsx"
        replay_metadata = _replay_metadata_for_project(
            project_code,
            export_type="excel_model_export",
            workbook_type="values_only_excel_export",
            export_timestamp=utc_now_iso(),
            runtime_timestamp=utc_now_iso(),
            project_id=project_record.project_id if project_record else None,
            scenario_name=scenario,
            runtime_origin="factory_base_runtime",
            artifact_name=filename,
        )
        excel_bytes = build_excel_export(
            result=demo.result,
            project_inputs=demo.project_inputs,
            provenance_metadata=replay_metadata,
        )
        if project_record and project_record.project_origin == "saved_baseline":
            replay_metadata["baseline_source"] = True
        record_export(
            user_id=user.user_id,
            project_code=project_code,
            export_type="excel_model_export",
            artifact_name=filename,
            artifact_path=f"/download?project_type={project_type}&scenario={scenario}",
            project_id=project_record.project_id if project_record else None,
            governance_state=_governance_snapshot(project_code),
            replay_metadata=replay_metadata,
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

    safe_project = project.strip().lower() if project else "tuho"
    project_record = get_project_by_code(user.user_id, safe_project)
    runtime_project_code = safe_project
    if project_record is not None:
        runtime_project_code = _normalize_template_source(project_record.template_source or project_record.source_project_template, project_record.project_type)

    try:
        runtime_rows = build_runtime_summary_rows(runtime_project_code)
        csv_text = build_runtime_summary_csv(
            runtime_project_code,
            generated_at=runtime_rows[0]["generated_at"],
            source_branch=runtime_rows[0]["source_branch"],
        )
    except ValueError as exc:
        return HTMLResponse(
            content=f"<html><body><h2>Runtime summary export failed</h2><p>{str(exc)}</p><a href='/'>Back</a></body></html>",
            status_code=400,
        )

    filename = f"phase10_{safe_project}_runtime_summary.csv"
    data = csv_text.encode("utf-8")
    record_export(
        user_id=user.user_id,
        project_code=safe_project,
        export_type="runtime_summary_csv",
        artifact_name=filename,
        artifact_path=f"/exports/runtime-summary.csv?project={safe_project}",
        project_id=project_record.project_id if project_record else None,
        governance_state=_governance_snapshot(safe_project),
        replay_metadata=_replay_metadata_for_project(
            safe_project,
            export_type="runtime_summary_csv",
            export_timestamp=runtime_rows[0]["export_generated_at"],
            runtime_timestamp=runtime_rows[0]["runtime_generated_at"],
            project_id=project_record.project_id if project_record else None,
            runtime_origin=runtime_rows[0]["runtime_origin"],
            artifact_name=filename,
            baseline_source=(project_record.project_origin == "saved_baseline") if project_record else None,
        ),
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

    safe_project = project.strip().lower() if project else "tuho"
    project_record = get_project_by_code(user.user_id, safe_project)
    runtime_project_code = safe_project
    if project_record is not None:
        runtime_project_code = _normalize_template_source(project_record.template_source or project_record.source_project_template, project_record.project_type)

    try:
        runtime_rows = build_runtime_summary_rows(runtime_project_code)
        workbook_bytes = export_institutional_workbook_skeleton(runtime_project_code)
    except ValueError as exc:
        return HTMLResponse(
            content=f"<html><body><h2>Institutional workbook export failed</h2><p>{str(exc)}</p><a href='/'>Back</a></body></html>",
            status_code=400,
        )

    filename = f"phase10_{safe_project}_institutional_workbook_skeleton.xlsx"
    record_export(
        user_id=user.user_id,
        project_code=safe_project,
        export_type="institutional_workbook",
        artifact_name=filename,
        artifact_path=f"/exports/institutional-workbook.xlsx?project={safe_project}",
        project_id=project_record.project_id if project_record else None,
        governance_state=_governance_snapshot(safe_project),
        replay_metadata=_replay_metadata_for_project(
            safe_project,
            export_type="institutional_workbook",
            workbook_type="institutional_workbook_runtime_binding",
            export_timestamp=runtime_rows[0]["export_generated_at"],
            runtime_timestamp=runtime_rows[0]["runtime_generated_at"],
            project_id=project_record.project_id if project_record else None,
            runtime_origin=runtime_rows[0]["runtime_origin"],
            artifact_name=filename,
            baseline_source=(project_record.project_origin == "saved_baseline") if project_record else None,
        ),
    )
    return StreamingResponse(
        iter([workbook_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(workbook_bytes)),
        },
    )


@app.get("/projects/new")
async def new_project_form(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(
        request=request,
        name="partials/new_project_form.html",
        context={
            "project_types": PROJECT_TYPES,
            "template_options": NEW_PROJECT_TEMPLATE_OPTIONS,
            "validation_errors": [],
            "submitted": _submitted_new_project_defaults(),
        },
    )


@app.post("/projects/create")
async def create_project_route(
    request: Request,
    project_name: str = Form(...),
    project_type: str = Form(...),
    template_source: str = Form(""),
    country_market: str = Form("Croatia"),
    capacity_mw: str = Form(""),
    cod_date: str = Form(""),
    construction_months: str = Form(""),
    horizon_years: str = Form(""),
    tariff_eur_mwh: str = Form(""),
    ppa_term_years: str = Form(""),
    p50_hours: str = Form(""),
    opex_y1_keur: str = Form(""),
    total_capex_keur: str = Form(""),
    gearing_pct: str = Form(""),
    interest_rate_pct: str = Form(""),
    tenor_years: str = Form(""),
    target_dscr: str = Form("1.20"),
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    submitted = _submitted_new_project_defaults()
    submitted.update(
        {
            "project_name": project_name,
            "project_type": project_type,
            "template_source": template_source,
            "country_market": country_market,
            "capacity_mw": capacity_mw,
            "cod_date": cod_date,
            "construction_months": construction_months,
            "horizon_years": horizon_years,
            "tariff_eur_mwh": tariff_eur_mwh,
            "ppa_term_years": ppa_term_years,
            "p50_hours": p50_hours,
            "opex_y1_keur": opex_y1_keur,
            "total_capex_keur": total_capex_keur,
            "gearing_pct": gearing_pct,
            "interest_rate_pct": interest_rate_pct,
            "tenor_years": tenor_years,
            "target_dscr": target_dscr,
        }
    )

    clean_name = _coerce_form_text(project_name)
    canonical_type = _canonical_project_type(project_type)
    normalized_source = _normalize_template_source(template_source, canonical_type)
    submitted["project_name"] = clean_name
    submitted["project_type"] = project_type
    submitted["template_source"] = normalized_source
    validation_errors = _validate_new_project_payload(submitted)

    if normalized_source in {"tuho", "generic_wind"} and canonical_type != "Wind":
        validation_errors.append("Wind templates require project type Wind.")
    if normalized_source in {"oborovo", "generic_solar"} and canonical_type != "Solar":
        validation_errors.append("Solar templates require project type Solar.")

    if validation_errors:
        return templates.TemplateResponse(
            request=request,
            name="partials/new_project_form.html",
            context=_new_project_validation_error_context(submitted, validation_errors),
            status_code=400,
        )

    base_slug = _slugify_project_code(clean_name)
    project_code = base_slug
    suffix = 2
    while get_project_by_code(user.user_id, project_code) is not None:
        project_code = f"{base_slug}-{suffix}"
        suffix += 1

    baseline_snapshot = _apply_new_project_required_inputs(
        _project_baseline_snapshot(canonical_type, normalized_source),
        project_name=clean_name,
        project_code=project_code,
        project_type=canonical_type,
        project_origin="user_created",
        template_source=normalized_source,
        submitted=submitted,
    )

    project_record = create_project_record(
        user_id=user.user_id,
        project_code=project_code,
        project_name=clean_name,
        project_type=canonical_type,
        project_origin="user_created",
        template_source=normalized_source,
        baseline_snapshot=baseline_snapshot,
        governance_state=_governance_snapshot(project_code),
        replay_metadata=_replay_metadata_for_project(
            project_code,
            project_id=None,
            export_type="project_record_created",
        ),
    )
    save_workspace_state(
        user_id=user.user_id,
        project_id=project_record.project_id,
        project_code=project_record.project_code,
        draft_snapshot=baseline_snapshot,
        saved_snapshot=baseline_snapshot,
        dirty=False,
        governance_state=_governance_snapshot(project_code),
        replay_metadata=_replay_metadata_for_project(
            project_code,
            project_id=project_record.project_id,
            export_type="workspace_project_created",
        ),
    )

    return templates.TemplateResponse(
        request=request,
        name="partials/new_project_result.html",
        context={
            "project_record": project_record,
            "template_source_label": _template_source_label(normalized_source),
        },
        headers={"HX-Redirect": f"/?project={project_record.project_code}"},
    )


@app.get("/scenarios")
async def list_scenarios_endpoint(request: Request, project: str = "tuho"):
    """Render the saved scenario and export-history workspace for the active project."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    project_record = _resolve_project_record(user, project)
    project_record, workspace_state, scenarios, history, exports, export_lineage, scenario_summary_cards = _current_project_workspace(user, project_record)
    return _render_scenario_workspace(
        request,
        user,
        project_record,
        workspace_state,
        scenarios,
        history,
        exports,
        export_lineage,
        scenario_summary_cards,
    )


@app.post("/scenarios/state/draft")
async def save_workspace_draft_endpoint(request: Request):
    """Persist unsaved workspace edits without promoting them to saved-scenario authority."""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Login required"}, status_code=401)

    form = await request.form()
    snapshot = _collect_form_snapshot(form)
    project_record, existing = _project_workspace_from_snapshot(user, snapshot)
    project_code = project_record.project_code
    saved_snapshot = existing.saved_snapshot if existing else (project_record.baseline_snapshot or _default_workspace_snapshot(project_code))
    active_scenario_id = existing.active_scenario_id if existing else (form.get("current_saved_scenario_id", "") or None)
    active_scenario_name = existing.active_scenario_name if existing else None
    workspace_state = save_workspace_state(
        user_id=user.user_id,
        project_id=project_record.project_id,
        project_code=project_code,
        active_scenario_id=active_scenario_id,
        active_scenario_name=active_scenario_name,
        draft_snapshot=snapshot,
        saved_snapshot=saved_snapshot,
        dirty=not snapshots_equal(snapshot, saved_snapshot),
        governance_state=_governance_snapshot(project_code),
        replay_metadata=_replay_metadata_for_project(
            project_code,
            project_id=project_record.project_id,
            scenario_id=active_scenario_id,
            export_type="workspace_draft_state",
        ),
    )
    payload = _workspace_state_meta(workspace_state)
    payload["message"] = "Workspace draft captured. Saved scenario authority is unchanged."
    return JSONResponse(payload)


@app.post("/scenarios/state/discard")
async def discard_workspace_draft_endpoint(request: Request):
    """Discard unsaved workspace edits and restore the last saved scenario boundary."""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Login required"}, status_code=401)

    form = await request.form()
    snapshot = _collect_form_snapshot(form)
    project_record, _ = _project_workspace_from_snapshot(user, snapshot)
    project_code = project_record.project_code
    workspace_state = discard_workspace_draft(user.user_id, project_record.project_id)
    if workspace_state is None:
        baseline_snapshot = project_record.baseline_snapshot or _default_workspace_snapshot(project_code)
        workspace_state = save_workspace_state(
            user_id=user.user_id,
            project_id=project_record.project_id,
            project_code=project_code,
            draft_snapshot=baseline_snapshot,
            saved_snapshot=baseline_snapshot,
            dirty=False,
            governance_state=_governance_snapshot(project_code),
            replay_metadata=_replay_metadata_for_project(
                project_code,
                project_id=project_record.project_id,
                export_type="workspace_draft_state",
            ),
        )
    payload = _workspace_state_meta(workspace_state)
    payload["snapshot"] = workspace_state.draft_snapshot
    payload["message"] = "Unsaved edits discarded. Workspace restored to the last saved runtime boundary."
    return JSONResponse(payload)


@app.get("/scenarios/history")
async def scenario_history_endpoint(request: Request, project: str = "tuho"):
    """Refresh scenario history and lineage for the active project."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    project_record = _resolve_project_record(user, project)
    project_record, workspace_state, _, _, _, _, _ = _current_project_workspace(user, project_record)
    scenarios, history, exports, export_lineage, scenario_summary_cards = _workspace_refresh_payload(user, project_record)
    return _render_scenario_workspace(
        request,
        user,
        project_record,
        workspace_state,
        scenarios,
        history,
        exports,
        export_lineage,
        scenario_summary_cards,
        message="Refreshed scenario history and export lineage.",
    )


@app.get("/scenarios/compare")
async def scenario_compare_endpoint(
    request: Request,
    project: str = "tuho",
    left_scenario_id: str | None = None,
    right_scenario_id: str | None = None,
):
    """Render a lightweight, governance-aware scenario comparison."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    project_record = _resolve_project_record(user, project)
    project_record, workspace_state, _, _, _, _, _ = _current_project_workspace(user, project_record)
    scenarios, history, exports, export_lineage, scenario_summary_cards = _workspace_refresh_payload(user, project_record)

    compare_result = None
    message = "Select two saved scenarios to compare."
    if left_scenario_id and right_scenario_id:
        compare_result = compare_scenarios(user.user_id, left_scenario_id, right_scenario_id)
        if compare_result is None:
            message = "Could not compare those scenarios."
        else:
            compare_result = _build_compare_ui_context(compare_result, workspace_state)
            message = "Scenario compare ready. Review numeric deltas together with governance posture."

    return _render_scenario_workspace(
        request,
        user,
        project_record,
        workspace_state,
        scenarios,
        history,
        exports,
        export_lineage,
        scenario_summary_cards,
        message=message,
        compare_result=compare_result,
    )


@app.post("/scenarios/save")
async def save_scenario_endpoint(request: Request):
    """Persist the current form snapshot as a saved scenario."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    form = await request.form()
    snapshot = _collect_form_snapshot(form)
    project_record, existing_workspace_state = _project_workspace_from_snapshot(user, snapshot)

    # Block save for factory templates and saved baselines
    if project_record.project_origin in ("factory_template", "saved_baseline"):
        return _render_scenario_workspace(
            request, user, project_record, existing_workspace_state,
            [], [], [], [], [],
            message=f"Save is not available for {project_record.project_origin.replace('_', ' ')} "
                    f"'{project_record.project_code}'. Use 'Save As' to create a user project.",
        )

    project_code = project_record.project_code
    project_name = project_record.project_name
    scenario_name = f"{project_name} {snapshot.get('scenario', 'Base')} {dt.now().strftime('%Y-%m-%d %H:%M')}"
    saved_record = save_scenario(
        user_id=user.user_id,
        project_id=project_record.project_id,
        scenario_name=scenario_name,
        project_code=project_code,
        source_project_template=project_record.template_source or project_record.source_project_template,
        snapshot=snapshot,
        governance_state=_governance_snapshot(project_code),
        last_run_summary=(
            existing_workspace_state.last_runtime_summary
            if existing_workspace_state and snapshots_equal(existing_workspace_state.last_runtime_snapshot, snapshot)
            else {}
        ),
        replay_metadata=_replay_metadata_for_project(
            project_code,
            project_id=project_record.project_id,
            export_type="saved_scenario_snapshot",
        ),
    )
    workspace_state = bind_workspace_to_scenario(
        user.user_id,
        project_record.project_id,
        project_code,
        saved_record,
        governance_state=_governance_snapshot(project_code),
        replay_metadata=_replay_metadata_for_project(
            project_code,
            project_id=project_record.project_id,
            scenario_id=saved_record.scenario_id,
            export_type="workspace_saved_boundary",
        ),
    )
    scenarios = list_scenarios(user.user_id, project_id=project_record.project_id, include_archived=False, limit=12)
    history = get_scenario_history(user.user_id, project_id=project_record.project_id, limit=20)
    exports = list_exports(user.user_id, project_id=project_record.project_id, limit=8)
    export_lineage = build_export_lineage(user.user_id, project_id=project_record.project_id, limit=8)
    scenario_summary_cards = []
    export_counts = {}
    for entry in export_lineage:
        export_counts[entry["scenario_name"]] = export_counts.get(entry["scenario_name"], 0) + 1
    for item in scenarios:
        summary = item.last_run_summary or {}
        scenario_summary_cards.append(
            {
                "scenario_id": item.scenario_id,
                "scenario_name": item.scenario_name,
                "project_code": item.project_code,
                "updated_at": item.updated_at,
                "copied_from_scenario_id": item.copied_from_scenario_id,
                "project_irr": summary.get("project_irr"),
                "equity_irr": summary.get("equity_irr"),
                "avg_dscr": summary.get("avg_dscr"),
                "export_count": export_counts.get(item.scenario_name, 0),
                "governance_state": item.governance_state,
            }
        )
    return _render_scenario_workspace(
        request,
        user,
        project_record,
        workspace_state,
        scenarios,
        history,
        exports,
        export_lineage,
        scenario_summary_cards,
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
    bind_workspace_to_scenario(
        user.user_id,
        record.project_id,
        record.project_code,
        record,
        governance_state=record.governance_state,
        replay_metadata=_replay_metadata_for_project(
            record.project_code,
            project_id=record.project_id,
            scenario_id=record.scenario_id,
            export_type="workspace_loaded_scenario",
        ),
    )

    return templates.TemplateResponse(
        request=request,
        name="partials/scenario_load_result.html",
        context={
            "record": record,
            "message": f"Loaded {record.scenario_name}. The form has been refreshed with the saved snapshot.",
            "project_code": record.project_code,
            "workspace_state_meta": _workspace_state_meta(get_workspace_state(user.user_id, record.project_id)),
        },
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
    history = get_scenario_history(user.user_id, project_id=original.project_id, limit=20)
    exports = list_exports(user.user_id, project_id=original.project_id, limit=8)
    export_lineage = build_export_lineage(user.user_id, project_id=original.project_id, limit=8)
    export_counts = {}
    for entry in export_lineage:
        export_counts[entry["scenario_name"]] = export_counts.get(entry["scenario_name"], 0) + 1
    scenario_summary_cards = []
    for item in scenarios:
        summary = item.last_run_summary or {}
        scenario_summary_cards.append(
            {
                "scenario_id": item.scenario_id,
                "scenario_name": item.scenario_name,
                "project_code": item.project_code,
                "updated_at": item.updated_at,
                "copied_from_scenario_id": item.copied_from_scenario_id,
                "project_irr": summary.get("project_irr"),
                "equity_irr": summary.get("equity_irr"),
                "avg_dscr": summary.get("avg_dscr"),
                "export_count": export_counts.get(item.scenario_name, 0),
                "governance_state": item.governance_state,
            }
        )
    return _render_scenario_workspace(
        request,
        user,
        project_record,
        get_workspace_state(user.user_id, original.project_id),
        scenarios,
        history,
        exports,
        export_lineage,
        scenario_summary_cards,
        message=f"Duplicated {original.scenario_name}.",
    )


@app.post("/projects/{project_code}/save-as")
async def save_project_as_endpoint(request: Request, project_code: str):
    """Duplicate a factory template or saved baseline into a user-editable project."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    from app.persistence.repository import get_project_record as gpr
    source = gpr(user_id=user.user_id, project_code=project_code)
    if source is None:
        return JSONResponse({"error": f"Project '{project_code}' not found"}, status_code=404)
    if source.project_origin == "user_created":
        return JSONResponse({"error": "Already a user project"}, status_code=400)
    now = _now_utc()
    new_code = f"{project_code}-copy-{now.strftime('%Y%m%d%H%M%S')}"
    new_name = f"{source.project_name} (Copy)"
    new_record = save_project(
        user_id=user.user_id,
        project_code=new_code,
        project_name=new_name,
        project_type=source.project_type,
        project_origin="user_created",
        source_project_template=source.source_project_template,
        template_source=source.template_source,
        baseline_snapshot=source.baseline_snapshot,
        is_readonly=False,
        governance_state={"g20": "BLOCKED", "r99_r102": "NOT_APPROVED", "lender_ready": False},
        last_run_summary={},
        replay_metadata={
            "export_type": "project_duplicated",
            "source_project_code": project_code,
            "source_project_origin": source.project_origin,
            "baseline_source": source.project_origin == "saved_baseline",
        },
    )
    save_workspace_state(
        user_id=user.user_id,
        project_id=new_record.project_id,
        project_code=new_record.project_code,
        draft_snapshot=source.baseline_snapshot,
        saved_snapshot=source.baseline_snapshot,
        dirty=False,
        governance_state={"g20": "BLOCKED", "r99_r102": "NOT_APPROVED", "lender_ready": False},
        replay_metadata={
            "export_type": "workspace_duplicated",
            "source_project_code": project_code,
            "baseline_source": source.project_origin == "saved_baseline",
        },
    )
    return RedirectResponse(url=f"/?project={new_code}", status_code=302)


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
    history = get_scenario_history(user.user_id, project_id=record.project_id, limit=20)
    exports = list_exports(user.user_id, project_id=record.project_id, limit=8)
    export_lineage = build_export_lineage(user.user_id, project_id=record.project_id, limit=8)
    export_counts = {}
    for entry in export_lineage:
        export_counts[entry["scenario_name"]] = export_counts.get(entry["scenario_name"], 0) + 1
    scenario_summary_cards = []
    for item in scenarios:
        summary = item.last_run_summary or {}
        scenario_summary_cards.append(
            {
                "scenario_id": item.scenario_id,
                "scenario_name": item.scenario_name,
                "project_code": item.project_code,
                "updated_at": item.updated_at,
                "copied_from_scenario_id": item.copied_from_scenario_id,
                "project_irr": summary.get("project_irr"),
                "equity_irr": summary.get("equity_irr"),
                "avg_dscr": summary.get("avg_dscr"),
                "export_count": export_counts.get(item.scenario_name, 0),
                "governance_state": item.governance_state,
            }
        )
    return _render_scenario_workspace(
        request,
        user,
        project_record,
        get_workspace_state(user.user_id, record.project_id),
        scenarios,
        history,
        exports,
        export_lineage,
        scenario_summary_cards,
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
    history = get_scenario_history(user.user_id, project_id=record.project_id, limit=20)
    exports = list_exports(user.user_id, project_id=record.project_id, limit=8)
    export_lineage = build_export_lineage(user.user_id, project_id=record.project_id, limit=8)
    export_counts = {}
    for entry in export_lineage:
        export_counts[entry["scenario_name"]] = export_counts.get(entry["scenario_name"], 0) + 1
    scenario_summary_cards = []
    for item in scenarios:
        summary = item.last_run_summary or {}
        scenario_summary_cards.append(
            {
                "scenario_id": item.scenario_id,
                "scenario_name": item.scenario_name,
                "project_code": item.project_code,
                "updated_at": item.updated_at,
                "copied_from_scenario_id": item.copied_from_scenario_id,
                "project_irr": summary.get("project_irr"),
                "equity_irr": summary.get("equity_irr"),
                "avg_dscr": summary.get("avg_dscr"),
                "export_count": export_counts.get(item.scenario_name, 0),
                "governance_state": item.governance_state,
            }
        )
    return _render_scenario_workspace(
        request,
        user,
        project_record,
        get_workspace_state(user.user_id, record.project_id),
        scenarios,
        history,
        exports,
        export_lineage,
        scenario_summary_cards,
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
    snapshot = _collect_form_snapshot(form)
    project_type = form.get("project_type", "")
    scenario = form.get("scenario", "")
    project_record, workspace_state = _project_workspace_from_snapshot(user, snapshot)
    project_code = project_record.project_code
    project_name = project_record.project_name
    allow_run, runtime_origin, guard_message = runtime_guard_for_snapshot(workspace_state, snapshot)
    if not allow_run:
        return templates.TemplateResponse(
            request=request,
            name="partials/save_result.html",
            context={"success": False, "error": guard_message},
            headers={"HX-Trigger": "refreshHistory"},
        )

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
    effective_project_type = project_record.project_type or project_type
    if not _validate_form(effective_project_type, scenario, errors):
        return templates.TemplateResponse(
            request=request,
            name="partials/save_result.html",
            context={"success": False, "error": errors[0] if errors else "Invalid form"},
            headers={"HX-Trigger": "refreshHistory"},
        )

    # Re-run model to get fresh KPIs from the clean saved runtime source.
    try:
        if project_record.project_origin == "user_created":
            runtime_snapshot = _clean_user_project_runtime_snapshot(project_record, workspace_state, runtime_origin)
            override = build_projectinputs_from_snapshot(runtime_snapshot)
            runtime_project_key = "Solar" if _canonical_project_type(effective_project_type) == "Solar" else "Wind"
        else:
            schema = _build_schema_from_form(
                effective_project_type, scenario,
                inputs.get("capacity_mw"), inputs.get("tariff_eur_mwh"),
                inputs.get("p50_hours"), inputs.get("total_capex_keur"),
                inputs.get("opex_y1_keur"), inputs.get("gearing_pct"),
                inputs.get("target_dscr"), inputs.get("interest_rate_pct"),
                inputs.get("tenor_years"),
            )
            override = build_projectinputs(schema)
            runtime_seed = _normalize_template_source(project_record.template_source or project_record.source_project_template, effective_project_type)
            if runtime_seed == "tuho":
                runtime_project_key = "TUHO"
            elif runtime_seed == "oborovo":
                runtime_project_key = "Oborovo"
            else:
                runtime_project_key = "Solar" if _canonical_project_type(effective_project_type) == "Solar" else "Wind"
        result = run_project(runtime_project_key, scenario, project_inputs_override=override)
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
            project_type=effective_project_type,
            scenario=scenario,
            inputs=inputs,
            kpis=kpis,
            replay_metadata=_replay_metadata_for_project(
                project_code,
                export_type="saved_run_metadata",
                runtime_timestamp=utc_now_iso(),
            ),
        )
        save_project(
            user_id=user_id,
            project_code=project_code,
            project_name=project_name,
            source_project_template=project_code,
            governance_state=_governance_snapshot(project_code),
            last_run_summary=kpis,
            replay_metadata=_replay_metadata_for_project(
                project_code,
                project_id=None,
                export_type="saved_run_project_state",
                runtime_timestamp=run_record.created_at.isoformat(),
            ),
        )
        return templates.TemplateResponse(
            request=request,
            name="partials/save_result.html",
            context={
                "success": True,
                "run_id": run_record.run_id,
                "project_type": effective_project_type,
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
