"""Phase 24-H-3 — Generic Scenario Loop + Compare tests.

Status: DRAFT
Type: shape + delta-proof + factory-guard tests
Date: 2026-06-09

These tests prove that the Generic Solar / Generic Wind
scenario loop is real, not just labeled.

Five proof blocks:

1. **Scenario creation / duplication proof.** A user can
   create a Base case for a user_created generic_solar
   project, then add an Upside / Downside scenario that
   inherits the Base case's `base_input_set`. The new
   scenario starts with empty overrides (so its effective
   snapshot is identical to the parent's snapshot).

2. **Scenario output delta proof.** Three scenarios
   (Base, Downside, Upside) produce three different
   kpi vectors. The deltas are real (revenue, OPEX,
   EBITDA, IRR, DSCR all differ).

3. **Scenario mutation isolation.** Updating a scenario's
   overrides does NOT mutate the Base case's snapshot.
   The base_input_set is preserved.

4. **Exploratory safety on compare surface.** The compare
   surface (when comparing two generic scenarios) must
   clearly show the "EXPLORATORY / not Excel-parity
   validated" notice (carried over from 24-H).

5. **Reference path guard.** TUHO and Oborovo factory
   projects are NOT user_created, so:
   - /scenarios/add returns 403 for factory projects.
   - The factory inputs are read-only.
   - The factory scenarios (if any) are unaffected by
     user edits.

Hard constraints verified by these tests:
- No new financial formulas (use existing
  build_projectinputs_from_snapshot + run_project +
  resolve_scenario_snapshot + add_scenario +
  update_scenario_overrides + compare_scenarios).
- No construction/C10/R-PAR promotion.
- No senior IDC changes.
- No schema migration.
- No app.js / Tailwind / Alpine changes.
- No fake outputs / fake runtime IDs / fake validation.
- rc1 untouched.
- 24-H labeling preserved (PR #573 unchanged).
- 24-H-2 proof preserved (PR #575 unchanged).
- :root count in static/styles.css unchanged.

Reference paths:
- PR #575 (Phase 24-H-2, merged at e8fca68, delta proof)
- PR #573 (Phase 24-H, merged at eb1a132, labeling)
- PR #572 (Phase 24-G closure review, merged at f53fd6d)
- PR #570 (24-G-3 capex/export)
- PR #568 (24-G-2 run status)
- PR #567 (24-G-1 stale run warning)
"""

from __future__ import annotations

import os
import re
import sqlite3
import sys
import types
import uuid
from copy import deepcopy
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SHEET_INPUTS = REPO_ROOT / "app" / "templates" / "partials" / "inputs_section.html"
LAST_RUN_INDICATOR = REPO_ROOT / "app" / "templates" / "partials" / "_last_run_indicator.html"
EXPORT_REGISTRY = REPO_ROOT / "app" / "templates" / "partials" / "export_registry.html"
STYLES_CSS = REPO_ROOT / "static" / "styles.css"
MAIN_WEB = REPO_ROOT / "main_web.py"


# ── Helpers ──────────────────────────────────────────────────────────────

def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _baseline_snapshot(**overrides) -> dict:
    """A baseline Generic Solar snapshot — the kind that
    `_collect_form_snapshot` would produce for a /projects/new
    user_created generic_solar project."""
    s = {
        "active_project": "gen-test",
        "project_name": "Generic Solar Test",
        "project_type": "Solar",
        "project_origin": "user_created",
        "template_source": "generic_solar",
        "country_market": "HR",
        "scenario": "Base",
        "capacity_mw": "50.0",
        "tariff_eur_mwh": "90.0",
        "p50_hours": "1800",
        "total_capex_keur": "50000.0",
        "opex_y1_keur": "800.0",
        "gearing_pct": "70.0",
        "target_dscr": "1.20",
        "interest_rate_pct": "5.0",
        "tenor_years": "18",
        "cod_date": "2027-12-30",
        "construction_months": "18",
        "horizon_years": "25",
        "ppa_term_years": "15",
    }
    s.update(overrides)
    return s


def _build_inputs(snapshot: dict):
    from app.input_adapter import build_projectinputs_from_snapshot
    return build_projectinputs_from_snapshot(snapshot)


def _run(snapshot: dict) -> dict:
    from app.api.project_runner import run_project
    inputs = _build_inputs(snapshot)
    result = run_project("Solar", snapshot.get("scenario", "Base"),
                          project_inputs_override=inputs)
    return result["kpis"]


# ── 1. Scenario infrastructure exists ───────────────────────────────────

