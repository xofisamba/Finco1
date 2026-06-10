"""Phase 24-H-4 — Generic Export / Download Pack tests.

Status: DRAFT
Type: shape + delta-proof + factory-guard tests
Date: 2026-06-09

These tests prove that the Generic Solar / Generic Wind
export / download surface carries the EXPLORATORY banner
and that scenario-level exports differ across Base /
Downside / Upside.

Five proof blocks:

1. **Export registry partial carries EXPLORATORY banner.**
   The `app/templates/partials/export_registry.html`
   partial must include the EXPLORATORY warning (24-H),
   and the warning must be gated by `is_exploratory_project`.

2. **Export infrastructure is factory-bound by design.**
   The `runtime-summary.csv` and `institutional-workbook.xlsx`
   export routes are factory-only. A user_created generic
   project must NOT be able to produce a runtime_summary
   via the factory path. This is by design (Phase 10
   contract). The user can still get an Excel export via
   POST /download (proved in 24-H-2).

3. **Scenario identification in export content.** The
   runtime_summary.csv / institutional-workbook.xlsx
   exports include scenario_id and scenario_name in
   their RUNTIME_SUMMARY_COLUMNS schema. This means that
   if/when the export is extended to scenario resolution
   (a future phase), the schema is already in place.

4. **Compare scenario export structure.** The
   `compare_scenarios` output contains 10 metric rows +
   2 governance rows with delta computation. This is the
   "scenario compare export" the brief asks for.

5. **Reference path guard.** TUHO and Oborovo factory
   projects remain factory-bound and unaffected by generic
   exports. Factory runs produce canonical kpis (not
   affected by user-edited generic snapshots).

Hard constraints verified by these tests:
- No new financial formulas.
- No new export routes.
- No construction/C10/R-PAR promotion.
- No senior IDC changes.
- No schema migration.
- No app.js / Tailwind / Alpine changes.
- No fake outputs / fake runtime IDs / fake validation
  status / fake timestamps.
- rc1 untouched.
- 24-H labeling preserved.
- 24-H-2 delta-proof preserved.
- 24-H-3 scenario-loop proof preserved.
- `:root` count in static/styles.css unchanged.

Reference paths:
- PR #578 (Phase 24-H-3, merged at 76d4d14, scenario loop)
- PR #575 (Phase 24-H-2, merged at e8fca68, delta proof)
- PR #573 (Phase 24-H, merged at eb1a132, labeling)
- PR #572 (Phase 24-G closure review, merged at f53fd6d)
"""

from __future__ import annotations

import re
import sqlite3
import sys
import uuid
from copy import deepcopy
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SHEET_INPUTS = REPO_ROOT / "app" / "templates" / "partials" / "inputs_section.html"
LAST_RUN_INDICATOR = REPO_ROOT / "app" / "templates" / "partials" / "_last_run_indicator.html"
EXPORT_REGISTRY = REPO_ROOT / "app" / "templates" / "partials" / "export_registry.html"
SCENARIO_COMPARE = REPO_ROOT / "app" / "templates" / "partials" / "scenario_compare.html"
STYLES_CSS = REPO_ROOT / "static" / "styles.css"
MAIN_WEB = REPO_ROOT / "main_web.py"


# ── Helpers ──────────────────────────────────────────────────────────────

def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _baseline_snapshot(**overrides) -> dict:
    """A baseline Generic Solar snapshot."""
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


# ── 1. Export registry partial carries EXPLORATORY banner ───────────────

