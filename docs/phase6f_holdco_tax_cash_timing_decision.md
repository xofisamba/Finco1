# Phase 6F — HoldCo Tax Cash Timing: Architectural Decision Record

**Repository:** xofisamba/Finco1
**Branch:** `phase6f-holdco-tax-cash-timing-decision`
**Date:** 2026-05-11
**Type:** Architecture Decision Record (ADR)
**Scope:** Documentation only — no implementation changes

---

## Status

**ACCEPTED** — Decision recorded. Implementation deferred to Phase 7A.

---

## Context

Phase 6C established the HoldCo tax schema (`run_holdco_tax_engine()`) and the WHT calculation
framework. The schema is in place; the CIT calculation logic is defined but not yet wired to
active computation in the current `main` branch.

Regardless of where the engine is in its implementation, a cash timing question must be answered
before Phase 7 sponsor economics integration: **when is HoldCo CIT actually paid in cash?**

This document records the architectural decision for that question.

---

## 1. Current State

Phase 6C provides:

- `HoldCoTaxInputs` schema — defines the inputs the HoldCo engine will accept
- result schema — defines what the engine will produce
- `HoldCoTaxResult` dataclass — result container (schema in place; active CIT calculation not yet connected)
- `calculate_withholding_tax_keur()` — WHT amounts per entity per period (implemented)
- `calculate_holdco_taxable_income_before_limitations()` — tax base computation (schema defined; active computation deferred)
- Audit export sheets for HoldCo tax results (schema-driven, not yet active)

The schema anticipates per-period accrual values. The distinction between accrual and cash timing
is a **schema design question** that must be resolved now, so that Phase 7A implementation of the
actual computation follows a consistent contract.

**What is missing:**
- No active CIT calculation wired to the engine
- No cash payment timing model
- No distinction between accrual CIT and cash CIT in the result schema
- No cash flow integration with HoldCo cash waterfall

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
- No additional fields required in result schema

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

2. **Simplicity** — No mandatory schema changes required beyond a per-country `cit_payment_lag`
   configuration field. The lag is applied in the cash timing transform layer.

3. **Preserves accrual/cash distinction** — Accrual CIT is reported separately from
   Cash CIT in audit sheets. Both are tracked independently.

4. **Jurisdiction override capability** — Model A naturally supports per-country lag overrides.
   Model B (zero lag) and Model C (legal calendar) are both implementable as
   jurisdiction-specific lag values in Phase 7A.

5. **Sponsor IRR materiality** — The one-period lag is a bounded, small shift. Phase 7A sponsor
   waterfall integration can correct for it explicitly.

6. **No waterfall changes required now** — The HoldCo cash waterfall will receive cash CIT
   as an input in Phase 7A. The tax engine itself is not modified.

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

### Implementation Caveat

**Implementation details (schema field names, transform function signatures, result schema
extensions) are subject to Phase 7A design.** This ADR records the **architectural decision**
— the chosen model and its rationale — not the approved implementation. Phase 7A will
determine the exact schema contract based on the active HoldCo engine implementation at
that time.

---

## 5. Architectural Constraints

The following constraints must be respected in any Phase 7A implementation:

### 5.1 No Tax Engine Modification

The HoldCo tax engine computes **accrual** CIT. Cash timing is a **transform layer** applied
downstream, not a change to the engine itself.

```
HoldCo Tax Engine (accrual)  →  Cash Timing Transform (lag applied)  →  Cash Flow Input
```

### 5.2 No Waterfall Modifications in Phase 6F

Phase 6F is documentation-only. No waterfall code is modified. Phase 7A integration will
introduce cash CIT as a new input to the HoldCo cash waterfall.

### 5.3 No Sponsor IRR Implementation in Phase 6F

Sponsor waterfall, Sponsor IRR, and MOIC are Phase 7 topics. Phase 6F documents the
timing question but does not implement the integration.

### 5.4 Accrual and Cash Remain Separate

Both accrual CIT and cash CIT must be tracked separately in result schema and audit sheets.
They are not merged into a single figure.

### 5.5 Jurisdiction Override Capability Preserved

Any cash timing implementation must support per-country lag configuration. Hardcoding a
single lag for all jurisdictions is not acceptable.

### 5.6 Determinism Preserved

Cash timing must not introduce calendar-date dependencies. The model must produce identical
outputs on every run. Lag is expressed in **model periods**, not calendar days.

---

## 6. Future Integration Notes

*This section describes the integration concept. Exact schema, field names, and function
signatures are subject to Phase 7A design.*

### 6.1 Config Extension Concept

A per-country `cit_payment_lag` configuration field would allow each jurisdiction template
to specify its own lag, with a default of `1` semiannual period.

