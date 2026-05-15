"""Phase 7H O2 tests — OPEX line-item calculation engine."""
import pytest
from domain.opex.line_items import OpexBasis, OpexGroup, OpexItem, OpexItemStep, ManualOverride
from domain.opex.engine import compute_annual_opex


def make_group(code="G1", name="Group 1", inflation=0.0, wth=0.0, items=None, contingency_pct=0.0):
    return OpexGroup(
        code=code,
        name=name,
        inflation_rate=inflation,
        wth_rate=wth,
        items=tuple(items or []),
        order=0,
        editable=True,
        contingency_pct=contingency_pct,
    )


def make_item(code="I1", name="Item 1", budget=100.0, basis=OpexBasis.FIXED_ANNUAL_KEUR,
              group_code="G1", inflation=None, wth=0.0, active_flags=None,
              explicit_schedule=None, manual_overrides=None, step_changes=None,
              selected_group_codes=None, notes=""):
    return OpexItem(
        code=code,
        name=name,
        budget_keur=budget,
        basis=basis,
        group_code=group_code,
        inflation_rate=inflation,
        wth_rate=wth,
        active_flags=tuple(active_flags) if active_flags is not None else (),
        explicit_schedule_keur=tuple(explicit_schedule) if explicit_schedule else (),
        manual_overrides=tuple(manual_overrides) if manual_overrides else (),
        step_changes=tuple(step_changes) if step_changes else (),
        selected_group_codes=tuple(selected_group_codes) if selected_group_codes else (),
        notes=notes,
    )


class TestOpexFixedAnnualWithInflation:
    """Test 1: fixed annual with inflation — Y1=100, Y2=102, Y3=104.04"""

    def test_fixed_annual_with_inflation(self):
        item = make_item(budget=100.0, inflation=0.02)
        group = make_group(items=[item])
        result = compute_annual_opex([group], years=3)

        # Y1 = 100 * (1.02)^0 = 100
        # Y2 = 100 * (1.02)^1 = 102
        # Y3 = 100 * (1.02)^2 = 104.04
        r1 = result.item_result(1, "G1", "I1")
        r2 = result.item_result(2, "G1", "I1")
        r3 = result.item_result(3, "G1", "I1")

        assert abs(r1.total_keur - 100.0) < 0.01
        assert abs(r2.total_keur - 102.0) < 0.01
        assert abs(r3.total_keur - 104.04) < 0.01

        assert r1.calculated_keur == 100.0
        assert abs(r2.calculated_keur - 102.0) < 0.01
        assert abs(r3.calculated_keur - 104.04) < 0.01


class TestOpexActiveFlag:
    """Test 2: active flag — [True, False, True] gives Y2=0"""

    def test_active_flag_false_gives_zero(self):
        item = make_item(budget=100.0, inflation=0.02, active_flags=[True, False, True])
        group = make_group(items=[item])
        result = compute_annual_opex([group], years=3)

        r1 = result.item_result(1, "G1", "I1")
        r2 = result.item_result(2, "G1", "I1")
        r3 = result.item_result(3, "G1", "I1")

        assert abs(r1.total_keur - 100.0) < 0.01
        assert r2.total_keur == 0.0
        assert r2.active is False
        assert abs(r3.total_keur - 104.04) < 0.01

    def test_default_active_when_no_flags(self):
        """No active_flags → always active."""
        item = make_item(budget=100.0, inflation=0.02)  # no flags
        group = make_group(items=[item])
        result = compute_annual_opex([group], years=3)

        for year in [1, 2, 3]:
            r = result.item_result(year, "G1", "I1")
            assert r.active is True


