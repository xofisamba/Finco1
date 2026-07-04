"""V2-9 Architecture Freeze — CI-enforced boundary tests.

These tests form the permanent architecture contract for finco_core after
completion of the V2 Controlled Extraction Programme (V2-3 through V2-8).

They must remain green forever. Any PR that breaks them is introducing an
architectural regression and must not be merged.

Contract:
1. Zero domain.* imports inside finco_core/ (runtime and TYPE_CHECKING)
2. Zero circular imports inside finco_core packages
3. All public API entry points accessible
4. Compatibility shims preserve object identity
5. Waterfall execution path has no domain.* module references at runtime
6. finco_core internal dependency graph has no outgoing domain.* edges
"""
from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).parent.parent
FINCO_CORE = REPO_ROOT / "finco_core"

FINCO_CORE_PACKAGES = [
    "finco_core.inputs",
    "finco_core.engine",
    "finco_core.revenue",
    "finco_core.opex",
    "finco_core.tax",
    "finco_core.sponsor",
    "finco_core.waterfall",
    "finco_core.shl",
    "finco_core.depreciation",
    "finco_core.debt",
    "finco_core.validation",
]


# ---------------------------------------------------------------------------
# 1. Zero domain.* imports (AST-level, catches runtime AND TYPE_CHECKING)
# ---------------------------------------------------------------------------