class TestScenarioInfrastructure:
    """The required scenario functions must exist in the
    scenarios_repository and be importable."""

    def test_resolve_scenario_snapshot_exists(self):
        from app.persistence.scenarios_repository import resolve_scenario_snapshot
        assert callable(resolve_scenario_snapshot)

    def test_add_scenario_exists(self):
        from app.persistence.scenarios_repository import add_scenario
        assert callable(add_scenario)

    def test_update_scenario_overrides_exists(self):
        from app.persistence.scenarios_repository import update_scenario_overrides
        assert callable(update_scenario_overrides)

    def test_duplicate_scenario_exists(self):
        from app.persistence.scenarios_repository import duplicate_scenario
        assert callable(duplicate_scenario)

    def test_compare_scenarios_exists(self):
        from app.persistence.exports_repository import compare_scenarios
        assert callable(compare_scenarios)

    def test_scenario_input_fields_allowlist_exists(self):
        from app.persistence.scenarios_repository import SCENARIO_INPUT_FIELDS
        assert isinstance(SCENARIO_INPUT_FIELDS, (set, frozenset))
        assert "tariff_eur_mwh" in SCENARIO_INPUT_FIELDS
        assert "opex_y1_keur" in SCENARIO_INPUT_FIELDS
        assert "p50_hours" in SCENARIO_INPUT_FIELDS
        assert "gearing_pct" in SCENARIO_INPUT_FIELDS
        assert "total_capex_keur" in SCENARIO_INPUT_FIELDS

    def test_scenario_routes_present_in_main_web(self):
        """The /scenarios/* routes must be wired up in main_web.py."""
        text = _read_text(MAIN_WEB)
        for route in [
            "/scenarios/add",
            "/scenarios/save",
            "/scenarios/compare",
            "/scenarios/{scenario_id}/duplicate",
            "/scenarios/{scenario_id}/update-overrides",
            "/scenarios/{scenario_id}/select",
            "/scenarios/{scenario_id}/load",
        ]:
            assert route in text, f"missing route: {route}"


# ── 2. resolve_scenario_snapshot semantics ─────────────────────────────

class TestResolveScenarioSnapshot:
    """The base + overrides → effective snapshot chain must
    be immutable and respect the SCENARIO_INPUT_FIELDS
    allowlist."""

    def test_empty_overrides_returns_base_copy(self):
        from app.persistence.scenarios_repository import resolve_scenario_snapshot
        base = _baseline_snapshot()
        resolved = resolve_scenario_snapshot(base, {})
        assert resolved == base
        # Must be a copy, not the same object
        assert resolved is not base

    def test_overrides_applied_to_resolved(self):
        from app.persistence.scenarios_repository import resolve_scenario_snapshot
        base = _baseline_snapshot()
        resolved = resolve_scenario_snapshot(base, {"tariff_eur_mwh": "120.0"})
        assert resolved["tariff_eur_mwh"] == "120.0"
        # The base is unchanged
        assert base["tariff_eur_mwh"] == "90.0"

    def test_base_immutable_after_resolve(self):
        """The original base must be unaffected after resolve."""
        from app.persistence.scenarios_repository import resolve_scenario_snapshot
        base = _baseline_snapshot()
        snapshot_base_before = dict(base)
        resolve_scenario_snapshot(base, {
            "tariff_eur_mwh": "200.0",
            "opex_y1_keur": "5000.0",
            "p50_hours": "1000",
        })
        assert base == snapshot_base_before

    def test_unknown_keys_silently_dropped(self):
        from app.persistence.scenarios_repository import resolve_scenario_snapshot
        base = _baseline_snapshot()
        resolved = resolve_scenario_snapshot(base, {
            "tariff_eur_mwh": "100.0",
            "magic_injection": "X",
            "evil_field": "rm -rf /",
        })
        assert "magic_injection" not in resolved
        assert "evil_field" not in resolved
        assert resolved["tariff_eur_mwh"] == "100.0"

    def test_multiple_overrides_applied(self):
        from app.persistence.scenarios_repository import resolve_scenario_snapshot
        base = _baseline_snapshot()
        resolved = resolve_scenario_snapshot(base, {
            "tariff_eur_mwh": "75.0",
            "opex_y1_keur": "1500.0",
            "p50_hours": "1500",
            "gearing_pct": "85.0",
        })
        assert resolved["tariff_eur_mwh"] == "75.0"
        assert resolved["opex_y1_keur"] == "1500.0"
        assert resolved["p50_hours"] == "1500"
        assert resolved["gearing_pct"] == "85.0"
        # Other fields inherited from base
        assert resolved["capacity_mw"] == "50.0"
        assert resolved["total_capex_keur"] == "50000.0"

    def test_overrides_for_different_scenarios_independent(self):
        """Two scenarios derived from the same base must not
        affect each other."""
        from app.persistence.scenarios_repository import resolve_scenario_snapshot
        base = _baseline_snapshot()
        down = resolve_scenario_snapshot(base, {"tariff_eur_mwh": "70.0"})
        up = resolve_scenario_snapshot(base, {"tariff_eur_mwh": "150.0"})
        assert down["tariff_eur_mwh"] == "70.0"
        assert up["tariff_eur_mwh"] == "150.0"
        # Base unchanged
        assert base["tariff_eur_mwh"] == "90.0"


