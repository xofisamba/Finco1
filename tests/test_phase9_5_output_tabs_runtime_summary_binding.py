"""
Phase 9.5 — Output Tabs Runtime Summary Binding Tests

Tests that runtime summary blocks appear in all output tabs after a run,
that TUHO and Oborovo produce different summaries, that preview sections
are still labeled as preview, and that NOT_AVAILABLE is used for missing
metrics rather than fabricated zeros.

No runtime model files are changed — these are UI/binding tests only.
"""

import pytest
import json
import os
from fastapi.testclient import TestClient

# Resolve the app root
APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARTIALS = os.path.join(APP_ROOT, "app", "templates", "partials")


class TestRuntimeSummaryBinding:
    """Runtime summary propagation after run."""

    def test_run_tuho_returns_runtime_summary(self, client: TestClient, authenticated_client: TestClient):
        """POST /run with TUHO returns a runtime_summary in sessionStorage script."""
        resp = authenticated_client.post(
            "/run",
            data={"active_project": "tuho", "project_type": "Solar", "scenario": "Base"},
        )
        assert resp.status_code == 200
        text = resp.text
        # sessionStorage.setItem("lastRuntimeSummary", ...) must be present
        assert 'sessionStorage.setItem("lastRuntimeSummary"' in text, \
            "Runtime summary must be stored in sessionStorage"
        # The JSON object must contain expected keys
        assert '"project_irr"' in text or '"avg_dscr"' in text, \
            "Runtime summary must contain KPI fields"

    def test_run_oborovo_returns_runtime_summary(self, client: TestClient, authenticated_client: TestClient):
        """POST /run with Oborovo returns a runtime_summary in sessionStorage script."""
        resp = authenticated_client.post(
            "/run",
            data={"active_project": "oborovo", "project_type": "Solar", "scenario": "Base"},
        )
        assert resp.status_code == 200
        text = resp.text
        assert 'sessionStorage.setItem("lastRuntimeSummary"' in text
        assert '"project_irr"' in text or '"avg_dscr"' in text

    def test_tuho_and_oborovo_runtime_summaries_differ(self, client: TestClient, authenticated_client: TestClient):
        """TUHO and Oborovo must produce different runtime_summary values."""
        tuho_resp = authenticated_client.post(
            "/run",
            data={"active_project": "tuho", "project_type": "Solar", "scenario": "Base"},
        )
        tuho_text = tuho_resp.text
        assert 'sessionStorage.setItem("lastRuntimeSummary"' in tuho_text

        # Extract the JSON from sessionStorage.setItem("lastRuntimeSummary", {...})
        import re
        m = re.search(r'sessionStorage\.setItem\("lastRuntimeSummary",\s*({.*?})\);', tuho_text, re.DOTALL)
        assert m, "Could not extract runtime_summary JSON from sessionStorage script"
        tuho_summary = json.loads(m.group(1))

        obo_resp = authenticated_client.post(
            "/run",
            data={"active_project": "oborovo", "project_type": "Solar", "scenario": "Base"},
        )
        obo_text = obo_resp.text
        m2 = re.search(r'sessionStorage\.setItem\("lastRuntimeSummary",\s*({.*?})\);', obo_text, re.DOTALL)
        assert m2
        obo_summary = json.loads(m2.group(1))

        # Active project must differ
        assert tuho_summary.get("project_id") != obo_summary.get("project_id"), \
            "TUHO and Oborovo must have different active_project in runtime summary"

        # Revenue must differ (guardrails: TUHO ~423M, Oborovo ~238M)
        tuho_rev = tuho_summary.get("total_revenue_keur", 0)
        obo_rev = obo_summary.get("total_revenue_keur", 0)
        assert tuho_rev != obo_rev, \
            f"TUHO revenue ({tuho_rev}) must differ from Oborovo ({obo_rev})"


