"""Phase C3 — U1 Integration tests.

Proves that C3 Gross Fixed Assets / Net Fixed Assets now consume
ProjectFinancingResult.book_depreciable_asset_basis as the ONLY financial authority.

§12 Required negative tests:
1. C3 GFA changes when canonical BookDepreciableAssetBasis legitimately changes.
2. C3 does NOT independently read raw IDC for GFA.
3. C3 does NOT independently read raw commitment-fee accrual for GFA.
4. construction_financing=None does not make Solar/Wind GFA unavailable.
5. Missing book_depreciable_asset_basis fails closed truthfully.
6. No project identity dispatch determines GFA.
7. No residual/balancing GFA component exists.

§13 Four-project matrix: basis authority, GFA, cumulative depreciation, NFA, statuses.
"""
from __future__ import annotations

import dataclasses

import pytest


def _run_and_assemble(ptype: str):
    import app.project_factories as pf
    from app.services.production_financial_authority import run_clean_production
    from financial_engine.financial_statements import (
        assemble_decision_complete_financial_statements,
    )
    factories = {
        "Solar": pf.create_default_solar_project,
        "Wind": pf.create_default_wind_project,
        "Oborovo": pf.create_default_oborovo,
        "TUHO": pf.create_default_tuho_wind1,
    }
    pi = factories[ptype]()
    run = run_clean_production(pi, project_type=ptype)
    fs = assemble_decision_complete_financial_statements(run.g2c_result, pi)
    return run, fs


# ---------------------------------------------------------------------------
# §13 — Four-project matrix
# ---------------------------------------------------------------------------

