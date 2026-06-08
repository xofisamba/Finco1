# Phase C5 - Construction Engine Comparison Tests

> **Scope label:** **Engine-comparison only — no Layer 4 bridge module,
> no Layer 5 runtime wiring.**
>
> Type: TEST / VALIDATION IMPLEMENTATION (no domain model, no app, no runtime)
> Status: DRAFT
> Date: 2026-06-08
> Base SHA: `dcc30b6` (post-Phase C4)
> Branch: `phase-c5-construction-engine-comparison`
> Hard constraints: **NO app/ runtime changes, NO domain model changes, NO
> waterfall changes, NO CAPEX formula changes, NO debt/SHL/IDC runtime
> changes, NO tax changes, NO depreciation changes, NO schema/persistence
> changes, NO feature flags, NO project status changes, NO new domain
> modules**

---

## 0. Purpose

C4 (`dcc30b6`) implemented the **frozen golden snapshot scaffolding**:
207 fields for TUHO, 142 fields for Oborovo, 131 structure-validation
tests. C4 documented what C5+ would do — engine comparison against
the snapshots — and explicitly **deferred** it.

This C5 phase **implements the engine-comparison tests** that:

- Run the **existing** construction engine
  (`domain/construction/engine.py:compute_construction_schedule`).
- Compare the engine output to the **C4 frozen snapshots**.
- Apply the **per-field policy** from C2 §2.1
  (replaced / frozen / retained / derived).
- Assert that the engine output matches the snapshot for
  `replaced` fields, and document the manual-vs-derived
  delta for `frozen` fields.
- Verify the senior IDC effective-rate caveat (C1 R-PAR-2)
  is preserved at the engine level.

**C5 does NOT implement the Layer 4 bridge module
(`domain/construction/opening_bridge.py` per C2 §3.5).** C5
tests are **engine-comparison tests**, not bridge tests. The
bridge module is **C6+** and requires its own design review
(per C2 §3.6: the bridge is a pure function with a specific
input/output contract and an audit table).

**C5 does NOT implement Layer 5 (runtime integration
seam, C1 blocker 3).** C5 tests are read-only against the
construction engine; they do not mutate the operating
waterfall.

### 0.1 What C5 implements

- **Engine-comparison tests** that load C4 snapshots, run the
  engine, and compare.
- **Manual-vs-derived reconciliation tests** (C2 §6.3 partial)
  that exercise the per-field policy from C2 §2.1.
- **C2 §6.1 + §6.2 implementation** (TUHO + Oborovo
  construction-period parity assertions).
- **Senior IDC effective-rate caveat validation** (C1
  R-PAR-2).

### 0.2 What C5 does NOT implement (deferred to C6+)

- **Layer 4 bridge module** (`domain/construction/opening_bridge.py`,
  C2 §3.5). Deferred to C6 — requires separate design review
  for the audit table schema, the dataclass contract, and the
  `BridgeMetadata` field.
- **COD opening balance reconciliation test** (C2 §6.4).
  Deferred — requires the bridge module.
- **IDC by source reconciliation test** (C2 §6.5). Deferred —
  requires the bridge output (`capitalized_senior_idc_keur`).
- **No double-counting test plan** (C2 §6.6). Deferred —
  requires the bridge audit table.
- **Layer 5 runtime seam** (C2 §5, C1 blocker 3). Deferred to
  C7+.
- **Opt-in flag flip** (`use_construction_schedule_engine`,
  C1 blocker 3). Deferred to C7+.
- **Senior IDC base-rate modelling** (C1 blocker 5).
  Separate workstream.

---

## 1. Engine comparison: what is being compared

### 1.1 The engine

`domain/construction/engine.py:compute_construction_schedule`
takes a `ConstructionConfig` and returns a
`ConstructionScheduleResult`. The result contains:

- `monthly_entries: tuple[ConstructionMonthlyEntry, ...]`
- `total_uses_keur: float`
- `total_equity_draw_keur: float`
- `total_shl_draw_keur: float`
- `total_junior_draw_keur: float`
- `total_senior_draw_keur: float`
- `total_shl_idc_keur: float`
- `total_senior_idc_keur: float`
- `opening_senior_balance_keur: float`
- `opening_shl_balance_keur: float`
- `equity_contribution_at_cod_keur: float`
- `config_used: ConstructionConfig`
- `policy_version: str` (e.g. `"C2-1.0"`)

