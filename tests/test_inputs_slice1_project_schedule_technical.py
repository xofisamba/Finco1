"""Canonical Inputs Slice 1 tests.

Coverage:
- field inventory and registry mapping
- feature flag ON/OFF rendering
- editable save path through ProjectInputSet -> ProjectInputs
- read-only and protected-reference server rejection
- validation error preserves submitted value without dirtying the workspace
- representative explicit Run after an edit
"""
from __future__ import annotations

import os
import re
import unittest
import urllib.parse
from unittest.mock import patch

os.environ.setdefault("FINCO_WORKBOOK_V2", "1")
os.environ.setdefault("FINCO_INPUTS_SLICE1_ENABLED", "1")
os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-key-inputs-slice1")

from fastapi.testclient import TestClient  # noqa: E402

import main_web  # noqa: E402
from app.auth import COOKIE_NAME, create_session_token, decode_session_token  # noqa: E402
from app.ui.inputs_slice1 import (  # noqa: E402
    EDITABLE_BOUND,
    READ_ONLY_REFERENCE_PROJECT,
    READ_ONLY_TEMPLATE_LOCKED,
    SLICE1_EDITABLE_FIELD_IDS,
    SLICE1_FIELD_IDS,
    UNAVAILABLE_UNRESOLVED,
    build_inputs_slice1_sections,
)
from app.workbook.registry import WORKBOOK  # noqa: E402
from app.workbook.service import WorkbookService  # noqa: E402


def _authed_client() -> TestClient:
    tc = TestClient(main_web.app, follow_redirects=False)
    tc.cookies.set(COOKIE_NAME, create_session_token())
    return tc


