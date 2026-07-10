"""
Tests for WorkbookUpdateService (PR 864).

Coverage:
1. validate_field_update — all 11 project_setup fields, type coercion, bounds, options
2. Error taxonomy — UnknownFieldError, NonEditableFieldError, FieldValidationError
3. apply_field_to_pis — immutability, content_hash change, error propagation
4. apply_draft_update — stale hash, protected reference, persist path
5. FieldValidationResult contract
"""
from __future__ import annotations

import unittest
from datetime import date
from unittest.mock import MagicMock, patch, call

from app.workbook.input_set import ProjectInputSet
from app.workbook.registry import WORKBOOK
from app.workbook.update_service import (
    FieldValidationError,
    FieldValidationResult,
    NonEditableFieldError,
    ProtectedReferenceError,
    StaleContentError,
    UnknownFieldError,
    WorkbookUpdateError,
    WorkbookUpdateService,
)


def _make_pis(snapshot: dict = None) -> ProjectInputSet:
    return ProjectInputSet.from_snapshot(snapshot or {}, workbook=WORKBOOK)


# ---------------------------------------------------------------------------
# 1. validate_field_update — per-field coverage
# ---------------------------------------------------------------------------

class TestValidateFieldUpdate(unittest.TestCase):

    def _valid(self, field_id: str, raw: str):
        r = WorkbookUpdateService.validate_field_update(field_id, raw)
        self.assertTrue(r.is_valid, f"expected valid for {field_id}={raw!r}: {r.error}")
        return r

    def _invalid(self, field_id: str, raw: str):
        r = WorkbookUpdateService.validate_field_update(field_id, raw)
        self.assertFalse(r.is_valid, f"expected invalid for {field_id}={raw!r}")
        return r

    # --- project_setup.identity fields ---

    def test_project_name_text(self):
        r = self._valid("project_setup.identity.project_name", "My Wind Farm")
        self.assertEqual(r.typed_value, "My Wind Farm")

    def test_project_name_empty_string_fails_required(self):
        r = self._invalid("project_setup.identity.project_name", "")
        self.assertIn("required", r.error.lower())

    def test_project_name_whitespace_fails_required(self):
        r = self._invalid("project_setup.identity.project_name", "   ")
        self.assertIn("required", r.error.lower())

    def test_country_market_text(self):
        r = self._valid("project_setup.identity.country_market", "Germany")
        self.assertEqual(r.typed_value, "Germany")

    def test_country_market_empty_allowed(self):
        r = WorkbookUpdateService.validate_field_update("project_setup.identity.country_market", "")
        self.assertTrue(r.is_valid)
        self.assertIsNone(r.typed_value)

    def test_currency_valid_option(self):
        for opt in ("EUR", "USD", "GBP", "HRK", "PLN", "RON"):
            r = self._valid("project_setup.identity.currency", opt)
            self.assertEqual(r.typed_value, opt)

    def test_currency_invalid_option(self):
        r = self._invalid("project_setup.identity.currency", "BTC")
        self.assertIn("not a valid option", r.error)
        self.assertIn("EUR", r.error)

    def test_scenario_text(self):
        r = self._valid("project_setup.identity.scenario", "Upside")
        self.assertEqual(r.typed_value, "Upside")

    # --- project_setup.technical fields ---

    def test_capacity_mw_float(self):
        r = self._valid("project_setup.technical.capacity_mw", "150.5")
        self.assertAlmostEqual(r.typed_value, 150.5)

    def test_capacity_mw_below_min(self):
        r = self._invalid("project_setup.technical.capacity_mw", "0.05")
        self.assertIn("≥", r.error)
        self.assertIn("0.1", r.error)

    def test_capacity_mw_zero_invalid(self):
        r = self._invalid("project_setup.technical.capacity_mw", "0")
        self.assertFalse(r.is_valid)

    def test_capacity_mw_not_a_number(self):
        r = self._invalid("project_setup.technical.capacity_mw", "abc")
        self.assertFalse(r.is_valid)

    def test_capacity_mw_required_empty_fails(self):
        r = self._invalid("project_setup.technical.capacity_mw", "")
        self.assertIn("required", r.error.lower())

    def test_p50_hours_float(self):
        r = self._valid("project_setup.technical.p50_hours", "2200")
        self.assertAlmostEqual(r.typed_value, 2200.0)

    def test_p50_hours_below_min(self):
        r = self._invalid("project_setup.technical.p50_hours", "0")
        self.assertIn("≥", r.error)

    def test_cod_date_valid(self):
        r = self._valid("project_setup.technical.cod_date", "2028-06-01")
        self.assertEqual(r.typed_value, date(2028, 6, 1))

    def test_cod_date_invalid_format(self):
        r = self._invalid("project_setup.technical.cod_date", "06/01/2028")
        self.assertFalse(r.is_valid)

    def test_construction_months_int(self):
        r = self._valid("project_setup.technical.construction_months", "18")
        self.assertEqual(r.typed_value, 18)

    def test_construction_months_max(self):
        r = self._invalid("project_setup.technical.construction_months", "121")
        self.assertIn("≤", r.error)

    def test_construction_months_below_min(self):
        r = self._invalid("project_setup.technical.construction_months", "0")
        self.assertFalse(r.is_valid)

    def test_horizon_years_int(self):
        r = self._valid("project_setup.technical.horizon_years", "25")
        self.assertEqual(r.typed_value, 25)

    def test_horizon_years_max(self):
        r = self._invalid("project_setup.technical.horizon_years", "51")
        self.assertIn("≤", r.error)


