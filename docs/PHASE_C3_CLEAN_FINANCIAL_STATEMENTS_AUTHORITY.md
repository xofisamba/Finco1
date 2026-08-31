# Phase C3 — Clean Financial Statements & Output Completeness Authority

## CURRENT AUTHORITATIVE STATE — CORRECTION H + FINAL DOCUMENTATION CLOSURE

**Branch:** `phasec3-clean-financial-statements-authority`
**PR:** #964 (DRAFT — NOT MERGED)
**Delivery classification:** `PHASE_C3_BLOCKED_BY_UPSTREAM_ENGINE_AUTHORITY`

C3 internal contracts are coherent; all C3 suites (A, D, F, G) agree;
dedicated CI gate covers all C3 suites; 33/33 CI check-runs green at
exact HEAD; only genuine upstream economic authorities remain as blockers.

### What Correction G established

| § | Change |
|---|---|
| §3 | Raw IDC fallback (`senior_idc_accrual_keur`) prohibited. Fail closed when `senior_idc_capitalized_uses_keur` absent. |
| §5/§6 | `BookCapitalizationTreatment` drives GFA component inclusion. Unknown/UNRESOLVED non-zero component fails GFA closed. |
| §7 | Policy-causal negative tests prove map is authority, not metadata. |
| §8/§9 | Dep-basis mismatch fires on any material difference (>1 kEUR), not only zero-vs-nonzero. Per-component comparison in `gfa_report["dep_basis_comparison"]`. |
| §13/§14 | `preconstruction_retained_earnings_keur` and `preconstruction_retained_earnings_authority` added to `AccountingPolicyConfig` (canonical input layer). |
| §15 | Oborovo/TUHO: `preconstruction_re = 0.0 / SOURCE_PROVEN` (newly incorporated SPV evidence). Solar/Wind: default `None / UNRESOLVED`. |
| §16 | COD opening RE = typed pre-construction RE + authoritative construction NI. Construction NI counted exactly once. |
| §17 | Value / status / authority / line-authority are independently consistent. No `OK` with UNRESOLVED authority. |
| §18 | `USER_CONFIGURED` maps to `USER_CONFIGURED_ACCOUNTING_POLICY` (new `LineAuthority` member), never `SOURCE_PROVEN_CONFIGURATION`. |
| §19/§20 | Legal reserve UNRESOLVED/disabled preserved. Stale D12 tests corrected to assert UNAVAILABLE/UNRESOLVED/kernel-not-activated. |
| §22 | C3 workflow runs all four suites: main C3 acceptance, Correction D provenance, Correction F persistence, Correction G GFA policy. |
| §27/§28 | Two distinct unavailable reasons: `unrestricted_cash_balance_rollforward` (cash balance roll-forward absent) and `cash_reserve_interest` (interest-on-cash rate policy absent). |
| §29/§30 | Tax payable classified `TAX_PAYABLE_NOT_APPLICABLE` — clean engine handles CIT timing directly; source evidence confirms no separate payable balance sheet row. |

### What Correction H established

