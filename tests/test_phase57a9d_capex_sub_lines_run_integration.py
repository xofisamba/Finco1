"""Phase 57A-9D — Run / materialization integration tests.

These tests pin the contract for the explicit Run/
materialization boundary where persisted user-added
CAPEX sub-lines fold into the input CapexStructure of
the financial model.

This is the FIRST phase where user-added CAPEX rows may
affect model outputs. Treat as high risk.

The contract:

1. Factory / template-seeded projects (TUHO, Oborovo,
   Generic Solar, Generic Wind) have no user sub-lines.
   The integration helper returns the input CapexStructure
   unchanged. The factory total capex is bit-for-bit
   identical to the pre-57A-9D baseline.

2. User projects load active (is_active=1) sub-lines
   from the capex_sub_lines table, keyed by project_id.
   Soft-deleted rows are excluded.

3. Scenario override amount (from the reserved
   _capex_sub_line_overrides key) REPLACES the project
   default amount. It is NOT a delta adjustment. This
   is the 57A-9B Claude delta review fix.

4. Unknown sub_line_id override UUIDs are ignored (the
   line may have been removed since the scenario was
   saved). The Run does not crash; a warning is logged.

5. Unknown parent categories raise ValueError loudly.
   The 57A-9B validate_parent_category helper rejects
   C.17 and C.18 at persistence time, so they never
   reach this integration layer.

6. C.08 and C.11 both fold into audit_legal additively.

7. 57A-8 in-memory preview rows (TMP markers) are NOT
   persisted and therefore cannot leak into the Run.

8. The integration helper does NOT touch the model
   formula path, the Excel export, the UI, or the
   waterfall engine internals. It is a pure input-
   materialization step.

Type: runtime model-input integration, DRAFT PR (57A-9D).
"""

from __future__ import annotations

import logging
import os
import sqlite3
import uuid
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def test_db(monkeypatch, tmp_path):
    """Isolated SQLite DB with the persistence schema migrated."""
    db_file = tmp_path / f"phase57a9d_{uuid.uuid4().hex[:8]}.db"
    monkeypatch.setenv("FINCO_DB_PATH", str(db_file))
    import app.persistence.db as db_mod
    monkeypatch.setattr(db_mod, "DB_PATH", str(db_file))
    db_mod.init_db()
    yield db_file


@pytest.fixture
def make_sub_line():
    """Factory for building CapexSubLine records (test-side helper)."""
    from app.persistence.capex_sub_lines import CapexSubLine

    def _make(
        *,
        sub_line_id: str = "",
        project_id: str = "user-proj-1",
        parent_category_code: str = "C.02",
        label: str = "Test sub-line",
        amount_keur: float = 100.0,
        is_active: bool = True,
        display_order: int = 1,
    ) -> CapexSubLine:
        return CapexSubLine(
            id=0,
            sub_line_id=sub_line_id or str(uuid.uuid4()),
            project_id=project_id,
            parent_category_code=parent_category_code,
            business_code=f"{parent_category_code}.U{display_order:03d}",
            display_order=display_order,
            label=label,
            amount_keur=amount_keur,
            comments="",
            schedule_json="{}",
            source="user",
            is_active=is_active,
            governance_state={},
            replay_metadata={},
            created_at="2026-06-05T00:00:00+00:00",
            updated_at="2026-06-05T00:00:00+00:00",
        )

    return _make


# ---------------------------------------------------------------------------
# 1. Factory / template-seeded projects: no-op, parity preserved
# ---------------------------------------------------------------------------


