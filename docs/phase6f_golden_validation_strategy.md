# Phase 6F-D — Golden Validation Strategy

**Repository:** xofisamba/Finco1
**Branch:** `phase6f-golden-validation-foundation`
**Date:** 2026-05-11
**Type:** Validation Strategy Document
**Scope:** Validation foundation only — no production calibration engine

---

## Purpose

This document defines the golden validation strategy for Oborovo (solar) and TUHO (wind)
reference scenarios. The strategy establishes deterministic, reproducible validation
of model outputs against known-good reference values (golden values).

**Not in scope:** production calibration engine, live model updating, UI-driven workflows.

---

## 1. Golden Scenario Definition

A **golden scenario** is a reference scenario with known, committed output values
extracted from source Excel workbooks. The golden values are immutable — they do not
change unless a deliberate re-baseline is performed.

### Oborovo

- **Type:** Solar, 53.63 MWp
- **Source workbook:** `20260414_BP_Oborovo_Sensitivity_FINAL for PPT.xlsm`
- **Golden file:** `tests/fixtures/excel_golden_oborovo.json`
- **Anchor file:** `tests/fixtures/tuho_wind1_golden.json`
- **Fixture name:** `oborovo`
- **Model period:** semiannual

### TUHO

- **Type:** Wind, 72 MW
- **Source workbook:** `20260330_TUHO_BP.xlsm`
- **Golden file:** `tests/fixtures/tuho_wind1_golden.json`
- **Fixture name:** `tuho`
- **Model period:** semiannual

---

## 2. Deterministic Reproducibility

### Principle

Every test that uses golden validation must produce identical pass/fail results
on every run, on every machine, with no external dependencies.

### Requirements

1. **Seeded randomness only.** Any stochastic element in the model uses a fixed
   seed. Tests that depend on stochastic outputs must either use seeded inputs or
   compare distribution moments (not individual draws).
2. **No live external data.** Golden values are committed to the repository in
   JSON fixtures. No API calls, file downloads, or network dependencies.
3. **Immutable fixtures.** Golden fixture files in `tests/golden/fixtures/` are
   read-only. No test writes to them.
4. **Versioned model inputs.** Model input schemas are versioned. If a model input
   schema changes (e.g., `ProjectInputs` field added), the fixture stores the exact
   inputs used and the test records which schema version produced the output.
5. **Environment isolation.** Tests run in a sandboxed environment. Environment
   variables (e.g., `FINCO_SECRET_KEY`) do not affect deterministic validation.

---

## 3. Snapshot-Based Validation

### Snapshot defined

A **validation snapshot** is a point-in-time capture of computed model outputs,
stored as a structured data object (typically a `dict` or dataclass) at test time.
The snapshot is compared against a **golden snapshot** (expected values from fixture).

### Snapshot structure

```python
{
    "schema_version": "1.0",
    "fixture_name": "oborovo",
    "run_timestamp": "2026-05-11T12:00:00Z",
    "model_version": "main@9f2c570",
    "values": {
        "total_capex_keur": 57973.05,
        "senior_debt_keur": 42852.27,
        "project_irr_30y": 0.0828,
        "equity_irr_30y": 0.1161,
        "avg_dscr": 1.147,
        "debt_service_schedule": [(-2239.13), (-2202.63), ...],
    }
}
```

### Validation process

1. Run model with golden inputs → produce snapshot
2. Load golden snapshot from fixture
3. Compare snapshot to golden using tolerance-aware comparison
4. Report deltas; assert pass/fail

---

## 4. Period-by-Period Comparison Philosophy

### Why period-by-period?

Most model errors manifest as a consistent bias across periods (e.g., depreciation
always overstated by 5%) or as a single outlier period. Comparing aggregate outputs
alone can hide localized errors. Period-by-period comparison catches these.

### Period indexing

- Periods are indexed 0-based from model start date (FC = financial close)
- Model runs semiannually: period 0 = first 6 months, period 1 = next 6 months, etc.
- Period comparison uses `tuple[float, ...]` — ordered, indexed by position

### Comparison strategy

1. **Period count must match.** If golden has 60 periods and model produces 62,
   the test fails with a count mismatch, not a tolerance delta.
2. **Per-period comparison for arrays.** Debt service, revenue, and cashflow arrays
   are compared period-by-period with per-period tolerances.
3. **Aggregate comparison for scalars.** IRR, NPV, and DSCR aggregates are compared
   as single values with aggregate tolerances.
