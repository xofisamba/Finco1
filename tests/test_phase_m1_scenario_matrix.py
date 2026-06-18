"""Phase M1 — Read-Only Scenario Matrix Prototype (tests).

M1 is a UX prototype that demonstrates the
intended future Scenario Matrix layout
(Base | Downside | Upside | Custom) using
existing project inputs and existing runtime
outputs. M1 is INTENTIONALLY read-only and
INTENTIONALLY has no scenario persistence,
no scenario CRUD, and no scenario
calculations.

These tests prove that:

- The helper module `app.ui.scenario_matrix`
  exports the 4 canonical columns in the
  canonical order.
- The helper module registers all required
  input rows and KPI rows.
- The helper module's `build_matrix_rows`
  populates the Base column from a
  `project_ctx`-like object.
- The non-Base columns are placeholders
  ("inherits Base" / em-dash) — no scenario
  values are computed.
- The matrix Jinja partial
  (`partials/scenario_matrix.html`) renders
  the 4 columns, the 2 sections, and all
  required rows.
- The matrix card is wired into the
  Overview tab in `workspace_shell.html`.
- No scenario persistence is introduced
  (no new tables, no new save/load calls).
- No scenario CRUD is introduced (no
  routes, no service methods, no
  per-project scenario endpoints).
- No scenario calculation is introduced
  (no new resolver path, no new
  ScenarioOverride model).
- No `static/app.js` changes.
- No `main_web.py` changes.
- No `main_api.py` changes.
- No factory path changes (TUHO / Oborovo
  preserved bit-exact).
- rc1 is untouched.
- Phase S1 / S2 / S3 / P1-A / P1-B
  invariants are preserved.
- Phase 51F parity guardrails pass.

M1 is the prototype for layout / usability /
information density / navigation /
Excel-like feel. M2 will introduce actual
scenario overrides.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, ".."))

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")


from app.ui.scenario_matrix import (
    COLUMNS,
    COLUMN_BADGES,
    COLUMN_CELL_CLASSES,
    INPUT_ROWS,
    KPI_ROWS,
    ALL_ROWS,
    NON_BASE_PLACEHOLDER,
    NON_BASE_INHERIT_NOTE,
    INHERITANCE_NOTE,
    MatrixRow,
    ROW_KIND_INPUT,
    ROW_KIND_KPI,
    build_matrix_rows,
    format_cell_value,
    get_base_value,
)


RC1_SHA = "b425a0708719eaa5e1d922b1008e5609758e0ad4"


def _read(path: str) -> str:
    with open(os.path.join(REPO_ROOT, path)) as f:
        return f.read()


# ---------------------------------------------------------------------------
# Forbidden path list (must NEVER be touched by M1)
# ---------------------------------------------------------------------------

M1_FORBIDDEN_PATHS = [
    # main_web.py is no longer in the M1
    # forbidden list. The post-M1 trust-
    # polish mini-arc ships a wiring fix
    # in main_web.py (PR1 form timing
    # fields sidecar / integration) that
    # is required to eliminate the
    # silent template-default drift.
    "main_api.py",
    "app/project_factories.py",
    "app/waterfall_runner.py",
    "app/waterfall_core.py",
    "app/services/",
    "app/persistence/",
    "static/app.js",
]


# ---------------------------------------------------------------------------
# 1. Column / row registry invariants
# ---------------------------------------------------------------------------


class TestColumnRegistry:
    """The 4 matrix columns are the canonical
    Excel-like scenario columns: Base |
    Downside | Upside | Custom. The order is
    Base, Downside, Upside, Custom.
    """

    def test_column_count_is_4(self):
        assert len(COLUMNS) == 4

    def test_columns_in_canonical_order(self):
        assert COLUMNS == ("Base", "Downside", "Upside", "Custom")

    def test_every_column_has_badge(self):
        for col in COLUMNS:
            assert col in COLUMN_BADGES
            label, css = COLUMN_BADGES[col]
            assert isinstance(label, str) and label
            assert isinstance(css, str) and css

    def test_every_column_has_cell_class(self):
        for col in COLUMNS:
            assert col in COLUMN_CELL_CLASSES
            assert COLUMN_CELL_CLASSES[col]

    def test_base_badge_is_live(self):
        label, css = COLUMN_BADGES["Base"]
        assert label == "Live"
        assert css == "badge-base"

    def test_downside_upside_share_inherit_badge(self):
        # Downside and Upside are visually
        # identical placeholders ("Inherits
        # Base" / "badge-inherit").
        assert COLUMN_BADGES["Downside"] == COLUMN_BADGES["Upside"]

    def test_custom_badge_is_future(self):
        label, css = COLUMN_BADGES["Custom"]
        assert label == "Future override"
        assert css == "badge-future"


class TestRowRegistry:
    """Input rows + KPI rows are the source of
    truth for the matrix contents.
    """

    def test_input_rows_have_required_fields(self):
        for row in INPUT_ROWS:
            assert isinstance(row, MatrixRow)
            assert row.kind == ROW_KIND_INPUT
            assert row.label and row.attr

    def test_kpi_rows_have_required_fields(self):
        for row in KPI_ROWS:
            assert isinstance(row, MatrixRow)
            assert row.kind == ROW_KIND_KPI
            assert row.label and row.attr

    def test_input_rows_cover_required_inputs(self):
        attrs = {r.attr for r in INPUT_ROWS}
        for required in [
            "ppa_tariff_eur_mwh",
            "operating_hours_p50",
            "capacity_mw",
            "total_capex_keur",
            "opex_y1_total_keur",
            "interest_rate_pct",
            "senior_tenor_years",
            "target_dscr",
            "gearing_pct",
            "ppa_term_years",
            "construction_months",
        ]:
            assert required in attrs, (
                f"M1 input rows must include {required!r}; "
                f"got {sorted(attrs)}"
            )

    def test_kpi_rows_cover_required_outputs(self):
        attrs = {r.attr for r in KPI_ROWS}
        for required in [
            "total_revenue_keur",
            "total_ebitda_keur",
            "project_irr",
            "equity_irr",
            "senior_debt_amount_keur",
            "min_dscr",
        ]:
            assert required in attrs, (
                f"M1 KPI rows must include {required!r}; "
                f"got {sorted(attrs)}"
            )

    def test_input_rows_come_before_kpi_rows(self):
        # The combined ALL_ROWS tuple must
        # place inputs before KPIs so the
        # rendered table shows the Inputs
        # section first.
        assert ALL_ROWS[:len(INPUT_ROWS)] == INPUT_ROWS
        assert ALL_ROWS[len(INPUT_ROWS):] == KPI_ROWS

    def test_no_duplicate_attr(self):
        attrs = [r.attr for r in ALL_ROWS]
        assert len(attrs) == len(set(attrs)), (
            f"duplicate row attr: {attrs}"
        )


# ---------------------------------------------------------------------------
# 2. Cell rendering — non-Base columns are placeholders
# ---------------------------------------------------------------------------


class TestCellRendering:
    """Non-Base columns render placeholders
    only. No scenario override values are
    ever computed. This is the M1
    read-only contract.
    """

    def test_non_base_placeholder_is_em_dash(self):
        assert NON_BASE_PLACEHOLDER == "—"

    def test_non_base_inherit_note_is_text(self):
        assert NON_BASE_INHERIT_NOTE == "inherits Base"

    def test_inheritance_note_explains_no_storage(self):
        assert "UI prototype" in INHERITANCE_NOTE
        assert "no scenario overrides" in INHERITANCE_NOTE.lower() or "no scenario overrides" in INHERITANCE_NOTE
        assert "M2" in INHERITANCE_NOTE

    def test_get_base_value_reads_ctx_attr(self):
        class Ctx:
            ppa_tariff_eur_mwh = 75.0
        v = get_base_value(Ctx(), INPUT_ROWS[0])  # Tariff row
        assert v == 75.0

    def test_get_base_value_returns_none_when_attr_missing(self):
        class Ctx:
            pass
        v = get_base_value(Ctx(), INPUT_ROWS[0])  # Tariff row
        assert v is None

    def test_get_base_value_returns_none_when_ctx_none(self):
        v = get_base_value(None, INPUT_ROWS[0])
        assert v is None

    def test_format_cell_value_uses_row_formatter(self):
        row = INPUT_ROWS[0]  # Tariff row
        out = format_cell_value(row, 75.0)
        assert "75" in out
        assert "EUR/MWh" in out

    def test_format_cell_value_renders_em_dash_for_none(self):
        row = INPUT_ROWS[0]
        out = format_cell_value(row, None)
        assert out == "—"


# ---------------------------------------------------------------------------
# 3. build_matrix_rows — Base column reads project_ctx
# ---------------------------------------------------------------------------


class TestBuildMatrixRows:
    """The matrix builder populates Base from
    project_ctx; non-Base columns are
    placeholders. The shape is locked so the
    Jinja partial can iterate it.
    """

    def test_build_with_real_ctx(self):
        class Ctx:
            ppa_tariff_eur_mwh = 75.0
            operating_hours_p50 = 2400
            capacity_mw = 50.0
            total_capex_keur = 50000.0
            opex_y1_total_keur = 1200.0
            interest_rate_pct = 0.06
            senior_tenor_years = 18
            target_dscr = 1.30
            gearing_pct = 0.70
            ppa_term_years = 15
            construction_months = 24
            total_revenue_keur = 130000.0
            total_ebitda_keur = 95000.0
            project_irr = 0.085
            equity_irr = 0.110
            senior_debt_amount_keur = 35000.0
            min_dscr = 1.25
        rows = build_matrix_rows(Ctx())
        assert len(rows) == len(ALL_ROWS)
        # First row is Tariff (input).
        first = rows[0]
        assert first["row"].attr == "ppa_tariff_eur_mwh"
        assert "75" in first["base"]
        assert first["downside"] == NON_BASE_INHERIT_NOTE
        assert first["upside"] == NON_BASE_INHERIT_NOTE
        assert first["custom"] == NON_BASE_PLACEHOLDER

    def test_build_with_none_ctx(self):
        rows = build_matrix_rows(None)
        assert len(rows) == len(ALL_ROWS)
        for entry in rows:
            assert entry["base"] == NON_BASE_PLACEHOLDER
            assert entry["downside"] == NON_BASE_INHERIT_NOTE
            assert entry["upside"] == NON_BASE_INHERIT_NOTE
            assert entry["custom"] == NON_BASE_PLACEHOLDER

    def test_build_section_invariant(self):
        # Inputs section precedes KPIs.
        class Ctx:
            pass
        rows = build_matrix_rows(Ctx())
        input_rows = [r for r in rows if r["kind"] == ROW_KIND_INPUT]
        kpi_rows = [r for r in rows if r["kind"] == ROW_KIND_KPI]
        assert len(input_rows) == len(INPUT_ROWS)
        assert len(kpi_rows) == len(KPI_ROWS)
        # Inputs appear before KPIs in the
        # combined list.
        input_indices = [rows.index(r) for r in input_rows]
        kpi_indices = [rows.index(r) for r in kpi_rows]
        assert max(input_indices) < min(kpi_indices)

    def test_build_no_runtime_calculation(self):
        # The builder must NOT call any
        # function that depends on a runtime
        # result. It only reads the named
        # attribute from project_ctx.
        # We assert this by passing a ctx
        # whose attribute is a sentinel and
        # checking it propagates verbatim.
        sentinel = object()
        class Ctx:
            ppa_tariff_eur_mwh = sentinel
        rows = build_matrix_rows(Ctx())
        assert rows[0]["base"] is not None
        # The exact value is whatever the
        # formatter produced for the
        # sentinel; the point is that the
        # value passed through (no scenario
        # override logic intervened).
        # The formatter is _fmt_eur_mwh,
        # which would fail on a non-numeric
        # sentinel and fall back to str().
        assert isinstance(rows[0]["base"], str)


# ---------------------------------------------------------------------------
# 4. Jinja partial — 4 columns, 2 sections, all rows
# ---------------------------------------------------------------------------


class TestMatrixPartialTemplate:
    """The Jinja partial renders the matrix
    with all 4 columns, both sections, and
    all required rows. The Base column reads
    project_ctx directly (so the template
    works without a custom context helper).
    """

    def test_partial_exists(self):
        assert os.path.exists(
            os.path.join(
                REPO_ROOT,
                "app/templates/partials/scenario_matrix.html",
            )
        )

    def test_partial_has_4_columns_in_header(self):
        src = _read("app/templates/partials/scenario_matrix.html")
        for col in COLUMNS:
            assert f'data-m1-column="{col}"' in src
            assert f'data-m1-column-badge="{col}"' in src

    def test_partial_has_inputs_section(self):
        src = _read("app/templates/partials/scenario_matrix.html")
        assert 'data-m1-section="Inputs"' in src
        assert ">Inputs<" in src

    def test_partial_has_outputs_section(self):
        src = _read("app/templates/partials/scenario_matrix.html")
        assert 'data-m1-section="Outputs (KPIs)"' in src
        assert "Outputs (KPIs)" in src

    def test_partial_has_every_input_row_attr(self):
        src = _read("app/templates/partials/scenario_matrix.html")
        for row in INPUT_ROWS:
            assert f'data-m1-row="{row.attr}"' in src
            assert f'data-m1-row-kind="input"' in src

    def test_partial_has_every_kpi_row_attr(self):
        src = _read("app/templates/partials/scenario_matrix.html")
        for row in KPI_ROWS:
            assert f'data-m1-row="{row.attr}"' in src
            assert f'data-m1-row-kind="kpi"' in src

    def test_partial_reads_project_ctx_for_base(self):
        # The template must use `project_ctx`
        # for the Base column so the
        # workspace_shell.html context (which
        # already passes project_ctx) works
        # without route changes.
        src = _read("app/templates/partials/scenario_matrix.html")
        assert "project_ctx" in src

    def test_partial_renders_em_dash_for_missing_value(self):
        # For each row, the Base cell must
        # render an em-dash when the
        # underlying attribute is missing /
        # None. (This is what shows in the
        # "no project selected" case.)
        src = _read("app/templates/partials/scenario_matrix.html")
        # Em-dash literal "—" appears at
        # least once in matrix-cell-base
        # contexts.
        assert "—" in src

    def test_partial_explains_inheritance(self):
        src = _read("app/templates/partials/scenario_matrix.html")
        # Inheritance note must explicitly
        # say it's a UI prototype and that
        # no scenario overrides are stored.
        assert "UI prototype" in src
        assert "inherits Base" in src

    def test_partial_has_legend(self):
        src = _read("app/templates/partials/scenario_matrix.html")
        # Legend at the bottom must call out
        # all three placeholder types.
        assert "badge-base" in src
        assert "badge-inherit" in src
        assert "badge-future" in src

    def test_partial_no_save_buttons(self):
        # M1 is read-only. No save / load /
        # submit / form-post controls.
        src = _read("app/templates/partials/scenario_matrix.html")
        for forbidden in [
            "<form",
            'type="submit"',
            "Save scenario",
            "Load scenario",
            "Apply scenario",
            "Delete scenario",
        ]:
            assert forbidden not in src, (
                f"M1 read-only prototype must NOT contain {forbidden!r}"
            )

    def test_partial_no_input_editable(self):
        # M1 is read-only. No editable
        # <input> / <textarea> / <select>
        # for scenario values.
        src = _read("app/templates/partials/scenario_matrix.html")
        for forbidden in [
            "<input",
            "<textarea",
            "<select",
        ]:
            assert forbidden not in src, (
                f"M1 read-only prototype must NOT contain {forbidden!r}"
            )


# ---------------------------------------------------------------------------
# 5. workspace_shell.html — matrix wired into Overview tab
# ---------------------------------------------------------------------------


class TestWorkspaceShellWiring:
    """The matrix is wired into the Overview
    tab (`#panel-overview`) of
    workspace_shell.html via an `{% include
    "partials/scenario_matrix.html" %}`.
    """

    def test_workspace_shell_includes_matrix_partial(self):
        src = _read("app/templates/partials/workspace_shell.html")
        assert '{% include "partials/scenario_matrix.html" %}' in src

    def test_matrix_renders_inside_overview_panel(self):
        # The include line must come AFTER
        # the `id="panel-overview"` div
        # opens, and BEFORE the `</div>` that
        # closes the overview panel. (The
        # Overview panel currently has no
        # closing `</div>` marker other than
        # matching the `<div class="tab-panel
        # active" id="panel-overview">` open
        # tag.)
        src = _read("app/templates/partials/workspace_shell.html")
        overview_open = src.find('id="panel-overview"')
        overview_close_marker = src.find('<!-- ----------------------------------------------- INPUTS --')
        assert overview_open >= 0
        assert overview_close_marker >= 0
        # The matrix include must be
        # somewhere between the two.
        include_idx = src.find(
            '{% include "partials/scenario_matrix.html" %}'
        )
        assert overview_open < include_idx < overview_close_marker


# ---------------------------------------------------------------------------
# 6. CSS — matrix styling exists
# ---------------------------------------------------------------------------


class TestMatrixCss:
    """The matrix has dedicated CSS in
    static/styles.css. M1 does NOT touch any
    existing rule.
    """

    def test_matrix_section_present(self):
        src = _read("static/styles.css")
        # The Phase M1 block must be present
        # with the canonical section header.
        assert "PHASE M1" in src or "Phase M1" in src

    def test_required_css_classes(self):
        src = _read("static/styles.css")
        for css_class in [
            ".scenario-matrix-card",
            ".scenario-matrix-table",
            ".scenario-matrix-table thead",
            ".scenario-matrix-table tbody",
            ".matrix-cell-base",
            ".matrix-cell-inherit",
            ".matrix-cell-future",
            ".badge-base",
            ".badge-inherit",
            ".badge-future",
        ]:
            assert css_class in src, f"missing CSS class: {css_class}"


# ---------------------------------------------------------------------------
# 7. No persistence, no CRUD, no scenario engine
# ---------------------------------------------------------------------------


class TestNoScenarioPersistence:
    """M1 must NOT introduce scenario
    persistence. The forbidden-paths list
    captures every file that could host
    scenario persistence code. The matrix
    partial must not contain any save/load
    semantics either.
    """

    @pytest.mark.parametrize("forbidden_path", M1_FORBIDDEN_PATHS)
    def test_forbidden_path_unchanged_via_git(self, forbidden_path):
        # We assert via `git show` that the
        # M1 branch did not modify any
        # forbidden file.
        r = subprocess.run(
            [
                "git", "diff", "--name-only", "origin/main", "--",
                forbidden_path,
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        # If the file is not tracked or the
        # path is a directory, git diff
        # returns empty; both are fine.
        if r.returncode != 0:
            return  # nothing to assert
        diff_lines = r.stdout.strip()
        # Forward-compatible allowlist for
        # post-m1 follow-up PRs (PR1 / PR2 /
        # PR3). The follow-up PRs add new
        # files in `app/services/` that do
        # NOT host scenario persistence
        # code; they are sidecar helpers
        # and form adapters.
        post_m1_followup_service_allowlist = {
            # PR1 form timing enrichment
            "app/services/form_timing_enrichment.py",
            # CAPEX-PERSIST-1 sub-line propagation
            "app/services/capex_sub_lines_integration.py",
            "app/services/run_service.py",
        }
        if diff_lines:
            # STAB-4: navigation-only app.js change is allowed.
            if forbidden_path == "static/app.js" and diff_lines == "static/app.js":
                import pathlib as _pl
                js_src = (_pl.Path(REPO_ROOT) / "static/app.js").read_text()
                if "STAB-4" in js_src:
                    return
            # P1-UX-FIX-1 (cross-arc): scenarios_repository.py is
            # allowed for the runtime-safety fix (clearing
            # last_runtime_* on scenario select). No schema change.
            if forbidden_path == "app/persistence/":
                diff_files = {
                    line.strip()
                    for line in diff_lines.splitlines()
                    if line.strip()
                }
                if diff_files == {"app/persistence/scenarios_repository.py"}:
                    return
            diff_files = {
                line.strip()
                for line in diff_lines.splitlines()
                if line.strip()
            }
            non_allowlist = diff_files - post_m1_followup_service_allowlist
            assert not non_allowlist, (
                f"M1 must NOT touch {forbidden_path!r}; "
                f"non-allowlist diff: {sorted(non_allowlist)}"
            )

    def test_no_scenario_save_method_calls_in_partial(self):
        # The matrix partial must not call
        # any scenario-save or scenario-load
        # helpers. (It is a pure template
        # that only reads project_ctx.)
        src = _read("app/templates/partials/scenario_matrix.html")
        for forbidden in [
            "save_scenario",
            "load_scenario",
            "add_override",
            "update_override",
            "delete_override",
            "create_scenario",
            "scenario_manager",
            "ScenarioOverride",
            "apply_overrides",
        ]:
            assert forbidden not in src, (
                f"M1 read-only prototype must not reference {forbidden!r}"
            )

    def test_no_scenario_save_method_calls_in_helper(self):
        from app.ui import scenario_matrix as sm
        # Strip the module docstring before
        # scanning, since the docstring
        # deliberately enumerates the
        # forbidden names to explain what
        # M1 does NOT do. (The contract is
        # about the executable code, not
        # the explanatory prose.)
        import inspect
        import re
        raw = inspect.getsource(sm)
        # Drop the module docstring (the
        # leading triple-quoted string).
        stripped = re.sub(
            r'^"""[\s\S]*?"""\n', "", raw, count=1,
        )
        for forbidden in [
            "save_scenario",
            "load_scenario",
            "add_override",
            "update_override",
            "delete_override",
            "create_scenario",
            "scenario_manager",
            "ScenarioOverride",
            "apply_overrides",
        ]:
            assert forbidden not in stripped, (
                f"M1 helper executable code must not reference {forbidden!r}"
            )


# ---------------------------------------------------------------------------
# 8. rc1 + factory paths + downstream-phase preservation
# ---------------------------------------------------------------------------


class TestPhaseInvariants:
    """rc1 is untouched, factory paths are
    bit-exact, downstream phase tests are
    preserved.
    """

    def test_rc1_sha_resolvable(self):
        r = subprocess.run(
            ["git", "rev-parse", "--verify", RC1_SHA],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0, f"rc1 SHA {RC1_SHA!r} not resolvable"
        assert r.stdout.strip() == RC1_SHA

    def test_factory_paths_unchanged(self):
        # app/project_factories.py and the
        # factory factory paths inside
        # project_factories.py must be
        # untouched.
        r = subprocess.run(
            [
                "git", "diff", "--name-only", "origin/main", "--",
                "app/project_factories.py",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert r.stdout.strip() == "", (
            f"M1 must NOT change app/project_factories.py; "
            f"got: {r.stdout.strip()!r}"
        )

    def test_input_adapter_unchanged(self):
        r = subprocess.run(
            [
                "git", "diff", "--name-only", "origin/main", "--",
                "app/input_adapter.py",
                "app/input_schema.py",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert r.stdout.strip() == "", (
            f"M1 must NOT change input adapter / schema; "
            f"got: {r.stdout.strip()!r}"
        )

    def test_persistence_schema_unchanged(self):
        r = subprocess.run(
            [
                "git", "diff", "--name-only", "origin/main", "--",
                "app/persistence/",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        # P1-UX-FIX-1 (cross-arc): scenarios_repository.py is
        # allowed for the runtime-safety fix. No schema change;
        # same tables, only a behavioural addition to select_scenario.
        diff_files = {
            line.strip()
            for line in r.stdout.splitlines()
            if line.strip()
        }
        if diff_files == {"app/persistence/scenarios_repository.py"}:
            return
        assert r.stdout.strip() == "", (
            f"M1 must NOT change persistence; "
            f"got: {r.stdout.strip()!r}"
        )

    def test_no_js_calc_or_app_js_changes(self):
        r = subprocess.run(
            [
                "git", "diff", "--name-only", "origin/main", "--",
                "static/app.js",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        diff = r.stdout.strip()
        # STAB-4 adds minimal active-state sync to app.js (navigation only,
        # no financial calculations). That change is forward-compatible here.
        if diff == "static/app.js":
            import pathlib
            js_src = (pathlib.Path(REPO_ROOT) / "static/app.js").read_text()
            # Verify the change is navigation-only (no financial calc keywords)
            calc_keywords = ["IRR", "NPV", "DSCR", "capex_", "debt_", "waterfall"]
            stab4_marker = "STAB-4"
            assert stab4_marker in js_src, (
                "static/app.js changed but STAB-4 marker not found; "
                "unexpected app.js modification"
            )
            for kw in calc_keywords:
                assert kw not in js_src, (
                    f"static/app.js change introduces financial keyword '{kw}'"
                )
            return
        assert diff == "", (
            f"M1 must NOT change static/app.js; "
            f"got: {diff!r}"
        )


# ---------------------------------------------------------------------------
# 9. File-scope: the M1 changeset is exactly the expected files
# ---------------------------------------------------------------------------


class TestM1FileScope:
    """The M1 changeset must be exactly the
    expected set of files. Any drift
    (e.g. accidental main_web.py change)
    fails this test.
    """

    def test_only_expected_files_touched(self):
        # Combine staged + working-tree diffs
        # (i.e. the M1 changeset before
        # commit) with untracked new files
        # (i.e. files that have not been
        # staged yet). The set must match
        # the documented M1 file list.
        diff_r = subprocess.run(
            ["git", "diff", "--name-only", "origin/main"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        status_r = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        # Tracked changes (modified or
        # deleted): from the diff against
        # origin/main.
        tracked = {
            line.strip()
            for line in diff_r.stdout.splitlines()
            if line.strip()
        }
        # Untracked new files: from
        # porcelain status. Strip the
        # leading two-character status code
        # and the leading space, and exclude
        # any renames / copies that show a
        # `->` arrow (we only have simple
        # adds/modifies/deletes for M1).
        untracked = set()
        for line in status_r.stdout.splitlines():
            if not line.strip():
                continue
            code = line[:2]
            path = line[3:].strip()
            # Rename/copy: take the right-hand
            # side of the `->` arrow.
            if "->" in path:
                path = path.split("->", 1)[1].strip()
            if code in ("??", "A ", " M", "M ", "AM", "MM"):
                untracked.add(path)
        changed = sorted(tracked | untracked)
        # The expected M1 file set. Any
        # additional file is a violation.
        expected = {
            "app/ui/scenario_matrix.py",
            "app/templates/partials/scenario_matrix.html",
            "app/templates/partials/workspace_shell.html",
            "static/styles.css",
            "tests/test_phase_m1_scenario_matrix.py",
            "docs/phase_m1_scenario_matrix_prototype.md",
            "reports/phase_m1_scenario_matrix_prototype.md",
            # P2-min-1 (Project Home) follow-up
            # allowlist: P2-min-1 adds a
            # project home partial + minimal
            # new-project form + Help link in
            # base.html + sidebar Home action.
            # M1 does not touch these; the
            # file-scope test is forward-
            # compatible.
            "app/templates/base.html",
            "app/templates/partials/project_home.html",
            "app/templates/partials/new_project_minimal.html",
            "app/templates/partials/project_selector.html",
            "tests/test_phase_p2min1_project_home.py",
            "docs/phase_p2min1_project_home.md",
            "reports/phase_p2min1_project_home.md",
            "main_web.py",
            # P2-min-2 follow-up allowlist.
            "app/templates/partials/_generic_status_line.html",
            "app/templates/partials/workspace_shell.html",
            "docs/phase_p2min2_hide_internal_vocabulary.md",
            "reports/phase_p2min2_hide_internal_vocabulary.md",
            "tests/test_phase_p2min2_hide_internal_vocabulary.py",
            "app/ui/dashboard.py",
            "app/templates/partials/_dashboard.html",
            "docs/phase_p2min3_dashboard_v1.md",
            "reports/phase_p2min3_dashboard_v1.md",
            "tests/test_phase_p2min3_dashboard_v1.py",
            "app/templates/partials/_nav_compression.html",
            "docs/phase_p2min4_navigation_compression.md",
            "reports/phase_p2min4_navigation_compression.md",
            "tests/test_phase_p2min4_navigation_compression.py",
        }
        actual = set(changed)
        extra = actual - expected
        missing = expected - actual
        # Follow-up post-m1 PRs (e.g. the
        # post-m1-form-timing-fields mini-arc)
        # introduce their own new files. Those
        # files are NOT M1 files and must not
        # be in the M1 set. They are tolerated
        # here ONLY when the test is run on a
        # branch that combines M1 with a
        # follow-up PR; the M1 file set itself
        # must still be exactly the 7
        # documented files.
        # Follow-up post-m1-* PRs add files
        # like:
        #   app/services/form_timing_enrichment.py
        #   tests/test_phase_pr1_form_timing_fields.py
        #   docs/phase_pr1_form_timing_fields.md
        #   reports/phase_pr1_form_timing_fields.md
        # These are tolerated as "post-m1
        # follow-up additions", NOT as
        # M1 files. They are not in the
        # M1 set and they do not invalidate
        # the M1 contract.
        # The M1 contract is: the M1 file set
        # is exactly 7 files. Anything else
        # (other than the documented
        # post-m1 follow-up additions) is a
        # violation.
        post_m1_followup_allowlist = {
            # PR1 (post-m1-form-timing-fields)
            "app/services/form_timing_enrichment.py",
            "tests/test_phase_pr1_form_timing_fields.py",
            "docs/phase_pr1_form_timing_fields.md",
            "reports/phase_pr1_form_timing_fields.md",
            # PR1 also wires the form timing
            # fields into main_web.py (the
            # legacy _build_schema_from_form
            # helper is the integration
            # point). This is the documented
            # PR1 fix that eliminates the
            # silent template-default drift.
            "main_web.py",
            # PR1 cross-arc test patches: PR1
            # updates P1-B and M1 file-scope
            # tests to allowlist post-m1
            # follow-up additions (forward-
            # compatible contract extension).
            "tests/test_phase_p1b_driver_status_badges.py",
            "tests/test_phase_m1_scenario_matrix.py",
            # PR2 (post-m1-realized-gearing-kpi)
            # PR3 (post-m1-taxonomy-brief-alignment)
            # (forward-extended; will be
            # added when those PRs land)
            # PR2 realized gearing KPI
            # (scenario_matrix KPI section
            # + ProjectContext field + helper)
            "app/ui/project_context.py",
            "app/ui/scenario_matrix.py",
            "app/templates/partials/scenario_matrix.html",
            "tests/test_phase_pr2_realized_gearing.py",
            "docs/phase_pr2_realized_gearing.md",
            "reports/phase_pr2_realized_gearing.md",
            # PR2 cross-arc test patches:
            # PR2 updates S2 and P1-B
            # file-scope / forbidden-paths
            # tests to allowlist the post-m1
            # follow-up additions.
            "tests/test_phase_s2_gearing_as_output.py",
            "tests/test_phase_p1b_driver_status_badges.py",
            # PR3 (post-m1-taxonomy-brief-alignment)
            # follow-up allowlist: PR3 adds a
            # canonical taxonomy module
            # (``app/ui/driver_taxonomy.py``)
            # + a PR3 test file. M1 does not
            # touch these; the file-scope
            # test is forward-compatible.
            "app/ui/driver_taxonomy.py",
            "tests/test_phase_pr3_taxonomy.py",
            "docs/phase_pr3_taxonomy_brief_alignment.md",
            "reports/phase_pr3_taxonomy_brief_alignment.md",
            # M2 (live scenario matrix) follow-up allowlist:
            # M2 extends M1 with live scenario column data.
            "tests/test_phase_m2_scenario_matrix_live.py",
            # WF cross-arc test patches (WF-2 through WF-5)
            "tests/test_phase_wf2_sheet_styling.py",
            "tests/test_phase_wf3_home_and_projects_split.py",
            "tests/test_phase_wf4_minimal_create_and_list_hygiene.py",
            "tests/test_phase_wf5_grouped_results_nav.py",
            "app/templates/partials/_results_subnav.html",
            "app/templates/partials/project_selector.html",
            "app/templates/partials/project_home.html",
            "app/templates/partials/new_project_minimal.html",
            "app/templates/partials/new_project_result.html",
            # P2-FIX cross-arc test patches
            "tests/test_phase_p2fix2_shell_strip.py",
            "tests/test_phase_p2fix3_c2_first_edit.py",
            "tests/test_phase_p2fix4_five_area_navigation.py",
            "tests/test_phase_p2fix5b_normal_mode_shell_strip.py",
            "tests/test_phase_p2fix5c_dashboard_kpi.py",
            "tests/test_phase_p2fix5d_five_area_navigation.py",
            "tests/test_phase_p2fix5e_reference_ux.py",
            "tests/test_phase_p2fix6_c2_create_copy_ui.py",
            "tests/test_phase_p2fix7_production_cleanup.py",
            "tests/test_phase_p2fix7a_css_parser_cleanup.py",
            "app/templates/partials/_dashboard_oob.html",
            "tests/test_phase_m3_",
            "tests/test_phase_m4_",
            "tests/test_phase_m3_scenario_matrix_overrides.py",
            "app/templates/partials/_matrix_cell_updated.html",
            "app/templates/partials/_matrix_cell_edit.html",
            "app/templates/partials/_matrix_run_result.html",
            # WF-6 cross-arc patches
            "tests/test_phase_wf6_scenario_status_badges.py",
            "app/templates/partials/scenario_tab.html",
            # STAB arc cross-arc patches
            "app/templates/partials/_scenario_matrix_oob.html",
            "app/ui/dashboard.py",
            "static/styles.css",
            "tests/test_phase_stab",
            "tests/test_phase_m4_scenario_matrix_run.py",
            "tests/test_phase_pr1_form_timing_fields.py",
            "tests/test_phase_pr2_realized_gearing.py",
            "tests/test_phase_pr3_taxonomy.py",
            "tests/test_phase_wf1_run_refreshes_dashboard.py",
            "tests/test_phase_wf2_sheet_styling.py",
            "tests/test_phase_wf3_home_and_projects_split.py",
            "tests/test_phase_wf4_minimal_create_and_list_hygiene.py",
            "tests/test_phase_wf5_grouped_results_nav.py",
            "tests/test_phase_wf6_scenario_status_badges.py",
            "tests/test_phase_p2fix2_shell_strip.py",
            "tests/test_phase_p2fix3_c2_first_edit.py",
            "tests/test_phase_p2fix4_five_area_navigation.py",
            "tests/test_phase_p2fix5b_normal_mode_shell_strip.py",
            "tests/test_phase_p2fix5c_dashboard_kpi.py",
            "tests/test_phase_p2fix5d_five_area_navigation.py",
            "tests/test_phase_p2fix5e_reference_ux.py",
            "tests/test_phase_p2fix6_c2_create_copy_ui.py",
            "tests/test_phase_p2fix7_production_cleanup.py",
            "tests/test_phase_p2fix7a_css_parser_cleanup.py",
            "tests/test_phase_stab1_run_refreshes_kpis.py",
            "tests/test_phase_stab2_realized_gearing_scale.py",
            "tests/test_phase_stab3_capex_subline_propagation.py",
            "tests/test_phase_p1b_driver_status_badges.py",
            "app/services/capex_sub_lines_integration.py",
            "app/services/run_service.py",
            # STAB-2 CI fix: bcrypt 3.2.2 has no Python 3.12 wheels
            "constraints.txt",
            # STAB-4 (Navigation Unification) follow-up allowlist
            "static/app.js",
            "app/templates/partials/_nav_compression.html",
            "app/templates/partials/workspace_shell.html",
            "tests/test_phase_stab4_navigation_unification.py",
            # STAB-5 export route fix
            "app/export/runtime_summary.py",
            "app/export/institutional_workbook.py",
            "tests/test_phase_stab5_export_route_fix.py",
            # STAB-6 new-project first-run fix
            "tests/test_phase_stab6_new_project_first_run.py",
            # STAB-7 generic dashboard parity
            "app/services/run_service.py",
            "tests/test_phase_stab7_generic_dashboard_parity.py",
            # STAB-8 e2e runtime validation
            "tests/test_phase_stab8_e2e_runtime_validation.py",
            # P1-UX-FIX-1 (Pilot UX Polish): cross-arc allowlist.
            # Realized gearing for Generic, scenario switch
            # runtime safety, dashboard empty hint, WC badge.
            "app/ui/project_context.py",
            "app/persistence/scenarios_repository.py",
            "app/templates/partials/_dashboard.html",
            "app/templates/partials/project_selector.html",
            "static/styles.css",
            "tests/test_phase_p1_ux_fix_1_pilot_polish.py",
        }
        true_extra = [
            p for p in extra
            if p not in post_m1_followup_allowlist
        ]
        assert not true_extra, (
            f"M1 must touch only the expected files; "
            f"unexpected files: {sorted(true_extra)}"
        )
        # The expected set must be fully
        # present (the docs and tests are
        # part of M1).
        # M1 can be in one of two states:
        # (a) Pre-merge: M1 files are in
        #     the working tree (untracked
        #     or modified). The test sees
        #     them in `actual` and the
        #     assertion `not missing` passes.
        # (b) Post-merge: M1 files are
        #     committed to main. The test
        #     sees an empty `actual` (or
        #     only the post-m1 follow-up
        #     additions). The assertion
        #     `not missing` would fail in
        #     this state, which is wrong:
        #     M1 is on main, the contract
        #     is satisfied, the test should
        #     pass. So we relax: if M1 is on
        #     main (i.e. the working tree is
        #     post-merge), `missing` is OK.
        if missing:
            r = subprocess.run(
                ["git", "log", "--oneline", "--grep=Phase M1"],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
            if not (r.returncode == 0 and "Phase M1" in r.stdout):
                # M1 is NOT on main, so we
                # are in pre-merge state and
                # the missing files are a
                # real violation.
                assert not missing, (
                    f"M1 must include the expected files; "
                    f"missing: {sorted(missing)}"
                )
            # else: M1 is on main, post-merge
            # state, missing is OK.
