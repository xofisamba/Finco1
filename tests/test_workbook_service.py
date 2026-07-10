"""
Tests for WorkbookService — the pure domain service layer (Workbook V2, PR 4).

Key contracts under test:
- template_source is never derived from project_code or any identity field.
- Draft vs saved snapshot boundaries are explicit (separate methods).
- Neither workspace method mutates WorkspaceStateRecord data.
- strict mode is forwarded to ProjectInputSet.from_snapshot().
- All methods are static; WorkbookService has no instance state.
"""
from __future__ import annotations

import inspect
import unittest
from unittest.mock import MagicMock
from typing import Any

from app.workbook.service import WorkbookService
from app.workbook.input_set import ProjectInputSet, ProjectInputSetError
from app.workbook.runtime_result import RuntimeResult


# ---------------------------------------------------------------------------
# Snapshot fixtures
# ---------------------------------------------------------------------------

def _make_snapshot(**overrides: Any) -> dict[str, Any]:
    base = {
        "project_name": "Test Project",
        "capex_meur": "100",
        "cod_year": "2028",
    }
    base.update(overrides)
    return base


def _full_snapshot(**overrides: Any) -> dict[str, Any]:
    """Complete snapshot with all required fields (mirrors _tuho_snapshot())."""
    from app.project_factories import create_default_tuho_wind1
    pi = create_default_tuho_wind1()
    base = {
        "active_project": "tuho",
        "project_name": pi.info.name,
        "project_type": "Wind",
        "template_source": "tuho",
        "country_market": pi.info.country_iso,
        "capacity_mw": str(pi.technical.capacity_mw),
        "tariff_eur_mwh": str(pi.revenue.ppa_base_tariff),
        "p50_hours": str(pi.technical.operating_hours_p50),
        "total_capex_keur": str(pi.capex.total_capex),
        "opex_y1_keur": str(sum(i.y1_amount_keur for i in pi.opex)),
        "target_dscr": str(pi.financing.target_dscr),
        "interest_rate_pct": str(pi.financing.base_rate + pi.financing.margin_bps / 10_000),
        "tenor_years": str(pi.financing.senior_tenor_years),
        "cod_date": str(pi.info.cod_date),
        "construction_months": str(pi.info.construction_months),
        "horizon_years": str(pi.info.horizon_years),
        "ppa_term_years": str(int(pi.revenue.ppa_term_years)),
        "gearing_pct": "",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# WorkspaceStateRecord mock
# ---------------------------------------------------------------------------

def _make_ws(
    *,
    draft_snapshot: dict | None = None,
    saved_snapshot: dict | None = None,
    project_code: str = "some-project-id",
    last_runtime_snapshot_id: str = "20260710T120000Z",
    last_runtime_summary: dict | None = None,
    last_runtime_at: Any = None,
    last_runtime_origin: str = "saved_state",
    last_financial_statements: dict | None = None,
    last_debt_schedule: dict | None = None,
    last_tax_schedule: dict | None = None,
    last_distribution_schedule: dict | None = None,
    last_sponsor_schedule: dict | None = None,
    _no_summary: bool = False,
) -> MagicMock:
    ws = MagicMock()
    ws.draft_snapshot = draft_snapshot if draft_snapshot is not None else _make_snapshot()
    ws.saved_snapshot = saved_snapshot if saved_snapshot is not None else _make_snapshot(capex_meur="80")
    ws.project_code = project_code
    ws.last_runtime_snapshot_id = last_runtime_snapshot_id
    ws.last_runtime_summary = {} if _no_summary else (last_runtime_summary or {"project_irr": 0.08})
    ws.last_runtime_at = last_runtime_at
    ws.last_runtime_origin = last_runtime_origin
    ws.last_financial_statements = last_financial_statements if last_financial_statements is not None else {}
    ws.last_debt_schedule = last_debt_schedule if last_debt_schedule is not None else {}
    ws.last_tax_schedule = last_tax_schedule if last_tax_schedule is not None else {}
    ws.last_distribution_schedule = last_distribution_schedule if last_distribution_schedule is not None else {}
    ws.last_sponsor_schedule = last_sponsor_schedule if last_sponsor_schedule is not None else {}
    return ws


# ---------------------------------------------------------------------------
# build_input_set
# ---------------------------------------------------------------------------

class TestBuildInputSet(unittest.TestCase):

    def test_returns_project_input_set(self):
        pis = WorkbookService.build_input_set(_make_snapshot())
        self.assertIsInstance(pis, ProjectInputSet)

    def test_snapshot_values_preserved(self):
        snap = _make_snapshot(capex_meur="250")
        pis = WorkbookService.build_input_set(snap)
        self.assertEqual(pis.snapshot_origin.get("capex_meur"), "250")

    def test_content_hash_is_stable(self):
        snap = _make_snapshot()
        pis1 = WorkbookService.build_input_set(snap)
        pis2 = WorkbookService.build_input_set(snap)
        self.assertEqual(pis1.content_hash, pis2.content_hash)

    def test_different_snapshots_yield_different_hashes(self):
        pis_a = WorkbookService.build_input_set(_make_snapshot(capex_meur="100"))
        pis_b = WorkbookService.build_input_set(_make_snapshot(capex_meur="200"))
        self.assertNotEqual(pis_a.content_hash, pis_b.content_hash)

    def test_template_source_in_snapshot_preserved(self):
        snap = _make_snapshot(template_source="tuho")
        pis = WorkbookService.build_input_set(snap)
        self.assertEqual(pis.template_source, "tuho")

    def test_template_source_generic_wind_preserved(self):
        snap = _make_snapshot(template_source="generic_wind")
        pis = WorkbookService.build_input_set(snap)
        self.assertEqual(pis.template_source, "generic_wind")

    def test_template_source_generic_solar_preserved(self):
        snap = _make_snapshot(template_source="generic_solar")
        pis = WorkbookService.build_input_set(snap)
        self.assertEqual(pis.template_source, "generic_solar")

    def test_template_source_oborovo_preserved(self):
        snap = _make_snapshot(template_source="oborovo")
        pis = WorkbookService.build_input_set(snap)
        self.assertEqual(pis.template_source, "oborovo")

    def test_absent_template_source_is_empty_string_not_invented(self):
        snap = _make_snapshot()  # no template_source key
        pis = WorkbookService.build_input_set(snap)
        # template_source absent from snapshot → ProjectInputSet normalises to ""
        self.assertEqual(pis.template_source, "")

    def test_project_origin_in_snapshot_preserved(self):
        snap = _make_snapshot(project_origin="factory_template")
        pis = WorkbookService.build_input_set(snap)
        self.assertEqual(pis.project_origin, "factory_template")

    def test_strict_false_tolerates_unknown_keys(self):
        snap = _make_snapshot(unknown_key_xyz="irrelevant")
        pis = WorkbookService.build_input_set(snap, strict=False)
        self.assertIsInstance(pis, ProjectInputSet)

    def test_strict_true_raises_on_unknown_keys(self):
        snap = _make_snapshot(unknown_key_xyz="irrelevant")
        with self.assertRaises(ProjectInputSetError):
            WorkbookService.build_input_set(snap, strict=True)

    def test_delegates_to_from_snapshot(self):
        snap = _make_snapshot()
        via_service = WorkbookService.build_input_set(snap)
        direct = ProjectInputSet.from_snapshot(snapshot=snap)
        self.assertEqual(via_service.content_hash, direct.content_hash)


# ---------------------------------------------------------------------------
# build_draft_input_set_from_workspace
# ---------------------------------------------------------------------------

class TestBuildDraftInputSetFromWorkspace(unittest.TestCase):

    def test_returns_project_input_set(self):
        ws = _make_ws()
        pis = WorkbookService.build_draft_input_set_from_workspace(ws)
        self.assertIsInstance(pis, ProjectInputSet)

    def test_uses_draft_snapshot_not_saved(self):
        draft = _make_snapshot(capex_meur="999")
        saved = _make_snapshot(capex_meur="1")
        ws = _make_ws(draft_snapshot=draft, saved_snapshot=saved)
        pis = WorkbookService.build_draft_input_set_from_workspace(ws)
        self.assertEqual(pis.snapshot_origin.get("capex_meur"), "999")

    def test_does_not_use_saved_snapshot_value(self):
        draft = _make_snapshot(capex_meur="222")
        saved = _make_snapshot(capex_meur="333")
        ws = _make_ws(draft_snapshot=draft, saved_snapshot=saved)
        pis = WorkbookService.build_draft_input_set_from_workspace(ws)
        self.assertNotEqual(pis.snapshot_origin.get("capex_meur"), "333")

    def test_does_not_copy_project_code_into_template_source(self):
        ws = _make_ws(project_code="arbitrary-project-id-123")
        pis = WorkbookService.build_draft_input_set_from_workspace(ws)
        self.assertNotEqual(pis.template_source, "arbitrary-project-id-123")

    def test_project_code_never_becomes_template_source(self):
        for code in ("tuho", "oborovo", "generic_wind", "my-private-project-42"):
            ws = _make_ws(
                project_code=code,
                draft_snapshot=_make_snapshot(),  # no template_source key
            )
            pis = WorkbookService.build_draft_input_set_from_workspace(ws)
            self.assertNotEqual(
                pis.template_source, code,
                f"project_code={code!r} must not be copied into template_source",
            )

    def test_explicit_template_source_in_draft_snapshot_preserved(self):
        draft = _make_snapshot(template_source="tuho")
        ws = _make_ws(draft_snapshot=draft, project_code="some-other-id")
        pis = WorkbookService.build_draft_input_set_from_workspace(ws)
        self.assertEqual(pis.template_source, "tuho")

    def test_missing_template_source_not_silently_invented(self):
        ws = _make_ws(draft_snapshot=_make_snapshot())  # no template_source
        pis = WorkbookService.build_draft_input_set_from_workspace(ws)
        self.assertEqual(pis.template_source, "")

    def test_draft_snapshot_not_mutated(self):
        snap = _make_snapshot()
        original = dict(snap)
        ws = _make_ws(draft_snapshot=snap, project_code="tuho")
        WorkbookService.build_draft_input_set_from_workspace(ws)
        self.assertEqual(snap, original)

    def test_content_hash_stable_for_same_draft(self):
        ws = _make_ws()
        pis1 = WorkbookService.build_draft_input_set_from_workspace(ws)
        pis2 = WorkbookService.build_draft_input_set_from_workspace(ws)
        self.assertEqual(pis1.content_hash, pis2.content_hash)

    def test_strict_true_forwarded(self):
        ws = _make_ws(draft_snapshot=_make_snapshot(bogus_field="x"))
        with self.assertRaises(ProjectInputSetError):
            WorkbookService.build_draft_input_set_from_workspace(ws, strict=True)


# ---------------------------------------------------------------------------
# build_saved_input_set_from_workspace
# ---------------------------------------------------------------------------

class TestBuildSavedInputSetFromWorkspace(unittest.TestCase):

    def test_returns_project_input_set(self):
        ws = _make_ws()
        pis = WorkbookService.build_saved_input_set_from_workspace(ws)
        self.assertIsInstance(pis, ProjectInputSet)

    def test_uses_saved_snapshot_not_draft(self):
        draft = _make_snapshot(capex_meur="999")
        saved = _make_snapshot(capex_meur="1")
        ws = _make_ws(draft_snapshot=draft, saved_snapshot=saved)
        pis = WorkbookService.build_saved_input_set_from_workspace(ws)
        self.assertEqual(pis.snapshot_origin.get("capex_meur"), "1")

    def test_does_not_use_draft_snapshot_value(self):
        draft = _make_snapshot(capex_meur="222")
        saved = _make_snapshot(capex_meur="333")
        ws = _make_ws(draft_snapshot=draft, saved_snapshot=saved)
        pis = WorkbookService.build_saved_input_set_from_workspace(ws)
        self.assertNotEqual(pis.snapshot_origin.get("capex_meur"), "222")

    def test_does_not_copy_project_code_into_template_source(self):
        ws = _make_ws(project_code="arbitrary-project-id-456")
        pis = WorkbookService.build_saved_input_set_from_workspace(ws)
        self.assertNotEqual(pis.template_source, "arbitrary-project-id-456")

    def test_project_code_never_becomes_template_source(self):
        for code in ("tuho", "oborovo", "generic_wind", "my-private-project-42"):
            ws = _make_ws(
                project_code=code,
                saved_snapshot=_make_snapshot(),  # no template_source key
            )
            pis = WorkbookService.build_saved_input_set_from_workspace(ws)
            self.assertNotEqual(
                pis.template_source, code,
                f"project_code={code!r} must not be copied into template_source",
            )

    def test_explicit_template_source_in_saved_snapshot_preserved(self):
        saved = _make_snapshot(template_source="oborovo")
        ws = _make_ws(saved_snapshot=saved, project_code="some-other-id")
        pis = WorkbookService.build_saved_input_set_from_workspace(ws)
        self.assertEqual(pis.template_source, "oborovo")

    def test_missing_template_source_not_silently_invented(self):
        ws = _make_ws(saved_snapshot=_make_snapshot())  # no template_source
        pis = WorkbookService.build_saved_input_set_from_workspace(ws)
        self.assertEqual(pis.template_source, "")

    def test_saved_snapshot_not_mutated(self):
        snap = _make_snapshot()
        original = dict(snap)
        ws = _make_ws(saved_snapshot=snap, project_code="tuho")
        WorkbookService.build_saved_input_set_from_workspace(ws)
        self.assertEqual(snap, original)

    def test_content_hash_stable_for_same_saved_snapshot(self):
        ws = _make_ws()
        pis1 = WorkbookService.build_saved_input_set_from_workspace(ws)
        pis2 = WorkbookService.build_saved_input_set_from_workspace(ws)
        self.assertEqual(pis1.content_hash, pis2.content_hash)

    def test_strict_true_forwarded(self):
        ws = _make_ws(saved_snapshot=_make_snapshot(bogus_field="x"))
        with self.assertRaises(ProjectInputSetError):
            WorkbookService.build_saved_input_set_from_workspace(ws, strict=True)


# ---------------------------------------------------------------------------
# draft vs saved boundary separation
# ---------------------------------------------------------------------------

class TestDraftVsSavedBoundary(unittest.TestCase):

    def test_draft_and_saved_hashes_differ_when_snapshots_differ(self):
        draft = _make_snapshot(capex_meur="100")
        saved = _make_snapshot(capex_meur="200")
        ws = _make_ws(draft_snapshot=draft, saved_snapshot=saved)
        pis_draft = WorkbookService.build_draft_input_set_from_workspace(ws)
        pis_saved = WorkbookService.build_saved_input_set_from_workspace(ws)
        self.assertNotEqual(pis_draft.content_hash, pis_saved.content_hash)

    def test_draft_and_saved_hashes_equal_when_snapshots_equal(self):
        snap = _make_snapshot(capex_meur="150")
        ws = _make_ws(draft_snapshot=dict(snap), saved_snapshot=dict(snap))
        pis_draft = WorkbookService.build_draft_input_set_from_workspace(ws)
        pis_saved = WorkbookService.build_saved_input_set_from_workspace(ws)
        self.assertEqual(pis_draft.content_hash, pis_saved.content_hash)

    def test_saved_run_cannot_consume_draft_only_value(self):
        """A field present only in draft must not appear in the saved PIS."""
        draft = _make_snapshot(capex_meur="999", draft_only_field="DRAFT")
        saved = _make_snapshot(capex_meur="100")
        ws = _make_ws(draft_snapshot=draft, saved_snapshot=saved)
        pis_saved = WorkbookService.build_saved_input_set_from_workspace(ws)
        self.assertIsNone(pis_saved.snapshot_origin.get("draft_only_field"))

    def test_draft_does_not_see_saved_only_value(self):
        draft = _make_snapshot(capex_meur="100")
        saved = _make_snapshot(capex_meur="999", saved_only_field="SAVED")
        ws = _make_ws(draft_snapshot=draft, saved_snapshot=saved)
        pis_draft = WorkbookService.build_draft_input_set_from_workspace(ws)
        self.assertIsNone(pis_draft.snapshot_origin.get("saved_only_field"))


# ---------------------------------------------------------------------------
# to_projectinputs
# ---------------------------------------------------------------------------

class TestToProjectInputs(unittest.TestCase):

    def _make_pis(self) -> ProjectInputSet:
        return WorkbookService.build_input_set(_full_snapshot())

    def test_result_is_same_as_pis_direct_call(self):
        pis = self._make_pis()
        via_service = WorkbookService.to_projectinputs(pis)
        direct = pis.to_projectinputs()
        self.assertEqual(via_service, direct)

    def test_delegates_without_transformation(self):
        pis = self._make_pis()
        pi = WorkbookService.to_projectinputs(pis)
        self.assertIsNotNone(pi)


# ---------------------------------------------------------------------------
# get_runtime_result
# ---------------------------------------------------------------------------

class TestGetRuntimeResult(unittest.TestCase):

    def test_returns_runtime_result_when_present(self):
        ws = _make_ws()
        rr = WorkbookService.get_runtime_result(ws)
        self.assertIsInstance(rr, RuntimeResult)

    def test_returns_none_when_no_snapshot_id(self):
        ws = _make_ws(last_runtime_snapshot_id="")
        rr = WorkbookService.get_runtime_result(ws)
        self.assertIsNone(rr)

    def test_returns_none_when_no_runtime_summary(self):
        ws = _make_ws(_no_summary=True)
        rr = WorkbookService.get_runtime_result(ws)
        self.assertIsNone(rr)

    def test_snapshot_id_propagated(self):
        ws = _make_ws(last_runtime_snapshot_id="20260710T090000Z")
        rr = WorkbookService.get_runtime_result(ws)
        self.assertEqual(rr.snapshot_id, "20260710T090000Z")

    def test_origin_propagated(self):
        ws = _make_ws(last_runtime_origin="workspace_base")
        rr = WorkbookService.get_runtime_result(ws)
        self.assertEqual(rr.origin, "workspace_base")

    def test_runtime_summary_propagated(self):
        ws = _make_ws(last_runtime_summary={"project_irr": 0.12})
        rr = WorkbookService.get_runtime_result(ws)
        self.assertAlmostEqual(rr.runtime_summary["project_irr"], 0.12)

    def test_result_is_immutable(self):
        ws = _make_ws(last_runtime_summary={"project_irr": 0.08})
        rr = WorkbookService.get_runtime_result(ws)
        with self.assertRaises(TypeError):
            rr.runtime_summary["project_irr"] = 0.99

    def test_delegates_to_runtime_result_from_workspace_state(self):
        ws = _make_ws()
        via_service = WorkbookService.get_runtime_result(ws)
        direct = RuntimeResult.from_workspace_state(ws)
        self.assertEqual(via_service.snapshot_id, direct.snapshot_id)
        self.assertEqual(via_service.origin, direct.origin)


# ---------------------------------------------------------------------------
# runtime_hydration_script
# ---------------------------------------------------------------------------

class TestRuntimeHydrationScript(unittest.TestCase):

    def test_returns_script_tag_when_runtime_present(self):
        ws = _make_ws()
        script = WorkbookService.runtime_hydration_script(ws)
        self.assertTrue(script.startswith("<script>"))
        self.assertTrue(script.endswith("</script>"))

    def test_returns_empty_string_when_no_runtime(self):
        ws = _make_ws(last_runtime_snapshot_id="")
        self.assertEqual(WorkbookService.runtime_hydration_script(ws), "")

    def test_returns_empty_string_when_no_summary(self):
        ws = _make_ws(_no_summary=True)
        self.assertEqual(WorkbookService.runtime_hydration_script(ws), "")

    def test_script_contains_runtime_summary_key(self):
        ws = _make_ws()
        script = WorkbookService.runtime_hydration_script(ws)
        self.assertIn("lastRuntimeSummary", script)

    def test_script_removes_stale_keys_when_no_schedules(self):
        ws = _make_ws()
        script = WorkbookService.runtime_hydration_script(ws)
        self.assertIn("sessionStorage.removeItem", script)

    def test_script_matches_direct_rr_call(self):
        ws = _make_ws()
        via_service = WorkbookService.runtime_hydration_script(ws)
        rr = RuntimeResult.from_workspace_state(ws)
        self.assertEqual(via_service, rr.to_sessionstorage_script())

    def test_safe_to_concatenate_empty_result(self):
        ws = _make_ws(last_runtime_snapshot_id="")
        prefix = "<html><body>"
        self.assertEqual(prefix + WorkbookService.runtime_hydration_script(ws), prefix)


# ---------------------------------------------------------------------------
# Import surface
# ---------------------------------------------------------------------------

class TestImportSurface(unittest.TestCase):

    def test_importable_from_workbook_package(self):
        from app.workbook import WorkbookService as WS
        self.assertIs(WS, WorkbookService)

    def test_all_public_methods_are_static(self):
        for name in (
            "build_input_set",
            "build_draft_input_set_from_workspace",
            "build_saved_input_set_from_workspace",
            "to_projectinputs",
            "get_runtime_result",
            "runtime_hydration_script",
        ):
            self.assertIsInstance(
                inspect.getattr_static(WorkbookService, name),
                staticmethod,
                f"{name} should be a staticmethod",
            )

    def test_old_generic_method_not_present(self):
        self.assertFalse(
            hasattr(WorkbookService, "build_input_set_from_workspace"),
            "build_input_set_from_workspace must not exist; use the explicit draft/saved variants",
        )

    def test_instantiation_yields_no_shared_state(self):
        ws1 = WorkbookService()
        ws2 = WorkbookService()
        self.assertIsNot(ws1, ws2)


if __name__ == "__main__":
    unittest.main()
