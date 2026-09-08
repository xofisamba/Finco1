"""
tests.test_ui3b_scenario_sensitivity — UI-3B surface contracts.

Covers:
  - ScenarioProjection / build_scenario_projection formatting
  - build_compare_rows delta arithmetic (raw float path, not string re-parse)
  - Output integrity: kpis_raw populated correctly
  - Sensitivity DRIVER_SPECS completeness
  - OverviewProjection active_scenario_name field
"""
from __future__ import annotations

import pytest

from app.v2.scenario_kpi_projection import (
    KPI_CATALOG,
    ScenarioKpiRow,
    ScenarioProjection,
    build_compare_rows,
    build_scenario_projection,
)


# ── helpers ──────────────────────────────────────────────────────────────── #

def _make_rs(**kw):
    """Minimal runtime_summary dict with sane defaults."""
    defaults = {
        "project_irr": 0.085,
        "equity_irr": 0.120,
        "min_dscr": 1.32,
        "avg_dscr": 1.45,
        "min_llcr": 1.28,
        "senior_debt_keur": 27_000.0,
        "total_capex_keur": 45_000.0,
        "total_revenue_keur": 120_000.0,
        "total_ebitda_keur": 80_000.0,
        "total_cfads_keur": 60_000.0,
    }
    defaults.update(kw)
    return defaults


# ── build_scenario_projection ─────────────────────────────────────────────── #

class TestBuildScenarioProjection:

    def test_clean_state(self):
        rs = _make_rs()
        sp = build_scenario_projection("Base Case", rs, "2025-01-01T10:00:00", is_stale=False)
        assert sp.state == "CLEAN"
        assert sp.scenario_name == "Base Case"

    def test_stale_state(self):
        rs = _make_rs()
        sp = build_scenario_projection("Base Case", rs, "2025-01-01T10:00:00", is_stale=True)
        assert sp.state == "STALE"

    def test_not_run_state(self):
        sp = build_scenario_projection("Downside", None, None, is_stale=False)
        assert sp.state == "NOT_RUN"
        assert sp.ran_at == ""

    def test_pct_formatting(self):
        rs = _make_rs(project_irr=0.085)
        sp = build_scenario_projection("B", rs, None, is_stale=False)
        assert sp.kpis["project_irr"] == "8.50%"

    def test_ratio_formatting(self):
        rs = _make_rs(avg_dscr=1.45)
        sp = build_scenario_projection("B", rs, None, is_stale=False)
        assert sp.kpis["avg_dscr"] == "1.45x"

    def test_keur_formatting(self):
        rs = _make_rs(total_capex_keur=45_000.0)
        sp = build_scenario_projection("B", rs, None, is_stale=False)
        assert "45,000" in sp.kpis["total_capex_keur"]
        assert "kEUR" in sp.kpis["total_capex_keur"]

    def test_kpis_raw_populated(self):
        rs = _make_rs(project_irr=0.085)
        sp = build_scenario_projection("B", rs, None, is_stale=False)
        assert sp.kpis_raw["project_irr"] == pytest.approx(0.085)

    def test_kpis_raw_none_on_missing(self):
        sp = build_scenario_projection("B", {}, None, is_stale=False)
        for key in [item["key"] for item in KPI_CATALOG]:
            assert sp.kpis_raw[key] is None

    def test_kpis_raw_none_on_nan(self):
        import math
        rs = _make_rs(project_irr=float("nan"))
        sp = build_scenario_projection("B", rs, None, is_stale=False)
        assert sp.kpis_raw["project_irr"] is None
        assert sp.kpis["project_irr"] == "—"

    def test_ran_at_truncation(self):
        rs = _make_rs()
        sp = build_scenario_projection("B", rs, "2025-06-15T14:30:00Z", is_stale=False)
        assert sp.ran_at == "2025-06-15 14:30"
        assert "2025-06-15" in sp.ran_at


# ── build_compare_rows ────────────────────────────────────────────────────── #

