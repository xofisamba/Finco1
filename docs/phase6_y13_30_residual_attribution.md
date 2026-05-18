# Phase 6 — Y13–30 R67 Residual Attribution

## Branch
`phase6-y13-30-residual-attribution-per-driver`

## Status
**Diagnostic only — no production code changes, no bridge implemented.**

---

## Context

After PRs #71 and #73:
- Years 1–12: Python R67 = 0 = Excel R67 ✅
- Years 13–30 residual:
  - Python R67: -43,512 kEUR
  - Excel R67:  -38,241 kEUR
  - Residual:   **+5,271 kEUR** (Python overpays)

---

## Attribution Method

**Annual H1+H2 basis.** Excel R43 CIT = 18% × annual (H1+H2) R41, paid in H2.
Python annual cash = H1 cash (suppressed, =0) + H2 cash (= 2 × tax_keur for flag-on).

**Sequential substitution bridge** (Python → Excel):
1. Replace Python EBITDA with Excel CF R40 → EBITDA gap
2. Replace Python book depreciation with Excel P&L R13 → Depreciation gap
3. Replace Python SHL interest with Excel P&L R27 → SHL gap
4. Replace Python senior interest with Excel P&L R24 → Senior gap
5. Apply Excel loss carryforward: Excel R41 − Excel R35 → Loss CF impact
6. CIT = 18% × net TI → compare to Python annual cash tax

**Sign convention:** positive = Python pays MORE than Excel (gap increases).

---

## Annual Attribution Table (kEUR)

| Yr | Gap (CIT) | EBITDA | Dep | SHL | Senior | Loss CF |
|----|----------:|-------:|----:|----:|-------:|--------:|
| 13 | +1,360 | +11 | +419 | −72 | −2 | +739 |
| 14 | +625 | +8 | +419 | −28 | −10 | 0 |
| 15 | +622 | −1 | +419 | −41 | 0 | 0 |
| 16 | +627 | +3 | +419 | −44 | 0 | 0 |
| 17 | +623 | −1 | +419 | −53 | 0 | 0 |
| 18 | +618 | −6 | +419 | −65 | 0 | 0 |
| 19 | +613 | −11 | +419 | 0 | 0 | 0 |
| 20 | +608 | −16 | +419 | 0 | 0 | 0 |
| 21 | −21 | −6 | −219 | 0 | 0 | 0 |
| 22 | −26 | −11 | −219 | 0 | 0 | 0 |
| 23 | −32 | −17 | −219 | 0 | 0 | 0 |
| 24 | −38 | −23 | −219 | 0 | 0 | 0 |
| 25 | −45 | −30 | −219 | 0 | 0 | 0 |
| 26 | −38 | −23 | −219 | 0 | 0 | 0 |
| 27 | −45 | −30 | −219 | 0 | 0 | 0 |
| 28 | −52 | −38 | −219 | 0 | 0 | 0 |
| 29 | −60 | −45 | −219 | 0 | 0 | 0 |
| 30 | −68 | −54 | −219 | 0 | 0 | 0 |
| **Total** | **+5,271** | **−289** | **+1,159** | **−302** | **−12** | **+739** |

**Attributed: 1,295 kEUR | Unattributed: 3,977 kEUR**

Attribution target: residual ±200 kEUR. Current result: 3,977 kEUR unattributed — **does not reconcile**.

---

## Verdict

**First-pass sequential attribution did not reconcile.**

Only +1,295 kEUR of the +5,271 kEUR Y13–30 residual is explained by the tested independent drivers. The remaining **+3,977 kEUR indicates material interaction terms or missing counterfactual mechanics.**

Attribution target ±200 kEUR NOT met. This branch is a non-reconciling first-pass diagnostic, not a completed attribution.

### Depreciation — largest identified partial driver (+1,159 kEUR)
- Years 13–20: Excel P&L R13 book depreciation ≈ 1,786 kEUR/period; Python ledger book depreciation ≈ 1,217 kEUR/period. Python has lower depreciation deductions → higher TI → Python overpays.
- Years 21–30: Excel Dep R30 = 0.00 (fiscal depreciation row); Python ledger book depreciation ≈ 1,217 kEUR/period. Python depreciation deductions continue while Excel shows zero → Python underpays slightly.

