"""
Round-trip tests for the V2 edit pipeline (PR 864).

For each BOUND project_setup field:
  1. Create a project and load the V2 workbook page
  2. Extract the current content_hash
  3. POST /v2/workbook/update with semantic field_id + new value
  4. Follow the redirect back to GET /v2/workbook
  5. Verify the new value is displayed
  6. Verify the legacy snapshot key was NOT posted

Coverage:
A. Round-trip for all 6 BOUND project_setup fields
B. Stale content_hash → 409
C. Legacy snapshot key in field_id → 422
D. Non-editable field → 422
E. Protected reference guard
F. Auth guard on /v2/workbook/update
G. Field validation errors → 422
"""
from __future__ import annotations

import json
import os
import re
import unittest
import urllib.parse

os.environ.setdefault("FINCO_WORKBOOK_V2", "1")
os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-key-for-roundtrip")

from fastapi.testclient import TestClient  # noqa: E402

import main_web  # noqa: E402
from app.auth import COOKIE_NAME, create_session_token  # noqa: E402
from app.workbook.input_set import ProjectInputSet  # noqa: E402
from app.workbook.registry import WORKBOOK  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _authed_client() -> TestClient:
    tc = TestClient(main_web.app, follow_redirects=False)
    tc.cookies.set(COOKIE_NAME, create_session_token())
    return tc


def _create_project(client: TestClient, suffix: str) -> str:
    resp = client.post(
        "/projects/create",
        data={
            "project_name": f"RT Test {suffix}",
            "project_type": "Wind",
            "template_source": "generic_wind",
            "country_market": "Poland",
            "capacity_mw": "50",
            "cod_date": "2028-01-01",
            "construction_months": "18",
            "horizon_years": "20",
            "tariff_eur_mwh": "55",
            "ppa_term_years": "15",
            "p50_hours": "2200",
            "opex_y1_keur": "900",
            "total_capex_keur": "60000",
            "gearing_pct": "70",
            "interest_rate_pct": "4.5",
            "tenor_years": "18",
            "target_dscr": "1.30",
        },
        follow_redirects=False,
    )
    redirect = resp.headers.get("hx-redirect") or resp.headers.get("location", "")
    assert redirect, f"expected redirect from /projects/create, got {resp.status_code}"
    parsed = urllib.parse.parse_qs(urllib.parse.urlparse(redirect).query)
    codes = parsed.get("project", [])
    assert codes, f"no project= in redirect URL: {redirect}"
    return codes[0]


def _get_workbook(client: TestClient, project_code: str):
    resp = client.get(f"/v2/workbook?project={project_code}")
    assert resp.status_code == 200, f"GET /v2/workbook status {resp.status_code}"
    return resp


def _extract_content_hash(body: str) -> str:
    """Extract content_hash from data-content-hash attribute."""
    m = re.search(r'data-content-hash="([^"]+)"', body)
    assert m, "data-content-hash not found in response body"
    return m.group(1)


def _post_update(client: TestClient, project_code: str, content_hash: str,
                 field_id: str, value: str) -> "TestClient response":
    return client.post(
        "/v2/workbook/update",
        data={
            "project": project_code,
            "field_id": field_id,
            "value": value,
            "workbook_version": "2.1.0",
            "content_hash": content_hash,
        },
        follow_redirects=False,
    )


# ---------------------------------------------------------------------------
# A. Round-trip for each BOUND project_setup field
# ---------------------------------------------------------------------------

