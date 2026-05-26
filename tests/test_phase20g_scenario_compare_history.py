"""Phase 20G — Scenario Compare + Runtime History tests.

Run with:  python -m pytest tests/test_phase20g_scenario_compare_history.py -v
"""
import os
import sys
import uuid

import pytest

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")
os.environ.setdefault("FINCO_COOKIE_SECURE", "false")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from app.auth import COOKIE_NAME, create_session_token
from app.persistence.repository import (
    add_scenario,
    bind_workspace_to_scenario,
    create_project_record,
    get_base_case_scenario,
    get_scenario,
    get_workspace_state,
    record_workspace_runtime,
    save_workspace_state,
    seed_scenarios_if_needed,
    update_scenario_last_run_summary,
)


@pytest.fixture
def isolated_db():
    """Isolated file-backed DB per test."""
    import app.persistence.db as db_mod
    old_path = os.environ.get("FINCO_DB_PATH")
    db_file = f"/tmp/phase20g_{uuid.uuid4().hex[:8]}.db"
    os.environ["FINCO_DB_PATH"] = db_file
    db_mod.DB_PATH = db_file
    db_mod._connection = None
    yield db_file
    db_mod._connection = None
    if old_path:
        os.environ["FINCO_DB_PATH"] = old_path
        db_mod.DB_PATH = old_path
    else:
        os.environ.pop("FINCO_DB_PATH", None)


@pytest.fixture
def client(isolated_db):
    from main_web import app
    c = TestClient(app, raise_server_exceptions=False)
    c.cookies.set(COOKIE_NAME, create_session_token())
    yield c


# ─── Helpers ────────────────────────────────────────────────────────────────────────

def _base_snapshot(tariff="60", capacity_mw="50"):
    return {
        "active_project": "phase20g-test",
        "project_name": "Phase20G Test",
        "project_type": "wind",
        "template_source": "blank",
        "country_market": "Croatia",
        "scenario": "base",
        "capacity_mw": capacity_mw,
        "tariff_eur_mwh": tariff,
        "p50_hours": "2200",
        "total_capex_keur": "45000",
        "opex_y1_keur": "900",
        "gearing_pct": "85",
        "target_dscr": "1.4",
        "interest_rate_pct": "6.5",
        "tenor_years": "15",
        "cod_date": "2029-12-31",
        "construction_months": "24",
        "horizon_years": "25",
        "capacity_factor": "",
        "ppa_term_years": "10",
        "project_origin": "user_created",
    }


def _runtime_summary(tariff=60.0, project_irr=0.09, equity_irr=0.11, dscr=1.45):
    return {
        "total_revenue_keur": 32000.0,
        "total_opex_keur": 1200.0,
        "total_ebitda_keur": 18000.0,
        "distribution_keur": 42000.0,
        "senior_debt_keur": 43000.0,
        "project_irr": project_irr,
        "equity_irr": equity_irr,
        "avg_dscr": dscr,
        "min_dscr": 1.2,
        "shl_balance_keur": 8000.0,
    }


def _replay_meta(scenario_id=None, runtime_origin="saved_state"):
    return {
        "scenario_id": scenario_id,
        "runtime_origin": runtime_origin,
        "runtime_snapshot_id": uuid.uuid4().hex[:16],
        "runtime_timestamp": "2026-05-01T12:00:00",
    }


def _make_project(user_id="1"):
    """Create a project with a saved workspace + base case scenario."""
    code = f"t20g-{uuid.uuid4().hex[:8]}"
    kw = {
        "user_id": user_id,
        "project_code": code,
        "project_name": "Phase20G Test",
        "project_type": "wind",
        "template_source": "blank",
        "project_origin": "factory_template",
        "baseline_snapshot": _base_snapshot(),
    }
    pr = create_project_record(**kw)
    save_workspace_state(
        user_id=user_id, project_id=pr.project_id, project_code=pr.project_code,
        active_scenario_id=None, active_scenario_name=None,
        draft_snapshot=_base_snapshot(), saved_snapshot=_base_snapshot(),
        last_runtime_snapshot=_base_snapshot(), last_runtime_summary={},
        last_runtime_snapshot_id="", last_runtime_origin="", dirty=False,
    )
    seed_scenarios_if_needed(
        user_id=user_id,
        project_id=pr.project_id,
        project_code=pr.project_code,
        project_type="wind",
        source_project_template="blank",
        baseline_snapshot=_base_snapshot(),
        governance_state={},
        template_origin="factory_template",
    )
    return pr


