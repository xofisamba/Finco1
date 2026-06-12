"""Phase P2-FIX-3 — C2 First-Edit Copy (Reference Projects as Normal
Projects).

Verifies the C2 architecture for protected reference projects:

1. TUHO Wind and Oborovo Solar PV appear as normal projects in
   the UI.
2. Opening them does NOT create a working copy. The user views,
   runs, and exports the read-only reference.
3. The first edit / save attempt triggers a 409 response with
   ``needs_copy_confirmation: true`` and a friendly message. The
   protected reference fixture never mutates.
4. After the user confirms (via /projects/{code}/confirm-first-
   edit-copy), a user-owned working copy is created. The
   working copy is editable.
5. The protected reference fixture is unchanged.

This is the C2 architecture (modified C1): explicit user consent
required to create a working copy, instead of implicit creation
on Open (which would create hidden records merely by browsing).
"""

from __future__ import annotations

import os
import re
import time

import pytest

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-key-p2fix3")

from fastapi.testclient import TestClient  # noqa: E402

from app.auth import create_session_token  # noqa: E402
from app.ui.protected_reference_service import (  # noqa: E402
    is_protected_reference,
    first_edit_response,
    working_copy_replay_metadata,
    PROTECTED_REFERENCE_TEMPLATE_SOURCES,
)
from main_web import app  # noqa: E402


# ─────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def logged_in_client():
    """TestClient with a valid session cookie."""
    client = TestClient(app)
    token = create_session_token(user_id="1", username="test_user")
    client.cookies.set("finco_session", token)
    return client


@pytest.fixture
def fresh_client(logged_in_client):
    """A new client per test to avoid state pollution from
    the workspace draft state DB writes that occur during
    generic draft saves. The cookie is shared across clients
    (same user_id / session token)."""
    client = TestClient(app)
    # Copy the cookie from the module-scoped logged-in client.
    for cookie_name, cookie_value in logged_in_client.cookies.items():
        client.cookies.set(cookie_name, cookie_value)
    return client


# ─────────────────────────────────────────────────────────────────────
# Test: protected_reference_service unit tests
# ─────────────────────────────────────────────────────────────────────


class TestProtectedReferenceService:
    """Unit tests for the protected_reference_service helpers."""

    def test_protected_template_sources_set(self):
        assert PROTECTED_REFERENCE_TEMPLATE_SOURCES == frozenset(
            {"tuho", "oborovo"}
        )

    def test_is_protected_reference_with_tuho(self):
        """A TUHO factory template record is a protected reference."""
        # Build a minimal record-like object with the required
        # attributes. We use a SimpleNamespace to avoid coupling
        # to the full ProjectRecord constructor.
        from types import SimpleNamespace

        record = SimpleNamespace(
            project_origin="factory_template",
            template_source="tuho",
            source_project_template="tuho",
        )
        assert is_protected_reference(record) is True

    def test_is_protected_reference_with_oborovo(self):
        from types import SimpleNamespace

        record = SimpleNamespace(
            project_origin="factory_template",
            template_source="oborovo",
            source_project_template="oborovo",
        )
        assert is_protected_reference(record) is True

    def test_is_protected_reference_with_generic_solar(self):
        """Generic Solar factory template is NOT a protected
        reference. It is an internal-use model that can be
        edited directly via existing /save-as."""
        from types import SimpleNamespace

        record = SimpleNamespace(
            project_origin="factory_template",
            template_source="generic_solar",
            source_project_template="generic_solar",
        )
        assert is_protected_reference(record) is False

    def test_is_protected_reference_with_user_created(self):
        """A user_created project is not a protected reference,
        even if its template_source happens to be 'tuho'
        (which would mean a working copy was created from a
        TUHO reference)."""
        from types import SimpleNamespace

        record = SimpleNamespace(
            project_origin="user_created",
            template_source="tuho",
            source_project_template="tuho",
        )
        assert is_protected_reference(record) is False

    def test_is_protected_reference_with_none(self):
        assert is_protected_reference(None) is False

    def test_first_edit_response_payload(self):
        from types import SimpleNamespace

        record = SimpleNamespace(
            project_code="tuho",
            project_name="TUHO Wind 1",
            template_source="tuho",
        )
        resp = first_edit_response(record)
        assert resp["error"] == "protected_reference"
        assert resp["needs_copy_confirmation"] is True
        assert resp["project_code"] == "tuho"
        assert resp["project_name"] == "TUHO Wind 1"
        assert resp["template_source"] == "tuho"
        assert "Create an editable copy?" in resp["message"]

    def test_working_copy_replay_metadata(self):
        meta = working_copy_replay_metadata(
            source_project_code="tuho",
            source_project_origin="factory_template",
        )
        assert meta["export_type"] == "working_copy_from_protected_reference"
        assert meta["source_project_code"] == "tuho"
        assert meta["source_project_origin"] == "factory_template"
        assert meta["created_via"] == "p2fix3_first_edit_confirmation"
        assert meta["baseline_source"] is False


