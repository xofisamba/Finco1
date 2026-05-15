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
              selected_group_codes=None, notes="",
              inflation_start_exponent=0):
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
        inflation_start_exponent=inflation_start_exponent,
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
    """Test 10: contingency — pct item is sole mechanism (no double-count).

    After adding PCT_OF_SELECTED_GROUPS to _compute_item_base (pass1),
    the pct item correctly computes base = sum(selected) * pct / 100.
    The group.contingency_pct adds NOTHING extra in pass2 when a pct item exists
    (use contingency_pct=0 to avoid double-counting).
    For B.13 modeling: group.contingency_pct=0, item.budget=6, item provides the 6% mechanism.
    """

    def test_contingency_pct_of_selected_groups(self):
        # Group A with one item
        item_a = make_item(code="IA", name="Item A", budget=1000.0, group_code="GA")
        group_a = make_group(code="GA", name="Group A", items=[item_a])

        # Group C (contingency): pct item IS the mechanism (contingency_pct=0)
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
            contingency_pct=0.0  # item IS the contingency, no extra pass2
        )

        result = compute_annual_opex([group_a, group_c], years=2)

        # Y1: Group A = 1000
        # pct item in pass1: base = 1000 * 6/100 = 60
        gr_a = result.group_result(1, "GA")
        gr_c = result.group_result(1, "GC")
        ir_c = result.item_result(1, "GC", "IC")

        assert abs(gr_a.group_total_keur - 1000.0) < 0.01
        # pct item gives 60 (6% of 1000), no extra pass2 contingency
        assert abs(ir_c.total_keur - 60.0) < 0.01
        assert abs(ir_c.calculated_keur - 60.0) < 0.01
        assert abs(gr_c.group_total_keur - 60.0) < 0.01
        assert abs(gr_c.contingency_from_groups_keur - 0.0) < 0.01

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
        group_c = make_group(
            code="GC", name="Contingency",
            items=[item_c],
            contingency_pct=0.0
        )

        result = compute_annual_opex([group_a, group_b, group_c], years=1)

        gr_c = result.group_result(1, "GC")
        # pct item = 10% of GA (1000) = 100. GB is not selected.
        assert abs(gr_c.group_total_keur - 100.0) < 0.01
        assert abs(result.group_result(1, "GA").group_total_keur - 1000.0) < 0.01


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

class TestExplicitScheduleNoInflation:
    """A. EXPLICIT_SCHEDULE must not be inflated — values are already final."""

    def test_explicit_schedule_ignored_inflation_rate(self):
        """Explicit [100, 200, 300] with inflation 10% returns exactly 100, 200, 300."""
        item = make_item(budget=100.0, basis=OpexBasis.EXPLICIT_SCHEDULE,
                         inflation=0.10, explicit_schedule=[100.0, 200.0, 300.0])
        group = make_group(items=[item])
        result = compute_annual_opex([group], years=3)

        assert abs(result.item_result(1, "G1", "I1").total_keur - 100.0) < 0.01
        assert abs(result.item_result(2, "G1", "I1").total_keur - 200.0) < 0.01
        assert abs(result.item_result(3, "G1", "I1").total_keur - 300.0) < 0.01

    def test_explicit_schedule_with_wth_still_applies_wth(self):
        """WTH is added cost — still applies to explicit schedule values."""
        item = make_item(budget=100.0, basis=OpexBasis.EXPLICIT_SCHEDULE,
                         wth=0.10, explicit_schedule=[100.0, 200.0, 300.0])
        group = make_group(items=[item])
        result = compute_annual_opex([group], years=3)

        # Y1: 100 + 10% WTH = 110
        assert abs(result.item_result(1, "G1", "I1").total_keur - 110.0) < 0.01
        # Y2: 200 + 10% WTH = 220
        assert abs(result.item_result(2, "G1", "I1").total_keur - 220.0) < 0.01

    def test_explicit_schedule_with_manual_override_uses_override(self):
        """Manual override takes precedence even for explicit_schedule items."""
        item = make_item(budget=100.0, basis=OpexBasis.EXPLICIT_SCHEDULE,
                         explicit_schedule=[100.0, 200.0, 300.0],
                         manual_overrides=[ManualOverride(year_index=2, value_keur=999.0)])
        group = make_group(items=[item])
        result = compute_annual_opex([group], years=3)

        assert abs(result.item_result(1, "G1", "I1").total_keur - 100.0) < 0.01
        assert result.item_result(2, "G1", "I1").is_manual_override is True
        assert abs(result.item_result(2, "G1", "I1").total_keur - 999.0) < 0.01
        assert abs(result.item_result(3, "G1", "I1").total_keur - 300.0) < 0.01

    def test_explicit_schedule_inactive_flag_wins(self):
        """Inactive flag → 0 even for explicit_schedule items."""
        item = make_item(budget=100.0, basis=OpexBasis.EXPLICIT_SCHEDULE,
                         explicit_schedule=[100.0, 200.0, 300.0],
                         active_flags=[True, False, True])
        group = make_group(items=[item])
        result = compute_annual_opex([group], years=3)

        assert abs(result.item_result(1, "G1", "I1").total_keur - 100.0) < 0.01
        assert result.item_result(2, "G1", "I1").active is False
        assert result.item_result(2, "G1", "I1").total_keur == 0.0
        assert abs(result.item_result(3, "G1", "I1").total_keur - 300.0) < 0.01


