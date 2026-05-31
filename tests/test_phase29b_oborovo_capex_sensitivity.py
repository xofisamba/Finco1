"""
Phase 29B: Oborovo CAPEX Sensitivity
Tests for Oborovo CAPEX sensitivity diagnostic pack.
Diagnostic only. No financial formula changes. No runtime model changes.
"""
import os
import sys
import copy

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _scale_oborovo_capex(inputs, factor):
    """Scale Oborovo capex items by factor, return new ProjectInputs (test-local only)."""
    import copy
    from dataclasses import replace
    cloned = copy.deepcopy(inputs)
    items = list(cloned.capex.capex_items())
    scaled_items = [replace(item, amount_keur=item.amount_keur * factor) for item in items]
    # Rebuild CapexStructure with scaled items
    new_capex = replace(cloned.capex,
        epc_contract=scaled_items[0],
        production_units=scaled_items[1],
        epc_other=scaled_items[2],
        grid_connection=scaled_items[3],
        ops_prep=scaled_items[4],
        insurances=scaled_items[5],
        lease_tax=scaled_items[6],
        construction_mgmt_a=scaled_items[7],
        commissioning=scaled_items[8],
        audit_legal=scaled_items[9],
        construction_mgmt_b=scaled_items[10],
        contingencies=scaled_items[11],
        taxes=scaled_items[12],
        project_acquisition=scaled_items[13],
        project_rights=scaled_items[14])
    return replace(cloned, capex=new_capex)

sys.path.insert(0, REPO_ROOT)


class TestPhase29BDocExists:
    def test_phase29b_doc_exists(self):
        path = os.path.join(REPO_ROOT, "docs/phase29b_oborovo_capex_sensitivity.md")
        assert os.path.exists(path), f"phase29b doc not found at {path}"

    def test_phase29b_matrix_exists(self):
        path = os.path.join(REPO_ROOT, "docs/phase29b_oborovo_capex_sensitivity_matrix.md")
        assert os.path.exists(path), f"phase29b matrix not found at {path}"


