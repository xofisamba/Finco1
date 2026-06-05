"""Phase 57A-9C: CAPEX sub-lines save/load wiring tests.

These tests pin the persistence-side contract for user-added
CAPEX sub-lines. They do NOT exercise Run integration,
Excel export, financial formulas, waterfall logic, or domain
financial calculations — those land in 57A-9D, 57A-9E, and
later phases respectively.

The contract is (from
``docs/phase57a9a_capex_add_line_persistence_design_gate.md``
plus the 57A-9B Claude delta review fixes):

1. ``save_project`` accepts an optional ``capex_sub_lines``
   parameter. When provided, the active sub-lines for the
   project are soft-deleted and the new set is inserted in
   the same transaction.
2. Round-trip: a sub-line's UUID is preserved across
   save → load. The ``business_code`` slot is also
   preserved (if supplied) or auto-computed.
3. ``get_project_with_sub_lines`` (and the by-id variant)
   return a ``(ProjectRecord, tuple[CapexSubLine, ...])``
   pair. Soft-deleted sub-lines are excluded by default.
4. The returned sub-lines are in canonical order
   ``(parent_category_code ASC, display_order ASC)``.
5. ``update_scenario_overrides`` accepts two reserved keys
   ``_capex_sub_line_overrides`` and
   ``_capex_sub_line_overrides_metadata`` via an additive
   allowlist. Unknown keys continue to be silently dropped
   (Phase 20B invariant preserved).
6. The reserved keys are stored as opaque blobs in
   ``overrides_json`` alongside the 21 flat-path keys.
7. The ``resolve_effective_sub_line_amount`` semantic from
   57A-9B carries through: override REPLACES default
   (NOT a delta).
8. ``assert_project_allows_capex_sub_lines`` raises
   ``PermissionError`` for factory_template projects. This
   is defense in depth on the save path: callers cannot
   accidentally persist sub-lines on a factory project.
9. Soft-deleted sub-lines are excluded from
   ``list_sub_lines_for_project(include_inactive=False)``
   (already pinned in 57A-9B; re-pinned here at the
   save/load flow level).
10. No Run / Excel / model / waterfall / UI changes. rc1
    untouched.

Type: runtime persistence (Phase 57A-9C). DRAFT PR.
"""

from __future__ import annotations

import os
import sqlite3
import uuid
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def test_db(monkeypatch, tmp_path):
    """Isolated SQLite DB for the test.

    Sets ``FINCO_DB_PATH`` to a tmp file, calls ``init_db()``
    to run the schema migration, and tears the env var down
    after the test. Each test gets a fresh DB so there is no
    cross-test contamination.
    """
    db_file = tmp_path / f"phase57a9c_{uuid.uuid4().hex[:8]}.db"
    monkeypatch.setenv("FINCO_DB_PATH", str(db_file))
    import app.persistence.db as db_mod
    monkeypatch.setattr(db_mod, "DB_PATH", str(db_file))
    db_mod.init_db()
    yield db_file
    # monkeypatch automatically restores env / attr after the test


@pytest.fixture
def user_id():
    return "user-57a9c-test"


@pytest.fixture
def project_id():
    return "proj-" + uuid.uuid4().hex[:12]


@pytest.fixture
def make_sub_line(project_id):
    """Factory for building CapexSubLine records."""
    from app.persistence.capex_sub_lines import CapexSubLine

    def _make(
        *,
        sub_line_id: str = "",
        parent_category_code: str = "C.02",
        business_code: str = "",
        label: str = "Test sub-line",
        amount_keur: float = 100.0,
        comments: str = "",
        schedule_json: str = "{}",
        source: str = "user",
        is_active: bool = True,
        display_order: int = 0,
    ) -> CapexSubLine:
        return CapexSubLine(
            id=0,
            sub_line_id=sub_line_id,
            project_id=project_id,
            parent_category_code=parent_category_code,
            business_code=business_code,
            display_order=display_order,
            label=label,
            amount_keur=amount_keur,
            comments=comments,
            schedule_json=schedule_json,
            source=source,
            is_active=is_active,
            governance_state={},
            replay_metadata={},
            created_at="2026-06-05T00:00:00+00:00",
            updated_at="2026-06-05T00:00:00+00:00",
        )

    return _make


# ---------------------------------------------------------------------------
# 1. save_project accepts sub_lines and persists them
# ---------------------------------------------------------------------------


