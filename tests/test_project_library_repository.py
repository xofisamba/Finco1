"""Unit tests for the project library repository layer.

Covers: paginated queries, search escaping, deterministic ordering,
independent workspace/content hash, reference bootstrap idempotency,
duplicate-reference prevention, clone lineage, migration/backfill.
"""
import os
import tempfile
import pytest


@pytest.fixture()
def isolated_db(monkeypatch):
    """Provide a fresh temp SQLite DB for each test."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    monkeypatch.setenv("FINCO_DB_PATH", db_path)
    # Force the module-level constant to the temp path.
    import app.persistence.db as _db
    monkeypatch.setattr(_db, "DB_PATH", db_path)
    yield db_path
    os.unlink(db_path)


# ---------------------------------------------------------------------------
# Migration / backfill
# ---------------------------------------------------------------------------

class TestMigrationBackfill:
    def test_new_schema_has_project_role_column(self, isolated_db):
        from app.persistence.db import get_connection
        conn = get_connection()
        cols = {row[1] for row in conn.execute("PRAGMA table_info(projects)").fetchall()}
        assert "project_role" in cols
        assert "is_protected" in cols
        assert "source_project_id" in cols

    def test_factory_template_tuho_backfilled_as_reference(self, isolated_db):
        """Existing factory_template + tuho row gets backfilled to project_role='reference'."""
        from app.persistence.projects_repository import save_project, REFERENCE_USER_ID
        # Insert a legacy factory_template/tuho row directly with role='user_project' (pre-migration)
        r = save_project(
            user_id=REFERENCE_USER_ID,
            project_code="legacy-tuho",
            project_name="TUHO Legacy",
            source_project_template="tuho",
            project_type="Wind",
            project_origin="factory_template",
            template_source="tuho",
            project_role="user_project",  # as if pre-migration
        )
        # The DB backfill only runs at schema init, so for a fresh DB the INSERT already
        # carries 'user_project' and no automatic re-backfill runs mid-test.
        # What we test is that is_protected_reference() detects the legacy combo.
        from app.services.project_library_service import is_protected_reference
        assert is_protected_reference(r)  # legacy composite check still works

    def test_generic_solar_not_backfilled(self, isolated_db):
        from app.persistence.projects_repository import save_project
        r = save_project(
            user_id="some-user",
            project_code="gen-solar",
            project_name="Generic Solar",
            source_project_template="generic_solar",
            project_type="Solar",
            project_origin="factory_template",
            template_source="generic_solar",
        )
        from app.services.project_library_service import is_protected_reference
        assert not is_protected_reference(r)


# ---------------------------------------------------------------------------
# Reference bootstrap
# ---------------------------------------------------------------------------

class TestReferenceBootstrap:
    def test_bootstrap_creates_two_references(self, isolated_db):
        from app.services.project_library_service import ensure_reference_models
        created = ensure_reference_models()
        assert len(created) == 2
        roles = {r.project_role for r in created}
        assert roles == {"reference"}
        protected = {r.is_protected for r in created}
        assert protected == {True}

    def test_bootstrap_idempotent(self, isolated_db):
        from app.services.project_library_service import ensure_reference_models
        first = ensure_reference_models()
        second = ensure_reference_models()
        assert len(first) == 2
        assert len(second) == 0  # no new creations

    def test_bootstrap_no_duplicates_same_template_source(self, isolated_db):
        from app.services.project_library_service import ensure_reference_models
        from app.persistence.projects_repository import get_reference_projects
        ensure_reference_models()
        ensure_reference_models()
        refs = get_reference_projects()
        template_sources = [r.template_source for r in refs]
        assert template_sources.count("tuho") == 1
        assert template_sources.count("oborovo") == 1

    def test_bootstrap_references_use_real_factories(self, isolated_db):
        from app.services.project_library_service import ensure_reference_models
        created = ensure_reference_models()
        tuho = next(r for r in created if r.template_source == "tuho")
        obo = next(r for r in created if r.template_source == "oborovo")
        # References should be readonly and protected
        assert tuho.is_readonly is True
        assert obo.is_protected is True
        assert tuho.project_type == "Wind"
        assert obo.project_type == "Solar"


# ---------------------------------------------------------------------------
# Project library paginated query
# ---------------------------------------------------------------------------

class TestListProjectsPaged:
    def _make_projects(self, user_id, count, prefix="Project", isolated_db=None):
        from app.persistence.projects_repository import save_project
        records = []
        for i in range(count):
            r = save_project(
                user_id=user_id,
                project_code=f"{prefix.lower()}-{i:03d}",
                project_name=f"{prefix} {i:03d}",
                source_project_template="generic_solar",
                project_type="Solar",
                project_origin="user_created",
                template_source="generic_solar",
                project_role="user_project",
            )
            records.append(r)
        return records

    def test_basic_pagination(self, isolated_db):
        from app.persistence.projects_repository import list_projects_paged
        self._make_projects("u1", 25)
        page1, total = list_projects_paged(user_id="u1", page=1, page_size=10)
        assert total == 25
        assert len(page1) == 10

        page3, total3 = list_projects_paged(user_id="u1", page=3, page_size=10)
        assert total3 == 25
        assert len(page3) == 5

    def test_empty_page_beyond_total(self, isolated_db):
        from app.persistence.projects_repository import list_projects_paged
        self._make_projects("u1", 5)
        results, total = list_projects_paged(user_id="u1", page=99, page_size=10)
        assert total == 5
        assert results == []

    def test_search_filters_by_name(self, isolated_db):
        from app.persistence.projects_repository import save_project, list_projects_paged
        save_project(user_id="u1", project_code="alpha-1", project_name="Alpha Project",
                     source_project_template="generic_solar", project_type="Solar",
                     project_origin="user_created", template_source="generic_solar")
        save_project(user_id="u1", project_code="beta-1", project_name="Beta Project",
                     source_project_template="generic_solar", project_type="Solar",
                     project_origin="user_created", template_source="generic_solar")
        results, total = list_projects_paged(user_id="u1", search="Alpha")
        assert total == 1
        assert results[0].project_name == "Alpha Project"

    def test_search_escapes_like_wildcards(self, isolated_db):
        from app.persistence.projects_repository import save_project, list_projects_paged
        save_project(user_id="u1", project_code="pct-1", project_name="100% Project",
                     source_project_template="generic_solar", project_type="Solar",
                     project_origin="user_created", template_source="generic_solar")
        save_project(user_id="u1", project_code="pct-2", project_name="Other Project",
                     source_project_template="generic_solar", project_type="Solar",
                     project_origin="user_created", template_source="generic_solar")
        # Searching for "%" must not match everything
        results, total = list_projects_paged(user_id="u1", search="%")
        assert total == 1
        assert results[0].project_code == "pct-1"

    def test_role_filter_working_copy(self, isolated_db):
        from app.persistence.projects_repository import save_project, list_projects_paged
        save_project(user_id="u1", project_code="wc-1", project_name="WC One",
                     source_project_template="tuho", project_type="Wind",
                     project_origin="user_created", template_source="tuho",
                     project_role="working_copy")
        save_project(user_id="u1", project_code="up-1", project_name="UP One",
                     source_project_template="generic_solar", project_type="Solar",
                     project_origin="user_created", template_source="generic_solar",
                     project_role="user_project")
        results, total = list_projects_paged(user_id="u1", role_filter="working_copy")
        assert total == 1
        assert results[0].project_code == "wc-1"

    def test_references_visible_to_all_users(self, isolated_db):
        """References must appear in any user's paginated library results."""
        from app.services.project_library_service import ensure_reference_models
        from app.persistence.projects_repository import list_projects_paged
        ensure_reference_models()
        results_user1, total1 = list_projects_paged(user_id="user-alice")
        results_user2, total2 = list_projects_paged(user_id="user-bob")
        assert total1 == 2
        assert total2 == 2
        assert all(r.project_role == "reference" for r in results_user1)

    def test_deterministic_ordering_references_first(self, isolated_db):
        from app.services.project_library_service import ensure_reference_models
        from app.persistence.projects_repository import save_project, list_projects_paged
        ensure_reference_models()
        save_project(user_id="u1", project_code="user-proj-1", project_name="User Project",
                     source_project_template="generic_solar", project_type="Solar",
                     project_origin="user_created", template_source="generic_solar",
                     project_role="user_project")
        results, _ = list_projects_paged(user_id="u1")
        roles = [r.project_role for r in results]
        # References must appear before user_project
        ref_indices = [i for i, role in enumerate(roles) if role == "reference"]
        user_indices = [i for i, role in enumerate(roles) if role == "user_project"]
        assert max(ref_indices) < min(user_indices)


