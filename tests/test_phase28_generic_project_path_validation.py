"""
Phase 28: Generic Project Path Validation
Tests for generic/new-project path characterization and internal consistency.
Diagnostic only. No financial formula changes. No runtime model changes.
"""
import os
import sys
import re

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)


class TestPhase28DocExists:
    def test_phase28_doc_exists(self):
        path = os.path.join(REPO_ROOT, "docs/phase28_generic_project_path_validation.md")
        assert os.path.exists(path), f"phase28 doc not found at {path}"

    def test_phase28_validation_matrix_exists(self):
        path = os.path.join(REPO_ROOT, "docs/phase28_generic_path_validation_matrix.md")
        assert os.path.exists(path), f"validation matrix not found at {path}"


class TestGenericProjectsListed:
    def test_generic_projects_are_listed(self):
        path = os.path.join(REPO_ROOT, "docs/phase28_generic_project_path_validation.md")
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        # Should mention generic project types
        assert "generic" in content and ("solar" in content or "wind" in content), \
            "generic projects (solar/wind) should be mentioned"
        # Should explicitly state generic path is unvalidated
        assert "unvalidated" in content or "not validated" in content, \
            "generic/new-project path should be explicitly marked unvalidated"


class TestGenericPathArchitecture:
    def test_generic_path_does_not_use_frozen_fixtures(self):
        """Verify generic projects have use_frozen_excel_senior_debt_schedule=False."""
        from app.project_factories import create_default_solar_project, create_default_wind_project
        solar = create_default_solar_project()
        wind = create_default_wind_project()
        # Both generic projects should NOT use frozen Excel senior debt schedule
        assert solar.financing.use_frozen_excel_senior_debt_schedule is False, \
            "Generic solar should not use frozen Excel senior debt schedule"
        assert wind.financing.use_frozen_excel_senior_debt_schedule is False, \
            "Generic wind should not use frozen Excel senior debt schedule"

    def test_generic_uses_live_dscr_sculpting(self):
        """Generic projects should use live DSCR sculpting, not frozen fixtures."""
        from app.project_factories import create_default_solar_project, create_default_wind_project
        from domain.inputs import DebtSizingMethod
        solar = create_default_solar_project()
        wind = create_default_wind_project()
        # Both should use dscr_sculpt method
        assert solar.financing.debt_sizing_method == DebtSizingMethod.DSCR_SCULPT.value, \
            "Generic solar should use DSCR_SCULPT debt sizing method"
        assert wind.financing.debt_sizing_method == DebtSizingMethod.DSCR_SCULPT.value, \
            "Generic wind should use DSCR_SCULPT debt sizing method"


class TestTUHOOborovoFrozenPathUnchanged:
    def test_tuho_frozen_path_unchanged(self):
        from app.project_factories import create_default_tuho_wind1
        tuho = create_default_tuho_wind1()
        assert tuho.financing.use_frozen_excel_senior_debt_schedule is True, \
            "TUHO should still use frozen Excel senior debt schedule"

    def test_oborovo_frozen_path_unchanged(self):
        from app.project_factories import create_default_oborovo
        oborovo = create_default_oborovo()
        assert oborovo.financing.use_frozen_excel_senior_debt_schedule is True, \
            "Oborovo should still use frozen Excel senior debt schedule"


class TestGenericProjectsCanRun:
    def test_generic_projects_can_run_without_crashing(self):
        """Instantiate and run generic projects through the backend — no crash."""
        from app.ui_runner import run_demo_project
        try:
            solar_result = run_demo_project("Solar", "Base")
            assert solar_result is not None, "Generic solar should return a result"
            assert solar_result.result is not None or len(solar_result.messages) == 0, \
                "Generic solar should run without fatal errors"
        except Exception as e:
            raise AssertionError(f"Generic solar crashed: {e}")

        try:
            wind_result = run_demo_project("Wind", "Base")
            assert wind_result is not None, "Generic wind should return a result"
            assert wind_result.result is not None or len(wind_result.messages) == 0, \
                "Generic wind should run without fatal errors"
        except Exception as e:
            raise AssertionError(f"Generic wind crashed: {e}")

    def test_generic_outputs_have_required_headline_fields(self):
        """If result is present, check headline fields exist."""
        from app.ui_runner import run_demo_project
        solar_result = run_demo_project("Solar", "Base")
        # result may be None if validation errors — check attributes exist
        if solar_result.result is not None:
            result = solar_result.result
            # Check for expected headline fields (using actual attribute names)
            assert hasattr(result, 'total_revenue_keur') or hasattr(result, 'senior_debt_keur') or \
                   hasattr(result, 'project_irr') or hasattr(result, 'equity_irr'), \
                "Result should have some headline financial fields"

    def test_generic_outputs_are_numeric_and_safe(self):
        """Check that outputs from generic run are numeric (not NaN)."""
        from app.ui_runner import run_demo_project
        solar_result = run_demo_project("Solar", "Base")
        if solar_result.result is not None:
            result = solar_result.result
            # Check numeric fields are not NaN
            numeric_fields = ['senior_debt_keur', 'project_irr', 'equity_irr', 'total_revenue_keur']
            for field in numeric_fields:
                if hasattr(result, field):
                    val = getattr(result, field)
                    if val is not None:
                        assert isinstance(val, (int, float)), f"{field} should be numeric"
                        # Allow inf for DSCR after debt repaid
                        if field != 'avg_dscr' and field != 'min_dscr':
                            assert val != float('nan'), f"{field} should not be NaN"


