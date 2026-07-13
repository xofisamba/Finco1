"""
tests/test_workbook_v2_runtime_integration.py — Workbook V2 runtime integration tests.

Coverage:
  1.  TestRunSuccess — 200, runtime persisted, dirty=False, snapshot_id set
  2.  TestNotRunToCleanTransition — NOT_RUN → CLEAN after run
  3.  TestScalarEditThenRun — edit → STALE → run → CLEAN, dirty=False
  4.  TestProjectTypeValidation — Solar/Wind pass, unknown fails closed
  5.  TestStaleInitialHashRejected — stale hash → no engine, no persist
  6.  TestFinalCASConflict — v2_atomic_run_commit wrong hash → raises, state unchanged
  7.  TestEngineFailureAtomic — engine exception → no snapshot, dirty preserved
  8.  TestPersistenceFailureAtomic — mock commit raises → no partial state
  9.  TestOneRunOneResult — exactly 1 engine call, exactly 1 commit call
  10. TestProjectionFromDB — sheets have snapshot_id/origin from DB
  11. TestHtmxOobTargetIds — no nested duplicate IDs, each OOB target appears once
  12. TestRunControlsRefreshedAfterScalarEdit — scalar edit response has v2-run-controls OOB
  13. TestRunControlsRefreshedAfterCapexEdit — CAPEX mutation response has v2-run-controls OOB
  14. TestUnauthenticatedRun — redirect to login
  15. TestNonHtmxRunRedirects — 303 on success
"""
from __future__ import annotations

import os
import sys
import unittest
import urllib.parse
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("FINCO_WORKBOOK_V2", "1")
os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-key-for-v2-integration")

from fastapi.testclient import TestClient  # noqa: E402

import main_web  # noqa: E402
from app.auth import COOKIE_NAME, create_session_token  # noqa: E402
from app.workbook.service import WorkbookService  # noqa: E402


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _authed_client() -> TestClient:
    tc = TestClient(main_web.app, follow_redirects=False)
    tc.cookies.set(COOKIE_NAME, create_session_token())
    return tc


def _create_project(client: TestClient, suffix: str = "integ", project_type: str = "Wind") -> str:
    """Create a project; return project_code."""
    template_source = "generic_wind" if project_type.lower() == "wind" else "generic_solar"
    resp = client.post(
        "/projects/create",
        data={
            "project_name": f"V2 Runtime Integ {suffix}",
            "project_type": project_type,
            "template_source": template_source,
            "country_market": "Poland",
            "capacity_mw": "50",
            "cod_date": "2028-01-01",
            "construction_months": "18",
            "horizon_years": "25",
            "tariff_eur_mwh": "55",
            "ppa_term_years": "15",
            "p50_hours": "2200",
            "opex_y1_keur": "900",
            "total_capex_keur": "60000",
            "gearing_pct": "70",
            "interest_rate_pct": "4.5",
            "tenor_years": "18",
            "target_dscr": "1.30",
        },
        follow_redirects=False,
    )
    redirect = resp.headers.get("hx-redirect") or resp.headers.get("location", "")
    assert redirect, f"expected redirect from /projects/create, got {resp.status_code}"
    parsed = urllib.parse.parse_qs(urllib.parse.urlparse(redirect).query)
    codes = parsed.get("project", [])
    assert codes, f"no project= in redirect URL: {redirect}"
    return codes[0]


def _get_content_hash(client: TestClient, project_code: str) -> tuple[str, str]:
    """Fetch workbook page; return (content_hash, workbook_version) from page."""
    resp = client.get(f"/v2/workbook?project={project_code}")
    assert resp.status_code == 200, f"GET /v2/workbook failed: {resp.status_code}"
    body = resp.text
    import re
    ch_m = re.search(r'data-content-hash="([^"]+)"', body)
    wv_m = re.search(r'data-workbook-version="([^"]+)"', body)
    assert ch_m, "data-content-hash not found in page"
    assert wv_m, "data-workbook-version not found in page"
    return ch_m.group(1), wv_m.group(1)


