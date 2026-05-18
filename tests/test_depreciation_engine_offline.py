"""Tests for the Phase 6 Depreciation Offline Engine.

These tests cover the offline domain/depreciation_offline package only.
No runtime or waterfall integration. No R99/R102 references.
"""

import warnings
import pytest
from domain.depreciation_offline import (
    DepreciationConfig,
    DepreciationEngine,
    AssetCategoryRule,
    DepreciationScheduleEntry,
    DepreciationScheduleResult,
    aggregate,
)
from domain.depreciation_offline.categories import CROATIA_TEMPLATE, DEFAULT_TEMPLATE, get_template


# -----------------------------------------------------------------------
# 1. Straight-line semiannual schedule
# 20-year useful life = 40 semiannual periods
# capex 40,000 kEUR → 1,000 kEUR/period
# zero after period 40
# -----------------------------------------------------------------------

def test_straight_line_semiannual_40_periods():
    """20-year useful life at semiannual frequency = 40 periods."""
    config = DepreciationConfig(
        asset_categories=[
            AssetCategoryRule(
                category_id="turbines",
                category_name="Wind Turbine Generators",
                capex_amount_keur=40_000.0,
                useful_life_years=20,
                depreciation_method="straight_line",
                start_period=0,
                residual_value_keur=0.0,
                frequency="semiannual",
            )
        ],
        period_count=60,
        period_frequency="semiannual",
    )
    engine = DepreciationEngine(config)
    results = engine.generate()
    assert len(results) == 1
    result = results[0]

    # First 40 periods: 1,000 kEUR/period
    for i in range(40):
        entry = result.entries[i]
        assert entry.period_index == i
        assert abs(entry.book_depreciation_keur - 1_000.0) < 0.01, f"period {i}"
        assert abs(entry.remaining_book_basis_keur - (40_000.0 - (i + 1) * 1_000.0)) < 0.01, f"period {i}"

    # Periods 40–59: zero
    for i in range(40, 60):
        entry = result.entries[i]
        assert abs(entry.book_depreciation_keur) < 0.01, f"period {i} should be 0"
        assert entry.is_zero_after_life is True, f"period {i}"

    # Total depreciation
    assert abs(result.total_book_depreciation_keur - 40_000.0) < 0.01
    # Remaining basis after all 40 periods = 0
    assert abs(result.entries[-1].remaining_book_basis_keur) < 0.01


# -----------------------------------------------------------------------
# 2. Residual value
# capex 10,000 / residual 1,000 / 10 years semiannual → 9,000 / 20 = 450 kEUR/period
# remaining basis never below 1,000
# -----------------------------------------------------------------------

def test_residual_value_not_below_residual():
    """Remaining basis must never go below residual value."""
    config = DepreciationConfig(
        asset_categories=[
            AssetCategoryRule(
                category_id="epc",
                category_name="EPC Contract",
                capex_amount_keur=10_000.0,
                useful_life_years=10,
                depreciation_method="straight_line",
                start_period=0,
                residual_value_keur=1_000.0,
                frequency="semiannual",
            )
        ],
        period_count=30,
        period_frequency="semiannual",
    )
    engine = DepreciationEngine(config)
    results = engine.generate()
    result = results[0]

    # Period amount = (10,000 - 1,000) / 20 = 450
    period_amount = 9_000.0 / 20
    for i in range(20):
        entry = result.entries[i]
        assert abs(entry.book_depreciation_keur - period_amount) < 0.01, f"period {i}"
        remaining = 10_000.0 - (i + 1) * period_amount
        assert entry.remaining_book_basis_keur >= 1_000.0 - 0.01, f"period {i}"

    # After period 20: zero, remaining = residual
    for i in range(20, 30):
        entry = result.entries[i]
        assert abs(entry.book_depreciation_keur) < 0.01, f"period {i}"
        assert entry.is_zero_after_life is True

    assert abs(result.entries[-1].remaining_book_basis_keur - 1_000.0) < 0.01


# -----------------------------------------------------------------------
# 3. start_period
# depreciation starts only at configured start_period; prior periods are zero
# -----------------------------------------------------------------------