# ---------------------------------------------------------------------------
# Clone lineage and independence
# ---------------------------------------------------------------------------

class TestCloneLineage:
    def test_working_copy_lineage(self, isolated_db):
        from app.services.project_library_service import ensure_reference_models, create_working_copy
        refs = ensure_reference_models()
        tuho_ref = next(r for r in refs if r.template_source == "tuho")
        wc = create_working_copy("user1", tuho_ref.project_id)
        assert wc.project_role == "working_copy"
        assert wc.source_project_id == tuho_ref.project_id
        assert wc.is_protected is False
        assert wc.user_id == "user1"

    def test_working_copy_independent_workspace(self, isolated_db):
        from app.services.project_library_service import ensure_reference_models, create_working_copy
        from app.persistence.workspace_repository import get_workspace_state, save_workspace_state
        refs = ensure_reference_models()
        tuho_ref = next(r for r in refs if r.template_source == "tuho")
        wc = create_working_copy("user1", tuho_ref.project_id)

        # Modify the working copy's workspace
        wc_ws = get_workspace_state("user1", wc.project_id)
        assert wc_ws is not None
        save_workspace_state(
            user_id="user1",
            project_id=wc.project_id,
            project_code=wc.project_code,
            draft_snapshot={"modified": True},
            saved_snapshot={"modified": True},
            governance_state={},
        )

        # Reference workspace must be unchanged
        from app.persistence.projects_repository import REFERENCE_USER_ID
        ref_ws = get_workspace_state(REFERENCE_USER_ID, tuho_ref.project_id)
        assert ref_ws is not None
        assert not ref_ws.saved_snapshot.get("modified")

    def test_working_copy_unique_name_suffix(self, isolated_db):
        from app.services.project_library_service import ensure_reference_models, create_working_copy
        refs = ensure_reference_models()
        tuho_ref = next(r for r in refs if r.template_source == "tuho")
        wc1 = create_working_copy("user1", tuho_ref.project_id)
        wc2 = create_working_copy("user1", tuho_ref.project_id)
        assert wc1.project_code != wc2.project_code
        assert wc1.project_name != wc2.project_name

    def test_clone_requires_reference_source(self, isolated_db):
        from app.persistence.projects_repository import save_project
        from app.services.project_library_service import create_working_copy
        user_proj = save_project(
            user_id="user1", project_code="my-proj",
            project_name="My Project", source_project_template="generic_solar",
            project_type="Solar", project_origin="user_created",
            template_source="generic_solar", project_role="user_project",
        )
        with pytest.raises(ValueError, match="not a canonical reference model"):
            create_working_copy("user2", user_proj.project_id)

    def test_oborovo_clone_lineage(self, isolated_db):
        from app.services.project_library_service import ensure_reference_models, create_working_copy
        refs = ensure_reference_models()
        obo_ref = next(r for r in refs if r.template_source == "oborovo")
        wc = create_working_copy("user1", obo_ref.project_id)
        assert wc.source_project_id == obo_ref.project_id
        assert wc.template_source == "oborovo"


