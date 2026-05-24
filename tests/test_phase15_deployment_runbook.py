from __future__ import annotations

import os


def _read(*parts: str) -> str:
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(base, *parts), encoding="utf-8") as handle:
        return handle.read()


def test_deployment_runbook_exists_and_stays_in_single_user_pilot_scope():
    docs = _read("docs", "phase15_deployment_runbook.md")

    assert "single-user guided internal pilot" in docs
    assert "does **not** claim" in docs
    assert "lender-ready deployment status" in docs
    assert "audit-certified operating status" in docs
    assert "SaaS or multi-tenant readiness" in docs
    assert "Runtime remains backend-owned" in docs
    assert "Backup and restore is operational recovery only. It is **not** audit replay" in docs
    assert "`audit_economic_mode` remains audit/reconciliation-only." in docs
    assert "`runtime_economic_mode` remains the only explicit runtime staging path." in docs
    assert "`G20` remains `BLOCKED`." in docs
    assert "`R99/R102` remain `NOT APPROVED`." in docs
    assert "python main_web.py" in docs
    assert "port: `8765`" in docs
    assert "/public-health" in docs


def test_environment_inventory_backup_and_smoke_reports_exist():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for report_name in (
        "phase15_environment_inventory.csv",
        "phase15_backup_restore_checklist.csv",
        "phase15_pilot_smoke_test_checklist.csv",
        "phase15_deployment_risk_register.csv",
    ):
        assert os.path.exists(os.path.join(base, "reports", report_name))

    inventory = _read("reports", "phase15_environment_inventory.csv")
    backup = _read("reports", "phase15_backup_restore_checklist.csv")
    smoke = _read("reports", "phase15_pilot_smoke_test_checklist.csv")
    risk = _read("reports", "phase15_deployment_risk_register.csv")

    assert "FINCO_SECRET_KEY,required" in inventory
    assert "FINCO_DB_PATH,optional" in inventory
    assert "FINCO_COOKIE_SECURE,optional" in inventory
    assert "git_ref_lock_permission_issue,known_environment_issue" in inventory
    assert "pytest_cache_permission_warning,known_environment_issue" in inventory
    assert "bundled_spreadsheet_package_path_issue,known_environment_issue" in inventory
    assert "test_bcrypt_shim_status,known_test_harness_state" in inventory

    assert "backup restore is not audit replay and not replay-engine behavior" in backup
    assert "verify export lineage and provenance remain readable" in backup

    assert "select_tuho" in smoke
    assert "select_oborovo" in smoke
    assert "verify_dirty_state" in smoke
    assert "verify_no_auto_run_after_save" in smoke
    assert "verify_governance_labels,\"G20 BLOCKED and R99/R102 NOT APPROVED remain visible\"" in smoke

    assert "backup_confused_with_audit_replay,guardrail" in risk
    assert "overclaiming_pilot_readiness,guardrail" in risk


def test_runbook_guardrails_confirm_no_behavior_or_authority_drift():
    docs = _read("docs", "phase15_deployment_runbook.md")

    assert "Persistence stores workflow metadata and saved boundaries only." in docs
    assert "Workbook/export remains descriptive and reviewer-facing." in docs
    assert "Scenario compare remains descriptive only." in docs
    assert "does not become replay-engine behavior" in docs
    assert "without changing runtime behavior" in docs

    lowered = docs.lower()
    assert "lender-ready" in lowered
    assert "audit-certified" in lowered
    assert "saaS".lower() in lowered
