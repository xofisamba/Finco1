"""UX-2E-NEW-PROJECT-FINAL-SIMPLIFICATION: New Project is the first sheet
of the model, not a setup wizard.

Covers the 5 required test categories from the brief:

1. The New Project page (standalone ``/projects/new`` minimal form and the
   in-workspace ``panel-new-project`` block) renders exactly the four
   required fields: Project name, Technology, Country/market, Capacity.
2. Currency remains optional (present, not required) on both forms.
3. The fields removed from visibility (SPV name, construction start date,
   construction duration, COD date, template source) are no longer
   *rendered* as visible inputs -- they are carried as hidden defaults so
   the backend contract (Phase 51M-1, 17-field route signature) is
   untouched.
4. The end-to-end project creation flow (POST /projects/create) still
   succeeds with only the 4 required fields + optional currency, and the
   removed fields fall back to factory/derived defaults exactly as before.
5. No forbidden setup/internal terminology (factory, create_default_,
   template_source, bootstrap, golden) leaks into either New Project
   template's visible copy.

This module does not touch domain/waterfall/*, app/waterfall_core.py,
app/input_adapter.py, app/project_factories.py, or any financial engine --
only the New Project template wiring already simplified for UX-2E.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-key-ux2e")

import pytest
from fastapi.testclient import TestClient

from app.auth import create_session_token
from app.persistence.projects_repository import get_project_by_code
from main_web import app

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

MINIMAL_TEMPLATE = Path(REPO_ROOT) / "app/templates/partials/new_project_minimal.html"
WORKSPACE_SHELL = Path(REPO_ROOT) / "app/templates/partials/workspace_shell.html"


@pytest.fixture()
def client():
    return TestClient(app, follow_redirects=True)


def _login(client, user_id):
    token = create_session_token(user_id=user_id, username=user_id)
    client.cookies.set("finco_session", token)
    return client


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")


def _new_project_panel_block(text: str) -> str:
    """Extract just the #panel-new-project block from workspace_shell.html."""
    start = text.find('id="panel-new-project"')
    assert start != -1, "panel-new-project block not found"
    # Heuristically capture up to the next top-level tab-panel start.
    end = text.find('id="panel-', start + 1)
    return text[start: end if end != -1 else len(text)]


# ---------------------------------------------------------------------------
# 1. Required fields rendered, nothing else visible
# ---------------------------------------------------------------------------

class TestRequiredFieldsRendered:
    def test_minimal_form_has_required_visible_fields(self):
        text = MINIMAL_TEMPLATE.read_text()
        for name in ("project_name", "project_type", "country_market", "capacity_mw"):
            assert f'name="{name}"' in text, f"{name} missing from minimal form"

    def test_workspace_panel_has_required_visible_fields(self):
        text = _new_project_panel_block(WORKSPACE_SHELL.read_text())
        for name in ("project_name", "project_type", "country_market", "capacity_mw"):
            assert f'name="{name}"' in text, f"{name} missing from workspace panel"


# ---------------------------------------------------------------------------
# 2. Currency stays optional
# ---------------------------------------------------------------------------

class TestCurrencyOptional:
    def test_minimal_form_currency_field_present_and_not_required(self):
        text = MINIMAL_TEMPLATE.read_text()
        m = re.search(r'<select[^>]*name="currency"[^>]*>', text)
        assert m is not None, "currency select missing"
        assert "required" not in m.group(0)
        assert "optional" in text.lower()

    def test_workspace_panel_currency_field_present_and_not_required(self):
        text = _new_project_panel_block(WORKSPACE_SHELL.read_text())
        m = re.search(r'<select[^>]*name="currency"[^>]*>', text)
        assert m is not None, "currency select missing from workspace panel"
        assert "required" not in m.group(0)


# ---------------------------------------------------------------------------
# 3. Removed fields no longer rendered as visible inputs
# ---------------------------------------------------------------------------

REMOVED_FIELDS = (
    "spv_name",
    "construction_start_date",
    "construction_duration_months",
    "cod_date",
    "template_source",
)


class TestRemovedFieldsHiddenOnly:
    def test_minimal_form_removed_fields_are_hidden(self):
        text = MINIMAL_TEMPLATE.read_text()
        for name in REMOVED_FIELDS:
            m = re.search(rf'<input[^>]*name="{name}"[^>]*>', text)
            if m is None:
                # template_source / cod_date / spv_name etc. may simply not
                # exist at all on the minimal form -- that's fine, only
                # assert that IF present it is hidden, never a visible
                # labeled input.
                continue
            assert 'type="hidden"' in m.group(0), (
                f"{name} must be a hidden input on the minimal form, got: {m.group(0)}"
            )

    def test_workspace_panel_removed_fields_are_hidden(self):
        text = _new_project_panel_block(WORKSPACE_SHELL.read_text())
        for name in REMOVED_FIELDS:
            m = re.search(rf'<input[^>]*name="{name}"[^>]*>', text)
            assert m is not None, f"{name} hidden default missing from workspace panel"
            assert 'type="hidden"' in m.group(0), (
                f"{name} must be a hidden input on the workspace panel, got: {m.group(0)}"
            )

    def test_no_visible_labels_for_removed_fields(self):
        for block_text in (
            MINIMAL_TEMPLATE.read_text(),
            _new_project_panel_block(WORKSPACE_SHELL.read_text()),
        ):
            assert "SPV name" not in block_text
            assert "Construction start" not in block_text
            assert "Construction duration" not in block_text
            assert 'for="np-cod_date"' not in block_text
            assert 'for="np-template_source"' not in block_text


