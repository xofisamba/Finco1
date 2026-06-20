"""U4 — Scenario Matrix MVP: unified entry point + Avg DSCR KPI row.

UI orchestration only. No new modelling, no scenario math changes.
These tests pin:
  - Avg DSCR added to KPI_ROWS (reads the existing pre-computed
    "avg_dscr" kpi key; no new computation).
  - The new read-only unified entry partial renders inside the
    Scenarios tab, surfacing the 7 headline KPIs across
    Base | Downside | Upside | Custom.
  - The unified entry partial does NOT duplicate the interactive
    scenario_matrix.html markup (no colliding DOM ids / hx-targets).
  - The original interactive matrix include stays in its pinned
    location inside panel-overview (Dashboard tab).
"""

from __future__ import annotations

import pathlib

import pytest

from app.ui.scenario_matrix import KPI_ROWS, ALL_ROWS, build_matrix_context

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

REQUIRED_KPI_LABELS = (
    "Revenue",
    "EBITDA",
    "Senior Debt",
    "Avg DSCR",
    "Min DSCR",
    "Project IRR",
    "Equity IRR",
)


class TestAvgDscrKpiRow:
    def test_avg_dscr_row_present_in_kpi_rows(self):
        labels = [row.label for row in KPI_ROWS]
        assert "Avg DSCR" in labels

    def test_avg_dscr_row_reads_existing_attr(self):
        row = next(r for r in KPI_ROWS if r.label == "Avg DSCR")
        assert row.attr == "avg_dscr"

    def test_avg_dscr_row_alongside_min_dscr(self):
        labels = [row.label for row in KPI_ROWS]
        assert "Min DSCR" in labels
        assert labels.index("Avg DSCR") < labels.index("Min DSCR")

    def test_all_required_kpi_labels_present(self):
        labels = [row.label for row in KPI_ROWS]
        for required in REQUIRED_KPI_LABELS:
            assert required in labels, f"missing required KPI row: {required}"

    def test_avg_dscr_formats_with_x_suffix(self):
        row = next(r for r in KPI_ROWS if r.label == "Avg DSCR")
        assert row.fmt(1.347) == "1.35x"

    def test_all_rows_invariant_inputs_then_kpis(self):
        # Locked invariant: input rows first, then KPI rows.
        from app.ui.scenario_matrix import INPUT_ROWS

        assert ALL_ROWS[: len(INPUT_ROWS)] == INPUT_ROWS
        assert ALL_ROWS[len(INPUT_ROWS):] == KPI_ROWS


class TestBuildMatrixContextWithAvgDscr:
    def test_avg_dscr_base_value_from_runtime_kpis(self):
        class FakeCtx:
            pass

        ctx = build_matrix_context(
            FakeCtx(), scenario_records=[], runtime_kpis={"avg_dscr": 1.5}
        )
        row_entry = next(
            e for e in ctx["matrix_rows"] if e["row"].label == "Avg DSCR"
        )
        assert row_entry["base"] == "1.50x"


class TestUnifiedEntryPartial:
    def test_partial_file_exists(self):
        path = REPO_ROOT / "app/templates/partials/_scenario_unified_entry.html"
        assert path.exists()

    def test_partial_has_unique_root_id(self):
        content = (
            REPO_ROOT / "app/templates/partials/_scenario_unified_entry.html"
        ).read_text()
        assert 'id="scenario-unified-entry"' in content

    def test_partial_does_not_duplicate_interactive_matrix_ids(self):
        content = (
            REPO_ROOT / "app/templates/partials/_scenario_unified_entry.html"
        ).read_text()
        # The interactive matrix's DOM ids must not appear here, or
        # HTMX hx-target wiring for M3/M4 inline-edit/run would collide.
        assert 'id="scenario-matrix-prototype"' not in content
        assert "matrix-run-badge-" not in content
        assert 'hx-target="this"' not in content

    def test_partial_links_to_compare(self):
        content = (
            REPO_ROOT / "app/templates/partials/_scenario_unified_entry.html"
        ).read_text()
        assert "switchTab('compare')" in content

    def test_partial_renders_with_matrix_context(self):
        from jinja2 import Environment, FileSystemLoader

        class FakeCtx:
            pass

        ctx = build_matrix_context(
            FakeCtx(), scenario_records=[], runtime_kpis={"avg_dscr": 1.5}
        )
        env = Environment(
            loader=FileSystemLoader(str(REPO_ROOT / "app/templates"))
        )
        template = env.get_template("partials/_scenario_unified_entry.html")
        html = template.render(**ctx)
        assert "Avg DSCR" in html
        assert "Revenue" in html
        assert "Equity IRR" in html


class TestWorkspaceShellWiring:
    def test_unified_entry_included_in_scenario_panel(self):
        content = (
            REPO_ROOT / "app/templates/partials/workspace_shell.html"
        ).read_text()
        assert (
            '{% include "partials/_scenario_unified_entry.html" %}' in content
        )

    def test_unified_entry_included_inside_panel_scenario(self):
        content = (
            REPO_ROOT / "app/templates/partials/workspace_shell.html"
        ).read_text()
        scenario_idx = content.index('id="panel-scenario"')
        include_idx = content.index(
            '{% include "partials/_scenario_unified_entry.html" %}'
        )
        scenario_tab_idx = content.index(
            '{% include "partials/scenario_tab.html" %}'
        )
        assert scenario_idx < include_idx < scenario_tab_idx

    def test_original_matrix_include_still_in_overview_panel(self):
        # Pinned by test_phase_m1_scenario_matrix.py too; re-asserted
        # here because U4 touches the same file.
        content = (
            REPO_ROOT / "app/templates/partials/workspace_shell.html"
        ).read_text()
        overview_idx = content.index('id="panel-overview"')
        matrix_idx = content.index(
            '{% include "partials/scenario_matrix.html" %}'
        )
        inputs_marker_idx = content.index(
            '<!-- ----------------------------------------------- INPUTS --'
        )
        assert overview_idx < matrix_idx < inputs_marker_idx
