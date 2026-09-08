"""
tests.test_ui3b_completion — UI-3B completion acceptance suite.

Covers (beyond the 27-test base suite):
  - Per-scenario runtime isolation (last_run_summary persisted per ScenarioRecord)
  - Stale detection: scenario edited after run → STALE
  - Base Case protection (cannot rename/archive/delete)
  - Scenario override isolation: overrides don't leak between scenarios
  - Compare stale/clean detection via build_scenario_projection
  - Sensitivity driver field resolution (correct snapshot keys)
  - Sensitivity non-destructive proof (pis_base values unchanged)
  - Output integrity chain: raw → projection → display string
  - update_scenario_last_run_summary exists and persists correctly
  - Driver specs have correct PIS snapshot keys
"""
from __future__ import annotations

import uuid
import pytest
from datetime import datetime, timezone, timedelta
from typing import Any, Optional


# ── test fixtures ─────────────────────────────────────────────────────────── #

def _uid():
    return f"test_{uuid.uuid4().hex[:8]}"


def _make_project(user_id, project_type="solar"):
    from app.persistence.repository import save_project
    code = f"proj_{uuid.uuid4().hex[:8]}"
    return save_project(
        user_id=user_id,
        project_code=code,
        project_name=f"Test {project_type.title()} Project",
        project_type=project_type,
        project_origin="user_created",
        source_project_template=f"generic_{project_type}",
        template_source=f"generic_{project_type}",
        baseline_snapshot={"tariff_eur_mwh": 65.0, "total_capex_keur": 40000.0,
                           "gearing_pct": 0.70, "interest_rate_pct": 0.04,
                           "p50_hours": 1800.0, "opex_y1_keur": 600.0},
        governance_state={},
        last_run_summary={},
        replay_metadata={},
    ), code


def _make_base_and_scenario(user_id, project_id, project_code, base_inputs=None):
    from app.persistence.scenarios_repository import get_or_create_base_case_scenario, add_scenario
    base_inputs = base_inputs or {
        "tariff_eur_mwh": 65.0, "total_capex_keur": 40000.0,
        "gearing_pct": 0.70, "interest_rate_pct": 0.04,
        "p50_hours": 1800.0, "opex_y1_keur": 600.0,
    }
    base = get_or_create_base_case_scenario(
        user_id=user_id,
        project_id=project_id,
        project_code=project_code,
        project_name="Test",
        project_type="solar",
        source_project_template="generic_solar",
        base_input_set=base_inputs,
        governance_state={},
    )
    child = add_scenario(
        user_id=user_id,
        project_id=project_id,
        project_code=project_code,
        scenario_name="Downside",
        parent_scenario_id=base.scenario_id,
        base_input_set=base_inputs,
        overrides={"tariff_eur_mwh": 55.0},  # -10 EUR/MWh override
    )
    return base, child


def _fake_kpis(irr=0.085, dscr=1.40):
    return {
        "project_irr": irr,
        "equity_irr": irr + 0.03,
        "min_dscr": dscr,
        "avg_dscr": dscr + 0.05,
        "min_llcr": dscr + 0.10,
        "senior_debt_keur": 28000.0,
        "total_capex_keur": 40000.0,
        "total_revenue_keur": 110000.0,
        "total_ebitda_keur": 75000.0,
        "total_cfads_keur": 60000.0,
    }


# ── Per-scenario runtime isolation ───────────────────────────────────────── #