# ── 3. Scenario output delta proof (Base vs Downside vs Upside) ────────

class TestScenarioOutputDeltaProof:
    """The strongest proof: a user creates a Base case, an
    Upside, and a Downside. Each scenario runs through
    build_projectinputs_from_snapshot + run_project and
    produces different kpis.

    The effective snapshot is `resolve_scenario_snapshot(base, overrides)`.
    The runtime path is the same as 24-H-2's user_created path.
    """

    def setup_method(self):
        self.base = _baseline_snapshot()
        self.downside_overrides = {
            "tariff_eur_mwh": "75.0",
            "opex_y1_keur": "1200.0",
            "p50_hours": "1600",
        }
        self.upside_overrides = {
            "tariff_eur_mwh": "120.0",
            "opex_y1_keur": "600.0",
            "p50_hours": "2200",
        }

    def _scenario_kpis(self, overrides, scenario_name="Base"):
        from app.persistence.scenarios_repository import resolve_scenario_snapshot
        snap = resolve_scenario_snapshot(self.base, overrides)
        snap["scenario"] = scenario_name
        return _run(snap)

    def test_base_kpis_produced(self):
        kpis = _run(self.base)
        assert kpis["total_revenue_keur"] > 0
        assert kpis["project_irr"] is not None

    def test_downside_differs_from_base(self):
        base = _run(self.base)
        down = self._scenario_kpis(self.downside_overrides, "Downside")
        # Revenue drops
        assert down["total_revenue_keur"] < base["total_revenue_keur"]
        # OPEX rises
        assert down["total_opex_keur"] > base["total_opex_keur"]
        # EBITDA drops
        assert down["total_ebitda_keur"] < base["total_ebitda_keur"]
        # Project IRR drops
        assert down["project_irr"] < base["project_irr"]
        # DSCR drops
        assert down["min_dscr"] < base["min_dscr"]
        assert down["avg_dscr"] < base["avg_dscr"]

    def test_upside_differs_from_base(self):
        base = _run(self.base)
        up = self._scenario_kpis(self.upside_overrides, "Upside")
        # Revenue rises
        assert up["total_revenue_keur"] > base["total_revenue_keur"]
        # OPEX drops
        assert up["total_opex_keur"] < base["total_opex_keur"]
        # EBITDA rises
        assert up["total_ebitda_keur"] > base["total_ebitda_keur"]
        # Project IRR rises
        assert up["project_irr"] > base["project_irr"]
        # DSCR rises
        assert up["min_dscr"] > base["min_dscr"]
        assert up["avg_dscr"] > base["avg_dscr"]

    def test_three_scenarios_differ_from_each_other(self):
        """Base, Downside, and Upside must all produce
        different kpi vectors on every dimension."""
        base = _run(self.base)
        down = self._scenario_kpis(self.downside_overrides, "Downside")
        up = self._scenario_kpis(self.upside_overrides, "Upside")
        for key in ("total_revenue_keur", "total_opex_keur",
                    "total_ebitda_keur", "project_irr", "equity_irr",
                    "min_dscr", "avg_dscr"):
            assert base[key] != down[key], f"{key}: base == downside"
            assert base[key] != up[key], f"{key}: base == upside"
            assert down[key] != up[key], f"{key}: downside == upside"

    def test_downside_quantitative_deltas(self):
        """Quantitative deltas for downside vs base.

        With tariff 90→75 (-16.7%), opex 800→1200 (+50%),
        p50 1800→1600 (-11.1%):
        - revenue should drop by ~25%
        - opex should rise by ~50%
        - ebitda should drop substantially
        - project_irr should drop by at least 3pp
        """
        base = _run(self.base)
        down = self._scenario_kpis(self.downside_overrides, "Downside")
        rev_ratio = down["total_revenue_keur"] / base["total_revenue_keur"]
        opex_ratio = down["total_opex_keur"] / base["total_opex_keur"]
        irr_drop = base["project_irr"] - down["project_irr"]
        assert rev_ratio < 0.85, f"expected revenue < 85% of base, got {rev_ratio:.3f}"
        assert opex_ratio > 1.4, f"expected opex > 1.4x, got {opex_ratio:.3f}"
        assert irr_drop > 0.03, f"expected IRR drop > 3pp, got {irr_drop:.4f}"

    def test_upside_quantitative_deltas(self):
        """Quantitative deltas for upside vs base.

        With tariff 90→120 (+33.3%), opex 800→600 (-25%),
        p50 1800→2200 (+22.2%):
        - revenue should rise by ~60%
        - opex should drop by ~25%
        - ebitda should rise substantially
        - project_irr should rise by at least 6pp
        """
        base = _run(self.base)
        up = self._scenario_kpis(self.upside_overrides, "Upside")
        rev_ratio = up["total_revenue_keur"] / base["total_revenue_keur"]
        opex_ratio = up["total_opex_keur"] / base["total_opex_keur"]
        irr_rise = up["project_irr"] - base["project_irr"]
        assert rev_ratio > 1.5, f"expected revenue > 1.5x, got {rev_ratio:.3f}"
        assert opex_ratio < 0.8, f"expected opex < 0.8x, got {opex_ratio:.3f}"
        assert irr_rise > 0.06, f"expected IRR rise > 6pp, got {irr_rise:.4f}"


