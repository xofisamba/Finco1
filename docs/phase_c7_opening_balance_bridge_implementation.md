# Phase C7 - Layer 4 Opening Balance Bridge Offline Implementation

> **Scope label:** **OFFLINE DOMAIN IMPLEMENTATION. NO RUNTIME
> WIRING. NO WATERFALL CHANGES.**
>
> Type: Domain implementation (offline, pure)
> Status: DRAFT
> Date: 2026-06-08
> Base SHA: `2d8a91c` (post-Phase C5)
> Branch: `phase-c7-opening-balance-bridge-offline-implementation`
> Hard constraints: **NO runtime wiring, NO waterfall changes, NO
> app changes, NO main_web/main_api changes, NO persistence changes,
> NO schema changes, NO feature flags, NO CAPEX formula changes, NO
> debt service changes, NO tax changes, NO depreciation changes, NO
> IDC runtime promotion, NO project status changes, NO UI changes.**

---

## 0. Purpose

C1–C6 produced a complete construction parity framework at the
design and test-scaffolding level. C6 (DRAFT,
`origin/phase-c6-opening-balance-bridge-implementation-plan`)
defined the exact API / dataclass shape and the
double-counting guard rules for the Layer 4 Opening Balance
Bridge. C6 explicitly stopped at the plan and **deferred
implementation** to C7.

This C7 phase is the **first domain implementation phase** in
the C-series. It implements:

- The bridge module (`domain/construction/opening_bridge.py`).
- The 8 frozen dataclasses specified in C6 §5.
- The 1 exception class (`BridgeIdentityError`).
- The module-level `POLICY_TABLE` constant (11 entries from
  C2 §2.1).
- The single public function
  `build_opening_balance_bridge(input) -> result`.

C7 does **not**:

- Wire the bridge into runtime (Layer 5 is C8+).
- Modify any other file in `domain/` or `app/`.
- Touch `main_web.py`, `main_api.py`, `static/`.
- Change any formula (CAPEX, debt, tax, depreciation, IDC).
- Change any project status.
- Flip any feature flag.
- Persist any data.
- Render any UI.

C7 produces **4 files only**:

- `domain/construction/opening_bridge.py` (the bridge module).
- `tests/test_phase_c7_opening_balance_bridge.py` (the test file).
- `docs/phase_c7_opening_balance_bridge_implementation.md` (this).
- `reports/phase_c7_opening_balance_bridge_implementation.json`.

---

## 1. C1–C6 stack verification

C7 is the first implementation phase. Before writing code, C7
verifies the C1–C6 stack is complete and consistent.

### 1.1 C1 — Construction / IDC Design Gate (merged `5fccc3a`)

C1 produced the design gate with 5 blockers. C1 status post-C6:
**4 of 5 blockers closed (or planned). 1 deferred (senior IDC
base-rate modelling — separate workstream).**

### 1.2 C2 — SHL IDC Convention + Opening Balance Bridge Design
(merged `59f9e3d`)

C2 produced:

- **Convention B** (Excel full-source elapsed compound) is the
  authoritative SHL IDC convention. Convention A is the current
  convention and remains so until the C7–C9 sequence is complete.
- **Layer 4 bridge design** (§3 inputs, §3.3 outputs, §3.4
  algorithm, §3.5 location, §3.7 output contract).
- **§4 audit table**: 14 columns, 5 invariants, 3 example rows.
- **§6 validation requirements** (8 items in §6.7 readiness
  checklist).

C2 status post-C6: **design complete, implementation in C7.**

### 1.3 C3 — Construction Parity Snapshot Design (merged `aa800a5`)

C3 produced the construction-period parity framework. C3 status
post-C6: **complete.**

### 1.4 C4 — Snapshot Scaffolding (merged `dcc30b6`)

C4 produced the frozen golden snapshot files. C4 status:
**complete. C7 reads but does not modify the snapshots.**

### 1.5 C5 — Engine Comparison Tests (merged `2d8a91c`)

C5 produced 93 engine-comparison tests. C5 status post-C6:
**complete. C7 does not re-implement the engine; it consumes the
engine output.**

