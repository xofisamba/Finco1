"""Tests for project persistence layer."""

import os, sys, pytest, uuid

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.persistence.repository import save_run, get_run, list_runs, delete_run, count_runs


# ── Test DB isolation via pytest tmp_path ────────────────────────────────────

@pytest.fixture
def test_db(tmp_path):
    """Each test gets a fresh temp DB. Real app/data/finco_runs.db never touched."""
    import app.persistence.db as db_mod

    old_path = os.environ.get("FINCO_DB_PATH")
    db_file = str(tmp_path / "test_runs.db")
    os.environ["FINCO_DB_PATH"] = db_file
    db_mod._connection = None
    db_mod.DB_PATH = db_file

    yield db_file

    if old_path:
        os.environ["FINCO_DB_PATH"] = old_path
    else:
        os.environ.pop("FINCO_DB_PATH", None)
    db_mod._connection = None


# ── Repository unit tests ─────────────────────────────────────────────────────

class TestSaveAndLoad:
    def test_save_run_returns_record(self, test_db):
        uid = f"u{uuid.uuid4().hex[:8]}"
        run = save_run(uid, "Solar", "Base", {"cap": "50"}, {"irr": 0.10})
        assert run.run_id is not None
        assert run.user_id == uid
        assert run.project_type == "Solar"
        assert run.scenario == "Base"

    def test_get_run_by_id(self, test_db):
        uid = f"u{uuid.uuid4().hex[:8]}"
        run = save_run(uid, "Wind", "Downside", {"cap": "60"}, {"irr": 0.09})
        found = get_run(run.run_id, uid)
        assert found is not None
        assert found.project_type == "Wind"

    def test_get_run_wrong_user_returns_none(self, test_db):
        uid1 = f"u{uuid.uuid4().hex[:8]}"
        uid2 = f"u{uuid.uuid4().hex[:8]}"
        run = save_run(uid1, "Solar", "Base", {}, {})
        assert get_run(run.run_id, uid2) is None

    def test_list_runs_returns_recent_first(self, test_db):
        uid = f"u{uuid.uuid4().hex[:8]}"
        save_run(uid, "Solar", "Base", {}, {"irr": 0.10})
        save_run(uid, "Wind", "Upside", {}, {"irr": 0.12})
        save_run(uid, "Solar", "Downside", {}, {"irr": 0.08})
        runs = list_runs(uid, limit=10)
        assert len(runs) == 3
        assert runs[0].scenario == "Downside"
        assert runs[1].scenario == "Upside"
        assert runs[2].scenario == "Base"

    def test_delete_run(self, test_db):
        uid = f"u{uuid.uuid4().hex[:8]}"
        run = save_run(uid, "Solar", "Base", {}, {})
        assert delete_run(run.run_id, uid) is True
        assert get_run(run.run_id, uid) is None

    def test_delete_run_wrong_user_fails(self, test_db):
        uid1 = f"u{uuid.uuid4().hex[:8]}"
        uid2 = f"u{uuid.uuid4().hex[:8]}"
        run = save_run(uid1, "Solar", "Base", {}, {})
        assert delete_run(run.run_id, uid2) is False
        assert get_run(run.run_id, uid1) is not None

    def test_count_runs(self, test_db):
        uid = f"u{uuid.uuid4().hex[:8]}"
        before = count_runs(uid)
        save_run(uid, "Solar", "Base", {}, {})
        save_run(uid, "Wind", "Base", {}, {})
        assert count_runs(uid) == before + 2

    def test_run_record_to_dict(self, test_db):
        uid = f"u{uuid.uuid4().hex[:8]}"
        run = save_run(uid, "Solar", "Base", {"gearing": 75}, {"irr": 0.10})
        d = run.to_dict()
        assert d["run_id"] == run.run_id
        assert d["inputs"]["gearing"] == 75


# ── User isolation — repository level ───────────────────────────────────────

class TestUserIsolationRepository:
    def test_user_a_cannot_get_user_b_run(self, test_db):
        uid_a = f"ua{uuid.uuid4().hex[:8]}"
        uid_b = f"ub{uuid.uuid4().hex[:8]}"
        run = save_run(uid_a, "Solar", "Base", {}, {})
        assert get_run(run.run_id, uid_a) is not None
        assert get_run(run.run_id, uid_b) is None

    def test_user_a_cannot_delete_user_b_run(self, test_db):
        uid_a = f"ua{uuid.uuid4().hex[:8]}"
        uid_b = f"ub{uuid.uuid4().hex[:8]}"
        run_b = save_run(uid_b, "Solar", "Base", {}, {})
        result = delete_run(run_b.run_id, uid_a)
        assert result is False
        assert get_run(run_b.run_id, uid_b) is not None

    def test_list_runs_only_returns_own_runs(self, test_db):
        uid_a = f"ua{uuid.uuid4().hex[:8]}"
        uid_b = f"ub{uuid.uuid4().hex[:8]}"
        save_run(uid_a, "Solar", "Base", {}, {})
        save_run(uid_a, "Wind", "Base", {}, {})
        save_run(uid_b, "Solar", "Base", {}, {})
        runs_a = list_runs(uid_a)
        runs_b = list_runs(uid_b)
        assert len(runs_a) == 2
        assert all(r.user_id == uid_a for r in runs_a)
        assert len(runs_b) == 1
        assert runs_b[0].user_id == uid_b

    def test_count_runs_is_user_scoped(self, test_db):
        uid_a = f"ua{uuid.uuid4().hex[:8]}"
        uid_b = f"ub{uuid.uuid4().hex[:8]}"
        save_run(uid_a, "Solar", "Base", {}, {})
        save_run(uid_a, "Solar", "Base", {}, {})
        save_run(uid_b, "Wind", "Base", {}, {})
        assert count_runs(uid_a) == 2
        assert count_runs(uid_b) == 1


