"""Phase 9 audit_economic_mode contract reconciliation tests."""

from __future__ import annotations

import csv
import dataclasses
import inspect
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = REPO_ROOT / "docs" / "phase9_audit_economic_mode_contract_reconciliation.md"
FIELD_MAP = REPO_ROOT / "reports" / "phase9_audit_economic_mode_field_map.csv"
AUTHORITY_MATRIX = REPO_ROOT / "reports" / "phase9_audit_vs_runtime_authority_matrix.csv"
GATE_MATRIX = REPO_ROOT / "reports" / "phase9_audit_economic_mode_gate_matrix.csv"


def _csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _run_waterfall(
    *,
    project_name: str = "TUHO-WIND-1",
    use_distributionaccount_runtime_wiring: bool = False,
    use_dualrun_validation: bool = False,
):
    from app.project_factories import create_default_oborovo, create_default_tuho_wind1
    from app.ui_runner import _build_period_engine as build_period_engine
    from app.waterfall_core import run_waterfall_v3_core

    common = dict(
        rate_per_period=0.0,
        tenor_periods=0,
        target_dscr=1.15,
        lockup_dscr=1.10,
        tax_rate=0.10,
        dsra_months=6,
        shl_amount=0.0,
        shl_rate=0.0,
        shl_idc_keur=0.0,
        shl_repayment_method="bullet",
        shl_tenor_years=0,
        shl_wht_rate=0.0,
        discount_rate_project=0.0641,
        discount_rate_equity=0.0965,
        fixed_debt_keur=None,
        fixed_ds_keur=None,
        rate_schedule=None,
        senior_sculpting_config=None,
        equity_irr_method="equity_only",
        share_capital_keur=0.0,
        sculpt_capex_keur=0.0,
        debt_sizing_method="dscr_sculpt",
        dscr_schedule=None,
        advanced_opex_line_items=None,
        advanced_capex_line_items=None,
        advanced_capex_depreciation_schedule=None,
        use_senior_sweep_cash_cap_for_shl=False,
        use_tuho_r99_input_engine=False,
        use_shl_fcf_waterfall_engine=False,
        use_tax_bridge_engine=False,
        use_shl_gross_accrued_for_pnl=False,
        shl_fcf_waterfall_cash_schedule_keur=(),
        shl_fcf_waterfall_minimum_cash_retained_keur=0.0,
        tuho_cit_cash_tax_start_operating_index=None,
        use_shl_canonical_engine=False,
        use_depreciation_canonical_engine=False,
        use_senior_debt_sizing_engine=False,
        use_co2_revenue_bridge=False,
        use_co2_cit_bridge=False,
        use_distributionaccount_runtime_wiring=use_distributionaccount_runtime_wiring,
        use_dualrun_validation=use_dualrun_validation,
    )

    inputs = (
        create_default_tuho_wind1()
        if project_name == "TUHO-WIND-1"
        else create_default_oborovo()
    )
    engine = build_period_engine(inputs)
    return run_waterfall_v3_core(inputs=inputs, engine=engine, **common)


class TestRequiredArtifacts:
    def test_doc_and_reports_exist(self):
        for path in (DOC_PATH, FIELD_MAP, AUTHORITY_MATRIX, GATE_MATRIX):
            assert path.exists(), f"Missing expected artifact: {path}"


class TestContractDefaults:
    def test_distribution_account_input_defaults_are_explicit_and_off(self):
        from domain.distribution_account.inputs import DistributionAccountPeriodInput

        by_name = {field.name: field for field in dataclasses.fields(DistributionAccountPeriodInput)}
        assert by_name["audit_economic_mode"].default is False
        assert by_name["runtime_economic_mode"].default is False
        assert by_name["enable_r99_r102_runtime"].default is False

    def test_runtime_flags_default_off_in_waterfall_signature(self):
        from app.waterfall_core import run_waterfall_v3_core

        signature = inspect.signature(run_waterfall_v3_core)
        assert signature.parameters["use_dualrun_validation"].default is False
        assert signature.parameters["use_distributionaccount_runtime_wiring"].default is False


class TestRoutingBoundary:
    def test_runtime_wiring_uses_runtime_mode_not_audit_mode(self):
        from app import waterfall_core

        source = inspect.getsource(waterfall_core._apply_distributionaccount_runtime_wiring)
        assert "runtime_economic_mode=True" in source
        assert "audit_economic_mode=True" not in source

    def test_dualrun_still_uses_audit_mode_for_comparison(self):
        from app import waterfall_core

        source = inspect.getsource(waterfall_core)
        assert "audit_economic_mode=True" in source

    def test_waterfall_core_does_not_import_persistence_authority(self):
        from app import waterfall_core

        source = inspect.getsource(waterfall_core)
        assert "app.persistence" not in source
        assert "replay_engine" not in source


class TestAuditModeVisibilityOnly:
    def test_dualrun_adds_visibility_without_mutating_runtime_totals(self):
        baseline = _run_waterfall(use_distributionaccount_runtime_wiring=False, use_dualrun_validation=False)
        audit_view = _run_waterfall(use_distributionaccount_runtime_wiring=False, use_dualrun_validation=True)

        assert hasattr(audit_view, "_dualrun_validation")
        assert audit_view._dualrun_validation is not None
        assert audit_view.total_distribution_keur == baseline.total_distribution_keur
        assert [p.distribution_keur for p in audit_view.periods] == [p.distribution_keur for p in baseline.periods]

    def test_audit_mode_disabled_preserves_default_runtime_outputs(self):
        baseline = _run_waterfall(use_distributionaccount_runtime_wiring=False, use_dualrun_validation=False)
        again = _run_waterfall(use_distributionaccount_runtime_wiring=False, use_dualrun_validation=False)

        assert baseline.total_distribution_keur == again.total_distribution_keur
        assert baseline.distribution_source == again.distribution_source


class TestAuthorityReports:
    def test_field_map_marks_audit_mode_as_never_routable(self):
        rows = {row["field_name"]: row for row in _csv_rows(FIELD_MAP)}
        assert rows["audit_economic_mode"]["runtime_route_allowed"] == "no"
        assert rows["runtime_economic_mode"]["default_state"] == "false"

    def test_authority_matrix_marks_workbook_and_reports_non_authoritative(self):
        rows = {row["artifact_or_path"]: row for row in _csv_rows(AUTHORITY_MATRIX)}
        assert rows["workbook exports"]["runtime_authoritative"] == "no"
        assert rows["CSV reports"]["runtime_authoritative"] == "no"
        assert rows["frontend HTMX/Jinja"]["runtime_authoritative"] == "no"

    def test_gate_matrix_keeps_governance_blocked(self):
        rows = {row["control_or_gate"]: row for row in _csv_rows(GATE_MATRIX)}
        assert rows["G20 gate"]["governance_status"] == "BLOCKED"
        assert rows["R99 promotion"]["governance_status"] == "NOT_APPROVED"
        assert rows["R102 promotion"]["governance_status"] == "NOT_APPROVED"


class TestContractDocumentation:
    def test_doc_states_current_conclusion_and_scope_guardrails(self):
        content = DOC_PATH.read_text(encoding="utf-8")
        assert "Conclusion reached: **A — no current runtime contradiction exists**" in content
        assert "no runtime/model formulas changed" in content
        assert "no workbook calculations changed" in content
        assert "no replay engine behavior added" in content

    def test_doc_preserves_governance_posture(self):
        content = DOC_PATH.read_text(encoding="utf-8")
        assert "`G20` remains `BLOCKED`" in content
        assert "`R99` remains `NOT APPROVED`" in content
        assert "`R102` remains `NOT APPROVED`" in content
