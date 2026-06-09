# Phase C1–C9 Closure Review

> Type: REPORT ONLY (no code, no implementation, no runtime, no flag flip)
> Status: DRAFT
> Date: 2026-06-09
> Base SHA: `d55a900` (post-C9 merge, PR #552)
> Branch: `phase-c9-closure-review`
> Hard constraints:
> - No code changes
> - No implementation
> - No runtime promotion
> - No senior IDC promotion
> - No Oborovo before TUHO
> - DRAFT until reviewed
> - rc1 untouched

---

## 0. Purpose

A report-only closure review that summarizes the eight sequential
phases (C1–C9) which together form the design, offline bridge,
scaffolding, and guard path for the Layer 5 construction-period
runtime seam. This document:

1. Summarizes each phase
2. Confirms the C9 active guard
3. Confirms import-contract enforcement
4. Confirms no runtime promotion has occurred
5. Lists remaining blockers before any C10 work
6. Records the R-PAR-2 status

It is intentionally **non-normative**: it does not authorize, plan,
or design any next step. It only audits what is in main and what
remains open.

---

## 1. C1 — Construction Schedule / IDC Design Gate

- **PR:** #543 (merged at `5fccc3a`)
- **Type:** DESIGN ONLY, DOCS ONLY
- **File:** `docs/phase_c1_construction_idc_design_gate.md`
- **What it did:** Formal design gate identifying what must exist
  before any construction-period / IDC implementation. Identified
  five R-PAR blockers (R-PAR-1 … R-PAR-5) and the gap between
  diagnostic-only `domain/construction/` and runtime-authoritative
  `Project.spending_profile`.
- **Production code:** Untouched
- **Net effect:** Defined scope, evidence requirements, blockers
  for the rest of the C-series

## 2. C2 — SHL IDC Convention + Opening Balance Bridge Design

- **PR:** #544 (merged at `a30535a`)
- **Type:** DESIGN ONLY, DOCS ONLY
- **File:** `docs/phase_c2_shl_idc_convention_opening_balance_bridge.md`
- **What it did:** Defined the SHL IDC convention choice (PIK
  interest accrual, opening-balance-at-COD convention) and the
  bridge shape that would carry offline construction-bridge outputs
  into the runtime waterfall.
- **Production code:** Untouched
- **Net effect:** Narrowed the design space; resolved R-PAR-1
  conceptually; deferred R-PAR-2 (senior IDC)

## 3. C3 — Construction Period Parity Snapshot Design

- **PR:** #545 (merged at `aa800a5`)
- **Type:** DESIGN ONLY, DOCS ONLY
- **File:** `docs/phase_c3_construction_parity_snapshot_design.md`
- **What it did:** Designed the parity snapshot mechanism that would
  later lock construction-bridge outputs to Excel-extracted evidence
  for review. Defined `BridgeAuditRow` shape, parity classification
  taxonomy, and snapshot freeze semantics.
- **Production code:** Untouched
- **Net effect:** Established the evidence-comparison contract

## 4. C4 — Construction Period Parity Snapshot Implementation

- **PR:** #546 (merged at `dcc30b6`)
- **Type:** SNAPSHOT ONLY (engine runs, result captured, no routing)
- **File:** `tests/test_phase_c4_construction_parity_snapshots.py`
- **What it did:** Implemented the C3 snapshot design as an offline
  test-only artifact. Snapshots are written under
  `reports/phase_c4_*.json` for reviewer scrutiny. No runtime code
  reads them.
- **Production code:** Untouched
- **Net effect:** Locked the bridge's Excel-comparable shape

## 5. C5 — Construction Engine Comparison Tests

- **PR:** #547 (merged at `2d8a91c`)
- **Type:** ENGINE COMPARISON ONLY (engine vs engine, no bridge)
- **File:** `tests/test_phase_c5_construction_engine_comparison.py`
- **What it did:** Compared the diagnostic-only construction engine
  output against itself under two methodologies (linear vs S-curve
  drawdown) to expose methodology drift before any promotion.
- **Production code:** Untouched
- **Net effect:** Confirmed that the offline engine is methodologically
  stable; exposed that opening-balance accounting has a small,
  documented residual

## 6. C7 — Opening Balance Bridge Offline Implementation

- **PR:** #549 (merged at `b28723b`)
- **Type:** OFFLINE DOMAIN (no runtime wiring)
- **Files:**
  - `app/services/opening_balance_bridge.py` (offline)
  - `tests/test_phase_c7_opening_balance_bridge.py`
- **What it did:** Implemented the bridge that converts offline
  `ConstructionIDCResult` rows into the per-field shape the runtime
  would consume. Introduced `POLICY_TABLE` (11 fields) and the
  `BridgeFieldPolicy` namedtuple. **Does not import from or write
  to the live waterfall.** Import-contract gate installed in C7
  itself: no module outside the bridge may import the bridge.
- **Production code:** Untouched
- **Net effect:** Domain module is ready for scaffolding; import
  contract enforced via the C7 test guard
  `test_bridge_module_only_imported_by_seam`

## 7. C8 — Layer 5 Runtime Seam Design Gate

- **PR:** #551 (merged at `deeee42`)
- **Type:** DESIGN ONLY, DOCS ONLY
- **File:** `docs/phase_c8_layer5_runtime_seam_design_gate.md`
- **What it did:** Designed the Layer 5 seam that would (in a
  future phase, conditionally) call the bridge from a controlled
  path. Defined the C8 §5.1 / §5.2 behavior matrix
  (frozen / retained / replaced / derived × promotion × R-PAR-2 ×
  parity_ok) and the C8 §6.4 import-contract exemption that lets
  the seam import POLICY_TABLE + BridgeFieldPolicy from the bridge
  (and only those two names).
- **Production code:** Untouched
- **Net effect:** Behavior matrix is the contract C9 implements

## 8. C9 — Layer 5 Runtime Seam Scaffolding

- **PR:** #552 (merged at `d55a900`)
- **Type:** ADDITIVE SCAFFOLDING (seam module + tests + docs + report)
- **Files (all new, zero production-code modifications):**
  - `app/services/construction_runtime_seam.py` (650 lines)
  - `tests/test_phase_c9_construction_runtime_seam.py` (1167 lines, 95 tests)
  - `docs/phase_c9_construction_runtime_seam_scaffolding.md` (357 lines)
  - `reports/phase_c9_construction_runtime_seam_scaffolding.json` (318 lines)
- **What it did:** Implemented `assert_no_construction_runtime_promotion`
  per C8 §5.2 behavior matrix. R-PAR-2 fields (`senior_idc_keur`,
  `senior_opening_balance_keur`) are fail-closed by default.
  Derived fields (e.g. `equity_total_keur`) require explicit
  `parity_ok=True`. Frozen fields (e.g. `capex_keur`) are
  structurally hard-blocked.
- **Production code:** Untouched
- **Net effect:** Guard is callable, testable, and reachable from
  C10+ controlled-enablement code paths. It is **not** wired into
  the live waterfall.

---

## 9. C9 Active Guard — Confirmation

The guard function is:

```
assert_no_construction_runtime_promotion(
    *, field_code, policy, promotion_requested,
    rpar2_resolved=False, parity_ok=False,
) -> None
```

Behavior matrix (per C8 §5.2):

| policy     | promotion_requested | rpar2_resolved | parity_ok | result                        |
|------------|---------------------|----------------|-----------|-------------------------------|
| frozen     | *                   | *              | *         | RAISE (hard rule, no override)|
| retained   | *                   | *              | *         | PASS (no-op)                  |
| replaced   | False               | *              | *         | RAISE                         |
| replaced   | True                | False          | *         | RAISE (R-PAR-2 fail-closed)   |
| replaced   | True                | True           | *         | PASS                          |
| derived    | *                   | *              | False     | RAISE                         |
| derived    | True                | *              | True      | PASS                          |
| derived    | False               | *              | True      | RAISE                         |

Fail-closed defaults: `rpar2_resolved=False`, `parity_ok=False`.

Confirmed in C9 source at `app/services/construction_runtime_seam.py`.
The guard is callable from tests and from any future controlled
code path (e.g. an opt-in CLI), but is **not** wired into the live
runtime waterfall in C9.

---

## 10. Import-Contract Enforcement — Confirmation

The C7 import contract is:

> **No module in the repo may import from
> `app.services.opening_balance_bridge`, except the seam module
> `app.services.construction_runtime_seam`, which is allowed to
> import only `POLICY_TABLE` and `BridgeFieldPolicy`.**

The C7 test `test_bridge_module_only_imported_by_seam` enforces
this by scanning the import graph at test time.

The C9 seam module imports only the two allowed names:

```python
from app.services.opening_balance_bridge import (
    POLICY_TABLE,
    BridgeFieldPolicy,
)
```

No other C9 file imports from the bridge.

**Confirmed:** C9 honours the C8 §6.4 exemption and does not
violate the import contract.

---

## 11. Promotion Status — Confirmation

| Check                                          | Status |
|------------------------------------------------|--------|
| `use_construction_schedule_engine` flipped?    | NO — default remains `False` (`domain/inputs.py:147`) |
| Bridge values routed into waterfall?           | NO — seam not wired into `waterfall_core.py`        |
| Senior IDC promoted?                           | NO — `senior_idc_keur` blocked by R-PAR-2 fail-closed default |
| Senior opening balance promoted?               | NO — `senior_opening_balance_keur` policy=`frozen`    |
| TUHO runtime output changed?                   | NO — no production code modified in C1–C9           |
| Oborovo runtime output changed?                | NO — no production code modified in C1–C9           |
| Feature flags added?                           | NO — provenance list untouched                       |
| `rc1` modified?                                | NO — not touched by any C-phase                     |

Production code diff for `main~1..main` is empty (only 4 additive
files from C9). The runtime is bit-for-bit identical to the
state before the C-series began.

---

## 12. Remaining Blockers Before C10

These are the open items that any C10 work (Layer 5 runtime
wiring) must address before promotion can be considered:

### B1 — R-PAR-2: Senior IDC effective-rate caveat (CRITICAL)

- **Status:** OPEN
- **Issue:** The runtime's senior IDC accrual does not match the
  Excel-extracted effective rate for the same period. This is a
  formula-side gap, not a bridge-side gap.
- **Evidence:** `tests/test_tax_bridge_consumes_interest_limitation.py`
  and `test_oborovo_excel_reconciliation.py` both fail in the
  pre-C9 baseline. 88 parity-suite failures pre-date C9.
- **Decision required:** See the parallel R-PAR-2 Decision
  Discovery PR (this stack's Step 3). The three options are:
  A) model base-rate senior IDC properly
  B) permanently freeze senior opening balance / formally accept caveat
  C) defer promotion
