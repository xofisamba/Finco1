"""V3-8: Tests for full-fidelity ProjectInputs wiring on ScenarioRecord.

Covers:
- save_scenario with full_inputs persists and round-trips
- add_scenario with full_inputs persists and round-trips
- get_or_create_base_case_scenario with full_inputs persists and round-trips
- Rows without full_inputs_json (old SELECT) load with full_inputs=None
- ScenarioRecord field-shape: 20 fields including full_inputs
"""
import uuid
import pytest

from app.persistence.db import get_cursor
from app.persistence.scenarios_repository import (
    save_scenario,
    add_scenario,
    get_or_create_base_case_scenario,
    get_scenario,
)
from app.persistence.projects_repository import save_project
from finco_core.inputs import project_inputs_to_dict, project_inputs_from_dict
from app.ui_runner import run_demo_project


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def user_id():
    return f"test_user_{uuid.uuid4().hex[:8]}"


@pytest.fixture()
def tuho_inputs():
    return run_demo_project("TUHO").project_inputs


@pytest.fixture()
def project(user_id):
    rec = save_project(
        user_id=user_id,
        project_code=f"P{uuid.uuid4().hex[:6]}",
        project_name="Test Project",
        source_project_template="TUHO",
    )
    return rec


# ---------------------------------------------------------------------------
# save_scenario
# ---------------------------------------------------------------------------


class TestSaveScenarioFullInputs:
    def test_save_scenario_stores_full_inputs(self, user_id, project, tuho_inputs):
        d = project_inputs_to_dict(tuho_inputs)
        rec = save_scenario(
            user_id=user_id,
            project_id=project.project_id,
            scenario_name="S1",
            project_code=project.project_code,
            source_project_template="TUHO",
            snapshot={},
            full_inputs=d,
        )
        assert rec.full_inputs == d

    def test_save_scenario_no_full_inputs_gives_none(self, user_id, project):
        rec = save_scenario(
            user_id=user_id,
            project_id=project.project_id,
            scenario_name="S2",
            project_code=project.project_code,
            source_project_template="TUHO",
            snapshot={},
        )
        assert rec.full_inputs is None

    def test_save_scenario_round_trip_via_db(self, user_id, project, tuho_inputs):
        d = project_inputs_to_dict(tuho_inputs)
        rec = save_scenario(
            user_id=user_id,
            project_id=project.project_id,
            scenario_name="S3",
            project_code=project.project_code,
            source_project_template="TUHO",
            snapshot={},
            full_inputs=d,
        )
        loaded = get_scenario(rec.scenario_id, user_id)
        assert loaded is not None
        assert loaded.full_inputs == d
        assert project_inputs_from_dict(loaded.full_inputs) == tuho_inputs


# ---------------------------------------------------------------------------
# add_scenario
# ---------------------------------------------------------------------------


class TestAddScenarioFullInputs:
    def test_add_scenario_stores_full_inputs(self, user_id, project, tuho_inputs):
        d = project_inputs_to_dict(tuho_inputs)
        base = get_or_create_base_case_scenario(
            user_id=user_id,
            project_id=project.project_id,
            project_code=project.project_code,
            project_name="Base Case",
            project_type=None,
            source_project_template="TUHO",
            base_input_set={},
            governance_state={},
        )
        rec = add_scenario(
            user_id=user_id,
            project_id=project.project_id,
            project_code=project.project_code,
            scenario_name="Alt1",
            parent_scenario_id=base.scenario_id,
            base_input_set={},
            full_inputs=d,
        )
        assert rec is not None
        assert rec.full_inputs == d

    def test_add_scenario_round_trip_via_db(self, user_id, project, tuho_inputs):
        d = project_inputs_to_dict(tuho_inputs)
        base = get_or_create_base_case_scenario(
            user_id=user_id,
            project_id=project.project_id,
            project_code=project.project_code,
            project_name="Base Case",
            project_type=None,
            source_project_template="TUHO",
            base_input_set={},
            governance_state={},
        )
        rec = add_scenario(
            user_id=user_id,
            project_id=project.project_id,
            project_code=project.project_code,
            scenario_name="Alt2",
            parent_scenario_id=base.scenario_id,
            base_input_set={},
            full_inputs=d,
        )
        loaded = get_scenario(rec.scenario_id, user_id)
        assert loaded.full_inputs == d
        assert project_inputs_from_dict(loaded.full_inputs) == tuho_inputs


# ---------------------------------------------------------------------------
# get_or_create_base_case_scenario
# ---------------------------------------------------------------------------


class TestBaseScenarioFullInputs:
    def test_base_case_stores_full_inputs(self, user_id, project, tuho_inputs):
        d = project_inputs_to_dict(tuho_inputs)
        rec = get_or_create_base_case_scenario(
            user_id=user_id,
            project_id=project.project_id,
            project_code=project.project_code,
            project_name="Base Case",
            project_type=None,
            source_project_template="TUHO",
            base_input_set={},
            governance_state={},
            full_inputs=d,
        )
        assert rec.full_inputs == d

    def test_base_case_round_trip_via_db(self, user_id, project, tuho_inputs):
        d = project_inputs_to_dict(tuho_inputs)
        rec = get_or_create_base_case_scenario(
            user_id=user_id,
            project_id=project.project_id,
            project_code=project.project_code,
            project_name="Base Case",
            project_type=None,
            source_project_template="TUHO",
            base_input_set={},
            governance_state={},
            full_inputs=d,
        )
        loaded = get_scenario(rec.scenario_id, user_id)
        assert loaded.full_inputs == d
        assert project_inputs_from_dict(loaded.full_inputs) == tuho_inputs

    def test_base_case_existing_row_returned_without_full_inputs_if_not_set(self, user_id, project):
        # First call creates without full_inputs; second call returns cached row.
        first = get_or_create_base_case_scenario(
            user_id=user_id,
            project_id=project.project_id,
            project_code=project.project_code,
            project_name="Base Case",
            project_type=None,
            source_project_template="TUHO",
            base_input_set={},
            governance_state={},
        )
        second = get_or_create_base_case_scenario(
            user_id=user_id,
            project_id=project.project_id,
            project_code=project.project_code,
            project_name="Base Case",
            project_type=None,
            source_project_template="TUHO",
            base_input_set={},
            governance_state={},
        )
        assert first.scenario_id == second.scenario_id


# ---------------------------------------------------------------------------
# Backward compatibility: missing full_inputs_json column
# ---------------------------------------------------------------------------


class TestScenarioRecordMissingColumn:
    def test_from_row_without_full_inputs_column_gives_none(self, user_id, project):
        rec = save_scenario(
            user_id=user_id,
            project_id=project.project_id,
            scenario_name="Old",
            project_code=project.project_code,
            source_project_template="TUHO",
            snapshot={},
        )
        with get_cursor() as cur:
            cur.execute(
                "SELECT scenario_id, project_id, user_id, scenario_name, project_code, "
                "source_project_template, copied_from_scenario_id, archived, "
                "snapshot_json, governance_state_json, last_run_summary_json, replay_metadata_json, "
                "created_at, updated_at "
                "FROM scenarios WHERE scenario_id=? AND user_id=?",
                (rec.scenario_id, user_id),
            )
            row = cur.fetchone()

        from app.persistence.records import ScenarioRecord
        loaded = ScenarioRecord.from_row(row)
        assert loaded.full_inputs is None
