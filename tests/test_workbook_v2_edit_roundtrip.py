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
            "workbook_version": "2.0.0",
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

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, "rt-stale")

    def test_stale_hash_returns_409(self):
        resp = _post_update(
            self.client, self.project_code,
            content_hash="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa1",
            field_id="project_setup.identity.project_name",
            value="X",
        )
        self.assertEqual(resp.status_code, 409, resp.text[:200])

    def test_stale_hash_error_body(self):
        resp = _post_update(
            self.client, self.project_code,
            content_hash="stale-hash",
            field_id="project_setup.identity.project_name",
            value="X",
        )
        self.assertIn("error", resp.json())


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
                "workbook_version": "2.0.0",
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

    def test_capacity_mw_negative_returns_422(self):
        resp = _post_update(
            self.client, self.project_code, self._hash(),
            field_id="project_setup.technical.capacity_mw",
            value="-50",
        )
        self.assertEqual(resp.status_code, 422)
        self.assertIn("error", resp.json())

    def test_currency_invalid_option_returns_422(self):
        resp = _post_update(
            self.client, self.project_code, self._hash(),
            field_id="project_setup.identity.currency",
            value="BTC",
        )
        self.assertEqual(resp.status_code, 422)
        self.assertIn("error", resp.json())

    def test_project_name_required_empty_returns_422(self):
        resp = _post_update(
            self.client, self.project_code, self._hash(),
            field_id="project_setup.identity.project_name",
            value="",
        )
        self.assertEqual(resp.status_code, 422)
        self.assertIn("error", resp.json())

    def test_cod_date_bad_format_returns_422(self):
        resp = _post_update(
            self.client, self.project_code, self._hash(),
            field_id="project_setup.technical.cod_date",
            value="not-a-date",
        )
        self.assertEqual(resp.status_code, 422)


if __name__ == "__main__":
    unittest.main()