### 1.6 C6 — Bridge Implementation Plan (DRAFT, not yet merged)

C6 produced the implementation plan. C6 status: **DRAFT.** C7
implements what C6 designed.

### 1.7 C1–C6 preconditions for C7

| Precondition | Status |
|---|---|
| C1 design gate merged | ✅ done |
| C2 SHL IDC convention decided (Convention B) | ✅ done |
| C2 §3.7 bridge output contract | ✅ done |
| C2 §4.1 audit table schema (14 columns) | ✅ done |
| C2 §4.5 audit table invariants | ✅ done |
| C2 §2.1 per-field policy | ✅ done |
| C3 parity framework | ✅ done |
| C4 snapshot files (TUHO + Oborovo) | ✅ done |
| C5 engine comparison baseline | ✅ done |
| C6 API / dataclass shape | ✅ done (DRAFT) |
| C6 §6.1 double-counting guard rules | ✅ done (DRAFT) |
| C6 §6.4 senior IDC effective-rate caveat | ✅ done (DRAFT) |
| C7 test plan (C2 §6.4, §6.5, §6.6) | ✅ done (this phase) |
| rc1 SHA `b425a07...` reachable | ✅ done |
| `use_construction_schedule_engine` default-off | ✅ done |

**All preconditions for C7 are met. C7 can implement Layer 4.**

---

## 2. Implementation summary

C7 implements the bridge as a single pure function with 8 frozen
input/output dataclasses. The function:

1. Receives an `OpeningBalanceBridgeInput` (containing a
   `ConstructionScheduleResult`, manual overrides, project
   assumptions, replacement policy, parity references, and
   bridge version).
2. Iterates over the 11 policy fields and computes one
   `BridgeAuditRow` per field.
3. Returns an `OpeningBalanceBridgeResult` with the 6 numeric
   opening-balance fields plus the audit table and metadata.

### 2.1 Module structure

```text
domain/construction/opening_bridge.py
├── Constants (C2 §2.1 mirror)
│   ├── POLICY_VERSION = "C2-1.0"
│   ├── BRIDGE_VERSION = "C7-1.0"
│   ├── IDENTITY_TOLERANCE_KEUR = 0.001
│   ├── Selection reasons: REPLACED, FROZEN, RETAINED, DERIVED
│   ├── Override statuses: NO_OVERRIDE, MANUAL_ACTIVE, CONSTRUCTION_ACTIVE, COMPOSITE_NO_OVERRIDE
│   ├── Guards: SINGLE_SOURCE, COMPOSITE
│   └── Parity statuses: OK, DRIFT, UNKNOWN, NOT_APPLICABLE
├── Input dataclasses (frozen)
│   ├── ManualOverrideRow
│   ├── BridgeFieldPolicy
│   ├── ParityReferenceRow
│   ├── ProjectAssumptions
│   └── OpeningBalanceBridgeInput
├── Output dataclasses (frozen)
│   ├── BridgeAuditRow (14 columns per C2 §4.1)
│   ├── BridgeMetadata
│   └── OpeningBalanceBridgeResult (6 numeric fields + audit + metadata)
├── Exception
│   └── BridgeIdentityError(ValueError)
├── Module-level constant
│   └── POLICY_TABLE (11 entries from C2 §2.1)
├── Helper functions
│   ├── _lookup_manual
│   ├── _lookup_parity
│   ├── _construction_value
│   ├── _parity_status
│   ├── _parity_delta
│   ├── _compute_selected_value
│   ├── _override_status
│   ├── _double_counting_guard
│   ├── _lookup_audit
│   ├── _lookup_policy
│   └── _identity_ok
└── Public function
    └── build_opening_balance_bridge(input) -> OpeningBalanceBridgeResult
```

### 2.2 Algorithm

The bridge applies the per-field policy for each of the 11
fields, builds an audit row per field, computes the 6 numeric
output fields, and asserts the opening-balance identities.

The algorithm is per C6 §2.4 and C2 §3.4. Each step is a
single responsibility and is independently testable.

### 2.3 Opening balance identities

The bridge asserts the following identities (C2 §7.4), but **only
for opening balances that are `replaced` by the construction
engine** (refined by C6 §6.4 asymmetry):

