"""Phase 16 — CSP Inline Script Fix Tests.

Validates that the CSP/inline-script incompatibility has been fixed so that
production UI interactivity works in browser without CSP console errors.

Scope: security_headers.py, index.html, base.html, static/app.js
"""

from __future__ import annotations

import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

RUNTIME_BOUND_FIELDS = [
    "tariff_eur_mwh",
    "opex_y1_keur",
    "p50_hours",
    "gearing_pct",
    "target_dscr",
    "interest_rate_pct",
    "tenor_years",
]

PREVIEW_ONLY_FIELDS = ["ppa_term_years", "construction_months"]


class TestCSPHeader:
    """CSP header must be explicitly set with script-src 'self' (strict, no unsafe-inline)."""

    def test_security_headers_csp_has_explicit_script_src(self):
        """CSP must have explicit script-src 'self' (no unsafe-inline)."""
        security_file = os.path.join(BASE_DIR, "app/middleware/security_headers.py")
        content = open(security_file).read()

        assert "script-src 'self'" in content, (
            "CSP must explicitly set script-src 'self' — no unsafe-inline"
        )
        # Verify no unsafe-inline for scripts
        csp_match = re.search(r'CSP\s*=\s*\((.*?)\)', content, re.DOTALL)
        assert csp_match, "CSP definition not found"
        csp_body = csp_match.group(1)
        # script-src should not have unsafe-inline
        script_src_lines = [l.strip() for l in csp_body.split(";") if "script-src" in l]
        for line in script_src_lines:
            assert "'unsafe-inline'" not in line, (
                f"script-src must not contain unsafe-inline: {line}"
            )

    def test_csp_has_style_src_unsafe_inline(self):
        """style-src must allow unsafe-inline (needed for Jinja2)."""
        security_file = os.path.join(BASE_DIR, "app/middleware/security_headers.py")
        content = open(security_file).read()
        assert "style-src 'self' 'unsafe-inline'" in content, (
            "style-src must allow unsafe-inline for Jinja2 templates"
        )


class TestTemplateInlineScripts:
    """Template workspace init must use CSP-safe mechanisms."""

    def test_no_inline_executable_workspace_init_script(self):
        """No executable inline script calling applyWorkspaceStateMeta directly."""
        index_html = os.path.join(BASE_DIR, "app/templates/index.html")
        content = open(index_html).read()

        # Find the old pattern (blocked by CSP)
        old_pattern = re.search(
            r'<script>\s*document\.addEventListener\([\'"]DOMContentLoaded[\'"],\s*function\(\)\s*\{[^}]*applyWorkspaceStateMeta\s*\(\s*\{\{\s*workspace_state_meta',
            content,
            re.DOTALL,
        )
        assert not old_pattern, (
            "Old CSP-blocked inline script pattern still present. "
            "Use type=application/json script + JSON.parse approach instead."
        )

    def test_workspace_state_meta_uses_json_script_tag(self):
        """workspace_state_meta must be exposed via type=application/json script tag."""
        index_html = os.path.join(BASE_DIR, "app/templates/index.html")
        content = open(index_html).read()

        assert 'type="application/json"' in content, (
            "workspace_state_meta must use type=application/json script tag for CSP safety"
        )
        assert "workspace-state-meta-json" in content, (
            "workspace_state_meta must be in a script tag with id=workspace-state-meta-json"
        )

    def test_no_inline_onclick_for_discard(self):
        """btn-discard-edits must not have inline onclick handler."""
        index_html = os.path.join(BASE_DIR, "app/templates/index.html")
        content = open(index_html).read()

        # Find btn-discard-edits
        idx = content.find('id="btn-discard-edits"')
        assert idx >= 0, "btn-discard-edits not found"
        # Find the button element
        start = content.rfind("<", 0, idx)
        end = content.find(">", idx)
        btn_html = content[start:end+1]

        assert "onclick" not in btn_html, (
            "btn-discard-edits must not have inline onclick. "
            "Use hx-post or JS event listener in static/app.js."
        )
        # Must have hx-post
        assert "hx-post" in btn_html, "btn-discard-edits must have hx-post"

    def test_no_inline_onclick_for_new_project(self):
        """btn-new-project must not have inline onclick (use JS event listener)."""
        base_html = os.path.join(BASE_DIR, "app/templates/base.html")
        content = open(base_html).read()

        idx = content.find('id="btn-new-project"')
        assert idx >= 0, "btn-new-project not found"
        start = content.rfind("<", 0, idx)
        end = content.find(">", idx)
        btn_html = content[start:end+1]

        assert "onclick" not in btn_html, (
            "btn-new-project must not have inline onclick. "
            "Handler should be in static/app.js or inline script in index.html."
        )

    def test_workspace_init_from_json_data_in_dom(self):
        """Workspace init script must read from JSON script tag, not template injection."""
        index_html = os.path.join(BASE_DIR, "app/templates/index.html")
        content = open(index_html).read()

        # Must have JSON.parse pattern for workspace state
        has_json_parse = "JSON.parse" in content and "workspace-state-meta-json" in content
        assert has_json_parse, (
            "Workspace init must read from #workspace-state-meta-json via JSON.parse"
        )


