"""UX-2C-2-INPUTS-SHEET-SIMPLIFICATION.

Pins the requirements from the UX-2C-2 task: the Inputs tab should feel
like an Excel workbook input sheet, not a validation/admin screen.

  1. All 8 input sections still render: Identity, Schedule, Technical,
     Revenue, CAPEX, OPEX, Debt, Tax.
  2. No noisy per-row / repeated normal-user admin text: Saved,
     Internal, Template, Model default, Protected.
  3. Editable fields render with the input-cell style (``inp-input``).
  4. Read-only/calculated fields render with a muted formula-cell
     style (``inp-value-formula-cell``).
  5. Caveat icons/tooltips exist; the old long inline caveat-explainer
     block (``inp-driver-status-note`` rendered in the template) is
     gone -- caveat text lives in the per-row tooltip only.
  6. The protected/reference notice appears at most once.
  7. No forbidden internal terms leak into the rendered tab: factory,
     create_default_, golden, template_source.

This is presentation-only: no model/formula/runtime/export/validation
logic is touched by this phase.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-key-ux2c2")

from fastapi.testclient import TestClient  # noqa: E402

from app.auth import create_session_token  # noqa: E402
from main_web import app  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
INPUTS_SECTION = REPO_ROOT / "app" / "templates" / "partials" / "inputs_section.html"


@pytest.fixture(scope="module")
def logged_in_client():
    client = TestClient(app)
    token = create_session_token(user_id="1", username="test_user")
    client.cookies.set("finco_session", token)
    return client


@pytest.fixture(scope="module")
def user_project_code(logged_in_client):
    resp = logged_in_client.post(
        "/projects/create",
        data={
            "project_name": "UX2C2 Test Solar",
            "project_type": "Solar",
            "template_source": "",
            "country_market": "DE",
            "capacity_mw": "10",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    code = re.sub(r"[^a-z0-9]+", "-", "UX2C2 Test Solar".strip().lower()).strip("-")
    return code


def _inputs_panel_html(resp_text: str) -> str:
    start = resp_text.find('id="panel-inputs"')
    end = resp_text.find('id="panel-scenario"')
    assert start != -1 and end != -1 and end > start, (
        "panel-inputs not found in workspace response"
    )
    return resp_text[start:end]


class TestAllSectionsRender:
    @pytest.mark.parametrize(
        "section",
        ["Identity", "Schedule", "Technical", "Revenue", "CAPEX", "OPEX", "Debt", "Tax"],
    )
    def test_section_header_present(self, logged_in_client, section):
        r = logged_in_client.get("/?project=tuho", follow_redirects=True)
        panel = _inputs_panel_html(r.text)
        assert section in panel, f"Inputs tab is missing the {section!r} section"


class TestNoNoisyNormalUserText:
    NOISY_TERMS = ("Saved", "Internal", "Template", "Model default", "Protected")

    @staticmethod
    def _per_row_badge_texts(panel: str) -> list[str]:
        texts = []
        for row_match in re.finditer(r'<div class="inp-row">.*?</div>', panel, re.DOTALL):
            row = row_match.group(0)
            for badge_match in re.finditer(r'<span class="badge[^"]*"[^>]*>([^<]*)</span>', row):
                texts.append(badge_match.group(1).strip())
        return texts

    def test_no_noisy_badge_text_per_row(self, logged_in_client):
        r = logged_in_client.get("/?project=tuho", follow_redirects=True)
        panel = _inputs_panel_html(r.text)
        for text in self._per_row_badge_texts(panel):
            for noisy in self.NOISY_TERMS:
                assert noisy not in text, (
                    f"Per-row badge must not carry admin wording {noisy!r}: {text!r}"
                )

    def test_protected_notice_not_repeated_per_row(self, logged_in_client):
        r = logged_in_client.get("/?project=tuho", follow_redirects=True)
        panel = _inputs_panel_html(r.text)
        for text in self._per_row_badge_texts(panel):
            assert "Protected" not in text


class TestEditableInputCellStyle:
    def test_editable_field_uses_inp_input_class(self, logged_in_client, user_project_code):
        r = logged_in_client.get(f"/?project={user_project_code}", follow_redirects=True)
        panel = _inputs_panel_html(r.text)
        assert 'class="inp-input"' in panel

    def test_inp_input_css_defines_editable_tint(self):
        css = (REPO_ROOT / "static" / "styles.css").read_text(encoding="utf-8")
        assert ".inp-input {" in css


class TestReadOnlyFormulaCellStyle:
    def test_calculated_field_uses_formula_cell_class(self, logged_in_client):
        r = logged_in_client.get("/?project=tuho", follow_redirects=True)
        panel = _inputs_panel_html(r.text)
        assert "inp-value-formula-cell" in panel

    def test_formula_cell_css_defined(self):
        css = (REPO_ROOT / "static" / "styles.css").read_text(encoding="utf-8")
        assert ".inp-value-formula-cell" in css


class TestCaveatsAreIconsNotInlineText:
    def test_caveat_icon_present(self, logged_in_client):
        r = logged_in_client.get("/?project=tuho", follow_redirects=True)
        panel = _inputs_panel_html(r.text)
        assert 'class="inp-caveat-icon"' in panel

    def test_long_inline_driver_status_note_removed_from_template(self):
        src = INPUTS_SECTION.read_text(encoding="utf-8")
        assert "inp-driver-status-note" not in src, (
            "The long inline driver-status caveat-explainer block must "
            "not be rendered in inputs_section.html; caveats are "
            "conveyed via per-row tooltips only."
        )

    def test_driver_status_note_css_class_still_defined(self):
        # CSS class definition is kept even though the template no
        # longer renders it (presentation-only removal, not a hard
        # breaking change to any other consumer of the class).
        css = (REPO_ROOT / "static" / "styles.css").read_text(encoding="utf-8")
        assert ".inp-driver-status-note" in css


class TestProtectedNoticeAtMostOnce:
    def test_readonly_notice_appears_at_most_once_for_reference_project(self, logged_in_client):
        r = logged_in_client.get("/?project=tuho", follow_redirects=True)
        panel = _inputs_panel_html(r.text)
        assert panel.count('class="inp-readonly-notice"') <= 1


class TestNoForbiddenInternalTerms:
    FORBIDDEN = ("factory", "create_default_", "golden", "template_source")

    @pytest.mark.parametrize("project_code", ["tuho", "oborovo"])
    @pytest.mark.parametrize("forbidden", FORBIDDEN)
    def test_forbidden_term_not_in_rendered_inputs_tab(self, logged_in_client, project_code, forbidden):
        r = logged_in_client.get(f"/?project={project_code}", follow_redirects=True)
        panel = _inputs_panel_html(r.text)
        assert forbidden not in panel


class TestFileScope:
    ALLOWED_PREFIXES = (
        "app/templates/partials/inputs_section.html",
        "static/styles.css",
        "tests/",
    )
    DISALLOWED_PREFIXES = (
        "domain/",
        "app/waterfall_core.py",
        "app/input_adapter.py",
        "app/project_factories.py",
        "app/persistence/",
        "app/excel_export.py",
        "app/export/",
        "main_api.py",
        "app/templates/partials/sheet_capex.html",
        "app/templates/partials/sheet_opex.html",
        "app/templates/partials/scenario_matrix.html",
        "app/templates/partials/_dashboard.html",
        "app/ui/dashboard.py",
        "app/templates/partials/new_project_minimal.html",
        "app/export/",
    )

    def test_only_allowed_files_changed(self):
        import shutil
        import subprocess

        if shutil.which("git") is None or not (REPO_ROOT / ".git").exists():
            pytest.skip("git not available")
        result = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "diff", "--name-only", "origin/main"],
            capture_output=True, text=True,
        )
        changed = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
        for f in changed:
            assert not any(f.startswith(p) for p in self.DISALLOWED_PREFIXES), (
                f"UX-2C-2 must not touch {f}"
            )
            assert any(f.startswith(p) for p in self.ALLOWED_PREFIXES), (
                f"UX-2C-2 file outside allowed scope: {f}"
            )
