# Phase 7F — Sponsor Integration Readiness / App Wiring Plan

**Phase:** 7F-1 — Documentation and Readiness
**Date:** 2026-05-12
**Branch:** `phase7f-sponsor-integration-readiness`
**Scope:** Documentation + readiness checks only. No major UI redesign, no API/productization, no persistence backend changes, no tax/project/SPV calculation changes.
**Test Suite (post-PR #60 merge):** 2974 passed | 1 skipped | 1 xfailed

---

## 1. Current Phase 7 Sponsor Stack Status After PR #60

### PR #60 — `fix(waterfall): enforce gp-only catch-up and explicit promote shares` ✅ MERGED

Four bug fixes:

| Bug | Root Cause | Fix |
|-----|------------|-----|
| GP catch-up threshold used `cumulative_invested_by_period[0]` (0.0) | Wrong field used for LP committed capital | Added `lp_invested_capital_keur` to `WaterfallRunnerInputs`; multi-investor mode passes LP committed capital |
| PREFERRED_RETURN double-counted in aggregate cascade | PREF was in Step 1 AND a tier in aggregate cascade | Removed PREF from aggregate; `pref_result=None` passed to aggregate `WaterfallRunnerInputs` |
| `PreferredReturnAllocation.entry_for()` returned wrong period | Always returned last-period entry, not requested period | Fixed to return LP's entry for the exact requested period |
| PROMOTE tier used proportional ownership shares, not carry split | PROMOTE was identical to ROC when LP=80%, GP=20% | Explicit `promote_shares` computed: GP gets `gp_promote_share`; non-GP split proportionally |

### Phase 7 complete module map (post-#60)

```
domain/sponsor/
  equity_injection.py                # Phase 7A — frozen schema
  sponsor_cashflow_result.py         # Phase 7A — frozen results
  sponsor_cashflow_runner.py         # Phase 7A — pure runner
  sponsor_capital_account.py         # Phase 7A — capital account ledger
  sponsor_irr_result.py              # Phase 7B — frozen IRR/MOIC results
  sponsor_irr_runner.py              # Phase 7B — pure XIRR/MOIC runner
  xirr.py                            # Phase 7B — deterministic XIRR
  sponsor_waterfall_tier.py          # Phase 7C — TierType, SponsorShare, SponsorWaterfallTier
  preferred_return_calculator.py     # Phase 7C — PreferredReturnCalculator
  preferred_return_result.py         # Phase 7C — PreferredReturnResult schema
  waterfall_runner.py                # Phase 7C — run_waterfall() (single + multi)
  waterfall_allocation_result.py     # Phase 7C — allocation result schemas
  capital_account_tier_annotation.py # Phase 7C — tier annotation for capital accounts
  investor_registry.py               # Phase 7D — frozen InvestorRegistry
  capital_stack.py                  # Phase 7D — CapitalStack
  multi_investor_waterfall_runner.py # Phase 7D — run_multi_investor_waterfall()
  preferred_return_allocation.py     # Phase 7D — LP catch-up trigger adapter

domain/persistence/
  snapshot_base.py                   # Phase 7E — primitives
  project_snapshot.py               # Phase 7E — ProjectSnapshot
  scenario_snapshot.py               # Phase 7E — ScenarioSnapshot, InputSnapshot, ResultSnapshot
  sponsor_snapshot.py               # Phase 7E — SponsorSnapshot (NOT wired to ORM)
  snapshot_serializer.py            # Phase 7E — deterministic JSON + SHA-256
  snapshot_store.py                 # Phase 7E — SnapshotStore interface + InMemorySnapshotStore
```

**Phase 7 status:** All phases 7A–7E merged to `main`. PR #60 bug fixes merged. Phase 7F is scoped to integration readiness.

---

## 2. Confirm ISSUE-A and GP Catch-up Stabilization Status

### ISSUE-A: GP Catch-up Threshold Used Wrong LP Capital ✅ RESOLVED

**Root cause:** `cumulative_invested_by_period[0]` was 0.0 (first period), not LP committed capital.

**Fix (PR #60):** `lp_invested_capital_keur` field added to `WaterfallRunnerInputs`. Multi-investor mode passes LP's actual committed capital from `InvestorEntry.committed_capital_keur`. Single-investor falls back to `cumulative_invested_by_period[-1]`.

**Verification:**
```python
# Before fix: threshold = (0.20/0.80) × max(0, lp_cum_pref − 0.0) = 0.25 × trigger
# After fix:  threshold = (0.20/0.80) × max(0, lp_cum_pref − 8000.0) = 0.25 × max(0, trigger)
```
With LP invested capital 8,000 kEUR, LP cumulative preferred return must exceed 8,000 kEUR before GP catch-up triggers — correct institutional carry economics.

**Test coverage:** `TestGpCatchUpAllocations` confirms LP gets 0 in GP_CATCH_UP and GP gets full catch-up allocation.

---

## 3. Sponsor Modules Available for Orchestration

### Core runners

| Function | Location | Signature |
|----------|----------|-----------|
| `run_sponsor_cashflows` | `domain/sponsor/sponsor_cashflow_runner.py` | `(SponsorCashflowRunnerInputs) -> SponsorCashflowResult` |
| `run_sponsor_irr` | `domain/sponsor/sponsor_irr_runner.py` | `(SponsorIrrRunnerInputs) -> SponsorIrrResult` |
| `calculate_preferred_return` | `domain/sponsor/preferred_return_calculator.py` | `(PreferredReturnCalculatorInputs) -> PreferredReturnResult` |
| `run_waterfall` | `domain/sponsor/waterfall_runner.py` | `(WaterfallRunnerInputs) -> WaterfallAllocationResult` |
| `run_multi_investor_waterfall` | `domain/sponsor/multi_investor_waterfall_runner.py` | `(MultiInvestorWaterfallInputs) -> MultiInvestorWaterfallResult` |

### Result types

| Type | Purpose |
|------|---------|
| `SponsorCashflowResult` | Per-period equity injections, distributions, net cashflow, capital account balance |
| `SponsorIrrResult` | equity_irr, project_irr, moic |
| `PreferredReturnResult` | Accrued preferred return, unpaid balance, per-period entries |
| `WaterfallAllocationResult` | Per-period tier allocations across all sponsors |
| `MultiInvestorWaterfallResult` | Aggregate waterfall + per-investor breakdowns + capital accounts |
| `TierAnnotatedSponsorCapitalAccount` | Capital account with tier annotations |

### Input types

| Type | Purpose |
|------|---------|
| `SponsorCashflowRunnerInputs` | investor_id, equity_injections, holdco_distribution_by_period, etc. |
| `SponsorIrrRunnerInputs` | cashflow result + invested capital |
| `PreferredReturnCalculatorInputs` | tier, cumulative_invested_by_period, distributions_by_period |
| `WaterfallRunnerInputs` | tiers, available_cash, pref_result, cumulative_invested, num_periods, lp_cumulative_pref_by_period, lp_invested_capital_keur |
| `MultiInvestorWaterfallInputs` | capital_stack, registry, hurdle_rate_pa, compounding_convention, gp_promote_share, available_cash_by_period |

---

## 4. App/Orchestrator Integration Gap

### Current state

The Phase 7 domain runners exist but are **not wired into the app/orchestrator layer**:

```
app/waterfall_core.py    → run_waterfall_v3_core()  — SPV/project waterfall only
app/ui_runner.py         → _run_waterfall()         — SPV/project waterfall only
app/sponsor_waterfall_excel_export.py → write_sponsor_waterfall_audit_sheets() — reads domain results, standalone
app/excel_export.py      → calls sponsor_waterfall_excel_export (expects domain objects)
```

**Gap:** No `app/sponsor_runner.py` or equivalent that:
1. Builds `MultiInvestorWaterfallInputs` from project inputs
2. Calls `run_multi_investor_waterfall()`
3. Produces `MultiInvestorWaterfallResult`
4. Wires to Excel export and/or UI

Also:
- `domain/persistence/sponsor_snapshot.py` exists but is **not wired to ORM** (no SQLAlchemy model for `SponsorSnapshot`)
- `app.excel_export.py` accepts `sponsor_waterfall_result` etc. but there is no code path that actually produces these from Phase 7 runners for a real project

### Required integration points

1. **Project inputs → `MultiInvestorWaterfallInputs`** — build investor registry, capital stack, hurdle rate, promote share from project config
2. **Project model → available_cash_by_period** — wire cash flow projections into waterfall runner
3. **`run_multi_investor_waterfall()` output → Excel export** — pass result to `write_sponsor_waterfall_audit_sheets()`
4. **`run_multi_investor_waterfall()` output → `SponsorSnapshot`** — serialize for persistence
5. **`SponsorSnapshot` → ORM** — add `SponsorSnapshotModel` and wire to `Scenario`

---

## 5. Required Minimal Inputs for Sponsor Run

For a minimal end-to-end sponsor waterfall run:

```
MultiInvestorWaterfallInputs(
    capital_stack=CapitalStack(...),          # from InvestorRegistry + contributions
    registry=InvestorRegistry(...),            # LP + GP entries
    hurdle_rate_pa=0.08,                       # annual preferred return rate
    compounding_convention=CompoundingConvention.SEMIANNUAL,
    gp_promote_share=0.20,                    # GP carry % (20% for 8-and-20)
    available_cash_by_period=(1000.0, 2000.0, ...),  # per-period cash for distribution
    metadata=(("project","TUHO"), ("currency","EUR")),
)

PreferredReturnCalculatorInputs(
    tier=SponsorWaterfallTier(...),            # per-investor PREF tier
    cumulative_invested_by_period=(8000.0, ...),  # investor's own invested capital
    distributions_by_period=(0.0, 0.0, ...),   # distributions allocated to this investor
    num_periods=60,
)
```

**Minimum viable project config:**
- LP committed capital (kEUR)
- GP committed capital (kEUR)
- LP/GP ownership percentages (must sum to 1.0)
- Annual hurdle rate (decimal)
- Compounding convention
- GP promote/share (decimal)
- Per-period available cash for distribution (kEUR)

---

## 6. Required Minimal Outputs for Internal Product

### For waterfall display/export

```
MultiInvestorWaterfallResult:
  .registry                      → InvestorRegistry (echo)
  .per_investor_results          → tuple[PerInvestorWaterfallResult]  (LP + GP each)
  .aggregate_waterfall_result    → WaterfallAllocationResult (ROC+CATCH_UP+PROMOTE+RESIDUAL)
  .total_available_by_period_keur → tuple[float] (echo of inputs)
  .total_allocated_keur          → float
  .gp_catch_up_threshold_keur   → float (total committed capital)

PerInvestorWaterfallResult:
  .investor_id, .ownership_pct
  .pref_result                   → PreferredReturnResult (per-investor PREF)
  .waterfall_result              → WaterfallAllocationResult (aggregate tiers, per-investor-filtered)
  .capital_account               → TierAnnotatedSponsorCapitalAccount
```

### For IRR/MOIC display

```
SponsorIrrResult:
  .equity_irr      → float (XIRR)
  .project_irr     → float
  .moic            → float
```

### For Excel audit export

`write_sponsor_waterfall_audit_sheets()` already accepts:
- `waterfall_result: WaterfallAllocationResult`
- `preferred_return_result: PreferredReturnResult`
- `tier_annotated_accounts: TierAnnotatedSponsorCapitalAccount`

All types are frozen dataclasses — no mutation risk in export.

---

## 7. Excel/Export Readiness

### Phase 7C-5 sponsor waterfall audit export

**File:** `app/sponsor_waterfall_excel_export.py`
**Function:** `write_sponsor_waterfall_audit_sheets()`
**Status:** ✅ Implemented, produces three sheets:
1. `Sponsor Waterfall Allocation` — per-period per-tier available/allocated/remaining with LP/GP split
2. `Preferred Return Accrual` — per-period PREF accrual and unpaid balance
3. `Tier Capital Account` — tier-annotated capital account

**Not yet connected:** No app code path wires a real `MultiInvestorWaterfallResult` into this export for an actual project. The export expects `WaterfallAllocationResult` (single-investor aggregate) but Phase 7D produces `MultiInvestorWaterfallResult` with an `aggregate_waterfall_result: WaterfallAllocationResult`.

**Integration path:**
```python
result = run_multi_investor_waterfall(inputs)
# LP results
write_sponsor_waterfall_audit_sheets(
    fp, ..., 
    waterfall_result=result.per_investor_results[0].waterfall_result,  # LP
    preferred_return_result=result.per_investor_results[0].pref_result,
    tier_annotated_accounts=result.per_investor_results[0].capital_account,
)
# GP results similarly
```

### Excel export integration gap

`app/excel_export.py` already has the wire:
```python
if sponsor_waterfall_result or sponsor_preferred_return_result or tier_annotated_capital_accounts:
    write_sponsor_waterfall_audit_sheets(..., sponsor_waterfall_result, sponsor_preferred_return_result, tier_annotated_capital_accounts)
```

But `sponsor_waterfall_result=None` is passed in all current code paths. This is the integration gap to fill in Phase 7F.

---

## 8. Persistence Snapshot Readiness

### SponsorSnapshot exists but is not wired to ORM

**File:** `domain/persistence/sponsor_snapshot.py`

**Schema:**
```python
@dataclass(frozen=True)
class SponsorSnapshot:
    schema_version: str  = "1"
    investor_registry: InvestorRegistrySnapshot
    capital_stack: CapitalStackSnapshot
    waterfall_result_json: dict          # WaterfallAllocationResult as JSON
    preferred_return_json: dict | None   # PreferredReturnResult as JSON
    capital_account_json: dict           # TierAnnotatedSponsorCapitalAccount as JSON
    inputs_hash: str                    # SHA-256 of inputs that produced this result
```

**ORM gap:** There is no SQLAlchemy model for `SponsorSnapshot`. `Scenario` model in `persistence/models.py` does not have a `sponsor_snapshot` FK column.

### Persistence integration path

1. Add `SponsorSnapshotModel` to `persistence/models.py` (SQLAlchemy)
2. Add `sponsor_snapshot_id: Mapped[int] | None` FK to `ScenarioModel`
3. Add `sponsor_snapshot: Mapped[SponsorSnapshotModel | None]` relationship to `ScenarioModel`
4. In `ScenarioRepository.save()`, serialize `SponsorSnapshot` → `SponsorSnapshotModel`
5. In `ScenarioRepository.load()`, deserialize `SponsorSnapshotModel` → `SponsorSnapshot`

**Note:** This is a Phase 7F ORM wiring task, not a persistence schema change. The `SponsorSnapshot` domain type is frozen and ready.

---

## 9. Known Remaining Pre-Phase-8 Issues

### Open issues (not resolved by PR #60)

| # | Issue | Severity | Phase |
|---|-------|----------|-------|
| O-1 | Oborovo/TUHO golden calibration — model vs Excel still diverges on DSCR, equity IRR, OpEx | MEDIUM | 6B |
| O-2 | `persistence/` vs `domain/persistence/` — two persistence trees, migration needed | MEDIUM | 5→7 |
| O-3 | `SponsorSnapshot` typed instead of opaque dict — currently `waterfall_result_json: dict`, should be typed `WaterfallAllocationResult` | MEDIUM | 7E |
| O-4 | Sponsor app/orchestrator wiring — no code path from project inputs to `run_multi_investor_waterfall()` | HIGH | 7F |
| O-5 | Tier ordering validation — is tier ordering enforced in `run_multi_investor_waterfall()`? | LOW | 7C |

### ISSUE-A: GP catch-up threshold ✅ RESOLVED by PR #60

### ISSUE-B: PROMOTE proportional shares (not carry) ✅ RESOLVED by PR #60

### ISSUE-C: PREF double-counted in aggregate ✅ RESOLVED by PR #60

---

## 10. Recommended Phase 7F Implementation Order

### Step 1: Wire sponsor waterfall into app layer (HIGH priority — unblocks everything)
- Create `app/sponsor_runner.py`
- `SponsorRunConfig` dataclass: `investor_registry`, `capital_stack`, `hurdle_rate_pa`, `compounding_convention`, `gp_promote_share`, `available_cash_by_period`
- `run_sponsor_waterfall(config: SponsorRunConfig) -> MultiInvestorWaterfallResult`
- Minimal: just call `run_multi_investor_waterfall()` with the right inputs

### Step 2: Wire SponsorSnapshot to ORM (MEDIUM priority)
- Add `SponsorSnapshotModel` to `persistence/models.py`
- Add `sponsor_snapshot` FK on `Scenario`
- Update `ScenarioRepository.save()` / `load()`

### Step 3: Wire sponsor results to Excel export (MEDIUM priority)
- After `run_sponsor_waterfall()`, pass per-investor results to `write_sponsor_waterfall_audit_sheets()`
- Update `app/excel_export.py` to accept and pass `MultiInvestorWaterfallResult`

### Step 4: Wire to UI (LOW priority — Streamlit pages)
- `ui/pages/1_Project_Inputs.py` or new page: accept LP/GP capital, ownership, promote share
- `ui/pages/2_Waterfall.py`: display per-investor waterfall results
- Minimal: just show the data already produced by `run_sponsor_waterfall()`

### Step 5: Add sponsor IRR to run (LOW priority)
- `run_sponsor_irr()` on the cashflow result from `run_sponsor_waterfall()`
- Display equity IRR and MOIC per investor

### Step 6: Address remaining open issues (ongoing)
- O-1: Oborovo/TUHO golden calibration (separate Phase 6B follow-up)
- O-2: `persistence/` vs `domain/persistence/` migration (separate Phase 5→7 cleanup)
- O-3: Typed `SponsorSnapshot` instead of JSON dict
- O-5: Tier ordering validation confirm

---

## Appendix: Phase 7 Module Responsibility Matrix

| Module | Responsibility | Callable by |
|--------|---------------|-------------|
| `domain/sponsor/sponsor_cashflow_runner.py` | Equity CF per investor | App/orchestrator |
| `domain/sponsor/sponsor_irr_runner.py` | IRR/MOIC | App/orchestrator |
| `domain/sponsor/preferred_return_calculator.py` | PREF accrual per investor | App/orchestrator |
| `domain/sponsor/waterfall_runner.py` | Single-investor waterfall | App/orchestrator |
| `domain/sponsor/multi_investor_waterfall_runner.py` | Multi-investor waterfall | App/orchestrator |
| `app/sponsor_waterfall_excel_export.py` | Excel audit sheets | App/export |
| `app.excel_export.py` | Main Excel export orchestrator | App |
| `domain/persistence/sponsor_snapshot.py` | Snapshot serialization | App/persistence |
| `persistence/models.py` | ORM models | Persistence |

**No direct calls from domain → app.** All calls go: app → domain. Domain is pure and has zero app imports.