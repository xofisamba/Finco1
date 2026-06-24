"""Phase M2 — Live Scenario Matrix tests.

M2 upgrades the M1 read-only prototype to show live scenario
data in the Downside / Upside / Custom columns. Non-Base columns
now populate from existing ScenarioRecord objects passed into
build_matrix_context(). No new persistence, no new engine calls,
no new ScenarioOverride model.

Hard constraints verified here:

- Engine MD5 unchanged (waterfall_core.py).
- No new persistence schema (no new tables, no migrations).
- No app.js changes.
- No main_api.py changes.
- No factory path changes (TUHO / Oborovo parity).
- build_matrix_context() reads existing ScenarioRecord fields:
  overrides, snapshot, base_input_set, last_run_summary.
- Base column still reads from project_ctx.
- Non-Base columns fall back to em-dash when data is absent.
- Column assignment: first 3 non-base-case scenarios go to
  Downside, Upside, Custom in order.
- m2_live flag is True only when at least one non-Base column
  has a real scenario record assigned.

File scope: only allowed files changed.
"""

from __future__ import annotations

import hashlib
import os
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
HERE = str(REPO_ROOT / "tests")

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-key-m2")

from app.ui.scenario_matrix import (
    ALL_ROWS,
    INPUT_ROWS,
    KPI_ROWS,
    NON_BASE_PLACEHOLDER,
    build_matrix_context,
    get_scenario_cell_value,
)

ENGINE_MD5 = "6bf49f33efc989736c17cea0cb9b7723"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_scenario(
    name="Downside",
    is_base_case=False,
    snapshot=None,
    overrides=None,
    base_input_set=None,
    last_run_summary=None,
):
    """Build a minimal ScenarioRecord-like namespace."""
    return SimpleNamespace(
        scenario_name=name,
        is_base_case=is_base_case,
        snapshot=snapshot or {},
        overrides=overrides or {},
        base_input_set=base_input_set or {},
        last_run_summary=last_run_summary or {},
    )


def _make_ctx(**kwargs):
    """Build a minimal project_ctx-like namespace."""
    return SimpleNamespace(**kwargs)


# ---------------------------------------------------------------------------
# 1. Engine parity
# ---------------------------------------------------------------------------

class TestEngineParity:
    def test_engine_md5_unchanged(self):
        md5 = hashlib.md5(
            (REPO_ROOT / "app" / "waterfall_core.py").read_bytes()
        ).hexdigest()
        assert md5 == ENGINE_MD5, (
            f"waterfall_core.py MD5 changed: {md5!r} != {ENGINE_MD5!r}"
        )


# ---------------------------------------------------------------------------
# 2. build_matrix_context — column assignment
# ---------------------------------------------------------------------------

class TestColumnAssignment:
    def test_no_scenarios_all_none(self):
        ctx = _make_ctx(ppa_tariff_eur_mwh=80.0)
        result = build_matrix_context(ctx, [])
        assert result["col_downside"] is None
        assert result["col_upside"] is None
        assert result["col_custom"] is None
        assert result["m2_live"] is False

    def test_base_only_not_assigned_to_columns(self):
        ctx = _make_ctx(ppa_tariff_eur_mwh=80.0)
        base = _make_scenario("Base", is_base_case=True)
        result = build_matrix_context(ctx, [base])
        assert result["col_downside"] is None
        assert result["col_upside"] is None
        assert result["col_custom"] is None
        assert result["m2_live"] is False

    def test_one_non_base_goes_to_downside(self):
        ctx = _make_ctx(ppa_tariff_eur_mwh=80.0)
        s1 = _make_scenario("Downside")
        result = build_matrix_context(ctx, [s1])
        assert result["col_downside"] is s1
        assert result["col_upside"] is None
        assert result["col_custom"] is None
        assert result["m2_live"] is True

    def test_two_non_base_goes_to_downside_and_upside(self):
        ctx = _make_ctx(ppa_tariff_eur_mwh=80.0)
        s1 = _make_scenario("Downside")
        s2 = _make_scenario("Upside")
        result = build_matrix_context(ctx, [s1, s2])
        assert result["col_downside"] is s1
        assert result["col_upside"] is s2
        assert result["col_custom"] is None
        assert result["m2_live"] is True

    def test_three_non_base_fills_all_columns(self):
        ctx = _make_ctx(ppa_tariff_eur_mwh=80.0)
        s1 = _make_scenario("Downside")
        s2 = _make_scenario("Upside")
        s3 = _make_scenario("Custom")
        result = build_matrix_context(ctx, [s1, s2, s3])
        assert result["col_downside"] is s1
        assert result["col_upside"] is s2
        assert result["col_custom"] is s3
        assert result["m2_live"] is True

    def test_extra_scenarios_ignored(self):
        ctx = _make_ctx(ppa_tariff_eur_mwh=80.0)
        scenarios = [_make_scenario(f"S{i}") for i in range(6)]
        result = build_matrix_context(ctx, scenarios)
        assert result["col_downside"] is scenarios[0]
        assert result["col_upside"] is scenarios[1]
        assert result["col_custom"] is scenarios[2]

    def test_base_case_mixed_with_non_base(self):
        ctx = _make_ctx(ppa_tariff_eur_mwh=80.0)
        base = _make_scenario("Base", is_base_case=True)
        s1 = _make_scenario("Downside")
        result = build_matrix_context(ctx, [base, s1])
        assert result["col_downside"] is s1
        assert result["col_upside"] is None


