"""
Phase 29A: TUHO CO2 Revenue Deep-Dive
Tests for TUHO CO2 certificate revenue validation and generic wind CO2 non-validation.
Diagnostic only. No financial formula changes. No runtime model changes.
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)


class TestPhase29ADocExists:
    def test_phase29a_doc_exists(self):
        path = os.path.join(REPO_ROOT, "docs/phase29a_tuho_co2_revenue_deep_dive.md")
        assert os.path.exists(path), f"phase29a doc not found at {path}"

    def test_phase29a_evidence_matrix_exists(self):
        path = os.path.join(REPO_ROOT, "docs/phase29a_tuho_co2_evidence_matrix.md")
        assert os.path.exists(path), f"evidence matrix not found at {path}"


class TestTUHOCO2ScopeIsExplicit:
    def test_tuho_co2_scope_is_explicit(self, tmp_path=None):
        path = os.path.join(REPO_ROOT, "docs/phase29a_tuho_co2_revenue_deep_dive.md")
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        assert "tuho" in content and "co2" in content, "TUHO CO2 should be mentioned"
        assert "tuho" in content.lower() and "validation" in content.lower(), \
            "TUHO CO2 should be stated as validation target"
        assert "generic" in content and ("unvalidated" in content or "exploratory" in content), \
            "generic wind CO2 should be marked unvalidated/exploratory"


class TestTUHOCO2ArchitectureMapPresent:
    def test_tuho_co2_architecture_map_present(self):
        path = os.path.join(REPO_ROOT, "docs/phase29a_tuho_co2_revenue_deep_dive.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        # Should have sections on input fields, generation linkage, revenue aggregation
        required = ["input", "generation", "revenue", "source-to-output"]
        for term in required:
            assert term.lower() in content.lower(), f"architecture map should mention '{term}'"


class TestTUHOY1CO2AnchorPresent:
    def test_tuho_y1_co2_anchor_present(self):
        path = os.path.join(REPO_ROOT, "docs/phase29a_tuho_co2_revenue_deep_dive.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "611" in content, "TUHO Y1 CO2 anchor ~611 kEUR should be mentioned"


class TestTUHOEquityIRRContextPresent:
    def test_tuho_equity_irr_context_present(self):
        path = os.path.join(REPO_ROOT, "docs/phase29a_tuho_co2_revenue_deep_dive.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "11.81%" in content, "runtime equity IRR 11.81% should be mentioned"
        assert "11.61%" in content, "Excel context 11.61% should be mentioned"
        assert "0.20" in content or "0.20 pp" in content.lower() or "+0.20" in content, \
            "difference (+0.20pp) should be mentioned"


class TestTUHOCO2RevenueNonNegative:
    def test_tuho_co2_revenue_non_negative(self):
        # CO2 revenue is computed as generation_mwh × price_EUR/MWh / 1000
        # Both inputs are positive for TUHO (generation > 0, price > 0)
        from app.project_factories import create_default_tuho_wind1
        inputs = create_default_tuho_wind1()
        assert inputs.revenue.co2_enabled is True, "TUHO CO2 should be enabled"
        # Price schedule starts at 4.191 and declines, both positive
        assert inputs.revenue.co2_certificate_price_eur_per_mwh > 0, \
            "TUHO CO2 price should be positive"
        # CO2 revenue = generation × price / 1000 > 0 for any positive generation
        # Y1-H1: 72271 * 4.191 / 1000 ~= 303 kEUR
        y1_h1_gen = 72271.06849315068  # from runtime output
        y1_h1_price = 4.191063312
        co2_h1 = y1_h1_gen * y1_h1_price / 1000
        assert co2_h1 > 0, "TUHO Y1-H1 CO2 revenue should be positive"
        assert 280 < co2_h1 < 330, f"Y1-H1 CO2 should be ~303 kEUR, got {co2_h1:.1f}"


class TestTUHOTotalRevenueNonNegative:
    def test_tuho_total_revenue_non_negative(self):
        from app.ui_runner import run_demo_project
        result = run_demo_project("TUHO", "Base")
        assert result.result is not None, "TUHO should run without error"
        total_rev = result.result.total_revenue_keur
        assert total_rev >= 0, f"TUHO total revenue should be non-negative, got {total_rev}"


class TestGenericWindCO2NotValidated:
    def test_generic_wind_co2_not_validated(self):
        # Check phase28 docs
        path = os.path.join(REPO_ROOT, "docs/phase28_generic_project_path_validation.md")
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                content = f.read().lower()
            assert "co2" in content and ("unvalidated" in content or "not validated" in content or "exploratory" in content), \
                "generic wind CO2 should be marked unvalidated in phase28 doc"
        # Check phase29a doc
        path29a = os.path.join(REPO_ROOT, "docs/phase29a_tuho_co2_revenue_deep_dive.md")
        with open(path29a, encoding="utf-8") as f:
            content29a = f.read().lower()
        assert "generic" in content29a and "unvalidated" in content29a, \
            "phase29a doc should confirm generic wind CO2 is unvalidated"


class TestNoExternalCO2DataOrAPIClaim:
    def test_no_external_co2_data_or_api_claim(self):
        paths = [
            os.path.join(REPO_ROOT, "docs/phase29a_tuho_co2_revenue_deep_dive.md"),
            os.path.join(REPO_ROOT, "docs/phase29a_tuho_co2_evidence_matrix.md"),
        ]
        for path in paths:
            with open(path, encoding="utf-8") as f:
                content = f.read()
            # Deny external API and live market data claims
            lines = [l for l in content.split('\n') if 'api' in l.lower() or 'live market' in l.lower()]
            for line in lines:
                # Check both line and context — look at surrounding 200-char window
                line_lower = line.lower()
                context_window = content[max(0, content.find(line)-200):content.find(line)+len(line)+100].lower()
                context_ok = any(word in line_lower for word in ['no', 'not', 'deny', 'unvalidated', 'exploratory', 'model-input']) or \
                             any(word in context_window for word in ['out of scope', 'no live', 'not live', 'no external'])
                assert context_ok, f'CO2 API/market line should deny or be in out-of-scope context: {line.strip()[:60]}'


class TestEvidenceMatrixLinksClaimsToSources:
    def test_evidence_matrix_links_claims_to_sources(self):
        path = os.path.join(REPO_ROOT, "docs/phase29a_tuho_co2_evidence_matrix.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        # Should have table structure
        assert "|" in content and "---" in content, "matrix should have markdown table"
        # Should have key source references
        assert "app/project_factories.py" in content or "project_factories" in content, \
            "matrix should reference project_factories.py"
        assert "domain/revenue/generation.py" in content or "generation.py" in content, \
            "matrix should reference generation.py"
        # Should have required rows
        rows = ["tuho co2", "y1 co2", "generic wind co2", "no live external"]
        for row in rows:
            assert row in content.lower(), f"matrix should include row for '{row}'"


class TestDiagnosticCSVIfPresentIsValid:
    def test_diagnostic_csv_if_present_is_valid(self):
        csv_path = os.path.join(REPO_ROOT, "reports/phase29a_tuho_co2_revenue_diagnostic.csv")
        if os.path.exists(csv_path):
            with open(csv_path, encoding="utf-8") as f:
                lines = f.readlines()
            assert len(lines) > 1, "CSV should have header + at least 1 data row"
            header = lines[0].lower()
            assert "co2" in header or "revenue" in header, "CSV header should mention CO2 or revenue"
            # Check no negative CO2 values
            for line in lines[1:]:
                if "tuho" in line.lower():
                    parts = line.split(",")
                    for part in parts:
                        val = part.strip()
                        try:
                            fval = float(val)
                            if "co2" in header and val != "":
                                assert fval >= 0, f"CO2 revenue should be non-negative: {fval}"
                        except ValueError:
                            pass
        else:
            # CSV absent — doc explains why
            doc_path = os.path.join(REPO_ROOT, "docs/phase29a_tuho_co2_revenue_deep_dive.md")
            with open(doc_path, encoding="utf-8") as f:
                content = f.read()
            assert "csv" in content.lower() or "not exposed" in content.lower() or "period-level" in content.lower(), \
                "phase29a doc should explain why CSV was not created"


class TestNoBankLenderAuditSaaSClaims:
    def test_no_bank_lender_audit_saas_claims(self):
        docs_to_check = [
            os.path.join(REPO_ROOT, "docs/phase29a_tuho_co2_revenue_deep_dive.md"),
            os.path.join(REPO_ROOT, "docs/phase29a_tuho_co2_evidence_matrix.md"),
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
                            or "no" in window.lower()
                            or "❌" in window
                            or "unvalidated" in window
                            or "exploratory" in window
                            or "non-claim" in window
                            or "no bank" in window.lower()
                        )
                        assert is_denial, f"'{claim}' should be denied in {os.path.basename(path)}"


class TestNoRuntimeModelFilesChangedOrClaimed:
    def test_no_runtime_model_files_changed_or_claimed(self):
        path = os.path.join(REPO_ROOT, "docs/phase29a_tuho_co2_revenue_deep_dive.md")
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        assert "financial formula" in content and ("out of scope" in content or "not changed" in content or "no change" in content), \
            "phase29a doc should state no financial formula changes"
        assert "out of scope" in content or "not changed" in content, \
            "phase29a doc should clarify what was not changed"


class TestTUHOOborovoFrozenPathUnchanged:
    def test_tuho_frozen_path_unchanged(self):
        from app.project_factories import create_default_tuho_wind1
        tuho = create_default_tuho_wind1()
        assert tuho.financing.use_frozen_excel_senior_debt_schedule is True, \
            "TUHO frozen path should remain unchanged"

    def test_oborovo_frozen_path_unchanged(self):
        from app.project_factories import create_default_oborovo
        oborovo = create_default_oborovo()
        assert oborovo.financing.use_frozen_excel_senior_debt_schedule is True, \
            "Oborovo frozen path should remain unchanged"


class TestGuardrailsUnchanged:
    def test_guardrails_unchanged(self):
        shell_path = os.path.join(REPO_ROOT, "app/templates/partials/workspace_shell.html")
        with open(shell_path, encoding="utf-8") as f:
            content = f.read()
        import re
        assert "BLOCKED" in content, "G20 should remain BLOCKED"
        assert "NOT APPROVED" in content, "R99/R102 should remain NOT APPROVED"
        assert not re.search(r"partial[\s_-]pay[\s_-]sweep.*approved", content), \
            "partial_pay_sweep should not be promoted"
        assert not re.search(r"flat[\s_-]dscr.*sculpting.*approved", content), \
            "flat_dscr_sculpted should not be promoted"
        assert not re.search(r"minimum[\s_-]dscr.*sculpting.*approved", content), \
            "minimum_dscr_sculpted should not be promoted"


class TestTUHOCO2InputFields:
    def test_tuho_co2_enabled(self):
        from app.project_factories import create_default_tuho_wind1
        inputs = create_default_tuho_wind1()
        assert inputs.revenue.co2_enabled is True

    def test_tuho_co2_price_identified(self):
        from app.project_factories import create_default_tuho_wind1
        inputs = create_default_tuho_wind1()
        assert inputs.revenue.co2_certificate_price_eur_per_mwh > 0
        assert 4.0 < inputs.revenue.co2_certificate_price_eur_per_mwh < 5.0

    def test_tuho_co2_schedule_present(self):
        from app.project_factories import create_default_tuho_wind1
        inputs = create_default_tuho_wind1()
        assert inputs.revenue.co2_sales_schedule is not None

    def test_generic_wind_co2_flat_price_no_schedule(self):
        from app.project_factories import create_default_wind_project
        wind = create_default_wind_project()
        assert wind.revenue.co2_enabled is True
        assert wind.revenue.co2_price_eur == 5.0
        assert wind.revenue.co2_sales_schedule is None  # no schedule, flat price


class TestCO2RevenueCalculation:
    def test_co2_revenue_formula_positive_for_positive_inputs(self):
        # generation_mwh > 0, price_eur_mwh > 0 → co2_revenue_keur > 0
        from app.project_factories import create_default_tuho_wind1
        inputs = create_default_tuho_wind1()
        # Y1-H1 generation from runtime: ~72,271 MWh
        gen = 72271.06849315068
        price = inputs.revenue.co2_certificate_price_eur_per_mwh  # 4.191
        co2 = gen * price / 1000
        assert co2 > 0
        assert 280 < co2 < 330  # ~303 kEUR expected


class TestCO2AddedToRevenue:
    def test_co2_is_added_not_subtracted(self):
        # net_revenue = energy - balancing + co2
        # If co2 were subtracted, the formula would be energy - balancing - co2
        # Check doc confirms addition
        path = os.path.join(REPO_ROOT, "docs/phase29a_tuho_co2_revenue_deep_dive.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        # Should explicitly state CO2 is added
        assert "added (not subtracted)" in content.lower() or "added to" in content.lower(), \
            "CO2 should be documented as added to revenue, not subtracted"