def _create_project(client: TestClient, suffix: str) -> str:
    resp = client.post(
        "/projects/create",
        data={
            "project_name": f"Inputs Slice1 {suffix}",
            "project_type": "Wind",
            "template_source": "generic_wind",
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
    return parsed["project"][0]


def _get_workbook(client: TestClient, project_code: str) -> str:
    resp = client.get(f"/v2/workbook?project={project_code}")
    assert resp.status_code == 200, resp.text[:200]
    return resp.text


def _inputs_sheet_fragment(html: str) -> str:
    start = html.find('id="v2-sheet-inputs"')
    assert start >= 0, "Inputs Slice 1 sheet not found"
    next_panel = html.find('id="panel-revenue"', start)
    assert next_panel >= 0, "Inputs Slice 1 sheet end not found"
    return html[start:next_panel]


def _extract_hash(html: str) -> str:
    match = re.search(r'data-content-hash="([^"]+)"', html)
    if not match:
        match = re.search(r'name="content_hash"\s+value="([^"]+)"', html)
    assert match, "data-content-hash not found"
    return match.group(1)


def _extract_form_hashes(html: str) -> set[str]:
    return set(re.findall(r'name="content_hash"\s+value="([^"]+)"', html))


def _post_slice1(
    client: TestClient,
    project_code: str,
    field_id: str,
    value: str,
    content_hash: str,
    *,
    htmx: bool = True,
    workbook_version: str = WORKBOOK.version,
):
    headers = {"HX-Request": "true"} if htmx else {}
    return client.post(
        "/v2/workbook/inputs-slice1/update",
        data={
            "field_id": field_id,
            "value": value,
            "project": project_code,
            "workbook_version": workbook_version,
            "content_hash": content_hash,
        },
        headers=headers,
    )


def _workspace(client: TestClient, project_code: str):
    from app.persistence.projects_repository import get_project_record
    from app.persistence.workspace_repository import get_workspace_state
    token = client.cookies.get(COOKIE_NAME)
    user = decode_session_token(token)
    pr = get_project_record(user_id=user.user_id, project_code=project_code)
    ws = get_workspace_state(user_id=user.user_id, project_id=pr.project_id)
    return pr, ws


class TestInputsSlice1Inventory(unittest.TestCase):
    def test_final_visible_field_inventory_exact(self):
        self.assertEqual(SLICE1_FIELD_IDS, (
            "project_setup.identity.project_type",
            "project_setup.identity.country_market",
            "project_setup.technical.cod_date",
            "project_setup.technical.construction_months",
            "project_setup.technical.horizon_years",
            "project_setup.technical.capacity_mw",
            "project_setup.technical.p50_hours",
        ))

    def test_final_editable_field_inventory_exact(self):
        self.assertEqual(SLICE1_EDITABLE_FIELD_IDS, frozenset({
            "project_setup.technical.cod_date",
            "project_setup.technical.construction_months",
            "project_setup.technical.horizon_years",
            "project_setup.technical.capacity_mw",
            "project_setup.technical.p50_hours",
        }))

    def test_included_fields_have_registry_entries(self):
        for field_id in SLICE1_FIELD_IDS:
            self.assertEqual(WORKBOOK.field(field_id).field_id, field_id)

    def test_editable_fields_are_bound_with_projectinputs_path(self):
        for field_id in SLICE1_EDITABLE_FIELD_IDS:
            spec = WORKBOOK.field(field_id)
            self.assertEqual(spec.binding_status.value, "BOUND")
            self.assertTrue(spec.engine_path, f"{field_id} missing engine_path")
            self.assertTrue(spec.editable)
            self.assertTrue(spec.persisted)

    def test_degradation_not_implemented_without_registry_contract(self):
        with self.assertRaises(KeyError):
            WORKBOOK.field("project_setup.technical.degradation")

    def test_project_name_and_capacity_factor_are_not_visible_inventory(self):
        self.assertNotIn("project_setup.identity.project_name", SLICE1_FIELD_IDS)
        self.assertNotIn("project_setup.identity.project_name", SLICE1_EDITABLE_FIELD_IDS)
        self.assertNotIn("project_setup.technical.capacity_factor", SLICE1_FIELD_IDS)
        self.assertNotIn("project_setup.technical.capacity_factor", SLICE1_EDITABLE_FIELD_IDS)

    def test_zero_is_not_allowed_for_slice1_numeric_fields(self):
        for field_id in (
            "project_setup.technical.capacity_mw",
            "project_setup.technical.p50_hours",
            "project_setup.technical.construction_months",
            "project_setup.technical.horizon_years",
        ):
            spec = WORKBOOK.field(field_id)
            self.assertIsNotNone(spec.min_value)
            self.assertGreater(spec.min_value, 0)


class TestInputsSlice1Projection(unittest.TestCase):
    def test_user_project_statuses(self):
        class FakePis:
            def get(self, field_id, default=None):
                values = {
                    "project_setup.identity.project_type": "wind_onshore",
                    "project_setup.technical.capacity_mw": 50,
                }
                return values.get(field_id, default)

        sections = build_inputs_slice1_sections(FakePis(), project_editable=True)
        rows = {
            row["field_id"]: row
            for section in sections
            for row in section["rows"]
        }
        self.assertEqual(rows["project_setup.identity.project_type"]["status"], READ_ONLY_TEMPLATE_LOCKED)
        self.assertEqual(rows["project_setup.identity.country_market"]["status"], UNAVAILABLE_UNRESOLVED)
        self.assertEqual(rows["project_setup.technical.capacity_mw"]["status"], EDITABLE_BOUND)

    def test_protected_reference_statuses(self):
        class FakePis:
            def get(self, field_id, default=None):
                return None

        sections = build_inputs_slice1_sections(FakePis(), project_editable=False)
        statuses = {
            row["status"]
            for section in sections
            for row in section["rows"]
        }
        self.assertEqual(statuses, {READ_ONLY_REFERENCE_PROJECT})


class TestInputsSlice1Routes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "routes")

    def test_flag_on_renders_slice1_grid(self):
        with patch.dict(os.environ, {"FINCO_INPUTS_SLICE1_ENABLED": "1"}):
            html = _get_workbook(self.client, self.project_code)
        inputs_html = _inputs_sheet_fragment(html)
        self.assertIn("Canonical Slice 1", html)
        self.assertIn('data-inputs-slice="1"', html)
        self.assertIn("Project, Schedule, Technical and supported Production inputs", html)
        self.assertNotIn("Project Name", inputs_html)
        self.assertNotIn("Capacity Factor", inputs_html)

    def test_flag_off_preserves_existing_inputs_sheet(self):
        with patch.dict(os.environ, {"FINCO_INPUTS_SLICE1_ENABLED": "0"}):
            html = _get_workbook(self.client, self.project_code)
        self.assertNotIn("Canonical Slice 1", html)
        # Legacy accordion must NOT appear; disabled config-state notice shown instead.
        self.assertNotIn("Revenue Summary", html)
        self.assertIn("v2-slice1-config-state", html)

    def test_flag_off_rejects_slice1_post(self):
        html = _get_workbook(self.client, self.project_code)
        with patch.dict(os.environ, {"FINCO_INPUTS_SLICE1_ENABLED": "0"}):
            resp = _post_slice1(
                self.client,
                self.project_code,
                "project_setup.technical.capacity_mw",
                "88",
                _extract_hash(html),
            )
        self.assertEqual(resp.status_code, 409)

    def test_editable_capacity_saves_and_resolves_to_projectinputs(self):
        html = _get_workbook(self.client, self.project_code)
        resp = _post_slice1(
            self.client,
            self.project_code,
            "project_setup.technical.capacity_mw",
            "88.25",
            _extract_hash(html),
        )
        self.assertEqual(resp.status_code, 200, resp.text[:200])
        pr, ws = _workspace(self.client, self.project_code)
        self.assertTrue(ws.dirty)
        pis = WorkbookService.build_draft_input_set_from_workspace(ws)
        self.assertEqual(pis.get("project_setup.technical.capacity_mw"), 88.25)
        pi = pis.to_projectinputs()
        self.assertEqual(pi.technical.capacity_mw, 88.25)

    def test_sequential_cross_section_edits_refresh_all_form_hashes(self):
        project_code = _create_project(self.client, "sequence")
        html = _get_workbook(self.client, project_code)
        old_hash = _extract_hash(html)
        first = _post_slice1(
            self.client,
            project_code,
            "project_setup.technical.capacity_mw",
            "75",
            old_hash,
        )
        self.assertEqual(first.status_code, 200, first.text[:300])
        self.assertIn('id="v2-sheet-inputs"', first.text)
        hashes_after_first = _extract_form_hashes(first.text)
        self.assertEqual(len(hashes_after_first), 1)
        new_hash = next(iter(hashes_after_first))
        self.assertNotEqual(new_hash, old_hash)
        self.assertNotIn(old_hash, hashes_after_first)
        self.assertIn("Run required", first.text)

        second = _post_slice1(
            self.client,
            project_code,
            "project_setup.technical.construction_months",
            "24",
            new_hash,
        )
        self.assertEqual(second.status_code, 200, second.text[:300])
        self.assertNotIn("Draft changed since page loaded", second.text)
        hashes_after_second = _extract_form_hashes(second.text)
        self.assertEqual(len(hashes_after_second), 1)
        self.assertNotEqual(next(iter(hashes_after_second)), new_hash)
        _, ws = _workspace(self.client, project_code)
        pis = WorkbookService.build_draft_input_set_from_workspace(ws)
        self.assertEqual(pis.get("project_setup.technical.capacity_mw"), 75.0)
        self.assertEqual(pis.get("project_setup.technical.construction_months"), 24)

    def test_read_only_slice1_field_rejects_direct_post(self):
        html = _get_workbook(self.client, self.project_code)
        resp = _post_slice1(
            self.client,
            self.project_code,
            "project_setup.identity.project_type",
            "solar_pv",
            _extract_hash(html),
        )
        self.assertEqual(resp.status_code, 422)
        self.assertIn("read-only in Inputs Slice 1", resp.text)

    def test_out_of_slice_registry_field_rejects_without_mutation(self):
        project_code = _create_project(self.client, "outside")
        html = _get_workbook(self.client, project_code)
        _, ws_before = _workspace(self.client, project_code)
        resp = _post_slice1(
            self.client,
            project_code,
            "debt.senior.gearing_pct",
            "85",
            _extract_hash(html),
        )
        self.assertEqual(resp.status_code, 422)
        self.assertIn("outside the Inputs Slice 1", resp.text)
        _, ws_after = _workspace(self.client, project_code)
        self.assertEqual(ws_before.draft_snapshot, ws_after.draft_snapshot)
        self.assertEqual(ws_before.dirty, ws_after.dirty)

    def test_unknown_field_rejects_without_mutation(self):
        project_code = _create_project(self.client, "unknown")
        html = _get_workbook(self.client, project_code)
        _, ws_before = _workspace(self.client, project_code)
        resp = _post_slice1(
            self.client,
            project_code,
            "not.a.real.field",
            "1",
            _extract_hash(html),
        )
        self.assertEqual(resp.status_code, 422)
        self.assertNotIn("Traceback", resp.text)
        self.assertIn("Unknown workbook field", resp.text)
        _, ws_after = _workspace(self.client, project_code)
        self.assertEqual(ws_before.draft_snapshot, ws_after.draft_snapshot)
        self.assertEqual(ws_before.dirty, ws_after.dirty)

    def test_project_name_post_rejected_without_metadata_or_draft_divergence(self):
        project_code = _create_project(self.client, "name")
        html = _get_workbook(self.client, project_code)
        pr_before, ws_before = _workspace(self.client, project_code)
        pis_before = WorkbookService.build_draft_input_set_from_workspace(ws_before)
        resp = _post_slice1(
            self.client,
            project_code,
            "project_setup.identity.project_name",
            "Renamed By Slice",
            _extract_hash(html),
        )
        self.assertEqual(resp.status_code, 422)
        self.assertIn("metadata rename contract", resp.text)
        pr_after, ws_after = _workspace(self.client, project_code)
        pis_after = WorkbookService.build_draft_input_set_from_workspace(ws_after)
        self.assertEqual(pr_after.project_name, pr_before.project_name)
        self.assertEqual(
            pis_after.get("project_setup.identity.project_name"),
            pis_before.get("project_setup.identity.project_name"),
        )

    def test_capacity_factor_post_rejected_and_never_rendered(self):
        html = _get_workbook(self.client, self.project_code)
        self.assertNotIn("Capacity Factor", _inputs_sheet_fragment(html))
        resp = _post_slice1(
            self.client,
            self.project_code,
            "project_setup.technical.capacity_factor",
            "99",
            _extract_hash(html),
        )
        self.assertEqual(resp.status_code, 422)
        self.assertIn("runtime-derived projection", resp.text)
        self.assertNotIn('data-field-id="project_setup.technical.capacity_factor"', resp.text)

    def test_invalid_value_preserves_submitted_value_and_does_not_persist(self):
        project_code = _create_project(self.client, "invalid")
        html = _get_workbook(self.client, project_code)
        _, ws_before = _workspace(self.client, project_code)
        self.assertFalse(ws_before.dirty)
        resp = _post_slice1(
            self.client,
            project_code,
            "project_setup.technical.capacity_mw",
            "-5",
            _extract_hash(html),
        )
        self.assertEqual(resp.status_code, 422)
        self.assertIn('value="-5"', resp.text)
        self.assertIn("must be", resp.text)
        _, ws_after = _workspace(self.client, project_code)
        self.assertFalse(ws_after.dirty)
        pis = WorkbookService.build_draft_input_set_from_workspace(ws_after)
        self.assertEqual(pis.get("project_setup.technical.capacity_mw"), 50.0)

    def test_protected_reference_direct_post_rejects_mutation(self):
        project_code = _create_project(self.client, "protected")
        html = _get_workbook(self.client, project_code)
        with patch("app.ui.protected_reference_service.is_protected_reference", return_value=True), \
             patch("app.v2.router.is_protected_reference", return_value=True):
            resp = _post_slice1(
                self.client,
                project_code,
                "project_setup.technical.capacity_mw",
                "90",
                _extract_hash(html),
            )
        self.assertEqual(resp.status_code, 409)
        self.assertIn("protected", resp.text.lower())
        _, ws = _workspace(self.client, project_code)
        pis = WorkbookService.build_draft_input_set_from_workspace(ws)
        self.assertNotEqual(pis.get("project_setup.technical.capacity_mw"), 90)

    def test_stale_hash_rejects_with_409(self):
        resp = _post_slice1(
            self.client,
            self.project_code,
            "project_setup.technical.capacity_mw",
            "82",
            "0" * 64,
        )
        self.assertEqual(resp.status_code, 409)
        self.assertIn("Draft changed since page loaded", resp.text)

    def test_stale_hash_response_refreshes_hashes_and_retry_succeeds(self):
        project_code = _create_project(self.client, "stale-retry")
        html = _get_workbook(self.client, project_code)
        old_hash = _extract_hash(html)
        first = _post_slice1(
            self.client,
            project_code,
            "project_setup.technical.capacity_mw",
            "77",
            old_hash,
        )
        self.assertEqual(first.status_code, 200, first.text[:300])
        refreshed_hashes = _extract_form_hashes(first.text)
        self.assertEqual(len(refreshed_hashes), 1)
        refreshed_hash = next(iter(refreshed_hashes))
        self.assertNotEqual(refreshed_hash, old_hash)

        stale = _post_slice1(
            self.client,
            project_code,
            "project_setup.technical.construction_months",
            "24",
            old_hash,
        )
        self.assertEqual(stale.status_code, 409, stale.text[:300])
        self.assertIn("Draft changed since page loaded", stale.text)
        self.assertIn('id="v2-sheet-inputs"', stale.text)
        stale_hashes = _extract_form_hashes(stale.text)
        self.assertEqual(stale_hashes, {refreshed_hash})
        _, ws_after_stale = _workspace(self.client, project_code)
        pis_after_stale = WorkbookService.build_draft_input_set_from_workspace(ws_after_stale)
        self.assertEqual(pis_after_stale.get("project_setup.technical.capacity_mw"), 77.0)
        self.assertEqual(pis_after_stale.get("project_setup.technical.construction_months"), 18)

        retry = _post_slice1(
            self.client,
            project_code,
            "project_setup.technical.construction_months",
            "24",
            refreshed_hash,
        )
        self.assertEqual(retry.status_code, 200, retry.text[:300])
        _, ws_after_retry = _workspace(self.client, project_code)
        pis_after_retry = WorkbookService.build_draft_input_set_from_workspace(ws_after_retry)
        self.assertEqual(pis_after_retry.get("project_setup.technical.capacity_mw"), 77.0)
        self.assertEqual(pis_after_retry.get("project_setup.technical.construction_months"), 24)

    def test_version_mismatch_htmx_triggers_refresh(self):
        project_code = _create_project(self.client, "version")
        html = _get_workbook(self.client, project_code)
        _, ws_before = _workspace(self.client, project_code)
        resp = _post_slice1(
            self.client,
            project_code,
            "project_setup.technical.capacity_mw",
            "82",
            _extract_hash(html),
            workbook_version="0.0.0",
        )
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.headers.get("HX-Refresh"), "true")
        self.assertIn("workbook version", resp.text.lower())
        self.assertIn("reload", resp.text.lower())
        _, ws_after = _workspace(self.client, project_code)
        self.assertEqual(ws_before.draft_snapshot, ws_after.draft_snapshot)
        self.assertEqual(ws_before.dirty, ws_after.dirty)

    def test_validation_matrix_for_editable_fields(self):
        cases = {
            "project_setup.technical.cod_date": ("2029-01-01", "not-a-date", ""),
            "project_setup.technical.construction_months": ("24", "abc", "0"),
            "project_setup.technical.horizon_years": ("30", "abc", "0"),
            "project_setup.technical.capacity_mw": ("65.5", "abc", "0"),
            "project_setup.technical.p50_hours": ("2400", "abc", "0"),
        }
        for field_id, (valid_value, invalid_type, below_or_blank) in cases.items():
            with self.subTest(field_id=field_id):
                project_code = _create_project(self.client, field_id.split(".")[-1])
                html = _get_workbook(self.client, project_code)
                valid = _post_slice1(self.client, project_code, field_id, valid_value, _extract_hash(html))
                self.assertEqual(valid.status_code, 200, valid.text[:200])
                current_hash = _extract_hash(valid.text)
                invalid = _post_slice1(self.client, project_code, field_id, invalid_type, current_hash)
                self.assertEqual(invalid.status_code, 422, invalid.text[:200])
                self.assertIn(f'value="{invalid_type}"', invalid.text)
                current_hash = _extract_hash(invalid.text)
                blank = _post_slice1(self.client, project_code, field_id, "", current_hash)
                self.assertEqual(blank.status_code, 422, blank.text[:200])
                self.assertIn("required", blank.text.lower())
                if below_or_blank:
                    current_hash = _extract_hash(blank.text)
                    below = _post_slice1(self.client, project_code, field_id, below_or_blank, current_hash)
                    self.assertEqual(below.status_code, 422, below.text[:200])


