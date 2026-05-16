# Phase 7J Senior Debt Opening Balance Policy

## Purpose

This note documents the evidence for how the TUHO and Oborovo Excel workbooks treat senior debt principal, senior IDC, and senior commitment fees at COD / first operating period. It is a forensic policy document only. It does not change runtime behavior.

Current Python behavior uses the fixed senior debt principal amount as the operating senior opening balance. Phase 7J construction diagnostics separately expose computed senior IDC and senior opening balances for audit, but do not replace runtime debt balances.

## Decision Summary

Recommendation: **A. Keep runtime fixed senior debt as principal-only.**

The inspected Excel debt schedules show that the operating senior debt balance opens with the senior facility / principal draw only:

- TUHO: first operating beginning senior debt balance is approximately `43,358.531` kEUR.
- Oborovo: first operating beginning senior debt balance is approximately `42,852.279` kEUR.

Senior IDC and commitment fees are calculated in the IDC sheet and linked into CapEx rows. They are not shown as capitalized additions to the operating senior debt opening balance in the inspected DS schedules.

The earlier TUHO review target of `45,878.837` kEUR remains unresolved. It is not supported by the inspected workbook cells and is not equal to principal + IDC or principal + IDC + commitment fee.

## TUHO Evidence

Source workbook: `20260330_TUHO_BP.xlsm`

| Question | Evidence | Value / Formula | Interpretation |
|---|---:|---|---|
| Senior principal / facility amount | `Inputs!D175` | `=DS!D48`, value `43,358.531` kEUR | Input senior debt references the DS maximum funding row. |
| Senior principal / facility amount | `Inputs!D178` | `=DS!$D$44`, value `43,358.531` kEUR | Separate input reference also points to senior debt schedule. |
| Construction senior debt source cap | `IDC!D40` | `=MAX(G40:AJ40)`, value `43,359.274` kEUR | Construction diagnostic source cap matches runtime fixed debt within rounding. |
| Senior debt funding in construction/pre-op column | `DS!G48` | `43,358.531` kEUR | Debt schedule funding equals principal only. |
| Senior debt end of construction balance | `DS!G53` | `43,358.531` kEUR | Closing balance after construction/pre-op column equals principal only. |
| First operating senior beginning balance | `DS!H47` | `43,358.531` kEUR | Operating debt schedule opens at principal only. |
| First operating senior principal repayment | `DS!H49` | `819.279` kEUR | Principal repayment begins from principal-only opening balance. |
| First operating senior net interest | `DS!H50` | `1,297.082` kEUR | Operating interest is computed after COD in DS schedule. |
| First operating senior closing balance | `DS!H53` | `42,539.252` kEUR | Closing balance equals opening less principal repayment. |
| Senior IDC | `IDC!D57` | `=Macro!H13`, value `1,519.564` kEUR | Senior IDC is calculated outside the operating DS principal balance. |
| Senior commitment fee | `IDC!D58` | `=Macro!H14`, value `166.718` kEUR | Commitment fee is calculated separately from debt schedule opening balance. |
| Senior IDC linked to CapEx | `CapEx!C110` | `=IDC!D57`, value `1,519.564` kEUR | IDC is included in CapEx / construction cost presentation. |
| Commitment fee linked to CapEx | `CapEx!C113` | `=IDC!D58`, value `166.718` kEUR | Fee is included in CapEx / construction cost presentation. |

### TUHO Amount Bridge

| Component | Amount kEUR | Excel operating debt opening treatment |
|---|---:|---|
| Senior principal / facility draw | `43,358.531` to `43,359.274` | Included in operating senior debt opening balance. |
| Senior IDC | `1,519.564` | Calculated in IDC and linked to CapEx; not capitalized into operating DS opening balance. |
| Senior commitment fee | `166.718` | Calculated in IDC and linked to CapEx; not capitalized into operating DS opening balance. |
| Principal + IDC | `44,878.838` | Not observed as operating DS opening balance. |
| Principal + IDC + fee | `45,045.556` | Not observed as operating DS opening balance. |
| Prior review target | `45,878.837` | No matching workbook cell found in inspection; unresolved `+1,000` kEUR vs principal + IDC. |

