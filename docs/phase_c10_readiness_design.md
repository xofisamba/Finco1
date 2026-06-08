# Phase C10 Readiness Design — TUHO Controlled Promotion Gate (docs/tests only)

> **Scope label:** `DESIGN ONLY. NO IMPLEMENTATION. NO PROMOTION. NO WATERFALL ROUTING. NO FLAG FLIP. NO RUNTIME WIRING. NO SENIOR IDC PROMOTION. NO OBOROVO.`

## 0. Purpose

This is the **C10 readiness design** PR. It defines the TUHO
controlled promotion gate but **does not implement promotion**.

C10 is the first phase in which a specific project's bridge
values are routed into the runtime waterfall. The goal of this
PR is to:

- Define the **allowed fields** for TUHO controlled promotion.
- Define the **blocked fields** (with R-PAR-2 caveat).
- Define the **parity gates** for each allowed field.
- Define the **rollback plan** if a promotion causes a parity
  regression.
- Define the **no-go checks** that must be green before any
  promotion PR can open.
- Define the **required approvals** (modelling governance
  board, audit team, senior lender representative).
- Define the **exact tests needed** before any promotion PR
  can open.

This is a **docs/tests-only PR**. No code change. No
implementation. No promotion. No waterfall routing. No
feature-flag enablement. No runtime wiring.

## 1. Why C10 is TUHO-only (and not Oborovo)

C10 is the **first** controlled promotion phase. Per the
hard rules:

- **No Oborovo before TUHO.**
- TUHO is the **Level 2** project (more mature parity
  baseline; C1–C5 parity tests cover TUHO).
- Oborovo will follow as **C11** after C10 is proven.

C10 promotes only TUHO's bridge values. Oborovo's bridge
values remain unpromoted. The C9 guard ensures this
unilaterally: each promotion is gated by a per-project
opt-in flag (defined in §3.4 below) that is set to
`tuho=False, oborovo=False` by default.

## 2. Allowed fields for C10 (TUHO controlled promotion)

The C9 guard classifies fields by policy:

- **frozen** — never promoted (senior_opening_balance_keur,
  capex_keur)
- **replaced** — promotable if `promotion_requested=True`
  (and R-PAR-2 fields additionally require
  `rpar2_resolved=True`)
- **derived** — promotable if `parity_ok=True`
- **retained** — pass-through, always OK

For C10, the **allowed fields** are:

| Field | Policy | C10 eligible? | Why |
|---|---|---|---|
| `shl_idc_keur` | replaced | **YES** | No R-PAR-2; SHL is non-senior, no covenant concern. |
| `shl_amount_keur` | replaced | **YES** | No R-PAR-2; SHL is non-senior. |
| `shl_opening_balance_keur` | replaced | **YES** | No R-PAR-2; SHL is non-senior. |
| `equity_total_keur` | derived | **YES** | Parity baseline against rc1 must be green. |
| `senior_idc_keur` | replaced (R-PAR-2) | **NO** | R-PAR-2 is open (PR #556). Excluded until governance decision. |
| `senior_opening_balance_keur` | frozen | **NO** | Always frozen. |
| `capex_keur` | frozen | **NO** | Always frozen. |
| `reserves_keur` | retained | n/a | Pass-through, not actively promoted. |
| `vat_operating` | retained | n/a | Pass-through. |
| `financing_fees_keur` | retained | n/a | Pass-through. |
| `commitment_fee_keur` | retained | n/a | Pass-through. |

C10 promotes **4 fields** for TUHO: 3 replaced (SHL) + 1
derived (equity_total). Senior IDC is explicitly excluded
pending the R-PAR-2 governance decision.

## 3. Per-field design

### 3.1 `shl_idc_keur` (replaced)

**Source:** Layer 4 bridge `build_opening_balance_bridge()`.

**Target:** Waterfall's SHL IDC line (currently the
`shl_idc_keur` field in the construction engine input).

**Parity baseline:** rc1 (`b425a0708719eaa5e1d922b1008e5609758e0ad4`).
The post-correction snapshot for TUHO must match rc1 within
±1% (per the existing Phase 9 parity pack tolerance).

**Pre-promotion check (test):**
- `test_c10_shl_idc_parity_vs_rc1`: assert bridge
  `shl_idc_keur` is within ±1% of rc1 value for TUHO.

**Promotion mechanism:** the C9 guard is called by a new
`promote_field` method (NOT in this PR; will be in C10-impl
PR after this design is approved).

**Rollback:** the previous (legacy) SHL IDC value is cached
in the persistence layer. A single call to
`rollback_field('shl_idc_keur')` restores it.

### 3.2 `shl_amount_keur` (replaced)

**Source:** Layer 4 bridge `build_opening_balance_bridge()`.

**Target:** Waterfall's SHL amount line.

