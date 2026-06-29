"""C2-PR28/29/30 — Preview Architecture v2 characterization tests.

Captures the EXACT pre-refactor behaviour of the four existing
preview entry points so we can prove "byte-identical response shape"
after the PreviewContext + Registry extraction in
`app/services/preview_context.py` and `app/services/previews/`.

Methodology (mirrors C2-PR23's characterization-first approach):

1. These tests are written and run against the UNMODIFIED
   `app/services/model_preview.py` first. They pass, capturing the
   current public contract.
2. After the refactor in this PR (PreviewContext, previews/
   package, registry), they MUST still pass — proving that the
   extraction preserves behaviour.
3. The new tax-preview tests in
   `tests/test_c2_pr28_30_tax_preview_stub.py` cover ONLY the new
   tax preview shape.

What is captured here (mirrors C2-PR23's characterisations plus the
three response keys added by C2-PR25/26/27):

* Full valid payload: top-level response shape (16 keys) and the
  five existing echo slices (capex/revenue/opex/ebitda/ocf) +
  debt preview.
* Empty payload: same response shape (debt is unconditional, but
  capex/revenue/opex/ebitda/ocf are omitted).
* Invalid payload: still returns ok=False / status='invalid-payload'
  (no debt field).
* Forbidden project: still returns ok=False / status='forbidden-project'
  (no debt field).
* Unit tests of `compute_debt_preview()` with the exact same input/
  output pairs the PR24/PR25 tests rely on.
"""
import os

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")
os.environ.setdefault("FINCO_COOKIE_SECURE", "false")

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from main_web import app
from app.auth import create_session_token, COOKIE_NAME

client = TestClient(app)


def _auth_cookies():
    token = create_session_token()
    return {COOKIE_NAME: token}


def _valid_payload(**overrides):
    payload = {
        "valid": True,
        "dirtyCells": ["capex!C-01.amount"],
        "affectedGroups": ["overview-kpis"],
        "projectDirty": True,
        "reason": "manual-flush",
        "executionStatus": "stubbed",
        "project": None,
    }
    payload.update(overrides)
    return payload