class TestU1_FourProjectMatrix:
    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_canonical_basis_available(self, ptype):
        """All four projects expose a non-None canonical BookDepreciableAssetBasis after U1."""
        from financial_engine.financial_statements.contracts import StatementStatus
        _, fs = _run_and_assemble(ptype)
        assert fs.fixed_asset_status == StatementStatus.OK, (
            f"{ptype}: expected GFA OK after U1 integration, got {fs.fixed_asset_status}"
        )

    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_canonical_gfa_positive(self, ptype):
        """Canonical GFA is positive for all four projects."""
        _, fs = _run_and_assemble(ptype)
        report = fs.accounting_policies.provenance.get("gfa_report", {})
        gfa = report.get("canonical_book_gfa_keur")
        assert gfa is not None and gfa > 0, f"{ptype}: expected positive canonical GFA, got {gfa}"

    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_nfa_available_and_positive_initially(self, ptype):
        """NFA is available and positive in the first operating period."""
        from financial_engine.financial_statements.contracts import StatementStatus
        _, fs = _run_and_assemble(ptype)
        assert fs.fixed_asset_status == StatementStatus.OK
        nfa_values = [
            p.net_fixed_assets_keur for p in fs.fixed_asset_periods
            if p.net_fixed_assets_keur is not None
        ]
        assert len(nfa_values) > 0, f"{ptype}: expected at least one non-None NFA period"
        assert nfa_values[0] > 0, f"{ptype}: initial NFA must be positive"

    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_nfa_identity_all_periods(self, ptype):
        """NFA_t = GFA - cumulative_book_depreciation_t for all periods."""
        _, fs = _run_and_assemble(ptype)
        for p in fs.fixed_asset_periods:
            if p.gross_fixed_assets_keur is not None and p.net_fixed_assets_keur is not None:
                expected = p.gross_fixed_assets_keur - p.accumulated_book_depreciation_keur
                assert abs(p.net_fixed_assets_keur - expected) < 1e-3, (
                    f"{ptype} period {p.period_index}: NFA identity violated "
                    f"({p.net_fixed_assets_keur:.6f} != {expected:.6f})"
                )

    @pytest.mark.parametrize("ptype", ("Solar", "Wind"))
    def test_solar_wind_use_generic_basis(self, ptype):
        """Solar/Wind use GENERIC_CAPEX_STRUCTURE_BOOK_BASIS — not blocked by absent cfin."""
        _, fs = _run_and_assemble(ptype)
        report = fs.accounting_policies.provenance.get("gfa_report", {})
        assert report.get("canonical_book_basis_authority") == "GENERIC_CAPEX_STRUCTURE_BOOK_BASIS", (
            f"{ptype}: expected GENERIC_CAPEX_STRUCTURE_BOOK_BASIS, "
            f"got {report.get('canonical_book_basis_authority')}"
        )

    @pytest.mark.parametrize("ptype", ("Oborovo", "TUHO"))
    def test_oborovo_tuho_use_typed_basis(self, ptype):
        """Oborovo/TUHO use TYPED_CONSTRUCTION_FINANCING_RESULT_BOOK_BASIS."""
        _, fs = _run_and_assemble(ptype)
        report = fs.accounting_policies.provenance.get("gfa_report", {})
        assert report.get("canonical_book_basis_authority") == "TYPED_CONSTRUCTION_FINANCING_RESULT_BOOK_BASIS", (
            f"{ptype}: expected TYPED_CONSTRUCTION_FINANCING_RESULT_BOOK_BASIS, "
            f"got {report.get('canonical_book_basis_authority')}"
        )

    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_canonical_gfa_report_structure(self, ptype):
        """gfa_report must contain the three canonical keys for all four projects."""
        _, fs = _run_and_assemble(ptype)
        report = fs.accounting_policies.provenance.get("gfa_report", {})
        assert "canonical_book_gfa_keur" in report, f"{ptype}: missing canonical_book_gfa_keur"
        assert "canonical_book_basis_authority" in report, f"{ptype}: missing canonical_book_basis_authority"
        assert "canonical_book_basis_components" in report, f"{ptype}: missing canonical_book_basis_components"
        components = report["canonical_book_basis_components"]
        assert isinstance(components, list) and len(components) > 0, (
            f"{ptype}: canonical_book_basis_components must be non-empty list"
        )

    @pytest.mark.parametrize("ptype", ("Solar", "Wind", "Oborovo", "TUHO"))
    def test_canonical_gfa_equals_component_sum(self, ptype):
        """canonical_book_gfa_keur == sum of all component amounts."""
        _, fs = _run_and_assemble(ptype)
        report = fs.accounting_policies.provenance.get("gfa_report", {})
        gfa = report.get("canonical_book_gfa_keur", 0.0)
        components = report.get("canonical_book_basis_components", [])
        component_sum = sum(c["amount_keur"] for c in components)
        assert abs(gfa - component_sum) < 1e-6, (
            f"{ptype}: canonical_book_gfa_keur ({gfa:.6f}) != component sum ({component_sum:.6f})"
        )


# ---------------------------------------------------------------------------
# §12.1 — GFA changes when canonical basis changes
# ---------------------------------------------------------------------------

class TestU1_GFASensitivity:
    def test_gfa_changes_when_basis_changes(self):
        """C3 GFA changes when canonical BookDepreciableAssetBasis legitimately changes."""
        from app.project_factories import create_default_oborovo
        from app.services.production_financial_authority import run_clean_production
        from financial_engine.financial_statements import (
            assemble_decision_complete_financial_statements,
        )
        from finco_core.inputs.book_depreciable_asset_basis import (
            BookDepreciableAssetBasis, BookDepreciableAssetComponent,
        )
        pi = create_default_oborovo()
        run = run_clean_production(pi, project_type="Oborovo")
        fs_baseline = assemble_decision_complete_financial_statements(run.g2c_result, pi)
        baseline_gfa = fs_baseline.accounting_policies.provenance.get(
            "gfa_report", {}
        ).get("canonical_book_gfa_keur")
        assert baseline_gfa is not None and baseline_gfa > 0

        synthetic_basis = BookDepreciableAssetBasis(
            components=(BookDepreciableAssetComponent(
                code="test_capex",
                name="Test CAPEX",
                amount_keur=12345.0,
                asset_class_code="tangible_assets",
                useful_life_override=20,
                provenance="TEST",
            ),),
            authority="TEST_BASIS",
        )
        modified_fin = dataclasses.replace(
            run.g2c_result.financing_result,
            book_depreciable_asset_basis=synthetic_basis,
        )
        modified_g2c = dataclasses.replace(run.g2c_result, financing_result=modified_fin)
        fs_modified = assemble_decision_complete_financial_statements(modified_g2c, pi)
        modified_gfa = fs_modified.accounting_policies.provenance.get(
            "gfa_report", {}
        ).get("canonical_book_gfa_keur")
        assert abs(modified_gfa - 12345.0) < 1e-3, (
            f"C3 GFA must equal synthetic basis total 12345.0, got {modified_gfa}"
        )
        assert abs(baseline_gfa - modified_gfa) > 100.0, (
            "C3 GFA must change when canonical basis changes"
        )


