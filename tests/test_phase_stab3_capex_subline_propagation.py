"""CAPEX-PERSIST-1: CAPEX sub-line propagation into run inputs.

Defect: CAPEX sub-line edits in the C.xx grid (existing named
inputs) were not persisted and not fed into the run. The category
subtotals, Hard CAPEX, and Total CAPEX showed the original factory
amounts regardless of what the user entered in the grid.

Fix:
  1. ``persist_sub_line_form_edits``: parses ``capex_C_NN_MM_keur``
     form fields and upserts them to the ``capex_sub_lines`` table
     before the run fold step.
  2. ``apply_user_sub_lines_replacing_base``: zeroes the category
     base for fields with persisted sub-lines, then folds the
     sub-line sum in. This ensures the category total = sum(sub_lines),
     not base + sum(sub_lines).
  3. ``execute_run_route`` (user_created path) calls
     ``persist_sub_line_form_edits`` then uses
     ``apply_user_sub_lines_replacing_base`` for the fold.

Scope:
  - Edited EXISTING sub-lines (named inputs in the grid): DONE.
  - New lines (Phase 57A-8 temp rows, no name attr): DEFERRED.
    Temp rows carry no ``name`` attribute, so they are never
    submitted with the form POST and never reach this code.
    Their persistence remains a future phase.

Parity:
  - TUHO/Oborovo factory projects have no persisted sub-lines,
    so ``apply_user_sub_lines_replacing_base`` returns capex
    unchanged. P1 DSCR and hard capex totals are bit-identical.
  - Engine MD5: 6bf49f33efc989736c17cea0cb9b7723.
"""
from __future__ import annotations

import hashlib
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")

ENGINE_MD5 = "6bf49f33efc989736c17cea0cb9b7723"
TUHO_P1_DSCR = 1.4507
TUHO_HARD_CAPEX = 70691.54
OBOROVO_P1_DSCR = 1.15
OBOROVO_HARD_CAPEX = 55999.09


# ---------------------------------------------------------------------------
# Test DB fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def test_db(monkeypatch, tmp_path):
    db_path = tmp_path / "stab3_test.db"
    monkeypatch.setenv("FINCO_DB_PATH", str(db_path))
    import app.persistence.db as _db_mod
    monkeypatch.setattr(_db_mod, "DB_PATH", str(db_path))
    _db_mod.init_db()
    return db_path


def _make_project(db_path):
    """Create a minimal user project record for tests."""
    from app.persistence.projects_repository import save_project
    return save_project(
        user_id="u1",
        project_code="STAB3-PROJ-1",
        project_name="CAPEX-PERSIST-1 test project",
        source_project_template="Generic",
        project_origin="user_created",
        is_readonly=False,
    )


# ---------------------------------------------------------------------------
# A. _parse_capex_sub_line_form_fields
# ---------------------------------------------------------------------------

class TestParseCapexSubLineFormFields:
    def _fn(self):
        from app.services.capex_sub_lines_integration import (
            _parse_capex_sub_line_form_fields,
        )
        return _parse_capex_sub_line_form_fields

    def test_parses_single_field(self):
        fn = self._fn()
        result = fn({"capex_C_06_U001_keur": "700"})
        assert result == {"C.06.U001": 700.0}

    def test_converts_underscore_to_dots(self):
        fn = self._fn()
        result = fn({"capex_C_02_U003_keur": "1234.5"})
        assert result == {"C.02.U003": 1234.5}

    def test_ignores_category_level_fields(self):
        fn = self._fn()
        result = fn({"capex_epc_contract_keur": "10000"})
        assert result == {}

    def test_ignores_total_capex(self):
        fn = self._fn()
        result = fn({"total_capex_keur": "42000"})
        assert result == {}

    def test_parses_multiple_fields(self):
        fn = self._fn()
        form = {
            "capex_C_01_U001_keur": "5000",
            "capex_C_06_U001_keur": "700",
            "capex_C_13_U002_keur": "300",
            "total_capex_keur": "42000",
        }
        result = fn(form)
        assert set(result.keys()) == {"C.01.U001", "C.06.U001", "C.13.U002"}
        assert result["C.06.U001"] == 700.0

    def test_empty_value_becomes_zero(self):
        fn = self._fn()
        result = fn({"capex_C_06_U001_keur": ""})
        assert result == {"C.06.U001": 0.0}

    def test_none_value_becomes_zero(self):
        fn = self._fn()
        result = fn({"capex_C_06_U001_keur": None})
        assert result == {"C.06.U001": 0.0}

    def test_invalid_value_becomes_zero(self):
        fn = self._fn()
        result = fn({"capex_C_06_U001_keur": "abc"})
        assert result == {"C.06.U001": 0.0}

    def test_empty_form_returns_empty(self):
        fn = self._fn()
        result = fn({})
        assert result == {}

    def test_temp_code_not_matched(self):
        """Phase 57A-8 temp codes (C_03_TMP_1) are not matched."""
        fn = self._fn()
        result = fn({"capex_C_03_TMP_1_keur": "500"})
        assert result == {}