| § | Change |
|---|---|
| §H1 | `_GENERIC_CLEAN_ACCOUNTING_POLICY` constant added to `app/project_factories.py`. Explicitly sets four GENERIC_FINCO_POLICY dimensions; all other dimensions explicitly UNRESOLVED. No dataclass default promotion. |
| §H2 | `create_default_solar_project()` and `create_default_wind_project()` wired to `accounting_policy_config=_GENERIC_CLEAN_ACCOUNTING_POLICY`. Solar/Wind now have an explicit, deliberate policy (not an implicit dataclass default). |
| §H3 | `preconstruction_retained_earnings_keur=0.0` and `preconstruction_retained_earnings_authority=GENERIC_FINCO_POLICY` — generic new-SPV assumption: no pre-project equity history. Finco generic methodology, NOT source-proven. |
| §H4 | `opening_re_authority=GENERIC_FINCO_POLICY` and `shl_construction_accounting_authority=GENERIC_FINCO_POLICY` — both approved generic dimensions. |
| §H5 | `book_capitalization_authority=UNRESOLVED`, `book_capitalization_components={}`, `legal_reserve_policy=None`, `legal_reserve_authority=UNRESOLVED`, `cash_interest_authority=UNRESOLVED` — all non-approved dimensions explicitly UNRESOLVED. GFA / legal reserve / cash interest remain unavailable for Solar/Wind. |
| §H6 | Five stale test expectations corrected: D10 `test_generic_for_solar_wind` → `test_unresolved_for_solar_wind` (asserts `UNRESOLVED`, not `GENERIC_FINCO_POLICY`, for book_capitalization_authority); F `test_solar/wind_serializes_none_accounting_policy` → `test_solar/wind_serializes_generic_accounting_policy`; F `test_solar_round_trip_stays_none` → `test_solar_round_trip_preserves_generic_policy`. |
| §H7 | `_assemble_with_policy` in G test suite corrected: uses `run_clean_production` + `assemble_decision_complete_financial_statements` (correct import paths). |
| §H8 | Trailing whitespace removed from this document (`git diff --check` clean). |
| §H9 | Exact-head CI: 33/33 check-runs SUCCESS, 0 failure, 0 pending, 0 cancelled. |

### Generic Solar/Wind accounting policy (Correction H)

Assembly reads exclusively from `AccountingPolicyConfig`. No project identity
is used. The policy is provided by the factory/input layer.

```
_GENERIC_CLEAN_ACCOUNTING_POLICY = AccountingPolicyConfig(
    # Approved generic dimensions (Finco generic new-SPV methodology):
    preconstruction_retained_earnings_keur=0.0,
    preconstruction_retained_earnings_authority=GENERIC_FINCO_POLICY,
    opening_re_authority=GENERIC_FINCO_POLICY,
    shl_construction_accounting_authority=GENERIC_FINCO_POLICY,
    # All other dimensions explicitly UNRESOLVED:
    book_capitalization_authority=UNRESOLVED,
    book_capitalization_components={},
    legal_reserve_policy=None,
    legal_reserve_authority=UNRESOLVED,
    cash_interest_authority=UNRESOLVED,
)
```

This policy is:
- A Finco generic new-SPV methodology (fictional Solar/Wind SPVs)
- NOT source-proven (no project-specific workbook evidence)
- NOT sourced from project identity — assembly never dispatches on project name/code
- Provided exclusively by the factory/input layer; assembly consumes typed config only

### Accounting input architecture

Canonical module: `finco_core/inputs/accounting.py`

- ONE definition of `AccountingPolicyAuthority`, `BookCapitalizationTreatment`, `LegalReservePolicy`, `AccountingPolicyConfig`
- Zero imports from `financial_engine.*`
- `financial_engine/financial_statements/contracts.py` re-exports all four; identity guaranteed (`APC1 is APC2`)
- `ProjectInputs.accounting_policy_config: AccountingPolicyConfig | None = None`
- Serialization: full round-trip with backward compatibility (missing key → None, never SOURCE_PROVEN)
- Cache key: `hash_inputs_for_cache` includes accounting policy

### Upstream prerequisites (DO NOT implement in PR #964)

1. **`BOOK_DEPRECIABLE_ASSET_BASIS_UPSTREAM_REQUIRED`**
   `ConstructionFinancingResult → Canonical BookDepreciableAssetBasis → Operating book depreciation → C3 GFA/AccDep/NFA`

2. **`CASH_RESERVE_INTEREST_UPSTREAM_REQUIRED`**
   `Eligible cash/reserve balance + interest rate policy + timing/day-count → financing income → EBT → taxable income → CIT → Base CFADS → downstream waterfall`

### Completeness matrix (Correction H — current)

