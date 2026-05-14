# Phase 7F — Distribution Account R99 Engine Design (Revised)

**Date:** 2026-05-14
**Type:** Design + Implementation Plan (Revision 2)
**Author:** OpenClaw agent
**Status:** Draft — for review
**Branch target:** `phase7f-tuho-distribution-calibration` (PR C1)

---

## Context

Phase 7F investigation confirmed:
- Python `cf_after_tax - senior_ds` overstates Excel R99 by **+14,800 kEUR**
- Python `cf_after_tax` is 14,264 kEUR higher than Excel R69 (FCF Banks)
- Excel R99 = Distribution Account with lockup conditions
- PR B1 remains valid and clean
- PR B2 (SHL fcf_waterfall) is blocked until R99-equivalent exists

This is a **revised design** incorporating corrections from cofix review:
- Module moved to `domain/distribution_account/`
- Central waterfall integration (not ui_runner)
- Minimized Period fields
- Explicit R69 bridge as acceptance criterion
- Revised tests and non-goals

---

## 1. Module Location

```
domain/distribution_account/
  __init__.py
  engine.py      # R99 Engine compute function
  lockup.py      # Lockup condition logic
  config.py      # R99EngineConfig dataclass
  result.py      # DistributionAccountResult dataclass
```

**Reason:** R99 is core financial modeling logic — belongs in `domain/`, not `app/`. UI, tests, Excel export, API, and sponsor adapter all use the same central path, so the R99 Engine must be integrated there, not in a UI layer.

---

## 2. Integration Point

### Proposed: `domain/waterfall/waterfall_engine.py`

This is the central model/waterfall execution path. All consumers (UI, tests, Excel export, API, sponsor adapter) route through this layer.

**Why not `ui_runner`:** ui_runner is app-level orchestration. Placing R99 Engine there would mean different code paths for UI vs tests vs export vs sponsor adapter — exactly what we want to avoid.

**Integration sketch:**

```python
# domain/waterfall/waterfall_engine.py

class WaterfallEngine:
    def __init__(self, project, config=None):
        self.project = project
        self.config = config or WaterfallConfig()
        self.use_distribution_account = (
            project.use_distribution_account_r99_engine
            if hasattr(project, 'use_distribution_account_r99_engine')
            else False
        )

    def run(self):
        # Phase 1: Cash flow components (revenue, opex, taxes already done by this point)
        for period in self.periods:
            period.revenue_keur = self._compute_revenue(period)
            period.opex_keur = self._compute_opex(period)
            period.local_tax_keur = self._compute_local_tax(period)
            period.cash_int_keur = self._compute_cash_int(period)
            period.corp_tax_keur = self._compute_corp_tax(period)
            period.senior_ds_keur = self._compute_senior_ds(period)
            period.dsra_funding_keur = self._compute_dsra_funding(period)

        # Phase 2: R99 Engine (if enabled)
        if self.use_distribution_account:
            r99_engine = DistributionAccountEngine(self.project)
            r99_results = r99_engine.compute(self.periods)
            for i, period in enumerate(self.periods):
                result = r99_results[i]
                period.fcf_for_distribution_keur = result.r99_fcf_for_distribution_keur
                period.fcf_for_shl_keur = result.r99_fcf_for_distribution_keur
                period.distribution_lockup_flag = result.lockup_flag
                period.distribution_lockup_reason = result.lockup_reasons
        else:
            # Backward compatibility
            for period in self.periods:
                period.fcf_for_shl_keur = (
                    getattr(period, 'cf_after_tax_keur', 0) or 0
                ) - (
                    getattr(period, 'senior_ds_keur', 0) or 0
                )

        # Phase 3: SHL waterfall (PR C2, not in PR C1)
        # Phase 4: Distributions (PR C2)

        return self.periods
```

**Feature flag belongs in:** `project.financing_params` or `project.config` — must propagate through cache hash / runner config since it affects outputs.

---

## 3. Waterfall Order Clarification

R99 Engine **cannot** run before prerequisites exist. Revised order:

```
STEP 0: Project setup
  - financing_params (contains feature flag)
  - lockup thresholds from project config

STEP 1: Cash flow components (existing, needed before R99)
  revenue_keur         (R20)
  opex_keur            (R38)
  local_tax_keur       (R63)
  cash_int_keur        (R66)
  corp_tax_keur        (R67)
  senior_scheduled_ds_keur  (R70)
  dsra_funding_keur    (R82)

STEP 2: R99 Engine (NEW)
  2a. R69-equivalent = SUM(revenue, opex, local_tax, cash_int, corp_tax) + B70*(year=0)
      → r69_fcf_banks_keur

  2b. R84 = R69 + senior_ds + dsra_funding
      → r84_fcf_junior_keur

  2c. R96 = cash sweep (from DSRA/JDSRA reserves)
      → r96_cash_sweep_keur

  2d. R98 = R84 + R85 + R96 + carryforward_R100
      → r98_distribution_account_keur

  2e. R99 lockup gate:
      IF (OR(DSCR<threshold, year=0, R98<0, DSRA_end<target, JDSRA_end<target) AND year<=14)
        THEN r99 = 0 (locked)
        ELSE r99 = R98
      → r99_fcf_for_distribution_keur
      → fcf_for_shl_keur = r99_fcf_for_distribution_keur
      → r100_carryforward for next period

STEP 3: SHL waterfall (PR C2, not in PR C1)
  consumes fcf_for_shl_keur from Step 2e

STEP 4: Equity distribution (PR C2)
  post-SHL residual
```

---

## 4. Data Model — Minimized

### DistributionAccountResult (full audit, not on Period)

```python
@dataclass
class DistributionAccountResult:
    """Full R99 Engine output for one period — audit/validation use."""
    r69_fcf_banks_keur: float = 0.0          # R69 = FCF Banks
    r84_fcf_junior_keur: float = 0.0          # R84 = FCF Junior = R69 + R70 + R82
    r96_cash_sweep_keur: float = 0.0          # R96 = cash sweep
    r98_distribution_account_keur: float = 0.0  # R98 = SUM(R84,R85,R96) + prev_R100
    r99_fcf_for_distribution_keur: float = 0.0  # R99 = IF(lockup, 0, R98)
    r100_carryforward_keur: float = 0.0        # R100 = next period's carry-forward
    lockup_flag: bool = False
    lockup_reasons: str = ""  # comma-separated: "DSCR<1.1,year=0,DSRA<target"
    dscr_ratio: float = 0.0
    dsra_end_balance_keur: float = 0.0
    dsra_target_keur: float = 0.0
    jdsra_end_balance_keur: float = 0.0
    jdsra_target_keur: float = 0.0
```

### Period — minimum fields (4 fields only)

```python
@dataclass
class Period:
    # ... existing fields ...
    
    # R99 Engine outputs — minimum set
    fcf_for_distribution_keur: float = 0.0    # = R99 after lockup
    fcf_for_shl_keur: float = 0.0              # = fcf_for_distribution_keur (alias for SHL)
    distribution_lockup_flag: bool = False
    distribution_lockup_reason: str = ""
```

**Rationale:** Adding 14+ fields to Period before PR C1 is validated risks: (a) polluting the data model with fields that may need renaming, (b) creating migration work if the design changes post-validation. Full audit fields live in `DistributionAccountResult` — add to Period later only if persistence/export requires it.

---

## 5. R69 Bridge — Explicit Acceptance Criterion

**Critical:** If R69-equivalent is wrong, R99 engine may still miss target even if lockup logic is correct.

The 14,264 kEUR gap between Python `cf_after_tax` and Excel R69 must be traced and resolved in PR C1 — not deferred.

### R69 = FCF Banks formula:

```
R69 = SUM(R20, R38, R63, R66, R67) + B70 * (year = 0)
    = Revenue + OpEx + LocalTax + CashInt + CorpTax + B70*(year=0)
```

Where `B70 = 0` (from Inputs!$G$152) for TUHO operating period.

### R69 bridge acceptance criteria:

| # | Criterion | Target | Note |
|---|-----------|--------|------|
| R69-AC1 | Python R69-equivalent total vs Excel R69 | ±1% of Excel R69 total (300,927 kEUR) → 297,918–303,936 kEUR | **Primary AC** |
| R69-AC2 | R69 selected periods vs Excel | ±100 kEUR for sp_idx 0, 10, 20, 34, 42, 50 | Validate each component |
| R69-AC3 | R84 vs Excel R84 | Derived from R69 + R70 + R82 | Downstream of R69 |
| R69-AC4 | R98 vs Excel R98 | Derived from R84 + carryforward | Downstream of R69 |

**R69 gap must be understood before accepting PR C1.** Possible causes:
- Revenue timing (H1/H2 within period)
- OpEx classification (some OpEx items may be in R63/R66/R67 in Excel but not in Python)
- Tax treatment differences
- Missing DSRA funding contribution to R82

---

## 6. Feature Flag

```python
@dataclass
class WaterfallConfig:
    """Waterfall-level configuration — propagates through cache hash."""
    use_distribution_account_r99_engine: bool = False
    dscr_lockup_threshold: float = 1.1
    lockup_max_year: int = 14
    dsra_target_keur: float = 0.0
    jdsra_target_keur: float = 0.0
```

**Where it belongs:** `project.financing_params` or `project.config` (not `Project` directly). Must propagate through cache hash so that changing the flag invalidates cached results.

**Implementation:**

```python
@dataclass
class FinancingParams:
    """Financing-level parameters — affects waterfall execution."""
    use_distribution_account_r99_engine: bool = False
    dscr_lockup_threshold: float = 1.1
    lockup_max_year: int = 14
    dsra_target_keur: float = 0.0
    jdsra_target_keur: float = 0.0
    # ... existing fields (shl_rate, shl_pik_rate, etc.)
```

```python
@dataclass
class Project:
    financing_params: FinancingParams = field(default_factory=FinancingParams)
    # ... existing fields ...
```

```python
# In waterfall engine:
engine = WaterfallEngine(
    project,
    config=WaterfallConfig(
        use_distribution_account_r99_engine=project.financing_params.use_distribution_account_r99_engine,
        dscr_lockup_threshold=project.financing_params.dscr_lockup_threshold,
        lockup_max_year=project.financing_params.lockup_max_year,
        dsra_target_keur=project.financing_params.dsra_target_keur,
        jdsra_target_keur=project.financing_params.jdsra_target_keur,
    )
)
```

---

## 7. Calculation Flow — R69 → R84 → R98 → R99

```
For each period:
  1. Compute R20 = revenue_keur
  2. Compute R38 = opex_keur
  3. Compute R63 = local_tax_keur (from Macro sheet)
  4. Compute R66 = cash_int_keur (from P&L / reserves)
  5. Compute R67 = corp_tax_keur (from P&L sheet, negative)
  6. Compute R70 = senior_scheduled_ds_keur (negative)
  7. Compute R82 = dsra_funding_keur (zero in TUHO early periods)
  8. Compute R84 = R69 + R70 + R82
  9. Compute R96 = cash_sweep_keur (zero in TUHO)
 10. Compute R98 = R84 + R85 + R96 + prev_R100  (R85=0 in TUHO)
 11. Lockup gate: check conditions
      - DSCR < 1.1?
      - year == 0?
      - R98 < 0?
      - DSRA_end < DSRA_target?
      - JDSRA_end < JDSRA_target?
      AND year <= 14?
      → If all true: R99 = 0, lockup_flag = True
      → Else: R99 = R98, lockup_flag = False
 12. R100 = R98 - R99 + (prev_R100 if lockup)  [accumulate]
 13. Output: r69, r84, r96, r98, r99, carryforward, lockup_flag, lockup_reasons
```

---

## 8. Tests (Revised)

### R69 bridge tests (NEW)
```python
def test_tuho_r69_total_matches_excel():
    """Python R69-equivalent total within ±1% of Excel R69 = 300,927 kEUR."""
    # Target: 297,918 – 303,936 kEUR

def test_tuho_r69_selected_periods():
    """R69 period-by-period vs Excel ±100 kEUR for sp_idx 0, 10, 20, 34, 42, 50."""
    # Compare Python R69 vs Excel R69 for selected periods
```

