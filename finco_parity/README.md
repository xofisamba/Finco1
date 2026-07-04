# finco_parity

**Finco One v2 — Parity Harness**

`finco_parity` is the first-class parity testing infrastructure for the Finco One v2 extraction programme. It contains the golden fixtures, expected baseline outputs, and parametrised regression tests that validate the extracted `finco_core` engine against the Legacy Engine Baseline (`Finco1-RC2`).

## Package Responsibilities

| Subpackage | Responsibility |
|------------|---------------|
| `fixtures/` | Input configurations for TUHO Wind 1 and Oborovo Solar reference projects |
| `golden/` | Expected KPI outputs derived from the RC2 baseline run |
| `regression/` | Pytest parametrised tests comparing extracted engine output to golden baselines |

## Dependency Rule

`finco_parity` depends on `finco_core` only.  
`finco_parity` does not depend on `finco_app`, UI packages, or web frameworks.  
Test infrastructure (pytest) is a dev dependency only — not a runtime dependency.

## Parity Gate

Every extraction milestone PR (V2-3 and later) must pass all tests in `finco_parity/regression/` before merge is permitted.

## RC2 Tolerance Targets

| Project | KPI | Value | Tolerance |
|---------|-----|-------|-----------|
| TUHO Wind 1 | equity_irr | 11.32% | ±0.05% |
| TUHO Wind 1 | actual_avg_dscr | 1.3786 | ±0.001 |
| TUHO Wind 1 | total_tax_keur | 35,414 kEUR | ±500 kEUR |
| TUHO Wind 1 | total_distributions | 165,471 kEUR | ±200 kEUR |
| Oborovo Solar | equity_irr | 10.54% | ±0.05% |
| Oborovo Solar | actual_avg_dscr | 1.179 | ±0.005 |
| Oborovo Solar | total_tax_keur | 8,874 kEUR | ±100 kEUR |

## Extraction Status

| Milestone | Status |
|-----------|--------|
| V2-1 Skeleton | In progress |
| V2-4 Parity Harness | Planned — fixtures, golden baselines, regression suite |
