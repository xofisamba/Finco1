"""G1B-ANCHOR-PARITY-TESTS: automated Generic Solar/Wind anchor parity tests
against the refreshed G1E reference workbook fixtures.

Compares app.project_factories.create_default_solar_project() /
create_default_wind_project() runtime output against the Tier-1 anchors
extracted from the recalculated, post-G1E reference workbooks
(tests/fixtures/excel_golden_generic_{solar,wind}.json).

Anchors fall into two groups:

* TIGHT_TOLERANCES -- anchors where the runtime and the Excel reference
  already agree closely (capex, revenue, opex, EBITDA, IDC, bank fees,
  senior debt amount, realized gearing). These use the same near-Excel-
  grade tolerances baked into the golden fixtures' own
  ``initial_tolerances`` (see scripts/extract_generic_golden.py).

* WIDE_TOLERANCES -- anchors affected by a known, pre-existing methodology
  gap between the runtime's debt-sizing/DSCR machinery and the Excel
  bootstrap workbook's own debt-sizing proxy. This gap is NOT introduced
  or fixed by this test file (runtime/domain/factory code is out of
  scope here -- see docs/generic_validation_reference_excel_spec.md
  Section 6.2 for the documented rationale). These tests pin the
  *current* runtime behaviour with a deliberately wide, documented
  tolerance so that any further, unrelated drift is still caught as a
  regression, without asserting false Excel-grade precision the runtime
  does not yet deliver.

Project IRR in particular is called out per the documented note: the
bootstrap workbook's Project IRR is not fully debt-independent (its tax
line nets out the *actual* interest expense from the real debt schedule,
so the interest tax shield leaks into the nominally "unlevered" CFADS).
Debt-service-shape changes therefore legitimately move Project IRR by a
few percentage points even though its cash-flow row never includes debt
service directly. See docs/generic_validation_reference_excel_spec.md
Section 6.2.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import pytest

from app.project_factories import create_default_solar_project, create_default_wind_project
from app.waterfall_core import run_waterfall_v3_core
from domain.period_engine import PeriodEngine

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures"

PROJECT_FACTORIES = {
    "solar": create_default_solar_project,
    "wind": create_default_wind_project,
}

# (kind, value, floor) -- kind in {"relative_pct", "absolute", "absolute_pp"}.
# For "relative_pct", the tolerance is max(abs(expected) * value, floor).
TIGHT_TOLERANCES: dict[str, tuple[str, float, float | None]] = {
    "total_capex_keur": ("relative_pct", 0.005, 1.0),
    "total_revenue_keur": ("relative_pct", 0.005, 1.0),
    "total_opex_keur": ("relative_pct", 0.005, 1.0),
    "total_ebitda_keur": ("relative_pct", 0.005, 1.0),
    "idc_keur": ("relative_pct", 0.01, 1.0),
    "bank_fees_keur": ("relative_pct", 0.005, 1.0),
    "senior_debt_keur": ("relative_pct", 0.005, 1.0),
    "realized_gearing": ("absolute_pp", 0.5, None),
}

# Known debt-sizing/DSCR methodology gap (see module docstring). Bounds were
# set with headroom over the actual observed Solar/Wind diffs at the time
# this test was written (worst case ~36% relative on min_dscr, ~0.022 abs on
# project_irr, ~0.222 abs on equity_irr) so the tests pin current behaviour
# without asserting Excel-grade parity that does not exist yet.
WIDE_TOLERANCES: dict[str, tuple[str, float, float | None]] = {
    "avg_dscr": ("relative_pct", 0.35, 0.05),
    "min_dscr": ("relative_pct", 0.40, 0.05),
    "senior_debt_service_p1_keur": ("relative_pct", 0.35, 1.0),
    "senior_debt_service_p2_keur": ("relative_pct", 0.35, 1.0),
    "senior_debt_service_p3_keur": ("relative_pct", 0.35, 1.0),
    "project_irr": ("absolute", 0.025, None),
    "equity_irr": ("absolute", 0.25, None),
}

ALL_TOLERANCES: dict[str, tuple[str, float, float | None]] = {
    **TIGHT_TOLERANCES,
    **WIDE_TOLERANCES,
}


def _load_golden(project: str) -> dict:
    path = FIXTURE_DIR / f"excel_golden_generic_{project}.json"
    return json.loads(path.read_text())["golden_cells"]


@lru_cache(maxsize=None)
def _run(project: str):
    inputs = PROJECT_FACTORIES[project]()
    engine = PeriodEngine(
        financial_close=inputs.info.financial_close,
        construction_months=inputs.info.construction_months,
        horizon_years=inputs.info.horizon_years,
        ppa_years=inputs.revenue.ppa_term_years,
    )
    op_periods = [p for p in engine.periods() if p.is_operation]
    result = run_waterfall_v3_core(
        inputs=inputs,
        engine=engine,
        rate_per_period=inputs.financing.all_in_rate / 2,
        tenor_periods=len(op_periods),
        target_dscr=inputs.financing.target_dscr,
        lockup_dscr=inputs.financing.lockup_dscr,
        tax_rate=inputs.tax.corporate_rate,
        dsra_months=inputs.financing.dsra_months,
        shl_amount=inputs.financing.shl_amount_keur,
        shl_rate=inputs.financing.shl_rate,
        shl_idc_keur=0.0,
        shl_repayment_method="bullet",
        equity_irr_method="equity_only",
        share_capital_keur=inputs.financing.share_capital_keur,
        sculpt_capex_keur=inputs.capex.sculpt_capex_keur,
        debt_sizing_method="dscr_sculpt",
    )
    return inputs, result


def _runtime_anchors(project: str) -> dict[str, float]:
    inputs, result = _run(project)
    op_periods = [p for p in result.periods if p.is_operation]
    ds = [p.senior_ds_keur for p in op_periods[:3]]
    return {
        "total_capex_keur": inputs.capex.total_capex,
        "total_revenue_keur": result.total_revenue_keur,
        "total_opex_keur": result.total_opex_keur,
        "total_ebitda_keur": result.total_ebitda_keur,
        "idc_keur": inputs.capex.idc_keur,
        "bank_fees_keur": inputs.capex.bank_fees_keur,
        "senior_debt_keur": result.sculpting_result.debt_keur,
        "realized_gearing": result.sculpting_result.debt_keur / inputs.capex.total_capex * 100,
        "senior_debt_service_p1_keur": ds[0],
        "senior_debt_service_p2_keur": ds[1],
        "senior_debt_service_p3_keur": ds[2],
        "avg_dscr": result.avg_dscr,
        "min_dscr": result.min_dscr,
        "project_irr": result.project_irr,
        "equity_irr": result.equity_irr,
    }


def _assert_within_tolerance(
    anchor: str, actual: float, expected: float, spec: tuple[str, float, float | None]
) -> None:
    kind, value, floor = spec
    diff = actual - expected
    if kind == "relative_pct":
        tol = max(abs(expected) * value, floor or 0.0)
        assert abs(diff) <= tol, (
            f"{anchor}: runtime={actual} golden={expected} diff={diff} "
            f"exceeds relative tolerance {value * 100:.1f}% (tol={tol})"
        )
    elif kind == "absolute":
        assert abs(diff) <= value, (
            f"{anchor}: runtime={actual} golden={expected} diff={diff} "
            f"exceeds absolute tolerance {value}"
        )
    elif kind == "absolute_pp":
        assert abs(diff) <= value, (
            f"{anchor}: runtime={actual} golden={expected} diff={diff} "
            f"exceeds {value} percentage points"
        )
    else:  # pragma: no cover - defensive
        raise ValueError(f"unknown tolerance kind: {kind}")


@pytest.mark.parametrize("project", ["solar", "wind"])
@pytest.mark.parametrize("anchor", list(TIGHT_TOLERANCES))
def test_generic_anchor_tight_parity(project: str, anchor: str) -> None:
    """Anchors that already agree closely between runtime and the
    G1E-recalculated Excel reference (capex/revenue/opex/EBITDA/IDC/bank
    fees/senior debt/realized gearing)."""
    golden = _load_golden(project)
    runtime = _runtime_anchors(project)
    _assert_within_tolerance(anchor, runtime[anchor], golden[anchor]["value"], TIGHT_TOLERANCES[anchor])


@pytest.mark.parametrize("project", ["solar", "wind"])
@pytest.mark.parametrize("anchor", list(WIDE_TOLERANCES))
def test_generic_anchor_wide_parity_known_methodology_gap(project: str, anchor: str) -> None:
    """Anchors affected by the known, pre-existing debt-sizing/DSCR
    methodology gap between runtime and the Excel bootstrap workbook (see
    module docstring and docs/generic_validation_reference_excel_spec.md
    Section 6.2). Pinned with a deliberately wide, documented tolerance --
    not Excel-grade parity."""
    golden = _load_golden(project)
    runtime = _runtime_anchors(project)
    _assert_within_tolerance(anchor, runtime[anchor], golden[anchor]["value"], WIDE_TOLERANCES[anchor])


@pytest.mark.parametrize("project", ["solar", "wind"])
def test_generic_anchor_set_is_complete(project: str) -> None:
    """Every anchor required by the G1B anchor-parity spec must be present
    in both the golden fixture and the runtime extraction."""
    golden = _load_golden(project)
    runtime = _runtime_anchors(project)
    for anchor in ALL_TOLERANCES:
        assert anchor in golden, f"missing golden anchor: {anchor}"
        assert anchor in runtime, f"missing runtime anchor: {anchor}"


def test_engine_files_unchanged() -> None:
    """This test-only branch must not touch runtime/domain code.

    app/project_factories.py is intentionally excluded here: G1H legitimately
    updates it (Generic Solar/Wind equity/SHL funding fix), and that change is
    separately pinned by tests/test_g1b_factory_defaults_fix.py."""
    import hashlib

    expected_hashes = {
        "app/waterfall_core.py": "6bf49f33efc989736c17cea0cb9b7723",
        "app/input_adapter.py": "ab296e927a3bc5869726519f68e58bec",
        "domain/inputs.py": "73dd17f60203e4121934381ef72964b6",
        "domain/revenue/generation.py": "177ef500f38bdb3c1379438c9e1d4f29",
        "domain/waterfall/waterfall_engine.py": "ddd93874e776ada65b94dda9aef678b6",
    }
    for rel_path, expected_md5 in expected_hashes.items():
        path = REPO_ROOT / rel_path
        actual_md5 = hashlib.md5(path.read_bytes()).hexdigest()
        assert actual_md5 == expected_md5, f"{rel_path} changed unexpectedly"
