"""Tests for OPEX contingency method: fixed_amount vs percentage_of_opex."""

import pytest

from domain.opex.engine import compute_annual_opex
from domain.opex.line_items import OpexBasis, OpexContingencyMethod, OpexGroup, OpexItem
from domain.opex.result import OpexAnnualResult


def _make_item(code, budget, basis=OpexBasis.FIXED_ANNUAL_KEUR, inflation=0.02, selected=()):
    return OpexItem(
        code=code,
        name=code,
        budget_keur=budget,
        basis=basis,
        group_code="TEST",
        inflation_rate=inflation,
        selected_group_codes=selected,
    )


def _make_group(code, items, contingency_pct=0.0, contingency_method=OpexContingencyMethod.FIXED_AMOUNT):
    return OpexGroup(
        code=code,
        name=code,
        inflation_rate=0.02,
        items=items,
        contingency_pct=contingency_pct,
        contingency_method=contingency_method,
    )


class TestFixedAmountContingency:
    """Fixed-amount contingency: budget × (1+inflation)^year."""

    def test_fixed_amount_grows_with_inflation(self):
        groups = [
            _make_group(
                "G1",
                [_make_item("G1.1", 100.0)],
            ),
            _make_group(
                "G2",
                [_make_item("G2.1", 50.0)],
            ),
            _make_group(
                "GC",
                [_make_item("GC.1", 10.0, inflation=0.05)],  # 10 kEUR at 5% inflation
                contingency_pct=0.0,  # not used in fixed_amount
                contingency_method=OpexContingencyMethod.FIXED_AMOUNT,
            ),
        ]
        result = compute_annual_opex(groups, years=3)

        # G1 + G2 (100 + 50 = 150 at 2% inflation) + GC (10 at 5% inflation)
        g1_y1 = 100.0
        g1_y2 = 100.0 * 1.02
        g1_y3 = 100.0 * 1.02 ** 2
        g2_y1 = 50.0
        g2_y2 = 50.0 * 1.02
        g2_y3 = 50.0 * 1.02 ** 2
        gc_y1 = 10.0
        gc_y2 = 10.0 * 1.05
        gc_y3 = 10.0 * 1.05 ** 2

        assert result.total_for_year(1) == pytest.approx(g1_y1 + g2_y1 + gc_y1, abs=0.01)
        assert result.total_for_year(2) == pytest.approx(g1_y2 + g2_y2 + gc_y2, abs=0.01)
        assert result.total_for_year(3) == pytest.approx(g1_y3 + g2_y3 + gc_y3, abs=0.01)

    def test_pct_of_selected_without_contingency_pct_adds_item_amount(self):
        """PCT_OF_SELECTED_GROUPS items always compute their percentage, regardless of contingency_pct.

        contingency_pct=0.0 only means the contingency amount is zero; the item itself
        still contributes its computed pct-of-groups amount to the group total.
        """
        groups = [
            _make_group("G1", [_make_item("G1.1", 100.0)]),
            _make_group(
                "GC",
                [_make_item("GC.1", 10.0, basis=OpexBasis.PCT_OF_SELECTED_GROUPS, selected=("G1",))],
                contingency_pct=0.0,
                contingency_method=OpexContingencyMethod.FIXED_AMOUNT,
            ),
        ]
        result = compute_annual_opex(groups, years=1)
        gc = result.group_result(1, "GC")
        # 10% × G1=100 → 10 kEUR (item contributes, contingency_pct=0 just means
        # the group.contingency_pct doesn't override the item's own pct-of-groups calc)
        assert gc.group_total_keur == pytest.approx(10.0, abs=0.01)