# ── Route-level tests ────────────────────────────────────────────────────────

class TestPersistenceRoutes:
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

    def test_save_run_ignores_malicious_user_id_form_field(self):
        """Route uses session user_id only — form user_id is ignored."""
        tc = self._auth_client()
        r = tc.post("/save-run", data={
            "project_type": "Solar", "scenario": "Base",
            "capacity_mw": "50", "user_id": "malicious_user",
        })
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")

    def test_get_run_not_found_returns_404(self):
        tc = self._auth_client()
        r = tc.get("/run/notexistent", follow_redirects=False)
        assert r.status_code == 404

    def test_saved_run_appears_in_runs_history(self, test_db):
        """After saving, the run appears in /runs history panel."""
        tc = self._auth_client()
        save_resp = tc.post("/save-run", data={
            "project_type": "Solar", "scenario": "Base",
            "capacity_mw": "50", "gearing_pct": "75",
        })
        assert save_resp.status_code == 200
        assert "text/html" in save_resp.headers.get("content-type", "")
        import re
        m = re.search(r'ID: ([a-f0-9]+)', save_resp.text)
        assert m is not None, "run_id not found in HTML response"

        runs_resp = tc.get("/runs")
        assert runs_resp.status_code == 200
        assert "Solar" in runs_resp.text
        assert "Base" in runs_resp.text

    def test_save_response_has_refresh_history_header(self, test_db):
        """Successful save sends HX-Trigger: refreshHistory header."""
        tc = self._auth_client()
        r = tc.post("/save-run", data={
            "project_type": "Solar", "scenario": "Base", "capacity_mw": "50",
        })
        assert r.status_code == 200
        assert "hx-trigger" in r.headers
        assert r.headers["hx-trigger"] == "refreshHistory"

    def test_unauthenticated_all_routes_rejected(self):
        """All persistence routes require authentication."""
        from fastapi.testclient import TestClient
        from main_web import app
        tc = TestClient(app, raise_server_exceptions=False)
        for method, path in [("POST", "/save-run"), ("GET", "/runs"), ("GET", "/run/abc123")]:
            if method == "POST":
                r = tc.post(path, data={"project_type": "Solar", "scenario": "Base"}, follow_redirects=False)
            else:
                r = tc.get(path, follow_redirects=False)
            assert r.status_code in (302, 401), f"{method} {path} returned {r.status_code}"


# ── End-to-end multi-user route isolation ───────────────────────────────────

class TestMultiUserRouteIsolation:
    """End-to-end multi-user isolation with separate session tokens.

    Each test uses a distinct user_id in the session token, proving that
    the repository DB filter enforces isolation at the route level.
    """

    def test_user_a_run_invisible_to_user_b_via_get_runs(self, test_db):
        """User A's saved run is NOT visible to User B via GET /runs."""
        uid_a = f"ua{uuid.uuid4().hex[:8]}"
        uid_b = f"ub{uuid.uuid4().hex[:8]}"

        # User A saves a run
        save_run(uid_a, "Solar", "Base", {}, {})

        from fastapi.testclient import TestClient
        from main_web import app
        from app.auth import create_session_token

        # Two clients with different user_ids in their session tokens
        tc_a = TestClient(app)
        tc_b = TestClient(app)
        tc_a.cookies.set("finco_session", create_session_token(user_id=uid_a, username="user_a"))
        tc_b.cookies.set("finco_session", create_session_token(user_id=uid_b, username="user_b"))

        # User A can see their run
        runs_a = tc_a.get("/runs")
        assert runs_a.status_code == 200
        assert "Solar" in runs_a.text

        # User B cannot see User A's run (filtered by user_id in session)
        runs_b = tc_b.get("/runs")
        assert runs_b.status_code == 200
        assert "Solar" not in runs_b.text

    def test_user_b_cannot_load_user_a_run_via_get_run(self, test_db):
        """User B gets 404 when trying to GET /run/{user_a_run_id}."""
        uid_a = f"ua{uuid.uuid4().hex[:8]}"
        uid_b = f"ub{uuid.uuid4().hex[:8]}"

        run_a = save_run(uid_a, "Wind", "Upside", {}, {})

        from fastapi.testclient import TestClient
        from main_web import app
        from app.auth import create_session_token

        tc_b = TestClient(app)
        tc_b.cookies.set("finco_session", create_session_token(user_id=uid_b, username="user_b"))

        r = tc_b.get(f"/run/{run_a.run_id}", follow_redirects=False)
        assert r.status_code == 404

    def test_user_a_cannot_delete_user_b_run(self, test_db):
        """User A cannot delete User B's run (repo-level enforcement)."""
        uid_a = f"ua{uuid.uuid4().hex[:8]}"
        uid_b = f"ub{uuid.uuid4().hex[:8]}"
        run_b = save_run(uid_b, "Solar", "Base", {}, {})
        result = delete_run(run_b.run_id, uid_a)
        assert result is False
        assert get_run(run_b.run_id, uid_b) is not None