**Parity baseline:** rc1 ±1%.

**Pre-promotion check (test):**
- `test_c10_shl_amount_parity_vs_rc1`.

**Promotion mechanism:** as 3.1.

**Rollback:** as 3.1.

### 3.3 `shl_opening_balance_keur` (replaced)

**Source:** Layer 4 bridge `build_opening_balance_bridge()`.

**Target:** Waterfall's SHL opening balance line.

**Parity baseline:** rc1 ±1%.

**Pre-promotion check (test):**
- `test_c10_shl_opening_balance_parity_vs_rc1`.

**Promotion mechanism:** as 3.1.

**Rollback:** as 3.1.

### 3.4 `equity_total_keur` (derived)

**Source:** Layer 4 bridge `build_opening_balance_bridge()`.
This is a **derived** field: the bridge computes
`equity_total_keur` from the sum of all the project's
sources of capital (senior, SHL, equity, grants, etc.). The
parity gate is the **rc1 baseline** for the post-correction
snapshot.

**Target:** Waterfall's equity total line.

**Parity baseline:** rc1 ±0.5% (stricter tolerance for
derived fields, because they aggregate all the other
fields' errors).

**Pre-promotion check (test):**
- `test_c10_equity_total_parity_vs_rc1`.

**Promotion mechanism:** as 3.1, but the guard requires
`parity_ok=True` (per C9 guard's `equity_total_keur` rule).

**Rollback:** as 3.1.

## 4. Parity gates (per-project)

C10 establishes **per-project parity baselines** against rc1.
The rc1 SHA is `b425a0708719eaa5e1d922b1008e5609758e0ad4`.
The baseline is the **post-correction snapshot** for TUHO
(`tests/fixtures/construction_parity/tuho_construction_snapshot.json`).

**Per-field parity tolerance:**

| Field | Tolerance | Notes |
|---|---|---|
| `shl_idc_keur` | ±1% | Per Phase 9 parity pack |
| `shl_amount_keur` | ±1% | Per Phase 9 parity pack |
| `shl_opening_balance_keur` | ±1% | Per Phase 9 parity pack |
| `equity_total_keur` | ±0.5% | Stricter for derived/aggregate |

**The parity gate is a single test that runs all 4 fields
against the rc1 baseline and asserts the absolute % delta is
within the tolerance for each field.** If any field fails
the gate, **all promotions are blocked** (atomic promotion
semantics).

## 5. Rollback plan

The C10 promotion will **cache** the previous (legacy) value
of each promoted field in the persistence layer before
applying the new bridge value. A **single rollback call**
restores all cached values atomically.

**Rollback triggers (any one of):**

- Parity regression detected post-promotion
  (the post-promotion snapshot fails any of the 4 parity
  tests within 24 hours).
- Senior lender notifies the project of a covenant
  discrepancy.
- Modelling governance board issues a halt.
- Audit team flags a defect.

**Rollback procedure:**

1. Call `rollback_c10_promotion()` (NOT in this PR; will be
   in C10-impl PR).
2. Verify the post-rollback snapshot matches the pre-promotion
   snapshot.
3. Run the Phase 9 parity pack; assert all parity tests pass.
4. Notify stakeholders.

**Rollback is idempotent.** Calling it twice has the same
effect as calling it once.

## 6. No-go checks

The C10 implementation PR (C10-impl) **cannot open** until
**all** of the following are green:

| # | Check | Owner |
|---|---|---|
| 1 | This PR (C10 readiness design) is merged | PR review |
| 2 | R-PAR-2 decision discovery PR (#556) is reviewed and a decision (A/B/C) is recorded | Governance |
| 3 | `use_construction_schedule_engine` is `False` (default-off) | C9 already enforces |
| 4 | `senior_idc_keur` is **EXCLUDED** from C10's allowed fields list | C9 guard enforces |
| 5 | All C1–C9 tests pass on main | CI |
| 6 | TUHO's rc1 parity snapshot is within ±1% (SHL) and ±0.5% (equity) | Parity test |
| 7 | Senior lender representative has been notified of the C10 plan | Communication |
| 8 | Modelling governance board has approved the C10 plan | Governance |
| 9 | Audit team has reviewed the C10 design | Audit |
| 10 | Oborovo is **NOT** in scope of C10 | C9 guard enforces |

If any of these is red, C10-impl **cannot open**.

## 7. Required approvals

Before the C10-impl PR can be **merged**, the following
approvals are required:

| Approver | What they approve |
|---|---|
| Modelling governance board | The promotion of the 4 allowed fields, the parity gates, the rollback plan, the no-go checks. |
| Senior lender representative | Acknowledgement that the senior opening balance and senior IDC remain `frozen` (not promoted in C10). |
| Audit team | The pre-promotion snapshot, the parity baseline, the rollback plan, and the audit trail. |
| Project lead | Final go/no-go decision. |

The C10-impl PR's description must list all four
approvals explicitly, with timestamps and approver names.
Without all four, C10-impl **cannot merge**.

## 8. Tests needed before any promotion PR can open

The C10-impl PR (NOT this one) must include the following
test classes:

### 8.1 `TestC10AllowedFieldsList`

Verifies that the C10 allowed fields list is exactly:

```python
C10_ALLOWED_FIELDS = (
    "shl_idc_keur",
    "shl_amount_keur",
    "shl_opening_balance_keur",
    "equity_total_keur",
)
```

And that `senior_idc_keur`, `senior_opening_balance_keur`,
`capex_keur` are **NOT** in the list.

### 8.2 `TestC10PerFieldParityVsRc1`

For each allowed field, asserts the post-correction snapshot
matches the rc1 baseline within tolerance:

- `test_shl_idc_parity`: |bridge - rc1| / rc1 ≤ 1%
- `test_shl_amount_parity`: ≤ 1%
- `test_shl_opening_balance_parity`: ≤ 1%
- `test_equity_total_parity`: ≤ 0.5%

If any fails, the test class fails.

### 8.3 `TestC10AtomicPromotion`

Verifies that the C10 promotion is **atomic**: either all 4
fields are promoted, or none. A partial promotion is a
**fail**.

### 8.4 `TestC10Rollback`

Verifies that calling `rollback_c10_promotion()`:

- Restores all 4 fields to their pre-promotion values.
- Is idempotent.
- Passes the Phase 9 parity pack post-rollback.

### 8.5 `TestC10ExcludesOborovo`

Verifies that the C10 promotion is **TUHO-only**: Oborovo's
bridge values are NOT promoted. The test asserts that the
post-C10 Oborovo snapshot matches the pre-C10 Oborovo
snapshot.

### 8.6 `TestC10NoGoChecks`

A self-check that verifies the 10 no-go checks in §6 are
green at PR-open time. If any is red, the test fails.

### 8.7 `TestC10Rpar2Exclusion`

Verifies that the C9 guard's R-PAR-2 block is in effect for
`senior_idc_keur`. A direct call to
`assert_no_construction_runtime_promotion` with
`senior_idc_keur`, `policy='replaced'`, and `promotion_requested=True`
must RAISE (because `rpar2_resolved=False` by default).

### 8.8 `TestC10ScopeGuards`

C10's own `TestScopeGuards` (commit-relative, per PR #554
pattern). Verifies that C10 only adds the expected files and
does not touch `main_web.py`, `main_api.py`, `static/`,
`domain/`, or other forbidden paths.

### 8.9 `TestC10FeatureFlagUnchanged`

Verifies that `use_construction_schedule_engine` remains
`False` (default-off) after C10-impl. C10-impl must not
flip this flag.

### 8.10 `TestC10Rc1Untouched`

Verifies that rc1 (`b425a07...`) is reachable on
`origin/main` and that C10-impl has not modified it.

## 9. Hard rules confirmed

- ✓ **rc1 untouched:** `b425a07...` reachable on `origin/main`;
  no modifications from C10 readiness design
- ✓ **No global construction flag enablement:**
  `use_construction_schedule_engine: bool = False` (default-off)
- ✓ **No waterfall routing:** no app/waterfall_* changes
- ✓ **No runtime promotion:** no `promote_field` method exists
  (C9 has the guard; the caller is a C10-impl concern)
- ✓ **No senior IDC promotion without R-PAR-2 decision:**
  `senior_idc_keur` excluded from C10's allowed fields
- ✓ **No Oborovo before TUHO:** C10 is TUHO-only; Oborovo is
  C11
- ✓ **All PRs DRAFT until reviewed:** this PR is DRAFT
- ✓ **Each phase self-reviewed and ran relevant tests:**
  combined 1067/1067 pass on main, 0 deselected

## 10. Files in this PR (3, all docs+test)

| File | Purpose |
|---|---|
| `docs/phase_c10_readiness_design.md` | C10 readiness design (this file) |
| `reports/phase_c10_readiness_design.json` | Machine-readable C10 readiness report |
| `tests/test_phase_c10_readiness_design.py` | C10 readiness design tests (test-only) |

## 11. Stop after report

This is a **design** PR. It is **DRAFT**. It does **not**
implement promotion. It does **not** open a `promote_field`
method. It does **not** change the model, formulas, runtime,
waterfall, persistence, UI, or feature flags.

The next step (C10-impl) is a **future** PR that requires:

- This PR (#557) merged
- PR #556 (R-PAR-2 decision) reviewed
- Governance decision on R-PAR-2 recorded
- All 4 approvals (governance, senior lender, audit, project
  lead) obtained
- User approval to begin implementation
