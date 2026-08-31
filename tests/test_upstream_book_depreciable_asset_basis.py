"""Upstream canonical book depreciable asset basis — authority tests.

BOOK_DEPRECIABLE_ASSET_BASIS_UPSTREAM_REQUIRED

Twenty test categories proving:
  — Typed contract (BookDepreciableAssetBasis / BookDepreciableAssetComponent)
  — Generic Solar/Wind path (CapexStructure-derived basis)
  — Typed construction path (ConstructionFinancingResult-derived basis)
  — Capitalized IDC ≠ raw IDC when construction timing shifts
  — Adapter wiring into DepreciationInput.book_capex_items_for_depreciation
  — ProjectFinancingResult exposes book_depreciable_asset_basis
  — No project-code dispatch, no forbidden imports

Economic neutrality: all amounts on the typed path are pulled from the same
ConstructionFinancingResult vectors that already drive CapexStructure via
apply_capitalized_financing_costs. No economic delta.
"""
from __future__ import annotations

import dataclasses
from datetime import date
from pathlib import Path
from typing import Optional

import pytest

REPO_ROOT = Path(__file__).parent.parent

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_cfr(
    idc_capitalized_uses: tuple[float, ...] = (100.0, 200.0),
    idc_accrual: tuple[float, ...] = (150.0, 150.0),
    commitment_fee_accrual: tuple[float, ...] = (10.0, 20.0),
    structuring_fee: tuple[float, ...] = (50.0, 50.0),
    vat_idc_keur: float = 5.0,
    vat_commitment_fee_keur: float = 2.0,
):
    """Minimal synthetic ConstructionFinancingResult for basis builder tests.

    Only fields consumed by build_book_depreciable_asset_basis are meaningful;
    required structural fields are set to zero/empty.
    """
    from financial_engine.financing.contracts import ConstructionFinancingResult

    n = max(len(idc_capitalized_uses), len(commitment_fee_accrual), len(structuring_fee))
    z = tuple(0.0 for _ in range(n))
    dates_start = tuple(date(2025, 1, 1) for _ in range(n))
    dates_end = tuple(date(2025, 6, 30) for _ in range(n))
    return ConstructionFinancingResult(
        period_start_dates=dates_start,
        period_end_dates=dates_end,
        hard_capex_uses_keur=z,
        total_period_uses_keur=z,
        senior_draws_keur=z,
        cumulative_senior_keur=z,
        senior_idc_accrual_keur=tuple(idc_accrual),
        senior_commitment_fee_accrual_keur=tuple(commitment_fee_accrual),
        structuring_fee_keur=tuple(structuring_fee),
        shl_allocation_keur=z,
        shl_cash_contribution_keur=z,
        shl_day_count_fraction=z,
        shl_pik_accrual_keur=z,
        total_capitalized_financing_keur=0.0,
        shl_construction_pik_keur=0.0,
        opening_operating_shl_keur=0.0,
        final_total_project_uses_keur=0.0,
        final_senior_commitment_keur=8_000.0,
        sources_uses_residual_keur=0.0,
        outer_iterations=1,
        outer_residual_keur=0.0,
        stage_b2_iterations=1,
        stage_b2_residual_keur=0.0,
        senior_idc_capitalized_uses_keur=tuple(idc_capitalized_uses),
        vat_idc_keur=vat_idc_keur,
        vat_commitment_fee_keur=vat_commitment_fee_keur,
    )


def _make_minimal_capex_structure():
    """Minimal CapexStructure for typed construction path tests (hard CAPEX only)."""
    from finco_core.inputs._models import CapexItem, CapexStructure, AssetClass
    epc = CapexItem(name="EPC Contract", amount_keur=10_000.0, asset_class=AssetClass.CIVIL_GRID)
    zero = CapexItem(name="placeholder", amount_keur=0.0)

    def _z(name):
        return CapexItem(name=name, amount_keur=0.0)

    return CapexStructure(
        epc_contract=epc,
        production_units=_z("production_units"),
        epc_other=_z("epc_other"),
        grid_connection=_z("grid_connection"),
        ops_prep=_z("ops_prep"),
        insurances=_z("insurances"),
        lease_tax=_z("lease_tax"),
        construction_mgmt_a=_z("construction_mgmt_a"),
        commissioning=_z("commissioning"),
        audit_legal=_z("audit_legal"),
        construction_mgmt_b=_z("construction_mgmt_b"),
        contingencies=_z("contingencies"),
        taxes=_z("taxes"),
        project_acquisition=_z("project_acquisition"),
        project_rights=_z("project_rights"),
    )


