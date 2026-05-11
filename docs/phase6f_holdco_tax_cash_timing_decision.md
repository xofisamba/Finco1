# Phase 6F — HoldCo Tax Cash Timing: Architectural Decision Record

**Repository:** xofisamba/Finco1
**Branch:** `phase6f-holdco-tax-cash-timing-decision`
**Date:** 2026-05-11
**Type:** Architecture Decision Record (ADR)
**Scope:** Documentation only — no implementation changes

---

## Status

**ACCEPTED** — Decision recorded. Implementation deferred to Phase 7.

---

## Context

Phase 6C built a complete HoldCo tax engine (`run_holdco_tax_engine()`) that computes accrual CIT
payable per period. The engine correctly captures the tax base (dividend income + SHL interest
income − HoldCo OpEx) and calculates the CIT liability.

However, the current implementation is **accrual-only**. CIT is computed as owed for each period,
but the model does not address **when the cash is actually paid** — which is a critical input for
Sponsor IRR and for the HoldCo-level cash flow waterfall.

This document records the architectural decision for how HoldCo cash tax timing should be
handled when Phase 7 begins sponsor economics integration.

---

## 1. Current Accrual-Only State

The HoldCo tax engine today produces per-period accrual CIT:

```
Period 1: taxable_income = 1,000 kEUR  →  accrual CIT = 180 kEUR
Period 2: taxable_income = 1,200 kEUR  →  accrual CIT = 216 kEUR
...
```

**What exists:**
- `run_holdco_tax_engine()` — computes accrual CIT per period
- `calculate_holdco_taxable_income()` — computes per-period tax base
- `calculate_withholding_tax_keur()` — WHT amounts per entity per period
- `HoldCoTaxResult` dataclass — contains per-period accrual CIT values
- Audit export sheets — show accrual amounts per entity

**What is missing:**
- No cash payment timing model
- No deferred tax balance tracking
- No cash flow integration with HoldCo cash waterfall
- No distinction between accrual CIT and cash CIT for Sponsor IRR

The `HoldCoTaxResult` holds `cit_by_period_keur` (accrual) but does not track when those amounts
are actually paid. This is acceptable for audit visibility but is insufficient for accurate
Sponsor IRR calculation.

---

## 2. Why Timing Matters for Sponsor IRR

Sponsor IRR is sensitive to the timing of cash outflows. At the HoldCo level, the relevant
cash outflow is **HoldCo CIT paid** (not SPV CIT — those are upstream).

The timing of HoldCo CIT payments affects:

### 2.1 Equity IRR at HoldCo Level

The Sponsor's equity investment flows into HoldCo. HoldCo collects dividends from SPVs, pays
interest on SHL, pays HoldCo OpEx, pays CIT, and distributes the remainder to Sponsor.

If CIT payment is **delayed** relative to the period in which it accrues, the cash available
for distribution to Sponsor is higher in the near term — inflating equity IRR if not corrected.

If CIT payment is **accelerated** (paid before it legally accrues), equity IRR is reduced.

### 2.2 Sponsor Waterfall Timing

In a typical sponsor waterfall, distributions to Sponsor are constrained by DSCR tests at the SPV
level and leverage ratios at the HoldCo level. If HoldCo CIT is recognized as a liability but
not yet paid, the DSCR test may be understating the true obligation.

Conversely, if CIT is paid before it is recognized as a liability, the waterfall shows an
unanticipated outflow.

### 2.3 Determinism Requirement

The model must be **deterministic** — same inputs produce same outputs every time. Any cash timing
model must be reproducible across runs and not introduce non-deterministic behavior (e.g.,
payment dates based on calendar day, business day conventions, or external data lookups).

### 2.4 Sponsor IRR Sensitivity

For a wind farm with typical HoldCo-level leverage, a one-period delay in HoldCo CIT payments
can shift equity IRR by approximately **+5–15 basis points** depending on the effective tax rate
and leverage ratio. This is material for sponsor covenant compliance.

---

## 3. Candidate Models

Three candidate models were evaluated for HoldCo CIT cash timing:

### 3.1 Model A — Deterministic One-Period Lag (DEFAULT)

**Mechanism:** Cash CIT payment in period *t* = Accrual CIT calculated for period *t−1*.

```
Accrual CIT (period 1) = 180 kEUR  →  Cash CIT paid (period 2) = 180 kEUR
Accrual CIT (period 2) = 216 kEUR  →  Cash CIT paid (period 3) = 216 kEUR
```

**Pros:**
- Deterministic — purely based on period index, no calendar dependency
- Simple to implement and audit
- Jurisdictional flexibility: override capability allows jurisdiction-specific lag
- Preserves accrual/cash distinction clearly in model logic
- No circular dependencies
- Sponsor IRR impact is small and bounded