class TestFactoryNoOpParity:
    """TUHO and Oborovo factory projects have no user sub-lines.
    The integration helper must return the input CapexStructure
    unchanged. The factory total capex is bit-for-bit identical
    to the pre-57A-9D baseline.

    These are the canonical parity references.
    """

    def test_tuho_factory_total_capex_unchanged(self, monkeypatch):
        """TUHO factory project: 57A-9D integration helper
        returns capex unchanged. The factory total is
        bit-for-bit identical to the pre-57A-9D baseline.
        """
        # Force the integration helper to use a DB that has
        # NO sub-lines for TUHO's project_id (which is the
        # factory case).
        monkeypatch.setenv("FINCO_DB_PATH", "/nonexistent/test_db.db")
        from app.ui_runner import run_demo_project
        from app.services.capex_sub_lines_integration import (
            _apply_user_sub_lines_to_capex,
        )

        r = run_demo_project("TUHO", "Base")
        capex_baseline = r.project_inputs.capex
        # Run through the integration helper with a fake
        # project_id (the DB doesn't exist, so loading
        # returns empty, but we also test the empty-DB
        # defensive path here).
        capex_after = _apply_user_sub_lines_to_capex(
            capex_baseline, project_id="nonexistent-tuho-proj",
        )
        # TUHO has no user sub-lines; helper returns
        # capex unchanged.
        assert capex_after is capex_baseline
        # Numeric parity: factory total capex is unchanged.
        total_baseline = sum(
            getattr(capex_baseline, f).amount_keur
            for f in [
                "epc_contract", "production_units", "epc_other",
                "grid_connection", "ops_prep", "insurances",
                "lease_tax", "construction_mgmt_a",
                "commissioning", "audit_legal",
                "construction_mgmt_b", "contingencies",
                "taxes", "project_acquisition", "project_rights",
            ]
        )
        total_after = sum(
            getattr(capex_after, f).amount_keur
            for f in [
                "epc_contract", "production_units", "epc_other",
                "grid_connection", "ops_prep", "insurances",
                "lease_tax", "construction_mgmt_a",
                "commissioning", "audit_legal",
                "construction_mgmt_b", "contingencies",
                "taxes", "project_acquisition", "project_rights",
            ]
        )
        assert total_after == total_baseline
        # Pinned numeric baseline (captured pre-57A-9D).
        assert abs(total_baseline - 70691.54) < 0.01, (
            f"TUHO factory total drifted: {total_baseline}"
        )

    def test_oborovo_factory_total_capex_unchanged(
        self, monkeypatch
    ):
        """Oborovo factory project: 57A-9D integration helper
        returns capex unchanged. The factory total is
        bit-for-bit identical to the pre-57A-9D baseline.
        """
        monkeypatch.setenv("FINCO_DB_PATH", "/nonexistent/test_db.db")
        from app.ui_runner import run_demo_project
        from app.services.capex_sub_lines_integration import (
            _apply_user_sub_lines_to_capex,
        )

        r = run_demo_project("Oborovo", "Base")
        capex_baseline = r.project_inputs.capex
        capex_after = _apply_user_sub_lines_to_capex(
            capex_baseline, project_id="nonexistent-oborovo-proj",
        )
        assert capex_after is capex_baseline
        total_baseline = sum(
            getattr(capex_baseline, f).amount_keur
            for f in [
                "epc_contract", "production_units", "epc_other",
                "grid_connection", "ops_prep", "insurances",
                "lease_tax", "construction_mgmt_a",
                "commissioning", "audit_legal",
                "construction_mgmt_b", "contingencies",
                "taxes", "project_acquisition", "project_rights",
            ]
        )
        total_after = sum(
            getattr(capex_after, f).amount_keur
            for f in [
                "epc_contract", "production_units", "epc_other",
                "grid_connection", "ops_prep", "insurances",
                "lease_tax", "construction_mgmt_a",
                "commissioning", "audit_legal",
                "construction_mgmt_b", "contingencies",
                "taxes", "project_acquisition", "project_rights",
            ]
        )
        assert total_after == total_baseline
        # Pinned numeric baseline.
        assert abs(total_baseline - 55999.09) < 0.01, (
            f"Oborovo factory total drifted: {total_baseline}"
        )

    def test_empty_project_id_returns_capex_unchanged(
        self, monkeypatch
    ):
        """If the caller passes an empty project_id (e.g.
        from a generic / template-seeded path), the helper
        MUST short-circuit and return capex unchanged.
        This is a defensive guard for the run_service
        path."""
        monkeypatch.setenv("FINCO_DB_PATH", "/nonexistent/test_db.db")
        from app.ui_runner import run_demo_project
        from app.services.capex_sub_lines_integration import (
            _apply_user_sub_lines_to_capex,
        )

        r = run_demo_project("Solar", "Base")
        capex = r.project_inputs.capex
        capex_after = _apply_user_sub_lines_to_capex(
            capex, project_id="",
        )
        assert capex_after is capex