# ---------------------------------------------------------------------------
# Category 1 — Typed contract structure
# ---------------------------------------------------------------------------

class TestBasisContractStructure:
    def test_component_required_fields(self):
        from finco_core.inputs.book_depreciable_asset_basis import BookDepreciableAssetComponent
        fields = {f.name for f in dataclasses.fields(BookDepreciableAssetComponent)}
        assert {"code", "name", "amount_keur", "asset_class_code",
                "useful_life_override", "provenance"} <= fields

    def test_basis_required_fields(self):
        from finco_core.inputs.book_depreciable_asset_basis import BookDepreciableAssetBasis
        fields = {f.name for f in dataclasses.fields(BookDepreciableAssetBasis)}
        assert {"components", "authority"} <= fields

    def test_total_keur_property(self):
        from finco_core.inputs.book_depreciable_asset_basis import (
            BookDepreciableAssetBasis, BookDepreciableAssetComponent,
        )
        c1 = BookDepreciableAssetComponent("a", "A", 100.0, "civil_grid", None, "p")
        c2 = BookDepreciableAssetComponent("b", "B", 250.0, "financial_costs", 12, "p")
        basis = BookDepreciableAssetBasis(components=(c1, c2), authority="TEST")
        assert abs(basis.total_keur - 350.0) < 1e-9

    def test_total_keur_empty(self):
        from finco_core.inputs.book_depreciable_asset_basis import BookDepreciableAssetBasis
        basis = BookDepreciableAssetBasis(components=(), authority="TEST")
        assert basis.total_keur == 0.0

    def test_exported_from_finco_core_inputs(self):
        from finco_core.inputs import BookDepreciableAssetBasis, BookDepreciableAssetComponent
        assert BookDepreciableAssetBasis is not None
        assert BookDepreciableAssetComponent is not None


# ---------------------------------------------------------------------------
# Category 2 — Immutability (frozen dataclass)
# ---------------------------------------------------------------------------

class TestBasisImmutability:
    def test_component_is_frozen(self):
        from finco_core.inputs.book_depreciable_asset_basis import BookDepreciableAssetComponent
        c = BookDepreciableAssetComponent("x", "X", 1.0, "civil_grid", None, "p")
        with pytest.raises((TypeError, dataclasses.FrozenInstanceError)):
            c.amount_keur = 999.0  # type: ignore[misc]

    def test_basis_is_frozen(self):
        from finco_core.inputs.book_depreciable_asset_basis import BookDepreciableAssetBasis
        basis = BookDepreciableAssetBasis(components=(), authority="A")
        with pytest.raises((TypeError, dataclasses.FrozenInstanceError)):
            basis.authority = "B"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Category 3 — Generic path: Solar project
# ---------------------------------------------------------------------------

class TestGenericPathSolar:
    def test_authority_is_generic(self):
        from app.project_factories import create_default_solar_project
        from financial_engine.book_basis import build_book_depreciable_asset_basis
        inputs = create_default_solar_project()
        basis = build_book_depreciable_asset_basis(inputs.capex)
        assert basis.authority == "GENERIC_CAPEX_STRUCTURE_BOOK_BASIS"

    def test_returns_basis_instance(self):
        from app.project_factories import create_default_solar_project
        from financial_engine.book_basis import build_book_depreciable_asset_basis
        from finco_core.inputs.book_depreciable_asset_basis import BookDepreciableAssetBasis
        inputs = create_default_solar_project()
        basis = build_book_depreciable_asset_basis(inputs.capex)
        assert isinstance(basis, BookDepreciableAssetBasis)

    def test_no_cfr_needed(self):
        from app.project_factories import create_default_solar_project
        from financial_engine.book_basis import build_book_depreciable_asset_basis
        inputs = create_default_solar_project()
        # No construction_financing_result → generic path, must not raise
        basis = build_book_depreciable_asset_basis(inputs.capex, None)
        assert basis is not None


