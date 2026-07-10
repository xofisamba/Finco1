"""
Tests for Workbook V2 RuntimeResult — app/workbook/runtime_result.py

Validates:
1.  from_run_result() — builds from run_project() result dict
2.  from_workspace_state() — reconstruct from persisted WorkspaceStateRecord
3.  to_sessionstorage_script() — JS matches expected sessionStorage format
4.  has_schedules() — predicate helper
5.  Immutability — frozen dataclass
6.  Persistence round-trip — schedules survive DB write/read via save_workspace_state
7.  record_workspace_runtime passes schedules through to DB
8.  WorkspaceStateRecord carries the 5 new schedule fields
9.  sessionStorage key names are stable (contract test)
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone

import pytest

from app.workbook.runtime_result import (
    RuntimeResult,
    _SS_KEY_DEBT_SCHEDULE,
    _SS_KEY_DISTRIBUTION_SCHEDULE,
    _SS_KEY_FINANCIAL_STATEMENTS,
    _SS_KEY_RUNTIME_SUMMARY,
    _SS_KEY_SPONSOR_SCHEDULE,
    _SS_KEY_TAX_SCHEDULE,
)

# ---------------------------------------------------------------------------
# Isolated test DB — each persistence test gets its own SQLite file so it
# never touches the dev or production DB.
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Per-test isolated SQLite DB via FINCO_DB_PATH."""
    import app.persistence.db as db_mod
    db_file = str(tmp_path / "test_runtime_result.db")
    monkeypatch.setenv("FINCO_DB_PATH", db_file)
    monkeypatch.setattr(db_mod, "DB_PATH", db_file)
    # Trigger schema init on the fresh DB.
    conn = db_mod.get_connection()
    conn.close()
    yield db_file


def _insert_project(user_id: str, project_id: str, project_code: str) -> None:
    """Insert the minimal project row required to satisfy the FK constraint."""
    from app.persistence.db import get_cursor
    now = "2026-07-10T00:00:00+00:00"
    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO projects
              (project_id, user_id, project_code, project_name, project_type,
               project_origin, source_project_template, template_source,
               baseline_snapshot_json, archived, governance_state_json,
               last_run_summary_json, replay_metadata_json,
               created_at, updated_at, is_readonly)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project_id, user_id, project_code, f"Test {project_code}",
                "Wind", "user_created", "", None,
                json.dumps({}), 0,
                json.dumps({}), json.dumps({}), json.dumps({}),
                now, now, 0,
            ),
        )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_SUMMARY = {
    "project_id": "proj_test",
    "project_name": "Test Wind",
    "ran_at": "2026-07-10T12:00:00+00:00",
    "status": "ok",
    "project_irr": "12.34%",
    "equity_irr": "15.67%",
    "avg_dscr": "1.35x",
    "min_dscr": "1.10x",
}

SAMPLE_FS = {"periods": [{"year": 1, "revenue_keur": 5000.0}], "version": "v2"}
SAMPLE_DS = {"periods": [{"year": 1, "senior_ds_keur": 1200.0}]}
SAMPLE_TS = {"periods": [{"year": 1, "tax_keur": 300.0}]}
SAMPLE_DIST = {"periods": [{"year": 1, "distribution_keur": 800.0}]}
SAMPLE_SPONSOR = {"irr": "14.5%", "moic": "2.1x"}

SAMPLE_RESULT_DICT = {
    "kpis": SAMPLE_SUMMARY,
    "financial_statements": SAMPLE_FS,
    "debt_schedule": SAMPLE_DS,
    "tax_schedule": SAMPLE_TS,
    "distribution_schedule": SAMPLE_DIST,
    "sponsor_schedule": SAMPLE_SPONSOR,
    "messages": [],
    "integration_status": "full",
}


@pytest.fixture
def full_rr() -> RuntimeResult:
    return RuntimeResult.from_run_result(
        SAMPLE_RESULT_DICT,
        runtime_summary=SAMPLE_SUMMARY,
        snapshot_id="20260710T120000Z",
        ran_at="2026-07-10T12:00:00+00:00",
        origin="workspace_base",
    )