class TestInflationStartExponent:
    """B. inflation_start_exponent shifts the inflation exponent."""

    def test_default_start_exponent_zero(self):
        """Default inflation_start_exponent=0: Y1=base, Y2=base*1.02, Y3=base*1.02^2."""
        item = make_item(budget=100.0, inflation=0.02)  # no explicit start
        group = make_group(items=[item])
        result = compute_annual_opex([group], years=3)

        assert abs(result.item_result(1, "G1", "I1").total_keur - 100.0) < 0.01
        assert abs(result.item_result(2, "G1", "I1").total_keur - 102.0) < 0.01
        assert abs(result.item_result(3, "G1", "I1").total_keur - 104.04) < 0.01

    def test_start_exponent_one_shifts_by_one(self):
        """inflation_start_exponent=1: Y1=base*1.02, Y2=base*1.02^2, Y3=base*1.02^3."""
        item = make_item(budget=100.0, inflation=0.02, wth=0.0,
                         active_flags=None, explicit_schedule=None, manual_overrides=None,
                         step_changes=None, selected_group_codes=None,
                         notes="", inflation_start_exponent=1)
        group = make_group(items=[item])
        result = compute_annual_opex([group], years=3)

        # Y1: 100 * (1.02)^(1-1+1) = 100 * 1.02^1 = 102
        assert abs(result.item_result(1, "G1", "I1").total_keur - 102.0) < 0.01
        # Y2: 100 * (1.02)^(2-1+1) = 100 * 1.02^2 = 104.04
        assert abs(result.item_result(2, "G1", "I1").total_keur - 104.04) < 0.01
        # Y3: 100 * (1.02)^(3-1+1) = 100 * 1.02^3 = 106.1208
        assert abs(result.item_result(3, "G1", "I1").total_keur - 106.1208) < 0.01

    def test_start_exponent_zero_with_step_change(self):
        """Step changes reset inflation from step year (inflation_start_exponent not involved)."""
        item = make_item(budget=100.0, inflation=0.02,
                         step_changes=[OpexItemStep(year_index=2, new_budget_keur=200.0)])
        group = make_group(items=[item])
        result = compute_annual_opex([group], years=3)

        # Y1: 100 * (1.02)^0 = 100
        assert abs(result.item_result(1, "G1", "I1").total_keur - 100.0) < 0.01
        # Y2: step to 200, exponent resets: 200 * (1.02)^(2-2) = 200
        assert abs(result.item_result(2, "G1", "I1").total_keur - 200.0) < 0.01
        # Y3: 200 * (1.02)^(3-2) = 200 * 1.02 = 204
        assert abs(result.item_result(3, "G1", "I1").total_keur - 204.0) < 0.01


