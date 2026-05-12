# Phase 7C Waterfall Kickoff Decisions

**Date:** 2026-05-12
**Phase:** 7C (preferred return / promote waterfall)
**Purpose:** Lock core waterfall policy choices before schema and runner implementation begin.
**Status:** Decisions only — no implementation yet.

---

## 1. Context and Purpose

Phase 7A/7B established the sponsor economics foundation: immutable cashflow results, XIRR-based IRR, and MOIC. Phase 7C adds the preferred return (pref) and promote (carried interest) waterfall on top of those results.

The sponsor economics architecture has two levels:

```
HoldCo (equity layer)
    └── SPV (project level, debt + equity)
```

Sponsor cashflows are computed at the SPV-HoldCo interface and flow upward to the sponsor. Phase 7C waterfall applies pref and promote at the **sponsor/HoldCo level**, consuming `SponsorCashflowResult` outputs from Phase 7A/7B. The waterfall does **not** mutate `SponsorCashflowResult` — it produces new `SponsorWaterfallResult` immutable outputs.

This document locks five decisions that must be consistent across all Phase 7C schema and runner work.

---

## 2. Waterfall Architecture Assumptions

These assumptions are inherited from Phase 7A/7B and constrain all waterfall work:

1. **Single-investor sponsor** for Phase 7C. Multi-investor waterfall allocation is deferred.
2. **Deterministic, immutable outputs.** No mutation of sponsor cashflow records.
3. **Audit-safe by design.** All waterfall result schemas require `audit_note` fields.
4. **Cash-basis distribution model.** Distributions are actual cash flows; accrual adjustments are tracked separately.
5. **Semiannual periods** (6-month intervals) from the model period engine.
6. **No persistence layer** in Phase 7C. Results exist in memory only.
7. **No Excel redesign** in Phase 7C. Waterfall outputs follow existing export conventions.

---

## 3. Decision 1: Compounding Convention

### Chosen Default: **Annual compounding of preferred return**

The preferred return is compounded **once per year** (at each anniversary of the financial close date), not continuously and not semiannually.

### Rationale

Annual compounding is the dominant market convention for project finance waterfalls in the BIH/HR market. It is simple to audit, maps cleanly to Excel's standard XIRR-based pref math, and avoids the complexity of continuous or monthly compounding that is rarely applied in this asset class.

Semiannual compounding would be mathematically equivalent to annual if the pref rate were adjusted, but annual is simpler to explain and verify in an audit context.

### Alternatives Considered

| Option | Considered | Rejected? |
|---|---|---|
| Continuous compounding | Standard in some derivatives contexts | Overkill for project finance; harder to verify in Excel |
| Semiannual compounding | Matches model period frequency | Would require rate adjustment to match annual economics; added complexity |
| Monthly compounding | Used in some credit structures | Not standard for equity pref in solar/wind; audit complexity |
| Non-compounding (simple pref) | Common in early-stage funds | Penalizes GP in back-loaded exit scenarios; GP would dislike it |

### Future Extensibility

The compounding convention is implemented as a configurable parameter on the waterfall inputs schema. Switching to semiannual in a future phase requires only changing the compounding frequency flag and updating the accrual computation — the waterfall result schemas and audit outputs do not need structural changes.

### Audit / Export Implications

Annual compounding means the preferred return balance is updated once per year (every 2 semiannual periods). The audit sheet must show the annual pref balance alongside the period-by-period distribution log. Year-fragment periods (e.g., if FC is mid-year) should use actual calendar days for the first partial year, then annual thereafter.

### Fit to FincoGPT Scope

Annual compounding maps directly to Excel's built-in XIRR verification: the sponsor's IRR is computed from actual cash flows, and the pref return is verified by checking that the sponsor's IRR exceeds the pref hurdle before promote triggers. Annual compounding is standard for this model tier and avoids over-engineering for a scope that does not yet require quarterly reporting.

---

## 4. Decision 2: Catch-up Algorithm

### Chosen Default: **Full GP catch-up (100% to GP until GP has received pref + 100% of remaining equity)**

The waterfall allocates **100% of distributions to the GP** until the GP has received an amount equal to the sponsor's pref accrual plus 100% of the remaining sponsor equity commitment. This is the "full catch-up" model.

After the catch-up is satisfied, distributions split between GP and sponsor according to the promote split (e.g., 80/20 or 50/50 above the hurdle).

### Rationale

Full GP catch-up is the standard for project finance SPVs where the GP has typically funded 10-20% of equity but carries 100% of the promote. The GP receives no distributions until the sponsor has received their preferred return **and** the sponsor's remaining equity has been returned — this means the sponsor must effectively get their money back plus pref before GP starts earning carry.

A partial catch-up (e.g., 50% to GP until GP has 20% of distributions) is a variation used in some fund structures but is less common in single-asset project finance where the SPV is a single-purpose vehicle.

### Alternatives Considered