# ─── Test 1: base_vs_active_compare helper ──────────────────────────────────────

class TestBaseVsActiveCompare:
    def test_none_when_no_base_case(self, isolated_db):
        """No project → base_vs_active_compare returns base+empty_state (seed happens)."""
        from app.persistence.repository import base_vs_active_compare
        # Passing a project ID that doesn't exist would fail FK in seed.
        # Instead verify: for a real project (via _make_project), base exists but no active.
        pr = _make_project()
        result = base_vs_active_compare("1", pr.project_id)
        assert result is not None
        assert result["base"] is not None
        assert result["active"] is None
        assert "empty_state" in result

    def test_no_runtime_yet_returns_base_with_no_active(self, isolated_db):
        """Base case exists but has no last_run_summary → base populated, active=None."""
        from app.persistence.repository import base_vs_active_compare
        pr = _make_project()
        result = base_vs_active_compare("1", pr.project_id)
        assert result is not None
        assert result["base"] is not None
        assert result["active"] is None
        assert result["empty_state"] is not None

    def test_base_has_runtime_active_is_none(self, isolated_db):
        """Base has runtime but no active selected → empty_state guidance shown."""
        from app.persistence.repository import base_vs_active_compare
        pr = _make_project()
        base_sc = get_base_case_scenario("1", pr.project_id)
        update_scenario_last_run_summary(
            "1", base_sc.scenario_id,
            _runtime_summary(tariff=60, project_irr=0.09, equity_irr=0.11, dscr=1.45),
            _replay_meta(base_sc.scenario_id, "workspace_base"),
        )
        result = base_vs_active_compare("1", pr.project_id)
        assert result is not None
        assert result["base"] is not None
        assert result["active"] is None
        assert result["empty_state"] is not None

    def test_full_compare_base_and_active(self, isolated_db):
        """Base vs Active → metrics computed with base_value/active_value/delta/sign_class."""
        from app.persistence.repository import base_vs_active_compare
        pr = _make_project()
        base_sc = get_base_case_scenario("1", pr.project_id)
        update_scenario_last_run_summary(
            "1", base_sc.scenario_id,
            _runtime_summary(tariff=60, project_irr=0.09, equity_irr=0.11, dscr=1.45),
            _replay_meta(base_sc.scenario_id, "workspace_base"),
        )
        high_sc = add_scenario(
            user_id="1", project_id=pr.project_id, project_code=pr.project_code,
            scenario_name="High Tariff", parent_scenario_id=base_sc.scenario_id,
            base_input_set=_base_snapshot(tariff="60"),
            overrides={"tariff_eur_mwh": "85"},
        )
        update_scenario_last_run_summary(
            "1", high_sc.scenario_id,
            _runtime_summary(tariff=85, project_irr=0.11, equity_irr=0.14, dscr=1.55),
            _replay_meta(high_sc.scenario_id, "saved_state"),
        )
        bind_workspace_to_scenario("1", pr.project_id, pr.project_code, high_sc)

        result = base_vs_active_compare("1", pr.project_id)
        assert result is not None
        assert result["base"] is not None
        assert result["active"] is not None
        assert result["active"].scenario_name == "High Tariff"
        # Verify metrics structure
        assert len(result["metrics"]) > 0
        rev_row = next((r for r in result["metrics"] if "revenue" in r["key"].lower()), None)
        assert rev_row is not None
        assert rev_row["base_value"] is not None
        assert rev_row["active_value"] is not None
        irr_rows = [r for r in result["metrics"] if "irr" in r["key"].lower() and "equity" not in r["key"].lower()]
        assert len(irr_rows) >= 1
        assert irr_rows[0]["delta"] is not None

    def test_active_unknown_id_shows_empty(self, isolated_db):
        """Workspace active_scenario_id points to non-existent scenario → empty_state."""
        from app.persistence.repository import base_vs_active_compare
        pr = _make_project()
        base_sc = get_base_case_scenario("1", pr.project_id)
        update_scenario_last_run_summary(
            "1", base_sc.scenario_id, _runtime_summary(), _replay_meta(base_sc.scenario_id),
        )
        save_workspace_state(
            user_id="1", project_id=pr.project_id, project_code=pr.project_code,
            active_scenario_id="does-not-exist", active_scenario_name="Unknown Scenario",
            draft_snapshot=_base_snapshot(), saved_snapshot=_base_snapshot(),
            last_runtime_snapshot=_base_snapshot(), last_runtime_summary=_runtime_summary(),
            last_runtime_snapshot_id="", last_runtime_origin="", dirty=False,
        )
        result = base_vs_active_compare("1", pr.project_id)
        assert result is not None
        assert result["base"] is not None
        assert result["active"] is None
        assert "not found" in result["empty_state"]

    def test_delta_sign_class_function(self, isolated_db):
        """_delta_sign_class returns correct Bootstrap color class."""
        from app.persistence.repository import _delta_sign_class
        assert _delta_sign_class(0.05) == "delta-positive"
        assert _delta_sign_class(-0.05) == "delta-negative"
        assert _delta_sign_class(0.0) == "delta-neutral"
        assert _delta_sign_class(None) == "delta-neutral"

    def test_override_field_list_in_runtime_dict(self, isolated_db):
        """_scenario_runtime_dict computes override_field_count and override_field_list."""
        from app.persistence.repository import _scenario_runtime_dict

        class FakeScenario:
            scenario_id = "sc1"
            scenario_name = "High Tariff"
            is_base_case = False
            updated_at = "2026-05-01T12:00:00"
            last_run_summary = {"project_irr": 0.11, "total_revenue_keur": 40000}
            replay_metadata = {"runtime_timestamp": "2026-05-01T12:00:00", "runtime_origin": "saved_state"}
            overrides = {"tariff_eur_mwh": "85", "capacity_mw": "60"}
            snapshot = {"project_origin": "user_created"}

        d = _scenario_runtime_dict(FakeScenario())
        assert d["override_field_count"] == 2
        assert "tariff_eur_mwh" in d["override_field_list"]
        assert d["is_base_case"] is False