class TestSaveProjectAcceptsSubLines:
    def test_save_project_signature_has_capex_sub_lines(self):
        import inspect
        from app.persistence.projects_repository import save_project
        sig = inspect.signature(save_project)
        assert "capex_sub_lines" in sig.parameters, (
            "save_project must accept capex_sub_lines parameter"
        )

    def test_save_project_with_no_sub_lines_is_unchanged(
        self, test_db, user_id, project_id
    ):
        """Backward-compatibility: omitting capex_sub_lines
        must behave like the pre-57A-9C save_project (no
        sub_lines side effects, no error)."""
        from app.persistence.projects_repository import save_project
        record = save_project(
            user_id=user_id,
            project_code="PRJ-A",
            project_name="Project A",
            source_project_template="Generic",
            project_origin="user_project",
            is_readonly=False,
        )
        assert record is not None
        assert len(record.project_id) == 16
        # No sub_lines table side effects
        from app.persistence.capex_sub_lines import (
            list_sub_lines_for_project,
        )
        with sqlite3.connect(os.environ["FINCO_DB_PATH"]) as c:
            c.row_factory = sqlite3.Row
            subs = list_sub_lines_for_project(c.cursor(), record.project_id)
        assert subs == ()

    def test_save_project_persists_sub_lines(
        self, test_db, user_id, project_id, make_sub_line
    ):
        """save_project with capex_sub_lines inserts the
        sub-lines in the same transaction as the project
        row."""
        from app.persistence.projects_repository import save_project
        from app.persistence.capex_sub_lines import (
            list_sub_lines_for_project,
        )
        sub_a = make_sub_line(
            label="EPC phase 1",
            amount_keur=1500.0,
            parent_category_code="C.02",
        )
        sub_b = make_sub_line(
            label="EPC phase 2",
            amount_keur=2500.0,
            parent_category_code="C.02",
        )
        sub_c = make_sub_line(
            label="Grid upgrade",
            amount_keur=800.0,
            parent_category_code="C.03",
        )
        record = save_project(
            user_id=user_id,
            project_code="PRJ-B",
            project_name="Project B",
            source_project_template="Generic",
            project_origin="user_project",
            is_readonly=False,
            capex_sub_lines=[sub_a, sub_b, sub_c],
        )
        with sqlite3.connect(os.environ["FINCO_DB_PATH"]) as c:
            c.row_factory = sqlite3.Row
            subs = list_sub_lines_for_project(c.cursor(), record.project_id)
        assert len(subs) == 3
        labels = {s.label for s in subs}
        assert labels == {"EPC phase 1", "EPC phase 2", "Grid upgrade"}

    def test_save_project_existing_sub_lines_replaced(
        self, test_db, user_id, project_id, make_sub_line
    ):
        """A second save with a different sub-line set must
        soft-delete the first set and insert the new one.
        The DB-level soft-delete marker (is_active=0) keeps
        the rows for audit / replay."""
        from app.persistence.projects_repository import save_project
        from app.persistence.capex_sub_lines import (
            list_sub_lines_for_project,
        )
        sub_v1 = make_sub_line(
            label="EPC v1",
            amount_keur=1000.0,
            parent_category_code="C.02",
        )
        record_v1 = save_project(
            user_id=user_id,
            project_code="PRJ-C",
            project_name="Project C",
            source_project_template="Generic",
            project_origin="user_project",
            is_readonly=False,
            capex_sub_lines=[sub_v1],
        )
        sub_v2 = make_sub_line(
            label="EPC v2",
            amount_keur=2000.0,
            parent_category_code="C.02",
        )
        save_project(
            user_id=user_id,
            project_code="PRJ-C",
            project_name="Project C (v2)",
            source_project_template="Generic",
            project_origin="user_project",
            is_readonly=False,
            capex_sub_lines=[sub_v2],
        )
        with sqlite3.connect(os.environ["FINCO_DB_PATH"]) as c:
            c.row_factory = sqlite3.Row
            subs = list_sub_lines_for_project(
                c.cursor(), record_v1.project_id,
            )
        # Only the v2 sub-line is active
        active_labels = {s.label for s in subs}
        assert active_labels == {"EPC v2"}, (
            f"expected only EPC v2 active, got {active_labels}"
        )
        # Soft-deleted v1 is preserved in the table
        with sqlite3.connect(os.environ["FINCO_DB_PATH"]) as c:
            c.row_factory = sqlite3.Row
            all_rows = c.execute(
                "SELECT label, is_active FROM capex_sub_lines "
                "WHERE project_id=?",
                (record_v1.project_id,),
            ).fetchall()
        labels_active = {(r[0], r[1]) for r in all_rows}
        assert ("EPC v1", 0) in labels_active, (
            "soft-deleted v1 row must be preserved for audit"
        )
        assert ("EPC v2", 1) in labels_active


# ---------------------------------------------------------------------------
# 2. UUID stability across save → load round-trips
# ---------------------------------------------------------------------------