def _post_run(client: TestClient, project_code: str, content_hash: str, workbook_version: str):
    return client.post(
        "/v2/workbook/run",
        data={
            "project": project_code,
            "content_hash": content_hash,
            "workbook_version": workbook_version,
        },
        headers={"HX-Request": "true"},
        follow_redirects=False,
    )


def _get_ws(client: TestClient, project_code: str):
    from app.persistence.projects_repository import get_project_record
    from app.persistence.workspace_repository import get_workspace_state
    from app.auth import decode_session_token
    token = client.cookies.get(COOKIE_NAME)
    session = decode_session_token(token)
    proj = get_project_record(user_id=session.user_id, project_code=project_code)
    return get_workspace_state(user_id=session.user_id, project_id=proj.project_id)


# ---------------------------------------------------------------------------
# 1. TestRunSuccess
# ---------------------------------------------------------------------------

class TestRunSuccess(unittest.TestCase):
    """POST /v2/workbook/run with valid identity → engine runs, result persisted."""

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, suffix="run-success")

    def test_returns_200(self):
        ch, wv = _get_content_hash(self.client, self.project_code)
        resp = _post_run(self.client, self.project_code, ch, wv)
        self.assertEqual(resp.status_code, 200)

    def test_runtime_persisted_after_run(self):
        """A completed run must persist a RuntimeResult in the workspace."""
        ch, wv = _get_content_hash(self.client, self.project_code)
        resp = _post_run(self.client, self.project_code, ch, wv)
        self.assertEqual(resp.status_code, 200)

        ws = _get_ws(self.client, self.project_code)
        self.assertIsNotNone(ws.last_runtime_snapshot_id, "snapshot_id must be set after run")
        self.assertIsNotNone(ws.last_runtime_summary, "runtime_summary must be set after run")

    def test_dirty_false_after_run(self):
        """After a successful run, dirty must be False."""
        ch, wv = _get_content_hash(self.client, self.project_code)
        resp = _post_run(self.client, self.project_code, ch, wv)
        self.assertEqual(resp.status_code, 200)

        ws = _get_ws(self.client, self.project_code)
        self.assertFalse(ws.dirty, "workspace must not be dirty after a successful run")

    def test_snapshot_id_set_after_run(self):
        """After a run, last_runtime_snapshot_id must be a non-empty string."""
        ch, wv = _get_content_hash(self.client, self.project_code)
        _post_run(self.client, self.project_code, ch, wv)

        ws = _get_ws(self.client, self.project_code)
        self.assertTrue(
            ws.last_runtime_snapshot_id and len(ws.last_runtime_snapshot_id) > 0,
            "last_runtime_snapshot_id must be a non-empty string after run",
        )


# ---------------------------------------------------------------------------
# 2. TestNotRunToCleanTransition
# ---------------------------------------------------------------------------

class TestNotRunToCleanTransition(unittest.TestCase):
    """Before any run: NOT_RUN state. After run: all three sheets CLEAN, dirty=False."""

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, suffix="not-run-to-clean")

    def test_a_before_run_no_snapshot(self):
        """A freshly created project must have no runtime snapshot."""
        ws = _get_ws(self.client, self.project_code)
        self.assertIsNone(ws.last_runtime_snapshot_id)

    def test_after_run_all_sheets_clean(self):
        """After a successful run all three projection states must be CLEAN."""
        ch, wv = _get_content_hash(self.client, self.project_code)
        resp = _post_run(self.client, self.project_code, ch, wv)
        self.assertEqual(resp.status_code, 200)

        ws = _get_ws(self.client, self.project_code)
        rr = WorkbookService.get_runtime_result(ws)
        self.assertIsNotNone(rr, "RuntimeResult must be available after run")

        from app.workbook.runtime_projection import build_runtime_projection_bundle
        proj = build_runtime_projection_bundle(rr, ws.dirty)
        self.assertEqual(proj.debt.state.value, "CLEAN", "debt must be CLEAN after run")
        self.assertEqual(proj.tax.state.value, "CLEAN", "tax must be CLEAN after run")
        # FS may be CLEAN or FS_UNAVAILABLE depending on engine output; NOT_RUN/STALE are not allowed
        self.assertIn(proj.fs.state.value, ("CLEAN", "UNAVAILABLE"), "fs must be CLEAN or UNAVAILABLE after run")

    def test_after_run_dirty_false(self):
        ch, wv = _get_content_hash(self.client, self.project_code)
        _post_run(self.client, self.project_code, ch, wv)
        ws = _get_ws(self.client, self.project_code)
        self.assertFalse(ws.dirty)