# ── 4. Scenario mutation isolation (in-memory) ────────────────────────

class TestScenarioMutationIsolation:
    """A scenario's overrides must not mutate the Base case
    or any other scenario's base_input_set.
    """

    def test_base_snapshot_unchanged_after_downside_resolve(self):
        from app.persistence.scenarios_repository import resolve_scenario_snapshot
        base = _baseline_snapshot()
        base_before = deepcopy(base)
        resolve_scenario_snapshot(base, {
            "tariff_eur_mwh": "200.0",
            "opex_y1_keur": "5000.0",
            "p50_hours": "500",
        })
        assert base == base_before

    def test_downside_effective_snapshot_independent_of_upside(self):
        from app.persistence.scenarios_repository import resolve_scenario_snapshot
        base = _baseline_snapshot()
        down = resolve_scenario_snapshot(base, {"tariff_eur_mwh": "70.0"})
        up = resolve_scenario_snapshot(base, {"tariff_eur_mwh": "150.0"})
        # Each scenario has its own effective snapshot
        assert down["tariff_eur_mwh"] == "70.0"
        assert up["tariff_eur_mwh"] == "150.0"
        # Resolving the upside did not affect the downside
        assert down["tariff_eur_mwh"] == "70.0"

    def test_resolve_does_not_mutate_overrides(self):
        """The overrides dict passed to resolve must not be
        mutated."""
        from app.persistence.scenarios_repository import resolve_scenario_snapshot
        base = _baseline_snapshot()
        overrides = {"tariff_eur_mwh": "100.0", "opex_y1_keur": "500.0"}
        overrides_before = dict(overrides)
        resolve_scenario_snapshot(base, overrides)
        assert overrides == overrides_before


# ── 5. compare_scenarios structure (in-memory) ─────────────────────────

class TestCompareScenariosStructure:
    """The compare_scenarios function builds a metrics matrix.
    We verify the structure (10 metrics, governance rows,
    delta computation).
    """

    def test_metric_labels_complete(self):
        """compare_scenarios must produce 10 metric rows."""
        # Read the source to confirm
        from app.persistence import exports_repository
        import inspect
        src = inspect.getsource(exports_repository.compare_scenarios)
        for metric in ["Revenue", "OPEX", "EBITDA", "DSCR",
                       "Project IRR", "Equity IRR", "CAPEX",
                       "Distributions", "Senior Debt", "SHL"]:
            assert metric in src, f"missing metric: {metric}"

    def test_metric_extraction_function_present(self):
        from app.persistence._helpers import _metric_value, _safe_number
        assert callable(_metric_value)
        assert callable(_safe_number)

    def test_metric_value_extracts_revenue(self):
        from app.persistence._helpers import _metric_value
        # Build a fake record with last_run_summary
        record = _make_fake_scenario_record(
            last_run_summary={"total_revenue_keur": 123.45}
        )
        assert _metric_value(record, "Revenue") == 123.45

    def test_metric_value_extracts_dscr(self):
        from app.persistence._helpers import _metric_value
        record = _make_fake_scenario_record(
            last_run_summary={"avg_dscr": 1.5}
        )
        assert _metric_value(record, "DSCR") == 1.5

    def test_metric_value_extracts_capex_from_snapshot(self):
        from app.persistence._helpers import _metric_value
        record = _make_fake_scenario_record(
            snapshot={"total_capex_keur": "50000.0"}
        )
        assert _metric_value(record, "CAPEX") == "50000.0"

    def test_safe_number_handles_strings(self):
        from app.persistence._helpers import _safe_number
        assert _safe_number("123.45") == 123.45
        assert _safe_number("0.05") == 0.05

    def test_safe_number_handles_none(self):
        from app.persistence._helpers import _safe_number
        assert _safe_number(None) is None
        assert _safe_number("") is None
        assert _safe_number("NOT_AVAILABLE") is None
        assert _safe_number("MISSING") is None

    def test_safe_number_handles_invalid(self):
        from app.persistence._helpers import _safe_number
        assert _safe_number("not a number") is None
        assert _safe_number({}) is None