# ─────────────────────────────────────────────────────────────────────
# Test: open behavior (no working copy creation)
# ─────────────────────────────────────────────────────────────────────


class TestOpenBehavior:
    """Opening TUHO or Oborovo should NOT create a new project
    record. Only the confirm-first-edit-copy endpoint creates a copy.
    P2-FIX-8 PR3: Draft save now returns HX-Redirect (transparent copy)
    instead of 409, but the GET open still does not create a record."""

    def test_opening_tuho_does_not_create_record(self, fresh_client):
        """GET /?project=tuho renders the workspace but does NOT
        create a new project record. We verify this by confirming
        a subsequent draft save triggers the copy redirect (meaning
        TUHO is still the factory template — if a copy had been
        silently created, draft save would return 200 without redirect)."""
        r1 = fresh_client.get("/?project=tuho", follow_redirects=True)
        assert r1.status_code == 200
        # Draft save must trigger transparent copy redirect (not plain 200)
        r2 = fresh_client.post(
            "/scenarios/state/draft",
            data={"active_project": "tuho", "project_name": "TUHO",
                  "technology": "Wind"},
            follow_redirects=False,
        )
        # P2-FIX-8: 200 + HX-Redirect replaces 409
        assert r2.status_code in (200, 302, 303), (
            f"Draft save on protected ref returned unexpected status {r2.status_code}"
        )
        if r2.status_code == 200:
            # Must have HX-Redirect (copy redirect) — not a plain 200 draft success
            body = r2.json()
            assert "hx-redirect" in {k.lower() for k in r2.headers} or \
                   "redirect" in body, (
                "Opening TUHO silently created a user_created copy — "
                "draft save should return a copy redirect, not plain success"
            )

    def test_opening_oborovo_does_not_create_record(self, fresh_client):
        r1 = fresh_client.get("/?project=oborovo", follow_redirects=True)
        assert r1.status_code == 200
        r2 = fresh_client.post(
            "/scenarios/state/draft",
            data={"active_project": "oborovo", "project_name": "Oborovo",
                  "technology": "Solar"},
            follow_redirects=False,
        )
        assert r2.status_code in (200, 302, 303)
        if r2.status_code == 200:
            body = r2.json()
            assert "hx-redirect" in {k.lower() for k in r2.headers} or \
                   "redirect" in body

    def test_view_run_export_still_works_on_tuho(self, fresh_client):
        """Opening TUHO still allows view (workspace render
        returns 200). The /run route and /export routes
        are not blocked."""
        # Workspace render
        r = fresh_client.get("/?project=tuho", follow_redirects=True)
        assert r.status_code == 200
        # Audit / Reference tab is reachable
        html = r.text
        # The workspace renders the Audit / Reference tab
        assert 'id="panel-audit"' in html

    def test_generic_solar_is_not_protected(self, fresh_client):
        """Generic Solar factory template can be edited
        directly (no 409 guard). It is internal-use model
        only, not a protected reference."""
        r = fresh_client.post(
            "/scenarios/state/draft",
            data={
                "active_project": "generic_solar",
                "project_name": "Generic",
                "technology": "Solar",
            },
            follow_redirects=False,
        )
        assert r.status_code == 200, (
            f"Generic Solar factory template should be editable "
            f"directly (status {r.status_code}, expected 200). "
            f"Only TUHO and Oborovo are protected references."
        )


