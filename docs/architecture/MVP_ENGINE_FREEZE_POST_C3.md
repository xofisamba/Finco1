# MVP Core Financial Engine Freeze — Post-C3

**Status: MVP_ENGINE_FREEZE_CORRECTION_B_READY_FOR_INDEPENDENT_REVIEW**

## Baseline

| Item | Value |
|---|---|
| Main baseline SHA | `ba965f94a3f1bd49f902f3f4cca9d1e09a6ca121` |
| Phase C3 PR | #964 — MERGED 2026-09-06T04:53:12Z |
| Phase C3 Correction | N (G2C trapped-cash roll-forward; C3 as pure consumer) |
| Freeze branch | `mvp-final-engine-freeze-post-c3` |
| Post-merge CI | 5/5 workflows SUCCESS on `ba965f94` |

---

## Production Entry Point

All four canonical projects run through a single, identical path:

```python
from app.services.production_financial_authority import run_clean_production
from financial_engine.financial_statements import assemble_decision_complete_financial_statements

run = run_clean_production(project_inputs, project_type="<Solar|Wind|Oborovo|TUHO>")
fs  = assemble_decision_complete_financial_statements(run.g2c_result, project_inputs)
```

Zero legacy waterfall execution. Zero `WaterfallRunner` production calls. Proven by
`TestFreezeS2_SingleProductionEngine` in `test_mvp_final_engine_freeze_post_c3.py`.

---

## Four-Project Scalar Fingerprint

Captured at main SHA `ba965f94`. Values are regression evidence, not source-fitted.

### Solar (Generic, Spain, 33 MW)

| Metric | Value |
|---|---|
| Operating periods | 40 |
| Total periods (incl. construction) | 42 |
| Revenue | 94,414.549 kEUR |
| OPEX | 9,233.001 kEUR |
| EBITDA | 85,181.548 kEUR |
| EBIT | 59,114.882 kEUR |
| Book depreciation | 26,066.667 kEUR |
| Ending accumulated book dep | 26,066.667 kEUR |
| Ending NFA | 6,933.333 kEUR |
| CIT accrual | 9,612.661 kEUR |
| Corporate cash tax | 9,612.661 kEUR |
| Ending tax loss | 0.000 kEUR |
| Financing income | **0.000 kEUR** (ZERO_BY_POLICY) |
| Senior commitment | 24,750.000 kEUR |
| Binding constraint | GEARING |
| Senior terminal status | REPAID |
| Min DSCR | 1.102902 |
| SHL opening operating balance | 7,750.000 kEUR |
| SHL construction PIK | 0.000 kEUR |
| SHL gross interest (operating) | 8,825.775 kEUR |
| SHL cash interest (operating) | 8,536.159 kEUR |
| SHL PIK (operating) | 289.616 kEUR |
| SHL principal paid | 1,365.745 kEUR |
| Terminal SHL balance | 6,673.871 kEUR |
| SHL terminal status | UNPAID_AT_CONTRACTUAL_MATURITY |
| Ending DSRA | 0.000 kEUR |
| Ending Distribution Account | 0.000 kEUR |
| Ending unrestricted cash | 25,362.696 kEUR |
| Ending share capital | 500.000 kEUR |
| Ending retained earnings | 25,122.158 kEUR |
| Ending legal reserve | **0.000 kEUR** (ZERO_BY_POLICY) |
| Total gross dividends | 5,002.163 kEUR |
| Project XIRR | 7.593% |
| BS max residual | 8.30e-12 kEUR |
| BS periods balanced (≤1e-4) | 42/42 |

### Wind (Generic, Germany, 80 MW)

