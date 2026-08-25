# PR-F1 Canonical Period Axis Freeze

## Authority decision

`ProjectInfo` is the persisted timeline authority. Its explicit `cod_date` is
carried into `financial_engine.inputs.CalendarInput`. Runtime validates it
against `financial_close + construction_months` and fails with
`PERIOD_AXIS_COD_MISMATCH` on disagreement. An old payload without the required
`ProjectInfo.cod_date` already fails deserialization; it cannot silently create
a different axis.

`finco_core.engine.period_engine.PeriodEngine` is the only axis producer.
`domain.period_engine` remains a compatibility re-export and contains no axis
logic. The engine creates one immutable tuple and validates it before exposing
it. Semiannual integer horizons contain exactly `horizon_years * 2` operating
periods. The final horizon date is the final scheduled semiannual boundary,
not literal `COD + horizon_years` followed by a clipped residual period.

Construction runs continuously from financial close to the operating boundary.
The explicit Oborovo convention preserves one source construction column. The
serialized default convention emits meaningful six-month segments, folds a
near-boundary remainder shorter than seven days into the preceding segment,
and never emits a zero-day placeholder. A real first operating stub remains
possible. PPA flags use period starts on this same axis and the existing typed
PPA end-date convention.

## Production authority inventory

| Surface | Axis behavior after PR-F1 |
|---|---|
| `finco_core/engine/period_engine.py` | Sole producer; immutable tuple; COD, count, continuity and phase invariants |
| `domain/period_engine.py` | Re-export only |
| `ProjectInfo` / serialization / cache | Explicit COD, frequency and convention persisted and cached; mismatch fails closed |
| project-input adapter | Carries explicit COD and typed convention into `CalendarInput` |
| operating / revenue / OPEX | Receive the same `PeriodEngine`; returned keys must exactly equal canonical order |
| depreciation | Built from the canonical tuple; book and tax schedules must exactly equal its keys |
| tax / CFADS | Existing count, duplicate and exact-order checks retained |
| Senior debt / sizing | Explicit operating debt-active subset; full-axis result maps absent debt periods to zero |
| SHL / post-Senior cash | Full canonical tuple and strict equal-length/index mapping |
| DSRA | Existing equal-length, duplicate, positive-duration and chronological guards retained |
| Distribution Account / shareholder waterfall | Strict post-Senior, DSCR, DSRF and SHL vector maps |
| sponsor returns | Strict SHL and post-Senior vector maps |
| diagnostics / audit | Base-performance reconciliation now uses strict maps, not `dict(zip(...))` |
| presentation / exports / audit | Clean presentation uses strict vector maps and rejects duplicate waterfall dates; exports consume immutable result/audit objects with no independent axis construction |

All production-side direct `PeriodEngine` builders (`app.ui_runner`, portfolio,
sensitivity and production-waterfall seam) now carry the typed frequency, COD
and period convention. The UI runner is locked to the same complete tuple as
clean orchestration for TUHO and Oborovo.

When book or tax depreciation is not configured, the depreciation boundary now
returns an explicit zero-valued schedule on every canonical period rather than
an empty mapping. Missing configured schedule keys still fail closed.

Independent absolute-index assumptions remain prohibited. Contractual Senior
and SHL indices are resolved from the produced operation subset. Tests that
formerly assumed two construction positions now derive the expected absolute
index from the first operating position. The PR-7 TUHO baseline diagnostic
likewise derives repayment start and maturity from the first and last canonical
operating indices rather than the removed `2..61` grid.

## Exact source anchors

| Project | Before | After |
|---|---|---|
| TUHO | 2 construction + 61 operation; zero-day construction placeholder; final one-day operation ending 2060-01-01 | 1 construction + 60 operation; first operation 2030-01-01 to 2030-06-30, 181 days; final 2059-12-31 |
| Oborovo | 1 construction + 60 operation; final 2060-06-30 | Unchanged; first operation 2030-06-30 to 2030-12-31, 184 days; final 2060-06-30 |
| Generic Solar | 2 construction + 41 operation; one-day tail ending 2051-01-01 | 2 construction + 40 operation; final 2050-12-31 |
| Generic Wind | 2 construction + 51 operation; one-day tail ending 2056-07-01 | 3 meaningful construction + 50 operation; final 2056-06-30 |

