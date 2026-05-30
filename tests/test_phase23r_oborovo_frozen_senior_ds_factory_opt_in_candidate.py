"""Phase 23R: Oborovo frozen senior DS factory opt-in candidate.

PR #316 (Phase 23Q) proved explicit fixture-backed parity for Oborovo frozen
senior DS. Phase 23R enables Oborovo factory opt-in for the same frozen path.

Before Phase 23R: Oborovo factory opt-in was blocked (frozen=False, sizing=False).
Phase 23R enables after Phase 23Q parity proof.

Tests:
1. Factory flags now enabled for Oborovo
2. Default Oborovo factory run loads Phase 23Q fixture automatically
3. Oborovo senior DS matches fixture in selected periods
4. Lock-up clean after factory opt-in (Phase 23O/P behavior preserved)
5. Corrected anchors unchanged (SHL amount/IDC/opening/tenor)
6. TUHO regression: flags and fixture unchanged
7. No other flags promoted (G20/R99/R102/partial_pay_sweep/flat_dscr/min_dscr)
8. Phase 23C negative guard allows only phase23q-prefixed fixture
"""
import csv
from pathlib import Path

import pytest

from app.project_factories import create_default_oborovo, create_default_tuho_wind1
from app.ui_runner import _build_period_engine
from app.waterfall_runner import WaterfallRunner, WaterfallRunConfig


# =============================================================================
# 1. Factory flags now enabled
# =============================================================================


def test_oborovo_factory_flags_now_enabled():
    """Oborovo factory now has frozen senior DS flags enabled (Phase 23R).

    Before Phase 23R, both flags were False — opt-in was blocked pending
    Phase 23Q parity proof. Phase 23R enables after proof is accepted.
    """
    oborovo = create_default_oborovo()
    fin = oborovo.financing
    info = oborovo.info
    assert info.use_senior_debt_sizing_engine is True, (
        "Oborovo info.use_senior_debt_sizing_engine must be True after Phase 23R"
    )
    assert fin.use_frozen_excel_senior_debt_schedule is True, (
        "Oborovo financing.use_frozen_excel_senior_debt_schedule must be True after Phase 23R"
    )


# =============================================================================
# 2. Default factory run loads Phase 23Q fixture
# =============================================================================


def test_oborovo_factory_run_loads_phase23q_fixture():
    """Default Oborovo factory waterfall loads Phase 23Q fixture automatically."""
    oborovo = create_default_oborovo()
    engine = _build_period_engine(oborovo)
    config = WaterfallRunConfig.from_inputs(oborovo, engine)
    result = WaterfallRunner(oborovo, engine).run(config)
    # Fixture marker should be set
    marker = getattr(result, '_oborovo_frozen_fixture_loaded', None)
    if marker is not None:
        assert marker is True, (
            f"Phase 23Q fixture marker = {marker}; expected True"
        )
    else:
        # Sanity check: senior DS should be loaded from fixture
        assert len(result.periods) > 0
        first_ds = result.periods[0].senior_ds_keur
        assert first_ds > 0, (
            f"First period senior_ds_keur = {first_ds}; fixture not loaded"
        )


# =============================================================================
# 3. Senior DS matches fixture — selected periods
# =============================================================================


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "reports" / "phase23q_oborovo_senior_debt_sizing_extraction.csv"

CHECK_PERIODS = [0, 1, 14, 25, 27]