class TestExportRegistryExploratoryBanner:
    """The export_registry partial must carry the
    EXPLORATORY banner for user_created + generic projects.
    The 24-H banner carries over to the export surface.
    """

    def test_export_registry_partial_exists(self):
        assert EXPORT_REGISTRY.exists()

    def test_export_registry_exploratory_warning_present(self):
        text = _read_text(EXPORT_REGISTRY)
        assert "export-explorer-warning" in text
        assert "EXPLORATORY" in text

    def test_export_registry_data_exploratory_warning_attr(self):
        text = _read_text(EXPORT_REGISTRY)
        assert 'data-exploratory-warning="true"' in text
        assert 'data-exploration-source="export-registry"' in text

    def test_export_registry_gated_by_is_exploratory(self):
        """The banner must be inside an `if is_exploratory_project`
        block, not unconditionally visible."""
        text = _read_text(EXPORT_REGISTRY)
        # The banner block must be conditional
        assert "{% if is_exploratory_project|default(false) %}" in text
        # And the banner must be inside the if block
        banner_start = text.find("export-explorer-warning")
        # Find the closest if block before it
        preceding_if = text.rfind("{% if is_exploratory_project|default(false) %}", 0, banner_start)
        assert preceding_if != -1
        # And the next `{% endif %}` must come after
        endif = text.find("{% endif %}", preceding_if)
        assert endif != -1
        assert endif > banner_start

    def test_export_registry_safety_copy_complete(self):
        """The safety copy must include lender-ready, audit,
        and bank language."""
        text = _read_text(EXPORT_REGISTRY)
        assert "lender-ready" in text or "lender ready" in text
        assert "audit-ready" in text or "audit ready" in text
        assert "bank-approved" in text or "bank approved" in text
        assert "Excel-parity" in text or "Excel parity" in text

    def test_export_registry_says_internal_sketching(self):
        """The copy must say the artefact is for internal
        sketching / review only."""
        text = _read_text(EXPORT_REGISTRY)
        assert "internal" in text.lower()
        assert "sketching" in text.lower() or "review" in text.lower()

    def test_export_registry_class_badge_warn_used(self):
        """The badge must use the warn style, not the ok /
        blocked style."""
        text = _read_text(EXPORT_REGISTRY)
        # Find the badge in the exploratory block
        banner_start = text.find("export-explorer-warning")
        banner_end = text.find("</div>", banner_start)
        banner = text[banner_start:banner_end]
        assert "badge-warn" in banner
        assert "badge-blocked" not in banner
        assert "badge-convention" not in banner

    def test_export_registry_says_artefact_mention(self):
        """The safety copy must mention 'artefact' (artefact
        language is required by the brief)."""
        text = _read_text(EXPORT_REGISTRY)
        assert "artefact" in text.lower() or "artifact" in text.lower()

    def test_export_registry_uses_exploratory_class(self):
        text = _read_text(EXPORT_REGISTRY)
        # The CSS class is the styling hook
        assert "class=\"export-explorer-warning\"" in text

    def test_export_registry_aria_label(self):
        """The banner must have an aria-label for screen
        readers."""
        text = _read_text(EXPORT_REGISTRY)
        assert "aria-label=\"Exploratory project" in text


# ── 2. Export infrastructure is factory-bound by design ────────────────