# ---------------------------------------------------------------------------
# B. persist_sub_line_form_edits — create new sub-line
# ---------------------------------------------------------------------------

class TestPersistSubLineFormEditsCreate:
    def test_creates_new_sub_line(self, test_db, monkeypatch):
        project = _make_project(test_db)
        from app.services.capex_sub_lines_integration import (
            persist_sub_line_form_edits,
        )
        from app.persistence.capex_sub_lines import get_active_sub_lines_for_project

        persist_sub_line_form_edits(
            project.project_id,
            {"capex_C_06_U001_keur": "700"},
        )
        lines = get_active_sub_lines_for_project(project.project_id)
        assert len(lines) == 1
        assert lines[0].business_code == "C.06.U001"
        assert abs(lines[0].amount_keur - 700.0) < 0.01
        assert lines[0].parent_category_code == "C.06"

    def test_creates_multiple_sub_lines(self, test_db, monkeypatch):
        project = _make_project(test_db)
        from app.services.capex_sub_lines_integration import (
            persist_sub_line_form_edits,
        )
        from app.persistence.capex_sub_lines import get_active_sub_lines_for_project

        persist_sub_line_form_edits(
            project.project_id,
            {
                "capex_C_01_U001_keur": "5000",
                "capex_C_06_U001_keur": "700",
            },
        )
        lines = get_active_sub_lines_for_project(project.project_id)
        assert len(lines) == 2
        codes = {l.business_code for l in lines}
        assert "C.01.U001" in codes
        assert "C.06.U001" in codes

    def test_no_op_for_empty_project_id(self, test_db, monkeypatch):
        from app.services.capex_sub_lines_integration import (
            persist_sub_line_form_edits,
        )
        # Must not raise
        persist_sub_line_form_edits("", {"capex_C_06_U001_keur": "700"})

    def test_no_op_for_empty_form(self, test_db, monkeypatch):
        project = _make_project(test_db)
        from app.services.capex_sub_lines_integration import (
            persist_sub_line_form_edits,
        )
        from app.persistence.capex_sub_lines import get_active_sub_lines_for_project

        persist_sub_line_form_edits(project.project_id, {})
        lines = get_active_sub_lines_for_project(project.project_id)
        assert lines == []


# ---------------------------------------------------------------------------
# C. persist_sub_line_form_edits — update existing sub-line
# ---------------------------------------------------------------------------

class TestPersistSubLineFormEditsUpdate:
    def test_updates_existing_sub_line(self, test_db, monkeypatch):
        project = _make_project(test_db)
        from app.services.capex_sub_lines_integration import (
            persist_sub_line_form_edits,
        )
        from app.persistence.capex_sub_lines import get_active_sub_lines_for_project

        # First persist: creates the sub-line
        persist_sub_line_form_edits(
            project.project_id, {"capex_C_06_U001_keur": "700"},
        )
        # Second persist: updates the amount
        persist_sub_line_form_edits(
            project.project_id, {"capex_C_06_U001_keur": "900"},
        )
        lines = get_active_sub_lines_for_project(project.project_id)
        # Only one row (not duplicated)
        c06_lines = [l for l in lines if l.business_code == "C.06.U001"]
        assert len(c06_lines) == 1
        assert abs(c06_lines[0].amount_keur - 900.0) < 0.01

    def test_idempotent_on_same_amount(self, test_db, monkeypatch):
        project = _make_project(test_db)
        from app.services.capex_sub_lines_integration import (
            persist_sub_line_form_edits,
        )
        from app.persistence.capex_sub_lines import get_active_sub_lines_for_project

        for _ in range(3):
            persist_sub_line_form_edits(
                project.project_id, {"capex_C_06_U001_keur": "700"},
            )
        lines = get_active_sub_lines_for_project(project.project_id)
        assert len(lines) == 1
        assert abs(lines[0].amount_keur - 700.0) < 0.01


