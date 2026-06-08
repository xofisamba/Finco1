# Phase C4 - Construction Period Parity Test Implementation

> **Scope label:** **Snapshot structure validation only — no runtime
> construction engine comparison yet.**
>
> Type: TEST / VALIDATION IMPLEMENTATION (no runtime, no model, no formula)
> Status: DRAFT
> Date: 2026-06-08
> Base SHA: `aa800a5` (post-Phase C1, C2, C3)
> Branch: `phase-c4-construction-parity-test-implementation`
> Hard constraints: **NO app/ runtime changes, NO domain model changes, NO
> waterfall changes, NO CAPEX formula changes, NO debt/SHL/IDC runtime
> changes, NO tax changes, NO depreciation changes, NO schema/persistence
> changes, NO feature flags, NO project status changes**

---

## 0. Purpose

C3 (`aa800a5`) defined the **construction period parity framework** at
the design level: 3 layers (funding, IDC, opening balance), 2 golden
datasets (TUHO + Oborovo), 349 canonical fields, schema version
`C3-1.0`, tolerance ±0.001 kEUR. C3 produced the design doc and a
report JSON — **no tests, no fixtures**.

This C4 phase **implements the test scaffolding** for the C3 framework.
It does **not** wire the construction engine into the operating
runtime. It does **not** compare engine output to the golden dataset.
It does **not** change formulas, debt, tax, depreciation, IDC, or
project status.

The C4 deliverable is **structure-only** validation:

- Frozen golden snapshot files exist (TUHO + Oborovo).
- The snapshots conform to the C3 schema (`C3-1.0`).
- The snapshots have the correct field counts (207 + 142 = 349).
- The monthly grid lengths match the calendar (18 for TUHO, 12 for
  Oborovo).
- The totals reconcile with the sum of monthly flows.
- The opening balance identities hold (opening = principal + IDC).
- The dates match the Excel reference.
- The tolerance policy is documented and enforced.
- The senior IDC effective-rate caveat is documented in both
  snapshots.

**This phase does NOT prove that the construction engine matches the
golden dataset.** That is a C5+ deliverable, after Layer 4 bridge
implementation and engine wiring decisions are made.

---

## 1. What C4 implements

### 1.1 Frozen golden snapshots (2 files)

| Project | Path | Field count |
|---|---|---|
| TUHO | `tests/fixtures/construction_parity/tuho_construction_snapshot.json` | 207 |
| Oborovo | `tests/fixtures/construction_parity/oborovo_construction_snapshot.json` | 142 |

Both snapshots are **frozen** in the sense that:

- They are **checked into the repo** (not generated at test time).
- They are **human-readable** (JSON, not binary).
- They are **versioned** (`schema_version: C3-1.0`).
- They are **declarative** (no Python code).
- They are **tested** for structural integrity (see §1.2).

A future change to a snapshot requires a C-phase (per C3 §9.4 schema
freeze rule).

### 1.2 Structural validation tests (1 file)

`tests/test_phase_c4_construction_parity_snapshots.py` contains tests
that:

- Load both snapshots from disk.
- Validate the schema version is `C3-1.0`.
- Validate the project codes are correct (`TUHO-WIND-1`, `OBOROVO`).
- Validate the tolerance policy is `exact_0.001_keur`.
- Validate the field counts (207 + 142 = 349 total).
- Validate the monthly grid length matches `construction_months`
  (18 for TUHO, 12 for Oborovo).
- Validate the monthly grid values sum to the `total_uses_keur`.
- Validate the cumulative values are monotonically non-decreasing.
- Validate the cumulative values match the running sum of monthly
  values (within ±0.001 kEUR).
- Validate the calendar dates are present and match the Excel
  reference.
- Validate the opening balances are present and satisfy the identity
  `opening = principal + IDC` (within ±0.001 kEUR).
- Validate the senior IDC effective-rate caveat is documented.
- Validate the SHL IDC convention reference is documented.
- Validate the missing-field failure mode (deleting a field from
  one snapshot causes a test to fail loudly).
- Validate the schema-version mismatch failure mode (changing the
  version in a snapshot causes a test to fail loudly).

### 1.3 What C4 does NOT implement

- **No engine comparison.** The construction engine
  (`domain/construction/engine.py`) is **not** invoked by the C4
  tests. The snapshots are validated **standalone**, not against
  engine output.
- **No CI workflow.** A CI workflow that runs the C4 tests on every
  push is a C5+ deliverable. C4 only adds the test file and the
  snapshot files; running the tests is the responsibility of the
  existing pytest setup.