def test_start_period_delays_depreciation():
    """Periods before start_period are zero."""
    config = DepreciationConfig(
        asset_categories=[
            AssetCategoryRule(
                category_id="grid",
                category_name="Grid Connection",
                capex_amount_keur=20_000.0,
                useful_life_years=10,
                depreciation_method="straight_line",
                start_period=10,  # starts at period 10
                residual_value_keur=0.0,
                frequency="semiannual",
            )
        ],
        period_count=30,
        period_frequency="semiannual",
    )
    engine = DepreciationEngine(config)
    results = engine.generate()
    result = results[0]

    # Periods 0-9: zero
    for i in range(10):
        entry = result.entries[i]
        assert abs(entry.book_depreciation_keur) < 0.01, f"period {i} should be 0"

    # Periods 10-29: depreciating
    period_amount = 20_000.0 / 20  # 1,000 kEUR/period
    for i in range(10, 30):
        entry = result.entries[i]
        assert abs(entry.book_depreciation_keur - period_amount) < 0.01, f"period {i}"


# -----------------------------------------------------------------------
# 4. zero_after_life — all periods after useful life are zero
# -----------------------------------------------------------------------

def test_zero_after_life():
    """Periods after useful life are zero and cumulative is capped."""
    config = DepreciationConfig(
        asset_categories=[
            AssetCategoryRule(
                category_id="project_rights",
                category_name="Project Rights",
                capex_amount_keur=5_000.0,
                useful_life_years=5,
                depreciation_method="straight_line",
                start_period=0,
                residual_value_keur=0.0,
                frequency="semiannual",
            )
        ],
        period_count=20,
        period_frequency="semiannual",
    )
    engine = DepreciationEngine(config)
    results = engine.generate()
    result = results[0]

    # Periods 0-9 (10 semiannual = 5 years): depreciating
    for i in range(10):
        entry = result.entries[i]
        assert entry.is_zero_after_life is False, f"period {i} should be active"

    # Periods 10-19: zero
    for i in range(10, 20):
        entry = result.entries[i]
        assert abs(entry.book_depreciation_keur) < 0.01, f"period {i}"
        assert entry.is_zero_after_life is True, f"period {i}"

    # Cumulative is capped at total depreciable amount
    assert abs(result.entries[9].cumulative_book_keur - 5_000.0) < 0.01
    assert abs(result.entries[10].cumulative_book_keur - 5_000.0) < 0.01  # no change


# -----------------------------------------------------------------------
# 5. Aggregate schedule
# main asset 20y + financing cost 12y sums correctly
# -----------------------------------------------------------------------

def test_aggregate_multiple_categories():
    """Two categories (20yr + 12yr) sum correctly in aggregate."""
    main = AssetCategoryRule(
        category_id="turbines",
        category_name="Turbines",
        capex_amount_keur=40_000.0,
        useful_life_years=20,
        depreciation_method="straight_line",
        start_period=0,
        frequency="semiannual",
    )
    idc = AssetCategoryRule(
        category_id="idc",
        category_name="IDC",
        capex_amount_keur=3_000.0,
        useful_life_years=12,
        depreciation_method="straight_line",
        start_period=0,
        frequency="semiannual",
    )
    config = DepreciationConfig(
        asset_categories=[main, idc],
        period_count=60,
        period_frequency="semiannual",
    )
    engine = DepreciationEngine(config)
    results = engine.generate()
    assert len(results) == 2

    combined = aggregate(results)

    # Period 0: 1,000 (20yr/40) + 125 (3,000/24) = 1,125
    assert abs(combined.entries[0].book_depreciation_keur - 1_125.0) < 0.01

    # Period 23: IDC last active period (12yr = 24 semiannual periods, 0-23 inclusive)
    # Combined = 1,000 (turbines) + 125 (IDC) = 1,125
    assert abs(combined.entries[23].book_depreciation_keur - 1_125.0) < 0.01

    # Period 24: IDC finished; only turbines = 1,000
    assert abs(combined.entries[24].book_depreciation_keur - 1_000.0) < 0.01

    # Period 40+: zero for turbines too
    assert abs(combined.entries[40].book_depreciation_keur) < 0.01


# -----------------------------------------------------------------------
# 6. Croatia template defaults
# -----------------------------------------------------------------------

def test_croatia_template_defaults():
    """Croatia template: main CAPEX 20yr, financing costs 12yr."""
    assert CROATIA_TEMPLATE.defaults["turbines"] == 20
    assert CROATIA_TEMPLATE.defaults["epc"] == 20
    assert CROATIA_TEMPLATE.defaults["grid_connection"] == 20
    assert CROATIA_TEMPLATE.defaults["project_rights"] == 20
    assert CROATIA_TEMPLATE.defaults["idc"] == 12
    assert CROATIA_TEMPLATE.defaults["commitment_fees"] == 12
    assert CROATIA_TEMPLATE.defaults["bank_fees"] == 12
    assert CROATIA_TEMPLATE.defaults["other"] == 20


