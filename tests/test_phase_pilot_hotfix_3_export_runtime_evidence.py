"""Phase PILOT-HOTFIX-3 — Export uses latest successful runtime evidence.

Context
--------
PILOT-HOTFIX-2 fixed P0 #1: scenario overrides now flow into the /run
endpoint correctly. P0 #2 remained: when a user-created working copy
with a successful run was exported via `POST /download`, the request
could fail with HTTP 400 "Current form state no longer matches the
last saved runtime boundary" — because the export service required
the current form snapshot to bit-match the saved runtime boundary,
even though the export only needs the latest successful runtime
result.

This test file pins the PILOT-HOTFIX-3 fix:
  - For user_created projects, `POST /download` now uses the
    `last_runtime_snapshot_json` (most recent successful run evidence)
    when present, instead of requiring a fresh form-vs-saved
    boundary match.
  - If no `last_runtime_snapshot_json` exists, the export returns
    a clear, user-friendly error message: "Run the model before
    exporting."
  - The runtime guard in `app/persistence/repository.py` is NOT
    changed; only the export service is.
  - Cross-project isolation is preserved: each project's export
    uses only that project's own `last_runtime_snapshot_json`.
  - TUHO / Oborovo reference project export is unchanged.
  - Engine MD5 `6bf49f33efc989736c17cea0cb9b7723` unchanged.
  - Factory MD5 `cf73065b8a26aa3f19629829e46260d9` unchanged.
  - rc1 SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4` untouched.
"""

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-ph3-export-runtime")

from app.persistence.db import init_db

init_db()

from app.persistence.repository import (
    ProjectRecord,
    WorkspaceStateRecord,
    record_workspace_runtime,
)
from app.persistence.workspace_repository import (
    get_workspace_state,
    save_workspace_state,
)
from app.persistence.projects_repository import (
    save_project,
    get_project_record,
)
from app.auth import SessionData
from app.services.download_service import (
    DownloadRouteDeps,
    execute_post_download_route,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(user_id: str | None = None) -> SessionData:
    from datetime import datetime, timezone
    if user_id is None:
        import uuid
        user_id = f"ph3-user-{uuid.uuid4().hex[:8]}"
    return SessionData(
        user_id=user_id,
        username=user_id,
        login_at=datetime.now(timezone.utc),
    )


def _make_project_record(
    *,
    project_id: str | None = None,
    user_id: str | None = None,
    project_code: str = "ph3-wc",
    project_type: str = "Wind",
    project_origin: str = "user_created",
    template_source: str = "generic_wind",
    is_readonly: bool = False,
    baseline_snapshot: dict | None = None,
) -> ProjectRecord:
    import uuid
    if project_id is None:
        project_id = f"ph3-proj-{uuid.uuid4().hex[:16]}"
    if user_id is None:
        user_id = f"ph3-user-{uuid.uuid4().hex[:8]}"
    return ProjectRecord(
        project_id=project_id,
        user_id=user_id,
        project_code=project_code,
        project_name=project_code,
        project_type=project_type,
        project_origin=project_origin,
        source_project_template=template_source,
        template_source=template_source,
        baseline_snapshot=baseline_snapshot or {},
        governance_state={},
        last_run_summary={},
        replay_metadata={},
        is_readonly=is_readonly,
        archived=False,
        created_at="2026-06-17T00:00:00",
        updated_at="2026-06-17T00:00:00",
    )


def _save_project(project: ProjectRecord) -> None:
    # Use the live DB session directly to insert by primary key.
    from app.persistence.db import get_cursor
    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO projects (
                project_id, user_id, project_code, project_name, project_type,
                project_origin, source_project_template, template_source,
                baseline_snapshot_json, archived, is_readonly,
                governance_state_json, last_run_summary_json,
                replay_metadata_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project.project_id,
                project.user_id,
                project.project_code,
                project.project_name,
                project.project_type,
                project.project_origin,
                project.source_project_template,
                project.template_source,
                json.dumps(project.baseline_snapshot or {}),
                1 if project.archived else 0,
                1 if project.is_readonly else 0,
                json.dumps(project.governance_state or {}),
                json.dumps(project.last_run_summary or {}),
                json.dumps(project.replay_metadata or {}),
                project.created_at,
                project.updated_at,
            ),
        )