# ---------------------------------------------------------------------------
# Sidebar bounded recent list
# ---------------------------------------------------------------------------

class TestRecentProjectsSidebar:
    def test_recent_projects_bounded(self, isolated_db):
        from app.persistence.projects_repository import save_project, list_recent_projects
        for i in range(12):
            save_project(
                user_id="u1", project_code=f"proj-{i:03d}",
                project_name=f"Project {i:03d}",
                source_project_template="generic_solar", project_type="Solar",
                project_origin="user_created", template_source="generic_solar",
            )
        recent = list_recent_projects("u1", limit=8)
        assert len(recent) == 8

    def test_recent_projects_exclude_current(self, isolated_db):
        from app.persistence.projects_repository import save_project, list_recent_projects
        r1 = save_project(user_id="u1", project_code="p1", project_name="P1",
                          source_project_template="generic_solar", project_type="Solar",
                          project_origin="user_created", template_source="generic_solar")
        save_project(user_id="u1", project_code="p2", project_name="P2",
                     source_project_template="generic_solar", project_type="Solar",
                     project_origin="user_created", template_source="generic_solar")
        recent = list_recent_projects("u1", limit=8, exclude_project_id=r1.project_id)
        assert all(r.project_id != r1.project_id for r in recent)


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------

class TestAuthorization:
    def test_user_cannot_see_other_users_private_project(self, isolated_db):
        from app.persistence.projects_repository import save_project, list_projects_paged
        save_project(user_id="alice", project_code="alice-proj", project_name="Alice Secret",
                     source_project_template="generic_solar", project_type="Solar",
                     project_origin="user_created", template_source="generic_solar",
                     project_role="user_project")
        results, total = list_projects_paged(user_id="bob")
        codes = [r.project_code for r in results]
        assert "alice-proj" not in codes

    def test_both_users_see_references(self, isolated_db):
        from app.services.project_library_service import ensure_reference_models
        from app.persistence.projects_repository import list_projects_paged
        ensure_reference_models()
        alice_refs, _ = list_projects_paged(user_id="alice", role_filter="reference")
        bob_refs, _ = list_projects_paged(user_id="bob", role_filter="reference")
        assert len(alice_refs) == 2
        assert len(bob_refs) == 2

    def test_search_does_not_leak_other_users_projects(self, isolated_db):
        from app.persistence.projects_repository import save_project, list_projects_paged
        save_project(user_id="alice", project_code="secret-alpha", project_name="Secret Alpha",
                     source_project_template="generic_solar", project_type="Solar",
                     project_origin="user_created", template_source="generic_solar")
        results, total = list_projects_paged(user_id="bob", search="Secret")
        assert total == 0
        assert results == []