- **Hard rule:** No C10 promotion of any R-PAR-2 field can occur
  before a documented decision lands.

### B2 — R-PAR-5: Equity total derived-field parity (BLOCKER)

- **Status:** OPEN
- **Issue:** `equity_total_keur` is `policy='derived'`; promotion
  requires `parity_ok=True` (audit parity check passes). The
  current parity evidence does not show a stable green pass on
  this field for either TUHO or Oborovo.
- **Decision required:** Either the parity check must turn green
  for a controlled test case (TUHO first, Oborovo never before
  TUHO) or the field must be re-categorized to `retained` or
  `frozen`.

### B3 — R67 tax-bridge residual (TUHO)

- **Status:** OPEN (pre-existing, documented)
- **Evidence:** `test_tax_bridge_residual_r67_final_calibration.py`
  shows a small but persistent R67 tax-cash residual. Not a C9
  regression; pre-dates the entire C-series.

### B4 — Debt-sculpting parity (TUHO and Oborovo)

- **Status:** OPEN (pre-existing)
- **Evidence:** `test_senior_dscr_sculpting_runtime_flag.py` and
  the `_full_schedule_fixtures` tests fail for both projects.

### B5 — R99 audit chain failures (TUHO and Oborovo)

- **Status:** OPEN (pre-existing, audit-only)
- **Evidence:** `test_tuho_r99_audit_fields.py` exposes a chain
  of audit-field failures. These are **audit fields**, not
  runtime outputs, but a green audit chain is required before
  promotion per the C-series rules.