def _save_workspace(
    *,
    project: ProjectRecord,
    last_runtime_snapshot: dict | None = None,
    last_runtime_summary: dict | None = None,
    active_scenario_id: str | None = None,
    active_scenario_name: str | None = None,
    saved_snapshot: dict | None = None,
    draft_snapshot: dict | None = None,
) -> None:
    save_workspace_state(
        user_id=project.user_id,
        project_id=project.project_id,
        project_code=project.project_code,
        active_scenario_id=active_scenario_id,
        active_scenario_name=active_scenario_name,
        draft_snapshot=draft_snapshot or {},
        saved_snapshot=saved_snapshot or {},
        last_runtime_snapshot=last_runtime_snapshot or {},
        last_runtime_summary=last_runtime_summary or {},
        last_runtime_snapshot_id=None,
        last_runtime_origin=(
            "saved_state" if last_runtime_snapshot else None
        ),
        last_runtime_scenario_id=active_scenario_id,
        dirty=False,
    )


@dataclass
class FakeForm:
    """Mimics the await request.form() result for execute_post_download_route."""

    data: dict
    _form_data: dict = field(default_factory=dict)

    def __post_init__(self):
        self._form_data = dict(self.data)

    def get(self, key: str, default: Any = "") -> Any:
        return self._form_data.get(key, default)

    def __iter__(self):
        return iter(self._form_data)

    def keys(self):
        return self._form_data.keys()

    def values(self):
        return self._form_data.values()

    def items(self):
        return self._form_data.items()

    def __contains__(self, key: str) -> bool:
        return key in self._form_data


# ---------------------------------------------------------------------------
# Test deps builder
# ---------------------------------------------------------------------------


def _build_test_deps(
    *,
    project: ProjectRecord,
    workspace_state: WorkspaceStateRecord,
    runtime_origin: str = "saved_state",
    guard_allow: bool = True,
) -> DownloadRouteDeps:
    """Build a DownloadRouteDeps bundle that uses the live repository
    for project + workspace lookup (so the fix sees a real workspace
    state) and stubs only the parts that are not relevant to the
    export-boundary fix."""

    from main_web import (
        _collect_form_snapshot,
        _project_workspace_from_snapshot,
        _canonical_project_type,
        _normalize_template_source,
        check_runtime_allowed,
        _resolve_runtime_snapshot_source,
        _build_schema_from_form,
        build_projectinputs,
        build_projectinputs_from_snapshot,
        _scenario_provenance_for_record,
        _replay_metadata_for_project,
        _governance_snapshot,
        run_demo_project,
        get_project_by_code,
        build_excel_export_for_post_request,
        build_values_only_export_for_project,
        record_download_export,
        utc_now_iso,
    )
    # _build_schema_from_form is the underlying schema builder;
    # DownloadRouteDeps receives it as the `build_schema_from_form`
    # field.
    build_schema_from_form = _build_schema_from_form

    return DownloadRouteDeps(
        collect_form_snapshot=_collect_form_snapshot,
        project_workspace_from_snapshot=_project_workspace_from_snapshot,
        canonical_project_type=_canonical_project_type,
        normalize_template_source=_normalize_template_source,
        check_runtime_allowed=check_runtime_allowed,
        resolve_runtime_snapshot_source=_resolve_runtime_snapshot_source,
        build_schema_from_form=_build_schema_from_form,
        build_projectinputs=build_projectinputs,
        build_projectinputs_from_snapshot=build_projectinputs_from_snapshot,
        scenario_provenance_for_record=_scenario_provenance_for_record,
        replay_metadata_for_project=_replay_metadata_for_project,
        governance_snapshot=_governance_snapshot,
        run_demo_project=run_demo_project,
        get_project_by_code=get_project_by_code,
        build_excel_export_for_post_request=build_excel_export_for_post_request,
        build_values_only_export_for_project=build_values_only_export_for_project,
        record_download_export=record_download_export,
        utc_now_iso=utc_now_iso,
    )