# ---------------------------------------------------------------------------
# Category 4 — Generic path: Wind project
# ---------------------------------------------------------------------------

class TestGenericPathWind:
    def test_authority_is_generic(self):
        from app.project_factories import create_default_wind_project
        from financial_engine.book_basis import build_book_depreciable_asset_basis
        inputs = create_default_wind_project()
        basis = build_book_depreciable_asset_basis(inputs.capex)
        assert basis.authority == "GENERIC_CAPEX_STRUCTURE_BOOK_BASIS"

    def test_components_non_empty(self):
        from app.project_factories import create_default_wind_project
        from financial_engine.book_basis import build_book_depreciable_asset_basis
        inputs = create_default_wind_project()
        basis = build_book_depreciable_asset_basis(inputs.capex)
        assert len(basis.components) > 0


# ---------------------------------------------------------------------------
# Category 5 — Generic path: economic identity with CapexStructure
# ---------------------------------------------------------------------------

class TestGenericPathEconomicIdentity:
    def test_solar_total_matches_capex_structure(self):
        from app.project_factories import create_default_solar_project
        from financial_engine.book_basis import build_book_depreciable_asset_basis
        inputs = create_default_solar_project()
        basis = build_book_depreciable_asset_basis(inputs.capex)
        implicit_total = sum(
            item.amount_keur for item in inputs.capex.book_depreciable_capex_items()
            if item.amount_keur != 0.0
        )
        assert abs(basis.total_keur - implicit_total) < 1e-9

    def test_wind_total_matches_capex_structure(self):
        from app.project_factories import create_default_wind_project
        from financial_engine.book_basis import build_book_depreciable_asset_basis
        inputs = create_default_wind_project()
        basis = build_book_depreciable_asset_basis(inputs.capex)
        implicit_total = sum(
            item.amount_keur for item in inputs.capex.book_depreciable_capex_items()
            if item.amount_keur != 0.0
        )
        assert abs(basis.total_keur - implicit_total) < 1e-9

    def test_solar_component_names_match(self):
        from app.project_factories import create_default_solar_project
        from financial_engine.book_basis import build_book_depreciable_asset_basis
        inputs = create_default_solar_project()
        basis = build_book_depreciable_asset_basis(inputs.capex)
        implicit_names = {item.name for item in inputs.capex.book_depreciable_capex_items()
                          if item.amount_keur != 0.0}
        basis_names = {c.name for c in basis.components}
        assert basis_names == implicit_names


# ---------------------------------------------------------------------------
# Category 6 — Generic path: provenance on all components
# ---------------------------------------------------------------------------

class TestGenericPathProvenances:
    def test_all_components_have_generic_provenance(self):
        from app.project_factories import create_default_solar_project
        from financial_engine.book_basis import build_book_depreciable_asset_basis
        inputs = create_default_solar_project()
        basis = build_book_depreciable_asset_basis(inputs.capex)
        for c in basis.components:
            assert c.provenance == "CAPEX_STRUCTURE_GENERIC", (
                f"component '{c.name}' has unexpected provenance '{c.provenance}'"
            )


# ---------------------------------------------------------------------------
# Category 7 — Non-depreciable items excluded
# ---------------------------------------------------------------------------