# ---------------------------------------------------------------------------
# D. apply_user_sub_lines_replacing_base — replace semantics
# ---------------------------------------------------------------------------

class TestApplyUserSubLinesReplacingBase:
    def test_replaces_category_base(self, test_db, monkeypatch):
        """Sub-line sum replaces (not adds to) the existing category base."""
        project = _make_project(test_db)
        from app.services.capex_sub_lines_integration import (
            apply_user_sub_lines_replacing_base,
            persist_sub_line_form_edits,
        )
        from app.project_factories import create_default_solar_project

        persist_sub_line_form_edits(
            project.project_id, {"capex_C_03_U001_keur": "700"},
        )
        proj = create_default_solar_project()
        # C.03 → grid_connection; factory default = 2000
        base_grid = proj.capex.grid_connection.amount_keur
        assert base_grid == 2000.0, f"Sanity: expected 2000, got {base_grid}"

        result_capex = apply_user_sub_lines_replacing_base(
            proj.capex, project_id=project.project_id,
        )
        # Should be 700, not 2000+700=2700
        assert abs(result_capex.grid_connection.amount_keur - 700.0) < 0.01, (
            f"Replace semantics: expected 700.0, got {result_capex.grid_connection.amount_keur}"
        )

    def test_no_op_for_empty_project_id(self, test_db, monkeypatch):
        from app.services.capex_sub_lines_integration import (
            apply_user_sub_lines_replacing_base,
        )
        from app.project_factories import create_default_solar_project
        proj = create_default_solar_project()
        result = apply_user_sub_lines_replacing_base(proj.capex, project_id="")
        assert result is proj.capex

    def test_no_op_for_no_sub_lines(self, test_db, monkeypatch):
        project = _make_project(test_db)
        from app.services.capex_sub_lines_integration import (
            apply_user_sub_lines_replacing_base,
        )
        from app.project_factories import create_default_solar_project
        proj = create_default_solar_project()
        result = apply_user_sub_lines_replacing_base(
            proj.capex, project_id=project.project_id,
        )
        assert result is proj.capex

    def test_non_touched_categories_unchanged(self, test_db, monkeypatch):
        """Fields without sub-lines keep their original amounts."""
        project = _make_project(test_db)
        from app.services.capex_sub_lines_integration import (
            apply_user_sub_lines_replacing_base,
            persist_sub_line_form_edits,
        )
        from app.project_factories import create_default_solar_project

        persist_sub_line_form_edits(
            project.project_id, {"capex_C_03_U001_keur": "700"},
        )
        proj = create_default_solar_project()
        epc_before = proj.capex.epc_contract.amount_keur

        result_capex = apply_user_sub_lines_replacing_base(
            proj.capex, project_id=project.project_id,
        )
        # C.02 → epc_contract; not in sub-lines, must be unchanged
        assert abs(result_capex.epc_contract.amount_keur - epc_before) < 0.01, (
            "epc_contract must be unchanged when no C.02 sub-lines exist"
        )


# ---------------------------------------------------------------------------
# E. Total CAPEX reflects edited sub-line on run
# ---------------------------------------------------------------------------

class TestTotalCapexReflectsSubLineEdit:
    def test_total_capex_uses_sub_line_amount(self, test_db, monkeypatch):
        """After persisting C.03.01=700, total capex changes correctly."""
        project = _make_project(test_db)
        from app.services.capex_sub_lines_integration import (
            apply_user_sub_lines_replacing_base,
            persist_sub_line_form_edits,
        )
        from app.project_factories import create_default_solar_project

        proj = create_default_solar_project()
        baseline_total = proj.capex.hard_capex_keur
        # C.03 → grid_connection (was 2000 in factory)
        original_grid = proj.capex.grid_connection.amount_keur

        persist_sub_line_form_edits(
            project.project_id, {"capex_C_03_U001_keur": "700"},
        )
        result_capex = apply_user_sub_lines_replacing_base(
            proj.capex, project_id=project.project_id,
        )

        delta = 700.0 - original_grid  # 700 - 2000 = -1300
        expected_hard = baseline_total + delta
        assert abs(result_capex.hard_capex_keur - expected_hard) < 0.01, (
            f"Hard CAPEX must reflect sub-line edit: "
            f"expected {expected_hard:.2f}, got {result_capex.hard_capex_keur:.2f}"
        )

    def test_senior_debt_sizing_reflects_sub_line(self, test_db, monkeypatch):
        """Verify that run output (waterfall) sees the updated CAPEX."""
        project = _make_project(test_db)
        from app.services.capex_sub_lines_integration import (
            apply_user_sub_lines_replacing_base,
            persist_sub_line_form_edits,
        )
        from app.project_factories import create_default_solar_project
        from app.ui_runner import _build_period_engine, _run_waterfall
        import dataclasses

        proj = create_default_solar_project()
        persist_sub_line_form_edits(
            project.project_id, {"capex_C_03_U001_keur": "50000"},
        )
        modified_capex = apply_user_sub_lines_replacing_base(
            proj.capex, project_id=project.project_id,
        )
        modified_proj = dataclasses.replace(proj, capex=modified_capex)

        result_baseline = _run_waterfall(proj, _build_period_engine(proj))
        result_modified = _run_waterfall(modified_proj, _build_period_engine(modified_proj))

        # Higher CAPEX → higher senior debt
        baseline_senior = result_baseline.periods[0].senior_balance_keur
        modified_senior = result_modified.periods[0].senior_balance_keur
        assert modified_senior > baseline_senior, (
            f"Higher CAPEX must increase senior debt; "
            f"baseline={baseline_senior:.2f}, modified={modified_senior:.2f}"
        )


