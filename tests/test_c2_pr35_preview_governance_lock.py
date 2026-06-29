"""C2-PR35 — Preview Governance Lock.

PERMANENT characterization tests that lock the Preview Architecture
so any future PR attempting to silently introduce new preview
modules, change the registry ordering, mutate the on-the-wire JSON
shape, or sneak financial computation into the frontend will
immediately fail the regression suite.

What is locked here:

  1. Registry has exactly 5 slices: operating, debt, tax, irr, dscr.
     No additional preview modules may silently appear.
  2. Registry ordering is fixed (operating, debt, tax, irr, dscr).
  3. Top-level JSON ordering is deterministic (the 18-key fixed
     shape documented in C2_PREVIEW_ARCHITECTURE_COMPLETE.md).
  4. Each backend-owned slice is unconditionally present in the
     response (even when no echo slice is sent).
  5. PreviewContext remains frozen-immutable.
  6. No frontend JS computation of debt / tax / irr / dscr (only
     formatting and DOM patching).
  7. No financial formulas exist in any runtime JS file
     (recalc-preview.js, runtime-renderer.js).
  8. No persistence writes from /model/preview.
  9. No exports affected.
  10. No Save changes.
  11. No Run changes.
  12. No waterfall / domain logic reachable from any preview
      module.
  13. recalc-preview.js is not allowed to grow new debt/tax/irr/
      dscr arithmetic.

These become permanent regression guardrails for the lifetime of
the preview architecture.
"""
from __future__ import annotations

import os

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")
os.environ.setdefault("FINCO_COOKIE_SECURE", "false")

import inspect
import re
import sys
import urllib.parse
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from main_web import app
from app.auth import create_session_token, COOKIE_NAME
from app.persistence.db import DB_PATH

client = TestClient(app)


def _auth_cookies():
    token = create_session_token()
    return {COOKIE_NAME: token}


def _create_user_project(name="C2 PR35 Lock"):
    resp = client.post(
        "/projects/create",
        data={
            "project_name": name,
            "project_type": "Solar",
            "template_source": "generic_solar",
            "country_market": "Croatia",
            "capacity_mw": "50",
            "cod_date": "2027-01-01",
            "construction_months": "12",
            "horizon_years": "25",
            "tariff_eur_mwh": "60",
            "ppa_term_years": "15",
            "p50_hours": "1400",
            "opex_y1_keur": "1000",
            "total_capex_keur": "50000",
            "gearing_pct": "70",
            "interest_rate_pct": "5",
            "tenor_years": "15",
            "target_dscr": "1.30",
        },
        cookies=_auth_cookies(),
        follow_redirects=False,
    )
    redirect = resp.headers.get("hx-redirect")
    assert redirect, f"no HX-Redirect: {resp.status_code}"
    return urllib.parse.parse_qs(
        urllib.parse.urlparse(redirect).query
    )["project"][0]


# ─────────────────────────────────────────────────────────────────────
# 1. Registry has exactly 5 slices; no additional preview modules
# ─────────────────────────────────────────────────────────────────────
class TestRegistryIsLockedToExactlyFiveSlices:
    """The preview registry is permanently locked to exactly 5
    slices. Any future PR that adds a sixth slice must update
    this assertion AND provide its own characterization +
    guardrail suite — silent additions will fail this test."""

    EXPECTED_SLICE_NAMES = ["operating", "debt", "tax", "irr", "dscr"]

    def test_registry_has_exactly_five_slices(self):
        from app.services.previews._registry import (
            register_default_slices,
            all_slices,
        )
        register_default_slices()
        names = [entry.name for entry in all_slices()]
        assert names == self.EXPECTED_SLICE_NAMES, (
            f"registry slice names changed: got {names}, expected "
            f"{self.EXPECTED_SLICE_NAMES}"
        )

    def test_no_additional_preview_module_files_exist(self):
        """No future PR may silently add a new preview module under
        app/services/previews/ without updating this assertion."""
        preview_dir = Path(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ) / "app" / "services" / "previews"
        # Exactly five slice modules: operating, debt, tax, irr,
        # dscr. Plus three internal modules: _base, _registry,
        # __init__ (8 files total).
        expected_files = {
            "__init__.py",
            "_base.py",
            "_registry.py",
            "operating_preview.py",
            "debt_preview.py",
            "tax_preview.py",
            "irr_preview.py",
            "dscr_preview.py",
        }
        actual_files = {p.name for p in preview_dir.glob("*.py")}
        assert actual_files == expected_files, (
            f"preview modules changed: got {actual_files}, expected "
            f"{expected_files}. If you are adding a new slice, you "
            f"must also update EXPECTED_SLICE_NAMES above."
        )


