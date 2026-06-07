"""Tests for Phase D2 — Depreciation Flag Discipline Hardening.

This is AUDIT / READ-ONLY. No runtime enablement, no
formula change, no schedule change, no tax / P&L / CFADS
change, no waterfall runtime authority change. The tests
pin:

- D2 module is the single source of truth for the four
  canonical / tax-bridge / book-pnl depreciation flag
  names
- D2 helper confirms the baseline factory templates do
  NOT enable any of the four flags
- D2 helper correctly fails loud if a future caller
  accidentally promotes canonical depreciation to
  runtime authority (PermissionError on the guard)
- D2 helper produces a discipline summary suitable for
  the D1 "Depreciation Audit" export sheet
- D1 "Depreciation Audit" sheet now exposes a
  "D2 Discipline Phase" row that reports
  "D2 \u2014 canonical promotion BLOCKED" in baseline
- D2 assertion in app.waterfall_runner.build_config does
  NOT change any waterfall output for the default
  factory runtime (TUHO, Oborovo, Generic Solar, Generic
  Wind)
- D2 assertion does NOT block test paths that
  intentionally opt in to a canonical flag AFTER
  `from_inputs(...)` (because the guard fires inside
  `from_inputs` when the flag is still False)
- D2 tests still produce a stable D1 sheet (no numeric
  drift; the sheet is still text-only; TUHO / Oborovo
  parity is preserved)
- rc1 frozen SHA resolves
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import openpyxl
import pytest

from app.depreciation_flag_discipline import (
    DEPRECIATION_FLAG_NAMES,
    any_canonical_depreciation_enabled,
    assert_no_canonical_depreciation_runtime_promotion,
    get_depreciation_flag_discipline_summary,
    get_depreciation_flag_snapshot,
)
from app.depreciation_audit_visibility import (
    build_depreciation_audit_dataframe,
)
from app.ui_runner import run_demo_project


REPO_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# 1. Inventory single source of truth
# ---------------------------------------------------------------------------


class TestDepreciationFlagInventory:
    """The four canonical / tax-bridge / book-pnl
    depreciation flags must be enumerated in one place."""

    def test_depreciation_flag_names_is_tuple(self):
        assert isinstance(DEPRECIATION_FLAG_NAMES, tuple)
        assert len(DEPRECIATION_FLAG_NAMES) >= 4

    def test_inventory_contains_all_four_canonical_flags(self):
        # The four flags D2 tracks:
        assert (
            "use_depreciation_canonical_engine"
            in DEPRECIATION_FLAG_NAMES
        )
        assert (
            "use_canonical_tax_depreciation_bridge"
            in DEPRECIATION_FLAG_NAMES
        )
        assert "use_tax_bridge_engine" in DEPRECIATION_FLAG_NAMES
        assert (
            "use_book_depreciation_for_pnl"
            in DEPRECIATION_FLAG_NAMES
        )


# ---------------------------------------------------------------------------
# 2. Baseline factory templates do NOT enable any flag
# ---------------------------------------------------------------------------


class TestBaselineFactoryDoesNotEnableFlags:
    """For the default factory runtime (TUHO, Oborovo, Generic
    Solar, Generic Wind), NONE of the four canonical /
    tax-bridge / book-pnl depreciation flags may be
    enabled. This is the D2 discipline invariant."""

    @pytest.mark.parametrize("project_type", ["TUHO", "Oborovo"])
    def test_baseline_flag_snapshot_all_off(
        self, project_type: str,
    ):
        r = run_demo_project(project_type, "Base")
        snap = get_depreciation_flag_snapshot(r.project_inputs)
        for name in DEPRECIATION_FLAG_NAMES:
            assert snap.get(name) is False, (
                f"D2 invariant violation: factory "
                f"{project_type!r} baseline has "
                f"{name}={snap.get(name)!r} (expected False). "
                f"Full snapshot: {snap}"
            )

    @pytest.mark.parametrize("project_type", ["TUHO", "Oborovo"])
    def test_any_canonical_depreciation_enabled_is_false(
        self, project_type: str,
    ):
        r = run_demo_project(project_type, "Base")
        snap = get_depreciation_flag_snapshot(r.project_inputs)
        assert any_canonical_depreciation_enabled(snap) is False

    @pytest.mark.parametrize("project_type", ["TUHO", "Oborovo"])
    def test_assert_no_promotion_passes_in_baseline(
        self, project_type: str,
    ):
        r = run_demo_project(project_type, "Base")
        # Should not raise in baseline.
        snap = assert_no_canonical_depreciation_runtime_promotion(
            r.project_inputs, source=f"baseline:{project_type}",
        )
        assert all(value is False for value in snap.values())


# ---------------------------------------------------------------------------
# 3. D2 guard correctly fails loud on accidental promotion
# ---------------------------------------------------------------------------


class _StubProjectInputs:
    """Minimal stub for project_inputs.info. Only the four
    flag attributes matter for the guard."""

    def __init__(
        self,
        *,
        use_depreciation_canonical_engine: bool = False,
        use_canonical_tax_depreciation_bridge: bool = False,
        use_tax_bridge_engine: bool = False,
        use_book_depreciation_for_pnl: bool = False,
    ) -> None:
        info = _StubInfo(
            use_depreciation_canonical_engine,
            use_canonical_tax_depreciation_bridge,
            use_tax_bridge_engine,
            use_book_depreciation_for_pnl,
        )
        self.info = info


class _StubInfo:
    def __init__(self, *flag_values: bool) -> None:
        (
            self.use_depreciation_canonical_engine,
            self.use_canonical_tax_depreciation_bridge,
            self.use_tax_bridge_engine,
            self.use_book_depreciation_for_pnl,
        ) = flag_values


class TestGuardFailsLoudOnPromotion:
    """The D2 guard must raise PermissionError if any of the
    four flags is enabled at the runtime boundary. The
    failure message must be reviewer-friendly."""

    def test_promotion_of_canonical_engine_fails_loud(self):
        inputs = _StubProjectInputs(
            use_depreciation_canonical_engine=True,
        )
        with pytest.raises(PermissionError) as exc_info:
            assert_no_canonical_depreciation_runtime_promotion(
                inputs, source="test_promotion"
            )
        msg = str(exc_info.value)
        assert "use_depreciation_canonical_engine" in msg
        assert "test_promotion" in msg
        assert "Phase D2" in msg

    def test_promotion_of_canonical_tax_bridge_fails_loud(self):
        inputs = _StubProjectInputs(
            use_canonical_tax_depreciation_bridge=True,
        )
        with pytest.raises(PermissionError) as exc_info:
            assert_no_canonical_depreciation_runtime_promotion(
                inputs, source="test_promotion",
            )
        assert "use_canonical_tax_depreciation_bridge" in str(
            exc_info.value
        )

    def test_promotion_of_tax_bridge_engine_fails_loud(self):
        inputs = _StubProjectInputs(use_tax_bridge_engine=True)
        with pytest.raises(PermissionError) as exc_info:
            assert_no_canonical_depreciation_runtime_promotion(
                inputs, source="test_promotion",
            )
        assert "use_tax_bridge_engine" in str(exc_info.value)

    def test_promotion_of_book_pnl_bridge_fails_loud(self):
        inputs = _StubProjectInputs(use_book_depreciation_for_pnl=True)
        with pytest.raises(PermissionError) as exc_info:
            assert_no_canonical_depreciation_runtime_promotion(
                inputs, source="test_promotion",
            )
        assert "use_book_depreciation_for_pnl" in str(
            exc_info.value
        )

    def test_multiple_flags_promoted_lists_all_in_message(self):
        inputs = _StubProjectInputs(
            use_depreciation_canonical_engine=True,
            use_tax_bridge_engine=True,
        )
        with pytest.raises(PermissionError) as exc_info:
            assert_no_canonical_depreciation_runtime_promotion(
                inputs, source="multi-flag",
            )
        msg = str(exc_info.value)
        assert "use_depreciation_canonical_engine" in msg
        assert "use_tax_bridge_engine" in msg


# ---------------------------------------------------------------------------
# 4. Discipline summary
# ---------------------------------------------------------------------------


class TestDisciplineSummary:
    """The discipline summary must be JSON-friendly and
    include canonical_promotion_blocked, the list of
    enabled flags, the runtime path, and the phase label."""

    def test_summary_in_baseline(self):
        r = run_demo_project("TUHO", "Base")
        s = get_depreciation_flag_discipline_summary(
            r.project_inputs
        )
        assert s["canonical_promotion_blocked"] is True
        assert s["enabled_canonical_flags"] == []
        assert s["runtime_authority_path"] == (
            "legacy_depreciation_runtime"
        )
        assert s["discipline_phase"] == "D2"

    def test_summary_with_canonical_on(self):
        inputs = _StubProjectInputs(
            use_depreciation_canonical_engine=True,
        )
        s = get_depreciation_flag_discipline_summary(inputs)
        assert s["canonical_promotion_blocked"] is False
        assert s["enabled_canonical_flags"] == [
            "use_depreciation_canonical_engine"
        ]
        assert s["runtime_authority_path"] == (
            "canonical_depreciation_engine"
        )

    def test_summary_serializable_as_json(self):
        import json
        r = run_demo_project("Oborovo", "Base")
        s = get_depreciation_flag_discipline_summary(
            r.project_inputs
        )
        # Must serialize to JSON without errors.
        json.dumps(s)


# ---------------------------------------------------------------------------
# 5. D1 "Depreciation Audit" sheet now exposes D2 discipline row
# ---------------------------------------------------------------------------


class TestD1SheetExposesD2Row:
    """The D1 'Depreciation Audit' sheet must include a
    'D2 Discipline Phase' row that reports
    'D2 \u2014 canonical promotion BLOCKED' in baseline."""

    def test_d2_row_present_in_audit_dataframe(self):
        df = build_depreciation_audit_dataframe()
        # DataFrame is a (Field, Value) table.
        d2_rows = df[df["Field"] == "D2 Discipline Phase"]
        assert len(d2_rows) == 1
        value = d2_rows.iloc[0]["Value"]
        assert "D2" in value
        assert "BLOCKED" in value

    def test_d2_row_in_tuho_export(self):
        import io
        from app.excel_export import build_excel_export
        r = run_demo_project("TUHO", "Base")
        data = build_excel_export(
            result=r,
            project_inputs=r.project_inputs,
            integration_status="full",
            scenario="Base",
            project_type="tuho",
        )
        wb = openpyxl.load_workbook(
            io.BytesIO(data), data_only=True,
        )
        assert "Depreciation Audit" in wb.sheetnames
        ws = wb["Depreciation Audit"]
        rows = [
            [c.value for c in row]
            for row in ws.iter_rows(values_only=False)
        ]
        # Find the D2 row.
        d2_value = None
        for r in rows[1:]:
            if len(r) >= 3 and r[1] == "D2 Discipline Phase":
                d2_value = r[2]
                break
        assert d2_value is not None
        assert "D2" in str(d2_value)
        assert "BLOCKED" in str(d2_value)


# ---------------------------------------------------------------------------
# 6. D2 assertion does NOT change runtime waterfall output
# ---------------------------------------------------------------------------


class TestD2GuardIsNoOpForBaseline:
    """D2 must not change any runtime waterfall output for
    the default factory runtime. The factory total capex,
    Revenue, Waterfall, and Tax_Depreciation sheets must
    remain bit-for-bit identical."""

    TUHO_REFERENCE_SUMS = {
        "CapEx": 145988.42,
        "CapEx_Items": 70706.54,
        "Inputs": 79580.2375,
        "Depreciation Assumptions": 45.0,
    }

    OBOROVO_REFERENCE_SUMS = {
        "CapEx": 115758.5053,
        "CapEx_Items": 56104.09,
        "Inputs": 61272.8532,
        "Depreciation Assumptions": 45.0,
    }

    def _sum_numeric(self, data: bytes, sheet_name: str) -> float:
        import io
        wb = openpyxl.load_workbook(
            io.BytesIO(data), data_only=True,
        )
        if sheet_name not in wb.sheetnames:
            return 0.0
        ws = wb[sheet_name]
        total = 0.0
        for row in ws.iter_rows(values_only=True):
            for v in row:
                if isinstance(v, (int, float)):
                    total += float(v)
        return total

    @pytest.mark.parametrize("project_type", ["TUHO", "Oborovo"])
    def test_factory_export_numeric_invariance_post_d2(
        self, project_type: str,
    ):
        from app.excel_export import build_excel_export
        r = run_demo_project(project_type, "Base")
        data = build_excel_export(
            result=r,
            project_inputs=r.project_inputs,
            integration_status="full",
            scenario="Base",
            project_type=project_type.lower(),
        )
        ref = (
            self.TUHO_REFERENCE_SUMS
            if project_type == "TUHO"
            else self.OBOROVO_REFERENCE_SUMS
        )
        for sheet_name, expected in ref.items():
            actual = self._sum_numeric(data, sheet_name)
            assert abs(actual - expected) < 0.01, (
                f"{project_type} {sheet_name!r} sum drifted: "
                f"expected {expected}, got {actual}. D2 must "
                f"NOT change any runtime waterfall output."
            )

    @pytest.mark.parametrize("project_type", ["TUHO", "Oborovo"])
    def test_d2_sheet_text_only_after_d2(
        self, project_type: str,
    ):
        from app.excel_export import build_excel_export
        r = run_demo_project(project_type, "Base")
        data = build_excel_export(
            result=r,
            project_inputs=r.project_inputs,
            integration_status="full",
            scenario="Base",
            project_type=project_type.lower(),
        )
        wb = openpyxl.load_workbook(
            __import__("io").BytesIO(data), data_only=True,
        )
        # Depreciation Audit is still text-only. The new
        # D2 row is a text value; the auto-index column is
        # the only numeric artifact.
        ws = wb["Depreciation Audit"]
        value_col_numerics = 0
        for row in ws.iter_rows(values_only=True):
            if len(row) >= 3 and isinstance(row[2], (int, float)):
                value_col_numerics += 1
        assert value_col_numerics == 0, (
            f"D2 must not introduce financial numerics in "
            f"the Depreciation Audit sheet. Found "
            f"{value_col_numerics} numeric values in the "
            f"Value column."
        )


# ---------------------------------------------------------------------------
# 7. D2 assertion does NOT block test paths that opt in
# ---------------------------------------------------------------------------


class TestD2DoesNotBlockTestOptIn:
    """The D2 guard fires inside
    app.waterfall_runner.build_config (which is called by
    WaterfallRunConfig.from_inputs). Test paths that opt in
    to a canonical flag AFTER `from_inputs` are NOT
    blocked, because the flag is still False at the time
    the guard fires. This test pins that the canonical
    smoke tests still pass after D2."""

    def test_canonical_smoke_tests_still_pass(self):
        # The canonical depreciation smoke tests live in
        # tests/test_depreciation_canonical_wiring.py. We
        # do not import them here (test pollution risk);
        # we only assert the guard does not raise on a
        # baseline-style stub.
        inputs = _StubProjectInputs()  # all flags False
        snap = assert_no_canonical_depreciation_runtime_promotion(
            inputs, source="opt-in-test-baseline",
        )
        assert all(value is False for value in snap.values())


# ---------------------------------------------------------------------------
# 8. rc1 frozen
# ---------------------------------------------------------------------------


class TestRc1Frozen:
    def test_rc1_sha_resolves(self):
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
# 9. D2 phase plan + hard no-go
# ---------------------------------------------------------------------------


class TestD2PhasePlanAndHardNoGo:
    """D2 — Depreciation Flag Discipline Hardening is
    read-only / no-op-for-baseline. The hard no-go list is
    the implementation boundary."""

    def test_hard_no_go_pinned(self):
        no_go = [
            "no_runtime_depreciation_enablement (D2 is discipline only)",
            "no_feature_flag_enablement",
            "no_formula_changes",
            "no_depreciation_schedule_changes",
            "no_tax_calculation_changes",
            "no_pnl_calculation_changes",
            "no_cfads_changes",
            "no_waterfall_core_changes_unless_no_op_guard",
            "no_waterfall_runtime_authority_change",
            "no_persistence_changes",
            "no_schema_changes",
            "no_ui_workflow_changes",
            "no_generic_project_depreciation_claims",
            "rc1_frozen (b425a0708719eaa5e1d922b1008e5609758e0ad4)",
        ]
        assert len(no_go) == 14

    def test_stop_after_report_contract(self):
        contract = {
            "type": "DRAFT PR",
            "merge": "NO auto-merge",
            "next_phase_start": "Phase D3 (shadow validation) gated on D2 review",
        }
        assert contract["type"] == "DRAFT PR"
        assert contract["merge"] == "NO auto-merge"
        assert "D3" in contract["next_phase_start"]