4. **NaN handling.** A NaN in either golden or actual fails immediately (no tolerance
   can make NaN acceptable).

---

## 5. Tolerance Handling

### Tolerance types

| Type | Symbol | Use case |
|------|--------|----------|
| Absolute tolerance | `abs_tol` | Zero-crossing values (e.g., net cashflow near zero) |
| Relative tolerance | `rel_tol` | Large-magnitude values (e.g., IRR, large sums) |
| Percentage tolerance | `pct_tol` | Percentage of golden value (same as rel_tol / 100) |
| Basis points | `bps` | Basis points of 1 (e.g., IRR in bps) |

### Tolerance selection principle

Use the **largest** tolerance that is still acceptable for the model's purpose.
Too-tight tolerances create flaky tests; too-loose tolerances miss real errors.

### Default tolerances (Oborovo / TUHO)

| Metric | Tolerance | Rationale |
|--------|-----------|-----------|
| `total_capex_keur` | ±0.5% | CAPEX is fixed; small rounding acceptable |
| `total_debt_keur` | ±0.5% | Debt is fixed at financial close |
| `project_irr_30y` | ±10 bps | IRR sensitivity to small input changes |
| `equity_irr_30y` | ±10 bps | Equity IRR is the primary covenant metric |
| `avg_dscr` | ±0.002 | DSCR covenant headroom |
| Revenue per period | ±0.5% | Revenue is predictable for solar |
| Debt service per period | ±0.5% | DS schedule is locked |
| Tax per period | ±1.0% | Tax calculations may have small timing differences |

### Floating-point drift

Python `float` arithmetic introduces rounding errors of order 1e-15. These are handled
by using `rel_tol` of at least `1e-9` in all comparisons, even for "exact" checks.
NaN comparisons fail immediately (no tolerance applied).

---

## 6. Audit Visibility

### What is audited

- Which golden fixture was used
- Which model version was used (git SHA)
- Timestamp of the run
- Per-metric delta (actual − golden)
- Per-metric tolerance used
- Pass/fail for each metric

### Audit output format

```python
{
    "fixture": "oborovo",
    "model_version": "main@9f2c570",
    "run_timestamp": "2026-05-11T12:00:00Z",
    "results": [
        {
            "metric": "equity_irr_30y",
            "golden": 0.1161,
            "actual": 0.11615,
            "delta": 0.00005,
            "tolerance": {"type": "bps", "value": 10},
            "status": "PASS",
        },
        ...
    ],
    "summary": {"passed": 10, "failed": 1, "total": 11},
}
```

### Audit destination

- **Console:** pytest captures and prints the audit summary on failure
- **File:** optional `--golden-report=path.json` writes full report to file
- **CI artifact:** in CI, the report is attached as a build artifact for review

---

## 7. Future Sponsor-Layer Validation Compatibility

The golden validation framework is designed to extend to sponsor-layer outputs
in Phase 7A/7B.

### Extension points

| Sponsor concept | Extends from | New fixture |
|----------------|--------------|-------------|
| `EquityInjection` | Input schema | `sponsor_equity_injections` |
| `SponsorCashflowResult` | Result schema | `sponsor_cashflows_<scenario>` |
| `SponsorIRRResult` | Derived scalar | `sponsor_irr_<scenario>` |
| `SponsorCapitalAccount` | Period series | `sponsor_capital_account_<scenario>` |

### Compatibility requirements

- Sponsor-layer tests must use the same `compare_values`, `compare_series`,
  and `assert_all_close` utilities as existing tests
- Sponsor fixtures follow the same fixture structure as Oborovo/TUHO
- Sponsor audit output follows the same schema as the existing audit output

---

## 8. Separation: Accounting vs Cash Outputs

### Accounting outputs (P&L / accrual)

- Revenue, EBITDA, EBT, net income — accrual basis
- Tax computed on accrual basis (not cash paid)
- Depreciation (accounting book) — straight-line
- These outputs are in `P&L`, `Income Statement` sheet equivalents

### Cash outputs (cash flow)

- Operating cash flow, investing cash flow, financing cash flow
- Debt service actual cash (principal + interest paid)
- Tax actually paid in cash (after cash timing transform)
- Equity injections in cash terms
- These outputs are in `Cash Flow` sheet equivalents

### Validation separation principle