The full TUHO and Oborovo vectors are locked for indices, starts, ends, day
counts, phase flags, operating indices, operating years, half-year labels and
PPA flags. The generic matrix covers Solar, Wind, BESS, Solar+BESS, Wind+BESS,
6/12/18-month construction, leap years, Jan 1, Jun 30, Jul 1, Dec 31 and a
near-boundary COD.

## Fail-closed attacks

The axis rejects empty, duplicate, non-contiguous, out-of-order, zero/negative
duration, overlapping/gapped, invalid phase and wrong operating-count inputs.
Parallel vectors reject unequal lengths, duplicate keys and out-of-order keys
before dictionary construction. Consumer schedules reject missing, extra,
shifted and reordered keys. Fixed-point delta comparison rejects unequal vector
lengths instead of truncating with `min(len(...))`.

## Base-versus-head financial bridge

All values are kEUR except counts/dates. No formulas, tax policy, debt policy,
SHL policy, project identity routing or source-output replay changed.

| Metric | Solar delta | Wind delta | Oborovo delta |
|---|---:|---:|---:|
| operating periods | -1 | -1 | 0 |
| final date | 2051-01-01 -> 2050-12-31 | 2056-07-01 -> 2056-06-30 | unchanged |
| revenue | -16.518045387 | -31.697201897 | 0 |
| OPEX | 0 | 0 | 0 |
| EBITDA | -16.518045387 | -31.697201897 | 0 |
| depreciation | 0 | 0 | 0 |
| Senior interest / principal / service | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| SHL gross / closing | 0 / 0 | 0 / 0 | 0 / 0 |
| cash tax | -4.129511347 | -7.924300474 | 0 |
| Base CFADS | -12.388534040 | -23.772901423 | 0 |
| Bank CFADS | -11.562631771 | -21.395611281 | 0 |
| Senior debt size | 0 | 0 | 0 |
| legal equity distributions | 0 | 0 | 0 |

These Solar/Wind deltas are exactly the economics formerly booked into the
removed one-day terminal periods and their tax/CFADS consequences. Existing
PPA and day-count policy is otherwise unchanged.

For the explicit TUHO clean DSCR test contract, removal of the terminal period
and the zero-day construction placeholder changes the axis from 63 total / 61
operating / 2060-01-01 to 61 total / 60 operating / 2059-12-31. Revenue changes
by -56.124426017, EBITDA by -56.124426017, cash tax by +66.959170873, Base
CFADS by -123.083596891, Bank CFADS by -106.861295043, Senior debt size by
-402.111244838, Senior interest by -790.459648900 and Senior service by
-1,192.570893738. This is the direct full-horizon consequence of removing the
phantom period while applying the same formulas to the canonical axis. TUHO's
factory production clean-tax path remains explicitly gated, so no unsupported
G2C/returns claim is made.

The legacy waterfall exact-output locks also moved onto this same axis. Their
base -> head totals are: Oborovo tax 8,489.215657 -> 8,490.320140,
distribution 63,997.380136 -> 64,006.489082 and Senior service 63,192.172875
-> 63,191.174225; TUHO tax 37,004.372718 -> 36,994.270322 and distribution
165,479.319576 -> 165,423.195150; Solar tax 9,432.701033 -> 9,428.571521 and
distribution 19,858.410252 -> 19,841.892207; Wind tax 31,098.189755 ->
31,090.265455 and distribution 72,995.889074 -> 72,964.191873. Oborovo's
count and dates are unchanged; its delta is the removal of the UI runner's
implicit default convention in favor of the factory's already typed
single-construction-column source convention. The other three changes follow
the phantom-period bridge above. The exact locks remain exact and their
tolerances were not widened.

KUPI's two annual source construction columns are explicitly placed at the
start of their corresponding years on its four-segment canonical semiannual
construction axis. A construction Uses vector whose length differs from that
axis now fails closed instead of truncating through `zip`.

## Correction B additions (PR-F1 Correction B)