class TestBuildCompareRows:

    def _two_projections(self, base_irr=0.085, alt_irr=0.094):
        rs_base = _make_rs(project_irr=base_irr)
        rs_alt = _make_rs(project_irr=alt_irr)
        p_base = build_scenario_projection("Base Case", rs_base, None, is_stale=False)
        p_alt = build_scenario_projection("Upside", rs_alt, None, is_stale=False)
        return p_base, p_alt

    def test_returns_all_kpi_keys(self):
        p1, p2 = self._two_projections()
        rows = build_compare_rows([p1, p2])
        keys = {r.key for r in rows}
        assert keys == {item["key"] for item in KPI_CATALOG}

    def test_base_delta_is_dash(self):
        p1, p2 = self._two_projections()
        rows = build_compare_rows([p1, p2])
        irr_row = next(r for r in rows if r.key == "project_irr")
        assert irr_row.deltas[0] == "—"

    def test_pct_delta_positive(self):
        p1, p2 = self._two_projections(base_irr=0.085, alt_irr=0.094)
        rows = build_compare_rows([p1, p2])
        irr_row = next(r for r in rows if r.key == "project_irr")
        # delta = (0.094 - 0.085) * 100 = +0.90%
        assert irr_row.deltas[1] == "+0.90%"

    def test_pct_delta_negative(self):
        p1, p2 = self._two_projections(base_irr=0.094, alt_irr=0.085)
        rows = build_compare_rows([p1, p2])
        irr_row = next(r for r in rows if r.key == "project_irr")
        assert irr_row.deltas[1] == "-0.90%"

    def test_ratio_delta_format(self):
        rs_base = _make_rs(avg_dscr=1.45)
        rs_alt = _make_rs(avg_dscr=1.50)
        p1 = build_scenario_projection("Base", rs_base, None, is_stale=False)
        p2 = build_scenario_projection("Alt", rs_alt, None, is_stale=False)
        rows = build_compare_rows([p1, p2])
        row = next(r for r in rows if r.key == "avg_dscr")
        assert row.deltas[1] == "+0.05x"

    def test_keur_delta_format(self):
        rs_base = _make_rs(total_capex_keur=45_000.0)
        rs_alt = _make_rs(total_capex_keur=50_000.0)
        p1 = build_scenario_projection("Base", rs_base, None, is_stale=False)
        p2 = build_scenario_projection("Alt", rs_alt, None, is_stale=False)
        rows = build_compare_rows([p1, p2])
        row = next(r for r in rows if r.key == "total_capex_keur")
        assert "+5,000" in row.deltas[1]
        assert "kEUR" in row.deltas[1]

    def test_delta_na_when_not_run(self):
        p1 = build_scenario_projection("Base", _make_rs(), None, is_stale=False)
        p2 = build_scenario_projection("NotRun", None, None, is_stale=False)
        rows = build_compare_rows([p1, p2])
        irr_row = next(r for r in rows if r.key == "project_irr")
        assert irr_row.deltas[1] == "—"

    def test_three_scenarios(self):
        rs = _make_rs()
        p1 = build_scenario_projection("A", rs, None, is_stale=False)
        p2 = build_scenario_projection("B", _make_rs(project_irr=0.10), None, is_stale=False)
        p3 = build_scenario_projection("C", _make_rs(project_irr=0.07), None, is_stale=False)
        rows = build_compare_rows([p1, p2, p3])
        irr_row = next(r for r in rows if r.key == "project_irr")
        assert len(irr_row.deltas) == 3
        assert irr_row.deltas[0] == "—"

    def test_values_list_length(self):
        p1, p2 = self._two_projections()
        rows = build_compare_rows([p1, p2])
        for row in rows:
            assert len(row.values) == 2
            assert len(row.deltas) == 2
            assert len(row.raw_values) == 2


# ── KPI_CATALOG completeness ──────────────────────────────────────────────── #

class TestKpiCatalog:

    def test_all_fmt_values_valid(self):
        valid_fmts = {"pct", "ratio", "keur"}
        for item in KPI_CATALOG:
            assert item["fmt"] in valid_fmts, f"{item['key']} has unknown fmt {item['fmt']!r}"

    def test_no_duplicate_keys(self):
        keys = [item["key"] for item in KPI_CATALOG]
        assert len(keys) == len(set(keys))

    def test_required_kpis_present(self):
        keys = {item["key"] for item in KPI_CATALOG}
        required = {"project_irr", "equity_irr", "min_dscr", "avg_dscr", "min_llcr"}
        assert required.issubset(keys)


# ── OverviewProjection active_scenario_name ───────────────────────────────── #

class TestOverviewProjectionScenarioName:

    def test_active_scenario_name_field_exists(self):
        from app.v2.overview_projection import OverviewProjection, NOT_AVAILABLE
        # Field must exist and default to ""
        import inspect
        sig = inspect.signature(OverviewProjection)
        assert "active_scenario_name" in sig.parameters

    def test_build_passes_through_name(self):
        from app.v2.overview_projection import build_overview_projection
        import inspect
        sig = inspect.signature(build_overview_projection)
        assert "active_scenario_name" in sig.parameters