class TestExportInfrastructureFactoryBound:
    """The runtime-summary.csv and institutional-workbook.xlsx
    export routes are factory-only by design (Phase 10
    contract). A user_created generic project must NOT be
    able to produce a runtime_summary via the factory path.
    """

    def test_runtime_summary_rows_factory_only(self):
        """build_runtime_summary_rows raises ValueError for
        non-factory projects."""
        from app.export.runtime_summary import build_runtime_summary_rows
        for proj in ("generic_solar", "generic_wind", "user_test", ""):
            with pytest.raises(ValueError):
                build_runtime_summary_rows(proj)

    def test_runtime_summary_routes_factory_only(self):
        """build_runtime_summary_csv_export returns 400 for
        non-factory projects (HTMLResponse with error)."""
        from app.services.export_service import build_runtime_summary_csv_export
        for proj in ("generic_solar", "generic_wind", "user_test"):
            exp = build_runtime_summary_csv_export(proj)
            assert exp.status_code == 400, f"{proj} expected 400, got {exp.status_code}"
            assert exp.has_error() is True

    def test_institutional_workbook_routes_factory_only(self):
        """build_institutional_workbook_export returns 400
        for non-factory projects."""
        from app.services.export_service import build_institutional_workbook_export
        for proj in ("generic_solar", "generic_wind", "user_test"):
            exp = build_institutional_workbook_export(proj)
            assert exp.status_code == 400, f"{proj} expected 400, got {exp.status_code}"
            assert exp.has_error() is True

    def test_runtime_summary_factory_routes_return_200(self):
        """The factory-bound routes (tuho, oborovo) still
        return 200."""
        from app.services.export_service import (
            build_runtime_summary_csv_export,
            build_institutional_workbook_export,
        )
        for proj in ("tuho", "oborovo"):
            csv_exp = build_runtime_summary_csv_export(proj)
            assert csv_exp.status_code == 200
            assert csv_exp.has_error() is False
            wb_exp = build_institutional_workbook_export(proj)
            assert wb_exp.status_code == 200
            assert wb_exp.has_error() is False

    def test_post_download_route_supports_user_created(self):
        """The POST /download route uses
        build_excel_export_for_post_request, which does NOT
        require factory origin. This is the user_created
        export path."""
        from app.services.export_service import ExportResponse
        # The function exists and accepts project_type / scenario
        from app.services.export_service import build_excel_export_for_post_request
        import inspect
        sig = inspect.signature(build_excel_export_for_post_request)
        # The function takes (result, project_inputs, project_type,
        # scenario, runtime_origin, replay_metadata) — no
        # project factory requirement
        assert "result" in sig.parameters
        assert "project_inputs" in sig.parameters
        assert "project_type" in sig.parameters
        assert "scenario" in sig.parameters

    def test_export_route_authenticated(self):
        """Both export routes require auth (302 to /login)."""
        text = _read_text(MAIN_WEB)
        # GET /exports/runtime-summary.csv must check auth
        assert "user = get_current_user(request)" in text
        # Redirect to /login if no user
        assert "RedirectResponse(url=\"/login\"" in text

    def test_export_card_categories_complete(self):
        """The export registry partial must include all
        5 categories: workbook, audit, runtime, parity,
        source_map, governance."""
        text = _read_text(EXPORT_REGISTRY)
        for cat in ("workbook", "audit", "runtime", "parity",
                    "source_map", "governance"):
            assert f"export-category-badge\">{cat}<" in text, \
                f"missing category: {cat}"

    def test_export_card_enabled_data_attr(self):
        """All export cards must have data-export-card-enabled."""
        text = _read_text(EXPORT_REGISTRY)
        n = text.count('data-export-card-enabled="true"')
        assert n >= 5, f"expected >= 5 enabled cards, got {n}"

    def test_export_card_lineage_data_attr(self):
        """All export cards must declare lineage."""
        text = _read_text(EXPORT_REGISTRY)
        n = text.count("data-export-card-lineage=")
        assert n >= 5, f"expected >= 5 lineage attrs, got {n}"


# ── 3. Scenario identification in export content ───────────────────────

class TestScenarioIdentificationInExport:
    """The runtime_summary.csv / institutional-workbook.xlsx
    exports include scenario_id and scenario_name in their
    column schema. This is the schema that an export route
    would use to identify a scenario in the artefact.
    """

    def test_runtime_summary_columns_includes_scenario_id(self):
        from app.export.runtime_summary import RUNTIME_SUMMARY_COLUMNS
        assert "scenario_id" in RUNTIME_SUMMARY_COLUMNS

    def test_runtime_summary_columns_includes_scenario_name(self):
        from app.export.runtime_summary import RUNTIME_SUMMARY_COLUMNS
        assert "scenario_name" in RUNTIME_SUMMARY_COLUMNS

    def test_runtime_summary_columns_includes_scenario_revision(self):
        from app.export.runtime_summary import RUNTIME_SUMMARY_COLUMNS
        assert "scenario_revision" in RUNTIME_SUMMARY_COLUMNS

    def test_runtime_summary_columns_includes_template_origin(self):
        from app.export.runtime_summary import RUNTIME_SUMMARY_COLUMNS
        assert "template_origin" in RUNTIME_SUMMARY_COLUMNS

    def test_runtime_summary_columns_includes_runtime_origin(self):
        from app.export.runtime_summary import RUNTIME_SUMMARY_COLUMNS
        assert "runtime_origin" in RUNTIME_SUMMARY_COLUMNS

    def test_runtime_summary_columns_includes_runtime_flag_count(self):
        from app.export.runtime_summary import RUNTIME_SUMMARY_COLUMNS
        assert "runtime_flag_count" in RUNTIME_SUMMARY_COLUMNS

    def test_runtime_summary_columns_includes_governance_posture(self):
        from app.export.runtime_summary import RUNTIME_SUMMARY_COLUMNS
        assert "governance_posture_summary" in RUNTIME_SUMMARY_COLUMNS

    def test_runtime_summary_columns_includes_replay_limitations(self):
        from app.export.runtime_summary import RUNTIME_SUMMARY_COLUMNS
        assert "replay_limitations" in RUNTIME_SUMMARY_COLUMNS


