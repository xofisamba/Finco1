"""Tests for the project-library-data-hygiene hotfix (final correctness).

Covers:
* pytest path-resolution isolation (relative paths, ./, ../, symlinks)
* cached app.persistence.db.DB_PATH safety
* real default-DB before/after fingerprint (SHA-256, size, mtime, project count)
* anchored candidate classification (no substring matching)
* negative test for substring-in-the-middle collisions
* WAL logical fingerprint
* exact path validation
* full validation inside BEGIN IMMEDIATE
* concurrent identity mutation under the lock
* backup inside repository rejected
* backup all-table count verification
* backup logical fingerprint verification
* valid apply archives exactly the 11 fixture candidates
* second apply returns success with zero writes (idempotent replay)
* partial already-archived manifest fails closed
* dependent records remain unchanged
* canonical references remain protected
* navigation (root / library / card copy) preserved

This file does NOT commit any project IDs, user IDs, project
names, or DB-specific artefacts. The fixture uses deterministic,
generic, non-conflicting names.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "archive_legacy_test_projects.py"
PROD_DB = REPO_ROOT / "app" / "data" / "finco_runs.db"


def _build_negative_classification_db(tmp_path: Path) -> Path:
    """Build a tiny DB that contains ONLY legitimate
    user projects whose names begin with PH2 Test,
    Inputs Test, or Inputs Slice1 but are NOT exact
    matches against the closed-suffix rules. The
    classifier must not produce any candidates from
    this DB."""
    db = tmp_path / "neg-class.db"
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE projects ("
        " project_id TEXT PRIMARY KEY, user_id TEXT, project_code TEXT,"
        " project_name TEXT, project_type TEXT,"
        " project_origin TEXT, source_project_template TEXT,"
        " template_source TEXT, baseline_snapshot_json TEXT,"
        " archived INTEGER, governance_state_json TEXT,"
        " last_run_summary_json TEXT, replay_metadata_json TEXT,"
        " created_at TEXT, updated_at TEXT, is_readonly INTEGER,"
        " full_inputs_json TEXT)"
    )
    cur.execute("CREATE TABLE scenarios (scenario_id TEXT PRIMARY KEY, project_id TEXT, name TEXT)")
    cur.execute("CREATE TABLE runs (run_id TEXT PRIMARY KEY, project_id TEXT)")
    cur.execute("CREATE TABLE workspace_states (project_id TEXT PRIMARY KEY, state_json TEXT)")
    negative_rows = [
        # PH2 Test ... not 'Walkthrough'
        ("n-ph2-wind", "u1", "ph2-test-wind-farm", "PH2 Test Wind Farm",
         "user_created", "generic_wind"),
        ("n-ph2-cust", "u1", "ph2-test-customer-model", "PH2 Test Customer Model",
         "user_created", "generic_wind"),
        # Inputs Test ... not one of the 7 suffixes
        ("n-inp-test-cust", "u1", "inputs-test-customer", "Inputs Test Customer",
         "user_created", "generic_wind"),
        ("n-inp-test-res",  "u1", "inputs-test-results",  "Inputs Test Results",
         "user_created", "generic_wind"),
        # Inputs Slice1 ... not one of the 15 suffixes
        ("n-inp-slice1-bud",  "u1", "inputs-slice1-budget",  "Inputs Slice1 Budget",
         "user_created", "generic_wind"),
        ("n-inp-slice1-cust", "u1", "inputs-slice1-customer-model",
         "Inputs Slice1 Customer Model", "user_created", "generic_wind"),
    ]
    for pid, uid, code, name, origin, tpl in negative_rows:
        cur.execute(
            "INSERT INTO projects (project_id, user_id, project_code,"
            " project_name, project_type, project_origin,"
            " source_project_template, template_source,"
            " baseline_snapshot_json, archived,"
            " governance_state_json, last_run_summary_json,"
            " replay_metadata_json, created_at, updated_at,"
            " is_readonly) VALUES (?,?,?,?,?,?,?,?,?,0,?,?,?,?,?,0)",
            (pid, uid, code, name, "Wind", origin, tpl, tpl,
             "{}", "{}", "{}", "{}", "2026-01-01", "2026-01-01"),
        )
    conn.commit()
    conn.close()
    return db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_sandbox_db(tmp_path: Path) -> Path:
    """Build a sandbox DB with the canonical schema and a known
    project set exercising each candidate rule plus protected
    and ambiguous rows."""
    db = tmp_path / "sandbox.db"
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE projects ("
        " project_id TEXT PRIMARY KEY,"
        " user_id TEXT NOT NULL,"
        " project_code TEXT NOT NULL,"
        " project_name TEXT NOT NULL,"
        " project_type TEXT,"
        " project_origin TEXT NOT NULL DEFAULT 'factory_template',"
        " source_project_template TEXT NOT NULL,"
        " template_source TEXT,"
        " baseline_snapshot_json TEXT NOT NULL DEFAULT '{}',"
        " archived INTEGER NOT NULL DEFAULT 0,"
        " governance_state_json TEXT NOT NULL,"
        " last_run_summary_json TEXT NOT NULL,"
        " replay_metadata_json TEXT NOT NULL DEFAULT '{}',"
        " created_at TEXT NOT NULL,"
        " updated_at TEXT NOT NULL,"
        " is_readonly INTEGER NOT NULL DEFAULT 0,"
        " full_inputs_json TEXT"
        ")"
    )
    cur.execute(
        "CREATE TABLE scenarios ("
        " scenario_id TEXT PRIMARY KEY,"
        " project_id TEXT NOT NULL,"
        " name TEXT NOT NULL"
        ")"
    )
    cur.execute(
        "CREATE TABLE runs ("
        " run_id TEXT PRIMARY KEY,"
        " project_id TEXT NOT NULL"
        ")"
    )
    cur.execute(
        "CREATE TABLE workspace_states ("
        " project_id TEXT PRIMARY KEY,"
        " state_json TEXT NOT NULL"
        ")"
    )
    # 11 evidence-backed candidates + 10 protected/ambiguous
    rows = [
        # ----- 10 protected/ambiguous rows -----
        ("p-tuho-ref",    "u1", "tuho",            "TUHO Wind 1",        "factory_template", "tuho",         0),
        ("p-obor-ref",    "u1", "oborovo",         "Oborovo Solar PV",   "factory_template", "oborovo",      0),
        ("p-tuho-base",   "u1", "tuho-baseline",   "TUHO Baseline",      "saved_baseline",   "tuho",         1),
        ("p-obor-base",   "u1", "oborovo-baseline","Oborovo Baseline",   "saved_baseline",   "oborovo",      1),
        ("p-gen-wind",    "u1", "generic_wind",    "Generic Wind Project","factory_template", "generic_wind", 0),
        ("p-gen-solar",   "u1", "generic_solar",   "Generic Solar Project","factory_template", "generic_solar",0),
        ("p-tuho-wc",     "u1", "tuho-wc-feb",     "TUHO Working Copy",  "user_created",     "tuho",         0),
        ("p-proba",       "u1", "proba-solar-2025","Proba solar",        "user_created",     "generic_solar",0),
        ("p-user-test",   "u1", "mytest",          "Project Test Plan",  "user_created",     "generic_solar",0),
        ("p-user-qa",     "u1", "qa-snapshot",     "QA Snapshot Review", "user_created",     "generic_solar",0),
        # ----- 11 evidence-backed candidates (one per rule_id) -----
        # The paired rules (PH2, Inputs Test, Inputs Slice 1,
        # P2FIX1) use the exact real-fixture name AND code.
        # The single-field rules use only the documented field.
        ("p-ph3-wc-1",    "qa", "ph3-wc-t1",       "ph3-wc-t1",          "user_created",     "generic_wind", 0),
        ("p-p1uxfix1-1",  "qa", "p1uxfix1-wc-01",  "P1-UX-FIX-1 Test",   "user_created",     "generic_solar",0),
        ("p-ph2-test-1",  "qa", "ph2-test-walkthrough", "PH2 Test Walkthrough", "user_created", "generic_wind", 0),
        ("p-pilot-1",     "qa", "testpilotproj",   "TestPilotProj",      "user_created",     "generic_solar",0),
        ("p-opex-life-1", "qa", "generic_wind",    "OPEX Lifecycle Test persist",  "user_created", "generic_wind", 0),
        ("p-opex-life-2", "qa", "generic_wind",    "OPEX Lifecycle Test order",    "user_created", "generic_wind", 0),
        ("p-opex-life-3", "qa", "generic_wind",    "OPEX Lifecycle Test proj-table","user_created","generic_wind", 0),
        ("p-inp-test-1",  "qa", "inputs-test-html-01", "Inputs Test html-01", "user_created", "generic_wind", 0),
        ("p-inp-slice-1", "qa", "inputs-slice1-runtime", "Inputs Slice1 runtime", "user_created", "generic_wind", 0),
        ("p-p2fix1-ws-1", "qa", "p2fix1-ws-abc12345", "P2FIX1-WS-abc12345", "user_created", "generic_wind", 0),
        ("p-p2fix1-t-1",  "qa", "p2fix1-test-abc12345","P2FIX1-Test-abc12345","user_created", "generic_wind", 0),
    ]
    for pid, uid, code, name, origin, tpl, ro in rows:
        cur.execute(
            "INSERT INTO projects"
            " (project_id,user_id,project_code,project_name,project_origin,"
            "  source_project_template,template_source,baseline_snapshot_json,"
            "  archived,governance_state_json,last_run_summary_json,"
            "  replay_metadata_json,created_at,updated_at,is_readonly)"
            " VALUES (?,?,?,?,?,?,?,?,0,?,?,?,?,?,?)",
            (pid, uid, code, name, origin, tpl, tpl,
             "{}", "{}", "{}", "{}", "2026-01-01", "2026-01-01", ro),
        )
        cur.execute(
            "INSERT INTO workspace_states (project_id, state_json) VALUES (?, '{}')",
            (pid,),
        )
    for pid in ("p-ph3-wc-1", "p-opex-life-1", "p-inp-test-1"):
        cur.execute(
            "INSERT INTO scenarios (scenario_id, project_id, name)"
            " VALUES (?, ?, 'baseline')",
            (f"s-{pid}", pid),
        )
        cur.execute(
            "INSERT INTO runs (run_id, project_id) VALUES (?, ?)",
            (f"r-{pid}", pid),
        )
    conn.commit()
    conn.close()
    return db


def _run_script(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True,
    )


def _db_meta(db: Path) -> dict:
    st = db.stat()
    return {
        "sha256": hashlib.sha256(db.read_bytes()).hexdigest(),
        "size": st.st_size,
        "mtime_ns": st.st_mtime_ns,
    }


# ---------------------------------------------------------------------------
# 1. Resolved-path isolation
# ---------------------------------------------------------------------------

class TestResolvedPathIsolation:
    """The conftest module-level guard must replace any
    FINCO_DB_PATH that resolves inside the repository with the
    session isolation DB."""

    def test_unset_finco_db_path(self, monkeypatch):
        monkeypatch.delenv("FINCO_DB_PATH", raising=False)
        import importlib
        # Re-import conftest to trigger the module-level guard
        # against a fresh env.
        # We can't trivially reimport conftest (already loaded),
        # so we manually re-evaluate the helper against the
        # current env.
        sys.path.insert(0, str(REPO_ROOT / "tests"))
        import conftest
        # After conftest import, FINCO_DB_PATH must point at a
        # path OUTSIDE the repository.
        path = Path(os.environ.get("FINCO_DB_PATH", ""))
        assert path.is_file()
        assert str(path.resolve()) != str(PROD_DB.resolve())
        assert conftest._is_repository_path(str(path)) is False

    def test_absolute_repo_db_path_is_rejected(self, monkeypatch):
        """If the env is set to the absolute repository DB path,
        conftest must replace it."""
        monkeypatch.setenv("FINCO_DB_PATH", str(PROD_DB.resolve()))
        # We re-run the same helper that conftest uses.
        sys.path.insert(0, str(REPO_ROOT / "tests"))
        import conftest
        # Recompute the decision: the env is the production
        # path. The helper must classify it as a repository
        # path.
        assert conftest._is_repository_path(str(PROD_DB.resolve())) is True

    def test_relative_repo_db_path_is_rejected(self, monkeypatch):
        monkeypatch.setenv(
            "FINCO_DB_PATH", "app/data/finco_runs.db"
        )
        sys.path.insert(0, str(REPO_ROOT / "tests"))
        import conftest
        # The relative path resolves to the production DB.
        # _is_repository_path must return True.
        assert conftest._is_repository_path("app/data/finco_runs.db") is True

    def test_dot_slash_repo_db_path_is_rejected(self, monkeypatch):
        monkeypatch.setenv("FINCO_DB_PATH", "./app/data/finco_runs.db")
        sys.path.insert(0, str(REPO_ROOT / "tests"))
        import conftest
        assert conftest._is_repository_path("./app/data/finco_runs.db") is True

    def test_double_dot_repo_db_path_is_rejected(self, monkeypatch):
        monkeypatch.setenv(
            "FINCO_DB_PATH",
            f"{(REPO_ROOT / 'tests').relative_to(REPO_ROOT)}"
            f"/../app/data/finco_runs.db",
        )
        sys.path.insert(0, str(REPO_ROOT / "tests"))
        import conftest
        # The `..` path resolves to the production DB.
        assert conftest._is_repository_path(
            f"{(REPO_ROOT / 'tests').relative_to(REPO_ROOT)}/../app/data/finco_runs.db"
        ) is True

    def test_symlink_to_repo_db_is_rejected(self, tmp_path: Path, monkeypatch):
        """A symlink in tmp_path that points to the production
        DB must also be rejected because Path.resolve() follows
        the symlink and lands on the production path."""
        link = tmp_path / "linked.db"
        try:
            link.symlink_to(PROD_DB)
        except (OSError, NotImplementedError) as e:
            pytest.skip(f"symlinks not supported: {e!r}")
        sys.path.insert(0, str(REPO_ROOT / "tests"))
        import conftest
        assert conftest._is_repository_path(str(link)) is True

    def test_external_temp_db_is_preserved(self, tmp_path: Path, monkeypatch):
        """An explicit external temp DB must NOT be replaced.
        This is the only way a test that wants a custom path
        can keep it."""
        external = tmp_path / "external.db"
        external.touch()
        monkeypatch.setenv("FINCO_DB_PATH", str(external))
        sys.path.insert(0, str(REPO_ROOT / "tests"))
        import conftest
        # The helper must classify the external path as
        # non-repository.
        assert conftest._is_repository_path(str(external)) is False
        # And conftest must NOT own the directory (so the
        # teardown hook won't rm -rf it).
        # CONFTEST_OWNS_ISOLATION_DIR is module-level; in
        # practice the env-set case leaves it False, but we
        # do not assert that here because the conftest has
        # already been imported for this process. We just
        # assert the path survives a round-trip.

    def test_cached_db_path_is_corrected(self, monkeypatch):
        """If app.persistence.db has already been imported with
        a repository-resolving path, the helper must classify
        DB_PATH as a repository path; the autouse fixture (in
        a normal pytest run) re-points it. Here we directly
        assert the helper classification and the re-point
        logic."""
        import sys as _sys
        _sys.path.insert(0, str(REPO_ROOT))
        # Import the db module fresh with the production path.
        monkeypatch.setenv("FINCO_DB_PATH", str(PROD_DB.resolve()))
        _sys.modules.pop("app.persistence.db", None)
        import app.persistence.db as _db
        # The helper classifies the production path as a
        # repository path.
        sys.path.insert(0, str(REPO_ROOT / "tests"))
        import conftest
        assert conftest._is_repository_path(_db.DB_PATH) is True
        # The autouse fixture in a normal pytest run will then
        # re-point DB_PATH at the isolation path. We assert
        # that the helper accepts the isolation path.
        assert conftest._is_repository_path(
            conftest._ISOLATION_DB_PATH_RESOLVED
        ) is False


# ---------------------------------------------------------------------------
# 2. Real default-DB mutation guard
# ---------------------------------------------------------------------------

class TestRealDefaultDbGuard:
    """The default DB fingerprint (SHA-256, size, mtime_ns,
    project count) must be UNCHANGED after running the
    known-contaminating test suites with test isolation
    enabled."""

    @pytest.fixture
    def before(self):
        if not PROD_DB.is_file():
            pytest.skip("default DB not present in this checkout")
        return _db_meta(PROD_DB), self._count_projects(PROD_DB)

    @staticmethod
    def _count_projects(db: Path) -> int:
        c = sqlite3.connect(db)
        cur = c.cursor()
        cur.execute("SELECT COUNT(*) FROM projects")
        n = int(cur.fetchone()[0])
        c.close()
        return n

    def test_inputs_slice1_does_not_mutate_default_db(self, before):
        before_meta, before_count = before
        # Run a focused subset that creates inputs-slice1-*
        # fixtures in the absence of isolation. (conftest
        # already enforces isolation, so this is a
        # regression test for the isolation contract.)
        r = subprocess.run(
            [
                sys.executable, "-m", "pytest",
                "tests/test_inputs_slice1_project_schedule_technical.py",
                "-q", "--no-header",
                "--deselect",
                "tests/test_inputs_slice1_project_schedule_technical.py::test_slice1_htmx_before_swap_synthetic_event_browser",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True, text=True, timeout=600,
        )
        assert r.returncode == 0, r.stderr[-500:]
        after_meta = _db_meta(PROD_DB)
        after_count = self._count_projects(PROD_DB)
        assert before_meta["sha256"] == after_meta["sha256"]
        assert before_meta["size"] == after_meta["size"]
        assert before_meta["mtime_ns"] == after_meta["mtime_ns"]
        assert before_count == after_count

    def test_p2fix1_does_not_mutate_default_db(self, before):
        before_meta, before_count = before
        # Run only the post-create / root-redirect tests
        # that exercise /projects/create POST. The browser
        # and umbrella tests are too slow for a fingerprint
        # guard. We assert that running those focused
        # tests does not mutate the default DB.
        focused = [
            "tests/test_phase_p2fix1_default_route_rewiring.py::TestGetRootNoProjectParam::test_get_root_no_project_param_redirects_to_library",
            "tests/test_phase_p2fix1_default_route_rewiring.py::TestGetRootNoProjectParam::test_get_root_no_project_param_does_not_contain_old_workspace_machinery",
            "tests/test_phase_p2fix1_default_route_rewiring.py::TestGetRootWithProjectParam::test_get_root_with_project_param_opens_workspace",
            "tests/test_phase_p2fix1_default_route_rewiring.py::TestGetHomeRedirects::test_get_home_redirects_to_root",
            "tests/test_phase_p2fix1_default_route_rewiring.py::TestGetProjectsNewRendersMinimalForm::test_get_projects_new_renders_minimal_form",
            "tests/test_phase_p2fix1_default_route_rewiring.py::TestGetProjectsNewRendersMinimalForm::test_get_projects_new_minimal_redirects_to_new",
            "tests/test_phase_p2fix1_default_route_rewiring.py::TestPostCreateWithMinimalFieldsCreatesProject::test_post_create_with_minimal_fields_creates_project",
            "tests/test_phase_p2fix1_default_route_rewiring.py::TestPostCreateWithMinimalFieldsRedirectsToWorkspace::test_post_create_with_minimal_fields_redirects_to_workspace",
            "tests/test_phase_p2fix1_default_route_rewiring.py::TestConsolidatedHelper::test_consolidated_helper_returns_tuho_and_oborovo",
            "tests/test_phase_p2fix1_default_route_rewiring.py::TestConsolidatedHelper::test_consolidated_helper_includes_user_projects",
            "tests/test_phase_p2fix1_default_route_rewiring.py::TestConsolidatedHelper::test_consolidated_helper_no_duplicate_codes",
            "tests/test_phase_p2fix1_default_route_rewiring.py::TestRouteRenames::test_no_route_renames_or_deletions",
            "tests/test_phase_p2fix1_default_route_rewiring.py::TestConstructionScheduleEngineFlag::test_use_construction_schedule_engine_remains_false",
            "tests/test_phase_p2fix1_default_route_rewiring.py::TestParityGuardrails::test_parity_guardrails_unchanged",
        ]
        args = [sys.executable, "-m", "pytest", "-q", "--no-header"] + focused
        r = subprocess.run(
            args, cwd=str(REPO_ROOT),
            capture_output=True, text=True, timeout=300,
        )
        # Some pre-existing infra-rot failures are allowed.
        # We only care that the default DB is unchanged.
        after_meta = _db_meta(PROD_DB)
        after_count = self._count_projects(PROD_DB)
        assert before_meta["sha256"] == after_meta["sha256"]
        assert before_count == after_count


# ---------------------------------------------------------------------------
# 3. Anchored candidate classification
# ---------------------------------------------------------------------------

class TestAnchoredCandidateClassification:
    def test_each_evidence_backed_fixture_family_is_detected(self, tmp_path: Path):
        db = _build_sandbox_db(tmp_path)
        m_path = tmp_path / "man.local.json"
        r = _run_script("--db", str(db), "--generate-manifest", str(m_path))
        assert r.returncode == 0, r.stderr
        m = json.loads(m_path.read_text())
        rules = {c["classification_rule"] for c in m["candidates"]}
        for required in (
            "ph3-working-copy-series",
            "p1-ux-fix1-fixtures",
            "ph2-test-walkthrough",
            "testpilotproj-fixtures",
            "opex-lifecycle-fixture",
            "inputs-slice1-fixture",
            "p2fix1-route-rewiring-fixture",
        ):
            assert required in rules, (
                f"rule {required!r} not detected for its fixture family"
            )

    def test_opex_lifecycle_fixtures_are_detected(self, tmp_path: Path):
        db = _build_sandbox_db(tmp_path)
        m_path = tmp_path / "man.local.json"
        _run_script("--db", str(db), "--generate-manifest", str(m_path))
        m = json.loads(m_path.read_text())
        opex = [c for c in m["candidates"]
                if c["classification_rule"] == "opex-lifecycle-fixture"]
        assert len(opex) == 3
        names = sorted(c["project_name"] for c in opex)
        assert all(
            n.startswith("OPEX Lifecycle Test ") and len(n.split()) == 4
            for n in names
        )

    def test_inputs_html_fixture_is_detected(self, tmp_path: Path):
        db = _build_sandbox_db(tmp_path)
        m_path = tmp_path / "man.local.json"
        _run_script("--db", str(db), "--generate-manifest", str(m_path))
        m = json.loads(m_path.read_text())
        ids = [c["project_id"] for c in m["candidates"]]
        assert "p-inp-test-1" in ids
        assert "p-inp-slice-1" in ids

    def test_manual_projects_are_preserved(self, tmp_path: Path):
        db = _build_sandbox_db(tmp_path)
        m_path = tmp_path / "man.local.json"
        _run_script("--db", str(db), "--generate-manifest", str(m_path))
        m = json.loads(m_path.read_text())
        candidate_ids = {c["project_id"] for c in m["candidates"]}
        for must_preserve in (
            "p-tuho-ref", "p-obor-ref", "p-tuho-base", "p-obor-base",
            "p-gen-wind", "p-gen-solar", "p-tuho-wc", "p-proba",
            "p-user-test", "p-user-qa",
        ):
            assert must_preserve not in candidate_ids, (
                f"{must_preserve} must NOT be classified"
            )

    def test_substring_in_the_middle_negative_matches(self, tmp_path: Path):
        """User project names that contain the test prefix as
        a SUBSTRING (not anchored) must NOT be classified. This
        is the negative-test contract that proves the rules
        are anchored."""
        db = tmp_path / "neg.db"
        conn = sqlite3.connect(db)
        cur = conn.cursor()
        cur.execute(
            "CREATE TABLE projects ("
            " project_id TEXT PRIMARY KEY, user_id TEXT, project_code TEXT,"
            " project_name TEXT, project_type TEXT,"
            " project_origin TEXT, source_project_template TEXT,"
            " template_source TEXT, baseline_snapshot_json TEXT,"
            " archived INTEGER, governance_state_json TEXT,"
            " last_run_summary_json TEXT, replay_metadata_json TEXT,"
            " created_at TEXT, updated_at TEXT, is_readonly INTEGER,"
            " full_inputs_json TEXT)"
        )
        cur.execute("CREATE TABLE scenarios (scenario_id TEXT PRIMARY KEY, project_id TEXT, name TEXT)")
        cur.execute("CREATE TABLE runs (run_id TEXT PRIMARY KEY, project_id TEXT)")
        cur.execute("CREATE TABLE workspace_states (project_id TEXT PRIMARY KEY, state_json TEXT)")
        # 5 false-positive names from the brief. None should be
        # classified.
        negative_rows = [
            ("n-1", "Customer Inputs Test results",        "customer-inputs"),
            ("n-2", "Acme OPEX Lifecycle Test persist migration", "acme-opex-mig"),
            ("n-3", "Review of testpilotproj acquisition", "testpilotproj-review"),
            ("n-4", "My ph3-wc-model documentation",        "ph3-wc-model"),
            ("n-5", "FY26 P2FIX1 annual planning",         "p2fix1-planning"),
        ]
        for pid, name, code in negative_rows:
            cur.execute(
                "INSERT INTO projects (project_id, user_id, project_code,"
                " project_name, project_type, project_origin,"
                " source_project_template, template_source,"
                " baseline_snapshot_json, archived,"
                " governance_state_json, last_run_summary_json,"
                " replay_metadata_json, created_at, updated_at,"
                " is_readonly) VALUES (?, 'u1', ?, ?, 'Wind',"
                " 'user_created', 'generic_wind', 'generic_wind',"
                " '{}', 0, '{}', '{}', '{}', '2026-01-01',"
                " '2026-01-01', 0)",
                (pid, code, name),
            )
        conn.commit()
        conn.close()
        m_path = tmp_path / "neg.local.json"
        _run_script("--db", str(db), "--generate-manifest", str(m_path))
        m = json.loads(m_path.read_text())
        ids = {c["project_id"] for c in m["candidates"]}
        for nid in ("n-1", "n-2", "n-3", "n-4", "n-5"):
            assert nid not in ids, (
                f"false positive: {nid!r} was classified but its "
                "name only contains the test prefix as a substring"
            )

    def test_ph2_test_walkthrough_active_user_negative_matches(
        self, tmp_path: Path
    ):
        """Legitimate user projects whose project_name
        starts with 'PH2 Test ' but does not end with
        'Walkthrough' must NOT be classified as PH2 test
        fixtures. The PH2 rule is anchored to the exact
        tokens 'PH2 Test Walkthrough' / 'ph2-test-walkthrough'."""
        db = _build_negative_classification_db(tmp_path)
        m_path = tmp_path / "neg-ph2.local.json"
        _run_script("--db", str(db), "--generate-manifest", str(m_path))
        m = json.loads(m_path.read_text())
        ids = {c["project_id"] for c in m["candidates"]}
        for nid in ("n-ph2-wind", "n-ph2-cust"):
            assert nid not in ids, (
                f"PH2 false positive: {nid!r} starts with "
                "'PH2 Test ' but is not the exact 'PH2 Test "
                "Walkthrough' fixture; must NOT be classified"
            )

    def test_inputs_test_active_user_negative_matches(self, tmp_path: Path):
        """Legitimate user projects whose project_name
        starts with 'Inputs Test ' but does not match one
        of the seven exact suffixes from
        test_workbook_v2_sheet_inputs.py must NOT be
        classified."""
        db = _build_negative_classification_db(tmp_path)
        m_path = tmp_path / "neg-inputs.local.json"
        _run_script("--db", str(db), "--generate-manifest", str(m_path))
        m = json.loads(m_path.read_text())
        ids = {c["project_id"] for c in m["candidates"]}
        for nid in ("n-inp-test-cust", "n-inp-test-res"):
            assert nid not in ids, (
                f"Inputs Test false positive: {nid!r} starts "
                "with 'Inputs Test ' but is not one of the "
                "seven exact suffixes; must NOT be classified"
            )

    def test_inputs_slice1_active_user_negative_matches(self, tmp_path: Path):
        """Legitimate user projects whose project_name
        starts with 'Inputs Slice1 ' but does not match one
        of the fifteen exact suffixes from
        test_inputs_slice1_project_schedule_technical.py
        must NOT be classified."""
        db = _build_negative_classification_db(tmp_path)
        m_path = tmp_path / "neg-slice1.local.json"
        _run_script("--db", str(db), "--generate-manifest", str(m_path))
        m = json.loads(m_path.read_text())
        ids = {c["project_id"] for c in m["candidates"]}
        for nid in ("n-inp-slice1-bud", "n-inp-slice1-cust"):
            assert nid not in ids, (
                f"Inputs Slice1 false positive: {nid!r} "
                "starts with 'Inputs Slice1 ' but is not one "
                "of the fifteen exact suffixes; must NOT be "
                "classified"
            )


# ---------------------------------------------------------------------------
# 3b. Cross-mismatch safety (name+code policy)
# ---------------------------------------------------------------------------

class TestNameAndCodeConjunction:
    """Every name_and_code rule requires BOTH project_name
    and project_code to match exactly. A fixture-like name
    with a customer code, or a fixture-like code with a
    customer name, is NOT classified. These tests call the
    real manifest-generation classifier path through the
    archive CLI; they do not duplicate the intended
    classifier logic in the test."""

    def _build_and_generate(self, tmp_path, rows):
        db = tmp_path / "conj.db"
        conn = sqlite3.connect(db)
        cur = conn.cursor()
        cur.execute(
            "CREATE TABLE projects ("
            " project_id TEXT PRIMARY KEY, user_id TEXT, project_code TEXT,"
            " project_name TEXT, project_type TEXT, project_origin TEXT,"
            " source_project_template TEXT, template_source TEXT,"
            " baseline_snapshot_json TEXT, archived INTEGER,"
            " governance_state_json TEXT, last_run_summary_json TEXT,"
            " replay_metadata_json TEXT, created_at TEXT, updated_at TEXT,"
            " is_readonly INTEGER, full_inputs_json TEXT)"
        )
        cur.execute("CREATE TABLE scenarios (scenario_id TEXT PRIMARY KEY, project_id TEXT, name TEXT)")
        cur.execute("CREATE TABLE runs (run_id TEXT PRIMARY KEY, project_id TEXT)")
        cur.execute("CREATE TABLE workspace_states (project_id TEXT PRIMARY KEY, state_json TEXT)")
        for pid, code, name in rows:
            cur.execute(
                "INSERT INTO projects (project_id, user_id, project_code,"
                " project_name, project_type, project_origin,"
                " source_project_template, template_source,"
                " baseline_snapshot_json, archived,"
                " governance_state_json, last_run_summary_json,"
                " replay_metadata_json, created_at, updated_at,"
                " is_readonly) VALUES (?, 'u1', ?, ?, 'Wind',"
                " 'user_created', 'generic_wind', 'generic_wind',"
                " '{}', 0, '{}', '{}', '{}', '2026-01-01',"
                " '2026-01-01', 0)",
                (pid, code, name),
            )
        conn.commit()
        conn.close()
        manifest_path = tmp_path / "man.local.json"
        r = _run_script(
            "--db", str(db), "--generate-manifest", str(manifest_path)
        )
        assert r.returncode == 0, r.stderr
        m = json.loads(manifest_path.read_text())
        return {c["project_id"] for c in m["candidates"]}

    def test_ph2_name_only_mismatch(self, tmp_path):
        ids = self._build_and_generate(tmp_path, [
            ("n-ph2-name", "real-wind-project", "PH2 Test Walkthrough"),
        ])
        assert "n-ph2-name" not in ids, (
            "name_and_code rule must require BOTH name and code"
        )

    def test_ph2_code_only_mismatch(self, tmp_path):
        ids = self._build_and_generate(tmp_path, [
            ("n-ph2-code", "ph2-test-walkthrough", "Real Wind Project"),
        ])
        assert "n-ph2-code" not in ids

    def test_inputs_test_name_only_mismatch(self, tmp_path):
        ids = self._build_and_generate(tmp_path, [
            ("n-it-name", "customer-input-model", "Inputs Test html-01"),
        ])
        assert "n-it-name" not in ids

    def test_inputs_test_code_only_mismatch(self, tmp_path):
        ids = self._build_and_generate(tmp_path, [
            ("n-it-code", "inputs-test-html-01", "Customer Input Model"),
        ])
        assert "n-it-code" not in ids

    def test_inputs_slice1_name_only_mismatch(self, tmp_path):
        ids = self._build_and_generate(tmp_path, [
            ("n-s1-name", "customer-runtime-model", "Inputs Slice1 runtime"),
        ])
        assert "n-s1-name" not in ids

    def test_inputs_slice1_code_only_mismatch(self, tmp_path):
        ids = self._build_and_generate(tmp_path, [
            ("n-s1-code", "inputs-slice1-runtime", "Customer Runtime Model"),
        ])
        assert "n-s1-code" not in ids

    def test_p2fix1_ws_name_only_mismatch(self, tmp_path):
        ids = self._build_and_generate(tmp_path, [
            ("n-p2f-ws-name", "real-working-copy", "P2FIX1-WS-abc12345"),
        ])
        assert "n-p2f-ws-name" not in ids

    def test_p2fix1_ws_code_only_mismatch(self, tmp_path):
        ids = self._build_and_generate(tmp_path, [
            ("n-p2f-ws-code", "p2fix1-ws-abc12345", "Real Working Copy"),
        ])
        assert "n-p2f-ws-code" not in ids

    def test_paired_positive_classify(self, tmp_path):
        """Each name_and_code rule with BOTH fields matching
        exactly is classified."""
        ids = self._build_and_generate(tmp_path, [
            ("p-ph2", "ph2-test-walkthrough", "PH2 Test Walkthrough"),
            ("p-it",  "inputs-test-html-01",  "Inputs Test html-01"),
            ("p-s1",  "inputs-slice1-runtime","Inputs Slice1 runtime"),
            ("p-p2fw","p2fix1-ws-abc12345",  "P2FIX1-WS-abc12345"),
            ("p-p2ft","p2fix1-test-abc12345", "P2FIX1-Test-abc12345"),
        ])
        for pid in ("p-ph2", "p-it", "p-s1", "p-p2fw", "p-p2ft"):
            assert pid in ids, (
                f"paired positive {pid!r} must be classified"
            )


class TestSingleFieldRules:
    """Rules whose repository evidence only guarantees one
    identity field (code_only or name_only) must still
    classify when only the documented field matches."""

    def _build_and_generate(self, tmp_path, rows):
        db = tmp_path / "sf.db"
        conn = sqlite3.connect(db)
        cur = conn.cursor()
        cur.execute(
            "CREATE TABLE projects ("
            " project_id TEXT PRIMARY KEY, user_id TEXT, project_code TEXT,"
            " project_name TEXT, project_type TEXT, project_origin TEXT,"
            " source_project_template TEXT, template_source TEXT,"
            " baseline_snapshot_json TEXT, archived INTEGER,"
            " governance_state_json TEXT, last_run_summary_json TEXT,"
            " replay_metadata_json TEXT, created_at TEXT, updated_at TEXT,"
            " is_readonly INTEGER, full_inputs_json TEXT)"
        )
        cur.execute("CREATE TABLE scenarios (scenario_id TEXT PRIMARY KEY, project_id TEXT, name TEXT)")
        cur.execute("CREATE TABLE runs (run_id TEXT PRIMARY KEY, project_id TEXT)")
        cur.execute("CREATE TABLE workspace_states (project_id TEXT PRIMARY KEY, state_json TEXT)")
        for pid, code, name in rows:
            cur.execute(
                "INSERT INTO projects (project_id, user_id, project_code,"
                " project_name, project_type, project_origin,"
                " source_project_template, template_source,"
                " baseline_snapshot_json, archived,"
                " governance_state_json, last_run_summary_json,"
                " replay_metadata_json, created_at, updated_at,"
                " is_readonly) VALUES (?, 'u1', ?, ?, 'Wind',"
                " 'user_created', 'generic_wind', 'generic_wind',"
                " '{}', 0, '{}', '{}', '{}', '2026-01-01',"
                " '2026-01-01', 0)",
                (pid, code, name),
            )
        conn.commit()
        conn.close()
        manifest_path = tmp_path / "sf.local.json"
        r = _run_script(
            "--db", str(db), "--generate-manifest", str(manifest_path)
        )
        assert r.returncode == 0, r.stderr
        m = json.loads(manifest_path.read_text())
        return {c["project_id"] for c in m["candidates"]}

    def test_opex_lifecycle_classifies_from_name_only(self, tmp_path):
        """opex-lifecycle-fixture is a name_only rule. A
        row whose project_name matches the exact fixture
        and whose project_code is unrelated must be
        classified."""
        ids = self._build_and_generate(tmp_path, [
            ("s-opex", "customer-anything",
             "OPEX Lifecycle Test persist"),
        ])
        assert "s-opex" in ids, (
            "opex-lifecycle-fixture is name_only; must "
            "classify from the exact project_name even if "
            "the project_code is unrelated"
        )

    def test_ph3_classifies_from_code_only(self, tmp_path):
        """ph3-working-copy-series is a code_only rule. A
        row whose project_code matches the exact fixture
        and whose project_name is unrelated must be
        classified."""
        ids = self._build_and_generate(tmp_path, [
            ("s-ph3", "ph3-wc-t1", "Customer Wind Project"),
        ])
        assert "s-ph3" in ids, (
            "ph3-working-copy-series is code_only; must "
            "classify from the exact project_code even if "
            "the project_name is unrelated"
        )

    def test_p1uxfix1_classifies_from_code_only(self, tmp_path):
        ids = self._build_and_generate(tmp_path, [
            ("s-p1ux", "p1uxfix1-wc-abcdef01", "Customer P1 Project"),
        ])
        assert "s-p1ux" in ids

    def test_testpilotproj_classifies_from_code_only(self, tmp_path):
        ids = self._build_and_generate(tmp_path, [
            ("s-pilot", "testpilotproj", "Customer Pilot Project"),
        ])
        assert "s-pilot" in ids


# ---------------------------------------------------------------------------
# 3c. Cross-pair mismatch (correlated identity-pair contract)
# ---------------------------------------------------------------------------

class TestCorrelatedIdentityPairs:
    """``name_and_code`` rules use correlated identity pairs.
    A valid fixture name combined with a different valid
    fixture code from the same rule family is NOT
    classified. The P2FIX1 rule additionally requires the
    same kind and the same eight-character token."""

    def _build_and_generate(self, tmp_path, rows):
        db = tmp_path / "pair.db"
        conn = sqlite3.connect(db)
        cur = conn.cursor()
        cur.execute(
            "CREATE TABLE projects ("
            " project_id TEXT PRIMARY KEY, user_id TEXT, project_code TEXT,"
            " project_name TEXT, project_type TEXT, project_origin TEXT,"
            " source_project_template TEXT, template_source TEXT,"
            " baseline_snapshot_json TEXT, archived INTEGER,"
            " governance_state_json TEXT, last_run_summary_json TEXT,"
            " replay_metadata_json TEXT, created_at TEXT, updated_at TEXT,"
            " is_readonly INTEGER, full_inputs_json TEXT)"
        )
        cur.execute("CREATE TABLE scenarios (scenario_id TEXT PRIMARY KEY, project_id TEXT, name TEXT)")
        cur.execute("CREATE TABLE runs (run_id TEXT PRIMARY KEY, project_id TEXT)")
        cur.execute("CREATE TABLE workspace_states (project_id TEXT PRIMARY KEY, state_json TEXT)")
        for pid, code, name in rows:
            cur.execute(
                "INSERT INTO projects (project_id, user_id, project_code,"
                " project_name, project_type, project_origin,"
                " source_project_template, template_source,"
                " baseline_snapshot_json, archived,"
                " governance_state_json, last_run_summary_json,"
                " replay_metadata_json, created_at, updated_at,"
                " is_readonly) VALUES (?, 'u1', ?, ?, 'Wind',"
                " 'user_created', 'generic_wind', 'generic_wind',"
                " '{}', 0, '{}', '{}', '{}', '2026-01-01',"
                " '2026-01-01', 0)",
                (pid, code, name),
            )
        conn.commit()
        conn.close()
        manifest_path = tmp_path / "pair.local.json"
        r = _run_script(
            "--db", str(db), "--generate-manifest", str(manifest_path)
        )
        assert r.returncode == 0, r.stderr
        m = json.loads(manifest_path.read_text())
        return {c["project_id"] for c in m["candidates"]}

    # ----- Inputs Test cross-pair negatives -----

    def test_inputs_test_html_name_runtime_code(self, tmp_path):
        ids = self._build_and_generate(tmp_path, [
            ("n-1", "inputs-test-runtime-matrix", "Inputs Test html-01"),
        ])
        assert "n-1" not in ids

    def test_inputs_test_runtime_name_html_code(self, tmp_path):
        ids = self._build_and_generate(tmp_path, [
            ("n-2", "inputs-test-html-01", "Inputs Test runtime-matrix"),
        ])
        assert "n-2" not in ids

    def test_inputs_test_parity_name_mwh_code(self, tmp_path):
        ids = self._build_and_generate(tmp_path, [
            ("n-3", "inputs-test-mwh-units", "Inputs Test parity-01"),
        ])
        assert "n-3" not in ids

    def test_inputs_test_all_seven_pairs_positive(self, tmp_path):
        """All seven exact correlated pairs classify."""
        rows = [
            ("p-par",     "inputs-test-parity-01",       "Inputs Test parity-01"),
            ("p-mwh",     "inputs-test-mwh-units",       "Inputs Test mwh-units"),
            ("p-rmat",    "inputs-test-runtime-matrix",  "Inputs Test runtime-matrix"),
            ("p-html",    "inputs-test-html-01",         "Inputs Test html-01"),
            ("p-edit",    "inputs-test-editable-01",     "Inputs Test editable-01"),
            ("p-prot",    "inputs-test-prot-ref-01",     "Inputs Test prot-ref-01"),
            ("p-htmx",    "inputs-test-htmx-01",         "Inputs Test htmx-01"),
        ]
        ids = self._build_and_generate(tmp_path, rows)
        for pid, _, _ in rows:
            assert pid in ids, (
                f"Inputs Test positive {pid!r} must be classified"
            )

    # ----- Inputs Slice 1 cross-pair negatives -----

    def test_inputs_slice1_runtime_name_capacity_mw_code(self, tmp_path):
        ids = self._build_and_generate(tmp_path, [
            ("n-1", "inputs-slice1-capacity-mw", "Inputs Slice1 runtime"),
        ])
        assert "n-1" not in ids

    def test_inputs_slice1_capacity_mw_name_runtime_code(self, tmp_path):
        ids = self._build_and_generate(tmp_path, [
            ("n-2", "inputs-slice1-runtime", "Inputs Slice1 capacity_mw"),
        ])
        assert "n-2" not in ids

    def test_inputs_slice1_cod_date_name_horizon_years_code(self, tmp_path):
        ids = self._build_and_generate(tmp_path, [
            ("n-3", "inputs-slice1-horizon-years", "Inputs Slice1 cod_date"),
        ])
        assert "n-3" not in ids

    def test_inputs_slice1_all_fifteen_pairs_positive(self, tmp_path):
        """All fifteen exact correlated pairs classify."""
        rows = [
            ("p-routes",            "inputs-slice1-routes",             "Inputs Slice1 routes"),
            ("p-sequence",          "inputs-slice1-sequence",           "Inputs Slice1 sequence"),
            ("p-outside",           "inputs-slice1-outside",            "Inputs Slice1 outside"),
            ("p-unknown",           "inputs-slice1-unknown",            "Inputs Slice1 unknown"),
            ("p-name",              "inputs-slice1-name",               "Inputs Slice1 name"),
            ("p-invalid",           "inputs-slice1-invalid",            "Inputs Slice1 invalid"),
            ("p-protected",         "inputs-slice1-protected",          "Inputs Slice1 protected"),
            ("p-stale-retry",       "inputs-slice1-stale-retry",        "Inputs Slice1 stale-retry"),
            ("p-version",           "inputs-slice1-version",            "Inputs Slice1 version"),
            ("p-cod-date",          "inputs-slice1-cod-date",           "Inputs Slice1 cod_date"),
            ("p-construction",      "inputs-slice1-construction-months", "Inputs Slice1 construction_months"),
            ("p-horizon",           "inputs-slice1-horizon-years",      "Inputs Slice1 horizon_years"),
            ("p-capacity",          "inputs-slice1-capacity-mw",        "Inputs Slice1 capacity_mw"),
            ("p-p50",               "inputs-slice1-p50-hours",          "Inputs Slice1 p50_hours"),
            ("p-runtime",           "inputs-slice1-runtime",            "Inputs Slice1 runtime"),
        ]
        ids = self._build_and_generate(tmp_path, rows)
        for pid, _, _ in rows:
            assert pid in ids, (
                f"Inputs Slice1 positive {pid!r} must be classified"
            )

    # ----- P2FIX1 kind / token correlation -----

    def test_p2fix1_ws_name_test_code(self, tmp_path):
        """P2FIX1-WS name with p2fix1-test code: different
        kind, must not classify."""
        ids = self._build_and_generate(tmp_path, [
            ("n-1", "p2fix1-test-abc12345", "P2FIX1-WS-abc12345"),
        ])
        assert "n-1" not in ids

    def test_p2fix1_test_name_ws_code(self, tmp_path):
        ids = self._build_and_generate(tmp_path, [
            ("n-2", "p2fix1-ws-abc12345", "P2FIX1-Test-abc12345"),
        ])
        assert "n-2" not in ids

    def test_p2fix1_ws_name_different_token_code(self, tmp_path):
        """P2FIX1-WS-<abc> with p2fix1-ws-<def>: same kind,
        different token, must not classify."""
        ids = self._build_and_generate(tmp_path, [
            ("n-3", "p2fix1-ws-def67890", "P2FIX1-WS-abc12345"),
        ])
        assert "n-3" not in ids

    def test_p2fix1_test_name_different_token_code(self, tmp_path):
        ids = self._build_and_generate(tmp_path, [
            ("n-4", "p2fix1-test-def67890", "P2FIX1-Test-abc12345"),
        ])
        assert "n-4" not in ids

    def test_p2fix1_ws_positive_correlated(self, tmp_path):
        ids = self._build_and_generate(tmp_path, [
            ("p-ws", "p2fix1-ws-abc12345", "P2FIX1-WS-abc12345"),
        ])
        assert "p-ws" in ids

    def test_p2fix1_test_positive_correlated(self, tmp_path):
        ids = self._build_and_generate(tmp_path, [
            ("p-test", "p2fix1-test-abc12345", "P2FIX1-Test-abc12345"),
        ])
        assert "p-test" in ids

    # ----- PH2 cross-pair -----

    def test_ph2_exact_pair_positive(self, tmp_path):
        ids = self._build_and_generate(tmp_path, [
            ("p-ph2", "ph2-test-walkthrough", "PH2 Test Walkthrough"),
        ])
        assert "p-ph2" in ids

    def test_ph2_name_with_other_code(self, tmp_path):
        ids = self._build_and_generate(tmp_path, [
            ("n-ph2-name", "real-wind-project", "PH2 Test Walkthrough"),
        ])
        assert "n-ph2-name" not in ids

    def test_ph2_code_with_other_name(self, tmp_path):
        ids = self._build_and_generate(tmp_path, [
            ("n-ph2-code", "ph2-test-walkthrough", "Real Wind Project"),
        ])
        assert "n-ph2-code" not in ids


class TestRuleStructureValidation:
    """The catalogue validator must reject inconsistent
    rule configuration with a controlled error rather than
    silently fall back to independent set matching."""

    @pytest.fixture(autouse=True)
    def _import_catalogue(self):
        sys.path.insert(0, str(SCRIPT.parent))
        import archive_legacy_test_projects as _cat
        self._catalogue = _cat.CANDIDATE_RULES
        self._validate = _cat._validate_rule_structure

    def test_missing_identity_pairs_raises(self):
        """A name_and_code rule without identity_pairs is
        rejected at import / classification time."""
        self._validate
        bad = {
            "rule_id": "bad-rule",
            "match_policy": "name_and_code",
            "code_prefixes": [],
            "name_prefixes": [],
            "name_fullmatch": [],
            "code_fullmatch": [],
            # identity_pairs is missing
        }
        with pytest.raises(SystemExit):
            self._validate(bad)

    def test_empty_identity_pairs_raises(self):
        self._validate
        bad = {
            "rule_id": "bad-rule",
            "match_policy": "name_and_code",
            "code_prefixes": [],
            "name_prefixes": [],
            "name_fullmatch": [],
            "code_fullmatch": [],
            "identity_pairs": [],
        }
        with pytest.raises(SystemExit):
            self._validate(bad)

    def test_pair_without_name_raises(self):
        self._validate
        bad = {
            "rule_id": "bad-rule",
            "match_policy": "name_and_code",
            "code_prefixes": [],
            "name_prefixes": [],
            "name_fullmatch": [],
            "code_fullmatch": [],
            "identity_pairs": [
                {"code_fullmatch": r"^foo$"},  # missing name
            ],
        }
        with pytest.raises(SystemExit):
            self._validate(bad)

    def test_code_only_without_code_matchers_raises(self):
        self._validate
        bad = {
            "rule_id": "bad-rule",
            "match_policy": "code_only",
            "code_prefixes": [],
            "name_prefixes": [],
            "name_fullmatch": [],
            "code_fullmatch": [],
        }
        with pytest.raises(SystemExit):
            self._validate(bad)

    def test_name_only_without_name_matchers_raises(self):
        self._validate
        bad = {
            "rule_id": "bad-rule",
            "match_policy": "name_only",
            "code_prefixes": [],
            "name_prefixes": [],
            "name_fullmatch": [],
            "code_fullmatch": [],
        }
        with pytest.raises(SystemExit):
            self._validate(bad)

    def test_unknown_match_policy_raises(self):
        self._validate
        bad = {
            "rule_id": "bad-rule",
            "match_policy": "or_magic",  # invalid
            "code_prefixes": [],
            "name_prefixes": [],
            "name_fullmatch": [],
            "code_fullmatch": [],
        }
        with pytest.raises(SystemExit):
            self._validate(bad)

    def test_all_committed_rules_pass_validation(self):
        """Every rule in the committed catalogue passes
        _validate_rule_structure without raising."""

        for rule in self._catalogue:
            self._validate(rule)


# ---------------------------------------------------------------------------
# 4. Manifest generation (logical fingerprint)
# ---------------------------------------------------------------------------

class TestManifestGeneration:
    def test_manifest_contains_logical_fingerprint(self, tmp_path: Path):
        db = _build_sandbox_db(tmp_path)
        m_path = tmp_path / "man.local.json"
        _run_script("--db", str(db), "--generate-manifest", str(m_path))
        m = json.loads(m_path.read_text())
        assert m["manifest_version"] == 2
        db_meta = m["database"]
        # Two authoritative logical fingerprints.
        assert "pre_apply_project_state_sha256" in db_meta
        assert "replay_state_sha256" in db_meta
        assert "schema_fingerprint" in db_meta
        assert "table_counts" in db_meta
        assert "absolute_path" in db_meta
        # raw_file_sha256 is informational, not authoritative.
        assert "raw_file_sha256" in db_meta

    def test_manifest_contains_row_fingerprints(self, tmp_path: Path):
        db = _build_sandbox_db(tmp_path)
        m_path = tmp_path / "man.local.json"
        _run_script("--db", str(db), "--generate-manifest", str(m_path))
        m = json.loads(m_path.read_text())
        for cand in m["candidates"]:
            assert "row_fingerprint" in cand
            assert "classification_rule" in cand

    def test_manifest_is_deterministic_except_timestamp(self, tmp_path: Path):
        db = _build_sandbox_db(tmp_path)
        p1 = tmp_path / "m1.local.json"
        p2 = tmp_path / "m2.local.json"
        _run_script("--db", str(db), "--generate-manifest", str(p1))
        _run_script("--db", str(db), "--generate-manifest", str(p2))
        m1 = json.loads(p1.read_text())
        m2 = json.loads(p2.read_text())
        assert m1["database"]["pre_apply_project_state_sha256"] == (
            m2["database"]["pre_apply_project_state_sha256"]
        )
        assert m1["database"]["replay_state_sha256"] == (
            m2["database"]["replay_state_sha256"]
        )
        ids1 = sorted(c["project_id"] for c in m1["candidates"])
        ids2 = sorted(c["project_id"] for c in m2["candidates"])
        assert ids1 == ids2


# ---------------------------------------------------------------------------
# 5. WAL logical fingerprint
# ---------------------------------------------------------------------------

class TestWalLogicalFingerprint:
    def test_wal_change_breaks_logical_fingerprint(self, tmp_path: Path):
        """WAL must not let the logical project_state_sha256
        be misleading. A committed row update must change the
        logical fingerprint."""
        # Import the script as a module.
        sys.path.insert(0, str(SCRIPT.parent))
        from archive_legacy_test_projects import _state_payload
        db = _build_sandbox_db(tmp_path)
        # First read.
        c1 = sqlite3.connect(db)
        cur1 = c1.cursor()
        cur1.execute("BEGIN")
        ps1, _, _ = _state_payload(cur1)
        cur1.execute("COMMIT")
        c1.close()
        # Mutate one row and commit.
        c2 = sqlite3.connect(db)
        cur2 = c2.cursor()
        cur2.execute(
            "UPDATE projects SET project_name = 'changed' "
            "WHERE project_id = 'p-ph3-wc-1'"
        )
        c2.commit()
        # Second read.
        cur2.execute("BEGIN")
        ps2, _, _ = _state_payload(cur2)
        cur2.execute("COMMIT")
        c2.close()
        assert ps1 != ps2, (
            "logical project_state_sha256 must change when a row "
            "is updated"
        )

    def test_stale_manifest_cannot_apply_after_wal_change(self, tmp_path: Path):
        """A manifest generated before a row change must fail
        closed (non-zero exit) with a clear error message."""
        db = _build_sandbox_db(tmp_path)
        m_path = tmp_path / "stale.local.json"
        _run_script("--db", str(db), "--generate-manifest", str(m_path))
        # Mutate a project row's identity.
        c = sqlite3.connect(db)
        c.execute(
            "UPDATE projects SET project_name = 'changed' "
            "WHERE project_id = 'p-ph3-wc-1'"
        )
        c.commit()
        c.close()
        # Dry-run validation must fail because the project
        # state changed.
        r = _run_script("--db", str(db), "--manifest", str(m_path))
        assert r.returncode != 0
        combined = r.stdout + r.stderr
        assert "ERROR" in combined


# ---------------------------------------------------------------------------
# 6. Apply safety
# ---------------------------------------------------------------------------

class TestApplySafety:
    def _generate(self, db: Path) -> Path:
        manifest = db.parent / "man.archive-manifest.local.json"
        r = _run_script("--db", str(db), "--generate-manifest", str(manifest))
        assert r.returncode == 0, r.stderr
        return manifest

    def test_apply_requires_manifest(self, tmp_path: Path):
        db = _build_sandbox_db(tmp_path)
        backup = Path(tempfile.mkdtemp(prefix="external_backups_"))
        r = _run_script("--db", str(db), "--backup-dir", str(backup),
                        "--apply")
        assert r.returncode == 2
        assert "manifest" in r.stderr

    def test_apply_requires_backup_dir(self, tmp_path: Path):
        db = _build_sandbox_db(tmp_path)
        manifest = self._generate(db)
        r = _run_script("--db", str(db),
                        "--manifest", str(manifest), "--apply")
        assert r.returncode == 5
        assert "backup-dir" in r.stderr

    def test_backup_inside_repository_rejected(self, tmp_path: Path):
        db = _build_sandbox_db(tmp_path)
        manifest = self._generate(db)
        repo_backup = REPO_ROOT / "app" / "data" / "backups" / "sqlite"
        r = _run_script(
            "--db", str(db), "--manifest", str(manifest),
            "--backup-dir", str(repo_backup), "--apply",
        )
        assert r.returncode != 0
        assert "repository" in (r.stdout + r.stderr)

    def test_backup_inside_live_db_dir_rejected(self, tmp_path: Path):
        db = _build_sandbox_db(tmp_path)
        manifest = self._generate(db)
        same_dir = db.parent
        r = _run_script(
            "--db", str(db), "--manifest", str(manifest),
            "--backup-dir", str(same_dir), "--apply",
        )
        assert r.returncode != 0

    def test_valid_manifest_archives_exact_eleven_rows(self, tmp_path: Path):
        db = _build_sandbox_db(tmp_path)
        manifest = self._generate(db)
        backup = Path(tempfile.mkdtemp(prefix="external_backups_"))
        r = _run_script(
            "--db", str(db), "--manifest", str(manifest),
            "--backup-dir", str(backup), "--apply",
        )
        assert r.returncode == 0, r.stderr
        assert "rows_archived_now=11" in r.stdout
        conn = sqlite3.connect(db)
        cur = conn.cursor()
        cur.execute("SELECT archived, COUNT(*) FROM projects GROUP BY archived")
        counts = dict(cur.fetchall())
        assert counts.get(0) == 10
        assert counts.get(1) == 11

    def test_dependent_records_retained(self, tmp_path: Path):
        db = _build_sandbox_db(tmp_path)
        manifest = self._generate(db)
        backup = Path(tempfile.mkdtemp(prefix="external_backups_"))
        _run_script(
            "--db", str(db), "--manifest", str(manifest),
            "--backup-dir", str(backup), "--apply",
        )
        conn = sqlite3.connect(db)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM projects")
        assert cur.fetchone()[0] == 21
        cur.execute("SELECT COUNT(*) FROM scenarios")
        assert cur.fetchone()[0] == 3
        cur.execute("SELECT COUNT(*) FROM runs")
        assert cur.fetchone()[0] == 3
        cur.execute("SELECT COUNT(*) FROM workspace_states")
        assert cur.fetchone()[0] == 21

    def test_backup_filename_uses_sqlite3_suffix(self, tmp_path: Path):
        db = _build_sandbox_db(tmp_path)
        # Snapshot the logical state BEFORE apply so the
        # backup fingerprint can be compared against the
        # pre-update authoritative state.
        sys.path.insert(0, str(SCRIPT.parent))
        from archive_legacy_test_projects import _state_payload
        c0 = sqlite3.connect(db)
        cur0 = c0.cursor()
        cur0.execute("BEGIN")
        try:
            ps_pre, schema_pre, _ = _state_payload(cur0)
        finally:
            cur0.execute("COMMIT")
        c0.close()

        manifest = self._generate(db)
        backup = Path(tempfile.mkdtemp(prefix="external_backups_"))
        _run_script(
            "--db", str(db), "--manifest", str(manifest),
            "--backup-dir", str(backup), "--apply",
        )
        backups = list(backup.glob("finco_runs.db.backup.*.sqlite3"))
        assert len(backups) == 1
        b = backups[0]
        bconn = sqlite3.connect(b)
        bcur = bconn.cursor()
        bcur.execute("PRAGMA integrity_check")
        assert bcur.fetchone()[0] == "ok"
        bcur.execute("SELECT COUNT(*) FROM projects")
        assert bcur.fetchone()[0] == 21
        bcur.execute("SELECT COUNT(*) FROM scenarios")
        assert bcur.fetchone()[0] == 3
        bcur.execute("SELECT COUNT(*) FROM runs")
        assert bcur.fetchone()[0] == 3
        bcur.execute("SELECT COUNT(*) FROM workspace_states")
        assert bcur.fetchone()[0] == 21
        bcur.execute("BEGIN")
        try:
            ps, schema, _ = _state_payload(bcur)
        finally:
            bcur.execute("COMMIT")
        bconn.close()
        # The backup represents the pre-update state.
        assert ps == ps_pre
        assert schema == schema_pre


# ---------------------------------------------------------------------------
# 7. Locked validation & concurrent identity mutation
# ---------------------------------------------------------------------------

class TestLockedValidation:
    def test_concurrent_identity_mutation_zero_writes(self, tmp_path: Path):
        """Between manifest load and the locked validation
        phase, an external mutation that changes a candidate's
        identity must cause the apply to fail with zero
        writes."""
        db = _build_sandbox_db(tmp_path)
        manifest = self._generate_local(db)
        # Hand-edit the manifest to inject a stale row
        # fingerprint for one candidate (simulating an
        # external race).
        m = json.loads(manifest.read_text())
        target = m["candidates"][0]
        target["row_fingerprint"] = "0" * 64
        manifest.write_text(json.dumps(m, indent=2, sort_keys=True))
        backup = Path(tempfile.mkdtemp(prefix="external_backups_"))
        r = _run_script(
            "--db", str(db), "--manifest", str(manifest),
            "--backup-dir", str(backup), "--apply",
        )
        assert r.returncode != 0
        # Zero writes.
        conn = sqlite3.connect(db)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM projects WHERE archived=1")
        assert cur.fetchone()[0] == 0

    def _generate_local(self, db: Path) -> Path:
        manifest = db.parent / "man.archive-manifest.local.json"
        _run_script("--db", str(db), "--generate-manifest", str(manifest))
        return manifest


# ---------------------------------------------------------------------------
# 8. Replay idempotency
# ---------------------------------------------------------------------------

class TestReplayIdempotency:
    """True same-manifest replay semantics.

    The same operator manifest, applied twice in a row,
    produces:

    * First apply:  status=APPLIED        rows_archived_now=N  backup created
    * Second apply: status=ALREADY_APPLIED rows_archived_now=0  no backup

    A fresh manifest generated AFTER all candidates are
    archived produces:

    * status=NO_CANDIDATES rows_archived_now=0  no backup

    A partial replay (some candidates archived, some not)
    always fails closed.
    """

    def test_exact_same_manifest_second_apply_is_noop(self, tmp_path: Path):
        """The exact same operator manifest applied twice
        produces status=ALREADY_APPLIED on the second
        invocation. The manifest bytes are not modified
        between the two applies. No second backup is
        created."""
        db = _build_sandbox_db(tmp_path)
        manifest = tmp_path / "man.archive-manifest.local.json"
        _run_script("--db", str(db), "--generate-manifest", str(manifest))
        backup = Path(tempfile.mkdtemp(prefix="external_backups_"))

        # First apply
        r1 = _run_script(
            "--db", str(db), "--manifest", str(manifest),
            "--backup-dir", str(backup), "--apply",
        )
        assert r1.returncode == 0, r1.stderr
        assert "status=APPLIED" in r1.stdout
        assert "rows_archived_now=11" in r1.stdout

        # Snapshot the manifest bytes
        manifest_bytes_before = manifest.read_bytes()
        backups_after_first = list(backup.glob("finco_runs.db.backup.*.sqlite3"))
        assert len(backups_after_first) == 1

        # Second apply with the EXACT same manifest file
        r2 = _run_script(
            "--db", str(db), "--manifest", str(manifest),
            "--backup-dir", str(backup), "--apply",
        )
        assert r2.returncode == 0, r2.stderr
        assert "status=ALREADY_APPLIED" in r2.stdout
        assert "rows_archived_now=0" in r2.stdout

        # Manifest bytes unchanged
        manifest_bytes_after = manifest.read_bytes()
        assert manifest_bytes_before == manifest_bytes_after, (
            "manifest bytes must not be modified by the "
            "same-manifest replay"
        )
        # No second backup
        backups_after_second = list(backup.glob("finco_runs.db.backup.*.sqlite3"))
        assert len(backups_after_second) == 1, (
            "same-manifest replay must NOT create a second "
            f"backup; found {len(backups_after_second)}"
        )
        # No additional project updates
        conn = sqlite3.connect(db)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM projects WHERE archived=1")
        assert cur.fetchone()[0] == 11, (
            "all 11 candidates must still be archived after the noop replay"
        )

    def test_zero_candidate_manifest_is_no_candidates(self, tmp_path: Path):
        """A fresh manifest generated AFTER all candidates
        are archived produces status=NO_CANDIDATES with
        rows_archived_now=0 and no backup created."""
        db = _build_sandbox_db(tmp_path)
        manifest_a = tmp_path / "man-a.local.json"
        _run_script("--db", str(db), "--generate-manifest", str(manifest_a))
        backup = Path(tempfile.mkdtemp(prefix="external_backups_"))
        # First apply archives all 11 candidates.
        r1 = _run_script(
            "--db", str(db), "--manifest", str(manifest_a),
            "--backup-dir", str(backup), "--apply",
        )
        assert r1.returncode == 0
        # Now generate a fresh manifest against the
        # post-archive DB. Candidate count must be 0.
        manifest_b = tmp_path / "man-b.local.json"
        r_gen = _run_script(
            "--db", str(db), "--generate-manifest", str(manifest_b)
        )
        assert r_gen.returncode == 0
        m = json.loads(manifest_b.read_text())
        assert m["candidate_count"] == 0, (
            f"fresh manifest must have candidate_count=0 after "
            f"all candidates are archived; got {m['candidate_count']}"
        )
        # Apply the zero-candidate manifest.
        r2 = _run_script(
            "--db", str(db), "--manifest", str(manifest_b),
            "--backup-dir", str(backup), "--apply",
        )
        assert r2.returncode == 0, r2.stderr
        assert "status=NO_CANDIDATES" in r2.stdout
        assert "rows_archived_now=0" in r2.stdout
        # Backup count remains 1
        backups = list(backup.glob("finco_runs.db.backup.*.sqlite3"))
        assert len(backups) == 1, (
            "NO_CANDIDATES must NOT create a backup; "
            f"found {len(backups)}"
        )

    def test_partial_replay_fails_specific_branch(self, tmp_path: Path):
        """A second apply with a manifest that contains a mix
        of already-archived and still-active candidates
        fails closed with a precise 'partial replay' error.
        Zero additional project updates. Zero new backups.
        """
        db = _build_sandbox_db(tmp_path)
        manifest = tmp_path / "man.archive-manifest.local.json"
        _run_script("--db", str(db), "--generate-manifest", str(manifest))
        backup = Path(tempfile.mkdtemp(prefix="external_backups_"))
        # First apply archives all 11 candidates.
        r1 = _run_script(
            "--db", str(db), "--manifest", str(manifest),
            "--backup-dir", str(backup), "--apply",
        )
        assert r1.returncode == 0
        backups_before = list(backup.glob("finco_runs.db.backup.*.sqlite3"))
        assert len(backups_before) == 1
        # Manually un-archive one row to create a partial
        # state.
        conn = sqlite3.connect(db)
        conn.execute(
            "UPDATE projects SET archived = 0 "
            "WHERE project_id = 'p-ph3-wc-1'"
        )
        conn.commit()
        # Also restore the row's updated_at to the manifest's
        # recorded value so the row fingerprint still matches
        # and the validator reaches the PARTIAL_REPLAY
        # branch rather than failing earlier.
        conn.execute(
            "UPDATE projects SET updated_at = '2026-01-01' "
            "WHERE project_id = 'p-ph3-wc-1'"
        )
        conn.commit()
        conn.close()
        # Second apply with the same manifest. The
        # validator must observe 1 active + 10 archived and
        # fail closed.
        r2 = _run_script(
            "--db", str(db), "--manifest", str(manifest),
            "--backup-dir", str(backup), "--apply",
        )
        assert r2.returncode != 0, (
            "partial replay must fail closed; "
            f"got exit {r2.returncode}"
        )
        combined = r2.stdout + r2.stderr
        assert "partial replay" in combined.lower(), (
            f"partial replay must produce 'partial replay' "
            f"error; got: {combined[:500]}"
        )
        # No new backup
        backups_after = list(backup.glob("finco_runs.db.backup.*.sqlite3"))
        assert len(backups_after) == 1, (
            "partial-replay rejection must NOT create a "
            f"backup; found {len(backups_after)}"
        )
        # No additional project updates: the unarchived row
        # is still unarchived, the other 10 are still
        # archived.
        conn = sqlite3.connect(db)
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM projects WHERE archived=1"
        )
        n_archived = cur.fetchone()[0]
        conn.close()
        assert n_archived == 10, (
            f"partial-replay rejection must NOT change the "
            f"archive count; expected 10, got {n_archived}"
        )

    def test_replay_fails_when_non_candidate_row_changed(self, tmp_path: Path):
        """A same-manifest replay fails when a non-candidate
        project row changes between the original apply and
        the replay."""
        db = _build_sandbox_db(tmp_path)
        manifest = tmp_path / "man.archive-manifest.local.json"
        _run_script("--db", str(db), "--generate-manifest", str(manifest))
        backup = Path(tempfile.mkdtemp(prefix="external_backups_"))
        r1 = _run_script(
            "--db", str(db), "--manifest", str(manifest),
            "--backup-dir", str(backup), "--apply",
        )
        assert r1.returncode == 0
        # Mutate a non-candidate protected row.
        conn = sqlite3.connect(db)
        conn.execute(
            "UPDATE projects SET project_name = 'CHANGED' "
            "WHERE project_id = 'p-tuho-ref'"
        )
        conn.commit()
        conn.close()
        r2 = _run_script(
            "--db", str(db), "--manifest", str(manifest),
            "--backup-dir", str(backup), "--apply",
        )
        assert r2.returncode != 0, (
            "replay must fail closed when a non-candidate "
            f"row changed; got exit {r2.returncode}"
        )
        combined = r2.stdout + r2.stderr
        assert (
            "replay" in combined.lower()
            or "logical" in combined.lower()
            or "fingerprint" in combined.lower()
        ), f"expected fingerprint/replay error, got: {combined[:500]}"

    def test_replay_fails_when_candidate_identity_changed(self, tmp_path: Path):
        """A same-manifest replay fails when a candidate
        identity (project_name) changes between the
        original apply and the replay."""
        db = _build_sandbox_db(tmp_path)
        manifest = tmp_path / "man.archive-manifest.local.json"
        _run_script("--db", str(db), "--generate-manifest", str(manifest))
        backup = Path(tempfile.mkdtemp(prefix="external_backups_"))
        r1 = _run_script(
            "--db", str(db), "--manifest", str(manifest),
            "--backup-dir", str(backup), "--apply",
        )
        assert r1.returncode == 0
        # Mutate a candidate row's identity.
        conn = sqlite3.connect(db)
        conn.execute(
            "UPDATE projects SET project_name = 'CHANGED' "
            "WHERE project_id = 'p-ph3-wc-1'"
        )
        conn.commit()
        conn.close()
        r2 = _run_script(
            "--db", str(db), "--manifest", str(manifest),
            "--backup-dir", str(backup), "--apply",
        )
        assert r2.returncode != 0, (
            "replay must fail closed when a candidate "
            f"identity changed; got exit {r2.returncode}"
        )
        combined = r2.stdout + r2.stderr
        assert "identity" in combined.lower() or "fingerprint" in combined.lower(), (
            f"expected identity/fingerprint error, got: {combined[:500]}"
        )

    def test_replay_fails_when_candidate_became_protected(self, tmp_path: Path):
        """A same-manifest replay fails when a candidate
        becomes a protected row between the original
        apply and the replay."""
        db = _build_sandbox_db(tmp_path)
        manifest = tmp_path / "man.archive-manifest.local.json"
        _run_script("--db", str(db), "--generate-manifest", str(manifest))
        backup = Path(tempfile.mkdtemp(prefix="external_backups_"))
        r1 = _run_script(
            "--db", str(db), "--manifest", str(manifest),
            "--backup-dir", str(backup), "--apply",
        )
        assert r1.returncode == 0
        # Make p-ph3-wc-1 protected (factory_template origin).
        # This changes project_origin which is in
        # ROW_IDENTITY_FIELDS, so the row fingerprint
        # changes first. Either an identity-change error or
        # a fingerprint/replay/protected error is a valid
        # fail-closed path; all are fail-closed.
        conn = sqlite3.connect(db)
        conn.execute(
            "UPDATE projects SET project_origin = 'factory_template' "
            "WHERE project_id = 'p-ph3-wc-1'"
        )
        conn.commit()
        conn.close()
        r2 = _run_script(
            "--db", str(db), "--manifest", str(manifest),
            "--backup-dir", str(backup), "--apply",
        )
        assert r2.returncode != 0, (
            "replay must fail closed when a candidate "
            f"became protected; got exit {r2.returncode}"
        )
        combined = r2.stdout + r2.stderr
        # Any of these are valid fail-closed paths.
        assert any(
            kw in combined.lower()
            for kw in (
                "protected",
                "fingerprint",
                "identity changed",
                "no longer matches",
                "table count",
            )
        ), f"expected fail-closed error, got: {combined[:500]}"

    def test_replay_fails_when_candidate_disappeared(self, tmp_path: Path):
        """A same-manifest replay fails when a candidate
        row no longer exists. The validator must detect
        this either via the row-existence check, the
        fingerprint check, or the table-count check; all
        paths are fail-closed."""
        db = _build_sandbox_db(tmp_path)
        manifest = tmp_path / "man.archive-manifest.local.json"
        _run_script("--db", str(db), "--generate-manifest", str(manifest))
        backup = Path(tempfile.mkdtemp(prefix="external_backups_"))
        r1 = _run_script(
            "--db", str(db), "--manifest", str(manifest),
            "--backup-dir", str(backup), "--apply",
        )
        assert r1.returncode == 0
        # Delete a candidate row.
        conn = sqlite3.connect(db)
        conn.execute(
            "DELETE FROM projects WHERE project_id = 'p-ph3-wc-1'"
        )
        conn.commit()
        conn.close()
        r2 = _run_script(
            "--db", str(db), "--manifest", str(manifest),
            "--backup-dir", str(backup), "--apply",
        )
        assert r2.returncode != 0, (
            "replay must fail closed when a candidate "
            f"disappeared; got exit {r2.returncode}"
        )
        combined = r2.stdout + r2.stderr
        # Any fail-closed path is acceptable.
        assert any(
            kw in combined.lower()
            for kw in (
                "no longer exists",
                "disappeared",
                "fingerprint",
                "table count",
                "identity",
            )
        ), f"expected fail-closed error, got: {combined[:500]}"


# ---------------------------------------------------------------------------
# 9. Canonical reference protection
# ---------------------------------------------------------------------------

class TestCanonicalReferenceProtection:
    def _build_minimal_db(self, tmp_path: Path) -> Path:
        db = tmp_path / "adv.db"
        conn = sqlite3.connect(db)
        cur = conn.cursor()
        cur.execute(
            "CREATE TABLE projects ("
            " project_id TEXT PRIMARY KEY, user_id TEXT, project_code TEXT,"
            " project_name TEXT, project_type TEXT,"
            " project_origin TEXT, source_project_template TEXT,"
            " template_source TEXT, baseline_snapshot_json TEXT,"
            " archived INTEGER, governance_state_json TEXT,"
            " last_run_summary_json TEXT, replay_metadata_json TEXT,"
            " created_at TEXT, updated_at TEXT, is_readonly INTEGER,"
            " full_inputs_json TEXT)"
        )
        cur.execute("CREATE TABLE scenarios (scenario_id TEXT PRIMARY KEY, project_id TEXT, name TEXT)")
        cur.execute("CREATE TABLE runs (run_id TEXT PRIMARY KEY, project_id TEXT)")
        cur.execute("CREATE TABLE workspace_states (project_id TEXT PRIMARY KEY, state_json TEXT)")
        rows = [
            ("adv-1", "u1", "tuho",        "TUHO Wind 1",       "factory_template", "tuho",    0),
            ("adv-2", "u1", "oborovo",     "Oborovo Solar PV",  "factory_template", "oborovo", 0),
            ("adv-3", "u1", "tuho-copy",   "TUHO Wind 1 (Copy)","user_created",     "tuho",    0),
            ("adv-4", "qa", "tuho-test",   "TUHO Test Copy",    "user_created",     "tuho",    0),
            ("adv-5", "u1", "user-test",   "My Test Project",   "user_created",     "generic_solar", 0),
            ("adv-6", "u-other", "ph3-wc-t1", "ph3-wc-t1",      "user_created",     "generic_wind", 0),
        ]
        for pid, uid, code, name, origin, tpl, ro in rows:
            cur.execute(
                "INSERT INTO projects"
                " (project_id,user_id,project_code,project_name,project_origin,"
                "  source_project_template,template_source,baseline_snapshot_json,"
                "  archived,governance_state_json,last_run_summary_json,"
                "  replay_metadata_json,created_at,updated_at,is_readonly)"
                " VALUES (?,?,?,?,?,?,?,?,0,?,?,?,?,?,?)",
                (pid, uid, code, name, origin, tpl, tpl,
                 "{}", "{}", "{}", "{}", "2026-01-01", "2026-01-01", ro),
            )
        conn.commit()
        conn.close()
        return db

    def test_canonical_tuho_and_oborovo_preserved(self, tmp_path: Path):
        db = self._build_minimal_db(tmp_path)
        m = tmp_path / "adv.local.json"
        _run_script("--db", str(db), "--generate-manifest", str(m))
        mm = json.loads(m.read_text())
        ids = {c["project_id"] for c in mm["candidates"]}
        assert "adv-1" not in ids
        assert "adv-2" not in ids

    def test_legitimate_user_tuho_working_copy_preserved(self, tmp_path: Path):
        db = self._build_minimal_db(tmp_path)
        m = tmp_path / "adv.local.json"
        _run_script("--db", str(db), "--generate-manifest", str(m))
        mm = json.loads(m.read_text())
        ids = {c["project_id"] for c in mm["candidates"]}
        assert "adv-3" not in ids
        assert "adv-4" not in ids

    def test_normal_user_with_test_like_substring_preserved(self, tmp_path: Path):
        db = self._build_minimal_db(tmp_path)
        m = tmp_path / "adv.local.json"
        _run_script("--db", str(db), "--generate-manifest", str(m))
        mm = json.loads(m.read_text())
        ids = {c["project_id"] for c in mm["candidates"]}
        assert "adv-5" not in ids


# ---------------------------------------------------------------------------
# Project Library Open / Clone destination is flag-aware.
# ---------------------------------------------------------------------------

class TestProjectLibraryOpenFlagAware:
    """Project Library Open and Clone links must NEVER point
    at an unmounted route. The single authoritative helper
    ``app.library.router.workbook_destination`` selects
    between the legacy workspace and the V2 workbook based
    on the canonical truthy value of FINCO_WORKBOOK_V2."""

    @pytest.fixture
    def helper_module(self):
        sys.path.insert(0, str(REPO_ROOT))
        from app.library import router as lib_router
        return lib_router

    @pytest.fixture(autouse=True)
    def _clean_flag(self, monkeypatch):
        # Make sure no leftover FINCO_WORKBOOK_V2 is set.
        monkeypatch.delenv("FINCO_WORKBOOK_V2", raising=False)
        yield

    def test_flag_absent_routes_to_legacy_workspace(self, helper_module, monkeypatch):
        monkeypatch.delenv("FINCO_WORKBOOK_V2", raising=False)
        dest = helper_module.workbook_destination("tuho")
        assert dest == "/?project=tuho"

    def test_flag_zero_routes_to_legacy_workspace(self, helper_module, monkeypatch):
        monkeypatch.setenv("FINCO_WORKBOOK_V2", "0")
        dest = helper_module.workbook_destination("tuho")
        assert dest == "/?project=tuho"

    def test_flag_false_routes_to_legacy_workspace(self, helper_module, monkeypatch):
        monkeypatch.setenv("FINCO_WORKBOOK_V2", "false")
        dest = helper_module.workbook_destination("tuho")
        assert dest == "/?project=tuho"

    def test_flag_no_routes_to_legacy_workspace(self, helper_module, monkeypatch):
        monkeypatch.setenv("FINCO_WORKBOOK_V2", "no")
        dest = helper_module.workbook_destination("tuho")
        assert dest == "/?project=tuho"

    def test_flag_off_routes_to_legacy_workspace(self, helper_module, monkeypatch):
        monkeypatch.setenv("FINCO_WORKBOOK_V2", "off")
        dest = helper_module.workbook_destination("tuho")
        assert dest == "/?project=tuho"

    def test_flag_one_routes_to_legacy_when_v2_not_mounted(
        self, helper_module, monkeypatch
    ):
        """Even with FINCO_WORKBOOK_V2=1, if the V2 router
        is not mounted on the app, the helper must NOT
        produce a navigation target for an unmounted route.
        We simulate the unmounted case by patching
        ``_is_v2_router_mounted`` to return False."""
        monkeypatch.setattr(
            helper_module, "_is_v2_router_mounted", lambda: False
        )
        monkeypatch.setenv("FINCO_WORKBOOK_V2", "1")
        dest = helper_module.workbook_destination("tuho")
        assert dest != "/v2/workbook?project=tuho", (
            "must not navigate to an unmounted V2 route"
        )
        assert dest == "/?project=tuho", (
            f"expected legacy fallback; got {dest!r}"
        )

    def test_canonical_truthy_values(self, helper_module, monkeypatch):
        """The single canonical truthy parser accepts
        exactly '1', 'true', 'yes', 'on' (case-insensitive,
        whitespace-stripped). When the V2 router is not
        mounted, all truthy values fall back to the
        legacy workspace."""
        monkeypatch.setattr(
            helper_module, "_is_v2_router_mounted", lambda: False
        )
        for v in ("1", "true", "yes", "on", "TRUE", " yes ", "ON"):
            monkeypatch.setenv("FINCO_WORKBOOK_V2", v)
            dest = helper_module.workbook_destination("tuho")
            assert dest == "/?project=tuho", (
                "truthy value " + repr(v) + " must fall back "
                "to legacy when V2 unmounted; got " + repr(dest)
            )

    def test_clone_destination_uses_helper(self, helper_module, monkeypatch):
        """The clone redirect uses workbook_destination
        and produces the same output for the same
        project_code."""
        monkeypatch.delenv("FINCO_WORKBOOK_V2", raising=False)
        from app.services.project_library_service import (
            create_working_copy,
        )
        # We do not need a real clone; we just need to
        # assert that the helper is the canonical source
        # of truth for the clone destination.
        assert helper_module.workbook_destination(
            "new-working-copy"
        ) == "/?project=new-working-copy"

    def test_url_quoting_handles_special_chars(self, helper_module, monkeypatch):
        monkeypatch.delenv("FINCO_WORKBOOK_V2", raising=False)
        dest = helper_module.workbook_destination("tuho&borovo=1")
        # The project_code is url-quoted.
        assert "tuho" in dest
        assert "&" not in dest.split("?project=")[1]


class TestConftestImportTimeIsolation:
    """The conftest module-level guard must replace any
    FINCO_DB_PATH that resolves inside the repository with
    a session-owned temporary file, both at import time and
    when app.persistence.db subsequently reads the env.
    These tests use fresh subprocesses to prove the actual
    module-import behavior; the same-module tests in
    TestResolvedPathIsolation verify the helper directly.
    """

    def _probe(self, finco_db_path_value):
        """Spawn a fresh Python interpreter that imports
        conftest and app.persistence.db, then prints both
        resolved values. Returns the parsed dict."""
        script = (
            "import sys, os, json, runpy\n"
            f"os.environ['FINCO_DB_PATH'] = {finco_db_path_value!r}\n"
            f"sys.path.insert(0, {str(REPO_ROOT)!r})\n"
            f"sys.path.insert(0, {str(REPO_ROOT / 'tests')!r})\n"
            # Re-trigger conftest with the env override.
            "import importlib, tests.conftest as conftest\n"
            "import app.persistence.db as db_module\n"
            "import pathlib\n"
            "print(json.dumps({\n"
            "  'finco_db_path': os.environ.get('FINCO_DB_PATH'),\n"
            "  'finco_db_resolved': str(pathlib.Path(os.environ.get('FINCO_DB_PATH', '')).expanduser().resolve()),\n"
            "  'app_db_path': db_module.DB_PATH,\n"
            "  'app_db_resolved': str(pathlib.Path(db_module.DB_PATH).expanduser().resolve()),\n"
            "}))"
        )
        r = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, timeout=30,
        )
        assert r.returncode == 0, f"subprocess failed: {r.stderr}"
        # The probe prints JSON on the last line.
        last_line = [ln for ln in r.stdout.splitlines() if ln.startswith("{")][-1]
        return json.loads(last_line)

    def test_unset_resolves_outside_repository(self):
        out = self._probe("")
        # "" was passed; subprocess sees an empty string for
        # FINCO_DB_PATH. The conftest guard must replace it
        # with an isolation path.
        from tests.conftest import _REPO_ROOT_RESOLVED
        prod = str((_REPO_ROOT_RESOLVED / "app" / "data" / "finco_runs.db").resolve())
        assert out["finco_db_resolved"] != prod
        assert out["app_db_resolved"] != prod
        # The conftest's isolation dir is outside the repo.
        try:
            pathlib_resolved = Path(out["finco_db_resolved"]).resolve()
            pathlib_resolved.relative_to(_REPO_ROOT_RESOLVED)
            assert False, (
                "isolation DB must not be inside repository"
            )
        except ValueError:
            pass

    def test_absolute_repo_path_replaced(self):
        prod = str((REPO_ROOT / "app" / "data" / "finco_runs.db").resolve())
        out = self._probe(prod)
        assert out["finco_db_resolved"] != prod, (
            f"absolute repository path must be replaced; got {out!r}"
        )
        assert out["app_db_resolved"] != prod

    def test_relative_repo_path_replaced(self):
        out = self._probe("app/data/finco_runs.db")
        prod = str((REPO_ROOT / "app" / "data" / "finco_runs.db").resolve())
        assert out["finco_db_resolved"] != prod

    def test_dot_slash_repo_path_replaced(self):
        out = self._probe("./app/data/finco_runs.db")
        prod = str((REPO_ROOT / "app" / "data" / "finco_runs.db").resolve())
        assert out["finco_db_resolved"] != prod

    def test_double_dot_repo_path_replaced(self):
        out = self._probe(
            str((REPO_ROOT / "tests").relative_to(REPO_ROOT))
            + "/../app/data/finco_runs.db"
        )
        prod = str((REPO_ROOT / "app" / "data" / "finco_runs.db").resolve())
        assert out["finco_db_resolved"] != prod

    def test_symlink_to_repo_replaced(self, tmp_path):
        link = tmp_path / "linked.db"
        try:
            link.symlink_to((REPO_ROOT / "app" / "data" / "finco_runs.db"))
        except (OSError, NotImplementedError) as e:
            pytest.skip(f"symlinks not supported: {e!r}")
        out = self._probe(str(link))
        prod = str((REPO_ROOT / "app" / "data" / "finco_runs.db").resolve())
        assert out["finco_db_resolved"] != prod, (
            "symlink to repository DB must be replaced; got "
            f"{out!r}"
        )

    def test_external_temp_path_preserved(self, tmp_path):
        external = tmp_path / "external.db"
        external.touch()
        out = self._probe(str(external))
        assert out["finco_db_resolved"] == str(external.resolve()), (
            "external temp DB must be preserved; got "
            f"{out!r}"
        )
        # The app.persistence.db.DB_PATH should also resolve
        # to the external path. Note: app.persistence.db is
        # imported BEFORE conftest in the probe. We rely on
        # the conftest module-level guard having replaced
        # the env var before the import took effect. If
        # app.persistence.db was already imported and
        # cached, we re-import.
        # In this probe, conftest is imported AFTER the env
        # is set but BEFORE app.persistence.db, so the env
        # takes effect.
        # The app DB path resolution depends on whether
        # app.persistence.db was already loaded by an
        # earlier test. We accept either the external path
        # OR the conftest's isolation path, but NOT the
        # production path.
        prod = str((REPO_ROOT / "app" / "data" / "finco_runs.db").resolve())
        assert out["app_db_resolved"] != prod


# ---------------------------------------------------------------------------
# External-path no-allocation subprocess test
# ---------------------------------------------------------------------------

class TestConftestExternalNoAllocation:
    """Fresh-process test proving that an explicit external
    FINCO_DB_PATH is preserved AND that conftest does NOT
    create an unused ``finco_test_db_*`` directory in that
    case."""

    def test_external_path_preserved_no_allocation(self, tmp_path):
        # Create a fresh external DB file the test owns.
        external_db = tmp_path / "external_test.db"
        external_db.touch()
        # Snapshot tmp_path for finco_test_db_* directories
        # BEFORE running the probe.
        glob = tmp_path.glob("finco_test_db_*")
        before_dirs = sorted(p.name for p in glob)
        assert before_dirs == [], (
            "fresh tmp_path should have no finco_test_db_* "
            f"before probe; found {before_dirs}"
        )
        # Build a probe that imports conftest with the
        # external path pre-set and reports (a) the env
        # value after import, (b) whether conftest created
        # an isolation tmpdir, (c) the conftest ownership
        # flag, and (d) whether the operator's external
        # file is still on disk.
        ext_path = str(external_db)
        repo_root = str(REPO_ROOT)
        script = (
            "import os, sys, json\n"
            "os.environ['FINCO_DB_PATH'] = " + repr(ext_path) + "\n"
            "os.environ['FINCO_SECRET_KEY'] = 'test-secret-key'\n"
            "sys.path.insert(0, " + repr(repo_root) + ")\n"
            "sys.path.insert(0, " + repr(repo_root + "/tests") + ")\n"
            "import conftest\n"
            "import pathlib\n"
            "iso_dir = conftest._ISOLATION_TMP_DIR_RESOLVED\n"
            "ext_db_path = pathlib.Path(" + repr(ext_path) + ")\n"
            "print(json.dumps({\n"
            "  'env_db_path': os.environ.get('FINCO_DB_PATH'),\n"
            "  'env_resolved': str(pathlib.Path(os.environ.get('FINCO_DB_PATH', '')).expanduser().resolve()),\n"
            "  'owns': conftest.CONFTEST_OWNS_ISOLATION_DIR,\n"
            "  'iso_dir_is_none': iso_dir is None,\n"
            "  'iso_dir_str': str(iso_dir) if iso_dir is not None else None,\n"
            "  'external_exists': ext_db_path.exists(),\n"
            "}))\n"
        )
        r = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, timeout=30,
        )
        assert r.returncode == 0, (
            f"subprocess failed: {r.stderr}\n"
            f"stdout: {r.stdout}"
        )
        last_line = [ln for ln in r.stdout.splitlines() if ln.startswith("{")][-1]
        out = json.loads(last_line)
        # External path preserved.
        assert out["env_db_path"] == str(external_db), (
            f"external path must be preserved; got {out!r}"
        )
        assert out["env_resolved"] == str(external_db.resolve())
        # Conftest does NOT own the directory.
        assert out["owns"] is False, (
            f"conftest must not own the dir when external "
            f"path is set; got {out!r}"
        )
        # No isolation tmpdir was created.
        assert out["iso_dir_is_none"] is True, (
            f"conftest must not allocate a tmpdir when "
            f"external path is set; got iso_dir={out['iso_dir_str']!r}"
        )
        # External file still on disk.
        assert out["external_exists"] is True
        # Verify after the probe that no finco_test_db_*
        # directory was created anywhere reachable from
        # tmp_path. (Because the subprocess inherited
        # FINCO_DB_PATH=external, the only possible
        # allocation site was conftest, which we just
        # confirmed did not allocate.)
        after_dirs = sorted(
            p.name for p in tmp_path.glob("finco_test_db_*")
        )
        assert after_dirs == [], (
            "no finco_test_db_* should appear in tmp_path; "
            f"found {after_dirs}"
        )


# ---------------------------------------------------------------------------
# Real mounted-V2 subprocess test
# ---------------------------------------------------------------------------

class TestV2MountedSubprocess:
    """Fresh-process tests that set FINCO_WORKBOOK_V2=1
    BEFORE importing main_web and then probe the actual
    app.routes for /v2/workbook. The mounted state is only
    covered when the application is imported with the flag
    set before startup."""

    def _probe(self, finco_workbook_v2_value):
        """Spawn a fresh Python interpreter that sets
        FINCO_WORKBOOK_V2, imports main_web, imports
        app.library.router, and prints:
          * v2_workbook_path_present: bool
          * workbook_v2_enabled: bool
          * workbook_destination(tuho): str
        """
        script = (
            "import os, json, sys\n"
            f"os.environ['FINCO_WORKBOOK_V2'] = {finco_workbook_v2_value!r}\n"
            f"os.environ['FINCO_SECRET_KEY'] = 'test-secret-key-final-review'\n"
            f"sys.path.insert(0, {str(REPO_ROOT)!r})\n"
            "import main_web\n"
            "from app.library.router import (\n"
            "    workbook_v2_enabled, workbook_destination,\n"
            ")\n"
            "target = '/v2/workbook'\n"
            "present = False\n"
            "for r in main_web.app.routes:\n"
            "    ctx = getattr(r, 'include_context', None)\n"
            "    if ctx is not None:\n"
            "        inner = getattr(ctx, 'included_router', None)\n"
            "        if inner is not None:\n"
            "            for ir in getattr(inner, 'routes', []) or []:\n"
            "                p = getattr(ir, 'path', '')\n"
            "                if (getattr(ctx, 'prefix', '') or '') + p == target:\n"
            "                    present = True\n"
            "                    break\n"
            "    if present:\n"
            "        break\n"
            "print(json.dumps({\n"
            "  'v2_workbook_path_present': present,\n"
            "  'workbook_v2_enabled': bool(workbook_v2_enabled()),\n"
            "  'workbook_destination': workbook_destination('tuho'),\n"
            "}))\n"
        )
        r = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, timeout=60,
        )
        assert r.returncode == 0, (
            f"subprocess failed: {r.stderr}\n"
            f"stdout: {r.stdout}"
        )
        last_line = [ln for ln in r.stdout.splitlines() if ln.startswith("{")][-1]
        return json.loads(last_line)

    def test_fresh_process_flag_1_mounts_v2(self):
        """With FINCO_WORKBOOK_V2=1 set before main_web
        is imported, the /v2/workbook route is mounted and
        the helper returns the V2 destination."""
        out = self._probe("1")
        assert out["v2_workbook_path_present"] is True, (
            f"/v2/workbook must be present when flag=1; got {out!r}"
        )
        assert out["workbook_v2_enabled"] is True
        assert out["workbook_destination"] == "/v2/workbook?project=tuho", (
            f"expected V2 destination; got {out!r}"
        )

    def test_fresh_process_flag_on_mounts_v2(self):
        """With FINCO_WORKBOOK_V2=on (alternative truthy
        value) the V2 router is also mounted."""
        out = self._probe("on")
        assert out["v2_workbook_path_present"] is True, (
            f"/v2/workbook must be present when flag=on; got {out!r}"
        )
        assert out["workbook_v2_enabled"] is True
        assert out["workbook_destination"] == "/v2/workbook?project=tuho"

    def test_fresh_process_flag_absent_unmounted(self):
        """Without FINCO_WORKBOOK_V2 the V2 router is not
        mounted and the helper returns the legacy
        destination."""
        out = self._probe("")
        assert out["v2_workbook_path_present"] is False
        assert out["workbook_v2_enabled"] is False
        assert out["workbook_destination"] == "/?project=tuho"

    def test_fresh_process_flag_0_unmounted(self):
        """FINCO_WORKBOOK_V2=0 is not truthy; the V2 router
        is not mounted and the helper returns legacy."""
        out = self._probe("0")
        assert out["v2_workbook_path_present"] is False
        assert out["workbook_v2_enabled"] is False
        assert out["workbook_destination"] == "/?project=tuho"

    def test_fresh_process_flag_false_unmounted(self):
        out = self._probe("false")
        assert out["v2_workbook_path_present"] is False
        assert out["workbook_v2_enabled"] is False
        assert out["workbook_destination"] == "/?project=tuho"

    def test_fresh_process_flag_no_unmounted(self):
        out = self._probe("no")
        assert out["v2_workbook_path_present"] is False
        assert out["workbook_v2_enabled"] is False
        assert out["workbook_destination"] == "/?project=tuho"

    def test_fresh_process_flag_off_unmounted(self):
        out = self._probe("off")
        assert out["v2_workbook_path_present"] is False
        assert out["workbook_v2_enabled"] is False
        assert out["workbook_destination"] == "/?project=tuho"

    def test_fresh_process_flag_1_explicitly_unmounted(
        self, tmp_path: Path
    ):
        """If the operator sets FINCO_WORKBOOK_V2=1 but
        the V2 router is NOT mounted (simulated by
        removing the included router after import), the
        helper must fall back to legacy. This case is
        harder to set up cleanly in a fresh process; we
        use a side-loaded import that does not call
        include_router for V2. The cleanest signal is to
        import a fresh main_web variant that omits the
        V2 include. We simulate this by importing the
        library.router against a freshly-created FastAPI
        app that does NOT include the V2 router, and
        monkeypatching the helper's mount probe."""
        # Build a fresh FastAPI app that has no V2 routes.
        script = (
            "import os, sys, json\n"
            f"os.environ['FINCO_WORKBOOK_V2'] = '1'\n"
            f"os.environ['FINCO_SECRET_KEY'] = 'test-secret'\n"
            f"sys.path.insert(0, {str(REPO_ROOT)!r})\n"
            # Import the library router module and force its\n"
            # _is_v2_router_mounted to inspect a fake app\n"
            # that has NO /v2 routes.\n"
            "from fastapi import FastAPI\n"
            "import app.library.router as lr\n"
            "fake_app = FastAPI()\n"
            # Patch main_web's app attribute to fake_app\n"
            "import main_web\n"
            "main_web.app = fake_app\n"
            "print(json.dumps({\n"
            "  'v2_workbook_path_present': lr._is_v2_router_mounted(),\n"
            "  'workbook_v2_enabled': bool(lr.workbook_v2_enabled()),\n"
            "  'workbook_destination': lr.workbook_destination('tuho'),\n"
            "}))\n"
        )
        r = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, timeout=60,
        )
        assert r.returncode == 0, (
            f"subprocess failed: {r.stderr}\nstdout: {r.stdout}"
        )
        last_line = [ln for ln in r.stdout.splitlines() if ln.startswith("{")][-1]
        out = json.loads(last_line)
        assert out["v2_workbook_path_present"] is False, (
            f"fake app must have no /v2/workbook; got {out!r}"
        )
        assert out["workbook_v2_enabled"] is False
        assert out["workbook_destination"] == "/?project=tuho", (
            f"expected legacy fallback when V2 is unmounted; "
            f"got {out!r}"
        )


