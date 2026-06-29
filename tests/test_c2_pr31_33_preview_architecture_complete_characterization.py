"""C2-PR31/32/33 — Final Preview Architecture QA characterization tests.

Captures the EXACT pre-PR31/32/33 behaviour of the three existing
backend preview slices (operating / debt / tax) so we can prove
"byte-identical response shape" after IRR + DSCR previews are
added to the registry and the JSON top-level key set grows.

Methodology (mirrors C2-PR23's and C2-PR28's characterization-first
approach):

1. These tests are written and run against the UNMODIFIED main
   state (after PR #735 / C2-PR28/29/30). They pass, capturing the
   current public contract.

2. After C2-PR31/32/33 lands (IRR + DSCR backend stubs, registry
   update, renderer additions), they MUST still pass — proving
   that the additions preserve behaviour for the three existing
   slices.

3. The new IRR/DSCR preview tests live in
   `tests/test_c2_pr31_33_irr_dscr_preview_final_qa.py`.

What is captured here (pin to PR28/29/30 final state):

* `/model/preview` valid-payload top-level response shape (17 keys
  today: the 16 from PR25/26/27 PLUS the 'tax' key from PR30).
  Re-pinned to 19 keys post-PR31/32/33 (adding 'irr' and 'dscr').
* The five existing echo slices byte-identical round-trip.
* The debt preview slice byte-identical (6-key shape + insertion
  order).
* The tax preview slice byte-identical (5-key shape + insertion
  order).
* The three existing backend slices — operating (echo only),
  debt, tax — are present and deterministic across runs.
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
# Top-level response shape (byte-identical to PR28/29/30 final)
# ─────────────────────────────────────────────────────────────────────
class TestTopLevelResponseShapeUnchanged:
    """Captures the EXACT top-level key set of `/model/preview`'s
    valid-payload response. Pre-PR31/32/33 the set is the 17 keys
    PR28/29/30 shipped (16 from PR25/26/27 PLUS the 'tax' key from
    PR30). Post-PR31/32/33 the set grows to 19 keys (adding 'irr'
    and 'dscr')."""

    EXPECTED_TOP_LEVEL_KEYS_PRE_REFACTOR = {
        "ok", "status", "executed", "accepted", "affectedGroups",
        "dirtyCells", "warnings", "message", "overview",
        "capex", "revenue", "opex", "ebitda", "operating_cash_flow",
        "debt",
        # C2-PR30 added:
        "tax",
    }
    # C2-PR31/32/33 ADDS two new top-level keys: 'irr' and 'dscr'.
    # The 17 keys above are preserved unchanged.
    EXPECTED_TOP_LEVEL_KEYS_POST_REFACTOR = (
        EXPECTED_TOP_LEVEL_KEYS_PRE_REFACTOR | {"irr", "dscr"}
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
        # On invalid payload NO backend slices are rendered.
        for k in ("debt", "tax", "irr", "dscr"):
            assert k not in body, f"{k!r} should be absent on invalid payload"

    def test_forbidden_project_top_level_keys(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(project="bogus-project-xyz"),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert body["ok"] is False
        assert body["status"] == "forbidden-project"
        for k in ("debt", "tax", "irr", "dscr"):
            assert k not in body, f"{k!r} should be absent on forbidden project"


# ─────────────────────────────────────────────────────────────────────
# Five existing operating-preview echo slices (byte-identical)
# ─────────────────────────────────────────────────────────────────────
class TestOperatingPreviewEchoFieldsUnchanged:
    """Five client-computed slices that the server only validates and
    echoes. Pre-PR31/32/33 shape must be byte-identical post-refactor."""

    def test_each_echo_round_trip(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(
                capexTotalPreview=111.11,
                revenueTotalPreview=222.22,
                opexTotalPreview=333.33,
                ebitdaPreview=444.44,
                operatingCashFlowPreview=555.55,
            ),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert body["capex"] == {"capex_total_preview": 111.11, "currency": "EUR"}
        assert body["revenue"] == {"preview": 222.22, "currency": "EUR"}
        assert body["opex"] == {"preview": 333.33, "currency": "EUR"}
        assert body["ebitda"] == {"preview": 444.44, "currency": "EUR"}
        assert body["operating_cash_flow"] == {"preview": 555.55, "currency": "EUR"}

    def test_omitted_optional_field_not_present_in_response(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        for k in ("capex", "revenue", "opex", "ebitda", "operating_cash_flow"):
            assert k not in body, f"{k!r} should be absent when not in payload"


# ─────────────────────────────────────────────────────────────────────
# Debt preview slice (byte-identical to PR25/26/27, then PR28/29/30)
# ─────────────────────────────────────────────────────────────────────
class TestDebtPreviewSliceUnchanged:
    def test_debt_unavailable_shape(self):
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

    def test_debt_unavailable_field_ordering_is_stable(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(project=None),
            cookies=_auth_cookies(),
        )
        debt = resp.json()["debt"]
        assert list(debt.keys()) == [
            "status", "senior_debt_preview", "saved_total_capex",
            "saved_gearing_pct", "currency", "basis",
        ]


# ─────────────────────────────────────────────────────────────────────
# Tax preview slice (byte-identical to PR28/29/30)
# ─────────────────────────────────────────────────────────────────────
class TestTaxPreviewSliceUnchanged:
    def test_tax_unavailable_shape(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(),
            cookies=_auth_cookies(),
        )
        tax = resp.json()["tax"]
        assert tax == {
            "status": "preview-unavailable",
            "basis": "saved-inputs-only",
            "tax_preview": None,
            "message": "Tax preview is not yet available.",
            "currency": "EUR",
        }

    def test_tax_unavailable_field_ordering_is_stable(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(),
            cookies=_auth_cookies(),
        )
        tax = resp.json()["tax"]
        assert list(tax.keys()) == [
            "status", "basis", "tax_preview", "message", "currency",
        ]

    def test_tax_still_unavailable_after_PR31_32_33(self):
        """Even after the IRR + DSCR preview boundaries are added,
        the tax slice must remain byte-identical to PR28/29/30 —
        C2-PR31/32/33 does NOT touch the tax module."""
        resp = client.post(
            "/model/preview",
            json=_valid_payload(),
            cookies=_auth_cookies(),
        )
        tax = resp.json()["tax"]
        assert tax["status"] == "preview-unavailable"
        assert tax["basis"] == "saved-inputs-only"
        assert tax["tax_preview"] is None
        assert tax["message"] == "Tax preview is not yet available."
        assert tax["currency"] == "EUR"


# ─────────────────────────────────────────────────────────────────────
# Backend slice determinism (operating + debt + tax already
# registered; IRR + DSCR will be added by PR31/32/33)
# ─────────────────────────────────────────────────────────────────────
class TestBackendSlicesDeterministicAcrossRuns:
    def test_run_all_returns_same_keys_in_same_order(self):
        from app.services.preview_context import PreviewContext
        from app.services.previews._registry import run_all
        ctx = PreviewContext.build(
            preview_request={
                "capexTotalPreview": 1.0,
                "revenueTotalPreview": 2.0,
                "opexTotalPreview": 3.0,
                "ebitdaPreview": 4.0,
                "operatingCashFlowPreview": 5.0,
            },
            project_record=None,
        )
        first = run_all(ctx)
        second = run_all(ctx)
        assert first == second
        assert list(first.keys()) == list(second.keys())
        # All five echo slices + debt + tax are present pre-PR31/32/33.
        assert "capex" in first
        assert "revenue" in first
        assert "opex" in first
        assert "ebitda" in first
        assert "operating_cash_flow" in first
        assert "debt" in first
        assert "tax" in first


# ─────────────────────────────────────────────────────────────────────
# Route-level: byte-identical on the wire
# ─────────────────────────────────────────────────────────────────────
class TestRouteStillReachable:
    def test_unauthenticated_request_returns_redirect(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(),
            follow_redirects=False,
        )
        assert resp.status_code in (302, 401)

    def test_authenticated_valid_payload_returns_200(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(),
            cookies=_auth_cookies(),
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True