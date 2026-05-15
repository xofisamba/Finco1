"""Parity tests for TUHO Wind 1 OPEX template.

These tests verify that build_tuho_opex_template() produces a template
that exactly matches the Excel annual OPEX totals from tuho_excel_1.xlsm
(OpEx sheet row 105, cols F–AE = Y1–Y30).

This fixture is OFFLINE ONLY — not connected to runtime run_waterfall,
TUHO factory, or any other model component.

Tolerance: ±0.01 kEUR per year, ±0.1 kEUR for 30-year total.
"""
from __future__ import annotations

import pytest

from domain.opex.engine import compute_annual_opex
from domain.opex.line_items import OpexBasis
from domain.opex.templates.tuho import build_tuho_opex_template


# ── Excel annual OPEX totals (row 105, cols F–AE) ──────────────────────────
EXCEL_ANNUAL = [
    1998.05, 2029.83, 2147.06, 2180.13, 2213.86,   # Y1–Y5
    2378.01, 2413.10, 2448.90, 2485.41, 2522.65,   # Y6–Y10
    2603.04, 2641.79, 2681.31, 2721.62, 2734.77,   # Y11–Y15
    2827.03, 2869.24, 2912.29, 2956.21, 3001.00,   # Y16–Y20
    3131.49, 3178.09, 3225.63, 3274.11, 3323.57,   # Y21–Y25
    3450.33, 3501.79, 3554.27, 3607.80, 3662.40,   # Y26–Y30
]
EXCEL_30YR_TOTAL = 84_674.78
EXCEL_Y1_Y30_SAMPLE = {1: 1998.05, 2: 2029.83, 7: 2413.10,
                         10: 2522.65, 13: 2681.31, 20: 3001.00, 30: 3662.40}

B02_EXPLICIT_Y1_Y30 = [
    385.6, 385.6,        # Y1–Y2
    465.6, 465.6, 465.6, # Y3–Y5
    588.0, 588.0, 588.0, 588.0, 588.0,  # Y6–Y10
    628.0, 628.0, 628.0, 628.0, 628.0,   # Y11–Y15
    676.0, 676.0, 676.0, 676.0, 676.0,   # Y16–Y20
    756.0, 756.0, 756.0, 756.0, 756.0,   # Y21–Y25
    828.0, 828.0, 828.0, 828.0, 828.0,   # Y26–Y30
]

B11_ACTIVE_FLAGS = (1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,   # Y1–Y14
                    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)  # Y15–Y30

TOL_YEAR = 0.01   # ±0.01 kEUR per year
TOL_TOTAL = 0.1  # ±0.1 kEUR for 30-year total


class TestTuhoOpexTemplateBuilds:
    """Task B.1 — template builder smoke test."""

    def test_returns_list(self):
        groups = build_tuho_opex_template()
        assert isinstance(groups, list)

    def test_contains_b01_b13(self):
        groups = build_tuho_opex_template()
        codes = {g.code for g in groups}
        assert codes >= {"B.01", "B.02", "B.03", "B.04", "B.05",
                         "B.06", "B.07", "B.08", "B.09", "B.10",
                         "B.11", "B.12", "B.13"}

    def test_b01_six_items(self):
        groups = build_tuho_opex_template()
        b01 = next(g for g in groups if g.code == "B.01")
        assert len(b01.items) == 6

    def test_b13_single_pct_item(self):
        groups = build_tuho_opex_template()
        b13 = next(g for g in groups if g.code == "B.13")
        assert len(b13.items) == 1
        assert b13.items[0].basis == OpexBasis.PCT_OF_SELECTED_GROUPS

    def test_b02_ten_items(self):
        groups = build_tuho_opex_template()
        b02 = next(g for g in groups if g.code == "B.02")
        assert len(b02.items) == 10

    def test_b11_two_items(self):
        groups = build_tuho_opex_template()
        b11 = next(g for g in groups if g.code == "B.11")
        assert len(b11.items) == 2


class TestTuhoOpexAnnualParityAllYears:
    """Task B.2 — all 30 years match Excel exactly."""

    def test_all_30_years(self):
        groups = build_tuho_opex_template()
        result = compute_annual_opex(groups, years=30)

        failures = []
        for y_idx in range(30):
            year = y_idx + 1
            engine_val = result.total_for_year(year)
            excel_val = EXCEL_ANNUAL[y_idx]
            delta = abs(engine_val - excel_val)
            if delta > TOL_YEAR:
                failures.append(f"Y{year}: engine={engine_val:.4f}, "
                                f"excel={excel_val:.4f}, Δ={delta:.4f}")

        assert not failures, (
            f"Years exceeding ±{TOL_YEAR} kEUR tolerance:\n" +
            "\n".join(failures)
        )