### TUHO Period Boundary Evidence

| Cell | Value | Interpretation |
|---|---|---|
| `DS!G1` / `DS!G2` / `DS!G3` | `2028-06-30` / `2029-12-31` / `0` | Construction or pre-operating debt schedule column. |
| `DS!H1` / `DS!H2` / `DS!H3` | `2030-01-01` / `2030-06-30` / `1` | First operating debt schedule period. |

## Oborovo Evidence

Source workbook: `20260414_BP_Oborovo_Sensitivity_FINAL for PPT.xlsm`

| Question | Evidence | Value / Formula | Interpretation |
|---|---:|---|---|
| Senior principal / facility amount | `Inputs!D192` | `=DS!D51`, value `42,852.279` kEUR | Input senior debt references the DS maximum funding row. |
| Senior principal / facility amount | `Inputs!D195` | `=MIN(DS!$D$47,G171*$D$230)`, value `42,852.279` kEUR | Senior amount is derived from DS and sizing cap. |
| Construction senior debt source cap | `IDC!D40` | `=MAX(G40:AJ40)`, value `42,852.267` kEUR | Construction diagnostic source cap matches runtime fixed debt within rounding. |
| Senior debt funding in construction/pre-op column | `DS!G51` | `42,852.279` kEUR | Debt schedule funding equals principal only. |
| Senior debt end of construction balance | `DS!G56` | `42,852.279` kEUR | Closing balance after construction/pre-op column equals principal only. |
| First operating senior beginning balance | `DS!H50` | `42,852.279` kEUR | Operating debt schedule opens at principal only. |
| First operating senior principal repayment | `DS!H52` | `935.650` kEUR | Principal repayment begins from principal-only opening balance. |
| First operating senior net interest | `DS!H53` | `1,303.483` kEUR | Operating interest is computed after COD in DS schedule. |
| First operating senior closing balance | `DS!H56` | `41,916.629` kEUR | Closing balance equals opening less principal repayment. |
| Senior IDC | `IDC!D57` | `=Macro!H13`, value `1,086.032` kEUR | Senior IDC is calculated outside the operating DS principal balance. |
| Senior commitment fee | `IDC!D58` | `=Macro!H14`, value `188.563` kEUR | Commitment fee is calculated separately from debt schedule opening balance. |
| Senior IDC linked to CapEx | `CapEx!C128` | `=IDC!D57`, value `1,086.032` kEUR | IDC is included in CapEx / construction cost presentation. |
| Commitment fee linked to CapEx | `CapEx!C131` | `=IDC!D58`, value `188.563` kEUR | Fee is included in CapEx / construction cost presentation. |

### Oborovo Amount Bridge

| Component | Amount kEUR | Excel operating debt opening treatment |
|---|---:|---|
| Senior principal / facility draw | `42,852.267` to `42,852.279` | Included in operating senior debt opening balance. |
| Senior IDC | `1,086.032` | Calculated in IDC and linked to CapEx; not capitalized into operating DS opening balance. |
| Senior commitment fee | `188.563` | Calculated in IDC and linked to CapEx; not capitalized into operating DS opening balance. |
| Principal + IDC | `43,938.299` | Not observed as operating DS opening balance. |
| Principal + IDC + fee | `44,126.862` | Not observed as operating DS opening balance. |

### Oborovo Period Boundary Evidence

| Cell | Value | Interpretation |
|---|---|---|
| `DS!G1` / `DS!G2` / `DS!G3` | `2029-06-29` / `2030-06-30` / `0` | Construction or pre-operating debt schedule column. |
| `DS!H1` / `DS!H2` / `DS!H3` | `2030-07-01` / `2030-12-31` / `1` | First operating debt schedule period. |

