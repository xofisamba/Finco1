# MVP G1 Current Financial Authority

## Test authority

| Class | Meaning | Release effect |
|---|---|---|
| `CURRENT_BLOCKING` | Protects the canonical engine or product contract | Required green |
| `HISTORICAL_COMPATIBILITY` | Compares current behavior with a superseded source/baseline | Runnable, non-blocking |
| `DIAGNOSTIC` | Locates and explains a divergence | Runnable, non-blocking |

Historical evidence is retained. It does not become current authority by updating
goldens, hashes, correction ledgers, or tolerances to match today's output.

## Current canonical authority

### Base tax

Canonical Base tax is generic and methodology-driven: calendar tax years,
explicit model/calendar fragmentation, FIFO loss vintages, configurable legal
loss-carryforward life, positive-taxable-income utilization, explicit interest
deductibility and fiscal reintegration, and explicit cash-tax timing. Source
cash-tax vectors are not runtime inputs. No project identity selects a tax formula.

Oborovo workbook conventions such as a five-model-period loss window, EBT-positive
utilization, H2/next-H1 pairing, June/H1 payment, and non-causal row-39 behavior are
`HISTORICAL_COMPATIBILITY`, not generic Base methodology.

### Bank case and Base case

Base Performance is the P50 operating case. Bank sizing is a separate lender case,
using generic P90 production and configured target DSCR (1.20x for Generic Solar
and Wind). Target DSCR controls Bank sizing. Base DSCR is independently calculated
as Base CFADS divided by actual Senior debt service and need not equal 1.20x.

### SHL causality

The only canonical SHL-to-Senior capacity path is:

`SHL gross interest -> deductible interest -> taxable income/cash tax -> Bank CFADS -> DSCR-sized Senior capacity`.

There is no direct SHL-principal addition, top-up, target fitting, or balancing
adjustment.

### Source projects

TUHO and Oborovo remain source-evidence and calibration projects. Calculations may
dispatch on typed project-owned capability, policy, or input. They may not dispatch
on project name, project code, baseline identity, or source workbook identity.

## Historical and diagnostic authorities

- Phase 2A exact `OPERATING_CORE_V1` snapshots are historical compatibility evidence.
- Phase 2B methodology/engine invariants remain current blocking. Its
  `TAX_CFADS_V1` correction-aware four-baseline comparison is marked
  `historical_compatibility` and remains diagnostic.
  Its 488 Oborovo differences are not approved corrections and are not a current
  release authority. The still-current hand-calculated tax invariants remain useful.
- C3B3B and earlier C3B3 tax/SHL stages remain forensic history superseded by B5-B8
  and G0/G0.1 where their assertions conflict.
- Phase 51F's old Oborovo OPEX total and whole-file implementation hashes are retired.
  The OPEX value was already superseded by hierarchical OPEX migration; evolving
  production modules are protected by semantic tests, review scope, and current
  exact-head gates. Immutable source-extraction report hashes remain blocking.

## G2B Simple Sponsor Returns canonical authority

### Pure Legal Equity

Outflows: share-capital contributions + share-premium contributions +
other-committed-equity contributions + additional-equity contributions
(all from G2A construction funding schedule).

Inflows: legal-equity distributions (operating periods only).

### Total Sponsor

Outflows: all Pure Legal Equity outflows + SHL cash principal contributions.

Inflows: legal-equity distributions + ACTUAL SHL cash interest paid +
ACTUAL SHL principal paid from available project cash.

Contractual SHL amounts due but unpaid because of a project cash deficit are
NOT sponsor cash receipts.  They remain visible through `cash_shortfall_keur`.

PIK accrual is not a sponsor cash receipt at accrual time.  When available
project cash actually repays the capitalised SHL balance (which may include
accrued PIK), that actual paid amount enters Total Sponsor receipts.  If the
contractual due amount exceeds available cash, only the portion actually paid
enters receipts; the remainder is a cash shortfall.

Actual SHL cash receipt derivation (per operating period):

```
cash_available_for_shl = max(0, signed_post_senior)
actual_cash_interest   = min(scheduled_cash_interest, cash_available_for_shl)
cash_after_interest    = max(0, cash_available_for_shl - actual_cash_interest)
actual_principal       = min(max(0, scheduled_principal_due), cash_after_interest)
```

Signed project cash deficits (CFADS < Senior debt service, or contractual
SHL service due > available post-Senior cash) are exposed as
`cash_shortfall_keur` and are not automatically funded by sponsor
contributions, top-ups, or balancing items.

