# Excel Parity Stack H — Sponsor Engine → Runtime Handoff

## Summary

Stack H completes the first Engine → UI wiring wave by exposing the existing Phase 7A/7B
Sponsor engine output through the runtime payload.

Unlike Stacks E, F, and G (which read fields that were already on `WaterfallResult`),
the Sponsor per-period cashflows live in separate domain objects that are not attached to
`WaterfallResult`. Stack H bridges this gap with the smallest possible handoff:
`project_runner.run_project()` calls the Sponsor engine's public interface after the
waterfall completes and adds the serialized result to the payload.

---

## H1 — Audit Findings

### Phase 7A — Sponsor Cashflow Engine

**Location:** `domain/sponsor/sponsor_cashflow_runner.py`

**Entry point:** `run_sponsor_cashflows(SponsorCashflowRunnerInputs) → SponsorCashflowResult`

**Per-period output (`SponsorCashflowPeriodResult`):**
- `period_index` — semiannual period index (0-based)
- `equity_injected_keur` — equity injection this period (cash outflow from sponsor)
- `distribution_received_keur` — distribution received from SPV (cash inflow to sponsor)
- `wht_on_distribution_keur` — WHT withheld on distribution
- `net_cashflow_keur` — net sponsor cashflow (`distribution - injection - WHT`)
- `capital_account_balance_keur` — cumulative capital account balance

**Summary output (`SponsorCashflowResult`):**
- `total_equity_injected_keur`
- `total_distributions_received_keur`
- `total_wht_keur`
- `total_net_cashflow_keur`
- `gross_sponsor_return_multiple` — basic MOIC (`distributions / injections`)

### Phase 7B — Sponsor IRR & MOIC

**Location:** `domain/sponsor/sponsor_irr_runner.py`

**IRR output (`SponsorIrrResult`):**
- `gross_sponsor_irr` — XIRR-computed annual IRR over semiannual cashflow timeline
- `xirr_converged` — whether the XIRR solver converged
- `net_sponsor_irr_placeholder: None` — placeholder, not yet computed

**MOIC output (`SponsorMoicResult`):**
- `gross_sponsor_moic` — `total_distributions / total_equity_injected`
- `total_equity_injected_keur`
- `total_distributions_received_keur`
- `net_multiple_placeholder: None` — placeholder, not yet computed

### Pre-existing WaterfallResult.sponsor_irr

`WaterfallResult` carries a `sponsor_irr` field (line 164 of `domain/waterfall/waterfall_engine.py`),
computed internally via `build_sponsor_cashflows()` from `domain/returns/sponsor_cashflows.py`.
This is a legacy simplified path already in the KPI block. Stack H wires the Phase 7A/7B
runner separately — both paths are independent.

---

## H2 — Runtime Ownership (Architecture)

```
project_runner.run_project()
  │
  ├─► run_demo_project() → WaterfallResult          [Waterfall engine — unchanged]
  │
  └─► _run_sponsor_engine(WaterfallResult, project_inputs, project_type)
        │
        ├─► SponsorCashflowRunnerInputs (assembled from WaterfallResult.periods[].distribution_keur)
        ├─► run_sponsor_cashflows()  → SponsorCashflowResult   [Phase 7A engine — unchanged]
        ├─► run_sponsor_irr()        → SponsorIrrResult         [Phase 7B engine — unchanged]
        └─► run_sponsor_moic()       → SponsorMoicResult        [Phase 7B engine — unchanged]

  └─► _serialize_sponsor_schedule(cf, irr, moic) → JSON-safe dict

return {"sponsor_schedule": payload, ...}
```

**Dependency direction:** `app/api/project_runner.py` → `domain/sponsor/*`

No reverse imports. No circular dependencies. Neither engine was modified.

---

## H3 — Runtime Payload

**sessionStorage key:** `lastSponsorSchedule`

