"""Project persistence functions extracted from app/persistence/repository.py.

This module holds Group A (project) persistence functions extracted
during Phase 53D (A-reads) and Phase 53E-2 (A-2 writes). The
functions are re-exported from app.persistence.repository for
backward compatibility.

Function inventory (Group A-reads, Phase 53D):

- get_project
- get_project_by_code
- list_projects
- list_baseline_records
- get_project_record
- list_project_records

Function inventory (Group A-2 writes, Phase 53E-2):

- save_project
- create_project_record
- update_project_record
- seed_baseline_projects_if_needed
- _compute_baseline_snapshot
- _build_default_snapshot
- _fill_missing_defaults

(Additional private helper _sum_opex is defined inside
_compute_baseline_snapshot as a nested function and moves with it.)

ProjectRecord is a dataclass defined inside app.persistence.repository.
It is shared with the read functions and is referenced via
TYPE_CHECKING + runtime lazy import to avoid circular import at
module load time. The class itself is not moved in this phase.

Behavior is preserved exactly as it was in repository.py. The only
change is the file location.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from app.persistence._helpers import _from_iso, _from_json, _now_utc, _to_json
from app.persistence.db import get_cursor

if TYPE_CHECKING:
    from app.persistence.records import ProjectRecord


# ===========================================================================
# Group A-reads (Phase 53D)
# ===========================================================================


def get_project(project_id: str, user_id: str) -> "Optional[ProjectRecord]":
    with get_cursor() as cur:
        cur.execute("SELECT * FROM projects WHERE project_id=? AND user_id=?", (project_id, user_id))
        row = cur.fetchone()
    from app.persistence.records import ProjectRecord
    return ProjectRecord.from_row(row) if row else None


def get_project_by_code(user_id: str, project_code: str) -> "Optional[ProjectRecord]":
    with get_cursor() as cur:
        cur.execute(
            "SELECT * FROM projects WHERE user_id=? AND project_code=?",
            (user_id, project_code),
        )
        row = cur.fetchone()
    from app.persistence.records import ProjectRecord
    return ProjectRecord.from_row(row) if row else None


def list_projects(user_id: str) -> "list[ProjectRecord]":
    with get_cursor() as cur:
        cur.execute(
            "SELECT * FROM projects WHERE user_id=? AND archived=0 ORDER BY updated_at DESC",
            (user_id,),
        )
        from app.persistence.records import ProjectRecord
        return [ProjectRecord.from_row(row) for row in cur.fetchall()]


def list_baseline_records(user_id: str) -> "list[ProjectRecord]":
    """Return saved-baseline records (project_origin='saved_baseline') for a user."""
    with get_cursor() as cur:
        cur.execute(
            "SELECT * FROM projects WHERE user_id=? AND project_origin='saved_baseline' AND archived=0 ORDER BY project_name",
            (user_id,),
        )
        from app.persistence.records import ProjectRecord
        return [ProjectRecord.from_row(row) for row in cur.fetchall()]


def get_project_record(
    *,
    user_id: str,
    project_id: Optional[str] = None,
    project_code: Optional[str] = None,
) -> "Optional[ProjectRecord]":
    if project_id:
        return get_project(project_id, user_id)
    if project_code:
        return get_project_by_code(user_id, project_code)
    return None


def list_project_records(
    *,
    user_id: str,
    include_archived: bool = False,
) -> "list[ProjectRecord]":
    query = "SELECT * FROM projects WHERE user_id=?"
    params: list[Any] = [user_id]
    if not include_archived:
        query += " AND archived=0"
    query += " ORDER BY updated_at DESC"
    with get_cursor() as cur:
        cur.execute(query, tuple(params))
        from app.persistence.records import ProjectRecord
        return [ProjectRecord.from_row(row) for row in cur.fetchall()]


# ===========================================================================
# Group A-2 writes (Phase 53E-2)
# ===========================================================================


def save_project(
    user_id: str,
    project_code: str,
    project_name: str,
    source_project_template: str,
    project_type: Optional[str] = None,
    project_origin: str = "factory_template",
    template_source: Optional[str] = None,
    baseline_snapshot: Optional[dict[str, Any]] = None,
    archived: bool = False,
    is_readonly: bool = False,
    governance_state: Optional[dict[str, Any]] = None,
    last_run_summary: Optional[dict[str, Any]] = None,
    replay_metadata: Optional[dict[str, Any]] = None,
    capex_sub_lines: Optional[list] = None,
) -> "ProjectRecord":
    now = _now_utc()
    governance_state = governance_state or {}
    last_run_summary = last_run_summary or {}
    baseline_snapshot = baseline_snapshot or {}
    replay_metadata = dict(replay_metadata or {})
    effective_template_source = template_source or source_project_template

    with get_cursor() as cur:
        cur.execute(
            """
            SELECT project_id, created_at, project_type, project_origin, template_source, baseline_snapshot_json, archived
            FROM projects
            WHERE user_id=? AND project_code=?
            """,
            (user_id, project_code),
        )
        existing = cur.fetchone()
        if existing:
            project_id = existing["project_id"]
            created_at = _from_iso(existing["created_at"])
            project_type = project_type or existing["project_type"]
            project_origin = project_origin or existing["project_origin"] or "factory_template"
            effective_template_source = effective_template_source or existing["template_source"] or source_project_template
            if not baseline_snapshot:
                baseline_snapshot = _from_json(existing["baseline_snapshot_json"], {})
            archived = bool(existing["archived"]) if archived is None else archived
            replay_metadata.setdefault("project_id", project_id)
            cur.execute(
                """
                UPDATE projects
                SET project_name=?, project_type=?, project_origin=?, source_project_template=?, template_source=?,
                    baseline_snapshot_json=?, archived=?, is_readonly=?, governance_state_json=?, last_run_summary_json=?,
                    replay_metadata_json=?, updated_at=?
                WHERE project_id=? AND user_id=?
                """,
                (
                    project_name,
                    project_type,
                    project_origin,
                    source_project_template,
                    effective_template_source,
                    _to_json(baseline_snapshot),
                    int(bool(archived)),
                    int(bool(is_readonly)),
                    _to_json(governance_state),
                    _to_json(last_run_summary),
                    _to_json(replay_metadata),
                    now.isoformat(),
                    project_id,
                    user_id,
                ),
            )
        else:
            project_id = uuid.uuid4().hex[:16]
            created_at = now
            replay_metadata.setdefault("project_id", project_id)
            cur.execute(
                """
                INSERT INTO projects (
                    project_id, user_id, project_code, project_name, project_type, project_origin,
                    source_project_template, template_source, baseline_snapshot_json, archived, is_readonly,
                    governance_state_json, last_run_summary_json, replay_metadata_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    user_id,
                    project_code,
                    project_name,
                    project_type,
                    project_origin,
                    source_project_template,
                    effective_template_source,
                    _to_json(baseline_snapshot),
                    int(bool(archived)),
                    int(bool(is_readonly)),
                    _to_json(governance_state),
                    _to_json(last_run_summary),
                    _to_json(replay_metadata),
                    created_at.isoformat(),
                    now.isoformat(),
                ),
            )

        # Phase 57A-9C: optionally replace the project's
        # user-added CAPEX sub-lines. This happens in the
        # same transaction as the project row write so a
        # partial failure rolls back both. Soft-delete +
        # re-insert preserves UUIDs for round-trips.
        if capex_sub_lines is not None:
            from app.persistence.records import ProjectRecord
            from app.persistence.capex_sub_lines import (
                assert_project_allows_capex_sub_lines,
                replace_sub_lines_for_project,
            )
            # Defense in depth: factory_template projects
            # cannot have sub-lines. The helper below is the
            # single source of truth for this invariant.
            project_record_for_guard = ProjectRecord(
                project_id=project_id,
                user_id=user_id,
                project_code=project_code,
                project_name=project_name,
                project_type=project_type,
                project_origin=project_origin,
                source_project_template=source_project_template,
                template_source=effective_template_source,
                baseline_snapshot=baseline_snapshot,
                archived=bool(archived),
                is_readonly=bool(is_readonly),
                governance_state=governance_state,
                last_run_summary=last_run_summary,
                replay_metadata=replay_metadata,
                created_at=created_at,
                updated_at=now,
            )
            from app.persistence.capex_sub_lines import (
                assert_project_allows_capex_sub_lines,
                replace_sub_lines_for_project,
            )
            assert_project_allows_capex_sub_lines(project_record_for_guard)
            replace_sub_lines_for_project(
                cur,
                project_id=project_id,
                sub_lines=capex_sub_lines,
            )

    from app.persistence.records import ProjectRecord
    return ProjectRecord(
        project_id=project_id,
        user_id=user_id,
        project_code=project_code,
        project_name=project_name,
        project_type=project_type,
        project_origin=project_origin,
        source_project_template=source_project_template,
        template_source=effective_template_source,
        baseline_snapshot=baseline_snapshot,
        archived=bool(archived),
        is_readonly=is_readonly,
        governance_state=governance_state,
        last_run_summary=last_run_summary,
        replay_metadata=replay_metadata,
        created_at=created_at,
        updated_at=now,
    )