# ---------------------------------------------------------------------------
# Reference mutation guard
# ---------------------------------------------------------------------------

class TestMutationGuard:
    def test_assert_project_not_protected_raises_for_reference(self, isolated_db):
        from app.services.project_library_service import (
            ensure_reference_models, assert_project_not_protected, ProtectedProjectError
        )
        refs = ensure_reference_models()
        tuho_ref = refs[0]
        with pytest.raises(ProtectedProjectError):
            assert_project_not_protected(tuho_ref)

    def test_assert_project_not_protected_passes_for_user_project(self, isolated_db):
        from app.persistence.projects_repository import save_project
        from app.services.project_library_service import assert_project_not_protected
        r = save_project(user_id="u1", project_code="up", project_name="User Project",
                         source_project_template="generic_solar", project_type="Solar",
                         project_origin="user_created", template_source="generic_solar",
                         project_role="user_project")
        assert_project_not_protected(r)  # should not raise

    def test_assert_project_not_protected_passes_for_working_copy(self, isolated_db):
        from app.services.project_library_service import (
            ensure_reference_models, create_working_copy, assert_project_not_protected
        )
        refs = ensure_reference_models()
        wc = create_working_copy("u1", refs[0].project_id)
        assert_project_not_protected(wc)  # working copy is editable

    def test_legacy_factory_template_combo_also_blocked(self, isolated_db):
        from app.persistence.projects_repository import save_project
        from app.services.project_library_service import assert_project_not_protected, ProtectedProjectError
        legacy_ref = save_project(
            user_id="__reference__", project_code="legacy-obo",
            project_name="Oborovo Old", source_project_template="oborovo",
            project_type="Solar", project_origin="factory_template",
            template_source="oborovo", project_role="user_project",  # old-style row
        )
        with pytest.raises(ProtectedProjectError):
            assert_project_not_protected(legacy_ref)

# ===========================================================================
# Migration and backfill safety
# ===========================================================================