class TestTuhoOpex30YrTotalMatchesExcel:
    """Task B.3 — 30-year total matches."""

    def test_30yr_total(self):
        groups = build_tuho_opex_template()
        result = compute_annual_opex(groups, years=30)
        engine_total = sum(result.total_for_year(y) for y in range(1, 31))
        delta = abs(engine_total - EXCEL_30YR_TOTAL)
        assert delta <= TOL_TOTAL, (
            f"30-year total mismatch: engine={engine_total:.2f}, "
            f"excel={EXCEL_30YR_TOTAL:.2f}, Δ={delta:.2f}"
        )


class TestTuhoOpexSelectedYearsMatchExcel:
    """Task B.4 — key years match."""

    @pytest.mark.parametrize("year,expected", [
        (1,  1998.05),
        (2,  2029.83),
        (7,  2413.10),
        (10, 2522.65),
        (13, 2681.31),
        (20, 3001.00),
        (30, 3662.40),
    ])
    def test_selected_year(self, year, expected):
        groups = build_tuho_opex_template()
        result = compute_annual_opex(groups, years=30)
        engine_val = result.total_for_year(year)
        delta = abs(engine_val - expected)
        assert delta <= TOL_YEAR, (
            f"Y{year}: engine={engine_val:.4f}, excel={expected:.4f}, Δ={delta:.4f}"
        )


class TestTuhoOpexB02ExplicitSchedule:
    """Task B.5 — B.02.1 explicit schedule, no inflation."""

    def test_b02_explicit_basis(self):
        groups = build_tuho_opex_template()
        b02 = next(g for g in groups if g.code == "B.02")
        b021 = next(i for i in b02.items if i.code == "B.02.1")
        assert b021.basis == OpexBasis.EXPLICIT_SCHEDULE

    def test_b02_explicit_values_all_30_years(self):
        groups = build_tuho_opex_template()
        result = compute_annual_opex(groups, years=30)

        failures = []
        for y_idx in range(30):
            year = y_idx + 1
            ir = result.item_result(year, "B.02", "B.02.1")
            expected = B02_EXPLICIT_Y1_Y30[y_idx]
            delta = abs(ir.total_keur - expected)
            if delta > TOL_YEAR:
                failures.append(f"Y{year}: got={ir.total_keur:.4f}, "
                                f"expected={expected:.4f}")

        assert not failures, (
            "B.02.1 explicit schedule mismatches:\n" + "\n".join(failures)
        )

    def test_b02_group_inflation_zero(self):
        """Group inflation_rate=0 ensures no double-inflation of explicit item."""
        groups = build_tuho_opex_template()
        b02 = next(g for g in groups if g.code == "B.02")
        assert b02.inflation_rate == 0.0


class TestTuhoOpexB11ActiveFlags:
    """Task B.6 — B.11 active flags: Y1–Y14 active, Y15–Y30 inactive."""

    def test_b11_flags_30_elements(self):
        groups = build_tuho_opex_template()
        b11 = next(g for g in groups if g.code == "B.11")
        for item in b11.items:
            assert len(item.active_flags) == 30

    def test_b11_flags_y1_y14_true(self):
        groups = build_tuho_opex_template()
        b11 = next(g for g in groups if g.code == "B.11")
        for item in b11.items:
            for y in range(1, 15):
                assert item.active_flags[y - 1] == 1, f"Y{y} should be active"

    def test_b11_flags_y15_y30_false(self):
        groups = build_tuho_opex_template()
        b11 = next(g for g in groups if g.code == "B.11")
        for item in b11.items:
            for y in range(15, 31):
                assert item.active_flags[y - 1] == 0, f"Y{y} should be inactive"

    def test_b11_y15_plus_zero(self):
        groups = build_tuho_opex_template()
        result = compute_annual_opex(groups, years=30)
        for year in range(15, 31):
            gr = result.group_result(year, "B.11")
            assert gr.group_total_keur == 0.0, f"Y{year} should be 0"