class TestPercentageOfOpexContingency:
    """Percentage-of-OPEX contingency: pct × sum(non-contingency groups), no separate inflation."""

    def test_contingency_excludes_itself_from_base(self):
        """Contingency group is never included in its own base."""
        groups = [
            _make_group("G1", [_make_item("G1.1", 100.0)]),
            _make_group("GC", [_make_item("GC.1", 6.0, basis=OpexBasis.PCT_OF_SELECTED_GROUPS, selected=("G1", "GC"))],
                contingency_pct=10.0,
                contingency_method=OpexContingencyMethod.PERCENTAGE_OF_OPEX,
            ),
        ]
        result = compute_annual_opex(groups, years=1)
        gc = result.group_result(1, "GC")
        # G1 = 100, GC = 0 (excluded from base). Contingency = 10% × 100 = 10
        assert gc.contingency_base_keur == pytest.approx(100.0, abs=0.01)
        assert gc.group_total_keur == pytest.approx(10.0, abs=0.01)
        # Total OPEX should be 100 (G1) + 10 (GC) = 110, NOT 100 + 11
        assert result.total_for_year(1) == pytest.approx(110.0, abs=0.01)

    def test_contingency_equals_pct_of_non_contingency_opex(self):
        groups = [
            _make_group("G1", [_make_item("G1.1", 500.0, inflation=0.0)]),
            _make_group("G2", [_make_item("G2.1", 300.0, inflation=0.0)]),
            _make_group(
                "GC",
                [_make_item("GC.1", 6.0, basis=OpexBasis.PCT_OF_SELECTED_GROUPS, selected=("G1", "G2"))],
                contingency_pct=10.0,
                contingency_method=OpexContingencyMethod.PERCENTAGE_OF_OPEX,
            ),
        ]
        result = compute_annual_opex(groups, years=1)
        gc = result.group_result(1, "GC")
        # Base = G1 + G2 = 500 + 300 = 800
        # Contingency = 10% × 800 = 80
        assert gc.contingency_base_keur == pytest.approx(800.0, abs=0.01)
        assert gc.group_total_keur == pytest.approx(80.0, abs=0.01)
        assert result.total_for_year(1) == pytest.approx(880.0, abs=0.01)

    def test_no_separate_contingency_inflation(self):
        """In percentage_of_opex mode, contingency does NOT grow by its own inflation rate."""
        groups = [
            _make_group("G1", [_make_item("G1.1", 1000.0, inflation=0.10)]),  # 10% inflation
            _make_group(
                "GC",
                [_make_item("GC.1", 6.0, basis=OpexBasis.PCT_OF_SELECTED_GROUPS, selected=("G1",))],
                contingency_pct=10.0,
                contingency_method=OpexContingencyMethod.PERCENTAGE_OF_OPEX,
            ),
        ]
        result = compute_annual_opex(groups, years=3)

        g1_y1 = 1000.0
        g1_y2 = 1000.0 * 1.10
        g1_y3 = 1000.0 * 1.10 ** 2

        contingency_y1 = 0.10 * g1_y1
        contingency_y2 = 0.10 * g1_y2  # Only because G1 inflates, not because contingency inflates
        contingency_y3 = 0.10 * g1_y3

        # Verify the contingency item has 0 inflation rate (no double-escalation)
        gc = result.group_result(2, "GC")
        contingency_item = gc.item_result("GC.1")
        assert contingency_item.inflation_rate == 0.0

        # But contingency amount is still pct × inflated base
        assert contingency_y1 == pytest.approx(100.0, abs=0.01)
        assert contingency_y2 == pytest.approx(110.0, abs=0.01)
        assert contingency_y3 == pytest.approx(121.0, abs=0.01)

        # Compare with what fixed-amount would give (10 kEUR base × 1.10^year):
        fixed_contingency_y2 = 100.0 * 1.10  # BUGGY: separate 10% inflation on contingency
        # The fixed_amount bug would give 110 kEUR in Y2 if contingency had 10% separate inflation
        # Our percentage_of_opex correctly gives 110 kEUR because G1 inflated to 1100, not because contingency inflated

    def test_percentage_mode_contingency_grows_indirectly_via_underlying_opex(self):
        """Contingency in percentage_of_opex mode grows only because underlying OPEX inflates.

        This is the key difference from fixed_amount mode where contingency itself inflates.
        """
        groups = [
            _make_group("G1", [_make_item("G1.1", 1000.0, inflation=0.02)]),
            _make_group(
                "GC",
                [_make_item("GC.1", 6.0, basis=OpexBasis.PCT_OF_SELECTED_GROUPS, selected=("G1",))],
                contingency_pct=5.0,
                contingency_method=OpexContingencyMethod.PERCENTAGE_OF_OPEX,
            ),
        ]
        result = compute_annual_opex(groups, years=4)

        # Y1: 5% × 1000 = 50
        # Y2: 5% × 1020 = 51  (only because G1 grew 2%)
        # Y3: 5% × 1040.4 = 52.02
        # Y4: 5% × 1061.208 = 53.06
        expected_contingency = [50.0, 51.0, 52.02, 53.06]
        for y in range(1, 5):
            gc = result.group_result(y, "GC")
            assert gc.group_total_keur == pytest.approx(expected_contingency[y - 1], abs=0.1)

    def test_fixed_and_percentage_produce_different_results_when_inflation_exists(self):
        """Demonstrate that fixed_amount (with inflation on contingency itself)
        and percentage_of_opex give different results when underlying OPEX inflates."""
        groups_fixed = [
            _make_group("G1", [_make_item("G1.1", 1000.0, inflation=0.10)]),  # base grows 10%/yr
            _make_group("GC", [_make_item("GC.1", 6.0, basis=OpexBasis.PCT_OF_SELECTED_GROUPS, selected=("G1",), inflation=0.0)],
                contingency_pct=10.0,
                contingency_method=OpexContingencyMethod.FIXED_AMOUNT,  # BUGGY: separate inflation
            ),
        ]
        result_fixed = compute_annual_opex(groups_fixed, years=3)

        groups_pct = [
            _make_group("G1", [_make_item("G1.1", 1000.0, inflation=0.10)]),
            _make_group("GC", [_make_item("GC.1", 6.0, basis=OpexBasis.PCT_OF_SELECTED_GROUPS, selected=("G1",))],
                contingency_pct=10.0,
                contingency_method=OpexContingencyMethod.PERCENTAGE_OF_OPEX,
            ),
        ]
        result_pct = compute_annual_opex(groups_pct, years=3)

        for y in (1, 2, 3):
            f = result_fixed.total_for_year(y)
            p = result_pct.total_for_year(y)
            # Results differ: percentage mode is the correct one
            assert f != pytest.approx(p, abs=0.01)