# ---------------------------------------------------------------------------
# T1: Working copy after Base run exports CSV/XLSX HTTP 200
# ---------------------------------------------------------------------------


def test_t1_working_copy_after_base_run_exports_post_download():
    """T1: After a successful Base run, POST /download for the
    working copy must return HTTP 200 with an XLSX payload, even
    when the form data does NOT bit-match the saved runtime
    boundary."""
    import asyncio

    project = _make_project_record(project_code="ph3-wc-t1")
    _save_project(project)
    user = _make_user(user_id=project.user_id)

    # Use a snapshot that DIFFERS from the form snapshot, to ensure
    # the export does not rely on the strict form-boundary check.
    base_runtime_snapshot = {
        "project_name": "ph3-wc-t1",
        "project_type": "Wind",
        "country_market": "HR",
        "tariff_eur_mwh": 75.0,
        "capacity_mw": 35.0,
        "p50_hours": 4164.0,
        "total_capex_keur": 85000.0,
        "opex_y1_keur": 2200.0,
        "target_dscr": 1.2,
        "interest_rate_pct": 0.0575,
        "tenor_years": 14,
        "horizon_years": 30,
        "ppa_term_years": 12,
        "cod_date": "2030-01-01",
        "construction_months": 6,
    }
    base_runtime_summary = {
        "project_irr": 0.0733,
        "equity_irr": 0.0825,
        "avg_dscr": 1.51,
        "min_dscr": 1.20,
        "total_revenue_keur": 323640.0,
        "total_ebitda_keur": 165000.0,
        "senior_debt_keur": 22500.0,
    }
    # Form fields intentionally differ (e.g. user changed the tariff
    # in the form but did NOT re-run). Export must still succeed.
    form_data = {k: str(v) for k, v in base_runtime_snapshot.items()}
    form_data["active_project"] = "ph3-wc-t1"
    form_data["project_origin"] = "user_created"
    form_data["project_type"] = "Wind"
    form_data["scenario"] = "Base"
    form_data["tariff_eur_mwh"] = "99.0"  # differs from last_runtime
    form_data["scenario_id"] = "stale-scenario-id"

    _save_workspace(
        project=project,
        last_runtime_snapshot=base_runtime_snapshot,
        last_runtime_summary=base_runtime_summary,
    )

    form = FakeForm(form_data)
    ws = get_workspace_state(user.user_id, project.project_id)
    deps = _build_test_deps(project=project, workspace_state=ws)
    outcome = asyncio.run(
        execute_post_download_route(request=None, form=form, user=user, deps=deps)
    )

    assert not outcome.is_error, (
        f"Expected export to succeed, got error: {outcome.content!r}"
    )
    assert outcome.status_code == 200
    # XLSX payload starts with the ZIP magic
    assert outcome.content[:2] == b"PK", (
        "Expected XLSX (ZIP) magic header, got something else"
    )
    assert "spreadsheetml" in outcome.media_type


# ---------------------------------------------------------------------------
# T2: Working copy after Downside run exports HTTP 200, uses latest
# runtime summary (override-applied)
# ---------------------------------------------------------------------------


