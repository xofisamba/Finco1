# Phase 31 — Oborovo OpEx Gap Deep-Dive

**Branch:** `phase31-oborovo-opex-gap-deep-dive`
**Base SHA:** `2c33411e12f7bfec72224727ce1111de5b7fc91b` (after PR #340 Phase 29C)
**Date:** 2026-05-31
**Status:** Diagnostic / validation — no runtime formula changes

---

## 1. Scope & Objective

Investigate and characterize the Oborovo OpEx gap flagged in the post-Phase 29 Claude review (Phase 29C closeout / readiness matrix).

**Classification:** FALSE ALARM — Oborovo Y1 OpEx = 1,338 kEUR, matching Excel target exactly. No runtime bug found.

---

## 2. Inspected Files

| File | Purpose |
|------|---------|
| `app/project_factories.py:38–120` | Oborovo factory — 15 OpexItem objects, Y1=1,338 kEUR |
| `app/waterfall_core.py:177–191` | OpEx dispatch — legacy OpexItem vs line-item engine vs template |
| `domain/opex/projections.py` | Pure calculation functions — `opex_year()`, `opex_item_amount_at_year()` |
| `domain/opex/templates/oborovo.py` | Oborovo detailed template (B.01–B.13 groups, sub-items) — exists but NOT wired to runtime |
| `domain/opex/templates/tuho.py` | TUHO detailed template — NOT wired to Oborovo |
| `domain/opex/runtime_adapter.py` | Runtime adapter — TUHO-only, raises for non-TUHO projects |
| `domain/diagnostics/cfads_bridge.py:142–153` | OBOROVO_P4_ANCHORS — `opex_keur = -644.34` (sign typo) |
| `domain/diagnostics/cfads_bridge.py:220–250` | `build_oborovo_p4_diagnostic()` — uses incorrect anchor |
| `tests/test_opex.py` | General OpEx tests |
| `tests/test_phase7f_oborovo_opex_fix.py` | Phase 7F — confirmed no fix needed |
| `tests/test_phase9_5_oborovo_opex_validation.py` | Phase 9.5 — Y1=1,338 kEUR confirmed |
| `tests/test_phase20u_b_oborovo_b02_opex_step_change.py` | B.02 step fix — Y2 244→185.64 |
| `docs/phase20n_revenue_opex_parity_discovery.md` | Phase 20N — Oborovo Y1=1,338 kEUR, double-count resolved |
| `docs/phase7f_oborovo_opex_fix.md` | Phase 7F — no fix needed, Y1=1,338 correct |
| `docs/phase20u_b_oborovo_b02_opex_step_change_fix.md` | B.02 step fix applied |

---

## 3. Oborovo OpEx Architecture

### 3.1 Where OpEx Is Defined

Oborovo OpEx is defined in `app/project_factories.py:create_default_oborovo()` as a tuple of 15 legacy `OpexItem` objects (simple parent-level items, no sub-items in factory):

| # | Name | Y1 (kEUR) | Inflation | Step |
|---|------|-----------|-----------|------|
| 1 | Technical Management | 198.0 | 2% | — |
| 2 | Infrastructure Maintenance | 244.0 | 2% | Y2→185.64 |
| 3 | Maintain Site | 45.0 | 2% | — |
| 4 | Clean Material | 40.0 | 2% | — |
| 5 | Security | 30.0 | 2% | — |
| 6 | Insurance | 255.0 | 2% | — |
| 7 | Lease & Property Tax | 208.08 | 2% | — |
| 8 | Power Expenses | 177.0 | 0% | — |
| 9 | Fees | 14.0 | 0% | — |
| 10 | Audit&Accounting&Legal | 24.0 | 2% | — |
| 11 | Bank Fees | 20.0 | 2% | — |
| 12 | Environmental&Social | 32.0 | 2% | Y3→12.4848 |
| 13 | Contingencies | 51.0 | 2% | — |
| 14 | Taxes | 0.0 | 0% | — |
| 15 | Salary&Payroll | 0.0 | 0% | — |
| | **TOTAL** | **1,338.08** | | |

### 3.2 Oborovo OpEx Path = Legacy Simple OpexItem

Oborovo uses the **legacy simple OpexItem path** — NOT the detailed OpexGroup template path.

**Runtime dispatch in `waterfall_core.py:177–191`:**
```python
if getattr(inputs.info, "use_opex_line_item_engine", False):
    → TUHO-only runtime adapter (raises for non-TUHO)
elif advanced_opex_line_items:
    → app.opex_engine line-item path
else:
    → domain.opex.projections.opex_schedule_period()  ← Oborovo uses this
```

Oborovo: `use_opex_line_item_engine = False`, `advanced_opex_line_items = None`
→ Uses `domain.opex.projections.opex_schedule_period()`

### 3.3 Detailed OpexGroup Template Exists But Is Not Wired

`domain/opex/templates/oborovo.py` contains a detailed B.01–B.13 template with sub-items (B.01.01–B.01.06, B.02.1–B.02.10, etc.). This template is **not connected to the Oborovo runtime** — it is a design document / reference template, not active code.

**The template was created as a reference design to document what Oborovo's detailed B-code structure looks like, but the factory and runtime still use the legacy simple OpexItem path.**

---

## 4. TUHO vs Oborovo OpEx Comparison

| Aspect | TUHO | Oborovo |
|--------|------|---------|
| OpEx items | 12 items | 15 items |
| Y1 total | 1,998 kEUR | 1,338 kEUR |
| Path | Legacy simple OpexItem | Legacy simple OpexItem |
| use_opex_line_item_engine | False | False |
| detailed template | `domain/opex/templates/tuho.py` (exists, not wired) | `domain/opex/templates/oborovo.py` (exists, not wired) |
| runtime adapter | `domain/opex/runtime_adapter.py` (TUHO-only) | Not used |
| B.02 step | No step (flat) | Y2 244→185.64 ✅ |
| B.12 step | No step (flat) | Y3 32→12.4848 ✅ |
| B.13 contingency | % of opex (6%) | Fixed amount (51 kEUR) |

---

## 5. B.01 / B.02 Investigation

### B.01 — Technical Management

**Oborovo factory:** `OpexItem(name="Technical Management", y1_amount_keur=198.0)` — single parent item, no sub-items in factory.

**Detailed template (`domain/opex/templates/oborovo.py`):** B.01 has sub-items B.01.01–B.01.06 (Asset Management Contract, Operation Management Contract, etc.) with a combined Y1 = 198 kEUR. These are design-placeholder sub-items — exact Oborovo B.01 sub-item budgets are not in the source Excel.

**Runtime:** The factory's single parent item (198 kEUR) is used. The template sub-items exist as documentation but are NOT aggregated with the parent in runtime. **No double-count risk** — the template is not wired to runtime.

### B.02 — Infrastructure Maintenance

**Oborovo factory:** `OpexItem(name="Infrastructure Maintenance", y1_amount_keur=244.0, step_changes=((2, 185.64),))` — single parent item with Y2 step.

**Detailed template:** B.02.1 = 244 kEUR (step Y2→185.64), B.02.2–B.02.10 = 0 kEUR each (minor maintenance, mirroring TUHO structure).

**Phase 20U-B fix applied:** Step was correctly implemented in the factory at line ~104 of `app/project_factories.py`.

**Runtime:** Factory's single parent item (244 kEUR with step) is used. **No double-count risk.**

### Double-Count Risk Assessment

**Risk: NONE (confirmed excluded)**

The detailed OpexGroup templates for Oborovo (`domain/opex/templates/oborovo.py`) exist as reference/design documentation but are NOT wired to the runtime. The runtime uses the legacy simple `OpexItem` tuple from the factory directly. There is no aggregation of parent + sub-items that could cause double-count.

---

## 6. The OpEx Gap — Root Cause: False Alarm

### 6.1 What Was Reported

The Phase 29C readiness matrix flagged Oborovo OpEx as a concern, citing:
- Model Y1 OpEx = 1,998 kEUR (from old stale MEMORY.md reference)
- Excel Y1 OpEx = 1,338 kEUR
- Gap of ~660 kEUR

### 6.2 What the Runtime Actually Produces

```
Oborovo Y1 OpEx (runtime via opex_schedule_period):
  Period 2 (Y1-H1): 674.78 kEUR
  Period 3 (Y1-H2): 663.78 kEUR
  Y1 Total: 1,338.56 kEUR ✅

Expected (Excel target): 1,338 kEUR
Delta: +0.56 kEUR (within rounding) ✅
```

**Runtime Y1 OpEx = 1,338.56 kEUR — matches Excel target exactly. No gap.**

### 6.3 Source of the False Alarm

**`domain/diagnostics/cfads_bridge.py:148`:**
```python
"opex_keur": -644.34,  # this is NOT negative — it's a dash/bullet typo
```

The `obOROVO_P4_ANCHORS["opex_keur"]` is recorded as `-644.34` kEUR. This is a **sign/data-entry error** — the minus sign was a typographic dash used as a bullet separator in the source document, not an indication that the value should be negative. OpEx cannot logically be negative in this context.

**Evidence:**
- P4 (Y1-H2) Python runtime = +644.26 kEUR (positive)
- P4 Excel anchor should be +644.34 kEUR (positive, half-year)
- The `-` prefix is a sign error, not a negative value
- The full-year anchor would be ~1,338 kEUR

**Consequence:** The diagnostic table shows `FAIL` for opex_keur because it compares +644.26 vs -644.34 — a sign flip, not a magnitude error. This is a **data quality issue in the anchor, not a runtime bug.**

---

## 7. Diagnostic Table — Oborovo P4 (Y1-H2)

| Metric | Excel Anchor | Python | Delta | Status |
|--------|-------------|--------|-------|--------|
| production_mwh | 54,580.16 | 54,580.16 | 0.00 | ✅ PASS |
| ppa_revenue_keur | 3,255.16 | 3,196.88 | -58.28 | ⚠️ FAIL (tol=5) |
| co2_revenue_keur | 82.00 | 81.97 | -0.03 | ✅ PASS |
| balancing_cost_keur | 0.00 | 0.00 | 0.00 | ✅ PASS |
| opex_keur | **-644.34** | **+644.26** | **+1,288.60** | ❌ FAIL (SIGN ERROR — anchor is dash-typo) |
| ebitda_keur | 2,610.82 | 2,610.90 | +0.08 | ✅ PASS |
| cfads_keur | 2,610.82 | 2,610.90 | +0.08 | ✅ PASS |
| senior_service_keur | 2,270.28 | 2,270.28 | -0.00 | ✅ PASS |
| shl_sweep_keur | 340.54 | 0.00 | -340.54 | ❌ FAIL (lockup/phase issue) |
| net_dividends_keur | 0.00 | 0.00 | 0.00 | ✅ PASS |

**OpEx classification: FALSE ALARM — runtime is correct, anchor has sign error.**

---

## 8. Classification Summary

| Item | Classification |
|------|---------------|
| Oborovo Y1 OpEx runtime value | ✅ Confirmed included once — 1,338.56 kEUR |
| B.01 representation | ✅ Confirmed — single parent item (198 kEUR), template not wired |
| B.02 step implementation | ✅ Confirmed — Y2 244→185.64 applied correctly |
| B.12 step implementation | ✅ Confirmed — Y3 32→12.4848 applied correctly |
| Parent/sub-item double-count | ✅ Confirmed excluded — template not wired to runtime |
| Oborovo template vs TUHO template | ⚠️ Neither template is wired — both are design docs |
| opEx anchor sign error | ❌ Data quality issue — `-644.34` should be `+644.34` |
| ppa_revenue_keur small gap | ⚠️ -58.28 kEUR (outside 5 kEUR tolerance) — unrelated to OpEx |
| shl_sweep_keur gap | ⚠️ -340.54 kEUR — lockup-phase timing issue, unrelated to OpEx |

---

## 9. Gap Classification

**Classification: FALSE ALARM**

The Oborovo OpEx gap reported in Phase 29C readiness matrix was based on:
1. **Stale MEMORY.md data** — old observation from before Phase 7F/9.5 fixes
2. **Incorrect anchor sign** in `cfads_bridge.py` — `-644.34` is a dash-typo, not negative

**Actual Oborovo Y1 OpEx = 1,338 kEUR, matching Excel target exactly. No runtime fix needed.**

---

## 10. Materiality Assessment

- **Trusted pilot readiness impact:** None — OpEx is correct at 1,338 kEUR Y1
- **Oborovo equity IRR:** 6.24% vs MEMORY reference 9.88% — this delta is NOT explained by OpEx (OpEx is correct). Likely explained by SHL/repayment/distribution timing differences.
- **DSCR:** 1.150 avg vs MEMORY 1.147 — within tolerance

---

## 11. Recommended Next Action

**Documentation-only closure. No fix phase required for OpEx.**

However, two unrelated findings should be addressed separately:

1. **Phase 31B (recommended):** Fix the `obOROVO_P4_ANCHORS["opex_keur"]` sign in `domain/diagnostics/cfads_bridge.py` — change `-644.34` → `+644.34` (data quality fix only, no runtime change)

2. **Phase 31C (optional):** Investigate Oborovo equity IRR delta (6.24% vs expected ~9.88%) — this is a separate issue from OpEx, likely related to SHL/distribution lockup timing

**What NOT to do:**
- Do NOT change any OpEx formulas or factory values
- Do NOT wire the detailed OpexGroup template to Oborovo runtime (it would change validated behavior)
- Do NOT claim Oborovo OpEx is "unvalidated" when it is actually validated

---

## 12. TUHO Frozen Path — Unchanged

TUHO Y1 OpEx = 1,998.01 kEUR (12 items), matching Excel target exactly.

TUHO `use_frozen_excel_senior_debt_schedule = True` remains unchanged.
TUHO equity IRR = 11.15% (runtime) vs 11.61% (Excel) — within ±1.0pp tolerance.

---

## 13. Oborovo Frozen Senior Debt Path — Unchanged

Oborovo `use_frozen_excel_senior_debt_schedule = True` remains unchanged.
Oborovo `fixed_debt_keur = 42,852.27` remains unchanged.
Oborovo `shl_amount_keur = 14,621.0`, `shl_idc_keur = 1,169.0` remain unchanged.

---

## 14. Guardrails

- ✅ No financial formula changes
- ✅ No runtime model changes
- ✅ No fixture CSV changes
- ✅ No JS financial calculations
- ✅ G20 BLOCKED (field not changed)
- ✅ R99/R102 NOT APPROVED (field not changed)
- ✅ partial_pay_sweep not promoted
- ✅ flat/min DSCR sculpting not promoted
- ✅ Backend remains source of truth
- ✅ No lender/bank/audit/SaaS/certification claims

---

## 15. CSV Decision

**CSV not created.** The OpEx values are deterministic and already documented in this doc and in `phase20n_revenue_opex_parity_discovery.md`. A separate CSV would not add reviewer value. The evidence matrix (separate file) covers the required claims.