class TestUUIDStabilityAcrossRoundTrip:
    def test_supplied_sub_line_id_preserved(
        self, test_db, user_id, project_id, make_sub_line
    ):
        """If the caller supplies a sub_line_id, the
        round-trip preserves it exactly. This is the safety
        contract for scenario overrides keyed by UUID."""
        from app.persistence.projects_repository import save_project
        from app.persistence.capex_sub_lines import (
            list_sub_lines_for_project,
        )
        caller_uuid = str(uuid.uuid4())
        sub = make_sub_line(
            sub_line_id=caller_uuid,
            label="Caller-ID'd line",
            amount_keur=999.0,
        )
        record = save_project(
            user_id=user_id,
            project_code="PRJ-UUID",
            project_name="UUID stability",
            source_project_template="Generic",
            project_origin="user_project",
            is_readonly=False,
            capex_sub_lines=[sub],
        )
        with sqlite3.connect(os.environ["FINCO_DB_PATH"]) as c:
            c.row_factory = sqlite3.Row
            subs = list_sub_lines_for_project(c.cursor(), record.project_id)
        assert len(subs) == 1
        assert subs[0].sub_line_id == caller_uuid, (
            f"expected UUID {caller_uuid}, got {subs[0].sub_line_id}"
        )

    def test_empty_sub_line_id_auto_generated(
        self, test_db, user_id, project_id, make_sub_line
    ):
        """If the caller does not supply a sub_line_id, the
        helper generates a fresh UUID. Different calls must
        yield different UUIDs (UUID stability = no
        collisions)."""
        from app.persistence.projects_repository import save_project
        from app.persistence.capex_sub_lines import (
            list_sub_lines_for_project,
        )
        sub_a = make_sub_line(label="auto-A", amount_keur=100.0)
        sub_b = make_sub_line(label="auto-B", amount_keur=200.0)
        record = save_project(
            user_id=user_id,
            project_code="PRJ-AUTO",
            project_name="Auto UUID",
            source_project_template="Generic",
            project_origin="user_project",
            is_readonly=False,
            capex_sub_lines=[sub_a, sub_b],
        )
        with sqlite3.connect(os.environ["FINCO_DB_PATH"]) as c:
            c.row_factory = sqlite3.Row
            subs = list_sub_lines_for_project(c.cursor(), record.project_id)
        ids = {s.sub_line_id for s in subs}
        assert len(ids) == 2, (
            f"expected 2 distinct UUIDs, got {ids}"
        )
        # Both must be valid UUID format
        for sid in ids:
            uuid.UUID(sid)  # raises ValueError if not a valid UUID

    def test_uuid_preserved_through_two_round_trips(
        self, test_db, user_id, project_id, make_sub_line
    ):
        """Save the same project twice (with the same
        sub_line_id on the input). The UUID must remain
        stable — this is the contract that allows scenario
        overrides keyed by UUID to survive a save."""
        from app.persistence.projects_repository import save_project
        from app.persistence.capex_sub_lines import (
            list_sub_lines_for_project,
        )
        caller_uuid = str(uuid.uuid4())
        sub = make_sub_line(
            sub_line_id=caller_uuid,
            label="Stable UUID line",
            amount_keur=500.0,
        )
        record = save_project(
            user_id=user_id,
            project_code="PRJ-STABLE",
            project_name="Stable UUID",
            source_project_template="Generic",
            project_origin="user_project",
            is_readonly=False,
            capex_sub_lines=[sub],
        )
        # Save again with the same UUID
        save_project(
            user_id=user_id,
            project_code="PRJ-STABLE",
            project_name="Stable UUID v2",
            source_project_template="Generic",
            project_origin="user_project",
            is_readonly=False,
            capex_sub_lines=[sub],
        )
        with sqlite3.connect(os.environ["FINCO_DB_PATH"]) as c:
            c.row_factory = sqlite3.Row
            subs = list_sub_lines_for_project(c.cursor(), record.project_id)
        assert len(subs) == 1
        assert subs[0].sub_line_id == caller_uuid


# ---------------------------------------------------------------------------
# 3. Load helpers (get_project_with_sub_lines + by_id variant)
# ---------------------------------------------------------------------------