### B6 — Depreciation shadow validation (Oborovo)

- **Status:** OPEN (pre-existing)
- **Evidence:** `test_phase_d3_depreciation_shadow_validation.py`
  fails for Oborovo.

### B7 — Oborovo-before-TUHO ordering

- **Status:** HARD RULE
- **Decision required:** C-series rules state Oborovo cannot
  proceed before TUHO. No C10 promotion of any kind is permitted
  on Oborovo before TUHO reaches the same gate.

### B8 — Controlled-enablement code path not yet designed

- **Status:** NOT DESIGNED
- **Issue:** The seam guard is callable, but no C10 plan defines
  *where* the call would be made from in the waterfall, what
  fields would be in the first TUHO promotion scope, or how the
  rollback would work. The C10 Readiness Design PR (this stack's
  Step 4) is the place to address this.

---

## 13. R-PAR-2 Status

- **C1 R-PAR-2 status:** OPEN
- **C2 impact:** C2 deferred R-PAR-2 to a future workstream
- **C7 impact:** `senior_idc_keur` policy=`replaced` with
  `c1_blocker_reference='blocker_5_R-PAR-2'`
- **C8 impact:** §4.4 / §5.2 row 3-4 codify the fail-closed
  default; row 3-4 require both `promotion_requested=True` AND
  `rpar2_resolved=True`
- **C9 impact:** Guard implements the fail-closed default;
  calling the guard with `rpar2_resolved=False` always raises
  for `senior_idc_keur` and `senior_opening_balance_keur`
- **Status as of 2026-06-09:** OPEN. The R-PAR-2 Decision
  Discovery PR (Step 3 of this stack) presents the three
  decision options but does not make the decision.

---

## 14. Test Count Summary (post-#552 main)

- C1–C9 + 57A-10F/G/H scoped run: **999 passed / 0 failed**
- Full parity + tuho + oborovo: **1671 passed / 88 failed / 2 skipped / 4 xfailed / 1 xpassed**
  - All 88 failures are pre-existing parity gaps (R-PAR-2,
    R99 audit, R67 tax bridge, debt sculpting, depreciation
    wiring). They are documented in `MEMORY.md` and pre-date
    the C-series.
  - **Zero regressions from C9.** `git diff main~1 main` on
    production code is empty.

---

## 15. What This Document Does Not Do

This closure review does **not**:

- Authorize any C10 implementation
- Flip any flag
- Promote any project
- Resolve any blocker
- Make the R-PAR-2 decision

It is a report-only artifact for review.
