"""V3-7: Tests for full-fidelity ProjectInputs persistence wiring.

Covers:
- save_project with full_inputs persists the dict to the DB
- get_project_by_code returns full_inputs matching what was saved
- round-trip: project_inputs_from_dict(record.full_inputs) == original inputs
- rows without full_inputs_json (simulated with None) load with full_inputs=None
- update without full_inputs param preserves the stored value
"""
import uuid
import pytest

from app.persistence.db import get_cursor
from app.persistence.projects_repository import save_project, get_project_by_code
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
def oborovo_inputs():
    return run_demo_project("Oborovo").project_inputs


def _save_minimal(user_id: str, project_code: str, full_inputs=None):
    """Save a minimal project row and return the ProjectRecord."""
    return save_project(
        user_id=user_id,
        project_code=project_code,
        project_name=f"Test {project_code}",
        source_project_template="TUHO",
        full_inputs=full_inputs,
    )


# ---------------------------------------------------------------------------
# Test: save and retrieve full_inputs
# ---------------------------------------------------------------------------


class TestSaveProjectFullInputs:
    def test_save_with_full_inputs_stores_dict(self, user_id, tuho_inputs):
        code = f"P{uuid.uuid4().hex[:6]}"
        d = project_inputs_to_dict(tuho_inputs)
        _save_minimal(user_id, code, full_inputs=d)

        record = get_project_by_code(user_id, code)
        assert record is not None
        assert record.full_inputs is not None
        assert record.full_inputs == d

    def test_save_without_full_inputs_gives_none(self, user_id):
        code = f"P{uuid.uuid4().hex[:6]}"
        _save_minimal(user_id, code, full_inputs=None)

        record = get_project_by_code(user_id, code)
        assert record is not None
        assert record.full_inputs is None

    def test_full_inputs_round_trip_tuho(self, user_id, tuho_inputs):
        code = f"P{uuid.uuid4().hex[:6]}"
        d = project_inputs_to_dict(tuho_inputs)
        _save_minimal(user_id, code, full_inputs=d)

        record = get_project_by_code(user_id, code)
        reconstructed = project_inputs_from_dict(record.full_inputs)
        assert reconstructed == tuho_inputs

    def test_full_inputs_round_trip_oborovo(self, user_id, oborovo_inputs):
        code = f"P{uuid.uuid4().hex[:6]}"
        d = project_inputs_to_dict(oborovo_inputs)
        _save_minimal(user_id, code, full_inputs=d)

        record = get_project_by_code(user_id, code)
        reconstructed = project_inputs_from_dict(record.full_inputs)
        assert reconstructed == oborovo_inputs


# ---------------------------------------------------------------------------
# Test: update preserves existing full_inputs when not supplied
# ---------------------------------------------------------------------------


class TestUpdatePreservesFullInputs:
    def test_update_without_full_inputs_preserves_stored_value(self, user_id, tuho_inputs):
        code = f"P{uuid.uuid4().hex[:6]}"
        d = project_inputs_to_dict(tuho_inputs)

        # Initial save with full_inputs
        _save_minimal(user_id, code, full_inputs=d)

        # Update without supplying full_inputs (should preserve)
        save_project(
            user_id=user_id,
            project_code=code,
            project_name="Updated Name",
            source_project_template="TUHO",
            full_inputs=None,
        )

        record = get_project_by_code(user_id, code)
        assert record is not None
        assert record.full_inputs == d

    def test_update_with_new_full_inputs_replaces_stored_value(self, user_id, tuho_inputs, oborovo_inputs):
        code = f"P{uuid.uuid4().hex[:6]}"
        d_tuho = project_inputs_to_dict(tuho_inputs)
        d_oborovo = project_inputs_to_dict(oborovo_inputs)

        _save_minimal(user_id, code, full_inputs=d_tuho)

        save_project(
            user_id=user_id,
            project_code=code,
            project_name="Updated",
            source_project_template="TUHO",
            full_inputs=d_oborovo,
        )

        record = get_project_by_code(user_id, code)
        assert record.full_inputs == d_oborovo


# ---------------------------------------------------------------------------
# Test: ProjectRecord.from_row handles missing full_inputs_json column
# ---------------------------------------------------------------------------


class TestProjectRecordMissingColumn:
    def test_from_row_without_full_inputs_column_gives_none(self, user_id):
        """Simulate a row that was written before V3-7 (no full_inputs_json column)."""
        code = f"P{uuid.uuid4().hex[:6]}"
        _save_minimal(user_id, code, full_inputs=None)

        # Read back via a SELECT that does NOT include full_inputs_json
        with get_cursor() as cur:
            cur.execute(
                "SELECT project_id, user_id, project_code, project_name, "
                "project_type, project_origin, source_project_template, "
                "template_source, baseline_snapshot_json, archived, is_readonly, "
                "governance_state_json, last_run_summary_json, replay_metadata_json, "
                "created_at, updated_at "
                "FROM projects WHERE user_id=? AND project_code=?",
                (user_id, code),
            )
            row = cur.fetchone()

        from app.persistence.records import ProjectRecord
        record = ProjectRecord.from_row(row)
        assert record.full_inputs is None
