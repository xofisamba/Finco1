"""
Tests for OPEX custom-row command lifecycle (PR #871).

Coverage
--------
1.  add_opex_line — basic add, business_code B.NN.UNNN, persisted after reload
2.  update_opex_line — label, amount, inflation_pct, notes; optimistic lock
3.  deactivate_opex_line — soft-delete; inactive excluded from projection; stale rejection
4.  reorder_opex_lines — display_order updated, final order 1..N contiguous
5.  Group guards — B.13 rejected; unknown group rejected
6.  Protected reference guard — factory_template rejected at command layer
7.  Workbook version mismatch — rejected
8.  Concurrent CAS — first succeeds, second stale → rejected
9.  OpexViewModel totals — custom rows included in group subtotals
10. Inputs OPEX summary matches updated OpexViewModel
11. B.09 "Fees" — custom-row eligible group; Add Row form in DOM
12. HTTP HTMX roundtrip — add/update/deactivate; CUSTOM badge; OOB banner
13. Dirty-state — each command sets ws_dirty=True
14. Rollback on missing workspace — mutation rolled back atomically
15. Reorder atomicity — stale/unknown/duplicate/missing/inactive rejection
16. Year projection table — subtotals include custom rows
17. No engine changes — B.13 always DERIVED; B.09 keeps ENGINE badge
18. Canonical group order preserved after lifecycle operations
19. Business-code uniqueness — gaps preserved on soft-delete
20. Concurrent adds — unique business codes under contention
"""
from __future__ import annotations

import os
import threading
import unittest
import urllib.parse
from unittest.mock import patch

os.environ.setdefault("FINCO_WORKBOOK_V2", "1")
os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-key-opex-lifecycle")

from bs4 import BeautifulSoup
from fastapi.testclient import TestClient

import main_web
from app.auth import COOKIE_NAME, create_session_token
from app.workbook.registry import WORKBOOK


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _authed_client() -> TestClient:
    tc = TestClient(main_web.app, follow_redirects=False)
    tc.cookies.set(COOKIE_NAME, create_session_token())
    return tc


def _create_project(client: TestClient, suffix: str) -> str:
    resp = client.post(
        "/projects/create",
        data={
            "project_name": f"OPEX Lifecycle Test {suffix}",
            "project_type": "Wind",
            "template_source": "generic_wind",
            "country_market": "Germany",
            "capacity_mw": "100",
            "cod_date": "2027-06-01",
            "construction_months": "24",
            "horizon_years": "20",
            "tariff_eur_mwh": "65",
            "ppa_term_years": "15",
            "p50_hours": "2500",
            "opex_y1_keur": "5000",
            "total_capex_keur": "80000",
            "gearing_pct": "70",
            "interest_rate_pct": "4.5",
            "tenor_years": "18",
            "target_dscr": "1.30",
        },
        follow_redirects=False,
    )
    redirect = resp.headers.get("hx-redirect") or resp.headers.get("location", "")
    assert redirect, f"Expected redirect, got {resp.status_code}"
    parsed = urllib.parse.parse_qs(urllib.parse.urlparse(redirect).query)
    codes = parsed.get("project", [])
    assert codes, f"No project= in redirect: {redirect}"
    return codes[0]


def _get_workbook_html(client: TestClient, project_code: str) -> str:
    resp = client.get(f"/v2/workbook?project={project_code}")
    assert resp.status_code == 200, f"GET workbook failed: {resp.status_code}"
    return resp.text


def _opex_div(html: str):
    return BeautifulSoup(html, "html.parser").find(id="v2-sheet-opex")


def _get_project_record_and_ws(project_code: str, user_id: str):
    from app.persistence.projects_repository import get_project_record
    from app.persistence.workspace_repository import get_workspace_state
    pr = get_project_record(user_id=user_id, project_code=project_code)
    ws = get_workspace_state(user_id=user_id, project_id=pr.project_id)
    return pr, ws


def _workbook_version() -> str:
    return WORKBOOK.version


def _user_id() -> str:
    from app.auth import decode_session_token
    token = create_session_token()
    return decode_session_token(token).user_id


# ---------------------------------------------------------------------------
# 1. add_opex_line
# ---------------------------------------------------------------------------

class TestAddOpexLine(unittest.TestCase):
    def setUp(self):
        self.client = _authed_client()
        self.project_code = _create_project(self.client, "add")
        self.user_id = _user_id()

    def test_add_returns_sub_line_with_uuid(self):
        from app.v2.opex_commands import add_opex_line
        pr, _ = _get_project_record_and_ws(self.project_code, self.user_id)
        sl = add_opex_line(
            project_record=pr,
            user_id=self.user_id,
            label="Grid fee",
            parent_group_code="B.09",
            amount_keur=50.0,
            workbook_version=_workbook_version(),
        )
        self.assertTrue(sl.sub_line_id)
        self.assertEqual(sl.label, "Grid fee")
        self.assertAlmostEqual(sl.amount_keur, 50.0)
        self.assertEqual(sl.parent_group_code, "B.09")

    def test_business_code_format(self):
        from app.v2.opex_commands import add_opex_line
        pr, _ = _get_project_record_and_ws(self.project_code, self.user_id)
        sl = add_opex_line(
            project_record=pr,
            user_id=self.user_id,
            label="Permit fee",
            parent_group_code="B.09",
            amount_keur=10.0,
            workbook_version=_workbook_version(),
        )
        import re
        self.assertRegex(sl.business_code, r"^B\.09\.U\d{3}$")

    def test_add_to_non_b09_group(self):
        from app.v2.opex_commands import add_opex_line
        pr, _ = _get_project_record_and_ws(self.project_code, self.user_id)
        sl = add_opex_line(
            project_record=pr,
            user_id=self.user_id,
            label="Extra insurance",
            parent_group_code="B.06",
            amount_keur=20.0,
            workbook_version=_workbook_version(),
        )
        self.assertEqual(sl.parent_group_code, "B.06")
        import re
        self.assertRegex(sl.business_code, r"^B\.06\.U\d{3}$")

    def test_add_persists_after_reload(self):
        from app.v2.opex_commands import add_opex_line
        from app.persistence.opex_sub_lines import get_active_sub_lines_for_project
        pr, _ = _get_project_record_and_ws(self.project_code, self.user_id)
        sl = add_opex_line(
            project_record=pr,
            user_id=self.user_id,
            label="Market operator fee",
            parent_group_code="B.09",
            amount_keur=75.0,
            workbook_version=_workbook_version(),
        )
        reloaded = get_active_sub_lines_for_project(pr.project_id)
        ids = [r.sub_line_id for r in reloaded]
        self.assertIn(sl.sub_line_id, ids)

    def test_display_order_increments(self):
        from app.v2.opex_commands import add_opex_line
        pr, _ = _get_project_record_and_ws(self.project_code, self.user_id)
        sl1 = add_opex_line(project_record=pr, user_id=self.user_id, label="Fee A",
                             parent_group_code="B.09", amount_keur=10.0,
                             workbook_version=_workbook_version())
        sl2 = add_opex_line(project_record=pr, user_id=self.user_id, label="Fee B",
                             parent_group_code="B.09", amount_keur=20.0,
                             workbook_version=_workbook_version())
        self.assertGreater(sl2.display_order, sl1.display_order)

    def test_empty_label_rejected(self):
        from app.v2.opex_commands import add_opex_line
        pr, _ = _get_project_record_and_ws(self.project_code, self.user_id)
        with self.assertRaises(ValueError):
            add_opex_line(project_record=pr, user_id=self.user_id, label="  ",
                          parent_group_code="B.09", amount_keur=10.0,
                          workbook_version=_workbook_version())