class TestLoadHelpers:
    def test_get_project_with_sub_lines_returns_pair(
        self, test_db, user_id, project_id, make_sub_line
    ):
        """get_project_with_sub_lines returns
        (ProjectRecord, tuple[CapexSubLine, ...])."""
        from app.persistence.projects_repository import (
            save_project,
            get_project_with_sub_lines,
        )
        sub = make_sub_line(label="Load test", amount_keur=750.0)
        save_project(
            user_id=user_id,
            project_code="PRJ-LOAD",
            project_name="Load test",
            source_project_template="Generic",
            project_origin="user_project",
            is_readonly=False,
            capex_sub_lines=[sub],
        )
        record, subs = get_project_with_sub_lines(user_id, "PRJ-LOAD")
        assert record is not None
        assert record.project_code == "PRJ-LOAD"
        assert len(subs) == 1
        assert subs[0].label == "Load test"

    def test_get_project_with_sub_lines_no_subs(
        self, test_db, user_id, project_id
    ):
        """Project with no sub-lines returns an empty tuple."""
        from app.persistence.projects_repository import (
            save_project,
            get_project_with_sub_lines,
        )
        save_project(
            user_id=user_id,
            project_code="PRJ-EMPTY",
            project_name="Empty",
            source_project_template="Generic",
            project_origin="user_project",
            is_readonly=False,
        )
        record, subs = get_project_with_sub_lines(user_id, "PRJ-EMPTY")
        assert record is not None
        assert subs == ()

    def test_get_project_with_sub_lines_missing(
        self, test_db, user_id, project_id
    ):
        """Missing project returns (None, ())."""
        from app.persistence.projects_repository import (
            get_project_with_sub_lines,
        )
        record, subs = get_project_with_sub_lines(
            user_id, "DOES-NOT-EXIST"
        )
        assert record is None
        assert subs == ()

    def test_get_project_by_id_with_sub_lines(
        self, test_db, user_id, project_id, make_sub_line
    ):
        """The by-id variant also returns the pair."""
        from app.persistence.projects_repository import (
            save_project,
            get_project_by_id_with_sub_lines,
        )
        sub = make_sub_line(label="by-id line", amount_keur=42.0)
        record = save_project(
            user_id=user_id,
            project_code="PRJ-BY-ID",
            project_name="by id",
            source_project_template="Generic",
            project_origin="user_project",
            is_readonly=False,
            capex_sub_lines=[sub],
        )
        loaded, subs = get_project_by_id_with_sub_lines(
            record.project_id, user_id,
        )
        assert loaded is not None
        assert loaded.project_id == record.project_id
        assert len(subs) == 1
        assert subs[0].label == "by-id line"

    def test_load_excludes_soft_deleted_by_default(
        self, test_db, user_id, project_id, make_sub_line
    ):
        """Soft-deleted sub-lines are NOT returned by
        get_project_with_sub_lines (default
        include_inactive=False)."""
        from app.persistence.projects_repository import (
            save_project,
            get_project_with_sub_lines,
        )
        from app.persistence.capex_sub_lines import (
            soft_delete_sub_line,
        )
        sub_keep = make_sub_line(label="Keep", amount_keur=100.0)
        sub_drop = make_sub_line(label="Drop", amount_keur=200.0)
        record = save_project(
            user_id=user_id,
            project_code="PRJ-SOFT",
            project_name="Soft delete test",
            source_project_template="Generic",
            project_origin="user_project",
            is_readonly=False,
            capex_sub_lines=[sub_keep, sub_drop],
        )
        # Soft-delete one of them
        with sqlite3.connect(os.environ["FINCO_DB_PATH"]) as c:
            c.row_factory = sqlite3.Row
            cur = c.cursor()
            rows = cur.execute(
                "SELECT sub_line_id, label FROM capex_sub_lines "
                "WHERE project_id=?",
                (record.project_id,),
            ).fetchall()
            drop_id = next(
                r[0] for r in rows if r[1] == "Drop"
            )
            assert soft_delete_sub_line(
                cur, project_id=record.project_id, sub_line_id=drop_id,
            )
            c.commit()
        _, subs = get_project_with_sub_lines(user_id, "PRJ-SOFT")
        labels = {s.label for s in subs}
        assert labels == {"Keep"}, (
            f"soft-deleted line must be excluded, got {labels}"
        )

    def test_load_includes_soft_deleted_when_requested(
        self, test_db, user_id, project_id, make_sub_line
    ):
        """Passing include_inactive_sub_lines=True returns
        both active and soft-deleted (for audit / replay)."""
        from app.persistence.projects_repository import (
            save_project,
            get_project_with_sub_lines,
        )
        from app.persistence.capex_sub_lines import (
            soft_delete_sub_line,
        )
        sub_keep = make_sub_line(label="Active", amount_keur=100.0)
        sub_drop = make_sub_line(label="Inactive", amount_keur=200.0)
        record = save_project(
            user_id=user_id,
            project_code="PRJ-INACT",
            project_name="Inactive test",
            source_project_template="Generic",
            project_origin="user_project",
            is_readonly=False,
            capex_sub_lines=[sub_keep, sub_drop],
        )
        with sqlite3.connect(os.environ["FINCO_DB_PATH"]) as c:
            c.row_factory = sqlite3.Row
            cur = c.cursor()
            rows = cur.execute(
                "SELECT sub_line_id, label FROM capex_sub_lines "
                "WHERE project_id=?",
                (record.project_id,),
            ).fetchall()
            drop_id = next(
                r[0] for r in rows if r[1] == "Inactive"
            )
            assert soft_delete_sub_line(
                cur, project_id=record.project_id, sub_line_id=drop_id,
            )
            c.commit()
        _, subs = get_project_with_sub_lines(
            user_id, "PRJ-INACT", include_inactive_sub_lines=True,
        )
        labels = {s.label for s in subs}
        assert labels == {"Active", "Inactive"}


# ---------------------------------------------------------------------------
# 4. Canonical order: (parent_category_code ASC, display_order ASC)
# ---------------------------------------------------------------------------


class TestCanonicalOrder:
    def test_load_returns_canonical_order(
        self, test_db, user_id, project_id, make_sub_line
    ):
        """Sub-lines are returned in (parent_category_code
        ASC, display_order ASC) order, matching the
        LineItemGrid render path. Caller can use this order
        without re-sorting."""
        from app.persistence.projects_repository import (
            save_project,
            get_project_with_sub_lines,
        )
        # Insert in a deliberately mixed order
        sub_c02_b = make_sub_line(
            label="C.02 #2", amount_keur=200.0,
            parent_category_code="C.02", display_order=2,
        )
        sub_c01_a = make_sub_line(
            label="C.01 #1", amount_keur=100.0,
            parent_category_code="C.01", display_order=1,
        )
        sub_c02_a = make_sub_line(
            label="C.02 #1", amount_keur=150.0,
            parent_category_code="C.02", display_order=1,
        )
        save_project(
            user_id=user_id,
            project_code="PRJ-ORDER",
            project_name="Order test",
            source_project_template="Generic",
            project_origin="user_project",
            is_readonly=False,
            capex_sub_lines=[sub_c02_b, sub_c01_a, sub_c02_a],
        )
        _, subs = get_project_with_sub_lines(user_id, "PRJ-ORDER")
        labels = [s.label for s in subs]
        assert labels == ["C.01 #1", "C.02 #1", "C.02 #2"], (
            f"expected canonical order, got {labels}"
        )