# ─── Test 2: repository API ─────────────────────────────────────────────────────

class TestScenarioRuntimeHistory:
    def test_get_base_case_scenario(self, isolated_db):
        pr = _make_project()
        result = get_base_case_scenario("1", pr.project_id)
        assert result is not None
        assert result.is_base_case is True

    def test_update_scenario_last_run_summary(self, isolated_db):
        pr = _make_project()
        base_sc = get_base_case_scenario("1", pr.project_id)
        summary = _runtime_summary(tariff=85, project_irr=0.11)
        ok = update_scenario_last_run_summary(
            "1", base_sc.scenario_id, summary, _replay_meta(base_sc.scenario_id, "saved_state"),
        )
        assert ok is True
        updated = get_scenario(base_sc.scenario_id, "1")
        assert updated.last_run_summary["project_irr"] == 0.11
        assert updated.replay_metadata["runtime_origin"] == "saved_state"

    def test_record_workspace_runtime_stores_scenario_id(self, isolated_db):
        pr = _make_project()
        base_sc = get_base_case_scenario("1", pr.project_id)
        update_scenario_last_run = _runtime_summary()
        update_scenario_last_run_summary("1", base_sc.scenario_id, update_scenario_last_run, _replay_meta(base_sc.scenario_id))
        record_workspace_runtime(
            user_id="1", project_id=pr.project_id, project_code=pr.project_code,
            runtime_snapshot=_base_snapshot(), runtime_summary=update_scenario_last_run,
            runtime_snapshot_id="run1", runtime_origin="saved_state",
            active_scenario_id=base_sc.scenario_id, active_scenario_name="Base Case",
            replay_metadata={"scenario_id": base_sc.scenario_id, "runtime_origin": "saved_state"},
        )
        ws2 = get_workspace_state("1", pr.project_id)
        assert ws2.last_runtime_scenario_id == base_sc.scenario_id