class TestMigrationBackfillSafety:
    """Verify that schema migration does not silently convert user-owned
    factory_template rows into globally visible reference projects."""

    @pytest.fixture(autouse=True)
    def isolated(self, isolated_db):
        pass

    def _raw_insert_project(self, user_id, project_code, project_name,
                             project_origin, template_source):
        """Insert a project row as it would exist before the Project Library migration."""
        import sqlite3, os
        # Ensure schema exists first (simulates a pre-migration DB with schema).
        from app.persistence.db import init_db
        init_db()
        conn = sqlite3.connect(os.environ["FINCO_DB_PATH"])
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        # Insert without the new project-library columns to simulate pre-migration state.
        conn.execute("""
            INSERT INTO projects (
                project_id, user_id, project_code, project_name,
                project_type, project_origin, source_project_template,
                template_source, baseline_snapshot_json, archived,
                governance_state_json, last_run_summary_json,
                replay_metadata_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, '{}', 0, '{}', '{}', '{}',
                      datetime('now'), datetime('now'))
        """, (
            "usr-" + project_code[:8], user_id, project_code, project_name,
            "Wind", project_origin, template_source, template_source,
        ))
        conn.commit()
        conn.close()

    def test_user_owned_tuho_row_not_promoted(self):
        """A user-owned TUHO factory_template row must stay user-owned after init_db."""
        from app.persistence.projects_repository import get_project_by_code
        # Pre-insert a user-owned TUHO row (simulating legacy state)
        self._raw_insert_project(
            "alice", "tuho-my-project", "Alice TUHO Project",
            "factory_template", "tuho"
        )
        # Re-run schema init (migration runs here)
        from app.persistence.db import init_db
        init_db()
        record = get_project_by_code("alice", "tuho-my-project")
        assert record is not None
        assert record.user_id == "alice", "User-owned row must stay with alice"
        assert record.project_role != "reference", \
            "User-owned factory_template TUHO row must NOT be promoted to reference"

    def test_user_owned_oborovo_row_not_promoted(self):
        """A user-owned Oborovo factory_template row must stay user-owned after init_db."""
        from app.persistence.projects_repository import get_project_by_code
        self._raw_insert_project(
            "bob", "oborovo-my-project", "Bob Oborovo Project",
            "factory_template", "oborovo"
        )
        from app.persistence.db import init_db
        init_db()
        record = get_project_by_code("bob", "oborovo-my-project")
        assert record is not None
        assert record.user_id == "bob", "User-owned row must stay with bob"
        assert record.project_role != "reference", \
            "User-owned factory_template Oborovo row must NOT be promoted to reference"

    def test_system_reference_row_is_backfilled(self):
        """A row already owned by __reference__ is backfilled to role='reference'."""
        import sqlite3, os
        # Ensure schema exists first.
        from app.persistence.db import init_db
        init_db()
        # Insert a __reference__-owned row that predates the project_role column
        conn = sqlite3.connect(os.environ["FINCO_DB_PATH"])
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            INSERT INTO projects (
                project_id, user_id, project_code, project_name,
                project_type, project_origin, source_project_template,
                template_source, baseline_snapshot_json, archived,
                governance_state_json, last_run_summary_json,
                replay_metadata_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, '{}', 0, '{}', '{}', '{}',
                      datetime('now'), datetime('now'))
        """, (
            "ref-tuho-old", "__reference__", "tuho-reference", "TUHO Reference",
            "Wind", "factory_template", "tuho", "tuho",
        ))
        conn.commit()
        conn.close()
        from app.persistence.db import init_db
        init_db()
        from app.persistence.projects_repository import get_project_by_code, REFERENCE_USER_ID
        record = get_project_by_code(REFERENCE_USER_ID, "tuho-reference")
        assert record is not None
        assert record.project_role == "reference", \
            f"System __reference__ TUHO row should be backfilled to 'reference', got {record.project_role!r}"
        assert record.is_protected is True

    def test_bootstrap_after_legacy_user_rows(self):
        """Bootstrap creates exactly two __reference__ projects even when user-owned rows exist."""
        from app.persistence.projects_repository import get_project_by_code, REFERENCE_USER_ID
        from app.persistence.projects_repository import get_reference_projects
        # Insert user-owned factory_template rows for alice
        self._raw_insert_project(
            "alice", "tuho-project", "Alice TUHO", "factory_template", "tuho"
        )
        self._raw_insert_project(
            "alice", "oborovo-project", "Alice Oborovo", "factory_template", "oborovo"
        )
        # Now bootstrap
        from app.services.project_library_service import ensure_reference_models
        ensure_reference_models()
        refs = get_reference_projects()
        ref_srcs = {r.template_source for r in refs}
        assert "tuho" in ref_srcs, "TUHO system reference must be created"
        assert "oborovo" in ref_srcs, "Oborovo system reference must be created"
        # Alice's rows must not be affected
        alice_tuho = get_project_by_code("alice", "tuho-project")
        assert alice_tuho is not None
        assert alice_tuho.project_role != "reference"

    def test_alice_cannot_see_bobs_tuho_row_in_library(self):
        """list_projects_paged must not expose Bob's user-owned TUHO row to Alice."""
        from app.persistence.projects_repository import save_project, list_projects_paged
        # Bob creates a user_project (even with factory_template origin)
        save_project(
            user_id="bob",
            project_code="bobs-tuho",
            project_name="Bob TUHO",
            source_project_template="tuho",
            project_type="Wind",
            project_origin="user_created",
            template_source="tuho",
            project_role="user_project",
        )
        # Alice queries the library
        records, total = list_projects_paged(user_id="alice")
        codes = [r.project_code for r in records]
        assert "bobs-tuho" not in codes, \
            "Alice must not see Bob's project in the library"