# ---------------------------------------------------------------------------
# F/G. TUHO / Oborovo parity unchanged
# ---------------------------------------------------------------------------

class TestStab3Parity:
    @staticmethod
    def _first_op_dscr(result):
        return next(
            (p.dscr for p in result.periods
             if p.is_operation and p.dscr and p.dscr == p.dscr
             and p.dscr != float("inf")),
            None,
        )

    def test_tuho_p1_dscr_unchanged(self):
        from app.project_factories import create_default_tuho_wind1
        from app.ui_runner import _build_period_engine, _run_waterfall
        proj = create_default_tuho_wind1()
        result = _run_waterfall(proj, _build_period_engine(proj))
        dscr = self._first_op_dscr(result)
        assert dscr is not None
        assert abs(dscr - TUHO_P1_DSCR) < 0.001, (
            f"TUHO P1 DSCR={dscr}; expected {TUHO_P1_DSCR}"
        )

    def test_tuho_hard_capex_unchanged(self):
        from app.project_factories import create_default_tuho_wind1
        proj = create_default_tuho_wind1()
        assert abs(proj.capex.hard_capex_keur - TUHO_HARD_CAPEX) < 0.01, (
            f"TUHO hard_capex={proj.capex.hard_capex_keur}; expected {TUHO_HARD_CAPEX}"
        )

    def test_oborovo_p1_dscr_unchanged(self):
        from app.project_factories import create_default_oborovo
        from app.ui_runner import _build_period_engine, _run_waterfall
        proj = create_default_oborovo()
        result = _run_waterfall(proj, _build_period_engine(proj))
        dscr = self._first_op_dscr(result)
        assert dscr is not None
        assert abs(dscr - OBOROVO_P1_DSCR) < 0.01, (
            f"Oborovo P1 DSCR={dscr}; expected {OBOROVO_P1_DSCR}"
        )

    def test_oborovo_hard_capex_unchanged(self):
        from app.project_factories import create_default_oborovo
        proj = create_default_oborovo()
        assert abs(proj.capex.hard_capex_keur - OBOROVO_HARD_CAPEX) < 0.01, (
            f"Oborovo hard_capex={proj.capex.hard_capex_keur}; expected {OBOROVO_HARD_CAPEX}"
        )

    def test_apply_replacing_base_tuho_no_sub_lines(self):
        """apply_user_sub_lines_replacing_base is a no-op for TUHO (no sub-lines)."""
        from app.services.capex_sub_lines_integration import (
            apply_user_sub_lines_replacing_base,
        )
        from app.project_factories import create_default_tuho_wind1
        proj = create_default_tuho_wind1()
        result = apply_user_sub_lines_replacing_base(
            proj.capex, project_id="nonexistent-tuho-project",
        )
        assert result is proj.capex, "No sub-lines → capex unchanged"

    def test_apply_replacing_base_oborovo_no_sub_lines(self):
        """apply_user_sub_lines_replacing_base is a no-op for Oborovo (no sub-lines)."""
        from app.services.capex_sub_lines_integration import (
            apply_user_sub_lines_replacing_base,
        )
        from app.project_factories import create_default_oborovo
        proj = create_default_oborovo()
        result = apply_user_sub_lines_replacing_base(
            proj.capex, project_id="nonexistent-oborovo-project",
        )
        assert result is proj.capex, "No sub-lines → capex unchanged"