# ─────────────────────────────────────────────────────────────────────
# 2. Registry ordering is fixed
# ─────────────────────────────────────────────────────────────────────
class TestRegistryOrderingIsFixed:
    EXPECTED_ORDER = ["operating", "debt", "tax", "irr", "dscr"]

    def test_default_slices_register_in_documented_order(self):
        from app.services.previews._registry import (
            register_default_slices,
            all_slices,
        )
        register_default_slices()
        names = [entry.name for entry in all_slices()]
        assert names == self.EXPECTED_ORDER

    def test_run_all_returns_slices_in_documented_order(self):
        """`run_all(context)` returns a dict whose key insertion
        order is the documented order (which is also the JSON byte
        stream order on the wire)."""
        from app.services.preview_context import PreviewContext
        from app.services.previews._registry import run_all

        ctx = PreviewContext.build(
            preview_request={
                "capexTotalPreview": 1.0, "revenueTotalPreview": 2.0,
                "opexTotalPreview": 3.0, "ebitdaPreview": 4.0,
                "operatingCashFlowPreview": 5.0,
            },
            project_record=None,
        )
        result = run_all(ctx)
        # The 4 backend slices must appear in registration order
        # AFTER the 5 operating slices.
        backend_keys = [k for k in result.keys()
                        if k in ("debt", "tax", "irr", "dscr")]
        assert backend_keys == ["debt", "tax", "irr", "dscr"]


# ─────────────────────────────────────────────────────────────────────
# 3. Top-level JSON ordering is deterministic
# ─────────────────────────────────────────────────────────────────────
class TestTopLevelJsonOrderingIsDeterministic:
    """The /model/preview JSON top-level key order is locked."""
    EXPECTED_ORDER = [
        "ok", "status", "executed", "accepted", "affectedGroups",
        "dirtyCells", "warnings", "message", "overview",
        "capex", "revenue", "opex", "ebitda", "operating_cash_flow",
        "debt", "tax", "irr", "dscr",
    ]

    def test_full_payload_response_keys_in_documented_order(self):
        project_code = _create_user_project()
        resp = client.post(
            "/model/preview",
            json={
                "valid": True, "dirtyCells": ["capex!C-01.amount"],
                "affectedGroups": ["overview-kpis"],
                "projectDirty": True, "reason": "manual-flush",
                "executionStatus": "stubbed", "project": project_code,
                "capexTotalPreview": 1.0, "revenueTotalPreview": 2.0,
                "opexTotalPreview": 3.0, "ebitdaPreview": 4.0,
                "operatingCashFlowPreview": 5.0,
            },
            cookies=_auth_cookies(),
        )
        body = resp.json()
        present = [k for k in self.EXPECTED_ORDER if k in body]
        assert list(body.keys()) == present

    def test_empty_payload_response_keys_in_documented_order(self):
        resp = client.post(
            "/model/preview",
            json={
                "valid": True, "dirtyCells": [],
                "affectedGroups": [], "projectDirty": True,
                "reason": "manual-flush", "executionStatus": "stubbed",
                "project": None,
            },
            cookies=_auth_cookies(),
        )
        body = resp.json()
        # Only base envelope + 4 backend slices present (no echo
        # slices since none were sent).
        backend_keys = [k for k in body if k in ("debt", "tax", "irr", "dscr")]
        assert backend_keys == ["debt", "tax", "irr", "dscr"]


