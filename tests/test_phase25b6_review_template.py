"""Phase 25B-6 — Project Review Card template rendering tests.

These tests render the read-only ``partials/project_review_card.html``
partial via Jinja2 directly. No HTTP, no live session, no DB.

Hard constraints:
- No JavaScript, no inline <script>, no Tailwind, no Alpine, no jQuery.
- All classes prefixed with ``rev-``.
- Renders correctly for all three classifications:
    factory_template, exploratory, user_created.
- Renders all six review sections: classification, assumptions, KPIs,
  scenarios, exploratory notes, known exclusions.
- Renders an empty-state (no run recorded) cleanly.
"""
from __future__ import annotations

import os
import sys

import pytest
from jinja2 import Environment, FileSystemLoader

# Repo root (parent of tests/)
HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, ".."))
TEMPLATES_DIR = os.path.join(REPO_ROOT, "app", "templates")

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from app.ui.project_review import build_project_review_ui  # noqa: E402


# ---------------------------------------------------------------------------
#  Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def jinja_env():
    return Environment(loader=FileSystemLoader(TEMPLATES_DIR))


@pytest.fixture(scope="module")
def review_tmpl(jinja_env):
    return jinja_env.get_template("partials/project_review_card.html")


@pytest.fixture(scope="module")
def workspace_tmpl(jinja_env):
    return jinja_env.get_template("partials/scenario_workspace.html")


def _build_review(**overrides):
    from types import SimpleNamespace
    project_ctx = SimpleNamespace(
        name="Generic Solar 5MW",
        code="GS5",
        country_iso="HR",
        technology="solar",
        capacity_mw=5.0,
        operating_hours_p50=1200.0,
        plant_availability=0.97,
        grid_availability=0.99,
        ppa_tariff_eur_mwh=80.0,
        ppa_term_years=12,
        ppa_index_pct=0.02,
        co2_enabled=False,
        financial_close="2026-06-30",
        cod_date="2027-12-30",
        horizon_years=20,
        total_capex_keur=4_500.0,
        senior_debt_keur=3_000.0,
        shl_amount_keur=500.0,
        interest_rate_pct=0.065,
        senior_tenor_years=15,
        target_dscr=1.30,
        gearing_pct=0.70,
    )
    last_run = {
        "project_irr": 0.09,
        "equity_irr": 0.11,
        "avg_dscr": 1.40,
        "min_dscr": 1.20,
        "total_revenue_keur": 480.0,
        "total_opex_keur": 110.0,
        "ebitda_keur": 370.0,
        "total_distributions_keur": 2_800.0,
        "senior_debt_end_keur": 1_500.0,
    }
    cards = [
        {"scenario_id": "a", "scenario_name": "Base", "is_active": True},
        {"scenario_id": "b", "scenario_name": "Downside", "is_active": False},
    ]
    defaults = dict(
        project_ctx=project_ctx,
        last_run_summary=last_run,
        scenario_cards=cards,
        is_user_project=True,
        template_source="generic_solar",
    )
    defaults.update(overrides)
    return build_project_review_ui(**defaults)


# ---------------------------------------------------------------------------
#  TestTemplateExists
# ---------------------------------------------------------------------------

class TestTemplateExists:
    def test_template_file_exists(self):
        path = os.path.join(TEMPLATES_DIR, "partials", "project_review_card.html")
        assert os.path.isfile(path), f"Missing: {path}"

    def test_template_file_contains_macros(self):
        path = os.path.join(TEMPLATES_DIR, "partials", "project_review_card.html")
        with open(path) as f:
            src = f.read()
        for macro in (
            "{%- macro classification_bar",
            "{%- macro assumptions_table",
            "{%- macro kpis_table",
            "{%- macro scenarios_summary",
            "{%- macro exploratory_notes",
            "{%- macro known_exclusions",
            "{%- macro project_review_card",
        ):
            assert macro in src, f"Missing macro: {macro!r}"


# ---------------------------------------------------------------------------
#  TestTemplateNoJavaScript
# ---------------------------------------------------------------------------

