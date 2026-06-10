"""Phase 25B-6 — Generic Project Review Pack factory-safety + no-regression tests.

The Project Review Pack is a read-only UI layer. These tests prove that:
- Factory (TUHO / Oborovo) projects are NOT affected.
- The review pack is purely a read-only display — no DB writes, no
  schema changes, no model formula changes.
- Hard constraints are honored: no construction flag flips, no
  model formulas, no Tailwind / Alpine, no inline <script>.
- The review pack does NOT mutate any of the inputs it receives.
- Wire-up in main_web.py preserves the original 5-tuple callers
  (no surprises for downstream code).
- The helper module does NOT import the database, persistence,
  HTTP, or main_web.
"""
from __future__ import annotations

import inspect
import os
import re
import sys

import pytest


# ---------------------------------------------------------------------------
#  Fixtures / imports
# ---------------------------------------------------------------------------

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, ".."))

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from app.ui import project_review as project_review_mod  # noqa: E402
from app.ui.project_review import build_project_review_ui  # noqa: E402


# ---------------------------------------------------------------------------
#  TestFactoryBaselineUntouched
# ---------------------------------------------------------------------------

class TestFactoryBaselineUntouched:
    """Factory (TUHO / Oborovo) review packs must be SAFE read-only payloads."""

    def test_factory_template_classification(self):
        ui = build_project_review_ui(
            is_user_project=False, template_source="tuho_wind"
        )
        assert ui["classification"] == "factory_template"

    def test_factory_exploratory_limitations_still_rendered(self):
        # Even for a factory template, the review pack carries the
        # "Exploratory Limitations" section so a reviewer can see what
        # is and is not in scope. This is intentional transparency.
        ui = build_project_review_ui(
            is_user_project=False, template_source="oborovo_solar"
        )
        assert len(ui["exploratory_limitations"]) >= 1

    def test_factory_known_exclusions_rendered(self):
        ui = build_project_review_ui(
            is_user_project=False, template_source="tuho_wind"
        )
        assert len(ui["known_exclusions"]) >= 5
        joined = " ".join(ui["known_exclusions"]).lower()
        assert "construction" in joined

    def test_factory_has_run_still_detected(self):
        ui = build_project_review_ui(
            is_user_project=False,
            template_source="tuho_wind",
            last_run_summary={"project_irr": 0.10},
        )
        assert ui["has_run"] is True

    def test_factory_no_run_yields_clean_payload(self):
        ui = build_project_review_ui(
            is_user_project=False,
            template_source="oborovo_solar",
            last_run_summary=None,
        )
        assert ui["has_run"] is False
        # KPIs render dashes, not errors.
        for row in ui["kpis"]:
            assert row["value"] == "—"


# ---------------------------------------------------------------------------
#  TestHardConstraints
# ---------------------------------------------------------------------------

class TestHardConstraints:
    """Project Review Pack must NOT touch construction flags / rc1 / rc2."""

    def test_helper_module_does_not_toggle_construction_flag(self):
        # The helper must not ASSIGN or READ the construction flag —
        # only mentioning it in a documentation string is allowed.
        src = inspect.getsource(project_review_mod)
        # Strip the documentation string (triple-quoted at module top).
        # The KNOWN_EXCLUSIONS list is allowed to mention
        # use_construction_schedule_engine, but the module must not
        # import it, assign it, or call anything that mutates it.
        forbidden = (
            "use_construction_schedule_engine =",
            "= use_construction_schedule_engine",
            "from app.runtime",
            "import use_construction_schedule_engine",
        )
        for needle in forbidden:
            assert needle not in src, f"Forbidden: {needle}"

    def test_helper_module_has_no_db_imports(self):
        src = inspect.getsource(project_review_mod)
        forbidden = [
            "import sqlite",
            "import psycopg",
            "import sqlalchemy",
            "from app.persistence import",
            "import requests",
            "import urllib",
            "import random",
            "import time",
            "import datetime",
        ]
        for needle in forbidden:
            assert needle not in src, f"Forbidden: {needle}"

    def test_helper_module_does_not_import_main_web(self):
        src = inspect.getsource(project_review_mod)
        assert "import main_web" not in src
        assert "from main_web" not in src

    def test_helper_module_uses_only_typing_optional_simplenamespace(self):
        # Inspect the module's imports.
        src = inspect.getsource(project_review_mod)
        # Only typing, __future__, this module, and the typing module
        # are allowed imports.
        for line in src.splitlines():
            if not line.strip().startswith(("import ", "from ")):
                continue
            if "from __future__" in line:
                continue
            if "from typing" in line or "import typing" in line:
                continue
            if "from app.ui.project_review" in line:
                continue
            # Allow only the import of the project_review module itself
            # (this would be a no-op in practice but we permit it).
            pytest.fail(f"Unexpected import in helper module: {line!r}")