# ─────────────────────────────────────────────────────────────────────
# 4. Each backend-owned slice is unconditionally present
# ─────────────────────────────────────────────────────────────────────
class TestBackendOwnedSlicesAlwaysPresent:
    """The four backend-owned slices (debt / tax / irr / dscr) are
    ALWAYS present in the response, regardless of which echo
    fields the frontend sent. This is the visual contract that the
    renderer relies on."""

    def test_all_four_backend_slices_present_with_no_echo_fields(self):
        resp = client.post(
            "/model/preview",
            json={
                "valid": True, "dirtyCells": [],
                "affectedGroups": [], "projectDirty": True,
                "reason": "manual-flush", "executionStatus": "stubbed",
                "project": None,
            },
            cookies=_auth_cookies(),
        )
        body = resp.json()
        for k in ("debt", "tax", "irr", "dscr"):
            assert k in body, (
                f"{k!r} must always be a top-level key in the response"
            )

    def test_all_four_backend_slices_present_with_all_echo_fields(self):
        project_code = _create_user_project()
        resp = client.post(
            "/model/preview",
            json={
                "valid": True, "dirtyCells": ["capex!C-01.amount"],
                "affectedGroups": ["overview-kpis"],
                "projectDirty": True, "reason": "manual-flush",
                "executionStatus": "stubbed", "project": project_code,
                "capexTotalPreview": 1.0, "revenueTotalPreview": 2.0,
                "opexTotalPreview": 3.0, "ebitdaPreview": 4.0,
                "operatingCashFlowPreview": 5.0,
            },
            cookies=_auth_cookies(),
        )
        body = resp.json()
        for k in ("debt", "tax", "irr", "dscr"):
            assert k in body, (
                f"{k!r} must always be a top-level key in the response"
            )


# ─────────────────────────────────────────────────────────────────────
# 5. PreviewContext is immutable
# ─────────────────────────────────────────────────────────────────────
class TestPreviewContextIsImmutable:
    def test_cannot_mutate_any_field(self):
        from app.services.preview_context import PreviewContext
        import dataclasses
        ctx = PreviewContext.build({"valid": True}, None)
        with pytest.raises(dataclasses.FrozenInstanceError):
            ctx.project_record = "x"
        with pytest.raises(dataclasses.FrozenInstanceError):
            ctx.baseline_snapshot = {"x": 1}
        with pytest.raises(dataclasses.FrozenInstanceError):
            ctx.project_code = "X"
        with pytest.raises(dataclasses.FrozenInstanceError):
            ctx.project_id = 1
        with pytest.raises(dataclasses.FrozenInstanceError):
            ctx.currency = "USD"
        with pytest.raises(dataclasses.FrozenInstanceError):
            ctx.preview_request = {"y": 2}


# ─────────────────────────────────────────────────────────────────────
# 6. No frontend JS computation of debt / tax / irr / dscr
# ─────────────────────────────────────────────────────────────────────
class TestNoFrontendBackendOwnedSliceComputation:
    """The runtime renderer + recalc-preview JS are FORBIDDEN from
    computing any backend-owned slice number. They may ONLY format
    and patch DOM with whatever the backend sent."""

    def test_runtime_renderer_has_no_debt_arithmetic(self):
        resp = client.get("/static/modelling/runtime-renderer.js")
        assert resp.status_code == 200
        text = resp.text
        forbidden = [r"\*\s*capex", r"capex\s*\*",
                     r"\*\s*gearing", r"gearing\s*\*"]
        for pat in forbidden:
            assert re.search(pat, text) is None

    def test_runtime_renderer_has_no_tax_arithmetic(self):
        resp = client.get("/static/modelling/runtime-renderer.js")
        text = resp.text
        forbidden = [r"\*\s*tax", r"tax\s*\*"]
        for pat in forbidden:
            assert re.search(pat, text) is None

    def test_runtime_renderer_has_no_irr_arithmetic(self):
        resp = client.get("/static/modelling/runtime-renderer.js")
        text = resp.text
        forbidden = [r"\*\s*irr", r"irr\s*\*"]
        for pat in forbidden:
            assert re.search(pat, text) is None

    def test_runtime_renderer_has_no_dscr_arithmetic(self):
        resp = client.get("/static/modelling/runtime-renderer.js")
        text = resp.text
        forbidden = [r"\*\s*dscr", r"dscr\s*\*"]
        for pat in forbidden:
            assert re.search(pat, text) is None