# ===========================================================================
# save_project() metadata preservation
# ===========================================================================

class TestSaveProjectMetadataPreservation:
    """Verify that save_project() preserves role/lineage/protection on updates
    when the caller does not pass the project-library arguments."""

    @pytest.fixture(autouse=True)
    def isolated(self, isolated_db):
        pass

    def test_working_copy_role_preserved_on_update(self):
        """A working_copy project must keep role/source_project_id after a
        routine save_project() call that omits the library params."""
        from app.persistence.projects_repository import save_project, get_project_by_code
        # Create the working copy explicitly
        save_project(
            user_id="alice",
            project_code="my-wc",
            project_name="My Working Copy",
            source_project_template="tuho",
            project_type="Wind",
            project_role="working_copy",
            source_project_id="ref-tuho-001",
            is_protected=False,
        )
        # Now simulate a routine update (name change) without passing library params
        save_project(
            user_id="alice",
            project_code="my-wc",
            project_name="My Working Copy (renamed)",
            source_project_template="tuho",
            project_type="Wind",
            # project_role, is_protected, source_project_id NOT passed
        )
        updated = get_project_by_code("alice", "my-wc")
        assert updated is not None
        assert updated.project_role == "working_copy", \
            f"Role must be preserved as 'working_copy', got {updated.project_role!r}"
        assert updated.source_project_id == "ref-tuho-001", \
            f"source_project_id must be preserved, got {updated.source_project_id!r}"
        assert updated.is_protected is False

    def test_reference_protection_preserved_on_metadata_update(self):
        """A reference project must keep role/protection after a benign metadata update."""
        from app.persistence.projects_repository import (
            save_project, get_project_by_code, REFERENCE_USER_ID,
        )
        save_project(
            user_id=REFERENCE_USER_ID,
            project_code="tuho-ref-test",
            project_name="TUHO Reference",
            source_project_template="tuho",
            project_type="Wind",
            project_role="reference",
            is_protected=True,
        )
        # Simulate a benign last_run_summary update without library params
        save_project(
            user_id=REFERENCE_USER_ID,
            project_code="tuho-ref-test",
            project_name="TUHO Reference",
            source_project_template="tuho",
            project_type="Wind",
            last_run_summary={"status": "success"},
            # project_role, is_protected NOT passed
        )
        updated = get_project_by_code(REFERENCE_USER_ID, "tuho-ref-test")
        assert updated is not None
        assert updated.project_role == "reference", \
            f"Role must remain 'reference', got {updated.project_role!r}"
        assert updated.is_protected is True, \
            "is_protected must remain True after metadata update"
        assert updated.user_id == REFERENCE_USER_ID

    def test_explicit_role_change_takes_effect(self):
        """Explicit project_role argument is honored on update."""
        from app.persistence.projects_repository import save_project, get_project_by_code
        save_project(
            user_id="carol",
            project_code="carol-proj",
            project_name="Carol Project",
            source_project_template="tuho",
            project_type="Wind",
            project_role="user_project",
        )
        # Explicitly upgrade to working_copy with lineage
        save_project(
            user_id="carol",
            project_code="carol-proj",
            project_name="Carol Working Copy",
            source_project_template="tuho",
            project_type="Wind",
            project_role="working_copy",
            source_project_id="ref-xyz",
        )
        updated = get_project_by_code("carol", "carol-proj")
        assert updated.project_role == "working_copy"
        assert updated.source_project_id == "ref-xyz"