# ---------------------------------------------------------------------------
# §12.2-§12.3 — No direct raw CFR field reads for GFA
# ---------------------------------------------------------------------------

class TestU1_NoDirectCfrReading:
    def test_c3_does_not_use_commitment_fee_accrual_for_gfa(self):
        """assembly.py must not contain senior_commitment_fee_accrual_keur (removed by U1)."""
        import inspect
        from financial_engine.financial_statements import assembly as asm
        src = inspect.getsource(asm)
        assert "senior_commitment_fee_accrual_keur" not in src, (
            "senior_commitment_fee_accrual_keur must not appear in assembly.py "
            "(old parallel GFA code eliminated by U1 integration)"
        )

    def test_gfa_keur_sourced_only_from_canonical_basis(self):
        """gfa_keur must be set from canonical basis.total_keur, not from cfin field sums."""
        import inspect
        from financial_engine.financial_statements import assembly as asm
        src = inspect.getsource(asm)
        assert "gfa_keur = basis.total_keur" in src, (
            "gfa_keur must be assigned exclusively from canonical basis.total_keur"
        )

    def test_audit_raw_idc_is_non_authoritative(self):
        """Raw IDC in gfa_report.audit must be marked non_authoritative=True."""
        _, fs = _run_and_assemble("TUHO")
        report = fs.accounting_policies.provenance.get("gfa_report", {})
        audit = report.get("audit", {})
        if audit:
            assert audit.get("non_authoritative") is True, (
                "gfa_report.audit must be marked non_authoritative=True"
            )


# ---------------------------------------------------------------------------
# §12.4 — construction_financing=None does not block Solar/Wind GFA
# ---------------------------------------------------------------------------

class TestU1_SolarWindGfaAvailable:
    @pytest.mark.parametrize("ptype", ("Solar", "Wind"))
    def test_solar_wind_gfa_available_without_cfin(self, ptype):
        """Solar/Wind have no construction_financing but GFA is AVAILABLE via generic basis."""
        from financial_engine.financial_statements.contracts import StatementStatus
        _, fs = _run_and_assemble(ptype)
        assert fs.fixed_asset_status == StatementStatus.OK, (
            f"{ptype}: GFA must be AVAILABLE even with construction_financing=None"
        )
        report = fs.accounting_policies.provenance.get("gfa_report", {})
        assert report.get("canonical_book_gfa_keur") is not None
        assert "gross_fixed_assets" not in fs.unavailable_reasons, (
            f"{ptype}: gross_fixed_assets must not be in unavailable_reasons after U1"
        )


# ---------------------------------------------------------------------------
# §12.5 — Missing basis fails closed truthfully
# ---------------------------------------------------------------------------