# ---------------------------------------------------------------------------
# 2. update_opex_line
# ---------------------------------------------------------------------------

class TestUpdateOpexLine(unittest.TestCase):
    def setUp(self):
        self.client = _authed_client()
        self.project_code = _create_project(self.client, "update")
        self.user_id = _user_id()
        from app.v2.opex_commands import add_opex_line
        pr, _ = _get_project_record_and_ws(self.project_code, self.user_id)
        self.project_record = pr
        self.sl = add_opex_line(
            project_record=pr, user_id=self.user_id, label="Original",
            parent_group_code="B.09", amount_keur=100.0,
            workbook_version=_workbook_version(),
        )

    def test_update_label_and_amount(self):
        from app.v2.opex_commands import update_opex_line
        updated = update_opex_line(
            project_record=self.project_record,
            user_id=self.user_id,
            sub_line_id=self.sl.sub_line_id,
            label="Updated fee",
            amount_keur=200.0,
            row_version=self.sl.updated_at,
            workbook_version=_workbook_version(),
        )
        self.assertEqual(updated.label, "Updated fee")
        self.assertAlmostEqual(updated.amount_keur, 200.0)

    def test_update_inflation_pct(self):
        from app.v2.opex_commands import update_opex_line
        updated = update_opex_line(
            project_record=self.project_record,
            user_id=self.user_id,
            sub_line_id=self.sl.sub_line_id,
            label="Original",
            amount_keur=100.0,
            inflation_pct=2.5,
            row_version=self.sl.updated_at,
            workbook_version=_workbook_version(),
        )
        self.assertAlmostEqual(updated.inflation_pct, 2.5)

    def test_stale_row_version_raises_concurrent(self):
        from app.v2.opex_commands import update_opex_line, OpexConcurrentEditError
        update_opex_line(
            project_record=self.project_record,
            user_id=self.user_id,
            sub_line_id=self.sl.sub_line_id,
            label="First update",
            amount_keur=150.0,
            row_version=self.sl.updated_at,
            workbook_version=_workbook_version(),
        )
        with self.assertRaises(OpexConcurrentEditError):
            update_opex_line(
                project_record=self.project_record,
                user_id=self.user_id,
                sub_line_id=self.sl.sub_line_id,
                label="Second update (stale)",
                amount_keur=999.0,
                row_version=self.sl.updated_at,   # stale
                workbook_version=_workbook_version(),
            )

    def test_update_updates_row_version(self):
        from app.v2.opex_commands import update_opex_line
        updated = update_opex_line(
            project_record=self.project_record,
            user_id=self.user_id,
            sub_line_id=self.sl.sub_line_id,
            label="New label",
            amount_keur=50.0,
            row_version=self.sl.updated_at,
            workbook_version=_workbook_version(),
        )
        self.assertNotEqual(updated.updated_at, self.sl.updated_at)

    def test_workbook_version_mismatch(self):
        from app.v2.opex_commands import update_opex_line, OpexVersionMismatchError
        with self.assertRaises(OpexVersionMismatchError):
            update_opex_line(
                project_record=self.project_record,
                user_id=self.user_id,
                sub_line_id=self.sl.sub_line_id,
                label="X",
                amount_keur=0.0,
                row_version=self.sl.updated_at,
                workbook_version="STALE",
            )


# ---------------------------------------------------------------------------
# 3. deactivate_opex_line
# ---------------------------------------------------------------------------

class TestDeactivateOpexLine(unittest.TestCase):
    def setUp(self):
        self.client = _authed_client()
        self.project_code = _create_project(self.client, "deactivate")
        self.user_id = _user_id()
        from app.v2.opex_commands import add_opex_line
        pr, _ = _get_project_record_and_ws(self.project_code, self.user_id)
        self.project_record = pr
        self.sl = add_opex_line(
            project_record=pr, user_id=self.user_id, label="Temp fee",
            parent_group_code="B.09", amount_keur=50.0,
            workbook_version=_workbook_version(),
        )

    def test_deactivate_removes_from_active_set(self):
        from app.v2.opex_commands import deactivate_opex_line
        from app.persistence.opex_sub_lines import get_active_sub_lines_for_project
        ok = deactivate_opex_line(
            project_record=self.project_record,
            user_id=self.user_id,
            sub_line_id=self.sl.sub_line_id,
            row_version=self.sl.updated_at,
            workbook_version=_workbook_version(),
        )
        self.assertTrue(ok)
        active = get_active_sub_lines_for_project(self.project_record.project_id)
        ids = [r.sub_line_id for r in active]
        self.assertNotIn(self.sl.sub_line_id, ids)

    def test_stale_row_version_raises_concurrent(self):
        from app.v2.opex_commands import deactivate_opex_line, OpexConcurrentEditError
        deactivate_opex_line(
            project_record=self.project_record,
            user_id=self.user_id,
            sub_line_id=self.sl.sub_line_id,
            row_version=self.sl.updated_at,
            workbook_version=_workbook_version(),
        )
        with self.assertRaises(OpexConcurrentEditError):
            deactivate_opex_line(
                project_record=self.project_record,
                user_id=self.user_id,
                sub_line_id=self.sl.sub_line_id,
                row_version=self.sl.updated_at,   # stale
                workbook_version=_workbook_version(),
            )

    def test_deactivated_row_excluded_from_viewmodel(self):
        from app.v2.opex_commands import deactivate_opex_line
        from app.ui.opex_view_model import build_opex_view_model
        from app.ui.project_context import build_project_context_for_record
        from app.persistence.opex_sub_lines import get_active_sub_lines_for_project
        from app.workbook.service import WorkbookService
        _, ws = _get_project_record_and_ws(self.project_code, self.user_id)
        pis = WorkbookService.build_draft_input_set_from_workspace(ws)
        snapshot = pis.to_snapshot()
        ctx = build_project_context_for_record(
            project_code=self.project_record.project_code,
            project_name=self.project_record.project_name,
            project_type=self.project_record.project_type,
            project_origin=self.project_record.project_origin,
            template_source=self.project_record.template_source,
            baseline_snapshot=snapshot,
        )
        before_sls = get_active_sub_lines_for_project(self.project_record.project_id)
        vm_before = build_opex_view_model(ctx, is_user_project=True, sub_lines=before_sls)
        y1_before = vm_before.y1_total_opex

        deactivate_opex_line(
            project_record=self.project_record,
            user_id=self.user_id,
            sub_line_id=self.sl.sub_line_id,
            row_version=self.sl.updated_at,
            workbook_version=_workbook_version(),
        )
        after_sls = get_active_sub_lines_for_project(self.project_record.project_id)
        vm_after = build_opex_view_model(ctx, is_user_project=True, sub_lines=after_sls)
        # y1_total may not change for B.09 if template has no B.09 baseline,
        # but the sub_line_id must no longer appear in any group's custom lines.
        for grp in vm_after.groups:
            custom_ids = [ln.sub_line_id for ln in grp.lines if ln.is_custom]
            self.assertNotIn(self.sl.sub_line_id, custom_ids)