@pytest.fixture
def partial_rr() -> RuntimeResult:
    """RuntimeResult with no sponsor or distribution schedule."""
    result = {**SAMPLE_RESULT_DICT, "sponsor_schedule": None, "distribution_schedule": None}
    return RuntimeResult.from_run_result(
        result,
        runtime_summary=SAMPLE_SUMMARY,
        snapshot_id="20260710T120000Z",
        ran_at="2026-07-10T12:00:00+00:00",
        origin="workspace_base",
    )


# ---------------------------------------------------------------------------
# 1. from_run_result()
# ---------------------------------------------------------------------------

class TestFromRunResult:
    def test_returns_runtime_result(self, full_rr):
        assert isinstance(full_rr, RuntimeResult)

    def test_snapshot_id_set(self, full_rr):
        assert full_rr.snapshot_id == "20260710T120000Z"

    def test_ran_at_set(self, full_rr):
        assert full_rr.ran_at == "2026-07-10T12:00:00+00:00"

    def test_origin_set(self, full_rr):
        assert full_rr.origin == "workspace_base"

    def test_runtime_summary_set(self, full_rr):
        assert full_rr.runtime_summary == SAMPLE_SUMMARY

    def test_financial_statements_set(self, full_rr):
        assert full_rr.financial_statements == SAMPLE_FS

    def test_debt_schedule_set(self, full_rr):
        assert full_rr.debt_schedule == SAMPLE_DS

    def test_tax_schedule_set(self, full_rr):
        assert full_rr.tax_schedule == SAMPLE_TS

    def test_distribution_schedule_set(self, full_rr):
        assert full_rr.distribution_schedule == SAMPLE_DIST

    def test_sponsor_schedule_set(self, full_rr):
        assert full_rr.sponsor_schedule == SAMPLE_SPONSOR

    def test_missing_schedule_is_none(self, partial_rr):
        assert partial_rr.sponsor_schedule is None
        assert partial_rr.distribution_schedule is None

    def test_always_present_schedules_still_set(self, partial_rr):
        assert partial_rr.financial_statements == SAMPLE_FS
        assert partial_rr.debt_schedule == SAMPLE_DS


# ---------------------------------------------------------------------------
# 2. from_workspace_state()
# ---------------------------------------------------------------------------

class TestFromWorkspaceState:
    def _make_ws(self, **overrides):
        """Build a minimal WorkspaceStateRecord-like object."""
        from types import SimpleNamespace
        defaults = dict(
            last_runtime_snapshot_id="20260710T120000Z",
            last_runtime_at=datetime(2026, 7, 10, 12, 0, 0, tzinfo=timezone.utc),
            last_runtime_origin="workspace_base",
            last_runtime_summary=SAMPLE_SUMMARY,
            last_financial_statements=SAMPLE_FS,
            last_debt_schedule=SAMPLE_DS,
            last_tax_schedule=SAMPLE_TS,
            last_distribution_schedule=SAMPLE_DIST,
            last_sponsor_schedule=SAMPLE_SPONSOR,
        )
        defaults.update(overrides)
        return SimpleNamespace(**defaults)

    def test_returns_runtime_result(self):
        ws = self._make_ws()
        rr = RuntimeResult.from_workspace_state(ws)
        assert isinstance(rr, RuntimeResult)

    def test_returns_none_when_no_snapshot_id(self):
        ws = self._make_ws(last_runtime_snapshot_id=None)
        assert RuntimeResult.from_workspace_state(ws) is None

    def test_returns_none_when_empty_summary(self):
        ws = self._make_ws(last_runtime_summary={})
        assert RuntimeResult.from_workspace_state(ws) is None

    def test_snapshot_id_preserved(self):
        ws = self._make_ws()
        rr = RuntimeResult.from_workspace_state(ws)
        assert rr.snapshot_id == "20260710T120000Z"

    def test_ran_at_from_datetime(self):
        ws = self._make_ws()
        rr = RuntimeResult.from_workspace_state(ws)
        assert "2026-07-10" in rr.ran_at

    def test_financial_statements_preserved(self):
        ws = self._make_ws()
        rr = RuntimeResult.from_workspace_state(ws)
        assert rr.financial_statements == SAMPLE_FS

    def test_empty_schedule_becomes_none(self):
        ws = self._make_ws(last_sponsor_schedule={})
        rr = RuntimeResult.from_workspace_state(ws)
        assert rr.sponsor_schedule is None

    def test_missing_schedule_attr_graceful(self):
        """If a WorkspaceStateRecord lacks the new fields (old DB row), use None."""
        from types import SimpleNamespace
        ws = SimpleNamespace(
            last_runtime_snapshot_id="20260710T120000Z",
            last_runtime_at=datetime(2026, 7, 10, 12, 0, 0, tzinfo=timezone.utc),
            last_runtime_origin="workspace_base",
            last_runtime_summary=SAMPLE_SUMMARY,
            # No last_financial_statements etc.
        )
        rr = RuntimeResult.from_workspace_state(ws)
        assert rr is not None
        assert rr.financial_statements is None