- **No helper functions in production code.** The C4 tests are
  self-contained; any helper functions live in the test file or in
  the snapshot JSON.
- **No runtime wiring.** `use_construction_schedule_engine` remains
  default-off. The operating waterfall is untouched.

---

## 2. Why snapshot-only is the right C4 scope

C3 produced 3 artifacts:

1. A design doc (`docs/phase_c3_construction_parity_snapshot_design.md`)
2. A report JSON (`reports/phase_c3_construction_parity_snapshot_design.json`)
3. A design test file (`tests/test_phase_c3_construction_parity_snapshot_design.py`)

C3 explicitly stated that the **parity test implementation** is a
**C4+** deliverable. C4 is the **first implementation step**, and the
**only safe implementation step** is the **snapshot structure
validation** — because:

- The construction engine is still **diagnostic-only** (Phase 7I
  default-off).
- The Layer 4 bridge (C2 design) is **not implemented**.
- The Layer 5 seam (C2 design) is **not wired**.
- Wiring the engine into the test would create a **runtime
  comparison** that the C-series has explicitly deferred.

Implementing engine comparison in C4 would be a **scope violation**
of the C-series design gates. The right C4 deliverable is the
**snapshot scaffolding** that future C5+ phases will use to run
engine comparison.

### 2.1 The snapshot is the contract

Once the snapshot is in place, it is the **contract** between:

- The Excel reference (TUHO/Oborovo workbook values).
- Any future construction engine output.
- The Layer 4 bridge (when implemented).

C4 freezes the contract. C5+ compares the engine output to the
contract.

### 2.2 The snapshot is the audit trail

The snapshot JSON files are **human-readable audit records** of the
Excel reference values. A future auditor can:

- Open `tuho_construction_snapshot.json`.
- See the 207 fields and their expected values.
- Compare to the Excel workbook.
- Verify the contract has not drifted.

C4 freezes the audit trail. C5+ uses the audit trail to validate
the engine.

---

## 3. TUHO snapshot structure

The TUHO snapshot
(`tests/fixtures/construction_parity/tuho_construction_snapshot.json`)
contains:

```json
{
  "project_code": "TUHO-WIND-1",
  "schema_version": "C3-1.0",
  "tolerance_policy": "exact_0.001_keur",
  "field_count_expected": 207,
  "calendar": {
    "construction_start_date": "2028-06-30",
    "cod_date": "2029-12-30",
    "shl_investment_date": "2028-06-30",
    "construction_months": 18
  },
  "totals_keur": {
    "total_uses": 72994.450,
    "total_equity_draw": 500.000,
    "total_shl_draw": 29135.176,
    "total_junior_draw": 0.000,
    "total_senior_draw": 43359.274,
    "total_shl_idc": 3568.688,
    "total_senior_idc": 1519.564
  },
  "opening_balances_keur": {
    "opening_senior_balance": 44878.838,
    "opening_shl_balance": 32703.864,
    "equity_contribution_at_cod": 500.000
  },
  "monthly_grid": [
    {"month_index": 1, "monthly_uses_keur": 24226.729, ...},
    ... (18 rows)
  ],
  "funding_caps_keur": {...},
  "rates": {
    "shl_interest_rate": 0.08,
    "senior_interest_rate_effective": 0.060454449320244484
  },
  "caveats": {
    "senior_idc_effective_rate_caveat_applies": true,
    "senior_idc_effective_rate": 0.060454449320244484,
    "senior_idc_target_keur": 1519.564,
    "policy_reference": "C1 R-PAR-2, C2 §2.1 freeze, C3 §6.3",
    "shl_idc_convention": "Excel full-source elapsed compound (C2 Convention B)",
    "equity_idc_capitalized": false
  },
  "source_documents": {
    "monthly_uses_source": "tuho.py:TUHO_MONTHLY_USES_KEUR",
    "funding_caps_source": "tuho.py:build_tuho_construction_config()",
    "totals_source": "Excel reference (Phase 7F / 7I discovery)"
  }
}
```

The C4 tests validate this structure end-to-end.

### 3.1 TUHO field count verification

The C3 design spec states **207 fields** for TUHO. The C4 test
asserts `field_count_expected == 207`. A future change to the
spec requires a C-phase (C3 §9.4).

### 3.2 TUHO monthly grid verification

The C4 test asserts:

- `len(monthly_grid) == construction_months` (18).
- For each row, `monthly_uses_keur` is a number.
- The sum of all `monthly_uses_keur` equals `total_uses` (within
  ±0.001 kEUR).
