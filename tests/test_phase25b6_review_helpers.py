"""Phase 25B-6 — Generic Project Review Pack helper tests.

Goal: a third-party reviewer can understand a generic project from a
single read-only review card. These tests cover the pure helpers in
``app.ui.project_review``.

Hard constraints:
- No DB, no I/O, no time, no random, no side-effects.
- No formula changes (no NPV/IRR/DSCR computations here).
- No schema changes.
- No model formula changes.
- rc1 / factory / factory baseline flow is untouched.

These tests are pure unit tests.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.ui.project_review import (
    EXPLORATORY_LIMITATIONS,
    KNOWN_EXCLUSIONS,
    build_assumptions_summary,
    build_kpis_summary,
    build_project_review_ui,
    build_scenario_summary,
)


# ---------------------------------------------------------------------------
#  Fixtures
# ---------------------------------------------------------------------------

def _make_project_ctx(**overrides) -> SimpleNamespace:
    """Build a simple project_ctx-like namespace with realistic defaults."""
    base = dict(
        name="Oborovo Solar",
        code="OBOROVO",
        country_iso="HR",
        technology="solar",
        capacity_mw=53.63,
        operating_hours_p50=1180.0,
        plant_availability=0.97,
        grid_availability=0.99,
        ppa_tariff_eur_mwh=78.5,
        ppa_term_years=12,
        ppa_index_pct=0.02,
        co2_enabled=False,
        financial_close="2026-06-30",
        cod_date="2027-12-30",
        horizon_years=20,
        total_capex_keur=42_000.0,
        senior_debt_keur=30_000.0,
        shl_amount_keur=10_000.0,
        interest_rate_pct=0.065,
        senior_tenor_years=15,
        target_dscr=1.30,
        gearing_pct=0.70,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _make_run_summary() -> dict:
    return {
        "project_irr": 0.085,
        "equity_irr": 0.105,
        "avg_dscr": 1.42,
        "min_dscr": 1.18,
        "total_revenue_keur": 4_250.0,
        "total_opex_keur": 1_120.0,
        "ebitda_keur": 3_130.0,
        "total_distributions_keur": 28_500.0,
        "senior_debt_end_keur": 15_400.0,
    }


# ---------------------------------------------------------------------------
#  TestKnownExclusionsAndLimitations
# ---------------------------------------------------------------------------

class TestKnownExclusionsAndLimitations:
    """The pack must carry a fixed, non-empty list of known exclusions
    and exploratory limitations."""

    def test_known_exclusions_is_non_empty_list_of_strings(self):
        assert isinstance(KNOWN_EXCLUSIONS, list)
        assert len(KNOWN_EXCLUSIONS) >= 5
        for item in KNOWN_EXCLUSIONS:
            assert isinstance(item, str)
            assert item.strip() != ""

    def test_exploratory_limitations_is_non_empty_list_of_strings(self):
        assert isinstance(EXPLORATORY_LIMITATIONS, list)
        assert len(EXPLORATORY_LIMITATIONS) >= 1
        for item in EXPLORATORY_LIMITATIONS:
            assert isinstance(item, str)
            assert item.strip() != ""

    def test_known_exclusions_mentions_construction_engine(self):
        joined = " ".join(KNOWN_EXCLUSIONS).lower()
        assert "construction" in joined

    def test_known_exclusions_mentions_idc(self):
        joined = " ".join(KNOWN_EXCLUSIONS).lower()
        assert "idc" in joined or "interest during construction" in joined


# ---------------------------------------------------------------------------
#  TestBuildAssumptionsSummary
# ---------------------------------------------------------------------------

class TestBuildAssumptionsSummary:
    """The assumptions summary must be a list of {label, value} rows."""

    def test_returns_empty_list_when_project_ctx_is_none(self):
        assert build_assumptions_summary(None) == []

    def test_returns_24_rows_for_full_project_ctx(self):
        rows = build_assumptions_summary(_make_project_ctx())
        assert len(rows) >= 20
        for row in rows:
            assert set(row.keys()) == {"label", "value"}
            assert isinstance(row["label"], str)
            assert isinstance(row["value"], str)

    def test_capacity_is_formatted_as_mw(self):
        rows = build_assumptions_summary(_make_project_ctx(capacity_mw=53.63))
        capacity_row = next(r for r in rows if r["label"] == "Capacity")
        assert capacity_row["value"] == "53.63 MW"

    def test_ppa_tariff_is_formatted_as_eur_per_mwh(self):
        rows = build_assumptions_summary(_make_project_ctx(ppa_tariff_eur_mwh=78.5))
        ppa_row = next(r for r in rows if r["label"] == "PPA tariff")
        assert ppa_row["value"] == "78.50 EUR/MWh"

    def test_plant_availability_is_formatted_as_percent(self):
        rows = build_assumptions_summary(_make_project_ctx(plant_availability=0.97))
        avail_row = next(r for r in rows if r["label"] == "Plant availability")
        assert avail_row["value"] == "97.0 %"

    def test_co2_enabled_renders_as_enabled(self):
        rows = build_assumptions_summary(_make_project_ctx(co2_enabled=True))
        co2_row = next(r for r in rows if r["label"] == "CO2 revenue")
        assert co2_row["value"] == "Enabled"

    def test_co2_disabled_renders_as_disabled(self):
        rows = build_assumptions_summary(_make_project_ctx(co2_enabled=False))
        co2_row = next(r for r in rows if r["label"] == "CO2 revenue")
        assert co2_row["value"] == "Disabled"

    def test_none_capacity_renders_as_dash(self):
        rows = build_assumptions_summary(_make_project_ctx(capacity_mw=None))
        capacity_row = next(r for r in rows if r["label"] == "Capacity")
        assert capacity_row["value"] == "—"

    def test_string_ppa_tariff_does_not_crash(self):
        # Even a string that cannot be cast to float must not crash.
        rows = build_assumptions_summary(_make_project_ctx(ppa_tariff_eur_mwh="oops"))
        ppa_row = next(r for r in rows if r["label"] == "PPA tariff")
        assert ppa_row["value"] == "—"

    def test_project_name_and_code_are_string_safe(self):
        rows = build_assumptions_summary(_make_project_ctx(name="", code=None))
        name_row = next(r for r in rows if r["label"] == "Project name")
        code_row = next(r for r in rows if r["label"] == "Project code")
        assert name_row["value"] == "—"
        assert code_row["value"] == "—"

    def test_horizon_years_formatted_as_years(self):
        rows = build_assumptions_summary(_make_project_ctx(horizon_years=20))
        h_row = next(r for r in rows if r["label"] == "Horizon")
        assert h_row["value"] == "20 years"

    def test_target_dscr_formatted_as_x(self):
        rows = build_assumptions_summary(_make_project_ctx(target_dscr=1.30))
        d_row = next(r for r in rows if r["label"] == "Target DSCR")
        assert d_row["value"] == "1.30 x"


# ---------------------------------------------------------------------------
#  TestBuildKpisSummary
# ---------------------------------------------------------------------------

class TestBuildKpisSummary:
    """KPI summary must read from the last_run_summary dict."""

    def test_returns_nine_rows_for_a_full_run(self):
        rows = build_kpis_summary(_make_run_summary())
        assert len(rows) == 9
        for row in rows:
            assert set(row.keys()) == {"label", "value"}

    def test_returns_nine_dashes_when_no_run_summary(self):
        rows = build_kpis_summary(None)
        assert len(rows) == 9
        for row in rows:
            assert row["value"] == "—"

    def test_returns_dashes_when_run_summary_is_empty(self):
        rows = build_kpis_summary({})
        assert len(rows) == 9
        for row in rows:
            assert row["value"] == "—"

    def test_project_irr_is_formatted_as_percent(self):
        rows = build_kpis_summary(_make_run_summary())
        irr_row = next(r for r in rows if r["label"] == "Project IRR")
        assert irr_row["value"] == "8.5 %"

    def test_avg_dscr_is_formatted_as_x(self):
        rows = build_kpis_summary(_make_run_summary())
        dscr_row = next(r for r in rows if r["label"] == "Average DSCR")
        assert dscr_row["value"] == "1.42 x"

    def test_revenue_is_formatted_with_thousands_separator(self):
        rows = build_kpis_summary(_make_run_summary())
        rev_row = next(r for r in rows if r["label"] == "Total revenue (Y1)")
        assert rev_row["value"] == "4,250 kEUR"

    def test_distributions_and_senior_debt_formatted(self):
        rows = build_kpis_summary(_make_run_summary())
        d_row = next(r for r in rows if r["label"] == "Total distributions")
        s_row = next(r for r in rows if r["label"] == "Senior debt (end)")
        assert d_row["value"] == "28,500 kEUR"
        assert s_row["value"] == "15,400 kEUR"

    def test_missing_keys_render_as_dash(self):
        rows = build_kpis_summary({"project_irr": 0.10})
        irr_row = next(r for r in rows if r["label"] == "Project IRR")
        dscr_row = next(r for r in rows if r["label"] == "Average DSCR")
        assert irr_row["value"] == "10.0 %"
        assert dscr_row["value"] == "—"

    def test_none_value_renders_as_dash(self):
        rows = build_kpis_summary({"project_irr": None, "equity_irr": None})
        assert all(r["value"] == "—" for r in rows)


# ---------------------------------------------------------------------------
#  TestBuildScenarioSummary
# ---------------------------------------------------------------------------

class TestBuildScenarioSummary:
    """The scenario summary aggregates a list of scenario cards."""

    def test_returns_zero_count_for_empty_list(self):
        result = build_scenario_summary([])
        assert result["count"] == 0
        assert result["names"] == []
        assert result["kinds"] == []
        assert result["active_name"] == ""
        assert result["by_kind"] == {"base": 0, "downside": 0, "upside": 0, "custom": 0}

    def test_returns_zero_count_for_none_cards(self):
        result = build_scenario_summary(None)
        assert result["count"] == 0
        assert result["by_kind"] == {"base": 0, "downside": 0, "upside": 0, "custom": 0}

    def test_aggregates_kinds(self):
        cards = [
            {"scenario_id": "a", "scenario_name": "Base", "is_active": True},
            {"scenario_id": "b", "scenario_name": "Downside", "is_active": False},
            {"scenario_id": "c", "scenario_name": "Upside", "is_active": False},
            {"scenario_id": "d", "scenario_name": "Custom", "is_active": False},
        ]
        result = build_scenario_summary(cards)
        assert result["count"] == 4
        assert set(result["names"]) == {"Base", "Downside", "Upside", "Custom"}
        assert result["active_name"] == "Base"
        # Without workflow_ui, all cards are classified as "custom"
        assert result["by_kind"] == {"base": 0, "downside": 0, "upside": 0, "custom": 4}

    def test_workflow_ui_overrides_kind(self):
        cards = [
            {"scenario_id": "a", "scenario_name": "Base", "is_active": True},
            {"scenario_id": "b", "scenario_name": "Downside", "is_active": False},
        ]
        workflow_ui = {
            "by_scenario": {
                "a": {"label": {"kind": "base"}},
                "b": {"label": {"kind": "downside"}},
            }
        }
        result = build_scenario_summary(cards, workflow_ui=workflow_ui)
        assert result["by_kind"]["base"] == 1
        assert result["by_kind"]["downside"] == 1
        assert result["by_kind"]["custom"] == 0

    def test_active_name_picks_first_active(self):
        cards = [
            {"scenario_id": "a", "scenario_name": "Base", "is_active": False},
            {"scenario_id": "b", "scenario_name": "Downside", "is_active": True},
        ]
        result = build_scenario_summary(cards)
        assert result["active_name"] == "Downside"


# ---------------------------------------------------------------------------
#  TestBuildProjectReviewUi
# ---------------------------------------------------------------------------

class TestBuildProjectReviewUi:
    """The composer must produce a complete UI payload."""

    def test_returns_all_sections(self):
        ui = build_project_review_ui(
            project_ctx=_make_project_ctx(),
            last_run_summary=_make_run_summary(),
            scenario_cards=[{"scenario_id": "a", "scenario_name": "Base", "is_active": True}],
        )
        for key in (
            "classification",
            "is_user_project",
            "template_source",
            "assumptions",
            "kpis",
            "scenarios",
            "exploratory_limitations",
            "known_exclusions",
            "has_run",
        ):
            assert key in ui

    def test_classification_factory_template_for_factory(self):
        ui = build_project_review_ui(is_user_project=False, template_source="tuho_wind")
        assert ui["classification"] == "factory_template"

    def test_classification_exploratory_for_user_generic(self):
        ui = build_project_review_ui(is_user_project=True, template_source="generic_solar")
        assert ui["classification"] == "exploratory"

    def test_classification_exploratory_for_user_generic_wind(self):
        ui = build_project_review_ui(is_user_project=True, template_source="generic_wind")
        assert ui["classification"] == "exploratory"

    def test_classification_user_created_for_custom_user_project(self):
        ui = build_project_review_ui(is_user_project=True, template_source="")
        assert ui["classification"] == "user_created"

    def test_classification_user_created_for_other_template(self):
        # A user-created project with a non-generic template source
        # is still classified as user_created (not exploratory, not factory).
        ui = build_project_review_ui(is_user_project=True, template_source="tuho_wind")
        assert ui["classification"] == "user_created"

    def test_has_run_is_false_when_no_summary(self):
        ui = build_project_review_ui(last_run_summary=None)
        assert ui["has_run"] is False

    def test_has_run_is_false_for_empty_summary(self):
        ui = build_project_review_ui(last_run_summary={})
        assert ui["has_run"] is False

    def test_has_run_is_false_when_all_values_are_none(self):
        ui = build_project_review_ui(
            last_run_summary={"project_irr": None, "equity_irr": None}
        )
        assert ui["has_run"] is False

    def test_has_run_is_true_when_any_value_is_set(self):
        ui = build_project_review_ui(
            last_run_summary={"project_irr": 0.10, "equity_irr": None}
        )
        assert ui["has_run"] is True

    def test_template_source_passthrough_uppercase(self):
        # The helper does not lowercase or strip; that is the caller's
        # responsibility (see main_web._workspace_refresh_payload). The
        # helper simply stores what it was given.
        ui = build_project_review_ui(
            is_user_project=True, template_source="Generic_Solar"
        )
        assert ui["template_source"] == "Generic_Solar"

    def test_template_source_passthrough_whitespace(self):
        # The helper does not strip whitespace.
        ui = build_project_review_ui(
            is_user_project=True, template_source="  generic_solar  "
        )
        assert ui["template_source"] == "  generic_solar  "

    def test_known_exclusions_and_limitations_always_present(self):
        for klass in ("factory_template", "exploratory", "user_created"):
            ui = build_project_review_ui(
                is_user_project=(klass != "factory_template"),
                template_source="generic_solar" if klass == "exploratory" else "",
            )
            assert len(ui["known_exclusions"]) == len(KNOWN_EXCLUSIONS)
            assert len(ui["exploratory_limitations"]) == len(EXPLORATORY_LIMITATIONS)

    def test_excludes_are_independent_copies(self):
        # Mutating the payload's known_exclusions must not affect the module-level list.
        ui1 = build_project_review_ui()
        ui1["known_exclusions"].append("X")
        ui2 = build_project_review_ui()
        assert "X" not in ui2["known_exclusions"]
        # The original module list must also be unchanged.
        assert "X" not in KNOWN_EXCLUSIONS

    def test_assumptions_and_kpis_independent_per_call(self):
        ui1 = build_project_review_ui(
            project_ctx=_make_project_ctx(),
            last_run_summary=_make_run_summary(),
        )
        ui1["assumptions"].append({"label": "X", "value": "Y"})
        ui1["kpis"].append({"label": "X", "value": "Y"})
        ui2 = build_project_review_ui(
            project_ctx=_make_project_ctx(),
            last_run_summary=_make_run_summary(),
        )
        assert all(r["label"] != "X" for r in ui2["assumptions"])
        assert all(r["label"] != "X" for r in ui2["kpis"])

    def test_scenarios_uses_cards(self):
        cards = [
            {"scenario_id": "a", "scenario_name": "Base", "is_active": True},
            {"scenario_id": "b", "scenario_name": "Downside", "is_active": False},
        ]
        ui = build_project_review_ui(scenario_cards=cards)
        assert ui["scenarios"]["count"] == 2
        assert set(ui["scenarios"]["names"]) == {"Base", "Downside"}


# ---------------------------------------------------------------------------
#  TestModulePurity
# ---------------------------------------------------------------------------

class TestModulePurity:
    """The helper module must be pure: no DB imports, no I/O, no time, no random."""

    def test_module_source_does_not_import_persistence(self, tmp_path):
        import app.ui.project_review as mod
        src_path = mod.__file__
        with open(src_path) as f:
            src = f.read()
        # No DB or I/O imports allowed in this helper module.
        forbidden = [
            "import sqlite",
            "import psycopg",
            "import sqlalchemy",
            "from app.persistence import",
            "import requests",
            "import urllib",
            "import random",
            "import time",
        ]
        for needle in forbidden:
            assert needle not in src, (
                f"Forbidden import '{needle}' found in {src_path}"
            )

    def test_module_source_does_not_import_main_web(self):
        import app.ui.project_review as mod
        with open(mod.__file__) as f:
            src = f.read()
        assert "import main_web" not in src
        assert "from main_web" not in src