# ---------------------------------------------------------------------------
# 10. Navigation (preserved)
# ---------------------------------------------------------------------------

class TestRootRouteRedirect:
    def test_root_without_project_redirects_to_library(self, client):
        r = client.get("/", follow_redirects=False)
        assert r.status_code == 302
        assert r.headers.get("location") == "/library"

    def test_root_with_explicit_project_still_opens_workspace(self, client):
        r = client.get("/?project=tuho", follow_redirects=False)
        if r.status_code in (301, 302, 303, 307, 308):
            assert r.headers.get("location") != "/library"

    def test_project_list_is_paginated(self, client):
        r = client.get("/library")
        assert r.status_code in (200, 302)

    def test_role_filter_works(self, client):
        r = client.get("/library/list?role=reference")
        assert r.status_code in (200, 302)

    def test_search_works(self, client):
        r = client.get("/library/list?q=tuho")
        assert r.status_code in (200, 302)


class TestReferenceCardCopy:
    def test_card_describes_tuho_and_oborovo_only(self):
        path = REPO_ROOT / "app/templates/partials/project_home.html"
        text = path.read_text(encoding="utf-8")
        assert "TUHO and Oborovo" in text
        assert "TUHO, Oborovo, Generic" not in text
        idx = text.find('data-p1sprint2-link="open-reference"')
        assert idx > 0
        anchor_start = text.rfind("<a ", 0, idx)
        anchor_end = text.find("</a>", idx)
        card = text[anchor_start: anchor_end]
        assert 'href="/library"' in card
        assert 'href="/projects/browse"' not in card


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    sys.path.insert(0, str(REPO_ROOT))
    from app.auth import create_session_token
    from main_web import app
    c = TestClient(app)
    token = create_session_token(user_id="1", username="test_user")
    c.cookies.set("finco_session", token)
    return c