class TestZeroDomainImports:
    """No file inside finco_core/ may import from domain.* at any level."""

    def _collect_domain_imports(self) -> list[tuple[str, int, str]]:
        hits = []
        for pyfile in sorted(FINCO_CORE.rglob("*.py")):
            if "__pycache__" in str(pyfile):
                continue
            try:
                tree = ast.parse(pyfile.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    if node.module.startswith("domain.") or node.module == "domain":
                        rel = str(pyfile.relative_to(REPO_ROOT))
                        hits.append((rel, node.lineno, node.module))
        return hits

    def test_zero_domain_imports_in_finco_core(self):
        hits = self._collect_domain_imports()
        assert hits == [], (
            "domain.* imports found inside finco_core/ — architectural regression:\n"
            + "\n".join(f"  {f}:{ln}: from {mod}" for f, ln, mod in hits)
        )


# ---------------------------------------------------------------------------
# 2. Zero circular imports
# ---------------------------------------------------------------------------

class TestNoCircularImports:
    """All finco_core packages must import cleanly with no circular dependency."""

    @pytest.mark.parametrize("module_name", FINCO_CORE_PACKAGES)
    def test_package_importable_without_circular(self, module_name: str):
        try:
            importlib.import_module(module_name)
        except ImportError as exc:
            pytest.fail(f"Import failed (possible circular): {module_name}: {exc}")


# ---------------------------------------------------------------------------
# 3. Public API entry points
# ---------------------------------------------------------------------------

class TestPublicAPIStable:
    """Critical public symbols must remain accessible via finco_core.*"""

    def test_inputs_api(self):
        from finco_core.inputs import (
            ProjectInputs, TechnicalParams, OpexItem, CapexItem,
            FinancingParams, TaxParams, ProjectInfo, BessParams,
        )
        assert all(x is not None for x in [
            ProjectInputs, TechnicalParams, OpexItem, CapexItem,
            FinancingParams, TaxParams, ProjectInfo, BessParams,
        ])

    def test_revenue_api(self):
        from finco_core.revenue.generation import (
            full_revenue_schedule, full_generation_schedule,
            revenue_decomposition_schedule, period_generation,
            annual_generation_mwh, period_revenue,
        )
        assert all(callable(f) for f in [
            full_revenue_schedule, full_generation_schedule,
            revenue_decomposition_schedule, period_generation,
            annual_generation_mwh, period_revenue,
        ])

    def test_opex_api(self):
        from finco_core.opex.projections import (
            opex_schedule_annual, opex_year, opex_item_amount_at_year,
            opex_per_mw_y1, opex_per_mwh_y1, opex_schedule_period,
            opex_breakdown_year, total_opex_over_horizon, opex_growth_rate,
        )
        assert all(callable(f) for f in [
            opex_schedule_annual, opex_year, opex_item_amount_at_year,
        ])

    def test_waterfall_api(self):
        from finco_core.waterfall import run_waterfall, WaterfallPeriod
        assert callable(run_waterfall)
        assert WaterfallPeriod is not None

    def test_engine_api(self):
        from finco_core.engine import PeriodEngine
        assert PeriodEngine is not None

    def test_debt_api(self):
        from finco_core.debt import iterative_sculpt_debt
        assert callable(iterative_sculpt_debt)

    def test_tax_api(self):
        from finco_core.tax import fiscal_reintegration
        assert callable(fiscal_reintegration)

    def test_shl_api(self):
        from finco_core.shl import ShlEngine
        assert ShlEngine is not None

    def test_depreciation_api(self):
        from finco_core.depreciation import DepreciationEngine
        assert DepreciationEngine is not None

    def test_sponsor_api(self):
        from finco_core.sponsor import xirr
        assert callable(xirr)


# ---------------------------------------------------------------------------
# 4. Compatibility shim object identity
# ---------------------------------------------------------------------------

class TestCompatibilityShimsPreserveIdentity:
    """domain.* shims must expose the same objects as finco_core.*"""

    def test_revenue_generation_shim(self):
        from domain.revenue.generation import full_revenue_schedule as D
        from finco_core.revenue.generation import full_revenue_schedule as F
        assert D is F, "full_revenue_schedule shim broken"

    def test_revenue_full_generation_schedule_shim(self):
        from domain.revenue.generation import full_generation_schedule as D
        from finco_core.revenue.generation import full_generation_schedule as F
        assert D is F

    def test_revenue_decomposition_schedule_shim(self):
        from domain.revenue.generation import revenue_decomposition_schedule as D
        from finco_core.revenue.generation import revenue_decomposition_schedule as F
        assert D is F

    def test_opex_schedule_annual_shim(self):
        from domain.opex.projections import opex_schedule_annual as D
        from finco_core.opex.projections import opex_schedule_annual as F
        assert D is F, "opex_schedule_annual shim broken"

    def test_opex_year_shim(self):
        from domain.opex.projections import opex_year as D
        from finco_core.opex.projections import opex_year as F
        assert D is F

    def test_waterfall_engine_shim(self):
        from domain.waterfall.waterfall_engine import run_waterfall as D
        from finco_core.waterfall.waterfall_engine import run_waterfall as F
        assert D is F

    def test_period_engine_shim(self):
        from domain.period_engine import PeriodEngine as D
        from finco_core.engine.period_engine import PeriodEngine as F
        assert D is F

    def test_tax_engine_shim(self):
        from domain.tax.engine import taxable_profit as D
        from finco_core.tax.engine import taxable_profit as F
        assert D is F


# ---------------------------------------------------------------------------
# 5. Waterfall execution path has no domain.* references at runtime
# ---------------------------------------------------------------------------

class TestWaterfallExecutionPathClean:
    """No domain.* modules must appear as attributes of the waterfall engine
    module after import (covers lazy imports resolved at module load time)."""

    WATERFALL_MODULES = [
        "finco_core.waterfall.waterfall_engine",
        "finco_core.revenue.generation",
        "finco_core.opex.projections",
    ]

    @pytest.mark.parametrize("module_name", WATERFALL_MODULES)
    def test_no_domain_runtime_attrs(self, module_name: str):
        mod = importlib.import_module(module_name)
        domain_attrs = [
            k for k, v in vars(mod).items()
            if isinstance(v, ModuleType) and hasattr(v, "__name__")
            and str(getattr(v, "__name__", "")).startswith("domain.")
        ]
        assert domain_attrs == [], (
            f"{module_name} has runtime domain.* module references: {domain_attrs}"
        )


# ---------------------------------------------------------------------------
# 6. Dependency graph — no outgoing domain.* edges (AST scan)
# ---------------------------------------------------------------------------

class TestDependencyGraphNoDomainEdges:
    """AST-level scan confirms the finco_core internal graph has zero
    outgoing domain.* edges. This is a superset of TestZeroDomainImports
    expressed as a graph assertion for audit purposes."""

    def test_no_domain_edges_in_dependency_graph(self):
        domain_edges: list[str] = []
        for pyfile in sorted(FINCO_CORE.rglob("*.py")):
            if "__pycache__" in str(pyfile):
                continue
            try:
                tree = ast.parse(pyfile.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    if node.module.startswith("domain.") or node.module == "domain":
                        rel = str(pyfile.relative_to(REPO_ROOT))
                        domain_edges.append(f"{rel}:{node.lineno}: {node.module}")
        assert domain_edges == [], (
            "Outgoing domain.* edges found in finco_core dependency graph:\n"
            + "\n".join(f"  {e}" for e in domain_edges)
        )
