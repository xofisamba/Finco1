"""tests.test_recon_fix02a_opex_structure — Deterministic OPEX structural truth tests.

These tests verify the fixture at tests/fixtures/excel_oborovo_opex_structural_truth.json
against the authoritative workbook SHA256.  All assertions are purely structural —
no financial engine code is called, no runtime behaviour changes.

Workbook presence:
    The authoritative workbook is available in CI only when
    OBOROVO_WORKBOOK_PATH is set.  Tests that require live extraction are
    skipped when the path is absent; fixture-only tests always run.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "excel_oborovo_opex_structural_truth.json"
_EXPECTED_SHA256 = "15a621c4d6b79024980766e00ebc79d7235fd56f00567be7bf345c769ce57920"
_WORKBOOK_PATH = os.environ.get("OBOROVO_WORKBOOK_PATH", "")
_WORKBOOK_AVAILABLE = bool(_WORKBOOK_PATH) and Path(_WORKBOOK_PATH).exists()

_REQUIRED_CATEGORIES = ["B.01", "B.02", "B.03", "B.04", "B.05", "B.06", "B.07",
                         "B.08", "B.09", "B.10", "B.11", "B.12", "B.13"]


@pytest.fixture(scope="module")
def fixture_data() -> dict:
    assert _FIXTURE_PATH.exists(), f"Fixture not found: {_FIXTURE_PATH}"
    return json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 1. Workbook SHA256 (requires live workbook)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _WORKBOOK_AVAILABLE, reason="OBOROVO_WORKBOOK_PATH not set")
def test_workbook_sha256_matches():
    """The authoritative workbook must match the pinned SHA256."""
    import hashlib
    h = hashlib.sha256()
    with open(_WORKBOOK_PATH, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    assert h.hexdigest() == _EXPECTED_SHA256


# ---------------------------------------------------------------------------
# 2. All B.01–B.13 categories present in fixture
# ---------------------------------------------------------------------------

def test_all_categories_present(fixture_data):
    """Fixture must contain all 13 OPEX categories B.01 through B.13."""
    categories = fixture_data["categories"]
    missing = [c for c in _REQUIRED_CATEGORIES if c not in categories]
    assert not missing, f"Missing categories: {missing}"


# ---------------------------------------------------------------------------
# 3. Category totals reconstruction
# ---------------------------------------------------------------------------

def test_total_opex_y1_sum_of_categories(fixture_data):
    """Sum of B.01–B.12 Y1 annual values + B.13 Y1 must equal workbook total incl. contingencies."""
    cats = fixture_data["categories"]
    b01_to_b12 = [c for k, c in cats.items() if k != "B.13"]
    sum_y1 = sum(c["annual_values_y1_y30"][0] for c in b01_to_b12)
    b13_y1 = cats["B.13"]["annual_values_y1_y30"][0]
    total_y1 = sum_y1 + b13_y1
    expected = fixture_data["totals"]["total_opex_incl_contingencies_y1"]
    assert abs(total_y1 - expected) < 0.01, (
        f"Y1 total mismatch: computed={total_y1:.4f}, expected={expected:.4f}"
    )


def test_b13_contingency_rate_applied_correctly(fixture_data):
    """B.13 Y1 = 4% × sum of B.01–B.12 Y1 annual values."""
    cats = fixture_data["categories"]
    b01_to_b12_y1 = sum(
        cats[k]["annual_values_y1_y30"][0]
        for k in _REQUIRED_CATEGORIES if k != "B.13"
    )
    computed_b13_y1 = 0.04 * b01_to_b12_y1
    fixture_b13_y1 = cats["B.13"]["annual_values_y1_y30"][0]
    assert abs(computed_b13_y1 - fixture_b13_y1) < 0.01, (
        f"B.13 Y1: 4%×{b01_to_b12_y1:.4f}={computed_b13_y1:.4f} ≠ fixture {fixture_b13_y1:.4f}"
    )


# ---------------------------------------------------------------------------
# 4. B.08 Balancing costs activation (OFF Y1-Y10, ON Y11-Y30)
# ---------------------------------------------------------------------------

def test_b08_balancing_costs_activation(fixture_data):
    """B.08.3 Balancing costs must be OFF Y1-Y10 and ON Y11-Y30."""
    subitems = fixture_data["categories"]["B.08"]["subitems"]
    # Find B.08.3 by name since subitems is a dict in the fixture
    if isinstance(subitems, dict):
        b083 = subitems.get("B.08.3") or next(
            (v for v in subitems.values() if "Balancing" in (v.get("name") or "")), None
        )
    else:
        b083 = next((s for s in subitems if "Balancing" in (s.get("name") or "")), None)

    assert b083 is not None, "B.08.3 Balancing costs not found in fixture"
    flags = b083["activation_flags"]
    assert len(flags) == 30, f"Expected 30 flags, got {len(flags)}"
    assert all(f == 0 for f in flags[:10]), f"B.08.3 should be OFF Y1-Y10, got {flags[:10]}"
    assert all(f == 1 for f in flags[10:]), f"B.08.3 should be ON Y11-Y30, got {flags[10:]}"


def test_b08_step_change_at_y11(fixture_data):
    """B.08 annual total must step up at Y11 when balancing costs activate."""
    annual = fixture_data["categories"]["B.08"]["annual_values_y1_y30"]
    y10 = annual[9]   # index 9 = Y10
    y11 = annual[10]  # index 10 = Y11
    assert y11 > y10 * 2, (
        f"B.08 should more than double at Y11 (balancing ON). Y10={y10:.2f}, Y11={y11:.2f}"
    )
    # All Y1-Y10 equal; all Y11-Y30 equal (zero inflation on B.08)
    assert all(abs(v - annual[0]) < 0.001 for v in annual[:10]), "B.08 Y1-Y10 must be flat"
    assert all(abs(v - annual[10]) < 0.001 for v in annual[10:]), "B.08 Y11-Y30 must be flat"


# ---------------------------------------------------------------------------
# 5. B.02 transition (Y1 ≠ Y2)
# ---------------------------------------------------------------------------

def test_b02_y1_y2_transition(fixture_data):
    """B.02 Y1 must differ from Y2 (O&M Y1-2 vs Y3-30 regime switch)."""
    annual = fixture_data["categories"]["B.02"]["annual_values_y1_y30"]
    assert abs(annual[0] - annual[1]) > 10, (
        f"B.02 Y1={annual[0]:.2f} and Y2={annual[1]:.2f} should differ by >10 kEUR "
        f"(regime transition)"
    )
    # Y1 > Y2: O&M Y1-2 rate (179) > Y3-30 rate (117)
    assert annual[0] > annual[1], "B.02 Y1 (higher O&M rate) must exceed Y2"


# ---------------------------------------------------------------------------
# 6. B.10 audit transition (Y1-Y2 > Y3)
# ---------------------------------------------------------------------------

def test_b10_audit_transition(fixture_data):
    """B.10 Y1-Y2 annual values must exceed Y3 (higher auditor fee expires)."""
    annual = fixture_data["categories"]["B.10"]["annual_values_y1_y30"]
    assert annual[0] > annual[2], (
        f"B.10 Y1={annual[0]:.2f} must exceed Y3={annual[2]:.2f} (auditor step-down)"
    )
    assert annual[1] > annual[2], (
        f"B.10 Y2={annual[1]:.2f} must exceed Y3={annual[2]:.2f}"
    )


# ---------------------------------------------------------------------------
# 7. B.11 expires at debt tenor year
# ---------------------------------------------------------------------------

def test_b11_expires_at_debt_tenor(fixture_data):
    """B.11 must be zero from Y15 onward (debt tenor = 14 years)."""
    annual = fixture_data["categories"]["B.11"]["annual_values_y1_y30"]
    tenor = fixture_data["inputs"]["b11_active_until_year"]
    assert annual[tenor - 1] > 0, f"B.11 Y{tenor} must be positive (last active year)"
    assert annual[tenor] == 0, f"B.11 Y{tenor + 1} must be zero (after debt expiry)"
    assert all(v == 0 for v in annual[tenor:]), f"B.11 must be zero after Y{tenor}"


# ---------------------------------------------------------------------------
# 8. B.12 monitoring expiry (Y3+ reduced)
# ---------------------------------------------------------------------------

def test_b12_monitoring_expiry(fixture_data):
    """B.12 Y1-Y2 must exceed Y3 (Fauna/Flora and E&S monitoring expires)."""
    annual = fixture_data["categories"]["B.12"]["annual_values_y1_y30"]
    assert annual[0] > annual[2], (
        f"B.12 Y1={annual[0]:.2f} must exceed Y3={annual[2]:.2f} (monitoring expires)"
    )
    # Y1 and Y2 should be equal (same flags)
    assert abs(annual[0] - annual[1]) < 1.0, (
        f"B.12 Y1={annual[0]:.2f} and Y2={annual[1]:.2f} should be close"
    )


# ---------------------------------------------------------------------------
# 9. B.13 formula — rate matches fixture
# ---------------------------------------------------------------------------

def test_b13_contingency_rate_in_fixture(fixture_data):
    """B.13 must carry contingency_rate = 0.04 in fixture."""
    b13 = fixture_data["categories"]["B.13"]
    assert "contingency_rate" in b13, "B.13 must have contingency_rate field"
    assert abs(b13["contingency_rate"] - 0.04) < 1e-9, (
        f"B.13 contingency_rate must be 0.04, got {b13['contingency_rate']}"
    )


# ---------------------------------------------------------------------------
# 10. Extraction determinism (re-extract and compare if workbook available)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _WORKBOOK_AVAILABLE, reason="OBOROVO_WORKBOOK_PATH not set")
def test_extraction_is_deterministic():
    """Re-extracting the workbook must produce the same SHA256 and category count."""
    from finco_recon.extract_oborovo_opex_structure import extract
    data1 = extract(Path(_WORKBOOK_PATH))
    data2 = extract(Path(_WORKBOOK_PATH))
    assert data1["_meta"]["source_sha256"] == data2["_meta"]["source_sha256"]
    assert set(data1["categories"]) == set(data2["categories"])
    for code in data1["categories"]:
        v1 = data1["categories"][code]["annual_values_y1_y30"]
        v2 = data2["categories"][code]["annual_values_y1_y30"]
        assert v1 == v2, f"Non-deterministic annual values for {code}"