### 6.2 Result Schema Concept

The result schema would carry both accrual and cash CIT values:

- **Accrual CIT** — the tax liability computed for each period (used for audit reporting)
- **Cash CIT** — the accrual CIT shifted by the configured lag (used for cash flow integration)

Both are maintained independently in the result schema.

### 6.3 Cash Timing Transform Concept

A deterministic transform applies the configured lag to accrual CIT to produce cash CIT.
For `lag=0`, accrual equals cash. For `lag=1`, cash in period *t* equals accrual from
period *t−1*. The first *lag* periods have zero cash CIT (no prior accrual to draw from).

### 6.4 HoldCo Cash Waterfall Concept

In Phase 7A, the HoldCo cash waterfall receives cash CIT (not accrual CIT) as a cash outflow.
The accrual figure continues to be available for audit reporting.

### 6.5 Audit Sheet Concept

Audit sheets would show both accrual and cash CIT figures per entity per period, so reviewers
can see the timing difference. Both are preserved for governance traceability.

---

## 7. Explicit Non-Scope

The following are explicitly out of scope for this decision and Phase 7A integration:

| Item | Reason |
|------|--------|
| Tax engine modifications | Accrual engine unchanged; cash timing is a transform |
| Deferred tax asset/liability tracking | Requires monthly model; not in Phase 7A scope |
| Monthly model | Semiannual periods only; cash timing in model periods not calendar months |
| Sponsor waterfall | Phase 7 sponsor economics topic |
| Sponsor IRR / MOIC | Phase 7 sponsor economics topic |
| Promote waterfall | Phase 7 sponsor economics topic |
| Tax payment scheduling (legal calendar) | Would introduce calendar-date dependencies; not deterministic |
| Treaty WHT engine | Cross-border treaty not modeled |
| Actual jurisdiction payment calendars | Requires legal/tax counsel; not available in model inputs |
| WHT remittance timing | WHT is audit-visible only; no cash flow integration in Phase 6 or 7 |
| HoldCo runner behavior changes | Engine schema unchanged; output extended in Phase 7A |

---

## 8. Risks

### 8.1 HIGH — Cash Timing Not Integrated Before Sponsor Economics Begins

**Risk:** Phase 7 begins sponsor waterfall integration without cash timing, using accrual CIT
in the waterfall. Sponsor IRR is understated (CIT appears to be paid before it actually is).

**Mitigation:** Phase 7A must introduce cash CIT as a first-class input to the HoldCo cash
waterfall. Accrual CIT must not be used as a cash flow input.

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
income. Taxable income computation uses dividend income + SHL interest income − HoldCo OpEx,
which does not include CIT. No circular reference is possible given the current schema design.

**Blocker:** No — structurally not possible in current architecture.

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
when computing DSCR. The audit trail (accrual vs cash figures) is available to reviewers.

**Blocker:** No — sponsor waterfall design is Phase 7.

---

## 9. Recommendation for Phase 7A

### Phase 7A HoldCo Tax Cash Timing

**Architectural direction:** Implement the deterministic one-period lag as described in this ADR.
Schema extensions, exact field names, and function signatures to be determined in Phase 7A design.

### Decision Record Summary

| Decision | Choice |
|----------|--------|
| Cash timing model | Model A — Deterministic One-Period Lag (default) |
| Default lag | `1` semiannual model period |
| Override mechanism | Per-country lag configuration in HoldCo tax config |
| Tax engine changes | None — transform applied downstream |
| Accrual/cash distinction | Both tracked separately in result schema |
| Sponsor IRR integration | Phase 7 sponsor waterfall topic; cash timing is prerequisite |
| Implementation phase | Phase 7A (this decision is architecture-only; implementation details subject to Phase 7A design) |

### Pre-Phase-7A Checklist

Before Phase 7A begins, the following should be confirmed by the Phase 7A design:

1. **Result schema contract** — Does the active `HoldCoTaxResult` schema carry per-period accrual
   values? What field name is used? Can a cash CIT field be added without breaking existing consumers?
2. **Config schema** — Is there a place for a per-country `cit_payment_lag` field in the
   HoldCo tax configuration schema?
3. **HoldCo cash waterfall contract** — Does the waterfall accept per-period cash CIT as an input?
   Is accrual CIT still available for audit?
4. **DSCR test interaction** — Does the HoldCo DSCR test need to account for CIT cash timing?
5. **Audit sheet format** — Are both accrual and cash CIT figures expected in the audit sheets?

---

*End of ADR — Phase 6F HoldCo Tax Cash Timing Decision*
*Branch: phase6f-holdco-tax-cash-timing-decision*
*Implementation: Deferred to Phase 7A (architecture decision only; implementation details TBD)*