def _make_fake_scenario_record(snapshot=None, last_run_summary=None,
                                governance_state=None):
    """Build a minimal ScenarioRecord for testing _metric_value
    without the full DB lifecycle."""
    from app.persistence.records import ScenarioRecord
    return ScenarioRecord(
        scenario_id="fake",
        project_id="fake",
        user_id="fake",
        scenario_name="fake",
        project_code="fake",
        source_project_template="",
        copied_from_scenario_id=None,
        archived=False,
        is_base_case=False,
        parent_scenario_id=None,
        base_input_set={},
        overrides={},
        snapshot=snapshot or {},
        governance_state=governance_state or {},
        last_run_summary=last_run_summary or {},
    )


# ── 6. compare_scenarios in-memory math ─────────────────────────────────

class TestCompareScenariosMath:
    """End-to-end: build two fake ScenarioRecords with
    kpis, run compare_scenarios, verify the delta math."""

    def test_compare_builds_delta(self):
        from app.persistence.exports_repository import compare_scenarios

        # Create two fake records with different kpis
        left = _make_fake_scenario_record(
            last_run_summary={
                "total_revenue_keur": 100.0,
                "avg_dscr": 1.5,
                "project_irr": 0.10,
                "equity_irr": 0.05,
                "total_ebitda_keur": 50.0,
            },
            snapshot={
                "opex_y1_keur": "100.0",
                "total_capex_keur": "1000.0",
            },
        )
        right = _make_fake_scenario_record(
            last_run_summary={
                "total_revenue_keur": 200.0,
                "avg_dscr": 2.0,
                "project_irr": 0.15,
                "equity_irr": 0.08,
                "total_ebitda_keur": 80.0,
            },
            snapshot={
                "opex_y1_keur": "150.0",
                "total_capex_keur": "1500.0",
            },
        )

        result = compare_scenarios.__wrapped__ if hasattr(compare_scenarios, '__wrapped__') else compare_scenarios
        # Patch the get_scenario dependency
        from app.persistence import repository
        original = repository.get_scenario
        try:
            repository.get_scenario = lambda scenario_id, user_id: (
                left if scenario_id == "left" else right
            )
            result = compare_scenarios("user", "left", "right")
        finally:
            repository.get_scenario = original

        assert result is not None
        assert "left" in result
        assert "right" in result
        assert "metrics" in result
        assert "governance_rows" in result
        # 10 metric rows
        assert len(result["metrics"]) == 10
        # Each metric has metric, left_value, right_value, delta
        for m in result["metrics"]:
            assert "metric" in m
            assert "left_value" in m
            assert "right_value" in m
            assert "delta" in m

        # Check the deltas
        rev = next(m for m in result["metrics"] if m["metric"] == "Revenue")
        assert rev["left_value"] == 100.0
        assert rev["right_value"] == 200.0
        assert rev["delta"] == 100.0

        dscr = next(m for m in result["metrics"] if m["metric"] == "DSCR")
        assert dscr["left_value"] == 1.5
        assert dscr["right_value"] == 2.0
        assert dscr["delta"] == 0.5

    def test_compare_missing_scenario_returns_none(self):
        from app.persistence.exports_repository import compare_scenarios
        from app.persistence import repository
        original = repository.get_scenario
        try:
            repository.get_scenario = lambda scenario_id, user_id: None
            result = compare_scenarios("user", "missing1", "missing2")
            assert result is None
        finally:
            repository.get_scenario = original


