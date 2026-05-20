"""Phase 7F Oborovo OpEx fix — tests verifying no code fix was needed."""
import pytest
from pathlib import Path
import csv

from app.project_factories import create_default_oborovo, create_default_tuho_wind1
from app.ui_runner import run_demo_project


def _rows_by_project_metric():
    rows = {}
    for r in csv.DictReader(open("reports/phase9_tuho_oborovo_calibration_comparison.csv")):
        key = (r["project"], r["metric"])
        rows[key] = r
    return rows


# =============================================================================
# Test 1: Oborovo OpEx Y1 is already 1,338 kEUR (no fix needed)
# =============================================================================
class TestOborovoOpExAlreadyFixed:
    """Oborovo Y1 OpEx = 1,338 kEUR — confirmed correct in factory.

    Earlier reported gap (~1,998 kEUR) was from stale data in PR #129 CSV.
    The create_default_oborovo() factory already produces correct values.
    """

    def test_factory_opex_total_is_1338(self):
        ob = create_default_oborovo()
        total_y1 = sum(item.y1_amount_keur for item in ob.opex)
        assert abs(total_y1 - 1338.0) < 1.0, \
            f"Oborovo Y1 OpEx {total_y1:.1f} kEUR should be 1,338 kEUR"

    def test_technical_management_is_198(self):
        ob = create_default_oborovo()
        by_name = {item.name: item.y1_amount_keur for item in ob.opex}
        assert by_name.get("Technical Management", 0) == 198.0, \
            "Technical Management should be 198 kEUR (no sub-items)"

    def test_infrastructure_maintenance_is_244(self):
        ob = create_default_oborovo()
        by_name = {item.name: item.y1_amount_keur for item in ob.opex}
        assert by_name.get("Infrastructure Maintenance", 0) == 244.0, \
            "Infrastructure Maintenance should be 244 kEUR"

    def test_environmental_social_is_32(self):
        ob = create_default_oborovo()
        by_name = {item.name: item.y1_amount_keur for item in ob.opex}
        assert by_name.get("Environmental&Social", 0) == 32.0, \
            "Environmental&Social should be 32 kEUR (not 200)"

    def test_csv_opex_status_is_ok(self):
        rows = _rows_by_project_metric()
        assert rows[("OBOROVO", "OpEx Y1 (kEUR)")]["status"] == "OK", \
            "Oborovo OpEx should be OK in CSV (was incorrectly marked FAIL in PR #129)"

    def test_csv_opex_model_value_is_1338(self):
        rows = _rows_by_project_metric()
        assert rows[("OBOROVO", "OpEx Y1 (kEUR)")]["model_value"] == "1338", \
            "CSV should show model_value=1338 (not 1998)"


# =============================================================================
# Test 2: TUHO OpEx is 1,998 kEUR (separate from Oborovo)
# =============================================================================
class TestTuhoOpEx:
    def test_tuho_opex_is_1998(self):
        tu = create_default_tuho_wind1()
        total_y1 = sum(item.y1_amount_keur for item in tu.opex)
        assert abs(total_y1 - 1998.0) < 1.0, \
            f"TUHO Y1 OpEx {total_y1:.1f} kEUR should be 1,998 kEUR"

    def test_csv_tuho_opex_is_ok(self):
        rows = _rows_by_project_metric()
        assert rows[("TUHO", "OpEx Y1 (kEUR)")]["status"] == "OK", \
            "TUHO OpEx should be OK in CSV"


# =============================================================================
# Test 3: Oborovo distributions model matches Excel
# =============================================================================
class TestOborovoDistributions:
    def test_oborovo_distributions_csv_is_ok(self):
        rows = _rows_by_project_metric()
        assert rows[("OBOROVO", "Total Distributions (kEUR)")]["status"] == "OK", \
            "Oborovo Total Distributions should be OK in CSV (was incorrectly marked FAIL in PR #129)"


# =============================================================================
# Test 4: Oborovo DSCR/IRR still have calibration gaps (not OpEx issues)
# =============================================================================
class TestOborovoCalibrationGaps:
    """Oborovo has non-OpEx calibration gaps documented as WARN."""

    def test_oborovo_avg_dscr_is_warn(self):
        rows = _rows_by_project_metric()
        assert rows[("OBOROVO", "Avg DSCR")]["status"] == "WARN", \
            "Oborovo Avg DSCR is WARN (model=1.229 vs Excel=1.147)"

    def test_oborovo_equity_irr_is_warn(self):
        rows = _rows_by_project_metric()
        assert rows[("OBOROVO", "Equity IRR")]["status"] == "WARN", \
            "Oborovo Equity IRR is WARN (model=9.17% vs Excel=10.60%)"

    def test_oborovo_project_irr_is_ok(self):
        rows = _rows_by_project_metric()
        assert rows[("OBOROVO", "Project IRR")]["status"] == "OK", \
            "Oborovo Project IRR is OK (model=7.98% vs Excel=7.96%)"


# =============================================================================
# Test 5: Fix doc exists and describes correct findings
# =============================================================================
class TestFixDoc:
    def test_fix_doc_exists(self):
        assert Path("docs/phase7f_oborovo_opex_fix.md").exists()

    def test_fix_doc_says_no_fix_needed(self):
        doc = Path("docs/phase7f_oborovo_opex_fix.md").read_text()
        assert "NO FIX NEEDED" in doc

    def test_fix_doc_explains_stale_csv(self):
        doc = Path("docs/phase7f_oborovo_opex_fix.md").read_text()
        assert "stale" in doc.lower() or "incorrect" in doc.lower()
        assert "1,998" in doc  # mentions the wrong value


# =============================================================================
# Test 6: No runtime changes
# =============================================================================
def test_no_runtime_changes():
    import subprocess
    result = subprocess.run(
        ["git", "diff", "--stat", "origin/main...HEAD"],
        cwd="/root/.openclaw/workspace/finco1",
        capture_output=True, text=True,
    )
    output = result.stdout.strip()
    if not output:
        return
    for line in output.split("\n"):
        if not line.strip() or line.strip().startswith("??"):
            continue
        allowed = ["docs/", "reports/", "tests/"]
        assert any(line.strip().startswith(p) for p in allowed), \
            f"Unexpected non-doc/report/test change: {line}"