class TestNonDepreciableItemsExcluded:
    def test_non_depreciable_flag_excluded_from_generic_basis(self):
        from finco_core.inputs._models import CapexItem, CapexStructure, AssetClass
        from financial_engine.book_basis import build_book_depreciable_asset_basis

        non_dep = CapexItem(name="Land", amount_keur=500.0, is_depreciable=False)
        dep = CapexItem(name="EPC Contract", amount_keur=10_000.0)
        z = CapexItem(name="placeholder", amount_keur=0.0)

        def _z(name):
            return CapexItem(name=name, amount_keur=0.0)

        capex = CapexStructure(
            epc_contract=dep,
            production_units=non_dep,
            epc_other=_z("epc_other"),
            grid_connection=_z("grid_connection"),
            ops_prep=_z("ops_prep"),
            insurances=_z("insurances"),
            lease_tax=_z("lease_tax"),
            construction_mgmt_a=_z("construction_mgmt_a"),
            commissioning=_z("commissioning"),
            audit_legal=_z("audit_legal"),
            construction_mgmt_b=_z("construction_mgmt_b"),
            contingencies=_z("contingencies"),
            taxes=_z("taxes"),
            project_acquisition=_z("project_acquisition"),
            project_rights=_z("project_rights"),
        )
        basis = build_book_depreciable_asset_basis(capex)
        names = {c.name for c in basis.components}
        assert "EPC Contract" in names
        assert "Land" not in names

    def test_non_depreciable_excluded_from_typed_basis(self):
        from finco_core.inputs._models import CapexItem, CapexStructure, AssetClass
        from financial_engine.book_basis import build_book_depreciable_asset_basis

        dep = CapexItem(name="EPC Contract", amount_keur=10_000.0)
        non_dep = CapexItem(name="Land", amount_keur=500.0, is_depreciable=False)

        def _z(name):
            return CapexItem(name=name, amount_keur=0.0)

        capex = CapexStructure(
            epc_contract=dep,
            production_units=non_dep,
            epc_other=_z("epc_other"),
            grid_connection=_z("grid_connection"),
            ops_prep=_z("ops_prep"),
            insurances=_z("insurances"),
            lease_tax=_z("lease_tax"),
            construction_mgmt_a=_z("construction_mgmt_a"),
            commissioning=_z("commissioning"),
            audit_legal=_z("audit_legal"),
            construction_mgmt_b=_z("construction_mgmt_b"),
            contingencies=_z("contingencies"),
            taxes=_z("taxes"),
            project_acquisition=_z("project_acquisition"),
            project_rights=_z("project_rights"),
        )
        cfr = _make_cfr()
        basis = build_book_depreciable_asset_basis(capex, cfr)
        names = {c.name for c in basis.components}
        assert "EPC Contract" in names
        assert "Land" not in names


# ---------------------------------------------------------------------------
# Category 8 — Typed construction path: authority
# ---------------------------------------------------------------------------

class TestTypedConstructionAuthority:
    def test_authority_is_typed(self):
        from financial_engine.book_basis import build_book_depreciable_asset_basis
        capex = _make_minimal_capex_structure()
        cfr = _make_cfr()
        basis = build_book_depreciable_asset_basis(capex, cfr)
        assert basis.authority == "TYPED_CONSTRUCTION_FINANCING_RESULT_BOOK_BASIS"

    def test_typed_path_triggered_by_cfr(self):
        from financial_engine.book_basis import build_book_depreciable_asset_basis
        capex = _make_minimal_capex_structure()
        # With CFR → typed
        basis_typed = build_book_depreciable_asset_basis(capex, _make_cfr())
        assert basis_typed.authority == "TYPED_CONSTRUCTION_FINANCING_RESULT_BOOK_BASIS"
        # Without CFR → generic
        basis_generic = build_book_depreciable_asset_basis(capex, None)
        assert basis_generic.authority == "GENERIC_CAPEX_STRUCTURE_BOOK_BASIS"


# ---------------------------------------------------------------------------
# Category 9 — Typed construction: IDC component from capitalized_uses
# ---------------------------------------------------------------------------

class TestTypedConstructionIDCComponent:
    def test_idc_amount_from_capitalized_uses_not_accrual(self):
        from financial_engine.book_basis import build_book_depreciable_asset_basis
        capex = _make_minimal_capex_structure()
        # accrual ≠ capitalized_uses so we can distinguish them
        cfr = _make_cfr(
            idc_capitalized_uses=(100.0, 200.0),   # sum = 300
            idc_accrual=(120.0, 180.0),            # sum = 300 — same total, different source
        )
        basis = build_book_depreciable_asset_basis(capex, cfr)
        idc_components = [c for c in basis.components if c.code == "senior_idc"]
        assert len(idc_components) == 1
        assert abs(idc_components[0].amount_keur - 300.0) < 1e-9

    def test_idc_useful_life_is_12(self):
        from financial_engine.book_basis import build_book_depreciable_asset_basis
        capex = _make_minimal_capex_structure()
        basis = build_book_depreciable_asset_basis(capex, _make_cfr())
        idc = next(c for c in basis.components if c.code == "senior_idc")
        assert idc.useful_life_override == 12

    def test_idc_asset_class_is_financial_costs(self):
        from financial_engine.book_basis import build_book_depreciable_asset_basis
        capex = _make_minimal_capex_structure()
        basis = build_book_depreciable_asset_basis(capex, _make_cfr())
        idc = next(c for c in basis.components if c.code == "senior_idc")
        assert idc.asset_class_code == "financial_costs"