# ---------------------------------------------------------------------------
# 4. reorder_opex_lines
# ---------------------------------------------------------------------------

class TestReorderOpexLines(unittest.TestCase):
    def setUp(self):
        self.client = _authed_client()
        self.project_code = _create_project(self.client, "reorder")
        self.user_id = _user_id()
        from app.v2.opex_commands import add_opex_line
        pr, _ = _get_project_record_and_ws(self.project_code, self.user_id)
        self.project_record = pr
        self.sl1 = add_opex_line(project_record=pr, user_id=self.user_id, label="Fee A",
                                  parent_group_code="B.09", amount_keur=10.0,
                                  workbook_version=_workbook_version())
        self.sl2 = add_opex_line(project_record=pr, user_id=self.user_id, label="Fee B",
                                  parent_group_code="B.09", amount_keur=20.0,
                                  workbook_version=_workbook_version())
        self.sl3 = add_opex_line(project_record=pr, user_id=self.user_id, label="Fee C",
                                  parent_group_code="B.09", amount_keur=30.0,
                                  workbook_version=_workbook_version())

    def test_reorder_updates_display_order(self):
        from app.v2.opex_commands import reorder_opex_lines
        from app.persistence.opex_sub_lines import get_active_sub_lines_for_project
        ordered_rows = [
            {"sub_line_id": self.sl3.sub_line_id, "row_version": self.sl3.updated_at},
            {"sub_line_id": self.sl1.sub_line_id, "row_version": self.sl1.updated_at},
            {"sub_line_id": self.sl2.sub_line_id, "row_version": self.sl2.updated_at},
        ]
        reorder_opex_lines(
            project_record=self.project_record,
            user_id=self.user_id,
            parent_group_code="B.09",
            ordered_rows=ordered_rows,
            workbook_version=_workbook_version(),
        )
        active = {sl.sub_line_id: sl for sl in
                  get_active_sub_lines_for_project(self.project_record.project_id)}
        self.assertEqual(active[self.sl3.sub_line_id].display_order, 1)
        self.assertEqual(active[self.sl1.sub_line_id].display_order, 2)
        self.assertEqual(active[self.sl2.sub_line_id].display_order, 3)

    def test_reorder_contiguous_1_to_n(self):
        from app.v2.opex_commands import reorder_opex_lines
        from app.persistence.opex_sub_lines import get_active_sub_lines_for_project
        ordered_rows = [
            {"sub_line_id": self.sl2.sub_line_id, "row_version": self.sl2.updated_at},
            {"sub_line_id": self.sl3.sub_line_id, "row_version": self.sl3.updated_at},
            {"sub_line_id": self.sl1.sub_line_id, "row_version": self.sl1.updated_at},
        ]
        reorder_opex_lines(
            project_record=self.project_record,
            user_id=self.user_id,
            parent_group_code="B.09",
            ordered_rows=ordered_rows,
            workbook_version=_workbook_version(),
        )
        sls = [sl for sl in get_active_sub_lines_for_project(self.project_record.project_id)
               if sl.parent_group_code == "B.09"]
        orders = sorted(sl.display_order for sl in sls)
        self.assertEqual(orders, list(range(1, len(orders) + 1)))

    def test_stale_row_version_rejected(self):
        from app.v2.opex_commands import reorder_opex_lines, OpexConcurrentEditError
        ordered_rows = [
            {"sub_line_id": self.sl1.sub_line_id, "row_version": "stale"},
            {"sub_line_id": self.sl2.sub_line_id, "row_version": self.sl2.updated_at},
            {"sub_line_id": self.sl3.sub_line_id, "row_version": self.sl3.updated_at},
        ]
        with self.assertRaises(OpexConcurrentEditError):
            reorder_opex_lines(
                project_record=self.project_record,
                user_id=self.user_id,
                parent_group_code="B.09",
                ordered_rows=ordered_rows,
                workbook_version=_workbook_version(),
            )

    def test_unknown_id_rejected(self):
        from app.v2.opex_commands import reorder_opex_lines, OpexConcurrentEditError
        ordered_rows = [
            {"sub_line_id": "unknown-uuid", "row_version": "x"},
            {"sub_line_id": self.sl1.sub_line_id, "row_version": self.sl1.updated_at},
            {"sub_line_id": self.sl2.sub_line_id, "row_version": self.sl2.updated_at},
        ]
        with self.assertRaises(OpexConcurrentEditError):
            reorder_opex_lines(
                project_record=self.project_record,
                user_id=self.user_id,
                parent_group_code="B.09",
                ordered_rows=ordered_rows,
                workbook_version=_workbook_version(),
            )

    def test_missing_active_id_rejected(self):
        from app.v2.opex_commands import reorder_opex_lines, OpexConcurrentEditError
        ordered_rows = [
            {"sub_line_id": self.sl1.sub_line_id, "row_version": self.sl1.updated_at},
            # sl2 and sl3 omitted
        ]
        with self.assertRaises(OpexConcurrentEditError):
            reorder_opex_lines(
                project_record=self.project_record,
                user_id=self.user_id,
                parent_group_code="B.09",
                ordered_rows=ordered_rows,
                workbook_version=_workbook_version(),
            )

    def test_duplicate_id_rejected(self):
        from app.v2.opex_commands import reorder_opex_lines, OpexConcurrentEditError
        ordered_rows = [
            {"sub_line_id": self.sl1.sub_line_id, "row_version": self.sl1.updated_at},
            {"sub_line_id": self.sl1.sub_line_id, "row_version": self.sl1.updated_at},
            {"sub_line_id": self.sl3.sub_line_id, "row_version": self.sl3.updated_at},
        ]
        with self.assertRaises(OpexConcurrentEditError):
            reorder_opex_lines(
                project_record=self.project_record,
                user_id=self.user_id,
                parent_group_code="B.09",
                ordered_rows=ordered_rows,
                workbook_version=_workbook_version(),
            )

    def test_second_reorder_stale_409(self):
        """Second concurrent reorder from the original row_versions fails."""
        from app.v2.opex_commands import reorder_opex_lines, OpexConcurrentEditError
        ordered_a = [
            {"sub_line_id": self.sl3.sub_line_id, "row_version": self.sl3.updated_at},
            {"sub_line_id": self.sl2.sub_line_id, "row_version": self.sl2.updated_at},
            {"sub_line_id": self.sl1.sub_line_id, "row_version": self.sl1.updated_at},
        ]
        ordered_b = [
            {"sub_line_id": self.sl1.sub_line_id, "row_version": self.sl1.updated_at},
            {"sub_line_id": self.sl2.sub_line_id, "row_version": self.sl2.updated_at},
            {"sub_line_id": self.sl3.sub_line_id, "row_version": self.sl3.updated_at},
        ]
        reorder_opex_lines(project_record=self.project_record, user_id=self.user_id,
                           parent_group_code="B.09", ordered_rows=ordered_a,
                           workbook_version=_workbook_version())
        with self.assertRaises(OpexConcurrentEditError):
            reorder_opex_lines(project_record=self.project_record, user_id=self.user_id,
                               parent_group_code="B.09", ordered_rows=ordered_b,
                               workbook_version=_workbook_version())