- The cumulative values are monotonically non-decreasing.
- The cumulative values match the running sum of monthly values.

### 3.3 TUHO opening balance identity verification

The C4 test asserts:

- `opening_senior_balance == total_senior_draw + total_senior_idc`
  (within ±0.001 kEUR).
- `opening_shl_balance == total_shl_draw + total_shl_idc` (within
  ±0.001 kEUR).
- `equity_contribution_at_cod == total_equity_draw` (within
  ±0.001 kEUR).

These identities are the **C2 §7.4 hard identities** — they are not
calibrated, they are derived from first principles.

### 3.4 TUHO caveat verification

The C4 test asserts:

- `caveats.senior_idc_effective_rate_caveat_applies == true`.
- `caveats.senior_idc_effective_rate` matches the value in
  `tuho.py:senior_interest_rate` (0.060454449320244484).
- `caveats.policy_reference` references C1, C2, and C3.
- `caveats.shl_idc_convention` references C2 Convention B.
- `caveats.equity_idc_capitalized == false`.

---

## 4. Oborovo snapshot structure

The Oborovo snapshot
(`tests/fixtures/construction_parity/oborovo_construction_snapshot.json`)
mirrors the TUHO structure with Oborovo-specific values. The C4 tests
validate the Oborovo snapshot with the same checks as TUHO, but with
Oborovo-specific reference values.

### 4.1 Oborovo field count verification

The C3 design spec states **142 fields** for Oborovo. The C4 test
asserts `field_count_expected == 142`.

### 4.2 Oborovo monthly grid verification

The C4 test asserts:

- `len(monthly_grid) == 12`.
- The sum of all `monthly_uses_keur` equals 57,973.041 kEUR.
- The cumulative values are monotonically non-decreasing.
- The cumulative values match the running sum of monthly values.

### 4.3 Oborovo opening balance identity verification

The C4 test asserts:

- `opening_senior_balance == 42,852.267 + 1,086.032 = 43,938.299`.
- `opening_shl_balance == 14,620.774 + 1,169.662 = 15,790.436`.
- `equity_contribution_at_cod == 500.000`.

### 4.4 Oborovo caveat verification

The C4 test asserts:

- `caveats.senior_idc_effective_rate_caveat_applies == true`.
- `caveats.senior_idc_effective_rate` matches the value in
  `oborovo.py:senior_interest_rate` (0.058947812283038616).
- `caveats.policy_reference` references C1, C2, and C3.
- `caveats.shl_idc_convention` references C2 Convention B.
- `caveats.equity_idc_capitalized == false`.

---

## 5. Test categories

The C4 test file contains the following test categories:

| Category | What it tests | Test count |
|---|---|---|
| File existence | Both snapshots exist on disk | 2 |
| Schema version | Both snapshots declare `C3-1.0` | 2 |
| Project codes | TUHO + Oborovo codes match | 2 |
| Tolerance policy | Both declare `exact_0.001_keur` | 2 |
| Field count | TUHO 207, Oborovo 142, total 349 | 3 |
| Monthly grid | Length matches construction_months | 2 |
| Monthly sum | Sum equals total_uses | 2 |
| Cumulative monotonicity | Cumulatives are non-decreasing | 2 |
| Cumulative identity | Each cumulative = running sum of monthly | 36 (18+12 + totals) |
| Calendar dates | 3 dates present per project | 6 |
| Totals | 7 total fields present per project | 14 |
| Opening balances | 3 opening balances present per project | 6 |
| Opening identity | opening = principal + IDC | 6 (3 per project) |
| Caveats | Senior IDC + SHL IDC + equity caveats | 6 |
| Failure modes | Missing field fails loudly | 4 (2 per project) |
| Failure modes | Schema version mismatch fails loudly | 2 |
| Failure modes | Tolerance policy mismatch fails loudly | 2 |
| Failure modes | Opening balance identity violation fails loudly | 2 |
| Cross-snapshot | Total field count = 207 + 142 = 349 | 1 |
| Cross-snapshot | Both use same schema version | 1 |
| Cross-snapshot | Both use same tolerance policy | 1 |
| Reference consistency | Snapshot values match `tuho.py` / `oborovo.py` source | 4 |

**Estimated total: ~120 tests.**

The exact test count is determined by the implementation; the table
above is a guideline.

---

## 6. Failure modes covered

The C4 tests must cover the following failure modes. If a test
breaks because of a real regression, it must fail **loudly** (i.e.
with a clear assertion message, not a KeyError or AttributeError).

### 6.1 Missing field

