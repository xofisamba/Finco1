"""G1B/G1C-FACTORY-DEFAULTS-FIX: focused tests for the Generic Solar/Wind
factory default fixes identified by the G1B/G1C anchor parity dry runs.

Covers three confirmed defects in app/project_factories.py:
  1. (G1B) The "Soft Costs" CapexItem was constructed but never wired into
     the CapexStructure, silently dropping it from total_capex.
  2. (G1B) market_prices_curve was a hardcoded linear ramp that did not
     honor market_inflation=0.02 / the G1A spec's stated 2%/yr compounding.
  3. (G1C) RevenueParams.balancing_cost_pv defaulted to 0.025 (a 2.5%-of-
     revenue "PV balancing" deduction) which has no counterpart in the
     G1A reference Excel workbooks; the factories now zero it explicitly.

These tests do not touch waterfall_core.py, input_adapter.py, domain/*, or
any other runtime/engine code; they only assert on the factory outputs.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from app.project_factories import (
    create_default_oborovo,
    create_default_solar_project,
    create_default_tuho_wind1,
    create_default_wind_project,
)
from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner
from domain.period_engine import PeriodEngine

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_generic_solar_total_capex_matches_g1a_spec() -> None:
    inputs = create_default_solar_project()
    assert inputs.capex.total_capex == 33_000.0


def test_generic_wind_total_capex_matches_g1a_spec() -> None:
    inputs = create_default_wind_project()
    assert inputs.capex.total_capex == 43_000.0


def test_generic_solar_soft_cost_included_exactly_once() -> None:
    inputs = create_default_solar_project()
    items = inputs.capex.capex_items()
    soft_items = [item for item in items if item.name == "Soft Costs"]
    assert len(soft_items) == 1
    assert soft_items[0].amount_keur == 3_000.0


def test_generic_wind_soft_cost_included_exactly_once() -> None:
    inputs = create_default_wind_project()
    items = inputs.capex.capex_items()
    soft_items = [item for item in items if item.name == "Soft Costs"]
    assert len(soft_items) == 1
    assert soft_items[0].amount_keur == 4_000.0


def test_generic_solar_market_curve_matches_2pct_compounding() -> None:
    """Y1=60, Y2=61 explicit (per G1A spec), then 2%/yr compounding from Y2,
    matching the bootstrap Excel reference workbook's Revenue-tab formula
    market_price_year = Y2 * (1 + esc) ** (year - 2)."""
    inputs = create_default_solar_project()
    curve = inputs.revenue.market_prices_curve
    assert curve[0] == 60.0
    assert curve[1] == 61.0
    for idx in range(2, len(curve)):
        expected = 61.0 * (1.02 ** (idx - 1))
        assert curve[idx] == expected, f"index {idx}: {curve[idx]} != {expected}"


def test_generic_wind_market_curve_matches_2pct_compounding() -> None:
    """Y1=65, Y2=66.3 explicit (per G1A spec), then 2%/yr compounding from Y2."""
    inputs = create_default_wind_project()
    curve = inputs.revenue.market_prices_curve
    assert curve[0] == 65.0
    assert curve[1] == 66.3
    for idx in range(2, len(curve)):
        expected = 66.3 * (1.02 ** (idx - 1))
        assert curve[idx] == expected, f"index {idx}: {curve[idx]} != {expected}"


def test_generic_solar_balancing_cost_pv_zeroed() -> None:
    """G1C: the G1A reference workbook has no PV-revenue-based balancing
    deduction; the domain default of 0.025 must be zeroed for Solar."""
    inputs = create_default_solar_project()
    assert inputs.revenue.balancing_cost_pv == 0.0


def test_generic_wind_balancing_cost_pv_zeroed() -> None:
    """G1C: same as Solar -- Wind's balancing cost is fully modeled via the
    flat balancing_cost_wind_eur_mwh field, so the PV-style deduction must
    be zeroed too."""
    inputs = create_default_wind_project()
    assert inputs.revenue.balancing_cost_pv == 0.0


def test_generic_solar_equity_funding_matches_gearing_complement() -> None:
    """G1H: share_capital_keur + shl_amount_keur must fund the full
    non-senior-debt share implied by gearing_ratio=0.75 (33,000 * 0.25 =
    8,250 kEUR), closing the funding gap identified in G1F."""
    inputs = create_default_solar_project()
    total = inputs.financing.share_capital_keur + inputs.financing.shl_amount_keur
    assert total == 8_250.0


def test_generic_wind_equity_funding_matches_gearing_complement() -> None:
    """G1H: same as Solar -- 43,000 * 0.25 = 10,750 kEUR."""
    inputs = create_default_wind_project()
    total = inputs.financing.share_capital_keur + inputs.financing.shl_amount_keur
    assert total == 10_750.0


def _run(factory):
    inputs = factory()
    engine = PeriodEngine(
        financial_close=inputs.info.financial_close,
        construction_months=inputs.info.construction_months,
        horizon_years=inputs.info.horizon_years,
        ppa_years=inputs.revenue.ppa_term_years,
    )
    config = WaterfallRunConfig.from_inputs(inputs, engine)
    result = WaterfallRunner(inputs, engine).run(config)
    return inputs, result


def test_generic_solar_senior_debt_unchanged_by_equity_fix() -> None:
    """G1H: closing the equity/SHL funding gap must not move senior debt
    sizing -- the gearing cap binds on total_capex, not on equity funding."""
    _, result = _run(create_default_solar_project)
    assert round(result.sculpting_result.debt_keur, 2) == 24_750.0


def test_generic_wind_senior_debt_unchanged_by_equity_fix() -> None:
    """G1H: same as Solar."""
    _, result = _run(create_default_wind_project)
    assert round(result.sculpting_result.debt_keur, 2) == 32_250.0


def test_generic_solar_realized_gearing_still_75_pct() -> None:
    """G1H: realized_gearing = senior_debt / total_capex * 100 must remain 75%."""
    inputs, result = _run(create_default_solar_project)
    realized_gearing = result.sculpting_result.debt_keur / inputs.capex.total_capex * 100
    assert round(realized_gearing, 4) == 75.0


def test_generic_wind_realized_gearing_still_75_pct() -> None:
    """G1H: same as Solar."""
    inputs, result = _run(create_default_wind_project)
    realized_gearing = result.sculpting_result.debt_keur / inputs.capex.total_capex * 100
    assert round(realized_gearing, 4) == 75.0


def test_tuho_wind1_unchanged() -> None:
    """TUHO is out of scope for this fix; pin its factory output."""
    inputs = create_default_tuho_wind1()
    assert inputs.capex.total_capex == 72_993.70999999999
    assert inputs.revenue.market_prices_curve[:3] == (94.554, 100.969, 102.6256)


def test_tuho_senior_debt_unchanged() -> None:
    """G1C: TUHO debt sizing must remain unaffected by the Solar/Wind-only
    balancing_cost_pv fix."""
    _, result = _run(create_default_tuho_wind1)
    assert round(result.sculpting_result.debt_keur, 2) == 43_359.0


def test_oborovo_unchanged() -> None:
    """Oborovo is out of scope for this fix; pin its factory output."""
    inputs = create_default_oborovo()
    assert inputs.capex.total_capex == 57_973.05265737862
    assert inputs.revenue.market_prices_curve[:3] == (0, 0, 0)


def test_oborovo_senior_debt_unchanged() -> None:
    """G1C: Oborovo debt sizing must remain unaffected by the Solar/Wind-only
    balancing_cost_pv fix."""
    _, result = _run(create_default_oborovo)
    assert round(result.sculpting_result.debt_keur, 2) == 42_852.27


def test_engine_files_unchanged() -> None:
    """waterfall_core.py, input_adapter.py, domain/inputs.py, and
    domain/revenue/generation.py must not be touched by this fix."""
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


def test_rc1_and_forbidden_areas_untouched() -> None:
    """This fix must be confined to app/project_factories.py only -- no UI,
    services, persistence, export, or rc1-tagged pilot code touched."""
    import subprocess

    diff = subprocess.run(
        ["git", "diff", "--name-only", "origin/main...HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    changed = [line for line in diff.stdout.splitlines() if line.strip()]
    if not changed:
        return
    allowed_prefixes = ("app/project_factories.py", "tests/", "docs/", "reports/")
    for f in changed:
        assert f.startswith(allowed_prefixes), f"unexpected file changed: {f}"