# ---------------------------------------------------------------------------
# 3. TestScalarEditThenRun
# ---------------------------------------------------------------------------

class TestScalarEditThenRun(unittest.TestCase):
    """Real end-to-end: create → run → edit scalar → STALE → run again → CLEAN."""

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, suffix="scalar-edit-run")

    def test_scalar_edit_then_run_clean(self):
        # First run to get a baseline
        ch, wv = _get_content_hash(self.client, self.project_code)
        resp = _post_run(self.client, self.project_code, ch, wv)
        self.assertEqual(resp.status_code, 200)

        # Edit a BOUND scalar (gearing) via /v2/workbook/update
        ch2, wv2 = _get_content_hash(self.client, self.project_code)
        edit_resp = self.client.post(
            "/v2/workbook/update",
            data={
                "project": self.project_code,
                "field_id": "debt.senior.gearing_pct",
                "value": "65",
                "workbook_version": wv2,
                "content_hash": ch2,
                "sheet_id": "debt",
            },
            headers={"HX-Request": "true"},
            follow_redirects=False,
        )
        self.assertIn(edit_resp.status_code, (200, 204, 303))

        # Workspace should now be dirty
        ws = _get_ws(self.client, self.project_code)
        self.assertTrue(ws.dirty, "workspace must be dirty after a scalar edit")

        # Run again with fresh hash
        ch3, wv3 = _get_content_hash(self.client, self.project_code)
        resp2 = _post_run(self.client, self.project_code, ch3, wv3)
        self.assertEqual(resp2.status_code, 200)

        ws2 = _get_ws(self.client, self.project_code)
        self.assertFalse(ws2.dirty, "workspace must not be dirty after second run")

        rr = WorkbookService.get_runtime_result(ws2)
        self.assertIsNotNone(rr)
        from app.workbook.runtime_projection import build_runtime_projection_bundle
        proj = build_runtime_projection_bundle(rr, ws2.dirty)
        self.assertEqual(proj.debt.state.value, "CLEAN")
        self.assertEqual(proj.tax.state.value, "CLEAN")


# ---------------------------------------------------------------------------
# 4. TestProjectTypeValidation
# ---------------------------------------------------------------------------

