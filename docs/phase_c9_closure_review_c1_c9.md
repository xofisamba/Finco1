# Phase C9 Closure Review — C1 → C9 (docs/report-only)

> **Scope label:** `CLOSURE REVIEW. DOCS + REPORT ONLY. NO IMPLEMENTATION. NO PROMOTION. NO WATERFALL ROUTING. NO FLAG FLIP. NO RUNTIME WIRING.`

## 0. Purpose

C1–C9 (with C7-fix, C8-fix, C-series-cleanup as companion PRs) is now
a **complete, design-and-scaffolding chain** for the Layer 5
runtime seam that the Construction Readiness Claude Review
required before any runtime promotion can happen. This document
is a **closure review**:

- It summarises what C1–C9 produced.
- It confirms C9's active guard is in place and import-contract
  enforcement is active.
- It confirms that **no runtime promotion has happened** and
  that the seam blocks all promotion paths.
- It lists the **remaining blockers** before C10 (TUHO
  controlled promotion) can be opened as an implementation PR.
- It states the **R-PAR-2** (Caveat 1) status: still open,
  no decision yet.

This is a **report** only. No code, no formula, no model, no
runtime, no waterfall, no persistence, no UI, no feature flag,
no promotion, no tax/debt/depreciation change.

## 1. C-series chain (C1–C9, all merged on main)

| Phase | PR | SHA | Status | What it delivered |
|---|---|---|---|---|
| C1 | #543 | `5fccc3a` | ✅ merged | Construction Schedule / IDC Design Gate (docs) |
| C2 | #544 | `59f9e3d` | ✅ merged | SHL IDC Convention + Opening Balance Bridge Design (docs) |
| C3 | #545 | `aa800a5` | ✅ merged | Construction Period Parity Snapshot Design (docs) |
| C4 | #546 | `dcc30b6` | ✅ merged | Construction Period Parity Snapshot Scaffolding (tests + fixtures) |
| C5 | #547 | `2d8a91c` | ✅ merged | Construction Engine Comparison Tests (tests) |
| C6 | #548 | — | CLOSED | Superseded by C7 implementation (Layer 4 bridge was the right decomposition) |
| C7 | #549 | `b28723b` | ✅ merged | Layer 4 Opening Balance Bridge Offline Implementation |
| C7-fix | #550 | `4ccf1f5` | ✅ merged | Post-merge test fix for C7 import-contract test |
| C8 | #551 | `deeee42` | ✅ merged | Layer 5 Runtime Seam Design Gate (docs) |
| C8-fix | #553 | `8921031` | ✅ merged | Make C8 `test_no_new_domain_module` commit-relative |
| C-series-cleanup | #554 | `2bbf711` | ✅ merged | Make C1–C5 `TestScopeGuards` commit-relative |
| **C9** | **#552** | **`d55a900`** | ✅ **merged** | **Layer 5 Runtime Seam Scaffolding (active guard + import contract)** |

C9 is the **last** phase in the design-and-scaffolding chain.
C10 (TUHO controlled promotion) cannot open as an
implementation PR until the blockers in §6 are resolved.

## 2. Cumulative test footprint

| Test file | Tests | Status |
|---|---|---|
| `test_phase_c1_construction_idc_design_gate.py` | 60 | ✅ |
| `test_phase_c2_shl_idc_convention_opening_balance_bridge.py` | 99 | ✅ |
| `test_phase_c3_construction_parity_snapshot_design.py` | 122 | ✅ |
| `test_phase_c4_construction_parity_snapshots.py` | 131 | ✅ |
| `test_phase_c5_construction_engine_comparison.py` | 93 | ✅ |
| `test_phase_c7_opening_balance_bridge.py` | 118 | ✅ |
| `test_phase_c8_layer5_runtime_seam_design_gate.py` | 134 | ✅ |
| `test_phase_c9_construction_runtime_seam.py` | **95** | ✅ |
| `test_phase9_tuho_full_line_item_parity_pack.py` | (parity) | ✅ |
| `test_phase23n_oborovo_post_correction_parity_snapshot.py` | (parity) | ✅ |
| `test_phase57a10f_capex_advanced_metadata_ui_audit_surface.py` | (57A-10F) | ✅ |
| `test_phase57a10g_capex_advanced_column_groups.py` | (57A-10G) | ✅ |
| `test_phase57a10h_capex_ux_polish_visual_review_cleanup.py` | (57A-10H) | ✅ |
| **Combined C1–C9 + 57A-10F/G/H + parity** | **1067** | **✅ 0 deselected** |

## 3. C9 active guard (confirmed)

