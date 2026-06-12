"""Phase WF-5 — Grouped Results Navigation.

Acceptance criteria:
1. Results sub-nav has 6 labelled groups:
   Production, Costs, Financing, Tax, P&L/Cash, Returns.
2. All 13 original sheet buttons remain (hidden != deleted).
3. Each button still calls switchTab with the correct panel target.
4. Group IDs are present in the DOM: results-group-*.
5. CSS rules exist for results-subnav-group and results-subnav-group-label.
6. Engine MD5 unchanged.
7. File scope: only allowed files changed.
"""
from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

import pytest

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-key-wf5")

from fastapi.testclient import TestClient  # noqa: E402

from app.auth import create_session_token  # noqa: E402
from main_web import app  # noqa: E402

REPO_ROOT = Path(__file__).parent.parent
ENGINE_MD5 = "6bf49f33efc989736c17cea0cb9b7723"

# All 13 original sheet buttons and their switchTab targets
EXPECTED_TABS = {
    "results-subnav-tab-revenue":       "revenue",
    "results-subnav-tab-production":    "production",
    "results-subnav-tab-opex":          "opex",
    "results-subnav-tab-capex":         "capex",
    "results-subnav-tab-construction":  "construction",
    "results-subnav-tab-senior-debt":   "senior-debt",
    "results-subnav-tab-shl":           "shl",
    "results-subnav-tab-tax":           "tax",
    "results-subnav-tab-pl":            "pl",
    "results-subnav-tab-cashflow":      "cashflow",
    "results-subnav-tab-balance":       "balance",
    "results-subnav-tab-distributions": "distributions",
    "results-subnav-tab-sponsor":       "sponsor",
}

EXPECTED_GROUPS = [
    "results-group-production",
    "results-group-costs",
    "results-group-financing",
    "results-group-tax",
    "results-group-pl-cash",
    "results-group-returns",
]

GROUP_LABELS = ["Production", "Costs", "Financing", "Tax", "Returns"]


@pytest.fixture(scope="module")
def workspace_html():
    c = TestClient(app, follow_redirects=True)
    token = create_session_token(user_id="wf5_user", username="wf5_user")
    c.cookies.set("finco_session", token)
    r = c.get("/?project=tuho")
    assert r.status_code == 200
    return r.text


# ---------------------------------------------------------------------------
# 1. Engine parity
# ---------------------------------------------------------------------------

class TestEngineParity:
    def test_engine_md5_unchanged(self):
        md5 = hashlib.md5(
            (REPO_ROOT / "app" / "waterfall_core.py").read_bytes()
        ).hexdigest()
        assert md5 == ENGINE_MD5


# ---------------------------------------------------------------------------
# 2. Six group containers in DOM
# ---------------------------------------------------------------------------

class TestSixGroupsInDOM:
    def test_results_subnav_present(self, workspace_html):
        assert 'id="results-subnav"' in workspace_html

    def test_all_six_group_ids_present(self, workspace_html):
        for gid in EXPECTED_GROUPS:
            assert f'id="{gid}"' in workspace_html, (
                f"Missing results group: {gid}"
            )

    def test_group_label_elements_present(self, workspace_html):
        assert "results-subnav-group-label" in workspace_html

    def test_production_group_label_text(self, workspace_html):
        assert "Production" in workspace_html

    def test_costs_group_label_text(self, workspace_html):
        assert "Costs" in workspace_html

    def test_financing_group_label_text(self, workspace_html):
        assert "Financing" in workspace_html

    def test_returns_group_label_text(self, workspace_html):
        assert "Returns" in workspace_html


# ---------------------------------------------------------------------------
# 3. All 13 original buttons preserved
# ---------------------------------------------------------------------------

