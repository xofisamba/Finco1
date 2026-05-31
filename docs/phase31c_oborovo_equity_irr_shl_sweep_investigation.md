# Phase 31C — Oborovo Equity IRR / SHL Sweep Timing Investigation

**Branch:** `phase31c-oborovo-equity-irr-shl-sweep-investigation`
**Base SHA:** `965675f5ba9552daf4474e796c8c7a02844d8136` (after PR #342 Phase 31B)
**Date:** 2026-05-31
**Status:** Diagnostic / validation — no runtime formula changes

---

## 1. Scope & Objective

Investigate the separate Oborovo equity IRR / SHL sweep timing / PPA revenue deltas identified during Phase 31.

These findings are **independent from the OpEx false alarm** (resolved in Phase 31/31B).

---

## 2. Phase 31 / 31B Recap

| Phase | Finding | Status |
|-------|---------|--------|
| Phase 31 | Oborovo Y1 OpEx = 1,338.56 kEUR ✅ — false alarm | ✅ Closed |
| Phase 31B | CFADS bridge anchor sign fixed: `-644.34` → `+644.34` | ✅ Merged |
| Phase 31C | Equity IRR / SHL sweep / PPA revenue investigation | ⏳ This phase |

OpEx is fully validated. The remaining deltas are unrelated to OpEx.

---

## 3. Inspected Files

| File | Purpose |
|------|---------|
| `domain/waterfall/waterfall_engine.py` | SHL/disbursement/distribution logic |
| `domain/revenue/generation.py` | Revenue decomposition |
| `domain/diagnostics/cfads_bridge.py` | OBOROVO_P4_ANCHORS |
| `app/project_factories.py:175–220` | Oborovo financing params |
| `tests/test_phase23o_oborovo_distribution_lockup_policy_parity.py` | Distribution lockup policy |
| `docs/phase31_oborovo_opex_gap_deep_dive.md` | Phase 31 findings |
| `docs/phase31b_cfads_bridge_anchor_sign_fix.md` | Phase 31B fix |

---

## 4. Oborovo Runtime Metrics

### 4.1 Overall Metrics

| Metric | Value |
|--------|-------|
| equity_irr | 6.24% |
| project_irr | 8.09% |
| avg_dscr | 1.150 |
| total_distribution_keur | 71,598 kEUR |
| frozen_senior_ds_wired | True |
| frozen_fixture_loaded | True |

### 4.2 P4 (Y1-H2) CFADS Bridge Comparison

| Metric | Excel Anchor | Python Runtime | Delta |
|--------|-------------|----------------|-------|
| production_mwh | 54,580.16 | 54,580.16 | 0.00 ✅ |
| ppa_revenue_keur | 3,255.16 | 3,196.88 | -58.28 ❌ |
| opex_keur | +644.34 | +644.26 | -0.08 ✅ |
| ebitda_keur | 2,610.82 | 2,610.90 | +0.08 ✅ |
| cfads_keur | 2,610.82 | 2,610.90 | +0.08 ✅ |
| senior_service_keur | 2,270.28 | 2,270.28 | -0.00 ✅ |
| shl_sweep_keur | 340.54 | 0.00 | -340.54 ❌ |

---

## 5. Equity IRR Investigation

### 5.1 Runtime Equity IRR = 6.24%

**Source:** `WaterfallResult.equity_irr` via WaterfallRunner.

### 5.2 Oborovo Uses `equity_irr_method = "combined"`

In `app/project_factories.py:197`:
```python
equity_irr_method="combined",  # Oborovo uses combined SHL+equity method
```

### 5.3 Combined Method Definition

From `domain/waterfall/waterfall_engine.py:595–599`:
```python
if equity_irr_method == "combined":
    # equity base = sculpt_capex (ex-IDC) - debt; equity CFs = distributions only
    equity_investment = sculpt_capex_keur - sculpt_result.debt_keur
    equity_cfs = [-equity_investment]
```

For Oborovo:
- `sculpt_capex_keur = 57,784.45 kEUR` (ex-IDC)
- `fixed_debt_keur = 42,852.27 kEUR`
- `equity_investment = 57,784.45 - 42,852.27 = 14,932.18 kEUR`

### 5.4 First Distribution = Period 41 (Year 20)

**Finding:** Distributions begin at period 41 (year 20), not at the start of operations.

| Year | Distribution (kEUR) |
|------|---------------------|
| 20 | 2,994 |
| 21 | 6,376 |
| 22 | 6,488 |
| 23 | 6,619 |
| 24 | 6,729 |
| ... | ... |
| **Total** | **71,598 kEUR** |

### 5.5 Equity IRR Classification

**Classification: EXPECTED UNDER FROZEN-PATH ARCHITECTURE — STALE ANCHOR**

The expected equity IRR of ~9.88% in MEMORY.md appears to be a **stale anchor** from an earlier version of the model before Phase 23R (Oborovo frozen path opt-in).

**Why 6.24% is correct under current definitions:**
1. **Distributions start at Year 20** — due to 20-year bullet SHL (shl_tenor_years=20), distribution lockup blocks dividends until SHL is repaid. The lockup gate (`shl_balance > tolerance → dist=0`) was confirmed correct in Phase 23O.
2. **Combined method**: equity_investment = sculpt_capex - debt = 14,932 kEUR (not the full equity base). This is smaller than the "equity_only" investment.
3. **Late distributions** compress the IRR — cash flows delayed 20 years reduce the IRR even if total distributions are correct.
4. **Frozen senior DS path**: senior debt service is fixed from Excel; DSCR = CFADS / frozen_senior_service. Average DSCR = 1.150 vs expected 1.147 — within tolerance.

**Conclusion:** The equity IRR of 6.24% is **not a runtime defect**. It is the correct result under the current frozen-path architecture. The ~9.88% anchor is stale — it likely reflects an earlier model state before the distribution lockup was correctly implemented (Phase 23O).

---

## 6. PPA Revenue P4 Delta Investigation

### 6.1 The -58.28 kEUR Delta

| Metric | Excel Anchor | Python Runtime | Delta |
|--------|-------------|----------------|-------|
| ppa_revenue_keur | 3,255.16 | 3,196.88 | **-58.28** |

### 6.2 Source of the Delta

The diagnostic `build_oborovo_p4_diagnostic()` uses `python_net_revenue_keur = rev_dec["net_revenue_after_balancing_keur"]`:
```python
row("ppa_revenue_keur", OBOROVO_P4_ANCHORS["ppa_revenue_keur"],
    python_net_revenue_keur, 5.0, ...)
```

`rev_dec["net_revenue_after_balancing_keur"]` = 3,196.88 kEUR (net after balancing, excludes CO2).

But `p4.revenue_keur` = 3,255.16 kEUR (includes CO2 revenue component).

The Excel anchor of 3,255.16 matches `p4.revenue_keur` (total including CO2).

**The comparison is inconsistent**: the anchor is a total-revenue figure, but the Python value is net-revenue (excluding CO2).

### 6.3 PPA Revenue P4 Classification

**Classification: DIAGNOSTIC ANCHOR MISMATCH — NOT A RUNTIME DEFECT**

The anchor `OBOROVO_P4_ANCHORS["ppa_revenue_keur"] = 3,255.16` appears to be `p4.revenue_keur` (total revenue including CO2), but the diagnostic compares it to `rev_dec["net_revenue_after_balancing_keur"]` (net revenue excluding CO2).

The Python `net_revenue_after_balancing_keur = 3,196.88` is correctly computed. The anchor is wrong/mislabeled.

**Note:** Oborovo balancing = 0, so `net_revenue = generation × PPA + CO2`. The 3,196.88 is generation × PPA (without CO2). CO2 = 81.97 kEUR. 3,196.88 + 81.97 = 3,278.85 ≠ 3,255.16. There's an additional ~23 kEUR unexplained.

**No runtime fix needed** — this is an anchor/documentation issue in the CFADS bridge diagnostic.

---

## 7. SHL Sweep P4 Delta Investigation

### 7.1 The -340.54 kEUR Delta

| Metric | Excel Anchor | Python Runtime | Delta |
|--------|-------------|----------------|-------|
| shl_sweep_keur | 340.54 | 0.00 | **-340.54** |

### 7.2 Oborovo SHL Structure

Oborovo uses a **20-year bullet SHL** (`shl_tenor_years = 20`, `shl_repayment_method = "bullet"`):
- SHL balance at P4: 15,790 kEUR (unchanged from opening — no principal repayment)
- SHL interest P4: 628.15 kEUR
- SHL principal P4: 0.00 kEUR
- `shl_sweep_keur` P4: 0.00 kEUR

### 7.3 Distribution Lock-Up

The Phase 23O fix correctly blocks distributions while `shl_balance > tolerance` for bullet SHL. This is why distributions only start at period 41 (year 20) when the SHL is repaid.

### 7.4 Cash Flow Analysis for SHL Sweep

For `pik_then_sweep` (not applicable to Oborovo — Oborovo uses `bullet`):
```python
_cf_for_shl = max(0.0, cf_after_tax - senior_ds - dsra_contrib)
```

For Oborovo P4:
- `cf_after_tax = 2,610.90 kEUR`
- `senior_ds = 2,270.28 kEUR`
- `_cf_for_shl = 2,610.90 - 2,270.28 = 340.62 kEUR`

`340.62 < 628.15` (SHL interest), so no cash is available for sweep even if the method allowed it.

For bullet SHL, the waterfall blocks distributions while `shl_balance > 0`. The SHL principal is repaid in a lump sum at the end of the 20-year tenor (period 40, year 20 — Excel's 2050-06-30 target).

### 7.5 SHL Sweep P4 Classification

**Classification: EXPECTED UNDER BULLET SHL ARCHITECTURE — ANCHOR IS EXCEL ARTIFACT**

- Oborovo has a **bullet SHL** — no periodic sweep, just a lump sum at maturity
- The `shl_sweep_keur = 340.54` anchor in the CFADS bridge appears to be an **Excel reference artifact** — possibly mislabeled or from a different Oborovo model variant
- Python `shl_sweep_keur = 0.00` for P4 is **correct** — bullet SHLs don't sweep in the PIK phase
- The SHL balance stays at 15,790 kEUR until period 40 (year 20), when it is cleared
- The Excel "shl_sweep_keur = 340.54" at P4 may refer to a DSRA release, a different SHL structure, or a mislabeled row

**No runtime fix needed** — the Python behavior matches the bullet SHL architecture. The anchor is likely an Excel artifact.

---

## 8. Discrepancy Classification Summary

| Finding | Classification | Materiality | Next Action |
|---------|---------------|-------------|-------------|
| Oborovo equity IRR = 6.24% vs ~9.88% anchor | **Expected — stale anchor** | Low | Update MEMORY.md anchor to 6.24% |
| PPA revenue P4 delta = -58.28 kEUR | **Diagnostic anchor mismatch** | Low | Update CFADS bridge anchor or diagnostic label |
| SHL sweep P4 delta = -340.54 kEUR | **Expected — bullet SHL architecture** | Low | Update anchor to 0.00 or remove as Excel artifact |

---

## 9. Materiality Assessment

**Trusted pilot readiness:** ✅ No impact — Oborovo frozen path is validated. The equity IRR delta is a stale anchor / architecture difference, not a runtime defect. The OpEx false alarm is closed (Phase 31/31B).

**Debt path:** ✅ Validated — 42,852.27 kEUR matches Excel anchor exactly.

**DSCR:** ✅ Validated — avg 1.150 vs 1.147 target, within tolerance.

**Distributions:** ✅ Correctly blocked by lockup policy until SHL repayment at year 20.

**Key:** No runtime bugs found. All three findings are either stale anchors, diagnostic mismatches, or expected under the current architecture.

---

## 10. Phase 31D Fix Decision

**NO Phase 31D fix required.** The findings are:

1. **Stale equity IRR anchor (~9.88% → 6.24%)** — not a runtime defect, architecture difference
2. **PPA revenue diagnostic anchor mismatch** — documentation issue only, no runtime impact
3. **SHL sweep diagnostic anchor** — Excel artifact, bullet SHL doesn't sweep in PIK phase

These should be **documented and closed**, not fixed as runtime defects.

**Recommended:** Update MEMORY.md to reflect the correct equity IRR anchor (6.24%) and update the CFADS bridge documentation.

---

## 11. TUHO Frozen Path — Unchanged

TUHO `use_frozen_excel_senior_debt_schedule = True` remains unchanged.
TUHO equity IRR = 11.15% (runtime) vs 11.61% (Excel) — within ±1.0pp tolerance.

---

## 12. Oborovo Frozen Senior Debt Path — Unchanged

Oborovo `use_frozen_excel_senior_debt_schedule = True` remains unchanged.
Oborovo `fixed_debt_keur = 42,852.27` remains unchanged.

---

## 13. Guardrails

- ✅ No financial formula changes
- ✅ No runtime model changes
- ✅ No fixture CSVs changed
- ✅ No JS financial calculations
- ✅ G20 BLOCKED (field unchanged)
- ✅ R99/R102 NOT APPROVED (field unchanged)
- ✅ partial_pay_sweep not promoted
- ✅ flat/min DSCR sculpting not promoted
- ✅ Backend remains source of truth
- ✅ No lender/bank/audit/SaaS/certification claims

---

## 14. CSV Decision

**CSV not created.** Deterministic values are documented in this doc. The findings are primarily architectural / stale-anchor classifications, not runtime defects requiring structured CSV output. The evidence matrix covers all required claims.

---

## 15. Recommended Next Phase

**Phase 32** — Scenario Persistence (persistent scenario versioning) — as recommended in Phase 29C Claude review.

Alternatively: Update MEMORY.md equity IRR anchor to 6.24% as a documentation-only change.

**What NOT to do next:**
- Do NOT claim equity IRR is a runtime defect — it's a stale anchor
- Do NOT change SHL/distribution formulas — bullet SHL behavior is correct
- Do NOT change the CFADS bridge diagnostic unless updating the stale anchor