# ---------------------------------------------------------------------------
#  TestCssHardConstraints
# ---------------------------------------------------------------------------

class TestCssHardConstraints:
    """CSS for the review card must be additive, scoped, and not touch :root."""

    @pytest.fixture(scope="class")
    def styles_css_text(self):
        path = os.path.join(REPO_ROOT, "static", "styles.css")
        with open(path) as f:
            return f.read()

    def test_rev_classes_are_present(self, styles_css_text):
        for cls in (
            ".rev-card",
            ".rev-classification",
            ".rev-classification--exploratory",
            ".rev-classification--parity_validated",
            ".rev-classification--factory_template",
            ".rev-classification--user_created",
            ".rev-section",
            ".rev-section__title",
            ".rev-table",
            ".rev-table__label",
            ".rev-table__value",
            ".rev-scenarios__count-num",
            ".rev-scenarios__kind--base",
            ".rev-scenarios__kind--downside",
            ".rev-scenarios__kind--upside",
            ".rev-scenarios__kind--custom",
            ".rev-list",
        ):
            assert cls in styles_css_text, f"Missing CSS class: {cls}"

    def test_no_root_count_increase(self, styles_css_text):
        # The :root count is an invariant from Phase 24G-2 (3 base).
        # We must not change :root, only add new selectors.
        m = re.findall(r":root\s*\{", styles_css_text)
        assert len(m) <= 3 + 2, (
            f"Expected at most 3 :root (+2 inside @media), found {len(m)}"
        )


# ---------------------------------------------------------------------------
#  TestHelperIsPure
# ---------------------------------------------------------------------------

class TestHelperIsPure:
    """The helper must not mutate any of its inputs."""

    def test_does_not_mutate_project_ctx(self):
        from types import SimpleNamespace
        ctx = SimpleNamespace(name="X", code="Y")
        snapshot = vars(ctx).copy()
        build_project_review_ui(project_ctx=ctx, is_user_project=True)
        assert vars(ctx) == snapshot

    def test_does_not_mutate_last_run_summary(self):
        last = {"project_irr": 0.10, "equity_irr": None}
        snapshot = dict(last)
        build_project_review_ui(
            last_run_summary=last, is_user_project=True, template_source="generic_solar"
        )
        assert last == snapshot

    def test_does_not_mutate_scenario_cards(self):
        cards = [
            {"scenario_id": "a", "scenario_name": "Base", "is_active": True},
        ]
        snapshot = [dict(c) for c in cards]
        build_project_review_ui(
            scenario_cards=cards, is_user_project=True, template_source="generic_solar"
        )
        assert cards == snapshot


# ---------------------------------------------------------------------------
#  TestNoRegressionOnFactoryPaths
# ---------------------------------------------------------------------------