class TestAllButtonsPreserved:
    @pytest.mark.parametrize("btn_id,target", list(EXPECTED_TABS.items()))
    def test_button_present(self, workspace_html, btn_id, target):
        assert f'id="{btn_id}"' in workspace_html, (
            f"Results subnav button missing: {btn_id}"
        )

    @pytest.mark.parametrize("btn_id,target", list(EXPECTED_TABS.items()))
    def test_button_calls_switchtab(self, workspace_html, btn_id, target):
        assert f"switchTab('{target}')" in workspace_html, (
            f"switchTab('{target}') not found for button {btn_id}"
        )

    def test_total_subnav_button_count(self, workspace_html):
        buttons = re.findall(r'class="results-subnav-tab"', workspace_html)
        assert len(buttons) == 13, (
            f"Expected 13 results subnav buttons, found {len(buttons)}"
        )


# ---------------------------------------------------------------------------
# 4. Group membership: each button is inside the correct group
# ---------------------------------------------------------------------------

class TestGroupMembership:
    def _group_content(self, html, group_id):
        start = html.find(f'id="{group_id}"')
        assert start != -1, f"{group_id} not found"
        # Extract to closing </div> of the group
        depth = 0
        i = html.rfind("<div", 0, start + len(group_id))
        while i < len(html):
            if html[i:i+5] in ("<div ", "<div>"):
                depth += 1
                i += 5
            elif html[i:i+6] == "</div>":
                depth -= 1
                i += 6
                if depth == 0:
                    break
            else:
                i += 1
        return html[html.rfind("<div", 0, start):i]

    def test_revenue_in_production_group(self, workspace_html):
        content = self._group_content(workspace_html, "results-group-production")
        assert "results-subnav-tab-revenue" in content

    def test_capex_in_costs_group(self, workspace_html):
        content = self._group_content(workspace_html, "results-group-costs")
        assert "results-subnav-tab-capex" in content

    def test_senior_debt_in_financing_group(self, workspace_html):
        content = self._group_content(workspace_html, "results-group-financing")
        assert "results-subnav-tab-senior-debt" in content

    def test_pl_in_pl_cash_group(self, workspace_html):
        content = self._group_content(workspace_html, "results-group-pl-cash")
        assert "results-subnav-tab-pl" in content

    def test_distributions_in_returns_group(self, workspace_html):
        content = self._group_content(workspace_html, "results-group-returns")
        assert "results-subnav-tab-distributions" in content


# ---------------------------------------------------------------------------
# 5. CSS coverage
# ---------------------------------------------------------------------------

class TestCSS:
    def test_results_subnav_group_css(self):
        css = (REPO_ROOT / "static" / "styles.css").read_text()
        assert ".results-subnav-group" in css
        assert ".results-subnav-group-label" in css
        assert ".results-subnav-tab" in css
        assert ".results-subnav" in css

    def test_wf5_marker_in_css(self):
        css = (REPO_ROOT / "static" / "styles.css").read_text()
        assert "WF-5" in css


# ---------------------------------------------------------------------------
# 6. File scope
# ---------------------------------------------------------------------------

class TestFileScope:
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
        allowed_prefixes = (
            "static/styles.css",
            "app/templates/partials/_results_subnav.html",
            "tests/test_phase_wf5_",
            "tests/test_phase_wf4_",
            "tests/test_phase_wf3_",
            "tests/test_phase_wf2_",
            "tests/test_phase_wf1_",
            "tests/test_phase_p2fix",
            "app/templates/",
            "docs/phase_wf",
            "reports/phase_wf",
            "scripts/",
        )
        disallowed_prefixes = (
            "app/persistence/",
            "app/services/",
            "app/waterfall_core.py",
            "app/project_factories.py",
            "app/excel_export.py",
            "main_api.py",
            "static/app.js",
        )
        for f in changed:
            assert not any(f.startswith(p) for p in disallowed_prefixes), (
                f"Disallowed file changed: {f}"
            )
            assert any(f.startswith(p) for p in allowed_prefixes), (
                f"File outside allowed scope: {f}"
            )