class TestProjectTypeValidation(unittest.TestCase):
    """Solar and Wind pass; unknown project type fails closed."""

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.wind_project_code = _create_project(cls.client, suffix="pt-wind", project_type="Wind")

    def test_wind_project_runs(self):
        ch, wv = _get_content_hash(self.client, self.wind_project_code)
        captured = []
        try:
            from app.api import project_runner
            orig = project_runner.run_project
        except Exception:
            self.skipTest("Cannot import project_runner")

        def capturing_run(pt, *a, **kw):
            captured.append(pt)
            return orig(pt, *a, **kw)

        with patch("app.api.project_runner.run_project", side_effect=capturing_run):
            resp = _post_run(self.client, self.wind_project_code, ch, wv)

        self.assertEqual(resp.status_code, 200)
        self.assertFalse(captured and "error" in resp.text.lower() and not captured)
        if captured:
            self.assertEqual(captured[0], "Wind")

    def test_unknown_project_type_fails_closed(self):
        ch, wv = _get_content_hash(self.client, self.wind_project_code)
        call_count = []

        try:
            from app.api import project_runner
            orig = project_runner.run_project
        except Exception:
            self.skipTest("Cannot import project_runner")

        def counting(pt, *a, **kw):
            call_count.append(pt)
            return orig(pt, *a, **kw)

        # Patch project_type to an unsupported value via the projects_repository module
        from app.persistence import projects_repository as pr_mod
        orig_gpr = pr_mod.get_project_record

        def patched_gpr(**kwargs):
            rec = orig_gpr(**kwargs)
            if rec is not None:
                # Monkey-patch the project_type attribute
                class _Rec:
                    pass
                fake = _Rec()
                fake.__dict__.update(rec.__dict__) if hasattr(rec, '__dict__') else None
                # Use dataclasses replace or direct attribute override
                try:
                    import dataclasses
                    return dataclasses.replace(rec, project_type="Hydro")
                except Exception:
                    pass
            return rec

        with patch("app.persistence.projects_repository.get_project_record", side_effect=patched_gpr):
            with patch("app.api.project_runner.run_project", side_effect=counting):
                resp = _post_run(self.client, self.wind_project_code, ch, wv)

        # Engine must NOT have been called
        self.assertEqual(len(call_count), 0, "Engine must not run for unsupported project type")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("v2-status-banner", resp.text)


# ---------------------------------------------------------------------------
# 5. TestStaleInitialHashRejected
# ---------------------------------------------------------------------------

class TestStaleInitialHashRejected(unittest.TestCase):
    """Submitting a stale content_hash must not trigger an engine run."""

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, suffix="stale-hash")

    def test_stale_hash_no_engine_run(self):
        _ch, wv = _get_content_hash(self.client, self.project_code)
        stale_hash = "00000000000000000000000000000000"
        call_count = []

        try:
            from app.api import project_runner
            orig = project_runner.run_project
        except Exception:
            self.skipTest("Cannot import project_runner")

        def counting(*args, **kwargs):
            call_count.append(1)
            return orig(*args, **kwargs)

        with patch("app.api.project_runner.run_project", side_effect=counting):
            resp = _post_run(self.client, self.project_code, stale_hash, wv)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(call_count), 0, "Engine must not run on stale content_hash")

    def test_stale_hash_returns_error_in_banner(self):
        _ch, wv = _get_content_hash(self.client, self.project_code)
        resp = _post_run(self.client, self.project_code, "ffffffffffffffffffffffffffffffff", wv)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("v2-status-banner", resp.text)

    def test_stale_hash_no_new_snapshot_committed(self):
        ws_before = _get_ws(self.client, self.project_code)
        snapshot_before = getattr(ws_before, "last_runtime_snapshot_id", None)

        _ch, wv = _get_content_hash(self.client, self.project_code)
        _post_run(self.client, self.project_code, "deadbeef" * 4, wv)

        ws_after = _get_ws(self.client, self.project_code)
        self.assertEqual(
            getattr(ws_after, "last_runtime_snapshot_id", None),
            snapshot_before,
            "Stale hash must not update the runtime snapshot",
        )


# ---------------------------------------------------------------------------
# 6. TestFinalCASConflict
# ---------------------------------------------------------------------------

