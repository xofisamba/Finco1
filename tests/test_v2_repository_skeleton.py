"""V2-1 Repository Skeleton — structural tests.

Verifies that:
- All required v2 package directories exist
- All packages are importable (have __init__.py)
- Required documentation files exist
- No Finco1 engine code has been copied into the new packages
- No legacy test files have been copied into the new packages
- No reports/ directory exists inside the new packages
- Existing application is unaffected (spot-check imports)

These tests contain NO financial logic and NO parity assertions.
They are structural only.
"""
from __future__ import annotations

import importlib
import os
from pathlib import Path

import pytest

# Root of the repository
REPO_ROOT = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# Package directory existence
# ---------------------------------------------------------------------------

class TestRequiredDirectoriesExist:
    """All required v2 package directories must exist."""

    @pytest.mark.parametrize("rel_path", [
        "finco_core",
        "finco_core/inputs",
        "finco_core/engine",
        "finco_core/debt",
        "finco_core/tax",
        "finco_core/depreciation",
        "finco_core/shl",
        "finco_core/waterfall",
        "finco_core/sponsor",
        "finco_core/audit",
        "finco_core/exports",
        "finco_core/validation",
        "finco_app",
        "finco_app/api",
        "finco_app/services",
        "finco_app/persistence",
        "finco_parity",
        "finco_parity/fixtures",
        "finco_parity/golden",
        "finco_parity/regression",
    ])
    def test_directory_exists(self, rel_path: str):
        path = REPO_ROOT / rel_path
        assert path.is_dir(), f"Required v2 directory missing: {rel_path}"

    @pytest.mark.parametrize("rel_path", [
        "finco_core/__init__.py",
        "finco_core/inputs/__init__.py",
        "finco_core/engine/__init__.py",
        "finco_core/debt/__init__.py",
        "finco_core/tax/__init__.py",
        "finco_core/depreciation/__init__.py",
        "finco_core/shl/__init__.py",
        "finco_core/waterfall/__init__.py",
        "finco_core/sponsor/__init__.py",
        "finco_core/audit/__init__.py",
        "finco_core/exports/__init__.py",
        "finco_core/validation/__init__.py",
        "finco_app/__init__.py",
        "finco_app/api/__init__.py",
        "finco_app/services/__init__.py",
        "finco_app/persistence/__init__.py",
        "finco_parity/__init__.py",
        "finco_parity/fixtures/__init__.py",
        "finco_parity/golden/__init__.py",
        "finco_parity/regression/__init__.py",
    ])
    def test_init_py_exists(self, rel_path: str):
        path = REPO_ROOT / rel_path
        assert path.is_file(), f"Missing __init__.py: {rel_path}"


# ---------------------------------------------------------------------------
# Package importability
# ---------------------------------------------------------------------------

class TestPackagesAreImportable:
    """All v2 packages must be importable without errors."""

    @pytest.mark.parametrize("module_name", [
        "finco_core",
        "finco_core.inputs",
        "finco_core.engine",
        "finco_core.debt",
        "finco_core.tax",
        "finco_core.depreciation",
        "finco_core.shl",
        "finco_core.waterfall",
        "finco_core.sponsor",
        "finco_core.audit",
        "finco_core.exports",
        "finco_core.validation",
        "finco_app",
        "finco_app.api",
        "finco_app.services",
        "finco_app.persistence",
        "finco_parity",
        "finco_parity.fixtures",
        "finco_parity.golden",
        "finco_parity.regression",
    ])
    def test_module_importable(self, module_name: str):
        try:
            importlib.import_module(module_name)
        except ImportError as exc:
            pytest.fail(f"Cannot import {module_name}: {exc}")


# ---------------------------------------------------------------------------
# Documentation files
# ---------------------------------------------------------------------------

class TestRequiredDocumentationExists:
    """All required v2 documentation files must exist."""

    @pytest.mark.parametrize("rel_path", [
        "docs/V2_ARCHITECTURE.md",
        "docs/V2_IMPORT_AUDIT.md",
        "docs/RC2_BASELINE.md",
        "docs/EXTRACTION_STRATEGY_UPDATE.md",
        "docs/FINCO_V2_CONTROLLED_EXTRACTION_PLAN.md",
        "finco_core/README.md",
        "finco_app/README.md",
        "finco_parity/README.md",
    ])
    def test_documentation_file_exists(self, rel_path: str):
        path = REPO_ROOT / rel_path
        assert path.is_file(), f"Required documentation file missing: {rel_path}"


# ---------------------------------------------------------------------------
# No engine code copied into new packages
# ---------------------------------------------------------------------------

