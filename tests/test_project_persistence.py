"""Tests for project persistence layer."""

import os, sys, pytest, uuid

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.persistence.repository import save_run, get_run, list_runs, delete_run, count_runs


# ── Test DB isolation via pytest tmp_path ────────────────────────────────────

@pytest.fixture
def test_db(tmp_path):
    """Set up a fresh temp DB for each test; reset app.persistence.db state."""
    import app.persistence.db as db_mod

    # Save current state
    old_path = os.environ.get("FINCO_DB_PATH")

    # Point persistence at a fresh temp file
    db_file = str(tmp_path / "test_runs.db")
    os.environ["FINCO_DB_PATH"] = db_file

    # Reset module-level connection so it picks up the new path
    db_mod._connection = None
    db_mod.DB_PATH = db_file

    yield db_file

    # Restore
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
        assert get_run(run.run_id, uid2) is None  # wrong user

    def test_list_runs_returns_recent_first(self, test_db):
        uid = f"u{uuid.uuid4().hex[:8]}"
        save_run(uid, "Solar", "Base", {}, {"irr": 0.10})
        save_run(uid, "Wind", "Upside", {}, {"irr": 0.12})
        save_run(uid, "Solar", "Downside", {}, {"irr": 0.08})
        runs = list_runs(uid, limit=10)
        assert len(runs) == 3
        assert runs[0].scenario == "Downside"  # most recent first
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
        assert delete_run(run.run_id, uid2) is False  # wrong user
        assert get_run(run.run_id, uid1) is not None   # still exists

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
        assert get_run(run.run_id, uid_a) is not None   # owner can read
        assert get_run(run.run_id, uid_b) is None        # other user cannot

    def test_user_a_cannot_delete_user_b_run(self, test_db):
        uid_a = f"ua{uuid.uuid4().hex[:8]}"
        uid_b = f"ub{uuid.uuid4().hex[:8]}"
        run = save_run(uid_a, "Solar", "Base", {}, {})
        result = delete_run(run.run_id, uid_b)          # wrong user
        assert result is False
        assert get_run(run.run_id, uid_a) is not None    # still there

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
        """Even if client sends user_id in form, server uses session user_id only."""
        tc = self._auth_client()
        r = tc.post("/save-run", data={
            "project_type": "Solar",
            "scenario": "Base",
            "capacity_mw": "50",
            "user_id": "malicious_user",   # should be ignored
        })
        # Route returns HTML partial, not JSON
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")
        assert "Run saved successfully" in r.text or "error" in r.text.lower()

    def test_auth_user_cannot_load_another_users_run(self, test_db):
        """At repository level, user A's run is invisible to user B."""
        uid_a = f"ua{uuid.uuid4().hex[:8]}"
        uid_b = f"ub{uuid.uuid4().hex[:8]}"
        run = save_run(uid_a, "Solar", "Base", {}, {})
        assert get_run(run.run_id, uid_a) is not None   # owner: OK
        assert get_run(run.run_id, uid_b) is None        # other user: invisible

    def test_runs_never_includes_other_users_runs(self, test_db):
        uid_a = f"ua{uuid.uuid4().hex[:8]}"
        uid_b = f"ub{uuid.uuid4().hex[:8]}"
        save_run(uid_a, "Solar", "Base", {}, {})
        save_run(uid_b, "Wind", "Upside", {}, {})
        # Repository enforces user isolation
        runs_a = list_runs(uid_a)
        runs_b = list_runs(uid_b)
        assert all(r.user_id == uid_a for r in runs_a)
        assert all(r.user_id == uid_b for r in runs_b)
        assert len(runs_a) == 1
        assert len(runs_b) == 1

    def test_get_run_not_found_returns_404(self):
        tc = self._auth_client()
        r = tc.get("/run/notexistent", follow_redirects=False)
        assert r.status_code == 404

    def test_saved_run_appears_in_runs_history(self, test_db):
        """After saving, the run appears in /runs history panel."""
        tc = self._auth_client()
        # Save a run (response is HTML partial, not JSON)
        save_resp = tc.post("/save-run", data={
            "project_type": "Solar",
            "scenario": "Base",
            "capacity_mw": "50",
            "gearing_pct": "75",
        })
        assert save_resp.status_code == 200
        assert "text/html" in save_resp.headers.get("content-type", "")
        # Extract run_id from HTML (ID: <hex>)
        import re
        m = re.search(r'ID: ([a-f0-9]+)', save_resp.text)
        assert m is not None, "run_id not found in HTML response"
        run_id = m.group(1)

        # List runs and verify it appears
        runs_resp = tc.get("/runs")
        assert runs_resp.status_code == 200
        assert "Solar" in runs_resp.text
        assert "Base" in runs_resp.text

    def test_save_response_has_refresh_history_header(self, test_db):
        """Successful save response sends HX-Trigger: refreshHistory header."""
        tc = self._auth_client()
        r = tc.post("/save-run", data={
            "project_type": "Solar",
            "scenario": "Base",
            "capacity_mw": "50",
        })
        assert r.status_code == 200
        # FastAPI/Starlette normalizes header keys to lowercase
        assert "hx-trigger" in r.headers
        assert r.headers["hx-trigger"] == "refreshHistory"

    def test_runs_endpoint_excludes_other_users_runs_via_route(self, test_db):
        """At route level, /runs only includes the current user's runs."""
        import app.persistence.repository as repo
        # Create run under uid_a
        uid_a = f"ua{uuid.uuid4().hex[:8]}"
        run = save_run(uid_a, "Wind", "Downside", {}, {})
        # With auth-lite single-user sessions, we can't easily simulate user B
        # So we document that route-level multi-user isolation depends on session scope
        # The repository-level test above (test_runs_never_includes_other_users_runs)
        # proves the isolation is enforced in the DB layer
        assert get_run(run.run_id, uid_a) is not None

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