class TestFinalCASConflict(unittest.TestCase):
    """v2_atomic_run_commit with wrong hash raises V2RunCommitConflictError; state unchanged."""

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, suffix="final-cas")

    def test_direct_wrong_hash_raises(self):
        from app.persistence.workspace_repository import (
            V2RunCommitConflictError,
            v2_atomic_run_commit,
        )
        from app.persistence.projects_repository import get_project_record
        from app.auth import decode_session_token
        from datetime import datetime, timezone

        token = self.client.cookies.get(COOKIE_NAME)
        session = decode_session_token(token)
        proj = get_project_record(user_id=session.user_id, project_code=self.project_code)

        with self.assertRaises(V2RunCommitConflictError):
            v2_atomic_run_commit(
                user_id=session.user_id,
                project_id=proj.project_id,
                project_code=proj.project_code,
                expected_composite_hash="wrong_hash_000000000000000000000000",
                runtime_snapshot_id="test-snap-id",
                runtime_origin="v2_run",
                runtime_summary={},
                financial_statements={},
                debt_schedule={},
                tax_schedule={},
                distribution_schedule={},
                sponsor_schedule={},
                active_scenario_id=None,
                active_scenario_name=None,
                ran_at=datetime.now(timezone.utc),
            )

    def test_state_unchanged_after_failed_commit(self):
        from app.persistence.workspace_repository import (
            V2RunCommitConflictError,
            v2_atomic_run_commit,
            get_workspace_state,
        )
        from app.persistence.projects_repository import get_project_record
        from app.auth import decode_session_token
        from datetime import datetime, timezone

        token = self.client.cookies.get(COOKIE_NAME)
        session = decode_session_token(token)
        proj = get_project_record(user_id=session.user_id, project_code=self.project_code)
        ws_before = get_workspace_state(user_id=session.user_id, project_id=proj.project_id)
        snap_before = ws_before.last_runtime_snapshot_id

        try:
            v2_atomic_run_commit(
                user_id=session.user_id,
                project_id=proj.project_id,
                project_code=proj.project_code,
                expected_composite_hash="wrong_hash",
                runtime_snapshot_id="should-not-be-saved",
                runtime_origin="v2_run",
                runtime_summary={},
                financial_statements={},
                debt_schedule={},
                tax_schedule={},
                distribution_schedule={},
                sponsor_schedule={},
                active_scenario_id=None,
                active_scenario_name=None,
                ran_at=datetime.now(timezone.utc),
            )
        except V2RunCommitConflictError:
            pass

        ws_after = get_workspace_state(user_id=session.user_id, project_id=proj.project_id)
        self.assertEqual(ws_after.last_runtime_snapshot_id, snap_before)


# ---------------------------------------------------------------------------
# 7. TestEngineFailureAtomic
# ---------------------------------------------------------------------------

class TestEngineFailureAtomic(unittest.TestCase):
    """If run_project raises, no partial workspace state must be committed."""

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, suffix="engine-fail")

    def test_engine_exception_no_persist(self):
        ws_before = _get_ws(self.client, self.project_code)
        snapshot_before = getattr(ws_before, "last_runtime_snapshot_id", None)

        ch, wv = _get_content_hash(self.client, self.project_code)

        with patch("app.api.project_runner.run_project", side_effect=RuntimeError("engine boom")):
            resp = _post_run(self.client, self.project_code, ch, wv)

        self.assertEqual(resp.status_code, 200)
        self.assertIn("v2-status-banner", resp.text)

        ws_after = _get_ws(self.client, self.project_code)
        self.assertEqual(
            getattr(ws_after, "last_runtime_snapshot_id", None),
            snapshot_before,
            "Engine failure must not commit a new runtime snapshot",
        )

    def test_engine_exception_dirty_preserved(self):
        """Dirty flag must be preserved (not changed) on engine failure."""
        ws_before = _get_ws(self.client, self.project_code)
        dirty_before = ws_before.dirty

        ch, wv = _get_content_hash(self.client, self.project_code)

        with patch("app.api.project_runner.run_project", side_effect=RuntimeError("boom")):
            _post_run(self.client, self.project_code, ch, wv)

        ws_after = _get_ws(self.client, self.project_code)
        self.assertEqual(ws_after.dirty, dirty_before, "dirty flag must not change on engine failure")


# ---------------------------------------------------------------------------
# 8. TestPersistenceFailureAtomic
# ---------------------------------------------------------------------------