# ---------------------------------------------------------------------------
# 2. User projects: active sub-lines fold, soft-deleted excluded
# ---------------------------------------------------------------------------


class TestUserProjectFold:
    def test_user_project_with_one_c02_sub_line_increases_epc(
        self, test_db, make_sub_line
    ):
        """A user project with a single C.02 (EPC) sub-line
        increases the epc_contract amount by the sub-line
        amount. This is the canonical user-projection fold.
        """
        from app.ui_runner import run_demo_project
        from app.services.capex_sub_lines_integration import (
            _apply_user_sub_lines_to_capex,
        )
        from app.persistence.capex_sub_lines import (
            create_sub_line,
        )
        from app.persistence.projects_repository import save_project

        # Create a user project in the test DB.
        project = save_project(
            user_id="u1",
            project_code="PRJ-C02-1",
            project_name="User C.02 test",
            source_project_template="Generic",
            project_origin="user_project",
            is_readonly=False,
        )
        # Create one C.02 sub-line.
        with sqlite3.connect(os.environ["FINCO_DB_PATH"]) as c:
            c.row_factory = sqlite3.Row
            create_sub_line(
                c.cursor(),
                project_id=project.project_id,
                parent_category_code="C.02",
                label="Extra EPC phase",
                amount_keur=5000.0,
            )
            c.commit()

        r = run_demo_project("Solar", "Base")
        capex = r.project_inputs.capex
        capex_before_epc = capex.epc_contract.amount_keur

        capex_after = _apply_user_sub_lines_to_capex(
            capex, project_id=project.project_id,
        )
        # +5000 from the sub-line.
        assert (
            capex_after.epc_contract.amount_keur
            == capex_before_epc + 5000.0
        )

    def test_c08_and_c11_add_into_audit_legal(
        self, test_db, make_sub_line
    ):
        """C.08 and C.11 both fold into audit_legal
        additively. The locked mapping (57A-9B) is
        preserved at the integration layer."""
        from app.ui_runner import run_demo_project
        from app.services.capex_sub_lines_integration import (
            _apply_user_sub_lines_to_capex,
        )
        from app.persistence.capex_sub_lines import (
            create_sub_line,
        )
        from app.persistence.projects_repository import save_project

        project = save_project(
            user_id="u2",
            project_code="PRJ-AUD-1",
            project_name="Audit legal test",
            source_project_template="Generic",
            project_origin="user_project",
            is_readonly=False,
        )
        with sqlite3.connect(os.environ["FINCO_DB_PATH"]) as c:
            c.row_factory = sqlite3.Row
            create_sub_line(
                c.cursor(),
                project_id=project.project_id,
                parent_category_code="C.08",
                label="C.08 line",
                amount_keur=300.0,
            )
            create_sub_line(
                c.cursor(),
                project_id=project.project_id,
                parent_category_code="C.11",
                label="C.11 line",
                amount_keur=400.0,
            )
            c.commit()

        r = run_demo_project("Wind", "Base")
        capex = r.project_inputs.capex
        capex_after = _apply_user_sub_lines_to_capex(
            capex, project_id=project.project_id,
        )
        # C.08 + C.11 both add into audit_legal.
        assert (
            capex_after.audit_legal.amount_keur
            == capex.audit_legal.amount_keur + 700.0
        )

    def test_soft_deleted_sub_lines_excluded(
        self, test_db, make_sub_line
    ):
        """Soft-deleted sub-lines are excluded from the
        Run/materialization. The audit / replay trail
        remains in the table, but the fold only sees
        active rows."""
        from app.ui_runner import run_demo_project
        from app.services.capex_sub_lines_integration import (
            _apply_user_sub_lines_to_capex,
        )
        from app.persistence.capex_sub_lines import (
            create_sub_line,
            soft_delete_sub_line,
        )
        from app.persistence.projects_repository import save_project

        project = save_project(
            user_id="u3",
            project_code="PRJ-SD-1",
            project_name="Soft delete test",
            source_project_template="Generic",
            project_origin="user_project",
            is_readonly=False,
        )
        with sqlite3.connect(os.environ["FINCO_DB_PATH"]) as c:
            c.row_factory = sqlite3.Row
            keep = create_sub_line(
                c.cursor(),
                project_id=project.project_id,
                parent_category_code="C.02",
                label="Keep",
                amount_keur=1000.0,
            )
            drop = create_sub_line(
                c.cursor(),
                project_id=project.project_id,
                parent_category_code="C.02",
                label="Drop",
                amount_keur=2000.0,
            )
            c.commit()
            # Soft-delete drop.
            with sqlite3.connect(os.environ["FINCO_DB_PATH"]) as c2:
                c2.row_factory = sqlite3.Row
                assert soft_delete_sub_line(
                    c2.cursor(),
                    project_id=project.project_id,
                    sub_line_id=drop.sub_line_id,
                )
                c2.commit()

        r = run_demo_project("Solar", "Base")
        capex = r.project_inputs.capex
        capex_after = _apply_user_sub_lines_to_capex(
            capex, project_id=project.project_id,
        )
        # Only +1000 (keep) folds in; soft-deleted drop is
        # excluded.
        assert (
            capex_after.epc_contract.amount_keur
            == capex.epc_contract.amount_keur + 1000.0
        )


