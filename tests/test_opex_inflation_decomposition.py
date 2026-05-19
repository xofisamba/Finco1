"""OPEX Inflation Decomposition — audit/explainability tests.

These tests validate the decomposition output only.
No production runtime behavior changes.
"""
import csv
import math
import os
import pytest

from domain.opex.templates.tuho import build_tuho_opex_template, B02_EXPLICIT_SCHEDULE, B11_ACTIVE_FLAGS
from domain.opex.engine import compute_annual_opex


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REPORT_CSV = os.path.join(
    os.path.dirname(__file__),
    "..",
    "reports",
    "phase7_opex_inflation_decomposition.csv",
)

TUHO_HORIZON_KEUR = 84_674.78  # Excel CF!R38 / OpEx!R105


def load_csv():
    with open(REPORT_CSV, newline="") as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------------------
# Report file
# ---------------------------------------------------------------------------

class TestReportExists:
    def test_csv_exists(self):
        assert os.path.exists(REPORT_CSV), f"{REPORT_CSV} not found"


class TestReportShape:
    def test_1530_rows(self):
        rows = load_csv()
        assert len(rows) == 1530, f"Expected 1530 rows, got {len(rows)}"

    def test_51_items(self):
        rows = load_csv()
        codes = {r["item_code"] for r in rows}
        assert len(codes) == 51, f"Expected 51 unique item codes, got {len(codes)}"

    def test_30_years(self):
        rows = load_csv()
        years = {int(r["year_index"]) for r in rows}
        assert years == set(range(1, 31)), f"Expected years 1-30, got {sorted(years)}"


# ---------------------------------------------------------------------------
# Driver classification
# ---------------------------------------------------------------------------

class TestDriverTaxonomy:
    def test_b01_classified_as_inflation(self):
        rows = load_csv()
        b01 = [r for r in rows if r["item_code"] == "B.01.1"]
        assert len(b01) == 30
        drivers = {r["primary_driver"] for r in b01}
        assert drivers == {"INFLATION"}, f"B.01.1 should be INFLATION, got {drivers}"

    def test_b02_1_classified_as_explicit_schedule(self):
        rows = load_csv()
        b021 = [r for r in rows if r["item_code"] == "B.02.1"]
        assert len(b021) == 30
        drivers = {r["primary_driver"] for r in b021}
        assert drivers == {"EXPLICIT_SCHEDULE"}, (
            f"B.02.1 should be EXPLICIT_SCHEDULE, got {drivers}"
        )

    def test_b11_1_classified_active_then_zero(self):
        rows = load_csv()
        b111 = [r for r in rows if r["item_code"] == "B.11.1"]
        assert len(b111) == 30
        by_year = {int(r["year_index"]): r for r in b111}
        # Y1-Y14 active
        for y in range(1, 15):
            assert by_year[y]["primary_driver"] in ("ACTIVE_FLAG", "INFLATION"), (
                f"B.11.1 Y{y} should be ACTIVE_FLAG/INFLATION, got {by_year[y]['primary_driver']}"
            )
        # Y15+ zero
        for y in range(15, 31):
            assert by_year[y]["primary_driver"] == "ZERO_LINE", (
                f"B.11.1 Y{y} should be ZERO_LINE, got {by_year[y]['primary_driver']}"
            )

    def test_b13_1_classified_as_contingency_pct(self):
        rows = load_csv()
        b131 = [r for r in rows if r["item_code"] == "B.13.1"]
        assert len(b131) == 30
        drivers = {r["primary_driver"] for r in b131}
        assert drivers == {"CONTINGENCY_PCT"}, (
            f"B.13.1 should be CONTINGENCY_PCT, got {drivers}"
        )


# ---------------------------------------------------------------------------
# Reconciliation
# ---------------------------------------------------------------------------

