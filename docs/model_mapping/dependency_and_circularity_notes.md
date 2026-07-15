# Dependency and circularity notes

This document pins which **engine-owned** financial concepts are
closed-form solutions in the Finco1 engine. These concepts must
**not** be re-implemented in:

* Jinja templates
* JavaScript (front-end calculation, command palette, etc.)
* the registry or input-set layer
* the UI / HTMX partials
* any subsequent Excel-coverage work

This PR does not add, change, or re-route any of these
closed-form solutions.

## Engine-owned closed-form zones (canonical)

The v5 catalog has **7 engine-owned `DERIVED_ONLY` fields**
(domain=engine). They are **not** candidates to be turned
into editable input cells.

| Canonical field | Engine path | Notes |
|---|---|---|
| `engine.debt_sculpting.schedule` | `financing.sculpting_schedule` | Per-period principal repayment solved from `target_dscr` |
| `engine.shl_distribution.waterfall` | `waterfall.shl_distribution` | SHL priority / lockup / sweep; closed-form |
| `engine.dscr.lockup` | `covenants.dscr_lockup` | DSCR + lockup covenant; engine computes |
| `engine.tax.loss_carryforward_motion` | `tax.loss_carryforward_motion` | Per-period LCF roll; engine computes |
| `engine.frozen_calibrated.toggle` | `financing.use_frozen_excel_senior_debt_schedule` | Engine-owned boundary toggle |
| `engine.capex.idc` | `capex.idc_keur` | IDC; computed from debt schedule + construction period |
| `engine.capex.reserve_accounts` | `capex.reserve_accounts_keur` | Reserve accounts funding; computed from CFADS |

The 5 `capex.F.*` fields in the registry are `TEMPLATE_LOCKED`:
their workbook cells exist on the `Financing!` sheet, not on
`Inputs`, and the engine consumes them from the waterfall
solver.

## Why these are not `FULLY_BOUND`

A genuine editable input may be `FULLY_BOUND` only when every
layer is proven: registry field, snapshot key, save/persistence
path, adapter mapping, ProjectInputs path, engine consumption,
expected RuntimeResult effect, and runtime-test evidence.

The 7 engine-owned concepts above are **not** editable inputs.
They are computed by the engine from other inputs. Marking
them `FULLY_BOUND` would be misleading and would invite future
arcs to re-implement them in templates or JavaScript, which is
explicitly out of scope.

## What this PR does to the fixed-point zones

Nothing. The PR does not modify the engine, the waterfall, the
IDC, the debt sizing, the sculpting, the SHL distribution, the
tax motion, the reserve accounts, the DSCR or the lockup. The
PR is a documentation, validation, and planning layer above the
engine.

## Parser-artifact dependencies in the preliminary pack

The preliminary pack's dependency graph contains 2 181 edges
that are **parser artifacts**, not real model dependencies.
Examples discovered during review:

| Token | Origin | Correct interpretation |
|---|---|---|
| `BS138-DS` | cell-range token split by `-` | row 138 in the `DS` sheet |
| `-CF` | negative-prefixed sheet label | the `CF` sheet (negative sign was a parser bug) |
| `&Inputs` | concatenation residual | refers to the `Inputs` sheet |
| `1-Inputs` | numeric prefix artifact | the `Inputs` sheet |
| `[127]P&L` | bracketed sheet index | the `P&L` sheet at index 127 |

The validator does not currently parse dependencies; this is a
known limit. The next arc that introduces a runtime dependency
check must use the corrected tokens above.

## What the validator enforces

* `validate_manifests.py` performs a structural check on the
  artifacts: file presence, JSON / CSV validity, ID uniqueness,
  classification vocabularies, engine-owned boundary
  classification, FULLY_BOUND evidence, and
  manifest<->source-extraction bijection.

* `validate_manifests.py` does **not** perform dependency
  validation. The dependency notes above are pinned by the
  engine code itself and by the parity guardrails.