| Output | Solar | Wind | Oborovo | TUHO |
|---|---|---|---|---|
| Revenue / OPEX / EBITDA | OK | OK | OK | OK |
| Book depreciation (P&L) | OK | OK | OK | OK |
| Financing income (interest on cash) | FINANCING_INCOME_AUTHORITY_UNAVAILABLE | same | same | same |
| P&L complete | FINANCING_INCOME_AUTHORITY_UNAVAILABLE | same | same | same |
| Tax accrual / cash / bridge | OK | OK | OK | OK |
| Tax payable balance sheet row | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE |
| PF cash waterfall | OK | OK | OK | OK |
| Construction funding | OK (no cfin) | OK (no cfin) | OK | OK |
| FC/COD funding | OK | OK | OK | OK |
| Candidate GFA | N/A (no cfin, UNRESOLVED policy) | same | audit only | audit only |
| Canonical BookDepreciableAssetBasis | UPSTREAM_REQUIRED | UPSTREAM_REQUIRED | UPSTREAM_REQUIRED | UPSTREAM_REQUIRED |
| GFA (fixed) | BOOK_CAPITALIZATION_BASIS_UNAVAILABLE | same | BOOK_DEPRECIABLE_ASSET_BASIS_UPSTREAM_REQUIRED | same |
| Accumulated book depreciation | OK (PARTIAL — dep schedule only) | same | same | same |
| NFA | BOOK_CAPITALIZATION_BASIS_UNAVAILABLE | same | BOOK_DEPRECIABLE_ASSET_BASIS_UPSTREAM_REQUIRED | same |
| Pre-construction retained earnings | 0.0 / GENERIC_FINCO_POLICY | same | 0.0 / SOURCE_PROVEN | same |
| COD opening RE | OK (GENERIC_FINCO_ACCOUNTING_POLICY) | same | OK (SOURCE_PROVEN_CONFIGURATION) | same |
| Legal reserve | LEGAL_RESERVE_AUTHORITY_UNAVAILABLE | same | same | same |
| Full RE roll-forward | FINANCING_INCOME_AUTHORITY_UNAVAILABLE | same | same | same |
| Unrestricted cash (closing) | UNRESTRICTED_CASH_AUTHORITY_UNAVAILABLE | same | same | same |
| Senior | OK | OK | OK | OK |
| SHL | OK | OK | OK | OK |
| DSRA | OK (NONE mode) | OK (NONE mode) | OK (CASH_DSRA) | OK (CASH_DSRA) |
| Distribution Account | OK | OK | OK | OK |
| Balance Sheet complete | UNRESTRICTED_CASH_AUTHORITY_UNAVAILABLE | same | same | same |

### GFA audit report — TUHO (Correction G §34)

Candidate GFA preserved in `gfa_report["candidate_book_gfa_keur"]`; dep-basis
mismatch detailed in `gfa_report["dep_basis_comparison"]`.

| Component | Amount (kEUR) | Treatment | Basis |
|---|---|---|---|
| Hard CAPEX | 70,691.539 | CAPITALIZE_FIXED_ASSET | clean cfin |
| Raw Senior IDC | 1,769.354 | audit only | clean cfin |
| Capitalized Senior IDC | 1,552.229 | CAPITALIZE_FIXED_ASSET | `senior_idc_capitalized_uses_keur` |
| Terminal raw IDC excluded | 217.125 | audit only (not capitalized) | raw − capitalized |
| Senior commitment fee | 166.967 | CAPITALIZE_FIXED_ASSET | clean cfin |
| Structuring fee | 471.514 | CAPITALIZE_FIXED_ASSET | clean cfin |
| VAT IDC | 122.314 | CAPITALIZE_FIXED_ASSET | clean cfin |
| VAT commitment fee | 26.466 | CAPITALIZE_FIXED_ASSET | clean cfin |
| Total capitalized financing | 2,339.490 | — | cfin aggregate |
| Candidate GFA | 73,031.030 | — | hard capex + cap financing |
| Dep basis financing (capex scalars) | 0.000 | — | capex.idc_keur etc. |
| Dep basis gap | 2,339.490 kEUR | BOOK_DEPRECIABLE_ASSET_BASIS_UPSTREAM_REQUIRED | — |

