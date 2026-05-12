# Phase 7A/7B Architecture Review — Sponsor Economics Foundation

**Date:** 2026-05-12
**Phase:** 7A (sponsor cashflow) → 7B (sponsor IRR/MOIC)
**Next:** Phase 7C (preferred return / promote waterfall)
**Status:** PRs #46/#47 merged to main

---

## 1. Architecture Summary

### Modules produced

| File | Lines | Role |
|---|---|---|
| `domain/sponsor/equity_injection.py` | 223 | Immutable injection event schema |
| `domain/sponsor/sponsor_capital_account.py` | 258 | Capital account ledger (contributions + distributions) |
| `domain/sponsor/sponsor_cashflow_result.py` | 259 | Frozen per-period + aggregate sponsor cashflow result |
| `domain/sponsor/sponsor_cashflow_runner.py` | 375 | Pure-function sponsor cashflow runner |
| `domain/sponsor/sponsor_irr_result.py` | 193 | Frozen IRR + MOIC result schemas |
| `domain/sponsor/sponsor_irr_runner.py` | 253 | Pure-function IRR/MOIC runners |
| `domain/sponsor/xirr.py` | 170 | Deterministic XIRR wrapper with NR + bisection fallback |
| `tests/test_sponsor_cashflow_runner.py` | ~1180 | Cashflow runner tests |
| `tests/test_sponsor_irr_runner.py` | ~558 | IRR/MOIC runner tests |

**Total: ~3476 lines across 9 files.**

---

## 2. Phase 6F Readiness Bridge

### What was inherited from 6F

The Phase 6F sponsor cashflow infrastructure (equity injection schema, capital account skeleton) was already in place. Phase 7A built the `run_sponsor_cashflows()` pure function on top of that foundation.

### Bridge quality: GOOD

- `EquityInjection` schema is clean and frozen
- `SponsorCapitalAccount` ledger is complete and reconciliation-checked
- No mutation of upstream HoldCo results
- All inputs validated before computation

### Gap identified

**`holdco_distribution_by_period` is a raw `tuple[float, ...]`** — no schema type alias or validation wrapper. When Phase 7C waterfall calls `run_sponsor_cashflows()`, the caller must supply this tuple correctly. There is no `HoldCoDistributionSchedule` or similar input schema that enforces period alignment, WHT basis, and dividend/opex decomposition.

**Recommendation:** Before Phase 7C, add a thin `HoldCoDistributionSchedule` input type (or at minimum document the required tuple structure) to prevent callers from supplying misaligned distributions.

---

## 3. Immutability Policy Compliance

### Status: COMPLIANT ✅

All result dataclasses use `@dataclass(frozen=True)`:

```
SponsorCashflowPeriodResult   — frozen ✅
SponsorCashflowResult          — frozen ✅
SponsorCapitalAccount          — frozen ✅
CapitalAccountEntry            — frozen ✅
SponsorIrrResult               — frozen ✅
SponsorMoicResult              — frozen ✅
SponsorXirrResult              — frozen ✅ (in xirr.py)
```

All runner functions are pure (no mutation, no I/O, deterministic).

### Minor concern: `object.__setattr__` used in post-init

Both `sponsor_cashflow_runner.py` and `sponsor_capital_account.py` use `object.__setattr__` in `__post_init__` to set normalized tuples (for schema enforcement on frozen dataclasses). This is correct Python technique but worth noting — future auditors should understand this is intentional normalization, not mutation.

---

## 4. Cash vs Accrual Separation

### Status: CLEAR ✅

The architecture cleanly separates cash flows (actual transfers) from accrual accounting:

**Cash side (in `SponsorCashflowPeriodResult`):**
- `equity_injected_keur` — actual cash out
- `distribution_received_keur` — actual cash in from HoldCo
- `wht_on_distribution_keur` — actual withholding tax
- `net_cashflow_keur` — cash net position
- `capital_account_balance_keur` — cumulative cash capital account

**Accrual reference (stored but not deducted at sponsor level):**
- `holdco_dividend_by_period` — used only for WHT basis computation
- `holdco_opex_by_period` — stored for audit reference, not deducted

**WHT computation:** `wht = distribution * wht_rate` (cash-based, on gross distribution)

This is correct. The sponsor receives cash net of WHT; the accrual decomposition (dividend vs opex) is a HoldCo-level concern that doesn't affect sponsor cashflows.

### Gap: No accrued dividend tracking at sponsor level

`SponsorCashflowPeriodResult` stores `distribution_received_keur` (cash) but does not separately track the dividend component (for potential use in return-of-capital vs income classification). For the waterfall phase, this may matter for tax treatment.

**Recommendation:** Add an optional `dividend_component_keur` field to `SponsorCashflowPeriodResult` before Phase 7C. This would preserve the dividend/opex decomposition from `holdco_dividend_by_period` through to the sponsor result, enabling correct capital return classification in the waterfall.

