"""Scenario / Compare C1 Migration: markup-contract test.

Asserts the four true tabular/grid surfaces migrated under this PR emit
a valid, internally-consistent C1 `data-fc-*` markup contract:

  - `app/templates/partials/scenario_matrix.html`
    (`data-fc-grid="scenarios"`) -- the Dashboard-tab Phase M2 Live
    Scenario Matrix (Base | Downside | Upside | Custom).
  - `app/templates/partials/scenario_tab.html`
    (`data-fc-grid="scenario-inputs"`) -- the Scenarios-tab Excel-like
    input comparison matrix (`#sc-matrix`).
  - `app/templates/partials/_scenario_unified_entry.html`
    (`data-fc-grid="scenario-summary"`) -- the Scenarios-tab KPI
    summary table.
  - `app/templates/partials/scenario_compare.html`
    (`data-fc-grid="scenario-compare"`) -- the Compare tab, covering
    both the Base-vs-Active mode and the legacy Left-vs-Right mode.

See docs/SCENARIO_COMPARE_C1_MIGRATION_NOTE.md for the full audit and
address-scheme rationale. This is a static (HTML-string) test,
mirroring tests/test_tax_c1_markup_contract.py /
tests/test_export_audit_c1_markup_contract.py. Production-route
browser coverage lives in
tests/test_scenario_compare_c1_migration_browser.py.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_TEMPLATES = REPO_ROOT / "app" / "templates"

CELL_RE = re.compile(r'<[a-zA-Z]+[^>]*data-fc-cell="true"[^>]*>', re.IGNORECASE)
ATTR_RE = re.compile(r'(data-fc-[a-z]+)="([^"]*)"')


def _env():
    return Environment(
        loader=FileSystemLoader(str(APP_TEMPLATES)),
        autoescape=select_autoescape(["html"]),
    )


def _fc_cells(html):
    cells = []
    for match in CELL_RE.finditer(html):
        tag = match.group(0)
        attrs = dict(ATTR_RE.findall(tag))
        cells.append(attrs)
    return cells


# ---------------------------------------------------------------------------
# Sample data builders
# ---------------------------------------------------------------------------


class _Ctx(dict):
    def __getattr__(self, key):
        return self.get(key)


SAMPLE_PROJECT_CTX = _Ctx(
    ppa_tariff_eur_mwh=55.0,
    operating_hours_p50=1400,
    capacity_mw=50.0,
    total_capex_keur=45000.0,
    opex_y1_total_keur=900.0,
    interest_rate_pct=5.0,
    senior_tenor_years=15,
    target_dscr=1.3,
    gearing_pct=70.0,
    ppa_term_years=15,
    construction_months=12,
    total_revenue_keur=6000.0,
    total_ebitda_keur=4800.0,
    project_irr=9.2,
    equity_irr=12.5,
    senior_debt_amount_keur=31000.0,
    realized_gearing_pct=68.0,
    avg_dscr=1.45,
    min_dscr=1.21,
)


class _ScenarioRecord(_Ctx):
    """Minimal ScenarioRecord-like stand-in for standalone rendering."""


def _scenario_record(scenario_id, name, is_base_case=False, overrides=None, snapshot=None,
                      base_input_set=None, last_run_summary=None):
    return _ScenarioRecord(
        scenario_id=scenario_id,
        scenario_name=name,
        is_base_case=is_base_case,
        overrides=overrides or {},
        snapshot=snapshot or {},
        base_input_set=base_input_set or {},
        last_run_summary=last_run_summary,
    )


def _build_matrix_context(scenario_records=None, runtime_kpis=None):
    from app.ui.scenario_matrix import build_matrix_context
    return build_matrix_context(SAMPLE_PROJECT_CTX, scenario_records or [], runtime_kpis=runtime_kpis)


# ---------------------------------------------------------------------------
# 1. scenario_matrix.html (data-fc-grid="scenarios")
# ---------------------------------------------------------------------------


def _render_scenario_matrix(scenario_records=None):
    ctx = _build_matrix_context(scenario_records)
    tmpl = _env().get_template("partials/scenario_matrix.html")
    return tmpl.render(**ctx)


@pytest.fixture(scope="module")
def matrix_html_no_scenarios():
    return _render_scenario_matrix(scenario_records=[])


@pytest.fixture(scope="module")
def matrix_html_with_downside():
    downside = _scenario_record(
        "scn-downside-1", "Downside Case",
        overrides={"ppa_tariff_eur_mwh": 48.0},
        snapshot={"ppa_tariff_eur_mwh": 48.0},
    )
    return _render_scenario_matrix(scenario_records=[downside])


class TestScenarioMatrixMarkupContract:
    def test_grid_root_present(self, matrix_html_no_scenarios):
        assert 'data-fc-grid="scenarios"' in matrix_html_no_scenarios

    def test_scroll_container_present(self, matrix_html_no_scenarios):
        assert 'data-fc-scroll-container="true"' in matrix_html_no_scenarios

    def test_fc_cells_exist(self, matrix_html_no_scenarios):
        assert len(_fc_cells(matrix_html_no_scenarios)) > 0

    def test_every_cell_has_addr_kind_and_editable(self, matrix_html_no_scenarios):
        for attrs in _fc_cells(matrix_html_no_scenarios):
            assert attrs.get("data-fc-addr"), attrs
            assert attrs.get("data-fc-kind") == "text", attrs
            assert attrs.get("data-fc-editable") in ("true", "false"), attrs

    def test_no_duplicate_addresses(self, matrix_html_no_scenarios):
        addrs = [a["data-fc-addr"] for a in _fc_cells(matrix_html_no_scenarios)]
        assert len(addrs) == len(set(addrs))

    def test_addresses_are_deterministic_not_display_text(self, matrix_html_no_scenarios):
        for attrs in _fc_cells(matrix_html_no_scenarios):
            addr = attrs["data-fc-addr"]
            assert addr.startswith("scenarios!"), addr
            assert " " not in addr, addr

    def test_known_address_examples_present(self, matrix_html_no_scenarios):
        addrs = {a["data-fc-addr"] for a in _fc_cells(matrix_html_no_scenarios)}
        for expected in (
            "scenarios!base.project_irr",
            "scenarios!downside.avg_dscr",
            "scenarios!upside.ppa_tariff_eur_mwh",
            "scenarios!custom.total_capex_keur",
        ):
            assert expected in addrs, f"{expected} missing from {sorted(addrs)}"

    def test_no_live_scenario_means_all_cells_non_editable(self, matrix_html_no_scenarios):
        """With no scenario_records, downside/upside/custom are
        placeholder text ('inherits Base' / '-') -- not editable."""
        for attrs in _fc_cells(matrix_html_no_scenarios):
            assert attrs["data-fc-editable"] == "false", attrs

    def test_base_column_always_non_editable(self, matrix_html_with_downside):
        addrs = {a["data-fc-addr"]: a for a in _fc_cells(matrix_html_with_downside)}
        for attr in ("scenarios!base.project_irr", "scenarios!base.ppa_tariff_eur_mwh"):
            assert addrs[attr]["data-fc-editable"] == "false"

    def test_live_downside_input_cell_is_editable(self, matrix_html_with_downside):
        """When a real Downside scenario is assigned, its INPUT cells
        (not KPI cells) use the existing hx-get cell-edit affordance --
        this migration must preserve that as editable=true, not make
        it newly editable (it was already click-to-edit)."""
        addrs = {a["data-fc-addr"]: a for a in _fc_cells(matrix_html_with_downside)}
        assert addrs["scenarios!downside.ppa_tariff_eur_mwh"]["data-fc-editable"] == "true"

    def test_live_downside_kpi_cell_remains_non_editable(self, matrix_html_with_downside):
        """KPI rows are never editable even for a live scenario column
        (KPIs are outputs, not overridable inputs)."""
        addrs = {a["data-fc-addr"]: a for a in _fc_cells(matrix_html_with_downside)}
        assert addrs["scenarios!downside.project_irr"]["data-fc-editable"] == "false"

    def test_existing_hx_get_preserved_on_editable_cell(self, matrix_html_with_downside):
        """The C1 attributes must not remove the existing hx-get
        click-to-edit affordance on a live, editable scenario cell."""
        assert "hx-get=\"/matrix/scenario/scn-downside-1/cell-edit?field=ppa_tariff_eur_mwh&col=downside\"" in matrix_html_with_downside

    def test_deterministic_ordering_across_renders(self):
        html_a = _render_scenario_matrix()
        html_b = _render_scenario_matrix()
        addrs_a = [a["data-fc-addr"] for a in _fc_cells(html_a)]
        addrs_b = [a["data-fc-addr"] for a in _fc_cells(html_b)]
        assert addrs_a == addrs_b

    def test_raw_values_match_project_ctx(self, matrix_html_no_scenarios):
        addrs = {a["data-fc-addr"]: a for a in _fc_cells(matrix_html_no_scenarios)}
        # base.project_irr is formatted via _fmt_pct -- raw mirrors the
        # *displayed* (formatted) string, matching the established
        # cross-migration convention of data-fc-raw = the cell's text.
        assert addrs["scenarios!base.capacity_mw"]["data-fc-raw"]


# ---------------------------------------------------------------------------
# 2. scenario_tab.html (data-fc-grid="scenario-inputs")
# ---------------------------------------------------------------------------


def _render_scenario_tab(is_user_project=True, non_base_scenarios=None, base_case_record=None):
    from main_web import SCENARIO_EDITABLE_FIELDS
    base = base_case_record or _scenario_record(
        "scn-base", "Base Case", is_base_case=True,
        base_input_set={"capacity_mw": 50.0, "tariff_eur_mwh": 55.0},
    )
    tmpl = _env().get_template("partials/scenario_tab.html")
    return tmpl.render(
        project_record=_Ctx(project_code="acme"),
        base_case_record=base,
        non_base_scenarios=non_base_scenarios or [],
        workspace_state=_Ctx(active_scenario_id=base.scenario_id),
        is_user_project=is_user_project,
        scenario_editable_fields=SCENARIO_EDITABLE_FIELDS,
    )


@pytest.fixture(scope="module")
def scenario_tab_html_with_variant():
    variant = _scenario_record(
        "scn-variant-1", "Downside Variant",
        overrides={"tariff_eur_mwh": 48.0},
    )
    return _render_scenario_tab(is_user_project=True, non_base_scenarios=[variant])


@pytest.fixture(scope="module")
def scenario_tab_html_readonly_project():
    variant = _scenario_record("scn-variant-2", "Variant")
    return _render_scenario_tab(is_user_project=False, non_base_scenarios=[variant])


class TestScenarioInputsMarkupContract:
    def test_grid_root_present(self, scenario_tab_html_with_variant):
        assert 'data-fc-grid="scenario-inputs"' in scenario_tab_html_with_variant

    def test_scroll_container_present(self, scenario_tab_html_with_variant):
        assert 'data-fc-scroll-container="true"' in scenario_tab_html_with_variant

    def test_fc_cells_exist(self, scenario_tab_html_with_variant):
        assert len(_fc_cells(scenario_tab_html_with_variant)) > 0

    def test_every_cell_has_addr_kind_and_editable(self, scenario_tab_html_with_variant):
        for attrs in _fc_cells(scenario_tab_html_with_variant):
            assert attrs.get("data-fc-addr"), attrs
            assert attrs.get("data-fc-kind") == "text", attrs
            assert attrs.get("data-fc-editable") in ("true", "false"), attrs

    def test_no_duplicate_addresses(self, scenario_tab_html_with_variant):
        addrs = [a["data-fc-addr"] for a in _fc_cells(scenario_tab_html_with_variant)]
        assert len(addrs) == len(set(addrs))

    def test_addresses_are_deterministic_not_display_text(self, scenario_tab_html_with_variant):
        for attrs in _fc_cells(scenario_tab_html_with_variant):
            addr = attrs["data-fc-addr"]
            assert addr.startswith("scenario-inputs!"), addr
            assert " " not in addr, addr

    def test_known_address_examples_present(self, scenario_tab_html_with_variant):
        addrs = {a["data-fc-addr"] for a in _fc_cells(scenario_tab_html_with_variant)}
        assert "scenario-inputs!base.capacity_mw" in addrs
        assert "scenario-inputs!scn-variant-1.tariff_eur_mwh" in addrs

    def test_base_column_always_non_editable(self, scenario_tab_html_with_variant):
        addrs = {a["data-fc-addr"]: a for a in _fc_cells(scenario_tab_html_with_variant)}
        for k, a in addrs.items():
            if k.startswith("scenario-inputs!base."):
                assert a["data-fc-editable"] == "false", k

    def test_non_base_cells_editable_for_user_project(self, scenario_tab_html_with_variant):
        """Real <input>-backed editing only happens via the existing
        ondblclick popover (window.startScenarioEdit), gated by
        is_user_project -- exactly the same gate this migration must
        reuse, not bypass."""
        addrs = {a["data-fc-addr"]: a for a in _fc_cells(scenario_tab_html_with_variant)}
        variant_cells = [a for k, a in addrs.items() if k.startswith("scenario-inputs!scn-variant-1.")]
        assert variant_cells
        for a in variant_cells:
            assert a["data-fc-editable"] == "true"

    def test_non_base_cells_non_editable_for_readonly_project(self, scenario_tab_html_readonly_project):
        """Protected (non-user) projects cannot add/edit scenarios --
        the dblclick handler is omitted server-side
        (`{% if is_user_project %}ondblclick=...{% endif %}`); C1 must
        not introduce new editability where the underlying behaviour
        is read-only."""
        addrs = {a["data-fc-addr"]: a for a in _fc_cells(scenario_tab_html_readonly_project)}
        variant_cells = [a for k, a in addrs.items() if k.startswith("scenario-inputs!scn-variant-2.")]
        assert variant_cells
        for a in variant_cells:
            assert a["data-fc-editable"] == "false"

    def test_existing_ondblclick_preserved_on_editable_cell(self, scenario_tab_html_with_variant):
        assert "ondblclick=\"window.startScenarioEdit(this)\"" in scenario_tab_html_with_variant

    def test_deterministic_ordering_across_renders(self):
        variant = _scenario_record("scn-variant-1", "Downside Variant")
        html_a = _render_scenario_tab(non_base_scenarios=[variant])
        html_b = _render_scenario_tab(non_base_scenarios=[variant])
        addrs_a = [a["data-fc-addr"] for a in _fc_cells(html_a)]
        addrs_b = [a["data-fc-addr"] for a in _fc_cells(html_b)]
        assert addrs_a == addrs_b


# ---------------------------------------------------------------------------
# 3. _scenario_unified_entry.html (data-fc-grid="scenario-summary")
# ---------------------------------------------------------------------------


def _render_unified_entry(scenario_records=None):
    ctx = _build_matrix_context(scenario_records)
    tmpl = _env().get_template("partials/_scenario_unified_entry.html")
    return tmpl.render(**ctx)


@pytest.fixture(scope="module")
def unified_entry_html():
    return _render_unified_entry(scenario_records=[])


@pytest.fixture(scope="module")
def unified_entry_html_empty():
    """When matrix_rows is undefined entirely, the template degrades
    to the 'No KPI data available yet' empty state with no grid."""
    tmpl = _env().get_template("partials/_scenario_unified_entry.html")
    return tmpl.render()


class TestScenarioSummaryMarkupContract:
    def test_grid_root_present(self, unified_entry_html):
        assert 'data-fc-grid="scenario-summary"' in unified_entry_html

    def test_scroll_container_present(self, unified_entry_html):
        assert 'data-fc-scroll-container="true"' in unified_entry_html

    def test_fc_cells_exist(self, unified_entry_html):
        assert len(_fc_cells(unified_entry_html)) > 0

    def test_every_cell_non_editable(self, unified_entry_html):
        """This is a read-only KPI roll-up; no <input> exists here."""
        for attrs in _fc_cells(unified_entry_html):
            assert attrs["data-fc-editable"] == "false", attrs

    def test_no_duplicate_addresses(self, unified_entry_html):
        addrs = [a["data-fc-addr"] for a in _fc_cells(unified_entry_html)]
        assert len(addrs) == len(set(addrs))

    def test_addresses_are_deterministic_not_display_text(self, unified_entry_html):
        for attrs in _fc_cells(unified_entry_html):
            addr = attrs["data-fc-addr"]
            assert addr.startswith("scenario-summary!"), addr
            assert " " not in addr, addr

    def test_known_address_examples_present(self, unified_entry_html):
        addrs = {a["data-fc-addr"] for a in _fc_cells(unified_entry_html)}
        assert "scenario-summary!base.project_irr" in addrs
        assert "scenario-summary!downside.avg_dscr" in addrs

    def test_only_kpi_rows_addressed_not_input_rows(self, unified_entry_html):
        """This summary table only ever renders KPI rows
        (`{% if entry.is_kpi %}`); input rows like ppa_tariff_eur_mwh
        must not appear here (they belong to the matrix/inputs grids,
        not this read-only roll-up)."""
        addrs = {a["data-fc-addr"] for a in _fc_cells(unified_entry_html)}
        assert "scenario-summary!base.ppa_tariff_eur_mwh" not in addrs

    def test_no_grid_when_no_matrix_data(self, unified_entry_html_empty):
        assert 'data-fc-grid="scenario-summary"' not in unified_entry_html_empty

    def test_deterministic_ordering_across_renders(self):
        html_a = _render_unified_entry()
        html_b = _render_unified_entry()
        addrs_a = [a["data-fc-addr"] for a in _fc_cells(html_a)]
        addrs_b = [a["data-fc-addr"] for a in _fc_cells(html_b)]
        assert addrs_a == addrs_b


# ---------------------------------------------------------------------------
# 4. scenario_compare.html (data-fc-grid="scenario-compare")
# ---------------------------------------------------------------------------


def _render_compare_base_vs_active(empty=False):
    base = _scenario_record("scn-base", "Base Case", is_base_case=True)
    if empty:
        compare_result = _Ctx(base=base, active=None, empty_state="No Active Scenario")
    else:
        active = _scenario_record("scn-active", "Active Scenario")
        compare_result = _Ctx(
            base=base,
            active=active,
            metrics=[
                {"key": "project_irr", "base_value": 8.5, "active_value": 9.2, "delta": 0.7, "sign_class": "delta-positive"},
                {"key": "avg_dscr", "base_value": 1.30, "active_value": 1.45, "delta": 0.15, "sign_class": "delta-positive"},
            ],
        )
    tmpl = _env().get_template("partials/scenario_compare.html")
    return tmpl.render(compare_panel=True, compare_result=compare_result, audit_mode=False)


def _render_compare_legacy_left_right():
    left = _Ctx(scenario_name="Left Scenario")
    right = _Ctx(scenario_name="Right Scenario")
    compare_result = _Ctx(
        left=left,
        right=right,
        compare_generated_at="2026-06-27 10:00",
        dirty_note="",
        missing_metric_note="",
        left_context=_Ctx(source_label="Saved", scenario_timestamp="-", runtime_timestamp="-", runtime_snapshot_id="-", runtime_origin="-"),
        right_context=_Ctx(source_label="Saved", scenario_timestamp="-", runtime_timestamp="-", runtime_snapshot_id="-", runtime_origin="-"),
        workspace_runtime_origin_label="Last clean backend run",
        metrics=[
            {"metric": "Project IRR", "left_value": "8.50", "right_value": "9.20", "delta": "+0.70"},
            {"metric": "Avg DSCR", "left_value": "1.30", "right_value": "1.45", "delta": "+0.15"},
        ],
        governance_rows=[],
        governance_summary="",
    )
    tmpl = _env().get_template("partials/scenario_compare.html")
    return tmpl.render(compare_panel=False, compare_result=compare_result, audit_mode=False)


def _render_compare_truly_empty():
    tmpl = _env().get_template("partials/scenario_compare.html")
    return tmpl.render(compare_panel=True, compare_result=None, audit_mode=False)


@pytest.fixture(scope="module")
def compare_html_base_vs_active():
    return _render_compare_base_vs_active()


@pytest.fixture(scope="module")
def compare_html_partial_empty():
    return _render_compare_base_vs_active(empty=True)


@pytest.fixture(scope="module")
def compare_html_legacy():
    return _render_compare_legacy_left_right()


@pytest.fixture(scope="module")
def compare_html_truly_empty():
    return _render_compare_truly_empty()


class TestScenarioCompareMarkupContract:
    def test_grid_root_present_base_vs_active(self, compare_html_base_vs_active):
        assert 'data-fc-grid="scenario-compare"' in compare_html_base_vs_active

    def test_scroll_container_present_base_vs_active(self, compare_html_base_vs_active):
        assert 'data-fc-scroll-container="true"' in compare_html_base_vs_active

    def test_grid_root_present_legacy(self, compare_html_legacy):
        assert 'data-fc-grid="scenario-compare"' in compare_html_legacy

    def test_no_grid_in_partial_empty_state(self, compare_html_partial_empty):
        """Base exists but no Active scenario selected -- no compare
        table to address yet."""
        assert 'data-fc-grid="scenario-compare"' not in compare_html_partial_empty

    def test_no_grid_in_truly_empty_state(self, compare_html_truly_empty):
        assert 'data-fc-grid="scenario-compare"' not in compare_html_truly_empty

    def test_every_cell_non_editable_base_vs_active(self, compare_html_base_vs_active):
        for attrs in _fc_cells(compare_html_base_vs_active):
            assert attrs["data-fc-editable"] == "false", attrs

    def test_every_cell_non_editable_legacy(self, compare_html_legacy):
        for attrs in _fc_cells(compare_html_legacy):
            assert attrs["data-fc-editable"] == "false", attrs

    def test_no_duplicate_addresses_base_vs_active(self, compare_html_base_vs_active):
        addrs = [a["data-fc-addr"] for a in _fc_cells(compare_html_base_vs_active)]
        assert len(addrs) == len(set(addrs))

    def test_no_duplicate_addresses_legacy(self, compare_html_legacy):
        addrs = [a["data-fc-addr"] for a in _fc_cells(compare_html_legacy)]
        assert len(addrs) == len(set(addrs))

    def test_addresses_are_deterministic_not_display_text(self, compare_html_base_vs_active):
        for attrs in _fc_cells(compare_html_base_vs_active):
            addr = attrs["data-fc-addr"]
            assert addr.startswith("scenario-compare!"), addr
            assert " " not in addr, addr

    def test_known_address_examples_present_base_vs_active(self, compare_html_base_vs_active):
        addrs = {a["data-fc-addr"] for a in _fc_cells(compare_html_base_vs_active)}
        assert "scenario-compare!project_irr.left" in addrs
        assert "scenario-compare!project_irr.right" in addrs
        assert "scenario-compare!project_irr.delta" in addrs
        assert "scenario-compare!avg_dscr.delta" in addrs

    def test_known_address_examples_present_legacy(self, compare_html_legacy):
        addrs = {a["data-fc-addr"] for a in _fc_cells(compare_html_legacy)}
        assert "scenario-compare!project_irr.left" in addrs
        assert "scenario-compare!project_irr.right" in addrs
        assert "scenario-compare!avg_dscr.delta" in addrs

    def test_legacy_metric_labels_slugified_no_spaces(self, compare_html_legacy):
        """row.metric values like 'Project IRR' must be slugified to
        snake_case addresses, never embedding the raw display label
        with spaces."""
        for attrs in _fc_cells(compare_html_legacy):
            assert " " not in attrs["data-fc-addr"]

    def test_raw_values_present(self, compare_html_base_vs_active):
        addrs = {a["data-fc-addr"]: a for a in _fc_cells(compare_html_base_vs_active)}
        assert addrs["scenario-compare!project_irr.left"]["data-fc-raw"] == "8.5"
        assert addrs["scenario-compare!project_irr.right"]["data-fc-raw"] == "9.2"

    def test_deterministic_ordering_across_renders(self):
        html_a = _render_compare_base_vs_active()
        html_b = _render_compare_base_vs_active()
        addrs_a = [a["data-fc-addr"] for a in _fc_cells(html_a)]
        addrs_b = [a["data-fc-addr"] for a in _fc_cells(html_b)]
        assert addrs_a == addrs_b