# ---------------------------------------------------------------------------
# 2. Error taxonomy
# ---------------------------------------------------------------------------

class TestErrorTaxonomy(unittest.TestCase):

    def test_unknown_field_raises(self):
        with self.assertRaises(UnknownFieldError):
            WorkbookUpdateService.validate_field_update("capacity_mw", "100")

    def test_legacy_snapshot_key_raises_unknown(self):
        """Legacy keys like 'project_name' (without sheet prefix) must raise."""
        with self.assertRaises(UnknownFieldError):
            WorkbookUpdateService.validate_field_update("project_name", "Test")

    def test_display_only_raises_non_editable(self):
        with self.assertRaises(NonEditableFieldError):
            WorkbookUpdateService.validate_field_update(
                "project_setup.technical.capacity_factor", "30"
            )

    def test_template_locked_raises_non_editable(self):
        with self.assertRaises(NonEditableFieldError):
            WorkbookUpdateService.validate_field_update(
                "project_setup.identity.project_type", "solar_pv"
            )

    def test_error_types_are_subclasses(self):
        self.assertTrue(issubclass(UnknownFieldError, WorkbookUpdateError))
        self.assertTrue(issubclass(NonEditableFieldError, WorkbookUpdateError))
        self.assertTrue(issubclass(FieldValidationError, WorkbookUpdateError))
        self.assertTrue(issubclass(StaleContentError, WorkbookUpdateError))
        self.assertTrue(issubclass(ProtectedReferenceError, WorkbookUpdateError))


# ---------------------------------------------------------------------------
# 3. apply_field_to_pis
# ---------------------------------------------------------------------------