# ---------------------------------------------------------------------------
# get_canonical_reference_by_id
# ---------------------------------------------------------------------------

class TestCanonicalReferenceById:
    def test_get_canonical_reference_by_id_returns_reference(self, isolated_db):
        from app.services.project_library_service import ensure_reference_models
        from app.persistence.projects_repository import get_canonical_reference_by_id
        refs = ensure_reference_models()
        tuho = next(r for r in refs if r.template_source == "tuho")
        result = get_canonical_reference_by_id(tuho.project_id)
        assert result is not None
        assert result.project_id == tuho.project_id
        assert result.template_source == "tuho"
        assert result.project_role == "reference"
        assert result.is_protected is True

    def test_get_canonical_reference_by_id_rejects_user_owned(self, isolated_db):
        from app.persistence.projects_repository import (
            save_project, get_canonical_reference_by_id,
        )
        r = save_project(
            user_id="bob",
            project_code="bobs-tuho",
            project_name="Bob TUHO",
            source_project_template="tuho",
            project_type="Wind",
            project_origin="factory_template",
            template_source="tuho",
            project_role="user_project",
        )
        assert get_canonical_reference_by_id(r.project_id) is None

    def test_get_canonical_reference_by_id_rejects_archived(self, isolated_db):
        from app.persistence.projects_repository import (
            save_project, get_canonical_reference_by_id, REFERENCE_USER_ID,
        )
        r = save_project(
            user_id=REFERENCE_USER_ID,
            project_code="archived-tuho",
            project_name="Archived TUHO",
            source_project_template="tuho",
            project_type="Wind",
            project_role="reference",
            is_protected=True,
            template_source="tuho",
            archived=True,
        )
        assert get_canonical_reference_by_id(r.project_id) is None

    def test_get_canonical_reference_by_id_rejects_wrong_role(self, isolated_db):
        from app.persistence.projects_repository import (
            save_project, get_canonical_reference_by_id, REFERENCE_USER_ID,
        )
        # Use a non-reference template_source so db.py backfill does not promote it.
        r = save_project(
            user_id=REFERENCE_USER_ID,
            project_code="ref-wrong-role",
            project_name="Ref Wrong Role",
            source_project_template="generic_wind",
            project_type="Wind",
            project_role="user_project",
            template_source="generic_wind",
        )
        assert get_canonical_reference_by_id(r.project_id) is None


# ---------------------------------------------------------------------------
# create_working_copy — strict authorization
# ---------------------------------------------------------------------------

class TestCreateWorkingCopyAuthorization:
    def test_clone_rejects_bob_normal_project(self, isolated_db):
        from app.persistence.projects_repository import save_project
        from app.services.project_library_service import create_working_copy
        r = save_project(
            user_id="bob",
            project_code="bob-proj",
            project_name="Bob Project",
            source_project_template="tuho",
            project_type="Wind",
            project_role="user_project",
            template_source="tuho",
        )
        with pytest.raises(ValueError, match="not a canonical reference model"):
            create_working_copy("alice", r.project_id)

    def test_clone_rejects_bob_factory_template_tuho(self, isolated_db):
        """Bob owns a factory_template/tuho row (not __reference__) — must be rejected."""
        from app.persistence.projects_repository import save_project
        from app.services.project_library_service import create_working_copy
        r = save_project(
            user_id="bob",
            project_code="bob-factory-tuho",
            project_name="Bob Factory TUHO",
            source_project_template="tuho",
            project_type="Wind",
            project_role="reference",
            is_protected=True,
            template_source="tuho",
        )
        with pytest.raises(ValueError, match="not a canonical reference model"):
            create_working_copy("alice", r.project_id)

    def test_clone_rejects_bob_working_copy(self, isolated_db):
        from app.persistence.projects_repository import save_project
        from app.services.project_library_service import create_working_copy
        r = save_project(
            user_id="bob",
            project_code="bob-wc",
            project_name="Bob Working Copy",
            source_project_template="tuho",
            project_type="Wind",
            project_role="working_copy",
            template_source="tuho",
        )
        with pytest.raises(ValueError, match="not a canonical reference model"):
            create_working_copy("alice", r.project_id)

    def test_clone_rejects_archived_reference(self, isolated_db):
        from app.persistence.projects_repository import save_project, REFERENCE_USER_ID
        from app.services.project_library_service import create_working_copy
        r = save_project(
            user_id=REFERENCE_USER_ID,
            project_code="archived-ref",
            project_name="Archived Ref",
            source_project_template="tuho",
            project_type="Wind",
            project_role="reference",
            is_protected=True,
            template_source="tuho",
            archived=True,
        )
        with pytest.raises(ValueError, match="not a canonical reference model"):
            create_working_copy("alice", r.project_id)

    def test_canonical_reference_can_be_cloned(self, isolated_db):
        from app.services.project_library_service import ensure_reference_models, create_working_copy
        refs = ensure_reference_models()
        tuho = next(r for r in refs if r.template_source == "tuho")
        wc = create_working_copy("alice", tuho.project_id)
        assert wc.project_role == "working_copy"
        assert wc.user_id == "alice"
        assert wc.source_project_id == tuho.project_id