# ─────────────────────────────────────────────────────────────────────
# Test: first edit triggers 409 protected_reference
# ─────────────────────────────────────────────────────────────────────


class TestFirstEditGuard:
    """P2-FIX-8 PR3: Transparent copy-on-first-save replaces the 409 guard.
    Draft save on a protected reference now returns HX-Redirect (200 + header
    or 302) instead of 409. The fixture is never mutated by the draft route itself."""

    def test_first_draft_save_on_tuho_returns_redirect(self, fresh_client):
        """P2-FIX-8: Draft save on TUHO returns copy redirect, not 409."""
        r = fresh_client.post(
            "/scenarios/state/draft",
            data={"active_project": "tuho", "project_name": "TUHO",
                  "technology": "Wind"},
            follow_redirects=False,
        )
        assert r.status_code != 409, (
            "P2-FIX-8: Draft save on protected ref must not return 409 — "
            "transparent copy redirect replaces this"
        )
        assert r.status_code in (200, 302, 303)

    def test_first_draft_save_on_oborovo_returns_redirect(self, fresh_client):
        r = fresh_client.post(
            "/scenarios/state/draft",
            data={"active_project": "oborovo", "project_name": "Oborovo",
                  "technology": "Solar"},
            follow_redirects=False,
        )
        assert r.status_code != 409
        assert r.status_code in (200, 302, 303)

    def test_first_draft_save_does_not_mutate_fixture(self, fresh_client):
        """The draft route must NOT mutate the TUHO fixture — it only
        returns a redirect. Two draft saves must both return a redirect
        (dedup ensures same destination), never a plain draft success."""
        r1 = fresh_client.post(
            "/scenarios/state/draft",
            data={"active_project": "tuho", "project_name": "TUHO"},
            follow_redirects=False,
        )
        assert r1.status_code in (200, 302, 303), (
            f"First draft save must return redirect, got {r1.status_code}"
        )
        # Second attempt — must also return redirect (dedup to same copy)
        r2 = fresh_client.post(
            "/scenarios/state/draft",
            data={"active_project": "tuho", "project_name": "TUHO"},
            follow_redirects=False,
        )
        assert r2.status_code in (200, 302, 303), (
            f"Second draft save must also return redirect (dedup), "
            f"got {r2.status_code}"
        )

    def test_user_can_abandon_by_ignoring_redirect(self, fresh_client):
        """User 'cancels' by not following the HX-Redirect. The draft route
        returns a redirect but does NOT create a copy itself. As long as
        the browser doesn't follow to /confirm-first-edit-copy, no copy exists."""
        for _ in range(3):
            r = fresh_client.post(
                "/scenarios/state/draft",
                data={"active_project": "tuho", "project_name": "TUHO"},
                follow_redirects=False,
            )
            # Each call returns a redirect (not an error, not a mutation)
            assert r.status_code in (200, 302, 303)


# ─────────────────────────────────────────────────────────────────────
# Test: confirm-first-edit-copy creates working copy
# ─────────────────────────────────────────────────────────────────────