| Metric | Value |
|---|---|
| Operating periods | 50 |
| Total periods | 53 |
| Revenue | 213,093.254 kEUR |
| OPEX | 17,617.771 kEUR |
| EBITDA | 195,475.482 kEUR |
| EBIT | 153,972.314 kEUR |
| Book depreciation | 41,503.168 kEUR |
| Ending accumulated book dep | 41,503.168 kEUR |
| Ending NFA | 1,496.832 kEUR |
| CIT accrual | 32,612.879 kEUR |
| Corporate cash tax | 32,612.879 kEUR |
| Ending tax loss | 0.000 kEUR |
| Financing income | **0.000 kEUR** (ZERO_BY_POLICY) |
| Senior commitment | 32,250.000 kEUR |
| Binding constraint | GEARING |
| Senior terminal status | REPAID |
| Min DSCR | 1.276688 |
| SHL opening operating balance | 10,250.000 kEUR |
| SHL construction PIK | 0.000 kEUR |
| SHL gross interest (operating) | 9,433.370 kEUR |
| SHL cash interest (operating) | 9,433.370 kEUR |
| SHL PIK (operating) | 0.000 kEUR |
| SHL principal paid | 2,002.917 kEUR |
| Terminal SHL balance | 8,247.083 kEUR |
| SHL terminal status | UNPAID_AT_CONTRACTUAL_MATURITY |
| Ending DSRA | 0.000 kEUR |
| Ending Distribution Account | 0.000 kEUR |
| Ending unrestricted cash | 98,269.006 kEUR |
| Ending share capital | 500.000 kEUR |
| Ending retained earnings | 91,018.755 kEUR |
| Ending legal reserve | **0.000 kEUR** (ZERO_BY_POLICY) |
| Total gross dividends | 10,506.513 kEUR |
| Project XIRR | 11.366% |
| BS max residual | 4.50e-11 kEUR |
| BS periods balanced (≤1e-4) | 53/53 |

### Oborovo (Real, Bosnia, 61.5 MW Solar)

| Metric | Value |
|---|---|
| Operating periods | 60 |
| Total periods | 61 |
| Revenue | 237,686.922 kEUR |
| OPEX | 55,782.951 kEUR |
| EBITDA | 181,903.972 kEUR |
| EBIT | 123,930.929 kEUR |
| Book depreciation | 57,973.042 kEUR |
| Ending accumulated book dep | 57,973.042 kEUR |
| Ending NFA | 0.000 kEUR |
| CIT accrual | 10,445.005 kEUR |
| Corporate cash tax | 10,445.005 kEUR |
| Ending tax loss | 0.000 kEUR |
| Financing income | 71.003 kEUR (U2 schedule authority) |
| Senior commitment | 42,852.303 kEUR |
| Binding constraint | DSCR |
| Senior terminal status | REPAID |
| Min DSCR | 1.068192 |
| SHL opening operating balance | 15,790.399 kEUR |
| SHL construction PIK | 1,169.659 kEUR |
| SHL gross interest (operating) | 31,000.373 kEUR |
| SHL cash interest (operating) | 20,039.148 kEUR |
| SHL PIK (operating) | 10,961.225 kEUR |
| SHL principal paid | 26,751.624 kEUR |
| Terminal SHL balance | 0.000 kEUR |
| SHL terminal status | REPAID |
| Ending DSRA | 0.000 kEUR |
| Ending Distribution Account | 0.000 kEUR |
| Ending unrestricted cash | 550.000 kEUR |
| Ending share capital | 500.000 kEUR |
| Ending retained earnings | 0.000 kEUR |
| Ending legal reserve | 50.000 kEUR |
| Total gross dividends | 61,753.806 kEUR |
| Project XIRR | 8.512% |
| BS max residual | 1.67e-09 kEUR |
| BS periods balanced (≤1e-4) | 61/61 |

### TUHO Wind1 (Real, Bosnia, 102 MW Wind)

| Metric | Value |
|---|---|
| Operating periods | 60 |
| Total periods | 61 |
| Revenue | 423,762.002 kEUR |
| OPEX | 85,403.451 kEUR |
| EBITDA | 338,358.551 kEUR |
| EBIT | 265,327.521 kEUR |
| Book depreciation | 73,031.030 kEUR |
| Ending accumulated book dep | 73,031.030 kEUR |
| Ending NFA | 0.000 kEUR |
| CIT accrual | 38,937.931 kEUR |
| Corporate cash tax | 38,937.931 kEUR |
| Ending tax loss | 0.000 kEUR |
| Financing income | 124.317 kEUR (U2 schedule authority) |
| Senior commitment | 43,789.921 kEUR |
| Binding constraint | DSCR |
| Senior terminal status | REPAID |
| Min DSCR | 1.398270 |
| SHL opening operating balance | 32,261.528 kEUR |
| SHL construction PIK | 3,520.420 kEUR |
| SHL gross interest (operating) | 48,654.530 kEUR |
| SHL cash interest (operating) | 38,253.888 kEUR |
| SHL PIK (operating) | 10,400.642 kEUR |
| SHL principal paid | 42,662.171 kEUR |
| Terminal SHL balance | 0.000 kEUR |
| SHL terminal status | REPAID |
| Ending DSRA | 0.000 kEUR |
| Ending Distribution Account | 0.000 kEUR |
| Ending unrestricted cash | 550.000 kEUR |
| Ending share capital | 500.000 kEUR |
| Ending retained earnings | 0.000 kEUR |
| Ending legal reserve | 50.000 kEUR |
| Total gross dividends | 151,792.901 kEUR |
| Project XIRR | 9.478% |
| BS max residual | 8.16e-09 kEUR |
| BS periods balanced (≤1e-4) | 61/61 |