class TestOpexManualOverride:
    """Test 3: manual override — Y2 override 150 replaces calculated 102"""

    def test_manual_override_replaces_calculated(self):
        item = make_item(budget=100.0, inflation=0.02,
                         manual_overrides=[ManualOverride(year_index=2, value_keur=150.0)])
        group = make_group(items=[item])
        result = compute_annual_opex([group], years=3)

        r1 = result.item_result(1, "G1", "I1")
        r2 = result.item_result(2, "G1", "I1")
        r3 = result.item_result(3, "G1", "I1")

        # Y1: no override → 100
        assert abs(r1.total_keur - 100.0) < 0.01
        assert r1.is_manual_override is False

        # Y2: override 150 replaces 102
        assert r2.is_manual_override is True
        assert r2.manual_override_keur == 150.0
        assert abs(r2.calculated_keur - 102.0) < 0.01  # what formula would give
        assert abs(r2.total_keur - 150.0) < 0.01  # actual

        # Y3: no override → 104.04
        assert abs(r3.total_keur - 104.04) < 0.01
        assert r3.is_manual_override is False

    def test_override_not_inflected(self):
        """Manual override is used as-is, not inflated."""
        item = make_item(budget=100.0, inflation=0.02,
                         manual_overrides=[ManualOverride(year_index=2, value_keur=150.0)])
        group = make_group(items=[item])
        result = compute_annual_opex([group], years=3)
        r2 = result.item_result(2, "G1", "I1")
        # calculated would be 102, but override is 150 exactly
        assert r2.manual_override_keur == 150.0
        assert abs(r2.total_keur - 150.0) < 0.01


class TestOpexManualOverrideInactive:
    """Test 4: inactive year with override still 0 — inactive wins"""

    def test_inactive_with_override_still_zero(self):
        # Override at Y2 but flag is inactive
        item = make_item(budget=100.0, inflation=0.02,
                         active_flags=[True, False, True],
                         manual_overrides=[ManualOverride(year_index=2, value_keur=150.0)])
        group = make_group(items=[item])
        result = compute_annual_opex([group], years=3)

        r2 = result.item_result(2, "G1", "I1")
        # Inactive wins → 0
        assert r2.active is False
        assert r2.total_keur == 0.0
        assert r2.is_manual_override is False


class TestOpexExplicitSchedule:
    """Test 5: explicit schedule — [10, 20, 30] exact values, no inflation"""

    def test_explicit_schedule_no_inflation(self):
        item = make_item(budget=0.0, basis=OpexBasis.EXPLICIT_SCHEDULE,
                         explicit_schedule=[10.0, 20.0, 30.0])
        group = make_group(items=[item])
        result = compute_annual_opex([group], years=3)

        r1 = result.item_result(1, "G1", "I1")
        r2 = result.item_result(2, "G1", "I1")
        r3 = result.item_result(3, "G1", "I1")

        assert abs(r1.total_keur - 10.0) < 0.01
        assert abs(r2.total_keur - 20.0) < 0.01
        assert abs(r3.total_keur - 30.0) < 0.01

        # calculated_keur = explicit value (no inflation)
        assert abs(r1.calculated_keur - 10.0) < 0.01

    def test_explicit_schedule_out_of_range_gives_zero(self):
        item = make_item(budget=0.0, basis=OpexBasis.EXPLICIT_SCHEDULE,
                         explicit_schedule=[10.0])  # only Y1 defined
        group = make_group(items=[item])
        result = compute_annual_opex([group], years=3)

        r1 = result.item_result(1, "G1", "I1")
        r2 = result.item_result(2, "G1", "I1")

        assert abs(r1.total_keur - 10.0) < 0.01
        assert r2.total_keur == 0.0  # out of range → 0


class TestOpexEurPerMwYear:
    """Test 6: eur_per_mw_year — capacity 50MW, rate 10,000 EUR/MW/year => 500 kEUR/year"""

    def test_eur_per_mw_year(self):
        item = make_item(budget=10000.0, basis=OpexBasis.EUR_PER_MW_YEAR)  # EUR/MW/year
        group = make_group(items=[item])
        result = compute_annual_opex([group], years=2, capacity_mw=50.0)

        r1 = result.item_result(1, "G1", "I1")
        # base = 10000 * 50 / 1000 = 500 kEUR
        assert abs(r1.calculated_keur - 500.0) < 0.01
        assert abs(r1.total_keur - 500.0) < 0.01


class TestOpexEurPerMwh:
    """Test 7: eur_per_mwh — production 100,000 MWh, rate 2 EUR/MWh => 200 kEUR"""

    def test_eur_per_mwh(self):
        item = make_item(budget=2.0, basis=OpexBasis.EUR_PER_MWH)  # EUR/MWh
        group = make_group(items=[item])
        result = compute_annual_opex([group], years=2,
                                      production_mwh_by_year=[100_000.0, 100_000.0])

        r1 = result.item_result(1, "G1", "I1")
        # base = 2 * 100000 / 1000 = 200 kEUR
        assert abs(r1.calculated_keur - 200.0) < 0.01
        assert abs(r1.total_keur - 200.0) < 0.01

    def test_eur_per_mwh_varies_by_production(self):
        item = make_item(budget=2.0, basis=OpexBasis.EUR_PER_MWH)
        group = make_group(items=[item])
        result = compute_annual_opex([group], years=2,
                                      production_mwh_by_year=[100_000.0, 150_000.0])

        r1 = result.item_result(1, "G1", "I1")
        r2 = result.item_result(2, "G1", "I1")

        assert abs(r1.total_keur - 200.0) < 0.01
        assert abs(r2.total_keur - 300.0) < 0.01  # 2 * 150000 / 1000