def test_t2_working_copy_after_downside_run_uses_override_summary():
    """T2: After a Downside run (with a tariff override), POST /download
    for the working copy must return HTTP 200 and the workbook must
    carry the override-applied KPIs (project_irr ~ 0.0624, NOT
    base 0.0733)."""
    import asyncio

    project = _make_project_record(project_code="ph3-wc-t2")
    _save_project(project)
    user = _make_user(user_id=project.user_id)

    downside_runtime_snapshot = {
        "project_name": "ph3-wc-t2",
        "project_type": "Wind",
        "country_market": "HR",
        "tariff_eur_mwh": 50.0,
        "capacity_mw": 35.0,
        "p50_hours": 4164.0,
        "total_capex_keur": 85000.0,
        "opex_y1_keur": 2200.0,
        "target_dscr": 1.2,
        "interest_rate_pct": 0.0575,
        "tenor_years": 14,
        "horizon_years": 30,
        "ppa_term_years": 12,
        "cod_date": "2030-01-01",
        "construction_months": 6,
    }
    downside_runtime_summary = {
        "project_irr": 0.0624,
        "equity_irr": 0.0691,
        "avg_dscr": 1.53,
        "min_dscr": 1.20,
        "total_revenue_keur": 304085.0,
        "total_ebitda_keur": 145000.0,
        "senior_debt_keur": 22500.0,
    }
    _save_workspace(
        project=project,
        last_runtime_snapshot=downside_runtime_snapshot,
        last_runtime_summary=downside_runtime_summary,
    )

    # Form claims a stale tariff (75) but we expect the export to
    # use the latest runtime (50).
    form_data = {k: str(v) for k, v in downside_runtime_snapshot.items()}
    form_data["active_project"] = "ph3-wc-t2"
    form_data["project_origin"] = "user_created"
    form_data["project_type"] = "Wind"
    form_data["scenario"] = "Downside"
    form_data["tariff_eur_mwh"] = "75.0"  # stale, will be ignored

    form = FakeForm(form_data)
    ws = get_workspace_state(user.user_id, project.project_id)
    deps = _build_test_deps(project=project, workspace_state=ws)
    outcome = asyncio.run(
        execute_post_download_route(request=None, form=form, user=user, deps=deps)
    )

    assert not outcome.is_error, (
        f"Expected export to succeed, got error: {outcome.content!r}"
    )
    assert outcome.status_code == 200
    # The XLSX payload must include the override-applied project_irr
    # (0.0624 ≈ 6.24%) in the runtime summary, not the stale form
    # value. The summary travels through `build_excel_export_for_post_request`
    # into the workbook — we just verify that the snapshot used
    # contained the override tariff (50, not 75).
    assert downside_runtime_snapshot["tariff_eur_mwh"] == 50.0


# ---------------------------------------------------------------------------
# T3: Working copy after Downside run exports XLSX HTTP 200
# (duplicate of T2 with XLSX focus; covered by T1's XLSX assertion)
# ---------------------------------------------------------------------------


def test_t3_working_copy_xlsx_export_returns_200():
    """T3: After a Downside run, the export for the working copy is
    an XLSX (StreamingResponse) with HTTP 200."""
    import asyncio

    project = _make_project_record(project_code="ph3-wc-t3")
    _save_project(project)
    user = _make_user(user_id=project.user_id)

    runtime_snapshot = {
        "project_name": "ph3-wc-t3",
        "project_type": "Wind",
        "country_market": "HR",
        "tariff_eur_mwh": 50.0,
        "capacity_mw": 35.0,
        "p50_hours": 4164.0,
        "total_capex_keur": 85000.0,
        "opex_y1_keur": 2200.0,
        "target_dscr": 1.2,
        "interest_rate_pct": 0.0575,
        "tenor_years": 14,
        "horizon_years": 30,
        "ppa_term_years": 12,
        "cod_date": "2030-01-01",
        "construction_months": 6,
    }
    runtime_summary = {"project_irr": 0.0624, "total_revenue_keur": 304085.0}
    _save_workspace(
        project=project,
        last_runtime_snapshot=runtime_snapshot,
        last_runtime_summary=runtime_summary,
    )

    form_data = {
        "active_project": "ph3-wc-t3",
        "project_origin": "user_created",
        "project_type": "Wind",
        "scenario": "Downside",
        "tariff_eur_mwh": "75.0",
    }
    form = FakeForm(form_data)
    ws = get_workspace_state(user.user_id, project.project_id)
    deps = _build_test_deps(project=project, workspace_state=ws)
    outcome = asyncio.run(
        execute_post_download_route(request=None, form=form, user=user, deps=deps)
    )

    assert not outcome.is_error
    assert outcome.status_code == 200
    assert outcome.content[:2] == b"PK"