# ─────────────────────────────────────────────────────────────────────
# 7. No financial formulas exist in runtime JS files
# ─────────────────────────────────────────────────────────────────────
class TestNoFinancialFormulasInRuntimeJs:
    """recalc-preview.js must not grow any debt/tax/irr/dscr
    arithmetic keywords. The runtime renderer is allowed to format
    whatever the backend sent, but never to compute."""

    def test_recalc_preview_js_disclaimer_keywords_unchanged(self):
        resp = client.get("/static/modelling/recalc-preview.js")
        text = resp.text.lower()
        # The two pre-existing disclaimer phrases that are allowed.
        for kw in ("no debt/tax/depreciation/financing",
                   "no debt service, no tax, no depre"):
            assert kw in text, (
                f"recalc-preview.js lost its pre-existing disclaimer: "
                f"{kw!r}"
            )

    def test_recalc_preview_js_has_no_xirr_moic_sculpt_dscr(self):
        resp = client.get("/static/modelling/recalc-preview.js")
        text = resp.text.lower()
        for kw in ("xirr", "moic", "sculpt", "coverage ratio",
                   "loss carryforward", "tax shield"):
            assert kw not in text, (
                f"recalc-preview.js contains forbidden financial "
                f"keyword {kw!r}"
            )


# ─────────────────────────────────────────────────────────────────────
# 8. No persistence writes from /model/preview
# ─────────────────────────────────────────────────────────────────────
class TestNoPersistenceWritesFromPreview:
    def test_db_unchanged_after_preview_round_trip(self):
        before_mtime = os.path.getmtime(DB_PATH) if os.path.exists(DB_PATH) else None
        before_size = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else None
        client.post(
            "/model/preview",
            json={
                "valid": True, "dirtyCells": [],
                "affectedGroups": [], "projectDirty": True,
                "reason": "manual-flush", "executionStatus": "stubbed",
                "project": None,
            },
            cookies=_auth_cookies(),
        )
        after_mtime = os.path.getmtime(DB_PATH) if os.path.exists(DB_PATH) else None
        after_size = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else None
        assert before_mtime == after_mtime
        assert before_size == after_size


# ─────────────────────────────────────────────────────────────────────
# 9. No exports affected
# ─────────────────────────────────────────────────────────────────────
class TestNoExportsAffected:
    """The export endpoints are unaffected by the preview pipeline.
    A distinctive sentinel preview value must not leak into export
    output."""

    def test_csv_export_does_not_carry_preview_sentinel(self):
        # Create a project with distinctive numbers.
        token = create_session_token()
        resp = client.post(
            "/projects/create",
            data={
                "project_name": "C2 PR35 Sentinel",
                "project_type": "Solar",
                "template_source": "generic_solar",
                "country_market": "Croatia",
                "capacity_mw": "50", "cod_date": "2027-01-01",
                "construction_months": "12", "horizon_years": "25",
                "tariff_eur_mwh": "60", "ppa_term_years": "15",
                "p50_hours": "1400", "opex_y1_keur": "1000",
                "total_capex_keur": "91111", "gearing_pct": "77",
                "interest_rate_pct": "5", "tenor_years": "15",
                "target_dscr": "1.30",
            },
            cookies={COOKIE_NAME: token},
            follow_redirects=False,
        )
        project_code = urllib.parse.parse_qs(
            urllib.parse.urlparse(resp.headers["hx-redirect"]).query
        )["project"][0]

        # Issue a preview round-trip.
        prev_resp = client.post(
            "/model/preview",
            json={
                "valid": True, "dirtyCells": [],
                "affectedGroups": [], "projectDirty": True,
                "reason": "manual-flush", "executionStatus": "stubbed",
                "project": project_code,
            },
            cookies={COOKIE_NAME: token},
        )
        senior_debt = prev_resp.json()["debt"]["senior_debt_preview"]
        sentinel = str(senior_debt).replace(".", "")

        # CSV export must not contain the sentinel.
        export_resp = client.get(
            f"/exports/runtime-summary.csv?project={project_code}",
            cookies={COOKIE_NAME: token},
        )
        assert export_resp.status_code == 200
        assert sentinel not in export_resp.text


