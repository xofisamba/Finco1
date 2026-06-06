"""Phase 51B — Vertical extraction of POST /run orchestration.

This module owns the orchestration body that previously lived inside the
``@app.post("/run")`` route handler in ``main_web.py``.

The route is now thin: it authenticates the user, parses the form, calls
``execute_run_route(...)`` and renders the returned ``RunRouteOutcome`` via
the existing FastAPI / Jinja rendering path.

Why ``RunRouteOutcome`` (return value) instead of building a Response here:
- The route in ``main_web.py`` owns the FastAPI ``Request`` and the
  ``Jinja2Templates`` instance. Passing a ``Response`` across that boundary
  forces the service to depend on FastAPI internals, which would couple
  the service to the web framework and complicate future unit testing.
- Returning a plain dataclass keeps the service free of framework
  dependencies, and the route is the only place that calls
  ``templates.TemplateResponse(...)`` and ``HTMLResponse(...)``.

This module does NOT import ``main_web``. All helper functions that the
route in ``main_web.py`` still owns (``_build_schema_from_form``,
``_format_kpis``, ``_replay_metadata_for_project``, etc.) are passed in as
callable dependencies by the route. This keeps the import direction clean
(``main_web`` -> ``run_service`` and never the reverse).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Mapping, Optional


@dataclass
class RunRouteOutcome:
    """Result of POST /run orchestration.

    The route in ``main_web.py`` translates this into a FastAPI response.
    ``prepend_html`` is the sessionStorage save script that is prepended
    to ``partials/runtime_summary.html`` outputs (it must be prepended at
    the bytes level, not as Jinja context, so the service cannot put it
    inside ``context``).
    """

    template_name: str
    context: dict
    status_code: int = 200
    prepend_html: Optional[str] = None
    headers: dict = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# Service entry point
# ─────────────────────────────────────────────────────────────────────────────


async def execute_run_route(
    *,
    request: RequestLike,
    form: FormLike,
    user: Any,
    deps: "RunRouteDeps",
) -> RunRouteOutcome:
    """Execute the /run orchestration and return a ``RunRouteOutcome``.

    Parameters
    ----------
    request
        A FastAPI ``Request`` (or any object exposing ``.url.path`` and
        a session-cookie friendly interface). The service does not use it
        for anything other than passing through to ``templates.TemplateResponse``;
        it is provided as a hook for the route to wire up its own request
        context.
    form
        An async form result (``await request.form()``). The service
        extracts form fields from this object.
    user
        The authenticated user object (must have ``user_id``).
    deps
        Bundle of dependencies from the route (helpers, persistence
        functions, runtime-resolution helper). See ``RunRouteDeps``.
    """
    # ── 1. Form parsing ─────────────────────────────────────────────────
    active_project = form.get("active_project", "").strip().lower()  # type: ignore[arg-type]
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

    # ── 2. Snapshot + project/workspace resolution ───────────────────────
    snapshot = deps.collect_form_snapshot(form)
    project_record, workspace_state = deps.project_workspace_from_snapshot(user, snapshot)
    project_code = project_record.project_code
    project_name = project_record.project_name

    # ── 3. Runtime guard ────────────────────────────────────────────────
    allow_run, runtime_origin, guard_message = deps.check_runtime_allowed(workspace_state, snapshot)
    if not allow_run:
        return RunRouteOutcome(
            template_name="partials/errors.html",
            context={"errors": [guard_message]},
        )

    # ── 4. Runtime snapshot resolution ──────────────────────────────────
    runtime_seed = deps.normalize_template_source(
        project_record.template_source or project_record.source_project_template,
        project_record.project_type,
    )
    runtime_snapshot: Optional[dict] = None
    active_scenario_record = None
    runtime_warning: Optional[str] = None
    effective_runtime_origin = runtime_origin
    if (runtime_origin == "saved_state" and workspace_state.active_scenario_id) \
            or project_record.project_origin == "user_created":
        runtime_snapshot, active_scenario_record, runtime_warning, effective_runtime_origin = \
            deps.resolve_runtime_snapshot_source(
                user, project_record, workspace_state, runtime_origin,
            )

    # ── 5. Three execution paths ────────────────────────────────────────
    # Phase 51B: order and bodies preserved exactly from the original
    # /run route. Only the wrapper code (record/persistence calls) was
    # delegated to helper closures to remove repetition.
    if project_record.project_origin == "user_created":
        return await _execute_user_created_path(
            request=request, user=user, snapshot=snapshot, scenario=scenario,
            project_record=project_record, workspace_state=workspace_state,
            runtime_snapshot=runtime_snapshot, active_scenario_record=active_scenario_record,
            runtime_warning=runtime_warning,
            runtime_origin=runtime_origin, effective_runtime_origin=effective_runtime_origin,
            deps=deps,
        )

    if runtime_seed in {"tuho", "oborovo"}:
        return await _execute_template_seeded_path(
            request=request, user=user, snapshot=snapshot, scenario=scenario,
            project_record=project_record, workspace_state=workspace_state,
            runtime_snapshot=runtime_snapshot, active_scenario_record=active_scenario_record,
            runtime_warning=runtime_warning, runtime_origin=runtime_origin,
            capacity_mw=capacity_mw, tariff_eur_mwh=tariff_eur_mwh, p50_hours=p50_hours,
            total_capex_keur=total_capex_keur, opex_y1_keur=opex_y1_keur,
            gearing_pct=gearing_pct, target_dscr=target_dscr, interest_rate_pct=interest_rate_pct,
            tenor_years=tenor_years, runtime_seed=runtime_seed, deps=deps,
        )

    # Generic template-seeded path
    return await _execute_generic_path(
        request=request, user=user, snapshot=snapshot, scenario=scenario,
        project_record=project_record, workspace_state=workspace_state,
        runtime_snapshot=runtime_snapshot, active_scenario_record=active_scenario_record,
        runtime_warning=runtime_warning, runtime_origin=runtime_origin,
        project_type=project_type, capacity_mw=capacity_mw, tariff_eur_mwh=tariff_eur_mwh,
        p50_hours=p50_hours, total_capex_keur=total_capex_keur, opex_y1_keur=opex_y1_keur,
        gearing_pct=gearing_pct, target_dscr=target_dscr, interest_rate_pct=interest_rate_pct,
        tenor_years=tenor_years, deps=deps,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Dependencies bundle (DI for helpers still in main_web.py)
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class RunRouteDeps:
    """Dependencies that ``execute_run_route`` needs from the route.

    The route in ``main_web.py`` owns these helpers; passing them in as
    callables (rather than importing from ``main_web``) keeps the
    ``main_web`` -> ``run_service`` import direction clean and lets
    future test code inject test doubles.
    """

    # Form/snapshot helpers
    collect_form_snapshot: Callable[[Any], dict]
    project_workspace_from_snapshot: Callable[[Any, dict], tuple]
    normalize_template_source: Callable[..., str]
    canonical_project_type: Callable[[Any], str]

    # Runtime guard + resolution
    check_runtime_allowed: Callable[..., tuple]
    resolve_runtime_snapshot_source: Callable[..., tuple]

    # Schema build + validation
    build_schema_from_form: Callable[..., Any]
    validate_form: Callable[[str, str, list], bool]
    format_kpis: Callable[[dict], list]
    default_workspace_snapshot: Callable[[str], dict]

    # Replay + governance
    replay_metadata_for_project: Callable[..., dict]
    governance_snapshot: Callable[..., dict]
    scenario_provenance_for_record: Callable[..., Any]

    # Model execution
    run_project: Callable[..., dict]

    # Snapshot -> project inputs adapter
    build_projectinputs: Callable[..., Any]
    build_projectinputs_from_snapshot: Callable[..., Any]

    # Persistence
    record_workspace_runtime: Callable[..., Any]
    update_scenario_last_run_summary: Callable[..., Any]

    # Summary serializer
    runtime_summary_to_dict: Callable[..., dict]

    # Snapshot error class (for narrow except in user_created path)
    snapshot_input_error: type


# ─────────────────────────────────────────────────────────────────────────────
# Path implementations
# ─────────────────────────────────────────────────────────────────────────────


async def _execute_user_created_path(
    *,
    request,
    user,
    snapshot: dict,
    scenario: str,
    project_record,
    workspace_state,
    runtime_snapshot: Optional[dict],
    active_scenario_record,
    runtime_warning: Optional[str],
    runtime_origin: str,
    effective_runtime_origin: str,
    deps: RunRouteDeps,
) -> RunRouteOutcome:
    """User-created project run path (Phase 17C snapshot binding).

    Body is preserved **byte-for-byte** with the legacy /run user_created
    branch. The only thing that changes is that the route in main_web.py
    no longer contains this code.
    """
    try:
        override = deps.build_projectinputs_from_snapshot(runtime_snapshot)

        # Phase 57A-9D: fold persisted user-added CAPEX
        # sub-lines into the input CapexStructure. This
        # is the explicit Run/materialization boundary.
        # It runs ONLY in the user-created path — factory
        # / template-seeded paths (TUHO, Oborovo, Generic
        # Solar, Generic Wind) do NOT call this helper.
        # 57A-8 in-memory preview rows are NOT persisted,
        # so they cannot leak in here.
        if active_scenario_record is not None:
            _scenario_overrides_for_fold = (
                active_scenario_record.overrides
            )
        else:
            _scenario_overrides_for_fold = None
        from app.services.capex_sub_lines_integration import (
            _apply_user_sub_lines_to_capex,
        )
        folded_capex = _apply_user_sub_lines_to_capex(
            override.capex,
            project_id=project_record.project_id,
            scenario_overrides=_scenario_overrides_for_fold,
        )
        if folded_capex is not override.capex:
            # The fold produced a new CapexStructure (it
            # is frozen, so it had to). Replace the
            # override's capex with the folded one.
            from dataclasses import replace as _dc_replace
            override = _dc_replace(override, capex=folded_capex)

        scenario_name = (
            (runtime_snapshot.get("scenario") if runtime_snapshot else None)
            or snapshot.get("scenario", "")
            or "Base"
        )
        runtime_project_key = (
            "Solar"
            if (runtime_snapshot.get("project_type") or project_record.project_type or "").strip().lower() == "solar"  # type: ignore[union-attr]
            else "Wind"
        )
        result = deps.run_project(runtime_project_key, scenario_name, project_inputs_override=override)
        kpis = deps.format_kpis(result["kpis"])
        runtime_summary = deps.runtime_summary_to_dict(result, project_record.project_code, project_record.project_name)
        runtime_snapshot_id = _utc_now_iso_compact()
        scenario_provenance = deps.scenario_provenance_for_record(project_record, active_scenario_record)
        bound_scenario_id = active_scenario_record.scenario_id if active_scenario_record else None
        bound_scenario_name = active_scenario_record.scenario_name if active_scenario_record else None

        # Persist (note: legacy /run passes runtime_snapshot through unchanged here;
        # the gate is only applied for the template-seeded and generic paths).
        replay_metadata = deps.replay_metadata_for_project(
            project_record.project_code,
            project_id=project_record.project_id,
            scenario_id=bound_scenario_id if effective_runtime_origin == "saved_state" else None,
            scenario_name=active_scenario_record.scenario_name if active_scenario_record else scenario_name,
            runtime_timestamp=_utc_now_iso_full_iso(),
            runtime_snapshot_id=runtime_snapshot_id,
            export_type="workspace_runtime_state",
            active_scenario_id=bound_scenario_id if effective_runtime_origin == "saved_state" else None,
            active_scenario_name=bound_scenario_name if effective_runtime_origin == "saved_state" else None,
            scenario_provenance=scenario_provenance,
            warning_note=runtime_warning,
        )
        deps.record_workspace_runtime(
            user_id=user.user_id,
            project_id=project_record.project_id,
            project_code=project_record.project_code,
            runtime_snapshot=runtime_snapshot,
            runtime_summary=result["kpis"],
            runtime_snapshot_id=runtime_snapshot_id,
            runtime_origin=effective_runtime_origin,
            governance_state=deps.governance_snapshot(project_record.project_code),
            active_scenario_id=bound_scenario_id if effective_runtime_origin == "saved_state" else None,
            active_scenario_name=bound_scenario_name if effective_runtime_origin == "saved_state" else None,
            replay_metadata=replay_metadata,
        )
        if effective_runtime_origin == "saved_state" and bound_scenario_id:
            scenario_replay = deps.replay_metadata_for_project(
                project_record.project_code,
                project_id=project_record.project_id,
                scenario_id=workspace_state.active_scenario_id,
                scenario_name=active_scenario_record.scenario_name if active_scenario_record else scenario_name,
                runtime_timestamp=_utc_now_iso_full_iso(),
                runtime_snapshot_id=runtime_snapshot_id,
                export_type="scenario_runtime_summary",
                active_scenario_id=bound_scenario_id,
                active_scenario_name=bound_scenario_name,
                scenario_provenance=scenario_provenance,
                warning_note=runtime_warning,
            )
            deps.update_scenario_last_run_summary(
                user.user_id, bound_scenario_id, result["kpis"], replay_metadata=scenario_replay,
            )

        result_messages = list(result.get("messages", []))
        if runtime_warning:
            result_messages.append(runtime_warning)

        prepend_html = _build_sessionstorage_save_tag(
            runtime_summary=runtime_summary,
            runtime_origin=runtime_origin,
            workspace_state=workspace_state,
            runtime_snapshot_id=runtime_snapshot_id,
        )
        return RunRouteOutcome(
            template_name="partials/runtime_summary.html",
            context={
                "kpis": kpis,
                "runtime_summary": runtime_summary,
                "run_data": {"project_type": project_record.project_type, "scenario": scenario_name},
                "messages": result_messages,
                "integration_status": result.get("integration_status", "full"),
            },
            prepend_html=prepend_html,
        )
    except deps.snapshot_input_error as e:  # type: ignore[misc]
        return RunRouteOutcome(
            template_name="partials/errors.html",
            context={"errors": [str(e)]},
        )
    except Exception as e:  # noqa: BLE001
        return RunRouteOutcome(
            template_name="partials/errors.html",
            context={"errors": [f"Model error ({project_record.project_code}): {str(e)}"]},
        )


async def _execute_template_seeded_path(
    *,
    request,
    user,
    snapshot: dict,
    scenario: str,
    project_record,
    workspace_state,
    runtime_snapshot: Optional[dict],
    active_scenario_record,
    runtime_warning: Optional[str],
    runtime_origin: str,
    capacity_mw, tariff_eur_mwh, p50_hours, total_capex_keur, opex_y1_keur,
    gearing_pct, target_dscr, interest_rate_pct, tenor_years,
    runtime_seed: str,
    deps: RunRouteDeps,
) -> RunRouteOutcome:
    """TUHO/Oborovo template-seeded path (existing factory flow)."""
    try:
        project_key = "TUHO" if runtime_seed == "tuho" else "Oborovo"
        scenario_name = snapshot.get("scenario", "") or "Base"
        if runtime_snapshot and runtime_origin == "saved_state" and workspace_state.active_scenario_id:
            override = deps.build_projectinputs_from_snapshot(runtime_snapshot)
        else:
            project_type = project_record.project_type or deps.default_workspace_snapshot(runtime_seed)["project_type"]
            schema = deps.build_schema_from_form(
                project_type, scenario_name, capacity_mw, tariff_eur_mwh, p50_hours,
                total_capex_keur, opex_y1_keur, gearing_pct, target_dscr,
                interest_rate_pct, tenor_years,
            )
            override = deps.build_projectinputs(schema)
        result = deps.run_project(project_key, scenario_name, project_inputs_override=override)
        kpis = deps.format_kpis(result["kpis"])
        runtime_summary = deps.runtime_summary_to_dict(result, project_record.project_code, project_record.project_name)
        runtime_snapshot_id = _utc_now_iso_compact()
        scenario_provenance = deps.scenario_provenance_for_record(project_record, active_scenario_record)
        bound_scenario_id = active_scenario_record.scenario_id if active_scenario_record else None
        bound_scenario_name = active_scenario_record.scenario_name if active_scenario_record else None

        # Persist (template-seeded gates runtime_snapshot on saved_state).
        replay_metadata = deps.replay_metadata_for_project(
            project_record.project_code,
            project_id=project_record.project_id,
            scenario_id=bound_scenario_id if runtime_origin == "saved_state" else None,
            scenario_name=active_scenario_record.scenario_name if active_scenario_record else scenario_name,
            runtime_timestamp=_utc_now_iso_full_iso(),
            runtime_snapshot_id=runtime_snapshot_id,
            export_type="workspace_runtime_state",
            active_scenario_id=bound_scenario_id if runtime_origin == "saved_state" else None,
            active_scenario_name=bound_scenario_name if runtime_origin == "saved_state" else None,
            scenario_provenance=scenario_provenance,
            warning_note=runtime_warning,
        )
        deps.record_workspace_runtime(
            user_id=user.user_id,
            project_id=project_record.project_id,
            project_code=project_record.project_code,
            runtime_snapshot=runtime_snapshot if runtime_snapshot and runtime_origin == "saved_state" else snapshot,
            runtime_summary=result["kpis"],
            runtime_snapshot_id=runtime_snapshot_id,
            runtime_origin=runtime_origin,
            governance_state=deps.governance_snapshot(project_record.project_code),
            active_scenario_id=bound_scenario_id if runtime_origin == "saved_state" else None,
            active_scenario_name=bound_scenario_name if runtime_origin == "saved_state" else None,
            replay_metadata=replay_metadata,
        )
        if runtime_origin == "saved_state" and bound_scenario_id:
            scenario_replay = deps.replay_metadata_for_project(
                project_record.project_code,
                project_id=project_record.project_id,
                scenario_id=workspace_state.active_scenario_id,
                scenario_name=active_scenario_record.scenario_name if active_scenario_record else scenario_name,
                runtime_timestamp=_utc_now_iso_full_iso(),
                runtime_snapshot_id=runtime_snapshot_id,
                export_type="scenario_runtime_summary",
                active_scenario_id=bound_scenario_id,
                active_scenario_name=bound_scenario_name,
                scenario_provenance=scenario_provenance,
                warning_note=runtime_warning,
            )
            deps.update_scenario_last_run_summary(
                user.user_id, bound_scenario_id, result["kpis"], replay_metadata=scenario_replay,
            )

        result_messages = list(result.get("messages", []))
        if runtime_warning:
            result_messages.append(runtime_warning)

        prepend_html = _build_sessionstorage_save_tag(
            runtime_summary=runtime_summary,
            runtime_origin=runtime_origin,
            workspace_state=workspace_state,
            runtime_snapshot_id=runtime_snapshot_id,
        )
        return RunRouteOutcome(
            template_name="partials/runtime_summary.html",
            context={
                "kpis": kpis,
                "runtime_summary": runtime_summary,
                "run_data": {"project_type": project_record.project_type or runtime_seed.title(), "scenario": scenario_name},
                "messages": result_messages,
                "integration_status": result.get("integration_status", "full"),
            },
            prepend_html=prepend_html,
        )
    except Exception as e:  # noqa: BLE001
        return RunRouteOutcome(
            template_name="partials/errors.html",
            context={"errors": [f"Model error ({project_record.project_code}): {str(e)}"]},
        )


async def _execute_generic_path(
    *,
    request,
    user,
    snapshot: dict,
    scenario: str,
    project_record,
    workspace_state,
    runtime_snapshot: Optional[dict],
    active_scenario_record,
    runtime_warning: Optional[str],
    runtime_origin: str,
    project_type, capacity_mw, tariff_eur_mwh, p50_hours, total_capex_keur, opex_y1_keur,
    gearing_pct, target_dscr, interest_rate_pct, tenor_years,
    deps: RunRouteDeps,
) -> RunRouteOutcome:
    """Generic template-seeded path (kpis.html output, no sessionStorage script)."""
    errors: list[str] = []
    effective_project_type = project_record.project_type or project_type
    if not deps.validate_form(effective_project_type, scenario, errors):
        return RunRouteOutcome(
            template_name="partials/errors.html",
            context={"errors": errors},
        )

    try:
        if runtime_snapshot and runtime_origin == "saved_state" and workspace_state.active_scenario_id:
            override = deps.build_projectinputs_from_snapshot(runtime_snapshot)
            scenario_name = scenario
        else:
            try:
                schema = deps.build_schema_from_form(
                    effective_project_type, scenario, capacity_mw, tariff_eur_mwh, p50_hours,
                    total_capex_keur, opex_y1_keur, gearing_pct, target_dscr,
                    interest_rate_pct, tenor_years,
                )
            except ValueError as ve:
                return RunRouteOutcome(
                    template_name="partials/errors.html",
                    context={"errors": [str(ve)]},
                )
            override = deps.build_projectinputs(schema)
            scenario_name = scenario
        runtime_project_key = (
            "Solar" if deps.canonical_project_type(effective_project_type) == "Solar" else "Wind"
        )
        result = deps.run_project(runtime_project_key, scenario_name, project_inputs_override=override)
        kpis = deps.format_kpis(result["kpis"])
        runtime_snapshot_id = _utc_now_iso_compact()
        scenario_provenance = deps.scenario_provenance_for_record(project_record, active_scenario_record)
        bound_scenario_id = active_scenario_record.scenario_id if active_scenario_record else None
        bound_scenario_name = active_scenario_record.scenario_name if active_scenario_record else None

        # Persist (generic path: same gate as template-seeded on saved_state).
        replay_metadata = deps.replay_metadata_for_project(
            project_record.project_code,
            project_id=project_record.project_id,
            scenario_id=bound_scenario_id if runtime_origin == "saved_state" else None,
            scenario_name=active_scenario_record.scenario_name if active_scenario_record else scenario_name,
            runtime_timestamp=_utc_now_iso_full_iso(),
            runtime_snapshot_id=runtime_snapshot_id,
            export_type="workspace_runtime_state",
            active_scenario_id=bound_scenario_id if runtime_origin == "saved_state" else None,
            active_scenario_name=bound_scenario_name if runtime_origin == "saved_state" else None,
            scenario_provenance=scenario_provenance,
            warning_note=runtime_warning,
        )
        deps.record_workspace_runtime(
            user_id=user.user_id,
            project_id=project_record.project_id,
            project_code=project_record.project_code,
            runtime_snapshot=runtime_snapshot if runtime_snapshot and runtime_origin == "saved_state" else snapshot,
            runtime_summary=result["kpis"],
            runtime_snapshot_id=runtime_snapshot_id,
            runtime_origin=runtime_origin,
            governance_state=deps.governance_snapshot(project_record.project_code),
            active_scenario_id=bound_scenario_id if runtime_origin == "saved_state" else None,
            active_scenario_name=bound_scenario_name if runtime_origin == "saved_state" else None,
            replay_metadata=replay_metadata,
        )
        if runtime_origin == "saved_state" and bound_scenario_id:
            scenario_replay = deps.replay_metadata_for_project(
                project_record.project_code,
                project_id=project_record.project_id,
                scenario_id=workspace_state.active_scenario_id,
                scenario_name=active_scenario_record.scenario_name if active_scenario_record else scenario_name,
                runtime_timestamp=_utc_now_iso_full_iso(),
                runtime_snapshot_id=runtime_snapshot_id,
                export_type="scenario_runtime_summary",
                active_scenario_id=bound_scenario_id,
                active_scenario_name=bound_scenario_name,
                scenario_provenance=scenario_provenance,
                warning_note=runtime_warning,
            )
            deps.update_scenario_last_run_summary(
                user.user_id, bound_scenario_id, result["kpis"], replay_metadata=scenario_replay,
            )

        result_messages = list(result.get("messages", []))
        if runtime_warning:
            result_messages.append(runtime_warning)

        return RunRouteOutcome(
            template_name="partials/kpis.html",
            context={
                "kpis": kpis,
                "run_data": {
                    "project_type": effective_project_type,
                    "scenario": scenario_name,
                    "capacity_mw": capacity_mw,
                    "tariff_eur_mwh": tariff_eur_mwh,
                    "total_capex_keur": total_capex_keur,
                    "gearing_pct": gearing_pct,
                },
                "messages": result_messages,
                "integration_status": result.get("integration_status", "full"),
            },
        )
    except Exception as e:  # noqa: BLE001
        return RunRouteOutcome(
            template_name="partials/errors.html",
            context={"errors": [f"Model error: {str(e)}"]},
        )


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers (NOT part of public API)
# ─────────────────────────────────────────────────────────────────────────────


def _utc_now_iso_compact() -> str:
    """Return a UTC ISO string with ``:`` and ``-`` removed (matches legacy)."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat().replace(":", "").replace("-", "")