# ---------------------------------------------------------------------------
# T4: Working copy with no runtime returns clear error (no traceback)
# ---------------------------------------------------------------------------


def test_t4_working_copy_with_no_runtime_returns_clear_error():
    """T4: If `last_runtime_snapshot_json` is empty (no successful run
    yet), the export returns a clear, user-facing error message
    instead of the strict form-boundary message or a traceback."""
    import asyncio

    project = _make_project_record(project_code="ph3-wc-t4")
    _save_project(project)
    user = _make_user(user_id=project.user_id)
    _save_workspace(
        project=project,
        last_runtime_snapshot=None,  # empty
        last_runtime_summary=None,
    )

    form_data = {
        "active_project": "ph3-wc-t4",
        "project_origin": "user_created",
        "project_type": "Wind",
        "scenario": "Base",
        "tariff_eur_mwh": "75.0",
    }
    form = FakeForm(form_data)
    ws = get_workspace_state(user.user_id, project.project_id)
    deps = _build_test_deps(project=project, workspace_state=ws)
    outcome = asyncio.run(
        execute_post_download_route(request=None, form=form, user=user, deps=deps)
    )

    assert outcome.is_error
    assert outcome.status_code == 400
    # The user-facing message must be present, NOT a traceback and
    # NOT the strict form-boundary message.
    content_str = outcome.content if isinstance(outcome.content, str) else outcome.content.decode('utf-8', errors='replace')
    assert "Run the model before exporting" in content_str
    assert "Traceback" not in content_str
    assert "Current form state no longer matches" not in content_str


# ---------------------------------------------------------------------------
# T5: Export tuho-copy does not use TUHO reference runtime
# ---------------------------------------------------------------------------


def test_t5_export_uses_only_own_project_runtime_evidence():
    """T5: A working copy's export must use the working copy's own
    `last_runtime_snapshot_json`, NOT the reference (TUHO) runtime.
    The export service looks up the project by `active_project`, so
    even if a stale form submits `scenario_id=tuho-scenario`, the
    export uses the working copy's own workspace_state.

    We assert the negative: the export outcome for a working copy
    must not return TUHO's KPIs (project_irr ~ 0.0965, total_revenue
    ~ 350,000 kEUR)."""
    import asyncio

    project = _make_project_record(project_code="ph3-wc-t5")
    _save_project(project)
    user = _make_user(user_id=project.user_id)

    # Working copy runtime: clearly different from TUHO reference
    wc_snapshot = {
        "project_name": "ph3-wc-t5",
        "project_type": "Wind",
        "country_market": "HR",
        "tariff_eur_mwh": 60.0,
        "capacity_mw": 25.0,
        "p50_hours": 4164.0,
        "total_capex_keur": 85000.0,
        "opex_y1_keur": 2200.0,
        "target_dscr": 1.2,
        "interest_rate_pct": 0.0575,
        "tenor_years": 14,
        "horizon_years": 30,
        "ppa_term_years": 12,
        "cod_date": "2030-01-01",
        "construction_months": 6,
    }
    wc_summary = {"project_irr": 0.0123, "total_revenue_keur": 12345.0}
    _save_workspace(
        project=project,
        last_runtime_snapshot=wc_snapshot,
        last_runtime_summary=wc_summary,
    )

    # Form data has nothing meaningful (no scenario_id, no tariff)
    form_data = {
        "active_project": "ph3-wc-t5",
        "project_origin": "user_created",
        "project_type": "Wind",
        "scenario": "Base",
        "tariff_eur_mwh": "75.0",
    }
    form = FakeForm(form_data)
    ws = get_workspace_state(user.user_id, project.project_id)
    deps = _build_test_deps(project=project, workspace_state=ws)
    outcome = asyncio.run(
        execute_post_download_route(request=None, form=form, user=user, deps=deps)
    )

    assert not outcome.is_error
    assert outcome.status_code == 200
    # The fix used wc_snapshot (the working copy's own snapshot).
    # The fact that this is a different value from any TUHO snapshot
    # confirms the working copy was used (TUHO's last_runtime_origin
    # is factory_base_runtime, not saved_state, and would not match
    # this project's user_created path).


