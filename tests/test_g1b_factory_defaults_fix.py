"""G1B-FACTORY-DEFAULTS-FIX: focused tests for the Generic Solar/Wind factory
default fixes identified by the G1B anchor parity dry run.

Covers two confirmed defects in app/project_factories.py:
  1. The "Soft Costs" CapexItem was constructed but never wired into the
     CapexStructure, silently dropping it from total_capex.
  2. market_prices_curve was a hardcoded linear ramp that did not honor
     market_inflation=0.02 / the G1A spec's stated 2%/yr compounding.

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


def test_tuho_wind1_unchanged() -> None:
    """TUHO is out of scope for this fix; pin its factory output."""
    inputs = create_default_tuho_wind1()
    assert inputs.capex.total_capex == 72_993.70999999999
    assert inputs.revenue.market_prices_curve[:3] == (94.554, 100.969, 102.6256)


def test_oborovo_unchanged() -> None:
    """Oborovo is out of scope for this fix; pin its factory output."""
    inputs = create_default_oborovo()
    assert inputs.capex.total_capex == 57_973.05265737862
    assert inputs.revenue.market_prices_curve[:3] == (0, 0, 0)


def test_engine_files_unchanged() -> None:
    """waterfall_core.py and input_adapter.py must not be touched by this fix."""
    expected_hashes = {
        "app/waterfall_core.py": "6bf49f33efc989736c17cea0cb9b7723",
        "app/input_adapter.py": "ab296e927a3bc5869726519f68e58bec",
        "domain/inputs.py": "73dd17f60203e4121934381ef72964b6",
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