- `opening_senior == total_senior_draw + capitalized_senior_idc`
  (within ±0.001 kEUR) — only when `senior_opening_balance_keur`
  policy is `replaced`.
- `opening_shl == total_shl_draw + capitalized_shl_idc`
  (within ±0.001 kEUR) — only when `shl_opening_balance_keur`
  policy is `replaced`.
- `equity_contribution_at_cod == total_equity_draw` (within
  ±0.001 kEUR) — only when `equity_total_keur` policy is
  `replaced`.

When a field is `frozen`, the identity is **not** asserted
because the manual value is the authority by definition and may
not include the capitalized IDC. For TUHO, this is the case
for `senior_opening_balance_keur` (frozen = 43,359.274, while
the engine value is 44,878.838 = 43,359.274 + 1,519.564 IDC).

If any identity fails (for replaced fields), the bridge
**raises** `BridgeIdentityError`.

### 2.4 Senior IDC effective-rate caveat (C1 R-PAR-2)

C6 §6.4 specifies the asymmetry: `senior_idc_keur` is
`replaced` (engine wins, parity_ok) but
`senior_opening_balance_keur` is `frozen` (manual wins,
parity_drift) until the senior IDC is modelling-correct.

C7 preserves this asymmetry:

- The `senior_idc_keur` audit row records
  `c1_blocker_reference = "blocker_5_R-PAR-2"`,
  `selection_reason = "replaced"`,
  `parity_status = "parity_ok"`.
- The `senior_opening_balance_keur` audit row records
  `c1_blocker_reference = "blocker_5_R-PAR-2"`,
  `selection_reason = "frozen"`,
  `parity_status = "parity_drift"`.

### 2.5 Forbidden imports

The bridge does NOT import from:

- `domain.inputs` (the `Project` dataclass)
- `domain.waterfall*` (any waterfall module)
- `app.*` (any app module)
- `main_web`, `main_api`
- `static.*` (UI)

C7 enforces this with an AST-level guard in the test file
(`TestNoForbiddenImports`). The bridge module imports only:

- `datetime` (stdlib)
- `dataclasses` (stdlib)
- `typing` (stdlib)
- `__future__` (stdlib)
- `domain.construction.result` (the result types)

No engine call. No persistence. No I/O. No side effects.

---

## 3. Implementation details

### 3.1 `POLICY_TABLE` mirrors C2 §2.1

```text
POLICY_TABLE[0]  : shl_idc_keur              policy=replaced   c1=blocker_1_R-PAR-1
POLICY_TABLE[1]  : shl_amount_keur           policy=replaced   c1=
POLICY_TABLE[2]  : shl_opening_balance_keur  policy=replaced   c1=
POLICY_TABLE[3]  : senior_opening_balance_keur policy=frozen    c1=blocker_5_R-PAR-2
POLICY_TABLE[4]  : senior_idc_keur           policy=replaced   c1=blocker_5_R-PAR-2
POLICY_TABLE[5]  : capex_keur                policy=frozen     c1=
POLICY_TABLE[6]  : reserves_keur             policy=retained   c1=
POLICY_TABLE[7]  : vat_operating             policy=retained   c1=
POLICY_TABLE[8]  : financing_fees_keur       policy=retained   c1=
POLICY_TABLE[9]  : commitment_fee_keur       policy=retained   c1=
POLICY_TABLE[10] : equity_total_keur         policy=derived    c1=blocker_5_R-PAR-5
```

The 4 replaced fields (shl_idc, shl_amount, shl_opening,
senior_idc) yield parity_ok against the C4 snapshots. The 2
frozen fields (senior_opening, capex) preserve manual values.
The 4 retained fields use manual values without a construction
source. The 1 derived field (equity_total) uses the manual value
as a composite; the construction equity is recorded for audit.

### 3.2 Output values

For TUHO (against the C4 snapshot):

