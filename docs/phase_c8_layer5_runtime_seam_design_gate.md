# Phase C8 - Layer 5 Runtime Seam Design Gate

> **Scope label:** **DESIGN ONLY. DOCS / TESTS ONLY. NO
> IMPLEMENTATION. NO RUNTIME WIRING.**
>
> Type: Design gate (docs/tests only)
> Status: DRAFT
> Date: 2026-06-08
> Base SHA: `b28723b` (post-Phase C7, PR #549)
> Branch: `phase-c8-layer5-runtime-seam-design-gate`
> Hard constraints: **NO code implementation, NO runtime wiring,
> NO app changes, NO domain changes, NO waterfall changes, NO
> schema changes, NO persistence changes, NO feature flags, NO
> formula changes, NO CAPEX changes, NO debt changes, NO tax
> changes, NO depreciation changes, NO IDC runtime promotion,
> NO project status changes, NO UI changes.**

---

## 0. Purpose

C1–C7 produced:

- A construction engine (C1 design gate; C5 engine-comparison tests).
- A SHL IDC convention (Convention B per C2).
- A construction parity snapshot framework (C3–C4).
- A Layer 4 Opening Balance Bridge as an offline, pure domain
  module (C7, MERGED in `b28723b`).

C7 left a deliberate gap: the bridge produces an
`OpeningBalanceBridgeResult` with explicit per-field policy
decisions (POLICY_TABLE), but no consumer reads it. The runtime
waterfall remains on the legacy construction inputs. There is
**no Layer 5 seam** between the bridge and the waterfall.

This C8 phase is a **design gate only**. It designs the seam
that will eventually consume the bridge output. It does not
implement the seam, does not wire the bridge, does not change
runtime, and does not flip any feature flag.

C8 answers the question:

> "How should the future runtime seam consume Layer 4 bridge
> output without double-counting, without violating frozen
> policies, and without changing runtime results until an
> explicit promotion PR?"

The answer is: structurally respect the POLICY_TABLE that C2
designed and C7 implemented, gate the seam with an active
no-promotion guard, and define a strict C9→C10→C11 path that
separates seam scaffolding from controlled per-project
promotion.

---

## 1. C1–C7 verification summary

Before designing the seam, C8 verifies the C1–C7 stack.

### 1.1 C1 — Construction / IDC Design Gate (merged `5fccc3a`)

C1 identified 5 blockers. C1 status post-C7: **4 of 5
blockers closed (or planned). 1 deferred (senior IDC
effective-rate modelling — separate workstream,
`blocker_5_R-PAR-2`).**

### 1.2 C2 — SHL IDC Convention + Opening Balance Bridge Design
(merged `59f9e3d`)

C2 produced:

- **Convention B** (Excel full-source elapsed compound) is the
  authoritative SHL IDC convention. Convention A remains in
  effect until the C7–C9 sequence is complete.
- **§3 inputs / outputs** for the bridge.
- **§4 audit table** (14 columns, 5 invariants).
- **§6 validation requirements** (8 items).

C2 status post-C7: **design complete, implemented in C7.**

### 1.3 C3 — Construction Parity Snapshot Design (merged `aa800a5`)

C3 produced the construction-period parity framework. C3 status
post-C7: **complete.**

### 1.4 C4 — Snapshot Scaffolding (merged `dcc30b6`)

C4 produced the frozen golden snapshot files
(`tuho_construction_snapshot.json`,
`oborovo_construction_snapshot.json`). C4 status post-C7:
**complete. C7 reads but does not modify the snapshots.**

### 1.5 C5 — Engine Comparison Tests (merged `2d8a91c`)

C5 produced 93 engine-comparison tests. C5 status post-C7:
**complete. C7 does not re-implement the engine; it consumes
the engine output.**

### 1.6 C6 — Bridge Implementation Plan (DRAFT, PR #548)

C6 produced the implementation plan. C6 status post-C7:
**DRAFT, awaiting review.**

### 1.7 C7 — Layer 4 Bridge Offline Implementation
(merged `b28723b`)

C7 implemented:

- **8 frozen dataclasses**: ManualOverrideRow, BridgeFieldPolicy,
  ParityReferenceRow, ProjectAssumptions, OpeningBalanceBridgeInput,
  BridgeAuditRow, BridgeMetadata, OpeningBalanceBridgeResult.
- **1 exception**: `BridgeIdentityError(ValueError)`.
- **1 module-level constant**: `POLICY_TABLE` (11 entries,
  mirror C2 §2.1).
- **1 public function**: `build_opening_balance_bridge(input)
  -> result` (pure, no side effects, no caller mutation).

C7 status post-merge: **MERGED in `b28723b` (PR #549). The
bridge is offline-only. No runtime consumer exists.**

### 1.8 C1–C7 preconditions for C8

| Precondition | Status |
|---|---|
| C1 design gate | ✅ merged |
| C2 SHL IDC convention decided (Convention B) | ✅ merged |
| C2 §3.7 bridge output contract | ✅ merged |
| C2 §4.1 audit table schema (14 columns) | ✅ merged |
| C2 §4.5 audit table invariants | ✅ merged |
| C2 §2.1 per-field policy | ✅ merged |
| C3 parity framework | ✅ merged |
| C4 snapshot files (TUHO + Oborovo) | ✅ merged |
| C5 engine comparison baseline | ✅ merged |
| C6 API / dataclass shape | ✅ DRAFT |
| C6 §6.1 double-counting guard rules | ✅ DRAFT |
| C6 §6.4 senior IDC effective-rate caveat | ✅ DRAFT |
| C7 Layer 4 bridge module (offline) | ✅ MERGED |
| C7 `POLICY_TABLE` reachable in `domain.construction.opening_bridge` | ✅ merged |
| C7 `build_opening_balance_bridge` callable and tested | ✅ 118/118 |
| rc1 SHA `b425a07...` reachable | ✅ done |
| `use_construction_schedule_engine` default-off | ✅ done |

**All preconditions for C8 are met. C8 can design the seam.**

---

## 2. Layer 5 purpose

C8 defines Layer 5 as a **structural seam** between the Layer 4
bridge output and the runtime waterfall. The seam is a thin
adapter whose only job is to enforce POLICY_TABLE discipline and
gate promotion.

### 2.1 What Layer 5 owns

- **POLICY_TABLE enforcement** at the structural level. Every
  field passed across the seam must declare its policy
  (`replaced`, `frozen`, `retained`, `derived`) and the seam
  must reject any routing that violates a frozen or
  not-yet-promoted policy.
- **A read-only bridge-consumer interface** that translates an
  `OpeningBalanceBridgeResult` into a shape that *could* be
  consumed by the waterfall, without actually wiring the
  consumption in C8.
- **A no-promotion guard** that is callable from tests and from
  future controlled-enablement PRs (C9+). The guard must raise
  `PermissionError` on any attempt to route the bridge output
  into runtime without an explicit promotion flag flip.
- **An import-contract test surface** that statically verifies
  the bridge is not imported by runtime modules.

### 2.2 What Layer 5 must NOT own

- **Runtime waterfall logic.** Layer 5 does not compute CFADS,
  debt service, tax, depreciation, or any other waterfall
  output. It does not own the `app/waterfall_core.py` or
  `app/waterfall_runner.py` flow.
- **Persistence or schema.** Layer 5 does not write to the
  database, the audit log, or any JSON snapshot. C8 is a
  design gate; persistence wiring is a future concern.
- **Feature flags.** Layer 5 does not flip
  `use_construction_schedule_engine` from `False` to `True`.
  That is C10 (TUHO) and C11 (Oborovo).
- **Formula changes.** Layer 5 does not change CAPEX, debt,
  tax, depreciation, IDC, or any other formula. The bridge
  output is a *wiring* of the existing manual values plus the
  engine output; the formulas that consume these values are
  out of scope for C8.
- **UI changes.** Layer 5 does not change templates, partials,
  or HTMX attributes.

### 2.3 How Layer 5 differs from Layer 4 bridge

| Concern | Layer 4 bridge | Layer 5 seam |
|---|---|---|
| Type | Pure domain function | Structural adapter (design only) |
| Inputs | Construction result + manual overrides | Bridge output (downstream) |
| Outputs | `OpeningBalanceBridgeResult` | Policy-tagged field set (downstream) |
| Side effects | None | None (read-only) |
| Persistence | None | None (design only) |
| Feature flag | Does not read `use_construction_schedule_engine` | Does not flip it either |
| Idempotent | Yes (pure) | Yes (read-only) |
| Failure mode | `BridgeIdentityError` (ValueError) | `PermissionError` (no promotion) |
| Status (C8) | MERGED in `b28723b` | **DESIGN ONLY in C8** |

### 2.4 How Layer 5 differs from Waterfall runtime

| Concern | Waterfall runtime | Layer 5 seam |
|---|---|---|
| Owns | CFADS, debt service, tax, depreciation, P&L, balance sheet | Policy enforcement only |
| Consumes | `Project` dataclass + manual inputs | `OpeningBalanceBridgeResult` |
| Mutates | Runtime state (in-memory) | Nothing |
| Tests | Integration / regression / parity | Design contract only (C8) |
| Schema | Writes to DB / Excel / audit | None |
| Feature flag | Reads `use_construction_schedule_engine` | Does not read it (seam is policy-first) |

The seam is a **structural layer** between the bridge
(read-side, audit) and the waterfall (write-side, runtime).
C8 designs the seam so that when C9 scaffolds the seam module,
the waterfall can be retrofitted in a controlled, gated way.

---

## 3. POLICY_TABLE enforcement design

C2 §2.1 / C7 implementation define 4 policy categories:

- `replaced` — bridge output replaces manual value (engine wins)
- `frozen` — manual value is authority; bridge output is audit-only
- `retained` — manual value; no bridge source; parity n/a
- `derived` — composite of manual + engine; parity n/a (or
  composite)

Layer 5 must enforce this taxonomy **structurally** so that the
seam cannot be bypassed at runtime.

### 3.1 Replaced fields

**Policy:** bridge output is the runtime value if and only if an
explicit promotion has occurred (C10/C11).

**Layer 5 behavior:**

- Exposes the bridge output in a read-only structure (e.g. a
  tagged dataclass or a typed dict with policy metadata).
- The structure is *not* automatically routed to the waterfall.
  C8 designs the seam so that an explicit per-field promotion
  flag (not a global flag) is required to route any replaced
  field to runtime.
- For C8, the seam does not exist yet, so replaced fields are
  **NOT routed**. C9 will scaffold the seam; the per-field
  promotion gate will be enforced by the no-promotion guard
  (§5).

**Replaced fields in POLICY_TABLE:**

| Field | C1 blocker |
|---|---|
| `shl_idc_keur` | `blocker_1_R-PAR-1` |
| `shl_amount_keur` | — |
| `shl_opening_balance_keur` | — |
| `senior_idc_keur` | `blocker_5_R-PAR-2` (audit-side only) |

**C8 rule:** the `senior_idc_keur` field is `replaced` for
parity tracking, but its runtime promotion is BLOCKED at the
seam level until R-PAR-2 is resolved (see §4).

### 3.2 Frozen fields

**Policy:** manual value is authority. Bridge output is
audit-only. **Frozen fields cannot be promoted at the seam.**

**Layer 5 behavior:**

- The seam MUST reject any code path that attempts to route a
  frozen field's bridge value into the waterfall.
- The no-promotion guard (§5) enforces this. Any
  `assert_no_construction_runtime_promotion` call that names a
  frozen field raises `PermissionError`.
- C8 documents this as a structural invariant: frozen fields
  are not eligible for promotion **ever**, by design. The
  POLICY_TABLE entry is the contract; the seam is the enforcer.

**Frozen fields in POLICY_TABLE:**

| Field | Reason |
|---|---|
| `senior_opening_balance_keur` | R-PAR-2 caveat; manual is authority |
| `capex_keur` | CAPEX formula stability; manual is authority |

**C8 hard rule:** **frozen fields cannot be promoted by Layer 5.
Period. No exception, no override, no future flag flip can
enable this.**

### 3.3 Retained fields

**Policy:** manual value; no bridge source; parity n/a.

**Layer 5 behavior:**

- The seam does not need to enforce anything for retained
  fields because they are not produced by the bridge. They
  pass through unchanged.
- The seam still records the field's policy in the audit
  metadata so that future code can verify the contract was
  honored.

**Retained fields in POLICY_TABLE:**

| Field | Reason |
|---|---|
| `reserves_keur` | Manual reserve assumption |
| `vat_operating` | Manual VAT rate |
| `financing_fees_keur` | Manual fee assumption |
| `commitment_fee_keur` | Manual commitment fee assumption |

### 3.4 Derived fields

**Policy:** composite of manual + engine; parity_ok when manual
is consistent with engine; identity asserted.

**Layer 5 behavior:**

- The seam honors the composite result. If the bridge reports
  `parity_ok` for a derived field, the seam is allowed to
  forward the composite value to runtime (in C10/C11, not C8).
- If the bridge reports `parity_drift` for a derived field,
  the seam MUST reject the route. This is a structural
  invariant: a derived field with drift is an identity
  violation, and `BridgeIdentityError` would have already
  fired at bridge time.

**Derived fields in POLICY_TABLE:**

| Field | C1 blocker |
|---|---|
| `equity_total_keur` | `blocker_5_R-PAR-5` |

### 3.5 POLICY_TABLE enforcement summary

| Policy | C8 seam | Future C9 seam module | Runtime C10/C11 |
|---|---|---|---|
| `replaced` | Read-only exposed | Gated per-field | Promoted per-field with explicit approval |
| `frozen` | **REJECTED at seam** | **REJECTED at seam** | **NEVER promoted** |
| `retained` | Read-only | Read-only | Manual value (unchanged) |
| `derived` | Composite verified | Composite verified | Composite promoted when parity_ok |

---

## 4. R-PAR-2 constraint

C1 identified the senior IDC effective-rate caveat as
`blocker_5_R-PAR-2`. C6 refined the asymmetry:

- `senior_idc_keur` is `replaced` for parity tracking. The
  bridge value is recorded with `parity_ok` against the C4
  snapshot.
- `senior_opening_balance_keur` is `frozen` because the
  manual value is the contract for downstream runtime. The
  bridge value differs by exactly `+capitalized_senior_idc`
  (TUHO: +1,519.564; Oborovo: +1,086.032). This is the
  `parity_drift` recorded in the audit table.

### 4.1 Senior IDC effective-rate caveat

The senior IDC is computed using an effective rate, not a
modelling-correct rate. This is a known modelling
imperfection documented in C1 §blocker 5. C7 records the
asymmetry in the audit table but does not fix the underlying
modelling issue.

### 4.2 Senior opening balance remains frozen

The senior opening balance is `frozen` because the runtime
waterfall (and downstream debt-service calculations) consume
the manual value. Promoting the bridge value would silently
increase the senior debt service basis by the capitalized
senior IDC, which is **not** a runtime change that should
happen implicitly.

### 4.3 Parity drift remains audit-only

The `parity_drift` recorded in the audit table for
`senior_opening_balance_keur` is **evidence of the asymmetry**,
not a bug. It is preserved as audit data and surfaced for
human review, not consumed by runtime.

### 4.4 Conditions required before future promotion

The senior IDC effective-rate caveat can be resolved by **one
of the following**:

1. **R-PAR-2 closed:** the senior IDC method is updated to a
   modelling-correct rate (e.g. day-count + accrual basis).
   When this happens, `senior_opening_balance_keur` may
   transition from `frozen` to `replaced` and the seam may
   route the bridge value to runtime. This is a separate
   workstream, **not** part of C8–C11.
2. **R-PAR-2 formally accepted:** the modelling imperfection
   is explicitly documented as a permanent caveat, and the
   asymmetry becomes the long-term contract. In this case,
   `senior_opening_balance_keur` remains `frozen` *forever*,
   and the seam continues to enforce this. No promotion
   occurs.
3. **No third path.** The seam does not invent new conditions.

### 4.5 C8 rule for R-PAR-2

> **Until R-PAR-2 is resolved (case 1) or formally accepted
> (case 2), `senior_idc_keur` is audit/bridge-side only.
> The seam does not route `senior_idc_keur` to runtime
> even when it is `replaced`.**

This is a C8-defined structural invariant. It is enforced by
the no-promotion guard (§5) and verified by the
import-contract test (§6).

---

## 5. No-promotion guard design

C8 designs a no-promotion guard analogous to
`assert_no_canonical_depreciation_runtime_promotion` (D2 redo,
`app/depreciation_flag_discipline.py`).

### 5.1 Guard function signature

```python
# Future C9+ signature (NOT implemented in C8)
def assert_no_construction_runtime_promotion(
    *,
    field_code: str,
    policy: str,  # "replaced" | "frozen" | "retained" | "derived"
    promotion_requested: bool,
    rpar2_resolved: bool = False,
) -> None:
    """Raise PermissionError if construction bridge output is
    routed into runtime without approval.

    Behavior:
    - frozen fields: ALWAYS raise (frozen is structural).
    - senior_idc_keur (replaced): raise unless R-PAR-2 is
      resolved or formally accepted.
    - other replaced fields: raise unless promotion_requested.
    - derived fields: raise unless parity_ok AND
      promotion_requested.
    - retained fields: never raise (no bridge source).
    """
```

### 5.2 Expected behavior

| Field | promotion_requested | R-PAR-2 resolved | Expected |
|---|---|---|---|
| `senior_opening_balance_keur` (frozen) | * | * | **RAISE PermissionError** |
| `capex_keur` (frozen) | * | * | **RAISE PermissionError** |
| `senior_idc_keur` (replaced, R-PAR-2) | True | False | **RAISE** (R-PAR-2 blocking) |
| `senior_idc_keur` (replaced, R-PAR-2) | True | True | OK (pass) |
| `shl_idc_keur` (replaced) | True | n/a | OK (pass) |
| `shl_idc_keur` (replaced) | False | n/a | RAISE (no promotion) |
| `shl_amount_keur` (replaced) | True | n/a | OK |
| `shl_opening_balance_keur` (replaced) | True | n/a | OK |
| `equity_total_keur` (derived) | True | n/a | OK (parity assumed) |
| `equity_total_keur` (derived) | False | n/a | RAISE |
| `reserves_keur` (retained) | * | * | OK (pass-through) |
| `vat_operating` (retained) | * | * | OK |
| `financing_fees_keur` (retained) | * | * | OK |
| `commitment_fee_keur` (retained) | * | * | OK |

### 5.3 C8 design contract

- The guard is **not implemented** in C8. C8 designs the
  contract.
- The guard signature and expected behavior are recorded in
  this document (§5.1, §5.2).
- C9 will scaffold the guard module in a future phase. C9
  must not implement the guard with behavior that deviates
  from §5.2.
- The guard is **NOT wired into the live waterfall path** in
  C8 or C9. It is callable from tests and from future
  controlled-enablement PRs (C10/C11).

### 5.4 Testable without runtime changes

The guard contract (§5.1, §5.2) is testable in C8 as a
**design-contract test** that:

- Verifies the **design exists** in this document.
- Verifies the **future module location** is reserved (e.g.
  `app/services/construction_runtime_seam.py`).
- Verifies the **signature** is documented in the design.
- Verifies the **expected behavior table** (§5.2) is
  consistent with the POLICY_TABLE.

The test does **not** import a guard module. It does **not**
exercise the guard. It does **not** depend on runtime
behavior.

### 5.5 R-PAR-2 as a guard parameter

The `rpar2_resolved: bool = False` parameter in §5.1 is the
explicit carrier of the R-PAR-2 status. By default it is
`False`, which means the seam treats R-PAR-2 as unresolved
unless explicitly told otherwise. This makes the guard
fail-closed: any caller that does not affirmatively declare
R-PAR-2 resolution will be blocked from promoting
`senior_idc_keur`.

This is a deliberate design choice. C1, C2, and C7 all
treat R-PAR-2 as unresolved. The seam must inherit this
default.

---

## 6. Import-contract design

C8 designs an import-contract test that statically verifies the
bridge is not imported by runtime modules.

### 6.1 Forbidden importers

The following modules MUST NOT import
`domain.construction.opening_bridge` (or any of its public
symbols: `POLICY_TABLE`, `build_opening_balance_bridge`,
`OpeningBalanceBridgeResult`, `BridgeAuditRow`, etc.) in C8
or in C9:

- `app/`
- `main_web.py`
- `main_api.py`
- `app/services/` (runtime service modules)
- `app/waterfall_core.py` (and any `domain/waterfall*` module)
- `app/waterfall_runner.py`
- `app/persistence/`
- `static/`

### 6.2 Test design

The import-contract test is implemented in C8 as a
**static-AST test** that:

- Walks each file in the forbidden-importer list.
- Parses the file with `ast.parse(src)`.
- Iterates `ast.walk(tree)` and inspects every
  `ast.Import` and `ast.ImportFrom` node.
- Asserts that no node imports from
  `domain.construction.opening_bridge` or any of its
  sub-paths.
- The test is read-only and does not import the bridge
  module.

### 6.3 C8 test scope

C8 adds the import-contract test as part of its test file
(`tests/test_phase_c8_layer5_runtime_seam_design_gate.py`).
The test covers all files in the forbidden-importer list at
the time C8 is merged. Future files added to those paths
must be covered by future import-contract tests in C9+.

### 6.4 Future C9+ extension

When C9 scaffolds the seam module (in a future phase, not
C8), the import-contract test will be **relaxed** to allow
the seam module itself to import the bridge. The test will
be updated to reflect the new exception. This update is
explicit and is part of the C9 deliverables, not C8.

---

## 7. Future C9 implementation boundaries

C8 defines the C9 deliverable scope. C9 is the first
implementation phase of the seam.

### 7.1 C9 may implement only

- The seam module skeleton
  (e.g. `app/services/construction_runtime_seam.py`).
- The no-promotion guard function
  (`assert_no_construction_runtime_promotion`) with behavior
  per §5.1, §5.2.
- An audit-only visibility helper that exposes the bridge
  output to read-only consumers (e.g. an audit endpoint that
  does not affect runtime).
- Tests for the seam module and the guard.
- The import-contract test (§6) plus any updates needed for
  the seam module to be exempt from the contract.

### 7.2 C9 must NOT

- **Flip feature flags.** `use_construction_schedule_engine`
  remains `False` (default-off).
- **Route values into the waterfall.** The seam is a
  read-side adapter, not a write-side consumer. The seam
  exposes bridge output; the waterfall continues to consume
  manual inputs.
- **Change runtime outputs.** The runtime waterfall output
  must be byte-identical to C8 baseline (within rounding
  tolerance) after C9 scaffolding.
- **Change tax, debt, depreciation, CFADS, or any
  formula.** C9 is a structural phase, not a numerical
  phase.
- **Change persistence or schema.** No new tables, no new
  JSON, no new in-memory state.
- **Change UI.** No new templates, no new partials, no new
  HTMX attributes.
- **Mutate `use_construction_schedule_engine` to `True` for
  any project.** TUHO and Oborovo remain in
  `False` (audit-only / runtime-off).

### 7.3 C9 deliverable count

C9 will produce:

- 1 new module: `app/services/construction_runtime_seam.py`
  (scaffolding only, no waterfall integration).
- 1 new test file:
  `tests/test_phase_c9_construction_runtime_seam.py`.
- 1 new doc:
  `docs/phase_c9_construction_runtime_seam_scaffolding.md`.
- 1 new report:
  `reports/phase_c9_construction_runtime_seam_scaffolding.json`.

C9 is also design-contract heavy. The seam module will be
heavily commented to make the no-promotion intent obvious.

---

## 8. Future promotion path

C8 defines a strict C9→C10→C11 path. C10 and C11 are
**separated** to prevent accidental cross-project promotion.

### 8.1 C9 — Seam scaffolding

- Implement the seam module (per §7.1).
- Implement the no-promotion guard.
- All 11 fields remain non-promoted.
- `use_construction_schedule_engine` remains `False`.
- Tests verify: seam exists, guard exists, import-contract
  holds, no runtime change.

### 8.2 C10 — TUHO controlled promotion

- Flip `use_construction_schedule_engine` to `True` for
  **TUHO only** (via per-project opt-in, not a global flag).
- The seam routes the bridge output for the 4 replaced fields
  to the runtime waterfall for TUHO:
  - `shl_idc_keur`
  - `shl_amount_keur`
  - `shl_opening_balance_keur`
  - `senior_idc_keur` (only if R-PAR-2 is resolved or formally
    accepted; otherwise remains audit-side only)
- The 2 frozen fields (`senior_opening_balance_keur`,
  `capex_keur`) are explicitly **not promoted** (the guard
  raises `PermissionError` if anyone tries).
- The 4 retained fields pass through unchanged.
- The 1 derived field (`equity_total_keur`) is promoted with
  parity_ok.
- TUHO parity baseline is captured before C10.
- Tests verify: TUHO parity is **unchanged** (within rounding
  tolerance) after C10. The whole point of C10 is to confirm
  the seam does not break parity.

### 8.3 C11 — Oborovo controlled promotion

- Same as C10 but for **Oborovo only**.
- Oborovo parity baseline is captured before C11.
- Tests verify: Oborovo parity is **unchanged** after C11.

### 8.4 Why C10 and C11 are separated

- **Risk isolation.** If a promotion path is broken for
  TUHO, Oborovo is unaffected. If a promotion path is
  broken for Oborovo, TUHO is not regressed.
- **Cleaner rollback.** A failed C10 can be reverted without
  touching C11.
- **Sequential learning.** The TUHO promotion reveals
  patterns (audit row counts, drift, identity checks) that
  inform the Oborovo promotion.
- **Reviewer burden.** Smaller PRs are easier to review
  thoroughly.

### 8.5 Promotion gate criteria

Before C10 can be opened:

- C9 merged.
- C8 review approved.
- C7 review approved.
- All C1–C7 tests still pass.
- C9 tests pass.
- `use_construction_schedule_engine` default-off confirmed.

Before C11 can be opened:

- C10 merged.
- TUHO parity baseline unchanged after C10 promotion.
- All C1–C9 tests still pass.
- C10 tests pass.

---

## 9. Risk register

C8 records the following risks. Each risk has a mitigation
that is part of the C8 design.

### 9.1 Double-counting

- **Risk:** the bridge output is added on top of the manual
  value rather than replacing it. This silently inflates the
  senior debt service basis, the SHL opening balance, etc.
- **Mitigation:** C7's `POLICY_TABLE` declares
  `replaced`/`frozen`/`retained`/`derived` for every field.
  The seam is the structural enforcer: it routes the bridge
  output as a *replacement* for `replaced` fields, never as
  an *addition*. The no-promotion guard raises
  `PermissionError` if anyone tries to add on top.
- **Detection:** the audit table records the selected
  runtime value with its source. Any deviation is visible.

### 9.2 Frozen field promotion

- **Risk:** the seam is bypassed or a future refactor
  accidentally promotes a frozen field. The runtime then
  uses the bridge value for `senior_opening_balance_keur` or
  `capex_keur`, breaking parity.
- **Mitigation:** §3.2 hard rule. The guard raises
  `PermissionError` for frozen fields *unconditionally*. The
  guard is enforced by tests in C8 and by integration tests
  in C9+.

### 9.3 R-PAR-2 leakage

- **Risk:** the senior IDC effective-rate caveat is treated
  as resolved when it is not, and the seam routes
  `senior_idc_keur` to runtime prematurely. This inflates
  the senior debt service basis by the capitalized senior
  IDC.
- **Mitigation:** §4.5 rule. The guard's
  `rpar2_resolved: bool = False` default makes the seam
  fail-closed for R-PAR-2. Any caller that does not
  affirmatively declare resolution is blocked.
- **Process gate:** R-PAR-2 resolution requires a separate
  workstream PR, not a side-effect of the C9/C10/C11 path.

### 9.4 Hidden runtime import

- **Risk:** a runtime module (e.g. `app/waterfall_core.py`)
  imports the bridge directly, bypassing the seam. This
  breaks the structural invariant and creates an unaudited
  promotion path.
- **Mitigation:** §6 import-contract test. The test walks
  the AST of every forbidden-importer file and asserts that
  no `ast.Import` or `ast.ImportFrom` node targets
  `domain.construction.opening_bridge`. The test runs in
  C8 and C9+.

### 9.5 Feature flag misuse

- **Risk:** `use_construction_schedule_engine` is flipped
  globally (not per-project) in C9 or C10, affecting Generic
  Wind / Generic Solar / future projects unintentionally.
- **Mitigation:** §7.2 hard rule. C9 must not flip the flag.
  C10/C11 must use a **per-project opt-in** (e.g. by project
  factory or by saved-state), not a global flag flip. The
  default-off invariant is preserved.

### 9.6 Tax / depreciation downstream impact

- **Risk:** promoting the bridge output (e.g. a higher
  opening senior balance) changes the debt service
  amortization, which changes interest, which changes the
  tax computation (loss windows, R35, R67), which changes
  CFADS, which changes distributions. This is a cascading
  change that is hard to isolate.
- **Mitigation:** §8 promotion gate criteria. C10/C11
  require **parity unchanged** as a hard gate. If the
  parity delta is non-zero (beyond rounding), the promotion
  is rejected and the workstream is split into smaller
  PRs.

### 9.7 Risk matrix

| Risk | Severity | Likelihood | Mitigation | C8 design coverage |
|---|---|---|---|---|
| Double-counting | High | Medium | POLICY_TABLE + guard | §3, §5 |
| Frozen field promotion | High | Low | §3.2 hard rule + guard | §3.2, §5 |
| R-PAR-2 leakage | High | Medium | §4.5 fail-closed default | §4.5, §5.5 |
| Hidden runtime import | High | Low | §6 import-contract test | §6 |
| Feature flag misuse | Medium | Low | §7.2 + §8.5 per-project opt-in | §7.2, §8.5 |
| Tax/depreciation downstream | High | Medium | §8 parity gate | §8 |

---

## 10. Recommendation

### 10.1 Choice: **B. More design needed**

Rationale:

1. **C8 is a design gate, not an implementation.** C8
   produces 3 files (doc + report + test file). The design
   is complete and structurally consistent, but the seam
   itself does not exist yet. C9 will implement it.
2. **POLICY_TABLE enforcement is structurally specified.**
   Replaced, frozen, retained, derived fields are all
   addressed. Frozen fields are explicitly blocked from
   promotion. The guard signature and expected behavior
   table are recorded.
3. **R-PAR-2 is preserved as a blocking constraint.** The
   guard's `rpar2_resolved: bool = False` default makes the
   seam fail-closed. Senior IDC promotion is blocked until
   R-PAR-2 is resolved or formally accepted.
4. **Import-contract test is specified.** C8 includes the
   AST-level test in its test file. The test is
   design-contract: it verifies the design exists and the
   future module location is reserved, but it does not
   import any seam module (which does not exist yet).
5. **Promotion path is strict and separated.** C9
   (scaffolding) → C10 (TUHO) → C11 (Oborovo). Each phase
   is gated by a parity-unchanged invariant.

### 10.2 What would unblock "A. Ready for C9"

- Reviewer sign-off on §3 POLICY_TABLE enforcement.
- Reviewer sign-off on §5.1 guard signature and §5.2
  expected behavior.
- Reviewer sign-off on §8 promotion path.
- Confirmation that the C8 import-contract test is
  implementable as a static-AST test without runtime
  changes (it is; see §6.2).

### 10.3 What would unblock "C. Defer"

- A pivot in priorities (not anticipated).
- A decision to skip the seam entirely and route the bridge
  output directly to the waterfall (this is rejected by
  §3.2 and §3.5; it would violate the frozen-field rule).

### 10.4 Multi-phase path status

| Phase | Scope | Status | SHA |
|---|---|---|---|
| C1 | Design gate | ✅ merged | `5fccc3a` |
| C2 | SHL IDC convention + bridge design | ✅ merged | `59f9e3d` |
| C3 | Construction parity framework | ✅ merged | `aa800a5` |
| C4 | Snapshot scaffolding | ✅ merged | `dcc30b6` |
| C5 | Engine comparison tests | ✅ merged | `2d8a91c` |
| C6 | Bridge implementation plan | DRAFT | `c72bc94` (PR #548) |
| C7 | Layer 4 bridge module | ✅ MERGED | `b28723b` (PR #549) |
| **C8** | **Layer 5 seam design gate** | **DRAFT** | — |
| C9 | Layer 5 seam scaffolding | future | — |
| C10 | TUHO controlled promotion | future | — |
| C11 | Oborovo controlled promotion | future | — |

### 10.5 Stop after report

C8 is a **design gate** in the strictest sense. It produces
3 files (doc + report + test file). It does not implement
the seam, does not flip any flag, does not change runtime,
does not modify any production file.

Deliverables: this document +
`reports/phase_c8_layer5_runtime_seam_design_gate.json` +
`tests/test_phase_c8_layer5_runtime_seam_design_gate.py`.

### 10.6 Project status confirmation (C8 invariant)

| Project | Status |
|---|---|
| **TUHO** (TUHO-WIND-1) | **Level 2** — unchanged ✓ |
| **Oborovo** | **Level 2** — unchanged ✓ |
| **Generic Wind** | **Level 1** — unchanged ✓ |
| **Generic Solar** | **Level 1** — unchanged ✓ |

### 10.7 rc1 confirmation

`b425a0708719eaa5e1d922b1008e5609758e0ad4` reachable on
`origin/main` ✓

### 10.8 Feature flag confirmation

`use_construction_schedule_engine` remains **default-off** ✓
(declared in `domain/inputs.py:147`)
