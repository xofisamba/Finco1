"""Product Gap PR12 -- Overview / Dashboard Final Polish tests.

Scope (see docs/PRODUCT_GAP_PR12_OVERVIEW_DASHBOARD_FINAL_POLISH.md):

1. Dashboard renders (template exists and includes key structural elements).
2. Pre-Run state is honest: "No run yet" CTA is shown when no runtime snapshot
   exists; no fake financial values are displayed; all KPIs default to "—".
3. Post-Run KPIs remain authoritative: build_dashboard_kpis_from_raw_kpis()
   sources every value from the real run's raw_kpis dict; "—" sentinel is used
   for any KPI not present in the dict.
4. No placeholder KPIs remain: no hardcoded zeros or fabricated financial
   values exist in the dashboard template or KPI builder.
5. Empty states are shown where appropriate: "No data available" SVG charts
   when yearly_series is empty; empty-hint copy when runtime snapshot exists
   but all KPIs are missing.
6. No banned internal wording appears in user-visible dashboard copy.
7. SPA behaviour unchanged: HTMX OOB swap target exists, routing attributes
   preserved, no new JS calculation paths introduced.
8. Guardrail files untouched: domain/*, waterfall_core, input_adapter,
   project_factories, runtime-renderer.js, preview services not in diff.

Investigation conclusion: the Dashboard was already honest. This is a
documentation/test-only PR — the same outcome as PR10 (Scenarios/Compare)
and PR11 (Export). No functional code was changed.
"""
from __future__ import annotations

import os
import re
import subprocess

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")
os.environ.setdefault("FINCO_COOKIE_SECURE", "false")

# Banned internal wording that must not appear in user-visible dashboard copy.
BANNED_JARGON = [
    "Preview Architecture",
    "Runtime Pipeline",
    "TODO:",
    "FIXME",
    "placeholder architecture",
]

# All expected KPI keys from build_dashboard_kpis_from_raw_kpis.
EXPECTED_KPI_KEYS = {
    "project_irr",
    "equity_irr",
    "senior_debt",
    "realized_gearing",
    "min_dscr",
    "avg_dscr",
    "project_npv",
    "y1_revenue",
    "y1_ebitda",
    "total_capex",
}

# KPI keys returned by build_dashboard_kpis_from_raw_kpis (before realized_gearing merge).
RAW_KPI_BUILDER_KEYS = {
    "project_irr",
    "equity_irr",
    "senior_debt",
    "realized_gearing",
    "min_dscr",
    "avg_dscr",
    "project_npv",
    "y1_revenue",
    "y1_ebitda",
    "total_capex",
}

GUARDRAIL_PATHS = [
    "domain/",
    "app/waterfall_core.py",
    "app/input_adapter.py",
    "app/project_factories.py",
    "static/modelling/runtime-renderer.js",
    "app/services/model_preview.py",
    "app/services/preview_context.py",
    "app/services/previews/",
]