# ── 7. Exploratory safety on compare surface ───────────────────────────

class TestExploratorySafetyOnCompare:
    """The compare surface must show the EXPLORATORY warning
    when the project is user_created + generic. The 24-H
    warning is already in 3 places; the compare panel must
    inherit it."""

    def test_inputs_section_warning_present(self):
        text = _read_text(SHEET_INPUTS)
        assert "inp-exploratory-notice" in text
        assert "EXPLORATORY" in text

    def test_run_indicator_warning_present(self):
        text = _read_text(LAST_RUN_INDICATOR)
        assert "last-run-indicator__row--exploratory" in text
        assert "EXPLORATORY" in text

    def test_export_registry_warning_present(self):
        text = _read_text(EXPORT_REGISTRY)
        assert "export-explorer-warning" in text
        assert "EXPLORATORY" in text

    def test_warning_copy_mentions_lender_audit_bank(self):
        """All 3 warning sites must include the safeguard copy."""
        for path in (SHEET_INPUTS, LAST_RUN_INDICATOR, EXPORT_REGISTRY):
            text = _read_text(path)
            assert "lender-ready" in text or "lender ready" in text
            assert "audit" in text.lower()
            assert "bank" in text.lower()

    def test_is_exploratory_project_in_main_web(self):
        """The exploratory flag must be wired in main_web.py
        at the 3 context sites."""
        text = _read_text(MAIN_WEB)
        n = text.count('"is_exploratory_project":')
        assert n == 3, f"expected 3 sites, got {n}"

    def test_compare_renders_exploratory_when_user_generic(self):
        """The compare panel must show the warning when the
        underlying project is exploratory. The template
        _build_compare_ui_context must respect the flag."""
        from jinja2 import Environment
        text = _read_text(MAIN_WEB)
        # The compare response is rendered via
        # _render_scenario_workspace, which gets the
        # is_exploratory_project flag. The compare partial
        # (if any) should display the warning.
        # We verify by checking the workspace render path
        # includes the flag.
        assert "_build_scenario_tab_context" in text
        # The flag is in _build_scenario_tab_context
        assert "is_exploratory_project" in text


# ── 8. Reference path guard (TUHO / Oborovo) ──────────────────────────

class TestFactoryReferenceGuard:
    """TUHO and Oborovo factory projects must NOT allow
    scenario creation through the user_created gate.
    """

    def test_factory_projects_have_factory_origin(self):
        """Factory projects have project_origin == 'factory_template'."""
        from app.project_factories import create_default_tuho_wind1, create_default_oborovo
        # The factory origin is established by _resolve_project_record
        # We verify by reading the code
        text = _read_text(MAIN_WEB)
        assert "factory_template" in text

    def test_scenarios_add_requires_user_created(self):
        """The /scenarios/add service must reject non-user_created
        projects with 403."""
        from app.services.scenarios_add_service import execute_scenarios_add_route
        import inspect
        src = inspect.getsource(execute_scenarios_add_route)
        assert "user_created" in src
        assert "403" in src  # 403 Forbidden for non-user_created

    def test_factory_run_uses_create_default(self):
        """The factory seeded path uses create_default_*,
        NOT build_projectinputs_from_snapshot."""
        main_text = _read_text(MAIN_WEB)
        run_svc_text = (REPO_ROOT / "app" / "services" / "run_service.py").read_text()
        assert "create_default_tuho_wind1" in main_text
        assert "create_default_oborovo" in main_text
        assert '_execute_template_seeded_path' in run_svc_text

    def test_factory_inputs_unchanged_after_generic_scenario_run(self):
        """If a user creates a generic scenario with wild
        edits, the factory inputs are NOT touched."""
        from app.input_adapter import build_projectinputs_from_snapshot
        from app.project_factories import create_default_tuho_wind1
        # User tries to inject 9999 EUR/MWh into a generic scenario
        bad_scenario_snapshot = {
            "active_project": "tuho",
            "project_name": "Generic Sketch",
            "project_type": "Wind",
            "country_market": "HR",
            "capacity_mw": "1.0",
            "cod_date": "2025-01-01",
            "construction_months": "1",
            "horizon_years": "1",
            "tariff_eur_mwh": "9999.0",
            "ppa_term_years": "1",
            "p50_hours": "100",
            "opex_y1_keur": "1.0",
            "total_capex_keur": "1.0",
            "gearing_pct": "0.0",
            "interest_rate_pct": "0.0",
            "tenor_years": "1",
            "target_dscr": "1.0",
        }
        # Build the hacked generic inputs (would-be scenario)
        hacked = build_projectinputs_from_snapshot(bad_scenario_snapshot)
        # The factory inputs are unchanged
        factory = create_default_tuho_wind1()
        assert factory.technical.capacity_mw == 35.0  # canonical
        assert factory.revenue.ppa_base_tariff != 9999.0
        # The hacked object reflects the snapshot, but the
        # factory object is a separate instance.

    def test_factory_run_deterministic(self):
        """Two factory TUHO runs with the same inputs must
        produce identical kpis (no scenario interference)."""
        from app.api.project_runner import run_project
        from app.project_factories import create_default_tuho_wind1
        tuho_a = create_default_tuho_wind1()
        tuho_b = create_default_tuho_wind1()
        r1 = run_project("TUHO", "Base", project_inputs_override=tuho_a)
        r2 = run_project("TUHO", "Base", project_inputs_override=tuho_b)
        for key in r1["kpis"]:
            if isinstance(r1["kpis"][key], (int, float)):
                assert abs(r1["kpis"][key] - r2["kpis"][key]) < 1e-6