# ── router DRIVER_SPECS completeness ─────────────────────────────────────── #

class TestDriverSpecs:

    def _get_driver_specs(self):
        import importlib, ast, re
        src = open("app/v2/router.py").read()
        # Find DRIVER_SPECS dict literal
        m = re.search(r"DRIVER_SPECS\s*=\s*\{(.+?)\}\s*\n[^\s]", src, re.DOTALL)
        assert m, "DRIVER_SPECS not found in router.py"
        return m.group(0)

    def test_driver_specs_exists(self):
        src = open("app/v2/router.py").read()
        assert "DRIVER_SPECS" in src

    def test_required_drivers_present(self):
        src = open("app/v2/router.py").read()
        # capex_total and opex_total removed from MVP — their summary fields are not writable
        for driver in ["tariff", "generation", "interest_rate", "gearing"]:
            assert f'"{driver}"' in src or f"'{driver}'" in src, f"driver {driver!r} missing"

    def test_five_steps_per_driver(self):
        import re
        src = open("app/v2/router.py").read()
        # Count step lists — each should have 5 entries
        step_lists = re.findall(r'"steps":\s*\[([^\]]+)\]', src)
        for sl in step_lists:
            count = len([x.strip() for x in sl.split(",") if x.strip()])
            assert count == 5, f"Expected 5 steps, got {count}: {sl}"


# ── Correction C: driver contract + canonical field_id ───────────────────── #

import os
import sys
import socket
import subprocess
import time
import urllib.parse
import urllib.request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

os.environ.setdefault("FINCO_SECRET_KEY", "ui3b-sens-correction-c-key")
os.environ.setdefault("FINCO_COOKIE_SECURE", "false")

from app.auth import create_session_token  # noqa: E402

COOKIE_NAME = "finco_session"


# Maps each driver to (field_id, snapshot_key, expected_step_magnitude, mode).
# capex_total and opex_total removed: their summary fields are derived_display
# and not writable via with_value() — removed from MVP catalog per spec.
DRIVER_FIELD_MAP = {
    "tariff":        ("revenue.ppa.base_tariff",          "rev_ppa_base_tariff",    0.10,   "pct_multiplier"),
    "generation":    ("project_setup.technical.p50_hours","p50_hours",              0.05,   "pct_multiplier"),
    "interest_rate": ("debt.senior.interest_rate_pct",    "interest_rate_pct",      1.0,    "absolute_add"),
    "gearing":       ("debt.senior.gearing_pct",          "gearing_pct",            5.0,    "absolute_add"),
}


class TestDriverFieldContract:
    """Each driver field_id must exist in WORKBOOK and be writable via with_value()."""

    def test_all_field_ids_in_workbook(self):
        from app.workbook.registry import WORKBOOK
        all_fids = {f.field_id for f in WORKBOOK.all_fields()}
        for driver, (field_id, *_) in DRIVER_FIELD_MAP.items():
            assert field_id in all_fids, \
                f"Driver {driver!r}: field_id {field_id!r} not in WORKBOOK registry"

    def test_tariff_legacy_field_id_in_workbook(self):
        """Fallback tariff field must also exist in WORKBOOK."""
        from app.workbook.registry import WORKBOOK
        all_fids = {f.field_id for f in WORKBOOK.all_fields()}
        assert "revenue.ppa.tariff_legacy" in all_fids

    def test_interest_rate_absolute_steps_are_percentage_points(self):
        """interest_rate steps must be in percentage-point units (e.g. ±2.0, not ±0.02)."""
        import re
        src = open("app/v2/router.py").read()
        m = re.search(r'"interest_rate".*?"steps":\s*\[([^\]]+)\]', src, re.DOTALL)
        assert m, "interest_rate driver steps not found"
        vals = [float(x.strip()) for x in m.group(1).split(",") if x.strip()]
        assert len(vals) == 5
        # Steps must be ±1.0 and ±2.0 (percentage points), not ±0.01 and ±0.02 (fractions)
        assert max(abs(v) for v in vals) >= 1.0, \
            f"interest_rate steps look like fractions, not pp: {vals}"

    def test_gearing_absolute_steps_are_percentage_points(self):
        """gearing steps must be in percentage-point units (e.g. ±10.0, not ±0.10)."""
        import re
        src = open("app/v2/router.py").read()
        m = re.search(r'"gearing".*?"steps":\s*\[([^\]]+)\]', src, re.DOTALL)
        assert m, "gearing driver steps not found"
        vals = [float(x.strip()) for x in m.group(1).split(",") if x.strip()]
        assert max(abs(v) for v in vals) >= 5.0, \
            f"gearing steps look like fractions, not pp: {vals}"

    def test_field_ids_use_semantic_not_snapshot_keys(self):
        """DRIVER_SPECS must not contain snapshot keys as field_id values."""
        import re
        src = open("app/v2/router.py").read()
        # These are snapshot keys that must NOT appear as field_id values
        forbidden_as_field_id = [
            '"field_id": "rev_ppa_base_tariff"',
            '"field_id": "p50_hours"',
            '"field_id": "interest_rate_pct"',
            '"field_id": "gearing_pct"',
            '"field_id": "tariff_eur_mwh"',
        ]
        for bad in forbidden_as_field_id:
            assert bad not in src, f"Snapshot key used as field_id in DRIVER_SPECS: {bad!r}"