class TestTemplateNoJavaScript:
    """No JS / Tailwind / Alpine in the template."""

    def test_no_inline_script(self):
        path = os.path.join(TEMPLATES_DIR, "partials", "project_review_card.html")
        with open(path) as f:
            src = f.read()
        # Strip Jinja2 comments {# ... #} so we only check actual tags.
        import re
        stripped = re.sub(r"\{#.*?#\}", "", src, flags=re.DOTALL)
        assert "<script" not in stripped.lower()
        assert "onclick" not in stripped.lower()
        assert "onload" not in stripped.lower()
        assert "tailwind" not in stripped.lower()
        assert "alpine" not in stripped.lower()
        assert "jquery" not in stripped.lower()
        assert "htmx" not in stripped.lower()

    def test_uses_rev_class_prefix(self):
        path = os.path.join(TEMPLATES_DIR, "partials", "project_review_card.html")
        with open(path) as f:
            src = f.read()
        # All hard-coded CSS classes should start with rev-.
        # Jinja2 expressions like `{{ review.classification }}` are not
        # literal class names and are allowed.
        import re
        stripped = re.sub(r"\{\{.*?\}\}", "", src, flags=re.DOTALL)
        stripped = re.sub(r"\{#.*?#\}", "", stripped, flags=re.DOTALL)
        classes = re.findall(r'class="([^"]+)"', stripped)
        for cls in classes:
            for token in cls.split():
                if not token:
                    continue
                # Skip Jinja2 attribute interpolations, dotted names, etc.
                if any(ch in token for ch in (".", "?", ":")):
                    continue
                if token.startswith("rev-"):
                    continue
                pytest.fail(f"Class '{token}' does not start with 'rev-'")


# ---------------------------------------------------------------------------
#  TestClassificationRendering
# ---------------------------------------------------------------------------

class TestClassificationRendering:
    def test_exploratory_classification_renders(self, review_tmpl):
        review = _build_review(is_user_project=True, template_source="generic_solar")
        out = review_tmpl.module.project_review_card(review)
        assert 'rev-classification--exploratory' in out
        assert "Exploratory project" in out
        assert "generic_solar" in out

    def test_user_created_classification_renders(self, review_tmpl):
        review = _build_review(is_user_project=True, template_source="")
        out = review_tmpl.module.project_review_card(review)
        assert 'rev-classification--user_created' in out
        assert "User-created project" in out

    def test_factory_template_classification_renders(self, review_tmpl):
        review = _build_review(is_user_project=False, template_source="tuho_wind")
        out = review_tmpl.module.project_review_card(review)
        assert 'rev-classification--factory_template' in out
        assert "Factory baseline" in out
        assert "tuho_wind" in out


# ---------------------------------------------------------------------------
#  TestAssumptionsRendering
# ---------------------------------------------------------------------------

class TestAssumptionsRendering:
    def test_assumptions_section_renders_all_rows(self, review_tmpl):
        review = _build_review()
        out = review_tmpl.module.project_review_card(review)
        assert "Project Assumptions" in out
        for label in (
            "Project name",
            "Project code",
            "Country",
            "Technology",
            "Capacity",
            "PPA tariff",
            "Financial close",
            "Commercial operation date",
            "Total CAPEX",
        ):
            assert label in out, f"Missing label: {label}"

    def test_assumption_values_are_formatted(self, review_tmpl):
        review = _build_review()
        out = review_tmpl.module.project_review_card(review)
        assert "5.00 MW" in out
        assert "80.00 EUR/MWh" in out
        assert "4,500 kEUR" in out
        assert "20 years" in out

    def test_no_assumptions_section_when_project_ctx_is_none(self, review_tmpl):
        review = build_project_review_ui(
            is_user_project=True,
            template_source="generic_solar",
            project_ctx=None,
        )
        out = review_tmpl.module.project_review_card(review)
        # Assumptions section is rendered only when there are rows.
        # No project_ctx means no rows, no section.
        assert "Project Assumptions" not in out


# ---------------------------------------------------------------------------
#  TestKpisRendering
# ---------------------------------------------------------------------------

class TestKpisRendering:
    def test_kpis_section_renders_all_rows(self, review_tmpl):
        review = _build_review()
        out = review_tmpl.module.project_review_card(review)
        assert "Key KPIs (last run)" in out
        for label in (
            "Project IRR",
            "Equity IRR",
            "Average DSCR",
            "Minimum DSCR",
            "Total revenue (Y1)",
            "Total OPEX (Y1)",
            "EBITDA (Y1)",
            "Total distributions",
            "Senior debt (end)",
        ):
            assert label in out, f"Missing label: {label}"

    def test_kpis_section_shows_formatted_values(self, review_tmpl):
        review = _build_review()
        out = review_tmpl.module.project_review_card(review)
        assert "9.0 %" in out
        assert "11.0 %" in out
        assert "1.40 x" in out

    def test_kpis_section_shows_no_run_notice(self, review_tmpl):
        review = build_project_review_ui(
            is_user_project=True,
            template_source="generic_solar",
            last_run_summary=None,
        )
        out = review_tmpl.module.project_review_card(review)
        assert "No run has been recorded yet" in out