def _utc_now_iso_full_iso() -> str:
    """Full ISO-8601 UTC string (with ``:`` and ``-``)."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _build_sessionstorage_save_tag(
    *,
    runtime_summary: dict,
    runtime_origin: str,
    workspace_state,
    runtime_snapshot_id: str,
) -> str:
    """Return the sessionStorage save ``<script>`` block.

    Preserves the legacy per-origin ``dirty`` / ``dirty_label`` /
    ``last_runtime_origin_label`` logic from the original /run route.
    The route in main_web.py decides whether to inject this after
    ``<body`` (for the ``<!DOCTYPE`` template-seeded flow) or to
    prepend it directly to the body (for the user_created flow).
    """
    if runtime_origin in ("saved_state", "workspace_base"):
        is_clean = True
    else:
        is_clean = False
    if runtime_origin == "saved_state":
        dirty_label = "Clean saved state"
    elif runtime_origin == "workspace_base":
        dirty_label = "Clean workspace base"
    else:
        dirty_label = "Unsaved edits"
    if runtime_origin == "saved_state":
        last_origin_label = "Runtime bound to saved scenario snapshot"
    elif runtime_origin == "workspace_base":
        last_origin_label = "Runtime bound to clean workspace base"
    else:
        last_origin_label = "Runtime bound to clean workspace base"
    return (
        '<script>'
        'sessionStorage.setItem("lastRuntimeSummary", ' + json.dumps(runtime_summary) + ');'
        'window.applyWorkspaceStateMeta && window.applyWorkspaceStateMeta(' + json.dumps({
            "dirty": False if is_clean else True,
            "dirty_label": dirty_label,
            "active_scenario_id": getattr(workspace_state, "active_scenario_id", "") or "",
            "active_scenario_name": getattr(workspace_state, "active_scenario_name", "") or "",
            "last_runtime_origin": runtime_origin,
            "last_runtime_origin_label": last_origin_label,
            "last_runtime_snapshot_id": runtime_snapshot_id,
        }) + ');'
        'window._populateRuntimeBlock && window._populateRuntimeBlock();'
        '</script>'
    )


# ─────────────────────────────────────────────────────────────────────────────
# Public type aliases
# ─────────────────────────────────────────────────────────────────────────────

# These are intentionally loose: we accept anything with a __getattr__/form
# interface, including FastAPI's awaitable form. Keeping them as aliases
# avoids forcing ``fastapi.Request`` to be imported here.
RequestLike = Any
FormLike = Any