class TestSensitivityProductionHandler:
    """Integration tests hitting POST /v2/workbook/scenarios/sensitivity/run directly."""

    @classmethod
    def setup_class(cls):
        """Start a live server and create a Solar project once for the class."""
        cls.port = _pick_free_port()
        cls.base_url = f"http://127.0.0.1:{cls.port}"
        env = os.environ.copy()
        cls.proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "main_web:app",
             "--host", "127.0.0.1", "--port", str(cls.port)],
            cwd=BASE_DIR,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        _wait_for_health(cls.base_url)
        cls.token = create_session_token()
        cls.project_code = _create_solar_project(cls.base_url, cls.token)

    @classmethod
    def teardown_class(cls):
        cls.proc.terminate()
        try:
            cls.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            cls.proc.kill()

    def _post_sensitivity(self, driver, scenario_id=None):
        params = {"project": self.project_code, "driver": driver}
        if scenario_id:
            params["scenario_id"] = scenario_id
        form = urllib.parse.urlencode(params).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/v2/workbook/scenarios/sensitivity/run",
            data=form,
            method="POST",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Cookie": f"{COOKIE_NAME}={self.token}",
                "HX-Request": "true",
            },
        )
        with urllib.request.urlopen(req, timeout=120.0) as resp:
            return resp.status, resp.read().decode()

    def test_tariff_sensitivity_returns_200_five_rows(self):
        status, body = self._post_sensitivity("tariff")
        assert status == 200
        for label in ("-20%", "-10%", "Base", "+10%", "+20%"):
            assert label in body, f"Label {label!r} missing. body[:300]={body[:300]}"
        assert "FAILED" not in body, f"FAILED in tariff sensitivity response: {body[:600]}"

    def test_generation_sensitivity_returns_200_five_rows(self):
        status, body = self._post_sensitivity("generation")
        assert status == 200
        for label in ("-10%", "-5%", "Base", "+5%", "+10%"):
            assert label in body, f"Label {label!r} missing"
        assert "FAILED" not in body

    def test_interest_rate_sensitivity_returns_200_five_rows(self):
        status, body = self._post_sensitivity("interest_rate")
        assert status == 200
        for label in ("-200 bps", "-100 bps", "Base", "+100 bps", "+200 bps"):
            assert label in body, f"Label {label!r} missing"
        assert "FAILED" not in body

    def test_no_silent_base_fallback_tariff(self):
        """All non-base tariff points must produce different IRRs from the base point."""
        from app.api.project_runner import run_project
        from app.workbook.service import WorkbookService
        snap = {
            "project_name": "SensFallbackTest", "project_type": "Solar",
            "country_market": "Poland", "capacity_mw": 50.0,
            "cod_date": "2025-01-01", "construction_months": 18,
            "horizon_years": 20, "tariff_eur_mwh": 65.0, "ppa_term_years": 15,
            "p50_hours": 1750.0, "opex_y1_keur": 800.0, "total_capex_keur": 42000.0,
            "gearing_pct": 70.0, "interest_rate_pct": 4.5, "tenor_years": 18,
            "target_dscr": 1.30,
        }
        pis_base = WorkbookService.build_input_set(snap)
        field_id = "revenue.ppa.tariff_legacy"  # legacy tariff
        base_val = pis_base.values.get(field_id)
        assert base_val is not None, "tariff_legacy not in PIS"

        irrs = []
        for step in [-0.20, -0.10, 0.0, +0.10, +0.20]:
            new_val = float(base_val) * (1.0 + step)
            pis_sens = pis_base.with_value(field_id, str(new_val))
            pi = WorkbookService.to_projectinputs(pis_sens)
            r = run_project("Solar", "Base", project_inputs_override=pi)
            irrs.append(r["kpis"]["project_irr"])

        # All IRRs must differ (no silent base fallback)
        assert len(set(round(v, 6) for v in irrs)) == 5, \
            f"Some sensitivity IRRs are identical (silent fallback?): {irrs}"
        # Must be monotone increasing (higher tariff → higher IRR)
        assert irrs == sorted(irrs), f"Tariff sensitivity not monotone: {irrs}"


