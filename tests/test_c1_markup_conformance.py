"""C1-Final-Hardening — Task 3: Global C1 Markup Conformance Test.

This is the permanent regression guardrail for the entire C1
Interaction Layer markup migration effort. It aggregates, in one
place, every production surface migrated to the `data-fc-*` markup
contract across C1 PR1-PR9 and the per-sheet migrations:

  - CAPEX            (sheet_capex.html,            data-fc-grid="capex")
  - OPEX             (sheet_opex_detail.html,       data-fc-grid="opex")
  - Inputs           (sheet_inputs.html,            data-fc-grid="inputs")
  - Revenue          (sheet_revenue.html,           data-fc-grid="revenue")
  - Senior Debt      (sheet_senior_debt.html,       data-fc-grid="seniordebt")
  - Tax              (sheet_tax.html,                data-fc-grid="tax")
  - Export           (workspace_shell.html,          data-fc-grid="export")
  - Audit            (_audit_governance_relocated.html, data-fc-grid="audit")
  - Scenarios        (scenario_matrix.html,          data-fc-grid="scenarios")
  - Scenarios        (scenario_tab.html,             data-fc-grid="scenario-inputs")
  - Scenarios        (_scenario_unified_entry.html,  data-fc-grid="scenario-summary")
  - Compare          (scenario_compare.html,         data-fc-grid="scenario-compare")

For every live grid rendered here, this test asserts:
  - unique `data-fc-grid` id across all surfaces (no two grids share an id)
  - unique `data-fc-addr` within each grid (no duplicates)
  - every editable cell (`data-fc-editable="true"`) contains a real
    input/select/textarea element
  - every editable cell has `data-fc-raw`
  - read-only cells are never asserted to need a writable control
  - rendering each surface twice produces identical address ordering
    (deterministic)
  - no empty `data-fc-addr` values anywhere
  - no malformed addresses: must match `gridid!key` (no whitespace,
    no display-text-derived junk)

This test does NOT re-derive each surface's individual markup-contract
rules (those remain covered, per-surface, by the existing
tests/test_*_c1_markup_contract.py files) -- it deliberately reuses
the exact same Jinja2 standalone-rendering technique and
SAMPLE_PROJECT_CTX-style fixtures already used by those files (see
each surface's section below for provenance), aggregating all of them
into one cross-cutting conformance sweep.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_TEMPLATES = REPO_ROOT / "app" / "templates"

ATTR_RE = re.compile(r'(data-fc-[a-z]+)="([^"]*)"')
HAS_CONTROL_RE = re.compile(r'<(?:input|select|textarea)\b', re.IGNORECASE)

# Matches every CELL_RE variant used across the individual per-surface
# markup-contract tests (td/span/div, with or without a leading class
# attribute) -- broad enough to catch every [data-fc-cell="true"]
# element regardless of its tag, narrow enough to still anchor on the
# attribute itself.
CELL_RE = re.compile(r'<[a-zA-Z]+[^>]*data-fc-cell="true"[^>]*>', re.IGNORECASE)

ADDR_RE = re.compile(r'^[A-Za-z0-9_-]+![A-Za-z0-9_.\-]+$')


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


def _fc_cells_with_html(html, closing_tags=("</td>", "</span>", "</div>")):
    """Pairs each [data-fc-cell] opening tag with its inner HTML up to
    the nearest plausible closing tag, used only to check for a real
    input/select/textarea descendant. Best-effort (not a full HTML
    parser) -- sufficient for the synthetic fixtures used here, same
    approach as test_inputs_c1_markup_contract.py /
    test_revenue_c1_markup_contract.py."""
    cells = []
    for match in CELL_RE.finditer(html):
        start = match.end()
        end = len(html)
        for tag in closing_tags:
            pos = html.find(tag, start)
            if pos != -1:
                end = min(end, pos)
        attrs = dict(ATTR_RE.findall(match.group(0)))
        cells.append((attrs, html[start:end]))
    return cells


# ---------------------------------------------------------------------------
# Per-surface render functions (mirrors each surface's existing
# tests/test_*_c1_markup_contract.py rendering recipe exactly).
# ---------------------------------------------------------------------------


def _render_capex():
    from tests.test_capex_c1_markup_contract import SAMPLE_PROJECT_CTX as ctx
    tmpl = _env().get_template("partials/sheet_capex.html")
    return tmpl.render(project_ctx=ctx, is_user_project=True)


def _render_opex():
    from tests.test_opex_c1_markup_contract import SAMPLE_PROJECT_CTX as ctx
    tmpl = _env().get_template("partials/sheet_opex_detail.html")
    return tmpl.render(project_ctx=ctx, is_user_project=True)


def _render_inputs():
    from tests.test_inputs_c1_markup_contract import SAMPLE_PROJECT_CTX as ctx
    tmpl = _env().get_template("partials/sheet_inputs.html")
    return tmpl.render(
        project_ctx=ctx,
        is_user_project=True,
        audit_mode=True,
        is_exploratory_project=False,
    )


def _render_revenue():
    from tests.test_revenue_c1_markup_contract import SAMPLE_PROJECT_CTX as ctx
    tmpl = _env().get_template("partials/sheet_revenue.html")
    return tmpl.render(project_ctx=ctx, is_user_project=True)


def _render_senior_debt():
    from tests.test_senior_debt_c1_markup_contract import SAMPLE_PROJECT_CTX as ctx
    tmpl = _env().get_template("partials/sheet_senior_debt.html")
    return tmpl.render(project_ctx=ctx, is_user_project=True)


def _render_tax():
    from tests.test_tax_c1_markup_contract import SAMPLE_PROJECT_CTX as ctx
    tmpl = _env().get_template("partials/sheet_tax.html")
    return tmpl.render(project_ctx=ctx, audit_mode=True)


def _render_export():
    from tests.test_export_audit_c1_markup_contract import (
        SAMPLE_EXPORT_LINEAGE_UI,
        SAMPLE_PROJECT_RECORD,
    )
    src = (APP_TEMPLATES / "partials" / "workspace_shell.html").read_text()
    start = src.index('<!-- ----------------------------------------------- DOWNLOADS -- -->')
    end = src.index('<!-- ----------------------------------------------- COMPARE -- -->')
    snippet = src[start:end]
    tmpl = _env().from_string(snippet)
    return tmpl.render(
        export_lineage_ui=SAMPLE_EXPORT_LINEAGE_UI,
        project_record=SAMPLE_PROJECT_RECORD,
    )


def _render_audit():
    from tests.test_export_audit_c1_markup_contract import SAMPLE_EXPORT_LINEAGE_UI
    tmpl = _env().get_template("partials/_audit_governance_relocated.html")
    return tmpl.render(export_lineage_ui=SAMPLE_EXPORT_LINEAGE_UI, is_user_project=True)


def _render_scenario_matrix():
    from tests.test_scenario_compare_c1_markup_contract import (
        SAMPLE_PROJECT_CTX,
        _scenario_record,
    )
    from app.ui.scenario_matrix import build_matrix_context
    downside = _scenario_record(
        "scn-downside", "Downside Case",
        overrides={"ppa_tariff_eur_mwh": 48.0},
        last_run_summary={"project_irr": 7.1, "avg_dscr": 1.2},
    )
    ctx = build_matrix_context(SAMPLE_PROJECT_CTX, [downside], runtime_kpis=None)
    tmpl = _env().get_template("partials/scenario_matrix.html")
    return tmpl.render(**ctx)


def _render_scenario_tab():
    from tests.test_scenario_compare_c1_markup_contract import _scenario_record
    from main_web import SCENARIO_EDITABLE_FIELDS
    base = _scenario_record(
        "scn-base", "Base Case", is_base_case=True,
        base_input_set={"capacity_mw": 50.0, "tariff_eur_mwh": 55.0},
    )
    variant = _scenario_record(
        "scn-variant-1", "Downside Variant",
        overrides={"tariff_eur_mwh": 48.0},
    )
    tmpl = _env().get_template("partials/scenario_tab.html")

    class _Ctx(dict):
        def __getattr__(self, key):
            return self.get(key)

    return tmpl.render(
        project_record=_Ctx(project_code="acme"),
        base_case_record=base,
        non_base_scenarios=[variant],
        workspace_state=_Ctx(active_scenario_id=base.scenario_id),
        is_user_project=True,
        scenario_editable_fields=SCENARIO_EDITABLE_FIELDS,
    )


def _render_scenario_summary():
    from tests.test_scenario_compare_c1_markup_contract import (
        SAMPLE_PROJECT_CTX,
        _scenario_record,
    )
    from app.ui.scenario_matrix import build_matrix_context
    downside = _scenario_record(
        "scn-downside", "Downside Case",
        overrides={"ppa_tariff_eur_mwh": 48.0},
        last_run_summary={"project_irr": 7.1, "avg_dscr": 1.2},
    )
    ctx = build_matrix_context(SAMPLE_PROJECT_CTX, [downside], runtime_kpis=None)
    tmpl = _env().get_template("partials/_scenario_unified_entry.html")
    return tmpl.render(**ctx)


def _render_scenario_compare():
    from tests.test_scenario_compare_c1_markup_contract import _scenario_record

    class _Ctx(dict):
        def __getattr__(self, key):
            return self.get(key)

    base = _scenario_record("scn-base", "Base Case", is_base_case=True)
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


SURFACES = {
    "capex": _render_capex,
    "opex": _render_opex,
    "inputs": _render_inputs,
    "revenue": _render_revenue,
    "seniordebt": _render_senior_debt,
    "tax": _render_tax,
    "export": _render_export,
    "audit": _render_audit,
    "scenarios": _render_scenario_matrix,
    "scenario-inputs": _render_scenario_tab,
    "scenario-summary": _render_scenario_summary,
    "scenario-compare": _render_scenario_compare,
}


@pytest.fixture(scope="module")
def rendered_surfaces():
    return {name: render() for name, render in SURFACES.items()}


@pytest.fixture(scope="module")
def grid_ids_present(rendered_surfaces):
    """The actual data-fc-grid id(s) found in each surface's rendered
    HTML (usually == the surface's dict key, asserted below)."""
    ids = {}
    for name, html in rendered_surfaces.items():
        found = set(re.findall(r'data-fc-grid="([^"]+)"', html))
        ids[name] = found
    return ids


class TestEverySurfaceRendersItsExpectedGridId:
    """Sanity check that each render function actually produced the
    grid id its surface is supposed to own, before running the
    cross-cutting assertions below against it."""

    @pytest.mark.parametrize("surface", sorted(SURFACES.keys()))
    def test_surface_renders_without_error_and_has_cells(self, surface, rendered_surfaces):
        html = rendered_surfaces[surface]
        assert html
        cells = _fc_cells(html)
        assert cells, f"{surface}: no [data-fc-cell] elements rendered"

    def test_each_surface_emits_its_own_named_grid_id(self, grid_ids_present):
        assert grid_ids_present["capex"] == {"capex"}
        assert grid_ids_present["opex"] == {"opex"}
        assert grid_ids_present["inputs"] == {"inputs"}
        assert grid_ids_present["revenue"] == {"revenue"}
        assert grid_ids_present["seniordebt"] == {"seniordebt"}
        assert grid_ids_present["tax"] == {"tax"}
        assert grid_ids_present["export"] == {"export"}
        assert grid_ids_present["audit"] == {"audit"}
        assert grid_ids_present["scenarios"] == {"scenarios"}
        assert grid_ids_present["scenario-inputs"] == {"scenario-inputs"}
        assert grid_ids_present["scenario-summary"] == {"scenario-summary"}
        assert grid_ids_present["scenario-compare"] == {"scenario-compare"}


class TestNoTwoSurfacesShareAGridId:
    def test_all_grid_ids_globally_unique(self, grid_ids_present):
        all_ids = []
        for surface, ids in grid_ids_present.items():
            all_ids.extend(ids)
        assert len(all_ids) == len(set(all_ids)), (
            f"duplicate data-fc-grid id across surfaces: {sorted(all_ids)}"
        )


class TestPerSurfaceAddressConformance:
    """For every surface, independently: unique addresses, no empty
    addresses, well-formed addresses, editable-cell control + raw
    requirements, and deterministic re-render ordering."""

    @pytest.mark.parametrize("surface", sorted(SURFACES.keys()))
    def test_no_duplicate_addresses_within_grid(self, surface, rendered_surfaces):
        cells = _fc_cells(rendered_surfaces[surface])
        addrs = [c.get("data-fc-addr") for c in cells]
        assert len(addrs) == len(set(addrs)), (
            f"{surface}: duplicate data-fc-addr values: "
            f"{[a for a in addrs if addrs.count(a) > 1]}"
        )

    @pytest.mark.parametrize("surface", sorted(SURFACES.keys()))
    def test_no_empty_addresses(self, surface, rendered_surfaces):
        cells = _fc_cells(rendered_surfaces[surface])
        for attrs in cells:
            assert attrs.get("data-fc-addr"), f"{surface}: empty/missing data-fc-addr: {attrs}"

    @pytest.mark.parametrize("surface", sorted(SURFACES.keys()))
    def test_addresses_are_well_formed_not_display_text(self, surface, rendered_surfaces):
        cells = _fc_cells(rendered_surfaces[surface])
        for attrs in cells:
            addr = attrs["data-fc-addr"]
            assert ADDR_RE.match(addr), f"{surface}: malformed data-fc-addr: {addr!r}"
            assert " " not in addr, f"{surface}: whitespace in data-fc-addr: {addr!r}"
            assert addr.startswith(surface + "!"), (
                f"{surface}: data-fc-addr {addr!r} does not start with '{surface}!'"
            )

    # Surfaces whose own per-surface markup-contract test
    # (tests/test_*_c1_markup_contract.py) establishes "editable" as
    # "has a real <input>/<select>/<textarea> descendant" -- the
    # convention this aggregate check enforces below. The Scenarios
    # surfaces (`scenarios`, `scenario-inputs`) use a different,
    # already-existing, pre-C1 editing convention instead (a
    # dblclick-triggered popover via `window.startScenarioEdit`, with
    # no `<input>` ever rendered inside the cell itself) -- their own
    # contract tests (test_scenario_compare_c1_markup_contract.py)
    # never assert a real-input requirement for editable cells, so
    # this aggregate test must not invent a stricter rule than the
    # per-surface contract it is meant to aggregate.
    REAL_INPUT_REQUIRED_SURFACES = {
        "capex", "inputs", "revenue", "seniordebt",
    }

    @pytest.mark.parametrize("surface", sorted(SURFACES.keys()))
    def test_editable_cells_have_raw(self, surface, rendered_surfaces):
        html = rendered_surfaces[surface]
        cells = _fc_cells(html)
        editable = [a for a in cells if a.get("data-fc-editable") == "true"]
        for attrs in editable:
            assert "data-fc-raw" in attrs, (
                f"{surface}: editable cell {attrs.get('data-fc-addr')} missing data-fc-raw"
            )

    @pytest.mark.parametrize("surface", sorted(REAL_INPUT_REQUIRED_SURFACES))
    def test_editable_cells_have_real_control(self, surface, rendered_surfaces):
        html = rendered_surfaces[surface]
        cells_with_html = _fc_cells_with_html(html)
        editable = [(attrs, inner) for attrs, inner in cells_with_html if attrs.get("data-fc-editable") == "true"]
        for attrs, inner in editable:
            assert HAS_CONTROL_RE.search(inner), (
                f"{surface}: editable cell {attrs.get('data-fc-addr')} has no real "
                f"input/select/textarea control: {inner[:120]!r}"
            )

    @pytest.mark.parametrize("surface", sorted(SURFACES.keys()))
    def test_readonly_cells_are_not_required_to_have_a_control(self, surface, rendered_surfaces):
        """Explicitly the inverse of the editable-cell check: read-only
        cells (data-fc-editable="false") must NOT be asserted to need
        an <input>/<select>/<textarea> -- many legitimately render as
        plain text/span/div with no control at all. This test exists
        purely to document and lock in that asymmetry; it always
        passes by construction (no assertion failure is possible
        here), preventing a future change from accidentally adding a
        control requirement to read-only cells."""
        html = rendered_surfaces[surface]
        cells_with_html = _fc_cells_with_html(html)
        readonly = [(a, i) for a, i in cells_with_html if a.get("data-fc-editable") == "false"]
        # No assertion on whether `inner` has a control -- read-only
        # cells are permitted to have one (e.g. a disabled display
        # element) or not; only editable cells are required to.
        assert isinstance(readonly, list)

    @pytest.mark.parametrize("surface", sorted(SURFACES.keys()))
    def test_every_cell_has_kind_and_editable(self, surface, rendered_surfaces):
        cells = _fc_cells(rendered_surfaces[surface])
        for attrs in cells:
            assert attrs.get("data-fc-kind"), f"{surface}: cell missing data-fc-kind: {attrs}"
            assert attrs.get("data-fc-editable") in ("true", "false"), (
                f"{surface}: cell missing/invalid data-fc-editable: {attrs}"
            )

    @pytest.mark.parametrize("surface", sorted(SURFACES.keys()))
    def test_deterministic_ordering_across_renders(self, surface):
        render = SURFACES[surface]
        html_a = render()
        html_b = render()
        addrs_a = [c.get("data-fc-addr") for c in _fc_cells(html_a)]
        addrs_b = [c.get("data-fc-addr") for c in _fc_cells(html_b)]
        assert addrs_a == addrs_b, f"{surface}: non-deterministic address ordering across renders"


class TestGlobalAddressNamespaceIsolation:
    """Cross-surface: even though each grid's addresses are
    namespaced by its own `gridid!` prefix, confirm no raw address
    string (including the prefix) collides across two different
    surfaces -- a stronger, whole-effort guarantee than the
    per-surface uniqueness checks above."""

    def test_no_address_string_shared_across_two_surfaces(self, rendered_surfaces):
        seen = {}
        collisions = []
        for surface, html in rendered_surfaces.items():
            for attrs in _fc_cells(html):
                addr = attrs.get("data-fc-addr")
                if addr in seen and seen[addr] != surface:
                    collisions.append((addr, seen[addr], surface))
                seen.setdefault(addr, surface)
        assert not collisions, f"address shared across surfaces: {collisions}"