`DISTRIBUTE_ALL_POST_SHL_CASH` is a Generic MVP distribution policy.
It is not an institutional waterfall, a lock-up covenant, or an Excel
parity rule.

### BULLET fail-closed semantics

If the contractual BULLET balloon exceeds available project cash at maturity:

1. The SHL liability is NOT extinguished. Unpaid principal remains.
2. No post-maturity default interest, sponsor top-up, or balancing plug is invented.
3. Legal-equity distributions in all periods after unresolved maturity = 0.
4. All four return metrics (Pure Equity XIRR/MOIC, Total Sponsor XIRR/MOIC) = None.
5. All four metric statuses = `UNPAID_SHL_AT_CONTRACTUAL_MATURITY`.
6. `shl_bullet_unpaid_at_maturity = True` on `SponsorReturnResult`.

Actual sponsor receipts remain cash-only: actual SHL cash interest, actual SHL
principal paid at maturity (cash-capped), and legal-equity distributions in periods
up to and including the maturity period where cash was available.

This applies identically to Default Generic Solar and Wind (both have underfunded
BULLET balloons under default parameters).

### Timing

Construction cashflow dates: `financial_close + (period_index − 1) months`.
This is the Generic MVP sponsor-return timing projection over the G2A
monthly funding periods, not an Excel source-truth draw axis.

Operating cashflow dates: `period_end` from the clean engine operating
period grid.

## G2C Covenant-Gated Shareholder Waterfall canonical authority

### Source authority

Authoritative workbook: `20260414_BP_Oborovo_Sensitivity_FINAL_for_PPT.xlsm`
SHA-256: `15a621c4d6b79024980766e00ebc79d7235fd56f00567be7bf345c769ce57920`

Source fixture (dual-load extracted):
`tests/fixtures/g2c_da_source_evidence.json`
Generation method: `dual_load_from_authoritative_workbook`

### Waterfall ordering (source-proven)

```
1. post-Senior cash (R84, signed) — pre-DSRA, pre-gate
2. Applicable explicit DSRF fee treatment (EXPLICIT_GENERIC_MVP_POLICY_POST_SENIOR_CASH)
3. CF108 Distribution Account available — DA causal roll-forward
4. CF109 five-component covenant gate → da_release / fcf_for_distribution
5. CF112 SHL cash service drawn from fcf_for_distribution (CF112 = CF109)
6. CF116 legal-equity distribution = residual post-SHL
```

**THE CF109 COVENANT GATE IS UPSTREAM OF SHL.**

Both SHL service (CF112) and legal-equity distributions (CF116) are downstream
of the CF109 gate. No layer of the waterfall receives cash before the gate
is evaluated.

### CF108 — Distribution Account causal roll-forward

Source: `CF!G108 = =SUM(G94,G95,G106)+F110` (workbook-verified).

```
da_available[t] = signed_post_senior[t]           (eligible inflow this period)
                  + da_closing[t-1]               (carry from prior period)
```

`da_available[t]` is the signed DA balance available before the gate. It can be
negative (accumulated deficit).

### CF109 — Five-component covenant gate

Source: `CF!G109 = =IF(AND(OR(G$138<$B$109,G$4=0,G108<0,G91<G86,G105<G100),G$4<=$B$11),0,G108)`

Gate components:

```
A = DSCR < lockup threshold       (G138 < B109;  B109 = 1.10)
B = construction period           (G4 = 0)
C = DA available < 0              (G108 < 0)
D = Senior DSRA ending < target   (G91 < G86;  Oborovo: both = 0 → False)
E = J-DSRA ending < target        (G105 < G100; NOT modelled → False)
```

Gate active when:
```
gate_locked = OR(A, B, C, D, E)  AND  within_senior_maturity (G4 <= B11)
```

`B11 = 14` (senior debt maturity years, extracted as scalar in source fixture).
`within_senior_maturity` is a proxy for `G4 <= B11`; formal row-4 mapping evidence
is not yet committed — see `G2C_RESERVE_GATE_NOT_CAUSALLY_CLOSED` below.

Gate output (signed — CF109 passes G108 directly when open, does not clip):

```
gate_locked → da_release = 0;          da_closing = da_available  (accumulates)
gate_open   → da_release = da_available; da_closing = 0
```

Gate status attribution:

```
comp_A triggered → LOCKED_DSCR_BELOW_LOCKUP
any other trigger → LOCKED_COVENANT_GATE
gate open → OPEN or DSCR_UNAVAILABLE_GATE_OPEN (no Senior debt service)
```

