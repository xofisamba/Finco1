# Phase 1 MVP — Independent SPV Portfolio Aggregation

**Branch:** `portfolio`
**Repository:** `xofisamba/Finco1`
**Phase:** 1 (Minimum Viable Portfolio)

---

## Overview

Phase 1 MVP implements **independent SPV portfolio aggregation** — each SPV runs through the existing single-asset waterfall engine independently, results are preserved per-SPV, and aggregate summary metrics are computed.

Phase 1 does **NOT** implement pooled financing, shared debt sculpting, or HoldCo structures.

---

## Architecture

```
IndependentPortfolioInputs
    └── run_independent_portfolio()
            └── For each SPV:
                    run_waterfall_v3_core()  [existing single-asset engine]
            └── SPVOutput (per-SPV preserved)
            └── IndependentPortfolioResult (aggregated)
```

**Key modules:**
- `domain/portfolio/independent/inputs.py` — IndependentPortfolioInputs, DSRFConfig
- `domain/portfolio/independent/result.py` — SPVOutput, IndependentPortfolioResult
- `domain/portfolio/independent/runner.py` — run_independent_portfolio()
- `domain/portfolio/independent/__init__.py` — public API

**Existing modules (NOT expanded in Phase 1):**
- `domain/portfolio/inputs.py` — PooledPortfolioInputs (pooled financing, experimental)
- `domain/portfolio/waterfall.py` — Pooled financing waterfall (experimental / Phase 2+)
- `domain/portfolio/aggregation.py` — Weighted KPI aggregation (legacy)

---

## What Phase 1 Does

### Per-SPV Run
- Each SPV runs independently through the existing calibrated `run_waterfall_v3_core()` engine
- Per-SPV outputs are fully preserved: waterfall periods, DSCR schedule, IRRs
- No shared financing parameters between SPVs

### Aggregation
- **Total metrics:** revenue, EBITDA, tax, senior debt service, distributions (summed)
- **DSCR:** min across SPVs (conservative for lenders), avg across SPVs (unweighted)
- **Per-SPV IRRs:** project IRR and equity IRR per SPV preserved in result

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
| Portfolio-level debt sculpting | ❌ Not in default path | Per-SPV debt only |
| Pooled financing waterfall | ⚠️ Experimental | `domain/portfolio/waterfall.py`, not default |
| DSRF integration | ❌ Placeholder only | Schema defined, not integrated into calculations |

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

## Pooled Financing vs. Independent Aggregation

| Path | Module | Status |
|------|--------|--------|
| Independent SPV Aggregation | `domain/portfolio/independent/` | ✅ Phase 1 MVP (this module) |
| Pooled Financing Waterfall | `domain/portfolio/waterfall.py` | ⚠️ Experimental / Phase 2+ |
| Weighted KPI Aggregation | `domain/portfolio/aggregation.py` | Legacy (not used for Phase 1) |

**Distinction:** The independent path treats each SPV as a standalone project with its own debt. The pooled path treats all SPVs as a single financed pool with shared debt sculpted from combined CFADS. Phase 1 uses the independent path only.

---

## Excel Export (Phase 1)

Existing `excel_export.py` already supports `portfolio_result` via `build_portfolio_table()` and `Portfolio CF` sheet.

Phase 1 adds per-SPV breakdown sheets when portfolio result is provided — without refactoring the whole export engine.

---

## Tests

Phase 1 tests verify:
1. 2–3 SPVs run independently through waterfall engine
2. Aggregation equals sum/min of child outputs
3. Feature flag / default behavior does not change single-asset mode
4. DSRF disabled has zero effect
5. Independent path does NOT use pooled debt sculpting

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
- DSRF: optional placeholder only, not integrated into calculations

Pooled Financing (domain/portfolio/waterfall.py) is experimental / Phase 2+:
- Shared financing with cross-default enforcement
- Portfolio-level debt sculpting from pooled CFADS
- Not enabled by default in Phase 1
```

---

*Document created for Phase 1 MVP implementation. Updates to follow as features are added.*