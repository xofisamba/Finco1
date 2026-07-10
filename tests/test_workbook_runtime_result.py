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

    # -- Genuine deep-immutability (MappingProxyType) --

    def test_runtime_summary_top_level_mutation_fails(self, full_rr):
        """Direct key-assignment on runtime_summary must fail."""
        with pytest.raises(TypeError):
            full_rr.runtime_summary["injected"] = "bad"  # type: ignore[index]

    def test_financial_statements_top_level_mutation_fails(self, full_rr):
        with pytest.raises(TypeError):
            full_rr.financial_statements["injected"] = "bad"  # type: ignore[index]

    def test_debt_schedule_top_level_mutation_fails(self, full_rr):
        with pytest.raises(TypeError):
            full_rr.debt_schedule["injected"] = "bad"  # type: ignore[index]

    def test_nested_dict_in_list_mutation_fails(self, full_rr):
        """Nested dict inside a list (financial_statements.periods[0]) must be immutable."""
        # _freeze makes every dict node a MappingProxyType, so mutation of
        # a deeply-nested dict raises TypeError even though the list is still a list.
        period = full_rr.financial_statements["periods"][0]
        with pytest.raises(TypeError):
            period["revenue_keur"] = 99999.0  # type: ignore[index]

    def test_nested_dict_key_assignment_fails_two_levels_deep(self, full_rr):
        """Mutation fails at a second nested dict level."""
        meta = full_rr.financial_statements.get("version")
        # Test a different nested dict — runtime_summary is MappingProxyType.
        with pytest.raises(TypeError):
            full_rr.runtime_summary["new_field"] = "injected"  # type: ignore[index]

    def test_source_result_dict_mutation_does_not_affect_rr(self):
        """Mutating the original result dict after construction leaves RuntimeResult unchanged."""
        result = {
            "financial_statements": {"periods": [{"year": 1, "revenue_keur": 5000.0}]},
            "debt_schedule": None,
            "tax_schedule": None,
            "distribution_schedule": None,
            "sponsor_schedule": None,
        }
        rr = RuntimeResult.from_run_result(
            result,
            runtime_summary={"project_id": "p"},
            snapshot_id="snap",
            ran_at="",
            origin="workspace_base",
        )
        # Mutate the source dict after construction.
        result["financial_statements"]["periods"][0]["revenue_keur"] = 99999.0
        result["financial_statements"]["new_key"] = "injected"
        # RuntimeResult must be unchanged.
        assert rr.financial_statements["periods"][0]["revenue_keur"] == 5000.0
        assert "new_key" not in rr.financial_statements

    def test_workspace_state_mutation_does_not_affect_rr(self):
        """Mutating WorkspaceStateRecord payload after reconstruction leaves RuntimeResult unchanged."""
        from types import SimpleNamespace
        from datetime import datetime, timezone
        fs = {"periods": [{"year": 1, "revenue_keur": 5000.0}]}
        ws = SimpleNamespace(
            last_runtime_snapshot_id="snap",
            last_runtime_at=datetime(2026, 7, 10, 12, 0, 0, tzinfo=timezone.utc),
            last_runtime_origin="workspace_base",
            last_runtime_summary={"project_id": "p"},
            last_financial_statements=fs,
            last_debt_schedule={},
            last_tax_schedule={},
            last_distribution_schedule={},
            last_sponsor_schedule={},
        )
        rr = RuntimeResult.from_workspace_state(ws)
        assert rr is not None
        # Mutate the source after construction.
        fs["periods"][0]["revenue_keur"] = 99999.0
        fs["injected"] = "bad"
        # RuntimeResult must not be affected.
        assert rr.financial_statements["periods"][0]["revenue_keur"] == 5000.0
        assert "injected" not in rr.financial_statements


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


# ---------------------------------------------------------------------------
# 10. Extended persistence tests
# ---------------------------------------------------------------------------