### TASK 1: Mandatory expected-axis enforcement at all production boundaries

Three independently-derived axis contracts:

1. **Full model axis** — `tuple(p.period_index for p in canonical_periods)` from
   `PeriodEngine.periods()`.  Used for CFADS, tax, all full-model vectors.
   Derived at `financial_engine/orchestrator.py:run_senior_debt_model` as
   `full_axis = tuple(p.period_index for p in phase2b_result.periods)`.

2. **Operating axis** — `tuple(p.period_index for p in canonical_periods if p.is_operation)`.
   Used for bank/debt-sizing operating schedules.

3. **Senior debt-active axis** — derived from the operating axis using typed
   `SeniorDebtPolicy.repayment_start_period_index` and `maturity_period_index`:
   `senior_axis = tuple(p.period_index for p in debt_periods)` where
   `debt_periods = tuple(p for p in bank_phase2a_result.periods if p.is_operation
   and debt_start <= p.period_index <= debt_end)`.
   This is NOT derived from the solver's returned `period_indices`.

Updated production consumers with `expected_indices` enforcement:

| Consumer | Axis | File:line (approx) |
|---|---|---|
| `_assemble_post_senior_cash_schedules` — CFADS | full_axis | orchestrator.py |
| `_assemble_post_senior_cash_schedules` — Senior DS | senior_axis | orchestrator.py |
| `_build_debt_sizing_schedules_from_bank` — Senior DS | senior_axis | orchestrator.py |
| `_build_debt_sizing_schedules_from_bank` — solver DSCR | senior_axis | orchestrator.py |
| `_build_result_senior_debt_schedules` — Senior DS | senior_axis | orchestrator.py |
| `_build_result_senior_debt_schedules` — Base CFADS | full_axis | orchestrator.py |
| `run_senior_debt_model` — final senior interest | senior_axis | orchestrator.py |
| `run_senior_debt_model` — result service | senior_axis | orchestrator.py |
| `run_senior_debt_model` — result base CFADS | full_axis | orchestrator.py |
| `_run_senior_debt_model_with_shl` — Senior interest | senior_axis_shl | orchestrator.py |
| `_run_senior_debt_model_with_shl` — SHL gross interest (per iteration) | full_axis_shl | orchestrator.py |
| `_run_senior_debt_model_with_shl` — final SHL interest | full_axis_shl | orchestrator.py |
| `_run_senior_debt_model_with_shl` — final Senior interest | senior_axis_shl | orchestrator.py |

Rule: `.get(index, 0.0)` for zeros outside the Senior debt tenor is permitted only after
the exact Senior subset has been accepted by `_strict_period_map(expected_indices=senior_axis)`.

### TASK 2: Day-count validation in `validate_canonical_period_axis()`

COD-inclusive +1 rule: `days_in_period = calendar_days + 1` is permitted ONLY for the
first operating period (`operating_period_index == 0`) when `start_date.day == 1`.
Construction periods and all other operating periods must be exactly `calendar_days`.

day_fraction reconciliation: every period must satisfy
`day_fraction == days_in_period / approved_denominator` where
`approved_denominator = 366.0 if period.is_leap_year else 365.0`.

Attack matrix:
- Construction period with +1 day: raises `PERIOD_AXIS_DAYS_IN_PERIOD_MISMATCH`
- Non-first operating period with +1: raises `PERIOD_AXIS_DAYS_IN_PERIOD_MISMATCH`
- Wrong day_fraction (e.g. days/360 instead of days/365): raises `PERIOD_AXIS_DAY_FRACTION_RECONCILIATION_FAILED`
- Wrong leap flag (fraction correct for original denom, flag flipped): raises `PERIOD_AXIS_DAY_FRACTION_RECONCILIATION_FAILED`
- Valid COD-inclusive +1 (first operating, start.day==1): PASSES

### TASK 3: Real production-boundary attacks

Attack class `TestRealProductionBoundaryAttacks` in
`tests/test_prefreeze_prf1_canonical_period_axis.py` proves through the real
`run_senior_debt_model` production consumer using monkeypatch injection:

| Attack | Test | Error code |
|---|---|---|
| rb1 — shifted same-shape Senior interest | test_rb1_* | AXIS_PERIOD_MISSING |
| rb2 — missing Senior DS period | test_rb2_* | AXIS_PERIOD_MISSING |
| rb3 — extra Senior period | test_rb3_* | AXIS_PERIOD_EXTRA |
| rb4 — reordered Senior period | test_rb4_* | AXIS_PERIOD_SHIFTED |
| rb5 — duplicate raw Senior period | test_rb5_* | AXIS_PERIOD_DUPLICATE |
| rb6 — shifted full-axis CFADS | test_rb6_* | AXIS_PERIOD_MISSING |
| rb9 — no partial result returned | test_rb9_* | (no partial result) |

### TASK 4: Error-code precedence

Documented stable precedence (implemented in `map_period_vector`):

1. `AXIS_PERIOD_DUPLICATE` — duplicate raw indices, checked before any axis comparison
2. `AXIS_LENGTH_MISMATCH` — length differs with both missing and extra indices
3. `AXIS_PERIOD_MISSING` — expected index absent from supplied (includes shifted ranges)
4. `AXIS_PERIOD_EXTRA` — supplied index not in expected (same-length, superset)
5. `AXIS_PERIOD_SHIFTED` — same set, same length, different order

"Shifted range" (different offset) raises `AXIS_PERIOD_MISSING` (not `AXIS_PERIOD_SHIFTED`)
because the index sets differ.  `AXIS_PERIOD_SHIFTED` fires only when `set(supplied) == set(expected)`
but `tuple(supplied) != tuple(expected)`.

## Governance

No project name/code dispatch, workbook runtime read, source-vector replay,
target fitting, approved/expected delta, balancing plug, terminal top-up,
virtual debt, post-engine stub deletion or tolerance-based economic capacity
was introduced. `financial_engine/tax/engine.py` is untouched.

## Classification

`EXACT_MEMBERSHIP_CLOSED` is NOT claimed.  `FREEZE_COMPLETE` is NOT claimed.
All production-boundary attacks are implemented and green locally.  Independent
exact-head CI review is required before either classification is applied.

## Local verification (Correction B)

- 75 PRF1 canonical axis tests passed (including 7 new day-count attacks, 7 new
  production-boundary attacks, COD-inclusive pass case).
- 631 tests across PRF1 + Phase 2C Senior + c3b3d2b3/b4/b6 + SHL + PRF6/PRF7 passed.
- `git diff --check` clean (no whitespace errors).

## Correction C additions (PR-F1 Correction C)

### TASK 1: Downstream exact-axis enforcement in all consumer files

Five additional consumer files now pass `expected_indices` to every
`map_period_vector()` call, using independently derived axes:

| File | Axes added |
|---|---|
| `financial_engine/shareholder_waterfall/model.py` | full_axis, op_axis, senior_axis, shl_axis (= full_axis) |
| `financial_engine/sponsor_returns/model.py` | full_axis (SHL + post_senior_cash) |
| `financial_engine/adapters/shl_cash_seam.py` | full_axis (fast path × 3; legacy path × 1) |
| `financial_engine/diagnostics/base_performance_reconciliation.py` | full_axis, senior_axis, shl_axis, op_axis, tax_axis |
| `app/services/clean_presentation_adapter.py` | full_axis, senior_axis |

Rule: every consumer independently derives its axis from `model_result.periods`
— it never reuses an axis from a sibling call, and never uses the schedule's
own `period_indices` to validate that same schedule (self-validation is
prohibited).

### TASK 2: Bank-only axis authority in `_build_debt_sizing_schedules_from_bank()`

`financial_engine/orchestrator.py:_build_debt_sizing_schedules_from_bank()` now:

1. Derives `bank_full_axis` independently from `bank_phase2a_result.periods`
2. Reconciles Base vs Bank period metadata when `base_periods` is supplied:
   - Mismatched period count, start/end dates, or is_construction flag → `BASE_BANK_AXIS_MISMATCH`