class TestInputsSlice1Runtime(unittest.TestCase):
    def test_edit_marks_existing_runtime_stale_then_explicit_run_clears_dirty(self):
        client = _authed_client()
        project_code = _create_project(client, "runtime")
        html = _get_workbook(client, project_code)
        first_run = client.post(
            "/v2/workbook/run",
            data={
                "project": project_code,
                "workbook_version": WORKBOOK.version,
                "content_hash": _extract_hash(html),
            },
            headers={"HX-Request": "true"},
        )
        self.assertEqual(first_run.status_code, 200, first_run.text[:300])
        _, ws_after_run = _workspace(client, project_code)
        self.assertFalse(ws_after_run.dirty)
        self.assertTrue(ws_after_run.last_runtime_snapshot_id)

        html_after_run = _get_workbook(client, project_code)
        edit = _post_slice1(
            client,
            project_code,
            "project_setup.technical.p50_hours",
            "2300",
            _extract_hash(html_after_run),
        )
        self.assertEqual(edit.status_code, 200, edit.text[:300])
        _, ws_after_edit = _workspace(client, project_code)
        self.assertTrue(ws_after_edit.dirty)
        self.assertEqual(
            ws_after_edit.last_runtime_snapshot_id,
            ws_after_run.last_runtime_snapshot_id,
        )
        self.assertIn("Run required", edit.text)

        html_stale = _get_workbook(client, project_code)
        second_run = client.post(
            "/v2/workbook/run",
            data={
                "project": project_code,
                "workbook_version": WORKBOOK.version,
                "content_hash": _extract_hash(html_stale),
            },
            headers={"HX-Request": "true"},
        )
        self.assertEqual(second_run.status_code, 200, second_run.text[:300])
        _, ws_final = _workspace(client, project_code)
        self.assertFalse(ws_final.dirty)
        self.assertTrue(ws_final.last_runtime_snapshot_id)