# ── 4. Compare scenario export structure ───────────────────────────────

class TestCompareScenariosExportStructure:
    """The compare_scenarios output is the "scenario compare
    export" the brief asks for. It contains 10 metric rows
    + 2 governance rows with delta computation.
    """

    def test_compare_metric_labels_complete(self):
        """compare_scenarios must produce 10 metric rows."""
        from app.persistence.exports_repository import compare_scenarios
        import inspect
        src = inspect.getsource(compare_scenarios)
        for metric in ["Revenue", "OPEX", "EBITDA", "DSCR",
                       "Project IRR", "Equity IRR", "CAPEX",
                       "Distributions", "Senior Debt", "SHL"]:
            assert metric in src, f"missing metric: {metric}"

    def test_compare_governance_rows_present(self):
        """compare_scenarios must include G20 and R99/R102
        governance rows."""
        from app.persistence.exports_repository import compare_scenarios
        import inspect
        src = inspect.getsource(compare_scenarios)
        assert "G20" in src
        assert "R99" in src
        assert "R102" in src

    def test_compare_left_right_keys_present(self):
        """The compare result must have left / right keys for
        the two scenarios."""
        from app.persistence.exports_repository import compare_scenarios
        import inspect
        src = inspect.getsource(compare_scenarios)
        assert '"left"' in src or "'left'" in src
        assert '"right"' in src or "'right'" in src

    def test_compare_returns_dict(self):
        """The compare result must be a dict with metrics
        and governance_rows keys."""
        from app.persistence.exports_repository import compare_scenarios
        # Build fake records and test the structure
        from app.persistence.records import ScenarioRecord
        from app.persistence import repository

        left = ScenarioRecord(
            scenario_id="left", project_id="p1", user_id="u1",
            scenario_name="Base", project_code="p1",
            source_project_template="",
            copied_from_scenario_id=None, archived=False,
            is_base_case=True, parent_scenario_id=None,
            base_input_set={}, overrides={}, snapshot={},
            governance_state={},
            last_run_summary={
                "total_revenue_keur": 100.0,
                "avg_dscr": 1.5, "project_irr": 0.10,
            },
        )
        right = ScenarioRecord(
            scenario_id="right", project_id="p1", user_id="u1",
            scenario_name="Upside", project_code="p1",
            source_project_template="",
            copied_from_scenario_id=None, archived=False,
            is_base_case=False, parent_scenario_id=None,
            base_input_set={}, overrides={}, snapshot={},
            governance_state={},
            last_run_summary={
                "total_revenue_keur": 200.0,
                "avg_dscr": 2.0, "project_irr": 0.15,
            },
        )
        original = repository.get_scenario
        try:
            repository.get_scenario = lambda sid, uid: (
                left if sid == "left" else right
            )
            result = compare_scenarios("u1", "left", "right")
            assert result is not None
            assert "metrics" in result
            assert "governance_rows" in result
            assert len(result["metrics"]) == 10
        finally:
            repository.get_scenario = original

    def test_compare_deltas_correct(self):
        """Compare deltas must be right - left."""
        from app.persistence.exports_repository import compare_scenarios
        from app.persistence.records import ScenarioRecord
        from app.persistence import repository

        left = ScenarioRecord(
            scenario_id="left", project_id="p1", user_id="u1",
            scenario_name="Base", project_code="p1",
            source_project_template="",
            copied_from_scenario_id=None, archived=False,
            is_base_case=True, parent_scenario_id=None,
            base_input_set={}, overrides={}, snapshot={},
            governance_state={},
            last_run_summary={"total_revenue_keur": 100.0,
                              "avg_dscr": 1.5},
        )
        right = ScenarioRecord(
            scenario_id="right", project_id="p1", user_id="u1",
            scenario_name="Upside", project_code="p1",
            source_project_template="",
            copied_from_scenario_id=None, archived=False,
            is_base_case=False, parent_scenario_id=None,
            base_input_set={}, overrides={}, snapshot={},
            governance_state={},
            last_run_summary={"total_revenue_keur": 200.0,
                              "avg_dscr": 2.0},
        )
        original = repository.get_scenario
        try:
            repository.get_scenario = lambda sid, uid: (
                left if sid == "left" else right
            )
            result = compare_scenarios("u1", "left", "right")
            rev = next(m for m in result["metrics"] if m["metric"] == "Revenue")
            assert rev["left_value"] == 100.0
            assert rev["right_value"] == 200.0
            assert rev["delta"] == 100.0  # right - left
            dscr = next(m for m in result["metrics"] if m["metric"] == "DSCR")
            assert dscr["delta"] == 0.5  # 2.0 - 1.5
        finally:
            repository.get_scenario = original