If a future edit removes `total_uses_keur` from one snapshot, the
test must fail with: `KeyError: 'total_uses_keur'` or equivalent
clear message.

The C4 tests assert that **all required top-level keys are present**
in each snapshot. The set of required keys is documented in the
test file.

### 6.2 Schema version mismatch

If a future edit changes `schema_version` from `C3-1.0` to
`C3-1.1` without a corresponding C-phase, the test must fail. The
C4 test asserts `schema_version == "C3-1.0"`.

A version bump is a **breaking change** and requires a C-phase.

### 6.3 Tolerance policy mismatch

If a future edit changes `tolerance_policy` from `exact_0.001_keur`
to something else, the test must fail. The C4 test asserts
`tolerance_policy == "exact_0.001_keur"`.

A tolerance change is a **breaking change** and requires a C-phase.

### 6.4 Opening balance identity violation

If a future edit changes `opening_senior_balance` to a value that
does not equal `total_senior_draw + total_senior_idc`, the test
must fail. This is the C2 §7.4 hard identity.

### 6.5 Reference drift

The C4 tests cross-check snapshot values against the source files:

- `tuho.py:TUHO_MONTHLY_USES_KEUR` (the 18 monthly uses).
- `tuho.py:build_tuho_construction_config()` (the funding caps).
- `oborovo.py:OBOROVO_MONTHLY_USES_KEUR` (the 12 monthly uses).
- `oborovo.py:build_oborovo_construction_config()` (the funding
  caps).

If a future edit changes `tuho.py` without updating the snapshot
(or vice versa), the test must fail. This catches **drift
between the source of truth and the snapshot**.

### 6.6 What failure modes are NOT covered

- **No engine output validation** — the C4 tests do not invoke
  the construction engine. Engine output validation is C5+.
- **No runtime wiring validation** — the C4 tests do not exercise
  the operating waterfall with construction input.
- **No end-to-end COD opening balance test** — that requires
  Layer 4 bridge implementation (C2 design, C5+ code).

---

## 7. Hard constraints (re-asserted)

C4 introduces:

- **Allowed:** 1 test file, 2 snapshot fixture files, 1 design
  doc, 1 report JSON.
- **NOT allowed:** no app/ changes, no domain/ changes, no
  runtime changes, no model changes, no waterfall changes, no
  CAPEX/debt/SHL/IDC/tax/depreciation formula changes, no
  schema/persistence changes, no feature flags, no project
  status changes.

The C4 PR will be verified against these constraints via
`git diff` against the forbidden paths (`domain/`, `app/`,
`main_web.py`, `main_api.py`, `static/`).

---

## 8. What's NOT in C4 (deferred)

### 8.1 Engine comparison (C5+)

The actual parity test — load the snapshot, run the construction
engine, compare engine output to snapshot — is **C5+**. C5 is
**Layer 4 bridge implementation**, which is the prerequisite
for engine comparison.

### 8.2 CI workflow (C5+)

A CI workflow that runs the C4 (and future C5+) tests on every
push is **C5+**. C4 only adds the test files; running them is
the responsibility of the existing pytest setup.

### 8.3 Layer 4 bridge implementation (C5+)

The Layer 4 bridge is **designed** in C2 but **not implemented**.
Implementation requires a separate design review (C2 §3
recommendation: C5+ for implementation, after the parity
framework is in place).

### 8.4 Layer 5 seam implementation (C6+)

The Layer 5 seam is **bounded** in C2 §5 but **not wired**.
Wiring requires a runtime change, which is out of scope for the
C-series.

### 8.5 Opt-in flag flip (C7+)

`use_construction_schedule_engine` remains **default-off**. The
flag flip is C7+ and requires all of the above.

### 8.6 Senior IDC base-rate modelling (separate workstream)

C1 R-PAR-2 (senior IDC effective-rate brittleness) is documented
in the C4 snapshot caveats but not fixed. The fix is a separate
workstream.

---

## 9. Recommendation

### Choice: **B. More validation needed**

Rationale:

1. **C4 implements the snapshot scaffolding, not the engine
   comparison.** The C4 deliverable is the **frozen snapshots +
   structure validation tests**. Engine comparison is C5+. C4
   cannot prove parity; it can only prove that the snapshots
   are well-formed.

2. **The Layer 4 bridge is not implemented.** The bridge is
   **designed** in C2 §3 but **not coded**. C5 must implement
   the bridge before engine comparison is meaningful. C4
   therefore cannot include engine comparison in scope.

3. **The senior IDC effective-rate caveat is preserved.** The
   C4 snapshots document the caveat. The senior IDC remains
   calibrated to an effective rate (C1 R-PAR-2). C4 does not
   unlock the senior IDC fix.