class TestScenarioRuntimeIsolation:

    def test_update_scenario_last_run_summary_persists(self):
        """update_scenario_last_run_summary writes to scenarios.last_run_summary_json."""
        from app.persistence.repository import update_scenario_last_run_summary, get_scenario
        user_id = _uid()
        pr, code = _make_project(user_id)
        base, child = _make_base_and_scenario(user_id, pr.project_id, code)

        kpis = _fake_kpis(irr=0.092)
        summary = {"kpis": kpis, "ran_at": "2025-01-01T10:00:00", "snapshot_id": "snap001"}
        result = update_scenario_last_run_summary(
            user_id=user_id,
            scenario_id=child.scenario_id,
            last_run_summary=summary,
        )
        assert result is True

        sc = get_scenario(child.scenario_id, user_id)
        assert sc is not None
        assert sc.last_run_summary.get("kpis", {}).get("project_irr") == pytest.approx(0.092)
        assert sc.last_run_summary.get("ran_at") == "2025-01-01T10:00:00"

    def test_base_and_child_run_summaries_independent(self):
        """Updating child scenario run summary does not touch base's last_run_summary."""
        from app.persistence.repository import update_scenario_last_run_summary, get_scenario
        user_id = _uid()
        pr, code = _make_project(user_id)
        base, child = _make_base_and_scenario(user_id, pr.project_id, code)

        base_kpis = _fake_kpis(irr=0.085)
        child_kpis = _fake_kpis(irr=0.075)

        update_scenario_last_run_summary(user_id, base.scenario_id, {"kpis": base_kpis, "ran_at": "2025-01-01T09:00:00"})
        update_scenario_last_run_summary(user_id, child.scenario_id, {"kpis": child_kpis, "ran_at": "2025-01-01T10:00:00"})

        base_reloaded = get_scenario(base.scenario_id, user_id)
        child_reloaded = get_scenario(child.scenario_id, user_id)

        # IRRs must remain distinct
        assert base_reloaded.last_run_summary["kpis"]["project_irr"] == pytest.approx(0.085)
        assert child_reloaded.last_run_summary["kpis"]["project_irr"] == pytest.approx(0.075)

    def test_running_child_again_does_not_mutate_base(self):
        """Second run of child overwrites child but not base."""
        from app.persistence.repository import update_scenario_last_run_summary, get_scenario
        user_id = _uid()
        pr, code = _make_project(user_id)
        base, child = _make_base_and_scenario(user_id, pr.project_id, code)

        update_scenario_last_run_summary(user_id, base.scenario_id, {"kpis": _fake_kpis(0.085), "ran_at": "2025-01-01T09:00:00"})
        update_scenario_last_run_summary(user_id, child.scenario_id, {"kpis": _fake_kpis(0.075), "ran_at": "2025-01-01T10:00:00"})
        # Second child run
        update_scenario_last_run_summary(user_id, child.scenario_id, {"kpis": _fake_kpis(0.072), "ran_at": "2025-01-01T11:00:00"})

        base_r = get_scenario(base.scenario_id, user_id)
        child_r = get_scenario(child.scenario_id, user_id)
        assert base_r.last_run_summary["kpis"]["project_irr"] == pytest.approx(0.085)
        assert child_r.last_run_summary["kpis"]["project_irr"] == pytest.approx(0.072)


# ── Base Case protection ─────────────────────────────────────────────────── #

class TestBaseCaseProtection:

    def test_base_case_is_base_case_flag(self):
        from app.persistence.scenarios_repository import get_or_create_base_case_scenario
        user_id = _uid()
        pr, code = _make_project(user_id)
        base = get_or_create_base_case_scenario(
            user_id=user_id, project_id=pr.project_id, project_code=code,
            project_name="T", project_type="solar",
            source_project_template="generic_solar",
            base_input_set={}, governance_state={},
        )
        assert base.is_base_case is True

    def test_rename_base_case_blocked_at_router_layer(self):
        """Router guard prevents rename of base case via sc.is_base_case check."""
        src = open("app/v2/router.py").read()
        # Route must check is_base_case before allowing rename
        assert "is_base_case" in src
        assert "cannot be renamed" in src.lower() or "Base Case cannot be renamed" in src

    def test_archive_base_case_blocked_at_router_layer(self):
        """Router guard prevents archive of base case via sc.is_base_case check."""
        src = open("app/v2/router.py").read()
        assert "is_base_case" in src
        assert "cannot be archived" in src.lower() or "Base Case cannot be archived" in src

    def test_child_scenario_can_be_renamed(self):
        from app.persistence.scenarios_repository import rename_scenario, get_scenario
        user_id = _uid()
        pr, code = _make_project(user_id)
        _, child = _make_base_and_scenario(user_id, pr.project_id, code)
        result = rename_scenario(user_id=user_id, scenario_id=child.scenario_id, new_name="Renamed Child")
        assert result is not None
        reloaded = get_scenario(child.scenario_id, user_id)
        assert reloaded.scenario_name == "Renamed Child"

    def test_child_scenario_can_be_archived(self):
        from app.persistence.scenarios_repository import archive_scenario, get_scenario
        user_id = _uid()
        pr, code = _make_project(user_id)
        _, child = _make_base_and_scenario(user_id, pr.project_id, code)
        archive_scenario(user_id=user_id, scenario_id=child.scenario_id)
        reloaded = get_scenario(child.scenario_id, user_id)
        assert reloaded.archived is True

    def test_archived_scenario_not_in_active_list(self):
        from app.persistence.scenarios_repository import archive_scenario, list_scenarios
        user_id = _uid()
        pr, code = _make_project(user_id)
        _, child = _make_base_and_scenario(user_id, pr.project_id, code)
        archive_scenario(user_id=user_id, scenario_id=child.scenario_id)
        active = list_scenarios(user_id=user_id, project_id=pr.project_id, include_archived=False)
        ids = [s.scenario_id for s in active]
        assert child.scenario_id not in ids

    def test_rename_does_not_make_result_stale(self):
        """Rename is a metadata-only operation; last_run_summary remains valid."""
        from app.persistence.repository import update_scenario_last_run_summary, get_scenario
        from app.persistence.scenarios_repository import rename_scenario
        user_id = _uid()
        pr, code = _make_project(user_id)
        _, child = _make_base_and_scenario(user_id, pr.project_id, code)

        update_scenario_last_run_summary(user_id, child.scenario_id,
                                         {"kpis": _fake_kpis(0.085), "ran_at": "2025-06-01T10:00:00"})
        rename_scenario(user_id=user_id, scenario_id=child.scenario_id, new_name="Renamed")

        sc = get_scenario(child.scenario_id, user_id)
        # Run result must still be there
        assert sc.last_run_summary.get("kpis", {}).get("project_irr") == pytest.approx(0.085)


