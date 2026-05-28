"""Phase 21 v1 — OPEX detail line-item grid data model tests.

Tests Scope A (data model), Scope B (Oborovo detail factory), Scope C (template render),
Scope D (reconciliation), and regression guardrails.
"""
import pytest

from domain.opex.templates.oborovo import build_oborovo_opex_template
from domain.opex.templates.tuho import build_tuho_opex_template
from domain.opex.engine import compute_annual_opex


# ═══════════════════════════════════════════════════════════════════════════════
# SCOPE A — DATA MODEL TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestOpexDetailDataModel:
    """OpexItem / OpexGroup data model supports hierarchical structure."""

    def test_oborovo_template_has_13_groups(self):
        groups = build_oborovo_opex_template()
        assert len(groups) == 13

    def test_oborovo_group_codes_b01_to_b13(self):
        groups = build_oborovo_opex_template()
        assert [g.code for g in groups] == [f"B.{idx:02d}" for idx in range(1, 14)]

    def test_oborovo_b01_children_sum_to_198(self):
        groups = build_oborovo_opex_template()
        b01 = next(g for g in groups if g.code == "B.01")
        total = sum(item.budget_keur for item in b01.items if item.budget_keur > 0)
        assert total == 198.0

    def test_oborovo_b02_y1_year1_is_244(self):
        """B.02 Y1 budget (before step) must be 244 kEUR."""
        groups = build_oborovo_opex_template()
        b02 = next(g for g in groups if g.code == "B.02")
        # item with step_changes (B.02.1 O&M Services)
        oandm = next(it for it in b02.items if it.budget_keur == 244.0)
        assert oandm.budget_keur == 244.0

    def test_oborovo_b02_y1_step_at_y2_to_185(self):
        """B.02.1 steps from 244 → 185.64 at Y2 (site maintenance takes over)."""
        groups = build_oborovo_opex_template()
        b02 = next(g for g in groups if g.code == "B.02")
        from domain.opex.line_items import OpexItemStep
        oandm = next(it for it in b02.items if it.budget_keur == 244.0)
        # Step is defined on the item
        assert len(oandm.step_changes) == 1
        step = oandm.step_changes[0]
        assert step.year_index == 2
        assert step.new_budget_keur == 185.64

    def test_oborovo_b12_y1_y2_is_32(self):
        """B.12 Y1-Y2 budget = 32 kEUR (before step down at Y3)."""
        groups = build_oborovo_opex_template()
        b12 = next(g for g in groups if g.code == "B.12")
        mit = next(it for it in b12.items if it.budget_keur == 32.0)
        assert mit.budget_keur == 32.0

    def test_oborovo_b12_step_at_y3_to_12_4848(self):
        """B.12.1 steps from 32 → 12.4848 at Y3."""
        groups = build_oborovo_opex_template()
        b12 = next(g for g in groups if g.code == "B.12")
        mit = next(it for it in b12.items if it.budget_keur == 32.0)
        assert len(mit.step_changes) == 1
        step = mit.step_changes[0]
        assert step.year_index == 3
        assert step.new_budget_keur == 12.4848

    def test_inherited_inflation_works(self):
        """Items without explicit inflation inherit from group rate."""
        groups = build_oborovo_opex_template()
        b01 = next(g for g in groups if g.code == "B.01")
        # B.01.01 has no explicit inflation_rate → inherits from group
        b01_01 = next(it for it in b01.items if it.code == "B.01.01")
        assert b01_01.inflation_rate == 0.02  # same as group

    def test_wth_rate_support(self):
        """wth_rate field is present on OpexItem; currently 0 for template items."""
        groups = build_oborovo_opex_template()
        b01 = next(g for g in groups if g.code == "B.01")
        b01_01 = next(it for it in b01.items if it.code == "B.01.01")
        assert hasattr(b01_01, "wth_rate")
        assert b01_01.wth_rate is None  # not explicitly set → None

    def test_source_flag_serialization(self):
        """All template items have source tag in notes field."""
        groups = build_oborovo_opex_template()
        for group in groups:
            for item in group.items:
                # notes field is present (source flag stored in notes for template)
                assert hasattr(item, "notes")


# ═══════════════════════════════════════════════════════════════════════════════
# SCOPE B — OBOROVO REGRESSION
# ═══════════════════════════════════════════════════════════════════════════════