### 1.2 The snapshot

C4 frozen snapshots
(`tests/fixtures/construction_parity/tuho_construction_snapshot.json`
and `oborovo_construction_snapshot.json`) contain:

- `project_code` (e.g. `TUHO-WIND-1`)
- `schema_version` (e.g. `C3-1.0`)
- `tolerance_policy` (e.g. `exact_0.001_keur`)
- `field_count_expected` (207 or 142)
- `calendar` (start, COD, shl_investment_date, months)
- `totals_keur` (7 fields)
- `opening_balances_keur` (3 fields)
- `monthly_grid` (18 or 12 rows)
- `funding_caps_keur` (4 fields)
- `rates` (2 fields)
- `caveats` (8 fields)
- `source_documents` (3 fields)

### 1.3 The comparison

C5 tests load both snapshots, run the engine with the
**matching** construction config (TUHO or Oborovo), and
assert:

| Engine field | Snapshot field | Policy (C2 §2.1) | Expected status |
|---|---|---|---|
| `total_uses_keur` | `totals_keur.total_uses` | (audit-only, frozen for waterfall) | `parity_ok` |
| `total_equity_draw_keur` | `totals_keur.total_equity_draw` | derived | `parity_ok` |
| `total_shl_draw_keur` | `totals_keur.total_shl_draw` | replaced (C2 §2.1) | `parity_ok` |
| `total_senior_draw_keur` | `totals_keur.total_senior_draw` | retained (operating CAPEX differs) | `parity_ok` (audit-only) |
| `total_shl_idc_keur` | `totals_keur.total_shl_idc` | replaced (Convention B) | `parity_ok` |
| `total_senior_idc_keur` | `totals_keur.total_senior_idc` | replaced (effective-rate caveat) | `parity_ok` (with caveat) |
| `opening_senior_balance_keur` | `opening_balances_keur.opening_senior_balance` | frozen (senior IDC not modelling-correct) | `parity_drift` (audit) |
| `opening_shl_balance_keur` | `opening_balances_keur.opening_shl_balance` | replaced | `parity_ok` |
| `equity_contribution_at_cod_keur` | `opening_balances_keur.equity_contribution_at_cod` | derived | `parity_ok` |

The C5 tests also assert:

- The engine monthly grid length matches
  `snapshot.calendar.construction_months` (18 for TUHO, 12
  for Oborovo).
- The sum of engine monthly `uses_keur` matches
  `engine.total_uses_keur` (within ±0.001 kEUR).
- The engine opening balance identity holds:
  `opening_senior_balance == total_senior_draw + total_senior_idc`
  (within ±0.001 kEUR).
- The engine opening balance identity holds:
  `opening_shl_balance == total_shl_draw + total_shl_idc`
  (within ±0.001 kEUR).
- The senior IDC effective rate caveat applies: the engine
  `senior_interest_rate` value matches the snapshot
  `caveats.senior_idc_effective_rate`.

---

## 2. Manual-vs-derived reconciliation (C2 §6.3 partial)

C2 §6.3 specifies:

> A pytest test that runs the construction engine and the
> runtime adapter (Phase 7I) for both TUHO and Oborovo and
> asserts:
> - The audit table contains one row per policy field from
>   section 2.1.
> - The `selection_reason` is consistent with the policy
>   (section 2.1).
> - The `double_counting_guard` is satisfied for every
>   opening balance field.
> - The `parity_status` matches the expected status
>   (parity_ok for the fields where parity applies,
>   parity_drift for the senior opening balance, etc.).

C5 implements a **partial** version of C2 §6.3:

- The **per-field policy** from C2 §2.1 is encoded as a
  constant `POLICY_TABLE` in the test file (11 fields).
- The **engine-comparison test** asserts that the engine
  value matches the snapshot for `replaced` fields.
- The **frozen-field test** asserts that the engine
  computed a value but the waterfall would use the manual
  value (this is a documentation test, not a runtime
  test — the waterfall is not actually invoked).
- The **retained-field test** asserts that the engine did
  not produce a value (i.e. the field is operating-period,
  not construction-period).
- The **derived-field test** asserts that the engine
  produced a different number (construction equity vs
  operating equity) and the two are reported side by side
  in the snapshot.

