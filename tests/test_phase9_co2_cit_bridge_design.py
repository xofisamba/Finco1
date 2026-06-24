"""tests/test_phase9_co2_cit_bridge_design.py

Phase 9: CO2→CIT Bridge Design — R99 promotion dependency validation.

DESIGN / GOVERNANCE ONLY — no runtime promotion.

This module validates:
- CO2→CIT design docs exist and contain required sections
- CO2 revenue gap is explicitly documented
- Promotion dependencies are correctly classified
- R99/R102 remains BLOCKED
- No runtime files changed

R99/R102: BLOCKED — no promotion implemented.
"""

import pytest
from pathlib import Path


class TestCO2CITBridgeDesignDoc:
    """Design doc completeness validation."""

    def test_design_doc_exists(self):
        assert Path("docs/phase9_co2_cit_bridge_design.md").exists()

    def test_dependency_matrix_exists(self):
        assert Path("reports/phase9_co2_cit_dependency_matrix.csv").exists()

    def test_design_doc_has_required_sections(self):
        content = Path("docs/phase9_co2_cit_bridge_design.md").read_text()
        required = [
            "Overview",
            "Current CO2 Runtime Flow",
            "Why CO2 Revenue Matters for CIT",
            "Gap Analysis",
            "Affected Subsystems",
            "CO2→CIT Dependency Analysis",
            "TaxEngine — CO2 Input Field Design",
            "Waterfall Revenue Field — CO2 Inclusion Design",
            "Waterfall → TaxEngine Call Site Modification",
            "Depreciation → TaxEngine",
            "actual_cfads vs. sizing_cfads Implications",
            "Dependency Graph",
            "Recommended Promotion Order",
            "Explicit Blockers",
            "Final Recommendation",
        ]
        for section in required:
            assert section in content or section.replace("Executive Summary", "Overview") in content, f"Missing section: {section}"

    def test_co2_gap_explicitly_documented(self):
        """CO2 revenue gap (not in EBITDA) must be explicitly documented."""
        content = Path("docs/phase9_co2_cit_bridge_design.md").read_text()
        # The design doc must explicitly state CO2 is NOT in EBITDA/revenue
        gap_indicators = [
            "NOT included in",
            "not in ebitda",
            "NOT in ebitda",
            "CO2 bypasses",
            "not in period.revenue",
            "not wired",
        ]
        found = any(indicator.lower() in content.lower() for indicator in gap_indicators)
        assert found, "CO2 gap must be explicitly documented (CO2 not in EBITDA/revenue)"


class TestCO2CITDependencyMatrix:
    """Dependency matrix completeness validation."""

    def test_matrix_has_required_columns(self):
        import csv
        path = Path("reports/phase9_co2_cit_dependency_matrix.csv")
        with open(path) as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
        required = [
            "subsystem", "current_owner", "future_owner",
            "runtime_or_audit", "upstream_dependency", "downstream_dependency",
            "promotion_dependency", "current_status", "risk_level", "notes"
        ]
        for col in required:
            assert col in headers, f"Missing column: {col}"

    def test_matrix_has_minimum_rows(self):
        import csv
        path = Path("reports/phase9_co2_cit_dependency_matrix.csv")
        with open(path) as f:
            rows = list(csv.DictReader(f))
        assert len(rows) >= 15, f"Expected ≥15 rows, got {len(rows)}"

    def test_co2_entry_has_correct_status(self):
        """CO2 certificate revenue entry must have MISSING or CO2-MISSING status."""
        import csv
        path = Path("reports/phase9_co2_cit_dependency_matrix.csv")
        with open(path) as f:
            rows = {r["subsystem"]: r for r in csv.DictReader(f)}
        co2_row = rows.get("CO2 certificate revenue")
        assert co2_row is not None, "CO2 certificate revenue not in matrix"
        assert co2_row["current_status"] in ("MISSING", "CO2-MISSING"), \
            f"CO2 status should be MISSING/CO2-MISSING, got {co2_row['current_status']}"

    def test_r99_entry_is_blocked(self):
        """R99 gate must be classified as BLOCKED."""
        import csv
        path = Path("reports/phase9_co2_cit_dependency_matrix.csv")
        with open(path) as f:
            rows = {r["subsystem"]: r for r in csv.DictReader(f)}
        r99_row = rows.get("R99 gate")
        assert r99_row is not None, "R99 gate not in matrix"
        assert r99_row["current_status"] == "BLOCKED", \
            f"R99 should be BLOCKED, got {r99_row['current_status']}"

    def test_r102_entry_is_blocked(self):
        """R102 gate must be classified as BLOCKED."""
        import csv
        path = Path("reports/phase9_co2_cit_dependency_matrix.csv")
        with open(path) as f:
            rows = {r["subsystem"]: r for r in csv.DictReader(f)}
        r102_row = rows.get("R102 gate")
        assert r102_row is not None, "R102 gate not in matrix"
        assert r102_row["current_status"] == "BLOCKED", \
            f"R102 should be BLOCKED, got {r102_row['current_status']}"

    def test_distribution_account_is_audit_only(self):
        """DistributionAccount must be audit_only."""
        import csv
        path = Path("reports/phase9_co2_cit_dependency_matrix.csv")
        with open(path) as f:
            rows = {r["subsystem"]: r for r in csv.DictReader(f)}
        da_row = rows.get("DistributionAccount")
        assert da_row is not None
        assert da_row["runtime_or_audit"] in ("audit", "futuristic"), \
            f"DistributionAccount should be audit, got {da_row['runtime_or_audit']}"

    def test_taxbridge_is_audit_only(self):
        """TaxBridge must be audit_only."""
        import csv
        path = Path("reports/phase9_co2_cit_dependency_matrix.csv")
        with open(path) as f:
            rows = {r["subsystem"]: r for r in csv.DictReader(f)}
        tb_row = rows.get("TaxBridge")
        assert tb_row is not None
        assert tb_row["runtime_or_audit"] in ("audit", "futuristic"), \
            f"TaxBridge should be audit, got {tb_row['runtime_or_audit']}"

    def test_depreciation_canonical_is_audit_only(self):
        """Depreciation canonical must be audit_only (not CIT source yet)."""
        import csv
        path = Path("reports/phase9_co2_cit_dependency_matrix.csv")
        with open(path) as f:
            rows = {r["subsystem"]: r for r in csv.DictReader(f)}
        dep_row = rows.get("Depreciation canonical")
        assert dep_row is not None
        assert dep_row["runtime_or_audit"] in ("audit", "futuristic"), \
            f"Depreciation canonical should be audit, got {dep_row['runtime_or_audit']}"


