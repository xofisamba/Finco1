"""
Tests for WorkbookService — the pure domain service layer (Workbook V2, PR 4).

WorkbookService has no I/O, no DB calls, no HTTP.  Every method is a thin
coordinator that delegates to ProjectInputSet or RuntimeResult; these tests
verify the coordination contracts, not the delegate implementations.
"""
from __future__ import annotations

import inspect
import unittest
from unittest.mock import MagicMock
from typing import Any

from app.workbook.service import WorkbookService
from app.workbook.input_set import ProjectInputSet
from app.workbook.runtime_result import RuntimeResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_snapshot(**overrides: Any) -> dict[str, Any]:
    """Minimal snapshot that ProjectInputSet.from_snapshot() accepts."""
    base = {
        "project_name": "Test Project",
        "capex_meur": "100",
        "cod_year": "2028",
    }
    base.update(overrides)
    return base


def _make_ws(
    *,
    draft_snapshot: dict | None = None,
    project_code: str = "generic_wind",
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

    def test_template_source_in_snapshot_propagated(self):
        snap = _make_snapshot(template_source="tuho")
        pis = WorkbookService.build_input_set(snap)
        self.assertEqual(pis.template_source, "tuho")

    def test_project_origin_in_snapshot_propagated(self):
        snap = _make_snapshot(project_origin="factory_template")
        pis = WorkbookService.build_input_set(snap)
        self.assertEqual(pis.project_origin, "factory_template")

    def test_empty_snapshot_returns_empty_pis(self):
        # from_snapshot() tolerates empty snapshots (no required fields at this layer)
        pis = WorkbookService.build_input_set({})
        self.assertIsInstance(pis, ProjectInputSet)
        self.assertEqual(len(pis.snapshot_origin), 0)

    def test_delegates_to_from_snapshot(self):
        snap = _make_snapshot()
        via_service = WorkbookService.build_input_set(snap)
        direct = ProjectInputSet.from_snapshot(snapshot=snap)
        self.assertEqual(via_service.content_hash, direct.content_hash)


# ---------------------------------------------------------------------------
# build_input_set_from_workspace
# ---------------------------------------------------------------------------

class TestBuildInputSetFromWorkspace(unittest.TestCase):

    def test_returns_project_input_set(self):
        ws = _make_ws()
        pis = WorkbookService.build_input_set_from_workspace(ws)
        self.assertIsInstance(pis, ProjectInputSet)

    def test_uses_draft_snapshot(self):
        ws = _make_ws(draft_snapshot=_make_snapshot(capex_meur="999"))
        pis = WorkbookService.build_input_set_from_workspace(ws)
        self.assertEqual(pis.snapshot_origin.get("capex_meur"), "999")

    def test_injects_project_code_as_template_source(self):
        ws = _make_ws(project_code="tuho")
        pis = WorkbookService.build_input_set_from_workspace(ws)
        self.assertEqual(pis.template_source, "tuho")

    def test_snapshot_template_source_takes_precedence(self):
        ws = _make_ws(
            draft_snapshot=_make_snapshot(template_source="existing"),
            project_code="tuho",
        )
        pis = WorkbookService.build_input_set_from_workspace(ws)
        self.assertEqual(pis.template_source, "existing")

    def test_generic_wind_project_code(self):
        ws = _make_ws(project_code="generic_wind")
        pis = WorkbookService.build_input_set_from_workspace(ws)
        self.assertEqual(pis.template_source, "generic_wind")

    def test_draft_snapshot_not_mutated(self):
        snap = _make_snapshot()
        original_keys = set(snap.keys())
        ws = _make_ws(draft_snapshot=snap, project_code="tuho")
        WorkbookService.build_input_set_from_workspace(ws)
        self.assertEqual(set(snap.keys()), original_keys)

    def test_content_hash_stable_for_same_workspace(self):
        ws = _make_ws()
        pis1 = WorkbookService.build_input_set_from_workspace(ws)
        pis2 = WorkbookService.build_input_set_from_workspace(ws)
        self.assertEqual(pis1.content_hash, pis2.content_hash)


# ---------------------------------------------------------------------------
# to_projectinputs
# ---------------------------------------------------------------------------

def _full_snapshot() -> dict:
    """Complete snapshot with all required fields (mirrors _tuho_snapshot())."""
    from app.project_factories import create_default_tuho_wind1
    pi = create_default_tuho_wind1()
    return {
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
        ws = _make_ws(last_runtime_summary={"project_irr": 0.12, "equity_irr": 0.15})
        rr = WorkbookService.get_runtime_result(ws)
        self.assertAlmostEqual(rr.runtime_summary["project_irr"], 0.12)

    def test_schedule_payload_propagated(self):
        fs = {"periods": [{"year": 2029, "revenue_keur": 1000}]}
        ws = _make_ws(last_financial_statements=fs)
        rr = WorkbookService.get_runtime_result(ws)
        self.assertIsNotNone(rr.financial_statements)

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
        script = WorkbookService.runtime_hydration_script(ws)
        self.assertEqual(script, "")

    def test_returns_empty_string_when_no_summary(self):
        ws = _make_ws(_no_summary=True)
        script = WorkbookService.runtime_hydration_script(ws)
        self.assertEqual(script, "")

    def test_script_contains_runtime_summary_key(self):
        ws = _make_ws()
        script = WorkbookService.runtime_hydration_script(ws)
        self.assertIn("lastRuntimeSummary", script)

    def test_script_contains_setitem_for_summary(self):
        ws = _make_ws()
        script = WorkbookService.runtime_hydration_script(ws)
        self.assertIn("sessionStorage.setItem", script)

    def test_script_removes_stale_keys_when_no_schedules(self):
        ws = _make_ws()
        script = WorkbookService.runtime_hydration_script(ws)
        self.assertIn("sessionStorage.removeItem", script)

    def test_script_matches_direct_rr_call(self):
        ws = _make_ws()
        via_service = WorkbookService.runtime_hydration_script(ws)
        rr = RuntimeResult.from_workspace_state(ws)
        direct = rr.to_sessionstorage_script()
        self.assertEqual(via_service, direct)

    def test_safe_to_concatenate_empty_result(self):
        ws = _make_ws(last_runtime_snapshot_id="")
        prefix = "<html><body>"
        result = prefix + WorkbookService.runtime_hydration_script(ws)
        self.assertEqual(result, prefix)

    def test_script_includes_financial_statements_when_present(self):
        fs = {"periods": [{"year": 2029, "revenue_keur": 1000}]}
        ws = _make_ws(last_financial_statements=fs)
        script = WorkbookService.runtime_hydration_script(ws)
        self.assertIn("lastFinancialStatements", script)
        self.assertIn("setItem", script)


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
            "build_input_set_from_workspace",
            "to_projectinputs",
            "get_runtime_result",
            "runtime_hydration_script",
        ):
            self.assertIsInstance(
                inspect.getattr_static(WorkbookService, name),
                staticmethod,
                f"{name} should be a staticmethod",
            )

    def test_instantiation_yields_no_shared_state(self):
        ws1 = WorkbookService()
        ws2 = WorkbookService()
        self.assertIsNot(ws1, ws2)


if __name__ == "__main__":
    unittest.main()