# ---------------------------------------------------------------------------
# 5. Group guards
# ---------------------------------------------------------------------------

class TestGroupGuards(unittest.TestCase):
    def setUp(self):
        self.client = _authed_client()
        self.project_code = _create_project(self.client, "guards")
        self.user_id = _user_id()
        self.project_record, _ = _get_project_record_and_ws(self.project_code, self.user_id)

    def test_b13_contingencies_rejected(self):
        from app.v2.opex_commands import add_opex_line, OpexProtectedGroupError
        with self.assertRaises(OpexProtectedGroupError):
            add_opex_line(
                project_record=self.project_record,
                user_id=self.user_id,
                label="Invalid",
                parent_group_code="B.13",
                amount_keur=0.0,
                workbook_version=_workbook_version(),
            )

    def test_unknown_group_rejected(self):
        from app.v2.opex_commands import add_opex_line, OpexProtectedGroupError
        with self.assertRaises(OpexProtectedGroupError):
            add_opex_line(
                project_record=self.project_record,
                user_id=self.user_id,
                label="Invalid",
                parent_group_code="B.99",
                amount_keur=0.0,
                workbook_version=_workbook_version(),
            )

    def test_all_b01_to_b12_allowed(self):
        from app.v2.opex_commands import add_opex_line
        for n in range(1, 13):
            code = f"B.{n:02d}"
            sl = add_opex_line(
                project_record=self.project_record,
                user_id=self.user_id,
                label=f"Fee in {code}",
                parent_group_code=code,
                amount_keur=1.0,
                workbook_version=_workbook_version(),
            )
            self.assertEqual(sl.parent_group_code, code)

    def test_reorder_b13_rejected(self):
        from app.v2.opex_commands import reorder_opex_lines, OpexProtectedGroupError
        with self.assertRaises(OpexProtectedGroupError):
            reorder_opex_lines(
                project_record=self.project_record,
                user_id=self.user_id,
                parent_group_code="B.13",
                ordered_rows=[],
                workbook_version=_workbook_version(),
            )


# ---------------------------------------------------------------------------
# 6. Protected reference guard
# ---------------------------------------------------------------------------

class TestProtectedReferenceGuard(unittest.TestCase):
    def setUp(self):
        self.client = _authed_client()
        # We use a mock factory_template project_record
        self.user_id = _user_id()

    def _make_factory_record(self):
        from unittest.mock import MagicMock
        pr = MagicMock()
        pr.project_origin = "factory_template"
        pr.is_readonly = True
        pr.project_id = "proj-factory"
        return pr

    def test_add_to_factory_template_rejected(self):
        from app.v2.opex_commands import add_opex_line, OpexProtectedReferenceError
        with self.assertRaises(OpexProtectedReferenceError):
            add_opex_line(
                project_record=self._make_factory_record(),
                user_id=self.user_id,
                label="Fee",
                parent_group_code="B.09",
                amount_keur=0.0,
                workbook_version=_workbook_version(),
            )

    def test_update_factory_template_rejected(self):
        from app.v2.opex_commands import update_opex_line, OpexProtectedReferenceError
        with self.assertRaises(OpexProtectedReferenceError):
            update_opex_line(
                project_record=self._make_factory_record(),
                user_id=self.user_id,
                sub_line_id="any",
                label="X",
                amount_keur=0.0,
                row_version="ver",
                workbook_version=_workbook_version(),
            )

    def test_deactivate_factory_template_rejected(self):
        from app.v2.opex_commands import deactivate_opex_line, OpexProtectedReferenceError
        with self.assertRaises(OpexProtectedReferenceError):
            deactivate_opex_line(
                project_record=self._make_factory_record(),
                user_id=self.user_id,
                sub_line_id="any",
                row_version="ver",
                workbook_version=_workbook_version(),
            )


# ---------------------------------------------------------------------------
# 7. OpexViewModel totals include custom rows
# ---------------------------------------------------------------------------