---

## Period-Vector Digest Methodology

Each vector digest is SHA-256[:24] of the JSON-serialized list of
values rounded to 6 decimal places:

```python
import hashlib, json

def vec_digest(v: list) -> str:
    rounded = [round(float(x), 6) if x is not None else None for x in v]
    return hashlib.sha256(json.dumps(rounded).encode()).hexdigest()[:24]
```

Digests cover operating periods only (construction periods excluded),
unless the schedule is naturally continuous (e.g. BS, SHL, Senior, CFADS).

Full digest tables embedded in `_DIGESTS` dict in
`tests/test_mvp_final_engine_freeze_post_c3.py`.

**Digest count per project (Correction B): 25**
- IS/Tax/BS/SHL/CFADS/NFA/RE: 19 (original)
- Senior schedule (opening, interest, principal, debt_service, closing): +5
- Canonical Base CFADS: +1

Total: 25 authoritative vector digests per project × 4 projects = 100 digests.

---

## Accounting Identity Proof

Verified for every period of every project (`TestFreezeS7_AccountingIdentities`):

**P&L:**
```
Revenue − OPEX = EBITDA
EBITDA − BookDep = EBIT
NetFinancial = FI − SeniorInterest − SHLGrossInterest
EBIT + NetFinancial = EBT
EBT − CITAccrual = NI
SHLGross = SHLCashInterest + SHLPik
```

**Retained Earnings roll-forward (operating periods):**
```
RE_close = RE_open + NI − GrossDividend − LRTransfer
```

**Legal Reserve continuity:**
```
LR_close ≥ LR_open  (for all periods)
```

**UC roll-forward:**
```
UC_close = UC_open + UCChange  (every period)
UC_open[t] = UC_close[t-1]    (cross-period continuity)
```

**UC identity for Generic Solar/Wind:**
```
unallocated = shl_cash_input − shl_cash_interest − shl_principal − gross_dividend
UCChange = max(0, unallocated)
```

**Accumulated book depreciation:**
```
AccumDep_terminal = Σ(BookDep over all periods)
```

---

## BS Residuals

| Project | All balanced (≤1e-4) | Max residual | Status |
|---|---|---|---|
| Solar | 42/42 | 8.30e-12 kEUR | ✓ |
| Wind | 53/53 | 4.50e-11 kEUR | ✓ |
| Oborovo | 61/61 | 1.67e-09 kEUR | ✓ |
| TUHO | 61/61 | 8.16e-09 kEUR | ✓ |

All residuals are floating-point rounding noise, not economic gaps.
Tolerance limit: 1e-4 kEUR (0.10 EUR). All projects well within.

---

## Deterministic Rerun Proof

Two independent runs of each project produce:
- Identical scalar totals (rel tolerance 1e-12)
- Identical period-vector digests (exact match)

Proven by `TestFreezeS10_Determinism`. No mutable state leakage between runs.

---

## C3 Statement Completeness Matrix

| Statement | Solar | Wind | Oborovo | TUHO |
|---|---|---|---|---|
| P&L (income_statement_status) | OK | OK | OK | OK |
| Tax Bridge (tax_bridge_status) | OK | OK | OK | OK |
| PF Cash (cash_flow_status) | OK | OK | OK | OK |
| Fixed Assets (fixed_asset_status) | OK | OK | OK | OK |
| UC (unrestricted_cash_status) | OK | OK | OK | OK |
| Balance Sheet (balance_sheet_status) | OK | OK | OK | OK |
| RE (retained_earnings_status) | OK | OK | OK | OK |

---

## Known Non-Blocking Parity Exceptions

These are permanent classification decisions, not engine defects.