# ─────────────────────────────────────────────────────────────────────
# Top-level shape (byte-identical to PR25-27 final)
# ─────────────────────────────────────────────────────────────────────
class TestTopLevelResponseShapeUnchanged:
    """Captures the EXACT top-level key set of `/model/preview`'s
    valid-payload response. After the C2-PR28/29/30 refactor (which
    ADDS a new top-level 'tax' key as part of the tax preview stub
    in C2-PR30), these tests are re-pinned to the new key set in
    tests/test_c2_pr28_30_tax_preview_stub.py."""

    EXPECTED_TOP_LEVEL_KEYS_PRE_REFACTOR = {
        "ok", "status", "executed", "accepted", "affectedGroups",
        "dirtyCells", "warnings", "message", "overview",
        "capex", "revenue", "opex", "ebitda", "operating_cash_flow",
        "debt",
    }
    # C2-PR30 adds the tax preview top-level key. The full pre-
    # PR30 set PLUS 'tax' is the post-refactor expected set.
    # C2-PR31/32/33 ADDS two more top-level keys: 'irr' and 'dscr'.
    EXPECTED_TOP_LEVEL_KEYS_POST_REFACTOR = (
        EXPECTED_TOP_LEVEL_KEYS_PRE_REFACTOR | {"tax", "irr", "dscr"}
    )

    def test_top_level_keys_for_full_valid_payload(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(
                capexTotalPreview=111.11,
                revenueTotalPreview=222.22,
                opexTotalPreview=333.33,
                ebitdaPreview=444.44,
                operatingCashFlowPreview=555.55,
                # No project: anonymous user-owned baseline resolution
                # is not required for the top-level shape; debt field
                # is still unconditionally present (preview-unavailable).
            ),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert body["ok"] is True
        assert set(body.keys()) == self.EXPECTED_TOP_LEVEL_KEYS_POST_REFACTOR

    def test_invalid_payload_top_level_keys(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(capexTotalPreview="nope"),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert body["ok"] is False
        assert body["status"] == "invalid-payload"
        # On invalid payload NO debt field is rendered.
        assert "debt" not in body
        assert "tax" not in body

    def test_forbidden_project_top_level_keys(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(project="bogus-project-xyz"),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert body["ok"] is False
        assert body["status"] == "forbidden-project"
        assert "debt" not in body
        assert "tax" not in body


# ─────────────────────────────────────────────────────────────────────
# Five existing operating-preview echo slices (byte-identical)
# ─────────────────────────────────────────────────────────────────────
class TestOperatingPreviewEchoFieldsUnchanged:
    """Five client-computed slices that the server only validates and
    echoes. Pre-refactor shape must be byte-identical post-refactor."""

    def test_capex_echo_round_trip(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(capexTotalPreview=111.11),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert body["capex"] == {"capex_total_preview": 111.11, "currency": "EUR"}

    def test_revenue_echo_round_trip(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(revenueTotalPreview=222.22),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert body["revenue"] == {"preview": 222.22, "currency": "EUR"}

    def test_opex_echo_round_trip(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(opexTotalPreview=333.33),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert body["opex"] == {"preview": 333.33, "currency": "EUR"}

    def test_ebitda_echo_round_trip(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(ebitdaPreview=444.44),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert body["ebitda"] == {"preview": 444.44, "currency": "EUR"}

    def test_ocf_echo_round_trip(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(operatingCashFlowPreview=555.55),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert body["operating_cash_flow"] == {"preview": 555.55, "currency": "EUR"}

    def test_omitted_optional_field_not_present_in_response(self):
        """Each of the five optional echo fields must be OMITTED from
        the response (not None) when absent from the request payload."""
        resp = client.post(
            "/model/preview",
            json=_valid_payload(),  # no preview fields
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert "capex" not in body
        assert "revenue" not in body
        assert "opex" not in body
        assert "ebitda" not in body
        assert "operating_cash_flow" not in body


# ─────────────────────────────────────────────────────────────────────
# Debt preview slice (byte-identical to PR25-27)
# ─────────────────────────────────────────────────────────────────────
class TestDebtPreviewSliceUnchanged:
    """The C2-PR25/26/27 debt preview slice (6-key shape) must remain
    byte-identical across the PreviewContext + Registry refactor."""

    def test_debt_unavailable_shape(self):
        """No project in payload → debt preview is unavailable."""
        resp = client.post(
            "/model/preview",
            json=_valid_payload(project=None),
            cookies=_auth_cookies(),
        )
        debt = resp.json()["debt"]
        assert debt == {
            "status": "preview-unavailable",
            "senior_debt_preview": None,
            "saved_total_capex": None,
            "saved_gearing_pct": None,
            "currency": "EUR",
            "basis": "saved-inputs-only",
        }

    def test_debt_keys_set_for_unavailable(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(project=None),
            cookies=_auth_cookies(),
        )
        debt = resp.json()["debt"]
        assert set(debt.keys()) == {
            "status", "senior_debt_preview", "saved_total_capex",
            "saved_gearing_pct", "currency", "basis",
        }

    def test_debt_unavailable_field_ordering_is_stable(self):
        """Pin the key insertion order for the unavailable response so
        a future refactor cannot silently reorder (which would still
        pass `set == set` but break byte-identical JSON byte streams).
        """
        resp = client.post(
            "/model/preview",
            json=_valid_payload(project=None),
            cookies=_auth_cookies(),
        )
        debt = resp.json()["debt"]
        # Pin the exact insertion order: status → senior_debt_preview →
        # saved_total_capex → saved_gearing_pct → currency → basis.
        assert list(debt.keys()) == [
            "status", "senior_debt_preview", "saved_total_capex",
            "saved_gearing_pct", "currency", "basis",
        ]


# ─────────────────────────────────────────────────────────────────────
# Unit-level characterization of the debt preview helper
# ─────────────────────────────────────────────────────────────────────
class TestComputeDebtPreviewUnitUnchanged:
    """Direct unit test pinning compute_debt_preview's behaviour."""

    def test_unit_unavailable_when_no_project_record(self):
        import app.services.model_preview as mp
        result = mp.compute_debt_preview({}, None)
        assert result["status"] == "preview-unavailable"

    def test_unit_unavailable_when_snapshot_missing(self):
        import app.services.model_preview as mp

        class _Fake:
            baseline_snapshot = None

        result = mp.compute_debt_preview({}, _Fake())
        assert result["status"] == "preview-unavailable"

    def test_unit_unavailable_when_inputs_blank(self):
        import app.services.model_preview as mp

        class _Fake:
            baseline_snapshot = {"total_capex_keur": "50000", "gearing_pct": ""}

        result = mp.compute_debt_preview({}, _Fake())
        assert result["status"] == "preview-unavailable"

    def test_unit_ready_with_correct_formula(self):
        import app.services.model_preview as mp

        class _Fake:
            baseline_snapshot = {"total_capex_keur": "60000.00", "gearing_pct": "60"}

        result = mp.compute_debt_preview({}, _Fake())
        assert result["status"] == "preview-ready"
        assert result["senior_debt_preview"] == 36000.00
        assert result["saved_total_capex"] == 60000.00
        assert result["saved_gearing_pct"] == 60.0
        assert result["currency"] == "EUR"
        assert result["basis"] == "saved-inputs-only"

    def test_unit_does_not_read_body(self):
        """The debt preview must NOT use any field from the request
        body. Even if the frontend sends a wild capexTotalPreview, the
        computed senior_debt_preview must come from the saved
        snapshot only.
        """
        import app.services.model_preview as mp

        class _Fake:
            baseline_snapshot = {"total_capex_keur": "10000", "gearing_pct": "50"}

        # Wildly different frontend values — none of these can affect
        # the result.
        body = {
            "capexTotalPreview": 1.0,
            "revenueTotalPreview": 99999999.99,
            "opexTotalPreview": 99999999.99,
            "ebitdaPreview": 99999999.99,
            "operatingCashFlowPreview": 99999999.99,
        }
        result = mp.compute_debt_preview(body, _Fake())
        assert result["senior_debt_preview"] == 5000.0


# ─────────────────────────────────────────────────────────────────────
# Sanity: the route is still wired and reachable
# ─────────────────────────────────────────────────────────────────────
class TestRouteStillReachable:
    def test_unauthenticated_request_returns_redirect(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(),
            follow_redirects=False,
        )
        # 302 to /login or 401 — both are pre-PR28 behaviour.
        assert resp.status_code in (302, 401)

    def test_authenticated_valid_payload_returns_200(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(),
            cookies=_auth_cookies(),
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True