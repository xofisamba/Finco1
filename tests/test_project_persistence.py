"""Tests for project persistence layer."""

import os
os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")

import pytest
import uuid
sys_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys
sys.path.insert(0, sys_path)

from app.persistence.repository import save_run, get_run, list_runs, delete_run, count_runs


class TestSaveAndLoad:
    """Unit tests for persistence repository — use unique user IDs for isolation."""

    def test_save_run_returns_record(self):
        uid = f"t_save_{uuid.uuid4().hex[:8]}"
        run = save_run(
            user_id=uid, project_type="Solar", scenario="Base",
            inputs={"capacity_mw": "50", "gearing_pct": "75"},
            kpis={"project_irr": 0.104, "equity_irr": 0.081},
        )
        assert run.run_id is not None
        assert run.user_id == uid
        assert run.project_type == "Solar"
        assert run.scenario == "Base"

    def test_get_run_by_id(self):
        uid = f"t_get_{uuid.uuid4().hex[:8]}"
        run = save_run(uid, "Wind", "Downside", {"capacity_mw": "60"}, {"project_irr": 0.09})
        found = get_run(run.run_id, uid)
        assert found is not None
        assert found.project_type == "Wind"
        assert found.scenario == "Downside"

    def test_get_run_wrong_user_returns_none(self):
        uid1 = f"t_wr1_{uuid.uuid4().hex[:8]}"
        uid2 = f"t_wr2_{uuid.uuid4().hex[:8]}"
        run = save_run(uid1, "Solar", "Base", {}, {"project_irr": 0.10})
        assert get_run(run.run_id, uid2) is None  # different user

    def test_list_runs_returns_recent_first(self):
        uid = f"t_lst_{uuid.uuid4().hex[:8]}"
        save_run(uid, "Solar", "Base", {}, {"project_irr": 0.10})
        save_run(uid, "Wind", "Upside", {}, {"project_irr": 0.12})
        save_run(uid, "Solar", "Downside", {}, {"project_irr": 0.08})
        runs = list_runs(uid, limit=10)
        assert len(runs) == 3
        assert runs[0].scenario == "Downside"   # most recent first
        assert runs[1].scenario == "Upside"
        assert runs[2].scenario == "Base"

    def test_list_runs_user_isolation(self):
        uid1 = f"t_is1_{uuid.uuid4().hex[:8]}"
        uid2 = f"t_is2_{uuid.uuid4().hex[:8]}"
        save_run(uid1, "Solar", "Base", {}, {"project_irr": 0.10})
        save_run(uid2, "Wind", "Base", {}, {"project_irr": 0.09})
        assert len(list_runs(uid1)) == 1
        assert list_runs(uid1)[0].project_type == "Solar"
        assert len(list_runs(uid2)) == 1
        assert list_runs(uid2)[0].project_type == "Wind"

    def test_delete_run(self):
        uid = f"t_del_{uuid.uuid4().hex[:8]}"
        run = save_run(uid, "Solar", "Base", {}, {"project_irr": 0.10})
        assert delete_run(run.run_id, uid) is True
        assert get_run(run.run_id, uid) is None

    def test_delete_run_wrong_user_fails(self):
        uid1 = f"t_dw1_{uuid.uuid4().hex[:8]}"
        uid2 = f"t_dw2_{uuid.uuid4().hex[:8]}"
        run = save_run(uid1, "Solar", "Base", {}, {"project_irr": 0.10})
        assert delete_run(run.run_id, uid2) is False
        assert get_run(run.run_id, uid1) is not None  # still exists

    def test_count_runs(self):
        uid = f"t_cnt_{uuid.uuid4().hex[:8]}"
        before = count_runs(uid)
        save_run(uid, "Solar", "Base", {}, {})
        save_run(uid, "Wind", "Base", {}, {})
        assert count_runs(uid) == before + 2

    def test_run_record_to_dict(self):
        uid = f"t_tod_{uuid.uuid4().hex[:8]}"
        run = save_run(uid, "Solar", "Base", {"gearing": 75}, {"project_irr": 0.10})
        d = run.to_dict()
        assert d["run_id"] == run.run_id
        assert d["project_type"] == "Solar"
        assert d["scenario"] == "Base"
        assert d["inputs"]["gearing"] == 75
        assert d["kpis"]["project_irr"] == 0.10


class TestPersistenceRoutes:
    """Route-level tests using TestClient with auth."""

    def _auth_client(self):
        from fastapi.testclient import TestClient
        from main_web import app
        from app.auth import create_session_token
        tc = TestClient(app)
        tc.cookies.set("finco_session", create_session_token())
        return tc

    def test_save_run_requires_auth(self):
        from fastapi.testclient import TestClient
        from main_web import app
        tc = TestClient(app)
        r = tc.post("/save-run", data={"project_type": "Solar", "scenario": "Base"}, follow_redirects=False)
        assert r.status_code in (302, 401)

    def test_runs_endpoint_requires_auth(self):
        from fastapi.testclient import TestClient
        from main_web import app
        tc = TestClient(app)
        r = tc.get("/runs", follow_redirects=False)
        assert r.status_code in (302, 401)

    def test_get_run_requires_auth(self):
        from fastapi.testclient import TestClient
        from main_web import app
        tc = TestClient(app)
        r = tc.get("/run/abc123", follow_redirects=False)
        assert r.status_code in (302, 401)

    def test_save_run_with_valid_session(self):
        tc = self._auth_client()
        r = tc.post("/save-run", data={"project_type": "Solar", "scenario": "Base", "capacity_mw": "50", "gearing_pct": "75"})
        assert r.status_code == 200
        assert r.json()["status"] == "saved"
        assert "run_id" in r.json()

    def test_list_runs_returns_history(self):
        tc = self._auth_client()
        tc.post("/save-run", data={"project_type": "Wind", "scenario": "Upside", "capacity_mw": "60"})
        r = tc.get("/runs")
        assert r.status_code == 200
        assert "Wind" in r.text or "Upside" in r.text

    def test_load_run_restores_kpis(self):
        tc = self._auth_client()
        save_resp = tc.post("/save-run", data={"project_type": "Solar", "scenario": "Base", "capacity_mw": "50", "gearing_pct": "75"})
        run_id = save_resp.json()["run_id"]
        r = tc.get(f"/run/{run_id}")
        assert r.status_code == 200
        assert "KPI Results" in r.text

    def test_get_run_not_found(self):
        tc = self._auth_client()
        r = tc.get("/run/notexistent_id", follow_redirects=False)
        assert r.status_code == 404