def create_project_record(
    *,
    user_id: str,
    project_code: str,
    project_name: str,
    project_type: str,
    project_origin: str,
    template_source: str,
    baseline_snapshot: dict[str, Any],
    governance_state: Optional[dict[str, Any]] = None,
    last_run_summary: Optional[dict[str, Any]] = None,
    replay_metadata: Optional[dict[str, Any]] = None,
    is_readonly: bool = False,
) -> "ProjectRecord":
    return save_project(
        user_id=user_id,
        project_code=project_code,
        project_name=project_name,
        project_type=project_type,
        project_origin=project_origin,
        source_project_template=template_source,
        template_source=template_source,
        baseline_snapshot=baseline_snapshot,
        governance_state=governance_state,
        last_run_summary=last_run_summary,
        replay_metadata=replay_metadata,
        is_readonly=is_readonly,
    )


def update_project_record(
    *,
    user_id: str,
    project_code: str,
    project_name: Optional[str] = None,
    project_type: Optional[str] = None,
    template_source: Optional[str] = None,
    baseline_snapshot: Optional[dict[str, Any]] = None,
    archived: Optional[bool] = None,
    governance_state: Optional[dict[str, Any]] = None,
    last_run_summary: Optional[dict[str, Any]] = None,
    replay_metadata: Optional[dict[str, Any]] = None,
) -> "Optional[ProjectRecord]":
    existing = get_project_by_code(user_id, project_code)
    if existing is None:
        return None
    return save_project(
        user_id=user_id,
        project_code=existing.project_code,
        project_name=project_name or existing.project_name,
        project_type=project_type or existing.project_type,
        project_origin=existing.project_origin,
        source_project_template=template_source or existing.source_project_template,
        template_source=template_source or existing.template_source or existing.source_project_template,
        baseline_snapshot=baseline_snapshot if baseline_snapshot is not None else existing.baseline_snapshot,
        archived=existing.archived if archived is None else archived,
        governance_state=governance_state or existing.governance_state,
        last_run_summary=last_run_summary or existing.last_run_summary,
        replay_metadata=replay_metadata or existing.replay_metadata,
    )