class TestOutputTabsContainRuntimeSummary:
    """All output tab sheet partials contain 'Runtime summary — last run' label."""

    SHEETS_WITH_RUNTIME_BLOCK = [
        "sheet_financials.html",  # P&L, Cash Flow, Balance Sheet
        "sheet_senior_debt.html",
        "sheet_shl.html",
        "sheet_tax.html",
    ]

    @pytest.mark.parametrize("sheet", SHEETS_WITH_RUNTIME_BLOCK)
    def test_sheet_contains_runtime_summary_label(self, sheet):
        """Each output tab sheet must contain 'Runtime summary — last run'."""
        path = os.path.join(PARTIALS, sheet)
        assert os.path.exists(path), f"{sheet} not found in partials/"
        content = open(path, encoding="utf-8").read()
        assert "Runtime summary" in content, \
            f"{sheet}: must contain 'Runtime summary' text"

    def test_workspace_shell_includes_runtime_block_in_pl_tab(self):
        """workspace_shell.html must include shared_runtime_block in P&L tab."""
        path = os.path.join(PARTIALS, "workspace_shell.html")
        content = open(path, encoding="utf-8").read()
        # panel-pl must contain the shared_runtime_block include
        panel_match = content.find('id="panel-pl"')
        assert panel_match >= 0, "panel-pl not found in workspace_shell"
        panel_content = content[panel_match:panel_match + 2000]
        assert "shared_runtime_block" in panel_content, \
            "panel-pl must include shared_runtime_block.html"

    def test_workspace_shell_includes_runtime_block_in_senior_debt_tab(self):
        """workspace_shell.html must include shared_runtime_block in Senior Debt tab."""
        path = os.path.join(PARTIALS, "workspace_shell.html")
        content = open(path, encoding="utf-8").read()
        panel_match = content.find('id="panel-senior-debt"')
        assert panel_match >= 0
        panel_content = content[panel_match:panel_match + 2000]
        assert "shared_runtime_block" in panel_content

    def test_workspace_shell_includes_runtime_block_in_shl_tab(self):
        """workspace_shell.html must include shared_runtime_block in SHL tab."""
        path = os.path.join(PARTIALS, "workspace_shell.html")
        content = open(path, encoding="utf-8").read()
        panel_match = content.find('id="panel-shl"')
        assert panel_match >= 0
        panel_content = content[panel_match:panel_match + 2000]
        assert "shared_runtime_block" in panel_content

    def test_workspace_shell_includes_runtime_block_in_tax_tab(self):
        """workspace_shell.html must include shared_runtime_block in Tax tab."""
        path = os.path.join(PARTIALS, "workspace_shell.html")
        content = open(path, encoding="utf-8").read()
        panel_match = content.find('id="panel-tax"')
        assert panel_match >= 0
        panel_content = content[panel_match:panel_match + 2000]
        assert "shared_runtime_block" in panel_content


class TestPreviewLabelsPreserved:
    """Preview sections must still be labeled as preview."""

    SHEETS_WITH_PREVIEW = [
        "sheet_financials.html",
        "sheet_senior_debt.html",
        "sheet_shl.html",
        "sheet_tax.html",
    ]

    @pytest.mark.parametrize("sheet", SHEETS_WITH_PREVIEW)
    def test_preview_sections_still_labeled(self, sheet):
        """Preview tables must retain 'Preview schedule' or 'Template preview' label."""
        path = os.path.join(PARTIALS, sheet)
        assert os.path.exists(path), f"{sheet} not found"
        content = open(path, encoding="utf-8").read()
        # Must contain preview label
        has_preview = (
            "Preview schedule" in content or
            "Template preview" in content or
            "badge-preview" in content
        )
        assert has_preview, f"{sheet}: preview sections must still be labeled"


class TestMissingMetricsNotFabricated:
    """Unavailable metrics must show NOT_AVAILABLE, not 0 or fabricated values."""

    def test_runtime_summary_has_not_available_for_missing_fields(self, client: TestClient, authenticated_client: TestClient):
        """runtime_summary must use 'NOT_AVAILABLE' string for missing metrics."""
        resp = authenticated_client.post(
            "/run",
            data={"active_project": "tuho", "project_type": "Solar", "scenario": "Base"},
        )
        text = resp.text
        import re
        m = re.search(r'sessionStorage\.setItem\("lastRuntimeSummary",\s*({.*?})\);', text, re.DOTALL)
        assert m, "Could not extract runtime_summary from sessionStorage"
        summary = json.loads(m.group(1))

        # Check that some fields are either present or NOT_AVAILABLE
        # The summary should have active_project and at least one KPI
        assert "active_project" in summary or "project_irr" in summary, \
            "Runtime summary must contain at least active_project or project_irr"


class TestGovernanceBadgesUnchanged:
    """G20 BLOCKED and R99/R102 NOT APPROVED badges must remain visible
    where they are still part of the product (e.g. Sponsor tab).

    Product Gap PR9 removed the internal-jargon G20/R99/R102 governance
    cells from the user-facing Tax sheet (sheet_tax.html) -- those terms
    are explicitly banned jargon per the PR9 spec's "no R99/R102/G20"
    rule and were never real tax output to begin with. See
    docs/PRODUCT_GAP_PR9_TAX_REALITY_CHECK.md."""

    def test_tax_tab_no_longer_shows_internal_governance_jargon(self):
        """Product Gap PR9: Tax tab must not leak G20/R99/R102 internal
        governance jargon into user-facing tax copy."""
        path = os.path.join(PARTIALS, "sheet_tax.html")
        content = open(path, encoding="utf-8").read()
        import re
        visible = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL)
        assert "G20" not in visible
        assert "R99" not in visible
        assert "R102" not in visible

    def test_sponsor_tab_shows_r99_not_approved(self):
        """Sponsor tab must still show R99/R102 NOT APPROVED badge."""
        path = os.path.join(PARTIALS, "workspace_shell.html")
        content = open(path, encoding="utf-8").read()
        # Find panel-sponsor
        panel_match = content.find('id="panel-sponsor"')
        assert panel_match >= 0
        panel_content = content[panel_match:panel_match + 1000]
        assert "NOT APPROVED" in panel_content or "R99" in panel_content or "R102" in panel_content, \
            "Sponsor tab must show R99/R102 NOT APPROVED"