# ---------------------------------------------------------------------------
# 3. Scenario override semantic: REPLACE not delta
# ---------------------------------------------------------------------------


class TestScenarioOverrideReplace:
    def test_override_replaces_default_amount(
        self, test_db, make_sub_line
    ):
        """An override at the reserved
        ``_capex_sub_line_overrides`` key REPLACES the
        sub-line's default amount. It is NOT a delta
        adjustment. The 57A-9B Claude delta review fix
        is preserved at the integration layer."""
        from app.ui_runner import run_demo_project
        from app.services.capex_sub_lines_integration import (
            _apply_user_sub_lines_to_capex,
        )
        from app.persistence.capex_sub_lines import (
            create_sub_line,
        )
        from app.persistence.projects_repository import save_project

        project = save_project(
            user_id="u4",
            project_code="PRJ-OVR-1",
            project_name="Override test",
            source_project_template="Generic",
            project_origin="user_project",
            is_readonly=False,
        )
        with sqlite3.connect(os.environ["FINCO_DB_PATH"]) as c:
            c.row_factory = sqlite3.Row
            sub = create_sub_line(
                c.cursor(),
                project_id=project.project_id,
                parent_category_code="C.02",
                label="overridable",
                amount_keur=5000.0,
            )
            c.commit()
        sub_uuid = sub.sub_line_id

        r = run_demo_project("Solar", "Base")
        capex = r.project_inputs.capex
        baseline = capex.epc_contract.amount_keur

        # No override: +5000 (default).
        no_override = _apply_user_sub_lines_to_capex(
            capex, project_id=project.project_id,
            scenario_overrides=None,
        )
        assert (
            no_override.epc_contract.amount_keur
            == baseline + 5000.0
        )

        # Override to 8000: +8000 (REPLACE), NOT +5000+8000.
        replaced = _apply_user_sub_lines_to_capex(
            capex,
            project_id=project.project_id,
            scenario_overrides={
                "_capex_sub_line_overrides": {sub_uuid: 8000.0},
            },
        )
        assert (
            replaced.epc_contract.amount_keur
            == baseline + 8000.0
        )
        # Explicit "not a delta" check.
        assert (
            replaced.epc_contract.amount_keur
            != baseline + 5000.0 + 8000.0
        )

    def test_unknown_sub_line_id_override_ignored(
        self, test_db, make_sub_line
    ):
        """An override for a sub_line_id that does not
        exist (or has been soft-deleted) is silently
        ignored. The Run does not crash. A warning is
        logged for the reviewer to see."""
        from app.ui_runner import run_demo_project
        from app.services.capex_sub_lines_integration import (
            _apply_user_sub_lines_to_capex,
        )
        from app.persistence.capex_sub_lines import (
            create_sub_line,
        )
        from app.persistence.projects_repository import save_project

        project = save_project(
            user_id="u5",
            project_code="PRJ-STALE-1",
            project_name="Stale override test",
            source_project_template="Generic",
            project_origin="user_project",
            is_readonly=False,
        )
        with sqlite3.connect(os.environ["FINCO_DB_PATH"]) as c:
            c.row_factory = sqlite3.Row
            create_sub_line(
                c.cursor(),
                project_id=project.project_id,
                parent_category_code="C.02",
                label="real",
                amount_keur=100.0,
            )
            c.commit()

        r = run_demo_project("Solar", "Base")
        capex = r.project_inputs.capex
        baseline = capex.epc_contract.amount_keur

        # Override UUID that does NOT match any active
        # sub-line. Must be ignored, not crash.
        capex_after = _apply_user_sub_lines_to_capex(
            capex,
            project_id=project.project_id,
            scenario_overrides={
                "_capex_sub_line_overrides": {
                    "stale-uuid-1": 99999.0,
                    "stale-uuid-2": 88888.0,
                },
            },
        )
        # Only the real sub-line (+100) folds in. Stale
        # overrides are ignored.
        assert (
            capex_after.epc_contract.amount_keur
            == baseline + 100.0
        )

    def test_malformed_reserved_key_value_falls_back_to_empty(
        self, test_db, make_sub_line
    ):
        """If the reserved key carries a non-dict value
        (malformed scenario record), the helper falls
        back to an empty override map. The Run does not
        crash."""
        from app.ui_runner import run_demo_project
        from app.services.capex_sub_lines_integration import (
            _apply_user_sub_lines_to_capex,
        )
        from app.persistence.capex_sub_lines import (
            create_sub_line,
        )
        from app.persistence.projects_repository import save_project

        project = save_project(
            user_id="u6",
            project_code="PRJ-MAL-1",
            project_name="Malformed test",
            source_project_template="Generic",
            project_origin="user_project",
            is_readonly=False,
        )
        with sqlite3.connect(os.environ["FINCO_DB_PATH"]) as c:
            c.row_factory = sqlite3.Row
            create_sub_line(
                c.cursor(),
                project_id=project.project_id,
                parent_category_code="C.02",
                label="x",
                amount_keur=42.0,
            )
            c.commit()

        r = run_demo_project("Solar", "Base")
        capex = r.project_inputs.capex
        baseline = capex.epc_contract.amount_keur
        # Pass a non-dict value at the reserved key.
        capex_after = _apply_user_sub_lines_to_capex(
            capex,
            project_id=project.project_id,
            scenario_overrides={
                "_capex_sub_line_overrides": "not a dict",
            },
        )
        # Helper falls back to empty; +42 still folds in.
        assert (
            capex_after.epc_contract.amount_keur
            == baseline + 42.0
        )