---

## 5. Sponsor Cashflow → IRR Data Flow

### Status: CORRECT ✅

```
SponsorCashflowResult
  ├── period_results[i].net_cashflow_keur     → XIRR cash flows
  ├── period_results[i].equity_injected_keur  → MOIC numerator
  └── total_distributions_received_keur        → MOIC denominator
```

IR/MOIC are computed from `SponsorCashflowResult` only — no mutation of the source. The data flow is unidirectional and audit-safe.

### Critical correctness check: `capital_account_balance_keur` constraint

`SponsorCashflowPeriodResult.capital_account_balance_keur` is validated as **non-negative** (`>= 0`). This is enforced in `__post_init__` via `_finite_non_negative`.

**This creates a structural mismatch with the sponsor capital account ledger**, where `running_balance_keur` can legitimately be negative (distributions can exceed contributions in the return phase).

**This is a BUG:** When a sponsor receives large distributions that exceed cumulative contributions, the capital account balance goes negative — but `SponsorCashflowPeriodResult` rejects negative balances.

**Impact:** For any project where cumulative distributions exceed cumulative equity injections, `run_sponsor_cashflows()` will **raise a `ValueError`** at the `SponsorCashflowPeriodResult` construction step, because `capital_account_balance_keur` would be negative.

**Current workaround in tests:** All test fixtures use `abs(cap)` to bypass the constraint, which hides the real issue.

**Recommendation:** Before Phase 7C, change `capital_account_balance_keur` from `non-negative` to `finite` (allow negative values). The non-negative constraint should be moved to `SponsorCapitalAccount` (where `running_balance_keur` already has it as a design intent) — but even there, negative balances during return phase should be reviewed. The real question is: does the model need to represent a sponsor whose distributions have exceeded their equity injection? If yes, the constraint must be relaxed.

---

## 6. Capital Account Skeleton

### Status: COMPLETE ✅

`SponsorCapitalAccount` and `CapitalAccountEntry` are implemented with:

- Entry types: contribution, distribution, adjustment
- Source canonical mapping from `EquityInjection.purpose`
- Reconciliation checks between declared totals and entry sums
- Sorted metadata normalization

### Gap: No method to compute balances from entries

`SponsorCapitalAccount` provides `contributions_by_period` and `distributions_by_period` as read-only properties, but there's no method to compute the running balance from entries (the runner computes it imperatively and stores the final value). For waterfall allocation, we may need to reconstruct balances from entries.

**Recommendation:** Add `balance_at_period(period_index: int) -> float` method to `SponsorCapitalAccount` before Phase 7C. This would allow the waterfall engine to query the capital account at any period without maintaining separate mutable state.

---

## 7. XIRR Correctness Risks

### Risk 1: 183-day semiannual approximation ⚠️ MEDIUM

`run_sponsor_irr()` uses `period_index * 183` days for date derivation. This is a **constant approximation** (6 months ≈ 183 days), not a calendar-aware semiannual schedule.

Excel XIRR uses actual calendar days / 365. The difference between 183-day and real calendar semiannual periods accumulates over a 20-30 year project life:

- Real semiannual: months 1,4,7,10 → average 184.5 days (varies by month lengths)
- Approximation: 183 days exactly → systematic ~0.8% shorter year fraction per period

Over 60 semiannual periods (30 years), this could shift IRR by ~0.1-0.3 percentage points vs Excel.

**Current behavior:** When `fc_date` is provided, dates are computed as `fc_date + timedelta(days=period_index * 183)`. This is deterministic but not calendar-exact.

**Recommendation:** Before Phase 7C, confirm the financial close date convention with the model. If Excel uses actual calendar semiannual periods, replace 183 with a proper semiannual date schedule (e.g., using `dateutil.relativedelta` or a period-engine date lookup). If the model uses 183-day constant, document this clearly.

### Risk 2: Dummy base date when fc_date is None ⚠️ LOW

When `fc_date` is not supplied, `base_date = date(2000, 1, 1)` is used as a dummy. The year fractions are then `(date - dummy_base).days / 365`, which gives:
- Period 0 → year fraction 0
- Period 1 → 183/365 = 0.5014
- Period N → N*183/365

This is correct semiannual approximation, but the choice of `date(2000, 1, 1)` is arbitrary. The actual year fractions are unaffected by the base (only differences matter), so this is safe but should be documented.

### Risk 3: Bisection iteration count is always 0 ⚠️ LOW

`xirr_with_convergence()` returns `iterations=0` for bisection fallback. This means `SponsorIrrResult.xirr_iterations` is always 0 when bisection is used. For audit/compliance, it may matter to know how hard a non-convergence case was to solve.