C5 does **not** produce the **full audit table** as a runtime
object — that requires the bridge module (C6+). C5 produces
a **policy assertions table** as a test-time data structure
that mirrors the audit table's content.

### 2.1 Policy table (C5 encoding of C2 §2.1)

```python
POLICY_TABLE = (
    # (field_code, current_source, construction_source, policy, c1_blocker)
    ("shl_idc_keur", "project factory", "engine.total_shl_idc_keur", "replaced", "blocker_1_R-PAR-1"),
    ("shl_amount_keur", "project factory", "engine.total_shl_draw_keur", "replaced", "blocker_1_R-PAR-1"),
    ("shl_opening_balance_keur", "computed runtime", "engine.opening_shl_balance_keur", "replaced", "blocker_1_R-PAR-1"),
    ("senior_opening_balance_keur", "project factory (manual)", "engine.opening_senior_balance_keur", "frozen", "blocker_5_R-PAR-2"),
    ("senior_idc_keur", "not modelled", "engine.total_senior_idc_keur", "replaced", "blocker_5_R-PAR-2"),
    ("capex_keur", "project factory", "engine.total_uses_keur", "frozen", "blocker_2_R-PAR-5"),
    ("reserves_keur", "project factory", "not computed", "retained", "n/a"),
    ("vat_operating", "project factory", "not computed", "retained", "n/a"),
    ("financing_fees_keur", "project factory", "not computed", "retained", "n/a"),
    ("commitment_fee_keur", "project factory", "not computed", "retained", "n/a"),
    ("equity_total_keur", "computed runtime", "engine.total_equity_draw_keur", "derived", "blocker_2_R-PAR-5"),
)
```

This is a **mirror of C2 §2.1** (11 fields). The C5 test
asserts that the **POLICY_TABLE matches the C2 §2.1 doc
verbatim** (a docstring test).

---

## 3. Senior IDC effective-rate caveat (C1 R-PAR-2)

C1 R-PAR-2 documents that the senior IDC is calibrated to an
**effective rate**, not modelled from the senior debt rate ×
elapsed period. The effective rate is:

- TUHO: `0.060454449320244484` (gives exactly 1,519.564
  kEUR of senior IDC over 18 months)
- Oborovo: `0.058947812283038616` (gives exactly 1,086.032
  kEUR of senior IDC over 12 months)

The C5 tests assert:

- The engine's `senior_interest_rate` field
  (`ConstructionConfig.senior_interest_rate`) equals the
  snapshot's `caveats.senior_idc_effective_rate` value
  (within `1e-9` tolerance).
- The engine's `total_senior_idc_keur` equals the snapshot's
  `totals_keur.total_senior_idc` value (within `0.001`
  kEUR).
- The test docstring documents the **effective-rate
  brittleness** (C1 R-PAR-2) and notes that fixing it is
  a **separate workstream**.

This is the **C2 §6.5 senior IDC caveat** that C2 §6.5 says
"must include" in the IDC by source test. C5 implements the
caveat as a **docstring + assertion** in the engine-comparison
test, even though the full §6.5 test is deferred to C6+.

---

## 4. Test categories

The C5 test file contains the following test categories:

| Category | What it tests | Test count |
|---|---|---|
| File existence | C5 test file exists, C4 snapshots exist | 4 |
| Engine invocation | Engine runs for TUHO + Oborovo without error | 2 |
| Field count | Engine result has expected fields | 2 |
| Engine field parity | Engine fields match snapshot totals (10 fields × 2 projects) | 20 |
| Engine opening identity | opening = principal + IDC for senior + SHL (4 identities) | 4 |
| Engine monthly grid | Length matches construction_months, sum equals total | 4 |
| Engine caveats | Senior IDC effective rate matches snapshot | 4 |
| Manual-vs-derived policy | 11 policy fields assertable (mirrors C2 §2.1) | 11 |
| Replaced fields | 4 fields: engine == snapshot | 8 (4 × 2 projects) |
| Frozen fields | 2 fields: documented, not enforced at runtime | 4 |
| Retained fields | 4 fields: not computed by engine | 4 |
| Derived fields | 1 field: engine and snapshot both have a value, both correct | 4 |
| Senior IDC caveat | TUHO + Oborovo effective rate assertion | 4 |
| Cross-snapshot | Both projects use same engine parity status | 2 |
| Engine failure modes | Engine raises on bad config | 4 |
| Hard constraints | No app/domain changes (git diff guards) | 4 |
| rc1 frozen | SHA `b425a07...` reachable | 1 |
| C4 dependency | C4 snapshots still exist and pass structure tests | 1 |
| Project statuses | TUHO/Oborovo/Generic Wind/Solar unchanged | 4 |