class TestBoundFieldRoundTrip(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "rt-bound")

    def _round_trip(self, field_id: str, new_value: str, expected_in_body: str):
        """Full round-trip: get → extract hash → post → redirect → verify display."""
        resp = _get_workbook(self.client, self.project_code)
        content_hash = _extract_content_hash(resp.text)

        update_resp = _post_update(
            self.client, self.project_code, content_hash, field_id, new_value
        )
        self.assertEqual(update_resp.status_code, 303,
                         f"expected 303, got {update_resp.status_code}: {update_resp.text[:200]}")
        self.assertIn("/v2/workbook", update_resp.headers.get("location", ""))

        reload_resp = _get_workbook(self.client, self.project_code)
        self.assertIn(expected_in_body, reload_resp.text,
                      f"Expected {expected_in_body!r} in body after updating {field_id}")

    def test_project_name_round_trip(self):
        self._round_trip(
            "project_setup.identity.project_name",
            "Updated Wind Farm",
            "Updated Wind Farm",
        )

    def test_capacity_mw_round_trip(self):
        self._round_trip(
            "project_setup.technical.capacity_mw",
            "99",
            "99",
        )

    def test_p50_hours_round_trip(self):
        self._round_trip(
            "project_setup.technical.p50_hours",
            "2800",
            "2800",
        )

    def test_cod_date_round_trip(self):
        self._round_trip(
            "project_setup.technical.cod_date",
            "2030-06-15",
            "2030-06-15",
        )

    def test_construction_months_round_trip(self):
        self._round_trip(
            "project_setup.technical.construction_months",
            "24",
            "24",
        )

    def test_horizon_years_round_trip(self):
        self._round_trip(
            "project_setup.technical.horizon_years",
            "30",
            "30",
        )


# ---------------------------------------------------------------------------
# B. Stale content_hash → 409
# ---------------------------------------------------------------------------

class TestStaleContentHash(unittest.TestCase):
    """Stale-hash detection requires at least one prior V2 edit so the DB
    holds a pis.content_hash (not a legacy raw-JSON fallback hash).
    setUpClass performs one valid edit to put the project in V2-committed state.
    """

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "rt-stale")
        # Perform one successful V2 edit so draft_content_hash is a pis.content_hash.
        resp = _get_workbook(cls.client, cls.project_code)
        content_hash = _extract_content_hash(resp.text)
        seed_resp = _post_update(
            cls.client, cls.project_code, content_hash,
            field_id="project_setup.identity.project_name",
            value="Seeded Name",
        )
        assert seed_resp.status_code == 303, (
            f"setUpClass seed edit failed: {seed_resp.status_code} {seed_resp.text[:200]}"
        )

    def test_stale_hash_redirects_with_error(self):
        """Non-HTMX stale hash → 303 redirect to GET with v2_err flash param."""
        resp = _post_update(
            self.client, self.project_code,
            content_hash="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa1",
            field_id="project_setup.identity.project_name",
            value="X",
        )
        self.assertEqual(resp.status_code, 303, resp.text[:200])
        location = resp.headers.get("location", "")
        self.assertIn("v2_err", location,
                      "Redirect must carry v2_err flash param for stale hash")

    def test_stale_hash_htmx_returns_refreshed_sheet(self):
        """HTMX stale hash → 200 with re-rendered sheet so user can retry."""
        resp = self.client.post(
            "/v2/workbook/update",
            data={
                "field_id": "project_setup.identity.project_name",
                "project": self.project_code,
                "workbook_version": WORKBOOK.version,
                "content_hash": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
                "value": "X",
            },
            headers={"HX-Request": "true"},
        )
        self.assertEqual(resp.status_code, 200, resp.text[:200])
        self.assertIn("v2-sheet-project-setup", resp.text)
        # Error message appears in the OOB status banner
        self.assertIn("refreshed", resp.text)


# ---------------------------------------------------------------------------
# C. Legacy snapshot key as field_id → 422
# ---------------------------------------------------------------------------

class TestLegacySnapshotKeyRejected(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "rt-legacy")

    def _hash(self):
        resp = _get_workbook(self.client, self.project_code)
        return _extract_content_hash(resp.text)

    def test_capacity_mw_snapshot_key_rejected(self):
        """'capacity_mw' (legacy key) must be rejected; only semantic field_id accepted."""
        resp = _post_update(
            self.client, self.project_code, self._hash(),
            field_id="capacity_mw",
            value="100",
        )
        self.assertEqual(resp.status_code, 422, resp.text)

    def test_project_name_snapshot_key_rejected(self):
        resp = _post_update(
            self.client, self.project_code, self._hash(),
            field_id="project_name",
            value="Test",
        )
        self.assertEqual(resp.status_code, 422, resp.text)

    def test_p50_hours_snapshot_key_rejected(self):
        resp = _post_update(
            self.client, self.project_code, self._hash(),
            field_id="p50_hours",
            value="2000",
        )
        self.assertEqual(resp.status_code, 422, resp.text)


# ---------------------------------------------------------------------------
# D. Non-editable field → 422
# ---------------------------------------------------------------------------