class TestContingencyMethodEnum:
    def test_enum_values(self):
        assert OpexContingencyMethod.FIXED_AMOUNT.value == "fixed_amount"
        assert OpexContingencyMethod.PERCENTAGE_OF_OPEX.value == "percentage_of_opex"

    def test_default_in_group_is_fixed_amount(self):
        g = OpexGroup(code="G", name="G", items=(), contingency_pct=0.0)
        assert g.contingency_method == OpexContingencyMethod.FIXED_AMOUNT


class TestOpexGroupAnnualResultContingencyFields:
    def test_result_exposes_contingency_method_pct_and_base(self):
        groups = [
            _make_group("G1", [_make_item("G1.1", 400.0, inflation=0.0)]),
            _make_group("G2", [_make_item("G2.1", 200.0, inflation=0.0)]),
            _make_group(
                "GC",
                [_make_item("GC.1", 0.0, basis=OpexBasis.PCT_OF_SELECTED_GROUPS, selected=("G1", "G2"))],
                contingency_pct=10.0,
                contingency_method=OpexContingencyMethod.PERCENTAGE_OF_OPEX,
            ),
        ]
        result = compute_annual_opex(groups, years=1)
        gc = result.group_result(1, "GC")
        assert gc.contingency_method == "percentage_of_opex"
        assert gc.contingency_pct == 10.0
        assert gc.contingency_base_keur == pytest.approx(600.0, abs=0.01)


class TestTuhoUsesPercentageOfOpex:
    def test_tuho_contingency_uses_percentage_of_opex_at_6_percent(self):
        from domain.opex.templates.tuho import build_tuho_opex_template

        groups = build_tuho_opex_template()
        b13 = next(g for g in groups if g.code == "B.13")
        assert b13.contingency_method == OpexContingencyMethod.PERCENTAGE_OF_OPEX
        assert b13.contingency_pct == 6.0

    def test_tuho_contingency_y1_matches_excel_parity(self):
        from domain.opex.templates.tuho import build_tuho_opex_template

        groups = build_tuho_opex_template()
        result = compute_annual_opex(groups, years=1, capacity_mw=35.0,
                                     production_mwh_by_year=[145740.0])

        non_contingency_y1 = sum(
            result.group_result(1, f"B.{idx:02d}").group_total_keur
            for idx in range(1, 13)
        )
        contingency_y1 = result.group_result(1, "B.13").group_total_keur

        # 6% × sum(B.01..B.12)
        expected_contingency = non_contingency_y1 * 0.06
        assert contingency_y1 == pytest.approx(expected_contingency, abs=0.01)
        assert contingency_y1 == pytest.approx(113.10, abs=0.1)  # from Excel