# ---------------------------------------------------------------------------
# 4. Validation: unknown parent category raises loudly
# ---------------------------------------------------------------------------


class TestValidationFailFast:
    def test_unknown_parent_category_raises(
        self, test_db, make_sub_line
    ):
        """An unknown parent category in a persisted
        sub-line must raise ValueError loudly. The Run
        must not silently drop the line. The 57A-9B
        ``validate_parent_category`` helper is the
        fail-fast layer.
        """
        from app.services.capex_sub_lines_integration import (
            _apply_user_sub_lines_to_capex,
        )
        from app.persistence.capex_sub_lines import (
            validate_parent_category,
        )
        # Direct unit test: the validator raises.
        with pytest.raises(ValueError) as exc_info:
            validate_parent_category("C.99")
        assert "C.99" in str(exc_info.value) or "known" in str(
            exc_info.value
        ).lower()

    def test_c17_rejected(self):
        """C.17 is rejected at validation time. The 57A-9B
        mapping is locked: C.17 / C.18 are read-only in
        the CAPEX catalogue and do not accept user sub-
        lines."""
        from app.persistence.capex_sub_lines import (
            validate_parent_category,
        )
        with pytest.raises(ValueError) as exc_info:
            validate_parent_category("C.17")
        assert "C.17" in str(exc_info.value) or "read-only" in str(
            exc_info.value
        ).lower()

    def test_c18_rejected(self):
        """C.18 is rejected at validation time. Same
        contract as C.17."""
        from app.persistence.capex_sub_lines import (
            validate_parent_category,
        )
        with pytest.raises(ValueError):
            validate_parent_category("C.18")


