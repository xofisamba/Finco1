# Phase C9 — Layer 5 Runtime Seam Scaffolding (NO runtime promotion)

> **Scope label:** `SCAFFOLDING ONLY. STRUCTURAL ONLY. NO RUNTIME PROMOTION. NO WATERFALL ROUTING. NO FEATURE-FLAG ENABLEMENT.`

## 0. Purpose

C9 is the first **implementation** phase of the Layer 5 runtime seam
that was designed in C8 (`docs/phase_c8_layer5_runtime_seam_design_gate.md`,
PR #551). C9 is structural scaffolding only:

- It implements the **no-promotion guard** function as specified in
  C8 §5.1 with the behavior table in C8 §5.2.
- It implements a **read-only audit visibility helper** that exposes
  the bridge output to audit consumers (not to runtime).
- It implements a **seam class skeleton** that holds the seam
  version and exposes the guard and audit helper as methods.
- It implements the **import-contract exemption** for itself: C8's
  import-contract test was updated in C8 §6.4 to allow the seam
  module to import the bridge. C9 honours that exemption.

C9 does **not**:

- Flip `use_construction_schedule_engine` to `True`. The flag
  remains `False` (default-off).
- Route bridge values into the waterfall.
- Change runtime outputs, formulas, tax, debt, depreciation,
  CFADS, or persistence.
- Change UI, templates, or schema.
- Implement the C10/C11 promotion logic.

C9 is the **structural** layer. C10 and C11 are the **numerical**
layers that follow, separated by project (TUHO and Oborovo) for
risk isolation.

## 1. C-series chain (C1–C8 verified)

| Phase | Status | SHA | Notes |
|---|---|---|---|
| C1 | ✅ merged | `5fccc3a` | Design gate |
| C2 | ✅ merged | `59f9e3d` | SHL IDC convention + bridge design |
| C3 | ✅ merged | `aa800a5` | Construction parity framework |
| C4 | ✅ merged | `dcc30b6` | Snapshot scaffolding |
| C5 | ✅ merged | `2d8a91c` | Engine comparison tests |
| C6 | CLOSED | (PR #548) | Superseded by C7 |
| C7 | ✅ merged | `b28723b` | Layer 4 bridge module |
| C7-fix | ✅ merged | `4ccf1f5` | Post-merge test fix |
| C8 | ✅ merged | `deeee42` | Layer 5 seam **design** gate |
| **C9** | **DRAFT (this PR)** | — | Layer 5 seam **scaffolding** |
| C10 | future | — | TUHO controlled promotion |
| C11 | future | — | Oborovo controlled promotion |

## 2. C9 deliverable scope (per C8 §7.3)

C9 produces exactly **4 files**:

| File | Lines | Purpose |
|---|---|---|
| `app/services/construction_runtime_seam.py` | ~600 | Seam module with guard + audit helper + seam class |
| `tests/test_phase_c9_construction_runtime_seam.py` | ~750 | Guard behaviour, audit view, import contract, hard constraints |
| `docs/phase_c9_construction_runtime_seam_scaffolding.md` | (this file) | C9 design + scope |
| `reports/phase_c9_construction_runtime_seam_scaffolding.json` | ~250 | Machine-readable C9 report |

**No other files are added or modified.** The bridge module
(`domain/construction/opening_bridge.py`) is unchanged. The C8
import-contract test file is unchanged (its list of forbidden
importers already covers the C9 file set; only the seam module
itself is exempt). The C8 test file is unchanged.

## 3. The guard (`assert_no_construction_runtime_promotion`)

### 3.1 Signature (verbatim from C8 §5.1)

```python
def assert_no_construction_runtime_promotion(
    *,
    field_code: str,
    policy: str,  # "replaced" | "frozen" | "retained" | "derived"
    promotion_requested: bool,
    rpar2_resolved: bool = False,
    parity_ok: bool = False,
) -> None:
    """Raise if bridge output is being routed into runtime without
    explicit approval. Implements C8 §5.1, §5.2 behavior matrix."""
```

### 3.2 Behavior matrix (verbatim from C8 §5.2)

| Field | `promotion_requested` | `rpar2_resolved` | `parity_ok` | Expected |
|---|---|---|---|---|
| `senior_opening_balance_keur` (frozen) | * | * | * | **RAISE PermissionError** |
| `capex_keur` (frozen) | * | * | * | **RAISE PermissionError** |
| `senior_idc_keur` (replaced, R-PAR-2) | True | False | * | **RAISE** (R-PAR-2 blocking) |
| `senior_idc_keur` (replaced, R-PAR-2) | True | True | * | OK (pass) |
| `senior_idc_keur` (replaced, R-PAR-2) | False | * | * | **RAISE** |
| `shl_idc_keur` (replaced) | True | n/a | * | OK (pass) |
| `shl_idc_keur` (replaced) | False | n/a | * | **RAISE** |
| `shl_amount_keur` (replaced) | True | n/a | * | OK |
| `shl_amount_keur` (replaced) | False | n/a | * | **RAISE** |
| `shl_opening_balance_keur` (replaced) | True | n/a | * | OK |
| `shl_opening_balance_keur` (replaced) | False | n/a | * | **RAISE** |
| `equity_total_keur` (derived) | True | n/a | True | OK (parity assumed) |
| `equity_total_keur` (derived) | True | n/a | False | **RAISE** |
| `equity_total_keur` (derived) | False | n/a | * | **RAISE** |
| `reserves_keur` (retained) | * | * | * | OK (pass-through) |
| `vat_operating` (retained) | * | * | * | OK |
| `financing_fees_keur` (retained) | * | * | * | OK |
| `commitment_fee_keur` (retained) | * | * | * | OK |

(`*` = "any value, including default")

### 3.3 Exception type

The guard raises `PromotionBlockedError`, which subclasses
`PermissionError` (C8 §5.1 specified `PermissionError`; C9
subclasses it so callers can still catch the bare type for
compatibility). `PromotionBlockedError` also subclasses
`ConstructionSeamError` (the seam-module base class).

Input-validation errors (programmer mistakes, not promotion
blocks) raise distinct exception types:

- `UnknownFieldError` (subclasses `ValueError` and
  `ConstructionSeamError`) — field_code not in
  `SEAM_KNOWN_FIELDS`.
- `InvalidPolicyError` (subclasses `ValueError` and
  `ConstructionSeamError`) — policy literal not in
  `VALID_POLICIES`, or policy mismatch with the C7
  POLICY_TABLE.

This separation lets tests and future callers distinguish "I
called the guard wrong" from "the guard is doing its job".

### 3.4 What the guard does NOT do

- It does NOT mutate runtime state.
- It does NOT write to the waterfall.
- It does NOT flip feature flags.
- It does NOT call the construction engine.
- It does NOT call `build_opening_balance_bridge`.
- It does NOT read or write persistence.
- It does NOT change UI.

The guard is a **pure function**: given the same inputs, it
always returns the same answer (raise or return `None`).

## 4. R-PAR-2 treatment in the guard

C1 R-PAR-2 (senior IDC effective-rate caveat) is preserved as
a blocking constraint with **fail-closed defaults**:

- `senior_idc_keur` is the only field currently in `RPAR2_FIELDS`.
- The guard refuses to permit promotion of this field unless
  BOTH `promotion_requested=True` AND `rpar2_resolved=True`.
- The `rpar2_resolved` parameter defaults to `False` (fail-closed).
- The `parity_ok` parameter defaults to `False` (also fail-closed).

Resolution paths (per C8 §4.4):

1. R-PAR-2 closed (modelling-correct rate) — `senior_opening_balance_keur`
   may transition from `frozen` to `replaced` (separate workstream).
2. R-PAR-2 formally accepted (long-term caveat) — field remains
   `frozen` forever.
3. No third path.

C9 does not implement either resolution path. C9 only implements
the guard that **blocks** promotion until one of the two paths
is taken in a future workstream.

## 5. The audit visibility helper

`build_construction_seam_audit_view(audit_table)` takes a
sequence of bridge audit rows and produces a frozen
`ConstructionSeamAuditView` dataclass with high-level
counters:

- `field_count` — total number of fields in the audit table.
- `frozen_count`, `replaced_count`, `retained_count`, `derived_count`
  — per-policy counts.
- `parity_ok_count`, `parity_drift_count` — per-parity counts.
- `rpar2_blocked_count` — count of fields subject to R-PAR-2 in
  the replaced bucket.

The function is **pure**: it does not mutate the input, does
not call the construction engine, does not read or write
feature flags, and does not produce runtime waterfall input.

The audit view is intended for a future C-phase audit endpoint
(C9 does not implement the endpoint itself; it only provides
the helper). The endpoint, when implemented, will be
read-only and will not feed runtime state.

## 6. The seam class

`ConstructionRuntimeSeam` is a structural skeleton that:

- Holds a reference to the C7 `POLICY_TABLE` (for policy-name
  lookups via the `policy_table()` static method).
- Exposes the guard as a method (`assert_no_promotion`) for
  callers that already hold a seam instance.
- Exposes the audit-view builder as a method
  (`build_audit_view`).
- Records its own version (`VERSION = "C9-1.0"`) so callers
  can assert the seam they are talking to is the C9 seam (or
  later).

C9 does **not** implement any method that mutates runtime
state, writes to the waterfall, or flips feature flags. C10
and C11 may extend this class to add a real `promote_field`
method that calls the guard and then routes the bridge value
to the waterfall. **C9 leaves that for future phases.**

The class has no mutable state in C9. Two instances are
equivalent.

## 7. Import contract

### 7.1 The seam module is the only importer of the bridge

C8 §6.1 forbids the bridge from being imported by:

- `app/` (any subdirectory)
- `main_web.py`
- `main_api.py`
- `app/services/` (any module)
- `app/waterfall_core.py`, `app/waterfall_runner.py`
- `app/persistence/`
- `static/`
- `domain/waterfall*` (any)

C8 §6.4 carved out a documented exemption for the seam
module. C9 honours this exemption: **the seam module is the
ONLY module in C9 that may import the bridge**. The
import-contract test (extended in C9's test file) walks the
entire repo and asserts that no module other than the seam
module imports `domain.construction.opening_bridge`.

The seam module imports the bridge **only** for:

- `POLICY_TABLE` (the policy table constant)
- `BridgeFieldPolicy` (the field-policy dataclass)

It does **not** import `build_opening_balance_bridge`,
`OpeningBalanceBridgeResult`, or any other public symbol. The
seam's public API is independent of the bridge's public API.

### 7.2 The seam module imports no runtime

The seam module's import surface is restricted to:

- `__future__` (Python feature flags)
- `dataclasses` (for the `ConstructionSeamAuditView` frozen
  dataclass)
- `typing` (for type hints)
- `domain.construction.opening_bridge` (documented C8 §6.4
  exemption, restricted to `POLICY_TABLE` and
  `BridgeFieldPolicy`)

The seam module does **not** import:

- `app.waterfall`, `app.persistence`, `app.excel_export`
- `main_web`, `main_api`
- `domain.waterfall`, `domain.inputs`, `domain.financing`,
  `domain.tax`, `domain.depreciation`, `domain.debt`,
  `domain.capex`

C9's test file (`TestSeamModuleDependencies`) walks the seam
module's AST and asserts that no disallowed import is
present. This is the seam side of the import contract.

## 8. Hard constraints (C9 MUST NOTs)

C9 is bound by C8 §7.2's hard constraints. The C9 test file
verifies each of these:

| Constraint | Test |
|---|---|
| No app `main_*` changes | `test_no_app_main_changes` |
| No domain changes (seam is in `app/services/`) | `test_no_domain_changes_outside_seam` |
| No waterfall changes | `test_no_waterfall_changes` |
| No persistence changes | `test_no_persistence_changes` |
| No static changes | `test_no_static_changes` |
| No excel export changes | `test_no_excel_export_changes` |
| `use_construction_schedule_engine` remains default-off | `test_use_construction_schedule_engine_default_off` |
| rc1 SHA reachable | `test_rc1_reachable` |
| C7 bridge module unchanged | (verified by combined test run) |
| C4/C5 fixtures unchanged | (verified by combined test run) |
| No runtime promotion | `TestNoPromotionInSeamModule` |
| No feature flag mutation | `test_seam_module_does_not_mutate_feature_flag` |
| No construction engine call | `test_seam_module_does_not_call_construction_engine` |
| No side-effecting operations | `test_seam_module_has_no_side_effects` |

## 9. Promotion gate status (C9 → C10)

Per C8 §8.5, the promotion gate criteria for C10 are:

- [x] C8 review approved (PR #551, merged at `deeee42`)
- [x] C7 review approved (PR #549, merged at `b28723b`)
- [x] All C1–C7 tests still pass
- [ ] **C9 merged** (this PR is the prerequisite; not yet merged)
- [ ] C9 tests pass
- [ ] `use_construction_schedule_engine` default-off confirmed

C9 is the **next gate**. Until C9 is merged, C10 cannot be
opened. Until C10 is merged, C11 cannot be opened.

## 10. Project status confirmation (C9 invariant)

| Project | Status | Notes |
|---|---|---|
| **TUHO** (TUHO-WIND-1) | **Level 2** — unchanged ✓ | No promotion in C9 |
| **Oborovo** | **Level 2** — unchanged ✓ | No promotion in C9 |
| **Generic Wind** | **Level 1** — unchanged ✓ | Not in C9 scope |
| **Generic Solar** | **Level 1** — unchanged ✓ | Not in C9 scope |

## 11. rc1 confirmation

`b425a0708719eaa5e1d922b1008e5609758e0ad4` reachable on
`origin/main` ✓

## 12. Feature flag confirmation

`use_construction_schedule_engine` remains **default-off** ✓
(declared in `domain/inputs.py:147` as `bool = False`)

## 13. Open follow-ups (NOT in this PR)

1. **C10**: TUHO controlled promotion (per-project opt-in for
   the 4 replaced fields + 1 derived field, with R-PAR-2
   blocking for `senior_idc_keur`).
2. **C11**: Oborovo controlled promotion (mirror of C10).
3. **R-PAR-2 resolution**: separate workstream (not C9).
4. **Audit endpoint**: future phase that wires
   `build_construction_seam_audit_view` to a read-only HTTP
   endpoint. C9 provides the helper; the endpoint is not
   implemented.
5. **TestScopeGuards fix**: 5 C1-C5 tests with pre-existing
   pattern bug (same root cause as C7 pre-#550). This is a
   separate test-cleanup PR (not in C9 scope).
6. **C8 test fix**: C8 `test_no_new_domain_module` is an
   absolute working-tree check; it will fail once C9 adds
   `app/services/construction_runtime_seam.py`. Needs a
   separate C8-fix PR to be C8-commit-relative. This is
   **not in C9 scope** (C9 PR is additive only, 0 modified
   files). The C8-fix PR can be merged in parallel with or
   just before C9.

## 14. Stop after report

C9 is a **structural scaffolding** PR in the strictest sense.
It produces 4 files (seam module + test file + doc + report).
It does not flip any flag, does not change runtime, does not
modify the bridge, does not modify the waterfall, does not
modify the persistence layer, does not change UI.

C9 is the **gate** between C8 (design) and C10 (TUHO
promotion). Until C9 is merged, no runtime promotion can
happen.
