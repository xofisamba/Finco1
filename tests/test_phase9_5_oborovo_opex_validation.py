"""Phase 9.5 — Oborovo OPEX factory deduplication validation tests.

Confirms:
1. Oborovo Y1 OPEX = 1,338.08 kEUR (correct, from Sprint 11 fix)
2. TUHO Y1 OPEX = 1,998.05 kEUR (unchanged)
3. Oborovo and TUHO use different OPEX item sets (no TUHO leakage)
4. No duplicate OPEX line items in Oborovo
5. Contingency method is correct (fixed_amount for Oborovo)
6. UI context matches factory
7. No runtime drift
"""

import pytest
from app.project_factories import create_default_oborovo, create_default_tuho_wind1
from app.ui.project_context import get_project_context
from domain.opex.projections import opex_breakdown_year


class TestOborovoOpexCorrect:
    """Oborovo Y1 OPEX = 1,338.08 kEUR (confirmed correct in Sprint 11)."""

    def test_factory_y1_total_is_1338(self):
        proj = create_default_oborovo()
        total = sum(item.y1_amount_keur for item in proj.opex)
        assert abs(total - 1338.08) < 0.01

    def test_runtime_y1_total_is_1338(self):
        from app.ui_runner import run_demo_project
        demo = run_demo_project("Oborovo", "Base")
        wf = demo.result
        y1_periods = [
            p for p in wf.periods
            if getattr(p, "year_index", 99) == 1 and getattr(p, "is_operation", False)
        ]
        y1_opex = sum(getattr(p, "opex_keur", 0) for p in y1_periods)
        assert abs(y1_opex - 1338.08) < 1.0

    def test_no_duplicates_in_opex_items(self):
        proj = create_default_oborovo()
        names = [item.name for item in proj.opex]
        assert len(names) == len(set(names)), "Duplicate OPEX line items found"

    def test_oborovo_15_opex_items(self):
        proj = create_default_oborovo()
        assert len(proj.opex) == 15

    def test_technical_management_is_198(self):
        proj = create_default_oborovo()
        items = {i.name: i.y1_amount_keur for i in proj.opex}
        assert abs(items.get("Technical Management", 0) - 198.0) < 0.01

    def test_infrastructure_maintenance_is_244(self):
        proj = create_default_oborovo()
        items = {i.name: i.y1_amount_keur for i in proj.opex}
        assert abs(items.get("Infrastructure Maintenance", 0) - 244.0) < 0.01


class TestTuhuOpexUnchanged:
    """TUHO Y1 OPEX remains 1,998.05 kEUR — no drift."""

    def test_factory_y1_total_is_1998(self):
        proj = create_default_tuho_wind1()
        total = sum(item.y1_amount_keur for item in proj.opex)
        assert abs(total - 1998.05) < 0.1

    def test_runtime_y1_total_is_1998(self):
        from app.ui_runner import run_demo_project
        demo = run_demo_project("TUHO", "Base")
        wf = demo.result
        y1_periods = [
            p for p in wf.periods
            if getattr(p, "year_index", 99) == 1 and getattr(p, "is_operation", False)
        ]
        y1_opex = sum(getattr(p, "opex_keur", 0) for p in y1_periods)
        assert abs(y1_opex - 1998.05) < 1.0

    def test_tuho_12_opex_items(self):
        proj = create_default_tuho_wind1()
        assert len(proj.opex) == 12


class TestNoTuhuLeakageInOborovo:
    """Oborovo must not use TUHO OPEX items or template."""

    def test_oborovo_not_using_tuho_template(self):
        oborovo_proj = create_default_oborovo()
        tuho_proj = create_default_tuho_wind1()
        # Different number of items
        assert len(oborovo_proj.opex) != len(tuho_proj.opex)
        # Different Y1 totals
        oboro_total = sum(i.y1_amount_keur for i in oborovo_proj.opex)
        tuho_total = sum(i.y1_amount_keur for i in tuho_proj.opex)
        oboro_total = sum(i.y1_amount_keur for i in oborovo_proj.opex)
        tuho_total = sum(i.y1_amount_keur for i in tuho_proj.opex)
        assert abs(oboro_total - tuho_total) > 500  # clearly different

    def test_ui_context_shows_1338_for_oborovo(self):
        ctx = get_project_context("oborovo")
        assert abs(ctx.opex_y1_total_keur - 1338.08) < 0.01

    def test_ui_context_shows_1998_for_tuho(self):
        ctx = get_project_context("tuho")
        assert abs(ctx.opex_y1_total_keur - 1998.01) < 0.1

    def test_ui_context_no_cross_contamination(self):
        ctx_obo = get_project_context("oborovo")
        ctx_tuho = get_project_context("tuho")
        assert ctx_obo.opex_y1_total_keur != ctx_tuho.opex_y1_total_keur
        assert ctx_obo.opex_contingency_method != ctx_tuho.opex_contingency_method


class TestOborovoContingencyMethod:
    """Oborovo uses fixed_amount contingency (not percentage_of_opex)."""

    def test_oborovo_contingency_is_fixed_amount(self):
        ctx = get_project_context("oborovo")
        assert ctx.opex_contingency_method == "fixed_amount"

    def test_oborovo_has_contingency_line_item(self):
        proj = create_default_oborovo()
        items = {i.name: i.y1_amount_keur for i in proj.opex}
        assert "Contingencies" in items
        assert items["Contingencies"] == 51.0


class TestOborovoOpexBreakdown:
    """Oborovo Y1 breakdown matches expected values (verified vs Excel)."""

    def test_y1_total_from_breakdown(self):
        proj = create_default_oborovo()
        br = opex_breakdown_year(proj, 1)
        total = sum(v for v in br.values())
        assert abs(total - 1338.08) < 0.01

    def test_top_5_items(self):
        proj = create_default_oborovo()
        br = opex_breakdown_year(proj, 1)
        top5 = dict(sorted(br.items(), key=lambda x: -x[1])[:5])
        # Insurance(255) + Infra(244) + Lease(208.08) + TechMgmt(198) + Power(177)
        assert abs(sum(v for v in top5.values()) - 1082.08) < 0.01

    def test_no_zero_items_included(self):
        proj = create_default_oborovo()
        br = opex_breakdown_year(proj, 1)
        # Taxes and Salary should be 0 in Y1
        assert br.get("Taxes", 0) == 0.0
        assert br.get("Salary&Payroll", 0) == 0.0
