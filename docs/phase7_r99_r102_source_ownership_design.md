# Phase 7 — R98/R99/R102/R119 Source Ownership Design

> **Status:** DESIGN / DOCS ONLY  
> **Branch:** `phase7-r99-r102-source-ownership-design`  
> **PRs merged:** #97–#108  
> **R99/R102: BLOCKED**

---

## 1. Executive Summary

This document defines source ownership and module boundaries for the R98/R99/R102/R119 cashflow rows before any runtime promotion is attempted. It is a design document, not an implementation.

**Key findings:**
- `DistributionAccount` owns R98 (distribution account balance), R99 (FCF gate), R100 (carryforward), R102 (FCF for SHL)
- `SeniorDebtSizing` does NOT gate distributions — it only computes sizing capacity
- `ShlEngine` consumes post-senior cash, not R99/R102 directly
- `SponsorEngine` receives distributions, not R99/R102 directly
- R99/R102 gate logic is in `DistributionAccount.compute_tuho_r99_input_period()` — **this is the BLOCKED module**
- No canonical module promotes R99/R102 to runtime source

**Decision: R99/R102 remain BLOCKED** until the ownership matrix is resolved and default-off promotion path is designed.

---

## 2. Current Excel Source Map (TUHO)

Reference: `reports/phase7_tuho_shl_cash_sweep_extraction.csv` (PR #98)

### 2.1 R98/R99/R102/R119 Row Definitions

| Row | Excel Cell | Formula | Description |
|-----|-----------|---------|-------------|
| R69 | `CF!R69` | `=Revenue - OpEx + LocalTax + CashIntReserve - CashTax` | FCF Banks |
| R84 | `CF!R84` | `=R69 - SeniorDS + DSRA release` | FCF Junior |
| R98 | `CF!R98` | `=R84 + JuniorDS + ReserveSweep + prev_R100` | Distribution Account balance |
| R99 | `CF!R99` | `=IF(AND(OR(R128<$B$99,...),...),0,R98)` | FCF for Distribution (DSCR-gated) |
| R100 | `CF!R100` | `=IF(locked, R98, 0)` | Carryforward to next period |
| R102 | `CF!R102` | `=R99` | FCF for SHL |
| R119 | `CF!R119` | Dividend / final distribution | Sponsor cashflow |

### 2.2 R99 Gate Logic

```
IF(OR(R128 < B99, year=0, R98<0, DSRA<target, JDSRA<target), 0, R98)
  └── DS!R128 = current period DSCR
  └── B99 = lockup DSCR threshold (1.10 for TUHO)
```

**R99 = 0 (distribution locked) when any of:**
- DSCR < lockup threshold (1.10)
- Year index = 0 (construction)
- R98 < 0 (negative FCF)
- DSRA balance < target
- JDSRA balance < target

**R99 = R98 (distribution unlocked) when all conditions cleared.**

### 2.3 R102 = R99 (SHL gets 100% of post-gate cash)

After R99 distribution gate: `CF!R102 = R99` — SHL receives 100% of whatever passed through R99. No separate SHL reserve, no minimum cash retention.

---

## 3. Current Python Source Map

### 3.1 `domain/distribution_account/engine.py` — R99/R102 computation

```python
def compute_tuho_r99_input_period(
    revenue_keur, opex_keur, local_tax_keur,
    cash_interest_on_reserves_keur, corporate_tax_cash_keur,
    senior_ds_keur, dsra_release_or_funding_keur,
    junior_ds_keur, reserve_sweep_keur,
    previous_r100_carryforward_keur, year_index,
    senior_tenor_years, dscr, lockup_dscr,
    dsra_balance_keur, dsra_target_keur,
    jdsra_balance_keur, jdsra_target_keur,
) -> R99InputResult:
    r69 = revenue - opex + local_tax + cash_int_reserve - cash_tax
    r84 = r69 - senior_ds + dsra_release
    r98 = r84 + junior_ds + reserve_sweep + prev_r100

    reasons = []
    if dscr < lockup_dscr: reasons.append("dscr_below_lockup")
    if year_index == 0: reasons.append("year_zero")
    if r98 < 0: reasons.append("negative_r98")
    if dsra_balance < dsra_target: reasons.append("dsra_below_target")
    if jdsra_balance < jdsra_target: reasons.append("jdsra_below_target")

    locked = year_index <= senior_tenor_years and bool(reasons)
    r99 = 0.0 if locked else r98
    r100 = r98 if locked else 0.0
    r102 = r99
```

### 3.2 `app/waterfall_core.py` — R99/R102 wiring

```python
r99_audit = compute_tuho_r99_input_period(...)  # line 429
# Results attached as AUDIT fields only:
period.r69_fcf_banks_keur = r99_audit.r69_fcf_banks_keur
period.r84_fcf_junior_keur = r99_audit.r84_fcf_junior_keur
period.r98_distribution_account_keur = r99_audit.r98_distribution_account_keur
period.r99_fcf_for_distribution_keur = r99_audit.r99_fcf_for_distribution_keur
period.r100_carryforward_keur = r99_audit.r100_carryforward_keur
period.r102_fcf_for_shl_keur = r99_audit.r102_fcf_for_shl_keur
period.fcf_for_shl_keur = r99_audit.fcf_for_shl_keur
```

**Status: AUDIT ONLY** — these values do NOT feed runtime SHL service, distribution account, or sponsor IRR.

### 3.3 `domain/waterfall/waterfall_engine.py` — SHL service

```python
# TUHO SHL cash-cap — DISABLED (awaiting reorder)
if use_senior_sweep_cash_cap_for_shl and shl_repayment_method == "pik_then_sweep":
    pass  # DISABLED

# SHL computation uses cf_after_tax directly, not R99/R102:
if shl_repayment_method == "fcf_waterfall":
    fcf_waterfall_result = compute_shl_fcf_waterfall_period(...)
    shi, shp, shl_pik, shl_balance = ...
elif is_shl_disbursement_period:
    shi = shp = shl_pik = 0.0
else:
    (shi, shp, shl_pik, shl_balance) = compute_shl_period(
        shl_balance=shl_balance,
        shl_rate_per_period=shl_rate_per,
        cf_after_senior_ds=_cf_for_shl,  # ← cf_after_tax, not R99
        method=shl_repayment_method,
        ...
    )
```

**Status: Legacy SHL** uses `cf_after_tax` directly. R99/R102 is not wired to SHL service.

---

## 4. R98/R99/R102/R119 Ownership Matrix

| Row | Owner Module | Owner Function | Runtime Source? | Audit Only? |
|-----|-------------|----------------|-----------------|-------------|
| R69 (FCF Banks) | `DistributionAccount` | `compute_tuho_r99_input_period` | ❌ No | ✅ Yes |
| R84 (FCF Junior) | `DistributionAccount` | `compute_tuho_r99_input_period` | ❌ No | ✅ Yes |
| R98 (Dist Account balance) | **`DistributionAccount`** | `compute_tuho_r99_input_period` | ❌ No | ✅ Yes |
| R99 (FCF gate) | **`DistributionAccount`** | `compute_tuho_r99_input_period` (gate logic) | ❌ No | ✅ Yes |
| R100 (Carryforward) | `DistributionAccount` | `compute_tuho_r99_input_period` | ❌ No | ✅ Yes |
| R102 (FCF for SHL) | `DistributionAccount` (= R99) | `compute_tuho_r99_input_period` | ❌ No | ✅ Yes |
| R119 (Dividend) | `SponsorEngine` | Sponsor IRR computation | ❌ No | ✅ Yes |

### 4.1 Ownership Clarifications

**Q1: Who owns R98 distribution account balance?**
- **Owner:** `DistributionAccount.compute_tuho_r99_input_period()`
- R98 is computed as: `R84 + JuniorDS + ReserveSweep + prev_R100`
- This is the **input** to the distribution gate
- **Runtime source: NO** — R98 feeds gate logic only

**Q2: Who owns R99 FCF for distribution gate?**
- **Owner:** `DistributionAccount.compute_tuho_r99_input_period()`
- R99 = `0 if locked else R98` (lockup conditions apply)
- **Runtime source: NO** — gate result stored as audit field `r99_fcf_for_distribution_keur`
- **BLOCKED** — gate logic not promoted

**Q3: Who owns R102 FCF for SHL?**
- **Owner:** `DistributionAccount.compute_tuho_r99_input_period()` (since R102 = R99)
- R102 = R99 (100% of post-gate cash goes to SHL)
- **Runtime source: NO** — stored as audit field `r102_fcf_for_shl_keur`
- **BLOCKED** — not wired to SHL service

**Q4: Who owns R119 final distribution/dividend?**
- **Owner:** `SponsorEngine` (receives distributions from runtime distribution account)
- `DistributionAccount` does NOT compute R119
- R119 = final dividend after all gates and distributions
- **Runtime source: NO** — only audit fields populated

**Q5: When does SHL consume post-senior cash?**
- SHL consumes `cf_after_tax - senior_ds` (in legacy `compute_shl_period`)
- SHL does **NOT** consume R99 or R102 directly
- SHL does **NOT** apply DSCR gate — it receives cash from waterfall, not from distribution account

**Q6: When does cash move from SHL to distribution account?**
- Cash flows: `Waterfall → SHL service → cash_after_shl → distribution_account`
- SHL principal repayment and interest reduce `cash_after_shl`
- Distribution account receives `cash_after_shl` (or portion thereof)
- **R99 gate is NOT in this path** — gate applies to R98, not to post-SHL cash

**Q7: Which module applies DSCR / distribution lock-up gates?**
- **Owner:** `DistributionAccount.compute_tuho_r99_input_period()`
- DSCR lockup is in the gate logic (conditions checked before R99 = R98)
- **This is the BLOCKED module** — gate results are audit-only

**Q8: Which outputs flow to SponsorEngine?**
- `DistributionAccount` outputs: `cash_after_shl` (post-SHL cash)
- `SponsorEngine` inputs: `distribution_keur` (dividend/sponsor distribution)
- R99/R102 gate does **NOT** feed SponsorEngine directly

**Q9: Which rows remain audit-only?**
- All R69, R84, R98, R99, R100, R102 are AUDIT ONLY
- None of the distribution account rows feed runtime cash routing

**Q10: What must be true before R99/R102 can become runtime source?**
1. `DistributionAccount.compute_tuho_r99_input_period()` must be refactored to expose a flag
2. Gate logic must be decoupled from audit-only path
3. Default-off flag must be added to `ProjectInfo`
4. SHL service must be re-wired to receive R102 instead of `cf_after_tax` (or equivalent)
5. All existing tests must pass with new flag = False
6. TUHO fixture regression must confirm no regression
7. R99/R102 BLOCKED remains until conditions 1-6 are met

---

## 5. SHL → DistributionAccount Boundary

```
┌─────────────────────────────────────────────────────────────┐
│  WaterfallPeriod                                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ CFADS → cf_after_tax → senior_ds → _cf_for_shl      │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↓                                 │
│              compute_shl_period_v3()                        │
│              (legacy: cf_after_tax, not R99)               │
│                          ↓                                 │
│              SHL interest + principal + PIK                 │
│              cash_after_shl_keur (remainder)                │
│                          ↓                                 │
│              cash_for_distribution_keur                    │
│                          ↓                                 │
│              DistributionAccount (distributes to sponsor)  │
│                                                             │
│  R99 gate: checks DSCR, year, DSRA targets, R98            │
│  R99 = 0 (locked) OR R99 = R98 (unlocked)                  │
│  R102 = R99 (SHL gets 100% of gate output)                 │
└─────────────────────────────────────────────────────────────┘

Current: cash_after_shl → distribution (NO R99 gate in path)
Future:  R99 gate → R102 → SHL (if flag-on, after conditions met)
```

### 5.1 Current Boundary

| Module | Input | Output | Status |
|--------|-------|--------|--------|
| Waterfall | CFADS | `_cf_for_shl = cf_after_tax - senior_ds` | Runtime |
| SHL (legacy) | `_cf_for_shl` | `cash_after_shl` | Runtime |
| SHL (canonical, PR #103/108) | `post_senior_cash_available_keur` | `cash_for_distribution_keur` | Audit-only |
| DistributionAccount | `cash_after_shl` | `distribution_keur` | Runtime |

### 5.2 Canonical SHL (audit-only)

The canonical `ShlEngine.compute()` produces `cash_for_distribution_keur` per period — but this is **not wired** to `DistributionAccount`. The canonical result is for audit/comparison only.

---

## 6. DistributionAccount → SponsorEngine Boundary

```
DistributionAccount
  └── cash_after_shl → distribution_keur (to sponsor)
  └── NOT: R99/R102 gate applied to distribution
         (R99 gate is AUDIT ONLY)
```

**Current:** `distribution_keur = cash_after_shl` (no gate)
**Future (blocked):** `distribution_keur = f(R99, cash_after_shl)` with DSCR gate

---

## 7. Senior Debt / DSCR Gate Dependency

```
SeniorDebtSizingEngine (PR #100/104)
  └── Computes: debt_service_capacity_keur_by_period
  └── Does NOT: gate distributions

DSCR measurement
  └── waterfall_engine.py: computes per-period DSCR
  └── used by: DistributionAccount (lockup check)
  └── NOT used by: SeniorDebtSizingEngine (sizing only)

DistributionAccount lockup check
  └── dscr < lockup_dscr → R99 = 0
  └── dscr >= lockup_dscr → R99 = R98
```

**Key separation:** Senior debt sizing uses a **sizing DSCR** (from `sizing_cfads`), not the actual DSCR used in the distribution gate. The gate uses actual DSCR measured from runtime CFADS.

---

## 8. Tax and Cashflow Dependency

```
Revenue → EBITDA → Tax → CFADS → R69 → R84 → R98 → R99 (gate) → R102 → SHL
                                ↓
                    corporate_tax_cash_keur (reduces R69)
                                ↓
                    DistributionAccount (receives post-tax cash)
```

**Tax dependency:**
- `corporate_tax_cash_keur` (cash tax, not accrued) reduces R69
- R99 gate uses `dscr` which is computed after tax (CFADS-based)
- TaxEngine output (`cit_cash_tax_keur`) flows into R69 via `corporate_tax_cash_keur`

**No circular dependency** — tax flows into distribution, distribution does not flow back into tax.

---

## 9. Runtime Source vs Audit-Only Matrix

| Row | Module | Used by Runtime? | Audit Only? | Notes |
|-----|--------|-------------------|-------------|-------|
| R69 | DistributionAccount | ❌ | ✅ | CFADS after tax |
| R84 | DistributionAccount | ❌ | ✅ | FCF after senior |
| R98 | DistributionAccount | ❌ | ✅ | Distribution account balance |
| R99 | **DistributionAccount** | ❌ | ✅ | **BLOCKED — gate not promoted** |
| R100 | DistributionAccount | ❌ | ✅ | Carryforward |
| R102 | DistributionAccount | ❌ | ✅ | **BLOCKED — SHL not wired** |
| R119 | SponsorEngine | ❌ | ✅ | Final dividend |
| cash_after_shl | WaterfallEngine | ✅ | ❌ | Runtime: SHL → distribution |
| cash_for_dist (canonical) | ShlEngine (PR #103/108) | ❌ | ✅ | Audit only |
| distribution_keur | WaterfallEngine | ✅ | ❌ | Runtime to sponsor |
| shl_interest_keur | WaterfallEngine | ✅ | ❌ | Runtime SHL interest |
| shl_principal_keur | WaterfallEngine | ✅ | ❌ | Runtime SHL principal |

**Conclusion:** All R98-R102 rows are audit-only. Only `cash_after_shl` and `distribution_keur` are runtime sources.

---

## 10. Required Gates Before Promotion

R99/R102 cannot be promoted to runtime source until all of the following are true:

### Gate 1: DistributionAccount Refactor
- [ ] `compute_tuho_r99_input_period()` refactored to expose `DistributionAccountResult`
- [ ] Gate logic separated from audit computation
- [ ] `use_r99_runtime_gate: bool = False` flag in `ProjectInfo`
- [ ] Default-off path unchanged

### Gate 2: SHL Re-wiring
- [ ] SHL service receives R102 instead of `cf_after_tax` (or equivalent)
- [ ] `use_shl_canonical_engine` flag wired to receive canonical `cash_for_distribution`
- [ ] No circular dependency: R102 → SHL → cash_after_shl → DistributionAccount

### Gate 3: DSCR Gate Decoupling
- [ ] DSCR lockup check is owned by `DistributionAccount`, not `SeniorDebtSizing`
- [ ] Actual DSCR (from runtime) vs sizing DSCR separation confirmed
- [ ] Lockup threshold (`lockup_dscr`) is explicit input, not hardcoded

### Gate 4: TUHO Fixture Regression
- [ ] TUHO model runs with flag=False → no regression
- [ ] TUHO model runs with flag=True → matches Excel R99/R102 values
- [ ] Oborovo model runs with flag=False → no regression

### Gate 5: SponsorEngine Separation
- [ ] SponsorEngine receives `distribution_keur` from `DistributionAccount`, not from R99 gate directly
- [ ] R99 promotion does not change SponsorEngine behavior
- [ ] Sponsor IRR test confirms no regression

### Gate 6: Test Coverage
- [ ] `test_r99_gate_off_default` — flag=False, no change
- [ ] `test_r99_gate_on_matches_excel` — flag=True, R99 = Excel R99
- [ ] `test_shl_receives_r102` — flag=True, SHL cash = R102
- [ ] `test_no_sponsor_irr_regression` — sponsor IRR unchanged with flag=True

---

## 11. Default-Off Implementation Path

```
Phase A: Audit-only flag (R99/R102 remains BLOCKED)
─────────────────────────────────────────────────────
1. Add use_r99_runtime_gate: bool = False to ProjectInfo (domain/inputs.py)
2. DistributionAccount.compute_tuho_r99_input_period() stays audit-only
3. No runtime behavior change
4. TUHO fixture regression confirms no regression

Phase B: R99 gate flag-on (default-off, minimal wiring)
─────────────────────────────────────────────────────
5. Wire R99 result into DistributionAccount.distribution_keur computation
   - distribution_keur = f(R99, cash_after_shl) when flag=True
   - distribution_keur = cash_after_shl when flag=False (unchanged)
6. SHL: re-wire to receive R102 via fcf_waterfall_cash_schedule_keur or equivalent
7. All Phase A tests pass; new Phase B tests pass

Phase C: Canonical SHL wiring (optional, after Phase B)
─────────────────────────────────────────────────────
8. Wire canonical ShlEngine.compute() output to SHL service
   - canonical cash_for_distribution replaces legacy cash_after_shl
   - use_shl_canonical_engine flag controls wiring
   - R99 gate still applies (DistributionAccount owns gate, not ShlEngine)

Phase D: Full promotion (after Phase A+B+C validated)
─────────────────────────────────────────────────────
9. Remove `_runtime_gate=False` default → gate on
10. Oborovo model needs equivalent R99/R102 analysis
```

---

## 12. Non-Goals / Forbidden Scope

- ❌ **No runtime implementation** — this is design only
- ❌ **No R99/R102 promotion** — BLOCKED
- ❌ **No distribution account code changes** — audit-only path only
- ❌ **No SHL runtime behavior changes** — canonical is audit-only
- ❌ **No tax runtime changes** — TaxEngine unchanged
- ❌ **No sponsor IRR changes** — SponsorEngine unchanged
- ❌ **No `app/waterfall_core.py` changes** — no runtime rewrites
- ❌ **No new flags** — implementation path documented, flags deferred to future branches
- ❌ **No scalar plugs** — no hardcoded values in production code
- ❌ **No silent default behavior changes** — all defaults remain off

---

## 13. Recommended Next Branch

### Option A: `phase7-tax-runtime-bridge` (Recommended)
Wire `DepreciationEngine.tax_depreciation_keur` → `TaxEngine`:
- TaxEngine consumes `tax_depreciation_keur_by_period` from DepreciationEngine
- Clean integration: Depreciation → Tax → CFADS → R69
- Low risk: default-off, isolated module
- Dependency: requires canonical DepreciationEngine (✅ PR #105)

### Option B: `phase7-r99-runtime-gate`
Add `use_r99_runtime_gate: bool = False` to `ProjectInfo` and begin Phase A above:
- Refactor `DistributionAccount` to expose gate result
- Add flag propagation through waterfall
- Keep default-off, audit-only until Phase B

### Option C: `phase7-model-stack-consolidation`
Add integration tests combining SHL + SeniorDebtSizing + Depreciation:
- Validate cross-module cashflows (CFADS → senior → SHL → distribution)
- Confirm no circular dependencies
- Build consolidated fixture regression

---

## 14. R99/R102 Status Summary

```
R99/R102: BLOCKED — source ownership defined, promotion gates documented

Owner: DistributionAccount.compute_tuho_r99_input_period()
Audit: All R69, R84, R98, R99, R100, R102 rows are audit-only
Gate: DSCR lockup check owned by DistributionAccount (not SeniorDebtSizing)
SHL: Legacy receives cf_after_tax; canonical receives post_senior_cash (audit only)
Sponsor: Receives distribution_keur from WaterfallEngine (not from R99 gate)
```

**Conclusion: R99/R102 remain BLOCKED until all 6 gates in Section 10 are satisfied.**

---

*Document version: 1.0 — 2026-05-19*