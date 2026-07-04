"""V3-1 API Boundary Tests — enforce the finco_core public API contract.

See docs/finco_core_public_api_contract.md for the full contract.

Contract enforced here:
1. app/ has zero direct finco_core imports (uses domain.* shim layer only)
2. domain/* shims import only from public (non-_-prefixed) finco_core sub-modules
3. All approved public API entry points remain importable
"""
from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
APP_DIR = REPO_ROOT / "app"
DOMAIN_DIR = REPO_ROOT / "domain"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _finco_core_imports_in_dir(directory: Path) -> list[tuple[str, int, str]]:
    """Return (rel_path, lineno, module) for every finco_core import found."""
    hits = []
    for pyfile in sorted(directory.rglob("*.py")):
        if "__pycache__" in str(pyfile):
            continue
        try:
            tree = ast.parse(pyfile.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        rel = str(pyfile.relative_to(REPO_ROOT))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith("finco_core"):
                    hits.append((rel, node.lineno, node.module))
    return hits


def _is_private_finco_core_module(module: str) -> bool:
    """Return True if the module path crosses into a private (_-prefixed) leaf."""
    parts = module.split(".")
    # Any part after the package that starts with _ is private
    # e.g. finco_core.inputs._models  →  True
    # e.g. finco_core.inputs          →  False
    # e.g. finco_core.waterfall.waterfall_engine  →  False (no _ prefix)
    return any(p.startswith("_") for p in parts[1:])


# ---------------------------------------------------------------------------
# 1. app/ has zero direct finco_core imports
# ---------------------------------------------------------------------------

class TestAppLayerUsesShimsOnly:
    """The app/ layer must not import finco_core directly.
    It reaches the engine via domain.* compatibility shims only."""

    def test_app_has_no_direct_finco_core_imports(self):
        hits = _finco_core_imports_in_dir(APP_DIR)
        assert hits == [], (
            "app/ must not import finco_core directly — use domain.* shims instead:\n"
            + "\n".join(f"  {f}:{ln}: {mod}" for f, ln, mod in hits)
        )

    def test_main_web_has_no_direct_finco_core_imports(self):
        main_web = REPO_ROOT / "main_web.py"
        if not main_web.exists():
            pytest.skip("main_web.py not found")
        hits = []
        try:
            tree = ast.parse(main_web.read_text(encoding="utf-8"))
        except SyntaxError:
            return
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith("finco_core"):
                    hits.append((str(main_web.relative_to(REPO_ROOT)), node.lineno, node.module))
        assert hits == [], (
            "main_web.py must not import finco_core directly:\n"
            + "\n".join(f"  {f}:{ln}: {mod}" for f, ln, mod in hits)
        )


# ---------------------------------------------------------------------------
# 2. domain/* shims use only public (non-_) finco_core sub-modules
# ---------------------------------------------------------------------------

class TestDomainShimsUsePublicAPIOnly:
    """domain/* compatibility shims must not import from private finco_core
    internal modules (those with a _ prefix at any path component)."""

    def test_domain_shims_no_private_finco_core_imports(self):
        hits = [
            (f, ln, mod)
            for f, ln, mod in _finco_core_imports_in_dir(DOMAIN_DIR)
            if _is_private_finco_core_module(mod)
        ]
        assert hits == [], (
            "domain/* shims may not import from private finco_core internals:\n"
            + "\n".join(f"  {f}:{ln}: {mod}" for f, ln, mod in hits)
        )


# ---------------------------------------------------------------------------
# 3. All approved public entry points remain importable
# ---------------------------------------------------------------------------

PUBLIC_ENTRY_POINTS = [
    # inputs
    "finco_core.inputs",
    "finco_core.inputs.bess",
    "finco_core.inputs.senior_rate_schedule",
    "finco_core.inputs.senior_sculpting",
    # engine
    "finco_core.engine",
    "finco_core.engine.period_engine",
    "finco_core.engine.distribution_account",
    # revenue
    "finco_core.revenue",
    "finco_core.revenue.generation",
    # opex
    "finco_core.opex",
    "finco_core.opex.projections",
    # waterfall
    "finco_core.waterfall",
    "finco_core.waterfall.waterfall_engine",
    # tax
    "finco_core.tax",
    "finco_core.tax.engine",
    "finco_core.tax.reintegration",
    "finco_core.tax.loss_carryforward",
    "finco_core.tax.templates",
    # debt
    "finco_core.debt",
    "finco_core.debt.sculpting_iterative",
    "finco_core.debt.schedule",
    # shl
    "finco_core.shl",
    "finco_core.shl.engine",
    "finco_core.shl.fcf_waterfall",
    # sponsor
    "finco_core.sponsor",
    "finco_core.sponsor.xirr",
    "finco_core.sponsor.xirr_runner",
    "finco_core.sponsor.sponsor_cashflows",
    # depreciation
    "finco_core.depreciation",
    "finco_core.depreciation.engine",
    # validation
    "finco_core.validation",
    "finco_core.validation.validators",
]


class TestApprovedPublicEntryPointsImportable:
    """Every path listed in the public API contract must remain importable."""

    @pytest.mark.parametrize("module_name", PUBLIC_ENTRY_POINTS)
    def test_entry_point_importable(self, module_name: str):
        try:
            importlib.import_module(module_name)
        except ImportError as exc:
            pytest.fail(f"Public API entry point broken: {module_name}: {exc}")


# ---------------------------------------------------------------------------
# 4. Key public symbols accessible
# ---------------------------------------------------------------------------

class TestKeyPublicSymbols:
    """Spot-check that named public symbols are accessible via approved paths."""

    def test_inputs_symbols(self):
        from finco_core.inputs import (
            ProjectInputs, TechnicalParams, OpexItem, CapexItem,
            FinancingParams, TaxParams, ProjectInfo, BessParams,
            hash_inputs_for_cache,
        )
        assert all(x is not None for x in [
            ProjectInputs, TechnicalParams, OpexItem, CapexItem,
            FinancingParams, TaxParams, ProjectInfo, BessParams,
        ])
        assert callable(hash_inputs_for_cache)

    def test_revenue_symbols(self):
        from finco_core.revenue.generation import (
            full_revenue_schedule, full_generation_schedule,
            revenue_decomposition_schedule,
        )
        assert all(callable(f) for f in [
            full_revenue_schedule, full_generation_schedule,
            revenue_decomposition_schedule,
        ])

    def test_opex_symbols(self):
        from finco_core.opex.projections import opex_schedule_annual, opex_year
        assert callable(opex_schedule_annual)
        assert callable(opex_year)

    def test_waterfall_symbols(self):
        from finco_core.waterfall import run_waterfall, WaterfallPeriod, WaterfallResult
        assert callable(run_waterfall)
        assert WaterfallPeriod is not None
        assert WaterfallResult is not None

    def test_engine_symbols(self):
        from finco_core.engine import PeriodEngine
        from finco_core.engine.distribution_account import compute_tuho_r99_input_period
        assert PeriodEngine is not None
        assert callable(compute_tuho_r99_input_period)

    def test_debt_symbols(self):
        from finco_core.debt import iterative_sculpt_debt
        from finco_core.debt.schedule import senior_debt_amount
        assert callable(iterative_sculpt_debt)
        assert callable(senior_debt_amount)

    def test_tax_symbols(self):
        from finco_core.tax import fiscal_reintegration
        from finco_core.tax.engine import taxable_profit, atad_adjustment
        assert callable(fiscal_reintegration)
        assert callable(taxable_profit)
        assert callable(atad_adjustment)

    def test_shl_symbols(self):
        from finco_core.shl import ShlEngine
        from finco_core.shl.fcf_waterfall import compute_shl_fcf_waterfall_period
        assert ShlEngine is not None
        assert callable(compute_shl_fcf_waterfall_period)

    def test_sponsor_symbols(self):
        from finco_core.sponsor import xirr
        from finco_core.sponsor.xirr_runner import xirr_with_convergence
        assert callable(xirr)
        assert callable(xirr_with_convergence)

    def test_depreciation_symbols(self):
        from finco_core.depreciation import DepreciationEngine
        assert DepreciationEngine is not None