def seed_baseline_projects_if_needed(user_id: str) -> "list[ProjectRecord]":
    """
    Ensure TUHO Baseline and Oborovo Baseline exist for user.
    Idempotent — does not overwrite existing baseline records.
    """
    seeded = []
    for code, name, project_type, template_source in [
        ("tuho-baseline", "TUHO — Baseline", "Wind", "tuho"),
        ("oborovo-baseline", "Oborovo — Baseline", "Solar", "oborovo"),
    ]:
        existing = get_project_by_code(user_id, code)
        if existing is not None:
            continue  # already exists
        snapshot = _compute_baseline_snapshot(project_type, template_source)
        record = save_project(
            user_id=user_id,
            project_code=code,
            project_name=name,
            project_type=project_type,
            project_origin="saved_baseline",
            source_project_template=template_source,
            template_source=template_source,
            baseline_snapshot=snapshot,
            is_readonly=True,
            governance_state={"g20": "BLOCKED", "r99_r102": "NOT_APPROVED", "lender_ready": False},
        )
        seeded.append(record)
    return seeded


def _compute_baseline_snapshot(project_type: str, template_source: str) -> dict[str, Any]:
    """
    Build a workspace-ready snapshot dict for a saved baseline project.
    Mirrors the logic in main_web._project_baseline_snapshot.
    """
    from app.project_factories import (
        create_default_tuho_wind1,
        create_default_oborovo,
        create_default_wind_project,
        create_default_solar_project,
    )
    from app.persistence.db import get_cursor

    canonical_type = project_type
    normalized_source = template_source

    baseline = {
        "active_project": "",
        "project_name": "",
        "project_type": canonical_type,
        "project_origin": "saved_baseline",
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

    def _sum_opex(items):
        """Sum y1_amount_keur from an opex iterable."""
        total = 0.0
        for item in items:
            total += float(getattr(item, "y1_amount_keur", 0) or 0)
        return total

    if normalized_source == "tuho":
        pi = create_default_tuho_wind1()
        baseline.update({
            "active_project": "tuho-baseline",
            "project_name": pi.info.name,
            "project_type": "Wind",
            "template_source": "tuho",
            "country_market": pi.info.country_iso,
            "capacity_mw": str(pi.technical.capacity_mw),
            "tariff_eur_mwh": str(pi.revenue.ppa_base_tariff),
            "p50_hours": str(pi.technical.operating_hours_p50),
            "total_capex_keur": str(pi.capex.total_capex),
            "opex_y1_keur": str(_sum_opex(pi.opex)),
            "target_dscr": str(pi.financing.target_dscr),
            "interest_rate_pct": str(pi.financing.base_rate + pi.financing.margin_bps / 10_000),
            "tenor_years": str(pi.financing.senior_tenor_years),
            "cod_date": str(pi.info.cod_date),
            "construction_months": str(pi.info.construction_months),
            "horizon_years": str(pi.info.horizon_years),
            "capacity_factor": f"{(pi.technical.operating_hours_p50 / 8760) * 100:.2f}",
            "ppa_term_years": str(int(pi.revenue.ppa_term_years)),
        })
        return baseline

    if normalized_source == "oborovo":
        pi = create_default_oborovo()
        baseline.update({
            "active_project": "oborovo-baseline",
            "project_name": pi.info.name,
            "project_type": "Solar",
            "template_source": "oborovo",
            "country_market": pi.info.country_iso,
            "capacity_mw": str(pi.technical.capacity_mw),
            "tariff_eur_mwh": str(pi.revenue.ppa_base_tariff),
            "p50_hours": str(pi.technical.operating_hours_p50),
            "total_capex_keur": str(pi.capex.total_capex),
            "opex_y1_keur": str(_sum_opex(pi.opex)),
            "gearing_pct": str(float(getattr(pi.financing, "gearing_ratio", 0.0) or 0.0) * 100),
            "target_dscr": str(pi.financing.target_dscr),
            "interest_rate_pct": str(pi.financing.base_rate + pi.financing.margin_bps / 10_000),
            "tenor_years": str(pi.financing.senior_tenor_years),
            "cod_date": str(pi.info.cod_date),
            "construction_months": str(pi.info.construction_months),
            "horizon_years": str(pi.info.horizon_years),
            "capacity_factor": f"{(pi.technical.operating_hours_p50 / 8760) * 100:.2f}",
            "ppa_term_years": str(int(pi.revenue.ppa_term_years)),
        })
        return baseline

    # generic_wind / generic_solar fallback
    if canonical_type == "Solar":
        pi = create_default_solar_project()
    else:
        pi = create_default_wind_project()
    baseline.update({
        "active_project": normalized_source,
        "project_name": pi.info.name,
        "template_source": normalized_source,
        "country_market": pi.info.country_iso,
        "capacity_mw": str(pi.technical.capacity_mw),
        "tariff_eur_mwh": str(pi.revenue.ppa_base_tariff),
        "p50_hours": str(pi.technical.operating_hours_p50),
        "total_capex_keur": str(pi.capex.total_capex),
        "opex_y1_keur": str(_sum_opex(pi.opex)),
        "gearing_pct": str(float(getattr(pi.financing, "gearing_ratio", 0.0) or 0.0) * 100),
        "target_dscr": str(pi.financing.target_dscr),
        "interest_rate_pct": str(pi.financing.base_rate + pi.financing.margin_bps / 10_000),
        "tenor_years": str(pi.financing.senior_tenor_years),
        "cod_date": str(pi.info.cod_date),
        "construction_months": str(pi.info.construction_months),
        "horizon_years": str(pi.info.horizon_years),
        "capacity_factor": f"{(pi.technical.operating_hours_p50 / 8760) * 100:.2f}",
        "ppa_term_years": str(int(pi.revenue.ppa_term_years)),
    })
    return baseline


def _build_default_snapshot(project_code: str, defaults: dict[str, Any]) -> dict[str, Any]:
    """Build a workspace-ready snapshot from factory defaults."""
    from app.input_adapter import build_projectinputs_from_snapshot
    snapshot = dict(defaults)
    snapshot["active_project"] = project_code
    snapshot["project_origin"] = "saved_baseline"
    # Ensure runtime-usable fields are present
    _fill_missing_defaults(snapshot)
    return snapshot


def _fill_missing_defaults(snapshot: dict[str, Any]) -> None:
    """Ensure required snapshot fields exist with safe defaults."""
    defaults = {
        "scenario": "Base",
        "project_type": "Wind",
        "capacity_mw": 50.0,
        "p50_hours": 2500.0,
        "tariff_eur_mwh": 80.0,
        "total_capex_keur": 50000.0,
        "opex_y1_keur": 5000.0,
        "gearing_pct": 75.0,
        "target_dscr": 1.4,
        "interest_rate_pct": 7.0,
        "tenor_years": 20,
    }
    for k, v in defaults.items():
        if k not in snapshot:
            snapshot[k] = v


# ============================================================
# Phase 57A-9C: CAPEX sub-lines load wiring
# ============================================================


def get_project_with_sub_lines(
    user_id: str,
    project_code: str,
    include_inactive_sub_lines: bool = False,
) -> "tuple[Optional[ProjectRecord], tuple[Any, ...]]":
    """Load a project and its CAPEX sub-lines in one call.

    Returns a ``(project_record, sub_lines)`` tuple. ``project_record``
    is ``None`` if no project exists for the given
    (user_id, project_code). The ``sub_lines`` tuple is empty
    for projects that have no user-added sub-lines (the
    typical case for factory-template projects).

    Soft-deleted sub-lines are excluded by default; pass
    ``include_inactive_sub_lines=True`` to include them (for
    audit / replay).

    The sub-lines are returned in the canonical order
    ``(parent_category_code ASC, display_order ASC)`` — the
    same order used by the LineItemGrid render path. The
    caller can use this order directly without re-sorting.
    """
    project_record = get_project_by_code(user_id, project_code)
    if project_record is None:
        return None, ()
    from app.persistence.capex_sub_lines import (
        list_sub_lines_for_project,
    )
    with get_cursor() as cur:
        sub_lines = list_sub_lines_for_project(
            cur,
            project_record.project_id,
            include_inactive=include_inactive_sub_lines,
        )
    return project_record, sub_lines


def get_project_by_id_with_sub_lines(
    project_id: str,
    user_id: str,
    include_inactive_sub_lines: bool = False,
) -> "tuple[Optional[Any], tuple[Any, ...]]":
    """Same as ``get_project_with_sub_lines`` but by ``project_id``."""
    from app.persistence.capex_sub_lines import (
        list_sub_lines_for_project,
    )
    with get_cursor() as cur:
        cur.execute(
            "SELECT * FROM projects WHERE project_id=? AND user_id=?",
            (project_id, user_id),
        )
        row = cur.fetchone()
    if row is None:
        return None, ()
    from app.persistence.records import ProjectRecord
    project_record = ProjectRecord.from_row(row)
    with get_cursor() as cur:
        sub_lines = list_sub_lines_for_project(
            cur,
            project_id,
            include_inactive=include_inactive_sub_lines,
        )
    return project_record, sub_lines