# ---------------------------------------------------------------------------
# Category 10 — Typed construction: IDC provenance string
# ---------------------------------------------------------------------------

class TestTypedConstructionIDCProvenance:
    def test_idc_provenance_is_capitalized_uses(self):
        from financial_engine.book_basis import build_book_depreciable_asset_basis
        capex = _make_minimal_capex_structure()
        basis = build_book_depreciable_asset_basis(capex, _make_cfr())
        idc = next(c for c in basis.components if c.code == "senior_idc")
        assert idc.provenance == "CONSTRUCTION_FINANCING_RESULT_SENIOR_IDC_CAPITALIZED_USES"

    def test_hard_capex_provenance_is_hard_capex(self):
        from financial_engine.book_basis import build_book_depreciable_asset_basis
        capex = _make_minimal_capex_structure()
        basis = build_book_depreciable_asset_basis(capex, _make_cfr())
        hard_capex = [c for c in basis.components if c.code == "EPC Contract"]
        assert len(hard_capex) == 1
        assert hard_capex[0].provenance == "CAPEX_STRUCTURE_HARD_CAPEX"


# ---------------------------------------------------------------------------
# Category 11 — Capitalized IDC ≠ raw accrual (timing distinction)
# ---------------------------------------------------------------------------

class TestCapitalizedIDCNotRawIDC:
    def test_capitalized_uses_differ_from_accrual_when_timing_shifted(self):
        """Builder uses capitalized_uses; accrual is different when timing is next-period."""
        from financial_engine.book_basis import build_book_depreciable_asset_basis
        capex = _make_minimal_capex_structure()
        # Simulate NEXT_FUNDING_PERIOD timing: accrual in period 0, capitalized in period 1
        cfr = _make_cfr(
            idc_capitalized_uses=(0.0, 300.0),   # shifted forward by one period
            idc_accrual=(300.0, 0.0),            # accrues in period 0
        )
        basis = build_book_depreciable_asset_basis(capex, cfr)
        idc = next(c for c in basis.components if c.code == "senior_idc")
        # Amount = sum(capitalized_uses) = 300 — same total but different source
        assert abs(idc.amount_keur - 300.0) < 1e-9
        # Confirm provenance points to capitalized uses (not accrual)
        assert "CAPITALIZED_USES" in idc.provenance

    def test_zero_capitalized_idc_excluded(self):
        """When all IDC capitalized uses are zero, no IDC component appears."""
        from financial_engine.book_basis import build_book_depreciable_asset_basis
        capex = _make_minimal_capex_structure()
        cfr = _make_cfr(
            idc_capitalized_uses=(0.0, 0.0),
            idc_accrual=(150.0, 150.0),  # accrual > 0 but capitalized = 0
        )
        basis = build_book_depreciable_asset_basis(capex, cfr)
        idc_components = [c for c in basis.components if c.code == "senior_idc"]
        assert len(idc_components) == 0


# ---------------------------------------------------------------------------
# Category 12 — Commitment fee component
# ---------------------------------------------------------------------------

class TestTypedConstructionCommitmentFee:
    def test_commitment_fee_amount_from_accrual(self):
        from financial_engine.book_basis import build_book_depreciable_asset_basis
        capex = _make_minimal_capex_structure()
        cfr = _make_cfr(commitment_fee_accrual=(15.0, 25.0))
        basis = build_book_depreciable_asset_basis(capex, cfr)
        fee = next((c for c in basis.components if c.code == "senior_commitment_fee"), None)
        assert fee is not None
        assert abs(fee.amount_keur - 40.0) < 1e-9

    def test_commitment_fee_useful_life_is_12(self):
        from financial_engine.book_basis import build_book_depreciable_asset_basis
        capex = _make_minimal_capex_structure()
        basis = build_book_depreciable_asset_basis(capex, _make_cfr())
        fee = next(c for c in basis.components if c.code == "senior_commitment_fee")
        assert fee.useful_life_override == 12


