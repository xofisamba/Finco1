# Phase C3 — Clean Financial Statements & Output Completeness Authority

## Architecture

```
clean operating schedules
+ clean tax schedules (accrual + cash + audit vectors)
+ clean Senior schedules
+ clean SHL schedules
+ clean G2C waterfall / DA / distributions
+ clean DSRA schedules
+ clean construction financing / project uses
        ↓
financial_engine/financial_statements/  (assembly + identity checks only)
        ↓
presentation adapter (pass-through) → API / UI / persisted run
```

Strictly downstream. No inverse dependency: statements never feed back into
tax, debt sizing, SHL, distributions, returns or valuation. No second
engine. The legacy `domain/financial_statements/*` runtime path is NOT
promoted — production C3 imports nothing from it.

Entry point: `financial_engine.financial_statements.assembly.
assemble_decision_complete_financial_statements(g2c_result, project_inputs)`.
Exposed read-only through `clean_presentation_adapter`
(`view.financial_statements_result`).

## Canonical axis

The model period grid (`model.periods`). G2C waterfall periods live on a
different numbering axis and are joined by `cashflow_date == period_end`
(date join validated; any unmatched operating period fails closed with
`STATEMENT_PERIOD_AXIS_MISMATCH`). No positional zipping of unrelated arrays.

## Income Statement — line authority

| Line | Source | Authority |
|---|---|---|
| Revenue | `OperatingSchedules.revenue_keur` | EXISTING_CLEAN_AUTHORITY |
| OPEX | `OperatingSchedules.opex_keur` | EXISTING_CLEAN_AUTHORITY |
| EBITDA | `OperatingSchedules.ebitda_keur` (signed EBITDA authority, PR-5) | EXISTING_CLEAN_AUTHORITY |
| Book depreciation | `OperatingSchedules.book_depreciation_keur` (NOT tax dep) | EXISTING_CLEAN_AUTHORITY |
| EBIT | EBITDA − book depreciation | DERIVED_ACCOUNTING_ROLL_FORWARD |
| Senior interest expense | `SeniorDebtSchedules.senior_interest_keur` | EXISTING_CLEAN_AUTHORITY |
| SHL interest expense | gross accrued (cash + PIK), `ShareholderLoanSchedules.shl_gross_interest_keur` | EXISTING_CLEAN_AUTHORITY |
| EBT / Net income | identities; CIT = canonical accrual (`tax_keur`) — never recomputed | DERIVED_ACCOUNTING_ROLL_FORWARD |

## Book vs tax depreciation

Distinct concepts, distinct schedules (book basis includes capitalised
financing costs; tax basis is hard capex only). P&L and the balance-sheet
accumulated depreciation use BOOK; the tax bridge carries TAX
(`tax_depreciation_audit_keur`). Test C3-C proves both may differ (TUHO has
genuine book≠tax periods) without contamination in either direction.

## Accrued CIT vs cash tax

P&L carries the canonical accrual (`tax_keur` / `cit_accrual_audit_keur`);
the cash statement carries `corporate_tax_cash_keur`. They legitimately
differ (timing); tests prove neither is forced equal to the other.
`terminal_unpaid_tax_keur` is surfaced directly; a CIT payable roll-forward
is not part of the clean tax timing contract and is honestly marked
`TAX_PAYABLE_AUTHORITY_UNAVAILABLE`.

## Balance sheet (partial, honest)

Balances that ARE clean closing authority: Senior closing, SHL causal
closing (PIK + actual principal; unpaid BULLET stays visible),
Distribution Account closing (per period — never the historical locked
sum), DSRA closing (CASH_DSRA mode; NONE produces no fictitious asset).
Cumulative share capital/premium from typed contribution timing.

NOT yet authoritative (surfaced, never plugged): unrestricted cash (no
causal unrestricted-cash roll-forward exists → `balance_check_keur` is NOT
claimed), gross fixed assets / NFA (book capitalization basis not exposed
→ accumulated book depreciation roll-forward IS causal), opening retained
earnings (construction-equity accounting authority not yet typed). Status:
`UNRESTRICTED_CASH_AUTHORITY_UNAVAILABLE`.

## Cash / PF statement

Option A chosen: `PF_CASH_WATERFALL_STATEMENT` — the project-finance cash
waterfall with explicit accounting classification label (NOT claimed as
IFRS IAS 7). Rows reconcile one-to-one to G2C: revenue/opex/EBITDA cash,
cash tax, FCF banks (`signed_post_senior`), Senior DS, DSRA top-up/draw/
release, DA inflow/release/closing, SHL cash interest + principal, PIK as
a separate memo (non-cash), unpaid principal visibility, legal equity
distributions, equity contributions.

## Retained earnings

`closing = opening + NI − legal equity distributions` over operating
periods; SHL is debt and never deducted from RE; no legal-reserve
allocation invented; opening RE requires a construction-equity accounting
authority not yet typed → surfaced `OPENING_EQUITY_ACCOUNTING_AUTHORITY_
UNAVAILABLE` (no zero-default, no residual insert).

## No-residual insert principle

`balance_check_keur` is only claimable when every component has authority.
While unrestricted cash is unavailable, no balance check is emitted and no
cash figure is solved as a residual (test C3-K would fail on any residual insert).

## Legacy statement modules — new classification

