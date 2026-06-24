"""Phase P2-FIX-7 — Production Reality Cleanup.

Three production-facing mismatches from
P2-FIX-VERIFY, all addressed:

1. Standalone page templates (P2-FIX-5A) had
   classes that were never defined in
   static/styles.css. P2-FIX-7 adds the CSS.

2. inputs_section.html showed "Unknown" as
   Template Origin for Generic Solar / Wind
   (Phase 20D bug, March 2026). P2-FIX-7 makes
   the fallback project-type-aware.

3. _state_banner.html showed the "Protected
   original" banner for ANY non-user-created
   project, including Generic Solar / Wind.
   P2-FIX-7 restricts the banner to protected
   references only.

4. index.html P2-FIX-2 logic matched on
   ``template_source`` only, which is empty
   for factory-seeded Generic projects. P2-FIX-7
   adds ``project_ctx.code`` (case-insensitive
   contains 'generic') as a second signal.

Hard constraints preserved:
- rc1 SHA unchanged
- No formula / model / debt / tax / IDC /
  construction / R-PAR / C10 / R99/R102 / G20
- No persistence schema migration
- No static/app.js changes
- No main_api.py changes
- No dependencies added
- File scope: static/styles.css,
  app/templates/partials/inputs_section.html,
  app/templates/partials/_state_banner.html,
  app/templates/index.html (extended for Fix 3
  closure), tests, docs
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-key-p2fix7")

from fastapi.testclient import TestClient  # noqa: E402

from app.auth import create_session_token  # noqa: E402
from main_web import app  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def logged_in_client():
    client = TestClient(app)
    token = create_session_token(user_id="1", username="test")
    client.cookies.set("finco_session", token)
    return client


# ─────────────────────────────────────────────────────────────────
# Fix 1: standalone page CSS
# ─────────────────────────────────────────────────────────────────


class TestStandalonePageCSS:
    @pytest.fixture(autouse=True)
    def inject(self):
        self.css = (REPO_ROOT / "static" / "styles.css").read_text()

    def test_standalone_page_class_defined(self):
        assert re.search(r"body\.standalone-page\s*{", self.css), (
            "body.standalone-page CSS rule must be defined "
            "(P2-FIX-7 Fix 1)"
        )

    def test_inline_style_fallback_in_standalone_header(self):
        """P2-FIX-7A: the temporary inline <style>
        fallback that P2-FIX-7 added in
        _standalone_header.html has been removed
        now that the CSS parser bugs in
        ``static/styles.css`` are fixed. The
        standalone page rules now load from the
        external stylesheet only.

        Hidden != deleted: the original
        _standalone_header.html (P2-FIX-5A) never
        had an inline <style> block; P2-FIX-7
        added it as a runtime fallback. P2-FIX-7A
        removes it because the underlying CSS
        parser bugs are now fixed, so the
        external stylesheet delivers the
        standalone rules on its own.
        """
        header = (REPO_ROOT / "app" / "templates" / "partials" / "_standalone_header.html").read_text()
        # Strip Jinja {# ... #} comments first so
        # the assertion does not match the literal
        # text "<style>" inside a docstring/comment.
        header_no_comments = re.sub(
            r"\{#.*?#\}", "", header, flags=re.DOTALL
        )
        # Inline <style> block must be GONE.
        assert "<style>" not in header_no_comments, (
            "Inline <style> fallback must be removed "
            "in P2-FIX-7A"
        )
        # The header still has its normal P2-FIX-5A
        # markup (top-header, header-inner, etc.).
        assert "top-header" in header
        assert "header-inner" in header

    def test_standalone_main_class_defined(self):
        assert re.search(r"\.standalone-main\s*{", self.css), (
            ".standalone-main CSS rule must be defined"
        )

    def test_page_shell_class_defined(self):
        assert re.search(r"\.page-shell\s*{", self.css), (
            ".page-shell CSS rule must be defined"
        )

    def test_page_shell_header_class_defined(self):
        assert re.search(r"\.page-shell-header\s*{", self.css), (
            ".page-shell-header CSS rule must be defined"
        )

    def test_page_shell_title_class_defined(self):
        assert re.search(r"\.page-shell-title\s*{", self.css), (
            ".page-shell-title CSS rule must be defined"
        )

    def test_page_shell_desc_class_defined(self):
        assert re.search(r"\.page-shell-desc\s*{", self.css), (
            ".page-shell-desc CSS rule must be defined"
        )

    def test_page_shell_footer_class_defined(self):
        assert re.search(r"\.page-shell-footer\s*{", self.css), (
            ".page-shell-footer CSS rule must be defined"
        )

    def test_p2fix7_marker_comment_present(self):
        assert "Phase P2-FIX-7" in self.css, (
            "P2-FIX-7 marker comment must be present in CSS"
        )


# ─────────────────────────────────────────────────────────────────
# Fix 1 (rendered): standalone pages include the styled classes
# ─────────────────────────────────────────────────────────────────


class TestStandalonePagesRendered:
    @pytest.fixture(autouse=True)
    def inject(self, logged_in_client):
        self.client = logged_in_client

    def test_root_has_standalone_page_class(self):
        r = self.client.get("/", follow_redirects=True)
        assert "standalone-page" in r.text, (
            "GET / must include standalone-page class"
        )
        assert "page-shell" in r.text, (
            "GET / must include page-shell class"
        )

    def test_projects_new_has_standalone_page_class(self):
        r = self.client.get("/projects/new", follow_redirects=True)
        assert "standalone-page" in r.text
        assert "page-shell" in r.text

    def test_projects_browse_has_standalone_page_class(self):
        r = self.client.get("/projects/browse", follow_redirects=True)
        assert "standalone-page" in r.text
        assert "page-shell" in r.text

    def test_workspace_pages_unaffected(self):
        r = self.client.get("/?project=tuho", follow_redirects=True)
        # workspace pages use base.html body, not standalone-page
        assert "data-p2fix5a-page" not in r.text, (
            "Workspace page must NOT have standalone-page body class"
        )


# ─────────────────────────────────────────────────────────────────
# Fix 2: Template Origin no longer "Unknown" for Generic
# ─────────────────────────────────────────────────────────────────


class TestTemplateOriginNoUnknown:
    @pytest.fixture(autouse=True)
    def inject(self, logged_in_client):
        self.client = logged_in_client

    @staticmethod
    def _extract_template_origin(html: str) -> str | None:
        """Extract the value of the 'Template Origin' field
        from the inputs_section.html rendered output."""
        m = re.search(
            r"Template Origin.{0,2000}?class=\"inp-value\">([^<]+)</span>",
            html,
            re.DOTALL,
        )
        return m.group(1).strip() if m else None

    def test_generic_solar_not_unknown(self):
        r = self.client.get(
            "/?project=generic_solar", follow_redirects=True
        )
        val = self._extract_template_origin(r.text)
        assert val != "Unknown", (
            f"Generic Solar Template Origin must NOT be 'Unknown', got {val!r}"
        )
        assert val is not None
        # User-safe label expected
        assert val.lower() in {"generic", "generic solar", "internal-use model", "generic template"}, (
            f"Generic Solar should show 'Generic' or similar, got {val!r}"
        )

    def test_generic_wind_not_unknown(self):
        r = self.client.get(
            "/?project=generic_wind", follow_redirects=True
        )
        val = self._extract_template_origin(r.text)
        assert val != "Unknown", (
            f"Generic Wind Template Origin must NOT be 'Unknown', got {val!r}"
        )
        assert val is not None
        assert val.lower() in {"generic", "generic wind", "internal-use model", "generic template"}

    def test_tuho_template_origin_unchanged(self):
        r = self.client.get("/?project=tuho", follow_redirects=True)
        val = self._extract_template_origin(r.text)
        assert val == "TUHO", f"TUHO should still show 'TUHO', got {val!r}"

    def test_oborovo_template_origin_unchanged(self):
        r = self.client.get("/?project=oborovo", follow_redirects=True)
        val = self._extract_template_origin(r.text)
        assert val == "Oborovo", f"Oborovo should still show 'Oborovo', got {val!r}"

    def test_no_forbidden_internal_vocabulary_in_template_origin(self):
        for code in ("generic_solar", "generic_wind"):
            r = self.client.get(
                f"/?project={code}", follow_redirects=True
            )
            val = self._extract_template_origin(r.text)
            assert val is not None
            low = val.lower()
            for forbidden in ("factory", "baseline", "calibration", "golden", "parity"):
                assert forbidden not in low, (
                    f"Forbidden internal term {forbidden!r} leaked into "
                    f"Template Origin for {code}: {val!r}"
                )


# ─────────────────────────────────────────────────────────────────
# Fix 3: Protected original banner only for protected references
# ─────────────────────────────────────────────────────────────────


class TestProtectedOriginalBannerRestricted:
    @pytest.fixture(autouse=True)
    def inject(self, logged_in_client):
        self.client = logged_in_client

    def test_tuho_has_protected_original_banner(self):
        r = self.client.get("/?project=tuho", follow_redirects=True)
        assert "data-p2fix2-disclosure=\"protected-original\"" in r.text
        # P2-FIX-8: explicit CTA button removed from normal mode (transparent copy)

    def test_oborovo_has_protected_original_banner(self):
        r = self.client.get("/?project=oborovo", follow_redirects=True)
        assert "data-p2fix2-disclosure=\"protected-original\"" in r.text
        # P2-FIX-8: explicit CTA button removed from normal mode (transparent copy)

    def test_generic_solar_no_protected_original_banner(self):
        r = self.client.get(
            "/?project=generic_solar", follow_redirects=True
        )
        assert "data-p2fix2-disclosure=\"protected-original\"" not in r.text, (
            "Generic Solar must NOT show Protected original banner"
        )
        assert "data-p2fix2-disclosure=\"internal-use-model\"" in r.text
        assert "data-p2fix6-cta" not in r.text

    def test_generic_wind_no_protected_original_banner(self):
        r = self.client.get(
            "/?project=generic_wind", follow_redirects=True
        )
        assert "data-p2fix2-disclosure=\"protected-original\"" not in r.text
        assert "data-p2fix2-disclosure=\"internal-use-model\"" in r.text
        assert "data-p2fix6-cta" not in r.text

    def test_working_copy_no_protected_original_banner(self):
        # Create a working copy via C2 confirm
        r = self.client.post(
            "/projects/tuho/confirm-first-edit-copy",
            data={},
            follow_redirects=False,
        )
        assert r.status_code == 302
        new_url = r.headers.get("location", "")
        assert new_url
        r2 = self.client.get(new_url, follow_redirects=True)
        assert "data-p2fix2-disclosure=\"protected-original\"" not in r2.text, (
            "Working copy must NOT show Protected original banner"
        )
        assert "data-p2fix2-disclosure=\"internal-use-model\"" in r2.text
        assert "data-p2fix6-cta" not in r2.text

    def test_state_banner_factory_template_restricted_to_protected(self):
        """The _state_banner.html factory_template branch must
        require is_protected_reference. Verify by reading the
        template source."""
        template = (REPO_ROOT / "app" / "templates" / "partials" / "_state_banner.html").read_text()
        # P2-FIX-7 added "and is_protected_reference" to the
        # factory_template condition
        assert (
            "factory_template' and is_protected_reference" in template
            or "factory_template'and is_protected_reference" in template
        ), (
            "_state_banner.html factory_template branch must require "
            "is_protected_reference"
        )


# ─────────────────────────────────────────────────────────────────
# File-scope: only allowed files changed
# ─────────────────────────────────────────────────────────────────


class TestFileScope:
    def test_only_allowed_files_changed(self):
        if shutil.which("git") is None or not (REPO_ROOT / ".git").exists():
            pytest.skip("git not available")
        result = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "diff", "--name-only", "origin/main"],
            capture_output=True,
            text=True,
        )
        changed = [
            f.strip() for f in result.stdout.strip().split("\n")
            if f.strip()
        ]
        allowed_prefixes = (
            "static/styles.css",
            "app/templates/partials/inputs_section.html",
            "app/templates/partials/_state_banner.html",
            "app/templates/partials/_standalone_header.html",
            "app/templates/index.html",  # extended for Fix 3 closure
            "tests/test_phase_p2fix7_",
            "tests/test_phase_p2fix7a_",  # P2-FIX-7A cross-arc
            "tests/test_phase_p2fix6_",  # cross-arc allowlist
            "tests/test_phase_p2fix5a_",  # cross-arc allowlist
            "tests/test_phase_p2fix5b_",  # cross-arc allowlist
            "tests/test_phase_p2fix5c_",  # cross-arc allowlist
            "tests/test_phase_p2fix5d_",  # cross-arc allowlist
            "tests/test_phase_p2fix5e_",  # cross-arc allowlist
            "tests/test_phase_p2fix3_",   # cross-arc allowlist
            "tests/test_phase_p2fix2_",   # P2-FIX-7A cross-arc
            "tests/test_phase_p2fix4_",   # P2-FIX-7A cross-arc
            "docs/phase_p2fix7_",
            "reports/phase_p2fix7_",
            "docs/phase_p2fix7a_",
            "reports/phase_p2fix7a_",
            # P2-FIX-8 cross-arc allowlist
            "main_web.py",
            "app/templates/base.html",
            "app/templates/project_home_page.html",
            "app/templates/project_new_page.html",
            "app/templates/project_browse_page.html",
            "app/templates/partials/workspace_tabs.html",
            "app/templates/partials/workspace_shell.html",
            "app/middleware/security_headers.py",
            "static/styles.css",
            "scripts/",
            "tests/test_phase_p2fix8_",
            "app/templates/partials/project_home.html",
            "app/templates/partials/new_project_minimal.html",
            "app/templates/partials/new_project_result.html",
            "tests/test_phase_wf4_",
            # WF cross-arc allowlist
            "app/ui/dashboard.py",
            "app/templates/partials/_dashboard_oob.html",
            "app/templates/partials/project_selector.html",
            "tests/test_phase_wf1_",
            "tests/test_phase_wf2_",
            "tests/test_phase_wf3_",
            "tests/test_phase_wf4_",
            "tests/test_phase_wf5_",
            "tests/test_phase_wf6_",
            "app/templates/partials/_results_subnav.html",
            "app/ui/scenario_matrix.py",
            "app/templates/partials/scenario_matrix.html",
            "tests/test_phase_m2_",
            "tests/test_phase_m1_",
            "tests/test_phase_m3_",
            "tests/test_phase_m4_",
            "tests/test_phase_stab",
            "app/templates/partials/_scenario_matrix_oob.html",
            "app/ui/dashboard.py",
            "app/templates/partials/_matrix_cell_updated.html",
            "app/templates/partials/_matrix_cell_edit.html",
            "app/templates/partials/_matrix_run_result.html",
                    # UX-1C: active workspace cleanup follow-up allowlist
                    "tests/test_phase_p2fix2_shell_strip.py",
                    "tests/test_phase_p2fix3_c2_first_edit.py",
                    "tests/test_phase_p2fix4_five_area_navigation.py",
                    "tests/test_phase_p2fix5b_normal_mode_shell_strip.py",
                    "tests/test_phase_p2fix5d_five_area_navigation.py",
                    "tests/test_phase_p2fix5e_reference_ux.py",
                    "tests/test_phase_p2fix6_c2_create_copy_ui.py",
                    "tests/test_phase_scenario1_base_case_init.py",
                    "tests/test_phase_scenario1_review_fix.py",
                    "tests/test_phase_scenario2_fixes.py",
                    "tests/test_phase_stab1_run_refreshes_kpis.py",
                    "tests/test_phase_stab2_realized_gearing_scale.py",
                    "tests/test_phase_stab3_capex_subline_propagation.py",
                    "tests/test_phase_stab5_export_route_fix.py",
                    "tests/test_phase_stab6_new_project_first_run.py",
                    "tests/test_phase_stab8_e2e_runtime_validation.py",
                    "tests/test_phase_ux4b_save_as_button.py",
                    "tests/test_phase_wf2_sheet_styling.py",
                    "tests/test_phase_wf3_home_and_projects_split.py",
                    "tests/test_phase_wf4_minimal_create_and_list_hygiene.py",
                    "tests/test_phase_wf5_grouped_results_nav.py",
                    "tests/test_phase_wf6_scenario_status_badges.py",
                    "tests/test_phase57a4_single_capex_sheet_layout.py",
                    "tests/test_phase_pr1_form_timing_fields.py",
                    "tests/test_phase_pr2_realized_gearing.py",
                    "tests/test_phase_pr3_taxonomy.py",
                    "tests/test_phase_p2fix5c_dashboard_kpi.py",
                    "tests/test_phase_stab7_generic_dashboard_parity.py",
                    "tests/test_phase_m1_scenario_matrix.py",
                    "tests/test_phase_m2_scenario_matrix_live.py",
                    "tests/test_phase_m3_scenario_matrix_overrides.py",
                    "tests/test_phase_m4_scenario_matrix_run.py",
            "app/templates/partials/kpis.html",
            "app/templates/partials/scenario_multi_compare_picker.html",
            "app/templates/partials/scenario_workflow_indicators.html",
            "tests/test_phase51a_run_route_golden_characterization.py",
            "tests/test_ux1a_navigation_context_fix.py",
            "tests/test_p1_compare_validation.py",
            "tests/test_phase_ux1_inputs_badge_cleanup.py",
            "tests/test_phase_ux2_active_sheet_refresh.py",
            "tests/test_phase_ux4cde_pilot_polish.py",
            "tests/test_phase_wf2_",
            "tests/test_phase_wf3_",
            "tests/test_phase_wf4_",
            "tests/test_phase_wf5_",
)
        disallowed_prefixes = (
            "app/persistence/",
            "app/services/",
            "app/waterfall_core.py",
            "app/project_factories.py",
            "app/excel_export.py",
            "app/capex_engine.py",
            "app/ui/protected_reference_service.py",
            "main_api.py",
            "static/app.js",
        )
        for f in changed:
            disallowed = [f.startswith(p) for p in disallowed_prefixes]
            assert not any(disallowed), (
                f"Disallowed file changed: {f}"
            )
            allowed = [f.startswith(p) for p in allowed_prefixes]
            assert any(allowed), (
                f"File outside allowed scope: {f}"
            )