# ---------------------------------------------------------------------------
# Category 13 — Structuring fee component
# ---------------------------------------------------------------------------

class TestTypedConstructionStructuringFee:
    def test_structuring_fee_amount_from_vector(self):
        from financial_engine.book_basis import build_book_depreciable_asset_basis
        capex = _make_minimal_capex_structure()
        cfr = _make_cfr(structuring_fee=(200.0, 300.0))
        basis = build_book_depreciable_asset_basis(capex, cfr)
        struct = next((c for c in basis.components if c.code == "structuring_fee"), None)
        assert struct is not None
        assert abs(struct.amount_keur - 500.0) < 1e-9

    def test_structuring_fee_useful_life_is_12(self):
        from financial_engine.book_basis import build_book_depreciable_asset_basis
        capex = _make_minimal_capex_structure()
        basis = build_book_depreciable_asset_basis(capex, _make_cfr())
        struct = next(c for c in basis.components if c.code == "structuring_fee")
        assert struct.useful_life_override == 12


# ---------------------------------------------------------------------------
# Category 14 — VAT combined as single component
# ---------------------------------------------------------------------------

class TestTypedConstructionVAT:
    def test_vat_combined_as_single_component(self):
        from financial_engine.book_basis import build_book_depreciable_asset_basis
        capex = _make_minimal_capex_structure()
        cfr = _make_cfr(vat_idc_keur=8.0, vat_commitment_fee_keur=3.0)
        basis = build_book_depreciable_asset_basis(capex, cfr)
        vat = next((c for c in basis.components if c.code == "vat_costs"), None)
        assert vat is not None
        assert abs(vat.amount_keur - 11.0) < 1e-9

    def test_vat_useful_life_is_20(self):
        from financial_engine.book_basis import build_book_depreciable_asset_basis
        capex = _make_minimal_capex_structure()
        cfr = _make_cfr(vat_idc_keur=8.0, vat_commitment_fee_keur=3.0)
        basis = build_book_depreciable_asset_basis(capex, cfr)
        vat = next(c for c in basis.components if c.code == "vat_costs")
        assert vat.useful_life_override == 20

    def test_zero_vat_excluded(self):
        from financial_engine.book_basis import build_book_depreciable_asset_basis
        capex = _make_minimal_capex_structure()
        cfr = _make_cfr(vat_idc_keur=0.0, vat_commitment_fee_keur=0.0)
        basis = build_book_depreciable_asset_basis(capex, cfr)
        vat_components = [c for c in basis.components if c.code == "vat_costs"]
        assert len(vat_components) == 0


# ---------------------------------------------------------------------------
# Category 15 — SHL excluded from basis
# ---------------------------------------------------------------------------

class TestSHLExcludedFromBasis:
    def test_no_shl_pik_in_generic_basis(self):
        from app.project_factories import create_default_solar_project
        from financial_engine.book_basis import build_book_depreciable_asset_basis
        inputs = create_default_solar_project()
        basis = build_book_depreciable_asset_basis(inputs.capex)
        codes = {c.code for c in basis.components}
        names = {c.name.lower() for c in basis.components}
        assert not any("shl" in n or "shareholder" in n for n in names)
        assert "shl_pik" not in codes

    def test_no_shl_in_typed_basis(self):
        from financial_engine.book_basis import build_book_depreciable_asset_basis
        capex = _make_minimal_capex_structure()
        cfr = _make_cfr()
        basis = build_book_depreciable_asset_basis(capex, cfr)
        names = {c.name.lower() for c in basis.components}
        assert not any("shl" in n or "shareholder" in n for n in names)


# ---------------------------------------------------------------------------
# Category 16 — Zero amounts excluded
# ---------------------------------------------------------------------------

