"""UX-2C-1: Overview KPI deduplication.

Pins the requirements from the UX-2C-1 task:

  1. One canonical KPI surface (Dashboard v1 / ``_dashboard.html``)
     carries the required KPI labels: Project IRR, Equity IRR,
     Avg DSCR, Min DSCR, Revenue, EBITDA, Senior Debt, CAPEX.
  2. Project IRR / Equity IRR / Avg DSCR each appear only once in
     the normal (pre-run) Overview surface.
  3. The Run result response does not inject a second, immediately-
     visible duplicate KPI grid (the legacy runtime_summary.html
     KPI grid is collapsed by default behind a <details> disclosure,
     not removed/duplicated as a second open grid).
  4. The required KPI values are not removed from the app — only
     duplicate presentation is reduced.

No runtime/formula/persistence/export logic is touched by this
phase; these tests are presentation-only.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_TEMPLATES = REPO_ROOT / "app" / "templates"
DASHBOARD_PARTIAL = APP_TEMPLATES / "partials" / "_dashboard.html"
RUNTIME_SUMMARY_PARTIAL = APP_TEMPLATES / "partials" / "runtime_summary.html"

REQUIRED_KPI_LABELS = (
    "Project IRR",
    "Equity IRR",
    "Avg DSCR",
    "Min DSCR",
    "Y1 Revenue",
    "Y1 EBITDA",
    "Senior Debt",
    "CAPEX",
)


@pytest.fixture(scope="module")
def dashboard_kpis():
    from app.ui.dashboard import build_dashboard_kpis_from_raw_kpis

    raw_kpis = {
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
    return build_dashboard_kpis_from_raw_kpis(raw_kpis)


class TestDashboardKpisHaveAllRequiredLabels:
    def test_all_required_labels_present(self, dashboard_kpis):
        labels = {kpi["label"] for kpi in dashboard_kpis.values()}
        for required in REQUIRED_KPI_LABELS:
            assert required in labels, (
                f"Dashboard KPI dict is missing required label {required!r}; "
                f"got {sorted(labels)}"
            )

    def test_capex_kpi_uses_total_capex_keur(self, dashboard_kpis):
        assert dashboard_kpis["total_capex"]["label"] == "CAPEX"
        assert dashboard_kpis["total_capex"]["raw"] == 52800.0
        assert "52,800" in dashboard_kpis["total_capex"]["value"]

    def test_no_existing_kpi_value_removed(self, dashboard_kpis):
        # All 9 previously-existing keys remain present (CAPEX is
        # additive, not a replacement of any prior KPI).
        for key in (
            "project_irr", "equity_irr", "senior_debt",
            "realized_gearing", "min_dscr", "avg_dscr",
            "project_npv", "y1_revenue", "y1_ebitda",
        ):
            assert key in dashboard_kpis, f"missing pre-existing KPI key {key!r}"


class TestCanonicalDashboardGridRendersAllLabels:
    def test_dashboard_partial_renders_kpi_grid_markup(self):
        text = DASHBOARD_PARTIAL.read_text(encoding="utf-8")
        assert 'data-p2min3-kpi-grid="true"' in text
        assert "dashboard_kpis.items()" in text


class TestRuntimeSummaryDuplicateGridCollapsed:
    def test_legacy_kpi_grid_wrapped_in_collapsed_details(self):
        text = RUNTIME_SUMMARY_PARTIAL.read_text(encoding="utf-8")
        match = re.search(
            r'<details[^>]*data-runtime-kpi-detail="true"[^>]*>',
            text,
        )
        assert match is not None, (
            "runtime_summary.html's legacy KPI grid must be wrapped "
            "in a collapsed <details data-runtime-kpi-detail=\"true\"> "
            "element so it does not render as a second, immediately "
            "visible duplicate KPI grid after Run."
        )
        tag = match.group(0)
        assert "open" not in tag, (
            f"Legacy runtime_summary KPI detail must default to "
            f"collapsed (no 'open' attribute), got: {tag!r}"
        )

    def test_legacy_kpi_grid_still_contains_underlying_values(self):
        # The underlying values/derivation audit trail are preserved
        # (only the duplicate *presentation* is collapsed) so no KPI
        # value is removed from the app.
        text = RUNTIME_SUMMARY_PARTIAL.read_text(encoding="utf-8")
        assert 'id="kpi-grid"' in text
        assert 'id="kpi-project-irr"' in text
        assert 'id="kpi-equity-irr"' in text
        assert 'id="kpi-avg-dscr"' in text

    def test_provenance_banner_and_lifecycle_note_preserved(self):
        text = RUNTIME_SUMMARY_PARTIAL.read_text(encoding="utf-8")
        assert 'id="rs-provenance-banner"' in text
        assert "rs-lifecycle-note" in text
        assert "{{ runtime_summary.project_name }}" in text
        assert "{{ runtime_summary.ran_at }}" in text


class TestFileScope:
    ALLOWED_PREFIXES = (
        "app/templates/partials/runtime_summary.html",
        "app/ui/dashboard.py",
        "tests/test_ux2c1_",
        "tests/test_p1_compare_validation.py",
        "tests/test_phase_m1_",
        "tests/test_phase_m2_",
        "tests/test_phase_m3_",
        "tests/test_phase_m4_",
        "tests/test_phase_p2fix",
        "tests/test_phase_pr1_",
        "tests/test_phase_pr2_",
        "tests/test_phase_pr3_",
        "tests/test_phase_scenario1_",
        "tests/test_phase_stab",
        "tests/test_phase_ux2_",
        "tests/test_phase_ux4cde_",
    )
    DISALLOWED_PREFIXES = (
        "domain/",
        "app/waterfall_core.py",
        "app/input_adapter.py",
        "app/project_factories.py",
        "app/persistence/",
        "app/excel_export.py",
        "app/export/",
        "main_api.py",
    )

    def test_only_allowed_files_changed(self):
        import shutil
        if shutil.which("git") is None or not (REPO_ROOT / ".git").exists():
            pytest.skip("git not available")
        result = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "diff", "--name-only", "origin/main"],
            capture_output=True, text=True,
        )
        changed = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
        for f in changed:
            assert not any(f.startswith(p) for p in self.DISALLOWED_PREFIXES), (
                f"UX-2C-1 must not touch {f}"
            )
            assert any(f.startswith(p) for p in self.ALLOWED_PREFIXES), (
                f"UX-2C-1 file outside allowed scope: {f}"
            )
