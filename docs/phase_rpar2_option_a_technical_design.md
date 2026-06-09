# R-PAR-2 Option A — Technical Design (Hypothetical)

> Type: DESIGN ONLY, DOCS ONLY
> Status: DRAFT
> Date: 2026-06-09
> Base SHA: `233981e4` (post-pilot-readiness stack)
> Branch: `rpar2-option-a-technical-design`
> Hard constraints:
> - **NO IMPLEMENTATION** — design only, hypothetically assuming Option A is chosen
> - No model change
> - No formula change
> - No runtime change
> - No promotion
> - No flag flip
> - No senior IDC promotion
> - No Oborovo before TUHO
> - No persistence/schema changes
> - DRAFT until reviewed
> - rc1 untouched

---

## 0. Purpose

This document is the **technical design for Option A of the
R-PAR-2 senior IDC caveat**, assuming (hypothetically) that the
governance decision is to **model senior IDC base-rate properly**.

Option A is described in PR #562 (`phase_rpar2_decision_pack.md`).
This design assumes Option A is the ratified decision and lays
out the technical work that would be required to implement it.

**This is design only. No implementation. No promotion.** The
actual implementation is a future sprint (likely 25-D per PR #561
sequencing), and only after the governance decision is ratified.

If Option B is the ratified decision, this design document
**remains valid as a future-roadmap artifact** and the
implementation can be triggered later by the re-evaluation
condition in the B decision (PR #562 §9.4).

---

## 1. Scope of the technical change

### 1.1 What changes

- **Senior IDC accrual** in the construction-bridge offline
  domain (`domain/construction/`) is updated to compute interest
  using the **contractual base-rate method** instead of the
  effective-rate method.
- **Senior opening balance at COD** is re-baselined to reflect
  the base-rate accrual (typically higher than effective-rate
  would suggest).
- **C7 POLICY_TABLE** updates: `senior_idc_keur` and
  `senior_opening_balance_keur` are re-categorized from `frozen`
  to `replaced` (per the current intent) and the `c1_blocker_reference`
  is removed (since R-PAR-2 is resolved).
- **C9 guard** is updated: `rpar2_resolved=True` is now the
  default for `senior_idc_keur` and `senior_opening_balance_keur`.
- **C10 readiness** is updated to include `senior_idc_keur` and
  `senior_opening_balance_keur` in the allowed-fields list (these
  are currently `blocked` per PR #557).

### 1.2 What does NOT change

- Runtime waterfall routing is still NOT promoted automatically.
- The construction-period drawdown logic (`spending_profile`,
  `_CAPEX_ITEM_FIELDS`) does not change.
- Tax, depreciation, OPEX, revenue, distributions are unchanged.
- `use_construction_schedule_engine` remains `False`.
- Oborovo is not promoted before TUHO.

---

## 2. Senior IDC base-rate row model

### 2.1 Contractual base-rate method (target)

For each construction period *t* (typically monthly), senior IDC
is computed as:

```
senior_idc_t = senior_outstanding_balance_{t-1} × (base_rate / 12) × time_fraction_t
```

Where:

- `senior_outstanding_balance_{t-1}` is the **drawn senior debt**
  at the end of period *t-1*
- `base_rate` is the **contractual annual interest rate** (e.g.
  6.5% for TUHO per the bridge calibration), not an effective
  blended rate
- `time_fraction_t` accounts for partial periods (e.g. 30/365
  for a 30-day month)

The cumulative senior IDC over the construction period is:

```
senior_idc_construction = sum_t(senior_idc_t)
```

The senior opening balance at COD is:

```
senior_opening_balance_cod = total_senior_drawn + senior_idc_construction
```

(assuming IDC is **not** capitalized into the senior balance; if
it is, the formula is more complex and the bridge needs to
model the capitalization).

### 2.2 Effective-rate method (current, to be replaced)

The current method computes a **blended effective rate** based on
the drawdown profile, then applies it to the average balance.
This is a modelling approximation. The effective rate depends on:

- the shape of the drawdown profile (linear vs S-curve)
- the duration of the construction period
- the peak-to-average balance ratio

For TUHO and Oborovo, the effective rate produces a lower senior
IDC than the base-rate method. The exact delta is documented in
the parity test failures (`test_tax_bridge_consumes_*.py` family).

### 2.3 Key implementation details

- **Monthly granularity** — each construction period is one
  month; partial months use `time_fraction_t`.
- **Balance = drawn, not committed** — interest accrues only on
  the **actually drawn** balance, not on the committed-but-undrawn
  portion. Commitment fees are handled separately (already in the
  `retained` list per C7).
- **Capitalization toggle** — by default, senior IDC is **not**
  capitalized into the senior balance at COD. The opening balance
  equals principal drawn plus accrued interest as a separate
  line. If the project requires capitalization (e.g. PIK
  treatment), it is a separate field with explicit user opt-in.
- **Senior opening balance at COD** = principal drawn (sum of
  monthly draws) + cumulative senior IDC (separate line).

---

## 3. Required inputs

| Input | Source | Currently in runtime? | Notes |
|---|---|---|---|
| Senior base rate (annual) | Project input (UI form) | yes (`senior_interest_rate`) | Already in `Project.senior_interest_rate` |
| Senior commitment amount | Project input | yes (`senior_amount_keur`) | Already in `Project.senior_amount_keur` |
| Senior drawdown profile | Construction bridge offline | partial (`spending_profile`) | Need monthly granularity in bridge |
| Construction period dates | Project input (COD, FC) | yes (`commercial_operation_date`) | Already in `Project.commercial_operation_date` |
| Day-count convention | Convention (30/360 or actual/365) | not explicit | **NEW**: need to add to `Project` |
| Capitalization flag | Project input | not present | **NEW**: opt-in flag, default False |
| Senior opening balance at COD | Computed | frozen manual | **NEW**: computed from draws + IDC |

### 3.1 New inputs (if Option A is implemented)

- `senior_idc_day_count_convention` — string, default "30/360"
- `senior_idc_capitalize` — bool, default False

These would be added to `Project` (in `domain/inputs.py`) and
serialized through the persistence layer.

---

## 4. Excel parity evidence needed

To validate Option A against the Excel bridge, the following
evidence is required:

### 4.1 Per-period Excel evidence

- **Monthly senior draws** (TUHO and Oborovo): from the
  `phase9_tuho_full_line_item_period_bridge.csv` and the
  equivalent Oborovo bridge CSV.
- **Monthly senior IDC** (TUHO and Oborovo): from the same
  bridge CSVs (`excel_senior_interest_keur` column).
- **Senior opening balance at COD** (TUHO and Oborovo): from the
  bridge snapshot at the first operating period.

### 4.2 Required parity gates

- Per-period senior IDC within **±1%** of Excel.
- Senior opening balance at COD within **±1%** of Excel.
- Cumulative senior IDC over construction period within
  **±1%** of Excel.
- DSCR parity preserved (i.e. the change in senior IDC does not
  break existing DSCR parity gates).

### 4.3 Test artefacts

- **Snapshot test**: capture the post-A construction bridge
  output for both TUHO and Oborovo; compare against Excel
  bridge CSVs. All snapshot tests use the **tolerance** bounds
  listed above.
- **Regression test**: re-run all 88 pre-existing parity tests
  and confirm no regression; expect R-PAR-2 family to close
  (10 tests) and ~78 to remain.
- **Edge cases**: zero drawdown period, partial-month draws,
  capitalization on vs off, day-count convention variations.

---

## 5. Tests required before any promotion PR

The following test classes are required:

### 5.1 Base-rate row model unit tests

- `TestSeniorIDCBaseRateAccrual`
  - `test_base_rate_accrual_constant_balance`
  - `test_base_rate_accrual_increasing_balance`
  - `test_base_rate_accrual_zero_balance`
  - `test_base_rate_accrual_partial_month`
  - `test_base_rate_accrual_30_360_convention`
  - `test_base_rate_accrual_actual_365_convention`
  - `test_base_rate_accrual_capitalize_false`
  - `test_base_rate_accrual_capitalize_true`

### 5.2 Bridge parity tests

- `TestSeniorIDCParityVsExcel`
  - `test_tuho_monthly_senior_idc_within_1pct`
  - `test_tuho_cumulative_senior_idc_within_1pct`
  - `test_tuho_senior_opening_balance_within_1pct`
  - `test_oborovo_monthly_senior_idc_within_1pct` (TUHO-first rule)
  - `test_oborovo_cumulative_senior_idc_within_1pct`
  - `test_oborovo_senior_opening_balance_within_1pct`

### 5.3 Regression tests

- `TestNoParityRegressionFromOptionA`
  - `test_all_parity_tests_still_pass_or_close` (≤78 expected
    remaining, vs current 88)
  - `test_rpar2_family_closes` (10 tests in R-PAR-2 family
    should now pass)
  - `test_r99_chain_unchanged` (R99 still depends on its own
    chain; not auto-closed by A)
  - `test_dscr_parity_preserved`

### 5.4 Guard tests

- `TestC9GuardWithROptionAResolved`
  - `test_senior_idc_keur_promotable_when_rpar2_resolved_true`
  - `test_senior_opening_balance_keur_promotable_when_rpar2_resolved_true`
  - `test_other_fields_unaffected_by_rpar2_resolution`

### 5.5 Oborovo-first rule guard

- `TestOborovoAfterTUHO`
  - `test_oborovo_not_promoted_before_tuho`
  - `test_tuho_first_in_senior_idc_promotion_chain`

### 5.6 Test count estimate

- New unit tests: ~12
- New bridge parity tests: ~6
- Regression tests: ~5
- Guard tests: ~3
- Oborovo guard tests: ~2
- **Total: ~28 new tests** for Option A implementation.

---

## 6. No-go criteria

Option A implementation PRs are blocked if any of the following
are true:

1. **R-PAR-2 decision is B or C, not A** — no Option A
   implementation PRs may open until Option A is explicitly
   ratified by governance.
2. **`rpar2_resolved` flag is not set in `rpar2_decision.json`**
   — there must be a recorded governance decision before any
   implementation PR.
3. **Senior lender has not signed off** on the base-rate
   method.
4. **Audit team has not signed off** on the parity plan.
5. **TUHO parity is not green** — Option A must first make TUHO
   parity green before Oborovo (hard rule: Oborovo before TUHO).
6. **C10 implementation is not in flight** — Option A and C10
   are sequential, not parallel; C10 (with B-style rpar2_resolved)
   is the pilot-track path; Option A is the enterprise-track path.
7. **No `spending_profile` extension** for monthly drawdown
   granularity — the bridge needs monthly granularity; if the
   runtime cannot provide it, Option A cannot be implemented.
8. **No governance decision recorded** — there must be a
   signed decision memo, not just a PR.

---

## 7. Implementation order (if Option A is ratified)

1. **Design lock-in** — this document is reviewed and merged
   (DRAFT → ready → merge).
2. **C11+ Construction Bridge Refactor** — extend
   `domain/construction/` to expose monthly draws and base-rate
   accrual.
3. **Senior IDC base-rate module** — new
   `app/services/senior_idc_base_rate.py` with the row model
   from §2.
4. **C7 POLICY_TABLE update** — change `senior_idc_keur` and
   `senior_opening_balance_keur` to `replaced`, remove
   `c1_blocker_reference`.
5. **C9 guard update** — change `rpar2_resolved` default for
   senior IDC fields to `True` (post-ratification).
6. **Test suite** — add the ~28 tests from §5.
7. **TUHO parity validation** — run parity tests; confirm R-PAR-2
   family closes; confirm no regression.
8. **Oborovo parity validation** — same, after TUHO.
9. **C10 readiness update** — add senior IDC fields to allowed
   list.
10. **Promotion PR** — first C10 promotion PR with senior IDC
    fields included.

Estimated timeline: **L (multi-quarter)**, with the critical path
being the bridge refactor + parity validation.

---

## 8. What this document does NOT do

- No implementation
- No model change
- No formula change
- No runtime change
- No promotion
- No flag flip
- No governance decision (the board picks)
- No commitment to implement A in any particular sprint
- No test impact (this is a design-only PR)

The machine-readable companion is
`reports/phase_rpar2_option_a_technical_design.json`.

---

## 9. Test footprint

This PR introduces shape-only characterization tests that assert
the document exists, has the design sections (base-rate row,
inputs, parity evidence, tests, no-go, implementation order),
and lists ≥ 6 no-go criteria.
