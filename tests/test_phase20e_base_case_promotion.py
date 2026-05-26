"""Tests for Phase 20E root cause fix: backfill Base Case for legacy projects."""
import json
import os
import uuid

import pytest

os.environ["FINCO_COOKIE_SECURE"] = "false"
os.environ["FINCO_SECRET_KEY"] = "test-secret-key-for-phase20e"


# ── Fixtures ────────────────────────────────────────────────────────────────────

@pytest.fixture
def author_id():
    return "test-user-20e"


@pytest.fixture
def project_id():
    return "proj-phase20e-001"


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    """Isolated temp DB per test using the test_project_persistence pattern."""
    import app.persistence.db as db_mod

    old_path = os.environ.get("FINCO_DB_PATH")
    db_file = str(tmp_path / "test_repo.db")
    os.environ["FINCO_DB_PATH"] = db_file
    db_mod.DB_PATH = db_file
    db_mod._connection = None

    yield db_file

    if old_path:
        os.environ["FINCO_DB_PATH"] = old_path
    else:
        os.environ.pop("FINCO_DB_PATH", None)
    db_mod._connection = None


def _insert_project(user_id: str, project_id: str, project_code: str):
    """Insert a project row (required for FK on scenarios)."""
    from app.persistence.db import get_cursor
    now = "2026-05-01T00:00:00+00:00"
    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO projects
              (project_id, user_id, project_code, project_name, project_type,
               project_origin, source_project_template, template_source,
               baseline_snapshot_json, archived, governance_state_json,
               last_run_summary_json, replay_metadata_json,
               created_at, updated_at, is_readonly)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project_id, user_id, project_code, f"Test Project {project_code}",
                "Solar", "user_created", "", None,
                json.dumps({}), 0,
                json.dumps({}), json.dumps({}), json.dumps({}),
                now, now, 0,
            ),
        )