| Field | Value | Policy | Source |
|---|---|---|---|
| `opening_senior_balance_at_cod_keur` | 43,359.274 | frozen | manual |
| `opening_shl_balance_at_cod_keur` | 32,703.864 | replaced | engine |
| `equity_contribution_at_cod_keur` | 500.000 | derived | manual |
| `capitalized_senior_idc_keur` | 1,519.564 | replaced | engine |
| `capitalized_shl_idc_keur` | 3,568.688 | replaced | engine |
| `financing_fee_treatment_keur` | 0.000 | retained | manual |

For Oborovo (against the C4 snapshot):

| Field | Value | Policy | Source |
|---|---|---|---|
| `opening_senior_balance_at_cod_keur` | 42,852.267 | frozen | manual |
| `opening_shl_balance_at_cod_keur` | 15,790.436 | replaced | engine |
| `equity_contribution_at_cod_keur` | 500.000 | derived | manual |
| `capitalized_senior_idc_keur` | 1,086.032 | replaced | engine |
| `capitalized_shl_idc_keur` | 1,169.662 | replaced | engine |
| `financing_fee_treatment_keur` | 0.000 | retained | manual |

### 3.3 Audit table summary

The audit table has **11 rows** (one per policy field) and **14
columns** (per C2 §4.1). For TUHO:

| Field | selection_reason | override_status | guard | parity_status | c1_blocker |
|---|---|---|---|---|---|
| shl_idc_keur | replaced | construction_override_active | single_source | parity_ok | blocker_1_R-PAR-1 |
| shl_amount_keur | replaced | construction_override_active | single_source | parity_ok | |
| shl_opening_balance_keur | replaced | construction_override_active | single_source | parity_ok | |
| senior_opening_balance_keur | frozen | manual_override_active | single_source | parity_drift | blocker_5_R-PAR-2 |
| senior_idc_keur | replaced | construction_override_active | single_source | parity_ok | blocker_5_R-PAR-2 |
| capex_keur | frozen | manual_override_active | single_source | parity_ok | |
| reserves_keur | retained | no_override | single_source | parity_not_applicable | |
| vat_operating | retained | no_override | single_source | parity_not_applicable | |
| financing_fees_keur | retained | no_override | single_source | parity_not_applicable | |
| commitment_fee_keur | retained | no_override | single_source | parity_not_applicable | |
| equity_total_keur | derived | composite_no_override | composite | parity_ok | blocker_5_R-PAR-5 |

The Oborovo audit table has the same structure; only the
values differ.

---

## 4. Test counts

C7 test file: `tests/test_phase_c7_opening_balance_bridge.py`.

Categories:

- File existence (3 tests)
- Module constants (6 tests)
- POLICY_TABLE mirror C2 §2.1 (16 tests)
- Dataclasses frozen (8 tests)
- BridgeIdentityError (2 tests)
- TUHO bridge output (6 tests)
- Oborovo bridge output (6 tests)
- Audit table size (2 tests)
- Audit table columns (3 tests)
- Audit row invariants (8 tests)
- TUHO per-field policy (11 tests)
- Senior IDC asymmetry (3 tests)
- Bridge metadata (3 tests)
- BridgeIdentityError missing manual (4 tests)
- No-caller-mutation (5 tests)
- No-forbidden-imports (2 tests)
- No-engine-call (2 tests)
- Forbidden paths (10 tests, including parametrized)
- C4 snapshots unchanged (2 tests)
- rc1 SHA reachable (1 test)
- Feature flag unchanged (1 test)
- Project statuses unchanged (2 tests)
- Senior IDC effective-rate caveat (3 tests)
- C5 engine comparison still passes (2 tests)
- No double-counting (2 tests, parametrized)
- Pure function (1 test)
- Result is frozen dataclass (3 tests)

**Total: 118 tests** (all passing).

Combined with C1–C6: 118 + 848 = **966 tests passing**.

---

## 5. Hard constraints — ALL met

- NO runtime wiring: bridge is not imported by `app/`,
  `main_web.py`, or `main_api.py`. AST guard verifies.
- NO waterfall changes: bridge does not import
  `domain.waterfall*`. AST guard verifies.
- NO app changes: 0 files added or modified in `app/`.
- NO main_web/main_api changes: 0 files added or modified.
- NO persistence changes: 0 files added or modified in any
  persistence layer.