# ---------------------------------------------------------------------------
# 3. build_matrix_context — Base column still from project_ctx
# ---------------------------------------------------------------------------

class TestBaseColumnFromCtx:
    def test_base_column_reads_ctx(self):
        ctx = _make_ctx(ppa_tariff_eur_mwh=92.5)
        result = build_matrix_context(ctx, [])
        tariff_row = next(r for r in result["matrix_rows"] if r["row"].attr == "ppa_tariff_eur_mwh")
        assert "92" in tariff_row["base"]
        assert "EUR/MWh" in tariff_row["base"]

    def test_base_column_none_ctx_shows_em_dash(self):
        result = build_matrix_context(None, [])
        for entry in result["matrix_rows"]:
            assert entry["base"] == "—"

    def test_base_column_missing_attr_shows_em_dash(self):
        ctx = _make_ctx()  # no attributes at all
        result = build_matrix_context(ctx, [])
        for entry in result["matrix_rows"]:
            assert entry["base"] == "—"


# ---------------------------------------------------------------------------
# 4. get_scenario_cell_value — input rows read from snapshot hierarchy
# ---------------------------------------------------------------------------

class TestScenarioInputValue:
    def test_reads_from_overrides_first(self):
        row = INPUT_ROWS[0]  # ppa_tariff_eur_mwh
        s = _make_scenario(
            overrides={row.attr: 55.0},
            snapshot={row.attr: 70.0},
            base_input_set={row.attr: 80.0},
        )
        val = get_scenario_cell_value(s, row)
        assert "55" in val

    def test_falls_back_to_snapshot(self):
        row = INPUT_ROWS[0]
        s = _make_scenario(
            overrides={},
            snapshot={row.attr: 70.0},
            base_input_set={row.attr: 80.0},
        )
        val = get_scenario_cell_value(s, row)
        assert "70" in val

    def test_falls_back_to_base_input_set(self):
        row = INPUT_ROWS[0]
        s = _make_scenario(
            overrides={},
            snapshot={},
            base_input_set={row.attr: 80.0},
        )
        val = get_scenario_cell_value(s, row)
        assert "80" in val

    def test_em_dash_when_no_data(self):
        row = INPUT_ROWS[0]
        s = _make_scenario()
        val = get_scenario_cell_value(s, row)
        assert val == NON_BASE_PLACEHOLDER

    def test_none_scenario_returns_em_dash(self):
        row = INPUT_ROWS[0]
        val = get_scenario_cell_value(None, row)
        assert val == NON_BASE_PLACEHOLDER


# ---------------------------------------------------------------------------
# 5. get_scenario_cell_value — KPI rows read from last_run_summary
# ---------------------------------------------------------------------------