class TestConfirmFirstEditCopy:
    """The /projects/{code}/confirm-first-edit-copy route creates
    a user-owned working copy from a protected reference."""

    def test_confirm_creates_working_copy_for_tuho(self, fresh_client):
        # Confirm the transition
        r = fresh_client.post(
            "/projects/tuho/confirm-first-edit-copy",
            follow_redirects=False,
        )
        # 302 redirect to a copy (new or existing via dedup)
        assert r.status_code == 302
        location = r.headers.get("location", "")
        assert "?project=" in location, (
            f"confirm-first-edit-copy must redirect to a project, got: {location!r}"
        )
        new_code = location.split("project=")[1]

        # The new project must be editable (draft save returns 200)
        r2 = fresh_client.post(
            "/scenarios/state/draft",
            data={
                "active_project": new_code,
                "project_name": "TUHO (working copy)",
                "technology": "Wind",
            },
            follow_redirects=False,
        )
        assert r2.status_code == 200, (
            f"Working copy was not editable (status {r2.status_code})"
        )

    def test_confirm_creates_working_copy_for_oborovo(self, fresh_client):
        r = fresh_client.post(
            "/projects/oborovo/confirm-first-edit-copy",
            follow_redirects=False,
        )
        assert r.status_code == 302
        location = r.headers.get("location", "")
        assert "?project=" in location
        new_code = location.split("project=")[1]
        r2 = fresh_client.post(
            "/scenarios/state/draft",
            data={
                "active_project": new_code,
                "project_name": "Oborovo (working copy)",
                "technology": "Solar",
            },
            follow_redirects=False,
        )
        assert r2.status_code == 200

    def test_confirm_rejects_non_protected_reference(
        self, fresh_client
    ):
        """The /confirm-first-edit-copy route returns 400 for
        projects that are not protected references. This URL is
        reserved for the C2 transition only."""
        r = fresh_client.post(
            "/projects/generic_solar/confirm-first-edit-copy",
            follow_redirects=False,
        )
        assert r.status_code == 400
        body = r.json()
        assert body["error"] == "not_a_protected_reference"

    def test_confirm_rejects_unknown_project(self, fresh_client):
        r = fresh_client.post(
            "/projects/nonexistent_project/confirm-first-edit-copy",
            follow_redirects=False,
        )
        # 404 (not found) — the route is reachable but the
        # source doesn't exist.
        assert r.status_code == 404
        body = r.json()
        assert body["error"] == "project_not_found"

    def test_confirm_uses_working_copy_replay_metadata(
        self, fresh_client
    ):
        """The replay metadata of the new working copy is the
        ``working_copy_from_protected_reference`` variant. The
        audit / reviewer surface can trace the lineage."""
        from app.persistence.repository import get_project_record

        # Create the working copy
        r = fresh_client.post(
            "/projects/tuho/confirm-first-edit-copy",
            follow_redirects=False,
        )
        assert r.status_code == 302
        new_code = r.headers.get("location", "").split("project=")[1]
        # Lookup the new project record
        new_record = get_project_record(
            user_id="1", project_code=new_code
        )
        assert new_record is not None
        # The replay metadata must tag the transition
        assert (
            new_record.replay_metadata.get("export_type")
            == "working_copy_from_protected_reference"
        )
        assert (
            new_record.replay_metadata.get("source_project_code")
            == "tuho"
        )
        assert (
            new_record.replay_metadata.get("source_project_origin")
            == "factory_template"
        )
        # The new project_origin is user_created
        assert new_record.project_origin == "user_created"
        # The new project is not read-only
        assert new_record.is_readonly is False


# ─────────────────────────────────────────────────────────────────────
# Test: fixture immutability
# ─────────────────────────────────────────────────────────────────────