### OBOROVO_SOURCE_RE_LINEAGE_PARITY_BLOCKED_BY_DISTRIBUTION_CASH_TAX_TIMING_ARCHITECTURE

Oborovo's source workbook computes RE using a different distribution/cash-tax
timing architecture. The Finco clean canonical engine produces correct RE under
its own consistent framework. No Finco RE recalibration is required or permitted.

### TUHO_SOURCE_SHL_PARITY_BLOCKED_BY_CANONICAL_G2A_FINANCING_STACK_AUTHORITY

TUHO's source SHL balance differs from Finco's engine-derived SHL because the
G2A financing stack uses canonical sizing methodology (not source-workbook backward
fitting). The Finco SHL balance is internally consistent with all other
financing outputs. No SHL recalibration is required or permitted.

---

## v1.1 / KUPI Backlog

Items deferred to v1.1 (no MVP blocker):

| Gap ID | Classification |
|---|---|
| KUPI_SHL_CONSTRUCTION_COMPOUNDING_GAP | CURRENT_FINCO_CAPABILITY_GAP |
| GENERIC_DYNAMIC_REVENUE_RATIO_DSCR_FORMULA_NOT_IMPLEMENTED | CURRENT_FINCO_CAPABILITY_GAP |
| KUPI_VAT_FACILITY | UNSUPPORTED_INSTITUTIONAL_FEATURE |
| KUPI_SPONSOR_CONTRIBUTION_TIMING_POLICY_GAP | DEFINITION_OR_TIMING_DIFFERENCE |
| KUPI_TAX_WORKBOOK_COMPATIBILITY_GAP | CLEAN_POLICY_VS_WORKBOOK_COMPATIBILITY |
| KUPI_SENIOR_GAP_RESIDUAL | OPEN_SMALL_RESIDUAL (+498.819 kEUR / ~0.34%) |
| G2C_RESERVE_GATE_NOT_CAUSALLY_CLOSED | Three sub-causes (see G3 freeze doc) |

---

## UI Handoff — Safe Outputs

The following clean outputs are authoritative for UI consumption.
The UI must NOT reconstruct any financial logic; it must consume these outputs as-is.

| Output Category | Status | Source |
|---|---|---|
| Project metadata / inputs | ✓ SAFE | `project_inputs` |
| P&L (income_statement_periods) | ✓ SAFE | `fs.income_statement_periods` |
| Tax Bridge (tax_bridge_periods) | ✓ SAFE | `fs.tax_bridge_periods` |
| PF Cash Waterfall (pf_cash_waterfall_periods) | ✓ SAFE | `fs.pf_cash_waterfall_periods` |
| Balance Sheet (balance_sheet_periods) | ✓ SAFE | `fs.balance_sheet_periods` |
| Fixed Assets (fixed_asset_periods) | ✓ SAFE | `fs.fixed_asset_periods` |
| Senior Debt schedule | ✓ SAFE | `g2c.waterfall_periods` (senior_* fields) |
| SHL schedule | ✓ SAFE | `g2c.waterfall_periods` (shl_* fields) |
| DSRA / DA / UC schedules | ✓ SAFE | `g2c.waterfall_periods` |
| Return summary (XIRR, MOIC) | ✓ SAFE | `g2c.return_summary` |
| NPV / LLCR / PLCR | ✓ SAFE | `g2c.return_summary` |
| Distributions schedule | ✓ SAFE | `g2c.waterfall_periods.legal_equity_distribution_keur` |
| Sensitivity inputs/outputs | ✓ SAFE | Re-run `run_clean_production` with mutated inputs |

---

## Freeze Governance

- `DO NOT TOUCH #938` — KUPI G3B draft PR; independent validation track.
- No balancing plug, no name dispatch, no source fitting, no hard-coded residual.
- No EBITDA augmentation, no post-convergence financial mutation.
- No C3 import into upstream; no duplicate RE/LR engine.
- FI = ZERO_BY_POLICY for Solar/Wind.
- DA and UC remain distinct accounting concepts.
- Fail-closed SHL terms unchanged: `bullet_unpaid_active` gate not touched.

---

**MVP_ENGINE_FREEZE_CORRECTION_B_READY_FOR_INDEPENDENT_REVIEW**

Freeze evidence file: `tests/test_mvp_final_engine_freeze_post_c3.py`