class TestScenarioKpiValue:
    def test_reads_kpi_from_last_run_summary_kpis_key(self):
        row = KPI_ROWS[0]  # total_revenue_keur
        s = _make_scenario(last_run_summary={"kpis": {row.attr: 12345.0}})
        val = get_scenario_cell_value(s, row)
        assert "12" in val  # formatted kEUR

    def test_reads_kpi_direct_from_summary(self):
        row = KPI_ROWS[0]
        s = _make_scenario(last_run_summary={row.attr: 99999.0})
        val = get_scenario_cell_value(s, row)
        assert "99" in val

    def test_em_dash_when_no_run_summary(self):
        row = KPI_ROWS[0]
        s = _make_scenario(last_run_summary={})
        val = get_scenario_cell_value(s, row)
        assert val == NON_BASE_PLACEHOLDER

    def test_none_scenario_kpi_returns_em_dash(self):
        row = KPI_ROWS[0]
        val = get_scenario_cell_value(None, row)
        assert val == NON_BASE_PLACEHOLDER


# ---------------------------------------------------------------------------
# 6. matrix_rows shape
# ---------------------------------------------------------------------------

class TestMatrixRowsShape:
    def test_matrix_rows_count(self):
        ctx = _make_ctx()
        result = build_matrix_context(ctx, [])
        assert len(result["matrix_rows"]) == len(ALL_ROWS)

    def test_inputs_section_before_kpi_section(self):
        ctx = _make_ctx()
        result = build_matrix_context(ctx, [])
        rows = result["matrix_rows"]
        input_indices = [i for i, r in enumerate(rows) if r["section"] == "Inputs"]
        kpi_indices = [i for i, r in enumerate(rows) if r["section"] == "Outputs (KPIs)"]
        assert input_indices
        assert kpi_indices
        assert max(input_indices) < min(kpi_indices)

    def test_per_row_live_flags_true_when_scenario_assigned(self):
        ctx = _make_ctx()
        s1 = _make_scenario("Downside")
        result = build_matrix_context(ctx, [s1])
        for entry in result["matrix_rows"]:
            assert entry["downside_live"] is True
            assert entry["upside_live"] is False
            assert entry["custom_live"] is False

    def test_per_row_live_flags_false_when_no_scenarios(self):
        ctx = _make_ctx()
        result = build_matrix_context(ctx, [])
        for entry in result["matrix_rows"]:
            assert entry["downside_live"] is False
            assert entry["upside_live"] is False
            assert entry["custom_live"] is False


# ---------------------------------------------------------------------------
# 7. Template renders M2 attributes
# ---------------------------------------------------------------------------

class TestTemplateM2Attributes:
    def test_data_m2_matrix_attribute_present(self):
        tmpl = (REPO_ROOT / "app" / "templates" / "partials" / "scenario_matrix.html").read_text()
        assert 'data-m2-matrix="true"' in tmpl

    def test_data_m2_cell_downside_present(self):
        tmpl = (REPO_ROOT / "app" / "templates" / "partials" / "scenario_matrix.html").read_text()
        assert 'data-m2-cell="downside"' in tmpl

    def test_data_m2_cell_upside_present(self):
        tmpl = (REPO_ROOT / "app" / "templates" / "partials" / "scenario_matrix.html").read_text()
        assert 'data-m2-cell="upside"' in tmpl

    def test_data_m2_cell_custom_present(self):
        tmpl = (REPO_ROOT / "app" / "templates" / "partials" / "scenario_matrix.html").read_text()
        assert 'data-m2-cell="custom"' in tmpl

    def test_matrix_rows_jinja_loop_present(self):
        tmpl = (REPO_ROOT / "app" / "templates" / "partials" / "scenario_matrix.html").read_text()
        assert "for entry in matrix_rows" in tmpl

    def test_col_downside_conditional_present(self):
        tmpl = (REPO_ROOT / "app" / "templates" / "partials" / "scenario_matrix.html").read_text()
        assert "col_downside" in tmpl

    def test_m2_live_conditional_present(self):
        tmpl = (REPO_ROOT / "app" / "templates" / "partials" / "scenario_matrix.html").read_text()
        assert "m2_live" in tmpl


# ---------------------------------------------------------------------------
# 8. CSS for M2 states
# ---------------------------------------------------------------------------

class TestM2CSS:
    def test_badge_m2_live_defined(self):
        css = (REPO_ROOT / "static" / "styles.css").read_text()
        assert ".badge-m2-live" in css

    def test_badge_m2_scenario_defined(self):
        css = (REPO_ROOT / "static" / "styles.css").read_text()
        assert ".badge-m2-scenario" in css

    def test_matrix_cell_scenario_defined(self):
        css = (REPO_ROOT / "static" / "styles.css").read_text()
        assert ".matrix-cell-scenario" in css

    def test_m2_marker_in_css(self):
        css = (REPO_ROOT / "static" / "styles.css").read_text()
        assert "M2" in css