class TestBaseVsDownsideSensitivity:
    """Prove sensitivity is scenario-specific: Base ≠ Downside for the same driver."""

    def test_base_vs_downside_sensitivity_differ(self):
        from app.api.project_runner import run_project
        from app.workbook.service import WorkbookService
        from dataclasses import replace as _dc_replace
        from app.services.capex_sub_lines_integration import apply_user_sub_lines_replacing_base
        from app.services.opex_sub_lines_integration import apply_user_sub_lines_to_opex

        snap = {
            "project_name": "ScenSensTest", "project_type": "Solar",
            "country_market": "Poland", "capacity_mw": 50.0,
            "cod_date": "2025-01-01", "construction_months": 18,
            "horizon_years": 20, "tariff_eur_mwh": 65.0, "ppa_term_years": 15,
            "p50_hours": 1750.0, "opex_y1_keur": 800.0, "total_capex_keur": 42000.0,
            "gearing_pct": 70.0, "interest_rate_pct": 4.5, "tenor_years": 18,
            "target_dscr": 1.30,
        }
        # Downside has materially lower tariff (–25%)
        downside_snap = dict(snap)
        downside_snap["tariff_eur_mwh"] = 65.0 * 0.75  # 48.75 EUR/MWh

        pis_base = WorkbookService.build_input_set(snap)
        pis_downside = WorkbookService.build_input_set(downside_snap)

        field_id = "revenue.ppa.tariff_legacy"

        def run_5_point(pis):
            base_val = pis.values.get(field_id)
            irrs = []
            for step in [-0.20, -0.10, 0.0, +0.10, +0.20]:
                new_val = float(base_val) * (1.0 + step)
                pis_s = pis.with_value(field_id, str(new_val))
                pi = WorkbookService.to_projectinputs(pis_s)
                r = run_project("Solar", "Base", project_inputs_override=pi)
                irrs.append(r["kpis"]["project_irr"])
            return irrs

        base_irrs = run_5_point(pis_base)
        down_irrs = run_5_point(pis_downside)

        # Results must differ
        assert base_irrs != down_irrs, "Base and Downside sensitivity produced identical results"

        # Center of Downside sensitivity (step=0, i.e. index 2) must equal the
        # Downside canonical run basis — not the Base center
        down_center = down_irrs[2]
        base_center = base_irrs[2]
        assert abs(down_center - base_center) > 0.005, \
            f"Downside center IRR {down_center:.4%} too close to Base center {base_center:.4%}"

    def test_downside_center_equals_canonical_downside_run(self):
        """The center sensitivity point of Downside must equal a standalone Downside run."""
        from app.api.project_runner import run_project
        from app.workbook.service import WorkbookService

        snap = {
            "project_name": "ScenSensCanon", "project_type": "Solar",
            "country_market": "Poland", "capacity_mw": 50.0,
            "cod_date": "2025-01-01", "construction_months": 18,
            "horizon_years": 20, "tariff_eur_mwh": 48.0, "ppa_term_years": 15,
            "p50_hours": 1750.0, "opex_y1_keur": 800.0, "total_capex_keur": 42000.0,
            "gearing_pct": 70.0, "interest_rate_pct": 4.5, "tenor_years": 18,
            "target_dscr": 1.30,
        }
        pis = WorkbookService.build_input_set(snap)
        field_id = "revenue.ppa.tariff_legacy"
        base_val = pis.values.get(field_id)

        # Center (step=0) — no driver override
        pis_center = pis.with_value(field_id, str(float(base_val) * 1.0))
        pi_center = WorkbookService.to_projectinputs(pis_center)
        irr_center = run_project("Solar", "Base", project_inputs_override=pi_center)["kpis"]["project_irr"]

        # Standalone canonical run
        pi_canonical = WorkbookService.to_projectinputs(pis)
        irr_canonical = run_project("Solar", "Base", project_inputs_override=pi_canonical)["kpis"]["project_irr"]

        assert abs(irr_center - irr_canonical) < 1e-8, \
            f"Sensitivity center {irr_center:.6%} != canonical run {irr_canonical:.6%}"


