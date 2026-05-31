"""
Phase 26D: Deployment / Observability
Tests for health endpoints, observability helpers, and deployment runbook.
No financial formula changes. No runtime model changes.
"""
import os
import sys
import re

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)


class TestPhase26DDocExists:
    def test_phase26d_doc_exists(self):
        path = os.path.join(REPO_ROOT, "docs/phase26d_deployment_observability.md")
        assert os.path.exists(path), f"phase26d doc not found at {path}"


class TestDeploymentRunbook:
    def test_deployment_runbook_exists(self):
        path = os.path.join(REPO_ROOT, "docs/deployment_runbook.md")
        assert os.path.exists(path), f"deployment runbook not found at {path}"

    def test_runbook_documents_trusted_pilot_install(self):
        path = os.path.join(REPO_ROOT, "docs/deployment_runbook.md")
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        assert "constraints.txt" in content, "runbook should mention constraints.txt install"
        assert "pilot" in content, "runbook should mention FINCO_APP_MODE=pilot"
        assert "finco_admin_password" in content or "admin password" in content, \
            "runbook should mention required secret/admin password env vars"


class TestHealthReadinessEndpoint:
    def test_health_or_readiness_endpoint_or_helper_exists(self):
        obs_path = os.path.join(REPO_ROOT, "app/observability.py")
        assert os.path.exists(obs_path), "observability.py should exist"
        main_path = os.path.join(REPO_ROOT, "main_web.py")
        with open(main_path, encoding="utf-8") as f:
            content = f.read()
        has_readyz = "/readyz" in content or "readyz" in content
        has_healthz = "/healthz" in content or "healthz" in content
        assert has_readyz or has_healthz, "should have /readyz or /healthz endpoint in main_web.py"

    def test_health_status_redacts_secrets(self):
        sys.path.insert(0, os.path.join(REPO_ROOT, "app"))
        from observability import redact_config_value, get_safe_config_summary
        # short strings (<=4 chars) should be fully masked
        assert redact_config_value("abc") == "****", "short strings should be fully masked"
        assert redact_config_value("ab") == "****", "short strings should be fully masked"
        # longer strings show first 2 + last 2 chars
        result = redact_config_value("long-secret-value")
        assert result[:2] == "lo"
        assert "****" in result, "long strings should show first 2 + **** + last 2"
        # get_safe_config_summary should not expose raw secret values
        config = get_safe_config_summary()
        config_str = str(config).lower()
        assert "ghp_" not in config_str and "changeme" not in config_str, \
            "config summary should not expose raw secret values or placeholders"
        assert "finco_secret_key" not in config_str, \
            "FINCO_SECRET_KEY should not appear in safe config summary at all"

    def test_health_status_mentions_database_and_backup_posture(self):
        obs_path = os.path.join(REPO_ROOT, "app/observability.py")
        with open(obs_path, encoding="utf-8") as f:
            content = f.read()
        assert "db_reachable" in content, "health should mention db_reachable"
        assert "backup_dir_reachable" in content, "health should mention backup_dir_reachable"
        runbook_path = os.path.join(REPO_ROOT, "docs/deployment_runbook.md")
        with open(runbook_path, encoding="utf-8") as f:
            runbook = f.read().lower()
        assert "database" in runbook or "db" in runbook, "runbook should mention database/DB"
        assert "backup" in runbook, "runbook should mention backup"


class TestNoEnterpriseClaims:
    def test_no_enterprise_deployment_claims(self):
        runbook_path = os.path.join(REPO_ROOT, "docs/deployment_runbook.md")
        phase_doc_path = os.path.join(REPO_ROOT, "docs/phase26d_deployment_observability.md")
        found = []
        for path in [runbook_path, phase_doc_path]:
            with open(path, encoding="utf-8") as f:
                c = f.read().lower()
            for claim in ["soc2", "enterprise sla", "bank approval", "lender approval", "external audit", "saas-ready"]:
                start = 0
                while True:
                    idx = c.find(claim, start)
                    if idx == -1:
                        break
                    window_before = c[max(0, idx-100):idx]
                    window_after = c[idx+len(claim):idx+len(claim)+10]
                    is_denial = (
                        "not" in window_before
                        or "no " in window_before[-50:]
                        or "out of scope" in window_before
                        or "out-of-scope" in window_before
                        or "\xe2\x9d\x9c" in window_before.encode().decode('utf-8', 'ignore')  # ❌
                        or "\xe2\x9d\x9c" in window_after.encode().decode('utf-8', 'ignore')
                    )
                    if not is_denial:
                        found.append((path, claim))
                    start = idx + 1
        assert not found, f"docs should deny enterprise claims: {found}"


class TestAppModeDocumentation:
    def test_app_mode_and_pilot_config_documented(self):
        runbook_path = os.path.join(REPO_ROOT, "docs/deployment_runbook.md")
        with open(runbook_path, encoding="utf-8") as f:
            content = f.read().lower()
        assert "development" in content, "runbook should mention development mode"
        assert "internal" in content, "runbook should mention internal mode"
        assert "pilot" in content, "runbook should mention pilot mode"
        assert "fails fast" in content or "fail-fast" in content or "fail fast" in content, \
            "runbook should document pilot fail-fast behavior from Phase 26B"


class TestNoRuntimeModelChanges:
    def test_no_runtime_model_files_changed_or_claimed(self):
        phase_doc_path = os.path.join(REPO_ROOT, "docs/phase26d_deployment_observability.md")
        with open(phase_doc_path, encoding="utf-8") as f:
            content = f.read().lower()
        assert "no runtime formula changes" in content or "no financial formula changes" in content, \
            "phase doc should state no financial model changes"
        assert "no model files changed" in content or "no runtime model changes" in content, \
            "phase doc should state no model files changed"


class TestNoJSFinancialCalculations:
    def test_no_js_financial_calculations_added(self):
        app_js = os.path.join(REPO_ROOT, "static/app.js")
        if not os.path.exists(app_js):
            return
        with open(app_js, encoding="utf-8") as f:
            content = f.read()
        patterns = [
            r"\bdscr\s*=",
            r"\bequity\s*irr",
            r"\bproject\s*irr",
            r"\bsenior\s*debt",
            r"\bNPV\s*\(",
            r"\bIRR\s*\(",
        ]
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            short_allowed = ["dscr=", "irr="]
            real_matches = [m for m in matches if m.lower() not in short_allowed]
            assert not real_matches, \
                f"JS financial calculation pattern '{pattern}' found in app.js"


class TestGuardrailsUnchanged:
    def test_guardrails_unchanged(self):
        shell_path = os.path.join(REPO_ROOT, "app/templates/partials/workspace_shell.html")
        with open(shell_path, encoding="utf-8") as f:
            content = f.read()
        assert "BLOCKED" in content, "G20 should remain BLOCKED"
        assert "NOT APPROVED" in content, "R99/R102 should remain NOT APPROVED"

    def test_partial_pay_sweep_not_promoted(self):
        shell_path = os.path.join(REPO_ROOT, "app/templates/partials/workspace_shell.html")
        with open(shell_path, encoding="utf-8") as f:
            content = f.read().lower()
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