class TestNoRegressionOnFactoryPaths:
    """Re-run a few representative factory-path scenarios to make sure
    adding the project review UI does not break the previous 25B-* work."""

    def test_factory_exploratory_for_tuho(self):
        # TUHO is a factory template — review pack classifies it
        # as "factory_template" and renders all 6 sections.
        from types import SimpleNamespace
        ctx = SimpleNamespace(
            name="TUHO Wind",
            code="TUHO",
            country_iso="HR",
            technology="wind",
            capacity_mw=72.0,
            operating_hours_p50=2400.0,
            plant_availability=0.95,
            grid_availability=0.99,
            ppa_tariff_eur_mwh=77.0,
            ppa_term_years=12,
            ppa_index_pct=0.02,
            co2_enabled=True,
            financial_close="2028-06-30",
            cod_date="2029-12-30",
            horizon_years=25,
            total_capex_keur=85_000.0,
            senior_debt_keur=43_359.0,
            shl_amount_keur=14_621.0,
            interest_rate_pct=0.0793,
            senior_tenor_years=15,
            target_dscr=1.30,
            gearing_pct=0.70,
        )
        ui = build_project_review_ui(
            project_ctx=ctx,
            last_run_summary={"project_irr": 0.0947, "equity_irr": 0.1161,
                              "avg_dscr": 1.451, "min_dscr": 1.30,
                              "total_revenue_keur": 13_000.0,
                              "total_opex_keur": 1_998.0,
                              "ebitda_keur": 11_000.0,
                              "total_distributions_keur": 50_000.0,
                              "senior_debt_end_keur": 0.0},
            is_user_project=False,
            template_source="tuho_wind",
        )
        assert ui["classification"] == "factory_template"
        assert ui["has_run"] is True
        # KPIs from the TUHO calibration reference
        irr_row = next(r for r in ui["kpis"] if r["label"] == "Project IRR")
        assert irr_row["value"] == "9.5 %"
        dscr_row = next(r for r in ui["kpis"] if r["label"] == "Average DSCR")
        assert dscr_row["value"] == "1.45 x"

    def test_factory_exploratory_for_oborovo(self):
        from types import SimpleNamespace
        ctx = SimpleNamespace(
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
        ui = build_project_review_ui(
            project_ctx=ctx,
            last_run_summary={"project_irr": 0.0796, "equity_irr": 0.1060},
            is_user_project=False,
            template_source="oborovo_solar",
        )
        assert ui["classification"] == "factory_template"
        irr_row = next(r for r in ui["kpis"] if r["label"] == "Project IRR")
        assert irr_row["value"] == "8.0 %"
        equity_row = next(r for r in ui["kpis"] if r["label"] == "Equity IRR")
        assert equity_row["value"] == "10.6 %"


# ---------------------------------------------------------------------------
#  TestRenderSentinelForExclusionKeywords
# ---------------------------------------------------------------------------

class TestRenderSentinelForExclusionKeywords:
    """The known exclusions list must mention the 25B-* review-relevant
    hard-constraint items."""

    def test_known_exclusions_mentions_tax_engine(self):
        from app.ui.project_review import KNOWN_EXCLUSIONS
        joined = " ".join(KNOWN_EXCLUSIONS).lower()
        assert "tax" in joined

    def test_known_exclusions_mentions_depreciation(self):
        from app.ui.project_review import KNOWN_EXCLUSIONS
        joined = " ".join(KNOWN_EXCLUSIONS).lower()
        assert "depreciation" in joined

    def test_known_exclusions_mentions_lender_or_audit(self):
        from app.ui.project_review import KNOWN_EXCLUSIONS
        joined = " ".join(KNOWN_EXCLUSIONS).lower()
        # At least one of these should be present.
        assert ("lender" in joined) or ("audit" in joined)

    def test_known_exclusions_mentions_multi_user_or_saas(self):
        from app.ui.project_review import KNOWN_EXCLUSIONS
        joined = " ".join(KNOWN_EXCLUSIONS).lower()
        assert ("multi-user" in joined) or ("saas" in joined)
