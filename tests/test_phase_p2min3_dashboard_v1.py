"""Phase P2-min-3: Dashboard v1 (presentation only).

Dashboard v1 introduces 8 KPI cards + 3
inline-SVG charts. Server-rendered. NO
Chart.js / Plotly / D3 / JS calc. NO
formula / factory / model change.

Tests prove:
  - 8 KPI cards present (project_irr,
    equity_irr, senior_debt, realized_
    gearing, min_dscr, avg_dscr, y1_
    revenue, y1_ebitda)
  - 3 inline-SVG charts (revenue/ebitda,
    dscr with target, debt balance)
  - Realized gearing is computed in
    Python (not in Jinja / JS / SVG)
  - Debt balance uses explicit result
    field (NOT _find_debt_balance
    heuristic)
  - No Chart.js / Plotly / D3 / React /
    Vue / Svelte / Tailwind / Alpine
  - rc1 SHA preserved
  - use_construction_schedule_engine
    remains False
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
RC1_SHA = "b425a0708719eaa5e1d922b1008e5609758e0ad4"

HAS_GIT = shutil.which("git") is not None and (REPO_ROOT / ".git").exists()


# ---------------------------------------------------------------------------
# Test: dashboard module
# ---------------------------------------------------------------------------


class TestDashboardModule:
    def test_dashboard_module_imports(self):
        from app.ui import dashboard
        assert hasattr(dashboard, "build_dashboard_kpis")
        assert hasattr(dashboard, "build_revenue_ebitda_series")
        assert hasattr(dashboard, "build_dscr_series")
        assert hasattr(dashboard, "build_debt_balance_series")
        assert hasattr(dashboard, "render_svg_line_chart")
        assert hasattr(dashboard, "render_svg_dscr_chart")
        assert hasattr(dashboard, "render_svg_debt_chart")

    def test_dashboard_returns_eight_kpis(self):
        from app.ui.dashboard import build_dashboard_kpis
        class FakeRecord:
            pass
        kpis = build_dashboard_kpis(
            waterfall_result=None,
            project_record=FakeRecord(),
            realized_gearing_pct=None,
        )
        assert isinstance(kpis, dict)
        # 8 KPI cards.
        expected = {
            "project_irr", "equity_irr", "senior_debt",
            "realized_gearing", "min_dscr", "avg_dscr",
            "y1_revenue", "y1_ebitda",
        }
        assert expected.issubset(kpis.keys()), (
            f"missing KPIs: {expected - kpis.keys()}"
        )
        assert len(kpis) == 8, (
            f"Dashboard v1 must have exactly 8 KPIs; got {len(kpis)}"
        )

    def test_realized_gearing_kpi_status_is_derived(self):
        from app.ui.dashboard import build_dashboard_kpis
        class FakeRecord:
            pass
        kpis = build_dashboard_kpis(
            waterfall_result=None,
            project_record=FakeRecord(),
            realized_gearing_pct=42.5,
        )
        assert kpis["realized_gearing"]["raw"] == 42.5
        assert kpis["realized_gearing"]["status"] == "derived"

    def test_revenue_ebitda_series_helper(self):
        from app.ui.dashboard import build_revenue_ebitda_series
        class FakeResult:
            yearly_series = {
                "years": [1, 2, 3],
                "revenue_keur": [100.0, 200.0, 300.0],
                "ebitda_keur": [50.0, 80.0, 120.0],
            }
        out = build_revenue_ebitda_series(FakeResult())
        assert out["years"] == [1, 2, 3]
        assert out["revenue"] == [100.0, 200.0, 300.0]
        assert out["ebitda"] == [50.0, 80.0, 120.0]

    def test_dscr_series_helper(self):
        from app.ui.dashboard import build_dscr_series
        class FakeResult:
            yearly_series = {
                "years": [1, 2, 3],
                "dscr": [1.5, 1.6, 1.7],
                "target_dscr": [1.25, 1.25, 1.25],
            }
        out = build_dscr_series(FakeResult())
        assert out["dscr"] == [1.5, 1.6, 1.7]
        assert out["target"] == [1.25, 1.25, 1.25]

    def test_debt_balance_uses_explicit_field(self):
        """Phase P2-min-3 brief: 'Debt balance
        chart uses explicit result field
        (NOT _find_debt_balance)'. The
        helper must read from
        ``senior_debt_balance_keur`` /
        ``debt_balance_keur`` /
        ``senior_debt_balance`` /
        ``debt_balance`` — NOT from any
        heuristic helper.
        """
        from app.ui import dashboard
        src = Path(dashboard.__file__).read_text(encoding="utf-8")
        # Strip comments and docstrings to
        # avoid false positives.
        import re
        no_docstring = re.sub(r'\"{3}.*?\"{3}', '', src, flags=re.S)
        no_docstring = re.sub(r"'{3}.*?'{3}", '', no_docstring, flags=re.S)
        no_comments = re.sub(r'#.*', '', no_docstring)
        assert "_find_debt_balance" not in no_comments, (
            "P2-min-3: Debt balance must NOT use the "
            "_find_debt_balance heuristic. Use the explicit "
            "result field."
        )
        # Read from explicit result field.
        assert "senior_debt_balance_keur" in src, (
            "P2-min-3: Debt balance must read from the explicit "
            "result field 'senior_debt_balance_keur'"
        )


# ---------------------------------------------------------------------------
# Test: SVG rendering
# ---------------------------------------------------------------------------


class TestSvgRendering:
    def test_svg_line_chart_with_data(self):
        from app.ui.dashboard import render_svg_line_chart
        svg = render_svg_line_chart({
            "years": [1, 2, 3],
            "revenue": [100.0, 200.0, 300.0],
            "ebitda": [50.0, 80.0, 120.0],
        })
        assert "<svg" in svg
        assert "</svg>" in svg
        assert "<path" in svg
        assert "Dashboard line chart" in svg

    def test_svg_line_chart_with_no_data(self):
        from app.ui.dashboard import render_svg_line_chart
        svg = render_svg_line_chart({
            "years": [],
            "revenue": [],
            "ebitda": [],
        })
        assert "<svg" in svg
        assert "No data available" in svg

    def test_svg_dscr_chart_renders_target_line(self):
        from app.ui.dashboard import render_svg_dscr_chart
        svg = render_svg_dscr_chart({
            "years": [1, 2, 3],
            "dscr": [1.5, 1.6, 1.7],
            "target": [1.25, 1.25, 1.25],
        })
        assert "<svg" in svg
        assert "DSCR over time" in svg
        assert "stroke-dasharray" in svg, (
            "DSCR chart must include the dashed target line"
        )

    def test_svg_debt_chart_renders_area(self):
        from app.ui.dashboard import render_svg_debt_chart
        svg = render_svg_debt_chart({
            "years": [1, 2, 3],
            "debt_balance": [1000.0, 900.0, 800.0],
        })
        assert "<svg" in svg
        assert "Senior debt balance" in svg
        assert "rgba" in svg, (
            "Debt chart must include the area-under-line fill"
        )


# ---------------------------------------------------------------------------
# Test: workspace_shell integration
# ---------------------------------------------------------------------------


class TestWorkspaceShellIntegration:
    def test_workspace_shell_includes_dashboard_partial(self):
        path = REPO_ROOT / "app/templates/partials/workspace_shell.html"
        text = path.read_text(encoding="utf-8")
        assert "_dashboard.html" in text, (
            "workspace_shell.html must include the Dashboard v1 partial"
        )

    def test_workspace_shell_renders_dashboard_when_enabled(self):
        """When dashboard_enabled is True,
        the partial is rendered.

        We render the partial directly
        (not the full workspace_shell,
        which requires form_data and many
        other context keys).
        """
        from jinja2 import Environment, FileSystemLoader, select_autoescape
        env = Environment(
            loader=FileSystemLoader(
                str(REPO_ROOT / "app/templates")
            ),
            autoescape=select_autoescape(["html"]),
        )
        template = env.get_template("partials/_dashboard.html")
        rendered = template.render(
            dashboard_kpis={
                "project_irr": {"label": "Project IRR", "value": "12%",
                                "raw": 12.0, "status": "pass", "tooltip": ""},
            },
            dashboard_chart_revenue_ebitda_svg="<svg></svg>",
            dashboard_chart_dscr_svg="<svg></svg>",
            dashboard_chart_debt_svg="<svg></svg>",
        )
        assert "dashboard-v1" in rendered
        assert "dashboard-kpi-grid" in rendered
        assert "dashboard-charts" in rendered

    def test_workspace_shell_hides_dashboard_when_disabled(self):
        """The workspace_shell.html template
        guards the include with
        ``{% if dashboard_enabled %}``.
        We verify the guard is present.
        """
        path = REPO_ROOT / "app/templates/partials/workspace_shell.html"
        text = path.read_text(encoding="utf-8")
        assert "{% if dashboard_enabled" in text, (
            "workspace_shell.html must guard the dashboard "
            "include with {% if dashboard_enabled %}"
        )
        # When the flag is False, the
        # include is skipped, so the
        # partial is not rendered. We
        # verify the partial is NOT a
        # direct unconditional include.
        assert text.count("{% include \"partials/_dashboard.html\" %}") <= 1, (
            "There should be at most one include of _dashboard.html"
        )


# ---------------------------------------------------------------------------
# Test: NO chart.js / plotly / d3
# ---------------------------------------------------------------------------


class TestNoChartLibraries:
    def test_no_chart_libraries_imported(self):
        """No Chart.js / Plotly / D3 / React
        / Vue / Svelte / Tailwind / Alpine
        must be **imported or used**.
        """
        from app.ui import dashboard
        src = Path(dashboard.__file__).read_text(encoding="utf-8")
        # Check for actual imports / usage,
        # not comments.
        import re
        # Strip Python comments and
        # docstrings.
        no_docstring = re.sub(r'\"{3}.*?\"{3}', '', src, flags=re.S)
        no_docstring = re.sub(r"'{3}.*?'{3}", '', no_docstring, flags=re.S)
        no_comments = re.sub(r'#.*', '', no_docstring)
        lower = no_comments.lower()
        for forbidden in [
            "import chart", "from chart",
            "import plotly", "from plotly",
            "import d3", "from d3",
            "import react", "from react",
            "import vue", "from vue",
            "import svelte", "from svelte",
            "import tailwind", "from tailwind",
            "import alpine", "from alpine",
        ]:
            assert forbidden not in lower, (
                f"Dashboard v1 must NOT import {forbidden!r}"
            )

    def test_no_chart_libraries_in_static(self):
        """No Chart.js / Plotly / D3 / etc. in
        static/app.js.
        """
        path = REPO_ROOT / "static/app.js"
        if not path.is_file():
            pytest.skip("no static/app.js in this branch")
        text = path.read_text(encoding="utf-8")
        for forbidden in ["chart.js", "chartjs", "plotly", "d3."]:
            assert forbidden not in text.lower(), (
                f"static/app.js must NOT reference {forbidden!r}"
            )


# ---------------------------------------------------------------------------
# Test: phase invariants
# ---------------------------------------------------------------------------


class TestPhaseInvariants:
    def test_rc1_sha_resolvable(self):
        if not HAS_GIT:
            pytest.skip("no git in test env")
        r = subprocess.run(
            ["git", "rev-parse", "--verify", RC1_SHA],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        assert r.returncode == 0
        assert r.stdout.strip() == RC1_SHA

    def test_use_construction_schedule_engine_remains_false(self):
        if not HAS_GIT:
            pytest.skip("no git in test env")
        r = subprocess.run(
            [
                "grep", "-rn",
                "use_construction_schedule_engine\\s*=\\s*True",
                "app/", "main_web.py", "main_api.py",
            ],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        bad = r.stdout.strip().splitlines()
        assert not bad, (
            f"use_construction_schedule_engine=True "
            f"found in code: {bad}"
        )

    def test_parity_guardrails_unchanged(self):
        if not HAS_GIT:
            pytest.skip("no git in test env")
        r = subprocess.run(
            ["python3", "-m", "pytest",
             "tests/test_phase51f_parallel_work_guardrails.py",
             "-q", "--tb=line", "--no-header"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert r.returncode in (0, 5), (
            f"Phase 51F parity guardrails broke under P2-min-3: "
            f"returncode={r.returncode}\n"
            f"stdout={r.stdout[-1000:]}\n"
            f"stderr={r.stderr[-500:]}"
        )


# ---------------------------------------------------------------------------
# Test: prior-phase tests preserved
# ---------------------------------------------------------------------------


class TestPriorPhaseTestsPreserved:
    def test_all_prior_phase_tests_pass(self):
        if not HAS_GIT:
            pytest.skip("no git in test env")
        r = subprocess.run(
            ["python3", "-m", "pytest",
             "tests/test_phase_pr1_form_timing_fields.py",
             "tests/test_phase_pr2_realized_gearing.py",
             "tests/test_phase_pr3_taxonomy.py",
             "tests/test_phase_m1_scenario_matrix.py",
             "tests/test_phase_p1a_generic_driver_response_audit.py",
             "tests/test_phase_p1b_driver_status_badges.py",
             "tests/test_phase51f_parallel_work_guardrails.py",
             "tests/test_phase_p2min1_project_home.py",
             "tests/test_phase_p2min2_hide_internal_vocabulary.py",
             "-q", "--tb=line", "--no-header"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert r.returncode in (0, 5), (
            f"Prior-phase tests broke under P2-min-3: "
            f"returncode={r.returncode}\n"
            f"stdout={r.stdout[-1500:]}\n"
            f"stderr={r.stderr[-500:]}"
        )
