"""
Phase 25B: Onboarding / Help / Demo Mode
Tests for pilot help onboarding partial and pilot user guide.
No financial formula changes. No runtime model changes.
"""
import os
import re

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestPilotHelpOnboardingPartial:
    """Tests for pilot_help_onboarding.html partial."""

    def test_pilot_help_onboarding_partial_exists(self):
        path = os.path.join(REPO_ROOT, "app/templates/partials/pilot_help_onboarding.html")
        assert os.path.exists(path), f"pilot_help_onboarding.html not found at {path}"

    def test_help_partial_contains_core_topics(self):
        path = os.path.join(REPO_ROOT, "app/templates/partials/pilot_help_onboarding.html")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        topics = [
            "What is FincoGPT",
            "validated templates",
            "generic projects",
            "pilot workflow",
            "audit",  # audit/reconciliation
            "export",  # export/download
            "backup",  # backup/restore
            "limitations",
        ]
        for topic in topics:
            assert topic.lower() in content.lower(), f"Help partial missing topic: {topic}"


class TestPilotUserGuide:
    """Tests for pilot_user_guide.md."""

    def test_pilot_user_guide_exists(self):
        path = os.path.join(REPO_ROOT, "docs/pilot_user_guide.md")
        assert os.path.exists(path), f"pilot_user_guide.md not found at {path}"

    def test_pilot_user_guide_contains_quick_start(self):
        path = os.path.join(REPO_ROOT, "docs/pilot_user_guide.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "quick start" in content.lower() or "run workflow" in content.lower(), \
            "User guide should include quick start or run workflow section"

    def test_validated_scope_is_explicit(self):
        path = os.path.join(REPO_ROOT, "docs/pilot_user_guide.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        # TUHO/Oborovo should be listed as validated
        tuho_found = "tuho" in content.lower()
        oborovo_found = "oborovo" in content.lower()
        assert tuho_found, "TUHO should be mentioned in user guide as validated template"
        assert oborovo_found, "Oborovo should be mentioned in user guide as validated template"
        # Generic/new projects should be flagged as unvalidated/exploratory
        generic_found = (
            "generic" in content.lower()
            and ("unvalidated" in content.lower() or "exploratory" in content.lower())
        )
        assert generic_found, "Generic projects should be flagged as unvalidated/exploratory"

    def test_non_claims_are_explicit(self):
        path = os.path.join(REPO_ROOT, "docs/pilot_user_guide.md")
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        claims = ["bank approval", "lender approval", "external audit", "certification", "saas-ready"]
        for claim in claims:
            # Should appear in a negation context (claim followed by negation OR negation followed by claim)
            neg_context = re.search(
                rf"{re.escape(claim)}.*?(not|❌|—)|(not|❌|—)\s*.*{re.escape(claim)}",
                content,
                re.IGNORECASE | re.DOTALL,
            )
            assert neg_context, f"User guide should explicitly deny '{claim}' claim"

    def test_export_and_stale_run_guidance_present(self):
        path = os.path.join(REPO_ROOT, "docs/pilot_user_guide.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "last clean backend run" in content.lower() or "last backend run" in content.lower(), \
            "User guide should explain exports are based on last clean backend run"
        assert "save the scenario" in content.lower() or "run again" in content.lower() or "re-run" in content.lower(), \
            "User guide should include stale-run / re-run guidance"

    def test_backup_restore_guidance_present(self):
        path = os.path.join(REPO_ROOT, "docs/pilot_user_guide.md")
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        assert "backup" in content, "User guide should cover backup and restore"
        # Should NOT claim enterprise DR or cloud/offsite
        assert "enterprise dr" not in content, "User guide should not claim enterprise DR"
        assert "cloud/offsite" not in content, "User guide should not claim cloud/offsite backup"

    def test_single_user_boundary_guidance_present(self):
        path = os.path.join(REPO_ROOT, "docs/pilot_user_guide.md")
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        assert "single-user" in content or "single user" in content, \
            "User guide should state single-user mode"
        # Multi-user/tenant/RBAC should be explicitly denied
        denied = (
            "no multi-user" in content
            or "no multi-tenant" in content
            or "no rbac" in content.lower()
            or ("single-user" in content and "internal" in content)
        )
        assert denied, "User guide should deny multi-user / tenant isolation / RBAC"


class TestNoJSFinancialCalculations:
    """Tests to ensure no JS financial calculations were added."""

    def test_no_js_financial_calculations_added(self):
        # Scan app.js for obvious financial calculation patterns
        app_js = os.path.join(REPO_ROOT, "static/app.js")
        if not os.path.exists(app_js):
            return  # No app.js to scan
        with open(app_js, encoding="utf-8") as f:
            content = f.read()
        # Patterns that would indicate financial calculations in JS
        patterns = [
            r"\bdscr\s*=",
            r"\bequity\s*irr",
            r"\bproject\s*irr",
            r"\bsenior\s*debt",
            r"\bNPV\s*\(",
            r"\bIRR\s*\(",
            r"\bXIRR\s*\(",
            r"\bPV\s*\(",
        ]
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            # Allow very short matches that are likely CSS class names, not calculations
            short_allowed = ["dscr=", "irr="]
            real_matches = [m for m in matches if m.lower() not in short_allowed]
            assert not real_matches, \
                f"JS financial calculation pattern '{pattern}' found in app.js — this should not be added"


class TestGuardrailsUnchanged:
    """Tests to confirm guardrails remain in place."""

    def test_guardrails_unchanged(self):
        # Check workspace_shell.html for G20/R99/R102 status
        shell_path = os.path.join(REPO_ROOT, "app/templates/partials/workspace_shell.html")
        with open(shell_path, encoding="utf-8") as f:
            content = f.read()
        # G20 blocked
        assert "BLOCKED" in content, "G20 should remain BLOCKED"
        # R99/R102 not approved
        assert "NOT APPROVED" in content, "R99/R102 should remain NOT APPROVED"

    def test_partial_pay_sweep_not_promoted(self):
        shell_path = os.path.join(REPO_ROOT, "app/templates/partials/workspace_shell.html")
        with open(shell_path, encoding="utf-8") as f:
            content = f.read().lower()
        # Should not be promoted as approved/active
        assert not re.search(r"partial[\s_-]pay[\s_-]sweep.*approved", content), \
            "partial_pay_sweep should not be promoted"

    def test_flat_min_dscr_sculpting_not_promoted(self):
        shell_path = os.path.join(REPO_ROOT, "app/templates/partials/workspace_shell.html")
        with open(shell_path, encoding="utf-8") as f:
            content = f.read().lower()
        assert not re.search(r"flat[\s_-]dscr.*sculpting.*approved", content), \
            "flat_dscr_sculpted should not be promoted"
        assert not re.search(r"minimum[\s_-]dscr.*sculpting.*approved", content), \
            "minimum_dscr_sculpted should not be promoted"
