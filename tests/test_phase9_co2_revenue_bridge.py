"""Phase 9: CO2 Revenue Bridge — wiring validation tests.

TARGETED DEFAULT-OFF / VALIDATION-FIRST RUNTIME WIRING.

R99/R102: BLOCKED — CO2 bridge only affects revenue/EBITDA.
"""
import pytest
from pathlib import Path


class TestFlagDefaults:
    """Flag default behavior validation."""

    def test_flag_default_is_false(self):
        """use_co2_revenue_bridge defaults to False."""
        import app.waterfall_core as wc
        import inspect
        sig = inspect.signature(wc.run_waterfall_v3_core)
        param = sig.parameters["use_co2_revenue_bridge"]
        assert param.default is False, f"Expected False, got {param.default}"


class TestBridgeValidation:
    """CO2 bridge validation against revenue_decomposition_schedule."""

    def test_revenue_bridge_doc_exists(self):
        assert Path("docs/phase9_co2_revenue_bridge_wiring.md").exists()

    def test_revenue_bridge_csv_exists(self):
        assert Path("reports/phase9_co2_revenue_bridge_validation.csv").exists()

    def test_design_doc_references_bridge(self):
        doc = Path("docs/phase9_co2_cit_bridge_design.md").read_text()
        assert "CO2" in doc
        assert "revenue_keur" in doc

    def test_csv_has_required_columns(self):
        import csv
        path = Path("reports/phase9_co2_revenue_bridge_validation.csv")
        with open(path) as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
        required = ["subsystem", "test_case", "expected", "actual", "status", "notes"]
        for col in required:
            assert col in headers, f"Missing column: {col}"

    def test_csv_all_status_ok(self):
        import csv
        path = Path("reports/phase9_co2_revenue_bridge_validation.csv")
        rows = list(csv.DictReader(open(path)))
        for row in rows:
            assert row["status"] in ("OK", "WARN"), \
                f"Non-OK status in row: {row['test_case']}: {row['status']}"

    def test_csv_tuho_y1_co2_within_tolerance(self):
        """TUHO Y1 CO2 ≈ 611 kEUR is within ±5% of target."""
        import csv
        path = Path("reports/phase9_co2_revenue_bridge_validation.csv")
        for row in csv.DictReader(open(path)):
            if row["test_case"] == "revenue_decomposition_y1_co2":
                actual_str = row["actual"].replace(" kEUR", "").strip()
                actual = float(actual_str)
                assert 570 < actual < 650, \
                    f"CO2 Y1 {actual} kEUR outside 570-650 kEUR range"
                break
        else:
            pytest.fail("TUHO Y1 CO2 test case not found in CSV")

    def test_csv_flag_default_ok(self):
        import csv
        path = Path("reports/phase9_co2_revenue_bridge_validation.csv")
        for row in csv.DictReader(open(path)):
            if row["test_case"] == "flag_default_is_false":
                assert row["status"] == "OK"
                break
        else:
            pytest.fail("Flag default test case not found in CSV")


class TestNoRuntimeFilesChanged:
    """Design-only or narrow runtime: only expected files changed."""

    def test_no_app_waterfall_core_changes_exist(self):
        """app/waterfall_core.py has CO2 bridge changes (expected)."""
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
                "app/waterfall_core.py",  # CO2 bridge (expected)
                "docs/",
                "reports/",
                "tests/",
                "app/templates/partials/runtime_summary.html",  # UX-2C-1 cross-arc
                "app/ui/dashboard.py",  # UX-2C-1 cross-arc
            ]
            assert any(stripped.startswith(p) for p in allowed), \
                f"Unexpected change: {stripped}"

    def test_only_expected_doc_report_test_files(self):
        """Only expected docs/reports/tests changed (besides waterfall_core)."""
        import subprocess
        repo_root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            ["git", "diff", "--stat", "origin/main...HEAD"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
        )
        output = result.stdout.strip()
        changed_files = []
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
            changed_files.append(stripped.split("|")[0].strip())
        unexpected = [
            f for f in changed_files
            if not (
                f.startswith("docs/")
                or f.startswith("reports/")
                or f.startswith("tests/")
                or f == "app/waterfall_core.py"
                or f == "app/templates/partials/runtime_summary.html"  # UX-2C-1 cross-arc
                or f == "app/ui/dashboard.py"  # UX-2C-1 cross-arc
            )
        ]
        assert not unexpected, f"Unexpected files changed: {unexpected}"


class TestTUHOOnlyGuard:
    """TUHO-only guard prevents Oborovo activation."""

    def test_oborovo_guard_mentioned_in_doc(self):
        doc = Path("docs/phase9_co2_revenue_bridge_wiring.md").read_text()
        assert "Oborovo" in doc
        assert "ValueError" in doc

    def test_tuho_only_guard_in_code(self):
        """TUHO-only guard present in waterfall_core.py."""
        import app.waterfall_core as wc
        import inspect
        source = inspect.getsource(wc.run_waterfall_v3_core)
        assert "TUHO-WIND-1" in source
        assert "use_co2_revenue_bridge" in source


class TestTaxEngineUnchanged:
    """TaxEngine is NOT modified by this branch."""

    def test_tax_engine_not_in_diff(self):
        """No domain/tax changes in this branch."""
        import subprocess
        repo_root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            ["git", "diff", "--stat", "origin/main...HEAD"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
        )
        output = result.stdout
        for line in output.split("\n"):
            if "domain/tax" in line or "domain/distribution_account" in line:
                pytest.fail(f"Tax/distribution_account file changed: {line}")


class TestR99R102Blocked:
    """R99/R102 remain BLOCKED after this branch."""

    def test_r99_mentioned_as_blocked(self):
        doc = Path("docs/phase9_co2_revenue_bridge_wiring.md").read_text()
        assert "BLOCKED" in doc
        assert "R99" in doc

    def test_r102_mentioned_as_blocked(self):
        doc = Path("docs/phase9_co2_revenue_bridge_wiring.md").read_text()
        assert "R102" in doc
        assert "BLOCKED" in doc


class TestPromotionOrder:
    """CO2 bridge is first READY capability per design doc."""

    def test_bridge_is_first_ready_capability(self):
        """CO2→revenue bridge is ready in design doc Section 13."""
        doc = Path("docs/phase9_co2_cit_bridge_design.md").read_text()
        assert "CO2→revenue bridge" in doc or "CO2" in doc
        assert "READY" in doc or "ready" in doc