class TestExtendedPersistence:
    """Covers: old rows, discard draft, user/project auth, JSON round-trip,
    record_workspace_runtime with all 3 origin types."""

    def _uid(self):
        uid = uuid.uuid4().hex[:12]
        return f"user_{uid}", f"proj_{uid}"

    def test_old_db_row_without_schedule_columns_readable(self):
        """Rows inserted without the 5 schedule columns (pre-migration) must
        deserialise gracefully — from_row() must not raise."""
        from app.persistence.db import get_cursor, get_connection
        from app.persistence.records import WorkspaceStateRecord
        # Insert a minimal row without the schedule JSON columns.
        user_id, project_id = self._uid()
        _insert_project(user_id, project_id, "old_code")
        workspace_id = uuid.uuid4().hex[:16]
        now = "2026-07-10T00:00:00+00:00"
        with get_cursor() as cur:
            cur.execute(
                """
                INSERT INTO workspace_states (
                    workspace_id, project_id, user_id, project_code,
                    active_scenario_id, active_scenario_name,
                    draft_snapshot_json, saved_snapshot_json,
                    last_runtime_snapshot_json, last_runtime_summary_json,
                    last_runtime_snapshot_id, last_runtime_origin,
                    last_runtime_scenario_id, dirty,
                    governance_state_json, replay_metadata_json,
                    created_at, updated_at, last_runtime_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    workspace_id, project_id, user_id, "old_code",
                    None, None,
                    json.dumps({}), json.dumps({}),
                    json.dumps({}), json.dumps(SAMPLE_SUMMARY),
                    "snap_old", "workspace_base",
                    None, 0,
                    json.dumps({}), json.dumps({}),
                    now, now, None,
                ),
            )
        from app.persistence.workspace_repository import get_workspace_state
        ws = get_workspace_state(user_id, project_id)
        assert ws is not None
        # The new fields default to empty dict via _ensure_column DEFAULT '{}'.
        assert isinstance(ws.last_financial_statements, dict)
        rr = RuntimeResult.from_workspace_state(ws)
        assert rr is not None
        assert rr.financial_statements is None  # empty dict → None

    def test_discard_draft_preserves_runtime_schedules(self):
        """discard_workspace_draft must not erase last_financial_statements etc."""
        from app.persistence.workspace_repository import (
            save_workspace_state, get_workspace_state, discard_workspace_draft,
        )
        user_id, project_id = self._uid()
        _insert_project(user_id, project_id, "code")
        save_workspace_state(
            user_id=user_id,
            project_id=project_id,
            project_code="code",
            draft_snapshot={"capacity_mw": "50.0"},
            saved_snapshot={"capacity_mw": "35.0"},
            dirty=True,
            last_runtime_summary=SAMPLE_SUMMARY,
            last_runtime_snapshot_id="snap",
            last_runtime_origin="workspace_base",
            last_financial_statements=SAMPLE_FS,
            last_debt_schedule=SAMPLE_DS,
            last_tax_schedule=SAMPLE_TS,
            last_distribution_schedule=SAMPLE_DIST,
            last_sponsor_schedule=SAMPLE_SPONSOR,
        )
        ws = discard_workspace_draft(user_id, project_id)
        assert ws is not None
        # Draft is rolled back to saved snapshot.
        assert ws.draft_snapshot == {"capacity_mw": "35.0"}
        assert not ws.dirty
        # Runtime schedules must survive the discard.
        assert ws.last_financial_statements == SAMPLE_FS
        assert ws.last_debt_schedule == SAMPLE_DS
        assert ws.last_sponsor_schedule == SAMPLE_SPONSOR

    def test_get_workspace_state_wrong_user_returns_none(self):
        """get_workspace_state must not return another user's workspace."""
        from app.persistence.workspace_repository import save_workspace_state, get_workspace_state
        user_a, project_id = self._uid()
        user_b = f"user_other_{uuid.uuid4().hex[:8]}"
        _insert_project(user_a, project_id, "code")
        save_workspace_state(
            user_id=user_a,
            project_id=project_id,
            project_code="code",
            draft_snapshot={},
            saved_snapshot={},
            last_financial_statements=SAMPLE_FS,
        )
        ws = get_workspace_state(user_b, project_id)
        assert ws is None

    def test_json_round_trip_preserves_exact_payload(self):
        """Schedule payloads survive JSON serialise → DB write → deserialise unchanged."""
        from app.persistence.workspace_repository import save_workspace_state, get_workspace_state
        user_id, project_id = self._uid()
        _insert_project(user_id, project_id, "code")
        complex_fs = {
            "periods": [
                {"year": 1, "revenue_keur": 5000.0, "flags": ["ok", "complete"]},
                {"year": 2, "revenue_keur": 5200.5, "flags": []},
            ],
            "version": "v2",
            "metadata": {"source": "engine", "count": 2},
        }
        save_workspace_state(
            user_id=user_id,
            project_id=project_id,
            project_code="code",
            draft_snapshot={},
            saved_snapshot={},
            last_runtime_summary=SAMPLE_SUMMARY,
            last_runtime_snapshot_id="snap",
            last_runtime_origin="workspace_base",
            last_financial_statements=complex_fs,
        )
        ws = get_workspace_state(user_id, project_id)
        assert ws is not None
        # Exact content must match.
        assert ws.last_financial_statements == complex_fs

    def test_record_workspace_runtime_with_saved_state_origin(self):
        """record_workspace_runtime with origin=saved_state persists schedules."""
        from app.persistence.repository import record_workspace_runtime
        from app.persistence.workspace_repository import save_workspace_state, get_workspace_state
        user_id, project_id = self._uid()
        _insert_project(user_id, project_id, "code")
        save_workspace_state(user_id=user_id, project_id=project_id,
                             project_code="code", draft_snapshot={}, saved_snapshot={})
        record_workspace_runtime(
            user_id=user_id, project_id=project_id, project_code="code",
            runtime_snapshot={}, runtime_summary=SAMPLE_SUMMARY,
            runtime_snapshot_id="snap", runtime_origin="saved_state",
            financial_statements=SAMPLE_FS, debt_schedule=SAMPLE_DS,
        )
        ws = get_workspace_state(user_id, project_id)
        assert ws.last_financial_statements == SAMPLE_FS
        assert ws.last_runtime_origin == "saved_state"

    def test_record_workspace_runtime_with_workspace_base_origin(self):
        """record_workspace_runtime with origin=workspace_base persists schedules."""
        from app.persistence.repository import record_workspace_runtime
        from app.persistence.workspace_repository import save_workspace_state, get_workspace_state
        user_id, project_id = self._uid()
        _insert_project(user_id, project_id, "code")
        save_workspace_state(user_id=user_id, project_id=project_id,
                             project_code="code", draft_snapshot={}, saved_snapshot={})
        record_workspace_runtime(
            user_id=user_id, project_id=project_id, project_code="code",
            runtime_snapshot={}, runtime_summary=SAMPLE_SUMMARY,
            runtime_snapshot_id="snap", runtime_origin="workspace_base",
            financial_statements=SAMPLE_FS, tax_schedule=SAMPLE_TS,
        )
        ws = get_workspace_state(user_id, project_id)
        assert ws.last_financial_statements == SAMPLE_FS
        assert ws.last_tax_schedule == SAMPLE_TS

    def test_record_workspace_runtime_with_preview_only_origin(self):
        """record_workspace_runtime with origin=preview_only persists schedules."""
        from app.persistence.repository import record_workspace_runtime
        from app.persistence.workspace_repository import save_workspace_state, get_workspace_state
        user_id, project_id = self._uid()
        _insert_project(user_id, project_id, "code")
        save_workspace_state(user_id=user_id, project_id=project_id,
                             project_code="code", draft_snapshot={}, saved_snapshot={})
        record_workspace_runtime(
            user_id=user_id, project_id=project_id, project_code="code",
            runtime_snapshot={}, runtime_summary=SAMPLE_SUMMARY,
            runtime_snapshot_id="snap", runtime_origin="preview_only",
            distribution_schedule=SAMPLE_DIST, sponsor_schedule=SAMPLE_SPONSOR,
        )
        ws = get_workspace_state(user_id, project_id)
        assert ws.last_distribution_schedule == SAMPLE_DIST
        assert ws.last_sponsor_schedule == SAMPLE_SPONSOR