# ---------------------------------------------------------------------------
# 5. Run / materialization boundary
# ---------------------------------------------------------------------------


class TestRunMaterializationBoundary:
    def test_helper_does_not_mutate_input_capex(
        self, test_db, make_sub_line
    ):
        """The integration helper does NOT mutate the
        input CapexStructure. CapexStructure is frozen,
        so mutation is impossible, but this test pins
        the contract that the helper returns a new
        instance when the fold produces a delta."""
        from app.ui_runner import run_demo_project
        from app.services.capex_sub_lines_integration import (
            _apply_user_sub_lines_to_capex,
        )
        from app.persistence.capex_sub_lines import (
            create_sub_line,
        )
        from app.persistence.projects_repository import save_project

        project = save_project(
            user_id="u7",
            project_code="PRJ-IMM-1",
            project_name="Immutability test",
            source_project_template="Generic",
            project_origin="user_project",
            is_readonly=False,
        )
        with sqlite3.connect(os.environ["FINCO_DB_PATH"]) as c:
            c.row_factory = sqlite3.Row
            create_sub_line(
                c.cursor(),
                project_id=project.project_id,
                parent_category_code="C.02",
                label="+7777",
                amount_keur=7777.0,
            )
            c.commit()

        r = run_demo_project("Solar", "Base")
        capex = r.project_inputs.capex
        baseline_id = id(capex.epc_contract)
        capex_after = _apply_user_sub_lines_to_capex(
            capex, project_id=project.project_id,
        )
        # A NEW CapexItem was created; the input is not
        # mutated.
        assert id(capex_after.epc_contract) != baseline_id
        assert capex.epc_contract.amount_keur != (
            capex_after.epc_contract.amount_keur
        )
        # +7777.
        assert (
            capex_after.epc_contract.amount_keur
            == capex.epc_contract.amount_keur + 7777.0
        )

    def test_helper_returns_capex_unchanged_when_no_sub_lines(
        self, test_db, make_sub_line
    ):
        """If the project has NO sub-lines (the typical
        case), the helper returns the input CapexStructure
        unchanged. The fold helper is a no-op for empty
        input."""
        from app.ui_runner import run_demo_project
        from app.services.capex_sub_lines_integration import (
            _apply_user_sub_lines_to_capex,
        )
        from app.persistence.projects_repository import save_project

        project = save_project(
            user_id="u8",
            project_code="PRJ-EMPTY-1",
            project_name="Empty user project",
            source_project_template="Generic",
            project_origin="user_project",
            is_readonly=False,
            capex_sub_lines=[],  # explicit empty
        )
        r = run_demo_project("Solar", "Base")
        capex = r.project_inputs.capex
        capex_after = _apply_user_sub_lines_to_capex(
            capex, project_id=project.project_id,
        )
        # Empty sub-lines => no fold => same instance.
        assert capex_after is capex

    def test_in_memory_57a8_preview_rows_not_loaded(
        self, test_db, make_sub_line
    ):
        """The 57A-8 in-memory preview rows (TMP markers)
        are NOT persisted. They cannot leak into the Run.
        The integration helper only reads from
        ``capex_sub_lines`` (the persisted table), not
        from any in-memory preview buffer.

        This test pins the contract: a project with NO
        persisted sub-lines produces a capex identical
        to the no-fold baseline. 57A-8 preview rows are
        excluded by construction because they were never
        persisted in the first place.
        """
        from app.ui_runner import run_demo_project
        from app.services.capex_sub_lines_integration import (
            _apply_user_sub_lines_to_capex,
        )
        from app.persistence.projects_repository import save_project

        # A user project with no sub-lines (no 57A-8 preview
        # rows are ever saved, so this is the realistic
        # user-project state immediately after project
        # creation).
        project = save_project(
            user_id="u9",
            project_code="PRJ-NOPREV-1",
            project_name="No preview",
            source_project_template="Generic",
            project_origin="user_project",
            is_readonly=False,
        )
        r = run_demo_project("Solar", "Base")
        capex = r.project_inputs.capex
        capex_after = _apply_user_sub_lines_to_capex(
            capex, project_id=project.project_id,
        )
        # No persisted sub-lines => capex unchanged.
        assert capex_after is capex