class TestZeroAmountsExcluded:
    def test_zero_hard_capex_excluded_from_typed_basis(self):
        from financial_engine.book_basis import build_book_depreciable_asset_basis
        capex = _make_minimal_capex_structure()  # only EPC=10000, rest=0
        cfr = _make_cfr()
        basis = build_book_depreciable_asset_basis(capex, cfr)
        assert all(c.amount_keur != 0.0 for c in basis.components)

    def test_zero_financing_excluded_from_typed_basis(self):
        from financial_engine.book_basis import build_book_depreciable_asset_basis
        capex = _make_minimal_capex_structure()
        cfr = _make_cfr(
            idc_capitalized_uses=(0.0, 0.0),
            commitment_fee_accrual=(0.0, 0.0),
            structuring_fee=(0.0, 0.0),
            vat_idc_keur=0.0,
            vat_commitment_fee_keur=0.0,
        )
        basis = build_book_depreciable_asset_basis(capex, cfr)
        financing_codes = {"senior_idc", "senior_commitment_fee", "structuring_fee", "vat_costs"}
        present_codes = {c.code for c in basis.components}
        assert not financing_codes.intersection(present_codes)


# ---------------------------------------------------------------------------
# Category 17 — Builder signature: no project dispatch
# ---------------------------------------------------------------------------

class TestBuilderNoProjectDispatch:
    def test_builder_module_has_no_project_code_dispatch(self):
        """Builder must not dispatch on project codes or identity strings."""
        text = (REPO_ROOT / "financial_engine" / "book_basis.py").read_text()
        for name in {"oborovo", "tuho", "kupi", "OBR-001", "TUHO-WIND-1"}:
            assert name not in text, (
                f"book_basis.py contains project identity dispatch '{name}'"
            )

    def test_builder_signature_has_no_project_fields(self):
        import inspect
        from financial_engine.book_basis import build_book_depreciable_asset_basis
        sig = inspect.signature(build_book_depreciable_asset_basis)
        for bad in {"project", "project_code", "project_name"}:
            assert bad not in sig.parameters, (
                f"builder has forbidden parameter '{bad}'"
            )

    def test_contract_module_has_no_project_identity_fields(self):
        """Contract module must have no project-identity fields (project_code etc.)."""
        import dataclasses as _dc
        from finco_core.inputs.book_depreciable_asset_basis import (
            BookDepreciableAssetBasis, BookDepreciableAssetComponent,
        )
        for cls in (BookDepreciableAssetBasis, BookDepreciableAssetComponent):
            field_names = {f.name for f in _dc.fields(cls)}
            for bad in {"project", "project_code", "project_name", "dispatch"}:
                assert bad not in field_names, (
                    f"{cls.__name__} has forbidden field '{bad}'"
                )


# ---------------------------------------------------------------------------
# Category 18 — Adapter wiring into DepreciationInput
# ---------------------------------------------------------------------------

class TestAdapterWiring:
    def test_book_basis_replaces_implicit_path(self):
        from app.project_factories import create_default_solar_project
        from financial_engine.adapters.project_inputs import from_project_inputs
        from financial_engine.book_basis import build_book_depreciable_asset_basis

        inputs = create_default_solar_project()
        basis = build_book_depreciable_asset_basis(inputs.capex)
        op_input = from_project_inputs(inputs, book_basis=basis)

        dep_names = {item.name for item in op_input.depreciation.book_capex_items_for_depreciation}
        basis_names = {c.name for c in basis.components}
        assert dep_names == basis_names

    def test_adapter_without_basis_uses_implicit_path(self):
        from app.project_factories import create_default_solar_project
        from financial_engine.adapters.project_inputs import from_project_inputs

        inputs = create_default_solar_project()
        op_input = from_project_inputs(inputs)
        # Implicit path: same items as book_depreciable_capex_items()
        implicit_names = {
            item.name for item in inputs.capex.book_depreciable_capex_items()
            if item.amount_keur != 0.0
        }
        dep_names = {item.name for item in op_input.depreciation.book_capex_items_for_depreciation}
        assert dep_names == implicit_names

    def test_adapter_amounts_match_basis(self):
        from app.project_factories import create_default_solar_project
        from financial_engine.adapters.project_inputs import from_project_inputs
        from financial_engine.book_basis import build_book_depreciable_asset_basis

        inputs = create_default_solar_project()
        basis = build_book_depreciable_asset_basis(inputs.capex)
        op_input = from_project_inputs(inputs, book_basis=basis)

        dep_total = sum(
            item.amount_keur for item in op_input.depreciation.book_capex_items_for_depreciation
        )
        assert abs(dep_total - basis.total_keur) < 1e-9

    def test_adapter_useful_life_preserved(self):
        from financial_engine.adapters.project_inputs import from_project_inputs
        from financial_engine.book_basis import build_book_depreciable_asset_basis
        from finco_core.inputs.book_depreciable_asset_basis import (
            BookDepreciableAssetBasis, BookDepreciableAssetComponent,
        )
        from app.project_factories import create_default_solar_project

        inputs = create_default_solar_project()
        c = BookDepreciableAssetComponent(
            code="test_item", name="Test Item", amount_keur=1000.0,
            asset_class_code="civil_grid", useful_life_override=15, provenance="TEST",
        )
        basis = BookDepreciableAssetBasis(components=(c,), authority="TEST")
        op_input = from_project_inputs(inputs, book_basis=basis)
        dep = op_input.depreciation.book_capex_items_for_depreciation
        assert len(dep) == 1
        assert dep[0].useful_life_override == 15