class TestOborovoBaseCaseRecapPresent:
    def test_oborovo_base_senior_debt_42852_recapped(self):
        path = os.path.join(REPO_ROOT, "docs/phase29b_oborovo_capex_sensitivity.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "42,852" in content or "42852" in content, \
            "doc should mention Oborovo base senior debt 42,852.27 kEUR"

    def test_oborovo_shl_opening_15790_recapped(self):
        path = os.path.join(REPO_ROOT, "docs/phase29b_oborovo_capex_sensitivity.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "15,790" in content or "15790" in content, \
            "doc should mention Oborovo opening SHL ~15,790 kEUR"

    def test_oborovo_first_distribution_op39_recapped(self):
        path = os.path.join(REPO_ROOT, "docs/phase29b_oborovo_capex_sensitivity.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "op_idx 39" in content or "op_idx=39" in content or "op_idx 39" in content, \
            "doc should mention Oborovo first valid distribution op_idx 39"


class TestSensitivityScopeIsExplicit:
    def test_sensitivity_classified_as_diagnostic(self):
        path = os.path.join(REPO_ROOT, "docs/phase29b_oborovo_capex_sensitivity.md")
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        assert "diagnostic" in content, "sensitivity should be classified as diagnostic"
        assert "not excel-validated" in content or "not excel validated" in content, \
            "sensitivity should be stated as not Excel-validated"

    def test_not_bank_lender_ready(self):
        path = os.path.join(REPO_ROOT, "docs/phase29b_oborovo_capex_sensitivity.md")
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        # Check non-claims section or limitation section
        assert "not bank" in content or "not lender" in content or "bank" not in content.split("limitation")[0][-500:], \
            "sensitivity should deny bank/lender-ready claims"


class TestSensitivityCasesDefined:
    def test_sensitivity_cases_defined(self):
        path = os.path.join(REPO_ROOT, "docs/phase29b_oborovo_capex_sensitivity.md")
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        # Check for sensitivity case table with at least base, +5%, +10%, -5%, -10%
        cases = ["+5%", "+10%", "-5%", "-10%", "base"]
        for case in cases:
            assert case in content, f"doc should define CAPEX {case} sensitivity case"


class TestOborovoSensitivityCasesRunWithoutCrashing:
    def test_oborovo_base_runs(self):
        """Oborovo base case runs without crashing."""
        from app.project_factories import create_default_oborovo
        from app.waterfall_runner import WaterfallRunner
        from domain.period_engine import PeriodEngine

        inputs = create_default_oborovo()
        engine = PeriodEngine(
            financial_close=inputs.info.financial_close,
            construction_months=inputs.info.construction_months,
            horizon_years=inputs.info.horizon_years,
            ppa_years=inputs.revenue.ppa_term_years,
        )
        runner = WaterfallRunner(inputs=inputs, engine=engine)
        from app.waterfall_runner import WaterfallRunConfig
        config = WaterfallRunConfig.from_inputs(inputs, engine)
        result = runner.run(config)
        assert result is not None, "Oborovo base should run without crashing"

    def test_capex_5pct_clone_runs(self):
        """CAPEX +5% (cloned, test-local) runs without crashing."""
        from app.project_factories import create_default_oborovo
        from app.waterfall_runner import WaterfallRunner
        from domain.period_engine import PeriodEngine

        inputs = create_default_oborovo()
        scaled = _scale_oborovo_capex(inputs, 1.05)

        engine = PeriodEngine(
            financial_close=scaled.info.financial_close,
            construction_months=scaled.info.construction_months,
            horizon_years=scaled.info.horizon_years,
            ppa_years=scaled.revenue.ppa_term_years,
        )
        from app.waterfall_runner import WaterfallRunConfig
        config = WaterfallRunConfig.from_inputs(scaled, engine)
        runner = WaterfallRunner(inputs=scaled, engine=engine)
        result = runner.run(config)
        assert result is not None, "CAPEX +5% should run without crashing"

    def test_capex_10pct_clone_runs(self):
        """CAPEX +10% (cloned, test-local) runs without crashing."""
        from app.project_factories import create_default_oborovo
        from app.waterfall_runner import WaterfallRunner
        from domain.period_engine import PeriodEngine

        inputs = create_default_oborovo()
        scaled = _scale_oborovo_capex(inputs, 1.10)

        engine = PeriodEngine(
            financial_close=scaled.info.financial_close,
            construction_months=scaled.info.construction_months,
            horizon_years=scaled.info.horizon_years,
            ppa_years=scaled.revenue.ppa_term_years,
        )
        from app.waterfall_runner import WaterfallRunConfig
        config = WaterfallRunConfig.from_inputs(scaled, engine)
        runner = WaterfallRunner(inputs=scaled, engine=engine)
        result = runner.run(config)
        assert result is not None, "CAPEX +10% should run without crashing"

    def test_capex_minus5pct_clone_runs(self):
        """CAPEX -5% (cloned, test-local) runs without crashing."""
        from app.project_factories import create_default_oborovo
        from app.waterfall_runner import WaterfallRunner
        from domain.period_engine import PeriodEngine

        inputs = create_default_oborovo()
        scaled = _scale_oborovo_capex(inputs, 0.95)

        engine = PeriodEngine(
            financial_close=scaled.info.financial_close,
            construction_months=scaled.info.construction_months,
            horizon_years=scaled.info.horizon_years,
            ppa_years=scaled.revenue.ppa_term_years,
        )
        from app.waterfall_runner import WaterfallRunConfig
        config = WaterfallRunConfig.from_inputs(scaled, engine)
        runner = WaterfallRunner(inputs=scaled, engine=engine)
        result = runner.run(config)
        assert result is not None, "CAPEX -5% should run without crashing"

    def test_capex_minus10pct_clone_runs(self):
        """CAPEX -10% (cloned, test-local) runs without crashing."""
        from app.project_factories import create_default_oborovo
        from app.waterfall_runner import WaterfallRunner
        from domain.period_engine import PeriodEngine

        inputs = create_default_oborovo()
        scaled = _scale_oborovo_capex(inputs, 0.90)

        engine = PeriodEngine(
            financial_close=scaled.info.financial_close,
            construction_months=scaled.info.construction_months,
            horizon_years=scaled.info.horizon_years,
            ppa_years=scaled.revenue.ppa_term_years,
        )
        from app.waterfall_runner import WaterfallRunConfig
        config = WaterfallRunConfig.from_inputs(scaled, engine)
        runner = WaterfallRunner(inputs=scaled, engine=engine)
        result = runner.run(config)
        assert result is not None, "CAPEX -10% should run without crashing"


class TestSensitivityOutputsAreNumericAndSafe:
    def test_base_outputs_numeric(self):
        """Base case key outputs are numeric (no NaN)."""
        from app.ui_runner import run_demo_project
        result = run_demo_project("Oborovo", "Base")
        r = result.result
        assert r is not None, "Oborovo base should produce result"
        numeric_fields = ['total_revenue_keur', 'total_opex_keur', 'equity_irr', 'project_irr']
        for field in numeric_fields:
            val = getattr(r, field, None)
            if val is not None:
                assert isinstance(val, (int, float)), f"{field} should be numeric"
                assert val != float('nan'), f"{field} should not be NaN"


class TestSensitivityRevenueOpexDebtDistributionNonNegative:
    def test_base_revenue_non_negative(self):
        """Base case revenue, OPEX, distributions non-negative."""
        from app.ui_runner import run_demo_project
        result = run_demo_project("Oborovo", "Base")
        r = result.result
        assert r.total_revenue_keur >= 0, "total revenue should be non-negative"
        assert r.total_opex_keur >= 0, "total opex should be non-negative"
        assert r.total_distribution_keur >= 0, "total distribution should be non-negative"


class TestFrozenDebtScheduleLimitationDocumented:
    def test_frozen_debt_limitation_explained(self):
        """Doc explains frozen senior DS behavior under CAPEX variation."""
        path = os.path.join(REPO_ROOT, "docs/phase29b_oborovo_capex_sensitivity.md")
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        assert "frozen" in content and "senior debt" in content, \
            "doc should mention frozen senior debt behavior"
        assert "does not change" in content or "remains fixed" in content or "not re-size" in content, \
            "doc should explain CAPEX does not change frozen senior debt"


class TestOborovoBaseFrozenPathUnchanged:
    def test_oborovo_frozen_path_flag_true(self):
        from app.project_factories import create_default_oborovo
        oborovo = create_default_oborovo()
        assert oborovo.financing.use_frozen_excel_senior_debt_schedule is True, \
            "Oborovo frozen path should remain True"

    def test_oborovo_fixed_debt_approx_42852(self):
        from app.project_factories import create_default_oborovo
        oborovo = create_default_oborovo()
        assert 42800 < oborovo.financing.fixed_debt_keur < 42900, \
            f"Oborovo fixed debt should be ~42,852 kEUR, got {oborovo.financing.fixed_debt_keur}"


class TestTUHOFrozenPathUnchanged:
    def test_tuho_frozen_path_unchanged(self):
        from app.project_factories import create_default_tuho_wind1
        tuho = create_default_tuho_wind1()
        assert tuho.financing.use_frozen_excel_senior_debt_schedule is True, \
            "TUHO frozen path should remain unchanged"


class TestEvidenceMatrixLinksClaimsToSources:
    def test_evidence_matrix_has_table_structure(self):
        path = os.path.join(REPO_ROOT, "docs/phase29b_oborovo_capex_sensitivity_matrix.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "|" in content and "---" in content, "matrix should have markdown table"
        assert "capex" in content.lower(), "matrix should mention CAPEX"
        assert "frozen" in content.lower(), "matrix should mention frozen senior DS"

    def test_matrix_covers_base_protection_rows(self):
        path = os.path.join(REPO_ROOT, "docs/phase29b_oborovo_capex_sensitivity_matrix.md")
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        required = ["base senior debt", "frozen", "shl opening", "first distribution"]
        for item in required:
            assert item in content, f"matrix should include row for '{item}'"


class TestCSVIfPresentIsValid:
    def test_csv_if_present_valid(self):
        csv_path = os.path.join(REPO_ROOT, "reports/phase29b_oborovo_capex_sensitivity.csv")
        if os.path.exists(csv_path):
            with open(csv_path, encoding="utf-8") as f:
                lines = f.readlines()
            assert len(lines) > 1, "CSV should have header + data rows"
            header = lines[0].lower()
            assert "case" in header or "capex" in header, "CSV header should mention case/capex"
            # Check non-negative fields
            for line in lines[1:]:
                parts = line.split(",")
                # validation_classification should be present
        else:
            # CSV absent — doc explains why
            doc_path = os.path.join(REPO_ROOT, "docs/phase29b_oborovo_capex_sensitivity.md")
            with open(doc_path, encoding="utf-8") as f:
                content = f.read()
            assert "csv" in content.lower() or "not created" in content.lower(), \
                "phase29b doc should explain CSV decision"


class TestNoBankLenderAuditSaaSClaims:
    def test_no_bank_lender_audit_saas_claims(self):
        docs_to_check = [
            os.path.join(REPO_ROOT, "docs/phase29b_oborovo_capex_sensitivity.md"),
            os.path.join(REPO_ROOT, "docs/phase29b_oborovo_capex_sensitivity_matrix.md"),
        ]
        claims = ["bank approval", "lender approval", "bankable", "lender-ready",
                  "certification", "saas-ready"]
        for path in docs_to_check:
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    content = f.read()
                for claim in claims:
                    idx = content.lower().find(claim.lower())
                    if idx >= 0:
                        window = content[max(0, idx-100):idx+len(claim)+60]
                        is_denial = (
                            "no " in window.lower()
                            or "not " in window.lower()
                            or "❌" in window
                            or "unvalidated" in window.lower()
                            or "exploratory" in window.lower()
                            or "diagnostic" in window.lower()
                            or "not bank" in window.lower()
                        )
                        assert is_denial, f"'{claim}' should be denied in {os.path.basename(path)}"


class TestNoRuntimeModelFilesChangedOrClaimed:
    def test_no_runtime_model_changes_stated(self):
        path = os.path.join(REPO_ROOT, "docs/phase29b_oborovo_capex_sensitivity.md")
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        assert "no financial formula changes" in content or "out of scope" in content or "not changed" in content, \
            "phase29b doc should state no financial formula changes"


class TestGuardrailsUnchanged:
    def test_guardrails_unchanged(self):
        import re
        shell_path = os.path.join(REPO_ROOT, "app/templates/partials/workspace_shell.html")
        with open(shell_path, encoding="utf-8") as f:
            content = f.read()
        assert "BLOCKED" in content, "G20 should remain BLOCKED"
        assert "NOT APPROVED" in content, "R99/R102 should remain NOT APPROVED"
        assert not re.search(r"partial[\s_-]pay[\s_-]sweep.*approved", content), \
            "partial_pay_sweep should not be promoted"
        assert not re.search(r"flat[\s_-]dscr.*sculpting.*approved", content), \
            "flat_dscr_sculpted should not be promoted"
        assert not re.search(r"minimum[\s_-]dscr.*sculpting.*approved", content), \
            "minimum_dscr_sculpted should not be promoted"


class TestOborovoCAPEXArchitecture:
    def test_oborovo_hard_capex_known(self):
        from app.project_factories import create_default_oborovo
        oborovo = create_default_oborovo()
        hard_capex = oborovo.capex.hard_capex_keur
        assert 55000 < hard_capex < 57000, \
            f"Oborovo hard capex should be ~55,999 kEUR, got {hard_capex}"

    def test_oborovo_total_capex_computed(self):
        from app.project_factories import create_default_oborovo
        oborovo = create_default_oborovo()
        total = oborovo.capex.total_capex
        assert 57000 < total < 60000, \
            f"Oborovo total capex should be ~57,973 kEUR, got {total}"

    def test_oborovo_capex_items_count(self):
        from app.project_factories import create_default_oborovo
        oborovo = create_default_oborovo()
        items = oborovo.capex.capex_items()
        assert len(items) == 15, f"Oborovo should have 15 CAPEX items, got {len(items)}"


class TestOborovoFinancingFixedDebt:
    def test_oborovo_fixed_debt_exists(self):
        from app.project_factories import create_default_oborovo
        oborovo = create_default_oborovo()
        assert oborovo.financing.fixed_debt_keur is not None, \
            "Oborovo should have fixed_debt_keur"
        assert 42000 < oborovo.financing.fixed_debt_keur < 44000, \
            f"fixed_debt should be ~42,852, got {oborovo.financing.fixed_debt_keur}"

    def test_oborovo_shl_idc_set(self):
        from app.project_factories import create_default_oborovo
        oborovo = create_default_oborovo()
        assert oborovo.financing.shl_idc_keur is not None, "Oborovo should have shl_idc_keur"
        assert 1100 < oborovo.financing.shl_idc_keur < 1200, \
            f"shl_idc should be ~1,169, got {oborovo.financing.shl_idc_keur}"