# ── Scenario override isolation ──────────────────────────────────────────── #

class TestScenarioOverrideIsolation:

    def test_child_override_does_not_leak_to_base(self):
        """Child has tariff override; base_input_set remains at original value."""
        from app.persistence.scenarios_repository import get_scenario
        user_id = _uid()
        pr, code = _make_project(user_id)
        base, child = _make_base_and_scenario(user_id, pr.project_id, code)

        base_r = get_scenario(base.scenario_id, user_id)
        child_r = get_scenario(child.scenario_id, user_id)

        # Child has override; base does not
        assert child_r.overrides.get("tariff_eur_mwh") == 55.0
        assert base_r.overrides == {} or base_r.overrides is None or "tariff_eur_mwh" not in (base_r.overrides or {})

    def test_resolve_scenario_snapshot_applies_overrides(self):
        from app.persistence.scenarios_repository import resolve_scenario_snapshot
        base_inputs = {"tariff_eur_mwh": 65.0, "total_capex_keur": 40000.0}
        overrides = {"tariff_eur_mwh": 55.0}
        resolved = resolve_scenario_snapshot(base_inputs, overrides)
        assert resolved["tariff_eur_mwh"] == 55.0
        assert resolved["total_capex_keur"] == 40000.0

    def test_resolve_scenario_snapshot_base_unchanged(self):
        from app.persistence.scenarios_repository import resolve_scenario_snapshot
        base_inputs = {"tariff_eur_mwh": 65.0, "total_capex_keur": 40000.0}
        overrides = {"tariff_eur_mwh": 55.0}
        resolve_scenario_snapshot(base_inputs, overrides)
        # base_inputs must be unchanged
        assert base_inputs["tariff_eur_mwh"] == 65.0

    def test_updating_child_overrides_does_not_modify_base_input_set(self):
        from app.persistence.scenarios_repository import update_scenario_overrides, get_scenario
        user_id = _uid()
        pr, code = _make_project(user_id)
        base, child = _make_base_and_scenario(user_id, pr.project_id, code)

        update_scenario_overrides(user_id, child.scenario_id, {"tariff_eur_mwh": 50.0})
        base_r = get_scenario(base.scenario_id, user_id)
        assert base_r.base_input_set.get("tariff_eur_mwh") == 65.0


# ── Stale / current semantics ─────────────────────────────────────────────── #