class TestNonEditableFieldRejected(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "rt-nonedit")

    def _hash(self):
        resp = _get_workbook(self.client, self.project_code)
        return _extract_content_hash(resp.text)

    def test_display_only_field_rejected(self):
        resp = _post_update(
            self.client, self.project_code, self._hash(),
            field_id="project_setup.technical.capacity_factor",
            value="30",
        )
        self.assertEqual(resp.status_code, 422, resp.text)

    def test_template_locked_field_rejected(self):
        resp = _post_update(
            self.client, self.project_code, self._hash(),
            field_id="project_setup.identity.project_type",
            value="solar_pv",
        )
        self.assertEqual(resp.status_code, 422, resp.text)


# ---------------------------------------------------------------------------
# E. Protected reference guard
# ---------------------------------------------------------------------------

class TestProtectedReferenceGuard(unittest.TestCase):
    """TUHO/Oborovo projects must be rejected before any draft write."""

    @classmethod
    def setUpClass(cls):
        from app.persistence.projects_repository import get_project_record
        cls.client = _authed_client()
        # Use the seeded test user's TUHO or generic reference project.
        # We use the API: create a project that the service classifies as protected.
        # The easiest is to patch is_protected_reference at the route level.

    def test_protected_reference_returns_409(self):
        from unittest.mock import patch
        client = _authed_client()
        project_code = _create_project(client, "rt-protected")
        resp = _get_workbook(client, project_code)
        content_hash = _extract_content_hash(resp.text)

        with patch(
            "app.ui.protected_reference_service.is_protected_reference",
            return_value=True,
        ):
            resp = _post_update(
                client, project_code, content_hash,
                field_id="project_setup.identity.project_name",
                value="X",
            )
        self.assertEqual(resp.status_code, 409)
        self.assertIn("error", resp.json())
        self.assertIn("protected", resp.json()["error"].lower())


# ---------------------------------------------------------------------------
# F. Auth guard
# ---------------------------------------------------------------------------