**Cons:**
- Abstract: does not reflect any actual tax payment calendar
- Some jurisdictions pay CIT quarterly or annually; one-period lag is an approximation
- HoldCo CIT paid in period 2 is based on period 1 income, which may not align with legal payment due dates

**Jurisdiction override example:**
```python
# Per-country override:
# HR: two-period lag (CIT paid with 6-month delay)
# ME: zero-period lag (accrual = cash, paid same period)
# BA: one-period lag (default)
```

### 3.2 Model B — Accrual = Cash (Same Period)

**Mechanism:** Cash CIT payment = Accrual CIT for the same period. No lag.

```
Accrual CIT (period 1) = 180 kEUR  →  Cash CIT paid (period 1) = 180 kEUR
Accrual CIT (period 2) = 216 kEUR  →  Cash CIT paid (period 2) = 216 kEUR
```

**Pros:**
- Simplest model: no timing distinction
- Accurate for jurisdictions with monthly CIT instalments
- No additional fields required in HoldCoTaxResult

**Cons:**
- Inaccurate for most jurisdictions with quarterly or annual CIT
- Does not reflect cash flow timing lag in any jurisdiction
- Cannot be correct for all countries simultaneously

### 3.3 Model C — Legal Due Date Mapping

**Mechanism:** CIT payment due dates mapped to specific model periods based on jurisdiction-specific tax calendar.

```
HR CIT (annual): due 30 June following tax year  →  model period N (closest period)
ME CIT (quarterly): quarterly instalments  →  model periods N-1, N, N+1, N+2
BA CIT (monthly): monthly instalments  →  all model periods
```

**Pros:**
- Most accurate for jurisdictions with known payment calendars
- Reflects actual cash flow timing precisely

**Cons:**
- Requires per-country due date mappings
- Introduces **calendar date dependencies** — breaks reproducibility if model reference date changes
- Requires external data (jurisdiction tax calendars) not in scope for Phase 6
- More complex to audit and test
- Not deterministic across model runs with different reference dates
- Cannot be fully validated without legal/tax counsel engagement

---

## 4. Final Decision

**Model A — Deterministic One-Period Lag** is adopted as the **default**.

### Rationale

1. **Determinism** — Model A is purely period-index based. It does not depend on calendar dates,
   business days, or external lookups. Same inputs → same outputs → reproducible.

2. **Simplicity** — No new schema fields required in Phase 7 beyond a per-country `cit_payment_lag`
   integer field in `HoldCoTaxConfig`. The lag is applied in the cash timing transform layer.

3. **Preserves accrual/cash distinction** — Accrual CIT continues to be reported separately from
   Cash CIT in audit sheets. The `HoldCoTaxResult` can be extended with `cit_cash_by_period_keur`
   alongside the existing `cit_accrual_by_period_keur`.

4. **Jurisdiction override capability** — Model A naturally supports per-country lag overrides
   in `HoldCoTaxConfig`. Model B (zero lag) and Model C (legal calendar) are both implementable
   as jurisdiction-specific lag values.

5. **Sponsor IRR materiality** — The one-period lag is a bounded, small shift. Phase 7 sponsor
   waterfall integration can correct for it explicitly.

6. **No waterfall changes required** — The HoldCo cash waterfall receives `cit_cash_by_period_keur`
   as an input in Phase 7. The tax engine itself is not modified. The accrual engine output
   (`cit_by_period_keur`) remains unchanged.

### Default Value

| Parameter | Default | Unit |
|-----------|---------|------|
| `cit_payment_lag` | `1` | model periods (semiannual) |

A lag of `1` with semiannual model periods means CIT is paid approximately 6 months after it accrues.

### Jurisdiction Override Examples

| Country | Lag | Interpretation |
|---------|-----|----------------|
| HR (annual CIT) | `1` | Paid next semiannual period (approx. 6-month delay) |
| HR (monthly instalments) | `0` | Accrual = cash for monthly instalment countries |
| ME | `2` | Two semiannual periods (~12 months) for jurisdictions with annual CIT |
| BA | `1` | Default — one period lag |

---

## 5. Architectural Constraints

The following constraints must be respected in any Phase 7 implementation:

### 5.1 No Tax Engine Modification

The HoldCo tax engine (`run_holdco_tax_engine()`) computes **accrual** CIT. Cash timing is
a **transform layer** applied downstream, not a change to the engine itself.

```
HoldCo Tax Engine (accrual)  →  Cash Timing Transform (lag applied)  →  Cash Flow Input
```

### 5.2 No Waterfall Modifications in Phase 6F

Phase 6F is documentation-only. No waterfall code is modified. Phase 7 integration will
add `cit_cash_by_period_keur` as a new input parameter to the HoldCo cash waterfall,
not as a modification of existing waterfall logic.