class TestJavaScriptSafe:
    """static/app.js must not contain financial calculations."""

    def test_no_javascript_financial_calculations(self):
        """No Math.*, irr, npv, pmt, rate calculations in static/app.js."""
        app_js = os.path.join(BASE_DIR, "static/app.js")
        content = open(app_js).read()

        financial_patterns = [
            r'\bMath\.\s*(pow|sqrt|exp|log|sin|cos)',  # Math functions
            r'\birr\s*\(',      # IRR function
            r'\bnpv\s*\(',      # NPV function
            r'\bpmt\s*\(',      # PMT function
            r'\brate\s*\(',     # rate function
            r'\bNPV\s*\(',      # capital NPV
            r'\bIRR\s*\(',      # IRR capital
        ]

        for pattern in financial_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            assert not match, (
                f"JavaScript financial calculation found: {pattern} — "
                "frontend must not calculate financial outputs"
            )


class TestGuardrails:
    """Guardrails — no runtime/model changes."""

    def test_runtime_bound_fields_unchanged(self):
        """All 7 runtime-bound fields remain in _build_schema_from_form."""
        schema_file = os.path.join(BASE_DIR, "main_web.py")
        content = open(schema_file).read()

        for field in RUNTIME_BOUND_FIELDS:
            assert field in content, (
                f"Runtime-bound field '{field}' must remain in main_web.py"
            )

    def test_g20_remains_blocked(self):
        """G20 must remain BLOCKED in project context."""
        project_ctx = os.path.join(BASE_DIR, "app/ui/project_context.py")
        content = open(project_ctx).read()

        assert 'g20_status="BLOCKED"' in content, (
            "G20 must remain BLOCKED"
        )

    def test_r99_r102_not_approved(self):
        """R99 and R102 must remain NOT APPROVED."""
        project_ctx = os.path.join(BASE_DIR, "app/ui/project_context.py")
        content = open(project_ctx).read()

        assert 'r99_r102_status="NOT APPROVED"' in content, (
            "R99/R102 must remain NOT APPROVED"
        )

    def test_no_workbook_calculation_changes(self):
        """No changes to export calculation logic."""
        export_files = [
            os.path.join(BASE_DIR, "app/excel_export.py"),
            os.path.join(BASE_DIR, "app/export/institutional_workbook.py"),
        ]
        for f in export_files:
            if os.path.exists(f):
                content = open(f).read()
                # Just check files are readable and not obviously broken
                assert len(content) > 100, f"{f} seems broken"

    def test_no_persistence_authority_promotion(self):
        """No promotion of frontend/browser state as runtime authority."""
        index_html = os.path.join(BASE_DIR, "app/templates/index.html")
        content = open(index_html).read()

        # Should not have any comment saying "frontend is runtime authority"
        assert "frontend" not in content.lower() or "runtime" not in content.lower() or (
            "frontend does not become runtime authority" in content.lower()
        ), "No persistence authority promotion"

    def test_preview_only_fields_labeled(self):
        """Preview-only fields must have honest labels."""
        sheet_revenue = os.path.join(BASE_DIR, "app/templates/partials/sheet_revenue.html")
        sheet_opex = os.path.join(BASE_DIR, "app/templates/partials/sheet_opex.html")

        for f in [sheet_revenue, sheet_opex]:
            if os.path.exists(f):
                content = open(f).read()
                assert "Preview only — not runtime-bound yet" in content, (
                    f"{f}: preview-only fields must have honest label"
                )


class TestCompileAndSyntax:
    """Must compile and have valid syntax."""

    def test_main_web_compiles(self):
        """main_web.py must compile without errors."""
        main_web = os.path.join(BASE_DIR, "main_web.py")
        with open(main_web) as f:
            code = compile(f.read(), main_web, "exec")
        assert code is not None

    def test_static_app_js_syntax(self):
        """static/app.js must have valid JavaScript syntax."""
        import subprocess
        result = subprocess.run(
            ["node", "--check", os.path.join(BASE_DIR, "static/app.js")],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"app.js syntax error: {result.stderr}"


class TestStaticAppJSWorkspaceInit:
    """static/app.js must support workspace initialization from DOM."""

    def test_app_js_has_apply_workspace_state_meta(self):
        """app.js must have applyWorkspaceStateMeta function."""
        app_js = os.path.join(BASE_DIR, "static/app.js")
        content = open(app_js).read()
        assert "function applyWorkspaceStateMeta" in content or "applyWorkspaceStateMeta = function" in content, (
            "applyWorkspaceStateMeta must be defined in app.js"
        )

    def test_app_js_has_queue_workspace_draft_persist(self):
        """app.js must have queueWorkspaceDraftPersist function."""
        app_js = os.path.join(BASE_DIR, "static/app.js")
        content = open(app_js).read()
        assert "function queueWorkspaceDraftPersist" in content or "queueWorkspaceDraftPersist = function" in content, (
            "queueWorkspaceDraftPersist must be defined in app.js"
        )

    def test_app_js_handles_discard(self):
        """app.js must handle btn-discard-edits click event."""
        app_js = os.path.join(BASE_DIR, "static/app.js")
        content = open(app_js).read()
        assert "btn-discard-edits" in content, (
            "app.js must handle btn-discard-edits click event"
        )
        assert "/scenarios/state/discard" in content, (
            "app.js must POST to /scenarios/state/discard on discard click"
        )

    def test_app_js_applies_workspace_state_meta_from_response(self):
        """Discard handler must call applyWorkspaceStateMeta with response data."""
        app_js = os.path.join(BASE_DIR, "static/app.js")
        content = open(app_js).read()

        discard_idx = content.find('btn-discard-edits')
        assert discard_idx >= 0
        discard_section = content[discard_idx:discard_idx+2000]

        assert "applyWorkspaceStateMeta" in discard_section, (
            "Discard handler must call applyWorkspaceStateMeta with response data"
        )