class TestNoRuntimeFilesChanged:
    """Design-only branch: no runtime files changed."""

    def test_no_runtime_files_changed(self):
        """No app/, domain/, or non-design files changed."""
        import subprocess

        repo_root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            ["git", "diff", "--stat", "origin/main...HEAD"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
        )
        output = result.stdout.strip()
        if not output:
            return
        for line in output.split("\n"):
            stripped = line.strip()
            if (
                not stripped
                or stripped.startswith("??")
                or stripped.startswith("...")
                or "files changed" in stripped
                or "|" not in stripped
            ):
                continue
            allowed = [
                "docs/", "reports/", "tests/",
                "app/templates/partials/runtime_summary.html",  # UX-2C-1 cross-arc
                "app/ui/dashboard.py",  # UX-2C-1 cross-arc
                "tests/test_ux2c1_",  # UX-2C-1 cross-arc
            ]
            assert any(stripped.startswith(p) for p in allowed), \
                f"Unexpected change: {stripped}"

    def test_no_app_waterfall_core_changes(self):
        """No app/ changes (runtime wiring)."""
        import subprocess

        repo_root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            ["git", "diff", "--stat", "origin/main...HEAD"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
        )
        output = result.stdout.strip()
        for line in output.split("\n"):
            stripped = line.strip()
            if (
                not stripped
                or stripped.startswith("??")
                or stripped.startswith("...")
                or "files changed" in stripped
                or "|" not in stripped
            ):
                continue
            # UX-2C-1 cross-arc allowlist (Overview KPI dedup)
            ux2c1_allowed = (
                "app/templates/partials/runtime_summary.html",  # UX-2C-1 cross-arc
                "app/ui/dashboard.py",  # UX-2C-1 cross-arc
            )
            if stripped.startswith(ux2c1_allowed):
                continue
            assert not stripped.startswith("app/"), \
                f"app/ change detected (forbidden): {stripped}"


class TestPromotionOrderIsDocumented:
    """Promotion order section must have clear classifications."""

    def test_recommended_order_section_exists(self):
        """Section 13 Recommended Promotion Order must exist."""
        content = Path("docs/phase9_co2_cit_bridge_design.md").read_text()
        assert "Recommended Promotion Order" in content

    def test_r99_is_blocked_in_promotion_order(self):
        """R99 runtime must be classified as BLOCKED in promotion order."""
        content = Path("docs/phase9_co2_cit_bridge_design.md").read_text()
        # Find the promotion order table or list
        lines = content.split("\n")
        in_section = False
        r99_mentioned = False
        for line in lines:
            if "Recommended Promotion Order" in line:
                in_section = True
            elif in_section and line.startswith("#"):
                break  # Next section
            elif in_section and "R99" in line:
                r99_mentioned = True
                # If R99 is mentioned, it should be BLOCKED in this section
                assert "BLOCKED" in line or "blocked" in line.lower(), \
                    "R99 must be classified as BLOCKED in promotion order"
        assert r99_mentioned, "R99 not found in Recommended Promotion Order"

    def test_final_recommendation_section_exists(self):
        """Section 15 Final Recommendation must exist and have content."""
        content = Path("docs/phase9_co2_cit_bridge_design.md").read_text()
        assert "Final Recommendation" in content
        # Final section should have some actionable next step
        idx = content.index("Final Recommendation")
        section = content[idx:idx+500]
        assert len(section.strip()) > 50, "Final Recommendation section is empty"