3. Validates bank tax results against `bank_full_axis`:
   - Duplicate tax period index → `BANK_AXIS_PERIOD_DUPLICATE`
   - Missing tax period → `BANK_AXIS_PERIOD_MISSING`
   - Extra tax period (not in bank_full_axis) → `BANK_AXIS_PERIOD_EXTRA`
4. Validates bank CFADS results against `bank_full_axis`:
   - Duplicate CFADS period index → `BANK_AXIS_PERIOD_DUPLICATE`
   - Missing CFADS period → `BANK_AXIS_PERIOD_MISSING`
   - Extra CFADS period → `BANK_AXIS_PERIOD_EXTRA`

Error code precedence: DUPLICATE > MISSING (raised on first missing, even when
extra also exist) > EXTRA > BASE_BANK_AXIS_MISMATCH.

### TASK 3: COD-inclusive +1 rule is externally authoritative

`validate_canonical_period_axis()` now accepts a `cod_date` parameter.
When supplied, the COD-inclusive +1 rule is permitted ONLY when:
  - `period.start_date == cod_date`  (not merely `start_date.day == 1`)
  - `cod_date.day == 1`

`PeriodEngine.__init__()` now passes `cod_date=self._cod` into the call,
making the engine's own COD the authoritative gate.  A period that starts on
the first of a month but does not match the engine's COD cannot claim the
COD-inclusive +1 exception.

### TASK 4: Correction C attack matrix

Attack class `TestBankAxisAttacks` (unit tests; direct calls to
`_build_debt_sizing_schedules_from_bank` with crafted mocks):

| ID | Description | Error code |
|---|---|---|
| bank1 | Shifted CFADS period_indices (+1) | BANK_AXIS_PERIOD_MISSING |
| bank2 | Missing tax period | BANK_AXIS_PERIOD_MISSING |
| bank3 | Extra CFADS period | BANK_AXIS_PERIOD_EXTRA |
| bank4 | Duplicate bank tax period | BANK_AXIS_PERIOD_DUPLICATE |
| bank5 | Duplicate bank CFADS period | BANK_AXIS_PERIOD_DUPLICATE |
| bank6 | Base/Bank period_start date mismatch | BASE_BANK_AXIS_MISMATCH |

Attack class `TestDownstreamConsumerAttacks` (E2E monkeypatch attacks):

| ID | Description | Error code |
|---|---|---|
| wf1 | Shifted SHL period_indices at waterfall consumption | AXIS_PERIOD_MISSING |
| sr1 | Shifted post_senior_cash period_indices at sponsor return | AXIS_PERIOD_MISSING |
| np | Extra SHL period — no partial waterfall result returned | AXIS_PERIOD_EXTRA |

COD attacks retained from Correction B: cod1, cod2, tuho_cod_inclusive_pass.

### TASK 5: Performative governance stubs removed

`test_correction_b_classification_earned_after_independent_ci_review()` (which
contained only `assert True`) was replaced by
`test_correction_c_classification_status()` which asserts the full attack count:
`assert len(attacks_implemented) == 11`.

### Classification (Correction C)

`EXACT_MEMBERSHIP_CLOSED` and `FREEZE_COMPLETE` are NOT claimed.
All 88 PRF1 tests pass locally.  Independent CI review is required before
either classification is applied.

## Local verification (Correction C)

- 88 PRF1 canonical axis tests passed (88 in test_prefreeze_prf1_canonical_period_axis.py).
- 325 tests passed across PRF1 + shareholder waterfall + sponsor returns + PR6/PR7/DSRF suites.
- `git diff --check` clean (no whitespace errors).

## Correction G additions (PR-F1 Correction G)

### TASK 1: Fail-closed Senior axis — removal of all fail-open fallbacks

Three downstream Senior consumers previously used `expected_indices=None` (fail-open)
when `axis_contract` was absent.  All three now fail closed with the deterministic
error code `CANONICAL_AXIS_CONTRACT_MISSING`.