# ---------------------------------------------------------------------------
# 3. to_sessionstorage_script()
# ---------------------------------------------------------------------------

class TestToSessionstorageScript:
    def test_returns_script_tag(self, full_rr):
        script = full_rr.to_sessionstorage_script()
        assert script.startswith("<script>")
        assert script.endswith("</script>")

    def test_sets_financial_statements_key(self, full_rr):
        script = full_rr.to_sessionstorage_script()
        assert _SS_KEY_FINANCIAL_STATEMENTS in script
        assert "setItem" in script

    def test_sets_debt_schedule_key(self, full_rr):
        assert _SS_KEY_DEBT_SCHEDULE in full_rr.to_sessionstorage_script()

    def test_sets_tax_schedule_key(self, full_rr):
        assert _SS_KEY_TAX_SCHEDULE in full_rr.to_sessionstorage_script()

    def test_sets_distribution_schedule_key(self, full_rr):
        assert _SS_KEY_DISTRIBUTION_SCHEDULE in full_rr.to_sessionstorage_script()

    def test_sets_sponsor_schedule_key(self, full_rr):
        assert _SS_KEY_SPONSOR_SCHEDULE in full_rr.to_sessionstorage_script()

    def test_sets_runtime_summary_key(self, full_rr):
        assert _SS_KEY_RUNTIME_SUMMARY in full_rr.to_sessionstorage_script()

    def test_removes_missing_schedule(self, partial_rr):
        script = partial_rr.to_sessionstorage_script()
        assert f'removeItem("{_SS_KEY_SPONSOR_SCHEDULE}")' in script
        assert f'removeItem("{_SS_KEY_DISTRIBUTION_SCHEDULE}")' in script

    def test_payload_is_double_serialized(self, full_rr):
        """Payload must be json.dumps(json.dumps(payload)) matching legacy convention."""
        script = full_rr.to_sessionstorage_script()
        # Extract the value between setItem("lastRuntimeSummary", ...) by parsing
        # the JSON-encoded outer string manually.
        key_marker = f'setItem("{_SS_KEY_RUNTIME_SUMMARY}", '
        idx = script.index(key_marker) + len(key_marker)
        end = script.index(");", idx)
        outer_encoded = script[idx:end]
        # outer_encoded should be json.dumps(json.dumps(dict))
        inner_str = json.loads(outer_encoded)
        parsed = json.loads(inner_str)
        assert parsed["project_id"] == "proj_test"

    def test_empty_result_still_clears_all(self):
        """A RuntimeResult with no schedules removes all keys."""
        rr = RuntimeResult(
            snapshot_id="x",
            ran_at="",
            origin="",
            runtime_summary={"project_id": "p"},
            financial_statements=None,
            debt_schedule=None,
            tax_schedule=None,
            distribution_schedule=None,
            sponsor_schedule=None,
        )
        script = rr.to_sessionstorage_script()
        assert "removeItem" in script
        assert "setItem" in script  # runtime_summary is always set