# ---------------------------------------------------------------------------
#  TestScenariosRendering
# ---------------------------------------------------------------------------

class TestScenariosRendering:
    def test_scenarios_section_renders_count(self, review_tmpl):
        review = _build_review()
        out = review_tmpl.module.project_review_card(review)
        assert "Scenarios" in out
        assert ">2<" in out or "rev-scenarios__count-num" in out
        assert "Active:" in out
        assert "<strong>Base</strong>" in out

    def test_scenarios_section_renders_kinds(self, review_tmpl):
        review = _build_review()
        # Without workflow_ui, both cards are "custom"
        out = review_tmpl.module.project_review_card(review)
        assert "rev-scenarios__kind--custom" in out

    def test_scenarios_section_with_workflow_kinds(self, review_tmpl):
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
        review = build_project_review_ui(
            is_user_project=True,
            template_source="generic_solar",
            scenario_cards=cards,
            scenario_workflow_ui=workflow_ui,
        )
        out = review_tmpl.module.project_review_card(review)
        assert "rev-scenarios__kind--base" in out
        assert "rev-scenarios__kind--downside" in out


# ---------------------------------------------------------------------------
#  TestExploratoryAndExclusionsRendering
# ---------------------------------------------------------------------------

class TestExploratoryAndExclusionsRendering:
    def test_known_exclusions_always_rendered(self, review_tmpl):
        review = _build_review()
        out = review_tmpl.module.project_review_card(review)
        assert "Known Exclusions" in out
        assert "Construction schedule engine" in out
        assert "Senior IDC" in out or "Interest During Construction" in out

    def test_exploratory_limitations_rendered_for_generic(self, review_tmpl):
        review = _build_review(is_user_project=True, template_source="generic_solar")
        out = review_tmpl.module.project_review_card(review)
        assert "Exploratory Limitations" in out
        assert "Generic Solar" in out or "Generic Wind" in out

    def test_exploratory_limitations_rendered_for_factory(self, review_tmpl):
        # Even factory templates get the limitations section in the
        # review pack so a reviewer can see what the runtime does NOT
        # compute. This is intentional transparency for the review pack.
        review = _build_review(is_user_project=False, template_source="tuho_wind")
        out = review_tmpl.module.project_review_card(review)
        # The "Exploratory Limitations" title is always rendered when
        # EXPLORATORY_LIMITATIONS is non-empty.
        assert "Exploratory Limitations" in out


# ---------------------------------------------------------------------------
#  TestWorkspaceIntegration
# ---------------------------------------------------------------------------

class TestWorkspaceIntegration:
    def test_workspace_includes_review_card_when_payload_present(self, workspace_tmpl):
        # The workspace template must import the review partial and
        # render the project_review_card macro.
        src_path = os.path.join(TEMPLATES_DIR, "partials", "scenario_workspace.html")
        with open(src_path) as f:
            src = f.read()
        assert "project_review_card.html" in src
        assert "rev.project_review_card" in src
        assert "{% if project_review_ui %}" in src

    def test_workspace_skips_review_card_when_payload_absent(self, workspace_tmpl):
        src_path = os.path.join(TEMPLATES_DIR, "partials", "scenario_workspace.html")
        with open(src_path) as f:
            src = f.read()
        # The include is gated on `if project_review_ui`, so when the
        # payload is None/empty the partial is not rendered.
        assert "{% if project_review_ui %}" in src


# ---------------------------------------------------------------------------
#  TestCardContainerStructure
# ---------------------------------------------------------------------------

class TestCardContainerStructure:
    def test_card_has_data_classification_attribute(self, review_tmpl):
        review = _build_review()
        out = review_tmpl.module.project_review_card(review)
        assert 'data-classification="exploratory"' in out

    def test_card_root_class_is_rev_card(self, review_tmpl):
        review = _build_review()
        out = review_tmpl.module.project_review_card(review)
        assert 'class="rev-card"' in out

    def test_no_review_renders_nothing(self, review_tmpl):
        out = review_tmpl.module.project_review_card(None)
        assert out == ""