def _insert_scenario(user_id: str, project_id: str, name: str,
                     created_at: str, is_base_case: int = 0) -> str:
    """Direct INSERT for fine-grained control over created_at."""
    from app.persistence.db import get_cursor
    sc_id = uuid.uuid4().hex[:16]
    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO scenarios
              (scenario_id, project_id, user_id, scenario_name, project_code,
               is_base_case, archived, source_project_template,
               base_input_set_json, overrides_json, snapshot_json,
               governance_state_json, last_run_summary_json,
               replay_metadata_json, schema_version,
               created_at, updated_at,
               copied_from_scenario_id, parent_scenario_id)
            VALUES (?, ?, ?, ?, ?, ?, 0, '', ?, ?, ?, ?, ?, ?, '1.0', ?, ?, NULL, NULL)
            """,
            (
                sc_id, project_id, user_id, name, "phase20e-test",
                is_base_case,
                json.dumps({}),
                json.dumps({}),
                json.dumps({"project_name": name}),
                json.dumps({}),
                json.dumps({}),
                json.dumps({}),
                created_at, created_at,
            ),
        )
    return sc_id


@pytest.fixture
def with_scenarios(fresh_db, author_id, project_id):
    """Insert project + 3 non-base-case scenarios (created_at: Oldest < Middle < Newest)."""
    _insert_project(author_id, project_id, "phase20e-test")
    _insert_scenario(author_id, project_id, "Middle Scenario",
                     "2026-05-15T12:00:00+00:00")
    _insert_scenario(author_id, project_id, "Newest Scenario",
                     "2026-05-31T23:59:59+00:00")
    _insert_scenario(author_id, project_id, "Oldest Scenario",
                     "2026-05-01T00:00:00+00:00")


# ── _get_least_created_scenario_for_project ────────────────────────────────

def test_get_least_created_returns_earliest_created_at(
        fresh_db, author_id, project_id, with_scenarios):
    from app.persistence.repository import _get_least_created_scenario_for_project

    sc = _get_least_created_scenario_for_project(author_id, project_id)
    assert sc is not None
    assert sc.scenario_name == "Oldest Scenario"


def test_get_least_created_returns_none_when_no_project(
        fresh_db, author_id, project_id):
    from app.persistence.repository import _get_least_created_scenario_for_project
    result = _get_least_created_scenario_for_project("orphan", "no-such")
    assert result is None


# ── promote_scenario_to_base_case ──────────────────────────────────────────

def test_promote_sets_is_base_case_on_target(
        fresh_db, author_id, project_id, with_scenarios):
    from app.persistence.repository import promote_scenario_to_base_case
    from app.persistence.db import get_cursor

    with get_cursor() as cur:
        cur.execute(
            "SELECT scenario_id FROM scenarios WHERE user_id=? AND project_id=? LIMIT 1",
            (author_id, project_id),
        )
        target_id = cur.fetchone()[0]

    result = promote_scenario_to_base_case(author_id, target_id)
    assert result is not None
    assert result.is_base_case is True

    with get_cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM scenarios WHERE user_id=? AND project_id=? AND is_base_case=1",
            (author_id, project_id),
        )
        assert cur.fetchone()[0] == 1


def test_promote_clears_previous_base_case(
        fresh_db, author_id, project_id, with_scenarios):
    from app.persistence.repository import promote_scenario_to_base_case
    from app.persistence.db import get_cursor

    with get_cursor() as cur:
        cur.execute(
            "SELECT scenario_id FROM scenarios WHERE user_id=? AND project_id=? "
            "ORDER BY created_at ASC",
            (author_id, project_id),
        )
        rows = cur.fetchall()
        first_id, second_id = rows[0][0], rows[1][0]

    r1 = promote_scenario_to_base_case(author_id, first_id)
    assert r1.is_base_case is True

    r2 = promote_scenario_to_base_case(author_id, second_id)
    assert r2.is_base_case is True

    with get_cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM scenarios WHERE user_id=? AND is_base_case=1",
            (author_id,),
        )
        assert cur.fetchone()[0] == 1


def test_promote_idempotent_on_already_base(
        fresh_db, author_id, project_id, with_scenarios):
    from app.persistence.repository import promote_scenario_to_base_case
    from app.persistence.db import get_cursor

    with get_cursor() as cur:
        cur.execute(
            "SELECT scenario_id FROM scenarios WHERE user_id=? AND project_id=? LIMIT 1",
            (author_id, project_id),
        )
        target_id = cur.fetchone()[0]

    r1 = promote_scenario_to_base_case(author_id, target_id)
    assert r1.is_base_case is True

    # Same scenario again — idempotent
    r2 = promote_scenario_to_base_case(author_id, target_id)
    assert r2 is not None
    assert r2.is_base_case is True

    with get_cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM scenarios WHERE user_id=? AND is_base_case=1",
            (author_id,),
        )
        assert cur.fetchone()[0] == 1


def test_promote_returns_none_for_nonexistent(fresh_db):
    from app.persistence.repository import promote_scenario_to_base_case
    result = promote_scenario_to_base_case("ghost", "ghost-sc-id")
    assert result is None


def test_promote_does_not_affect_other_users(
        fresh_db, author_id, project_id, with_scenarios):
    from app.persistence.repository import promote_scenario_to_base_case
    from app.persistence.db import get_cursor

    other_user = "other-user-999"
    other_project = "proj-phase20e-other"
    _insert_project(other_user, other_project, "phase20e-test-other")
    _insert_scenario(other_user, other_project, "Other User Base",
                     "2026-05-01T00:00:00+00:00", is_base_case=1)

    with get_cursor() as cur:
        cur.execute(
            "SELECT scenario_id FROM scenarios WHERE user_id=? AND project_id=? LIMIT 1",
            (author_id, project_id),
        )
        target_id = cur.fetchone()[0]

    promote_scenario_to_base_case(author_id, target_id)

    with get_cursor() as cur:
        cur.execute(
            "SELECT is_base_case FROM scenarios WHERE user_id=?",
            (other_user,),
        )
        others = cur.fetchall()
    assert len(others) == 1
    assert others[0][0] == 1


# ── add_scenario after promotion ──────────────────────────────────────────

def test_add_scenario_works_after_promotion(
        fresh_db, author_id, project_id, with_scenarios):
    from app.persistence.repository import (
        promote_scenario_to_base_case,
        _get_least_created_scenario_for_project,
        add_scenario,
    )

    oldest = _get_least_created_scenario_for_project(author_id, project_id)
    promoted = promote_scenario_to_base_case(author_id, oldest.scenario_id)
    assert promoted.is_base_case is True

    new_sc = add_scenario(
        user_id=author_id,
        project_id=project_id,
        project_code="phase20e-test",
        scenario_name="New Inherited Scenario",
        parent_scenario_id=promoted.scenario_id,
        base_input_set=promoted.snapshot or {},
        overrides={},
        governance_state={},
        replay_metadata={},
    )
    assert new_sc is not None
    assert new_sc.scenario_name == "New Inherited Scenario"
    assert new_sc.parent_scenario_id == promoted.scenario_id
    assert new_sc.is_base_case is False