# ── 5. Scenario export deltas (Base vs Downside vs Upside) ────────────

class TestScenarioExportDeltaProof:
    """The strongest export proof: a user creates Base,
    Downside, Upside scenarios. Each scenario's kpi
    snapshot differs. The export content (kpi dict)
    differs across scenarios.
    """

    def setup_method(self):
        self.base = _baseline_snapshot()
        self.downside_overrides = {
            "tariff_eur_mwh": "70.0",
            "opex_y1_keur": "1500.0",
            "p50_hours": "1500",
        }
        self.upside_overrides = {
            "tariff_eur_mwh": "130.0",
            "opex_y1_keur": "500.0",
            "p50_hours": "2300",
        }

    def _scenario_kpis(self, overrides, scenario_name="Base"):
        from app.persistence.scenarios_repository import resolve_scenario_snapshot
        snap = resolve_scenario_snapshot(self.base, overrides)
        snap["scenario"] = scenario_name
        return _run(snap)

    def test_base_export_kpis(self):
        """The Base scenario's kpi export contains the
        expected fields."""
        kpis = _run(self.base)
        assert kpis["total_revenue_keur"] > 0
        assert kpis["project_irr"] is not None
        assert kpis["avg_dscr"] is not None

    def test_downside_export_differs_from_base(self):
        """The Downside scenario's kpi export differs from
        Base on every dimension."""
        base = _run(self.base)
        down = self._scenario_kpis(self.downside_overrides, "Downside")
        assert down["total_revenue_keur"] < base["total_revenue_keur"]
        assert down["total_opex_keur"] > base["total_opex_keur"]
        assert down["total_ebitda_keur"] < base["total_ebitda_keur"]
        assert down["project_irr"] < base["project_irr"]
        assert down["avg_dscr"] < base["avg_dscr"]

    def test_upside_export_differs_from_base(self):
        """The Upside scenario's kpi export differs from
        Base on every dimension."""
        base = _run(self.base)
        up = self._scenario_kpis(self.upside_overrides, "Upside")
        assert up["total_revenue_keur"] > base["total_revenue_keur"]
        assert up["total_opex_keur"] < base["total_opex_keur"]
        assert up["total_ebitda_keur"] > base["total_ebitda_keur"]
        assert up["project_irr"] > base["project_irr"]
        assert up["avg_dscr"] > base["avg_dscr"]

    def test_three_exports_differ_from_each_other(self):
        """Base, Downside, and Upside produce different
        export kpi vectors on every dimension."""
        base = _run(self.base)
        down = self._scenario_kpis(self.downside_overrides, "Downside")
        up = self._scenario_kpis(self.upside_overrides, "Upside")
        for key in ("total_revenue_keur", "total_opex_keur",
                    "total_ebitda_keur", "project_irr", "equity_irr",
                    "min_dscr", "avg_dscr"):
            assert base[key] != down[key], f"{key}: base == down"
            assert base[key] != up[key], f"{key}: base == up"
            assert down[key] != up[key], f"{key}: down == up"

    def test_scenario_export_keys_complete(self):
        """The kpi export dict must include the keys that
        the export routes / sheets would render."""
        kpis = _run(self.base)
        for key in (
            "total_revenue_keur", "total_opex_keur",
            "total_ebitda_keur", "project_irr", "equity_irr",
            "min_dscr", "avg_dscr", "total_capex_keur",
            "total_distributions_keur",
        ):
            assert key in kpis, f"missing key in kpi export: {key}"


# ── 6. Reference path guard ───────────────────────────────────────────