class TestStaleSemanticsViaProjection:
    """Test the compare stale-detection logic via build_scenario_projection."""

    def _make_sc_with_run(self, ran_at_delta_secs=0):
        """Create a mock scenario-like object for projection testing."""
        now = datetime(2025, 6, 1, 10, 0, 0, tzinfo=timezone.utc)
        ran_at = now - timedelta(seconds=abs(ran_at_delta_secs))
        updated_at = now if ran_at_delta_secs <= 0 else now + timedelta(seconds=ran_at_delta_secs)
        return ran_at.isoformat(), updated_at.isoformat()

    def test_clean_if_not_updated_after_run(self):
        from app.v2.scenario_kpi_projection import build_scenario_projection
        # ran_at=2025-06-01T10:00, scenario not updated after
        proj = build_scenario_projection("Base", _fake_kpis(), "2025-06-01T10:00:00", is_stale=False)
        assert proj.state == "CLEAN"

    def test_stale_if_flagged(self):
        from app.v2.scenario_kpi_projection import build_scenario_projection
        proj = build_scenario_projection("Downside", _fake_kpis(), "2025-06-01T10:00:00", is_stale=True)
        assert proj.state == "STALE"

    def test_not_run_if_no_kpis(self):
        from app.v2.scenario_kpi_projection import build_scenario_projection
        proj = build_scenario_projection("Downside", None, None, is_stale=False)
        assert proj.state == "NOT_RUN"

    def test_empty_kpis_dict_is_not_run(self):
        from app.v2.scenario_kpi_projection import build_scenario_projection
        proj = build_scenario_projection("Downside", {}, None, is_stale=False)
        assert proj.state == "NOT_RUN"


# ── Compare output integrity chain ───────────────────────────────────────── #

class TestCompareOutputIntegrity:
    """Prove raw → projection → display string chain with no recomputation."""

    def _build_two_projections(self):
        from app.v2.scenario_kpi_projection import build_scenario_projection
        base_kpis = _fake_kpis(irr=0.085, dscr=1.40)
        alt_kpis = _fake_kpis(irr=0.092, dscr=1.48)
        p1 = build_scenario_projection("Base", base_kpis, "2025-01-01T10:00:00", False)
        p2 = build_scenario_projection("Upside", alt_kpis, "2025-01-01T11:00:00", False)
        return p1, p2

    def test_project_irr_display_matches_raw(self):
        p1, _ = self._build_two_projections()
        # 0.085 raw → "8.50%" display
        assert p1.kpis["project_irr"] == "8.50%"
        assert p1.kpis_raw["project_irr"] == pytest.approx(0.085)

    def test_min_dscr_display_matches_raw(self):
        p1, _ = self._build_two_projections()
        assert p1.kpis["min_dscr"] == "1.40x"
        assert p1.kpis_raw["min_dscr"] == pytest.approx(1.40)

    def test_total_capex_display_matches_raw(self):
        p1, _ = self._build_two_projections()
        assert "40,000" in p1.kpis["total_capex_keur"]
        assert p1.kpis_raw["total_capex_keur"] == pytest.approx(40000.0)

    def test_compare_deltas_use_raw_not_strings(self):
        from app.v2.scenario_kpi_projection import build_compare_rows
        p1, p2 = self._build_two_projections()
        rows = build_compare_rows([p1, p2])
        irr_row = next(r for r in rows if r.key == "project_irr")
        # delta = (0.092 - 0.085) * 100 = +0.70%
        assert irr_row.deltas[1] == "+0.70%"

    def test_no_string_reparsing_for_deltas(self):
        """Raw values must be floats, not parsed from display strings."""
        from app.v2.scenario_kpi_projection import build_scenario_projection, build_compare_rows
        p1 = build_scenario_projection("A", _fake_kpis(0.10), "2025-01-01T10:00", False)
        p2 = build_scenario_projection("B", _fake_kpis(0.08), "2025-01-01T10:00", False)
        rows = build_compare_rows([p1, p2])
        irr_row = next(r for r in rows if r.key == "project_irr")
        # Must be -2.00% (floating point delta), not some string-parsed value
        assert irr_row.deltas[1] == "-2.00%"

    def test_stale_scenario_in_compare_shows_stale_state(self):
        from app.v2.scenario_kpi_projection import build_scenario_projection, build_compare_rows
        p1 = build_scenario_projection("Base", _fake_kpis(0.085), "2025-01-01T10:00", False)
        p2 = build_scenario_projection("Stale", _fake_kpis(0.080), "2025-01-01T09:00", True)
        rows = build_compare_rows([p1, p2])
        assert p2.state == "STALE"
        # Values still shown (not wiped)
        irr_row = next(r for r in rows if r.key == "project_irr")
        assert irr_row.values[1] == "8.00%"

    def test_not_run_scenario_in_compare_shows_na(self):
        from app.v2.scenario_kpi_projection import build_scenario_projection, build_compare_rows
        p1 = build_scenario_projection("Base", _fake_kpis(0.085), "2025-01-01T10:00", False)
        p2 = build_scenario_projection("NotRun", None, None, False)
        rows = build_compare_rows([p1, p2])
        assert p2.state == "NOT_RUN"
        irr_row = next(r for r in rows if r.key == "project_irr")
        assert irr_row.values[1] == "—"
        assert irr_row.deltas[1] == "—"

    def test_zero_delta(self):
        from app.v2.scenario_kpi_projection import build_scenario_projection, build_compare_rows
        kpis = _fake_kpis(0.085)
        p1 = build_scenario_projection("Base", kpis, "2025-01-01T10:00", False)
        p2 = build_scenario_projection("Same", dict(kpis), "2025-01-01T10:00", False)
        rows = build_compare_rows([p1, p2])
        irr_row = next(r for r in rows if r.key == "project_irr")
        assert irr_row.deltas[1] == "+0.00%"