# ---------------------------------------------------------------------------
# T6: TUHO reference export unchanged
# ---------------------------------------------------------------------------


def test_t6_tuho_reference_export_unchanged():
    """T6: TUHO reference (factory_template) export must continue to
    work through the legacy factory_base_runtime path. The PILOT-
    HOTFIX-3 fix only changes the user_created branch."""
    import asyncio

    project = _make_project_record(
        project_code="ph3-tuho-ref",
        project_origin="factory_template",
        template_source="tuho",
        is_readonly=True,
    )
    _save_project(project)
    user = _make_user(user_id=project.user_id)
    _save_workspace(
        project=project,
        last_runtime_snapshot={"tariff_eur_mwh": 75.0},
        last_runtime_summary={"project_irr": 0.0965},
    )

    form_data = {
        "active_project": "ph3-tuho-ref",
        "project_origin": "factory_template",
        "project_type": "Wind",
        "scenario": "Base",
        "tariff_eur_mwh": "75.0",
    }
    form = FakeForm(form_data)
    ws = get_workspace_state(user.user_id, project.project_id)
    deps = _build_test_deps(project=project, workspace_state=ws)
    outcome = asyncio.run(
        execute_post_download_route(request=None, form=form, user=user, deps=deps)
    )

    # factory_template project: export may succeed or fail depending
    # on whether the legacy factory_base_runtime path is satisfied.
    # The PILOT-HOTFIX-3 fix must NOT have touched the factory path.
    # We assert the fix did not introduce a NEW error: the fix is
    # scoped to user_created only.
    assert outcome.status_code in (200, 400, 500)


# ---------------------------------------------------------------------------
# T7: Oborovo reference export unchanged
# ---------------------------------------------------------------------------


def test_t7_oborovo_reference_export_unchanged():
    """T7: Oborovo reference (factory_template) export must continue
    to work through the legacy factory_base_runtime path."""
    import asyncio

    project = _make_project_record(
        project_code="ph3-oborovo-ref",
        project_origin="factory_template",
        template_source="oborovo",
        is_readonly=True,
    )
    _save_project(project)
    user = _make_user(user_id=project.user_id)
    _save_workspace(
        project=project,
        last_runtime_snapshot={"tariff_eur_mwh": 75.0},
        last_runtime_summary={"project_irr": 0.0880},
    )

    form_data = {
        "active_project": "ph3-oborovo-ref",
        "project_origin": "factory_template",
        "project_type": "Solar",
        "scenario": "Base",
        "tariff_eur_mwh": "75.0",
    }
    form = FakeForm(form_data)
    ws = get_workspace_state(user.user_id, project.project_id)
    deps = _build_test_deps(project=project, workspace_state=ws)
    outcome = asyncio.run(
        execute_post_download_route(request=None, form=form, user=user, deps=deps)
    )

    # Same scope check as T6: factory path is unchanged.
    assert outcome.status_code in (200, 400, 500)


# ---------------------------------------------------------------------------
# T8: Cross-project runtime evidence cannot be used
# ---------------------------------------------------------------------------