# ─────────────────────────────────────────────────────────────────────
# 10. No Save changes
# ─────────────────────────────────────────────────────────────────────
class TestNoSaveChanges:
    def test_preview_response_has_no_save_fields(self):
        resp = client.post(
            "/model/preview",
            json={
                "valid": True, "dirtyCells": [],
                "affectedGroups": [], "projectDirty": True,
                "reason": "manual-flush", "executionStatus": "stubbed",
                "project": None,
            },
            cookies=_auth_cookies(),
        )
        body = resp.json()
        for k in ("saved_baseline_id", "saved_snapshot",
                  "save_errors", "saved_at"):
            assert k not in body


# ─────────────────────────────────────────────────────────────────────
# 11. No Run changes
# ─────────────────────────────────────────────────────────────────────
class TestNoRunChanges:
    def test_preview_post_does_not_invoke_waterfall(
        self, monkeypatch
    ):
        import app.waterfall_core as waterfall_core
        called = []

        def _boom(*args, **kwargs):
            called.append(args)
            raise AssertionError(
                "Run must never fire as a side-effect of /model/preview"
            )

        monkeypatch.setattr(
            waterfall_core, "run_project", _boom, raising=False
        )
        resp = client.post(
            "/model/preview",
            json={
                "valid": True, "dirtyCells": [],
                "affectedGroups": [], "projectDirty": True,
                "reason": "manual-flush", "executionStatus": "stubbed",
                "project": None,
            },
            cookies=_auth_cookies(),
        )
        assert resp.status_code == 200
        assert called == []


# ─────────────────────────────────────────────────────────────────────
# 12. No waterfall / domain logic reachable from any preview module
# ─────────────────────────────────────────────────────────────────────
class TestNoWaterfallOrDomainInPreviewModules:
    FORBIDDEN_PATTERNS = [
        "from app.domain", "import app.domain",
        "from app.waterfall_core", "import app.waterfall_core",
        "from app.waterfall_runner", "import app.waterfall_runner",
        "from app.input_adapter", "import app.input_adapter",
        "from app.project_factories", "import app.project_factories",
        "from app.proj_factories", "import app.proj_factories",
    ]

    @pytest.mark.parametrize("module_path", [
        "app.services.preview_context",
        "app.services.previews._base",
        "app.services.previews._registry",
        "app.services.previews.operating_preview",
        "app.services.previews.debt_preview",
        "app.services.previews.tax_preview",
        "app.services.previews.irr_preview",
        "app.services.previews.dscr_preview",
        "app.services.model_preview",
    ])
    def test_module_does_not_import_forbidden(self, module_path):
        import importlib
        mod = importlib.import_module(module_path)
        source = inspect.getsource(mod)
        for pattern in self.FORBIDDEN_PATTERNS:
            assert pattern not in source, (
                f"{module_path} contains forbidden import: {pattern!r}"
            )


# ─────────────────────────────────────────────────────────────────────
# 13. recalc-preview.js cannot grow new debt/tax/irr/dscr arithmetic
# ─────────────────────────────────────────────────────────────────────
class TestRecalcPreviewJsCannotGrowBackendArithmetic:
    """recalc-preview.js is the legacy module that builds the
    /model/preview payload. It must NEVER compute any backend-
    owned slice value — only the 5 echo slices."""

    def test_recalc_preview_js_has_no_saved_capex_arithmetic(self):
        resp = client.get("/static/modelling/recalc-preview.js")
        text = resp.text
        # The renderer is forbidden from computing saved-capex
        # arithmetic.
        forbidden = [
            r"saved_total_capex\s*\*",
            r"saved_gearing_pct\s*\*",
            r"savedTotalCapex\s*\*",
            r"savedGearingPct\s*\*",
        ]
        for pat in forbidden:
            assert re.search(pat, text) is None, (
                f"recalc-preview.js contains forbidden pattern {pat!r}"
            )

    def test_recalc_preview_js_has_no_backend_slice_arithmetic(self):
        resp = client.get("/static/modelling/recalc-preview.js")
        text = resp.text
        # The renderer is forbidden from computing any backend-
        # owned slice value.
        forbidden = [
            r"taxPreview\s*\*", r"irrPreview\s*\*",
            r"dscrPreview\s*\*",
            r"tax_preview\s*\*", r"irr_preview\s*\*",
            r"dscr_preview\s*\*",
        ]
        for pat in forbidden:
            assert re.search(pat, text) is None, (
                f"recalc-preview.js contains forbidden pattern {pat!r}"
            )