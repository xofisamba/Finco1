# Phase 7I Construction Runtime Review

**Branch:** `phase7i-construction-runtime-review`  
**Base:** `origin/main` (`f5f809cd49d0e03a1271f3ee03a30cd169e517ac`)  
**Reviewing merged commit:** `45790a6fa397da4b0596923efa953443c75f3a34`  
**Date:** 2026-05-16  
**Reviewer:** Claude (code review + logic analysis)  
**Task source:** cofix prompt, phase7i_construction_runtime_review

---

## 1. Changed Files

| File | Type |
|---|---|
| `docs/phase7i_construction_schedule_engine.md` | documentation |
| `domain/construction/__init__.py` | package init |
| `domain/construction/config.py` | new module |
| `domain/construction/capex_schedule.py` | new module |
| `domain/construction/engine.py` | new module |
| `domain/construction/funding_allocation.py` | new module |
| `domain/construction/idc_calculator.py` | new module |
| `domain/construction/result.py` | new module |
| `domain/construction/templates/__init__.py` | new module |
| `domain/construction/templates/tuho.py` | new module |
| `domain/construction/templates/oborovo.py` | new module |
| `tests/test_construction_capex_schedule.py` | new test |
| `tests/test_construction_funding_allocation.py` | new test |
| `tests/test_construction_idc_calculator.py` | new test |
| `tests/test_tuho_construction_schedule_bridge.py` | new test |
| `tests/test_oborovo_construction_schedule_bridge.py` | new test |

**Total: 15 files** — all net-new, no modified existing files.

**No runtime behavior changed.** This PR adds a net-new offline diagnostic engine.

---

## 2. Offline Construction Engine Logic — Verification

### 2.1 Monthly Construction Uses

`build_monthly_uses()` in `capex_schedule.py` supports `LINEAR` and `CUSTOM` profiles.

For TUHO (18 months) and Oborovo (12 months), `CUSTOM` is used. Monthly values are
provided as a tuple directly in the config.

**Assessment:** ✅ Correct. Matches Excel discovery monthly construction cash flows.

### 2.2 Source-Waterfall Funding Sequence

`allocate_source_waterfall()` in `funding_allocation.py` applies funding in strict order:
1. Equity shares (capped)
2. SHL (capped)
3. Junior / mezzanine / carbon fund (capped)
4. Senior debt (residual)

Per-month logic:
- Cumulative uses are tracked
- Each source cap is applied sequentially
- Monthly draw = current cumulative − prior cumulative
- Validation: `abs(monthly_funding − monthly_uses) <= tolerance`

**Assessment:** ✅ Correct. Matches Excel source-waterfall priority order (equity → SHL → junior → senior).

### 2.3 SHL IDC — Full-Source Elapsed Compound

`compute_full_source_elapsed_compound_idc()` in `idc_calculator.py`:
```python
elapsed_years = (cod_date - investment_date).days / day_count_denominator
return source_draw_keur * ((1.0 + annual_rate) ** elapsed_years - 1.0)
```

This applies the full SHL draw amount as a single compound calculation over the entire
construction elapsed period. **Not** monthly compounding on the draw balance.

**Assessment:** ✅ Correct. Matches Excel SHL IDC method (full-source elapsed compound).

Verified in TUHO template:
- SHL draw: 29,135.176 kEUR
- SHL rate: 8.0%
- Elapsed: ~1.5 years (2028-06-30 → 2029-12-30)
- SHL IDC: 3,568.688 kEUR ✅ matches test assertion

Verified in Oborovo template:
- SHL draw: 14,620.774 kEUR
- SHL rate: 8.0%
- Elapsed: ~1.0 years (2029-06-29 → 2030-06-29)
- SHL IDC: 1,169.662 kEUR ✅ matches test assertion

### 2.4 Senior IDC — Monthly Cumulative-Balance Method

`compute_senior_monthly_cumulative_idc()` in `idc_calculator.py`:
```python
idc_t = (senior_rate + base_rate_t) * prior_cumulative_senior_balance * period_fraction_t
```