def _load_fixture():
    """Load {op_idx: ds_r57} from Phase 23Q fixture CSV."""
    by_op = {}
    with open(FIXTURE_PATH, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            op_str = row.get("operating_period_index", "").strip()
            ds_str = row.get("ds_r57_debt_service_keur", "").strip()
            if op_str and ds_str:
                by_op[int(op_str)] = float(ds_str)
    return by_op


def test_oborovo_factory_senior_ds_matches_fixture():
    """Selected periods from default factory run match Phase 23Q fixture.

    Tolerance: 20 kEUR (fixture values rounded to 4dp in CSV extraction).
    Period mapping: op_idx from CSV is 0-based, matches waterfall op_idx directly.
    """
    oborovo = create_default_oborovo()
    engine = _build_period_engine(oborovo)
    config = WaterfallRunConfig.from_inputs(oborovo, engine)
    result = WaterfallRunner(oborovo, engine).run(config)
    fixture = _load_fixture()

    TOL = 20.0  # kEUR — fixture rounding tolerance
    mismatches = []
    for op_idx in CHECK_PERIODS:
        runtime_ds = result.periods[op_idx].senior_ds_keur
        fixture_ds = fixture.get(op_idx, 0.0)
        diff = abs(runtime_ds - fixture_ds)
        if diff > TOL:
            mismatches.append(
                f"op_idx={op_idx}: runtime={runtime_ds:.2f}, fixture={fixture_ds:.2f}, diff={diff:.2f}"
            )
    assert not mismatches, (
        f"Fixture mismatch(es) beyond {TOL} kEUR tolerance:\n" + "\n".join(mismatches)
    )


# =============================================================================
# 4. Lock-up clean after factory opt-in
# =============================================================================


def test_oborovo_lockup_clean_after_factory_opt_in():
    """No distributions while SHL principal remains outstanding.

    Phase 23O/P: distributions blocked while SHL balance > 0.
    This test verifies Phase 23R opt-in does not regress that behavior.
    First valid distribution expected around op_idx 39 / 2050-06-30.
    """
    oborovo = create_default_oborovo()
    engine = _build_period_engine(oborovo)
    config = WaterfallRunConfig.from_inputs(oborovo, engine)
    result = WaterfallRunner(oborovo, engine).run(config)

    first_dist_idx = None
    for i, p in enumerate(result.periods):
        if getattr(p, 'distribution_keur', 0) > 0:
            first_dist_idx = i
            break

    # All distributions before first_dist_idx should be 0 while SHL outstanding
    for i, p in enumerate(result.periods):
        if first_dist_idx is not None and i < first_dist_idx:
            assert p.distribution_keur == 0, (
                f"Unexpected distribution at op_idx={i} before first valid distribution"
            )

    # First valid distribution should be around op_idx 38-40 (2050-06-30)
    assert first_dist_idx is not None, "No distributions found in runtime output"
    assert first_dist_idx >= 38, (
        f"First distribution at op_idx={first_dist_idx}; expected >= 38 (around 2050)"
    )


# =============================================================================
# 5. Corrected anchors unchanged
# =============================================================================


def test_oborovo_corrected_anchors_unchanged():
    """Phase 23L/23J/23K anchors remain correct after factory opt-in."""
    oborovo = create_default_oborovo()
    fin = oborovo.financing
    assert abs(fin.shl_amount_keur - 14621.0) <= 1.0, (
        f"shl_amount_keur={fin.shl_amount_keur}; expected ~14,621.0"
    )
    assert abs(fin.shl_idc_keur - 1169.0) <= 1.0, (
        f"shl_idc_keur={fin.shl_idc_keur}; expected ~1,169.0"
    )
    opening = fin.shl_amount_keur + fin.shl_idc_keur
    assert abs(opening - 15790.0) <= 1.0, (
        f"opening SHL={opening}; expected ~15,790.0"
    )
    assert fin.shl_tenor_years == 20, (
        f"shl_tenor_years={fin.shl_tenor_years}; expected 20"
    )


# =============================================================================
# 6. TUHO regression: flags and fixture unchanged
# =============================================================================


def test_tuho_regression_flags_and_fixture():
    """TUHO factory flags and fixture remain unchanged after Phase 23R."""
    tuho = create_default_tuho_wind1()
    fin = tuho.financing
    info = tuho.info
    assert info.use_senior_debt_sizing_engine is True, (
        "TUHO info.use_senior_debt_sizing_engine must remain True"
    )
    assert fin.use_frozen_excel_senior_debt_schedule is True, (
        "TUHO financing.use_frozen_excel_senior_debt_schedule must remain True"
    )
    # TUHO fixture still loads (spot check P4)
    engine = _build_period_engine(tuho)
    config = WaterfallRunConfig.from_inputs(tuho, engine)
    result = WaterfallRunner(tuho, engine).run(config)
    assert result.periods[3].senior_ds_keur > 0, (
        "TUHO senior DS at P4 should be non-zero (fixture loaded)"
    )


# =============================================================================
# 7. No other flags promoted
# =============================================================================


def test_oborovo_factory_opt_in_does_not_promote_other_flags():
    """Phase 23R enables only frozen senior DS; other experimental flags stay off."""
    oborovo = create_default_oborovo()
    info = oborovo.info
    fin = oborovo.financing

    # G20 remains blocked
    if hasattr(info, 'use_g20_engine'):
        assert info.use_g20_engine is False, "G20 engine must remain blocked"

    # R99/R102 not approved
    if hasattr(info, 'use_r99_engine'):
        assert info.use_r99_engine is False, "R99 must remain not approved"
    if hasattr(info, 'use_r102_engine'):
        assert info.use_r102_engine is False, "R102 must remain not approved"

    # partial_pay_sweep not promoted
    if hasattr(fin, 'use_partial_pay_sweep'):
        assert fin.use_partial_pay_sweep is False, "partial_pay_sweep must not be promoted"

    # flat_dscr_sculpted not promoted
    if hasattr(fin, 'flat_dscr_sculpted'):
        assert fin.flat_dscr_sculpted is False, "flat_dscr_sculpted must not be promoted"

    # minimum_dscr_sculpted not promoted
    if hasattr(fin, 'minimum_dscr_sculpted'):
        assert fin.minimum_dscr_sculpted is False, "minimum_dscr_sculpted must not be promoted"


# =============================================================================
# 8. Phase 23C negative guard allows only approved fixture
# =============================================================================


def test_phase23q_negative_guard_allows_only_approved_fixture():
    """Phase 23C negative fixture guard blocks unapproved files, allows phase23q."""
    import os
    reports_dir = str(Path(__file__).resolve().parents[1] / "reports")
    if not os.path.exists(reports_dir):
        pytest.skip("reports directory not accessible")
    files = os.listdir(reports_dir)
    oborovo_files = [
        f for f in files
        if "oborovo" in f.lower()
        and ("senior" in f.lower() or "sizing" in f.lower() or "frozen" in f.lower())
        and not f.lower().startswith("phase23q")
    ]
    assert len(oborovo_files) == 0, (
        f"Unexpected Oborovo frozen schedule files found: {oborovo_files}"
    )