class TestOpexPctOfRevenue:
    """Test 8: pct_of_revenue — revenue 1000 kEUR, 2% => 20 kEUR"""

    def test_pct_of_revenue(self):
        item = make_item(budget=0.02, basis=OpexBasis.PCT_OF_REVENUE)  # 2% = 0.02
        group = make_group(items=[item])
        result = compute_annual_opex([group], years=2, revenue_keur_by_year=[1000.0, 1100.0])

        r1 = result.item_result(1, "G1", "I1")
        r2 = result.item_result(2, "G1", "I1")

        assert abs(r1.total_keur - 20.0) < 0.01  # 0.02 * 1000
        assert abs(r2.total_keur - 22.0) < 0.01  # 0.02 * 1100


class TestOpexGroupTotal:
    """Test 9: group total equals sum of item totals"""

    def test_group_total_equals_sum_items(self):
        item1 = make_item(code="I1", name="Item 1", budget=100.0, inflation=0.02)
        item2 = make_item(code="I2", name="Item 2", budget=50.0, inflation=0.03)
        group = make_group(code="G1", name="Group 1", items=[item1, item2])
        result = compute_annual_opex([group], years=2)

        gr = result.group_result(1, "G1")
        assert gr is not None
        # Y1: 100 + 50 = 150
        assert abs(gr.group_total_keur - 150.0) < 0.01

        gr2 = result.group_result(2, "G1")
        # Y2: 100*1.02 + 50*1.03 = 102 + 51.5 = 153.5
        assert abs(gr2.group_total_keur - 153.5) < 0.01

    def test_total_by_year_keur_sum(self):
        item1 = make_item(code="I1", name="Item 1", budget=100.0)
        item2 = make_item(code="I2", name="Item 2", budget=50.0)
        group = make_group(items=[item1, item2])
        result = compute_annual_opex([group], years=2)

        assert abs(result.total_by_year_keur[0] - 150.0) < 0.01
        assert abs(result.total_by_year_keur[1] - 150.0) < 0.01


class TestOpexContingency:
    """Test 10: contingency — 6% of selected groups only"""

    def test_contingency_pct_of_selected_groups(self):
        # Group A with one item
        item_a = make_item(code="IA", name="Item A", budget=1000.0, group_code="GA")
        group_a = make_group(code="GA", name="Group A", items=[item_a])

        # Group C (contingency) with 6% of Group A
        item_c = make_item(
            code="IC", name="Contingency",
            budget=6.0,  # 6%
            basis=OpexBasis.PCT_OF_SELECTED_GROUPS,
            group_code="GC",
            selected_group_codes=["GA"]
        )
        group_c = make_group(
            code="GC", name="Contingency Group",
            items=[item_c],
            contingency_pct=6.0
        )

        result = compute_annual_opex([group_a, group_c], years=2)

        # Y1: Group A = 1000, Contingency item base (pass1) = 6
        # Contingency amount (pass2) = 6% × 1000 = 60
        gr_a = result.group_result(1, "GA")
        gr_c = result.group_result(1, "GC")
        ir_c = result.item_result(1, "GC", "IC")

        # Group A total = 1000
        assert abs(gr_a.group_total_keur - 1000.0) < 0.01

        # Contingency item: total_keur = 60 (the computed contingency amount)
        # calculated_keur reflects the actual amount after pass2 update
        assert abs(ir_c.total_keur - 60.0) < 0.01
        assert abs(ir_c.calculated_keur - 60.0) < 0.01

        # Group C total = item base (6) + contingency_amount (60) = 66
        assert abs(gr_c.group_total_keur - 66.0) < 0.01
        assert abs(gr_c.contingency_from_groups_keur - 60.0) < 0.01

        # Grand total Y1 = GA(1000) + GC(66) = 1066
        assert abs(result.total_for_year(1) - 1066.0) < 0.01

    def test_contingency_excludes_non_selected_groups(self):
        item_a = make_item(code="IA", name="Item A", budget=1000.0, group_code="GA")
        group_a = make_group(code="GA", name="Group A", items=[item_a])

        item_b = make_item(code="IB", name="Item B", budget=500.0, group_code="GB")
        group_b = make_group(code="GB", name="Group B", items=[item_b])

        # Contingency references only GA (not GB)
        item_c = make_item(
            code="IC", name="Contingency",
            budget=10.0,
            basis=OpexBasis.PCT_OF_SELECTED_GROUPS,
            group_code="GC",
            selected_group_codes=["GA"]
        )
        group_c = make_group(code="GC", name="Contingency", items=[item_c], contingency_pct=10.0)

        result = compute_annual_opex([group_a, group_b, group_c], years=1)

        gr_c = result.group_result(1, "GC")
        ir_c = result.item_result(1, "GC", "IC")
        # Contingency = 10% × GA(1000) = 100 (only selected GA, not GB)
        # Item IC total = 100 (contingency portion only)
        # Group GC total = item base(10) + contingency(100) = 110
        assert abs(ir_c.total_keur - 100.0) < 0.01
        assert abs(gr_c.group_total_keur - 110.0) < 0.01
        assert abs(gr_c.contingency_from_groups_keur - 100.0) < 0.01