| Module | Classification |
|---|---|
| `domain/financial_statements/result.py` (typed result shapes) | reusable shapes (re-implemented cleanly in C3 contracts) |
| `domain/financial_statements/tax_bridge.py`, `pf_cash_waterfall.py` field mappings | historical/offline validation only |
| `domain/financial_statements/pnl.py` TUHO book-dep bridge + fixtures | historical/offline validation only |
| `domain/financial_statements/balance_sheet.py` cash-as-residual, GFA placeholders | unsafe legacy runtime dependency — NOT promoted |
| `domain/financial_statements/assembly.py` (WaterfallResult entry) | historical/offline validation only |
| `finco_core/financial_statements/*` | historical/offline validation only |

Production C3 has ONE statement authority (this package); no production
module imports the legacy statement runtime.

## Output completeness matrix (C3 delivery)

| Output | Solar | Wind | Oborovo | TUHO |
|---|---|---|---|---|
| P&L | OK | OK | OK | OK |
| Tax accrual/cash bridge | OK | OK | OK | OK |
| PF Cash Flow | OK | OK | OK | OK |
| Fixed asset roll-forward (accumulated book dep) | PARTIAL | PARTIAL | PARTIAL | PARTIAL |
| Gross/NFA fixed assets | UNRESOLVED | UNRESOLVED | UNRESOLVED | UNRESOLVED |
| Retained earnings movements | OK | OK | OK | OK |
| Opening retained earnings | UNRESOLVED | UNRESOLVED | UNRESOLVED | UNRESOLVED |
| Senior | OK | OK | OK | OK |
| SHL | OK | OK | OK | OK |
| DA | OK | OK | OK | OK |
| DSRA | OK (NONE mode) | OK (NONE mode) | OK (CASH_DSRA) | OK (CASH_DSRA) |
| Balance Sheet (complete, incl. cash) | UNRESOLVED | UNRESOLVED | UNRESOLVED | UNRESOLVED |
| Closing unrestricted cash | UNRESOLVED | UNRESOLVED | UNRESOLVED | UNRESOLVED |

Overall delivery status: `UNRESTRICTED_CASH_AUTHORITY_UNAVAILABLE` —
honest partial availability per brief §33/§49; unblocking requires the
unrestricted-cash authority, the book-capitalization basis authority and
the opening-equity accounting authority (future typed stages).

## C1/C2 freeze

Untouched and re-proven on the C3 head: Project XIRR (Solar
7.593168077588568 %, Wind 11.366132007429408 %, Oborovo
8.512246818013307 %, TUHO 9.477998283668464 %) and TUHO C2 (NPV
29,291.16728832153 kEUR; LLCR 1.0578163095049742×; min LLCR 1.20×;
headroom −0.1421836904950258×; FAIL; PLCR COVERAGE_CASHFLOW_BASIS_NOT_
CONFIGURED). Tests C3-N.

## Correction B (this revision)

Correction B hardens the statement authority without touching engine
formulas (C3 remains strictly downstream):

1. **B1 — fail-closed construction-None path.** A `construction_funding
   = None` financing result now returns a typed
   `PF_CASH_CONSTRUCTION_AUTHORITY_UNAVAILABLE` result (empty statement
   tuples, no NameError, no zero-default). The blocker-reasons registry is
   initialized before any branch writes to it.
2. **B2 — canonical PR-F1 axis authority.** Statement assembly no longer
   self-authors axis definitions. Axes come from
   `CanonicalAxisContract.from_periods_and_policy` (full / operating /
   senior) built via the production senior adapter, and every consumed
   vector is validated through `map_period_vector` with exact
   `expected_indices` (AXIS_PERIOD_MISSING / EXTRA / SHIFTED / DUPLICATE /
   LENGTH_MISMATCH). Position maps are built by `enumerate` only after
   validation; any raw AXIS_* `ValueError` is converted to a typed
   `STATEMENT_PERIOD_AXIS_MISMATCH` fail-closed result.
3. **B3 — funding bridge completed.** Construction financing stays in its
   native grain (`construction_funding_rows`); non-construction FC/COD use
   is exposed exactly once as `non_construction_fc_row`; the funding audit
   identity `uses − sources ≡ residual ≈ 0` is asserted for all projects.
4. **Opening RE derivation.** When the typed tax policy is
   `shl_construction_accounting == EXPENSE_TO_PNL`, opening retained
   earnings at COD is derived as −Σ SHL construction gross interest
   (TUHO −3520.42 kEUR, Oborovo −1169.66 kEUR, Solar/Wind 0.0). No plug,
   no workbook reproduction.
5. **Legal reserve / unrestricted cash / financing / CIT** re-audited:
   legal-reserve allocation remains not typed (no invention); unrestricted
   cash remains the primary blocker; financing identity audit proven
   (residual ≈ 0 on all projects); CIT uses canonical realization values.

Corruption matrix: 18 axis/vector corruptions (first/last/mid/dup/reord/
short across tax/SHL/senior, DSRA missing/dup) all fail closed
`STATEMENT_PERIOD_AXIS_MISMATCH` — never silently zeroed.

Delivery classification (Correction B): still
`PHASE_C3_BLOCKED_BY_UNRESTRICTED_CASH_AUTHORITY` — opening RE is now
derived, but closing unrestricted cash and the balance sheet remain
unresolved pending the unrestricted-cash, book-capitalization and
opening-equity authorities.