### Legal reserve — source anchors (evidence only, not replayed)

Oborovo source workbook transfers: first partial ≈ 0.7952 kEUR, cap-filling
≈ 49.2048 kEUR, final reserve ≈ 50.0 kEUR.
Clean engine: single 50.0 kEUR transfer (correct cap, wrong per-period timing).
Classification: `legal_reserve_authority = UNRESOLVED`, `LegalReservePolicy(enabled=False)`.

### C1/C2 economic freeze (unchanged)

| Project | XIRR |
|---|---|
| Solar | 7.593168077588568 % |
| Wind | 11.366132007429408 % |
| Oborovo | 8.512246818013307 % |
| TUHO | 9.477998283668464 % |

TUHO C2: NPV 29,291.167 kEUR; LLCR 1.0578163×; min LLCR 1.20×; headroom −0.1421837×; FAIL.

---

*Historical correction notes (A through F) follow below.*

---

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
→ accumulated book depreciation roll-forward IS causal). Status:
`UNRESTRICTED_CASH_AUTHORITY_UNAVAILABLE`.

Opening retained earnings: now authoritative for all four projects. Oborovo/TUHO:
`SOURCE_PROVEN_CONFIGURATION` (typed evidence). Solar/Wind: `GENERIC_FINCO_ACCOUNTING_POLICY`
(explicit `_GENERIC_CLEAN_ACCOUNTING_POLICY`, Finco generic new-SPV methodology,
not source-proven). Full RE roll-forward remains `FINANCING_INCOME_AUTHORITY_UNAVAILABLE`
because financing income is not yet in upstream EBITDA/tax/CFADS.

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
allocation invented. Opening RE at COD is now authoritative for all four
projects: Oborovo/TUHO from `SOURCE_PROVEN` typed pre-construction RE +
authoritative construction NI; Solar/Wind from `GENERIC_FINCO_POLICY`
typed 0.0 pre-construction RE + authoritative construction NI. Full RE
roll-forward remains incomplete (`FINANCING_INCOME_AUTHORITY_UNAVAILABLE`)
because financing income authority is not yet resolved upstream.
No zero-default, no residual insert for any unavailable component.

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
| Opening retained earnings | OK (GENERIC_FINCO_ACCOUNTING_POLICY) | same | OK (SOURCE_PROVEN_CONFIGURATION) | same |
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


## Correction C (this revision)

Retained-earnings boundary repair + accounting-authority closure, still
strictly downstream (no engine formula changes):

1. **Blocker C1 fixed — construction loss no longer double-counted.**
   Option B (operating-only RE schedule) was chosen: the COD opening RE is
   derived from the AUTHORITATIVE construction P&L
   (pre-construction opening RE = 0.0 for a newly incorporated SPV whose
   complete construction P&L starts at the first model period; construction
   NI = -SHL gross interest under typed EXPENSE_TO_PNL) and the RE
   roll-forward begins ONLY at the first operating period. Construction
   periods do NOT emit RE rows. Synthetic no-double-count test: P0 -100,
   P1 -50, op +20 -> COD opening -150, first operating closing -130
   (never -250/-300).
2. **§6 COD identity proven on every project**: COD opening RE = 0.0 + sum
   of construction P&L NI = -sum construction SHL gross interest
   (TUHO -3520.4195552771707, Oborovo -1169.65916453466, Wind
   -41.54113227522754, Solar 0.0). SHL PIK affects RE exactly once, through
   P&L interest; SHL principal never touches RE.