# ---------------------------------------------------------------------------
# 4. End-to-end project creation flow still works
# ---------------------------------------------------------------------------

class TestCreationFlowStillWorks:
    def test_minimal_post_creates_project_with_factory_defaults(self, client):
        name = "UX2E Minimal Solar"
        _login(client, "ux2e_solar")
        resp = client.post(
            "/projects/create",
            data={
                "project_name": name,
                "project_type": "Solar",
                "template_source": "",
                "country_market": "Spain",
                "capacity_mw": "30",
            },
        )
        assert resp.status_code == 200
        record = get_project_by_code("ux2e_solar", _slug(name))
        assert record is not None
        snap = record.baseline_snapshot
        assert snap["project_type"] == "Solar"
        assert snap["template_source"] == "generic_solar"
        assert snap["country_market"] == "Spain"
        assert snap["capacity_mw"] == "30"
        # Removed-from-UI fields still get sane derived/factory defaults.
        assert snap["cod_date"]
        assert snap["construction_months"]

    def test_minimal_post_with_currency_field_still_succeeds(self, client):
        """Submitting the optional currency field alongside the 4 required
        fields must not break creation. (Backend currency persistence is a
        pre-existing main_web.py behavior, unchanged and out of scope for
        UX-2E; this test only proves the field is genuinely optional and
        does not block the create flow.)"""
        name = "UX2E Minimal Wind With Currency"
        _login(client, "ux2e_currency")
        resp = client.post(
            "/projects/create",
            data={
                "project_name": name,
                "project_type": "Wind",
                "template_source": "",
                "country_market": "Poland",
                "capacity_mw": "40",
                "currency": "USD",
            },
        )
        assert resp.status_code == 200
        record = get_project_by_code("ux2e_currency", _slug(name))
        assert record is not None
        assert record.baseline_snapshot.get("currency")


# ---------------------------------------------------------------------------
# 5. No forbidden setup/internal terminology in visible copy
# ---------------------------------------------------------------------------

FORBIDDEN_TERMS = ("factory", "create_default_", "template_source", "bootstrap", "golden")


class TestNoForbiddenTerminology:
    def test_minimal_form_visible_copy_has_no_forbidden_terms(self):
        text = MINIMAL_TEMPLATE.read_text()
        # Strip Jinja comments ({# ... #}) which carry developer-facing
        # implementation notes, not user-visible copy.
        visible = re.sub(r"\{#.*?#\}", "", text, flags=re.DOTALL)
        # The hidden template_source input's `name` attribute is allowed
        # (it is not visible copy); strip that single tag before scanning.
        visible = re.sub(r'<input[^>]*name="template_source"[^>]*/?>', "", visible)
        lowered = visible.lower()
        for term in FORBIDDEN_TERMS:
            assert term not in lowered, f"forbidden term '{term}' found in minimal form visible copy"

    def test_workspace_panel_visible_copy_has_no_forbidden_terms(self):
        text = _new_project_panel_block(WORKSPACE_SHELL.read_text())
        visible = re.sub(r"\{#.*?#\}", "", text, flags=re.DOTALL)
        visible = re.sub(r'<input[^>]*name="template_source"[^>]*/?>', "", visible)
        lowered = visible.lower()
        for term in FORBIDDEN_TERMS:
            assert term not in lowered, f"forbidden term '{term}' found in workspace panel visible copy"


# ---------------------------------------------------------------------------
# File scope guard
# ---------------------------------------------------------------------------

class TestUX2EFileScope:
    ALLOWED_PREFIXES = (
        "app/templates/partials/new_project_minimal.html",
        "app/templates/partials/workspace_shell.html",
        "tests/",
    )
    DISALLOWED_PREFIXES = (
        "app/waterfall_core.py",
        "app/input_adapter.py",
        "app/project_factories.py",
        "domain/",
        "app/services/",
        "app/persistence/",
    )

    def test_file_scope(self):
        import shutil
        if shutil.which("git") is None:
            pytest.skip("git not available")
        result = subprocess.run(
            ["git", "-C", REPO_ROOT, "diff", "--name-only", "origin/main"],
            capture_output=True, text=True,
        )
        changed = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
        for f in changed:
            assert not any(f.startswith(p) for p in self.DISALLOWED_PREFIXES), (
                f"UX-2E must not touch {f}"
            )