`assert_no_construction_runtime_promotion()` lives in
`app/services/construction_runtime_seam.py` (PR #552, `d55a900`).
It implements the C8 §5.1/§5.2 behavior matrix with
**fail-closed defaults** (`rpar2_resolved=False`, `parity_ok=False`).

### 3.1 Behavior table (C9 active)

| Field class | `promotion_requested` | Other | Behavior |
|---|---|---|---|
| **frozen** (`senior_opening_balance_keur`, `capex_keur`) | any | any | **RAISE** `PromotionBlockedError` |
| **replaced** (`senior_idc_keur`) | True | rpar2=False | **RAISE** (R-PAR-2 blocking) |
| **replaced** (`senior_idc_keur`) | True | rpar2=True | OK (pass) |
| **replaced** (`senior_idc_keur`, `shl_idc_keur`, `shl_amount_keur`, `shl_opening_balance_keur`) | False | any | **RAISE** |
| **derived** (`equity_total_keur`) | True | parity_ok=False | **RAISE** |
| **derived** (`equity_total_keur`) | True | parity_ok=True | OK |
| **derived** (`equity_total_keur`) | False | any | **RAISE** |
| **retained** (`reserves_keur`, `vat_operating`, `financing_fees_keur`, `commitment_fee_keur`) | any | any | OK (pass-through) |

`PromotionBlockedError` subclasses `PermissionError` (per C8 §5.1)
and `ConstructionSeamError` (seam-module base).

### 3.2 Coverage

The guard is exercised by **95 dedicated C9 tests** covering:

- Frozen fields (always RAISE)
- Replaced fields (True/False promotion)
- R-PAR-2 fields (senior_idc_keur) — fail-closed blocking
- Derived fields (equity_total_keur) — parity_required gating
- Retained fields (pass-through)
- Promotion-requested semantics
- rpar2_resolved fail-closed default
- parity_ok fail-closed default
- Unknown field code → `UnknownFieldError` (input validation)
- Invalid policy → `InvalidPolicyError` (input validation)

### 3.3 What the guard does NOT do

- It does NOT mutate runtime state.
- It does NOT write to the waterfall.
- It does NOT flip feature flags.
- It does NOT call the construction engine.
- It does NOT call `build_opening_balance_bridge`.
- It does NOT read or write persistence.
- It does NOT change UI.

The guard is a **pure function**: same inputs → same answer
(raise or return `None`).

## 4. Import-contract enforcement (confirmed)

C8 §6.4 carved out a documented exemption: the seam module
(`app/services/construction_runtime_seam.py`) is the **only**
module in the entire repo that may import the bridge
(`domain/construction/opening_bridge.py`). C9 honours this
exemption and enforces it with **AST-level tests**:

### 4.1 What the seam module imports

- `__future__` (Python feature flags)
- `dataclasses` (for the `ConstructionSeamAuditView` frozen dataclass)
- `typing` (for type hints)
- `domain.construction.opening_bridge` — **restricted to**:
  - `POLICY_TABLE` (the policy-name lookup table)
  - `BridgeFieldPolicy` (the field-policy dataclass)

The seam does **NOT** import:
- `build_opening_balance_bridge`
- `OpeningBalanceBridgeInput`
- `OpeningBalanceBridgeResult`
- `BridgeAuditRow`
- `BridgeMetadata`
- `ManualOverrideRow`
- `ParityReferenceRow`
- `ProjectAssumptions`
- `BridgeIdentityError`

### 4.2 What the seam module does NOT import (runtime)

- `main_web`, `main_api`
- `app.waterfall`, `app.waterfall_core`, `app.waterfall_runner`
- `app.persistence`
- `app.excel_export`
- `domain.waterfall`
- `domain.inputs`
- `domain.financing`, `domain.tax`, `domain.depreciation`,
  `domain.debt`, `domain.capex`
- `static.*`

### 4.3 Enforcement tests (C9 test suite)

- `TestBridgeImportContract::test_only_seam_module_imports_bridge`
  — walks the entire repo and asserts no module other than
  `app/services/construction_runtime_seam.py` imports
  `domain.construction.opening_bridge`.
- `TestSeamModuleDependencies` — AST inspection of the seam
  module's imports; rejects any disallowed runtime import.
- `TestSeamImportContract::test_seam_module_does_not_call_construction_engine`
  — rejects any import or call of `compute_construction_schedule`
  or `build_opening_balance_bridge`.
- `TestSeamImportContract::test_seam_module_does_not_mutate_feature_flag`
  — rejects any reference to `use_construction_schedule_engine`
  in the seam module.
- `TestSeamImportContract::test_seam_does_not_re_export_bridge_symbols`
  — verifies the seam's public API does not leak bridge symbols.

## 5. No promotion (confirmed)

| Project | Promotion status | Notes |
|---|---|---|
| **TUHO** (TUHO-WIND-1) | **NOT promoted** | Level 2 unchanged ✓ |
| **Oborovo** | **NOT promoted** | Level 2 unchanged ✓ |
| Generic Wind | NOT promoted | Level 1 unchanged ✓ |
| Generic Solar | NOT promoted | Level 1 unchanged ✓ |

C9 provides the **mechanism** (the guard) that will gate
future promotion. C9 does **not provide the path** for
promotion. The path is C10 (TUHO) and C11 (Oborovo), each
of which is **explicitly allowed** to do controlled
promotion, and each of which must satisfy the blockers in
§6 before opening.

## 6. Remaining blockers before C10 (TUHO controlled promotion)

C10 cannot open as an implementation PR until **all** of the
following are true:

### 6.1 R-PAR-2 decision (BLOCKER #1)

Senior IDC has an effective-rate caveat (C1 R-PAR-2). C9
guards promotion of `senior_idc_keur` behind `rpar2_resolved=True`.
A decision must be made:

- **A) Model base-rate senior IDC properly** (C-phase workstream,
  TBD): the model computes IDC at the senior base rate; the
  caveat is closed because the model is correct.