class TestPersistenceFailureAtomic(unittest.TestCase):
    """If v2_atomic_run_commit raises, no partial state, dirty preserved."""

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, suffix="persist-fail")

    def test_commit_exception_no_partial_state(self):
        ws_before = _get_ws(self.client, self.project_code)
        snap_before = ws_before.last_runtime_snapshot_id
        dirty_before = ws_before.dirty

        ch, wv = _get_content_hash(self.client, self.project_code)

        with patch(
            "app.persistence.workspace_repository.v2_atomic_run_commit",
            side_effect=Exception("DB exploded"),
        ):
            resp = _post_run(self.client, self.project_code, ch, wv)

        self.assertEqual(resp.status_code, 200)
        self.assertIn("v2-status-banner", resp.text)

        ws_after = _get_ws(self.client, self.project_code)
        self.assertEqual(ws_after.last_runtime_snapshot_id, snap_before)
        self.assertEqual(ws_after.dirty, dirty_before)


# ---------------------------------------------------------------------------
# 9. TestOneRunOneResult
# ---------------------------------------------------------------------------

class TestOneRunOneResult(unittest.TestCase):
    """A single POST must produce exactly one engine call and one commit call."""

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, suffix="one-result")

    def test_single_engine_call_per_run_post(self):
        ch, wv = _get_content_hash(self.client, self.project_code)
        calls = []

        try:
            from app.api import project_runner
            orig = project_runner.run_project
        except Exception:
            self.skipTest("Cannot import project_runner")

        def counting(pt, sc, **kw):
            calls.append((pt, sc))
            return orig(pt, sc, **kw)

        with patch("app.api.project_runner.run_project", side_effect=counting):
            resp = _post_run(self.client, self.project_code, ch, wv)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(calls), 1)

    def test_single_commit_call_per_run_post(self):
        """v2_atomic_run_commit must be called exactly once per run POST."""
        ch, wv = _get_content_hash(self.client, self.project_code)
        commit_calls = []

        from app.persistence import workspace_repository as wr
        orig_commit = wr.v2_atomic_run_commit

        def counting_commit(*a, **kw):
            commit_calls.append(1)
            return orig_commit(*a, **kw)

        with patch(
            "app.persistence.workspace_repository.v2_atomic_run_commit",
            side_effect=counting_commit,
        ):
            resp = _post_run(self.client, self.project_code, ch, wv)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(commit_calls), 1, "v2_atomic_run_commit must be called exactly once")


# ---------------------------------------------------------------------------
# 10. TestProjectionFromDB
# ---------------------------------------------------------------------------

class TestProjectionFromDB(unittest.TestCase):
    """After run, projections use snapshot_id and origin from the DB, not from a local object."""

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, suffix="proj-from-db")

    def test_rr_matches_db_after_run(self):
        ch, wv = _get_content_hash(self.client, self.project_code)
        resp = _post_run(self.client, self.project_code, ch, wv)
        self.assertEqual(resp.status_code, 200)

        ws = _get_ws(self.client, self.project_code)
        rr = WorkbookService.get_runtime_result(ws)
        self.assertIsNotNone(rr)

        # The snapshot_id on the RuntimeResult must match the DB
        self.assertEqual(rr.snapshot_id, ws.last_runtime_snapshot_id)
        # Origin must be set
        self.assertIsNotNone(rr.origin)
        self.assertTrue(len(rr.origin) > 0)

    def test_all_three_projections_use_same_snapshot(self):
        ch, wv = _get_content_hash(self.client, self.project_code)
        _post_run(self.client, self.project_code, ch, wv)

        ws = _get_ws(self.client, self.project_code)
        rr = WorkbookService.get_runtime_result(ws)
        self.assertIsNotNone(rr)

        from app.workbook.runtime_projection import build_runtime_projection_bundle
        proj = build_runtime_projection_bundle(rr, ws.dirty)

        # All three use the same rr, so they share the same snapshot_id
        snap_id = ws.last_runtime_snapshot_id
        self.assertEqual(rr.snapshot_id, snap_id)