**Payload structure:**
```json
{
  "periods": [
    {
      "period_index": 0,
      "equity_injected_keur": 500.0,
      "distribution_received_keur": 0.0,
      "wht_on_distribution_keur": 0.0,
      "net_cashflow_keur": -500.0,
      "capital_account_balance_keur": 500.0
    },
    ...
  ],
  "summary": {
    "total_equity_injected_keur": 500.0,
    "total_distributions_received_keur": 173572.29,
    "total_wht_keur": 0.0,
    "total_net_cashflow_keur": 173072.29,
    "gross_sponsor_return_multiple": 347.14,
    "gross_sponsor_irr": 0.30,
    "gross_sponsor_moic": 347.14,
    "xirr_converged": true,
    "investor_id": "SPONSOR-1",
    "entity_code": "SPV"
  },
  "source": "SponsorCashflowRunner + SponsorIrrRunner + SponsorMoicRunner"
}
```

**Serializer:** `_serialize_sponsor_schedule()` in `app/api/project_runner.py`.
Rounds to 2dp. Normalizes non-finite floats to `null`. No financial calculations.

---

## H4 — Capital Structure Constants

`_SPONSOR_CAPITAL_STRUCTURES` in `project_runner.py` defines the known project types:

| Project | LP (kEUR) | GP (kEUR) | Total Equity (kEUR) |
|---------|-----------|-----------|---------------------|
| TUHO    | 400       | 100       | 500                 |
| Oborovo | 400       | 100       | 500                 |

**Note:** These are simplified Phase 7A capital structure constants for the runtime bridge.
Full LP/GP waterfall allocation, preferred return, and promote are available in
`domain/sponsor/multi_investor_waterfall_runner.py` but require additional wiring
(see Remaining Gaps below).

For project types not in `_SPONSOR_CAPITAL_STRUCTURES`, `_run_sponsor_engine` returns `None`
and the sponsor schedule degrades gracefully to the unavailable panel.

---

## H5 — UI Wiring

**Template:** `app/templates/partials/_sheet_sponsor_partial.html`

**Pre-Run:** `sponsor-unavailable-panel` shown (existing `empty-state-notice--warn` pattern).

**Post-Run:** `sponsor-schedule-block` populated from `sessionStorage["lastSponsorSchedule"]`.
JS reads and renders:
- Per-period table: period index, equity injected, distribution received, WHT, net cashflow, capital account balance
- Summary KPI row: total equity, total distributions, IRR, MOIC

Zero client-side financial calculations. JS only reads and renders engine data.

---

## Files Changed

| File | Change |
|------|--------|
| `app/api/project_runner.py` | `_run_sponsor_engine()` + `_serialize_sponsor_schedule()` + `"sponsor_schedule"` in return dict |
| `app/services/run_service.py` | `sponsor_schedule` threaded through 3 paths + `sessionStorage["lastSponsorSchedule"]` |
| `app/templates/partials/_sheet_sponsor_partial.html` | JS reads `lastSponsorSchedule`, renders read-only table |
| `tests/test_excel_parity_stack_h.py` | 40 characterization tests |
| `docs/EXCEL_PARITY_STACK_H_SPONSOR_RUNTIME.md` | This document |

---

## Guardrail Confirmation

- No sponsor formulas changed — `run_sponsor_cashflows`, `run_sponsor_irr`, `run_sponsor_moic` unchanged
- No waterfall formulas changed — `waterfall_core.py` unchanged
- No circular dependencies — `domain/sponsor/*` does not import from `app/`
- No client-side JS calculations — JS only reads and renders engine-provided data
- No duplicated sponsor calculations — `project_runner.py` delegates to the domain engine
- `domain/*`, `waterfall_core.py`, `input_adapter.py`, `project_factories.py` — all untouched

---

## Remaining Parity Gaps

| Gap | Status | Blocker |
|-----|--------|---------|
| LP/GP waterfall allocation | Not wired | `multi_investor_waterfall_runner.py` requires investor registry inputs not yet available in `run_project()` |
| Preferred return / promote | Not wired | Depends on LP/GP waterfall allocation |
| Net IRR / net MOIC | Not computed | `net_sponsor_irr_placeholder` / `net_multiple_placeholder` are None in Phase 7B |
| WHT on distributions | Zero in H2 | `wht_rate=0.0` used in simplified bridge; real WHT rate is in `TaxParams.wht_sponsor_dividends` — future improvement |
| HoldCo opex | Zero in H2 | SPV-level bridge; HoldCo opex not applicable at this level |