Each month: interest on the **prior cumulative** senior draw balance (not the current month's draw).

**Assessment:** ✅ Correct. Matches Excel monthly cumulative-balance senior IDC method.

**Calibration note:** The TUHO template uses an effective rate of 6.045% and Oborovo
uses 5.895% to hit the discovered senior IDC targets (1,519.564 kEUR and 1,086.032 kEUR
respectively). This is because the Excel base-rate rows are not yet modeled. The notes
in the templates flag this explicitly. This is acceptable for an offline engine.

---

## 3. Runtime Integration Risk Assessment

### 3.1 What wiring construction output into runtime would require

The `ConstructionScheduleResult` object exposes these fields intended for runtime use:

| Field | TUHO | Oborovo | Purpose |
|---|---:|---:|---|
| `opening_shl_balance_keur` | 32,703.864 | 15,790.436 | Runtime opening SHL balance |
| `opening_senior_balance_keur` | 45,878.837 | 43,938.299 | Runtime opening senior balance |
| `total_shl_draw_keur` | 29,135.176 | 14,620.774 | SHL principal draw |
| `total_senior_draw_keur` | 43,359.274 | 42,852.267 | Senior principal draw |
| `total_shl_idc_keur` | 3,568.688 | 1,169.662 | SHL IDC (capitalized into opening balance) |
| `total_senior_idc_keur` | 1,519.564 | 1,086.032 | Senior IDC |
| `total_equity_draw_keur` | 500.000 | 500.000 | Equity contribution |

### 3.2 Risk: Double-Counting IDC

**Risk level: HIGH**

Both TUHO and Oborovo currently have hard-coded SHL and senior IDC values in their
project factory inputs. If the construction engine output is wired into runtime **without
removing or overriding the existing hard-coded values**, senior IDC would be counted twice:

- Existing: `shl_idc_keur` (from project factory)
- New: `total_senior_idc_keur` added to opening senior balance

The `ConstructionScheduleResult` adds IDC to opening balances when
`senior_idc_capitalized=True` / `shl_idc_capitalized=True`. The templates both set
`shl_idc_capitalized=True`. If the project factory also sets `shl_idc_keur` for operating
periods, the SHL IDC could be counted twice.

**Current factory values (approximate):**
- TUHO `shl_idc_keur`: already set in factory (phase 6B?)
- Oborovo `shl_idc_keur`: phase 7G-A identified this was missing (set to 0, needs 1,169)

The construction engine could correctly set Oborovo's SHL opening balance (15,790 with
IDC included), but if the factory also applies operating-period SHL IDC separately, there
is a double-count risk.

**Mitigation:** The runtime adapter must explicitly override or clear the factory-level
IDC inputs when the construction schedule is activated.

### 3.3 Risk: Opening Senior Balance vs. Project Factory Assumptions

**Risk level: MEDIUM**

Current project factory opening senior balance for TUHO: ~43,359 kEUR (senior draw only).
Construction engine adds senior IDC (1,519.564 kEUR) on top, giving opening balance
45,878.837 kEUR.

If runtime already bakes in a different opening senior balance assumption, the
difference will cause waterfall divergence from the first operating period.

**Mitigation required:** The runtime flag must validate that the construction engine's
opening senior balance matches the existing waterfall assumptions before enabling the flag.

### 3.4 Risk: TUHO Senior IDC Calibration vs. Actual Excel

**Risk level: LOW (but flagged)**

The TUHO template uses an effective rate of 6.045% to hit the Excel IDC target. This
effective rate is a calibration proxy because the actual base-rate rows from Excel
were not modeled in the `senior_base_rates` input. The template notes this explicitly.

If Excel's actual base-rate detail differs from this effective rate, wiring the
construction engine into runtime would use the effective rate and potentially produce
different senior IDC than Excel.

**Status:** Acknowledged in template notes. Not a blocker for the offline engine.
Must be resolved before runtime wiring.

### 3.5 Risk: Oborovo Month 1 Senior Draw Start

**Risk level: LOW**

Oborovo starts senior debt funding in month 1 alongside SHL (unlike TUHO which starts
senior debt in month 3). The construction engine correctly handles this — month 1
`equity_draw=500`, `shl_draw=14,620.774`, `senior_draw=1,384.663`.

This is fine as long as the runtime waterfall construction-period treatment can
handle senior draws starting at month 1.

### 3.6 Risk: Manual Existing Input Overrides

**Risk level: MEDIUM**

Project factories may have manual overrides on opening balances or senior/SHL
parameters. The runtime adapter must either:
a) respect manual overrides and skip construction-engine values, or
b) warn when construction-engine values differ from manual overrides

Without a defined override behavior, a manual override of opening senior balance
combined with construction flag ON would produce inconsistent results.

**Mitigation:** Define clear precedence: manual overrides take priority over
construction engine values, and a validation diff must be surfaced before flag activation.

### 3.7 Risk: Project Factory Assumptions vs. Construction Engine Outputs

**Risk level: MEDIUM**

Both TUHO and Oborovo project factories have existing assumptions:
- TUHO: `shl_idc_keur` and `shl_principal_keur` already set
- Oborovo: `shl_idc_keur=0` (phase 7G identified it should be 1,169)

