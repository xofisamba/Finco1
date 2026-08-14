from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"

MANUAL_ONLY = (
    "phase1b_baseline_check.yml",
    "phase2a_clean_engine_check.yml",
    "phase2b_tax_cfads_check.yml",
    "c3b3b_clean_tax_cfads_debt_feedback_check.yml",
    "c3b3c_tax_policy_contract_check.yml",
    "c3b3d0_tax_identity_atad_check.yml",
    "c3b3d1_canonical_shl_schedule_check.yml",
    "c3b3d2a_oborovo_shl_source_truth_check.yml",
    "c3b3d2b0_clean_shl_formula_parity_check.yml",
    "c3b3d2b1_shl_production_wiring_check.yml",
    "c3b3d2b2c_bank_sizing_cfads_production_check.yml",
    "c3b3d2b3_debt_sizing_case_production_check.yml",
    "c3b3d2b4_dscr_post_senior_cash_authority_check.yml",
    "phase2c_senior_debt_check.yml",
    "phase2d_recon_check.yml",
)

CURRENT_BLOCKING = (
    "mvp_g2a_financing_stack_check.yml",
    "mvp_g1_governance_methodology_lock.yml",
    "mvp_g0_generic_clean_engine_check.yml",
    "c3b3d2b5_shl_fixed_point_integration_check.yml",
    "c3b3d2b6_base_post_senior_cash_parity_check.yml",
    "c3b3d2b7_bank_case_senior_parity_check.yml",
    "c3b3d2b8_base_senior_shl_parity_check.yml",
    "c3b1_diagnostic_check.yml",
    "c3b3a_clean_senior_debt_check.yml",
    "ci.yml",
    "parity_guardrails.yml",
)


def _trigger_lines(workflow_name: str) -> list[str]:
    lines = (WORKFLOWS / workflow_name).read_text(encoding="utf-8").splitlines()
    start = lines.index("on:") + 1
    block: list[str] = []
    for line in lines[start:]:
        if line and not line[0].isspace() and not line.lstrip().startswith("#"):
            break
        if line.strip() and not line.lstrip().startswith("#"):
            block.append(line.strip())
    return block


def test_historical_workflows_are_strictly_manual_only() -> None:
    for workflow_name in MANUAL_ONLY:
        assert _trigger_lines(workflow_name) == ["workflow_dispatch:"], workflow_name


def test_current_blocking_ring_remains_automatic_on_pull_requests() -> None:
    for workflow_name in CURRENT_BLOCKING:
        triggers = _trigger_lines(workflow_name)
        assert "pull_request:" in triggers, workflow_name
        assert any("main" in line for line in triggers), workflow_name


def test_ci_and_parity_remain_automatic_on_main_pushes() -> None:
    for workflow_name in ("ci.yml", "parity_guardrails.yml"):
        triggers = _trigger_lines(workflow_name)
        assert "push:" in triggers, workflow_name
        assert any("main" in line for line in triggers), workflow_name