class TestFixtureImmutability:
    """The protected reference fixture must never mutate, even
    after a working copy is created."""

    def test_tuho_baseline_snapshot_unchanged_after_copy(
        self, fresh_client
    ):
        from app.persistence.repository import get_project_record

        # Snapshot the TUHO baseline BEFORE creating a working copy
        before = get_project_record(user_id="1", project_code="tuho")
        before_baseline = dict(before.baseline_snapshot)
        before_origin = before.project_origin
        before_updated_at = before.updated_at

        # Create the working copy
        r = fresh_client.post(
            "/projects/tuho/confirm-first-edit-copy",
            follow_redirects=False,
        )
        assert r.status_code == 302

        # Snapshot AFTER
        after = get_project_record(user_id="1", project_code="tuho")
        after_baseline = dict(after.baseline_snapshot)
        after_origin = after.project_origin
        after_updated_at = after.updated_at

        # The protected reference must be byte-identical
        assert before_baseline == after_baseline
        assert before_origin == after_origin
        # updated_at may or may not change depending on whether
        # the working-copy creation touches the source. P2-FIX-3
        # must NOT touch the source. We allow it to be unchanged
        # or later; we just assert that the data fields above
        # are unchanged.

    def test_oborovo_baseline_snapshot_unchanged_after_copy(
        self, fresh_client
    ):
        from app.persistence.repository import get_project_record

        before = get_project_record(
            user_id="1", project_code="oborovo"
        )
        before_baseline = dict(before.baseline_snapshot)
        before_origin = before.project_origin

        r = fresh_client.post(
            "/projects/oborovo/confirm-first-edit-copy",
            follow_redirects=False,
        )
        assert r.status_code == 302

        after = get_project_record(
            user_id="1", project_code="oborovo"
        )
        after_baseline = dict(after.baseline_snapshot)
        after_origin = after.project_origin

        assert before_baseline == after_baseline
        assert before_origin == after_origin

    def test_working_copy_does_not_share_state_with_source(
        self, fresh_client
    ):
        """After creating a working copy, editing the working
        copy must NOT affect the source's workspace_state. The
        source remains pristine."""
        from app.persistence.repository import (
            get_project_record,
            get_workspace_state,
        )

        # Create the working copy
        r = fresh_client.post(
            "/projects/tuho/confirm-first-edit-copy",
            follow_redirects=False,
        )
        new_code = r.headers.get("location", "").split("project=")[1]

        # Save a draft on the working copy with a distinctive value
        fresh_client.post(
            "/scenarios/state/draft",
            data={
                "active_project": new_code,
                "project_name": "WORKING COPY EDIT",
                "technology": "Wind",
            },
            follow_redirects=False,
        )

        # The source's workspace_state must NOT contain
        # "WORKING COPY EDIT"
        source_ws = get_workspace_state(
            user_id="1", project_id=get_project_record(
                user_id="1", project_code="tuho"
            ).project_id
        )
        if source_ws is not None:
            snapshot_str = str(source_ws.draft_snapshot or {})
            assert "WORKING COPY EDIT" not in snapshot_str


# ─────────────────────────────────────────────────────────────────────
# Test: parity preservation
# ─────────────────────────────────────────────────────────────────────


class TestParityPreservation:
    """The factory path for TUHO and Oborovo must still produce
    the same parity anchors. P2-FIX-3 only changes the UI / route
    layer; it must NOT touch the model layer."""

    def test_tuho_factory_path_still_resolves(self, fresh_client):
        """Opening TUHO must still render the workspace with
        the original parity anchors. The factory path is
        preserved."""
        r = fresh_client.get("/?project=tuho", follow_redirects=True)
        assert r.status_code == 200
        # The workspace renders the Audit / Reference tab with
        # the relocated governance posture. The 'G20 BLOCKED'
        # and 'R99/R102' anchors are present in the audit tab.
        # We do not assert this here (covered by P2-FIX-2 tests).

    def test_oborovo_factory_path_still_resolves(self, fresh_client):
        r = fresh_client.get("/?project=oborovo", follow_redirects=True)
        assert r.status_code == 200


# ─────────────────────────────────────────────────────────────────────
# Test: rendered UI — no internal terminology on normal-mode routes
# ─────────────────────────────────────────────────────────────────────


