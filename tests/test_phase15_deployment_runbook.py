from __future__ import annotations

import csv
import os
from io import StringIO


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

    inventory = list(csv.DictReader(StringIO(_read("reports", "phase15_environment_inventory.csv"))))
    backup = list(csv.DictReader(StringIO(_read("reports", "phase15_backup_restore_checklist.csv"))))
    smoke = list(csv.DictReader(StringIO(_read("reports", "phase15_pilot_smoke_test_checklist.csv"))))
    risk = list(csv.DictReader(StringIO(_read("reports", "phase15_deployment_risk_register.csv"))))

    inventory_map = {row["setting_or_issue"]: row for row in inventory}
    assert inventory_map["FINCO_SECRET_KEY"]["required"] == "required"
    assert inventory_map["FINCO_DB_PATH"]["required"] == "optional"
    assert inventory_map["FINCO_COOKIE_SECURE"]["required"] == "optional"
    assert inventory_map["git_ref_lock_permission_issue"]["required"] == "known_environment_issue"
    assert inventory_map["pytest_cache_permission_warning"]["required"] == "known_environment_issue"
    assert inventory_map["bundled_spreadsheet_package_path_issue"]["required"] == "known_environment_issue"
    assert inventory_map["test_bcrypt_shim_status"]["required"] == "known_test_harness_state"

    backup_steps = [row["step"] for row in backup]
    assert backup_steps[:2] == ["1", "2"]
    assert any(
        "backup restore is not audit replay and not replay-engine behavior" in row["details"]
        or "backup restore is not audit replay and not replay-engine behavior" in row["integrity_check"]
        for row in backup
    )
    assert any("verify export lineage and provenance remain readable" in row["details"] or "verify export lineage and provenance remain readable" in row["integrity_check"] for row in backup)

    smoke_steps = [row["step"] for row in smoke]
    assert smoke_steps[:4] == ["start_app", "check_public_health", "open_login", "select_tuho"]
    assert "select_oborovo" in smoke_steps
    assert "verify_dirty_state" in smoke_steps
    assert "verify_no_auto_run_after_save" in smoke_steps
    assert any(row["step"] == "verify_governance_labels" and row["expected_result"] == "G20 BLOCKED and R99/R102 NOT APPROVED remain visible" for row in smoke)

    risk_map = {row["risk"]: row for row in risk}
    assert risk_map["backup_confused_with_audit_replay"]["current_status"] == "guardrail"
    assert risk_map["overclaiming_pilot_readiness"]["current_status"] == "guardrail"


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