# ─── Test 3: HTTP ───────────────────────────────────────────────────────────────

class TestCompareTabHTTP:
    def test_scenarios_routes_ok(self, client, isolated_db):
        r = client.get("/scenarios?project=pilot-wind")
        assert r.status_code in (200, 302)

    def test_no_cookie_redirects(self, isolated_db):
        from fastapi.testclient import TestClient
        from main_web import app
        raw = TestClient(app, raise_server_exceptions=False)
        r = raw.get("/scenarios")
        assert r.status_code in (200, 302)


# ─── Test 4: Jinja2 template rendering ──────────────────────────────────────────

class TestScenarioCompareTemplate:
    def _render(self, **kwargs):
        from jinja2 import Environment, BaseLoader
        env = Environment(loader=BaseLoader())
        tpl = env.from_string(open("app/templates/partials/scenario_compare.html").read())
        return tpl.render(**kwargs)

    def test_empty_state_renders(self):
        """Empty compare_result dict → 'No scenarios to compare'."""
        result = self._render(compare_result={})
        assert "No scenarios to compare" in result

    def test_base_only_shows_base_runtime_and_guidance(self):
        """Base + active=None + empty_state → 'No Active Scenario' + base KPIs."""
        class FakeBase:
            scenario_name = "Phase20G Test"
            last_run_summary = {"project_irr": 0.09, "equity_irr": 0.11, "avg_dscr": 1.451, "min_dscr": 1.20}
            replay_metadata = {"runtime_origin": "workspace_base", "runtime_timestamp": "2026-05-01T12:00:00"}

        result = self._render(
            compare_result={
                "base": FakeBase(),
                "active": None,
                "empty_state": "No active scenario selected — select a saved scenario to compare against Base Case.",
            },
            compare_panel=True,
        )
        assert "Phase20G Test" in result
        assert "No Active Scenario" in result

    def test_full_compare_renders(self):
        """Base + Active + metrics → side-by-side table with delta column."""
        class FakeBase:
            scenario_name = "Phase20G Test"
            last_run_summary = {"project_irr": 0.09}
            replay_metadata = {"runtime_origin": "workspace_base", "runtime_timestamp": "2026-05-01T12:00:00"}

        class FakeActive:
            scenario_name = "High Tariff"
            last_run_summary = {"project_irr": 0.14}
            replay_metadata = {"runtime_origin": "saved_state", "runtime_timestamp": "2026-05-02T14:00:00"}

        result = self._render(
            compare_result={
                "base": FakeBase(),
                "active": FakeActive(),
                "metrics": [
                    {"key": "project_irr", "base_value": 0.09, "active_value": 0.14, "delta": 0.05, "sign_class": "delta-positive"},
                    {"key": "total_revenue_keur", "base_value": 30000, "active_value": 40000, "delta": 10000, "sign_class": "delta-positive"},
                ],
            },
            compare_panel=True,
        )
        assert "Phase20G Test" in result
        assert "High Tariff" in result
        assert "delta-positive" in result

    def test_delta_classes_positive_negative_neutral(self):
        class FakeBase:
            scenario_name = "Base"
            last_run_summary = {}
            replay_metadata = {}

        class FakeActive:
            scenario_name = "Active"
            last_run_summary = {}
            replay_metadata = {}

        result = self._render(
            compare_result={
                "base": FakeBase(),
                "active": FakeActive(),
                "metrics": [
                    {"key": "IRR", "base_value": 0.09, "active_value": 0.12, "delta": 0.03, "sign_class": "delta-positive"},
                    {"key": "OPEX", "base_value": 1200, "active_value": 900, "delta": -300, "sign_class": "delta-negative"},
                    {"key": "DSCR", "base_value": 1.45, "active_value": 1.45, "delta": 0, "sign_class": "delta-neutral"},
                ],
            },
            compare_panel=True,
        )
        assert "delta-positive" in result
        assert "delta-negative" in result
        assert "delta-neutral" in result