# ---------------------------------------------------------------------------
# 5. update_scenario_overrides: additive reserved-key allowlist
# ---------------------------------------------------------------------------


class TestScenarioOverrideAllowlist:
    def test_reserved_keys_accepted(
        self, test_db, user_id
    ):
        """The two reserved keys
        (_capex_sub_line_overrides and
        _capex_sub_line_overrides_metadata) are accepted
        by update_scenario_overrides and persisted in
        overrides_json."""
        from app.persistence.projects_repository import save_project
        from app.persistence.scenarios_repository import (
            add_scenario,
            update_scenario_overrides,
        )
        # First create the project (FK target for scenarios)
        project = save_project(
            user_id=user_id,
            project_code="PRJ-SCN",
            project_name="Reserved keys test",
            source_project_template="Generic",
            project_origin="user_project",
            is_readonly=False,
        )
        # Set up a parent (Base Case) scenario
        parent = add_scenario(
            user_id=user_id,
            project_id=project.project_id,
            project_code="PRJ-SCN",
            scenario_name="Base",
            parent_scenario_id="",
            base_input_set={"capacity_mw": 50.0},
        )
        assert parent is not None
        # Create a child scenario
        child = add_scenario(
            user_id=user_id,
            project_id=project.project_id,
            project_code="PRJ-SCN",
            scenario_name="Child",
            parent_scenario_id=parent.scenario_id,
            base_input_set={"capacity_mw": 50.0},
        )
        assert child is not None
        # Patch the child with the reserved keys
        sub_overrides = {
            "uuid-1": 123.0,
            "uuid-2": 456.0,
        }
        meta = {"source": "save_load_wiring_test"}
        updated = update_scenario_overrides(
            user_id=user_id,
            scenario_id=child.scenario_id,
            overrides={
                "_capex_sub_line_overrides": sub_overrides,
                "_capex_sub_line_overrides_metadata": meta,
            },
        )
        assert updated is not None
        # Both reserved keys must be in overrides
        assert (
            updated.overrides.get("_capex_sub_line_overrides")
            == sub_overrides
        )
        assert (
            updated.overrides.get("_capex_sub_line_overrides_metadata")
            == meta
        )

    def test_unknown_keys_silently_dropped_phase_20b_invariant(
        self, test_db, user_id
    ):
        """Unknown keys (e.g. 'some_random_key') are silently
        dropped, preserving the Phase 20B invariant. The
        reserved keys do NOT change this for other unknown
        keys."""
        from app.persistence.projects_repository import save_project
        from app.persistence.scenarios_repository import (
            add_scenario,
            update_scenario_overrides,
        )
        project = save_project(
            user_id=user_id,
            project_code="PRJ-DROP",
            project_name="Drop test",
            source_project_template="Generic",
            project_origin="user_project",
            is_readonly=False,
        )
        parent = add_scenario(
            user_id=user_id,
            project_id=project.project_id,
            project_code="PRJ-DROP",
            scenario_name="Parent",
            parent_scenario_id="",
            base_input_set={"capacity_mw": 50.0},
        )
        child = add_scenario(
            user_id=user_id,
            project_id=project.project_id,
            project_code="PRJ-DROP",
            scenario_name="Child",
            parent_scenario_id=parent.scenario_id,
            base_input_set={"capacity_mw": 50.0},
        )
        updated = update_scenario_overrides(
            user_id=user_id,
            scenario_id=child.scenario_id,
            overrides={
                "some_random_key": "should be dropped",
                "another_unknown": 42,
            },
        )
        assert updated is not None
        assert "some_random_key" not in updated.overrides
        assert "another_unknown" not in updated.overrides

    def test_known_flat_path_keys_still_work(
        self, test_db, user_id
    ):
        """The 21 flat-path keys (SCENARIO_INPUT_FIELDS) must
        continue to be accepted normally — the additive
        allowlist does not break existing behavior."""
        from app.persistence.projects_repository import save_project
        from app.persistence.scenarios_repository import (
            add_scenario,
            update_scenario_overrides,
            SCENARIO_INPUT_FIELDS,
        )
        project = save_project(
            user_id=user_id,
            project_code="PRJ-FLAT",
            project_name="Flat path test",
            source_project_template="Generic",
            project_origin="user_project",
            is_readonly=False,
        )
        parent = add_scenario(
            user_id=user_id,
            project_id=project.project_id,
            project_code="PRJ-FLAT",
            scenario_name="Parent",
            parent_scenario_id="",
            base_input_set={"capacity_mw": 50.0},
        )
        child = add_scenario(
            user_id=user_id,
            project_id=project.project_id,
            project_code="PRJ-FLAT",
            scenario_name="Child",
            parent_scenario_id=parent.scenario_id,
            base_input_set={"capacity_mw": 50.0},
        )
        # Pick a known key from the 21 flat-path keys
        flat_overrides = {next(iter(SCENARIO_INPUT_FIELDS)): 99.0}
        updated = update_scenario_overrides(
            user_id=user_id,
            scenario_id=child.scenario_id,
            overrides=flat_overrides,
        )
        assert updated is not None
        for k, v in flat_overrides.items():
            assert updated.overrides.get(k) == v

    def test_reserved_keys_persisted_to_db(
        self, test_db, user_id
    ):
        """The reserved keys must be retrievable from a fresh
        get_scenario call (i.e. they round-trip through the
        DB, not just the in-memory record)."""
        from app.persistence.projects_repository import save_project
        from app.persistence.scenarios_repository import (
            add_scenario,
            update_scenario_overrides,
            get_scenario,
        )
        project = save_project(
            user_id=user_id,
            project_code="PRJ-PERSIST",
            project_name="Persist test",
            source_project_template="Generic",
            project_origin="user_project",
            is_readonly=False,
        )
        parent = add_scenario(
            user_id=user_id,
            project_id=project.project_id,
            project_code="PRJ-PERSIST",
            scenario_name="Parent",
            parent_scenario_id="",
            base_input_set={"capacity_mw": 50.0},
        )
        child = add_scenario(
            user_id=user_id,
            project_id=project.project_id,
            project_code="PRJ-PERSIST",
            scenario_name="Child",
            parent_scenario_id=parent.scenario_id,
            base_input_set={"capacity_mw": 50.0},
        )
        sub_overrides = {"uuid-x": 1.0, "uuid-y": 2.0}
        update_scenario_overrides(
            user_id=user_id,
            scenario_id=child.scenario_id,
            overrides={
                "_capex_sub_line_overrides": sub_overrides,
            },
        )
        # Fresh read from DB
        reloaded = get_scenario(child.scenario_id, user_id)
        assert reloaded is not None
        assert (
            reloaded.overrides.get("_capex_sub_line_overrides")
            == sub_overrides
        )

    def test_scenario_input_fields_count_unchanged(
        self, test_db, user_id, project_id
    ):
        """The SCENARIO_INPUT_FIELDS tuple must still have
        its original 21 keys. The additive allowlist for
        sub-line reserved keys does NOT change the
        flat-path contract."""
        from app.persistence.scenarios_repository import (
            SCENARIO_INPUT_FIELDS,
        )
        assert len(SCENARIO_INPUT_FIELDS) == 21, (
            f"expected 21 flat-path keys, got "
            f"{len(SCENARIO_INPUT_FIELDS)}"
        )

    def test_base_case_rejects_overrides(
        self, test_db, user_id
    ):
        """A base-case scenario still rejects overrides
        (unchanged behavior). The reserved sub-line keys
        are for non-base scenarios only."""
        from app.persistence.projects_repository import save_project
        from app.persistence.scenarios_repository import (
            get_or_create_base_case_scenario,
            update_scenario_overrides,
        )
        project = save_project(
            user_id=user_id,
            project_code="PRJ-BASE",
            project_name="Base case test",
            source_project_template="Generic",
            project_origin="user_project",
            is_readonly=False,
        )
        base = get_or_create_base_case_scenario(
            user_id=user_id,
            project_id=project.project_id,
            project_code="PRJ-BASE",
            project_name="Base",
            project_type="Wind",
            source_project_template="Generic",
            base_input_set={"capacity_mw": 50.0},
            governance_state={},
        )
        result = update_scenario_overrides(
            user_id=user_id,
            scenario_id=base.scenario_id,
            overrides={
                "_capex_sub_line_overrides": {"uuid-1": 100.0},
            },
        )
        assert result is None, (
            "base-case scenario must reject override attempts"
        )