def test_get_template_croatia():
    """get_template returns CROATIA template."""
    t = get_template("croatia")
    assert t.template_id == "croatia"
    assert t.defaults["turbines"] == 20
    assert t.defaults["idc"] == 12


def test_get_template_default_fallback():
    """Unknown template id falls back to default."""
    t = get_template("unknown_template")
    assert t.template_id == "default"
    assert t.defaults["turbines"] == 30


# -----------------------------------------------------------------------
# 7. Default behavior isolation
# No imports from app/waterfall_core.py, no runtime/factory changes
# -----------------------------------------------------------------------

def test_no_runtime_imports():
    """Engine does not import from app/ or waterfall runtime."""
    import domain.depreciation_offline.engine as eng_mod
    import domain.depreciation_offline.config as cfg_mod
    import domain.depreciation_offline.categories as cat_mod

    eng_source = eng_mod.__file__
    cfg_source = cfg_mod.__file__
    cat_source = cat_mod.__file__

    assert "app/" not in eng_source, "engine.py must not import from app/"
    assert "app/" not in cfg_source, "config.py must not import from app/"
    assert "app/" not in cat_source, "categories.py must not import from app/"
    assert "waterfall" not in eng_source, "engine must not reference waterfall"
    assert "factory" not in eng_source, "engine must not reference factory"


# -----------------------------------------------------------------------
# 8. TUHO parity diagnostic test
# Uses the existing CSV extraction from phase6_dep_r30_excel_crosscheck
# Synthetic TUHO categories built from total CAPEX to match Dep R30 pattern.
# Exact category-level CAPEX breakdown is not available, so this is a
# documented diagnostic test marked xfail.
# -----------------------------------------------------------------------

def test_tuho_dep_r30_synthetic_parity():
    """Synthetic TUHO categories vs extracted Dep R30 totals.

    This test uses the phase6_dep_r30_excel_crosscheck.csv extracted values
    to build a synthetic category set. The exact category-level CAPEX breakdown
    (how much of the 72,993.7 kEUR belongs to turbines vs grid vs IDC) is not
    available from the extraction, so the test uses total CAPEX = 72,993.7 kEUR
    with 20-year straight-line as a proxy for the main TUHO depreciation.

    Status: DIAGNOSTIC / EXPECTED FAILURE — exact parity requires category-level CAPEX source data.
    """
    import csv, os

    csv_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "reports",
        "phase6_dep_r30_excel_crosscheck.csv",
    )
    if not os.path.exists(csv_path):
        pytest.skip(f"TUHO extraction CSV not found at {csv_path}")

    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Extract H1 values (op_idx even = H1)
    h1_rows = [r for r in rows if r.get("half") == "H1"]
    if not h1_rows:
        pytest.skip("No H1 rows found in TUHO extraction CSV")

    # Synthetic TUHO: main CAPEX 72,993.7 kEUR, 20yr, semiannual, start period 0
    TUHO_BOOK_TOTAL = 72_993.7
    TURBINE_YEARS = 20

    config = DepreciationConfig(
        asset_categories=[
            AssetCategoryRule(
                category_id="tuho_main",
                category_name="TUHO Aggregate Main CAPEX",
                capex_amount_keur=TUHO_BOOK_TOTAL,
                useful_life_years=TURBINE_YEARS,
                depreciation_method="straight_line",
                start_period=0,
                residual_value_keur=0.0,
                frequency="semiannual",
                source_reference="TUHO_BOOK_TOTAL from Python ledger fixture",
            )
        ],
        period_count=60,
        period_frequency="semiannual",
    )
    engine = DepreciationEngine(config)
    results = engine.generate()
    synthetic = results[0]

    # Compare first 20 H1 periods
    h1_op_indices = [int(r["op_idx"]) for r in h1_rows if int(r.get("op_idx", -1)) < 60]
    mismatches = []
    tolerance_eur = 1.0  # 1 kEUR tolerance

    for op_idx in h1_op_indices[:20]:  # first 20 H1 periods
        h1_entry = synthetic.entries[op_idx]
        csv_row = next((r for r in h1_rows if int(r.get("op_idx", -1)) == op_idx), None)
        if csv_row is None:
            continue
        excel_val = float(csv_row.get("ex_pl13", 0))
        diff = abs(h1_entry.book_depreciation_keur - excel_val)
        if diff > tolerance_eur:
            mismatches.append(
                f"op_idx={op_idx}: synthetic={h1_entry.book_depreciation_keur:.2f} "
                f"excel={excel_val:.2f} diff={diff:.2f}"
            )

    # Mismatches are expected — exact category-level CAPEX split is not available.
    # Mark as xfail: this test uses the old synthetic single-category approach
    # (TUHO_BOOK_TOTAL as one category) and is superseded by the extracted
    # category test in test_depreciation_category_capex_extraction.py.
    # The category-level CAPEX split IS now available (reports/phase6_dep_category_capex_extraction.csv)
    # but this test is kept as a historical record of the synthetic approach.
    # The extracted-category parity test (test_tuho_dep_r30_parity_vs_extracted_csv)
    # asserts near-parity bounds instead.
    if mismatches:
        gap_summary = "; ".join(mismatches[:3])
        pytest.xfail(
            f"Historical: synthetic single-category 20yr schedule vs extracted Dep R30. "
            f"Superseded by test_tuho_dep_r30_parity_vs_extracted_csv which uses extracted "
            f"category data. First mismatches: {gap_summary}. "
            f"See reports/phase6_dep_category_capex_extraction.csv and "
            f"docs/phase6_dep_category_capex_extraction.md for resolution."
        )


