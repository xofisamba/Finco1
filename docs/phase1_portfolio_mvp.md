# Phase 1 MVP — Independent SPV Portfolio Aggregation

**Branch:** `portfolio`
**Repository:** `xofisamba/Finco1`
**Phase:** 1 (Minimum Viable Portfolio)

---

## Overview

Phase 1 MVP implements **independent SPV portfolio aggregation** — each SPV runs through the existing single-asset waterfall engine independently, results are preserved per-SPV, and aggregate summary metrics are computed.

Phase 1 does **NOT** implement pooled financing, shared debt sculpting, or HoldCo structures.

---

## What Is Implemented

### Per-SPV Run
- Each SPV runs independently through the existing calibrated `run_waterfall_v3_core()` engine
- Per-SPV outputs are fully preserved: waterfall periods, DSCR schedule, IRRs
- No shared financing parameters between SPVs

### Aggregation
- **Total metrics:** revenue, EBITDA, tax, senior debt service, distributions (summed)
- **DSCR:** min across SPVs (conservative for lenders), avg across SPVs (unweighted)
- **Per-SPV IRRs:** project IRR and equity IRR per SPV preserved in result
- **Simple-average IRRs:** unweighted average of per-SPV IRRs — NOT true portfolio XIRR

### Error Handling
- `strict=True` (default): SPV waterfall failure raises `SPVWaterfallError` with SPV code context
- `strict=False`: failed SPV included with zero outputs and explicit warnings
- Portfolio-level warnings are deduplicated and attached to `IndependentPortfolioResult.warnings`

### Feature Flags
- `IndependentPortfolioInputs` is opt-in — not enabled by default
- Pooled financing remains behind `PortfolioInputs` (pooled-financing path) — experimental

---

## What Phase 1 Does NOT Do

| Feature | Status | Notes |
|---------|--------|-------|
| HoldCo entity | ❌ Not implemented | Phase 2+ |
| SHL / intercompany flows | ❌ Not implemented | Phase 2+ |
| Sponsor IRR | ❌ Placeholder only | Phase 2+ |
| Monthly model frequency | ❌ Not implemented | Single-asset is semiannual |
| Cross-SP cash pooling | ❌ Not implemented | Phase 2+ |
| Retained earnings constraint | ❌ Not implemented | Phase 2+ |
| Portfolio-level debt sculpting | ❌ Not in default path | Per-SP debt only |
| True portfolio IRR (XIRR) | ❌ Not implemented | Deferred — simple averages only |
| Pooled financing waterfall | ⚠️ Experimental | `domain/portfolio/waterfall.py`, not default |
| DSRF integration | ❌ Placeholder only | Schema defined, not integrated into calculations |
| Excel export integration | ❌ Not implemented | Domain-level only unless wired separately |

---

## Excel Export

**Excel export integration is NOT implemented in Phase 1.**

Phase 1 provides domain-level aggregation (`IndependentPortfolioResult`). If Excel export integration is needed, it requires a separate implementation that wires `IndependentPortfolioResult` into `app/excel_export.py` or equivalent. This is deferred.

---

## DSRF Status

`DSRFConfig` is a schema placeholder with `enabled=False` by default.

```
DSRFConfig:
  enabled: bool = False          # Phase 1: always False
  months_reserve: int = 6
  funding_threshold_dscr: float = 1.25
  release_threshold_dscr: float = 1.35
```

**Phase 1:** DSRF is defined but has zero impact on DSRA, DSCR, distributions, IRR, or exports.
**Phase 2:** DSRF funding/release triggers may be integrated.

If `enabled=True` is passed, a `ValueError` is raised immediately — ensuring DSRF cannot silently affect calculations.

---

## IRR Semantics

**`simple_avg_project_irr` and `simple_avg_equity_irr` are NOT true portfolio IRR values.**

These are computed as unweighted averages of individual SPV IRRs for convenience only:
- They do NOT account for different SPV sizes, timing, or capital amounts
- They do NOT use date-aligned cash flow aggregation (XIRR)
- True portfolio IRR requires aggregating all SPV cash flows across a common timeline

True portfolio IRR is deferred to a later phase.

---

## Pooled Financing vs. Independent Aggregation

| Path | Module | Status |
|------|--------|--------|
| Independent SPV Aggregation | `domain/portfolio/independent/` | ✅ Phase 1 MVP (this module) |
| Pooled Financing Waterfall | `domain/portfolio/waterfall.py` | ⚠️ Experimental / Phase 2+ |
| Weighted KPI Aggregation | `domain/portfolio/aggregation.py` | Legacy (not used for Phase 1) |

---

## Tests

Phase 1 tests verify:
1. 2–3 SPVs run independently through waterfall engine (real engine integration)
2. Aggregation equals sum/min of child outputs
3. Feature flag / default behavior does not change single-asset mode
4. DSRF disabled has zero effect
5. Strict mode raises on failure; non-strict mode returns zero output with warning
6. Phase 1 does NOT use pooled debt sculpting

All existing single-asset tests remain unchanged.

---

## Limitation Summary

```
Phase 1 MVP Limitations:
- No HoldCo entity
- No SHL / intercompany flows
- No Sponsor IRR (placeholder only, not computed)
- No monthly model frequency
- No cross-SP cash pooling
- No retained earnings constraint
- No portfolio-level debt sculpting (per-SP debt only)
- No true portfolio IRR (simple averages only)
- DSRF: optional placeholder only, not integrated into calculations
- Excel export integration: not implemented

Pooled Financing (domain/portfolio/waterfall.py) is experimental / Phase 2+:
- Shared financing with cross-default enforcement
- Portfolio-level debt sculpting from pooled CFADS
- Not enabled by default in Phase 1
```

---

*Document created for Phase 1 MVP implementation. Updates to follow as features are added.*