### 5.3 No Sponsor IRR Implementation in Phase 6F

Sponsor waterfall, Sponsor IRR, and MOIC are Phase 7 topics. Phase 6F documents the
timing question but does not implement the integration.

### 5.4 Accrual and Cash Remain Separate

Both `cit_accrual_by_period_keur` and `cit_cash_by_period_keur` must be tracked separately
in audit sheets. They are not merged into a single figure.

### 5.5 Jurisdiction Override Capability Preserved

Any cash timing implementation must support per-country lag configuration via
`HoldCoTaxConfig.cit_payment_lag` or equivalent. Hardcoding a single lag for all
jurisdictions is not acceptable.

### 5.6 Determinism Preserved

Cash timing must not introduce calendar-date dependencies. The model must produce identical
outputs on every run. Lag is expressed in **model periods**, not calendar days.

---

## 6. Future Integration Flow

The following describes the intended Phase 7 integration path for HoldCo CIT cash timing:

### 6.1 Schema Extension

```python
@dataclass(frozen=True)
class HoldCoTaxConfig:
    cit_payment_lag: int = 1  # model periods between accrual and cash payment
    # ... existing fields unchanged ...
```

### 6.2 HoldCoTaxResult Extension

```python
@dataclass(frozen=True)
class HoldCoTaxResult:
    cit_accrual_by_period_keur: tuple[float, ...]   # existing: per-period accrual CIT
    cit_cash_by_period_keur: tuple[float, ...        # NEW: per-period cash CIT (after lag)
    wht_by_period_keur: tuple[float, ...             # existing
    taxable_income_by_period_keur: tuple[float, ...  # existing
    # ...
```

### 6.3 Cash Timing Transform

```python
def apply_cit_cash_timing(
    accrual_by_period: tuple[float, ...],
    lag: int,
) -> tuple[float, ...]:
    """Apply deterministic lag to accrual CIT to produce cash CIT."""
    if lag == 0:
        return accrual_by_period
    # Shift by lag: period[t] cash = period[t-lag] accrual
    # First `lag` periods: cash = 0 (no prior accrual to draw from)
    cash = tuple(0.0 for _ in range(lag)) + accrual_by_period[:-lag]
    return cash
```

### 6.4 HoldCo Cash Waterfall Integration

In Phase 7, the HoldCo cash waterfall receives both accrual and cash CIT:

```python
# In HoldCo cash waterfall (Phase 7):
available_cash = (
    dividend_income
    + shl_interest_income
    - holdco_opex
    - cit_cash_by_period_keur[period]   # cash outflow from HoldCo CIT payment
    - wht_by_period_keur[period]         # WHT remittance
)
```

The accrual figure (`cit_accrual_by_period_keur`) continues to be used for audit reporting only.

### 6.5 Audit Sheet Updates (Phase 7)

Two new columns added to HoldCo Tax Summary audit sheet:
- `Accrual CIT (kEUR)` — existing, from `cit_accrual_by_period_keur`
- `Cash CIT (kEUR)` — new, from `cit_cash_by_period_keur`

The cash column reflects the actual cash outflow used in the waterfall. Both are shown
together so reviewers can see the timing difference.

---

## 7. Explicit Non-Scope

The following are explicitly out of scope for this decision and Phase 7 integration:

| Item | Reason |
|------|--------|
| Tax engine modifications | Accrual engine unchanged; cash timing is a transform |
| Deferred tax asset/liability tracking | Requires monthly model; not in Phase 7 scope |
| Monthly model | Semiannual periods only; cash timing in model periods not calendar months |
| Sponsor waterfall | Phase 7 sponsor economics topic |
| Sponsor IRR / MOIC | Phase 7 sponsor economics topic |
| Promote waterfall | Phase 7 sponsor economics topic |
| Tax payment scheduling (legal calendar) | Would introduce calendar-date dependencies; not deterministic |
| Treaty WHT engine | Cross-border treaty not modeled |
| Actual jurisdiction payment calendars | Requires legal/tax counsel; not available in model inputs |
| WHT remittance timing | WHT is audit-visible only; no cash flow integration in Phase 6 or 7 |
| HoldCo runner behavior changes | `run_holdco_tax_engine()` unchanged; output extended |

---

## 8. Risks

### 8.1 HIGH — Cash Timing Not Integrated Before Sponsor Economics Begins

**Risk:** Phase 7 begins sponsor waterfall integration without cash timing, using accrual CIT
in the waterfall. Sponsor IRR is understated (CIT appears to be paid before it actually is).

**Mitigation:** Phase 7 must include `cit_cash_by_period_keur` as a first-class input to the
HoldCo cash waterfall. Accrual CIT must not be used as a cash flow input.

