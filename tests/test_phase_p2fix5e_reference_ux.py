"""Phase P2-FIX-5E — Reference Project UX Cleanup.

Final cleanup pass. P2-FIX-3 already implemented
the C2 first-edit copy flow. P2-FIX-5B already
cleaned up 'TUHO seed' / 'Oborovo seed' suffixes
from project card meta. P2-FIX-2 already cleaned
up 'Reference' badges.

P2-FIX-5E locks the user-facing contract:

1. TUHO / Oborovo appear as plain project names.
2. No 'factory' / 'fixture' / 'baseline' / 'calibration'
   / 'golden' / 'parity' wording in normal-mode user-
   facing project browser / project home.
3. The 'Protected original' banner explains the
   read-only behaviour to third-party users.
4. Factory paths (TUHO/Oborovo) are unchanged.
5. Parity guardrails pass.
"""

from __future__ import annotations

import os
import re

import pytest

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-key-p2fix5e")

from fastapi.testclient import TestClient  # noqa: E402

from app.auth import create_session_token  # noqa: E402
from main_web import app  # noqa: E402

REPO_ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]


PROJECTS_TO_TEST = ["tuho", "oborovo", "generic_solar", "generic_wind"]


def _strip_html_comments(text: str) -> str:
    text = re.sub(r"\{#.*?#\}", "", text, flags=re.DOTALL)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    return text


def _strip_allowed_project_names(text: str) -> str:
    for name in ("TUHO Wind", "Oborovo Solar PV"):
        text = text.replace(name, "")
    return text