### R84/R98/R99 tests (revised)
```python
def test_tuho_r84_selected_periods():
    """R84 = R69 + R70 + R82 for selected periods vs Excel ±100 kEUR."""

def test_tuho_r98_carryforward():
    """R98 includes correct carry-forward from prior period."""
    # Verify R100 accumulates correctly when R99 = 0 (lockup)

def test_tuho_r99_total_matches_excel():
    """Python R99 total within ±1% of Excel 234,745 kEUR."""
    # Target: 232,398 – 237,092 kEUR

def test_tuho_r99_lockup_conditions():
    """R99 = 0 when lockup conditions met (DSCR<1.1 AND year<=14)."""
    # Mock: DSCR=1.05, year=5 → R99=0
    # Mock: DSCR=1.05, year=15 → R99=R98 (no lockup, year>14)
```

### Integration tests (revised)
```python
def test_r99_engine_flag_default_false():
    """Default FinancingParams has use_distribution_account_r99_engine=False."""

def test_oborovo_unchanged_when_r99_engine_disabled():
    """Oborovo with flag=False produces same results as before PR C1."""
```

### Full test suite regression
```python
def test_pr_b1_unchanged():
    """All existing tests pass after PR C1 — PR B1 remains clean."""
```

---

## 9. PR C1 Explicit Non-Goals

The following are explicitly **NOT** in scope for PR C1:

- ❌ **No SHL fcf_waterfall** — SHL waterfall is PR C2
- ❌ **No changes to existing pik_then_sweep** — SHL mechanics unchanged
- ❌ **No change to R119 distribution calculation** — R119 is PR C2's validation target
- ❌ **No construction IDC** — PR C4 (independent future work)
- ❌ **No PPA/H1-H2 revenue timing fix** — PR C3 (future)
- ❌ **No UI changes** — optional display later (after PR C1 validation)
- ❌ **No Excel target changes** — 234,745 and 151,709 are fixed
- ❌ **No scaling factor** — R99 must be computed, not fitted
- ❌ **No hardcoded Excel R99 values** — computation only

---

## 10. Revised File List

**Module (new files):**
```
domain/distribution_account/
  __init__.py
  engine.py          # DistributionAccountEngine
  lockup.py          # lockup condition evaluation
  config.py         # R99EngineConfig dataclass
  result.py          # DistributionAccountResult dataclass
```

**Core domain (modify):**
```
domain/waterfall/waterfall_engine.py  # ADD: R99 Engine integration, new output fields
domain/period.py                      # ADD: 4 period fields (fcf_for_distribution, fcf_for_shl, lockup_flag, lockup_reason)
domain/project.py                    # ADD: use_distribution_account_r99_engine in financing_params
```

**Project factories (modify):**
```
domain/project_factories.py   # TUHO: set flag=True; Oborovo: flag=False
```

**Tests (new + modify):**
```
domain/test/
  test_waterfall_engine.py   # MODIFY: add R99 Engine call
  test_distribution_account.py  # NEW: R99 Engine tests (R69, R84, R98, R99, lockup)
  test_period.py             # MODIFY: add new period fields
  test_project.py            # MODIFY: add financing_params flag test
```

**No changes to:** `ui_runner.py`, `app/` modules, `infrastructure/`, revenue/OPEX, SHL mechanics, existing waterfall order.

**Total new files:** ~5 (module) + 2-3 (tests) = 7-8
**Total modified files:** ~4 (domain)
**No ui_runner changes:** ✅

---

## 11. Acceptance Criteria