# ---------------------------------------------------------------------------
# 4. has_schedules()
# ---------------------------------------------------------------------------

class TestHasSchedules:
    def test_full_rr_has_schedules(self, full_rr):
        assert full_rr.has_schedules()

    def test_no_schedules_returns_false(self):
        rr = RuntimeResult(
            snapshot_id="x",
            ran_at="",
            origin="",
            runtime_summary={"project_id": "p"},
            financial_statements=None,
            debt_schedule=None,
            tax_schedule=None,
            distribution_schedule=None,
            sponsor_schedule=None,
        )
        assert not rr.has_schedules()

    def test_partial_still_has_schedules(self, partial_rr):
        assert partial_rr.has_schedules()


# ---------------------------------------------------------------------------
# 5. Immutability
# ---------------------------------------------------------------------------

class TestImmutability:
    def test_frozen_rejects_attribute_set(self, full_rr):
        with pytest.raises((AttributeError, TypeError)):
            full_rr.snapshot_id = "mutated"  # type: ignore[misc]

    def test_frozen_rejects_schedule_set(self, full_rr):
        with pytest.raises((AttributeError, TypeError)):
            full_rr.financial_statements = {}  # type: ignore[misc]

    def test_repr_contains_snapshot_id(self, full_rr):
        r = repr(full_rr)
        assert "20260710T120000Z" in r
        assert "RuntimeResult" in r


# ---------------------------------------------------------------------------
# 6. Persistence round-trip via save_workspace_state
# ---------------------------------------------------------------------------

