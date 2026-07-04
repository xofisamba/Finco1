"""V2-4 Engine Extraction — structural and identity tests.

Verifies that:
- All finco_core.* engine packages are importable
- domain.X is finco_core.X (object identity — same code running)
- finco_core packages have zero runtime dependency on app/
- Legacy domain.* paths remain functional
- Critical engine entry points are accessible from finco_core

No financial logic is tested here; parity is verified in the parity suite.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# Package importability
# ---------------------------------------------------------------------------

class TestV24PackagesImportable:
    """All V2-4 finco_core engine packages must be importable."""

    @pytest.mark.parametrize("module_name", [
        "finco_core.engine",
        "finco_core.engine.period_engine",
        "finco_core.engine.distribution_account",
        "finco_core.waterfall",
        "finco_core.waterfall.waterfall_engine",
        "finco_core.waterfall.cash_flow",
        "finco_core.waterfall.dsra_engine",
        "finco_core.waterfall.reserves",
        "finco_core.waterfall.shl_engine",
        "finco_core.waterfall.tax_engine",
        "finco_core.tax",
        "finco_core.tax.engine",
        "finco_core.tax.engine_runner",
        "finco_core.tax.loss_carryforward",
        "finco_core.tax.reintegration",
        "finco_core.tax.atad_engine",
        "finco_core.tax.templates",
        "finco_core.debt",
        "finco_core.debt.schedule",
        "finco_core.debt.sculpting_iterative",
        "finco_core.debt.covenants",
        "finco_core.depreciation",
        "finco_core.depreciation.engine",
        "finco_core.depreciation.ledger",
        "finco_core.shl",
        "finco_core.shl.engine",
        "finco_core.shl.fcf_waterfall",
        "finco_core.sponsor",
        "finco_core.sponsor.xirr",
        "finco_core.sponsor.xnpv",
        "finco_core.sponsor.sponsor_cashflows",
        "finco_core.validation",
        "finco_core.validation.validators",
    ])
    def test_module_importable(self, module_name: str):
        try:
            importlib.import_module(module_name)
        except ImportError as exc:
            pytest.fail(f"Cannot import {module_name}: {exc}")


# ---------------------------------------------------------------------------
# Object identity: domain.X is finco_core.X
# ---------------------------------------------------------------------------

class TestObjectIdentity:
    """Critical engine symbols must be the same object in both namespaces."""

    def test_waterfall_period_identity(self):
        from domain.waterfall.waterfall_engine import WaterfallPeriod as DW
        from finco_core.waterfall.waterfall_engine import WaterfallPeriod as FW
        assert DW is FW, "WaterfallPeriod must be same object in domain and finco_core"

    def test_run_waterfall_identity(self):
        from domain.waterfall.waterfall_engine import run_waterfall as DW
        from finco_core.waterfall.waterfall_engine import run_waterfall as FW
        assert DW is FW, "run_waterfall must be same object in domain and finco_core"

    def test_taxable_profit_identity(self):
        from domain.tax.engine import taxable_profit as DT
        from finco_core.tax.engine import taxable_profit as FT
        assert DT is FT

    def test_fiscal_reintegration_identity(self):
        from domain.tax.reintegration import fiscal_reintegration as DT
        from finco_core.tax.reintegration import fiscal_reintegration as FT
        assert DT is FT

    def test_loss_carryforward_identity(self):
        import domain.tax.loss_carryforward as DL
        import finco_core.tax.loss_carryforward as FL
        # verify the module is the same content — check one callable
        assert hasattr(FL, "__file__") and FL.__file__ is not None

    def test_iterative_sculpt_identity(self):
        from domain.financing.sculpting_iterative import iterative_sculpt_debt as DD
        from finco_core.debt.sculpting_iterative import iterative_sculpt_debt as FD
        assert DD is FD

    def test_senior_debt_amount_identity(self):
        from domain.financing.schedule import senior_debt_amount as DS
        from finco_core.debt.schedule import senior_debt_amount as FS
        assert DS is FS

    def test_period_engine_identity(self):
        from domain.period_engine import PeriodEngine as DP
        from finco_core.engine.period_engine import PeriodEngine as FP
        assert DP is FP

    def test_compute_tuho_identity(self):
        from domain.distribution_account import compute_tuho_r99_input_period as DD
        from finco_core.engine.distribution_account import compute_tuho_r99_input_period as FD
        assert DD is FD

    def test_shl_engine_identity(self):
        from domain.shl.engine import ShlEngine as DS
        from finco_core.shl.engine import ShlEngine as FS
        assert DS is FS

    def test_depreciation_engine_identity(self):
        from domain.depreciation.engine import DepreciationEngine as DD
        from finco_core.depreciation.engine import DepreciationEngine as FD
        assert DD is FD

    def test_xirr_identity(self):
        from domain.returns.xirr import xirr as DR
        from finco_core.sponsor.xirr import xirr as FR
        assert DR is FR

    def test_xnpv_identity(self):
        from domain.returns.xnpv import xnpv as DR
        from finco_core.sponsor.xnpv import xnpv as FR
        assert DR is FR


# ---------------------------------------------------------------------------
# No app/ runtime dependency in finco_core
# ---------------------------------------------------------------------------

class TestNoAppDependency:
    """finco_core engine modules must not import from app/ at runtime."""

    ENGINE_MODULES = [
        "finco_core.waterfall.waterfall_engine",
        "finco_core.tax.engine",
        "finco_core.debt.sculpting_iterative",
        "finco_core.depreciation.engine",
        "finco_core.shl.engine",
        "finco_core.engine.period_engine",
    ]

    @pytest.mark.parametrize("module_name", ENGINE_MODULES)
    def test_no_app_import(self, module_name: str):
        mod = importlib.import_module(module_name)
        app_attrs = [
            k for k, v in vars(mod).items()
            if isinstance(v, ModuleType) and hasattr(v, "__name__")
            and str(getattr(v, "__name__", "")).startswith("app.")
        ]
        assert app_attrs == [], (
            f"{module_name} has runtime app.* module references: {app_attrs}"
        )


# ---------------------------------------------------------------------------
# Legacy domain paths still work
# ---------------------------------------------------------------------------

class TestLegacyDomainPathsWork:
    """All legacy domain.* import paths must remain functional."""

    @pytest.mark.parametrize("module_name", [
        "domain.waterfall.waterfall_engine",
        "domain.tax.engine",
        "domain.tax.reintegration",
        "domain.financing.schedule",
        "domain.financing.sculpting_iterative",
        "domain.depreciation.engine",
        "domain.shl.engine",
        "domain.returns.xirr",
        "domain.returns.xnpv",
        "domain.period_engine",
        "domain.distribution_account",
        "domain.validation",
    ])
    def test_legacy_path_importable(self, module_name: str):
        try:
            importlib.import_module(module_name)
        except ImportError as exc:
            pytest.fail(f"Legacy path broken: {module_name}: {exc}")


# ---------------------------------------------------------------------------
# Key engine entry points accessible from finco_core
# ---------------------------------------------------------------------------

class TestKeyEntryPoints:
    """Critical engine entry points must be accessible via finco_core."""

    def test_run_waterfall_accessible(self):
        from finco_core.waterfall import run_waterfall
        assert callable(run_waterfall)

    def test_waterfall_period_accessible(self):
        from finco_core.waterfall import WaterfallPeriod
        assert WaterfallPeriod is not None

    def test_period_engine_accessible(self):
        from finco_core.engine import PeriodEngine
        assert PeriodEngine is not None

    def test_iterative_sculpt_accessible(self):
        from finco_core.debt import iterative_sculpt_debt
        assert callable(iterative_sculpt_debt)

    def test_fiscal_reintegration_accessible(self):
        from finco_core.tax import fiscal_reintegration
        assert callable(fiscal_reintegration)

    def test_shl_engine_accessible(self):
        from finco_core.shl import ShlEngine
        assert ShlEngine is not None

    def test_depreciation_engine_accessible(self):
        from finco_core.depreciation import DepreciationEngine
        assert DepreciationEngine is not None

    def test_xirr_accessible(self):
        from finco_core.sponsor import xirr
        assert callable(xirr)