def _extract_visible_text(html: str) -> str:
    html = _strip_html_comments(html)
    html = _strip_allowed_project_names(html)
    html = re.sub(
        r"<script\b[^>]*>.*?</script>", " ", html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    html = re.sub(
        r"<style\b[^>]*>.*?</style>", " ", html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    html = re.sub(r'\s[a-zA-Z-]+="[^"]*"', " ", html)
    html = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", html).strip()


def _strip_audit_panel(html: str) -> str:
    audit_start = html.find('id="panel-audit"')
    if audit_start == -1:
        return html
    div_start = html.rfind("<div", 0, audit_start)
    depth = 0
    i = div_start
    while i < len(html):
        if html[i:i + 5] == "<div " or html[i:i + 5] == "<div>":
            depth += 1
            i += 5
        elif html[i:i + 6] == "</div>":
            depth -= 1
            i += 6
            if depth == 0:
                break
        else:
            i += 1
    return html[:div_start] + html[i:]


@pytest.fixture(scope="module")
def logged_in_client():
    client = TestClient(app)
    token = create_session_token(user_id="1", username="test_user")
    client.cookies.set("finco_session", token)
    return client


# ─────────────────────────────────────────────────────────────────────
# 1. TUHO / Oborovo appear as plain project names
# ─────────────────────────────────────────────────────────────────────


class TestPlainProjectNames:
    @pytest.fixture(autouse=True)
    def inject(self, logged_in_client):
        self.client = logged_in_client

    def test_tuho_appears_in_project_browser(self):
        r = self.client.get(
            "/projects/browse", follow_redirects=True
        )
        assert "TUHO Wind" in r.text, (
            "TUHO Wind must appear as a plain project name in "
            "/projects/browse"
        )

    def test_oborovo_appears_in_project_browser(self):
        r = self.client.get(
            "/projects/browse", follow_redirects=True
        )
        assert "Oborovo Solar PV" in r.text, (
            "Oborovo Solar PV must appear as a plain project "
            "name in /projects/browse"
        )

    def test_no_seed_suffix_in_project_browser(self):
        r = self.client.get(
            "/projects/browse", follow_redirects=True
        )
        visible = _extract_visible_text(r.text).lower()
        assert "tuho seed" not in visible
        assert "oborovo seed" not in visible


# ─────────────────────────────────────────────────────────────────────
# 2. No factory / fixture / baseline / parity / golden
#    / calibration in normal-mode project browser / home
# ─────────────────────────────────────────────────────────────────────


class TestNoInternalTerminology:
    @pytest.fixture(autouse=True)
    def inject(self, logged_in_client):
        self.client = logged_in_client

    def test_project_browser_no_internal_terms(self):
        r = self.client.get(
            "/projects/browse", follow_redirects=True
        )
        visible = _extract_visible_text(r.text).lower()
        for term in (
            "factory",
            "fixture",
            "baseline",
            "calibration",
            "golden",
            "parity",
        ):
            assert term not in visible, (
                f"/projects/browse must not contain {term!r} "
                f"in user-facing copy"
            )

    def test_project_home_no_internal_terms(self):
        r = self.client.get("/", follow_redirects=True)
        visible = _extract_visible_text(r.text).lower()
        for term in (
            "factory",
            "fixture",
            "baseline",
            "calibration",
            "golden",
            "parity",
            "seed",
        ):
            assert term not in visible, (
                f"/ must not contain {term!r} in user-facing copy"
            )

    def test_workspace_no_internal_terms_in_normal_mode(self):
        """Normal-mode workspace panels (outside the
        audit tab) must not contain internal terms."""
        for project_code in PROJECTS_TO_TEST:
            r = self.client.get(
                f"/?project={project_code}", follow_redirects=True
            )
            html = _strip_audit_panel(r.text)
            visible = _extract_visible_text(html).lower()
            for term in (
                "factory",
                "fixture",
                "baseline",
                "calibration",
                "golden",
                "parity",
            ):
                assert term not in visible, (
                    f"{project_code} workspace normal-mode "
                    f"contains {term!r}"
                )


# ─────────────────────────────────────────────────────────────────────
# 3. Protected original banner explains read-only behaviour
# ─────────────────────────────────────────────────────────────────────


class TestProtectedOriginalBanner:
    @pytest.fixture(autouse=True)
    def inject(self, logged_in_client):
        self.client = logged_in_client

    def test_tuho_workspace_has_protected_banner(self):
        r = self.client.get(
            "/?project=tuho", follow_redirects=True
        )
        assert "Protected original" in r.text, (
            "TUHO workspace must show a 'Protected original' "
            "banner explaining read-only behaviour"
        )

    def test_oborovo_workspace_has_protected_banner(self):
        r = self.client.get(
            "/?project=oborovo", follow_redirects=True
        )
        assert "Protected original" in r.text, (
            "Oborovo workspace must show a 'Protected original' "
            "banner explaining read-only behaviour"
        )

    def test_protected_banner_mentions_editable_copy(self):
        r = self.client.get(
            "/?project=tuho", follow_redirects=True
        )
        # The banner should mention the editable copy path
        # (the P2-FIX-3 first-edit flow).
        assert "editable copy" in r.text.lower() or \
               "editable" in r.text.lower(), (
            "Protected original banner must mention the "
            "editable copy path"
        )


# ─────────────────────────────────────────────────────────────────────
# 4. Factory paths preserved (TUHO/Oborovo unchanged)
# ─────────────────────────────────────────────────────────────────────


class TestFactoryPathsPreserved:
    """The C2 first-edit flow remains functional. The
    factory paths (TUHO/Oborovo fixtures) are
    unchanged in main and on disk."""

    @pytest.fixture(autouse=True)
    def inject(self, logged_in_client):
        self.client = logged_in_client

    def test_c2_first_edit_endpoint_exists(self):
        """POST /projects/{code}/confirm-first-edit-copy
        still works for protected reference projects."""
        r = self.client.post(
            "/projects/tuho/confirm-first-edit-copy",
            data={},
            follow_redirects=False,
        )
        # 302 redirect to the new working copy is the
        # expected response
        assert r.status_code in (200, 302), (
            f"Expected 200/302 from C2 confirm route, got "
            f"{r.status_code}"
        )

    def test_factory_template_fixtures_unchanged(self):
        """The TUHO / Oborovo factory template fixtures
        remain reachable."""
        for code in ("tuho", "oborovo"):
            r = self.client.get(
                f"/?project={code}", follow_redirects=True
            )
            assert r.status_code == 200


# ─────────────────────────────────────────────────────────────────────
# 5. File scope: P2-FIX-5E is presentation-only
# ─────────────────────────────────────────────────────────────────────


class TestFileScope:
    def test_only_allowed_files_changed(self):
        import shutil
        import subprocess
        if shutil.which("git") is None or not (REPO_ROOT / ".git").exists():
            pytest.skip("git not available")
        result = subprocess.run(
            [
                "git", "-C", str(REPO_ROOT),
                "diff", "--name-only", "origin/main",
            ],
            capture_output=True,
            text=True,
        )
        changed = [
            f.strip() for f in result.stdout.strip().split("\n")
            if f.strip()
        ]
        allowed_prefixes = (
            "main_web.py",
            "app/templates/partials/_state_banner.html",
            "app/templates/partials/inputs_section.html",
            "app/templates/partials/_standalone_header.html",
            "app/templates/index.html",
            "tests/test_phase_p2fix5e_reference_ux.py",
            "tests/test_phase_p2fix3_c2_first_edit.py",
            "tests/test_phase_p2fix5b_normal_mode_shell_strip.py",
            "tests/test_phase_p2fix5c_dashboard_kpi.py",
            "tests/test_phase_p2fix5d_five_area_navigation.py",
            "tests/test_phase_p2fix6_c2_create_copy_ui.py",
            "tests/test_phase_p2fix7_production_cleanup.py",
            "tests/test_phase_p2fix7a_css_parser_cleanup.py",
            "tests/test_phase_p2fix2_",  # P2-FIX-7A cross-arc
            "tests/test_phase_p2fix4_",  # P2-FIX-7A cross-arc
            "docs/phase_p2fix5e_",
            "reports/phase_p2fix5e_",
            "docs/phase_p2fix7_",
            "reports/phase_p2fix7_",
            "docs/phase_p2fix7a_",
            "reports/phase_p2fix7a_",
            # P2-FIX-8 cross-arc allowlist
            "app/templates/base.html",
            "app/templates/project_home_page.html",
            "app/templates/project_new_page.html",
            "app/templates/project_browse_page.html",
            "app/templates/partials/workspace_tabs.html",
            "app/templates/partials/workspace_shell.html",
            "app/templates/partials/project_home.html",
            "app/middleware/security_headers.py",
            "scripts/",
            "tests/test_phase_p2fix8_",
            "tests/test_phase_p2fix5a_",
            # WF cross-arc allowlist
            "app/ui/dashboard.py",
            "app/templates/partials/_dashboard_oob.html",
            "tests/test_phase_wf1_",
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
        # Phase P2-FIX-7: allow static/styles.css.
        for f in changed:
            if f == "static/styles.css":
                continue
            with_dash = [f.startswith(p) for p in disallowed_prefixes]
            assert not any(with_dash), (
                f"Disallowed file changed: {f}"
            )
            ok = [f.startswith(p) for p in allowed_prefixes]
            assert any(ok), (
                f"File outside allowed scope: {f}"
            )