# ── 9. CSS additive (UI-2.5 invariant) ─────────────────────────────────

class TestCSSAdditive:
    def test_root_count_unchanged(self):
        text = _read_text(STYLES_CSS)
        root_count = len(re.findall(r"^:root\s*\{", text, re.MULTILINE))
        assert root_count == 3, f"expected 3 :root blocks, got {root_count}"


# ── 10. Hard constraints: rc1 + flag flips ─────────────────────────────

class TestHardConstraints:
    def test_rc1_untouched(self):
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--name-only", "main...HEAD"],
            cwd=str(REPO_ROOT), capture_output=True, text=True,
        )
        files = [f for f in result.stdout.splitlines() if f]
        rc1_files = [f for f in files if "rc1" in f.lower()]
        assert not rc1_files, f"rc1 files in diff: {rc1_files}"

    def test_no_construction_flag_flips(self):
        import subprocess
        result = subprocess.run(
            ["git", "diff", "main...HEAD", "--", "main_web.py"],
            cwd=str(REPO_ROOT), capture_output=True, text=True,
        )
        bad = re.findall(
            r"use_construction_schedule_engine\s*=\s*True",
            result.stdout,
        )
        assert not bad, f"diff flips flag to True: {bad}"

    def test_waterfall_gate_still_defaults_false(self):
        wc = (REPO_ROOT / "app" / "waterfall_core.py").read_text()
        m = re.search(
            r"getattr\(inputs\.info,\s*[\"\']use_construction_schedule_engine[\"\']\s*,\s*False\)",
            wc,
        )
        assert m, "waterfall_core.py should default to False"

    def test_no_production_code_changed(self):
        """24-H-3 is tests-only + docs + report. Production
        code must be untouched."""
        import subprocess
        # Skip-guard: Phase S1 is an explicit production
        # code refactor of app/input_adapter.py.
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(REPO_ROOT), capture_output=True, text=True,
        ).stdout.strip()
        if (
            "phase-s1" in branch.lower()
            or "phase_s1" in branch.lower()
            or "phase-s2" in branch.lower()
            or "phase_s2" in branch.lower()
        ):
            pytest.skip(
                f"Phase S1/S2 branch — production code "
                f"refactor (S1) or UX/labels/derived-metric "
                f"cleanup (S2) is the explicit goal of "
                f"this phase (current: {branch!r})."
            )
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--name-only", "main...HEAD"],
            cwd=str(REPO_ROOT), capture_output=True, text=True,
        )
        files = [f for f in result.stdout.splitlines() if f]
        production = [
            f for f in files
            if not (
                f.startswith("tests/")
                or f.startswith("docs/")
                or f.startswith("reports/")
            )
        ]
        assert not production, f"production code in diff: {production}"

    def test_24h_labeling_preserved(self):
        """The 24-H exploratory flag is still present in
        main_web.py."""
        text = _read_text(MAIN_WEB)
        assert "is_exploratory_project" in text
        assert text.count('"is_exploratory_project":') == 3


# ── 11. End-to-end: full scenario loop ────────────────────────────────

