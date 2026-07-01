# Excel Parity Stack G — Distribution & Sponsor Engine → UI Wiring

Branch: `excel-parity-stack-g-distribution-sponsor-ui`

## Summary

Stack G wires the Distribution schedule (G1) to the UI via `sessionStorage["lastDistributionSchedule"]`.
The Sponsor per-period schedule (G2) is documented as a gap — only the scalar `sponsor_irr` exists on
`WaterfallResult`, and wiring per-period sponsor cashflows would require new intermediate architecture
explicitly forbidden by Stack G guardrails.

---

## G1: Distribution — Audit Findings

### Fields on `WaterfallPeriod` (per-period, all serialized)

| Field | Description |
|---|---|
| `distribution_keur` | Equity distribution paid this period |
| `cash_sweep_keur` | Cash sweep this period |
| `cum_distribution_keur` | Cumulative distribution to date |
| `lockup_active` | True if lockup covenants block distribution |
| `cf_after_reserves_keur` | CF available after DSRA/MRA reserve movements |
| `dsra_balance_keur` | DSRA closing balance |
| `dsra_contribution_keur` | DSRA funding/(release) this period |
| `mra_balance_keur` | MRA closing balance |
| `mra_contribution_keur` | MRA funding/(release) this period |
| `legacy_distribution_keur` | Runtime distribution before DA override (Phase 9C audit) |
| `da_paid_distribution_keur` | DA `equity_distribution_paid_keur` (Phase 9C) |
| `distribution_source` | `"runtime"` \| `"distribution_account"` \| `""` (Phase 9C) |
| `distribution_wiring_delta_keur` | `da_paid - legacy` (Phase 9C audit delta) |

### Fields on `WaterfallResult` (summary, all serialized)

| Field | Description |
|---|---|
| `total_distribution_keur` | Total equity distributions over project life |
| `legacy_distribution_keur` | Pre-override total (Phase 9C) |
| `da_paid_distribution_keur` | DA-paid total (Phase 9C) |
| `distribution_source` | Result-level distribution source label |
| `distribution_wiring_delta_keur` | Total delta (Phase 9C) |

### Payload Structure

```json
{
  "periods": [
    {
      "period": 1,
      "date": "2025-06-30",
      "year_index": 1,
      "period_in_year": 1,
      "is_operation": true,
      "distribution_keur": 1234.56,
      "cash_sweep_keur": 0.0,
      "cum_distribution_keur": 1234.56,
      "lockup_active": false,
      "cf_after_reserves_keur": 1234.56,
      "dsra_balance_keur": 500.0,
      "dsra_contribution_keur": 0.0,
      "mra_balance_keur": 0.0,
      "mra_contribution_keur": 0.0,
      "legacy_distribution_keur": 1234.56,
      "da_paid_distribution_keur": 0.0,
      "distribution_source": "",
      "distribution_wiring_delta_keur": 0.0
    }
  ],
  "summary": {
    "total_distribution_keur": 45678.90,
    "legacy_distribution_keur": 45678.90,
    "da_paid_distribution_keur": 0.0,
    "distribution_source": "",
    "distribution_wiring_delta_keur": 0.0
  },
  "source": "WaterfallResult.periods (per-period engine output)"
}
```

---

## G2: Sponsor — Audit Findings (Gap Documented)

### What exists on `WaterfallResult`

| Field | Description |
|---|---|
| `sponsor_irr` | Scalar float — gross sponsor IRR computed by `run_waterfall_v3_core()` |

The `sponsor_irr` scalar is already surfaced in the KPIs block (`run_project()["kpis"]`) and
exposed in `sessionStorage["lastRuntimeSummary"]`.

### What does NOT exist on `WaterfallResult`

The `domain/sponsor/` module contains:
- `SponsorCashflowResult` / `SponsorCashflowPeriodResult` — per-period equity cashflows
- `SponsorIrrResult` — gross/net IRR with convergence metadata
- `SponsorMoicResult` — MOIC with invested capital basis
- `SponsorCapitalAccount` — LP/GP capital account tracking
- `domain/sponsor/sponsor_cashflow_runner.py` — computes the above

None of these are attached to `WaterfallResult` or `WaterfallPeriod`. The sponsor runner is
invoked separately and its output is not wired back onto the waterfall result object tree.

### Why G2 is NOT implemented

Wiring per-period sponsor cashflows would require:
1. Calling `sponsor_cashflow_runner.py` from `project_runner.py`
2. Attaching the `SponsorCashflowResult` to the `run_project()` return dict
3. Writing a `_serialize_sponsor_schedule()` serializer

This constitutes new intermediate architecture, explicitly forbidden by Stack G guardrails.
The `_sheet_sponsor_partial.html` template retains its honest unavailable-state panel with
documentation of the gap.

### sessionStorage keys NOT added

- `sessionStorage["lastSponsorSchedule"]` — NOT wired (G2 gap)

---

## sessionStorage Keys Added

| Key | Source | Template |
|---|---|---|
| `lastDistributionSchedule` | `_serialize_distribution_schedule(WaterfallResult)` | `_sheet_distributions_partial.html` |

---

## Files Changed

| File | Change |
|---|---|
| `app/api/project_runner.py` | Added `_serialize_distribution_schedule()` + call in `run_project()` |
| `app/services/run_service.py` | Added `distribution_schedule` param to `_build_sessionstorage_save_tag()`, threaded through all 3 paths |
| `app/templates/partials/_sheet_distributions_partial.html` | Added table rendering JS reading `lastDistributionSchedule` |
| `app/templates/partials/_sheet_sponsor_partial.html` | Updated comment documenting G2 gap |
| `tests/test_excel_parity_stack_g.py` | 34 characterization tests |
| `docs/EXCEL_PARITY_STACK_G_DISTRIBUTION_SPONSOR_UI.md` | This file |

---

## Remaining Parity Gaps

- **G2 Sponsor per-period cashflows**: `SponsorCashflowResult` not wired onto `WaterfallResult`. Requires new architecture.
- **Distribution Account detailed schedule**: The Phase 9C DA engine (`domain/distribution_account/`) output is partially surfaced via the `da_paid_distribution_keur` / `distribution_source` / `distribution_wiring_delta_keur` audit fields on `WaterfallPeriod`, but the full `DistributionAccountPeriodResult` is not serialized.

---

## Guardrail Confirmation

- `waterfall_core.py` — NOT touched
- `domain/*` — NOT touched
- `input_adapter.py` — NOT touched
- `project_factories.py` — NOT touched
- `tests/test_phase51f_parallel_work_guardrails.py` — NOT touched (21 tests still pass)
- No financial calculations added to Python or JS
- No client-side JS arithmetic
- No intermediate architecture invented