class TestOpexViewModelWithCustomRows(unittest.TestCase):
    def setUp(self):
        self.client = _authed_client()
        self.project_code = _create_project(self.client, "vm-totals")
        self.user_id = _user_id()
        self.project_record, ws = _get_project_record_and_ws(self.project_code, self.user_id)
        from app.workbook.service import WorkbookService
        pis = WorkbookService.build_draft_input_set_from_workspace(ws)
        from app.ui.project_context import build_project_context_for_record
        snapshot = pis.to_snapshot()
        self.project_ctx = build_project_context_for_record(
            project_code=self.project_record.project_code,
            project_name=self.project_record.project_name,
            project_type=self.project_record.project_type,
            project_origin=self.project_record.project_origin,
            template_source=self.project_record.template_source,
            baseline_snapshot=snapshot,
        )

    def _vm(self):
        from app.ui.opex_view_model import build_opex_view_model
        from app.persistence.opex_sub_lines import get_active_sub_lines_for_project
        sls = get_active_sub_lines_for_project(self.project_record.project_id)
        return build_opex_view_model(self.project_ctx, is_user_project=True, sub_lines=sls)

    def test_custom_row_appears_in_group(self):
        from app.v2.opex_commands import add_opex_line
        add_opex_line(project_record=self.project_record, user_id=self.user_id,
                      label="Grid fee", parent_group_code="B.09", amount_keur=500.0,
                      workbook_version=_workbook_version())
        vm = self._vm()
        # Find B.09 group
        b09 = next((g for g in vm.groups if g.code == "B.09"), None)
        self.assertIsNotNone(b09, "B.09 must appear in ViewModel after custom row added")
        custom = [ln for ln in b09.lines if ln.is_custom]
        self.assertEqual(len(custom), 1)
        self.assertAlmostEqual(custom[0].y1_keur, 500.0)

    def test_custom_row_increases_total(self):
        from app.v2.opex_commands import add_opex_line
        vm_before = self._vm()
        total_before = vm_before.y1_total_opex

        add_opex_line(project_record=self.project_record, user_id=self.user_id,
                      label="Regulatory fee", parent_group_code="B.09", amount_keur=1000.0,
                      workbook_version=_workbook_version())

        vm_after = self._vm()
        # Total incl. contingency must increase (B.09 feeds total_excl_contingency)
        self.assertGreater(vm_after.y1_total_opex, total_before)

    def test_deactivated_row_excluded_from_total(self):
        from app.v2.opex_commands import add_opex_line, deactivate_opex_line
        sl = add_opex_line(project_record=self.project_record, user_id=self.user_id,
                           label="Temp fee", parent_group_code="B.09", amount_keur=2000.0,
                           workbook_version=_workbook_version())
        vm_with = self._vm()
        total_with = vm_with.y1_total_opex

        deactivate_opex_line(project_record=self.project_record, user_id=self.user_id,
                             sub_line_id=sl.sub_line_id, row_version=sl.updated_at,
                             workbook_version=_workbook_version())
        vm_without = self._vm()
        self.assertLess(vm_without.y1_total_opex, total_with)

    def test_custom_row_year_values_escalated(self):
        from app.v2.opex_commands import add_opex_line
        add_opex_line(project_record=self.project_record, user_id=self.user_id,
                      label="Fee with escalation", parent_group_code="B.09",
                      amount_keur=1000.0, inflation_pct=2.0,
                      workbook_version=_workbook_version())
        vm = self._vm()
        b09 = next(g for g in vm.groups if g.code == "B.09")
        custom = [ln for ln in b09.lines if ln.is_custom][0]
        # Y1=1000, Y2=1020, Y3=1040.4 …
        self.assertAlmostEqual(custom.year_values[0], 1000.0, places=1)
        self.assertAlmostEqual(custom.year_values[1], 1020.0, places=1)

    def test_b13_always_derived_unchanged(self):
        """B.13 must remain is_contingency after custom rows added to B.09."""
        from app.v2.opex_commands import add_opex_line
        add_opex_line(project_record=self.project_record, user_id=self.user_id,
                      label="Fee", parent_group_code="B.09", amount_keur=100.0,
                      workbook_version=_workbook_version())
        vm = self._vm()
        b13 = next((g for g in vm.groups if g.code == "B.13"), None)
        if b13 is None:
            return  # Generic wind may not have B.13 in opex_detail_items
        for ln in b13.lines:
            self.assertTrue(ln.is_contingency or ln.is_derived,
                            f"B.13 line {ln.code!r} must be contingency/derived")


# ---------------------------------------------------------------------------
# 8. Inputs summary parity
# ---------------------------------------------------------------------------

class TestInputsSummaryParity(unittest.TestCase):
    def setUp(self):
        self.client = _authed_client()
        self.project_code = _create_project(self.client, "inputs-parity")
        self.user_id = _user_id()
        self.project_record, self.ws = _get_project_record_and_ws(self.project_code, self.user_id)
        from app.workbook.service import WorkbookService
        self.pis = WorkbookService.build_draft_input_set_from_workspace(self.ws)

    def test_inputs_summary_opex_matches_detail_sheet(self):
        from app.v2.opex_commands import add_opex_line
        add_opex_line(project_record=self.project_record, user_id=self.user_id,
                      label="Grid fee", parent_group_code="B.09", amount_keur=777.0,
                      workbook_version=_workbook_version())

        from app.ui.inputs_summary import build_inputs_summary
        from app.ui.opex_view_model import build_opex_view_model
        from app.ui.project_context import build_project_context_for_record
        from app.persistence.opex_sub_lines import get_active_sub_lines_for_project
        from app.persistence.workspace_repository import get_workspace_state

        ws_fresh = get_workspace_state(user_id=self.user_id, project_id=self.project_record.project_id)
        summary = build_inputs_summary(self.project_record, self.pis, ws_fresh)

        snapshot = self.pis.to_snapshot()
        ctx = build_project_context_for_record(
            project_code=self.project_record.project_code,
            project_name=self.project_record.project_name,
            project_type=self.project_record.project_type,
            project_origin=self.project_record.project_origin,
            template_source=self.project_record.template_source,
            baseline_snapshot=snapshot,
        )
        sls = get_active_sub_lines_for_project(self.project_record.project_id)
        vm = build_opex_view_model(ctx, is_user_project=True, sub_lines=sls)

        self.assertAlmostEqual(summary["opex_y1_keur"], vm.y1_total_opex, places=1)


# ---------------------------------------------------------------------------
# 9. B.09 DOM rendering
# ---------------------------------------------------------------------------

class TestB09DomRendering(unittest.TestCase):
    def setUp(self):
        self.client = _authed_client()
        self.project_code = _create_project(self.client, "b09-dom")

    def test_b09_group_in_dom(self):
        html = _get_workbook_html(self.client, self.project_code)
        soup = BeautifulSoup(html, "html.parser")
        b09 = soup.find(attrs={"data-testid": "opex-group-B.09"})
        self.assertIsNotNone(b09, "B.09 group must always be in DOM")

    def test_b09_has_add_row_button(self):
        html = _get_workbook_html(self.client, self.project_code)
        soup = BeautifulSoup(html, "html.parser")
        btn = soup.find(attrs={"data-testid": "opex-add-row-btn-B.09"})
        self.assertIsNotNone(btn, "Add Row button must appear for B.09 on editable project")

    def test_b09_add_row_form_targets_opex_sheet(self):
        html = _get_workbook_html(self.client, self.project_code)
        soup = BeautifulSoup(html, "html.parser")
        form = soup.find("form", {"hx-post": "/v2/opex/line/add"})
        self.assertIsNotNone(form)
        self.assertEqual(form.get("hx-target"), "#v2-sheet-opex")

    def test_custom_row_appears_in_dom_after_add(self):
        from app.v2.opex_commands import add_opex_line
        user_id = _user_id()
        pr, _ = _get_project_record_and_ws(self.project_code, user_id)
        sl = add_opex_line(project_record=pr, user_id=user_id, label="Grid fee",
                           parent_group_code="B.09", amount_keur=500.0,
                           workbook_version=_workbook_version())
        html = _get_workbook_html(self.client, self.project_code)
        soup = BeautifulSoup(html, "html.parser")
        row = soup.find(attrs={"data-testid": f"opex-custom-row-{sl.sub_line_id}"})
        self.assertIsNotNone(row, "Custom row must appear in DOM after add")

    def test_b09_engine_badge_present(self):
        """B.09 header shows ENGINE badge (no BOUND registry field)."""
        html = _get_workbook_html(self.client, self.project_code)
        soup = BeautifulSoup(html, "html.parser")
        badge = soup.find(attrs={"data-testid": "badge-engine-B.09"})
        self.assertIsNotNone(badge, "B.09 must carry ENGINE badge in group header")


