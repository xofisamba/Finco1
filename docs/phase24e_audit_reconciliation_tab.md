# Phase 24E: Audit / Reconciliation Tab

## Base SHA
`3870ef73dd181dd9c10a13fcf7810fd794405c2d` (after PR #325 merge)

## Why Phase 24E
Phase 24C.1 added frozen-vs-derived warnings and Phase 24F added SQLite backup/restore. Phase 24E surfaces the now-complete parity and validation status across all main model areas in a single audit view.

## PR #299 Status
`draft=True`, `state=open`, `merged=False` — superseded.

## New Partial

`app/templates/partials/audit_reconciliation_tab.html`

## Audit Tab Sections

| Section | Status | Notes |
|---------|--------|-------|
| Revenue | ✅ PASS | TUHO/Oborovo PPA+CO2+balancing parity confirmed |
| OPEX | ✅ PASS | TUHO 12 items Y1=1,998 kEUR / Oborovo 15 items Y1=1,338 kEUR |
| CAPEX | ⚠️ PENDING | Phase 21 display/schema only; C.16 + M1-M18 not runtime-effective |
| Debt / DSCR | ✅ PASS | TUHO/Oborovo fixture-backed frozen Excel, DSCR above target expected |
| SHL / Distribution | ✅ PASS | TUHO clean; Oborovo lock-up clean, first dist op_idx 39 |
| Unresolved Issues | ℹ️ INFO | Oborovo op_idx 27 +16.84 kEUR within tolerance; DSCR deviations expected |
| Validation Checks | ✅ PASS | Input validation, taxonomy, frozen-vs-derived warning, backup/restore |

## Status Taxonomy

| Audit status | Meaning |
|-------------|---------|
| PASS | Parity/behavior confirmed for TUHO/Oborovo frozen-template path |
| WARN | Minor issue within tolerance or expected under frozen DS path |
| FAIL | Parity gap exceeds tolerance or defect confirmed |
| NEEDS REVIEW | Not validated against Excel or requires human review |
| NOT APPLICABLE | Does not apply to this project/scope |
| PENDING | Planned but not yet runtime-effective |

## Frozen-Template vs Generic-Project Scope

| Scope | Status |
|-------|--------|
| TUHO frozen-template | ✅ PASS — validated |
| Oborovo frozen-template | ✅ PASS — validated |
| Generic wind/solar | ⚠️ NEEDS REVIEW — unvalidated |

## Explicit Non-Claims

This tab does NOT represent:
- Bank approval or lender approval
- External model audit or certified audit
- Credit committee approval
- SaaS/audit certification

Disclaimer is included in the tab header and footer.

## No Runtime Formula Changes

✅ No financial formula changes.
✅ No JS financial calculations.
✅ Backend remains source of truth.

## Known Limitations

- Audit tab is a new partial — routing into workspace tabs is a subsequent step.
- Generic project path is marked "Needs Review" but no runtime validation is performed.
- CAPEX per-line runtime not exposed — marked "Pending".
- Oborovo op_idx 27 DS residual (+16.84 kEUR) is within20 kEUR tolerance.

## Recommended Next Phase

**Phase 24D — Shared LineItemGrid**
- Extract shared grid rendering logic for CAPEX/OPEX/Revenue line items
- Reduce duplication across sheet partials
- The audit tab reveals multiple sheets use similar table-rendering patterns

**Phase 25A — Treatment UI** (alternative)
- Surface the tax treatment assumptions and IDC capitalization logic
- Pending/future tax treatment display

## Guardrails

- ✅ No financial formula changes
- ✅ No runtime calculation changes
- ✅ No factory flag changes
- ✅ No fixture value changes
- ✅ G20 BLOCKED
- ✅ R99/R102 NOT APPROVED
- ✅ partial_pay_sweep not promoted
- ✅ flat/min DSCR sculpting not promoted
- ✅ PR #299 remains draft / not merged / superseded
- ✅ Backend remains source of truth
- ✅ No JS financial calculations

## Tests

10 tests in `tests/test_phase24e_audit_reconciliation_tab.py`:
1. `test_audit_reconciliation_partial_exists` ✅
2. `test_audit_tab_contains_required_sections` ✅
3. `test_audit_tab_uses_runtime_impact_taxonomy` ✅
4. `test_audit_tab_contains_frozen_template_scope_warning` ✅
5. `test_audit_tab_contains_no_bank_or_external_audit_claim` ✅
6. `test_capex_audit_status_not_runtime_promoted` ✅
7. `test_debt_dscr_audit_status_mentions_fixture_backed` ✅
8. `test_shl_distribution_audit_status_mentions_lockup` ✅
9. `test_no_js_financial_calculations_added` ✅
10. `test_guardrails_unchanged` ✅

Full suite: **182 passed, 2 xfailed, 1 xpassed**