**Candidate structural difference requiring crosscheck, not final proof of accelerated depreciation.**

### SHL interest gap (−302 kEUR)
- Years 13–20: Python SHL gross-accrued (from fixture) is lower than Excel P&L R27 in early years (yr13: 1,520 vs 1,703 kEUR). Python deducts less SHL interest → higher TI → slight overpayment.
- Years 21–30: SHL fully amortized in both models → gap = 0.

### Loss carryforward (+739 kEUR, yr13 only)
- Year 13 H2: Excel R37 = +1,807 kEUR allocated loss consumption (construction-period losses). Python loss engine has no opening loss balance → Python's TI is 1,807 kEUR higher than Excel's for that period → Python overpays.
- Years 14–30: R37 = 0 (loss pool exhausted after yr13). No further loss CF impact.
- Note: Excel R36 carries a +4,106 kEUR balance from yr16 onward, but R39 = 0 (not a positive carryforward — it is an R37 allocation history accumulator, not a deductable loss).

### EBITDA gap (−289 kEUR)
- Python EBITDA vs Excel CF R40: small per-period differences (mostly ±50 kEUR range). Net −289 kEUR over 18 years. Marginal impact.

### Senior interest gap (−12 kEUR)
- Negligible. Both models converge by yr15 (senior debt fully repaid in both).

---

## Why Does the Bridge Not Reconcile?

**The sequential substitution approach does not produce additive driver impacts** because Python's `taxable_income_before_losses_audit_keur` is already a function of Python's own ATAD limitation, depreciation ledger, and interest values. Substituting Excel inputs into an already-modified Python TI creates **interaction terms** that don't cleanly separate.

The true bridge would require recomputing Python's TI with Excel's inputs in isolation — a counterfactual that the current Python tax bridge cannot produce without architectural changes.

The residual is real and significant. The attribution by inspection of source rows is insufficient.

---

## Structural Notes

### Excel Dep R30 behavior
- Years 13–20: Dep R30 ≈ 1,786 kEUR/semiannual ≈ 3,572 kEUR/yr
- Years 21–30: Dep R30 = 0.00
This suggests the Excel model uses an accelerated depreciation schedule (perhaps 20-year MACRS or similar) that fully writes off the asset before year 21. Python uses a 30-year straight-line depreciation ledger.

### Excel P&L R13 vs Dep R30
For years 13–20: P&L R13 ≈ Dep R30 (book depreciation ≈ fiscal depreciation in the Excel model). For years 21–30: both are 0 or near-zero.

### Loss carryforward pattern (R36/R37/R39)
- Excel R36 opening balance carries +4,106 kEUR from yr16 onward
- Excel R37 = 0 from yr14 onward (loss pool exhausted)
- Excel R39 = 0 from yr14 onward (formula-capped at 0 when R38 = 0)
- **Do NOT describe R39 as a positive carryforward.** R39 = 0 in all years 13–30.

---

## R99/R102 Status

**BLOCKED / audit-only.**

R99/R102 must not be promoted while the Y13–30 R67 residual remains +3,977 kEUR unattributed. This branch makes no R99/R102 runtime-source decision. No SHL FCF opt-in.

---

## Recommended Next Branches

| Priority | Branch | Goal |
|----------|--------|------|
| P1 | `phase6-tax-bridge-counterfactual-attribution` | Build diagnostic-only counterfactual recomputation using Excel inputs and Python tax mechanics to produce additive driver attribution |
| P2 | `phase6-dep-r30-excel-crosscheck` | Verify Excel Dep R30/P&L R13 behavior and whether Python ledger should align to Excel depreciation schedule |

**Recommended ordering:** If the objective is to explain the full residual, do P1 (counterfactual attribution) first. If the objective is to pursue the largest known partial driver, do P2 (dep crosscheck) first. Do not implement production bridge yet.

---

## Removed from Immediate Scope
- `phase6-loss-carryforward-source-bridge` — contingent on attribution success
- `phase6-legal-reserve-source-bridge` — confirmed not applicable
- `phase6-formula-inspection-r41-r43` — confirmed not applicable

---

## Validation
- Tests: 54/54 passed (4 suites)
- Production code: NO changes
- Default behavior: UNCHANGED
- R99/R102: no runtime impact