### CF110 — Distribution Account closing balance

Source: `CF!G110 = G108 - G109`

```
da_closing[t] = da_available[t] - da_release[t]
```

### DA telescoping identity (across-period invariant)

```
sum(da_inflow)  =  sum(da_release)  +  da_closing[final_period]
```

This replaces any earlier "gate partition" or "sum_pre_gate conservation" invariant,
which was not valid under the DA carry-forward model.

### R-row source map

```
R84  → signed_post_senior (pre-DSRA, pre-gate; see limitation below)
CF108 → da_available (signed DA balance after eligible inflow + carry)
CF109 → fcf_for_distribution / da_release (gate output)
CF110 → da_closing (DA closing balance)
CF112 → SHL cash service input (= CF109 per source formula CF112 = H109)
CF116 → legal_equity_distribution_keur (residual post-SHL)
```

### DSRF fee treatment

Only one DSRF fee treatment is implemented:
`EXPLICIT_GENERIC_MVP_POLICY_POST_SENIOR_CASH`

No source evidence exists for any other treatment. Any other configuration raises
a fail-closed error.

### Explicit stop boundaries (retained — not implemented in this PR)

`G2C_RESERVE_GATE_NOT_CAUSALLY_CLOSED` — three sub-causes retained:

1. **CASH_DSRA draw engine not implemented**: `senior_dsra_closing = senior_dsra_target`
   (static; no draw or replenishment modelled). Gate component D depends on this.

2. **J-DSRA not modelled**: Gate component E is always False (no junior DSRA data).

3. **`period_index <= senior_last_period_index` is a proxy for `G4 <= B11`**:
   Formal row-4 mapping evidence is not yet committed; the proxy has not been proven
   equivalent to the source formula condition.

Do NOT remove or weaken these stop boundaries in this phase.

## DSRF — Debt Service Reserve Facility canonical authority

### DebtServiceReserveSupportMode

Three typed modes; dispatch is via `FinancingParams.dsra_support_mode`.
NEVER dispatch on project name, code, or workbook identity.

| Mode | Meaning | Project Use at FC | Operating fee |
|---|---|---|---|
| `CASH_DSRA` | Cash-funded DSRA | `reserve_accounts_keur` (Project Use) | None |
| `DSRF` | Standby facility | None (no cash use) | Commitment fee from COD |
| `NONE` | Default | None | None |

### DSRF commitment fee

`fee_keur = dsrf_commitment_keur × dsrf_commitment_fee_rate_pa × period_fraction`

Fee classification: FINANCING/DEBT-FACILITY cost. NOT operational OPEX.
Visible per-period as `dsrf_commitment_fee_keur` on `CovenantGatedWaterfallPeriod`.
Fee accrues from COD (construction periods: fee = 0).

### Sources & Uses invariant

For the same project inputs (same hard CAPEX, same `reserve_accounts_keur`):

```
Total Uses_CASH_DSRA - Total Uses_DSRF = funded reserve amount (= reserve_accounts_keur)
```

Hard CAPEX is identical between modes. The difference is solely the funded reserve use.

### MVP limitations

No DSRF draw or reimbursement mechanics are implemented. The DSRF is modelled as
a pure commitment fee generator; draw events are out of scope.

## Current blocking ring

1. MVP G2C Covenant-Gated Shareholder Waterfall
2. MVP G2B Simple Sponsor Returns
3. MVP G2A Financing Stack and Derived SHL
4. MVP G1 Governance & Methodology Lock
5. MVP G0 Generic Clean Engine
6. C3B3D2B5 SHL Fixed-Point Integration
7. C3B3D2B6 Base/Post-Senior Cash
8. C3B3D2B7 Bank/Senior Source Parity
9. C3B3D2B8 Base/Senior/SHL Closure
10. C3B1 source-truth evidence
11. C3B3A clean Senior contract
12. CI product smoke/persistence and current semantic core checks
13. Parity Guardrails semantic outputs, immutable source hashes, and import boundaries

Phase 2A, Phase 2B, C3B3B/C3B3C/C3B3D0/C3B3D1/C3B3D2A/B0-B4,
Phase 2C, and Phase 2D are manual historical or diagnostic workflows unless a later
authority explicitly promotes a surviving assertion. A workflow-authority test
locks those workflows to `workflow_dispatch` while preserving automatic
pull-request execution for every member of the current blocking ring.