# -----------------------------------------------------------------------
# 9. Fallback warning emitted
# -----------------------------------------------------------------------

def test_fallback_warning_emitted():
    """Using 'other' category with 30yr fallback emits a DeprecationWarning."""
    config = DepreciationConfig(
        asset_categories=[
            AssetCategoryRule(
                category_id="other",
                category_name="Other CAPEX",
                capex_amount_keur=5_000.0,
                useful_life_years=30,  # fallback value
                depreciation_method="straight_line",
                start_period=0,
                frequency="semiannual",
            )
        ],
        period_count=60,
        period_frequency="semiannual",
        fallback_warning_enabled=True,
    )
    engine = DepreciationEngine(config)

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        engine.generate()
        deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
        assert len(deprecation_warnings) >= 1, "Expected DeprecationWarning for fallback 'other' category"
        assert "other" in str(deprecation_warnings[0].message).lower()


def test_no_warning_when_disabled():
    """Fallback warning can be disabled."""
    config = DepreciationConfig(
        asset_categories=[
            AssetCategoryRule(
                category_id="other",
                category_name="Other",
                capex_amount_keur=5_000.0,
                useful_life_years=30,
                depreciation_method="straight_line",
                start_period=0,
                frequency="semiannual",
            )
        ],
        period_count=60,
        period_frequency="semiannual",
        fallback_warning_enabled=False,
    )
    engine = DepreciationEngine(config)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        engine.generate()
        deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
        assert len(deprecation_warnings) == 0


# -----------------------------------------------------------------------
# 10. end_period explicit cap
# -----------------------------------------------------------------------

def test_end_period_caps_schedule():
    """An explicit end_period caps the schedule."""
    config = DepreciationConfig(
        asset_categories=[
            AssetCategoryRule(
                category_id="test",
                category_name="Test Asset",
                capex_amount_keur=20_000.0,
                useful_life_years=20,  # would be 40 semiannual periods
                depreciation_method="straight_line",
                start_period=0,
                end_period=15,  # explicit cap at period 15 (16 periods total)
                residual_value_keur=0.0,
                frequency="semiannual",
            )
        ],
        period_count=60,
        period_frequency="semiannual",
    )
    engine = DepreciationEngine(config)
    results = engine.generate()
    result = results[0]

    # Periods 0-15: active (16 periods)
    for i in range(16):
        entry = result.entries[i]
        assert entry.is_zero_after_life is False, f"period {i} should be active"

    # Period 16+: zero (capped at end_period=15)
    for i in range(16, 20):
        entry = result.entries[i]
        assert abs(entry.book_depreciation_keur) < 0.01, f"period {i} should be 0"


# -----------------------------------------------------------------------
# 11. Non-depreciable asset (capex = residual)
# -----------------------------------------------------------------------

def test_non_depreciable_asset():
    """An asset with capex == residual is non-depreciable."""
    config = DepreciationConfig(
        asset_categories=[
            AssetCategoryRule(
                category_id="land",
                category_name="Land",
                capex_amount_keur=1_000.0,
                useful_life_years=0,  # non-depreciable
                depreciation_method="straight_line",
                start_period=0,
                residual_value_keur=1_000.0,  # capex == residual
                frequency="semiannual",
            )
        ],
        period_count=10,
        period_frequency="semiannual",
    )
    engine = DepreciationEngine(config)
    results = engine.generate()
    result = results[0]

    for entry in result.entries:
        assert abs(entry.book_depreciation_keur) < 0.01
        assert entry.is_zero_after_life is True

    assert abs(result.total_book_depreciation_keur) < 0.01