class TestPersistenceRoundTrip:
    """
    Verifies that schedule payloads survive a DB write → read round-trip
    through save_workspace_state / get_workspace_state.
    """

    def _unique_ids(self):
        uid = uuid.uuid4().hex[:12]
        return f"user_{uid}", f"proj_{uid}"

    def test_schedules_survive_roundtrip(self):
        from app.persistence.workspace_repository import save_workspace_state, get_workspace_state
        user_id, project_id = self._unique_ids()
        _insert_project(user_id, project_id, "test_code")
        save_workspace_state(
            user_id=user_id,
            project_id=project_id,
            project_code="test_code",
            draft_snapshot={"capacity_mw": "35.0"},
            saved_snapshot={"capacity_mw": "35.0"},
            last_runtime_summary=SAMPLE_SUMMARY,
            last_runtime_snapshot_id="20260710T120000Z",
            last_runtime_origin="workspace_base",
            last_financial_statements=SAMPLE_FS,
            last_debt_schedule=SAMPLE_DS,
            last_tax_schedule=SAMPLE_TS,
            last_distribution_schedule=SAMPLE_DIST,
            last_sponsor_schedule=SAMPLE_SPONSOR,
        )
        ws = get_workspace_state(user_id, project_id)
        assert ws is not None
        assert ws.last_financial_statements == SAMPLE_FS
        assert ws.last_debt_schedule == SAMPLE_DS
        assert ws.last_tax_schedule == SAMPLE_TS
        assert ws.last_distribution_schedule == SAMPLE_DIST
        assert ws.last_sponsor_schedule == SAMPLE_SPONSOR

    def test_missing_schedules_default_to_empty_dict(self):
        from app.persistence.workspace_repository import save_workspace_state, get_workspace_state
        user_id, project_id = self._unique_ids()
        _insert_project(user_id, project_id, "test_code")
        save_workspace_state(
            user_id=user_id,
            project_id=project_id,
            project_code="test_code",
            draft_snapshot={},
            saved_snapshot={},
        )
        ws = get_workspace_state(user_id, project_id)
        assert ws is not None
        assert isinstance(ws.last_financial_statements, dict)
        assert ws.last_financial_statements == {}

    def test_from_workspace_state_after_roundtrip(self):
        from app.persistence.workspace_repository import save_workspace_state, get_workspace_state
        user_id, project_id = self._unique_ids()
        _insert_project(user_id, project_id, "test_code")
        save_workspace_state(
            user_id=user_id,
            project_id=project_id,
            project_code="test_code",
            draft_snapshot={},
            saved_snapshot={},
            last_runtime_summary=SAMPLE_SUMMARY,
            last_runtime_snapshot_id="20260710T120000Z",
            last_runtime_origin="workspace_base",
            last_financial_statements=SAMPLE_FS,
            last_debt_schedule=SAMPLE_DS,
            last_tax_schedule=SAMPLE_TS,
            last_distribution_schedule=SAMPLE_DIST,
            last_sponsor_schedule=SAMPLE_SPONSOR,
        )
        ws = get_workspace_state(user_id, project_id)
        rr = RuntimeResult.from_workspace_state(ws)
        assert rr is not None
        assert rr.financial_statements == SAMPLE_FS
        assert rr.sponsor_schedule == SAMPLE_SPONSOR
        script = rr.to_sessionstorage_script()
        assert _SS_KEY_FINANCIAL_STATEMENTS in script
        assert _SS_KEY_RUNTIME_SUMMARY in script

    def test_update_preserves_schedules(self):
        """Updating unrelated fields does not clobber schedules."""
        from app.persistence.workspace_repository import save_workspace_state, get_workspace_state
        user_id, project_id = self._unique_ids()
        _insert_project(user_id, project_id, "test_code")
        save_workspace_state(
            user_id=user_id,
            project_id=project_id,
            project_code="test_code",
            draft_snapshot={},
            saved_snapshot={},
            last_runtime_summary=SAMPLE_SUMMARY,
            last_runtime_snapshot_id="20260710T120000Z",
            last_runtime_origin="workspace_base",
            last_financial_statements=SAMPLE_FS,
            last_debt_schedule=SAMPLE_DS,
            last_tax_schedule=SAMPLE_TS,
            last_distribution_schedule=SAMPLE_DIST,
            last_sponsor_schedule=SAMPLE_SPONSOR,
        )
        # Update only draft_snapshot — schedules should carry forward.
        save_workspace_state(
            user_id=user_id,
            project_id=project_id,
            project_code="test_code",
            draft_snapshot={"capacity_mw": "50.0"},
            saved_snapshot={},
            dirty=True,
        )
        ws = get_workspace_state(user_id, project_id)
        assert ws.last_financial_statements == SAMPLE_FS
        assert ws.last_sponsor_schedule == SAMPLE_SPONSOR


# ---------------------------------------------------------------------------
# 7. record_workspace_runtime passes schedules through
# ---------------------------------------------------------------------------