| File | Change |
|---|---|
| `app/services/clean_presentation_adapter.py` | Removed ternary `None` fallback for `_senior_expected`; raises if Senior is active without contract |
| `financial_engine/diagnostics/base_performance_reconciliation.py` | Removed `_senior_axis=None` fallback in `_runtime_maps()`; raises if Senior is active without contract |
| `financial_engine/shareholder_waterfall/model.py` | Removed broad `except Exception: expected_senior_axis = None` swallow; raises unconditionally if contract absent |

`CanonicalAxisContract` is the runtime immutable authority for all axis
derivation.  Its three fields are:

- `full_axis` — `tuple(p.period_index for p in canonical_periods)` from
  `PeriodEngine.periods()`.
- `operating_axis` — `tuple(p.period_index for p in canonical_periods if p.is_operation)`.
- `senior_axis` — derived from typed `SeniorDebtPolicy` repayment bounds applied
  to the operating axis.  This is NOT derived from the solver's returned
  `period_indices`.

Active Senior consumers (where `senior_debt.period_indices` is non-empty) require
a `CanonicalAxisContract` attached to the result.  The contract is populated by
`run_senior_debt_model` (Phase 2C).  A missing contract on an active Senior
schedule is a hard error (`CANONICAL_AXIS_CONTRACT_MISSING`), not a silent
no-op.  Self-validation (using a schedule's own `period_indices` to validate
that same schedule) is prohibited.

### TASK 2: Real Bank E2E attack matrix (via `_build_debt_sizing_schedules_from_bank`)

Two new E2E tests in `TestBankE2EAttacksG` exercise the production Bank assembly
boundary through the real `run_senior_debt_model` orchestration path:

| ID | Description | Error code |
|---|---|---|
| g2_missing_bank_tax | Missing tax period injected before Bank assembly | BANK_AXIS_PERIOD_MISSING |
| g2_extra_bank_cfads | Extra CFADS period injected before Bank assembly | BANK_AXIS_PERIOD_EXTRA |

### TASK 3: Downstream Senior consumer attack matrix

Three new test classes exercise the fail-closed guards in each downstream consumer:

**`TestCleanPresentationAdapterDownstreamAttacksG`** — calls `map_period_vector`
with `axis_contract.senior_axis` as `expected_indices`:

| Attack | Error code |
|---|---|
| Shifted Senior period_indices | AXIS_PERIOD_MISSING |
| Missing Senior period | AXIS_PERIOD_MISSING |
| Reordered Senior period_indices | AXIS_PERIOD_SHIFTED |
| Duplicate Senior period | AXIS_PERIOD_DUPLICATE |

**`TestBaseReconciliationDownstreamAttacksG`** — calls `_runtime_maps()` with
corrupted `result.senior_debt.period_indices`:

| Attack | Error code |
|---|---|
| Shifted Senior period_indices | AXIS_PERIOD_MISSING |
| Missing Senior period | AXIS_PERIOD_MISSING |
| Reordered Senior period_indices | AXIS_PERIOD_SHIFTED |
| Duplicate Senior period | AXIS_PERIOD_DUPLICATE |

**`TestWaterfallDownstreamSeniorAttacksG`** — monkeypatches
`map_period_vector` inside the waterfall model:

| Attack | Error code |
|---|---|
| Missing Senior period | AXIS_PERIOD_MISSING |
| Reordered Senior period_indices | AXIS_PERIOD_SHIFTED |
| Duplicate Senior period | AXIS_PERIOD_DUPLICATE |

**`TestCanonicalAxisContractMissingFailClosed`** — verifies the three
fail-closed guards raise `CANONICAL_AXIS_CONTRACT_MISSING` when `axis_contract`
is absent on an active Senior schedule.

### Classification (Correction G)

`EXACT_MEMBERSHIP_CLOSED` and `FREEZE_COMPLETE` are NOT claimed.
All 116 PRF1 tests pass locally.  Independent CI review is required before
either classification is applied.

## Local verification (Correction G)

- 116 PRF1 canonical axis tests passed (116 in test_prefreeze_prf1_canonical_period_axis.py).
- All 4 required suites passed: PRF1, c3b3d2b6, c3b3d2b7, c3b3d2b8.
- `git diff --check` clean (no whitespace errors).
- `financial_engine/tax/engine.py` is untouched.
- Expected financial delta: ZERO.