If the construction runtime flag is activated, the factory assumptions must be
aligned with the construction schedule outputs. Currently they are not aligned
(Oborovo's factory has `shl_idc_keur=0` while the construction engine computes 1,169.662).

**Mitigation:** Before runtime flag activation, the project factory inputs for both
projects must be updated to match construction engine outputs.

---

## 4. Exact Fields Needed Before Runtime Flag Can Safely Exist

The following fields must be explicitly defined and validated before the
`use_construction_schedule` flag can be switched on:

### Opening Balances
| Field | Source | Validation |
|---|---|---|
| `construction_opening_senior_balance_keur` | `ConstructionScheduleResult.opening_senior_balance_keur` | Must match existing waterfall assumption ±1 kEUR |
| `construction_opening_shl_balance_keur` | `ConstructionScheduleResult.opening_shl_balance_keur` | Must match existing SHL waterfall opening ±1 kEUR |

### IDC Treatment
| Field | Source | Validation |
|---|---|---|
| `senior_idc_keur` | `ConstructionScheduleResult.total_senior_idc_keur` | Must not conflict with factory `senior_idc_keur` |
| `shl_idc_keur` | `ConstructionScheduleResult.total_shl_idc_keur` | Must not conflict with factory `shl_idc_keur` |
| `senior_idc_capitalized` | Config flag | Must be True if senior IDC is added to opening balance |
| `shl_idc_capitalized` | Config flag | Must be True if SHL IDC is added to opening balance |

### Draw Schedules
| Field | Source | Validation |
|---|---|---|
| `senior_principal_draw_schedule` | Monthly entries cumulative | Must span construction_months; first draw must be > 0 for TUHO (month 3) and > 0 for Oborovo (month 1) |
| `shl_principal_draw_schedule` | Monthly entries cumulative | Must align with SHL waterfall engine |
| `equity_draw_schedule` | Monthly entries | TUHO: 500 all in month 1; Oborovo: 500 in month 1 |

### Validation Deltas
| Check | Tolerance | Behavior on mismatch |
|---|---|---|
| Opening senior vs existing assumption | ±1 kEUR | Warn; block flag activation |
| Opening SHL vs existing assumption | ±1 kEUR | Warn; block flag activation |
| Senior IDC vs target | ±0.01 kEUR | Warn; block flag activation |
| SHL IDC vs target | ±0.01 kEUR | Warn; block flag activation |
| Total uses vs funding | ±0.05 kEUR | Raise in validation |

### Manual Override Behavior
- If manual overrides exist on `senior_opening_balance`, `shl_opening_balance`, or
  `shl_idc_keur`, the construction engine values must NOT override them
- A clear UI message must state: "Construction schedule values differ from manual
  overrides; manual overrides take priority"
- The override field names in project factories must be explicitly documented

### Warning Behavior
- When `construction_opening_senior_balance_keur` differs from runtime assumption by
  more than 1 kEUR: surface warning listing both values
- When `total_senior_idc_keur` differs from existing senior IDC input by more than 1 kEUR:
  surface warning about potential IDC double-count
- When `shl_idc_keur` differs from factory value: surface warning about SHL IDC treatment

---

## 5. Recommended Next Branch

**Recommendation: Option A — `phase7i-construction-runtime-flag`**

### Rationale

The construction engine is a clean, isolated, offline diagnostic. All prerequisites
for a runtime flag exist within the `domain/construction/` package itself — the engine,
templates, and test fixtures are all in place. The only remaining work is the runtime
adapter and flag wiring.

Options B (senior debt alignment) and C (CAPEX line-item template) are both valid
future work but neither is a prerequisite for the construction runtime flag. The
construction engine does not depend on senior debt recalibration — it produces its own
opening balances independently. A CAPEX line-item template is similarly orthogonal to
the construction schedule wiring.

The logical sequence is:
1. Wire construction schedule into runtime (Phase 7I continuation) — **this recommendation**
2. Senior debt alignment (Phase 7J) — can follow independently
3. CAPEX line-item template — can follow independently

### Why not B (senior debt alignment) first?

Senior debt alignment (ensuring the runtime waterfall's opening senior balance
assumption matches the construction engine's output) is a valuable prerequisite, but
it is not strictly required to demonstrate that the construction runtime flag does
not break existing behavior. You can:
- Enable construction flag as default-OFF
- Validate that with flag-OFF, TUHO and Oborovo produce identical results to current HEAD
- Build the runtime adapter to compute opening balances from the construction engine
- Compare them against existing assumptions without immediately replacing them

This gives you a clean comparison point before making any changes to senior debt logic.

### Why not C (CAPEX line-item template) first?

The construction engine produces CAPEX draw schedules, but the CAPEX line-item
template is about how those draws are categorized and displayed in the UI. The
construction runtime flag only needs to wire the *total* CAPEX draw amounts into
opening balances — it does not need per-line-item categorization. Those are separate
concerns.

---

## 6. Exact Allowed Scope for `phase7i-construction-runtime-flag`

### Allowed changes (green)

- `domain/construction/` — already exists, modifications OK
- `app/project_factories.py` — add `use_construction_schedule: bool = False` flag to
  `ProjectInputs` (or `ProjectInfo`)
- `app/ui_runner.py` or `app/waterfall_runner.py` — add conditional path when
  `use_construction_schedule=True` that calls `compute_construction_schedule()` and
  passes results into waterfall inputs
- `domain/inputs.py` or wherever `ProjectInputs` is defined — add the flag field
- `domain/waterfall/waterfall_engine.py` — accept construction schedule result as input
  and use its `opening_senior_balance_keur` / `opening_shl_balance_keur` values
- New file: `domain/construction/runtime_adapter.py` — bridge from
  `ConstructionScheduleResult` to waterfall inputs
- New test: isolated tests proving flag-OFF equivalence and flag-ON opening balance parity
- `docs/phase7i_construction_runtime_review.md` — update with runtime flag spec

### Hard rejection (red)

The following files/directories must NOT be modified in this branch:
- `app/waterfall_core.py` ❌
- `domain/waterfall/` (all files) ❌
- `domain/revenue/` (all files) ❌
- `domain/opex/` (all files) ❌
- `domain/tax/` (all files) ❌
- `domain/inputs.py` (existing fields — only new flag field allowed) ❌
- `app/project_factories.py` — only add the flag, do not change existing factory
  logic or hardcoded values ❌
- `domain/sponsor/` (all files) ❌
- `domain/distribution_account.py` ❌
- Cache-related files ❌
- HTMX UI files ❌

### Runtime behavior requirements

1. **Flag-off equivalence:** Running TUHO and Oborovo with `use_construction_schedule=False`
   must produce exactly the same waterfall results as current HEAD (verified by comparing
   full period-by-period output, not just aggregate metrics)

2. **Opening balance parity (isolated):** When `use_construction_schedule=True` for TUHO,
   the runtime's opening senior balance must match `ConstructionScheduleResult.opening_senior_balance_keur`
   (45,878.837 kEUR) to within 1 kEUR, verified in isolation before any downstream cash
   routing is activated

3. **No double-count:** Senior IDC and SHL IDC must appear exactly once in the runtime —
   either in the construction opening balance (if capitalized) or in subsequent operating
   period calculations, never both

4. **Validation gate:** If computed construction opening balances differ from existing
   project factory assumptions by more than the tolerances in Section 4, the runtime
   must surface a warning and block activation unless overrides are explicitly confirmed

### Prerequisites for branch creation

Before creating `phase7i-construction-runtime-flag`, confirm:
- [ ] TUHO factory: `shl_idc_keur` and `senior_idc_keur` are documented and not double-counted
- [ ] Oborovo factory: `shl_idc_keur` is set (currently 0, should be 1,169.662 from construction engine)
- [ ] Senior IDC base-rate resolution: TUHO effective rate (6.045%) and Oborovo effective rate (5.895%)
    are documented as temporary calibrations, with a plan to replace them with actual base-rate inputs
- [ ] Test fixtures: TUHO and Oborovo construction schedule results are frozen as golden fixtures
    for flag-on comparison tests

---

## 7. Summary

| Item | Finding |
|---|---|
| Code changed | Yes — 15 new files, no modified existing files |
| Runtime behavior changed | No — offline diagnostic engine only |
| Funding sequence | ✅ Matches Excel: equity → SHL → junior → senior |
| SHL IDC method | ✅ Full-source elapsed compound |
| Senior IDC method | ✅ Monthly cumulative-balance |
| SHL opening balance | TUHO: 32,703.864 kEUR; Oborovo: 15,790.436 kEUR |
| Senior opening balance | TUHO: 45,878.837 kEUR; Oborovo: 43,938.299 kEUR |
| Key integration risk | Double-counting IDC when wiring into runtime |
| Key blocking issue | Oborovo `shl_idc_keur=0` in factory vs construction engine's 1,169.662 |
| Recommended next branch | **A) `phase7i-construction-runtime-flag`** |
| Senior debt alignment needed first | No — can run in parallel, not a prerequisite |
| CAPEX line-item template needed first | No — orthogonal concern |