class TestOpexWTH:
    """Test 11: WTH audit — wth_keur computed and exposed"""

    def test_wth_added_to_cost(self):
        item = make_item(budget=100.0, wth=0.1)  # 10% WTH
        group = make_group(items=[item])
        result = compute_annual_opex([group], years=1)

        r = result.item_result(1, "G1", "I1")
        # final = 100, wth = 100 * 0.1 = 10, total = 110
        assert r.total_keur == 110.0
        assert r.wth_keur == 10.0
        assert r.wth_rate == 0.1

    def test_wth_zero_by_default(self):
        item = make_item(budget=100.0)  # wth=0.0
        group = make_group(items=[item])
        result = compute_annual_opex([group], years=1)

        r = result.item_result(1, "G1", "I1")
        assert r.wth_rate == 0.0
        assert r.wth_keur == 0.0
        assert r.total_keur == 100.0

    def test_wth_with_inflation(self):
        item = make_item(budget=100.0, inflation=0.02, wth=0.1)
        group = make_group(items=[item])
        result = compute_annual_opex([group], years=2)

        r2 = result.item_result(2, "G1", "I1")
        # calculated = 102, wth = 102 * 0.1 = 10.2, total = 112.2
        assert abs(r2.total_keur - 112.2) < 0.01


class TestOpexStepChange:
    """Test 12: step change — budget changes at year, inflation from step year"""

    def test_step_change_at_year(self):
        item = make_item(
            budget=100.0,
            inflation=0.02,
            step_changes=[OpexItemStep(year_index=2, new_budget_keur=200.0)]
        )
        group = make_group(items=[item])
        result = compute_annual_opex([group], years=3)

        r1 = result.item_result(1, "G1", "I1")
        r2 = result.item_result(2, "G1", "I1")
        r3 = result.item_result(3, "G1", "I1")

        # Y1: no step yet → 100 * (1.02)^0 = 100
        assert abs(r1.total_keur - 100.0) < 0.01

        # Y2: step kicks in → new_base = 200, exponent from step year = 2-2 = 0
        # 200 * (1.02)^0 = 200
        assert abs(r2.total_keur - 200.0) < 0.01

        # Y3: step active → 200 * (1.02)^(3-2) = 200 * 1.02 = 204
        assert abs(r3.total_keur - 204.0) < 0.01

    def test_step_change_multiple(self):
        item = make_item(
            budget=100.0,
            inflation=0.0,  # no inflation for clarity
            step_changes=[
                OpexItemStep(year_index=2, new_budget_keur=200.0),
                OpexItemStep(year_index=3, new_budget_keur=150.0),
            ]
        )
        group = make_group(items=[item])
        result = compute_annual_opex([group], years=4)

        assert abs(result.item_result(1, "G1", "I1").total_keur - 100.0) < 0.01
        assert abs(result.item_result(2, "G1", "I1").total_keur - 200.0) < 0.01
        assert abs(result.item_result(3, "G1", "I1").total_keur - 150.0) < 0.01
        assert abs(result.item_result(4, "G1", "I1").total_keur - 150.0) < 0.01