| # | Criterion | Target | Note |
|---|-----------|--------|------|
| AC1 | Python R69-equivalent total | 297,918–303,936 kEUR (±1%) | **Primary** — must validate R69 before R99 |
| AC2 | Python R69 selected periods | ±100 kEUR for sp_idx 0, 10, 20, 34, 42, 50 | R69 bridge |
| AC3 | Python R84 selected periods | ±100 kEUR for same 6 periods | Downstream of R69 |
| AC4 | Python R98 carry-forward | R100 accumulates when lockup | Downstream |
| AC5 | Python R99 total | 232,398–237,092 kEUR (±1%) | Main target |
| AC6 | Python R99 selected periods | ±100 kEUR for same 6 periods | |
| AC7 | Lockup conditions correct | DSCR<1.1 AND year≤14 triggers R99=0 | Unit tests |
| AC8 | Oborovo unchanged | Flag=False → same results as before PR C1 | Integration |
| AC9 | PR B1 tests pass | Full test suite | Regression |
| AC10 | No SHL fcf_waterfall | Code review — SHL unchanged | |

---

## 12. Summary Answers

### 1. Updated design summary
Design revised with: module in `domain/`, central waterfall integration, minimized Period fields (4), explicit R69 bridge, revised tests (8 total), explicit non-goals.

### 2. Revised module location
```
domain/distribution_account/
  __init__.py / engine.py / lockup.py / config.py / result.py
```

### 3. Revised integration point
`domain/waterfall/waterfall_engine.py` — central model/waterfall execution path. NOT ui_runner. All consumers (UI, tests, Excel export, API, sponsor adapter) share this path.

### 4. Minimal period fields (4)
```python
fcf_for_distribution_keur: float
fcf_for_shl_keur: float
distribution_lockup_flag: bool
distribution_lockup_reason: str
```
Full audit in `DistributionAccountResult` dataclass.

### 5. R69/R84/R98/R99 calculation flow
```
R20 (revenue) + R38 (opex) + R63 (local_tax) + R66 (cash_int) + R67 (corp_tax)
→ R69 (FCF Banks)
R69 + R70 (senior_ds) + R82 (dsra_funding) → R84 (FCF Junior)
R84 + R85 (junior_ds) + R96 (sweep) + prev_R100 → R98 (Distribution Account)
R98 + lockup gate (DSCR<1.1 AND year≤14, or DSRA/JDSRA below target) → R99
R100 = carry-forward for next period
```

### 6. Revised file list
**New:** 5 files in `domain/distribution_account/`, 2-3 test files
**Modified:** `domain/waterfall/waterfall_engine.py`, `domain/period.py`, `domain/project.py`, `domain/project_factories.py`
**No ui_runner changes:** ✅

### 7. Revised test plan
**R69 bridge (2 tests):** `test_tuho_r69_total_matches_excel`, `test_tuho_r69_selected_periods`
**R84/R98/R99 (4 tests):** `test_tuho_r84_selected_periods`, `test_tuho_r98_carryforward`, `test_tuho_r99_total_matches_excel`, `test_tuho_r99_lockup_conditions`
**Integration (3 tests):** `test_r99_engine_flag_default_false`, `test_oborovo_unchanged_when_r99_engine_disabled`, `test_pr_b1_unchanged`
**Total: 9 tests**

### 8. Is PR C1 implementation-ready after this revision?

**Partially — ready for implementation once R69 gap is understood.**

The design is solid and all corrections have been applied. However, before PR C1 can be approved for implementation, the **R69 gap of 14,264 kEUR must be analyzed and either:
- resolved (R69 Python = Excel R69 within ±1%), or
- documented as an Excel-vs-Python structural difference that does not affect R99 accuracy.

**Reason:** If R69 is wrong by 14,264 kEUR, R99 Engine will compute from the wrong base and will miss the 234,745 kEUR target regardless of lockup logic correctness.

**Recommendation:** Add a diagnostic phase before PR C1 implementation — run the R99 Engine with current Python cf_after_tax inputs (as R69 proxy) and see if R99 still misses target. If R99 hits target even with wrong R69, then the lockup logic is the only gap. If R99 misses target, R69 must be fixed first.

---

## Status

**Design: ✅ Complete (Revision 2)**
**R69 diagnostic: ⏳ Pending** — must resolve 14,264 kEUR gap before PR C1 implementation
**PR C1: ⏳ Blocked on R69 diagnostic**
**PR C2: ⏳ Blocked on PR C1 validation**
**PR C3/4: 🔜 Future (independent)**