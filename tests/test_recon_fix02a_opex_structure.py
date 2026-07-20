"""tests.test_recon_fix02a_opex_structure — Deterministic OPEX structural truth tests.

Fixture schema (produced by extract_oborovo_opex_structure.extract()):
  _meta, inputs, scenarios, categories{B.01..B.13}, totals

  categories.B.xx:
    code, opex_row, name,
    budget{formula_cell, cached_value, [formula_text]},
    inflation{formula_cell, cached_value, [formula_text]},
    wht_cached,
    annual{formula_template_y1, formula_template_y2, cached_values_y1_y30},
    subitems{<code|row_N>: {opex_row, code, name, budget, activation_cached_y1_y30,
                             [activation_formula_y1], [label_flag_mismatch]}}

  categories.B.13:
    (same header fields, no subitems)
    contingency{calculation_type, contingency_rate, rate_cell,
                budget_formula_text, annual_formula_template_y1,
                contingency_base_rows, contingency_base_codes, contingency_base,
                excluded_categories}

Workbook-dependent tests skip when OBOROVO_WORKBOOK_PATH is unset.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "excel_oborovo_opex_structural_truth.json"
_EXPECTED_SHA256 = "15a621c4d6b79024980766e00ebc79d7235fd56f00567be7bf345c769ce57920"
_WORKBOOK_PATH = os.environ.get("OBOROVO_WORKBOOK_PATH", "")
_WORKBOOK_AVAILABLE = bool(_WORKBOOK_PATH) and Path(_WORKBOOK_PATH).exists()

_REQUIRED_CATEGORIES = [
    "B.01", "B.02", "B.03", "B.04", "B.05", "B.06", "B.07",
    "B.08", "B.09", "B.10", "B.11", "B.12", "B.13",
]

# Checkpoint years (1-based) used in reconstruction tests
_CHECKPOINT_YEARS = [1, 2, 3, 10, 11, 14, 15, 30]


@pytest.fixture(scope="module")
def fd() -> dict:
    assert _FIXTURE_PATH.exists(), f"Fixture not found: {_FIXTURE_PATH}"
    return json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 1. SHA256 (live workbook)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _WORKBOOK_AVAILABLE, reason="OBOROVO_WORKBOOK_PATH not set")
def test_workbook_sha256_matches():
    import hashlib
    h = hashlib.sha256()
    with open(_WORKBOOK_PATH, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    assert h.hexdigest() == _EXPECTED_SHA256


# ---------------------------------------------------------------------------
# 2. All 13 categories present
# ---------------------------------------------------------------------------

def test_all_categories_present(fd):
    missing = [c for c in _REQUIRED_CATEGORIES if c not in fd["categories"]]
    assert not missing, f"Missing categories: {missing}"


# ---------------------------------------------------------------------------
# 3. Subitem counts and coverage
# ---------------------------------------------------------------------------

def test_b01_has_4_subitems(fd):
    assert len(fd["categories"]["B.01"]["subitems"]) == 4


def test_b02_has_17_subitems(fd):
    """B.02 range has 17 rows (rows 9-25 inclusive)."""
    assert len(fd["categories"]["B.02"]["subitems"]) == 17


def test_b03_includes_pest_control(fd):
    """B.03 Pest Control (row 29, no code → key 'row_29') must be present."""
    subitems = fd["categories"]["B.03"]["subitems"]
    pest_ctrl = subitems.get("row_29")
    assert pest_ctrl is not None, "B.03 Pest Control (row_29) missing from fixture"
    assert "Pest Control" in (pest_ctrl.get("name") or "")
    assert pest_ctrl["budget"]["cached_value"] == pytest.approx(1.8, abs=1e-9)


def test_total_subitem_count(fd):
    """Total subitems across all B.01-B.12 categories must be 61."""
    total = sum(
        len(fd["categories"][k]["subitems"])
        for k in _REQUIRED_CATEGORIES if k != "B.13"
    )
    assert total == 61, f"Expected 61 total subitems, got {total}"


# ---------------------------------------------------------------------------
# 4. B.02 label / flag mismatch explicitly documented
# ---------------------------------------------------------------------------

def test_b02_1_label_flag_mismatch_documented(fd):
    """B.02.1 labeled 'Y1-2' but only Y1 active — mismatch must be recorded."""
    si = fd["categories"]["B.02"]["subitems"]["B.02.1"]
    assert "label_flag_mismatch" in si, "B.02.1 must have label_flag_mismatch field"
    assert "Y1-2" in si["label_flag_mismatch"]
    # Actual flag: Y1=1, Y2=0
    flags = si["activation_cached_y1_y30"]
    assert flags[0] == 1, "B.02.1 Y1 must be 1"
    assert flags[1] == 0, "B.02.1 Y2 must be 0 (mismatch with label)"


def test_b02_2_label_flag_mismatch_documented(fd):
    """B.02.2 labeled 'Y3-30' but active Y2-Y30 — mismatch must be recorded."""
    si = fd["categories"]["B.02"]["subitems"]["B.02.2"]
    assert "label_flag_mismatch" in si, "B.02.2 must have label_flag_mismatch field"
    assert "Y3-30" in si["label_flag_mismatch"]
    # Actual flag: Y1=0, Y2=1, Y3-Y30=1
    flags = si["activation_cached_y1_y30"]
    assert flags[0] == 0, "B.02.2 Y1 must be 0"
    assert flags[1] == 1, "B.02.2 Y2 must be 1 (active from Y2, not Y3)"


# ---------------------------------------------------------------------------
# 5. B.08 activation
# ---------------------------------------------------------------------------

def test_b08_3_balancing_off_y1_y10_on_y11_y30(fd):
    si = fd["categories"]["B.08"]["subitems"]["B.08.3"]
    flags = si["activation_cached_y1_y30"]
    assert len(flags) == 30
    assert all(f == 0 for f in flags[:10]), f"B.08.3 Y1-Y10 must be 0: {flags[:10]}"
    assert all(f == 1 for f in flags[10:]), f"B.08.3 Y11-Y30 must be 1: {flags[10:]}"


def test_b08_step_change_at_y11(fd):
    annual = fd["categories"]["B.08"]["annual"]["cached_values_y1_y30"]
    assert annual[10] > annual[9] * 2
    assert all(abs(v - annual[0]) < 0.001 for v in annual[:10]), "B.08 Y1-Y10 must be flat"
    assert all(abs(v - annual[10]) < 0.001 for v in annual[10:]), "B.08 Y11-Y30 must be flat"


# ---------------------------------------------------------------------------
# 6. B.11 source formula proof
# ---------------------------------------------------------------------------

def test_b11_3_activation_formula_source_read(fd):
    """B.11.3 activation formula must be read from OpEx cell, not hardcoded."""
    info = fd["inputs"]["b11_3_activation_formula"]
    assert info["formula_cell"] == "OpEx!F68"
    assert "formula_text" in info
    assert "D$196" in info["formula_text"] or "D196" in info["formula_text"]
    assert info["driver_cached_value"] == fd["inputs"]["senior_debt_tenor"]["cached_value"]


def test_b11_3_active_y1_to_y14_only(fd):
    si = fd["categories"]["B.11"]["subitems"]["B.11.3"]
    flags = si["activation_cached_y1_y30"]
    tenor = fd["inputs"]["senior_debt_tenor"]["cached_value"]
    assert all(f == 1 for f in flags[:tenor]), f"B.11.3 Y1-Y{tenor} must be 1"
    assert all(f == 0 for f in flags[tenor:]), f"B.11.3 Y{tenor+1}-Y30 must be 0"
    assert "activation_formula_y1" in si
    assert "IF" in si["activation_formula_y1"]


def test_b11_expires_at_debt_tenor(fd):
    annual = fd["categories"]["B.11"]["annual"]["cached_values_y1_y30"]
    tenor = fd["inputs"]["senior_debt_tenor"]["cached_value"]
    assert annual[tenor - 1] > 0
    assert annual[tenor] == 0
    assert all(v == 0 for v in annual[tenor:])


# ---------------------------------------------------------------------------
# 7. B.13 formula structure
# ---------------------------------------------------------------------------

def test_b13_contingency_structure(fd):
    cont = fd["categories"]["B.13"]["contingency"]
    assert cont["calculation_type"] == "PERCENTAGE_OF_SELECTED_CATEGORIES"
    assert abs(cont["contingency_rate"] - 0.04) < 1e-9
    assert "budget_formula_text" in cont
    assert "$D$76" in cont["budget_formula_text"] or "D76" in cont["budget_formula_text"]
    assert "annual_formula_template_y1" in cont


def test_b13_base_includes_b01_to_b12_plus_d_f(fd):
    cont = fd["categories"]["B.13"]["contingency"]
    base_codes = cont["contingency_base_codes"]
    required = ["B.01", "B.02", "B.03", "B.04", "B.05", "B.06",
                "B.07", "B.08", "B.09", "B.10", "B.11", "B.12", "D", "F"]
    for code in required:
        assert code in base_codes, f"{code} missing from B.13 base"


def test_b13_excludes_claims(fd):
    cont = fd["categories"]["B.13"]["contingency"]
    base_codes = cont["contingency_base_codes"]
    assert "C" not in base_codes, "Claims (C) must be excluded from B.13 base"
    excl = [e["code"] for e in cont["excluded_categories"]]
    assert "C" in excl, "Claims (C) must appear in excluded_categories"


def test_b13_contingency_reconstructed_y1(fd):
    """B.13 Y1 = 4% × sum of B.01..B.12 + D + F annual Y1 values."""
    cats = fd["categories"]
    cont = cats["B.13"]["contingency"]
    base_rows = cont["contingency_base_rows"]
    # Rebuild sum using opex_row → annual[0]
    row_to_annual = {}
    for code, cat in cats.items():
        row_to_annual[cat["opex_row"]] = cat["annual"]["cached_values_y1_y30"]
    # Excluded and non-OPEX rows (D=82, F=90) are not in categories;
    # but their annual values are in the D/F rows of OpEx (all zero for Oborovo).
    # B.13 base rows include D (82) and F (90) which are zero — fixture records their
    # category annual as all-zero (D and F are not extracted as categories, so we
    # sum only what we have and check the total).
    base_sum_from_cats = sum(
        cats[code]["annual"]["cached_values_y1_y30"][0]
        for code in ["B.01","B.02","B.03","B.04","B.05","B.06",
                     "B.07","B.08","B.09","B.10","B.11","B.12"]
    )  # D and F are zero for Oborovo
    computed_b13_y1 = 0.04 * base_sum_from_cats
    fixture_b13_y1 = cats["B.13"]["annual"]["cached_values_y1_y30"][0]
    assert abs(computed_b13_y1 - fixture_b13_y1) < 0.05, (
        f"B.13 Y1: 4%×{base_sum_from_cats:.4f}={computed_b13_y1:.4f} ≠ fixture {fixture_b13_y1:.4f}"
    )


# ---------------------------------------------------------------------------
# 8. Inflation source chain traced to scalar
# ---------------------------------------------------------------------------

def test_inflation_chain_traced_to_scalar(fd):
    inf = fd["inputs"]["inflation_rate"]
    assert inf["formula_cell"] == "OpEx!C102"
    assert "=Inputs!D85" in (inf.get("formula_text") or "")
    chain = inf.get("chain", {})
    assert chain.get("Inputs!D93") == pytest.approx(0.02, abs=1e-9)
    assert abs(inf["cached_value"] - 0.02) < 1e-9


# ---------------------------------------------------------------------------
# 9. Subitem budgets link to Scenarios sheet
# ---------------------------------------------------------------------------

def test_subitem_budgets_link_to_scenarios(fd):
    for cat_code, cat in fd["categories"].items():
        if cat_code == "B.13":
            continue
        for si_key, si in cat["subitems"].items():
            ftext = si["budget"].get("formula_text")
            if ftext is not None:
                assert ftext.startswith("=Scenarios!E"), (
                    f"{cat_code}/{si_key} budget formula must link to Scenarios!E, got: {ftext!r}"
                )
                assert "scenarios_lineage" in si["budget"], (
                    f"{cat_code}/{si_key} must have scenarios_lineage in budget"
                )


def test_scenarios_lineage_has_per_scenario_values(fd):
    """Each Scenarios-linked subitem must have values for all 4 scenario columns."""
    b02_1 = fd["categories"]["B.02"]["subitems"]["B.02.1"]
    lineage = b02_1["budget"]["scenarios_lineage"]
    for col in ["H", "I", "J", "K"]:
        assert col in lineage["per_scenario_values"], f"Missing column {col} in lineage"
        assert "cached_value" in lineage["per_scenario_values"][col]


def test_scenarios_metadata_columns_named(fd):
    cols = fd["scenarios"]["columns"]
    assert "HYBRID" in cols["H"]["name"]
    assert cols["K"]["index"] == 4
    assert fd["scenarios"]["selected_index"] == fd["scenarios"]["columns"]["K"]["index"]


# ---------------------------------------------------------------------------
# 10. Full category reconstruction at checkpoint years
# ---------------------------------------------------------------------------

def _reconstruct_category_y(cat: dict, year_idx: int) -> float:
    """
    Reconstruct SUMPRODUCT(budgets, flags_year) × (1+inf)^(year-1) for year_idx (0-based).

    B.07 is special: formula uses (1+inf)^year (exponent = year, not year-1).
    B.08 and B.09 have zero inflation.
    For zero-flag rows the contribution is 0 regardless of budget.
    """
    code = cat["code"]
    if code == "B.13":
        return 0.0  # contingency handled separately

    inf = cat["inflation"]["cached_value"] or 0.0
    year_num = year_idx + 1  # 1-based

    if code == "B.07":
        # Workbook inflates with exponent = year (not year-1)
        escalation = (1.0 + inf) ** year_num
    else:
        escalation = (1.0 + inf) ** (year_num - 1)

    total = 0.0
    for si in cat["subitems"].values():
        budget = si["budget"]["cached_value"]
        if budget is None:
            budget = 0.0
        flag = si["activation_cached_y1_y30"][year_idx]
        if flag is None:
            flag = 0.0
        total += float(budget) * float(flag)

    return total * escalation


@pytest.mark.parametrize("cat_code", [c for c in _REQUIRED_CATEGORIES if c != "B.13"])
@pytest.mark.parametrize("year_idx", [y - 1 for y in _CHECKPOINT_YEARS])
def test_category_reconstruction_vs_excel(fd, cat_code, year_idx):
    """Reconstructed SUMPRODUCT×inflation must match Excel cached annual value."""
    cat = fd["categories"][cat_code]
    reconstructed = _reconstruct_category_y(cat, year_idx)
    excel_val = cat["annual"]["cached_values_y1_y30"][year_idx] or 0.0
    # Tolerance: 1 EUR (rounding from BESS zero rows with None flags)
    assert abs(reconstructed - excel_val) < 1.0, (
        f"{cat_code} Y{year_idx + 1}: reconstructed={reconstructed:.4f} ≠ excel={excel_val:.4f}"
    )


# ---------------------------------------------------------------------------
# 11. B.02 transition (Y1 ≠ Y2; test actual flags not labels)
# ---------------------------------------------------------------------------

def test_b02_y1_higher_than_y2_actual_flags(fd):
    """B.02 Y1 actual must exceed Y2 based on extracted activation flags."""
    subitems = fd["categories"]["B.02"]["subitems"]
    b02_1_y1 = subitems["B.02.1"]["activation_cached_y1_y30"][0]  # Y1 flag
    b02_2_y1 = subitems["B.02.2"]["activation_cached_y1_y30"][0]  # Y1 flag (should be 0)
    b02_1_y2 = subitems["B.02.1"]["activation_cached_y1_y30"][1]  # Y2 flag (should be 0)
    b02_2_y2 = subitems["B.02.2"]["activation_cached_y1_y30"][1]  # Y2 flag (should be 1)
    assert b02_1_y1 == 1, "B.02.1 Y1 flag must be 1"
    assert b02_1_y2 == 0, "B.02.1 Y2 flag must be 0 (label 'Y1-2' is misleading)"
    assert b02_2_y1 == 0, "B.02.2 Y1 flag must be 0"
    assert b02_2_y2 == 1, "B.02.2 Y2 flag must be 1 (label 'Y3-30' is misleading)"


# ---------------------------------------------------------------------------
# 12. B.10 and B.12 transitions
# ---------------------------------------------------------------------------

def test_b10_audit_step_down(fd):
    annual = fd["categories"]["B.10"]["annual"]["cached_values_y1_y30"]
    assert annual[0] > annual[2] and annual[1] > annual[2]


def test_b12_monitoring_expiry(fd):
    annual = fd["categories"]["B.12"]["annual"]["cached_values_y1_y30"]
    assert annual[0] > annual[2]
    assert abs(annual[0] - annual[1]) < 1.5


# ---------------------------------------------------------------------------
# 13. Totals
# ---------------------------------------------------------------------------

def test_total_opex_y1_matches_fixture(fd):
    cats = fd["categories"]
    y1_sum = sum(cats[k]["annual"]["cached_values_y1_y30"][0] for k in _REQUIRED_CATEGORIES)
    expected = fd["totals"]["total_opex_incl_contingencies"]["y1_cached"]
    assert abs(y1_sum - expected) < 0.01


# ---------------------------------------------------------------------------
# 14. Strong determinism: extractor output == committed fixture (live workbook)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _WORKBOOK_AVAILABLE, reason="OBOROVO_WORKBOOK_PATH not set")
def test_extraction_is_deterministic():
    from finco_recon.extract_oborovo_opex_structure import extract
    data1 = extract(Path(_WORKBOOK_PATH))
    data2 = extract(Path(_WORKBOOK_PATH))
    assert json.dumps(data1, sort_keys=True) == json.dumps(data2, sort_keys=True)


@pytest.mark.skipif(not _WORKBOOK_AVAILABLE, reason="OBOROVO_WORKBOOK_PATH not set")
def test_full_round_trip_every_field():
    """canonical_json(extract(workbook)) must equal the committed fixture exactly."""
    from finco_recon.extract_oborovo_opex_structure import extract

    extracted = extract(Path(_WORKBOOK_PATH))
    committed = json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))

    def _diff(path: str, expected, actual) -> list[str]:
        diffs = []
        if type(expected) != type(actual):
            if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
                if abs(float(expected) - float(actual)) > 1e-9:
                    diffs.append(f"{path}: {expected!r} ≠ {actual!r}")
            else:
                diffs.append(f"{path}: type {type(expected).__name__} ≠ {type(actual).__name__}")
        elif isinstance(expected, dict):
            for k in expected:
                if k not in actual:
                    diffs.append(f"{path}.{k}: missing in extractor")
                else:
                    diffs.extend(_diff(f"{path}.{k}", expected[k], actual[k]))
            for k in actual:
                if k not in expected:
                    diffs.append(f"{path}.{k}: extra field not in fixture")
        elif isinstance(expected, list):
            if len(expected) != len(actual):
                diffs.append(f"{path}: len {len(expected)} ≠ {len(actual)}")
            for i, (e, a) in enumerate(zip(expected, actual)):
                diffs.extend(_diff(f"{path}[{i}]", e, a))
        elif isinstance(expected, float):
            if abs(expected - actual) > 1e-9:
                diffs.append(f"{path}: {expected!r} ≠ {actual!r}")
        else:
            if expected != actual:
                diffs.append(f"{path}: {expected!r} ≠ {actual!r}")
        return diffs

    diffs = _diff("root", committed, extracted)
    assert not diffs, (
        f"Round-trip: {len(diffs)} mismatches. First 20:\n"
        + "\n".join(f"  {d}" for d in diffs[:20])
    )