class TestApplyFieldToPis(unittest.TestCase):

    def setUp(self):
        self.pis = _make_pis({"project_name": "Old Name", "capacity_mw": "50"})

    def test_returns_new_pis_instance(self):
        r = WorkbookUpdateService.validate_field_update(
            "project_setup.identity.project_name", "New Name"
        )
        new_pis = WorkbookUpdateService.apply_field_to_pis(self.pis, r)
        self.assertIsNot(new_pis, self.pis)

    def test_original_pis_unchanged(self):
        r = WorkbookUpdateService.validate_field_update(
            "project_setup.identity.project_name", "New Name"
        )
        WorkbookUpdateService.apply_field_to_pis(self.pis, r)
        self.assertEqual(self.pis.get("project_setup.identity.project_name"), "Old Name")

    def test_new_pis_has_updated_value(self):
        r = WorkbookUpdateService.validate_field_update(
            "project_setup.identity.project_name", "New Name"
        )
        new_pis = WorkbookUpdateService.apply_field_to_pis(self.pis, r)
        self.assertEqual(new_pis.get("project_setup.identity.project_name"), "New Name")

    def test_content_hash_changes(self):
        r = WorkbookUpdateService.validate_field_update(
            "project_setup.identity.project_name", "New Name"
        )
        new_pis = WorkbookUpdateService.apply_field_to_pis(self.pis, r)
        self.assertNotEqual(new_pis.content_hash, self.pis.content_hash)

    def test_unrelated_fields_unchanged(self):
        r = WorkbookUpdateService.validate_field_update(
            "project_setup.identity.project_name", "New Name"
        )
        new_pis = WorkbookUpdateService.apply_field_to_pis(self.pis, r)
        self.assertAlmostEqual(
            new_pis.get("project_setup.technical.capacity_mw"), 50.0
        )

    def test_invalid_validation_raises_field_validation_error(self):
        r = WorkbookUpdateService.validate_field_update(
            "project_setup.technical.capacity_mw", "-5"
        )
        self.assertFalse(r.is_valid)
        with self.assertRaises(FieldValidationError):
            WorkbookUpdateService.apply_field_to_pis(self.pis, r)

    def test_capacity_mw_typed_as_float(self):
        r = WorkbookUpdateService.validate_field_update(
            "project_setup.technical.capacity_mw", "200"
        )
        new_pis = WorkbookUpdateService.apply_field_to_pis(self.pis, r)
        self.assertAlmostEqual(new_pis.get("project_setup.technical.capacity_mw"), 200.0)

    def test_date_field_typed_as_date(self):
        r = WorkbookUpdateService.validate_field_update(
            "project_setup.technical.cod_date", "2030-01-01"
        )
        new_pis = WorkbookUpdateService.apply_field_to_pis(self.pis, r)
        self.assertEqual(
            new_pis.get("project_setup.technical.cod_date"), date(2030, 1, 1)
        )

    def test_to_snapshot_contains_updated_key(self):
        """to_snapshot() maps back to the legacy snapshot key (not field_id)."""
        r = WorkbookUpdateService.validate_field_update(
            "project_setup.identity.project_name", "New Name"
        )
        new_pis = WorkbookUpdateService.apply_field_to_pis(self.pis, r)
        snap = new_pis.to_snapshot()
        self.assertEqual(snap["project_name"], "New Name")
        # Semantic field_id must NOT appear as a snapshot key
        self.assertNotIn("project_setup.identity.project_name", snap)


# ---------------------------------------------------------------------------
# 4. apply_draft_update
# ---------------------------------------------------------------------------

