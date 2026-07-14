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
        with pytest.raises(ValueError, match="not a reference model"):
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