- **B) Formally accept the caveat** (governance decision):
  senior IDC remains frozen forever; the caveat becomes a
  documented long-term model assumption.
- **C) Defer**: keep the guard active; revisit later.

See PR #556 (R-PAR-2 decision discovery) for the formal
option matrix and discovery doc.

### 6.2 Parity baseline for derived field `equity_total_keur` (BLOCKER #2)

The C9 guard blocks promotion of the derived
`equity_total_keur` field unless `parity_ok=True`. The
parity baseline is the **rc1 baseline** (`b425a07…`) for
the post-correction snapshots. C10 must establish a
**per-project** parity baseline against rc1 for the
project being promoted (TUHO first, Oborovo second).

### 6.3 Audit endpoint (BLOCKER #3, soft)

The seam provides `build_construction_seam_audit_view`
but the **HTTP audit endpoint** is not yet implemented.
C10 can proceed without it (audit view is callable from
Python). The endpoint is a separate workstream.

### 6.4 TestScopeGuards for C10/C11 (BLOCKER #4, soft)

PR #554 made C1–C5 commit-relative. C10 and C11 will
need their own `TestScopeGuards` (commit-relative) when
they are opened. This is a per-phase setup task.

## 7. R-PAR-2 status

| Field | Status |
|---|---|
| **Caveat** | C1 R-PAR-2: senior IDC effective-rate caveat |
| **Discovered** | During C1 design (PR #543) |
| **Documented in** | C1 design doc, C2 design doc, C7 bridge module, C8 design doc, C9 seam module |
| **Decision** | **OPEN** — no decision yet |
| **Discovery PR** | PR #556 (R-PAR-2 decision discovery, docs/tests only) |
| **Resolution paths** | A) model base-rate properly; B) formally accept caveat; C) defer |
| **C9 enforcement** | `senior_idc_keur` promotion blocked unless `rpar2_resolved=True` AND `promotion_requested=True` |
| **Default** | `rpar2_resolved=False` (fail-closed) |

The senior IDC caveat is the **single most important
unresolved modelling question** in the project. Until a
decision is made, C9's guard will block any attempt to
promote `senior_idc_keur` (which is the only field
currently in the R-PAR-2 set).

## 8. Hard rules confirmed

- ✓ **rc1 untouched:** `b425a0708719eaa5e1d922b1008e5609758e0ad4`
  reachable on `origin/main`; no modifications
- ✓ **No global construction flag enablement:**
  `use_construction_schedule_engine: bool = False` (default-off,
  `domain/inputs.py:147`)
- ✓ **No waterfall routing** (no app/waterfall_* changes since
  C9 merge)
- ✓ **No runtime promotion** (no promote_field method exists;
  no caller invokes the guard; no path from bridge to waterfall)
- ✓ **No senior IDC promotion without R-PAR-2 decision** (C9
  guard blocks at the seam)
- ✓ **No Oborovo before TUHO** (C10 is TUHO-only; C11 follows)
- ✓ **Every PR has been DRAFT until reviewed** (all 12 PRs
  in the C-series chain)
- ✓ **Each phase self-reviewed and ran relevant tests** (combined
  1067/1067 pass, 0 deselected)

## 9. What is NOT in this PR

- No C10 implementation. C10 is a **separate** design-then-
  implementation PR.
- No C11 implementation. C11 is a future phase.
- No R-PAR-2 decision. R-PAR-2 decision is a **separate**
  discovery PR (PR #556).
- No waterfall routing.
- No feature-flag enablement.
- No construction engine activation.
- No bridge output consumption (the seam only imports
  `POLICY_TABLE` and `BridgeFieldPolicy`).
- No project status changes.
- No runtime changes.
- No formula, tax, debt, depreciation, IDC, or persistence
  changes.

## 10. Stop after report

This is a **closure review** PR. It is **DRAFT**. It does
not change any code, test, fixture, or runtime state. It
documents the C1–C9 chain and lists the blockers before
C10 can open.

The next step is **PR #556 (R-PAR-2 decision discovery)**,
which is **docs/tests only** and **does not implement**
either resolution path. The next step after that is
**PR #557 (C10 readiness design)**, which is also
**docs/tests only** and **does not implement promotion**.