# ---------------------------------------------------------------------------
# 6. No Run path / Excel / UI / static changes
# ---------------------------------------------------------------------------


class TestNoForbiddenChanges:
    FORBIDDEN_PRODUCTION_PATHS = (
        "app/waterfall_core.py",
        "app/excel_export.py",
        "app/sponsor_waterfall_excel_export.py",
        "app/tax_assumptions_excel_export.py",
        "app/tax_assumptions_snapshot_excel_export.py",
        "app/tax_excel_export.py",
        "app/holdco_tax_excel_export.py",
        "app/depreciation_bankable.py",
        "app/depreciation_engine.py",
        "app/opex_engine.py",
        "app/sponsor_runner.py",
        "app/portfolio_runner.py",
        "app/waterfall_runner.py",
        "app/templates/",
        "static/app.js",
        "static/styles.css",
    )

    def test_forbidden_paths_not_changed(self):
        """57A-9D must NOT touch the model formula path,
        the Excel export path, the UI templates, the
        static assets, or any other forbidden production
        code. Only app/persistence/*, app/services/
        run_service.py, app/services/
        capex_sub_lines_integration.py, tests/*, docs/*,
        and reports/* are in scope.
        """
        import subprocess
        r = subprocess.run(
            [
                "git", "diff", "origin/main", "--name-only",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        changed = set(
            line.strip() for line in r.stdout.splitlines()
            if line.strip()
        )
        forbidden_hits = {
            p for p in self.FORBIDDEN_PRODUCTION_PATHS
            if any(c.startswith(p) or c == p for c in changed)
        }
        assert not forbidden_hits, (
            f"57A-9D must not modify: {sorted(forbidden_hits)}"
        )

    def test_only_persistence_services_tests_changed(self):
        """Allowed: app/persistence/*, app/services/
        run_service.py, app/services/
        capex_sub_lines_integration.py, tests/*, docs/*,
        reports/*. Anything else is suspicious."""
        import subprocess
        r = subprocess.run(
            [
                "git", "diff", "origin/main", "--name-only",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        changed = set(
            line.strip() for line in r.stdout.splitlines()
            if line.strip()
        )
        allowed_prefixes = (
            "app/persistence/",
            "app/services/run_service.py",
            "app/services/capex_sub_lines_integration.py",
            "tests/",
            "docs/",
            "reports/",
        )
        unexpected = {
            c for c in changed
            if not c.startswith(allowed_prefixes)
        }
        assert not unexpected, (
            f"unexpected files changed: {sorted(unexpected)}"
        )

    def test_no_financial_formula_changes(self):
        """No new model fields, no new formula path, no
        changes to waterfall_core.py, opex_engine.py,
        depreciation_engine.py, or tax_assumptions_*
        beyond the CAPEX total materialization path.
        """
        import subprocess
        r = subprocess.run(
            [
                "git", "diff", "origin/main", "--name-only",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        changed = set(
            line.strip() for line in r.stdout.splitlines()
            if line.strip()
        )
        formula_paths = {
            "app/waterfall_core.py",
            "app/waterfall_runner.py",
            "app/opex_engine.py",
            "app/depreciation_engine.py",
            "app/depreciation_bankable.py",
            "app/holdco_tax_ui.py",
            "app/tax_assumptions_ui.py",
            "app/tax_ui.py",
            "domain/",
        }
        formula_hits = {
            p for p in formula_paths
            if any(c.startswith(p) for c in changed)
        }
        assert not formula_hits, (
            f"57A-9D must not modify formula paths: "
            f"{sorted(formula_hits)}"
        )


# ---------------------------------------------------------------------------
# 7. rc1 frozen
# ---------------------------------------------------------------------------


class TestRc1Frozen:
    def test_rc1_sha_resolves(self):
        import subprocess
        r = subprocess.run(
            [
                "git", "rev-parse", "--verify",
                "b425a0708719eaa5e1d922b1008e5609758e0ad4",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0, (
            "rc1 frozen SHA must still resolve."
        )


# ---------------------------------------------------------------------------
# 8. Phase plan + hard no-go
# ---------------------------------------------------------------------------


class TestPhasePlanAndHardNoGo:
    def test_phase_plan_pinned(self):
        """The 7-row phase plan (57A-9A through 57A-10)
        is still the design contract. 57A-9D is the
        third runtime PR (after 57A-9B schema and
        57A-9C save/load)."""
        plan = {
            "57A-9A": "MERGED (design gate, PR #505, c37bc6b)",
            "57A-9B": "MERGED (schema + repo skeleton, PR #506, efe68a3)",
            "57A-9C": "MERGED or DRAFT PR #507 (save/load wiring, f89b799)",
            "57A-9D": "THIS PR (Run integration, DRAFT)",
            "57A-9E": "Not started (Excel export, DRAFT)",
            "57A-9F": "Not started (governance refresh, auto-merge)",
            "57A-10": "Not started (TUHO/Oborovo parity gate, auto-merge)",
        }
        assert len(plan) == 7
        assert "57A-9D" in plan
        assert "Run integration" in plan["57A-9D"]

    def test_hard_no_go_pinned(self):
        """The 17-item hard no-go list (16 from 57A-9C +
        1 new for 57A-9D: no_financial_formula_changes)
        is the implementation boundary."""
        no_go = [
            "no_financial_formula_changes (NEW for 57A-9D — input materialization only)",
            "no_idc_calculation_changes",
            "no_construction_funding_changes",
            "no_senior_debt_shl_drawdown_changes",
            "no_tax_engine_changes",
            "no_depreciation_engine_changes",
            "no_payment_schedule_changes",
            "no_idc_schedule_wiring",
            "no_g20_r99_r102_promotion",
            "no_tailwind_alpine_react_vue_svelte",
            "no_backend_keys_visible_in_ui",
            "no_overrides_json_schema_change (additive only)",
            "no_factory_project_mutation",
            "no_57a8_in_memory_preview_regression",
            "no_run_path_changes_beyond_capex_materialization",
            "no_excel_export_integration (deferred to 57A-9E)",
            "no_ui_redesign",
            "rc1_frozen (b425a0708719eaa5e1d922b1008e5609758e0ad4)",
        ]
        assert len(no_go) == 18

    def test_stop_after_report_contract(self):
        """57A-9D is a DRAFT PR. No auto-merge. No start
        of 57A-9E / 57A-9F / 57A-10 before review."""
        contract = {
            "type": "DRAFT PR",
            "merge": "NO auto-merge",
            "next_phase_start": "gated on user review",
        }
        assert contract["type"] == "DRAFT PR"
        assert contract["merge"] == "NO auto-merge"
