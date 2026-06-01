"""Scenario state service — low-risk helpers only.

Phase 50B: Extract only _workspace_state_meta and _scenario_provenance_for_record.
Do NOT extract _resolve_runtime_snapshot_source (deferred to Phase 50C).
"""
from typing import Any

from app.persistence.repository import (
    get_scenario_provenance,
    get_workspace_state,
)


def build_workspace_state_metadata(workspace_state) -> dict:
    """Build UI-visible dirty/runtime state metadata.

    Equivalent to main_web._workspace_state_meta().
    Returns same dict shape regardless of workspace_state being None.
    """
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


def _normalize_template_source(template_source: str | None, project_type: str | None) -> str:
    """Normalize template source string.

    Duplicated from main_web.py to avoid circular import.
    Must stay in sync with main_web._normalize_template_source().
    """
    source = (template_source or "").strip().lower()
    if source in {"tuho", "oborovo", "generic_wind", "generic_solar"}:
        return source
    return "generic_solar" if (project_type or "").strip().lower() == "solar" else "generic_wind"


def _template_origin_for_record(project_record) -> str:
    """Build template origin string for scenario provenance.

    Duplicated from main_web.py to avoid circular import.
    Must stay in sync with main_web._template_origin_for_record().
    """
    template_seed = _normalize_template_source(
        project_record.template_source or project_record.source_project_template,
        project_record.project_type,
    )
    return f"project_factory:{(template_seed or project_record.project_code or 'unknown').lower()}"


def scenario_provenance_for_record(project_record, scenario_record) -> dict | None:
    """Build scenario provenance dict for UI context.

    Equivalent to main_web._scenario_provenance_for_record().
    Returns None if scenario_record is None (passthrough behavior preserved).
    Returns None if project_record is None (early exit, avoids crash).
    """
    if scenario_record is None:
        return None
    if project_record is None:
        return None
    return get_scenario_provenance(
        scenario_record,
        project_record,
        _template_origin_for_record(project_record),
    )


# NOTE: build_workspace_state_metadata and scenario_provenance_for_record
# are the only functions in this module for Phase 50B.
#
# Deferred to Phase 50C:
#   - _resolve_runtime_snapshot_source (complex decision tree, runtime binding)
#   - resolve_active_scenario_runtime_snapshot integration
#   - runtime_guard_for_snapshot wrapper (check_runtime_allowed)