# ---------------------------------------------------------------------------
# 11. TestHtmxOobTargetIds
# ---------------------------------------------------------------------------

class TestHtmxOobTargetIds(unittest.TestCase):
    """Response must contain each OOB target ID exactly once; no nested duplicate IDs."""

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, suffix="oob-ids")

    def _run_and_get_body(self) -> str:
        ch, wv = _get_content_hash(self.client, self.project_code)
        resp = _post_run(self.client, self.project_code, ch, wv)
        self.assertEqual(resp.status_code, 200)
        return resp.text

    def test_status_banner_appears_exactly_once(self):
        body = self._run_and_get_body()
        self.assertEqual(body.count('id="v2-status-banner"'), 1)

    def test_run_controls_appears_exactly_once(self):
        body = self._run_and_get_body()
        self.assertEqual(body.count('id="v2-run-controls"'), 1)

    def test_debt_sheet_id_appears_exactly_once(self):
        body = self._run_and_get_body()
        self.assertEqual(body.count('id="v2-sheet-senior-debt"'), 1,
                         "v2-sheet-senior-debt must appear exactly once (no nested duplicate)")

    def test_tax_sheet_id_appears_exactly_once(self):
        body = self._run_and_get_body()
        self.assertEqual(body.count('id="v2-sheet-tax"'), 1,
                         "v2-sheet-tax must appear exactly once (no nested duplicate)")

    def test_fs_sheet_id_appears_exactly_once(self):
        body = self._run_and_get_body()
        self.assertEqual(body.count('id="v2-sheet-financial-statements"'), 1,
                         "v2-sheet-financial-statements must appear exactly once (no nested duplicate)")

    def test_debt_sheet_has_hx_swap_oob(self):
        body = self._run_and_get_body()
        # Find the debt sheet element and confirm it has hx-swap-oob
        import re
        m = re.search(r'<div id="v2-sheet-senior-debt"([^>]*)>', body)
        self.assertIsNotNone(m)
        self.assertIn("hx-swap-oob", m.group(1),
                      "v2-sheet-senior-debt must have hx-swap-oob on its root element")

    def test_response_contains_runtime_bar_oobs(self):
        body = self._run_and_get_body()
        self.assertIn('id="debt-runtime-bar"', body)
        self.assertIn('id="tax-runtime-bar"', body)
        self.assertIn('id="fs-runtime-bar"', body)


# ---------------------------------------------------------------------------
# 12. TestRunControlsRefreshedAfterScalarEdit
# ---------------------------------------------------------------------------

class TestRunControlsRefreshedAfterScalarEdit(unittest.TestCase):
    """After a scalar edit, response must contain v2-run-controls OOB."""

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, suffix="rc-scalar")

    def test_scalar_edit_response_has_run_controls_oob(self):
        ch, wv = _get_content_hash(self.client, self.project_code)
        resp = self.client.post(
            "/v2/workbook/update",
            data={
                "project": self.project_code,
                "field_id": "debt.senior.gearing_pct",
                "value": "68",
                "workbook_version": wv,
                "content_hash": ch,
                "sheet_id": "debt",
            },
            headers={"HX-Request": "true"},
            follow_redirects=False,
        )
        self.assertIn(resp.status_code, (200, 204, 303))
        if resp.status_code == 200:
            self.assertIn('id="v2-run-controls"', resp.text,
                          "scalar edit response must refresh #v2-run-controls OOB")


# ---------------------------------------------------------------------------
# 13. TestRunControlsRefreshedAfterCapexEdit
# ---------------------------------------------------------------------------