class TestReconciliation:
    def test_horizon_total_matches_engine(self):
        groups = build_tuho_opex_template()
        annual = compute_annual_opex(groups, years=30)
        engine_horizon = sum(
            i.total_keur
            for g_result in annual.group_results
            for i in g_result.item_results
        )
        rows = load_csv()
        decomp_horizon = sum(float(r["resulting_amount_keur"]) for r in rows)
        assert abs(decomp_horizon - engine_horizon) < 0.001, (
            f"Horizon mismatch: decomp={decomp_horizon:.3f}, engine={engine_horizon:.3f}"
        )

    def test_horizon_total_matches_excel(self):
        rows = load_csv()
        total = sum(float(r["resulting_amount_keur"]) for r in rows)
        assert abs(total - TUHO_HORIZON_KEUR) < 0.01, (
            f"Horizon {total:.2f} != Excel {TUHO_HORIZON_KEUR:.2f}"
        )

    def test_max_reconciliation_delta_within_tolerance(self):
        rows = load_csv()
        deltas = [abs(float(r["reconciliation_delta_keur"])) for r in rows]
        max_delta = max(deltas)
        assert max_delta <= 0.01, f"Max reconciliation delta {max_delta:.6f} exceeds 0.01 kEUR"

    def test_annual_totals_match_engine(self):
        groups = build_tuho_opex_template()
        annual = compute_annual_opex(groups, years=30)
        rows = load_csv()
        from collections import defaultdict

        decomp_by_year = defaultdict(float)
        for r in rows:
            decomp_by_year[int(r["year_index"])] += float(r["resulting_amount_keur"])

        for yr in range(1, 31):
            engine_total = sum(
                i.total_keur
                for g_result in annual.group_results
                for i in g_result.item_results
                if i.year_index == yr
            )
            delta = abs(decomp_by_year[yr] - engine_total)
            assert delta < 0.001, f"Y{yr}: decomp={decomp_by_year[yr]:.4f}, engine={engine_total:.4f}, delta={delta:.6f}"


# ---------------------------------------------------------------------------
# No runtime changes
# ---------------------------------------------------------------------------

class TestNoRuntimeChanges:
    def test_no_default_factory_opt_in(self):
        # Verify flag use_opex_line_item_engine is False by default on ProjectInfo
        from dataclasses import fields
        from domain.inputs import ProjectInfo

        # Find the field
        flag_field = next(f for f in fields(ProjectInfo) if f.name == "use_opex_line_item_engine")
        assert flag_field.default is False, (
            f"use_opex_line_item_engine default should be False, got {flag_field.default}"
        )

    def test_horizon_total_unchanged_from_existing_value(self):
        # The horizon total must remain 84,674.78 kEUR
        groups = build_tuho_opex_template()
        annual = compute_annual_opex(groups, years=30)
        total = sum(
            i.total_keur
            for g_result in annual.group_results
            for i in g_result.item_results
        )
        assert abs(total - 84_674.78) < 0.01


# ---------------------------------------------------------------------------
# Driver distribution
# ---------------------------------------------------------------------------

class TestDriverDistribution:
    def test_no_mixed_driver(self):
        rows = load_csv()
        mixed = {r["item_code"] for r in rows if r["primary_driver"] == "MIXED"}
        assert len(mixed) == 0, f"MIXED driver items found: {mixed}"

    def test_known_driver_counts(self):
        rows = load_csv()
        counts = {}
        for r in rows:
            d = r["primary_driver"]
            counts[d] = counts.get(d, 0) + 1
        # Expected: INFLATION: 1140, ZERO_LINE: 316, EXPLICIT_SCHEDULE: 30,
        #           ACTIVE_FLAG: 14, CONTINGENCY_PCT: 30
        assert counts.get("INFLATION", 0) == 1140, f"INFLATION={counts.get('INFLATION')}"
        assert counts.get("ZERO_LINE", 0) == 316, f"ZERO_LINE={counts.get('ZERO_LINE')}"
        assert counts.get("EXPLICIT_SCHEDULE", 0) == 30, f"EXPLICIT_SCHEDULE={counts.get('EXPLICIT_SCHEDULE')}"
        assert counts.get("ACTIVE_FLAG", 0) == 14, f"ACTIVE_FLAG={counts.get('ACTIVE_FLAG')}"
        assert counts.get("CONTINGENCY_PCT", 0) == 30, f"CONTINGENCY_PCT={counts.get('CONTINGENCY_PCT')}"


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v"])