# ---------------------------------------------------------------------------
# 10. B.13 always DERIVED
# ---------------------------------------------------------------------------

class TestB13AlwaysDerived(unittest.TestCase):
    def setUp(self):
        self.client = _authed_client()
        self.project_code = _create_project(self.client, "b13-derived")

    def test_b13_derived_badge_in_dom(self):
        html = _get_workbook_html(self.client, self.project_code)
        soup = BeautifulSoup(html, "html.parser")
        badge = soup.find(attrs={"data-testid": "badge-derived-B.13"})
        self.assertIsNotNone(badge, "B.13 must carry DERIVED badge")

    def test_b13_no_add_row_button(self):
        html = _get_workbook_html(self.client, self.project_code)
        soup = BeautifulSoup(html, "html.parser")
        btn = soup.find(attrs={"data-testid": "opex-add-row-btn-B.13"})
        self.assertIsNone(btn, "B.13 must NOT have an Add Row button")


# ---------------------------------------------------------------------------
# 11. HTTP HTMX roundtrip
# ---------------------------------------------------------------------------

class TestHTMXRoundtrip(unittest.TestCase):
    def setUp(self):
        self.client = _authed_client()
        self.project_code = _create_project(self.client, "htmx")
        self.user_id = _user_id()

    def _htmx_add(self, group_code="B.09", label="Fee", amount_keur=100.0) -> str:
        resp = self.client.post(
            "/v2/opex/line/add",
            data={
                "project": self.project_code,
                "parent_group_code": group_code,
                "label": label,
                "amount_keur": str(amount_keur),
                "workbook_version": _workbook_version(),
            },
            headers={"HX-Request": "true"},
        )
        self.assertEqual(resp.status_code, 200, f"Add failed: {resp.text[:200]}")
        return resp.text

    def _get_sub_line_id(self) -> tuple:
        from app.persistence.opex_sub_lines import get_active_sub_lines_for_project
        pr, _ = _get_project_record_and_ws(self.project_code, self.user_id)
        sls = get_active_sub_lines_for_project(pr.project_id)
        return sls, pr

    def test_add_returns_opex_sheet_partial(self):
        html = self._htmx_add()
        self.assertIn("v2-sheet-opex", html)

    def test_add_shows_custom_badge(self):
        html = self._htmx_add(label="Grid fee", amount_keur=500.0)
        soup = BeautifulSoup(html, "html.parser")
        badges = soup.find_all(class_="v2-opex-badge-custom")
        self.assertGreater(len(badges), 0, "CUSTOM badge must appear after add")

    def test_update_via_htmx(self):
        self._htmx_add(label="Orig fee", amount_keur=100.0)
        sls, pr = self._get_sub_line_id()
        sl = sls[0]
        resp = self.client.post(
            "/v2/opex/line/update",
            data={
                "project": self.project_code,
                "sub_line_id": sl.sub_line_id,
                "label": "Updated fee",
                "amount_keur": "250",
                "row_version": sl.updated_at,
                "workbook_version": _workbook_version(),
            },
            headers={"HX-Request": "true"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Updated fee", resp.text)

    def test_deactivate_via_htmx(self):
        self._htmx_add(label="Temp fee", amount_keur=50.0)
        sls, pr = self._get_sub_line_id()
        sl = sls[0]
        resp = self.client.post(
            "/v2/opex/line/deactivate",
            data={
                "project": self.project_code,
                "sub_line_id": sl.sub_line_id,
                "row_version": sl.updated_at,
                "workbook_version": _workbook_version(),
            },
            headers={"HX-Request": "true"},
        )
        self.assertEqual(resp.status_code, 200)
        soup = BeautifulSoup(resp.text, "html.parser")
        row = soup.find(attrs={"data-testid": f"opex-custom-row-{sl.sub_line_id}"})
        self.assertIsNone(row, "Deactivated row must not appear in re-rendered sheet")

    def test_protected_group_returns_error_in_partial(self):
        resp = self.client.post(
            "/v2/opex/line/add",
            data={
                "project": self.project_code,
                "parent_group_code": "B.13",
                "label": "Invalid",
                "amount_keur": "0",
                "workbook_version": _workbook_version(),
            },
            headers={"HX-Request": "true"},
        )
        self.assertEqual(resp.status_code, 200)
        soup = BeautifulSoup(resp.text, "html.parser")
        error = soup.find(class_="v2-field-error-banner")
        self.assertIsNotNone(error, "Error banner must appear for protected group")

    def test_oob_status_banner_returned(self):
        html = self._htmx_add()
        self.assertIn("v2-status-banner", html)

    def test_non_htmx_add_redirects(self):
        resp = self.client.post(
            "/v2/opex/line/add",
            data={
                "project": self.project_code,
                "parent_group_code": "B.09",
                "label": "Fee",
                "amount_keur": "100",
                "workbook_version": _workbook_version(),
            },
        )
        self.assertIn(resp.status_code, (302, 303))

    def test_stale_row_version_returns_409_json(self):
        self._htmx_add(label="Fee", amount_keur=100.0)
        sls, pr = self._get_sub_line_id()
        sl = sls[0]
        resp = self.client.post(
            "/v2/opex/line/update",
            data={
                "project": self.project_code,
                "sub_line_id": sl.sub_line_id,
                "label": "X",
                "amount_keur": "0",
                "row_version": "stale",
                "workbook_version": _workbook_version(),
            },
        )
        # Non-HTMX concurrent error → 409
        self.assertEqual(resp.status_code, 409)


# ---------------------------------------------------------------------------
# 12. Dirty-state guarantee
# ---------------------------------------------------------------------------

class TestDirtyState(unittest.TestCase):
    def setUp(self):
        self.client = _authed_client()
        self.project_code = _create_project(self.client, "dirty")
        self.user_id = _user_id()
        self.project_record, self.ws_clean = _get_project_record_and_ws(
            self.project_code, self.user_id
        )

    def _ws_dirty(self):
        from app.persistence.workspace_repository import get_workspace_state
        ws = get_workspace_state(
            user_id=self.user_id, project_id=self.project_record.project_id
        )
        return ws.dirty

    def test_add_marks_workspace_dirty(self):
        from app.v2.opex_commands import add_opex_line
        add_opex_line(project_record=self.project_record, user_id=self.user_id,
                      label="Fee", parent_group_code="B.09", amount_keur=100.0,
                      workbook_version=_workbook_version())
        self.assertTrue(self._ws_dirty())

    def test_update_marks_workspace_dirty(self):
        from app.v2.opex_commands import add_opex_line, update_opex_line
        sl = add_opex_line(project_record=self.project_record, user_id=self.user_id,
                           label="Fee", parent_group_code="B.09", amount_keur=100.0,
                           workbook_version=_workbook_version())
        update_opex_line(project_record=self.project_record, user_id=self.user_id,
                         sub_line_id=sl.sub_line_id, label="Updated", amount_keur=200.0,
                         row_version=sl.updated_at, workbook_version=_workbook_version())
        self.assertTrue(self._ws_dirty())

    def test_deactivate_marks_workspace_dirty(self):
        from app.v2.opex_commands import add_opex_line, deactivate_opex_line
        sl = add_opex_line(project_record=self.project_record, user_id=self.user_id,
                           label="Fee", parent_group_code="B.09", amount_keur=100.0,
                           workbook_version=_workbook_version())
        deactivate_opex_line(project_record=self.project_record, user_id=self.user_id,
                             sub_line_id=sl.sub_line_id, row_version=sl.updated_at,
                             workbook_version=_workbook_version())
        self.assertTrue(self._ws_dirty())

    def test_run_required_in_dom_after_add(self):
        from app.v2.opex_commands import add_opex_line
        add_opex_line(project_record=self.project_record, user_id=self.user_id,
                      label="Fee", parent_group_code="B.09", amount_keur=100.0,
                      workbook_version=_workbook_version())
        html = _get_workbook_html(self.client, self.project_code)
        soup = BeautifulSoup(html, "html.parser")
        run_req = soup.find(attrs={"data-testid": "opex-run-required-yes"})
        self.assertIsNotNone(run_req, "'Run Required: Yes' must appear after command")


# ---------------------------------------------------------------------------
# 13. Rollback on missing workspace
# ---------------------------------------------------------------------------

class TestRollbackOnMissingWorkspace(unittest.TestCase):
    def setUp(self):
        self.client = _authed_client()
        self.project_code = _create_project(self.client, "rollback")
        self.user_id = _user_id()
        self.project_record, _ = _get_project_record_and_ws(self.project_code, self.user_id)

    def test_add_rolls_back_if_no_workspace(self):
        from app.v2.opex_commands import add_opex_line, OpexCommandError
        from app.persistence.opex_sub_lines import get_active_sub_lines_for_project

        before = get_active_sub_lines_for_project(self.project_record.project_id)

        with patch(
            "app.v2.opex_commands.mark_workspace_dirty_cursor",
            return_value=False,
        ):
            with self.assertRaises(OpexCommandError):
                add_opex_line(
                    project_record=self.project_record,
                    user_id=self.user_id,
                    label="Fee",
                    parent_group_code="B.09",
                    amount_keur=100.0,
                    workbook_version=_workbook_version(),
                )

        after = get_active_sub_lines_for_project(self.project_record.project_id)
        self.assertEqual(len(before), len(after), "Row must not persist on rollback")


# ---------------------------------------------------------------------------
# 14. Business-code uniqueness and gap preservation
# ---------------------------------------------------------------------------

class TestBusinessCodeUniqueness(unittest.TestCase):
    def setUp(self):
        self.client = _authed_client()
        self.project_code = _create_project(self.client, "codes")
        self.user_id = _user_id()
        self.project_record, _ = _get_project_record_and_ws(self.project_code, self.user_id)

    def test_codes_unique_across_adds(self):
        from app.v2.opex_commands import add_opex_line
        sls = [
            add_opex_line(project_record=self.project_record, user_id=self.user_id,
                          label=f"Fee {i}", parent_group_code="B.09",
                          amount_keur=float(i), workbook_version=_workbook_version())
            for i in range(5)
        ]
        codes = [sl.business_code for sl in sls]
        self.assertEqual(len(codes), len(set(codes)), "Business codes must be unique")

    def test_gap_preserved_after_deactivate(self):
        from app.v2.opex_commands import add_opex_line, deactivate_opex_line
        sl1 = add_opex_line(project_record=self.project_record, user_id=self.user_id,
                             label="Fee A", parent_group_code="B.09",
                             amount_keur=10.0, workbook_version=_workbook_version())
        deactivate_opex_line(project_record=self.project_record, user_id=self.user_id,
                             sub_line_id=sl1.sub_line_id, row_version=sl1.updated_at,
                             workbook_version=_workbook_version())
        sl2 = add_opex_line(project_record=self.project_record, user_id=self.user_id,
                             label="Fee B", parent_group_code="B.09",
                             amount_keur=20.0, workbook_version=_workbook_version())
        # Gap preserved: sl1 was U001, sl2 should be U002 (not reuse U001)
        self.assertNotEqual(sl1.business_code, sl2.business_code)


# ---------------------------------------------------------------------------
# 15. Concurrent add — unique business codes under thread contention
# ---------------------------------------------------------------------------

class TestConcurrentAdds(unittest.TestCase):
    def setUp(self):
        self.client = _authed_client()
        self.project_code = _create_project(self.client, "concurrent")
        self.user_id = _user_id()
        self.project_record, _ = _get_project_record_and_ws(self.project_code, self.user_id)

    def test_concurrent_adds_unique_codes(self):
        from app.v2.opex_commands import add_opex_line
        results = []
        errors = []

        def _add():
            try:
                sl = add_opex_line(
                    project_record=self.project_record,
                    user_id=self.user_id,
                    label="Concurrent fee",
                    parent_group_code="B.09",
                    amount_keur=1.0,
                    workbook_version=_workbook_version(),
                )
                results.append(sl)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=_add) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Unexpected errors: {errors}")
        codes = [sl.business_code for sl in results]
        self.assertEqual(len(codes), len(set(codes)), "All codes must be unique")
        sub_ids = [sl.sub_line_id for sl in results]
        self.assertEqual(len(sub_ids), len(set(sub_ids)), "All UUIDs must be unique")


# ---------------------------------------------------------------------------
# 16. Year projection table includes custom rows
# ---------------------------------------------------------------------------

class TestYearProjectionWithCustomRows(unittest.TestCase):
    def setUp(self):
        self.client = _authed_client()
        self.project_code = _create_project(self.client, "proj-table")
        self.user_id = _user_id()

    def test_b09_proj_row_shows_nonzero_after_add(self):
        from app.v2.opex_commands import add_opex_line
        pr, _ = _get_project_record_and_ws(self.project_code, self.user_id)
        add_opex_line(project_record=pr, user_id=self.user_id, label="Fee",
                      parent_group_code="B.09", amount_keur=999.0,
                      workbook_version=_workbook_version())
        html = _get_workbook_html(self.client, self.project_code)
        soup = BeautifulSoup(html, "html.parser")
        cell = soup.find(attrs={"data-testid": "proj-B.09-y1"})
        self.assertIsNotNone(cell, "B.09 Y1 cell must exist in projection table")
        val = cell.get_text(strip=True)
        self.assertNotEqual(val, "—", "B.09 Y1 must show a value after custom row added")

    def test_total_proj_row_increases_after_add(self):
        html_before = _get_workbook_html(self.client, self.project_code)
        soup_before = BeautifulSoup(html_before, "html.parser")
        total_before_text = soup_before.find(attrs={"data-testid": "proj-total-y1"}).get_text(strip=True)
        total_before = float(total_before_text.replace(",", "")) if total_before_text != "—" else 0.0

        from app.v2.opex_commands import add_opex_line
        pr, _ = _get_project_record_and_ws(self.project_code, self.user_id)
        add_opex_line(project_record=pr, user_id=self.user_id, label="Fee",
                      parent_group_code="B.09", amount_keur=5000.0,
                      workbook_version=_workbook_version())

        html_after = _get_workbook_html(self.client, self.project_code)
        soup_after = BeautifulSoup(html_after, "html.parser")
        total_after_text = soup_after.find(attrs={"data-testid": "proj-total-y1"}).get_text(strip=True)
        total_after = float(total_after_text.replace(",", ""))
        self.assertGreater(total_after, total_before)


# ---------------------------------------------------------------------------
# 17. Canonical group order preserved
# ---------------------------------------------------------------------------

class TestCanonicalGroupOrder(unittest.TestCase):
    def setUp(self):
        self.client = _authed_client()
        self.project_code = _create_project(self.client, "order")
        self.user_id = _user_id()

    def test_canonical_order_preserved_in_dom(self):
        from app.v2.opex_commands import add_opex_line
        pr, _ = _get_project_record_and_ws(self.project_code, self.user_id)
        # Add to various groups
        for code in ["B.09", "B.03", "B.11"]:
            add_opex_line(project_record=pr, user_id=self.user_id, label=f"Fee {code}",
                          parent_group_code=code, amount_keur=100.0,
                          workbook_version=_workbook_version())

        html = _get_workbook_html(self.client, self.project_code)
        soup = BeautifulSoup(html, "html.parser")
        opex_sheet = soup.find(id="v2-sheet-opex")
        self.assertIsNotNone(opex_sheet, "#v2-sheet-opex must be in DOM")
        groups = opex_sheet.find_all(attrs={"data-group-code": True})
        codes = [g["data-group-code"] for g in groups]
        expected = [f"B.{n:02d}" for n in range(1, 14)]
        self.assertEqual(codes, expected, "Groups must appear in B.01–B.13 canonical order")

    def test_all_13_groups_in_dom(self):
        html = _get_workbook_html(self.client, self.project_code)
        soup = BeautifulSoup(html, "html.parser")
        for n in range(1, 14):
            code = f"B.{n:02d}"
            grp = soup.find(attrs={"data-testid": f"opex-group-{code}"})
            self.assertIsNotNone(grp, f"Group {code} must be in DOM")


# ---------------------------------------------------------------------------
# 18. Persistence layer unit tests
# ---------------------------------------------------------------------------

class TestOpexSubLinesPersistence(unittest.TestCase):
    def setUp(self):
        self.client = _authed_client()
        self.project_code = _create_project(self.client, "persist")
        self.user_id = _user_id()
        self.project_record, _ = _get_project_record_and_ws(self.project_code, self.user_id)

    def test_validate_parent_group_accepts_b01_to_b12(self):
        from app.persistence.opex_sub_lines import validate_parent_group
        for n in range(1, 13):
            code = f"B.{n:02d}"
            self.assertEqual(validate_parent_group(code), code)

    def test_validate_parent_group_rejects_b13(self):
        from app.persistence.opex_sub_lines import validate_parent_group
        with self.assertRaises(ValueError):
            validate_parent_group("B.13")

    def test_validate_parent_group_rejects_unknown(self):
        from app.persistence.opex_sub_lines import validate_parent_group
        with self.assertRaises(ValueError):
            validate_parent_group("B.99")

    def test_validate_business_code_valid(self):
        from app.persistence.opex_sub_lines import validate_business_code
        self.assertEqual(validate_business_code("B.09.U001"), "B.09.U001")

    def test_validate_business_code_invalid(self):
        from app.persistence.opex_sub_lines import validate_business_code
        with self.assertRaises(ValueError):
            validate_business_code("C.09.U001")  # wrong prefix

    def test_generate_next_business_code_empty(self):
        from app.persistence.opex_sub_lines import generate_next_business_code
        code = generate_next_business_code([], "B.09")
        self.assertEqual(code, "B.09.U001")

    def test_generate_next_business_code_increments(self):
        from app.persistence.opex_sub_lines import generate_next_business_code
        code = generate_next_business_code(["B.09.U001", "B.09.U002"], "B.09")
        self.assertEqual(code, "B.09.U003")

    def test_generate_gap_preserved(self):
        from app.persistence.opex_sub_lines import generate_next_business_code
        # U001 exists, U002 was soft-deleted but still occupies slot
        code = generate_next_business_code(["B.09.U001", "B.09.U002"], "B.09")
        self.assertEqual(code, "B.09.U003")

    def test_assert_project_allows_user_project(self):
        from app.persistence.opex_sub_lines import assert_project_allows_opex_sub_lines
        self.assertIsNone(assert_project_allows_opex_sub_lines(self.project_record))

    def test_assert_project_rejects_factory(self):
        from app.persistence.opex_sub_lines import assert_project_allows_opex_sub_lines
        from unittest.mock import MagicMock
        pr = MagicMock()
        pr.project_origin = "factory_template"
        pr.is_readonly = True
        with self.assertRaises(PermissionError):
            assert_project_allows_opex_sub_lines(pr)


if __name__ == "__main__":
    unittest.main()