## Python Current Behavior

Current runtime fixed senior debt behavior aligns with the Excel operating debt schedule opening balance policy:

| Project | Python / construction principal reference | Excel first operating senior opening balance | Delta | Comment |
|---|---:|---:|---:|---|
| TUHO | approximately `43,359` kEUR | approximately `43,358.531` kEUR | rounding-level | Runtime fixed senior debt is principal-only and directionally matches Excel DS opening balance. |
| Oborovo | approximately `42,852` kEUR | approximately `42,852.279` kEUR | rounding-level | Runtime fixed senior debt is principal-only and directionally matches Excel DS opening balance. |

Phase 7I / 7J construction diagnostics expose computed senior IDC and computed construction opening balances for audit. Those diagnostics should not be interpreted as proof that operating senior debt should include IDC. The inspected Excel operating DS rows show otherwise.

## Senior IDC Treatment

Evidence indicates senior IDC and commitment fees are:

- calculated in the `IDC` sheet,
- linked to `CapEx` rows,
- likely part of construction cost / tax / depreciation-related presentation,
- not capitalized into the operating senior debt schedule opening balance.

The current runtime should therefore avoid replacing fixed senior debt with principal + IDC unless a future review finds a separate Excel operating schedule cell that explicitly does so.

## Commitment Fee Treatment

Commitment fees are calculated separately from senior debt principal and are linked into CapEx:

- TUHO: `IDC!D58` to `CapEx!C113`.
- Oborovo: `IDC!D58` to `CapEx!C131`.

The inspected operating DS rows do not add the commitment fee to opening senior debt. A future implementation should not add commitment fees into debt opening balance unless a separate Excel debt schedule reference proves that treatment.

## Policy Recommendation

Adopt policy **A: keep runtime fixed senior debt as principal-only**.

Rationale:

1. TUHO Excel first operating senior opening balance equals the senior principal / facility funding amount, not principal + IDC or principal + IDC + fee.
2. Oborovo Excel first operating senior opening balance follows the same pattern.
3. Senior IDC and commitment fees are visible in IDC / CapEx rows, but not in the operating debt schedule opening balance.
4. Runtime fixed senior debt currently matches principal-only behavior within rounding.
5. Changing runtime senior opening balance to include IDC would likely overstate operating debt versus the inspected Excel DS schedule.

## Blocked / Unresolved Items

| Item | Status | Next action |
|---|---|---|
| TUHO `45,878.837` review target | Unresolved. No matching workbook cell was found near `45,878.837`; it is also not equal to principal + IDC or principal + IDC + fee. | Treat as superseded or ambiguous until a cell reference is identified. |
| Whether IDC affects tax depreciation / fiscal reintegration | Likely yes through CapEx rows, but not fully traced in this policy note. | Address in a tax / depreciation forensic branch if needed. |
| Senior schedule residual timing differences | Not solved by opening balance policy. | Compare repayment, interest, day-count, DSRA, and sculpting timing separately. |
| Senior IDC effective rate details | Construction diagnostics already expose senior IDC; exact rate/day-count parity may still require separate review. | Keep diagnostic-only until operating schedule treatment requires action. |

## Next Branch Recommendation

Recommended next branch: `phase7k-senior-debt-schedule-alignment`.

Suggested scope:

- keep opening senior debt principal-only,
- compare Excel vs Python senior repayment and interest period by period,
- isolate any remaining differences in day-count, repayment timing, DSCR sculpting input, and COD transition timing,
- avoid SHL waterfall changes,
- avoid tax/revenue/OPEX changes,
- avoid construction IDC capitalization changes unless directly proven by Excel DS schedule evidence.

Do not proceed with a senior debt opening balance replacement branch unless new Excel evidence proves that the operating senior debt schedule should include IDC or fees.
