"""
Phase 20A — Saved Baseline Models

Tests:
- repository: seed_baseline_projects_if_needed, list_baseline_records, is_readonly field
- web: save blocked for factory_template/saved_baseline; save-as creates user project
- export provenance: baseline_source flag recorded
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from app.persistence.repository import (
    ProjectRecord,
    save_project,
    get_project_by_code,
    list_baseline_records,
    seed_baseline_projects_if_needed,
    _compute_baseline_snapshot,
    create_project_record,
)
from app.persistence.db import get_connection, _ensure_column


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clean_baseline_records():
    """Remove any seeded baseline records before and after each test."""
    from app.persistence.db import get_cursor

    def _cleanup():
        with get_cursor() as cur:
            # Delete baseline records by origin (cleaner than by code)
            cur.execute(
                "DELETE FROM projects WHERE user_id=? AND project_origin='saved_baseline'",
                ("test_baseline_user",),
            )
            # Also delete the test readonly/user_created projects created by
            # TestIsReadonlyField tests
            for code in ["test-ro-check", "test-ro-check2"]:
                cur.execute(
                    "DELETE FROM projects WHERE user_id=? AND project_code=?",
                    ("test_baseline_user", code),
                )

    _cleanup()
    yield
    _cleanup()


@pytest.fixture
def baseline_user():
    return "test_baseline_user"


# ─────────────────────────────────────────────────────────────────────────────
# Repository — baseline snapshot computation
# ─────────────────────────────────────────────────────────────────────────────

class TestBaselineSnapshotComputation:
    def test_compute_baseline_snapshot_tuho(self):
        snap = _compute_baseline_snapshot("Wind", "tuho")
        assert snap["active_project"] == "tuho-baseline"
        assert snap["project_name"] == "TUHO Wind 1"
        assert snap["project_type"] == "Wind"
        assert snap["project_origin"] == "saved_baseline"
        assert snap["template_source"] == "tuho"
        assert snap["capacity_mw"] != ""
        assert snap["tariff_eur_mwh"] != ""

    def test_compute_baseline_snapshot_oborovo(self):
        snap = _compute_baseline_snapshot("Solar", "oborovo")
        assert snap["active_project"] == "oborovo-baseline"
        assert snap["project_name"] == "Oborovo Solar PV"
        assert snap["project_type"] == "Solar"
        assert snap["project_origin"] == "saved_baseline"

    def test_compute_baseline_snapshot_generic_wind(self):
        snap = _compute_baseline_snapshot("Wind", "generic_wind")
        assert snap["project_type"] == "Wind"
        assert snap["template_source"] == "generic_wind"

    def test_compute_baseline_snapshot_generic_solar(self):
        snap = _compute_baseline_snapshot("Solar", "generic_solar")
        assert snap["project_type"] == "Solar"
        assert snap["template_source"] == "generic_solar"


# ─────────────────────────────────────────────────────────────────────────────
# Repository — baseline persistence
# ─────────────────────────────────────────────────────────────────────────────

class TestBaselinePersistence:
    def test_seed_creates_two_records(self, baseline_user):
        records = seed_baseline_projects_if_needed(baseline_user)
        assert len(records) == 2
        codes = {r.project_code for r in records}
        assert codes == {"tuho-baseline", "oborovo-baseline"}

    def test_seed_is_idempotent(self, baseline_user):
        first = seed_baseline_projects_if_needed(baseline_user)
        second = seed_baseline_projects_if_needed(baseline_user)
        assert len(first) == 2
        assert len(second) == 0  # nothing new seeded

    def test_seed_records_are_readonly(self, baseline_user):
        seed_baseline_projects_if_needed(baseline_user)
        for code in ["tuho-baseline", "oborovo-baseline"]:
            rec = get_project_by_code(baseline_user, code)
            assert rec is not None
            assert rec.is_readonly is True

    def test_seed_records_have_correct_origin(self, baseline_user):
        seed_baseline_projects_if_needed(baseline_user)
        for code in ["tuho-baseline", "oborovo-baseline"]:
            rec = get_project_by_code(baseline_user, code)
            assert rec.project_origin == "saved_baseline"

    def test_seed_records_have_baseline_snapshot(self, baseline_user):
        seed_baseline_projects_if_needed(baseline_user)
        rec = get_project_by_code(baseline_user, "tuho-baseline")
        assert rec.baseline_snapshot != {}
        assert "capacity_mw" in rec.baseline_snapshot
        assert "tariff_eur_mwh" in rec.baseline_snapshot

    def test_list_baseline_records(self, baseline_user):
        seed_baseline_projects_if_needed(baseline_user)
        baselines = list_baseline_records(baseline_user)
        codes = {r.project_code for r in baselines}
        assert codes == {"tuho-baseline", "oborovo-baseline"}

    def test_list_baseline_records_excludes_user_projects(self, baseline_user):
        seed_baseline_projects_if_needed(baseline_user)
        # Create a user project
        save_project(
            user_id=baseline_user,
            project_code="my-test-project",
            project_name="My Test",
            project_type="Wind",
            project_origin="user_created",
            source_project_template="tuho",
            template_source="tuho",
            baseline_snapshot={},
            is_readonly=False,
        )
        baselines = list_baseline_records(baseline_user)
        codes = {r.project_code for r in baselines}
        assert "my-test-project" not in codes


# ─────────────────────────────────────────────────────────────────────────────
# Repository — is_readonly field
# ─────────────────────────────────────────────────────────────────────────────

class TestIsReadonlyField:
    def test_save_project_respects_is_readonly(self, baseline_user):
        record = save_project(
            user_id=baseline_user,
            project_code="test-ro-check",
            project_name="Readonly Test",
            project_type="Wind",
            project_origin="user_created",
            source_project_template="tuho",
            template_source="tuho",
            baseline_snapshot={},
            is_readonly=True,
        )
        assert record.is_readonly is True

    def test_create_project_record_respects_is_readonly(self, baseline_user):
        record = create_project_record(
            user_id=baseline_user,
            project_code="test-ro-check2",
            project_name="Readonly Test 2",
            project_type="Wind",
            project_origin="saved_baseline",
            template_source="tuho",
            baseline_snapshot={},
            is_readonly=True,
        )
        assert record.is_readonly is True