def _read(*parts: str) -> str:
    with open(os.path.join(PROJECT_ROOT, *parts), "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture(scope="module")
def dashboard_template():
    return _read("app", "templates", "partials", "_dashboard.html")


@pytest.fixture(scope="module")
def dashboard_oob_template():
    return _read("app", "templates", "partials", "_dashboard_oob.html")


@pytest.fixture(scope="module")
def workspace_shell():
    return _read("app", "templates", "partials", "workspace_shell.html")


@pytest.fixture(scope="module")
def generic_status_line():
    return _read("app", "templates", "partials", "_generic_status_line.html")


@pytest.fixture(scope="module")
def raw_kpis_sample() -> dict:
    """Representative raw_kpis dict as produced by run_project()."""
    return {
        "project_irr": 0.12,
        "equity_irr": 0.18,
        "senior_debt_keur": 30000.0,
        "min_dscr": 1.3,
        "avg_dscr": 1.5,
        "target_dscr": 1.2,
        "total_revenue_keur": 8000.0,
        "total_ebitda_keur": 6000.0,
        "project_npv_keur": 5000.0,
        "total_capex_keur": 52800.0,
    }


# ---------------------------------------------------------------------------
# 1. Dashboard renders
# ---------------------------------------------------------------------------


class TestDashboardRenders:
    def test_dashboard_partial_exists(self):
        path = os.path.join(
            PROJECT_ROOT, "app", "templates", "partials", "_dashboard.html"
        )
        assert os.path.isfile(path), "_dashboard.html template must exist"

    def test_dashboard_oob_partial_exists(self):
        path = os.path.join(
            PROJECT_ROOT, "app", "templates", "partials", "_dashboard_oob.html"
        )
        assert os.path.isfile(path), "_dashboard_oob.html template must exist"

    def test_dashboard_has_kpi_grid(self, dashboard_template):
        assert "dashboard-kpi-grid" in dashboard_template, (
            "Dashboard must have the KPI grid container"
        )

    def test_dashboard_has_kpi_card_loop(self, dashboard_template):
        assert "dashboard_kpis.items()" in dashboard_template, (
            "Dashboard must loop over dashboard_kpis dict"
        )

    def test_dashboard_section_has_correct_id(self, dashboard_template):
        assert 'id="dashboard-v1"' in dashboard_template, (
            "#dashboard-v1 must be present — it is the HTMX OOB swap target"
        )

    def test_dashboard_module_importable(self):
        from app.ui import dashboard  # noqa: F401

    def test_dashboard_builder_importable(self):
        from app.ui.dashboard import (  # noqa: F401
            build_dashboard_kpis,
            build_dashboard_kpis_from_raw_kpis,
        )

    def test_dashboard_context_builder_in_main_web(self):
        main_web = _read("main_web.py")
        assert "_build_index_dashboard_context" in main_web, (
            "_build_index_dashboard_context must be present in main_web.py"
        )

    def test_dashboard_enabled_true(self):
        """dashboard_enabled is hardcoded True in _build_index_dashboard_context."""
        main_web = _read("main_web.py")
        assert '"dashboard_enabled": True' in main_web, (
            "dashboard_enabled must be set to True in the index dashboard context"
        )

    def test_workspace_shell_includes_dashboard(self, workspace_shell):
        assert "partials/_dashboard.html" in workspace_shell, (
            "workspace_shell.html must include _dashboard.html"
        )

    def test_workspace_shell_has_panel_overview(self, workspace_shell):
        assert 'id="panel-overview"' in workspace_shell, (
            "Overview panel must exist in workspace_shell.html"
        )


# ---------------------------------------------------------------------------
# 2. Pre-Run state is honest
# ---------------------------------------------------------------------------


class TestPreRunStateHonest:
    def test_no_run_yet_cta_conditional(self, dashboard_template):
        """CTA is only shown when no runtime snapshot exists."""
        assert (
            "not runtime_summary or not runtime_summary.last_runtime_snapshot_id"
            in dashboard_template
        ), "Pre-run CTA must be gated on absence of last_runtime_snapshot_id"

    def test_no_run_yet_copy_present(self, dashboard_template):
        assert "No run yet" in dashboard_template, (
            "'No run yet' pre-run heading must be present"
        )

    def test_pre_run_cta_describes_kpis_correctly(self, dashboard_template):
        assert "Run the model to populate the dashboard" in dashboard_template, (
            "Pre-run CTA must explain that Run populates KPIs"
        )

    def test_kpis_default_to_dash_sentinel_pre_run(self):
        """When last_runtime_summary is None, all KPIs default to '—'."""
        from app.ui.dashboard import build_dashboard_kpis

        kpis = build_dashboard_kpis(
            last_runtime_summary=None,
            project_record=None,
            realized_gearing_pct=None,
        )
        for key, card in kpis.items():
            if key == "realized_gearing":
                # Realized gearing has its own 'missing' status path
                assert card["status"] == "missing", (
                    f"realized_gearing must be 'missing' pre-run; got {card['status']}"
                )
            else:
                assert card["value"] == "—", (
                    f"KPI '{key}' must default to '—' when no runtime summary; "
                    f"got {card['value']!r}"
                )
                assert card["status"] == "missing", (
                    f"KPI '{key}' must have status='missing' pre-run; "
                    f"got {card['status']!r}"
                )

    def test_kpis_default_to_dash_when_empty_summary(self):
        """When last_runtime_summary is an empty dict, all KPIs default to '—'."""
        from app.ui.dashboard import build_dashboard_kpis

        kpis = build_dashboard_kpis(
            last_runtime_summary={},
            project_record=None,
            realized_gearing_pct=None,
        )
        for key, card in kpis.items():
            if key == "realized_gearing":
                continue
            assert card["value"] == "—", (
                f"KPI '{key}' must be '—' when runtime summary is empty; "
                f"got {card['value']!r}"
            )

    def test_no_fake_financial_numbers_in_template(self, dashboard_template):
        """No hardcoded financial literals (e.g. '12.5%', '30,000') in the template."""
        # Check there are no inline numeric KPI values (only Jinja variable references)
        # A hardcoded IRR/DSCR/revenue value looks like: e.g. >12.5%< or >30,000<
        # We allow plain integers in CSS class names / data attrs / widths, but not
        # financial-looking decimal/comma patterns in text nodes
        hardcoded_pct = re.search(r">\s*\d+\.\d+%\s*<", dashboard_template)
        assert hardcoded_pct is None, (
            f"No hardcoded percentage financial values should appear in dashboard template; "
            f"found: {hardcoded_pct.group() if hardcoded_pct else ''!r}"
        )

    def test_no_fake_zeros_in_kpi_grid(self, dashboard_template):
        """The KPI grid uses {{ kpi.value }} Jinja, not hardcoded '0' values."""
        # Verify the value cell uses the Jinja variable
        assert "{{ kpi.value }}" in dashboard_template, (
            "KPI value must come from {{ kpi.value }} Jinja variable, not a literal"
        )


# ---------------------------------------------------------------------------
# 3. Post-Run KPIs remain authoritative
# ---------------------------------------------------------------------------


class TestPostRunKPIsAuthoritative:
    def test_build_kpis_from_raw_kpis_uses_real_values(self, raw_kpis_sample):
        from app.ui.dashboard import build_dashboard_kpis_from_raw_kpis

        kpis = build_dashboard_kpis_from_raw_kpis(raw_kpis_sample)
        # Project IRR: 0.12 → 12.0%
        assert kpis["project_irr"]["raw"] == pytest.approx(12.0), (
            "project_irr raw must be fraction × 100"
        )
        assert "12.0%" in kpis["project_irr"]["value"], (
            "project_irr value must be formatted as percentage"
        )
        # Equity IRR: 0.18 → 18.0%
        assert kpis["equity_irr"]["raw"] == pytest.approx(18.0)
        assert "18.0%" in kpis["equity_irr"]["value"]
        # Senior debt
        assert kpis["senior_debt"]["raw"] == pytest.approx(30000.0)
        # DSCR
        assert kpis["min_dscr"]["raw"] == pytest.approx(1.3)
        assert kpis["avg_dscr"]["raw"] == pytest.approx(1.5)
        # Revenue / EBITDA sourced from total_* fallback
        assert kpis["y1_revenue"]["raw"] == pytest.approx(8000.0)
        assert kpis["y1_ebitda"]["raw"] == pytest.approx(6000.0)

    def test_all_present_kpis_have_pass_status(self, raw_kpis_sample):
        from app.ui.dashboard import build_dashboard_kpis_from_raw_kpis

        kpis = build_dashboard_kpis_from_raw_kpis(raw_kpis_sample)
        for key, card in kpis.items():
            if key == "realized_gearing":
                continue  # This is always 'missing' from raw_kpis alone
            if card["raw"] is not None:
                assert card["status"] == "pass", (
                    f"KPI '{key}' with a real value must have status='pass'; "
                    f"got {card['status']!r}"
                )

    def test_missing_kpi_fields_still_dash(self):
        from app.ui.dashboard import build_dashboard_kpis_from_raw_kpis

        # A run that only produced IRR, not debt/DSCR/revenue
        partial_kpis = {"project_irr": 0.12, "equity_irr": 0.18}
        kpis = build_dashboard_kpis_from_raw_kpis(partial_kpis)
        assert kpis["project_irr"]["value"] != "—"
        assert kpis["senior_debt"]["value"] == "—", (
            "senior_debt must be '—' when not in raw_kpis"
        )
        assert kpis["senior_debt"]["status"] == "missing"

    def test_irr_converted_from_fraction_to_pct(self, raw_kpis_sample):
        from app.ui.dashboard import build_dashboard_kpis_from_raw_kpis

        kpis = build_dashboard_kpis_from_raw_kpis(raw_kpis_sample)
        # raw_kpis["project_irr"] = 0.12 (fraction); should become 12.0% not 0.1%
        assert "0.1%" not in kpis["project_irr"]["value"], (
            "project_irr must not display the raw fraction as a percentage"
        )
        assert "12.0%" in kpis["project_irr"]["value"], (
            "project_irr must multiply fraction by 100 before formatting"
        )

    def test_oob_template_uses_dashboard_kpis(self, dashboard_oob_template):
        """OOB update template also uses {{ kpi.value }} from dashboard_kpis."""
        assert "dashboard_kpis.items()" in dashboard_oob_template, (
            "_dashboard_oob.html must loop over dashboard_kpis"
        )
        assert "{{ kpi.value }}" in dashboard_oob_template

    def test_oob_template_has_oob_swap_attribute(self, dashboard_oob_template):
        assert 'hx-swap-oob="true"' in dashboard_oob_template, (
            "_dashboard_oob.html must have hx-swap-oob=true for HTMX OOB swap"
        )

    def test_oob_template_targets_same_id(self, dashboard_oob_template):
        assert 'id="dashboard-v1"' in dashboard_oob_template, (
            "_dashboard_oob.html must target #dashboard-v1 (same id as main template)"
        )

    def test_oob_update_wired_to_run_route(self):
        """main_web.py appends the OOB dashboard fragment after a run result."""
        main_web = _read("main_web.py")
        assert "_dashboard_oob.html" in main_web, (
            "main_web.py must reference _dashboard_oob.html for OOB update"
        )
        assert "build_dashboard_kpis_from_raw_kpis" in main_web, (
            "main_web.py must call build_dashboard_kpis_from_raw_kpis for OOB update"
        )

    def test_oob_update_reads_from_workspace_state(self):
        """OOB update reads raw_kpis from workspace_state, not fabricated."""
        main_web = _read("main_web.py")
        assert "last_runtime_summary" in main_web, (
            "main_web.py OOB path must read last_runtime_summary from workspace state"
        )

    def test_run_status_chip_conditional_on_snapshot_id(self, dashboard_template):
        """Status chip renders only when a real last_runtime_snapshot_id exists."""
        assert (
            "runtime_summary and runtime_summary.last_runtime_snapshot_id"
            in dashboard_template
        ), "Run status chip must be gated on last_runtime_snapshot_id"


# ---------------------------------------------------------------------------
# 4. No placeholder KPIs
# ---------------------------------------------------------------------------


class TestNoPlaceholderKPIs:
    def test_no_hardcoded_irr_value(self, dashboard_template):
        """No literal IRR value hardcoded in the template."""
        # A literal like ">10.5%<" or ">12.3%<" would indicate hardcoding
        literal_pct = re.findall(r">\s*\d+\.\d+%\s*<", dashboard_template)
        assert literal_pct == [], (
            f"No hardcoded percentage values allowed in dashboard template; found: {literal_pct}"
        )

    def test_no_hardcoded_dscr_value(self, dashboard_template):
        """No literal DSCR value hardcoded in the template."""
        # A literal like ">1.30<" or ">1.50<" in a KPI value slot would be fake
        literal_ratio = re.findall(r">\s*1\.\d{2}\s*<", dashboard_template)
        assert literal_ratio == [], (
            f"No hardcoded DSCR values allowed; found: {literal_ratio}"
        )

    def test_no_placeholder_zeroes_in_builder(self, raw_kpis_sample):
        """KPI builder never returns 0 as a real value when input data is None."""
        from app.ui.dashboard import build_dashboard_kpis_from_raw_kpis

        empty_kpis = build_dashboard_kpis_from_raw_kpis({})
        for key, card in empty_kpis.items():
            assert card["value"] == "—", (
                f"KPI '{key}' must show '—' when raw_kpis is empty; "
                f"got {card['value']!r}"
            )

    def test_realized_gearing_uses_correct_source(self):
        """Realized gearing is set from the call-site parameter, not raw_kpis."""
        from app.ui.dashboard import build_dashboard_kpis

        kpis = build_dashboard_kpis(
            last_runtime_summary={},
            project_record=None,
            realized_gearing_pct=65.5,
        )
        assert kpis["realized_gearing"]["raw"] == pytest.approx(65.5)
        assert "65.5%" in kpis["realized_gearing"]["value"]
        assert kpis["realized_gearing"]["status"] == "derived"

    def test_realized_gearing_missing_when_none(self):
        from app.ui.dashboard import build_dashboard_kpis

        kpis = build_dashboard_kpis(
            last_runtime_summary=None,
            project_record=None,
            realized_gearing_pct=None,
        )
        assert kpis["realized_gearing"]["value"] == "—"
        assert kpis["realized_gearing"]["status"] == "missing"

    def test_kpi_builder_keys_complete(self, raw_kpis_sample):
        """build_dashboard_kpis_from_raw_kpis returns the full expected key set."""
        from app.ui.dashboard import build_dashboard_kpis_from_raw_kpis

        kpis = build_dashboard_kpis_from_raw_kpis(raw_kpis_sample)
        for key in RAW_KPI_BUILDER_KEYS:
            assert key in kpis, f"Expected KPI key '{key}' missing from builder output"


# ---------------------------------------------------------------------------
# 5. Empty states are shown where appropriate
# ---------------------------------------------------------------------------


class TestEmptyStates:
    def test_charts_show_no_data_when_series_empty(self):
        """SVG chart renderer returns 'No data available' when series is empty."""
        from app.ui.dashboard import render_svg_line_chart

        svg = render_svg_line_chart(
            {"years": [], "revenue": [], "ebitda": []},
        )
        assert "No data available" in svg, (
            "Chart must show 'No data available' when years list is empty"
        )

    def test_dscr_chart_fallback_no_data(self):
        from app.ui.dashboard import render_svg_dscr_chart

        svg = render_svg_dscr_chart({"years": [], "dscr": [], "target": []})
        assert "No data available" in svg

    def test_debt_chart_fallback_no_data(self):
        from app.ui.dashboard import render_svg_debt_chart

        svg = render_svg_debt_chart({"years": [], "debt_balance": []})
        assert "No data available" in svg

    def test_empty_hint_copy_present_in_template(self, dashboard_template):
        """Empty-state hint 'Run the model to see KPIs here.' is present."""
        assert "Run the model to see KPIs here." in dashboard_template, (
            "Dashboard must have the empty-state hint for when snapshot exists "
            "but all KPIs are missing"
        )

    def test_empty_hint_conditional_on_all_missing(self, dashboard_template):
        """Empty hint only fires when all KPIs have status='missing'."""
        assert "_all_missing" in dashboard_template, (
            "Empty hint must check _all_missing condition"
        )
        assert "'missing'" in dashboard_template, (
            "Empty hint must check for 'missing' KPI status"
        )

    def test_pre_run_cta_links_to_run(self, dashboard_template):
        """Pre-run CTA action targets /run."""
        assert 'hx-post="/run"' in dashboard_template, (
            "Pre-run CTA must post to /run"
        )

    def test_generic_status_line_conditional(self, generic_status_line):
        """Generic status line only renders for exploratory projects."""
        assert "is_exploratory_project" in generic_status_line, (
            "Generic status line must be gated on is_exploratory_project"
        )

    def test_governance_cards_audit_mode_gated(self, workspace_shell):
        """Governance Status and TUHO Parity cards are gated on audit_mode."""
        # Find the card-title "Governance Status" (the actual rendered element, not a comment)
        assert "Governance Status" in workspace_shell
        # The card-title div is at the specific occurrence inside the audit panel block.
        # Confirm the {% if audit_mode %} block covers it by verifying both strings
        # appear in the same region, and that "audit_mode" precedes the card-title.
        card_title_marker = '<div class="card-title">Governance Status</div>'
        card_idx = workspace_shell.find(card_title_marker)
        assert card_idx != -1, (
            "Governance Status card-title div must exist in workspace_shell.html"
        )
        # Look backward from the card for an audit_mode conditional
        audit_gate_idx = workspace_shell.rfind("audit_mode", 0, card_idx)
        assert audit_gate_idx != -1, (
            "Governance Status card must be preceded by an audit_mode gate"
        )

    def test_charts_svg_has_no_data_available_aria(self):
        """No-data SVG has correct aria-label for accessibility."""
        from app.ui.dashboard import render_svg_line_chart

        svg = render_svg_line_chart({"years": [], "revenue": [], "ebitda": []})
        assert 'aria-label="No data available"' in svg, (
            "No-data SVG must have aria-label='No data available'"
        )


# ---------------------------------------------------------------------------
# 6. No banned internal wording in user-visible dashboard copy
# ---------------------------------------------------------------------------


class TestNoBannedWording:
    def _strip_jinja_comments(self, text: str) -> str:
        """Remove Jinja {# ... #} comments — they are not user-visible."""
        return re.sub(r"\{#.*?#\}", "", text, flags=re.DOTALL)

    def test_dashboard_template_no_banned_wording(self, dashboard_template):
        visible = self._strip_jinja_comments(dashboard_template)
        for term in BANNED_JARGON:
            assert term.lower() not in visible.lower(), (
                f"Banned term '{term}' found in user-visible _dashboard.html content"
            )

    def test_dashboard_oob_template_no_banned_wording(self, dashboard_oob_template):
        visible = self._strip_jinja_comments(dashboard_oob_template)
        for term in BANNED_JARGON:
            assert term.lower() not in visible.lower(), (
                f"Banned term '{term}' found in _dashboard_oob.html content"
            )

    def test_generic_status_line_no_banned_wording(self, generic_status_line):
        visible = self._strip_jinja_comments(generic_status_line)
        for term in BANNED_JARGON:
            assert term.lower() not in visible.lower(), (
                f"Banned term '{term}' found in _generic_status_line.html"
            )

    def test_dashboard_module_user_labels_no_banned(self):
        """KPI labels in dashboard.py must not contain banned internal terminology."""
        from app.ui.dashboard import build_dashboard_kpis_from_raw_kpis

        kpis = build_dashboard_kpis_from_raw_kpis({
            "project_irr": 0.12, "equity_irr": 0.18,
            "senior_debt_keur": 30000.0, "min_dscr": 1.3,
            "avg_dscr": 1.5, "total_revenue_keur": 8000.0,
            "total_ebitda_keur": 6000.0,
        })
        for key, card in kpis.items():
            label = card.get("label", "")
            tooltip = card.get("tooltip", "")
            for term in BANNED_JARGON:
                assert term.lower() not in label.lower(), (
                    f"Banned term '{term}' in KPI label for '{key}': {label!r}"
                )
                assert term.lower() not in tooltip.lower(), (
                    f"Banned term '{term}' in KPI tooltip for '{key}': {tooltip!r}"
                )

    def test_panel_overview_no_stub_in_rendered_text(self, workspace_shell):
        """No 'Stub'/'Prototype' in user-visible Overview panel text
        (developer comments stripped)."""
        # Extract panel-overview content
        start = workspace_shell.find('id="panel-overview"')
        end = workspace_shell.find('id="panel-inputs"', start)
        panel_text = workspace_shell[start:end]
        visible = self._strip_jinja_comments(panel_text)
        for term in ["Prototype", "TODO:", "FIXME"]:
            assert term not in visible, (
                f"'{term}' must not appear in user-visible Overview panel text"
            )


# ---------------------------------------------------------------------------
# 7. SPA behaviour unchanged
# ---------------------------------------------------------------------------


class TestSPABehaviourUnchanged:
    def test_htmx_run_target_preserved(self, workspace_shell):
        """HTMX model-output-area swap target still present."""
        assert 'id="model-output-area"' in workspace_shell

    def test_dashboard_oob_id_matches_dom_id(
        self, dashboard_template, dashboard_oob_template
    ):
        """The OOB replacement fragment targets the same DOM id as the initial render."""
        assert 'id="dashboard-v1"' in dashboard_template
        assert 'id="dashboard-v1"' in dashboard_oob_template

    def test_no_new_js_financial_calculation_in_templates(
        self, dashboard_template, dashboard_oob_template
    ):
        """Dashboard templates do not introduce any inline JS financial calculation."""
        for template_text, name in [
            (dashboard_template, "_dashboard.html"),
            (dashboard_oob_template, "_dashboard_oob.html"),
        ]:
            assert "<script" not in template_text, (
                f"No <script> tags allowed in {name} — KPIs are server-rendered"
            )

    def test_run_route_still_posts_to_run(self, dashboard_template):
        assert 'hx-post="/run"' in dashboard_template

    def test_dashboard_enabled_flag_in_shell(self, workspace_shell):
        """dashboard_enabled flag still gates the dashboard include."""
        assert "dashboard_enabled" in workspace_shell


# ---------------------------------------------------------------------------
# 8. Guardrail files untouched
# ---------------------------------------------------------------------------


class TestGuardrailsUntouched:
    def test_guardrail_paths_not_in_git_diff(self):
        """None of the restricted paths appear in git diff main --name-only."""
        result = subprocess.run(
            ["git", "diff", "main", "--name-only"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )
        changed_files = result.stdout.strip().splitlines()
        # V2-4 authorized: domain/ shims and finco_core/ engine modules
        _v24 = ("domain/waterfall/", "domain/tax/", "domain/financing/",
                "domain/depreciation/", "domain/shl/", "domain/sponsor/",
                "domain/returns/", "domain/distribution_account/",
                "finco_core/", "docs/V2_", "tests/test_v2_")
        _v24_files = {"domain/shl_fcf_waterfall.py", "domain/period_engine.py", "domain/validation.py"}
        changed_files = [c for c in changed_files if not c.startswith(_v24) and c not in _v24_files]
        for path in GUARDRAIL_PATHS:
            for changed in changed_files:
                assert not changed.startswith(path) and changed != path, (
                    f"Guardrail path '{path}' must not appear in git diff main; "
                    f"found changed file: {changed}"
                )

    def test_no_financial_formula_in_dashboard_module(self):
        """app/ui/dashboard.py must not import waterfall_core or domain modules."""
        import ast
        import importlib.util
        import sys

        dashboard_src = _read("app", "ui", "dashboard.py")
        assert "waterfall_core" not in dashboard_src, (
            "dashboard.py must not import waterfall_core"
        )
        assert "project_factories" not in dashboard_src, (
            "dashboard.py must not import project_factories"
        )
        # Parse AST to confirm no 'import run_project' or 'from x import run_project'
        tree = ast.parse(dashboard_src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "run_project" not in alias.name, (
                        "dashboard.py must not import run_project"
                    )
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    assert alias.name != "run_project", (
                        "dashboard.py must not import run_project"
                    )

    def test_main_web_dashboard_context_is_presentation_only(self):
        """_build_index_dashboard_context must not call run_project."""
        main_web = _read("main_web.py")
        # Extract only the function body (heuristic: look for the closing return block)
        fn_start = main_web.find("def _build_index_dashboard_context(")
        fn_end = main_web.find("\n\n\n", fn_start)
        fn_body = main_web[fn_start:fn_end]
        assert "run_project" not in fn_body, (
            "_build_index_dashboard_context must not call run_project — "
            "it is a pure presentation helper"
        )
        assert "input_adapter" not in fn_body

    def test_product_gap_pr1_through_pr11_unaffected(self):
        """Confirmed that the guardrail files from PR1-PR11 are untouched."""
        result = subprocess.run(
            ["git", "diff", "main", "--name-only"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )
        changed = result.stdout.strip()
        assert "app/waterfall_core.py" not in changed
        assert "app/input_adapter.py" not in changed
        assert "app/project_factories.py" not in changed
        assert "app/services/model_preview.py" not in changed
        assert "app/services/preview_context.py" not in changed
        assert "static/modelling/runtime-renderer.js" not in changed


# ---------------------------------------------------------------------------
# Characterization: pre-existing baseline failures confirmed unchanged
# ---------------------------------------------------------------------------


class TestBaselineConfirmation:
    def test_dashboard_kpi_builder_new_signature_works(self):
        """build_dashboard_kpis uses last_runtime_summary= (new signature).

        Confirms the post-HOTFIX-PILOT-BLOCKER-1 signature is correct.
        The two stale tests in test_phase_p2min3_dashboard_v1.py that use
        the old waterfall_result= kwarg are pre-existing failures on main
        (not caused by this PR).
        """
        from app.ui.dashboard import build_dashboard_kpis

        kpis = build_dashboard_kpis(
            last_runtime_summary={"project_irr": 0.10, "equity_irr": 0.15},
            project_record=None,
            realized_gearing_pct=None,
        )
        assert "project_irr" in kpis
        assert kpis["project_irr"]["raw"] == pytest.approx(10.0)

    def test_stale_waterfall_result_kwarg_fails(self):
        """The old waterfall_result= kwarg is no longer valid (pre-existing failure)."""
        from app.ui.dashboard import build_dashboard_kpis

        with pytest.raises(TypeError, match="unexpected keyword argument 'waterfall_result'"):
            build_dashboard_kpis(
                waterfall_result=None,
                project_record=None,
                realized_gearing_pct=None,
            )