class TestInputsSlice1SourceGuards(unittest.TestCase):
    def test_no_javascript_financial_calculation_added(self):
        js = open("static/js/workbook_v2.js", encoding="utf-8").read()
        self.assertNotRegex(js, re.compile(r"8760|capacity_factor\s*=|p50\s*/|capacity\s*/|revenue\s*=", re.I))

    def test_slice1_htmx_transport_handler_does_not_mutate_values_or_hashes(self):
        js = open("static/js/workbook_v2.js", encoding="utf-8").read()
        start = js.index("Scoped HTMX handling for controlled Slice 1 application errors.")
        end = js.index("Field editor: pending", start)
        handler = js[start:end]
        self.assertNotRegex(handler, re.compile(r"content_hash|\.value\s*=|setAttribute\(", re.I))

    def test_slice1_htmx_before_swap_handler_is_endpoint_scoped(self):
        js = open("static/js/workbook_v2.js", encoding="utf-8").read()
        self.assertIn("htmx:beforeSwap", js)
        self.assertIn("/v2/workbook/inputs-slice1/update", js)
        self.assertIn("shouldSwap = true", js)
        self.assertIn("isError = false", js)
        self.assertRegex(js, re.compile(r"CONTROLLED_SWAP_STATUSES\s*=\s*\{\s*409:\s*true,\s*422:\s*true\s*\}"))
        self.assertNotIn('responseHandling: [{code: ".*", swap: true}]', js)
        self.assertNotRegex(js, re.compile(r"status\s*>?=\s*400|status\s*<\s*500"))

    def test_no_capacity_factor_calculation_added_to_slice1_python_or_templates(self):
        paths = [
            "app/ui/inputs_slice1.py",
            "app/v2/router.py",
            "app/templates/v2/partials/inputs_slice1.html",
            "app/templates/v2/partials/inputs_slice1_section.html",
        ]
        for path in paths:
            text = open(path, encoding="utf-8").read()
            self.assertNotRegex(text, re.compile(r"8760|capacity\\s*/|p50\\s*/", re.I))