class TestU1_MissingBasisFailsClosed:
    def test_missing_basis_produces_unavailable_status(self):
        """When book_depreciable_asset_basis is None, GFA is BOOK_CAPITALIZATION_BASIS_UNAVAILABLE."""
        from app.project_factories import create_default_oborovo
        from app.services.production_financial_authority import run_clean_production
        from financial_engine.financial_statements import (
            assemble_decision_complete_financial_statements,
            StatementStatus,
        )
        pi = create_default_oborovo()
        run = run_clean_production(pi, project_type="Oborovo")
        modified_fin = dataclasses.replace(
            run.g2c_result.financing_result,
            book_depreciable_asset_basis=None,
        )
        modified_g2c = dataclasses.replace(run.g2c_result, financing_result=modified_fin)
        fs = assemble_decision_complete_financial_statements(modified_g2c, pi)
        assert fs.fixed_asset_status == StatementStatus.BOOK_CAPITALIZATION_BASIS_UNAVAILABLE, (
            f"Missing basis must produce BOOK_CAPITALIZATION_BASIS_UNAVAILABLE, got {fs.fixed_asset_status}"
        )
        assert "gross_fixed_assets" in fs.unavailable_reasons
        reason = fs.unavailable_reasons["gross_fixed_assets"]
        assert "CANONICAL_BOOK_BASIS_UNAVAILABLE" in reason, (
            f"Unavailable reason must say CANONICAL_BOOK_BASIS_UNAVAILABLE, got: {reason}"
        )


# ---------------------------------------------------------------------------
# §12.6 — No project identity dispatch
# ---------------------------------------------------------------------------

class TestU1_NoProjectDispatch:
    def test_no_project_identity_dispatch_in_assembly(self):
        """assembly.py must not dispatch on project name/code in executable code for GFA."""
        import ast
        import inspect
        from financial_engine.financial_statements import assembly as asm
        src = inspect.getsource(asm)
        tree = ast.parse(src)
        forbidden = {"Oborovo", "TUHO", "Solar", "Wind", "project_code", "project_name"}

        class NameDispatchVisitor(ast.NodeVisitor):
            found: list = []
            def visit_Constant(self, node):
                if isinstance(node.value, str) and node.value in forbidden:
                    self.found.append(node.value)
                self.generic_visit(node)
            def visit_Name(self, node):
                if node.id in forbidden:
                    self.found.append(node.id)
                self.generic_visit(node)

        visitor = NameDispatchVisitor()
        visitor.visit(tree)
        assert not visitor.found, (
            f"assembly.py must not dispatch on project identity in executable code; "
            f"found: {visitor.found}"
        )


# ---------------------------------------------------------------------------
# §12.7 — No residual/balancing GFA component
# ---------------------------------------------------------------------------

class TestU1_NoResidualComponent:
    @pytest.mark.parametrize("ptype", ("Oborovo", "TUHO"))
    def test_no_residual_component_in_canonical_basis(self, ptype):
        """Canonical basis components must not include a residual or balancing-plug entry."""
        _, fs = _run_and_assemble(ptype)
        report = fs.accounting_policies.provenance.get("gfa_report", {})
        components = report.get("canonical_book_basis_components", [])
        codes = {c["code"] for c in components}
        forbidden_codes = {"residual", "balancing_plug", "plug", "adjustment", "other_rounding"}
        overlap = codes & forbidden_codes
        assert not overlap, (
            f"{ptype}: canonical basis must not contain residual/balancing-plug codes; "
            f"found: {overlap}"
        )

    @pytest.mark.parametrize("ptype", ("Oborovo", "TUHO"))
    def test_financing_components_sum_to_cfr_canonical_total(self, ptype):
        """For typed projects: financial_costs components sum ties to cfr.total_capitalized_financing_keur."""
        _, fs = _run_and_assemble(ptype)
        report = fs.accounting_policies.provenance.get("gfa_report", {})
        audit = report.get("audit", {})
        components = report.get("canonical_book_basis_components", [])
        fin_sum = sum(
            c["amount_keur"] for c in components if c["asset_class_code"] == "financial_costs"
        )
        cfr_total = audit.get("total_capitalized_financing_keur")
        if cfr_total is not None and cfr_total > 0:
            assert abs(fin_sum - cfr_total) < 1.0, (
                f"{ptype}: financing component sum {fin_sum:.3f} != "
                f"cfr.total_capitalized_financing_keur {cfr_total:.3f}"
            )