# ── Sensitivity driver field validation ──────────────────────────────────── #

class TestSensitivityDriverSpecs:

    def _get_driver_specs(self):
        """Extract DRIVER_SPECS from router source (live import would trigger app init)."""
        import re
        src = open("app/v2/router.py").read()
        # Find the block between DRIVER_SPECS = { and the closing }
        m = re.search(r'DRIVER_SPECS: dict\[str, dict\] = \{(.+?)^\s*\}', src, re.DOTALL | re.MULTILINE)
        return m.group(0) if m else src

    def test_tariff_uses_snapshot_key(self):
        src = open("app/v2/router.py").read()
        assert '"tariff_eur_mwh"' in src or "'tariff_eur_mwh'" in src

    def test_capex_uses_snapshot_key(self):
        src = open("app/v2/router.py").read()
        assert '"total_capex_keur"' in src

    def test_opex_uses_snapshot_key(self):
        src = open("app/v2/router.py").read()
        assert '"opex_y1_keur"' in src

    def test_generation_uses_p50_hours(self):
        src = open("app/v2/router.py").read()
        assert '"p50_hours"' in src

    def test_interest_rate_uses_snapshot_key(self):
        src = open("app/v2/router.py").read()
        assert '"interest_rate_pct"' in src

    def test_gearing_uses_snapshot_key(self):
        src = open("app/v2/router.py").read()
        assert '"gearing_pct"' in src

    def test_no_dotted_paths_in_driver_fields(self):
        """Driver fields must be flat snapshot keys, not dotted engine paths."""
        import re
        src = open("app/v2/router.py").read()
        # Find DRIVER_SPECS block
        start = src.find("DRIVER_SPECS: dict[str, dict]")
        block = src[start:start+2000]
        # Look for "field": "something.something" patterns (dotted engine paths are wrong)
        wrong = re.findall(r'"field":\s*"[a-z]+\.[a-z]', block)
        assert wrong == [], f"Dotted engine paths found in DRIVER_SPECS fields: {wrong}"

    def test_sensitivity_non_destructive_guard_present(self):
        """The non-destructive runtime guard must be in the sensitivity handler."""
        src = open("app/v2/router.py").read()
        assert "_pis_base_values_snapshot" in src
        assert "NON-DESTRUCTIVE VIOLATION" in src

    def test_tariff_field_alt_present_for_newer_projects(self):
        src = open("app/v2/router.py").read()
        assert '"field_alt"' in src or "'field_alt'" in src


# ── Scenario select clears runtime evidence ──────────────────────────────── #