def test_slice1_htmx_before_swap_synthetic_event_browser():
    pytest = __import__("pytest")
    playwright = pytest.importorskip(
        "playwright.sync_api",
        reason=(
            "OPTIONAL_BROWSER_DEPENDENCY_MISSING: install playwright and chromium "
            "to run Slice 1 HTMX synthetic browser test"
        ),
    )
    js = open("static/js/workbook_v2.js", encoding="utf-8").read()
    with playwright.sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.set_content("<html><body></body></html>")
        page.evaluate(
            """
            window.__v2SyntheticEvents = {};
            window.document.addEventListener = function (name, handler) {
              window.__v2SyntheticEvents[name] = handler;
            };
            """
        )
        page.add_script_tag(content=js)
        result = page.evaluate(
            """
            function run(url, status) {
              var event = {
                detail: {
                  xhr: { status: status, responseURL: url },
                  shouldSwap: false,
                  isError: true
                }
              };
              window.__v2SyntheticEvents['htmx:beforeSwap'](event);
              return { shouldSwap: event.detail.shouldSwap, isError: event.detail.isError };
            }
            ({
              slice422: run('/v2/workbook/inputs-slice1/update', 422),
              slice409: run('/v2/workbook/inputs-slice1/update', 409),
              slice500: run('/v2/workbook/inputs-slice1/update', 500),
              other422: run('/v2/workbook/update', 422)
            })
            """
        )
        browser.close()
    assert result["slice422"] == {"shouldSwap": True, "isError": False}
    assert result["slice409"] == {"shouldSwap": True, "isError": False}
    assert result["slice500"] == {"shouldSwap": False, "isError": True}
    assert result["other422"] == {"shouldSwap": False, "isError": True}


if __name__ == "__main__":
    unittest.main()