class TestRecordWorkspaceRuntime:
    def _unique_ids(self):
        uid = uuid.uuid4().hex[:12]
        return f"user_{uid}", f"proj_{uid}"

    def test_schedules_persisted_via_record_workspace_runtime(self):
        from app.persistence.repository import record_workspace_runtime
        from app.persistence.workspace_repository import get_workspace_state
        user_id, project_id = self._unique_ids()
        # Bootstrap a workspace first (record_workspace_runtime reads existing).
        from app.persistence.workspace_repository import save_workspace_state
        _insert_project(user_id, project_id, "test_code")
        save_workspace_state(
            user_id=user_id,
            project_id=project_id,
            project_code="test_code",
            draft_snapshot={"capacity_mw": "35.0"},
            saved_snapshot={"capacity_mw": "35.0"},
        )
        record_workspace_runtime(
            user_id=user_id,
            project_id=project_id,
            project_code="test_code",
            runtime_snapshot={"capacity_mw": "35.0"},
            runtime_summary=SAMPLE_SUMMARY,
            runtime_snapshot_id="20260710T120000Z",
            runtime_origin="workspace_base",
            financial_statements=SAMPLE_FS,
            debt_schedule=SAMPLE_DS,
            tax_schedule=SAMPLE_TS,
            distribution_schedule=SAMPLE_DIST,
            sponsor_schedule=SAMPLE_SPONSOR,
        )
        ws = get_workspace_state(user_id, project_id)
        assert ws.last_financial_statements == SAMPLE_FS
        assert ws.last_debt_schedule == SAMPLE_DS
        assert ws.last_tax_schedule == SAMPLE_TS
        assert ws.last_distribution_schedule == SAMPLE_DIST
        assert ws.last_sponsor_schedule == SAMPLE_SPONSOR

    def test_record_without_schedules_defaults_empty(self):
        from app.persistence.repository import record_workspace_runtime
        from app.persistence.workspace_repository import get_workspace_state, save_workspace_state
        user_id, project_id = self._unique_ids()
        _insert_project(user_id, project_id, "test_code")
        save_workspace_state(
            user_id=user_id,
            project_id=project_id,
            project_code="test_code",
            draft_snapshot={},
            saved_snapshot={},
        )
        record_workspace_runtime(
            user_id=user_id,
            project_id=project_id,
            project_code="test_code",
            runtime_snapshot={},
            runtime_summary=SAMPLE_SUMMARY,
            runtime_snapshot_id="20260710T120000Z",
            runtime_origin="workspace_base",
        )
        ws = get_workspace_state(user_id, project_id)
        assert isinstance(ws.last_financial_statements, dict)


# ---------------------------------------------------------------------------
# 8. WorkspaceStateRecord carries 5 new fields
# ---------------------------------------------------------------------------

class TestWorkspaceStateRecord:
    def _uid(self):
        uid = uuid.uuid4().hex[:12]
        return f"user_{uid}", f"proj_{uid}"

    def test_has_financial_statements_field(self):
        from app.persistence.workspace_repository import save_workspace_state
        user_id, project_id = self._uid()
        _insert_project(user_id, project_id, "c")
        ws = save_workspace_state(
            user_id=user_id,
            project_id=project_id,
            project_code="c",
            draft_snapshot={},
            saved_snapshot={},
        )
        assert hasattr(ws, "last_financial_statements")
        assert hasattr(ws, "last_debt_schedule")
        assert hasattr(ws, "last_tax_schedule")
        assert hasattr(ws, "last_distribution_schedule")
        assert hasattr(ws, "last_sponsor_schedule")

    def test_new_fields_are_dicts(self):
        from app.persistence.workspace_repository import save_workspace_state
        user_id, project_id = self._uid()
        _insert_project(user_id, project_id, "c")
        ws = save_workspace_state(
            user_id=user_id,
            project_id=project_id,
            project_code="c",
            draft_snapshot={},
            saved_snapshot={},
        )
        assert isinstance(ws.last_financial_statements, dict)
        assert isinstance(ws.last_debt_schedule, dict)
        assert isinstance(ws.last_tax_schedule, dict)
        assert isinstance(ws.last_distribution_schedule, dict)
        assert isinstance(ws.last_sponsor_schedule, dict)


# ---------------------------------------------------------------------------
# 9. sessionStorage key names are stable (contract test)
# ---------------------------------------------------------------------------

class TestSessionStorageKeyNames:
    """These key names are contracts: templates read them by exact string."""

    def test_financial_statements_key(self):
        assert _SS_KEY_FINANCIAL_STATEMENTS == "lastFinancialStatements"

    def test_debt_schedule_key(self):
        assert _SS_KEY_DEBT_SCHEDULE == "lastDebtSchedule"

    def test_tax_schedule_key(self):
        assert _SS_KEY_TAX_SCHEDULE == "lastTaxSchedule"

    def test_distribution_schedule_key(self):
        assert _SS_KEY_DISTRIBUTION_SCHEDULE == "lastDistributionSchedule"

    def test_sponsor_schedule_key(self):
        assert _SS_KEY_SPONSOR_SCHEDULE == "lastSponsorSchedule"

    def test_runtime_summary_key(self):
        assert _SS_KEY_RUNTIME_SUMMARY == "lastRuntimeSummary"