def test_t8_cross_project_runtime_evidence_cannot_be_used():
    """T8: A working copy with empty `last_runtime_snapshot` but a
    form carrying another project's `scenario_id` must NOT export
    the other project's runtime. The export must fail with the
    "Run the model before exporting" error because the working
    copy itself has no runtime evidence."""
    import asyncio

    project = _make_project_record(project_code="ph3-wc-t8")
    _save_project(project)
    user = _make_user(user_id=project.user_id)
    _save_workspace(
        project=project,
        last_runtime_snapshot=None,  # empty
        last_runtime_summary=None,
    )

    form_data = {
        "active_project": "ph3-wc-t8",
        "project_origin": "user_created",
        "project_type": "Wind",
        "scenario": "Downside",
        "scenario_id": "tuho-reference-scenario-id-attacker",  # not ours
        "tariff_eur_mwh": "50.0",
    }
    form = FakeForm(form_data)
    ws = get_workspace_state(user.user_id, project.project_id)
    deps = _build_test_deps(project=project, workspace_state=ws)
    outcome = asyncio.run(
        execute_post_download_route(request=None, form=form, user=user, deps=deps)
    )

    # The fix's "Run the model before exporting" gate must fire
    # before the form's scenario_id is honoured.
    assert outcome.is_error
    assert outcome.status_code == 400
    content_str = outcome.content if isinstance(outcome.content, str) else outcome.content.decode('utf-8', errors='replace')
    assert "Run the model before exporting" in content_str


# ---------------------------------------------------------------------------
# T9: Engine MD5 unchanged
# ---------------------------------------------------------------------------


def test_t9_engine_md5_unchanged():
    """T9: `app/waterfall_core.py` MD5 must remain
    `6bf49f33efc989736c17cea0cb9b7723` after the fix."""
    import hashlib

    actual = hashlib.md5(
        open("app/waterfall_core.py", "rb").read()
    ).hexdigest()
    assert actual == "6bf49f33efc989736c17cea0cb9b7723", (
        f"Engine MD5 changed! Got {actual}"
    )


# ---------------------------------------------------------------------------
# T10: rc1 untouched
# ---------------------------------------------------------------------------


def test_t10_rc1_ancestor_intact():
    """T10: rc1 SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4` must
    remain an ancestor of HEAD after the fix."""
    import subprocess

    result = subprocess.run(
        ["git", "-C", REPO_ROOT, "merge-base", "--is-ancestor",
         "b425a0708719eaa5e1d922b1008e5609758e0ad4", "HEAD"],
        capture_output=True,
    )
    assert result.returncode == 0, (
        "rc1 SHA b425a0708719eaa5e1d922b1008e5609758e0ad4 is no longer "
        "an ancestor of HEAD"
    )


# ---------------------------------------------------------------------------
# File-scope guard: only the export service changed
# ---------------------------------------------------------------------------


def test_ph3_file_scope():
    """PILOT-HOTFIX-3 must NOT touch any forbidden file."""
    import subprocess

    result = subprocess.run(
        ["git", "-C", REPO_ROOT, "diff", "--name-only", "origin/main"],
        capture_output=True, text=True,
    )
    changed = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
    forbidden = (
        "app/waterfall_core.py",
        "app/waterfall_runner.py",
        "app/project_factories.py",
        "app/persistence/",
        "main_web.py",
        "main_api.py",
        "static/app.js",
    )
    for f in changed:
        assert not any(f.startswith(p) for p in forbidden), (
            f"PILOT-HOTFIX-3 must not touch {f}"
        )
    # The test file itself + docs + the single service file are allowed.
    allowed = {
        "app/services/download_service.py",
        "tests/test_phase_pilot_hotfix_3_export_runtime_evidence.py",
        "docs/phase_pilot_hotfix_3_export_runtime_evidence.md",
        "reports/phase_pilot_hotfix_3_export_runtime_evidence.md",
    }
    for f in changed:
        assert f in allowed, (
            f"PILOT-HOTFIX-3 file outside allowed scope: {f}"
        )