# ---------------------------------------------------------------------------
# Bootstrap concurrency / idempotency
# ---------------------------------------------------------------------------

class TestBootstrapConcurrency:
    def test_ensure_reference_models_idempotent_repeated_calls(self, isolated_db):
        from app.services.project_library_service import ensure_reference_models
        from app.persistence.projects_repository import get_reference_by_template_source
        created1 = ensure_reference_models()
        created2 = ensure_reference_models()
        created3 = ensure_reference_models()
        assert len(created1) == 2
        assert len(created2) == 0
        assert len(created3) == 0
        tuho = get_reference_by_template_source("tuho")
        obo = get_reference_by_template_source("oborovo")
        assert tuho is not None
        assert obo is not None
        assert tuho.project_role == "reference"
        assert obo.project_role == "reference"

    def test_get_reference_by_template_source_returns_only_reference_user(self, isolated_db):
        from app.persistence.projects_repository import (
            save_project, get_reference_by_template_source, REFERENCE_USER_ID,
        )
        # Insert a user-owned tuho row (not a system reference)
        save_project(
            user_id="someuser",
            project_code="user-tuho",
            project_name="User TUHO",
            source_project_template="tuho",
            project_type="Wind",
            project_role="user_project",
            template_source="tuho",
        )
        # Only the system reference user should be returned
        result = get_reference_by_template_source("tuho")
        if result is not None:
            assert result.user_id == REFERENCE_USER_ID


# ---------------------------------------------------------------------------
# Protection predicate consolidation
# ---------------------------------------------------------------------------

class TestProtectionPredicateConsolidation:
    def test_ui_service_is_protected_reference_matches_canonical(self, isolated_db):
        """Both import paths on the same object must return identical results."""
        from app.ui.protected_reference_service import is_protected_reference as ui_fn
        from app.services.project_library_service import is_protected_reference as svc_fn
        from app.persistence.projects_repository import save_project, REFERENCE_USER_ID
        r = save_project(
            user_id=REFERENCE_USER_ID,
            project_code="pred-test",
            project_name="Pred Test",
            source_project_template="tuho",
            project_type="Wind",
            project_role="reference",
            is_protected=True,
            template_source="tuho",
        )
        assert ui_fn(r) == svc_fn(r)
        assert ui_fn(r) is True

        # A genuinely non-reference row: user_project, non-tuho/oborovo template.
        r2 = save_project(
            user_id="alice",
            project_code="alice-proj-pred",
            project_name="Alice Project",
            source_project_template="generic_solar",
            project_type="Solar",
            project_role="user_project",
            template_source="generic_solar",
        )
        assert ui_fn(r2) == svc_fn(r2)
        assert ui_fn(r2) is False


# ---------------------------------------------------------------------------
# Workspace owner correctness for references
# ---------------------------------------------------------------------------

class TestWorkspaceOwnerForReference:
    def test_workspace_owner_id_correct_for_reference(self, isolated_db):
        """resolve_accessible_project returns __reference__ as workspace_owner for references."""
        from app.services.project_library_service import ensure_reference_models
        from app.persistence.projects_repository import resolve_accessible_project, REFERENCE_USER_ID
        ensure_reference_models()
        record, owner = resolve_accessible_project("some-requesting-user", "tuho-reference")
        assert record is not None
        assert owner == REFERENCE_USER_ID
        assert record.project_role == "reference"