| Option | Considered | Rejected? |
|---|---|---|
| No catch-up (distributions split from first dollar) | Used in some early-stage funds | GP not incentivized to maximize sponsor return |
| Partial catch-up (e.g., 50/50 until GP has 20%) | Used in some LPs | Not standard for single-asset SPV; adds unnecessary complexity |
| GP earns promote from period 1 | Sometimes used in co-invest scenarios | Sponsor protection reduces; GP would receive promote before pref is satisfied |

### Future Extensibility

The catch-up algorithm is implemented as a policy object. A future phase can introduce a "partial catch-up" mode by adding a `catch_up_fraction: float` field (e.g., 0.5 for 50% catch-up). The result schemas do not change — only the allocation policy does.

### Audit / Export Implications

The catch-up creates a **distribution log** with two phases: (1) sponsor-only phase, (2) GP+sponsor phase. The audit sheet must show per-period allocation amounts to each party. The catch-up balance (cumulative amount needed to satisfy catch-up) is a critical audit field.

### Fit to FincoGPT Scope

Full GP catch-up aligns with the TUHO/Oborovo model structure where the sponsor is the primary equity investor and the GP (if any) holds a carried interest. This is the simplest formulation that satisfies both sponsor protection and GP incentive alignment.

---

## 5. Decision 3: Promote Vesting Timing

### Chosen Default: **Per-period promote vesting (solve per period, based on cumulative IRR to date)**

Promote vesting is computed **period-by-period**: each semiannual period, the algorithm checks whether the sponsor's cumulative IRR to date exceeds the pref hurdle. If yes, promote allocates to GP for that period's distributions according to the promote split.

### Rationale

Per-period vesting is the simplest and most auditable approach. It avoids the complexity of a "vesting cliff" (single trigger event) or a forward-looking IRR projection, and it aligns with the model's semiannual output cadence.

A cliff-based trigger (GP earns promote only after sponsor exits) is not suitable for a project finance model where distributions occur over 20-30 years — the sponsor receives distributions semiannually and the IRR is computed over the full project life. Per-period vesting handles this naturally.

### Alternatives Considered

| Option | Considered | Rejected? |
|---|---|---|
| Cliff trigger (all or nothing at exit) | Simple concept | Doesn't fit semiannual distribution model; GP earns nothing for decades |
| Forward IRR projection (guess future distributions) | Sometimes used in waterfall models | Non-deterministic; violates audit-safe principle |
| Annual vesting (check once per year) | Matches annual compounding | Would delay promote credit by 6 months vs period accuracy; added conditional logic |
| Cumulative IRR with lookback | Used in some fund models | Per-period is simpler and equivalent for uniformly increasing distributions |

### Future Extensibility

Per-period vesting is parameterized: the promote trigger condition is a function `(sponsor_cumulative_irr > pref_hurdle)`. A future phase could introduce a "hurdle buffer" (promote triggers only when IRR exceeds hurdle by a spread, e.g., +1%) by adding a field — no schema change required, only policy logic.

### Audit / Export Implications

Each period's distribution must show: (a) sponsor amount before promote, (b) GP promote amount, (c) cumulative sponsor IRR at that point, (d) pref hurdle rate. The promote trigger logic must be explicitly documented in the audit sheet as a boolean `promote_triggered: bool` per period.

### Fit to FincoGPT Scope

Per-period vesting matches the model's semiannual output granularity and produces deterministic, auditable results. The IRR check is computed from `SponsorCashflowResult.period_results` cumulative net cashflows — no new data required.

---

## 6. Decision 4: Multi-Asset Aggregation Philosophy

### Chosen Default: **Deal-by-deal (project-by-project) hurdle treatment — no cross-project aggregation**

Each SPV/project is treated independently. The preferred return hurdle is computed **per project**, not aggregated across a portfolio. Distributions from Project A do not contribute to the pref hurdle of Project B.

### Rationale

FincoGPT models solar and wind assets as independent SPV structures. The sponsor's overall portfolio IRR is the weighted average of individual project IRRs — there is no "waterfall pool" that aggregates multiple projects into a single return calculation. Deal-by-deal treatment is the standard for project finance unless there is explicit equity sharing across assets (which is not the case for TUHO/Oborovo).

Cross-project aggregation would be relevant for a multi-asset fund where LP capital is deployed across projects and distributions are pooled. This is not in scope for Phase 7C.

### Alternatives Considered

| Option | Considered | Rejected? |
|---|---|---|
| Portfolio-level hurdle (pool all projects) | Used in multi-asset funds | Would require HoldCo-level distribution aggregation not yet in model |
| First-dollar priority (projects compete for distributions) | Sometimes used in credit structures | Not applicable; SPV distributions are asset-specific |
| Blended preferred return (average hurdle rate) | Used in some fund models | Doesn't make sense for independently modeled projects |

### Future Extensibility

If a future phase adds a HoldCo-level waterfall that aggregates multiple SPV distributions, the deal-by-deal decision is preserved because each SPV's `SponsorCashflowResult` is computed independently, and the aggregation happens at a higher layer. No Phase 7C schema needs to change to support portfolio-level aggregation later.

### Audit / Export Implications