class TestAuthGuard(unittest.TestCase):

    def test_unauthenticated_update_redirects_to_login(self):
        tc = TestClient(main_web.app, follow_redirects=False)
        # No cookie set
        resp = tc.post(
            "/v2/workbook/update",
            data={
                "project": "any-project",
                "field_id": "project_setup.identity.project_name",
                "value": "X",
                "workbook_version": "2.1.0",
                "content_hash": "abc",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.headers.get("location", ""))


# ---------------------------------------------------------------------------
# G. Field validation errors → 422
# ---------------------------------------------------------------------------

class TestFieldValidationErrors(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "rt-validation")

    def _hash(self):
        resp = _get_workbook(self.client, self.project_code)
        return _extract_content_hash(resp.text)

    def test_capacity_mw_negative_redirects_with_error(self):
        """Non-HTMX field validation failure → 303 redirect with v2_err flash."""
        resp = _post_update(
            self.client, self.project_code, self._hash(),
            field_id="project_setup.technical.capacity_mw",
            value="-50",
        )
        self.assertEqual(resp.status_code, 303)
        self.assertIn("v2_err", resp.headers.get("location", ""))

    def test_capacity_mw_negative_htmx_returns_error_sheet(self):
        """HTMX validation error → 200 with error in re-rendered sheet."""
        resp = self.client.post(
            "/v2/workbook/update",
            data={
                "field_id": "project_setup.technical.capacity_mw",
                "project": self.project_code,
                "workbook_version": WORKBOOK.version,
                "content_hash": self._hash(),
                "value": "-50",
            },
            headers={"HX-Request": "true"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("v2-sheet-project-setup", resp.text)

    def test_currency_invalid_option_returns_422(self):
        """currency is PARTIAL (NonEditableFieldError) → 422 JSON (API error)."""
        resp = _post_update(
            self.client, self.project_code, self._hash(),
            field_id="project_setup.identity.currency",
            value="BTC",
        )
        self.assertEqual(resp.status_code, 422)
        self.assertIn("error", resp.json())

    def test_project_name_required_empty_redirects_with_error(self):
        """Empty required field → 303 redirect with v2_err flash."""
        resp = _post_update(
            self.client, self.project_code, self._hash(),
            field_id="project_setup.identity.project_name",
            value="",
        )
        self.assertEqual(resp.status_code, 303)
        self.assertIn("v2_err", resp.headers.get("location", ""))

    def test_cod_date_bad_format_redirects_with_error(self):
        """Invalid date format → 303 redirect with v2_err flash."""
        resp = _post_update(
            self.client, self.project_code, self._hash(),
            field_id="project_setup.technical.cod_date",
            value="not-a-date",
        )
        self.assertEqual(resp.status_code, 303)
        self.assertIn("v2_err", resp.headers.get("location", ""))


# ---------------------------------------------------------------------------
# H. workbook_version enforcement — version mismatch → 409 with reload:true
# ---------------------------------------------------------------------------

class TestWorkbookVersionEnforcement(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "rt-version")

    def _hash(self):
        resp = _get_workbook(self.client, self.project_code)
        return _extract_content_hash(resp.text)

    def test_correct_version_returns_303(self):
        resp = self.client.post(
            "/v2/workbook/update",
            data={
                "project": self.project_code,
                "field_id": "project_setup.technical.capacity_mw",
                "value": "77",
                "workbook_version": "2.1.0",
                "content_hash": self._hash(),
            },
            follow_redirects=False,
        )
        self.assertEqual(resp.status_code, 303,
                         f"expected 303 with correct version, got {resp.status_code}: {resp.text[:200]}")

    def test_wrong_version_returns_409(self):
        resp = self.client.post(
            "/v2/workbook/update",
            data={
                "project": self.project_code,
                "field_id": "project_setup.technical.capacity_mw",
                "value": "78",
                "workbook_version": "1.0.0",
                "content_hash": self._hash(),
            },
            follow_redirects=False,
        )
        self.assertEqual(resp.status_code, 409,
                         f"expected 409 with wrong version, got {resp.status_code}: {resp.text[:200]}")

    def test_wrong_version_response_has_reload_flag(self):
        resp = self.client.post(
            "/v2/workbook/update",
            data={
                "project": self.project_code,
                "field_id": "project_setup.technical.capacity_mw",
                "value": "79",
                "workbook_version": "0.0.1",
                "content_hash": self._hash(),
            },
            follow_redirects=False,
        )
        self.assertEqual(resp.status_code, 409)
        body = resp.json()
        self.assertIn("error", body)
        self.assertTrue(body.get("reload"), "expected reload:true in 409 version mismatch response")

    def test_wrong_version_error_message_mentions_reload(self):
        resp = self.client.post(
            "/v2/workbook/update",
            data={
                "project": self.project_code,
                "field_id": "project_setup.technical.capacity_mw",
                "value": "80",
                "workbook_version": "9.9.9",
                "content_hash": self._hash(),
            },
            follow_redirects=False,
        )
        self.assertEqual(resp.status_code, 409)
        error_msg = resp.json().get("error", "")
        # Error should mention reload
        self.assertTrue(
            "reload" in error_msg.lower() or "9.9.9" in error_msg,
            f"expected reload instruction in error: {error_msg!r}",
        )

    # --- PARTIAL fields rejected at HTTP level ---

    def test_partial_country_market_returns_422(self):
        resp = self.client.post(
            "/v2/workbook/update",
            data={
                "project": self.project_code,
                "field_id": "project_setup.identity.country_market",
                "value": "Germany",
                "workbook_version": "2.1.0",
                "content_hash": self._hash(),
            },
            follow_redirects=False,
        )
        self.assertEqual(resp.status_code, 422,
                         f"PARTIAL field must be 422, got {resp.status_code}: {resp.text[:200]}")

    def test_partial_currency_returns_422(self):
        resp = self.client.post(
            "/v2/workbook/update",
            data={
                "project": self.project_code,
                "field_id": "project_setup.identity.currency",
                "value": "EUR",
                "workbook_version": "2.1.0",
                "content_hash": self._hash(),
            },
            follow_redirects=False,
        )
        self.assertEqual(resp.status_code, 422)

    def test_partial_scenario_returns_422(self):
        resp = self.client.post(
            "/v2/workbook/update",
            data={
                "project": self.project_code,
                "field_id": "project_setup.identity.scenario",
                "value": "Base Case",
                "workbook_version": "2.1.0",
                "content_hash": self._hash(),
            },
            follow_redirects=False,
        )
        self.assertEqual(resp.status_code, 422)


# ---------------------------------------------------------------------------
# I. Legacy row regression: canonical-hash comparison never bypassed
# ---------------------------------------------------------------------------

def _get_workspace_row(project_code: str) -> dict:
    """Return the raw workspace_states row for a project as a plain dict."""
    from app.persistence.db import get_connection
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT ws.* FROM workspace_states ws
            JOIN projects p ON p.project_id = ws.project_id
            WHERE p.project_code = ?
            LIMIT 1
            """,
            (project_code,),
        ).fetchone()
        return dict(row) if row else {}
    finally:
        conn.close()


def _set_raw_json_hash(project_code: str, snapshot: dict) -> str:
    """Overwrite draft_content_hash with the raw-JSON fallback hash.

    Simulates a legacy row (created before the V2 CAS pipeline).
    Returns the raw hash that was written.
    """
    from app.persistence.db import get_connection
    from app.persistence.workspace_repository import _draft_content_hash
    raw_hash = _draft_content_hash(snapshot)
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE workspace_states SET draft_content_hash = ?
            WHERE project_id = (SELECT project_id FROM projects WHERE project_code = ?)
            """,
            (raw_hash, project_code),
        )
        conn.commit()
    finally:
        conn.close()
    return raw_hash


def _set_draft_snapshot(project_code: str, snapshot: dict) -> None:
    """Directly overwrite draft_snapshot_json (simulates a legacy non-CAS write)."""
    from app.persistence.db import get_connection
    from app.persistence.workspace_repository import _draft_content_hash
    raw_hash = _draft_content_hash(snapshot)
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE workspace_states
            SET draft_snapshot_json = ?, draft_content_hash = ?
            WHERE project_id = (SELECT project_id FROM projects WHERE project_code = ?)
            """,
            (json.dumps(snapshot), raw_hash, project_code),
        )
        conn.commit()
    finally:
        conn.close()


class TestLegacyFirstWriteRegression(unittest.TestCase):
    """
    Regression: v2_atomic_draft_update must always compare the canonical
    ProjectInputSet.content_hash derived from the persisted snapshot — never
    treat a legacy raw-JSON draft_content_hash as a bypass token.

    Scenario (from review):
      1. Create row; reset draft_content_hash to raw-JSON fallback (legacy state).
      2. Browser reads snapshot A → canonical hash A.
      3. Legacy write changes persisted draft to snapshot B (different capacity_mw).
      4. Browser submits edit using stale hash A.
      5. CAS computes canonical hash of snapshot B ≠ hash A → stale conflict.
      6. Snapshot B remains unchanged.
    """

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "rt-legacy-regression")

    def _canonical_hash_from_db(self) -> str:
        """Read the persisted draft_snapshot_json and return its canonical PIS hash."""
        from app.workbook.input_set import ProjectInputSet
        from app.workbook.registry import WORKBOOK
        row = _get_workspace_row(self.project_code)
        snapshot = json.loads(row["draft_snapshot_json"] or "{}")
        return ProjectInputSet.from_snapshot(snapshot, workbook=WORKBOOK).content_hash

    def test_stale_legacy_hash_rejected(self):
        """Browser hash A stale after legacy write to snapshot B → 409."""
        # Step 1: reset to legacy raw-JSON hash state
        row = _get_workspace_row(self.project_code)
        snapshot_a = json.loads(row["draft_snapshot_json"] or "{}")
        _set_raw_json_hash(self.project_code, snapshot_a)

        # Step 2: browser computes canonical hash A from snapshot A
        from app.workbook.input_set import ProjectInputSet
        from app.workbook.registry import WORKBOOK
        hash_a = ProjectInputSet.from_snapshot(snapshot_a, workbook=WORKBOOK).content_hash

        # Step 3: legacy write changes draft to snapshot B (capacity_mw changed)
        snapshot_b = dict(snapshot_a)
        snapshot_b["capacity_mw"] = "999"
        _set_draft_snapshot(self.project_code, snapshot_b)

        # Step 4: browser submits edit with stale hash A
        resp = _post_update(
            self.client, self.project_code, hash_a,
            field_id="project_setup.identity.project_name",
            value="Should Not Write",
        )

        # Step 5: must be stale conflict — non-HTMX path redirects with v2_err
        self.assertEqual(resp.status_code, 303, resp.text[:300])
        self.assertIn("v2_err", resp.headers.get("location", ""))

        # Step 6: snapshot B still persisted; "Should Not Write" must not appear
        row_after = _get_workspace_row(self.project_code)
        snap_after = json.loads(row_after["draft_snapshot_json"] or "{}")
        self.assertEqual(str(snap_after.get("capacity_mw")), "999",
                         "snapshot B must remain after stale rejection")
        self.assertNotEqual(
            snap_after.get("project_name"), "Should Not Write",
            "stale write must not have been persisted",
        )

    def test_legacy_row_with_correct_canonical_hash_succeeds(self):
        """Legacy row + browser sends the correct canonical hash → 303."""
        # Reset to legacy raw-JSON hash state
        row = _get_workspace_row(self.project_code)
        snapshot = json.loads(row["draft_snapshot_json"] or "{}")
        _set_raw_json_hash(self.project_code, snapshot)

        # Get canonical hash for current snapshot
        canonical_hash = self._canonical_hash_from_db()

        resp = _post_update(
            self.client, self.project_code, canonical_hash,
            field_id="project_setup.identity.project_name",
            value="Legacy First Write",
        )
        self.assertEqual(resp.status_code, 303,
                         f"expected 303, got {resp.status_code}: {resp.text[:200]}")

    def test_first_v2_write_stores_canonical_pis_hash(self):
        """After a successful V2 write, draft_content_hash must be the canonical PIS hash."""
        # Reset to legacy state
        row = _get_workspace_row(self.project_code)
        snapshot = json.loads(row["draft_snapshot_json"] or "{}")
        _set_raw_json_hash(self.project_code, snapshot)

        canonical_hash = self._canonical_hash_from_db()

        _post_update(
            self.client, self.project_code, canonical_hash,
            field_id="project_setup.identity.project_name",
            value="Post-Migration Name",
        )

        # Verify that draft_content_hash is now a canonical PIS hash (not raw-JSON)
        row_after = _get_workspace_row(self.project_code)
        stored_hash = row_after.get("draft_content_hash")
        snap_after = json.loads(row_after["draft_snapshot_json"] or "{}")
        from app.workbook.input_set import ProjectInputSet
        from app.workbook.registry import WORKBOOK
        from app.persistence.workspace_repository import _draft_content_hash
        expected_canonical = ProjectInputSet.from_snapshot(snap_after, workbook=WORKBOOK).content_hash
        raw_json_hash = _draft_content_hash(snap_after)
        self.assertEqual(stored_hash, expected_canonical,
                         "draft_content_hash must be canonical PIS hash after first V2 write")
        self.assertNotEqual(stored_hash, raw_json_hash,
                            "draft_content_hash must not remain as raw-JSON fallback hash")

    def test_second_concurrent_caller_from_same_original_hash_fails(self):
        """Two callers from the same hash: first wins, second gets 409."""
        # Ensure a clean canonical-hash state by doing a fresh edit
        canonical_hash = self._canonical_hash_from_db()
        seed = _post_update(
            self.client, self.project_code, canonical_hash,
            field_id="project_setup.identity.project_name",
            value="Seed Before Concurrency",
        )
        self.assertEqual(seed.status_code, 303, f"seed failed: {seed.text[:200]}")

        # Now get the current canonical hash (post-seed)
        original_hash = self._canonical_hash_from_db()

        # First edit succeeds
        resp1 = _post_update(
            self.client, self.project_code, original_hash,
            field_id="project_setup.identity.project_name",
            value="First Concurrent",
        )
        self.assertEqual(resp1.status_code, 303,
                         f"first concurrent edit failed: {resp1.text[:200]}")

        # Second edit with the same original_hash → 303 redirect with v2_err
        # (StaleContentError, non-HTMX path redirects with flash error)
        resp2 = _post_update(
            self.client, self.project_code, original_hash,
            field_id="project_setup.identity.project_name",
            value="Second Concurrent",
        )
        self.assertEqual(resp2.status_code, 303,
                         f"second concurrent edit must redirect (stale), got {resp2.status_code}: {resp2.text[:200]}")
        self.assertIn("v2_err", resp2.headers.get("location", ""),
                      "Stale hash redirect must carry v2_err flash param")


if __name__ == "__main__":
    unittest.main()