class TestCompareStaleUsesSnapshotHash:
    """Regression: compare stale detection must use snapshot hash, not updated_at."""

    def test_compare_stale_helper_is_snap_is_stale(self):
        """The compare route must import _is_stale from scenario_presentation."""
        src = open("app/v2/router.py").read()
        # Must use the shared snapshot-hash helper, not timestamp comparison
        assert "scenario_presentation" in src and "_is_stale" in src, \
            "_is_stale from scenario_presentation not found in router.py"
        # Must NOT contain the old updated_at > ran_at pattern in the compare section
        assert "is_stale = _sc_updated > _ran_at_dt" not in src, \
            "Old updated_at timestamp comparison still present in router.py"

    def test_rename_does_not_cause_stale_in_compare(self):
        """Rename changes updated_at but not snapshot → must not be STALE."""
        from app.v2.scenario_presentation import _is_stale
        from datetime import datetime, timezone

        class FakeScenario:
            overrides = {}
            snapshot = {"tariff_eur_mwh": "65.0"}
            # updated_at is after ran_at (simulates rename happening after last run)
            updated_at = datetime(2026, 6, 2, 12, 0, 0, tzinfo=timezone.utc)
            last_run_summary = {
                "kpis": {"project_irr": 0.08},
                "ran_at": "2026-06-01T10:00:00",
                # snapshot_hash matches current snapshot
                "scenario_snapshot_hash": None,  # will trigger fallback: compare overrides
                "scenario_overrides_at_run": {},  # no overrides at run time
            }

        sc = FakeScenario()
        # After rename: overrides still empty, updated_at advanced → must be CURRENT
        assert not _is_stale(sc), "Rename incorrectly marks scenario STALE in compare"

    def test_financial_edit_causes_stale_in_compare(self):
        """Financial override change after run → must be STALE."""
        from app.v2.scenario_presentation import _is_stale

        class FakeScenario:
            overrides = {"tariff_eur_mwh": "50.0"}  # changed after run
            snapshot = None
            updated_at = None
            last_run_summary = {
                "kpis": {"project_irr": 0.08},
                "ran_at": "2026-06-01T10:00:00",
                "scenario_snapshot_hash": None,
                "scenario_overrides_at_run": {"tariff_eur_mwh": "65.0"},  # different
            }

        sc = FakeScenario()
        assert _is_stale(sc), "Financial edit must cause STALE in compare"


# ── helpers (duplicated from browser test module to avoid cross-module fixture coupling) ── #

def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        return s.getsockname()[1]


def _wait_for_health(base_url: str, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{base_url}/public-health", timeout=2.0) as r:
                if r.status == 200:
                    return
        except Exception:
            time.sleep(0.3)
    raise RuntimeError(f"Server at {base_url} did not become healthy within {timeout}s")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **kw):
        return None


def _create_solar_project(base_url: str, token: str) -> str:
    form = urllib.parse.urlencode({
        "project_name": "SensIntegration Solar",
        "project_type": "Solar",
        "country_market": "Poland",
        "capacity_mw": "50",
        "cod_date": "2025-01-01",
        "construction_months": "18",
        "horizon_years": "20",
        "tariff_eur_mwh": "65",
        "ppa_term_years": "15",
        "p50_hours": "1750",
        "opex_y1_keur": "800",
        "total_capex_keur": "42000",
        "gearing_pct": "70",
        "interest_rate_pct": "4.5",
        "tenor_years": "18",
        "target_dscr": "1.30",
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}/projects/create",
        data=form,
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Cookie": f"finco_session={token}",
        },
    )
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(req, timeout=15.0) as response:
            loc = response.headers.get("Location") or response.headers.get("HX-Redirect")
            if loc:
                code = urllib.parse.parse_qs(urllib.parse.urlparse(loc).query).get("project", [None])[0]
                if code:
                    return code
    except urllib.error.HTTPError as e:
        loc = e.headers.get("Location") or e.headers.get("HX-Redirect")
        if loc:
            code = urllib.parse.parse_qs(urllib.parse.urlparse(loc).query).get("project", [None])[0]
            if code:
                return code
    raise RuntimeError("Could not create Solar project for sensitivity integration tests")
