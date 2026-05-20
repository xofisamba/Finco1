# Phase 8: R99/R102 Pre-Promotion Design

**Branch:** `phase8-r99-r102-prepromotion-design`
**Base:** `main` (PR #119 merge, SHA `b70196f`)
**Date:** 2026-05-20
**Type:** DESIGN / SOURCE OWNERSHIP / NO RUNTIME CHANGES
**R99/R102:** BLOCKED — this document defines prerequisites, not promotion.

---

## Executive Summary

R99 and R102 are currently **audit-only fields** in `WaterfallPeriod`. This document
defines:

1. What R99 and R102 are (semantically and numerically)
2. Which module owns each row currently vs after promotion
3. What cashflow fields are allowed to change upon promotion
4. What prerequisites must be met before any R99/R102 flag is enabled
5. A gate matrix with clear ready/blocked/future-work separation

**R99/R102 remains BLOCKED after this document.**

---

## 1. What Are R99 and R102?

R99 and R102 are TUHO Excel cash-flow rows in the post-debt-service section of the
waterfall. They represent the residual cash available after senior debt service and
SHL sweep logic.

### R99 — FCF for Distribution (Equity Distribution Gate)

```
R99 = FCF available for equity distribution
    = max(0, R84_junior_balance + R98_distribution_account_topup
          - SHL_required_cash)
```

R99 is the **equity distribution gate**: if R99 > 0, equity can receive a distribution.
If R99 = 0, no equity distribution that period.

Source: `domain/distribution_account/engine.compute_tuho_r99_input_period()`
Computes: `r99_fcf_for_distribution_keur`

### R102 — FCF for SHL (SHL Sweep Gate)

```
R102 = SHL sweep amount
     = max(0, R99 - equity_distribution)
     = fcf_for_shl_keur
```

R102 is the **SHL sweep gate**: cash swept to repay SHL principal before it accrues.
If R102 > R99, the SHL is consuming more cash than available for distribution.

Source: `domain/distribution_account/engine.compute_tuho_r99_input_period()`
Computes: `r102_fcf_for_shl_keur`

Both are currently computed in `domain/distribution_account/engine.py` and exposed as
`WaterfallPeriod` attributes. They do **not** currently feed any runtime cash routing.

---

## 2. Current R99/R102 Source Ownership

```
domain/distribution_account/engine.py
    └── compute_tuho_r99_input_period()
            → produces R99InputResult(r99_fcf, r102_fcf, fcf_for_shl)

domain/waterfall/waterfall_engine.py (run_waterfall)
    └── calls compute_tuho_r99_input_period() for each period
            → writes r99_fcf_for_distribution_keur  (audit only)
            → writes r102_fcf_for_shl_keur          (audit only)

app/waterfall_core.py
    └── run_waterfall_v3_core() → no R99/R102 runtime wiring
```

**Current state:** R99/R102 are computed and stored as `WaterfallPeriod` attributes
but are **not wired** into any downstream cash router. They are pure audit fields.

---

## 3. What Triggers R99/R102 Promotion?

The Phase 8 design intent is that R99/R102 promotion means:

> R99/R102 audit values are promoted from `WaterfallPeriod` attributes to actual
> runtime inputs that affect:
> - Equity distribution amounts (→ sponsor cash)
> - SHL sweep amounts (→ SHL principal repayment timing)
> - DSCR computation (→ may use actual CFADS rather than sized CFADS)

This has downstream effects on sponsor economics, SHL balance schedule, and
potentially DSCR-driven debt sizing.

---

## 4. Design Questions — Answered

### Q1: What exactly is R99 runtime source candidate?

**R99** = `r99_fcf_for_distribution_keur` from `domain/distribution_account/engine`

The `compute_tuho_r99_input_period()` function already computes the full TUHO
Excel-style R99. The runtime source candidate is the **output of this function**
wired as input to the distribution router.

Current inputs to this function:
- `r84_fcf_junior_keur` — FCF available after senior debt service + DSRA
- `r98_distribution_account_keur` — distribution account top-up
- `shl_required_cash_keur` — SHL required cash (PIK + interest + sweep)
- `fcf_for_shl_keur` — FCF for SHL (output of function)

**Runtime promotion path:**
The distribution account engine result would need to be wired into a new
`DistributionAccount` class that routes cash to: (1) equity distributions,
(2) SHL sweep, (3) DSRA top-up.

### Q2: What exactly is R102 runtime source candidate?

**R102** = `r102_fcf_for_shl_keur` = `fcf_for_shl_keur`

R102 is the SHL sweep amount. In the TUHO Excel:
- R99 = max(0, R84 + R98 - SHL_cash)
- R102 = max(0, R99 - equity_distribution_taken)

**Runtime promotion path:**
R102 would feed the SHL sweep router: higher R102 → faster SHL repayment →
lower senior balance → different debt service schedule.

### Q3: Which module owns each row before promotion?

| Row | Module | Ownership |
|-----|--------|-----------|
| R99 | `domain/distribution_account/engine` | Audit computation only |
| R102 | `domain/distribution_account/engine` | Audit computation only |
| R98 | `domain/waterfall/waterfall_engine` | Part of waterfall cash flow |
| R84 | `domain/waterfall/waterfall_engine` | Part of waterfall cash flow |
| SHL sweep | `domain/shl/canonical_wiring` | Post-processing adapter (audit) |

### Q4: Which module owns each row after future promotion?

| Row | Module | Ownership after promotion |
|-----|--------|--------------------------|
| R99 | `domain/distribution_account/` (new `DistributionAccount` class) | **Runtime** — routes to equity |
| R102 | `domain/distribution_account/` (new `DistributionAccount` class) | **Runtime** — routes to SHL |
| R98 | `domain/distribution_account/` | Top-up input to distribution account |
| Equity distributions | `domain/distribution_account/` | Runtime output |
| SHL sweep | `domain/shl/` | Runtime input from DistributionAccount |

### Q5: Which cashflow fields are allowed to change?

**Allowed to change upon R99/R102 promotion:**
- `equity_distribution_keur` — equity cash distributions (new field)
- `shl_sweep_keur` — SHL principal sweep amount
- `shl_balance_keur` — SHL closing balance (downstream of sweep)
- `senior_balance_keur` — senior debt closing balance (indirect: if SHL repays faster, senior stays same but cash routing changes)
- `dscr_schedule` — if equity distribution reduces available FCF for DSCR

**Must remain audit-only (not runtime):**
- `r99_fcf_for_distribution_keur` — the gate itself (source of truth)
- `r102_fcf_for_shl_keur` — the SHL gate (source of truth)
- All `r*_audit` fields — audit diagnostics
- `corporate_tax_cash_keur` — owned by TaxBridge
- `depreciation_keur` — owned by canonical depreciation (post-processing)
- `tax_depreciation_audit_keur` — owned by TaxBridge fixture ledger

### Q6: Which fields must remain audit-only?

| Field | Reason |
|-------|--------|
| `r99_fcf_for_distribution_keur` | Gate computed result — not a driver |
| `r102_fcf_for_shl_keur` | Gate computed result — not a driver |
| `r67_excel_style_cash_tax_diagnostic_keur` | Tax bridge diagnostic |
| `tax_depreciation_audit_keur` | Owned by TaxBridge |
| `cit_accrual_audit_keur` | Owned by TaxBridge |
| `fcf_for_shl_keur` | Intermediate computation |

### Q7: What prerequisites must be completed before promotion?

1. **DistributionAccount class** — new module that receives R99/R102 inputs and
   routes cash to equity/SHL/DSRA with proper sequencing
2. **SHL sweep wiring** — R102 must wire into SHL sweep mechanism, not just audit
3. **SHL canonical adapter update** — current SHL canonical wiring is post-processing
   only; must be evaluated for interaction with R102 runtime sweep
4. **DSCR stability analysis** — equity distributions change DSCR denominators;
   must validate no DSCR drift
5. **Debt sizing stability** — R99/R102 promotion must not change debt sizing basis
6. **Circular dependency check** — R99/R102 affects DSCR → which affects debt sizing
   → which affects debt service → which affects R99/R102
7. **TUHO-only scope** — R99/R102 is TUHO-specific (TUHO!DS!R19 dual-DSCR);
   Oborovo does not use R99/R102

### Q8: Is canonical depreciation required to become CIT source before R99/R102 promotion?

**No — canonical depreciation is independent of R99/R102 promotion.**

Canonical depreciation affects `depreciation_keur` and `tax_depreciation_audit_keur`
(audit/post-processing fields only). R99/R102 is driven by FCF after debt service,
not by depreciation. The TaxBridge has its own depreciation ledger for CIT.

However: if a future branch makes canonical depreciation the CIT source, it must
replace the TaxBridge fixture ledger first (per §8 of depreciation doc). That work
is orthogonal to R99/R102 promotion.

### Q9: Is Macro!R50 explicit sizing CFADS required before R99/R102 promotion?

**No — but note the interaction.**

SeniorDebtSizing uses sizing CFADS to determine debt capacity. R99/R102 is the
**post-debt-service** distribution gate. They operate at different stages:

```
Sizing CFADS → Debt Sizing → Debt Service → R99/R102 → Distributions
                       ↑                          ↑
              SeniorDebtSizing              DistributionAccount
              (uses sizing CFADS)           (uses post-DS FCF)
```

Macro!R50 wiring is needed for accurate debt sizing calibration, not for R99/R102.
R99/R102 can be promoted independently of Macro!R50.

### Q10: What validation gates must pass before enabling any R99/R102 flag?

See `reports/phase8_r99_r102_prepromotion_gate_matrix.csv`.

---

## 5. DistributionAccount Ownership

`domain/distribution_account/` is a **pre-promotion stub** that currently computes
R99/R102 audit values. Upon promotion, it would become the **runtime distribution
router**.

```
domain/distribution_account/
    ├── engine.py           # compute_tuho_r99_input_period() — R99/R102 computation
    ├── result.py           # R99InputResult dataclass
    └── [NEW] distribution_account.py  # DistributionAccount class — routes cash post-DS
```

**Current ownership:** `engine.py` computes R99/R102 as audit fields.
**After promotion:** `distribution_account.py` receives post-debt-service FCF and
routes it: equity distributions → SHL sweep → DSRA top-up → residual cash.

**DistributionAccount must NOT be implemented in this branch.** This is design only.

---

## 6. TaxBridge Depreciation Ledger Independence

The TaxBridge (`use_tax_bridge_engine=True`) builds its own independent depreciation
ledger from the TUHO aggregate fixture. This is **not** affected by canonical
depreciation wiring.

| Component | Depreciation source for CIT |
|-----------|---------------------------|
| TaxBridge | TUHO aggregate fixture (own ledger) |
| Canonical Depreciation | Per-asset-class DepreciationEngine |
| R99/R102 | FCF after debt service (CIT already deducted) |

R99/R102 uses post-CIT FCF (CIT is deducted before R99 computation). Therefore:
- TaxBridge depreciation → affects CIT → affects FCF → indirectly affects R99
- Canonical depreciation → does NOT affect CIT (audit only) → does NOT affect R99

**Implication:** Even if canonical depreciation is promoted as CIT source in a
future branch, R99/R102 promotion remains a separate design decision.

---

## 7. Canonical Depreciation — Not CIT Source

`use_depreciation_canonical_engine=True`:
- ✅ Overrides `depreciation_keur` and `tax_depreciation_audit_keur` as **audit fields**
- ❌ Does **NOT** change CIT, cash tax, or distributions
- ❌ Is **NOT** the CIT depreciation source

TaxBridge owns the CIT computation path. Canonical depreciation provides an
**independent per-asset-class audit view** only.

**Future CIT promotion** (making canonical depreciation the CIT source) requires:
1. Replace the TaxBridge fixture ledger with canonical DepreciationEngine outputs
2. Validate no CIT/distribution drift
3. This is separate from R99/R102 promotion

---

## 8. SeniorDebtSizing — Proxy CFADS Limitation

`use_senior_debt_sizing_engine=True` currently:
- Attaches `_canonical_senior_debt_sizing` as **audit output**
- Uses **proxy sizing CFADS** derived from `ebitda × (1 − tax)` — not Macro!R50
- Does **NOT** override senior debt, DSCR, or distributions

**Invariant preserved:** `actual_cfads ≠ sizing_cfads` — but both currently derive
from the same EBITDA base (only labeling differs).

**Macro!R50 wiring** (future): would provide explicit hardcoded sizing CFADS per
period. This makes SeniorDebtSizing a true calibration reference (not just proxy).

**R99/R102 interaction:** SeniorDebtSizing and R99/R102 operate at different
waterfall stages and do not directly share fields. Macro!R50 wiring is not a
prerequisite for R99/R102 promotion.

---

## 9. SHL Canonical Post-Processing Adapter Behavior

`use_shl_canonical_engine=True`:
- Overrides SHL-specific fields (`total_shl_balance_keur`, `_canonical_shl_wiring`)
- Is a **post-processing adapter** — runs after waterfall, does not affect FCF
- R99/R102 operates **before** SHL sweep in the TUHO waterfall ordering

**SHL sweep vs R99 ordering (TUHO Excel):**
```
R84 (FCF after senior DS)
  → R98 (distribution account top-up)
  → R99 (equity distribution gate) ← R99/R102 computes here
  → R102 (SHL sweep = max(0, R99 - equity_distribution))
```

This means SHL sweep is **after** R99 in the cash flow sequence. SHL canonical
wiring runs after the full waterfall, so it cannot interfere with R99/R102
computation. However, if R99/R102 is promoted to runtime, the SHL sweep routing
would need to receive R102 as input.

---

## 10. R99/R102 Audit Fields vs Runtime Fields

| Field | Current state | After promotion |
|-------|--------------|-----------------|
| `r99_fcf_for_distribution_keur` | Audit (WaterfallPeriod) | Audit + distribution router input |
| `r102_fcf_for_shl_keur` | Audit (WaterfallPeriod) | Audit + SHL sweep router input |
| `fcf_for_shl_keur` | Audit (WaterfallPeriod) | Audit only |
| `r84_fcf_junior_keur` | Audit (WaterfallPeriod) | Runtime input to DistributionAccount |
| `r98_distribution_account_keur` | Audit (WaterfallPeriod) | Runtime input to DistributionAccount |
| `equity_distribution_keur` | Not present | **New runtime output** from DistributionAccount |
| `shl_sweep_keur` | Not present | **New runtime input** to SHL sweep |

**Key distinction:** R99/R102 values are **outputs** of the distribution computation,
not inputs. They are computed from R84 + R98 - SHL_required and then used as gates.
The **runtime routing** (where does the R99 cash actually go) is what needs a new
`DistributionAccount` class.

---

## 11. Sponsor/Distribution Downstream Impact

When R99/R102 is promoted to runtime, the key downstream effects are:

### Sponsor (Equity) Cash Flows
- R99 = max(0, FCF_remaining - SHL_required) → equity distribution amount
- If R99 = 0: no equity distribution that period
- If R99 > 0: equity receives distribution up to R99
- Equity IRR will change if distributions change (IRR formula: distributions/equity)

### SHL Balance Schedule
- R102 = SHL sweep amount
- Higher R102 → faster SHL principal repayment
- Faster SHL repayment → lower SHL balance → different PIK accrual
- PIK accrual affects future R99/R102 (circular dependency risk)

### DSCR Impact
- Distributions reduce cash held for DSCR denominator
- If equity takes distributions early, DSCR may be lower
- **Must validate:** no DSCR drift above ±0.05 threshold

### Circular Dependency Risk
```
R99 (equity distribution) → reduces cash → could reduce DSCR denominator
DSCR lower → could reduce debt sizing → reduces senior debt service
Senior debt service lower → more FCF available → R99 higher
```

This circular dependency must be analyzed and contained before promotion.
**Proposed mitigation:** R99 equity distributions are **subordinate** to DSCR
maintenance — distributions only paid from FCF remaining after DSCR is met.

---

## 12. TUHO vs Oborovo Scope

R99/R102 is **TUHO-specific**. It is defined in the TUHO Excel (TUHO!DS!R19
dual-DSCR structure). Oborovo does not have equivalent rows.

| Project | R99 | R102 | SHL sweep |
|---------|-----|------|-----------|
| TUHO-WIND-1 | ✅ Audit | ✅ Audit | TUHO-specific sweep cap |
| OBOROVO-SOLAR-1 | ❌ N/A | ❌ N/A | No R99 equivalent |

**Oborovo guard:** any R99/R102 runtime flag must have an Oborovo guard similar
to `use_tax_bridge_engine` guard (explicit `ValueError` if used with Oborovo).

---

## 13. Recommended Next Steps

### Immediate (future branches)

| Step | Branch | Description |
|------|--------|-------------|
| 1 | `phase8-distribution-account-design` | Design `DistributionAccount` class with full routing logic |
| 2 | `phase8-shl-sweep-wiring` | Wire R102 into SHL sweep mechanism as runtime input |
| 3 | `phase8-r99-runtime-wiring` | Wire R99 as input to `DistributionAccount.run()` |

### Prerequisites before R99/R102 runtime wiring

| Prerequisite | Status | Notes |
|-------------|--------|-------|
| DistributionAccount class designed | ❌ Not done | Design phase needed |
| SHL sweep runtime wiring | ❌ Not done | Needs R102 as input |
| DSCR stability analysis | ❌ Not done | Must validate ±0.05 threshold |
| Circular dependency analysis | ❌ Not done | Must prove convergence |
| Oborovo guard for R99/R102 | ❌ Not done | TUHO-only flag |
| TaxBridge ledger independence confirmed | ✅ Done | Documented in §6 |
| Canonical depreciation not CIT source confirmed | ✅ Done | Documented in §7 |
| Macro!R50 not required for R99/R102 confirmed | ✅ Done | Documented in §9 |

### R99/R102 remains BLOCKED

R99/R102 promotion requires:
1. A new `DistributionAccount` class that receives post-debt-service FCF and routes
   it to equity distributions, SHL sweep, and DSRA top-up
2. Runtime wiring of R99/R102 output to `DistributionAccount` input
3. SHL sweep routing update to consume R102 as runtime input
4. Full DSCR and circular-dependency validation
5. Explicit Oborovo guard for any R99/R102 flag

**This document defines the design. Promotion is a future branch.**

---

## 14. Key Definitions

| Term | Definition |
|------|------------|
| R99 | `r99_fcf_for_distribution_keur` — FCF available for equity distribution |
| R102 | `r102_fcf_for_shl_keur` — FCF remaining for SHL sweep after equity distribution |
| R84 | `r84_fcf_junior_keur` — FCF available after senior debt service |
| R98 | `r98_distribution_account_keur` — distribution account top-up amount |
| DistributionAccount | New class (not yet implemented) that routes post-DS FCF to equity/SHL/DSRA |
| SHL sweep | Payment of SHL principal from available FCF after equity distribution |
| Canonical depreciation | Post-processing adapter for `depreciation_keur` and `tax_depreciation_audit_keur` |
| Macro!R50 | TUHO Excel cell with explicit hardcoded sizing CFADS per period |
| `actual_cfads` | CFADS from full model run (CF!R69) |
| `sizing_cfads` | Sizing CFADS used for debt capacity (currently proxy; future: Macro!R50) |

---

## 15. Document History

| Date | Change |
|------|--------|
| 2026-05-20 | Initial design document — phase8-r99-r102-prepromotion-design |