# Phase C6 - Layer 4 Opening Balance Bridge Implementation Plan

> **Scope label:** **DESIGN / IMPLEMENTATION PLAN ONLY. DOCS ONLY.
> NO CODE. NO RUNTIME. NO DOMAIN. NO FORMULA CHANGES.**
>
> Type: DESIGN / IMPLEMENTATION PLAN
> Status: DRAFT
> Date: 2026-06-08
> Base SHA: `2d8a91c` (post-Phase C5)
> Branch: `phase-c6-opening-balance-bridge-implementation-plan`
> Hard constraints: **NO code, NO runtime changes, NO domain changes,
> NO schema changes, NO persistence changes, NO feature flags, NO
> formula changes, NO CAPEX/debt/tax/depreciation/IDC changes, NO
> project status changes. Docs / reports / tests only.**

---

## 0. Purpose

C1–C5 (merged `5fccc3a`..`2d8a91c`) produced a complete
**construction parity framework** at the design and test-scaffolding
level. C5 explicitly stopped at engine-comparison tests and
**deferred Layer 4 bridge implementation** to C6.

This C6 phase produces a **strict implementation plan** for the
Layer 4 Opening Balance Bridge. It is the **last design gate**
before any first domain implementation. C6 is **docs only** —
no code, no runtime, no domain, no formula changes. C6
**designates the future C7** as the actual implementation phase.

### 0.1 What C6 is

C6 is a **plan**. It:

- Verifies the C1–C5 stack (no surprises, no missing
  preconditions).
- Defines the **exact scope** of Layer 4 (what it implements,
  what it does not).
- Defines the **exact non-scope** (what it must never touch).
- Proposes the **exact file list** for the future C7
  implementation.
- Defines the **API / dataclass shape** that C7 must build.
- Defines the **double-counting guard rules** that C7 must
  enforce.
- Defines the **validation plan** that C7 must satisfy.
- Recommends **A / B / C** (A: ready for C7, B: more design
  needed, C: defer).

### 0.2 What C6 is not

C6 is **not** an implementation phase. C6 does not:

- Add `domain/construction/opening_bridge.py` (that is C7+).
- Add any new file in `domain/`.
- Add any new file in `app/`.
- Modify any existing code in `domain/` or `app/`.
- Touch `main_web.py`, `main_api.py`, `static/`.
- Change any formula (CAPEX, debt, tax, depreciation, IDC).
- Change any project status.
- Change any feature flag.
- Change any persistence schema.

C6 produces **3 files only**:

- `docs/phase_c6_opening_balance_bridge_implementation_plan.md` (this)
- `reports/phase_c6_opening_balance_bridge_implementation_plan.json`
- `tests/test_phase_c6_opening_balance_bridge_implementation_plan.py`

The test file is a **design-doc / report / non-scope / API shape /
guards / recommendation / hard-constraints** test, not a runtime
test. It asserts that this plan is correct, complete, and
self-consistent.

---

## 1. Verify C1–C5 stack

C6 is the last design gate. Before defining Layer 4 scope, C6
verifies the C1–C5 stack is complete and consistent.

### 1.1 C1 — Construction / IDC Design Gate (merged `5fccc3a`)

C1 produced the design gate doc with 5 blockers:

1. SHL IDC convention unresolved → **resolved in C2** (Convention B)
2. Layer 4 Opening Balance Bridge missing → **designed in C2, planned in C6 (this doc)**
3. Layer 5 Runtime Integration Seam missing → **deferred to C8+**
4. Construction-period parity snapshot missing → **shipped in C3, scaffolded in C4, engine-compared in C5**
5. Senior IDC effective-rate brittleness → **deferred to separate workstream** (not in C-series)

C1 status post-C5: **4 of 5 blockers closed (or planned). 1 deferred
(senior IDC base-rate modelling).**

### 1.2 C2 — SHL IDC Convention + Opening Balance Bridge Design (merged `59f9e3d`)

C2 produced:

- **Convention B** (Excel full-source elapsed compound) is the
  authoritative SHL IDC convention. Convention A is the current
  convention and remains so until the C7–C9 sequence is complete.
- **Layer 4 bridge design**: §3 inputs, §3.3 outputs, §3.4 algorithm,
  §3.5 location (`domain/construction/opening_bridge.py`), §3.6
  not-rules, §3.7 output contract.
- **§4 audit table**: 14 columns, 5 invariants, 3 example rows.
- **§5 Layer 5 runtime seam design** (deferred to C8+).
- **§6 validation requirements** (8 items in §6.7 readiness
  checklist).
- **§7 recommendation**: B (more discovery needed).

C2 status post-C5: **design complete, implementation pending
(this C6 plan).**

### 1.3 C3 — Construction Parity Snapshot Design (merged `aa800a5`)

C3 produced the **construction-period parity framework** at the
design level:

- 3 layers (funding, IDC, opening balance).
- 2 golden datasets (TUHO + Oborovo).
- 349 canonical fields (207 TUHO + 142 Oborovo).
- Schema version `C3-1.0`.
- Tolerance ±0.001 kEUR.

C3 status post-C5: **design implemented, snapshot scaffolded (C4),
engine-compared (C5).**

### 1.4 C4 — Snapshot Scaffolding (merged `dcc30b6`)

C4 produced the **frozen golden snapshot files** (2 files) and
**structure validation tests** (131 tests). Snapshots conform to
C3 schema.

C4 status: **complete.**

### 1.5 C5 — Engine Comparison Tests (merged `2d8a91c`)

C5 produced **93 engine-comparison tests** that call
`compute_construction_schedule()` for TUHO and Oborovo and
compare the engine output to the C4 snapshots. C5 implemented:

- 4 of 8 C2 §6.7 readiness items at the engine-comparison level.
- 1 partial (senior IDC caveat in docstring — full caveat is C7+).
- 3 deferred to C6+ (COD opening balance, IDC by source,
  no double-counting).
- 1 always deferred (second pair of eyes review).

C5 recommendation: **B. More validation needed** (engine comparison
established parity baseline; bridge is C6+).

C5 status: **complete, with clear handoff to C6.**

### 1.6 C1–C5 stack: preconditions for C6

| Precondition | Status |
|---|---|
| SHL IDC convention decided (C2) | ✅ done |
| Bridge output contract specified (C2 §3.7) | ✅ done |
| Audit table schema specified (C2 §4.1) | ✅ done |
| Audit table invariants specified (C2 §4.5) | ✅ done |
| Per-field policy specified (C2 §2.1) | ✅ done |
| Frozen snapshot fixtures exist (C4) | ✅ done |
| Engine parity baseline exists (C5) | ✅ done |
| C2 §6.7 readiness: 4/8 done at engine level (C5) | ✅ done |
| C2 §6.7 readiness: 3/8 deferred to C6+ | ✅ deferred |
| Senior IDC base-rate modelling | ⏸️ separate workstream |
| Second pair of eyes review (C2 §6.7 item 8) | ⏸️ always deferred |
| rc1 SHA `b425a07...` reachable | ✅ done |

**All C1–C5 preconditions for C6 are met. C6 can plan Layer 4.**

---

## 2. Define exact Layer 4 implementation scope

C2 §3.5 specifies the bridge as a pure transformation function in
`domain/construction/opening_bridge.py`. C6 **refines** the C2
spec into a precise implementation scope.

### 2.1 What Layer 4 implements (allowed)

C7 (the implementation phase) will add:

- **A single new module** at `domain/construction/opening_bridge.py`.
- **A pure function** `build_opening_balance_bridge(input)` that
  takes a `OpeningBalanceBridgeInput` and returns a
  `OpeningBalanceBridgeResult`.
- **Three dataclasses**:
  - `OpeningBalanceBridgeInput` (input value object)
  - `OpeningBalanceBridgeResult` (output value object)
  - `BridgeAuditRow` (per-field audit record)
- **Three enum-like string constants** (or `Literal` types) for
  the audit row's `selection_reason`, `override_status`, and
  `double_counting_guard` fields.
- **The 11-field policy table** (C2 §2.1) as a module-level
  constant (a `tuple[BridgeFieldPolicy, ...]`) — **not a Python
  enum**, just a frozen dataclass tuple of 11 entries.
- **The audit table generation** logic that produces one
  `BridgeAuditRow` per policy field (11 rows).
- **The double-counting guard** logic (see §6).
- **The opening balance identity check** that asserts
  `opening_senior_balance == total_senior_draw + capitalized_senior_idc`
  and `opening_shl_balance == total_shl_draw + capitalized_shl_idc`
  (within ±0.001 kEUR).

### 2.2 What Layer 4 implements (exact output contract)

Per C2 §3.7, the output is:

```text
OpeningBalanceBridgeResult:
    opening_senior_balance_at_cod_keur: float
    opening_shl_balance_at_cod_keur: float
    equity_contribution_at_cod_keur: float
    capitalized_senior_idc_keur: float
    capitalized_shl_idc_keur: float
    financing_fee_treatment_keur: float
    audit_reconciliation_table: tuple[BridgeAuditRow, ...]
    source_construction_result: ConstructionScheduleResult
    manual_overrides: tuple[ManualOverrideRow, ...]
    bridge_metadata: BridgeMetadata
        policy_version: str
        bridge_version: str
        bridge_run_timestamp: str  # ISO-8601
```

C6 enforces this contract in the C7 test file (C2 §6.4 COD
opening balance reconciliation test).

### 2.3 What Layer 4 implements (exact input contract)

C6 defines the input contract. The input is a single
`OpeningBalanceBridgeInput` dataclass with:

```text
OpeningBalanceBridgeInput:
    construction_result: ConstructionScheduleResult
    manual_overrides: tuple[ManualOverrideRow, ...]
    project_assumptions: ProjectAssumptions  # a new frozen dataclass
        shl_interest_rate: float
        senior_interest_rate: float
        construction_start_date: date
        cod_date: date
        shl_investment_date: date
    replacement_policy: tuple[BridgeFieldPolicy, ...]  # 11 entries
    parity_references: tuple[ParityReferenceRow, ...]  # optional, audit-only
    bridge_version: str  # e.g. "C7-1.0"
```