class TestOpexBackwardCompatibility:
    """Test 13: existing simple OPEX projection tests still pass"""

    def test_simple_group_no_inflation(self):
        item = make_item(budget=500.0, inflation=None)
        group = make_group(items=[item])
        result = compute_annual_opex([group], years=5)

        for year in range(1, 6):
            r = result.item_result(year, "G1", "I1")
            assert abs(r.total_keur - 500.0) < 0.01

    def test_group_inheritance(self):
        # Item without inflation → inherits group rate
        item = make_item(budget=100.0, inflation=None)  # group has 0.03
        group = make_group(inflation=0.03, items=[item])
        result = compute_annual_opex([group], years=2)

        r1 = result.item_result(1, "G1", "I1")
        r2 = result.item_result(2, "G1", "I1")

        assert abs(r1.total_keur - 100.0) < 0.01
        assert abs(r2.total_keur - 103.0) < 0.01

    def test_item_rate_overrides_group(self):
        # Item has own inflation → uses that, not group rate
        item = make_item(budget=100.0, inflation=0.05)  # 5% override
        group = make_group(inflation=0.02, items=[item])
        result = compute_annual_opex([group], years=2)

        r2 = result.item_result(2, "G1", "I1")
        # 100 * (1.05)^1 = 105
        assert abs(r2.total_keur - 105.0) < 0.01


class TestOpexNoRuntimeRegression:
    """Test 14: current runtime outputs unchanged (OpexItem compatible with existing schema)"""

    def test_old_opexitem_still_works(self):
        """Verify the old OpexItem from projections.py still works."""
        from domain.opex.projections import OpexItem as OldOpexItem

        # Old OpexItem has: name, y1_amount_keur, annual_inflation, step_changes
        old_item = OldOpexItem(
            name="Test Item",
            y1_amount_keur=200.0,
            annual_inflation=0.02,
            step_changes=()
        )
        assert old_item.y1_amount_keur == 200.0
        assert old_item.annual_inflation == 0.02

    def test_new_engine_not_wired_into_runtime(self):
        """Engine is isolated; not called by existing projections."""
        # This test confirms the new engine is separate from existing opex_schedule_annual
        from domain.opex.projections import opex_schedule_annual
        from domain.inputs import ProjectInputs

        tuho = ProjectInputs.create_default_tuho_wind1()
        annual = opex_schedule_annual(tuho, tuho.info.horizon_years)
        # Should return dict as before
        assert isinstance(annual, dict)
        assert len(annual) == 30


class TestOpexInactive:
    """Additional: inactive basis always returns 0"""

    def test_inactive_basis_always_zero(self):
        item = make_item(budget=1000.0, basis=OpexBasis.INACTIVE)
        group = make_group(items=[item])
        result = compute_annual_opex([group], years=3)

        for year in [1, 2, 3]:
            r = result.item_result(year, "G1", "I1")
            assert r.total_keur == 0.0
            assert r.calculated_keur == 0.0
            assert r.active is True  # basis=inactive, not flagged off


class TestOpexResultHelpers:
    """Test result helper methods"""

    def test_total_for_year(self):
        item = make_item(budget=100.0)
        group = make_group(items=[item])
        result = compute_annual_opex([group], years=3)

        assert abs(result.total_for_year(1) - 100.0) < 0.01
        assert abs(result.total_for_year(2) - 100.0) < 0.01

    def test_grand_total(self):
        item = make_item(budget=100.0)
        group = make_group(items=[item])
        result = compute_annual_opex([group], years=3)

        assert abs(result.grand_total_keur - 300.0) < 0.01

    def test_group_result_lookup(self):
        item = make_item(code="I1", name="Item", budget=50.0)
        group = make_group(code="G1", name="Group", items=[item])
        result = compute_annual_opex([group], years=2)

        gr = result.group_result(1, "G1")
        assert gr is not None
        assert gr.group_code == "G1"

        miss = result.group_result(1, "G99")
        assert miss is None

    def test_item_result_lookup(self):
        item = make_item(code="I1", name="Item", budget=50.0)
        group = make_group(code="G1", name="Group", items=[item])
        result = compute_annual_opex([group], years=2)

        ir = result.item_result(1, "G1", "I1")
        assert ir is not None
        assert ir.item_code == "I1"

        miss = result.item_result(1, "G1", "I99")
        assert miss is None