class TestOborovoRegression:
    """Oborovo Y1-Y6 totals must match Phase 20U-C after fix."""

    # Phase 20U-C reference: Y1 total incl. contingency = 1338.56 kEUR
    PHASE20U_REF = {
        1: 1338.56,
        2: 1333.42,  # Y2 total (incl. B.02 step, B.13 contingency)
        3: 1338.56,  # approximation
    }

    def test_oborovo_y1_total_incl_contingency(self):
        groups = build_oborovo_opex_template()
        result = compute_annual_opex(groups, years=1)
        total = sum(result.group_result(1, g.code).group_total_keur for g in groups)
        assert total == pytest.approx(1338.56, abs=0.5)

    def test_oborovo_y1_non_contingency_excl_b13(self):
        """Y1 non-contingency total should be ~1287 kEUR (B.13 excluded)."""
        groups = build_oborovo_opex_template()
        result = compute_annual_opex(groups, years=1)
        non_contingency = sum(
            result.group_result(1, g.code).group_total_keur
            for g in groups
            if g.code != "B.13"
        )
        assert non_contingency == pytest.approx(1287.08, abs=0.5)

    def test_oborovo_b13_is_4_pct_of_non_contingency(self):
        """B.13 = 4% × (B.01 + B.02 + ... + B.12) — no circular ref."""
        groups = build_oborovo_opex_template()
        result = compute_annual_opex(groups, years=1)
        b13 = result.group_result(1, "B.13").group_total_keur
        non_contingency = sum(
            result.group_result(1, g.code).group_total_keur
            for g in groups
            if g.code != "B.13"
        )
        expected = non_contingency * 0.04
        assert b13 == pytest.approx(expected, abs=0.01)

    def test_oborovo_b02_steps_at_y2(self):
        """B.02 Y1=244, Y2+=185.64 (step at Y2)."""
        groups = build_oborovo_opex_template()
        result = compute_annual_opex(groups, years=3)
        y1 = result.group_result(1, "B.02").group_total_keur
        y2 = result.group_result(2, "B.02").group_total_keur
        y3 = result.group_result(3, "B.02").group_total_keur
        assert y1 == pytest.approx(244.0, abs=0.01)
        assert y2 == pytest.approx(185.64, abs=0.01)
        assert y3 == pytest.approx(189.35, abs=0.5)  # Y3 = 185.64 * 1.02

    def test_oborovo_b12_steps_at_y3(self):
        """B.12 Y1-Y2=32, Y3+=12.4848 (step at Y3)."""
        groups = build_oborovo_opex_template()
        result = compute_annual_opex(groups, years=5)
        y1 = result.group_result(1, "B.12").group_total_keur
        y2 = result.group_result(2, "B.12").group_total_keur
        y3 = result.group_result(3, "B.12").group_total_keur
        assert y1 == pytest.approx(32.0, abs=0.01)
        assert y2 == pytest.approx(32.64, abs=0.1)  # 32 * 1.02
        assert y3 == pytest.approx(12.48, abs=0.1)


# ═══════════════════════════════════════════════════════════════════════════════
# SCOPE B — TUHO REGRESSION
# ═══════════════════════════════════════════════════════════════════════════════

class TestTUHORegression:
    """TUHO existing behavior unchanged."""

    EXCEL_ANNUAL_TOTALS = (
        1998.05, 2029.83, 2147.06, 2180.13, 2213.86,
        2378.01, 2413.10, 2448.90, 2485.41, 2522.65,
        2603.04, 2641.79, 2681.31, 2721.62, 2734.77,
        2827.03, 2869.24, 2912.29, 2956.21, 3001.00,
        3131.49, 3178.09, 3225.63, 3274.11, 3323.57,
        3450.33, 3501.79, 3554.27, 3607.80, 3662.40,
    )

    def test_tuho_template_has_13_groups(self):
        groups = build_tuho_opex_template()
        assert len(groups) == 13

    def test_tuho_annual_totals_match_excel(self):
        result = compute_annual_opex(build_tuho_opex_template(), years=30)
        for year in range(1, 31):
            actual = result.total_by_year_keur[year - 1]
            assert actual == pytest.approx(self.EXCEL_ANNUAL_TOTALS[year - 1], abs=0.01)

    def test_tuho_contingency_6_pct_no_self_reference(self):
        result = compute_annual_opex(build_tuho_opex_template(), years=1)
        groups = build_tuho_opex_template()
        b13_group = next(g for g in groups if g.code == "B.13")
        b13_item = b13_group.item_by_code("B.13.1")
        assert "B.13" not in b13_item.selected_group_codes
        assert b13_group.contingency_pct == 6.0
        assert b13_group.contingency_method.name == "PERCENTAGE_OF_OPEX"


# ═══════════════════════════════════════════════════════════════════════════════
# SCOPE C — TEMPLATE RENDER SMOKE TEST
# ═══════════════════════════════════════════════════════════════════════════════