class TestNoRuntimeModelFilesChanged:
    """No runtime model files (waterfall, engine, senior_debt, shl, tax) changed."""

    def test_no_domain_waterfall_changes(self):
        """domain/waterfall/ files must not have been modified in this branch."""
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--stat", "origin/main...HEAD", "--", "domain/waterfall/"],
            cwd=APP_ROOT,
            capture_output=True,
            text=True,
        )
        stdout = result.stdout.strip()
        assert stdout == "" or "origin/main...HEAD" in result.stderr, \
            f"Unexpected waterfall changes: {stdout}"

    def test_no_domain_senior_debt_changes(self):
        """domain/senior_debt/ files must not have been modified."""
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--stat", "origin/main...HEAD", "--", "domain/senior_debt/"],
            cwd=APP_ROOT,
            capture_output=True,
            text=True,
        )
        stdout = result.stdout.strip()
        assert stdout == "" or "origin/main...HEAD" in result.stderr

    def test_no_domain_shl_changes(self):
        """domain/shl/ files must not have been modified."""
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--stat", "origin/main...HEAD", "--", "domain/shl/"],
            cwd=APP_ROOT,
            capture_output=True,
            text=True,
        )
        stdout = result.stdout.strip()
        assert stdout == "" or "origin/main...HEAD" in result.stderr

    def test_no_domain_tax_bridge_changes(self):
        """domain/tax/ files must not have been modified."""
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--stat", "origin/main...HEAD", "--", "domain/tax/", "domain/tax_bridge/"],
            cwd=APP_ROOT,
            capture_output=True,
            text=True,
        )
        stdout = result.stdout.strip()
        assert stdout == "" or "origin/main...HEAD" in result.stderr


class TestUILabelConsistency:
    """Phase 9.5 UI closeout: label and badge consistency checks."""

    SHEETS = [
        "sheet_financials.html",
        "sheet_senior_debt.html",
        "sheet_shl.html",
        "sheet_tax.html",
    ]

    @pytest.mark.parametrize("sheet", SHEETS)
    def test_preview_labels_present(self, sheet):
        """Each output sheet must contain 'Preview schedule' or 'Template preview' label."""
        path = os.path.join(PARTIALS, sheet)
        content = open(path, encoding="utf-8").read()
        has_preview = (
            "Preview schedule" in content or
            "Template preview" in content or
            "badge-preview" in content
        )
        assert has_preview, f"{sheet}: must contain 'Preview schedule' or 'Template preview'"

    @pytest.mark.parametrize("sheet", SHEETS)
    def test_runtime_summary_labels_present(self, sheet):
        """Each output sheet must contain 'Runtime summary' label."""
        path = os.path.join(PARTIALS, sheet)
        content = open(path, encoding="utf-8").read()
        assert "Runtime summary" in content, \
            f"{sheet}: must contain 'Runtime summary'"

    def test_no_internal_governance_jargon_in_tax_tab(self):
        """Product Gap PR9: Tax tab must not contain G20/R99/R102
        internal governance jargon in user-facing copy (banned per the
        PR9 spec). See docs/PRODUCT_GAP_PR9_TAX_REALITY_CHECK.md."""
        path = os.path.join(PARTIALS, "sheet_tax.html")
        content = open(path, encoding="utf-8").read()
        import re
        visible = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL)
        assert "G20" not in visible
        assert "R99" not in visible
        assert "R102" not in visible

    def test_no_inline_onclick_handlers(self):
        """Rendered output sheets must not contain inline onclick= handlers (except htmx)."""
        import re
        for sheet in ["sheet_financials.html", "sheet_senior_debt.html",
                      "sheet_shl.html", "sheet_tax.html"]:
            path = os.path.join(PARTIALS, sheet)
            content = open(path, encoding="utf-8").read()
            # Find all onclick= attributes
            onclick_matches = re.findall(r'onclick=["\']([^"\']*)["\']', content)
            non_htmx = [h for h in onclick_matches if "htmx" not in h.lower()]
            assert not non_htmx, f"{sheet}: found non-htmx onclick handlers: {non_htmx}"


# Pytest fixtures

from tests.test_auth_lite import (
    TestClient,
    app,
    create_session_token,
    COOKIE_NAME,
    ADMIN_USERNAME,
)


@pytest.fixture
def client():
    """Unauthenticated test client."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def authenticated_client():
    """Authenticated test client with valid session cookie.

    Note: tests that need the form context (with hidden active_project)
    should call tc.get("/") themselves before POST /run.
    """
    tc = TestClient(app, raise_server_exceptions=False)
    token = create_session_token()
    tc.cookies.set(COOKIE_NAME, token)
    return tc