3. **§9-§11 separated statuses**: opening_retained_earnings_status (OK),
   retained_earnings_status (FINANCING_INCOME_AUTHORITY_UNAVAILABLE — the
   roll-forward consumes Net Income whose financing-income authority is
   incomplete; known arithmetic still exposed), legal_reserve_status
   (LEGAL_RESERVE_AUTHORITY_UNAVAILABLE — new enum member),
   unrestricted_cash_status (UNRESTRICTED_CASH_AUTHORITY_UNAVAILABLE).
4. **§14 metadata contradictions fixed**: resolved components carry no
   unavailable reason and a non-UNRESOLVED authority label
   (opening_retained_earnings = SOURCE_PROVEN_CONFIGURATION when typed);
   every unresolved component keeps an explicit reason. Consistency test
   over the full result added.
5. **Blocker C2 fixed — narrow public exception contract.** All
   map_period_vector calls go through one dedicated _axis_checked helper
   that converts ONLY known AXIS_* / PERIOD_VECTOR_* codes into the typed
   STATEMENT_PERIOD_AXIS_MISMATCH result; the public entry catches only
   _TypedUnavailable and _AxisMismatch. Unexpected generic ValueError
   propagates (test: synthetic accounting defect).
6. **§15 Balance Sheet RE follows the same authority**: full RE is not OK,
   so BS retained_earnings_keur stays None; no duplicate roll-forward.
7. **§18-§27 source audits (formula-first, no target fitting)**:
   - Legal reserve: the clean engine already contains a typed generic
     roll_forward_equity_state (transfer = min(positive NI,
     share_capital x legal_reserve_cap_fraction - opening reserve)), but it
     is source-proven only as the interest-limitation gates MINIMUM CAUSAL
     equity state, not as the accounting legal-reserve rule; promoting it
     without workbook proof of the accounting rule would be an invented
     allocation -> LEGAL_RESERVE_AUTHORITY_UNAVAILABLE stands.
   - Book capitalization: clean authorities carry hard CAPEX, capitalized
     senior IDC, commitment/structuring fees, VAT financing costs, FC/COD
     uses and reserve funding separately, but no typed book-capitalization
     contract maps them to a BOOK gross fixed-asset basis componentwise
     (and SHL construction interest must stay EXPENSE_TO_PNL, not GFA) ->
     BOOK_CAPITALIZATION_BASIS_UNAVAILABLE stands (named first missing
     typed concept: the capitalization mapping contract).
   - Unrestricted cash: no causal unrestricted-cash roll-forward authority
     exists (opening cash, minimum-cash/working-capital retention, DA/DSRA
     transfer timing); cash is never solved as a BS residual ->
     UNRESTRICTED_CASH_AUTHORITY_UNAVAILABLE stands.
   - Financing income (cash/reserve interest): not present upstream in
     EBITDA/tax/CFADS; C3 must NOT add it downstream only -> the P&L keeps
     FINANCING_INCOME_AUTHORITY_UNAVAILABLE. Changing upstream economics is
     out of scope for Correction C.
   - Tax payable: no separate CIT payable liability concept exists in the
     clean tax timing contract; terminal unpaid tax is surfaced directly ->
     TAX_PAYABLE_AUTHORITY_UNAVAILABLE (no invented liability).
8. **§29 overall**: highest-priority unresolved component reported
   (unrestricted cash) while unavailable_reasons retains ALL blockers
   (cash, balance sheet, GFA, legal reserve, financing income, tax payable).

Completeness matrix update (Correction C): Opening retained earnings is
now DERIVED/OK on all four projects; Retained earnings movements remain
arithmetically exposed with truthful non-OK status; all other cells
unchanged from Correction B.

Delivery classification (Correction C):
PHASE_C3_BLOCKED_BY_UNRESTRICTED_CASH_AUTHORITY (first blocker; GFA,
legal reserve, financing income and tax payable blockers all remain
visible and named).