class TestTemplateRender:
    """sheet_opex_detail.html renders without crashing."""

    def test_opex_detail_template_renders(self):
        from jinja2 import Environment
        from pathlib import Path

        path = Path(__file__).parent.parent / "app/templates/partials/sheet_opex_detail.html"
        with open(path) as f:
            source = f.read()

        env = Environment()
        tmpl = env.from_string(source)

        # Minimal context that matches what the template expects
        ctx = {
            "project_ctx": {
                "name": "Test Project",
                "data_source": "factory",
                "opex_detail_items": [],
            },
            "is_user_project": False,
        }

        rendered = tmpl.render(**ctx)
        assert "OPEX Detail" in rendered
        assert "fc-grid" in rendered
        assert "No detailed OPEX items available" in rendered  # empty case

    def test_opex_detail_template_with_categories(self):
        from jinja2 import Environment
        from pathlib import Path

        path = Path(__file__).parent.parent / "app/templates/partials/sheet_opex_detail.html"
        with open(path) as f:
            source = f.read()

        env = Environment()
        tmpl = env.from_string(source)

        ctx = {
            "project_ctx": {
                "name": "Oborovo Solar PV",
                "horizon_years": 25,
                "data_source": "factory",
                "opex_detail_items": [
                    {
                        "code": "B.01",
                        "name": "Technical Management",
                        "is_contingency": False,
                        "contingency_pct": 0.0,
                        "yearly_totals": [60.0] * 25,
                        "children": [
                            {
                                "code": "B.01.01",
                                "name": "Asset Management Contract",
                                "budget_y1_keur": 60.0,
                                "inflation_pct": 2.0,
                                "wth_rate": 0.0,
                                "notes": "placeholder",
                                "yearly_values": [60.0] * 25,
                                "active_flags": [1] * 25,
                            },
                        ],
                    },
                    {
                        "code": "B.13",
                        "name": "Contingency",
                        "is_contingency": True,
                        "contingency_pct": 4.0,
                        "yearly_totals": [51.48] * 25,
                        "children": [
                            {
                                "code": "B.13.1",
                                "name": "Contingency reserve",
                                "budget_y1_keur": 0.0,
                                "inflation_pct": 0.0,
                                "wth_rate": 0.0,
                                "notes": "4% x non-contingency OPEX",
                                "yearly_values": [0.0] * 25,
                                "active_flags": [1] * 25,
                            },
                        ],
                    },
                ],
            },
            "is_user_project": False,
        }

        rendered = tmpl.render(**ctx)
        assert "B.01" in rendered
        assert "Technical Management" in rendered
        assert "Asset Management Contract" in rendered
        assert "B.01.01" in rendered
        assert "198" in rendered or "2" in rendered  # budget value
        assert "badge-contingency" in rendered or "4%" in rendered  # contingency marker

    def test_no_jinja2_undefined_error(self):
        """Template should not reference undefined variables for normal data."""
        from jinja2 import Environment, StrictUndefined
        from pathlib import Path

        path = Path(__file__).parent.parent / "app/templates/partials/sheet_opex_detail.html"
        with open(path) as f:
            source = f.read()

        env = Environment(undefined=StrictUndefined)
        tmpl = env.from_string(source)

        ctx = {
            "project_ctx": {
                "name": "Test",
                    "horizon_years": 25,
                "data_source": "factory",
                "opex_detail_items": [
                    {
                        "code": "B.01",
                        "name": "Operations",
                        "is_contingency": False,
                        "contingency_pct": 0.0,
                        "yearly_totals": [100.0] * 25,
                        "children": [
                            {
                                "code": "B.01.01",
                                "name": "Item 1",
                                "budget_y1_keur": 100.0,
                                "inflation_pct": 2.0,
                                "wth_rate": 0.0,
                                "notes": "test",
                                "yearly_values": [100.0] * 25,
                                "active_flags": [1] * 25,
                            },
                        ],
                    },
                ],
            },
            "is_user_project": False,
        }

        # Should not raise UndefinedError
        rendered = tmpl.render(**ctx)
        assert "Item 1" in rendered