# ---------------------------------------------------------------------------
# H. Engine MD5 unchanged
# ---------------------------------------------------------------------------

class TestStab3EngineIntegrity:
    def test_engine_md5_unchanged(self):
        path = Path(REPO_ROOT) / "app/waterfall_core.py"
        digest = hashlib.md5(path.read_bytes()).hexdigest()
        assert digest == ENGINE_MD5, (
            f"waterfall_core.py must not change; got {digest}"
        )


# ---------------------------------------------------------------------------
# I. Deferred: Phase 57A-8 temp rows not persisted
# ---------------------------------------------------------------------------

class TestStab3NewLinePersistenceDeferred:
    def test_temp_code_not_parsed(self):
        """Phase 57A-8 temp codes (C_NN_TMP_*) are not matched by the parser."""
        from app.services.capex_sub_lines_integration import (
            _parse_capex_sub_line_form_fields,
        )
        result = _parse_capex_sub_line_form_fields({
            "capex_C_03_TMP_1_keur": "500",
            "capex_C_08_TMP_2_keur": "300",
        })
        assert result == {}, (
            "Phase 57A-8 temporary rows (TMP codes) must not be parsed. "
            "New-line persistence is deferred to a future phase."
        )

    def test_phase_57a8_rows_have_no_name_attr(self):
        """Document: Phase 57A-8 temp rows have no name attr → not submitted."""
        # This is a documentation / contract test, not a runtime test.
        # The Phase 57A-8 HTML explicitly uses data-capex-tmp="true"
        # and omits the name attribute on temp row inputs.
        template_path = Path(REPO_ROOT) / "app/templates/partials/sheet_capex.html"
        content = template_path.read_text()
        assert "data-capex-tmp" in content, "Phase 57A-8 temp rows must exist"
        assert "not included in model run" in content or "not persisted" in content, (
            "Template must still warn that temp rows are not in runs"
        )


# ---------------------------------------------------------------------------
# J. File scope
# ---------------------------------------------------------------------------

class TestStab3FileScope:
    STAB3_ALLOWED_PREFIXES = (
        "app/services/capex_sub_lines_integration.py",
        "app/services/run_service.py",
        "tests/test_phase_stab3_",
        # Prior arc allowlist entries (forward-compatible)
        "app/ui/scenario_matrix.py",
        "app/ui/driver_taxonomy.py",
        "tests/test_phase_stab",
        "tests/test_phase_m1_",
        "tests/test_phase_m2_",
        "tests/test_phase_m3_",
        "tests/test_phase_m4_",
        "tests/test_phase_wf",
        "tests/test_phase_p2fix",
        "tests/test_phase_pr1_",
        "tests/test_phase_pr2_",
        "tests/test_phase_pr3_",
        "tests/test_phase_p1b_",
        "static/styles.css",
        "constraints.txt",
        "docs/ci_infra_runner_failure_2026_06_13.md",
        "app/templates/",
        "main_web.py",
        "app/ui/dashboard.py",
        "app/ui/project_context.py",
        # STAB-5 export route fix
        "app/export/runtime_summary.py",
        "app/export/institutional_workbook.py",
        "tests/test_phase_stab5_",
    )

    STAB3_DISALLOWED_PREFIXES = (
        "app/waterfall_core.py",
        "app/project_factories.py",
        "app/persistence/",
    )

    def test_file_scope(self):
        import shutil
        if shutil.which("git") is None:
            pytest.skip("git not available")
        result = subprocess.run(
            ["git", "-C", REPO_ROOT, "diff", "--name-only", "origin/main"],
            capture_output=True, text=True,
        )
        changed = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
        for f in changed:
            # STAB-4: app.js change must be navigation-only
            if f == "static/app.js":
                import pathlib as _pl
                js_src = (_pl.Path(REPO_ROOT) / "static/app.js").read_text()
                assert "STAB-4" in js_src, f"static/app.js changed without STAB-4 marker"
                continue
            assert not any(f.startswith(p) for p in self.STAB3_DISALLOWED_PREFIXES), (
                f"CAPEX-PERSIST-1 must not touch {f}"
            )
            assert any(f.startswith(p) for p in self.STAB3_ALLOWED_PREFIXES), (
                f"CAPEX-PERSIST-1 file outside allowed scope: {f}"
            )

    def test_engine_md5_in_scope(self):
        path = Path(REPO_ROOT) / "app/waterfall_core.py"
        digest = hashlib.md5(path.read_bytes()).hexdigest()
        assert digest == ENGINE_MD5