`ProjectAssumptions` is a **new frozen dataclass** in
`domain/construction/opening_bridge.py`. It is **not** the same
as the existing `Project` dataclass in `domain/inputs.py` — the
bridge does not import `Project` (C2 §3.6.5: "The bridge does
not import the waterfall domain, the operating-period finance
logic, the project factory, or the UI").

`ManualOverrideRow` is a **new frozen dataclass** with
`(field_code, manual_value_keur)`.

`BridgeFieldPolicy` is a **new frozen dataclass** with
`(field_code, current_source_label, construction_source_field,
policy, c1_blocker_reference)`.

`ParityReferenceRow` is a **new frozen dataclass** with
`(field_code, parity_reference_keur)`. Optional input, used
for audit only.

### 2.4 What Layer 4 implements (per-field logic)

C2 §2.1 specifies the policy. The bridge applies the policy
field-by-field:

| Field | Policy | Bridge behavior |
|---|---|---|
| `shl_idc_keur` | `replaced` | Use `engine.total_shl_idc_keur`. |
| `shl_amount_keur` | `replaced` | Use `engine.total_shl_draw_keur`. |
| `shl_opening_balance_keur` | `replaced` | Use `engine.opening_shl_balance_keur`. |
| `senior_opening_balance_keur` | `frozen` | Use manual value. Audit row records `selection_reason=frozen`, `override_status=manual_override_active`. |
| `senior_idc_keur` | `replaced` | Use `engine.total_senior_idc_keur` (with effective-rate caveat). |
| `capex_keur` | `frozen` | Use manual value (operating CAPEX ≠ construction CAPEX). |
| `reserves_keur` | `retained` | Use manual value. No engine value. |
| `vat_operating` | `retained` | Use manual value. No engine value. |
| `financing_fees_keur` | `retained` | Use manual value. No engine value. |
| `commitment_fee_keur` | `retained` | Use manual value. No engine value. |
| `equity_total_keur` | `derived` | Use manual value (operating equity ≠ construction equity). Audit row records both side by side. |

### 2.5 What Layer 4 implements (audit table)

C2 §4.1 specifies 14 columns. The bridge produces 11 rows
(one per policy field). Each row records:

- `field_code` (str)
- `manual_value_keur` (float or None)
- `construction_derived_value_keur` (float or None)
- `selected_runtime_value_keur` (float)
- `selection_reason` (one of: `replaced`, `frozen`, `retained`, `derived`)
- `override_status` (one of: `no_override`, `manual_override_active`, `construction_override_active`, `composite_no_override`)
- `double_counting_guard` (one of: `guarded_single_source`, `guarded_composite`, `not_applicable`)
- `parity_reference_keur` (float or None)
- `parity_delta_keur` (float or None)
- `parity_status` (one of: `parity_ok`, `parity_drift`, `parity_unknown`, `parity_not_applicable`)
- `c1_blocker_reference` (str)
- `audit_timestamp` (ISO-8601 str)
- `bridge_version` (str)
- `policy_version` (str, e.g. `C2-1.0`)

The bridge produces **exactly 11 rows** (C2 §6.4: "The audit
table has exactly 11 rows (one per policy field)").

### 2.6 What Layer 4 implements (opening balance identities)

The bridge asserts the following hard identities (per C2 §7.4):

- `opening_senior_balance == total_senior_draw + capitalized_senior_idc`
  (within ±0.001 kEUR)
- `opening_shl_balance == total_shl_draw + capitalized_shl_idc`
  (within ±0.001 kEUR)
- `equity_contribution_at_cod == total_equity_draw` (within
  ±0.001 kEUR)

If any identity fails, the bridge **raises** `BridgeIdentityError`
(a new exception in `domain/construction/opening_bridge.py`).

### 2.7 What Layer 4 implements (no-side-effects guarantee)

Per C2 §3.6.1: "The bridge is not a runtime mutation. It does
not modify `Project` or any persistence record. The output is
a value object (a frozen dataclass) that Layer 5 may consume."

C7 must implement this guarantee. The test in C7 includes a
**mutation guard test** that:

- Takes a snapshot of the input `ConstructionScheduleResult`'s
  attributes before the bridge call.
- Calls the bridge.
- Asserts the input's attributes are unchanged after the call.
- Asserts the `manual_overrides` tuple is unchanged.
- Asserts the `replacement_policy` tuple is unchanged.

### 2.8 What Layer 4 does NOT implement

C6 explicitly excludes the following from Layer 4:

- **No wiring into the waterfall** (Layer 5, deferred to C8+).
- **No wiring into the runtime** (no calls from `app/`,
  `main_web.py`, `main_api.py`).
- **No feature flag flip** (C1 blocker 3, deferred to C9+).
- **No replacement of runtime manual fields** (the bridge is
  pure; Layer 5 is the wiring).
- **No change to CAPEX totals** (frozen, not replaced).
- **No change to debt service** (the bridge produces opening
  balances; the waterfall's debt service computation is
  downstream and unchanged).
- **No change to tax** (tax engine untouched).
- **No change to depreciation** (depreciation engine untouched).
- **No change to CFADS** (CFADS is computed from the waterfall,
  not from the bridge).
- **No change to project statuses** (TUHO remains Level 2,
  Oborovo remains Level 2).
- **No persistence writes** (the bridge returns a value object;
  Layer 5 may persist it later).
- **No UI rendering** (the audit table is consumed by Layer 5;
  the bridge does not render anything).

---

## 3. Define explicit non-scope

C6 explicitly lists what the bridge must **never** do. This is
the **negative spec** and is as important as the positive spec.

### 3.1 Bridge must NOT import from these modules

Per C2 §3.5: "The bridge does not import the waterfall domain,
the operating-period finance logic, the project factory, or
the UI."

Concretely, the C7 implementation must NOT add these imports
to `domain/construction/opening_bridge.py`:

- `domain/inputs.py` (the `Project` dataclass)
- `domain/waterfall*` (any waterfall module)
- `app/` (any app module)
- `main_web.py`, `main_api.py`
- `static/` (UI)

The C7 test file includes a **forbidden-imports AST guard** that
asserts `opening_bridge.py` does not import any of the above.

### 3.2 Bridge must NOT mutate the waterfall state

Per C2 §3.6.1: "The bridge is not a runtime mutation."

The C7 test file includes a **mutation guard test** that:

- Snapshots all attributes of the input
  `ConstructionScheduleResult`.
- Calls the bridge.
- Asserts the input is byte-for-byte identical after the call.

### 3.3 Bridge must NOT call the engine

The bridge receives a `ConstructionScheduleResult` as input. It
does **not** call `compute_construction_schedule()` itself. The
caller is responsible for running the engine and passing the
result to the bridge.

This decoupling is critical: the bridge is a pure transformation
function. It cannot be a runtime cost. It is **testable without
the engine** (using a synthetic `ConstructionScheduleResult`).

The C7 test file includes a **no-engine-call guard** that
inspects the bridge module's AST and asserts it does not call
`compute_construction_schedule` or `build_runtime_construction_schedule`.

### 3.4 Bridge must NOT flip feature flags

The `use_construction_schedule_engine` flag remains default-off.
The bridge does not read or write the flag. The flag is a
Layer 5 concern (C8+).

### 3.5 Bridge must NOT change formulas

The bridge does not introduce new formulas. It consumes the
engine output (already computed in `compute_construction_schedule`)
and applies a per-field policy. The per-field policy is
**data** (a `tuple[BridgeFieldPolicy, ...]`), not a formula.

The C7 test file includes a **formula-stable test** that:

- Hashes the engine output before the bridge call.
- Calls the bridge.
- Hashes the engine output after the bridge call.
- Asserts the hashes are identical (the engine output is the
  bridge's input; the bridge does not mutate it).

### 3.6 Bridge must NOT change project statuses

The bridge does not change `Project.project_status` or any
similar field. Project statuses are unchanged by the bridge.

### 3.7 Bridge must NOT change persistence

The bridge does not write to any database, file, or
in-memory state. It returns a frozen dataclass.

### 3.8 Bridge must NOT change UI

The bridge does not render anything. The audit table is a
structured object, not a string or HTML.

### 3.9 Bridge must NOT depend on the C7 test file

The bridge module is **independent of its own test file**. The
test file imports the bridge; the bridge does not import the
test file. (Trivial, but worth stating explicitly.)

---

## 4. Proposed files for future C7

C6 proposes the **exact file list** for the C7 implementation
phase. C7 is the **only** phase that creates these files.

### 4.1 New files (4 total)

| Path | Lines (est.) | Purpose |
|---|---|---|
| `domain/construction/opening_bridge.py` | ~250–350 | The bridge module (pure function + dataclasses). |
| `tests/test_phase_c7_opening_balance_bridge.py` | ~500–700 | The bridge test file (C2 §6.4, §6.5, §6.6). |
| `docs/phase_c7_opening_balance_bridge_implementation.md` | ~300–500 | The C7 implementation report (records what was done, what was deferred, what was tested). |
| `reports/phase_c7_opening_balance_bridge_implementation.json` | ~50–100 | The C7 machine-readable report. |

**Total: 4 new files, no modifications to existing files.**

### 4.2 What goes in `domain/construction/opening_bridge.py`

```python
# Pseudocode (NOT IMPLEMENTED IN C6)

@dataclass(frozen=True)
class ManualOverrideRow:
    field_code: str
    manual_value_keur: float

@dataclass(frozen=True)
class BridgeFieldPolicy:
    field_code: str
    current_source_label: str
    construction_source_field: str
    policy: str  # one of: replaced, frozen, retained, derived
    c1_blocker_reference: str

@dataclass(frozen=True)
class ParityReferenceRow:
    field_code: str
    parity_reference_keur: float | None

@dataclass(frozen=True)
class ProjectAssumptions:
    shl_interest_rate: float
    senior_interest_rate: float
    construction_start_date: date
    cod_date: date
    shl_investment_date: date

@dataclass(frozen=True)
class OpeningBalanceBridgeInput:
    construction_result: ConstructionScheduleResult
    manual_overrides: tuple[ManualOverrideRow, ...]
    project_assumptions: ProjectAssumptions
    replacement_policy: tuple[BridgeFieldPolicy, ...]
    parity_references: tuple[ParityReferenceRow, ...]
    bridge_version: str

@dataclass(frozen=True)
class BridgeAuditRow:
    field_code: str
    manual_value_keur: float | None
    construction_derived_value_keur: float | None
    selected_runtime_value_keur: float
    selection_reason: str
    override_status: str
    double_counting_guard: str
    parity_reference_keur: float | None
    parity_delta_keur: float | None
    parity_status: str
    c1_blocker_reference: str
    audit_timestamp: str
    bridge_version: str
    policy_version: str

@dataclass(frozen=True)
class BridgeMetadata:
    policy_version: str
    bridge_version: str
    bridge_run_timestamp: str

@dataclass(frozen=True)
class OpeningBalanceBridgeResult:
    opening_senior_balance_at_cod_keur: float
    opening_shl_balance_at_cod_keur: float
    equity_contribution_at_cod_keur: float
    capitalized_senior_idc_keur: float
    capitalized_shl_idc_keur: float
    financing_fee_treatment_keur: float
    audit_reconciliation_table: tuple[BridgeAuditRow, ...]
    source_construction_result: ConstructionScheduleResult
    manual_overrides: tuple[ManualOverrideRow, ...]
    bridge_metadata: BridgeMetadata

class BridgeIdentityError(ValueError):
    pass

# Module-level constant: the C2 §2.1 policy table
POLICY_TABLE: tuple[BridgeFieldPolicy, ...] = (
    # 11 entries
)

def build_opening_balance_bridge(
    input: OpeningBalanceBridgeInput,
) -> OpeningBalanceBridgeResult:
    # Pure function. No side effects.
    ...
```

### 4.3 What goes in `tests/test_phase_c7_opening_balance_bridge.py`

The C7 test file implements:

- **C2 §6.4** COD opening balance reconciliation test
  (6 numeric fields, 11 audit rows, non-empty metadata).
- **C2 §6.5** IDC by source reconciliation test
  (`capitalized_senior_idc_keur + capitalized_shl_idc_keur ==
  total_idc` within tolerance).
- **C2 §6.6** No double-counting test plan (executable).
- **Mutation guard test** (input is byte-for-byte identical
  after the bridge call).
- **No-engine-call guard** (AST-level assertion).
- **No-runtime-wiring guard** (AST-level assertion).
- **No-forbidden-imports guard** (AST-level assertion).
- **Forbidden-path guard** (git diff against `domain/`,
  `app/`, `main_web.py`, `main_api.py`, `static/`).
- **Senior IDC caveat test** (engine effective rate matches
  caveat).
- **Policy table mirror test** (POLICY_TABLE in the bridge
  matches C2 §2.1 verbatim).
- **Frozen/replaced/retained/derived field tests** (one per
  field × 2 projects = 22 tests).
- **Audit row invariants test** (per C2 §4.5).
- **rc1 SHA reachable test**.
- **Project statuses unchanged test** (TUHO, Oborovo,
  Generic Wind, Generic Solar).

**Estimated: 100–150 tests.**

### 4.4 What goes in `docs/phase_c7_opening_balance_bridge_implementation.md`

The C7 implementation report:

- Records the actual C7 SHAs.
- Records what was implemented (per C6 §2.1–§2.7).
- Records what was deferred (per C6 §3.1–§3.9).
- Records the test results.
- Records any deviation from this C6 plan (with rationale).
- Recommends A (ready for C8) / B (more design needed) / C
  (defer).

### 4.5 What goes in `reports/phase_c7_opening_balance_bridge_implementation.json`

The C7 machine-readable report: identical structure to C6
report, but with the actual C7 numbers.

---

## 5. API / dataclass shape

C6 defines the **exact API / dataclass shape** for C7. The
shapes below are **frozen dataclasses** (immutable) per C2
§3.6.1.

### 5.1 `OpeningBalanceBridgeInput`

```text
@dataclass(frozen=True)
class OpeningBalanceBridgeInput:
    construction_result: ConstructionScheduleResult
    manual_overrides: tuple[ManualOverrideRow, ...]
    project_assumptions: ProjectAssumptions
    replacement_policy: tuple[BridgeFieldPolicy, ...]
    parity_references: tuple[ParityReferenceRow, ...]
    bridge_version: str
```

### 5.2 `OpeningBalanceBridgeResult`

```text
@dataclass(frozen=True)
class OpeningBalanceBridgeResult:
    opening_senior_balance_at_cod_keur: float
    opening_shl_balance_at_cod_keur: float
    equity_contribution_at_cod_keur: float
    capitalized_senior_idc_keur: float
    capitalized_shl_idc_keur: float
    financing_fee_treatment_keur: float
    audit_reconciliation_table: tuple[BridgeAuditRow, ...]
    source_construction_result: ConstructionScheduleResult
    manual_overrides: tuple[ManualOverrideRow, ...]
    bridge_metadata: BridgeMetadata
```

### 5.3 `BridgeAuditRow`

```text
@dataclass(frozen=True)
class BridgeAuditRow:
    field_code: str
    manual_value_keur: float | None
    construction_derived_value_keur: float | None
    selected_runtime_value_keur: float
    selection_reason: str  # replaced | frozen | retained | derived
    override_status: str   # no_override | manual_override_active | construction_override_active | composite_no_override
    double_counting_guard: str  # guarded_single_source | guarded_composite | not_applicable
    parity_reference_keur: float | None
    parity_delta_keur: float | None
    parity_status: str  # parity_ok | parity_drift | parity_unknown | parity_not_applicable
    c1_blocker_reference: str
    audit_timestamp: str  # ISO-8601
    bridge_version: str
    policy_version: str
```

### 5.4 `BridgeMetadata`

```text
@dataclass(frozen=True)
class BridgeMetadata:
    policy_version: str   # e.g. "C2-1.0"
    bridge_version: str   # e.g. "C7-1.0"
    bridge_run_timestamp: str  # ISO-8601
```

### 5.5 `build_opening_balance_bridge(input) -> OpeningBalanceBridgeResult`

The single public function. It:

1. Receives an `OpeningBalanceBridgeInput`.
2. Applies the per-field policy (replaced / frozen / retained /
   derived) for each of the 11 fields.
3. Computes the audit row for each field.
4. Asserts the opening balance identities
   (senior, SHL, equity).
5. Returns the `OpeningBalanceBridgeResult`.

The function is **pure**: same input → same output. No side
effects. No I/O. No exceptions other than `BridgeIdentityError`
(when an identity fails) and `ValueError` (when the input is
malformed).

---

## 6. Double-counting guards

C2 §2.3 specifies the **double-counting guard invariant**:

> The operating waterfall reads exactly one of `{manual value,
> construction-derived value}` for each opening balance. The
> choice is recorded in the audit trail. Reading both is a
> guard failure.

C6 refines this into **explicit guard rules** for C7.

### 6.1 Per-field guard rules

| Field | Policy | Guard rule | `double_counting_guard` value |
|---|---|---|---|
| `shl_idc_keur` | `replaced` | Single source: construction. Manual is recorded but **not used** in the bridge output. | `guarded_single_source` |
| `shl_amount_keur` | `replaced` | Single source: construction. | `guarded_single_source` |
| `shl_opening_balance_keur` | `replaced` | Single source: construction (derived from `shl_amount_keur + shl_idc_keur`). | `guarded_single_source` |
| `senior_opening_balance_keur` | `frozen` | Single source: manual. Construction is computed and recorded for parity, but **not used** in the bridge output. | `guarded_single_source` |
| `senior_idc_keur` | `replaced` | Single source: construction (with effective-rate caveat). | `guarded_single_source` |
| `capex_keur` | `frozen` | Single source: manual. Construction total is recorded for parity, but **not used** in the bridge output. | `guarded_single_source` |
| `reserves_keur` | `retained` | Single source: manual. Construction does not produce a value. | `guarded_single_source` |
| `vat_operating` | `retained` | Single source: manual. Construction does not produce a value. | `guarded_single_source` |
| `financing_fees_keur` | `retained` | Single source: manual. Construction does not produce a value. | `guarded_single_source` |
| `commitment_fee_keur` | `retained` | Single source: manual. Construction does not produce a value. | `guarded_single_source` |
| `equity_total_keur` | `derived` | Composite: derived from manual inputs (`share_capital + share_premium + shl_amount + shl_idc`). Construction equity is a **different concept** (construction equity vs operating equity) and is recorded for audit, but **not used** in the composite. | `guarded_composite` |

**All 11 fields have `guarded_single_source` or
`guarded_composite` as their `double_counting_guard` value.**
No field has `not_applicable` (per C2 §4.5 invariant 4).

### 6.2 The guard is enforced by the bridge

The bridge enforces the guard **at output time**. For each
field:

- The bridge computes the audit row.
- The audit row records the source(s) used and not used.
- The bridge asserts that **exactly one source is in
  `selected_runtime_value_keur`**.
- If two sources are in `selected_runtime_value_keur`, the
  bridge raises `BridgeIdentityError`.

### 6.3 The guard is verified by C7 tests

C7 implements C2 §6.6 (no double-counting test plan). The test:

- Runs the bridge for TUHO and Oborovo.
- Asserts the audit table has exactly 11 rows.
- For each row, asserts `double_counting_guard` is
  `guarded_single_source` or `guarded_composite`.
- For each row, asserts `selected_runtime_value_keur` is
  exactly one of `manual_value_keur` or
  `construction_derived_value_keur` (or the derived composite
  for `equity_total_keur`).
- If any row violates the guard, the test fails.

### 6.4 Senior IDC effective-rate caveat (C1 R-PAR-2)

The senior IDC is calibrated to an effective rate (not modelled
from rate × elapsed period). The C7 implementation preserves
this caveat:

- The `senior_idc_keur` audit row records
  `c1_blocker_reference = "blocker_5_R-PAR-2"`.
- The `selection_reason` is `replaced` (the engine value is
  used) but the **policy** remains `frozen` for
  `senior_opening_balance_keur` (the engine value of the
  *opening balance* is computed but not used; the manual value
  is used).
- This asymmetry is intentional: the senior IDC (1,519.564
  kEUR) is the right number (effective-rate calibrated), but
  the senior opening balance (44,878.838 kEUR) is **not yet
  modelling-correct** (it depends on the IDC being a function
  of rate × elapsed, not a calibrated constant).

The C7 test asserts this asymmetry: the
`senior_idc_keur` row has `selection_reason=replaced` AND
`parity_status=parity_ok`, while the
`senior_opening_balance_keur` row has `selection_reason=frozen`
AND `parity_status=parity_drift`.

---

## 7. Validation plan for future C7 implementation

C6 defines the **exact tests** that C7 must satisfy. The
test file is `tests/test_phase_c7_opening_balance_bridge.py`.

### 7.1 File-existence tests (4 tests)

- `domain/construction/opening_bridge.py` exists.
- `tests/test_phase_c7_opening_balance_bridge.py` exists.
- `docs/phase_c7_opening_balance_bridge_implementation.md`
  exists.
- `reports/phase_c7_opening_balance_bridge_implementation.json`
  exists.

### 7.2 API / dataclass shape tests (10 tests)

- `OpeningBalanceBridgeInput` is a frozen dataclass.
- `OpeningBalanceBridgeResult` is a frozen dataclass.
- `BridgeAuditRow` is a frozen dataclass.
- `BridgeMetadata` is a frozen dataclass.
- `ManualOverrideRow` is a frozen dataclass.
- `BridgeFieldPolicy` is a frozen dataclass.
- `ParityReferenceRow` is a frozen dataclass.
- `ProjectAssumptions` is a frozen dataclass.
- `BridgeIdentityError` is a `ValueError` subclass.
- `build_opening_balance_bridge` is a function with the exact
  signature `(input: OpeningBalanceBridgeInput) -> OpeningBalanceBridgeResult`.

### 7.3 C2 §6.4 COD opening balance reconciliation test (5 tests)

- Bridge result has all 6 numeric fields
  (opening_senior, opening_shl, equity, capitalized_senior_idc,
  capitalized_shl_idc, financing_fee_treatment).
- Audit table has exactly 11 rows.
- `selected_runtime_value_keur` is one of `manual_value_keur` or
  `construction_derived_value_keur` for every non-derived field.
- `bridge_metadata.policy_version` is non-empty (e.g. `C2-1.0`).
- `bridge_metadata.bridge_version` is non-empty (e.g. `C7-1.0`).

### 7.4 C2 §6.5 IDC by source reconciliation test (4 tests)

- TUHO: `capitalized_senior_idc_keur + capitalized_shl_idc_keur ==
  total_idc` within ±0.001 kEUR.
- Oborovo: same.
- Senior IDC effective-rate caveat: if the senior IDC is
  effective-rate based, the test asserts
  `capitalized_senior_idc_keur` matches the engine value
  (1519.564 / 1086.032) within ±0.001 kEUR.
- Senior opening balance: the bridge returns the **manual**
  value (frozen), not the engine value (parity_drift).

### 7.5 C2 §6.6 no double-counting test plan (8 tests)

- Bridge audit table has exactly 11 rows.
- For each row, `double_counting_guard` is
  `guarded_single_source` or `guarded_composite` (never
  `not_applicable`).
- For each non-derived field,
  `selected_runtime_value_keur` is exactly one of
  `manual_value_keur` or `construction_derived_value_keur`.
- For the `equity_total_keur` (derived) field,
  `selected_runtime_value_keur` is the manual composite, and
  `double_counting_guard` is `guarded_composite`.
- The audit row's `selection_reason` matches the policy.
- The audit row's `override_status` matches the policy.
- The audit row's `parity_status` matches the expected status
  (parity_ok for `replaced` fields, parity_drift for
  `senior_opening_balance_keur`, parity_not_applicable for
  `retained` fields without parity reference).
- The bridge does not raise `BridgeIdentityError` for valid
  input.

### 7.6 Mutation guard test (1 test)

- Take a snapshot of all attributes of the input
  `ConstructionScheduleResult`, `manual_overrides`,
  `replacement_policy`, `parity_references`,
  `project_assumptions`.
- Call the bridge.
- Assert the input is byte-for-byte identical after the call.

### 7.7 No-engine-call guard (1 test, AST-level)

- Inspect the bridge module's AST.
- Assert it does not call `compute_construction_schedule` or
  `build_runtime_construction_schedule`.

### 7.8 No-runtime-wiring guard (1 test, AST-level)

- Inspect the bridge module's AST.
- Assert it does not import from `app/`, `main_web.py`,
  `main_api.py`, `static/`.
- Assert it does not import from `domain/inputs.py` (the
  `Project` dataclass).
- Assert it does not import from any waterfall module.

### 7.9 No-feature-flag-flips guard (1 test, AST-level)

- Inspect the bridge module's AST.
- Assert it does not read or write
  `use_construction_schedule_engine`,
  `use_opex_line_item_engine`,
  `use_senior_rate_schedule_engine`,
  `use_senior_sculpting_basis_engine`,
  `use_shl_fcf_waterfall_engine`.

### 7.10 Senior IDC caveat test (4 tests)

- TUHO: `caveats.senior_idc_effective_rate` ==
  `bridge.audit_table.senior_idc_keur.construction_derived_value_keur`
  within 1e-9.
- Oborovo: same.
- TUHO: `senior_idc_keur` row has
  `c1_blocker_reference="blocker_5_R-PAR-2"`.
- Oborovo: same.

### 7.11 Policy table mirror test (11 tests)

- For each of the 11 policy fields, assert the bridge
  `POLICY_TABLE` has the exact same `(field_code, policy,
  c1_blocker_reference)` as the C2 §2.1 doc.

### 7.12 Frozen / replaced / retained / derived field tests (22 tests)

- For each of the 11 fields × 2 projects, assert the bridge
  output matches the expected value (manual or construction,
  per the policy).

### 7.13 Audit row invariants test (5 tests, per C2 §4.5)

- Every policy field has exactly one row. No field is missing.
  No field is duplicated.
- `selected_runtime_value_keur` is one of `manual_value_keur` or
  `construction_derived_value_keur` (except for `derived`
  fields, explicitly marked).
- `selection_reason` matches the policy. No silent override.
- `double_counting_guard` is never `not_applicable` for opening
  balance fields.
- `parity_reference_keur` is `None` for fields with no Excel
  target. `parity_status` is then `parity_not_applicable`.

### 7.14 Forbidden-path guard (5 tests)

- `git diff` against `domain/` (excluding
  `domain/construction/opening_bridge.py`) shows no changes.
- `git diff` against `app/` shows no changes.
- `git diff` against `main_web.py` shows no changes.
- `git diff` against `main_api.py` shows no changes.
- `git diff` against `static/` shows no changes.

### 7.15 rc1 SHA reachable test (1 test)

- `b425a0708719eaa5e1d922b1008e5609758e0ad4` is reachable on
  `origin/main`.

### 7.16 Project statuses unchanged test (4 tests)

- TUHO remains **Level 2** in any project status reference.
- Oborovo remains **Level 2**.
- Generic Wind remains **Level 1**.
- Generic Solar remains **Level 1**.

### 7.17 C5 dependency test (1 test)

- C5 engine-comparison tests still pass (no regression in
  engine parity).

### 7.18 C4 dependency test (1 test)

- C4 snapshot structure tests still pass (snapshots unchanged).

### 7.19 Summary of test counts

| Category | Count |
|---|---|
| File existence | 4 |
| API / dataclass shape | 10 |
| C2 §6.4 COD opening balance reconciliation | 5 |
| C2 §6.5 IDC by source reconciliation | 4 |
| C2 §6.6 no double-counting | 8 |
| Mutation guard | 1 |
| No-engine-call | 1 |
| No-runtime-wiring | 1 |
| No-feature-flag-flips | 1 |
| Senior IDC caveat | 4 |
| Policy table mirror | 11 |
| Frozen / replaced / retained / derived | 22 |
| Audit row invariants | 5 |
| Forbidden-path | 5 |
| rc1 SHA reachable | 1 |
| Project statuses unchanged | 4 |
| C5 dependency | 1 |
| C4 dependency | 1 |
| **Total estimated** | **89** |

---

## 8. Recommendation

### Choice: **B. More design needed**

Rationale:

1. **C5 explicitly deferred Layer 4 to C6+.** C5's
   recommendation was B. C6 is the **first** of the C6+ phases.
   C6 is itself a design plan, not an implementation. C6
   produces a detailed plan for C7. C7 will be the **first
   domain implementation** (the first new module in
   `domain/construction/`). C7 requires its own design
   review (this C6 plan + C7 implementation report).

2. **The bridge has a non-trivial API surface.** 5 dataclasses,
   1 function, 1 exception, 1 policy table, 1 audit table, 1
   metadata dataclass. Each needs separate design review.
   This C6 plan documents the design; C7 implements it. C7
   is the first time we exercise the design in code.

3. **The bridge introduces a new layer of trust.** The
   C-series has been adding infrastructure (snapshots, engine
   tests, audit tables) without changing runtime. The bridge
   is the **first** component that will be consumed by Layer
   5 (the runtime seam). The bridge itself is pure, but the
   downstream effects (Layer 5 wiring, opt-in flag flip)
   are runtime changes. C6 plans the bridge; C7 implements
   it; C8 plans Layer 5; C9 implements Layer 5 (default-off);
   C10 flips the flag. This is a **5-phase rollout** for
   what looks like a single feature.

4. **The senior IDC effective-rate caveat is still unresolved.**
   C1 R-PAR-2 is the only C1 blocker that has not been
   addressed in any C-phase. C6 does not propose to fix it.
   The fix is a **separate workstream**. C7's bridge will
   preserve the caveat (frozen policy for
   `senior_opening_balance_keur`); the fix is out of scope
   for the C-series.

5. **C6 implements 0 of 3 deferred C2 §6.7 items.** C6 is a
   design plan, not an implementation. C2 §6.7 has 3 items
   deferred to C6+ (COD opening balance reconciliation,
   IDC by source reconciliation, no double-counting test
   plan). C6 does not implement any of them. C7 will.

6. **C6 is the right scope for the current C-series state.**
   The C-series is in a **design-implementation spiral**:
   C1, C2, C3 were design. C4 was snapshot scaffolding.
   C5 was engine comparison. C6 is implementation plan.
   C7 is bridge implementation. C8 is Layer 5 design.
   C9 is Layer 5 implementation. C10 is opt-in flag flip.
   C6 correctly stops at the plan; C7 is the next
   implementation.

### What would unblock "A. Ready for C7"

- A C6 implementation plan that includes:
  - Exact scope ✓ (this doc, §2)
  - Explicit non-scope ✓ (this doc, §3)
  - Proposed file list ✓ (this doc, §4)
  - API / dataclass shape ✓ (this doc, §5)
  - Double-counting guard rules ✓ (this doc, §6)
  - Validation plan ✓ (this doc, §7)
  - Recommendation ✓ (this doc, §8)
- A C7 implementation PR that:
  - Adds `domain/construction/opening_bridge.py` (the
    bridge module).
  - Adds the 5 dataclasses, 1 function, 1 exception.
  - Adds the C2 §6.4 / §6.5 / §6.6 tests.
  - Adds the mutation guard, no-engine-call guard,
    no-runtime-wiring guard, no-feature-flag-flips guard.
  - Adds the forbidden-path guards.
  - Verifies the C2 §6.7 readiness checklist: 3 of 8
    items now implemented (COD opening balance, IDC by
    source, no double-counting).

### What remains open after C6

- **Bridge module** (C7+).
- **C2 §6.4 COD opening balance reconciliation** (C7+).
- **C2 §6.5 IDC by source reconciliation** (C7+).
- **C2 §6.6 no double-counting test plan** (C7+).
- **Layer 5 runtime seam** (C8 design, C9 implementation).
- **Opt-in flag flip** (C10+).
- **Senior IDC base-rate modelling** (separate workstream).
- **Second pair of eyes review** (C7+ when the bridge
  module is implemented).

### Multi-phase path

| Phase | Scope | Status |
|---|---|---|
| C1 | Design gate | ✅ merged `5fccc3a` |
| C2 | SHL IDC convention + Layer 4 bridge design | ✅ merged `59f9e3d` |
| C3 | Construction parity framework design | ✅ merged `aa800a5` |
| C4 | Snapshot scaffolding + structure tests | ✅ merged `dcc30b6` |
| C5 | Engine-comparison tests (no bridge) | ✅ merged `2d8a91c` |
| **C6** | **Layer 4 bridge implementation plan (docs only)** | **This PR (DRAFT)** |
| C7 | Layer 4 bridge module + C2 §6.4/§6.5/§6.6 tests | Future |
| C8 | Layer 5 runtime seam design | Future |
| C9 | Layer 5 runtime seam implementation (default-off) | Future |
| C10 | Opt-in flag flip + TUHO promotion | Future |
| C11 | Oborovo promotion | Future |

---

## 9. Hard constraints (re-asserted)

C6 introduces:

- **Allowed:** 1 design doc, 1 report JSON, 1 test file.
- **NOT allowed:** no code, no runtime changes, no domain
  changes, no schema changes, no persistence changes, no
  feature flags, no formula changes, no CAPEX/debt/tax/
  depreciation/IDC changes, no project status changes.

C6 produces **3 files only**:

- `docs/phase_c6_opening_balance_bridge_implementation_plan.md` (this)
- `reports/phase_c6_opening_balance_bridge_implementation_plan.json`
- `tests/test_phase_c6_opening_balance_bridge_implementation_plan.py`

The C6 test file is a **design-doc / report / non-scope / API
shape / guards / recommendation / hard-constraints** test, not
a runtime test. It asserts that this plan is correct, complete,
and self-consistent.

**C6 does NOT add `domain/construction/opening_bridge.py`.**
That is C7+.

---

## 10. Stop after report

This document is the C6 deliverable. The C6 PR is opened as
DRAFT. Do not mark ready. Do not merge. Stop after report.

---

Deliverables: this document +
`reports/phase_c6_opening_balance_bridge_implementation_plan.json` +
`tests/test_phase_c6_opening_balance_bridge_implementation_plan.py`.