class TestNoEngineCopiedIntoV2Packages:
    """V2 packages must not contain copied Finco1 engine code in V2-1."""

    V2_PACKAGES = ["finco_core", "finco_app", "finco_parity"]

    # Fingerprints that would indicate copied engine code — these strings
    # appear in legacy engine files and must not appear in v2 skeleton files.
    ENGINE_FINGERPRINTS = [
        "def run_waterfall(",
        "def _tax_bridge_taxable_income_before_losses(",
        "class WaterfallPeriod(",
        "class WaterfallResult(",
        "class TaxEngine(",
        "def sculpt_senior_debt(",
        "class SHLEngine(",
        "TUHO-WIND-1",  # identity dispatch guard
    ]

    def _collect_py_files(self) -> list[Path]:
        files = []
        for pkg in self.V2_PACKAGES:
            pkg_path = REPO_ROOT / pkg
            if pkg_path.exists():
                files.extend(
                    p for p in pkg_path.rglob("*.py")
                    if p.name != "__init__.py"
                )
        return files

    # V2-2 update: finco_core/inputs/ now contains real module files extracted in V2-2.
    # Non-init files in other packages are still prohibited.
    V2_2_ALLOWED_NON_INIT = frozenset([
        "finco_core/inputs/_models.py",
        "finco_core/inputs/senior_rate_schedule.py",
        "finco_core/inputs/senior_sculpting.py",
    ])

    def test_no_non_init_py_files_in_v2_skeleton(self):
        """Only V2-2 extraction files are allowed as non-__init__.py modules."""
        non_init_files = self._collect_py_files()
        unexpected = [
            f for f in non_init_files
            if str(f.relative_to(REPO_ROOT)) not in self.V2_2_ALLOWED_NON_INIT
        ]
        assert unexpected == [], (
            "Unexpected non-__init__.py Python files in v2 packages. "
            f"Found: {[str(f.relative_to(REPO_ROOT)) for f in unexpected]}"
        )

    @pytest.mark.parametrize("pkg", V2_PACKAGES)
    def test_no_engine_fingerprints_in_init_files(self, pkg: str):
        """__init__.py files in v2 packages must not contain engine implementation."""
        pkg_path = REPO_ROOT / pkg
        if not pkg_path.exists():
            pytest.skip(f"{pkg} does not exist yet")
        for init_file in pkg_path.rglob("__init__.py"):
            content = init_file.read_text(encoding="utf-8")
            for fingerprint in self.ENGINE_FINGERPRINTS:
                assert fingerprint not in content, (
                    f"Engine fingerprint '{fingerprint}' found in "
                    f"{init_file.relative_to(REPO_ROOT)} — "
                    "no engine code may be copied in V2-1"
                )


# ---------------------------------------------------------------------------
# No legacy test files copied
# ---------------------------------------------------------------------------

class TestNoLegacyTestsCopied:
    """No legacy Finco1 test files must appear inside the v2 packages."""

    LEGACY_TEST_PREFIXES = [
        "test_stack_",
        "test_phase",
        "test_excel_parity_",
        "test_tax_bridge_",
    ]

    @pytest.mark.parametrize("pkg", ["finco_core", "finco_app", "finco_parity"])
    def test_no_legacy_tests_in_v2_package(self, pkg: str):
        pkg_path = REPO_ROOT / pkg
        if not pkg_path.exists():
            pytest.skip(f"{pkg} does not exist yet")
        for py_file in pkg_path.rglob("*.py"):
            name = py_file.name
            for prefix in self.LEGACY_TEST_PREFIXES:
                assert not name.startswith(prefix), (
                    f"Legacy test file '{name}' found inside {pkg}/ — "
                    "legacy tests must not be copied into v2 packages"
                )


# ---------------------------------------------------------------------------
# No reports directory in v2 packages
# ---------------------------------------------------------------------------

class TestNoReportsInV2Packages:
    """No reports/ directory may exist inside v2 package trees."""

    @pytest.mark.parametrize("pkg", ["finco_core", "finco_app", "finco_parity"])
    def test_no_reports_directory(self, pkg: str):
        pkg_path = REPO_ROOT / pkg
        if not pkg_path.exists():
            pytest.skip(f"{pkg} does not exist yet")
        reports_path = pkg_path / "reports"
        assert not reports_path.exists(), (
            f"reports/ directory must not exist inside {pkg}/"
        )


# ---------------------------------------------------------------------------
# Existing application unaffected (spot-check)
# ---------------------------------------------------------------------------

class TestExistingApplicationUnaffected:
    """The existing Finco1 application must be importable and unmodified."""

    def test_domain_inputs_importable(self):
        """domain.inputs must still import correctly."""
        try:
            importlib.import_module("domain.inputs")
        except ImportError as exc:
            pytest.fail(f"domain.inputs broken by v2 skeleton changes: {exc}")

    def test_app_project_factories_importable(self):
        """app.project_factories must still import correctly."""
        try:
            importlib.import_module("app.project_factories")
        except ImportError as exc:
            pytest.fail(f"app.project_factories broken by v2 skeleton changes: {exc}")

    def test_domain_waterfall_engine_importable(self):
        """domain.waterfall.waterfall_engine must still import correctly."""
        try:
            importlib.import_module("domain.waterfall.waterfall_engine")
        except ImportError as exc:
            pytest.fail(
                f"domain.waterfall.waterfall_engine broken by v2 skeleton changes: {exc}"
            )