**Estimated total: ~85 tests.**

The exact test count is determined by the implementation; the
table above is a guideline.

---

## 5. Failure modes covered

### 5.1 Engine produces wrong value

If a future edit to `domain/construction/engine.py` changes
the engine output (e.g. a rounding bug, a missing month, a
wrong rate), the engine-comparison test fails with a clear
assertion message (e.g. `engine total_shl_idc 3568.687 !=
snapshot 3568.688, delta > 0.001 kEUR`).

### 5.2 Snapshot drifts from Excel

If a future edit to a C4 snapshot changes a value to one
that does not match the Excel reference, the
engine-comparison test passes (engine matches snapshot) but
the **drift** is documented in the test output. This is a
**silent drift** and is the failure mode C5 is designed to
**not** cover — the C4 snapshot itself must be the source
of truth.

### 5.3 Engine does not produce a value

If the engine stops producing `total_shl_idc_keur` (e.g. a
refactor removes the field), the engine-comparison test
fails with `AttributeError: 'ConstructionScheduleResult'
object has no attribute 'total_shl_idc_keur'`. The test
docstring notes that this is a **breaking change** and
requires a C-phase.

### 5.4 Policy table drifts from C2 §2.1

If a future edit to the test file changes the POLICY_TABLE
without a corresponding change to the C2 §2.1 doc, the
**docstring cross-check test** fails. This is the
**policy-doc parity** test.

### 5.5 What failure modes are NOT covered

- **Bridge output validation** — C5 does not invoke the
  bridge. Bridge output validation is C6+.
- **Operating waterfall parity** — C5 does not invoke the
  waterfall. Waterfall parity is C9+ (after Layer 5 wiring).
- **End-to-end COD opening balance test** — C5 does not
  verify that the engine's `opening_senior_balance_keur`
  flows into the waterfall. That is C9+.

---

## 6. Hard constraints (re-asserted)

C5 introduces:

- **Allowed:** 1 test file, 1 design doc, 1 report JSON.
  The C4 snapshots are **read-only** (no modifications).
- **NOT allowed:** no app/ changes, no domain/ changes, no
  runtime changes, no model changes, no waterfall changes,
  no CAPEX/debt/SHL/IDC/tax/depreciation formula changes,
  no schema/persistence changes, no feature flags, no
  project status changes, **no new domain modules**.

The C5 PR will be verified against these constraints via
`git diff` against the forbidden paths (`domain/`, `app/`,
`main_web.py`, `main_api.py`, `static/`).

### 6.1 Why C5 does NOT add `domain/construction/opening_bridge.py`

C2 §3.5 specifies that the bridge is a new module in
`domain/construction/opening_bridge.py`. C5 deliberately
**does not add this module** because:

1. **The C-series works in design-implementation spiral.**
   C1 was design, C2 was design, C3 was design, C4 was
   test-only scaffolding, C5 is test-only engine
   comparison. Adding the bridge in C5 would mix
   implementation with test scaffolding, which has been
   explicitly deferred to a separate phase.

2. **The bridge requires a separate design review.** The
   bridge has a specific dataclass contract
   (C2 §3.7 `OpeningBalanceBridgeResult`), a specific
   audit table schema (C2 §4), and a specific algorithm
   (C2 §3.4). Each of these deserves a separate design
   review before implementation.

3. **C5 is a safe first step.** The engine-comparison
   tests can be written and run **today**, without the
   bridge. They establish the **engine parity baseline**
   that the bridge will eventually use.

4. **The bridge is a runtime seam, not a test concern.**
   C2 §3.6.1 says: "The bridge is not a runtime mutation.
   It does not modify Project or any persistence record.
   The output is a value object (a frozen dataclass) that
   Layer 5 may consume." Adding the bridge in C5 would
   create a runtime module that nothing consumes (Layer 5
   is C7+). This is a code smell.