class TestContingencySelectedGroups:
    """C. B.13 contingency = pct × sum of selected groups, no self-reference.

    The pct item IS the contingency mechanism. Use contingency_pct=0 on the group
    to avoid double-counting (pass1 item + pass2 group contingency).
    """

    def test_contingency_pct_of_selected_groups(self):
        """6% of selected groups — pct item is sole mechanism, no extra group contingency."""
        g1 = make_group(code="G1", items=[make_item(budget=100.0, group_code="G1")])
        g2 = make_group(code="G2", items=[make_item(budget=200.0, group_code="G2")])
        contingency_item = make_item(
            code="C1", budget=6.0, basis=OpexBasis.PCT_OF_SELECTED_GROUPS,
            group_code="CG", selected_group_codes=["G1", "G2"]
        )
        # contingency_pct=0: the pct item itself IS the contingency (no double-count)
        contingency_group = make_group(code="CG", items=[contingency_item], contingency_pct=0.0)
        result = compute_annual_opex([g1, g2, contingency_group], years=1)

        gr = result.group_result(1, "CG")
        # G1=100, G2=200, selected sum=300, 6%=18
        assert abs(gr.group_total_keur - 18.0) < 0.01
        assert abs(gr.contingency_from_groups_keur - 0.0) < 0.01  # no extra pass2 contingency

    def test_contingency_does_not_include_itself(self):
        """Selected groups do not include the contingency group itself."""
        g1 = make_group(code="G1", items=[make_item(budget=1000.0, group_code="G1")])
        contingency_item = make_item(
            code="C1", budget=10.0, basis=OpexBasis.PCT_OF_SELECTED_GROUPS,
            group_code="CG", selected_group_codes=["G1"]  # CG not in list
        )
        contingency_group = make_group(code="CG", items=[contingency_item], contingency_pct=0.0)
        result = compute_annual_opex([g1, contingency_group], years=1)

        gr = result.group_result(1, "CG")
        # CG total = 10% × G1(1000) = 100  (pct item only, no extra contingency)
        assert abs(gr.group_total_keur - 100.0) < 0.01
        assert abs(result.group_result(1, "G1").group_total_keur - 1000.0) < 0.01

    def test_contingency_changes_when_base_group_changes(self):
        """Contingency automatically updates when base group totals change."""
        g1 = make_group(code="G1", items=[make_item(budget=100.0, group_code="G1", inflation=0.02)])
        g2 = make_group(code="G2", items=[make_item(budget=200.0, group_code="G2", inflation=0.02)])
        contingency_item = make_item(
            code="C1", budget=6.0, basis=OpexBasis.PCT_OF_SELECTED_GROUPS,
            group_code="CG", selected_group_codes=["G1", "G2"]
        )
        contingency_group = make_group(code="CG", items=[contingency_item], contingency_pct=0.0)
        result = compute_annual_opex([g1, g2, contingency_group], years=3)

        # Y1: G1=100, G2=200, sum=300, 6%=18
        assert abs(result.group_result(1, "CG").group_total_keur - 18.0) < 0.01
        # Y2: G1=102, G2=204, sum=306, 6%=18.36
        assert abs(result.group_result(2, "CG").group_total_keur - 18.36) < 0.01
        # Y3: G1=104.04, G2=208.08, sum=312.12, 6%=18.7272
        assert abs(result.group_result(3, "CG").group_total_keur - 18.7272) < 0.01

    def test_contingency_with_inactive_base_groups(self):
        """Inactive base groups contribute 0 to contingency base."""
        g1 = make_group(code="G1", items=[make_item(budget=100.0, group_code="G1")])
        # G2 has budget=0 → 0 contribution
        g2 = make_group(code="G2", items=[make_item(budget=0.0, group_code="G2")])
        contingency_item = make_item(
            code="C1", budget=6.0, basis=OpexBasis.PCT_OF_SELECTED_GROUPS,
            group_code="CG", selected_group_codes=["G1", "G2", "G3"]  # G3 doesn't exist
        )
        contingency_group = make_group(code="CG", items=[contingency_item], contingency_pct=0.0)
        result = compute_annual_opex([g1, g2, contingency_group], years=1)

        gr = result.group_result(1, "CG")
        # G1=100, G2=0, G3 not present → sum=100, 6%=6
        assert abs(gr.group_total_keur - 6.0) < 0.01