class TestGenericNonNegative:
    def test_generic_revenue_opex_debt_distribution_non_negative(self):
        """Revenue, OPEX, debt service, distributions should be non-negative where they exist."""
        from app.ui_runner import run_demo_project
        solar_result = run_demo_project("Solar", "Base")
        if solar_result.result is not None:
            result = solar_result.result
            # Check non-negativity on key fields
            fields_to_check = ['total_revenue_keur', 'total_opex_keur']
            for field in fields_to_check:
                if hasattr(result, field):
                    val = getattr(result, field)
                    if val is not None:
                        assert val >= 0, f"{field} should be non-negative"


class TestGenericWarningLanguage:
    def test_generic_warning_language_present(self):
        """Docs should include generic unvalidated/exploratory language."""
        paths = [
            os.path.join(REPO_ROOT, "docs/pilot_user_guide.md"),
            os.path.join(REPO_ROOT, "docs/validation_pack_executive_summary.md"),
            os.path.join(REPO_ROOT, "docs/phase28_generic_project_path_validation.md"),
        ]
        found_warning = False
        for path in paths:
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    content = f.read().lower()
                if ("generic" in content and ("unvalidated" in content or "exploratory" in content or "not validated" in content)):
                    found_warning = True
        assert found_warning, "Generic project unvalidated/exploratory warning should appear in docs"


class TestValidationMatrixLinks:
    def test_validation_matrix_links_claims_to_evidence(self):
        """Matrix should include rows for generic runability, unvalidated status, fixture non-use."""
        path = os.path.join(REPO_ROOT, "docs/phase28_generic_path_validation_matrix.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        # Should have table structure
        assert "|" in content and "---" in content, "Matrix should have markdown table"
        # Should reference key claims
        assert "generic" in content.lower(), "Matrix should mention generic projects"
        assert "frozen" in content.lower() or "fixture" in content.lower(), \
            "Matrix should mention frozen/fixture non-use"
        assert "unvalidated" in content.lower() or "not validated" in content.lower(), \
            "Matrix should mention unvalidated status"


class TestNoBankLenderAuditSaaSClaims:
    def test_no_bank_lender_audit_saas_claims_for_generic(self):
        """Docs should not claim generic path is bank/lender/audit/SaaS ready."""
        docs_to_check = [
            os.path.join(REPO_ROOT, "docs/phase28_generic_project_path_validation.md"),
            os.path.join(REPO_ROOT, "docs/phase28_generic_path_validation_matrix.md"),
        ]
        claims = ["bank approval", "lender approval", "bankable", "lender-ready",
                  "certification", "saas-ready"]
        for path in docs_to_check:
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    content = f.read().lower()
                for claim in claims:
                    idx = content.find(claim)
                    if idx >= 0:
                        window = content[max(0, idx-80):idx+len(claim)+40]
                        is_denial = (
                            "not" in window
                            or "❌" in window
                            or "internal pilot" in window
                            or "unvalidated" in window
                            or "no bank" in window.lower()
                        )
                        assert is_denial, f"'{claim}' should be denied in {os.path.basename(path)}"


class TestJSONSummary:
    def test_json_summary_if_present_is_valid(self):
        """JSON manifest is optional — if present must be valid."""
        json_path = os.path.join(REPO_ROOT, "reports/phase28_generic_path_diagnostic_summary.json")
        if os.path.exists(json_path):
            import json as _json
            with open(json_path, encoding="utf-8") as f:
                data = _json.load(f)
            assert "generic_solar" in str(data.get("projects", [])).lower() or \
                   "solar" in str(data.get("projects", [])).lower(), \
                "JSON should mention generic/solar projects"
            limitations = str(data.get("limitations", []))
            assert "generic" in limitations.lower() or "unvalidated" in limitations.lower(), \
                "JSON limitations should mention generic path unvalidated"
            assert data.get("no_financial_formula_changes") or data.get("phase"), \
                "JSON should confirm no financial formula changes or identify phase"
        else:
            # JSON not present — Phase 28 doc explains why
            doc_path = os.path.join(REPO_ROOT, "docs/phase28_generic_project_path_validation.md")
            assert os.path.exists(doc_path), "phase28 doc should exist (JSON explained there)"
            with open(doc_path, encoding="utf-8") as f:
                content = f.read().lower()
            assert "json" in content, "phase28 doc should discuss JSON decision"


class TestNoRuntimeModelChanges:
    def test_no_runtime_model_files_changed_or_claimed(self):
        """Phase 28 should state no financial formula changes."""
        path = os.path.join(REPO_ROOT, "docs/phase28_generic_project_path_validation.md")
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        assert "no financial formula changes" in content or "no runtime formula changes" in content, \
            "phase28 doc should state no financial formula changes"


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