5. **The C6+ phase can add the bridge cleanly.** Once C5
   is merged, C6 can:
   - Add `domain/construction/opening_bridge.py` (the
     bridge module, per C2 §3.5).
   - Add the audit table dataclass.
   - Add the C2 §6.4 / §6.5 / §6.6 tests (COD opening
     balance reconciliation, IDC by source reconciliation,
     no double-counting test plan).
   - Use C5 as the engine-comparison baseline.

This sequencing is consistent with the C-series design:
**engine-comparison first, bridge second, runtime seam
third**.

---

## 7. What's NOT in C5 (deferred)

### 7.1 Bridge module implementation (C6+)

The `domain/construction/opening_bridge.py` module, the
`OpeningBalanceBridgeResult` dataclass, the audit table
schema, and the `BridgeMetadata` dataclass are all
**C6+** deliverables.

### 7.2 COD opening balance reconciliation (C2 §6.4, C6+)

The test that runs the bridge and asserts the bridge
output contains all 6 numeric fields, the audit table has
exactly 11 rows, and the metadata is non-empty — all
**C6+**.

### 7.3 IDC by source reconciliation (C2 §6.5, C6+)

The test that asserts `capitalized_senior_idc_keur +
capitalized_shl_idc_keur == total_idc` within tolerance —
**C6+** (requires the bridge).

### 7.4 No double-counting test plan (C2 §6.6, C6+)

The test that simulates the operating waterfall reading
the bridge output and asserts the double-counting guard
is satisfied — **C6+** (requires the bridge audit table).

### 7.5 Layer 5 runtime seam (C7+)

`use_construction_schedule_engine` flag wiring,
per-project opt-in enforcement, audit trail persistence
— all **C7+**.

### 7.6 Senior IDC base-rate modelling (separate workstream)

C1 R-PAR-2 (senior IDC effective-rate brittleness) is
documented in the C5 test docstring and snapshot caveats
but not fixed. The fix is a **separate workstream**.

### 7.7 Second pair of eyes review (always deferred)

C2 §6.7 (item 8): "The bridge (Layer 4) and the audit
table schema are reviewed by a second pair of eyes" — this
is a **human review** of the C6+ bridge module, not a
test. Deferred to C6+.

---

## 8. Recommendation

### Choice: **B. More validation needed**

Rationale:

1. **C5 implements the engine-comparison tests, not the
   bridge.** The C5 deliverable is the **engine parity
   baseline**. Bridge implementation is C6+. C5 cannot
   prove C2 §6.4/§6.5/§6.6 (those require the bridge);
   C5 can prove C2 §6.1/§6.2/§6.3 (engine parity +
   manual-vs-derived).

2. **The bridge is not implemented.** The bridge is
   **designed** in C2 §3 but **not coded**. C6 must
   implement the bridge before COD opening balance
   reconciliation, IDC by source reconciliation, and
   no-double-counting tests are meaningful. C5 therefore
   cannot include these in scope.

3. **The senior IDC effective-rate caveat is preserved.**
   The C5 tests document the caveat in the test
   docstring and assert the effective rate matches the
   snapshot. The senior IDC remains calibrated to an
   effective rate (C1 R-PAR-2). C5 does not unlock the
   senior IDC fix.

4. **C5 is the right scope for the current C-series state.**
   The C-series is in a **design-implementation spiral**:
   C1, C2, C3 were design. C4 was test scaffolding. C5
   is engine-comparison. C6 will be bridge implementation.
   C5 correctly stops at engine-comparison.

5. **C1 blocker 5 (senior IDC base-rate) is not
   addressed in any new way.** The senior IDC remains
   effective-rate calibrated. C5 documents the caveat
   but does not propose a fix. The fix is a separate
   workstream.

6. **C5 implements 3 of 8 C2 §6.7 readiness items.**
   C2 §6.7 has 8 items: TUHO snapshot, Oborovo
   snapshot, manual-vs-derived reconciliation, COD
   opening balance reconciliation, IDC by source
   reconciliation, no double-counting test plan, senior
   IDC caveat in docstring, second pair of eyes review.
   C5 implements items 1, 2, 3, 7 (4 items at the
   engine-comparison level). C5 partially implements
   items 4, 5, 6 (deferred to C6+ for the bridge-level
   tests). C5 does not implement item 8 (deferred to
   C6+ for the human review).