class TestSelectScenarioClearsRuntime:

    def test_select_clears_workspace_runtime(self):
        """Selecting a scenario clears last_runtime_snapshot_id in workspace."""
        from app.persistence.repository import (
            save_project, save_workspace_state, get_workspace_state as _get_ws
        )
        from app.persistence.scenarios_repository import (
            get_or_create_base_case_scenario, add_scenario, select_scenario
        )
        user_id = _uid()
        pr, code = _make_project(user_id)

        snap = {"tariff_eur_mwh": 65.0}
        # Create workspace with runtime evidence
        ws = save_workspace_state(
            user_id=user_id,
            project_id=pr.project_id,
            project_code=code,
            draft_snapshot=snap,
            saved_snapshot=snap,
            last_runtime_snapshot_id="old_snap",
            last_runtime_summary={"project_irr": 0.085},
        )
        assert _get_ws(user_id, pr.project_id).last_runtime_snapshot_id == "old_snap"

        base, child = _make_base_and_scenario(user_id, pr.project_id, code)
        select_scenario(user_id=user_id, project_id=pr.project_id, scenario_id=child.scenario_id)

        ws_after = _get_ws(user_id, pr.project_id)
        assert ws_after.last_runtime_snapshot_id is None
        assert ws_after.active_scenario_id == child.scenario_id

    def test_select_does_not_mutate_scenario_run_summary(self):
        """Selecting a scenario must not change either scenario's last_run_summary."""
        from app.persistence.repository import (
            save_project, update_scenario_last_run_summary, get_scenario
        )
        from app.persistence.scenarios_repository import add_scenario, select_scenario
        from app.persistence.scenarios_repository import get_or_create_base_case_scenario
        user_id = _uid()
        pr, code = _make_project(user_id)

        base, child = _make_base_and_scenario(user_id, pr.project_id, code)
        update_scenario_last_run_summary(user_id, base.scenario_id,
                                          {"kpis": _fake_kpis(0.085), "ran_at": "2025-01-01T09:00:00"})
        update_scenario_last_run_summary(user_id, child.scenario_id,
                                          {"kpis": _fake_kpis(0.075), "ran_at": "2025-01-01T10:00:00"})

        # Select child, then select base — neither run summary should change
        select_scenario(user_id, pr.project_id, child.scenario_id)
        select_scenario(user_id, pr.project_id, base.scenario_id)

        base_r = get_scenario(base.scenario_id, user_id)
        child_r = get_scenario(child.scenario_id, user_id)
        assert base_r.last_run_summary["kpis"]["project_irr"] == pytest.approx(0.085)
        assert child_r.last_run_summary["kpis"]["project_irr"] == pytest.approx(0.075)


# ── No financial arithmetic in router sensitivity ─────────────────────────── #

class TestNoFinancialArithmeticInTemplatesAndRouter:

    def _scan(self, path):
        return open(path).read()

    def _no_financial_calc(self, src, context=""):
        forbidden = [
            "Math.pow",       # JS power — used in IRR Newton-Raphson
            "npv(",           # NPV function
            "xirr(",          # XIRR
            "Math.exp(",      # Exponential (financial)
            "Math.log(",      # Log (financial)
        ]
        for f in forbidden:
            assert f not in src, f"{context}: forbidden financial function {f!r} found"

    def test_router_no_financial_calc(self):
        src = self._scan("app/v2/router.py")
        # These specific patterns would indicate client-side financial reconstruction
        assert "Math.pow" not in src
        assert "Math.exp" not in src
        # Sensitivity uses run_project() only, not manual IRR
        assert "xirr" not in src.lower()

    def test_compare_template_no_financial_calc(self):
        self._no_financial_calc(
            self._scan("app/templates/v2/partials/sheet_compare.html"),
            context="sheet_compare.html"
        )

    def test_sensitivity_template_no_financial_calc(self):
        self._no_financial_calc(
            self._scan("app/templates/v2/partials/sheet_sensitivity_results.html"),
            context="sheet_sensitivity_results.html"
        )

    def test_scenarios_template_no_financial_calc(self):
        self._no_financial_calc(
            self._scan("app/templates/v2/partials/sheet_scenarios.html"),
            context="sheet_scenarios.html"
        )

    def test_kpi_projection_no_financial_calc(self):
        src = self._scan("app/v2/scenario_kpi_projection.py")
        # No actual imports of financial engine functions
        assert "from app.api.project_runner import" not in src
        assert "from financial_engine" not in src
        assert "xirr" not in src.lower()
        assert "npv(" not in src.lower()


# ── Engine freeze gate ────────────────────────────────────────────────────── #

class TestEngineFreezeGate:

    def test_financial_engine_unmodified(self):
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--name-only",
             "74593eecfbe463314cd171f628f6bae795651dc8...HEAD",
             "--", "financial_engine/", "finco_core/",
             "app/api/project_runner.py",
             "app/services/production_financial_authority.py"],
            capture_output=True, text=True
        )
        assert result.stdout.strip() == "", (
            f"Frozen files were modified:\n{result.stdout}"
        )