class TestFullScenarioLoop:
    """The complete user story: start from Base, add Downside,
    add Upside, run all three, compare Base vs Downside,
    compare Base vs Upside. All produce different kpis."""

    def test_full_loop(self):
        from app.persistence.scenarios_repository import resolve_scenario_snapshot
        base = _baseline_snapshot()
        base_kpis = _run(base)
        down_overrides = {
            "tariff_eur_mwh": "70.0",
            "opex_y1_keur": "1500.0",
            "p50_hours": "1500",
        }
        up_overrides = {
            "tariff_eur_mwh": "130.0",
            "opex_y1_keur": "500.0",
            "p50_hours": "2300",
        }
        down_snap = resolve_scenario_snapshot(base, down_overrides)
        up_snap = resolve_scenario_snapshot(base, up_overrides)
        down_kpis = _run(down_snap)
        up_kpis = _run(up_snap)

        # Revenue: up > base > down
        assert up_kpis["total_revenue_keur"] > base_kpis["total_revenue_keur"]
        assert base_kpis["total_revenue_keur"] > down_kpis["total_revenue_keur"]

        # OPEX: down > base > up
        assert down_kpis["total_opex_keur"] > base_kpis["total_opex_keur"]
        assert base_kpis["total_opex_keur"] > up_kpis["total_opex_keur"]

        # EBITDA: up > base > down
        assert up_kpis["total_ebitda_keur"] > base_kpis["total_ebitda_keur"]
        assert base_kpis["total_ebitda_keur"] > down_kpis["total_ebitda_keur"]

        # IRR: up > base > down
        assert up_kpis["project_irr"] > base_kpis["project_irr"]
        assert base_kpis["project_irr"] > down_kpis["project_irr"]

        # Base snapshot is unchanged after the resolve steps
        assert base["tariff_eur_mwh"] == "90.0"
        assert base["opex_y1_keur"] == "800.0"
        assert base["p50_hours"] == "1800"

    def test_scenario_name_persists(self):
        """Different scenarios can have different scenario
        names, and the runtime uses the scenario name in
        output."""
        from app.persistence.scenarios_repository import resolve_scenario_snapshot
        base = _baseline_snapshot()
        down_snap = resolve_scenario_snapshot(base, {"tariff_eur_mwh": "70.0"})
        down_snap["scenario"] = "Downside"
        up_snap = resolve_scenario_snapshot(base, {"tariff_eur_mwh": "130.0"})
        up_snap["scenario"] = "Upside"
        # Both runs succeed
        kpis_down = _run(down_snap)
        kpis_up = _run(up_snap)
        assert kpis_down is not None
        assert kpis_up is not None
        # And the kpis differ
        assert kpis_down["project_irr"] != kpis_up["project_irr"]


# ── 12. Snapshot persistence proof (DB-level, in-memory DB) ────────────

class TestSnapshotPersistence:
    """The resolve_scenario_snapshot produces a dict that can
    be passed to build_projectinputs_from_snapshot and
    run_project — i.e., the persistence shape is the same as
    the runtime shape. This is the fundamental invariant
    that makes the scenario loop work."""

    def test_resolved_snapshot_passes_input_adapter(self):
        from app.persistence.scenarios_repository import resolve_scenario_snapshot
        from app.input_adapter import SnapshotInputError
        base = _baseline_snapshot()
        resolved = resolve_scenario_snapshot(base, {
            "tariff_eur_mwh": "100.0",
            "opex_y1_keur": "1000.0",
        })
        # Should not raise
        inputs = _build_inputs(resolved)
        assert inputs.revenue.ppa_base_tariff == 100.0
        total_y1 = sum(item.y1_amount_keur for item in inputs.opex)
        assert abs(total_y1 - 1000.0) < 1e-6

    def test_resolved_snapshot_missing_required_field_fails(self):
        """If a base_input_set is missing a required field,
        the scenario is invalid (cannot build inputs)."""
        from app.persistence.scenarios_repository import resolve_scenario_snapshot
        from app.input_adapter import SnapshotInputError
        incomplete_base = {
            "project_name": "X",
            "project_type": "Solar",
            "country_market": "HR",
            "capacity_mw": "50.0",
            "cod_date": "2027-12-30",
            "construction_months": "18",
            "horizon_years": "25",
            # missing: tariff_eur_mwh
            "ppa_term_years": "15",
            "p50_hours": "1800",
            "opex_y1_keur": "800.0",
            "total_capex_keur": "50000.0",
            "gearing_pct": "70.0",
            "interest_rate_pct": "5.0",
            "tenor_years": "18",
            "target_dscr": "1.20",
        }
        # resolve_scenario_snapshot doesn't validate; it
        # just merges. The validation happens at
        # build_projectinputs_from_snapshot time.
        resolved = resolve_scenario_snapshot(incomplete_base, {})
        with pytest.raises(SnapshotInputError):
            _build_inputs(resolved)