4. **C4 is the right scope for the current C-series state.**
   The C-series is in a **design-implementation spiral**: C1
   designed the gate, C2 designed the bridge, C3 designed the
   parity framework, C4 implements the snapshot scaffolding.
   C5+ implements the bridge, then engine comparison. C4
   correctly stops at the snapshot scaffolding.

5. **C4 does not address C1 blocker 5 in any new way.** The
   senior IDC base-rate modelling remains a separate
   workstream. C4 documents the caveat but does not propose
   a fix.

### What would unblock "A. Ready for C5+"

- A C5 design note that:
  - Implements the Layer 4 bridge (C2 design → code).
  - Implements the engine comparison test (C4 snapshot +
    engine output).
  - Verifies the senior IDC caveat is in the engine comparison
    test docstring.
  - Adds the CI workflow that runs the parity tests.

### What remains open after C4

- Engine comparison (C5+).
- Layer 4 bridge implementation (C5+).
- CI workflow (C5+).
- Layer 5 seam implementation (C6+).
- Opt-in flag flip (C7+).
- Senior IDC base-rate modelling (separate workstream).

### Multi-phase path

| Phase | Scope | Status |
|---|---|---|
| C1 | Design gate | ✅ Merged `5fccc3a` |
| C2 | SHL IDC convention + Layer 4 bridge design | ✅ Merged `59f9e3d` |
| C3 | Construction parity framework design | ✅ Merged `aa800a5` |
| **C4** | **Snapshot scaffolding + structure tests** | **This PR (DRAFT)** |
| C5 | Layer 4 bridge implementation + engine comparison | Future |
| C6 | Layer 5 seam implementation | Future |
| C7 | Opt-in flag flip | Future |
| C8+ | Other C1-listed work (e.g. promotion, multi-construction) | Future |

---

## 10. C3 readiness checklist status (post-C4)

Mapping to C2 §6.7:

- [x] **TUHO construction-period parity snapshot exists and
      passes** — **implemented** in C4 (structure validation,
      not engine comparison). The snapshot is frozen and
      structure-validated.
- [x] **Oborovo construction-period parity snapshot exists and
      passes** — **implemented** in C4 (structure validation).
- [x] **Manual-vs-derived reconciliation test exists and passes**
      — **partially implemented** in C4 (identity check on
      opening balances). Full reconciliation is C5+.
- [x] **COD opening balance reconciliation test exists and
      passes** — **partially implemented** in C4 (identity check
      on opening = principal + IDC). Full reconciliation
      against engine output is C5+.
- [x] **IDC by source reconciliation test exists and passes** —
      **partially implemented** in C4 (total IDC values
      asserted). Per-month IDC reconciliation is C5+.
- [x] **No double-counting test plan is implemented as an
      executable test and passes** — **partially implemented**
      in C4 (opening balance identity check enforces single
      source per field). Full no-double-counting test plan
      (with C2 §4 audit table) is C5+.
- [x] **The senior IDC effective-rate caveat is documented in
      the parity snapshot test docstring** — **implemented** in
      C4 (caveat in both snapshot JSONs and the test file).
- [ ] **The bridge (Layer 4) and the audit table schema are
      reviewed by a second pair of eyes** — **deferred** to
      C5+.

**7 of 8 C3 readiness items have structure-level C4
implementation. 0 of 8 have engine-comparison-level
implementation. C4 is a snapshot-scaffolding phase, not an
engine-comparison phase.**

---

## 11. Hard constraints (re-asserted)

C4 introduces **no app/ runtime changes, no domain model
changes, no waterfall changes, no CAPEX formula changes, no
debt/SHL/IDC runtime changes, no tax changes, no depreciation
changes, no schema/persistence changes, no feature flags, no
project status changes**. The C4 deliverable is **2 snapshot
fixture files + 1 test file + 1 design doc + 1 report JSON**.
Construction runtime remains diagnostic-only. The opt-in flag
`use_construction_schedule_engine` remains default-off.

---

## 12. Stop after report

This document is the C4 deliverable. The C4 PR is opened as
DRAFT. Do not mark ready. Do not merge. Stop after report.

---

Deliverables: this document +
`reports/phase_c4_construction_parity_test_implementation.json`
+
`tests/test_phase_c4_construction_parity_snapshots.py` +
`tests/fixtures/construction_parity/tuho_construction_snapshot.json` +
`tests/fixtures/construction_parity/oborovo_construction_snapshot.json`.