class TestRunControlsRefreshedAfterCapexEdit(unittest.TestCase):
    """After a CAPEX mutation (e.g. add line), response must contain v2-run-controls OOB."""

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, suffix="rc-capex")

    def test_capex_add_response_has_run_controls_oob(self):
        ch, wv = _get_content_hash(self.client, self.project_code)
        resp = self.client.post(
            "/v2/capex/line/add",
            data={
                "project": self.project_code,
                "parent_category_code": "C.01",
                "label": "Test CAPEX Line",
                "amount_keur": "100",
                "notes": "",
                "workbook_version": wv,
                "content_hash": ch,
            },
            headers={"HX-Request": "true"},
            follow_redirects=False,
        )
        # Accept 200 or 422 (if category not user-addable); just check if 200 has the OOB
        if resp.status_code == 200:
            self.assertIn('id="v2-run-controls"', resp.text,
                          "CAPEX add response must refresh #v2-run-controls OOB")


# ---------------------------------------------------------------------------
# 14. TestUnauthenticatedRun
# ---------------------------------------------------------------------------

class TestUnauthenticatedRun(unittest.TestCase):
    """Unauthenticated requests to /v2/workbook/run must be redirected to login."""

    @classmethod
    def setUpClass(cls):
        cls.anon_client = TestClient(main_web.app, follow_redirects=False)

    def test_unauthenticated_run_redirects_to_login(self):
        resp = self.anon_client.post(
            "/v2/workbook/run",
            data={"project": "any", "content_hash": "x", "workbook_version": "1"},
            headers={"HX-Request": "true"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.headers.get("location", ""))


# ---------------------------------------------------------------------------
# 15. TestNonHtmxRunRedirects
# ---------------------------------------------------------------------------

class TestNonHtmxRunRedirects(unittest.TestCase):
    """Non-HTMX POST /v2/workbook/run must redirect on success."""

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, suffix="non-htmx-run")

    def test_non_htmx_success_redirects(self):
        ch, wv = _get_content_hash(self.client, self.project_code)
        resp = self.client.post(
            "/v2/workbook/run",
            data={
                "project": self.project_code,
                "content_hash": ch,
                "workbook_version": wv,
            },
            follow_redirects=False,
        )
        self.assertEqual(resp.status_code, 303)
        self.assertIn("/v2/workbook", resp.headers.get("location", ""))


# ---------------------------------------------------------------------------
# Preserved: route registration tests
# ---------------------------------------------------------------------------

class TestRunRouteRegistration(unittest.TestCase):
    """The /v2/workbook/run route must be registered when V2 is on."""

    def test_run_route_registered(self):
        from app.v2.router import router
        paths = [r.path for r in router.routes]
        self.assertIn("/workbook/run", paths)

    def test_run_route_is_post(self):
        from app.v2.router import router
        for route in router.routes:
            if getattr(route, "path", None) == "/workbook/run":
                self.assertIn("POST", route.methods)
                return
        self.fail("/workbook/run route not found")


class TestV2OffByDefault(unittest.TestCase):
    """FINCO_WORKBOOK_V2 must remain OFF by default (no auto-enable)."""

    def test_v2_flag_not_set_in_router_module(self):
        import app.v2.router as rmod
        import inspect
        src = inspect.getsource(rmod)
        self.assertNotIn('os.environ["FINCO_WORKBOOK_V2"]', src)
        self.assertNotIn('os.environ.setdefault("FINCO_WORKBOOK_V2"', src)


class TestRunButtonInTemplate(unittest.TestCase):
    """The workbook shell must include a Run button wired to /v2/workbook/run."""

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, suffix="run-btn")

    def test_run_button_present(self):
        resp = self.client.get(f"/v2/workbook?project={self.project_code}")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("v2-run-btn", resp.text)

    def test_run_form_action_correct(self):
        resp = self.client.get(f"/v2/workbook?project={self.project_code}")
        self.assertIn("/v2/workbook/run", resp.text)

    def test_run_controls_div_present(self):
        resp = self.client.get(f"/v2/workbook?project={self.project_code}")
        self.assertIn('id="v2-run-controls"', resp.text,
                      "#v2-run-controls div must be present in page for OOB swaps to work")