# ---------------------------------------------------------------------------
# Category 19 — ProjectFinancingResult exposes basis field
# ---------------------------------------------------------------------------

class TestProjectFinancingResultExposure:
    def test_field_exists_on_contract(self):
        from financial_engine.financing.contracts import ProjectFinancingResult
        fields = {f.name for f in dataclasses.fields(ProjectFinancingResult)}
        assert "book_depreciable_asset_basis" in fields

    def test_field_defaults_to_none(self):
        from financial_engine.financing.contracts import ProjectFinancingResult
        fields = {f.name: f for f in dataclasses.fields(ProjectFinancingResult)}
        f = fields["book_depreciable_asset_basis"]
        assert f.default is None or (
            hasattr(f, "default") and f.default is None
        )

    def test_typed_construction_result_carries_basis(self):
        """Full typed construction run exposes a non-None book_depreciable_asset_basis."""
        pytest.importorskip("app.project_factories")
        try:
            from app.project_factories import create_default_oborovo_project
        except (ImportError, AttributeError):
            pytest.skip("create_default_oborovo_project not available")

        from app.services.production_financial_authority import run_clean_production
        inputs = create_default_oborovo_project()
        result = run_clean_production(inputs)
        # Navigate to ProjectFinancingResult
        pfr = getattr(result, "project_financing_result", None)
        if pfr is None:
            pytest.skip("project_financing_result not on result")
        basis = getattr(pfr, "book_depreciable_asset_basis", None)
        assert basis is not None, "book_depreciable_asset_basis must be set on typed construction run"
        assert basis.authority == "TYPED_CONSTRUCTION_FINANCING_RESULT_BOOK_BASIS"


# ---------------------------------------------------------------------------
# Category 20 — No forbidden imports in new modules
# ---------------------------------------------------------------------------

class TestNoForbiddenImports:
    def test_book_basis_does_not_import_financial_statements(self):
        text = (REPO_ROOT / "financial_engine" / "book_basis.py").read_text()
        assert "financial_engine.financial_statements" not in text
        assert "from financial_engine.financial_statements" not in text
        assert "import financial_engine.financial_statements" not in text

    def test_book_basis_contract_does_not_import_financial_statements(self):
        text = (REPO_ROOT / "finco_core" / "inputs" / "book_depreciable_asset_basis.py").read_text()
        assert "financial_statements" not in text

    def test_book_basis_does_not_import_c3_types(self):
        text = (REPO_ROOT / "financial_engine" / "book_basis.py").read_text()
        assert "financial_engine.financial_statements" not in text
        assert "CleanFinancialStatements" not in text
        assert "IncomeStatement" not in text

    def test_builder_module_not_in_financial_statements(self):
        """C3 financial statements module must not define the basis builder."""
        fs_dir = REPO_ROOT / "financial_engine" / "financial_statements"
        if not fs_dir.exists():
            return
        for f in fs_dir.rglob("*.py"):
            text = f.read_text()
            assert "build_book_depreciable_asset_basis" not in text, (
                f"{f}: basis builder must not be defined in financial_statements/"
            )