- NO schema changes: no database, no JSON, no in-memory state
  schema changes.
- NO feature flags: `use_construction_schedule_engine` remains
  default-off.
- NO CAPEX formula changes: capex_keur is `frozen` (manual wins).
- NO debt service changes: bridge does not compute debt service.
- NO tax changes: tax engine untouched.
- NO depreciation changes: depreciation engine untouched.
- NO IDC runtime promotion: the construction engine remains
  audit-only.
- NO project status changes: TUHO and Oborovo remain Level 2.
- NO UI changes: 0 files added or modified in `static/`.

---

## 6. Confirmation: project statuses unchanged

| Project | Status | Snapshot Hash | Bridge Result |
|---|---|---|---|
| **TUHO** (TUHO-WIND-1) | **Level 2** (unchanged) | `798399ea` | matches C4 snapshot |
| **Oborovo** | **Level 2** (unchanged) | `4e60d076` | matches C4 snapshot |
| **Generic Wind** | **Level 1** (unchanged) | — | n/a |
| **Generic Solar** | **Level 1** (unchanged) | — | n/a |

---

## 7. Confirmation: rc1 untouched

`b425a0708719eaa5e1d922b1008e5609758e0ad4` reachable on
`origin/main` ✓

---

## 8. Recommendation

### Choice: **B. More bridge validation needed**

Rationale:

1. **C6 was a plan; C7 is the implementation. C7 implements
   exactly what C6 designed.** No deviation. No new design
   surface area. The bridge output matches the C4 snapshots
   for both TUHO and Oborovo within tolerance.
2. **The audit table and the double-counting guard are
   enforced.** Every opening balance has exactly one source
   (manual or construction). The senior IDC asymmetry is
   preserved.
3. **The forbidden-imports / no-engine-call / no-mutation
   guards are all in place.** The bridge cannot be used as a
   runtime mutation vector.
4. **Layer 5 (runtime integration seam) is the next step.**
   Layer 5 must consume `OpeningBalanceBridgeResult` and route
   it to the waterfall. Layer 5 is C8 (design) and C9
   (implementation).
5. **The senior IDC effective-rate caveat (C1 R-PAR-2) is still
   a separate workstream.** The bridge records the
   asymmetry but does not fix the underlying modelling
   issue. This is by design — the bridge is a *wiring* of
   the C2 policy, not a fix for the senior IDC method.

### What would unblock "A. Ready for C8"

- A second pair of eyes review of the bridge code (C2 §6.7
  item 8, always deferred).
- A formal decision on the senior IDC method (C1 R-PAR-2,
  separate workstream).
- A Layer 5 (runtime integration seam) design document
  (C8 deliverable).

### What would unblock "C. Defer"

- A pivot in priorities away from construction (not
  anticipated).
- A decision that the bridge should be a different shape
  (no precedent for this).

None of these defer signals are present. The bridge
implementation is complete and the path to C8 is clear.

### Multi-phase path status

| Phase | Scope | Status | SHA |
|---|---|---|---|
| C1 | Design gate | ✅ merged | `5fccc3a` |
| C2 | SHL IDC convention + bridge design | ✅ merged | `59f9e3d` |
| C3 | Construction parity framework | ✅ merged | `aa800a5` |
| C4 | Snapshot scaffolding | ✅ merged | `dcc30b6` |
| C5 | Engine comparison tests | ✅ merged | `2d8a91c` |
| C6 | Bridge implementation plan | DRAFT | — |
| **C7** | **Layer 4 bridge module** | **DRAFT** | — |
| C8 | Layer 5 runtime seam design | future | — |
| C9 | Layer 5 runtime seam implementation | future | — |
| C10 | Opt-in flag flip + TUHO promotion | future | — |
| C11 | Oborovo promotion | future | — |

---

## 9. Stop after report

C7 is the **first implementation phase** in the C-series. It
adds 4 files, 0 modifications, and 118 tests. It does not wire
the bridge into runtime, does not modify any existing file,
and does not change any project status or feature flag.

Deliverables: this document +
`reports/phase_c7_opening_balance_bridge_implementation.json` +
the bridge module +
the test file.
