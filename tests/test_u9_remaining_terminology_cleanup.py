"""U9-REMAINING-EXTERNAL-TERMINOLOGY-CLEANUP.

Presentation-text-only remediation: removes remaining "factory"
terminology that leaked into external-facing surfaces despite
U5 (Export Polish) and U7 (Error & Warning Cleanup).

Covers the four surfaces identified by review:
  1. Institutional workbook export cell values (no "Factory-bound" /
     "factory" wording in exported cell text).
  2. CAPEX / OPEX editing tab rendered text (no "factory templates" /
     "factory default value" wording).
  3. Workspace shell lifecycle label and project home quick-action
     description (no "Factory reference" / "Browse factory
     references").
  4. This file itself -- widened terminology coverage so these
     surfaces cannot regress.

No formula, runtime, export-value, or validation-classification
changes are covered or required by these tests -- this is a
presentation-text-only check.
"""
from __future__ import annotations

import io
import os
import pathlib

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-key-u9")

import openpyxl
import pytest
from fastapi.testclient import TestClient

from app.auth import create_session_token
from app.export.institutional_workbook import export_institutional_workbook_skeleton
from main_web import app

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

FORBIDDEN_TERMS = (
    "Factory-bound",
    "factory template",
    "factory templates",
    "Factory reference",
    "Browse factory references",
)


@pytest.fixture()
def client():
    return TestClient(app, follow_redirects=True)


def _login(client, user_id):
    token = create_session_token(user_id=user_id, username=user_id)
    client.cookies.set("finco_session", token)
    return client


# ---------------------------------------------------------------------------
# 1. Institutional workbook export cell values
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def workbook():
    data = export_institutional_workbook_skeleton("tuho")
    return openpyxl.load_workbook(io.BytesIO(data))


def _all_cell_text(wb):
    return " ".join(
        str(c.value)
        for sheet in wb.worksheets
        for row in sheet.iter_rows()
        for c in row
        if c.value
    )


class TestInstitutionalWorkbookNoFactoryWording:
    def test_no_forbidden_terms_in_exported_cells(self, workbook):
        text = _all_cell_text(workbook)
        for term in FORBIDDEN_TERMS:
            assert term not in text, f"forbidden term leaked into workbook cells: {term!r}"

    def test_no_factory_bound_prose_in_exported_cells(self, workbook):
        # Internal runtime_origin/template_origin sentinel identifiers
        # (e.g. "factory_base_runtime", "project_factory:tuho") are out
        # of scope for this presentation-text-only sweep -- they are
        # shared enum-like values defined in app/services/* (disallowed
        # for this task) and used for internal classification, not
        # free-form prose. Only "Factory-bound"-style prose is checked.
        text = _all_cell_text(workbook)
        assert "Factory-bound" not in text


# ---------------------------------------------------------------------------
# 2. CAPEX / OPEX tab rendered text
# ---------------------------------------------------------------------------


class TestCapexOpexTabsNoFactoryWording:
    def test_opex_template_source_no_factory_wording(self):
        text = (REPO_ROOT / "app/templates/partials/sheet_opex.html").read_text()
        assert "factory" not in text.lower()

    def test_capex_detail_template_source_no_rendered_factory_text(self):
        text = (REPO_ROOT / "app/templates/partials/sheet_capex_detail.html").read_text()
        # The badge-factory CSS class name may remain; only rendered text
        # content (between tags) must not say "factory".
        assert ">factory<" not in text
        assert "factory default value" not in text

    def test_opex_detail_template_source_no_rendered_factory_text(self):
        text = (REPO_ROOT / "app/templates/partials/sheet_opex_detail.html").read_text()
        assert ">factory<" not in text
        assert "factory default value" not in text


# ---------------------------------------------------------------------------
# 3. Workspace shell lifecycle label and project home quick action
# ---------------------------------------------------------------------------


class TestWorkspaceShellAndHomeNoFactoryWording:
    def test_workspace_shell_no_factory_reference_label(self):
        text = (REPO_ROOT / "app/templates/partials/workspace_shell.html").read_text()
        assert "Factory reference" not in text
        assert "Factory references are read-only" not in text

    def test_tuho_workspace_response_no_forbidden_terms(self, client):
        _login(client, "u9_workspace")
        resp = client.get("/?project=tuho")
        assert resp.status_code == 200
        for term in FORBIDDEN_TERMS:
            assert term not in resp.text, f"forbidden term leaked: {term!r}"

    def test_project_home_no_browse_factory_references(self, client):
        _login(client, "u9_home")
        resp = client.get("/")
        assert resp.status_code == 200
        assert "Browse factory references" not in resp.text

    def test_project_home_partial_source_no_forbidden_terms(self):
        text = (REPO_ROOT / "app/templates/partials/project_home.html").read_text()
        assert "Browse factory references" not in text