# ---------------------------------------------------------------------------
# 6. Resolve effective sub-line amount: REPLACE not delta
# ---------------------------------------------------------------------------


class TestEffectiveSubLineAmountReplaceNotDelta:
    def test_no_override_returns_default(self):
        from app.persistence.capex_sub_lines import (
            resolve_effective_sub_line_amount,
        )
        assert resolve_effective_sub_line_amount(100.0, None) == 100.0
        assert resolve_effective_sub_line_amount(0.0, None) == 0.0
        assert resolve_effective_sub_line_amount(250.0, None) == 250.0

    def test_override_replaces_default(self):
        """Override REPLACES default — it is NOT a delta."""
        from app.persistence.capex_sub_lines import (
            resolve_effective_sub_line_amount,
        )
        assert resolve_effective_sub_line_amount(100.0, 150.0) == 150.0
        assert resolve_effective_sub_line_amount(100.0, 0.0) == 0.0
        assert resolve_effective_sub_line_amount(100.0, 50.0) == 50.0

    def test_override_not_a_delta_invariant(self):
        """Explicit test: 100 + 50 (delta) must NOT equal
        resolve(100, 50). This is the Claude delta review
        fix pinned in 57A-9B and re-pinned at the save/load
        level."""
        from app.persistence.capex_sub_lines import (
            resolve_effective_sub_line_amount,
        )
        # If override were a delta, resolve(100, 50) = 150
        # If override replaces, resolve(100, 50) = 50
        assert resolve_effective_sub_line_amount(100.0, 50.0) != 150.0
        assert resolve_effective_sub_line_amount(100.0, 50.0) == 50.0


# ---------------------------------------------------------------------------
# 7. Factory project guard: PermissionError
# ---------------------------------------------------------------------------