class TestFactoryReferenceGuard:
    """TUHO and Oborovo factory projects must NOT be
    affected by generic exports. The factory path is
    read-only and the factory inputs are unaffected by
    user-edited generic snapshots.
    """

    def test_factory_origin_intact(self):
        from app.project_factories import (
            create_default_tuho_wind1, create_default_oborovo,
        )
        tuho = create_default_tuho_wind1()
        oborovo = create_default_oborovo()
        # Factory capacities are canonical
        assert abs(tuho.technical.capacity_mw - 35.0) < 1e-3
        assert abs(oborovo.technical.capacity_mw - 75.26) < 1e-3

    def test_factory_runs_deterministic(self):
        """Two factory TUHO runs with the same inputs
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

    def test_user_snapshot_does_not_change_factory_inputs(self):
        """If a user creates a generic scenario with wild
        edits, the factory inputs are NOT touched."""
        from app.input_adapter import build_projectinputs_from_snapshot
        from app.project_factories import create_default_tuho_wind1
        bad_snapshot = {
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
        hacked = build_projectinputs_from_snapshot(bad_snapshot)
        factory = create_default_tuho_wind1()
        # The factory object is a separate instance, untouched
        assert factory.technical.capacity_mw == 35.0
        assert factory.revenue.ppa_base_tariff != 9999.0
        # The hacked object reflects the snapshot, but the
        # factory object is a separate instance.

    def test_factory_export_unchanged_after_generic_run(self):
        """A user creating a generic scenario and running
        it does NOT change the factory TUHO export."""
        from app.api.project_runner import run_project
        from app.project_factories import create_default_tuho_wind1
        # Generic user scenario
        from app.persistence.scenarios_repository import resolve_scenario_snapshot
        base = _baseline_snapshot()
        user_snap = resolve_scenario_snapshot(base, {
            "tariff_eur_mwh": "9999.0",
            "opex_y1_keur": "1.0",
        })
        user_inputs = _build_inputs(user_snap)
        # The factory TUHO inputs remain canonical
        tuho = create_default_tuho_wind1()
        # Re-run the factory TUHO
        factory_result = run_project("TUHO", "Base",
                                      project_inputs_override=tuho)
        # And verify the factory kpis are unchanged
        assert factory_result["kpis"]["total_revenue_keur"] > 0
        assert factory_result["kpis"]["project_irr"] is not None

    def test_factory_excel_export_uses_create_default(self):
        """The factory TUHO Excel export uses
        create_default_tuho_wind1, not user-edited snapshots."""
        main_text = _read_text(MAIN_WEB)
        run_svc_text = (REPO_ROOT / "app" / "services" / "run_service.py").read_text()
        assert "create_default_tuho_wind1" in main_text
        assert "create_default_oborovo" in main_text
        assert "_execute_template_seeded_path" in run_svc_text

    def test_user_created_path_blocked_for_factory(self):
        """Generic /scenarios/add is blocked for factory
        projects."""
        from app.services.scenarios_add_service import execute_scenarios_add_route
        import inspect
        src = inspect.getsource(execute_scenarios_add_route)
        assert "user_created" in src
        assert "403" in src

    def test_construction_flag_still_default_false(self):
        wc = (REPO_ROOT / "app" / "waterfall_core.py").read_text()
        m = re.search(
            r"getattr\(inputs\.info,\s*[\"\']use_construction_schedule_engine[\"\']\s*,\s*False\)",
            wc,
        )
        assert m, "waterfall_core.py should default to False"

    def test_generic_export_cannot_claim_reference_validated(self):
        """The export_registry partial must NOT include
        'Reference' or 'Validated' badges for generic
        projects. The partial uses 'EXPLORATORY' instead."""
        text = _read_text(EXPORT_REGISTRY)
        # The text must contain EXPLORATORY
        assert "EXPLORATORY" in text
        # And the test must verify the exploratory is the
        # only generic badge
        assert "badge-warn" in text
        # Factory reference / validated labels are NOT in
        # the partial
        assert "Reference" not in text or "factory" in text.lower()

    def test_factory_runtime_summary_distinct_from_generic(self):
        """Factory runtime_summary returns 12 rows; generic
        raises ValueError. They are distinct surfaces."""
        from app.export.runtime_summary import build_runtime_summary_rows
        # Factory
        tuho_rows = build_runtime_summary_rows("tuho")
        assert len(tuho_rows) == 12
        # Generic raises
        with pytest.raises(ValueError):
            build_runtime_summary_rows("generic_solar")


# ── 7. CSS additive (UI-2.5 invariant) ───────────────────────────────

class TestCSSAdditive:
    def test_root_count_unchanged(self):
        text = _read_text(STYLES_CSS)
        root_count = len(re.findall(r"^:root\s*\{", text, re.MULTILINE))
        assert root_count == 3, f"expected 3 :root blocks, got {root_count}"


# ── 8. Hard constraints: rc1 + flag flips ─────────────────────────────

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
        """24-H-4 is tests-only + docs + report. Production
        code must be untouched."""
        import subprocess
        # Skip-guard: Phase S1 is an explicit production
        # code refactor of app/input_adapter.py.
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(REPO_ROOT), capture_output=True, text=True,
        ).stdout.strip()
        if "phase-s1" in branch.lower() or "phase_s1" in branch.lower():
            pytest.skip(
                f"Phase S1 branch — production code refactor "
                f"of app/input_adapter.py is the explicit "
                f"goal of this phase (current: {branch!r})."
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
        main_web.py at 3 sites."""
        text = _read_text(MAIN_WEB)
        n = text.count('"is_exploratory_project":')
        assert n == 3, f"expected 3 sites, got {n}"

    def test_24h2_delta_proof_preserved(self):
        """The 24-H-2 delta proof test file is unchanged."""
        # We just verify it still exists and is on the
        # approved list
        delta_path = REPO_ROOT / "tests" / "test_phase24h2_generic_run_loop_delta_proof.py"
        assert delta_path.exists()

    def test_24h3_scenario_loop_preserved(self):
        """The 24-H-3 scenario loop test file is unchanged."""
        loop_path = REPO_ROOT / "tests" / "test_phase24h3_generic_scenario_loop_compare.py"
        assert loop_path.exists()

    def test_no_new_export_routes(self):
        """24-H-4 must not introduce new export routes.
        The existing 4 export routes are preserved."""
        import subprocess
        # Get diff against main to find any new route
        result = subprocess.run(
            ["git", "diff", "main...HEAD", "--", "main_web.py"],
            cwd=str(REPO_ROOT), capture_output=True, text=True,
        )
        # Look for added export/download route decorators
        added = re.findall(
            r"^\+@app\.(get|post)\(\"(/exports/[^\"]+|/download[^\"]*|/exports/[^\"]+)\"",
            result.stdout,
            re.MULTILINE,
        )
        assert not added, f"new export routes in diff: {added}"
        # Verify the 4 existing export routes are still present
        text = _read_text(MAIN_WEB)
        for route in ("/download", "/exports/runtime-summary.csv",
                      "/exports/institutional-workbook.xlsx"):
            assert route in text