Each project (SPV) produces its own waterfall result. The audit sheet is per-project. Portfolio-level totals are computed by summing project-level results — no special aggregation schema needed in Phase 7C.

### Fit to FincoGPT Scope

Deal-by-deal matches the actual TUHO/Oborovo model structure where each project is an independent SPV with its own debt, equity, and distributions. Sponsor IRR is computed per project in Phase 7B. Waterfall in Phase 7C follows naturally from that.

---

## 7. Decision 5: Excel Audit Sheet Philosophy

### Chosen Default: **Single audit sheet with tier column (no multi-sheet waterfall disclosure)**

The Excel export for Phase 7C waterfall uses a **single sheet** with a `tier` column distinguishing: (1) return of equity, (2) preferred return, (3) promote (GP/sponsor split).

### Rationale

A single audit sheet with a tier column is the most auditable format: every row represents a distribution event, the tier classifies it, and the amounts are traceable to the waterfall allocation algorithm. This matches the existing export pattern in the model (e.g., the tax export uses a single sheet with category columns).

Multi-sheet waterfall disclosure (separate sheets for pref, promote, final distribution) creates synchronization risks and is harder for a user to trace end-to-end. The tier column approach is standard for project finance audit disclosure.

### Alternatives Considered

| Option | Considered | Rejected? |
|---|---|---|
| Multiple sheets (one per waterfall tier) | Used in some investment management systems | Adds synchronization risk; harder to verify total distribution |
| Single sheet, no tier (flat list) | Simpler but less structured | Would require parsing notes/amounts to understand allocation |
| JSON export alongside Excel | Modern approach for API consumers | Not needed in Phase 7C; JSON export can be added later via adapter |

### Future Extensibility

A future phase could add a `waterfall_tier_detail` sheet for a detailed breakdown of promote allocation by period. The tier column is extensible: new tiers (e.g., "clawback", "management fee") can be added as string values without schema changes.

The tier convention is a string enum, not a hard-coded list — this allows future tiers without breaking the export schema.

### Audit / Export Implications

The audit sheet must show per-period allocation to sponsor and GP. The tier column provides the classification. The sheet must be traceable to: (a) the underlying `SponsorCashflowResult` totals, (b) the IRR threshold that triggered promote, (c) the catch-up status. The `audit_note` on result schemas maps directly to the audit sheet header.

### Fit to FincoGPT Scope

Single sheet with tier matches the existing FincoGPT export pattern and is appropriate for the model's current export maturity level. It is simple enough to implement in Phase 7C without requiring a full export framework redesign.

---

## 8. Deferred Future Considerations

The following are explicitly deferred beyond Phase 7C:

| Item | Reason for Deferral |
|---|---|
| Multi-investor allocation (LP1/LP2/GP split) | Single-sponsor model in scope; multi-investor requires investor registry and capital account splitting |
| Clawback provisions | Not standard in project finance SPVs; would require GP payback obligation tracking |
| GP management fee waterfall | Management fees are typically accounted for separately; not part of the distribution waterfall |
| Forward IRR projection for vesting | Non-deterministic; violates audit-safe principle of Phase 7A/7B |
| Portfolio-level cross-SPX aggregation | Requires HoldCo-level distribution aggregation not yet in model |
| WHT cross-border treatment in waterfall | WHT is applied at HoldCo→sponsor level in Phase 7A; not adjusted in waterfall |
| Promote reset on refinancing | Refinancing events are model-level concerns; waterfall is cash-distribution based |
| Quarterly compounding option | Annual is standard; quarterly can be added as a compounding frequency parameter |
| Incentive fee waterfall | Separate from carried interest; different regulatory treatment |

---

## 9. Explicit Non-Scope for Phase 7C

The following are explicitly **not** in Phase 7C:

- No multi-investor allocation engine
- No GP management fee deduction
- No clawback provision
- No refinancing event handling
- No portfolio-level aggregation across SPVs
- No persistence layer (database or file-based)
- No UI or editing workflow for waterfall parameters
- No Excel redesign of existing model sheets
- No JSON or API export for waterfall results
- No PySAM or revenue model integration in waterfall
- No tax equity or subordinated debt waterfall

---

## 10. Final Locked Defaults for Phase 7C

| Decision | Locked Default |
|---|---|
| Compounding convention | **Annual** — preferred return compounded once per year |
| Catch-up algorithm | **Full GP catch-up** — 100% to GP until sponsor pref + full equity returned |
| Promote vesting timing | **Per-period** — IRR checked each semiannual period; promote allocates period-by-period |
| Multi-asset aggregation | **Deal-by-deal** — each SPV/project is independent; no cross-project hurdle aggregation |
| Excel audit sheet | **Single sheet, tier column** — return-of-equity / pref / promote tiers in one sheet |

These defaults are fixed. Any Phase 7C schema or runner implementation must be consistent with all five. Changes to these defaults require a new decision document and sign-off before implementation proceeds.

---

*Document version: 1.0 — Phase 7C kickoff. Supersedes any prior waterfall convention references in the codebase. Next step: Phase 7C schema definitions and runner implementation.*