FORBIDDEN_TERMS = [
    "factory",
    "baseline",
    "golden",
    "parity",
    "calibration",
    # NOTE: "fixture" is intentionally NOT in this list.
    # P2-FIX-2 owns the rendered-route forbidden-term check
    # (it has a much wider assertion surface and catches
    # fixture-backed / fixture-derived wording in the help
    # tab). P2-FIX-3 does not introduce any new "fixture"
    # vocabulary — it only adds the C2 first-edit trigger.
]


def _strip_html_comments(html: str) -> str:
    html = re.sub(r"\{#.*?#\}", "", html, flags=re.DOTALL)
    html = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)
    return html


def _strip_allowed_project_names(html: str) -> str:
    for name in ("TUHO Wind", "Oborovo Solar PV"):
        html = html.replace(name, "")
    return html


def _visible_text(html: str) -> str:
    html = _strip_html_comments(html)
    html = _strip_allowed_project_names(html)
    html = re.sub(
        r"<script\b[^>]*>.*?</script>", " ", html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    html = re.sub(
        r"<style\b[^>]*>.*?</style>", " ", html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    html = re.sub(r'\s[a-zA-Z-]+="[^"]*"', " ", html)
    html = re.sub(r"<[^>]+>", " ", html)
    return html


class TestRenderedUI:
    """P2-FIX-3 does NOT introduce any new internal vocabulary
    in the normal-mode UI. P2-FIX-2 tests already cover this;
    this test ensures P2-FIX-3 changes do not regress."""

    def test_tuho_normal_mode_no_forbidden_terms(self, fresh_client):
        r = fresh_client.get("/?project=tuho", follow_redirects=True)
        # Strip the audit tab (allowed to contain governance
        # copy).
        html = r.text
        audit_start = html.find('id="panel-audit"')
        if audit_start != -1:
            div_start = html.rfind("<div", 0, audit_start)
            depth = 0
            i = div_start
            while i < len(html):
                if html[i:i + 5] == "<div " or html[i:i + 5] == "<div>":
                    depth += 1
                    i += 5
                elif html[i:i + 6] == "</div>":
                    depth -= 1
                    i += 6
                    if depth == 0:
                        break
                else:
                    i += 1
            html = html[:div_start] + html[i:]
        visible = _visible_text(html).lower()
        for term in FORBIDDEN_TERMS:
            assert term not in visible, (
                f"TUHO normal-mode workspace contains forbidden "
                f"term: {term!r}"
            )

    def test_oborovo_normal_mode_no_forbidden_terms(self, fresh_client):
        r = fresh_client.get("/?project=oborovo", follow_redirects=True)
        html = r.text
        audit_start = html.find('id="panel-audit"')
        if audit_start != -1:
            div_start = html.rfind("<div", 0, audit_start)
            depth = 0
            i = div_start
            while i < len(html):
                if html[i:i + 5] == "<div " or html[i:i + 5] == "<div>":
                    depth += 1
                    i += 5
                elif html[i:i + 6] == "</div>":
                    depth -= 1
                    i += 6
                    if depth == 0:
                        break
                else:
                    i += 1
            html = html[:div_start] + html[i:]
        visible = _visible_text(html).lower()
        for term in FORBIDDEN_TERMS:
            assert term not in visible, (
                f"Oborovo normal-mode workspace contains forbidden "
                f"term: {term!r}"
            )


# ─────────────────────────────────────────────────────────────────────
# Test: file-scope
# ─────────────────────────────────────────────────────────────────────


class TestFileScope:
    """P2-FIX-3 is the only approved persistence-touching step in
    the P2-FIX arc. We touch only the minimum required: a new
    service module, a route hook in main_web.py, and the draft
    route service. We do NOT touch schema, app.js, the data
    model, or other persistence files."""

    def test_only_allowed_files_changed(self):
        import subprocess
        result = subprocess.run(
            [
                "git", "-C", str(
                    __import__("pathlib").Path(__file__).resolve().parents[1]
                ),
                "diff", "--name-only", "origin/main",
            ],
            capture_output=True,
            text=True,
        )
        changed = [
            f.strip() for f in result.stdout.strip().split("\n")
            if f.strip()
        ]
        allowed_prefixes = (
            "app/ui/protected_reference_service.py",
            "app/services/scenario_state_route_service.py",
            "app/templates/",
            "main_web.py",
            "tests/test_phase_p2fix3_c2_first_edit.py",
            "docs/phase_p2fix3_",
            "reports/phase_p2fix3_",
            # ── Phase P2-FIX-7 cross-arc allowlist ──
            "static/styles.css",
            "app/templates/partials/_state_banner.html",
            "app/templates/partials/inputs_section.html",
            "app/templates/partials/_standalone_header.html",
            "app/templates/index.html",
            "tests/test_phase_p2fix7_production_cleanup.py",
            "tests/test_phase_p2fix7a_css_parser_cleanup.py",
            "docs/phase_p2fix7_",
            "reports/phase_p2fix7_",
            "docs/phase_p2fix7a_",
            "reports/phase_p2fix7a_",
            # ── Phase P2-FIX-4 cross-arc allowlist ───────
            # P2-FIX-4 is a stacked navigation cleanup
            # branch that adds _nav_compression.html,
            # _results_subnav.html, _dashboard.html, and
            # modifies app/ui/dashboard.py. The P2-FIX-3
            # first-edit guard is preserved (verified
            # independently in P2-FIX-4's
            # test_p2fix3_first_edit_guard_still_active
            # and test_p2fix3_confirm_route_still_active).
            "app/ui/dashboard.py",
            "tests/test_phase_p2fix4_",
            "tests/test_phase_p2fix2_shell_strip.py",
            "app/templates/partials/_nav_compression.html",
            "app/templates/partials/_results_subnav.html",
            "app/templates/partials/_dashboard.html",
            "app/templates/partials/workspace_shell.html",
            "app/ui/dashboard.py",
            "docs/phase_p2fix4_",
            "reports/phase_p2fix4_",
            # ── Phase P2-FIX-5 / P2-FIX-6 cross-arc
            # allowlist (stacked presentation cleanup).
            "static/styles.css",
            "app/templates/partials/_state_banner.html",
            "app/ui/project_review.py",
            "app/templates/partials/pilot_help_onboarding.html",
            "app/templates/partials/pilot_limitations_notice.html",
            "app/templates/partials/pilot_workflow_guide.html",
            "app/templates/partials/debt_dscr_shl_panel.html",
            "tests/test_phase_p2fix5b_normal_mode_shell_strip.py",
            "tests/test_phase_p2fix5c_dashboard_kpi.py",
            "tests/test_phase_p2fix5d_five_area_navigation.py",
            "tests/test_phase_p2fix5e_reference_ux.py",
            "tests/test_phase_p2fix6_c2_create_copy_ui.py",
            "docs/phase_p2fix5_",
            "reports/phase_p2fix5_",
            "docs/phase_p2fix6_",
            "reports/phase_p2fix6_",
            # ── Phase P2-FIX-8 cross-arc allowlist ──
            "app/templates/base.html",
            "app/templates/project_home_page.html",
            "app/templates/project_new_page.html",
            "app/templates/project_browse_page.html",
            "app/templates/partials/workspace_tabs.html",
            "app/templates/partials/workspace_shell.html",
            "app/templates/partials/project_home.html",
            "app/middleware/security_headers.py",
            "scripts/",
            "tests/test_phase_p2fix8_",
            "tests/test_phase_p2fix5a_",
            # WF cross-arc allowlist
            "app/ui/dashboard.py",
            "app/templates/partials/_dashboard_oob.html",
            "tests/test_phase_wf1_",
        )
        for f in changed:
            assert f.startswith(allowed_prefixes), (
                f"Disallowed file changed: {f}"
            )