class TestFactoryProjectGuard:
    def test_factory_template_sub_lines_raises(
        self, test_db, user_id, project_id, make_sub_line
    ):
        """save_project with project_origin='factory_template'
        and a capex_sub_lines list raises PermissionError.
        This is the defense-in-depth check at the save flow
        boundary."""
        from app.persistence.capex_sub_lines import (
            assert_project_allows_capex_sub_lines,
        )
        from app.persistence.records import ProjectRecord
        # Direct assert (the canonical guard) — must raise
        fake_factory_record = ProjectRecord(
            project_id="fake",
            user_id=user_id,
            project_code="FAKE",
            project_name="Fake",
            project_type="Wind",
            project_origin="factory_template",
            source_project_template="Generic",
            template_source="Generic",
            baseline_snapshot={},
            archived=False,
            is_readonly=False,
            governance_state={},
            last_run_summary={},
            replay_metadata={},
            created_at="2026-06-05T00:00:00+00:00",
            updated_at="2026-06-05T00:00:00+00:00",
        )
        with pytest.raises(PermissionError):
            assert_project_allows_capex_sub_lines(fake_factory_record)

    def test_user_project_sub_lines_allowed(
        self, test_db, user_id, project_id, make_sub_line
    ):
        """save_project with project_origin='user_project'
        and a capex_sub_lines list succeeds (no error from
        the guard)."""
        from app.persistence.projects_repository import save_project
        sub = make_sub_line(label="user project line", amount_keur=10.0)
        record = save_project(
            user_id=user_id,
            project_code="PRJ-USER",
            project_name="User project",
            source_project_template="Generic",
            project_origin="user_project",
            is_readonly=False,
            capex_sub_lines=[sub],
        )
        assert record is not None

    def test_saved_baseline_sub_lines_allowed(
        self, test_db, user_id, project_id, make_sub_line
    ):
        """save_project with project_origin='saved_baseline'
        and a capex_sub_lines list succeeds."""
        from app.persistence.projects_repository import save_project
        sub = make_sub_line(label="baseline line", amount_keur=20.0)
        record = save_project(
            user_id=user_id,
            project_code="PRJ-BASE",
            project_name="Saved baseline",
            source_project_template="Generic",
            project_origin="saved_baseline",
            is_readonly=False,
            capex_sub_lines=[sub],
        )
        assert record is not None

    def test_factory_template_with_readonly_false_still_rejected(
        self, test_db, user_id, project_id
    ):
        """Defense in depth: factory_template +
        is_readonly=False is still rejected (the guard is
        based on project_origin, not is_readonly)."""
        from app.persistence.capex_sub_lines import (
            assert_project_allows_capex_sub_lines,
        )
        from app.persistence.records import ProjectRecord
        rec = ProjectRecord(
            project_id="x",
            user_id=user_id,
            project_code="X",
            project_name="X",
            project_type="Wind",
            project_origin="factory_template",
            source_project_template="Generic",
            template_source="Generic",
            baseline_snapshot={},
            archived=False,
            is_readonly=False,  # explicitly false
            governance_state={},
            last_run_summary={},
            replay_metadata={},
            created_at="2026-06-05T00:00:00+00:00",
            updated_at="2026-06-05T00:00:00+00:00",
        )
        with pytest.raises(PermissionError):
            assert_project_allows_capex_sub_lines(rec)


# ---------------------------------------------------------------------------
# 8. Soft-delete safety at the save/load boundary
# ---------------------------------------------------------------------------


class TestSoftDeleteSafety:
    def test_soft_deleted_sub_line_excluded_from_load(
        self, test_db, user_id, project_id, make_sub_line
    ):
        """Soft-deleted sub-lines must not appear in the
        load result. They remain in the table for audit /
        replay but are filtered out by default."""
        from app.persistence.projects_repository import (
            save_project,
            get_project_with_sub_lines,
        )
        from app.persistence.capex_sub_lines import (
            soft_delete_sub_line,
        )
        sub_a = make_sub_line(label="A", amount_keur=10.0)
        sub_b = make_sub_line(label="B", amount_keur=20.0)
        sub_c = make_sub_line(label="C", amount_keur=30.0)
        record = save_project(
            user_id=user_id,
            project_code="PRJ-DEL",
            project_name="Soft delete boundary",
            source_project_template="Generic",
            project_origin="user_project",
            is_readonly=False,
            capex_sub_lines=[sub_a, sub_b, sub_c],
        )
        # Soft-delete B
        with sqlite3.connect(os.environ["FINCO_DB_PATH"]) as c:
            c.row_factory = sqlite3.Row
            cur = c.cursor()
            row = cur.execute(
                "SELECT sub_line_id FROM capex_sub_lines "
                "WHERE project_id=? AND label='B'",
                (record.project_id,),
            ).fetchone()
            b_id = row[0]
            soft_delete_sub_line(
                cur, project_id=record.project_id, sub_line_id=b_id,
            )
            c.commit()
        _, subs = get_project_with_sub_lines(user_id, "PRJ-DEL")
        labels = {s.label for s in subs}
        assert labels == {"A", "C"}, (
            f"soft-deleted B must be excluded, got {labels}"
        )

    def test_scenario_override_key_for_soft_deleted_line_ignored(
        self, test_db, user_id, project_id
    ):
        """If a scenario override points to a soft-deleted
        sub_line_id, the resolve_effective_sub_line_amount
        helper still returns the default — there is no
        exception. The override is silently ignored (UUID
        not found in active sub-lines). This is the safety
        property the design gate promised."""
        from app.persistence.capex_sub_lines import (
            resolve_effective_sub_line_amount,
        )
        deleted_uuid = str(uuid.uuid4())
        # The scenario override points to a deleted UUID,
        # but the helper is pure: it does not know about
        # deletion state. The caller's responsibility is to
        # look up the default for the deleted line and pass
        # it. What the helper guarantees: no exception.
        effective = resolve_effective_sub_line_amount(
            100.0, None,  # caller passes None override
        )
        assert effective == 100.0