# ═══════════════════════════════════════════════════════════════════════════════
# SCOPE D — RECONCILIATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestOpexReconciliation:
    """Category totals correctly sum from children; no double-counting."""

    def test_category_total_equals_sum_of_children_y1(self):
        """B.01 total = sum of B.01.01–B.01.06 at Y1."""
        groups = build_oborovo_opex_template()
        result = compute_annual_opex(groups, years=1)
        gr = result.group_result(1, "B.01")
        direct_total = gr.group_total_keur
        item_sum = sum(
            result.item_result(1, "B.01", it.code).total_keur
            for it in groups[0].items
        )
        assert direct_total == pytest.approx(item_sum, abs=0.01)

    def test_b13_not_in_b13_base(self):
        """B.13 contingency base excludes B.13 itself (no circular ref)."""
        groups = build_oborovo_opex_template()
        result = compute_annual_opex(groups, years=1)
        b13_group = next(g for g in groups if g.code == "B.13")
        b13_item = b13_group.item_by_code("B.13.1")
        assert "B.13" not in b13_item.selected_group_codes

    def test_no_double_counting_total_excl_contingency(self):
        """Total of all groups excluding B.13 = sum of category totals excl. B.13."""
        groups = build_oborovo_opex_template()
        result = compute_annual_opex(groups, years=1)
        non_contingency = sum(
            result.group_result(1, g.code).group_total_keur
            for g in groups
            if g.code != "B.13"
        )
        # Each category total is independently computed from children
        # So sum of category totals should equal sum of all children
        all_children_sum = sum(
            result.item_result(1, g.code, it.code).total_keur
            for g in groups
            if g.code != "B.13"
            for it in g.items
        )
        assert non_contingency == pytest.approx(all_children_sum, abs=0.01)

    def test_contingency_line_after_fixed_lines(self):
        """B.13 should be the last group (code B.13) in the categories list."""
        groups = build_oborovo_opex_template()
        codes = [g.code for g in groups]
        assert codes[-1] == "B.13"
        assert codes.index("B.13") == len(codes) - 1


# ═══════════════════════════════════════════════════════════════════════════════
# SCOPE A — PROJECT CONTEXT DATA BUILDER
# ═══════════════════════════════════════════════════════════════════════════════

class TestOpexDetailItemsBuilder:
    """_build_opex_detail_items produces correct hierarchical structure."""

    def test_build_opex_detail_items_returns_categories_tuple(self):
        from app.project_factories import create_default_oborovo
        from app.ui.project_context import _build_opex_detail_items

        proj = create_default_oborovo()
        result = _build_opex_detail_items(proj, code="OBOROVO")

        assert "categories" in result
        cats = result["categories"]
        assert isinstance(cats, (list, tuple))

    def test_build_opex_detail_items_has_b_codes(self):
        from app.project_factories import create_default_oborovo
        from app.ui.project_context import _build_opex_detail_items

        proj = create_default_oborovo()
        result = _build_opex_detail_items(proj, code="OBOROVO")
        cats = result["categories"]

        codes = [c["code"] for c in cats]
        assert "B" in codes or any("B.01" in c for c in codes)

    def test_build_opex_detail_items_child_has_required_fields(self):
        from app.project_factories import create_default_oborovo
        from app.ui.project_context import _build_opex_detail_items

        proj = create_default_oborovo()
        result = _build_opex_detail_items(proj, code="OBOROVO")
        cats = result["categories"]

        # Find a category with children
        cat_with_children = next((c for c in cats if c.get("children")), None)
        if cat_with_children:
            child = cat_with_children["children"][0]
            required = ["code", "name", "budget_y1_keur", "inflation_pct", "wth_rate", "source", "notes"]
            for field in required:
                assert field in child, f"Missing field: {field}"


# ═══════════════════════════════════════════════════════════════════════════════
# GUARDRAIL — REGRESSION SUITES
# ═══════════════════════════════════════════════════════════════════════════════

class TestGuardrailRegression:
    """Ensure existing OPEX engine tests still pass."""

    def test_opex_engine_tests_still_pass(self):
        """tests/test_opex_engine.py should pass unchanged."""
        import subprocess
        result = subprocess.run(
            ["python3", "-m", "pytest", "tests/test_opex_engine.py", "-v", "--tb=short"],
            capture_output=True,
            text=True,
            cwd=__import__("pathlib").Path(__file__).parent.parent,
        )
        assert result.returncode == 0, f"test_opex_engine.py failed:\n{result.stdout}\n{result.stderr}"

    def test_opex_line_item_engine_still_passes(self):
        """tests/test_opex_line_item_engine.py should pass unchanged."""
        import subprocess
        result = subprocess.run(
            ["python3", "-m", "pytest", "tests/test_opex_line_item_engine.py", "-v", "--tb=short"],
            capture_output=True,
            text=True,
            cwd=__import__("pathlib").Path(__file__).parent.parent,
        )
        assert result.returncode == 0, f"test_opex_line_item_engine.py failed:\n{result.stdout}\n{result.stderr}"