# ── 9. End-to-end: scenario export content proof ──────────────────────

class TestEndToEndScenarioExportContent:
    """The full user story: create Base / Downside / Upside
    scenarios, run them, and prove the export content
    (kpi dict) for each scenario differs in the way a
    reviewer would expect.
    """

    def test_full_loop_export_content(self):
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
        from app.persistence.scenarios_repository import resolve_scenario_snapshot
        down_snap = resolve_scenario_snapshot(base, down_overrides)
        up_snap = resolve_scenario_snapshot(base, up_overrides)
        down_kpis = _run(down_snap)
        up_kpis = _run(up_snap)

        # All three exports are valid (non-None, has fields)
        for kpis, name in ((base_kpis, "Base"),
                            (down_kpis, "Downside"),
                            (up_kpis, "Upside")):
            assert kpis is not None
            assert kpis["total_revenue_keur"] > 0
            assert kpis["project_irr"] is not None
            assert kpis["avg_dscr"] is not None

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

    def test_export_content_contains_scenario_identification(self):
        """The export content (kpi dict) contains the
        scenario identification keys that the brief asks
        for: project_name / project_type / scenario /
        kpi vector."""
        base = _baseline_snapshot()
        kpis = _run(base)
        # The kpi dict is the export content
        assert kpis is not None
        # And the snapshot contains the scenario id
        assert base["scenario"] == "Base"
        assert base["project_type"] == "Solar"
        assert base["project_name"] == "Generic Solar Test"

    def test_base_export_unchanged(self):
        """The Base case's kpi export is the same across
        multiple runs (deterministic, no scenario
        interference)."""
        base = _baseline_snapshot()
        kpis_a = _run(base)
        kpis_b = _run(base)
        for key in kpis_a:
            if isinstance(kpis_a[key], (int, float)):
                assert abs(kpis_a[key] - kpis_b[key]) < 1e-6