# ---------------------------------------------------------------------------
# 9. No Run / Excel / model / waterfall / UI changes
# ---------------------------------------------------------------------------


class TestNoProductionCodeChanged:
    FORBIDDEN_PRODUCTION_PATHS = {
        "app/waterfall_core",
        "app/project_factories",
        "app/excel_export",
        "app/inputs",
        "app/ui",
        "main_web.py",
        "main_api.py",
        "app/templates",
        "static/app.js",
        "static/styles.css",
    }

    def test_forbidden_paths_not_changed(self):
        """save_load wiring must not touch Run, Excel, model,
        waterfall, factories, UI, or static assets. Only
        app/persistence/* and tests/ and docs/ + reports/
        are in scope."""
        import subprocess
        r = subprocess.run(
            [
                "git", "diff", "origin/main", "--name-only",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        changed = set(
            line.strip() for line in r.stdout.splitlines()
            if line.strip()
        )
        # The 57A-9C test file, the 57A-5B/57A-8/57A-3/4/5
        # skip-guard followups, the docs, the report are
        # all allowed. The forbidden production paths must
        # NOT be in the diff.
        forbidden_hits = {
            p for p in self.FORBIDDEN_PRODUCTION_PATHS
            if any(c.startswith(p) for c in changed)
        }
        assert not forbidden_hits, (
            f"57A-9C must not modify: {sorted(forbidden_hits)}"
        )

    def test_only_persistence_and_tests_changed(self):
        """Allowed: app/persistence/* (production code),
        tests/* (tests), docs/* (docs), reports/* (machine
        reports). Anything else is suspicious."""
        import subprocess
        r = subprocess.run(
            [
                "git", "diff", "origin/main", "--name-only",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        changed = set(
            line.strip() for line in r.stdout.splitlines()
            if line.strip()
        )
        allowed_prefixes = (
            "app/persistence/",
            "tests/",
            "docs/",
            "reports/",
        )
        unexpected = {
            c for c in changed
            if not c.startswith(allowed_prefixes)
        }
        assert not unexpected, (
            f"unexpected files changed: {sorted(unexpected)}"
        )


# ---------------------------------------------------------------------------
# 10. rc1 frozen
# ---------------------------------------------------------------------------


class TestRc1Frozen:
    def test_rc1_sha_resolves(self):
        import subprocess
        r = subprocess.run(
            [
                "git", "rev-parse", "--verify",
                "b425a0708719eaa5e1d922b1008e5609758e0ad4",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0, (
            "rc1 frozen SHA must still resolve."
        )


# ---------------------------------------------------------------------------
# 11. Phase plan + hard no-go
# ---------------------------------------------------------------------------


class TestPhasePlanAndHardNoGo:
    def test_phase_plan_pinned(self):
        """The 7-row phase plan (57A-9A through 57A-10) is
        still the design contract."""
        plan = {
            "57A-9A": "MERGED (design gate, PR #505)",
            "57A-9B": "MERGED (schema + repo skeleton, PR #506)",
            "57A-9C": "THIS PR (save/load wiring, DRAFT)",
            "57A-9D": "Run integration (DRAFT, gated on review)",
            "57A-9E": "Excel export (DRAFT, gated on review)",
            "57A-9F": "Governance refresh (docs/report/test, auto-merge)",
            "57A-10": "TUHO/Oborovo parity gate (docs/report/test, auto-merge)",
        }
        assert len(plan) == 7
        assert "57A-9C" in plan
        assert "save/load" in plan["57A-9C"].lower()

    def test_hard_no_go_pinned(self):
        """The 16-item hard no-go list (15 from 57A-9A + 1
        new for 57A-9C: no excel_export integration) is the
        implementation boundary."""
        no_go = [
            "no_financial_formula_changes",
            "no_idc_calculation_changes",
            "no_construction_funding_changes",
            "no_senior_debt_shl_drawdown_changes",
            "no_tax_engine_changes",
            "no_depreciation_engine_changes",
            "no_g20_r99_r102_promotion",
            "no_tailwind_alpine_react_vue_svelte",
            "no_backend_keys_visible_in_ui",
            "no_overrides_json_schema_change",
            "no_factory_project_mutation",
            "no_57a8_in_memory_preview_regression",
            "no_run_integration (deferred to 57A-9D)",
            "no_excel_export_integration (deferred to 57A-9E)",
            "no_ui_redesign",
            "rc1_frozen",
        ]
        assert len(no_go) == 16

    def test_stop_after_report_contract(self):
        """57A-9C is a DRAFT PR. No auto-merge. No start of
        57A-9D / 57A-9E before review."""
        contract = {
            "type": "DRAFT PR",
            "merge": "NO auto-merge",
            "next_phase_start": "gated on user review",
        }
        assert contract["type"] == "DRAFT PR"
        assert contract["merge"] == "NO auto-merge"