### What would unblock "A. Ready for C6+"

- A C5 design note that:
  - Implements engine-comparison tests ✅ (this PR)
  - Verifies the senior IDC caveat is in the engine
    comparison test docstring ✅ (this PR)
  - Documents the policy table from C2 §2.1 ✅ (this PR)
- A C6 design note that:
  - Implements `domain/construction/opening_bridge.py`
    (C2 §3.5)
  - Implements the `OpeningBalanceBridgeResult`
    dataclass (C2 §3.7)
  - Implements the audit table schema (C2 §4)
  - Implements the C2 §6.4 / §6.5 / §6.6 tests
  - Adds the CI workflow that runs the parity tests

### What remains open after C5

- Bridge module implementation (C6+).
- COD opening balance reconciliation (C2 §6.4, C6+).
- IDC by source reconciliation (C2 §6.5, C6+).
- No double-counting test plan (C2 §6.6, C6+).
- Layer 5 runtime seam (C7+).
- Opt-in flag flip (C7+).
- Senior IDC base-rate modelling (separate workstream).
- Second pair of eyes review (always deferred to C6+).

### Multi-phase path

| Phase | Scope | Status |
|---|---|---|
| C1 | Design gate | ✅ Merged `5fccc3a` |
| C2 | SHL IDC convention + Layer 4 bridge design | ✅ Merged `59f9e3d` |
| C3 | Construction parity framework design | ✅ Merged `aa800a5` |
| C4 | Snapshot scaffolding + structure tests | ✅ Merged `dcc30b6` |
| **C5** | **Engine-comparison tests (no bridge)** | **This PR (DRAFT)** |
| C6 | Layer 4 bridge module + audit table | Future |
| C7 | Layer 5 runtime seam (default-off) | Future |
| C8 | Opt-in flag flip + TUHO promotion | Future |
| C9 | Oborovo promotion | Future |

---

## 9. C2 §6.7 readiness checklist status (post-C5)

Mapping to C2 §6.7:

- [x] **TUHO construction-period parity snapshot exists and
      passes** — **fully implemented** in C5 (engine parity
      asserted).
- [x] **Oborovo construction-period parity snapshot exists and
      passes** — **fully implemented** in C5 (engine parity
      asserted).
- [x] **Manual-vs-derived reconciliation test exists and passes**
      — **fully implemented** in C5 (policy table asserted,
      11 fields from C2 §2.1).
- [ ] **COD opening balance reconciliation test exists and
      passes** — **deferred** to C6+ (requires bridge module).
- [ ] **IDC by source reconciliation test exists and passes**
      — **deferred** to C6+ (requires bridge output).
- [ ] **No double-counting test plan is implemented as an
      executable test and passes** — **deferred** to C6+
      (requires bridge audit table).
- [x] **The senior IDC effective-rate caveat is documented in
      the parity snapshot test docstring** — **fully
      implemented** in C5 (caveat in test docstring +
      effective rate assertion).
- [ ] **The bridge (Layer 4) and the audit table schema are
      reviewed by a second pair of eyes** — **deferred** to
      C6+ (human review of the bridge module).

**4 of 8 C2 §6.7 readiness items have engine-comparison-level
C5 implementation. 3 of 8 are deferred to C6+ for
bridge-level implementation. 1 of 8 is the human review
(always deferred).**

---

## 10. Hard constraints (re-asserted)

C5 introduces **no app/ runtime changes, no domain model
changes, no waterfall changes, no CAPEX formula changes, no
debt/SHL/IDC runtime changes, no tax changes, no depreciation
changes, no schema/persistence changes, no feature flags, no
project status changes, no new domain modules**. The C5
deliverable is **1 test file + 1 design doc + 1 report JSON**.
C4 snapshots are read-only. Construction engine remains
diagnostic-only via the `use_construction_schedule_engine`
flag (default-off).

---

## 11. Stop after report

This document is the C5 deliverable. The C5 PR is opened as
DRAFT. Do not mark ready. Do not merge. Stop after report.

---

Deliverables: this document +
`reports/phase_c5_construction_engine_comparison.json` +
`tests/test_phase_c5_construction_engine_comparison.py`.