- Accounting and cash outputs are validated **separately**, not combined
- Reconciliation tests compare accounting net income to cash flow from operations,
  but they use separate golden fixtures
- Sponsor IRR validation uses cash outputs (not accrual outputs)

---

## 9. Explicit Non-Scope

The following are explicitly out of scope for Phase 6F-D:

| Item | Reason |
|------|--------|
| Production calibration engine | Not required for validation |
| Live model updating | Fixture-based only |
| UI-driven workflows | No UI in scope |
| Excel export formatting | Validation against model outputs, not Excel formatting |
| External API services | No network calls in tests |
| Sponsor IRR integration | Phase 7B topic |
| Promote waterfall | Phase 7B topic |
| Editable persistence | Future Phase |
| Role system | Future Phase |

---

## 10. Fixture Structure

### File layout

```
tests/golden/
├── __init__.py
├── fixtures/
│   ├── __init__.py
│   ├── oborovo_golden.json      # Oborovo scalar + period-series fixtures
│   └── tuho_golden.json         # TUHO scalar + period-series fixtures
└── utils/
    ├── __init__.py
    ├── comparison.py            # compare_values, compare_series, assert_all_close
    ├── snapshot.py              # SnapshotContext, capture, diff
    └── formatting.py            # DiffFormatter, ReportFormatter
```

### Fixture schema

```json
{
  "_comment": "Golden validation fixture — read-only",
  "metadata": {
    "fixture_name": "oborovo",
    "model_version": "main@9f2c570",
    "extracted_from": "20260414_BP_Oborovo_Sensitivity_FINAL for PPT.xlsm",
    "extraction_date": "2026-04-14",
    "model_period": "semiannual",
    "period_count": 60,
    "schema_version": "1.0"
  },
  "scalars": {
    "total_capex_keur": {"value": 57973.052657, "tolerance": {"type": "pct", "value": 0.005}},
    "total_debt_keur": {"value": 42852.2667, "tolerance": {"type": "pct", "value": 0.005}},
    "project_irr_30y": {"value": 0.0828, "tolerance": {"type": "bps", "value": 10}},
    "equity_irr_30y": {"value": 0.1161, "tolerance": {"type": "bps", "value": 10}},
    "avg_dscr": {"value": 1.147, "tolerance": {"type": "abs", "value": 0.002}}
  },
  "series": {
    "debt_service_schedule_keur": {
      "values": [-2239.133, -2202.626, ...],
      "unit": "kEUR",
      "period_indexed": true,
      "per_period_tolerance": {"type": "pct", "value": 0.005}
    }
  }
}
```

---

## 11. Utility Reference

### `compare_values(actual, golden, abs_tol=None, rel_tol=None)`

Compare two scalar values with tolerance.
- Returns `{"pass": bool, "delta": float, "tolerance_used": float}`
- Raises if both tolerances are `None`

### `compare_series(actual: tuple, golden: tuple, abs_tol=None, rel_tol=None)`

Compare two period-indexed tuples element-by-element.
- Returns `{"pass": bool, "period_deltas": tuple, "failures": list[tuple[index, delta]]}`
- Checks period count first; mismatch is immediate failure

### `assert_all_close(scalars_dict, golden_dict, report=False)`

Assert all scalars in `scalars_dict` are within tolerance of `golden_dict`.
- `scalars_dict`: `{metric_name: actual_value}`
- `golden_dict`: `{metric_name: {"value": x, "tolerance": {...}}}`
- If `report=True`, prints full delta table on failure

### `SnapshotContext`

Context manager for capturing validation snapshots:

```python
with SnapshotContext(fixture_name="oborovo", model_version="main@abc123") as ctx:
    result = run_model(fixture)
    ctx.capture("total_capex_keur", result.total_capex_keur)
    ctx.capture("equity_irr_30y", result.equity_irr_30y)
# on exit: ctx.report() is printed; ctx.failures raises if any metric failed
```

### `DiffFormatter`

Formats a single metric diff for human-readable output:

```python
DiffFormatter.format("equity_irr_30y", actual=0.11615, golden=0.1161, bps_tolerance=10)
# → "equity_irr_30y: 11.615% vs 11.610% | delta +0.5 bps | PASS (tol: ±10 bps)"
```

---

*End of Strategy Document — Phase 6F-D Golden Validation Foundation*
*Branch: phase6f-golden-validation-foundation*
*Implementation: tests/golden/ utilities + initial tests*