# ---------------------------------------------------------------------------
# 9. Workspace renders M2 context (integration smoke test)
# ---------------------------------------------------------------------------

class TestWorkspaceIntegration:
    @pytest.fixture(scope="class")
    def workspace_html(self):
        from fastapi.testclient import TestClient
        from app.auth import create_session_token
        from main_web import app
        c = TestClient(app, follow_redirects=True)
        token = create_session_token(user_id="m2_user", username="m2_user")
        c.cookies.set("finco_session", token)
        r = c.get("/?project=tuho")
        assert r.status_code == 200
        return r.text

    def test_matrix_card_present(self, workspace_html):
        assert 'data-m2-matrix="true"' in workspace_html

    def test_matrix_table_present(self, workspace_html):
        assert 'data-m2-table="scenario-matrix"' in workspace_html

    def test_base_column_header_present(self, workspace_html):
        assert 'data-m2-column="Base"' in workspace_html

    def test_non_base_column_headers_present(self, workspace_html):
        assert 'data-m2-column="Downside"' in workspace_html
        assert 'data-m2-column="Upside"' in workspace_html
        assert 'data-m2-column="Custom"' in workspace_html


# ---------------------------------------------------------------------------
# 10. File scope
# ---------------------------------------------------------------------------

class TestFileScope:
    def test_only_allowed_files_changed(self):
        import shutil
        import subprocess
        if shutil.which("git") is None or not (REPO_ROOT / ".git").exists():
            pytest.skip("git not available")
        result = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "diff", "--name-only", "origin/main"],
            capture_output=True, text=True,
        )
        changed = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
        allowed_prefixes = (
            "app/ui/scenario_matrix.py",
            "app/templates/partials/scenario_matrix.html",
            # U4-SCENARIO-MATRIX-MVP cross-arc allowlist
            "app/templates/partials/_scenario_unified_entry.html",
            "app/templates/partials/workspace_shell.html",
            "tests/test_u4_",
            "main_web.py",
            "static/styles.css",
            "tests/test_phase_m2_",
            "tests/test_phase_m1_",
            "tests/test_phase_wf1_",
            "tests/test_phase_wf2_",
            "tests/test_phase_wf3_",
            "tests/test_phase_wf4_",
            "tests/test_phase_wf5_",
            "tests/test_phase_wf6_",
            "app/templates/partials/_nav_compression.html",
            "app/templates/partials/scenario_tab.html",
            "tests/test_phase_p2fix",
            "app/templates/partials/_results_subnav.html",
            "app/templates/partials/project_selector.html",
            "app/templates/partials/project_home.html",
            "app/templates/partials/new_project_minimal.html",
            "app/templates/partials/new_project_result.html",
            "app/ui/dashboard.py",
            "app/templates/partials/_dashboard_oob.html",
            "tests/test_phase_m3_",
            "tests/test_phase_m4_",
            "tests/test_phase_stab",
            "app/templates/partials/_scenario_matrix_oob.html",
            "app/ui/dashboard.py",
            "app/templates/partials/_matrix_cell_updated.html",
            "app/templates/partials/_matrix_cell_edit.html",
            "app/templates/partials/_matrix_run_result.html",
            "tests/test_phase_pr1_",
            "tests/test_phase_pr2_",
            "tests/test_phase_pr3_",
            "app/templates/partials/runtime_summary.html",  # UX-2C-1 cross-arc
            "app/ui/dashboard.py",  # UX-2C-1 cross-arc
            "tests/",  # UX-2C-1 cross-arc (branch-wide test footprint)
        )
        disallowed_prefixes = (
            "app/persistence/",
            "app/services/",
            "app/waterfall_core.py",
            "app/project_factories.py",
            "app/excel_export.py",
            "main_api.py",
            "static/app.js",
        )
        for f in changed:
            assert not any(f.startswith(p) for p in disallowed_prefixes), (
                f"Disallowed file changed: {f}"
            )
            assert any(f.startswith(p) for p in allowed_prefixes), (
                f"File outside allowed scope: {f}"
            )