**Recommendation:** Track bisection iterations in `_core_bisection` or count bisection loop iterations in `xirr_with_convergence` before returning.

---

## 8. Golden Validation Readiness

### Status: NOT YET INTEGRATED ⚠️

There is no golden validation test for sponsor IRR or MOIC against known Excel benchmarks.

**Current test coverage:**
- Known-answer tests with fabricated cash flows (2-period, 10-period)
- Determinism tests (repeated run → identical)
- Edge case tests (all contributions, all distributions, empty)
- Schema validation tests

**Missing:**
- No comparison against actual Excel XIRR output
- No calibration against TUHO/Oborovo financial model sponsor IRR
- No `golden/` fixture for sponsor-level results
- `SponsorIrrResult` and `SponsorMoicResult` are not exported through the Excel export pipeline

### Recommendation: Before Phase 7C

1. Add a golden fixture for `SponsorIrrResult` (at minimum: TUHO and Oborovo known-answer cases)
2. Add `test_sponsor_irr_excel_alignment.py` against the actual TUHO/Oborovo Excel files
3. Verify `gross_sponsor_irr` matches Excel XIRR on the project's actual sponsor cashflow schedule

---

## 9. Export Split Readiness

### Status: NOT YET CONNECTED ⚠️

The sponsor economics modules are not yet wired into the export split architecture (Phase 6F). Specifically:

- `SponsorCashflowResult` is not exported through any `ExcelExport` pipeline
- `SponsorIrrResult` / `SponsorMoicResult` have no export path
- `SponsorCapitalAccount` is not persisted

The sponsor IRR/MOIC results exist only in memory after `run_sponsor_irr()` / `run_sponsor_moic()` are called. No downstream consumer (API, Excel export, report) has a defined interface to receive them.

### Phase 6F export split context

Phase 6F established split planning between Excel export and model domain. The sponsor economics modules sit in `domain/sponsor/` — they are domain logic, not export logic. The export split suggests this is correct: domain owns computation, export adapters own presentation.

**Recommendation:** Define an export adapter interface for `SponsorIrrResult` before Phase 7C. At minimum: a `SponsorExportSchema` with investor_id, gross_irr, moic, metadata. This ensures the IRR result can be surfaced through the existing export pipeline without contaminating domain logic with export format concerns.

---

## 10. Architecture Risks Summary

| Risk | Severity | Description |
|---|---|---|
| `capital_account_balance_keur` non-negative constraint | 🔴 HIGH | Rejects negative balances; will crash on projects where distributions > equity injected; must be fixed before 7C |
| No Excel XIRR calibration for sponsor IRR | 🟡 MEDIUM | 183-day approximation may differ from Excel; no golden fixture comparing to real model output |
| No `HoldCoDistributionSchedule` input type | 🟡 MEDIUM | Raw tuple interface for distributions; no schema enforcement on period alignment |
| Bisection iteration count = 0 | 🟢 LOW | Audit gap for convergence hardness tracking |
| No dividend component tracking at sponsor level | 🟢 LOW | Future waterfall may need dividend vs return-of-capital classification |
| No capital account balance-at-period method | 🟢 LOW | Waterfall engine can't query historical balance without re-computation |

---

## 11. Recommendations Before Phase 7C (Priority Order)

1. **[HIGH] Fix `capital_account_balance_keur` constraint** — change from non-negative to finite (allow negative), matching actual sponsor return dynamics.

2. **[MEDIUM] Confirm semiannual date convention** — verify 183-day vs real calendar with model; update date derivation if needed.

3. **[MEDIUM] Add golden validation** — create sponsor IRR fixtures from TUHO/Oborovo Excel; add `test_sponsor_irr_excel_alignment.py`.

4. **[MEDIUM] Add `HoldCoDistributionSchedule` input type** — thin schema wrapper for distribution inputs to `SponsorCashflowRunnerInputs`.

5. **[LOW] Track bisection iterations** — return actual bisection iteration count for audit trail.

6. **[LOW] Add `balance_at_period()` method** — to `SponsorCapitalAccount` for waterfall consumption.

7. **[LOW] Add `dividend_component_keur` to period result** — for future capital return classification.

8. **[LOW] Define `SponsorExportSchema`** — ensure IRR/MOIC results are exportable through the Phase 6F export pipeline.

---

## 12. Conclusion

Phase 7A/7B deliver a solid, audit-safe sponsor economics foundation. The architecture is clean, immutable, and deterministic. Core data flows (cashflow → IRR/MOIC) are correct and well-tested.

**Critical fix required before Phase 7C:** The `capital_account_balance_keur` non-negative constraint will cause runtime failures on realistic sponsor return profiles. This must be addressed before any waterfall integration.

**Confidence level for Phase 7C start:** Medium (pending item #1 fix). All other items are improvements, not blockers.