class TestTuhoOpexB13Contingency:
    """Task B.7 — B.13 = 6% of B.01–B.12, no self-reference, order-independent."""

    def test_b13_equals_6pct_of_selected(self):
        groups = build_tuho_opex_template()
        result = compute_annual_opex(groups, years=30)

        for y in [1, 7, 15, 20, 30]:
            sum_b01_b12 = sum(
                result.group_result(y, code).group_total_keur
                for code in ("B.01", "B.02", "B.03", "B.04", "B.05", "B.06",
                             "B.07", "B.08", "B.09", "B.10", "B.11", "B.12")
            )
            expected_b13 = sum_b01_b12 * 0.06
            actual_b13 = result.group_result(y, "B.13").group_total_keur
            delta = abs(actual_b13 - expected_b13)
            assert delta <= TOL_YEAR, (
                f"Y{y}: B.13={actual_b13:.4f}, "
                f"6%×Σ(B.01–B.12)={expected_b13:.4f}, Δ={delta:.4f}"
            )

    def test_b13_no_self_reference(self):
        groups = build_tuho_opex_template()
        b13 = next(g for g in groups if g.code == "B.13")
        selected = b13.items[0].selected_group_codes
        assert "B.13" not in selected, "B.13 must not reference itself"

    def test_b13_order_independent(self):
        """B.13 computed correctly regardless of group list order."""
        import copy
        groups = build_tuho_opex_template()
        result_normal = compute_annual_opex(groups, years=1)

        # Shuffle: B.13 first
        groups_shuffled = [next(g for g in groups if g.code == "B.13")] + [
            g for g in groups if g.code != "B.13"
        ]
        result_shuffled = compute_annual_opex(groups_shuffled, years=1)

        normal_b13 = result_normal.group_result(1, "B.13").group_total_keur
        shuffled_b13 = result_shuffled.group_result(1, "B.13").group_total_keur
        assert abs(normal_b13 - shuffled_b13) <= TOL_YEAR, (
            f"Order dependency: normal={normal_b13:.4f}, "
            f"shuffled={shuffled_b13:.4f}"
        )


class TestTuhoOpexNoRuntimeChange:
    """Task B.8 — confirm no runtime wiring."""

    def test_template_not_used_by_run_waterfall(self):
        """Verify build_tuho_opex_template is not called from waterfall."""
        import os, glob
        waterfall_files = (
            glob.glob("domain/waterfall/*.py") +
            glob.glob("domain/financing/*.py") +
            ["run_waterfall.py"] if os.path.exists("run_waterfall.py") else []
        )
        for path in waterfall_files:
            with open(path) as f:
                content = f.read()
            assert "build_tuho_opex_template" not in content, (
                f"Template builder referenced in {path}"
            )

    def test_existing_opex_engine_unchanged(self):
        """Smoke test: existing engine still works."""
        from domain.opex.line_items import OpexGroup, OpexItem, OpexBasis
        g = OpexGroup(code="G1", name="G1", inflation_rate=0.0, wth_rate=0.0,
                      items=(OpexItem(code="I1", name="I1", budget_keur=100.0,
                                      basis=OpexBasis.FIXED_ANNUAL_KEUR,
                                      group_code="G1", inflation_rate=None,
                                      wth_rate=0.0, active_flags=(),
                                      explicit_schedule_keur=[],
                                      manual_overrides=(), step_changes=(),
                                      selected_group_codes=(), notes=""),),
                      order=0, editable=True, contingency_pct=0.0)
        result = compute_annual_opex([g], years=1)
        assert result.total_for_year(1) == 100.0


class TestTuhoOpexB07StandardPattern:
    """Confirm B.07 uses standard (F2-1) pattern: inflation_start_exponent=0."""

    def test_b07_inflation_start_exponent_zero(self):
        groups = build_tuho_opex_template()
        b07 = next(g for g in groups if g.code == "B.07")
        for item in b07.items:
            assert item.inflation_start_exponent == 0

    def test_b07_y1_y3_values(self):
        """B.07 Y1=248.88, Y2=253.86, Y3=258.93 (standard pattern)."""
        groups = build_tuho_opex_template()
        result = compute_annual_opex(groups, years=3)

        expected = {1: 248.88, 2: 253.8576, 3: 258.934752}
        for y, exp in expected.items():
            ir = result.item_result(y, "B.07", f"B.07.{y}")
            # Get any B.07 item (there are 2)
            b07 = next(g for g in groups if g.code == "B.07")
            actual = sum(
                result.item_result(y, "B.07", i.code).total_keur
                for i in b07.items
            )
            delta = abs(actual - exp)
            assert delta <= TOL_YEAR, (
                f"Y{y}: expected={exp:.4f}, got={actual:.4f}, Δ={delta:.4f}"
            )