**Blocker for Phase 7:** Yes — sponsor economics cannot begin without cash timing resolution.

---

### 8.2 MEDIUM — One-Period Lag Is a Rough Approximation

**Risk:** The deterministic one-period lag may not reflect actual jurisdiction payment calendars.
For HR (annual CIT), the actual payment date is ~June following the tax year. For semiannual
model periods, this maps to approximately one period of lag, but the exact mapping is imprecise.

**Mitigation:** The lag is configurable per country. When jurisdiction-specific payment calendars
are available (Phase 8+), the lag can be overridden per template. The approximation is documented
and bounded.

**Blocker:** No — approximation is acceptable for screening model accuracy.

---

### 8.3 MEDIUM — Circular Reference Risk in HoldCo Cash Waterfall

**Risk:** If HoldCo CIT cash payments are fed back into the taxable income calculation (e.g.,
via SHL interest or distribution timing), a circular reference could form.

**Mitigation:** HoldCo CIT is deducted from **post-tax cash** in the waterfall, not from taxable
income. Taxable income computation uses `dividend_income + shl_interest_income - holdco_opex`,
which does not include CIT. No circular reference is possible.

**Blocker:** No — structurally impossible given current architecture.

---

### 8.4 LOW — Lag=0 vs Lag=1 for Monthly Instalment Jurisdictions

**Risk:** Some jurisdictions (e.g., certain EU countries) pay CIT monthly via instalments.
For those, `lag=0` (accrual = cash) is more accurate. But the model uses semiannual periods,
which cannot capture monthly instalments at any level of granularity.

**Mitigation:** Document the granularity limitation. `lag=0` for monthly instalment countries
is still an approximation given semiannual model periods. The limitation is accepted.

**Blocker:** No — semiannual model granularity is a known constraint.

---

### 8.5 LOW — Default Lag=1 May Not Suit All Sponsor Waterfall Structures

**Risk:** Some sponsor waterfalls compute DSCR before HoldCo CIT is paid. If CIT is paid with a
one-period lag, the DSCR test in period 1 may show artificially high available cash.

**Mitigation:** Sponsor waterfall Phase 7 design should explicitly account for CIT cash timing
when computing DSCR. The audit trail (`cit_accrual` vs `cit_cash`) is available to reviewers.

**Blocker:** No — sponsor waterfall design is Phase 7.

---

## 9. Recommendation for Phase 7

### Phase 7 HoldCo Tax Cash Timing Implementation Recommendation

**Recommended approach:** Implement as described in this ADR — extend `HoldCoTaxConfig` with
`cit_payment_lag` (default `1`), compute `cit_cash_by_period_keur` via the cash timing transform
in Phase 7's HoldCo cash waterfall, and add two new columns to the HoldCo Tax Summary audit sheet.

### Decision Record Summary

| Decision | Choice |
|----------|--------|
| Cash timing model | Model A — Deterministic One-Period Lag (default) |
| Default lag | `1` semiannual model period |
| Override mechanism | Per-country `cit_payment_lag` in `HoldCoTaxConfig` |
| Tax engine changes | None — transform applied downstream |
| Accrual/cash distinction | Both tracked separately in `HoldCoTaxResult` |
| Sponsor IRR integration | Phase 7 sponsor waterfall topic; cash timing is prerequisite |
| Implementation phase | Phase 7 (this decision is documentation-only) |

### Pre-Phase-7 Prerequisites

Before Phase 7 begins, the following should be confirmed:

1. **HoldCo cash waterfall contract** — Does the waterfall accept `cit_cash_by_period_keur` as
   an input? Is the accrual figure (`cit_accrual_by_period_keur`) still available for audit?
2. **HoldCoTaxConfig schema** — Is `cit_payment_lag` field accepted in the existing config schema?
3. **DSCR test interaction** — Does the HoldCo DSCR test need to account for CIT cash timing?
4. **Sponsor due diligence** — Are sponsor covenant reports expected to show both accrual and
   cash CIT figures?

### Audit Trail Requirements

Phase 7 implementation must preserve the complete audit trail:

- [ ] `cit_accrual_by_period_keur` — per-period accrual CIT (from `run_holdco_tax_engine()`)
- [ ] `cit_cash_by_period_keur` — per-period cash CIT (after lag transform)
- [ ] `cit_payment_lag` — the lag applied (per country)
- [ ] Audit sheet update — both accrual and cash columns shown together
- [ ] No modification of existing `HoldCoTaxResult` fields (backward compatibility)

---

*End of ADR — Phase 6F HoldCo Tax Cash Timing Decision*
*Branch: phase6f-holdco-tax-cash-timing-decision*
*Implementation: Deferred to Phase 7*