class TestApplyDraftUpdate(unittest.TestCase):

    def _make_ws(self, draft_snapshot=None, saved_snapshot=None):
        ws = MagicMock()
        ws.user_id = "test-user"
        ws.project_id = "proj-uuid"
        ws.project_code = "test-project"
        ws.draft_snapshot = draft_snapshot or {"project_name": "Test", "capacity_mw": "50"}
        ws.saved_snapshot = saved_snapshot or ws.draft_snapshot.copy()
        return ws

    def _make_project_record(self, project_origin="user_created", template_source="generic_wind"):
        pr = MagicMock()
        pr.project_origin = project_origin
        pr.template_source = template_source
        pr.source_project_template = None
        pr.project_code = "test-project"
        return pr

    def _current_hash(self, ws):
        pis = ProjectInputSet.from_snapshot(ws.draft_snapshot, workbook=WORKBOOK)
        return pis.content_hash

    @patch("app.persistence.workspace_repository.save_workspace_state")
    def test_success_updates_draft(self, mock_save):
        ws = self._make_ws()
        pr = self._make_project_record()
        content_hash = self._current_hash(ws)

        updated = WorkbookUpdateService.apply_draft_update(
            ws=ws, field_id="project_setup.identity.project_name",
            raw_value="Updated Name", content_hash=content_hash,
            project_record=pr,
        )

        self.assertEqual(updated.get("project_setup.identity.project_name"), "Updated Name")
        mock_save.assert_called_once()
        call_kwargs = mock_save.call_args.kwargs
        self.assertEqual(call_kwargs["draft_snapshot"]["project_name"], "Updated Name")
        self.assertEqual(call_kwargs["saved_snapshot"], ws.saved_snapshot)
        self.assertTrue(call_kwargs["dirty"])

    @patch("app.persistence.workspace_repository.save_workspace_state")
    def test_stale_hash_raises(self, mock_save):
        ws = self._make_ws()
        pr = self._make_project_record()
        with self.assertRaises(StaleContentError):
            WorkbookUpdateService.apply_draft_update(
                ws=ws, field_id="project_setup.identity.project_name",
                raw_value="X", content_hash="stale-hash",
                project_record=pr,
            )
        mock_save.assert_not_called()

    @patch("app.persistence.workspace_repository.save_workspace_state")
    def test_protected_reference_raises(self, mock_save):
        ws = self._make_ws(
            draft_snapshot={"project_name": "TUHO", "template_source": "tuho",
                            "project_origin": "factory_template"}
        )
        pr = self._make_project_record(project_origin="factory_template",
                                       template_source="tuho")
        content_hash = self._current_hash(ws)
        with self.assertRaises(ProtectedReferenceError):
            WorkbookUpdateService.apply_draft_update(
                ws=ws, field_id="project_setup.identity.project_name",
                raw_value="X", content_hash=content_hash,
                project_record=pr,
            )
        mock_save.assert_not_called()

    @patch("app.persistence.workspace_repository.save_workspace_state")
    def test_validation_error_not_saved(self, mock_save):
        ws = self._make_ws()
        pr = self._make_project_record()
        content_hash = self._current_hash(ws)
        with self.assertRaises(FieldValidationError):
            WorkbookUpdateService.apply_draft_update(
                ws=ws, field_id="project_setup.technical.capacity_mw",
                raw_value="-100", content_hash=content_hash,
                project_record=pr,
            )
        mock_save.assert_not_called()

    @patch("app.persistence.workspace_repository.save_workspace_state")
    def test_saved_snapshot_not_mutated(self, mock_save):
        """Saving a draft must never change the saved_snapshot."""
        ws = self._make_ws()
        pr = self._make_project_record()
        original_saved = ws.saved_snapshot.copy()
        content_hash = self._current_hash(ws)
        WorkbookUpdateService.apply_draft_update(
            ws=ws, field_id="project_setup.identity.project_name",
            raw_value="New Name", content_hash=content_hash,
            project_record=pr,
        )
        saved_kwarg = mock_save.call_args.kwargs["saved_snapshot"]
        self.assertEqual(saved_kwarg, original_saved)

    @patch("app.persistence.workspace_repository.save_workspace_state")
    def test_returned_pis_is_projectinputset(self, mock_save):
        ws = self._make_ws()
        pr = self._make_project_record()
        content_hash = self._current_hash(ws)
        result = WorkbookUpdateService.apply_draft_update(
            ws=ws, field_id="project_setup.identity.project_name",
            raw_value="Updated", content_hash=content_hash,
            project_record=pr,
        )
        self.assertIsInstance(result, ProjectInputSet)


# ---------------------------------------------------------------------------
# 5. FieldValidationResult contract
# ---------------------------------------------------------------------------

class TestFieldValidationResult(unittest.TestCase):

    def test_valid_result_is_valid(self):
        r = WorkbookUpdateService.validate_field_update(
            "project_setup.identity.project_name", "Farm"
        )
        self.assertTrue(r.is_valid)
        self.assertIsNone(r.error)

    def test_invalid_result_has_error(self):
        r = WorkbookUpdateService.validate_field_update(
            "project_setup.technical.capacity_mw", ""
        )
        self.assertFalse(r.is_valid)
        self.assertIsNotNone(r.error)

    def test_result_carries_spec(self):
        r = WorkbookUpdateService.validate_field_update(
            "project_setup.identity.project_name", "Farm"
        )
        self.assertEqual(r.spec.field_id, "project_setup.identity.project_name")

    def test_result_carries_raw_value(self):
        raw = "  My Farm  "
        r = WorkbookUpdateService.validate_field_update(
            "project_setup.identity.project_name", raw
        )
        self.assertEqual(r.raw_value, raw)

    def test_result_carries_field_id(self):
        r = WorkbookUpdateService.validate_field_update(
            "project_setup.identity.project_name", "Farm"
        )
        self.assertEqual(r.field_id, "project_setup.identity.project_name")


if __name__ == "__main__":
    unittest.main()
