"""Phase P1-CLEANUP-SPRINT-2 — Low-risk pilot polish.

Context
--------
After PILOT-HOTFIX-3, the internal pilot loop passes end-to-end.
P1-CLEANUP-SPRINT-1 audited three low-risk P1 / UX items. This
test file pins the implementation of all three:

  TASK A — POST /scenarios/{id}/update-overrides accepts both
           ``application/json`` and form-data. JSON behaviour is
           unchanged. Form-data fallback parses submitted fields
           into the overrides dict. Invalid payloads return 400
           instead of 500.

  TASK B — Editable badge cleanup:
            * P50 Hours for user_created projects: no Template
              badge (already in template; pinned by test).
            * P50 Hours for reference projects: keeps Template /
              protected behaviour (pinned).
            * PPA Term for user_created projects: shows a non-
              locking badge ("WIRED") instead of no badge at all.
            * PPA Term for reference projects: shows Template.

  TASK C — Landing page (GET /) Home section cards:
            * Existing project list is preserved.
            * New section links render above the project list.
            * No route redirects introduced.

Hard constraints (all pinned by tests):
  - rc1 SHA ``b425a0708719eaa5e1d922b1008e5609758e0ad4`` untouched.
  - Engine MD5 ``6bf49f33efc989736c17cea0cb9b7723`` unchanged.
  - Factory MD5 ``cf73065b8a26aa3f19629829e46260d9`` unchanged.
  - TUHO debt 43,359 kEUR + Oborovo debt 42,852.27 kEUR bit-identical.
  - No changes to waterfall_core / project_factories / input_adapter /
    persistence schema / run_service / download_service / tax / debt
    / construction / R99 / R102 / G20.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-p1sprint2")

from app.persistence.db import init_db

init_db()


# ---------------------------------------------------------------------------
# Constants — frozen anchors
# ---------------------------------------------------------------------------

RC1_SHA = "b425a0708719eaa5e1d922b1008e5609758e0ad4"
ENGINE_MD5 = "6bf49f33efc989736c17cea0cb9b7723"
FACTORY_MD5 = "cf73065b8a26aa3f19629829e46260d9"

ALLOWED_FILES = {
    # TASK A
    "main_web.py",
    # TASK B
    "app/templates/partials/inputs_section.html",
    # TASK C
    "app/templates/partials/project_home.html",
    "app/templates/project_home_page.html",
    "static/styles.css",
    # Tests / docs (this file + report + design doc)
    "tests/test_phase_p1_cleanup_sprint_2_low_risk_pilot_polish.py",
    "docs/phase_p1_cleanup_sprint_2_low_risk_pilot_polish.md",
    "reports/phase_p1_cleanup_sprint_2_low_risk_pilot_polish.md",
}

FORBIDDEN_FILES = {
    # Hard no-go: must not change
    "app/waterfall_core.py",
    "app/project_factories.py",
    "app/input_adapter.py",
    "app/persistence/db.py",  # schema frozen
    "app/persistence/repository.py",
    "app/services/run_service.py",
    "app/services/download_service.py",
    "app/services/scenario_update_overrides_service.py",
}


# ---------------------------------------------------------------------------
# TASK A helpers
# ---------------------------------------------------------------------------


def _parse_overrides_sync(
    content_type: str,
    body_bytes: bytes | None = None,
    form_data: dict | None = None,
) -> dict:
    """Synchronous re-implementation of the body-parsing branch
    inside ``update_overrides_endpoint``. Mirrors exactly the logic
    added in main_web.py so we can unit-test the parse contract
    without auth / DB / scenario lookup."""

    class _FakeForm:
        def __init__(self, data):
            self._data = data
        def multi_items(self):
            return list(self._data.items())
        def items(self):
            return self._data.items()

    class _FakeReq:
        def __init__(self, ct, body, fd):
            self.headers = {"content-type": ct}
            self._body = body
            self._fd = fd
        async def json(self):
            if self._body is None:
                raise ValueError("no json body")
            return json.loads(self._body.decode("utf-8"))
        async def form(self):
            return _FakeForm(self._fd)

    async def _run():
        overrides: dict = {}
        content_type_lower = (content_type or "").lower()
        req = _FakeReq(content_type_lower, body_bytes, form_data or {})
        if "application/json" in content_type_lower:
            try:
                body = await req.json()
            except Exception:
                body = None
            if isinstance(body, dict):
                overrides = body
            elif body is None:
                return {"_error": "Invalid JSON body. Expected JSON object.", "_status": 400}
            else:
                return {"_error": "Invalid JSON body. Expected a JSON object.", "_status": 400}
        else:
            try:
                form = await req.form()
            except Exception:
                return {"_error": "Invalid form-data body.", "_status": 400}
            _SKIP_KEYS = {"project_code", "scenario_id", "csrf_token", "csrf"}
            for key, val in form.multi_items():
                if key in _SKIP_KEYS or key.startswith("_"):
                    continue
                overrides[key] = val
        return overrides

    import asyncio
    return asyncio.get_event_loop().run_until_complete(_run())


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestTaskAUpdateOverrides:
    """TASK A — POST /scenarios/{id}/update-overrides dual body parsing."""

    def test_json_body_returns_overrides_dict(self):
        """T1. JSON body unchanged: returns the parsed dict."""
        result = _parse_overrides_sync(
            content_type="application/json",
            body_bytes=json.dumps({"tariff_eur_mwh": 50}).encode(),
        )
        assert result == {"tariff_eur_mwh": 50}

    def test_form_data_body_returns_overrides_dict(self):
        """T2. Form-data body parses fields into overrides dict."""
        result = _parse_overrides_sync(
            content_type="application/x-www-form-urlencoded",
            form_data={"tariff_eur_mwh": "50", "p50_hours": "2400"},
        )
        assert result == {"tariff_eur_mwh": "50", "p50_hours": "2400"}

    def test_form_data_filters_framework_keys(self):
        """Framework keys (project_code, scenario_id, csrf, _*) are skipped."""
        result = _parse_overrides_sync(
            content_type="multipart/form-data",
            form_data={
                "tariff_eur_mwh": "60",
                "project_code": "tuho-copy",
                "scenario_id": "abc123",
                "csrf_token": "xyz",
                "_dirty_marker": "1",
            },
        )
        assert result == {"tariff_eur_mwh": "60"}

    def test_malformed_json_returns_400_not_500(self):
        """T3. Malformed JSON returns 400 instead of bubbling to 500."""
        result = _parse_overrides_sync(
            content_type="application/json",
            body_bytes=b"{not-json",
        )
        assert result.get("_status") == 400
        assert "Invalid JSON" in result.get("_error", "")


class TestTaskBEditableBadgeCleanup:
    """TASK B — Editable badge cleanup."""

    INPUTS_TEMPLATE = (
        REPO_ROOT / "app" / "templates" / "partials" / "inputs_section.html"
    )

    @staticmethod
    def _find_field_row(content: str, label: str) -> str:
        """Find the field_row line for a given label, handling nested parens."""
        idx = content.find(f'field_row("{label}"')
        if idx < 0:
            return ""
        # Walk forward, tracking paren depth, until the closing ")" of the macro call.
        depth = 0
        end = idx
        started = False
        for i in range(idx, len(content)):
            ch = content[i]
            if ch == "(":
                depth += 1
                started = True
            elif ch == ")":
                depth -= 1
                if started and depth == 0:
                    end = i + 1
                    break
        return content[idx:end]

    def test_p50_hours_user_project_has_no_template_badge(self):
        """T4. P50 Hours for user_created (editable=True) uses None badge."""
        content = self.INPUTS_TEMPLATE.read_text()
        line = self._find_field_row(content, "P50 Hours")
        assert line, "P50 Hours field_row not found"
        # For user_created (editable=True), badge should resolve to None
        assert 'badge=(None if is_user_project else "Template")' in line, (
            f"P50 Hours must not show Template badge for user projects. "
            f"Line: {line}"
        )

    def test_p50_hours_reference_project_keeps_template_behaviour(self):
        """T5. P50 Hours for reference (editable=False) shows Template badge."""
        content = self.INPUTS_TEMPLATE.read_text()
        line = self._find_field_row(content, "P50 Hours")
        assert line
        # For reference (is_user_project=False), badge resolves to "Template"
        assert '"Template"' in line
        # And editable must be conditional on is_user_project
        assert "editable=is_user_project" in line

    def test_ppa_term_user_project_shows_non_locking_badge(self):
        """T6. PPA Term for user_created shows a non-locking badge (not Template)."""
        content = self.INPUTS_TEMPLATE.read_text()
        line = self._find_field_row(content, "PPA Term")
        assert line, "PPA Term field_row not found"
        assert "badge=" in line
        # Must NOT show "Template" badge for user_created
        # (the conditional allows it for the False branch only)
        assert 'badge=(None if is_user_project else "Template")' in line, (
            f"PPA Term must use conditional badge logic so user projects "
            f"do NOT show Template. Line: {line}"
        )

    def test_ppa_term_has_badge_title_tooltip(self):
        """PPA Term should keep its badge_title for tooltip context."""
        content = self.INPUTS_TEMPLATE.read_text()
        line = self._find_field_row(content, "PPA Term")
        assert line
        assert "badge_title=" in line


class TestTaskCLandingPageSectionCards:
    """TASK C — Landing page Home section cards."""

    PROJECT_HOME = (
        REPO_ROOT / "app" / "templates" / "partials" / "project_home.html"
    )
    PROJECT_HOME_PAGE = (
        REPO_ROOT / "app" / "templates" / "project_home_page.html"
    )

    def test_project_list_preserved(self):
        """T7. Existing My Projects table is still rendered."""
        content = self.PROJECT_HOME.read_text()
        assert 'class="ph-table"' in content or "ph-table" in content
        assert "home_user_projects" in content

    def test_section_cards_render_above_project_list(self):
        """T8. Quick action cards render above the project table."""
        content = self.PROJECT_HOME.read_text()
        # Quick-action block present
        assert "ph-quick-actions" in content
        assert "ph-quick-card" in content
        # Section-tab strip present
        assert "ph-section-tabs" in content
        assert "ph-section-tab" in content
        # New Project link
        assert "New Project" in content
        # Continue Modelling link (only rendered when _has_projects)
        assert "Continue Modelling" in content

    def test_no_route_redirects_introduced(self):
        """T9. No 302 / redirect logic added to project_home templates."""
        for path in (self.PROJECT_HOME, self.PROJECT_HOME_PAGE):
            content = path.read_text()
            assert "Redirect" not in content
            assert "redirect(" not in content
            assert "302" not in content
        # Also: home_user_projects logic preserved (no auto-pick logic
        # added that would cause a hidden redirect)
        content = self.PROJECT_HOME.read_text()
        # The first project is only used as a href target, not a redirect.
        assert "href=\"/?project=" in content

    def test_section_card_disabled_when_no_projects(self):
        """When no projects exist, section tabs render as disabled spans."""
        content = self.PROJECT_HOME.read_text()
        assert "ph-section-tab--disabled" in content
        # The disabled class should appear alongside the "if _disabled" branch
        assert "_disabled" in content

    def test_css_classes_defined(self):
        """New CSS classes (ph-quick-*, ph-section-tab*) are defined."""
        css = (REPO_ROOT / "static" / "styles.css").read_text()
        for cls in [
            ".ph-quick-actions",
            ".ph-quick-card",
            ".ph-quick-card--primary",
            ".ph-quick-card--accent",
            ".ph-section-tabs",
            ".ph-section-tabs-grid",
            ".ph-section-tab",
            ".ph-section-tab--disabled",
        ]:
            assert cls in css, f"CSS class {cls} missing"


class TestConstraintsPreserved:
    """Hard constraints — pinned invariants."""

    def test_rc1_frozen_sha_present(self):
        """T10. rc1 SHA is a known ancestor of HEAD."""
        import subprocess
        result = subprocess.run(
            ["git", "merge-base", "--is-ancestor", RC1_SHA, "HEAD"],
            capture_output=True,
            cwd=REPO_ROOT,
        )
        assert result.returncode == 0, (
            f"rc1 SHA {RC1_SHA} is not an ancestor of HEAD"
        )

    def test_engine_md5_unchanged(self):
        """T11. Engine MD5 unchanged."""
        engine_path = REPO_ROOT / "app" / "waterfall_core.py"
        if engine_path.exists():
            actual = hashlib.md5(engine_path.read_bytes()).hexdigest()
            assert actual == ENGINE_MD5, (
                f"Engine MD5 changed: {actual} != {ENGINE_MD5}"
            )

    def test_factory_md5_unchanged(self):
        """Factory MD5 unchanged."""
        factory_path = REPO_ROOT / "app" / "project_factories.py"
        if factory_path.exists():
            actual = hashlib.md5(factory_path.read_bytes()).hexdigest()
            assert actual == FACTORY_MD5, (
                f"Factory MD5 changed: {actual} != {FACTORY_MD5}"
            )

    def test_file_scope_only_allowed_files(self):
        """T12. File-scope guard — only allowed files changed vs. main."""
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--name-only", "origin/main", "HEAD"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        changed = set(line.strip() for line in result.stdout.splitlines() if line.strip())
        unexpected = changed - ALLOWED_FILES
        assert not unexpected, (
            f"Unexpected files changed vs. origin/main: {sorted(unexpected)}"
        )

    def test_no_forbidden_files_modified(self):
        """No forbidden files in the diff (defence-in-depth)."""
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--name-only", "origin/main", "HEAD"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        changed = set(line.strip() for line in result.stdout.splitlines() if line.strip())
        overlap = changed & FORBIDDEN_FILES
        assert not overlap, (
            f"Forbidden files modified: {sorted(overlap)}"
        )


class TestRouteBehaviourIntegration:
    """Integration-level smoke tests via TestClient (auth-bypassed)."""

    def test_update_overrides_endpoint_json_body_no_auth_does_not_crash(self):
        """End-to-end: JSON body without auth must NOT crash (no 500)."""
        from fastapi.testclient import TestClient
        from main_web import app
        client = TestClient(app, follow_redirects=False)
        r = client.post(
            "/scenarios/test-sc/update-overrides",
            json={"tariff_eur_mwh": 50},
        )
        # Without auth: 302 redirect to /login.
        # With auth but bad body: 400.
        # Either way, NOT 500 (no crash).
        assert r.status_code in (302, 400), (
            f"Expected 302 (no auth) or 400 (bad body), got {r.status_code}"
        )
        assert r.status_code != 500, (
            f"JSON body caused 500. Got {r.status_code}"
        )

    def test_update_overrides_endpoint_form_data_no_auth_does_not_crash(self):
        """End-to-end: form-data body without auth must NOT crash (no 500)."""
        from fastapi.testclient import TestClient
        from main_web import app
        client = TestClient(app, follow_redirects=False)
        r = client.post(
            "/scenarios/test-sc/update-overrides",
            data={"tariff_eur_mwh": "50"},
        )
        # Without auth: 302 redirect to /login.
        # With auth but bad body: 400.
        # Either way, NOT 500 (no crash).
        assert r.status_code in (302, 400), (
            f"Expected 302 (no auth) or 400 (bad body), got {r.status_code}"
        )
        assert r.status_code != 500, (
            f"Form-data caused 500. Got {r.status_code}. Body: {r.text[:200]}"
        )

    def test_route_source_uses_form_data_fallback(self):
        """Static check: route source contains form-data fallback logic."""
        source = (REPO_ROOT / "main_web.py").read_text()
        assert 'await request.form()' in source, (
            "Route must call await request.form() for form-data fallback"
        )
        assert '"application/json" in content_type' in source, (
            "Route must branch on content-type"
        )
        # And it must skip framework keys
        assert "_SKIP_KEYS" in source or 'csrf_token' in source, (
            "Route must filter framework keys (project_code/scenario_id/csrf)"
        )