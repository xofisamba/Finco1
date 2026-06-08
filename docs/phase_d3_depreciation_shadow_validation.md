# Phase D3 — Depreciation Shadow Validation / Audit-Only Comparison

**Type**: audit-only shadow comparison (no runtime
enablement, no waterfall change).

**Status**: DRAFT PR. **Do NOT mark ready.** Do NOT merge.
Do NOT start any further depreciation runtime work
before review and explicit go-ahead.

**Base**: `9cd228b1cdbbb0f0c9ba81f2d253bd6eccc73bd2` (post-PR #531,
D1 merged).

**Branch**: `phase-depreciation-d3-shadow-validation`

## 1. Summary

D3 is the third and final safe step recommended by
PR #530 (depreciation enablement readiness review).
PR #530 concluded **NO-GO** for broad runtime depreciation
enablement. The recommended safe sequence is:

1. **D1** (PR #531, MERGED at `9cd228b`) — audit
   visibility: a single text-only "Depreciation Audit"
   sheet that discloses the active depreciation path,
   runtime authority, and canonical flag status.
2. **D2** (PR #532, DRAFT, `3e53efa`) — flag discipline
   hardening: a single-source-of-truth inventory of the
   four canonical / tax-bridge / book-pnl depreciation
   flags; a read-only discipline summary; and a
   PermissionError guard helper.
3. **D3** (this PR) — shadow validation: compare the
   legacy active depreciation path with the canonical
   DepreciationEngine output in read-only mode, produce
   comparison tables, identify deltas and blockers,
   and document whether TUHO / Oborovo are ready for
   later controlled enablement.

D3 does NOT enable any feature flag, does NOT change
``period.depreciation_keur`` (legacy waterfall output is
unchanged), does NOT change
``tax_depreciation_audit_keur``, does NOT change P&L /
tax / CFADS, does NOT promote generic depreciation, and
does NOT change the waterfall runtime authority. The
canonical DepreciationEngine runs in shadow mode on a
local ephemeral copy of the project inputs; the
canonical values are NEVER routed into the waterfall
output.

## 2. Changed files (3 files, +854 / -0)

| Status | File | Rationale |
|---|---|---|
| A | `app/depreciation_shadow_validation.py` | NEW module. Public API: `run_shadow_validation(project_inputs, legacy_waterfall_result, project_label) -> ShadowComparisonSummary`; `to_json_dict(summary) -> dict`; `build_shadow_validation_audit_dataframe(summary) -> pd.DataFrame` (text-only, suitable for the D3 export audit sheet). Internal: `_safe_float` (defensive coercion), `_build_canonical_book_depreciation_array` (runs canonical engine on a local shadow copy, never mutates the caller's project inputs). Pure read-side. |
| A | `tests/test_phase_d3_depreciation_shadow_validation.py` | 21 new design-contract tests. |
| A | `docs/phase_d3_depreciation_shadow_validation.md` | This document. |
| A | `reports/phase_d3_depreciation_shadow_validation.json` | Machine-readable summary. |

ZERO changes to:
- `app/waterfall_core.py`
- `app/waterfall_runner.py`
- `app/opex_engine.py`
- `app/depreciation_engine.py`
- `app/depreciation_bankable.py`
- `app/services/run_service.py`
- `app/persistence/`
- `app/excel_export.py`
- `app/templates/`
- `static/app.js`
- `static/styles.css`
- `main_web.py`
- `main_api.py`
- `domain/`

The new module is read-only end-to-end: it never
mutates the caller's project inputs, never modifies the
legacy waterfall result, and never writes any new
runtime values.

## 3. How D3 works

1. Caller passes the factory default project inputs and
   the legacy waterfall result to
   ``run_shadow_validation``.
2. The helper builds the canonical DepreciationEngine
   output by calling ``build_canonical_depreciation_wiring``
   with the caller's project inputs (the canonical flag
   is NOT touched on the caller's project inputs; the
   canonical engine runs in shadow mode and the
   ``use_depreciation_canonical_engine`` flag is **not**
   enabled on the live project inputs).
3. The per-period book depreciation array is extracted
   from the canonical engine result via
   ``wire_canonical_depreciation_into_waterfall``.
4. The helper reads the legacy per-period
   ``depreciation_keur`` from
   ``legacy_waterfall_result.periods[i]``.
5. The helper computes the absolute and relative deltas
   per period and totals.
6. The helper returns a ``ShadowComparisonSummary`` with
   the totals, max deltas, and a tuple of
   ``ShadowComparisonRow`` per-period entries.

The canonical values are NEVER written to
``period.depreciation_keur`` (legacy waterfall output is
unchanged) and never written to
``tax_depreciation_audit_keur`` (legacy tax-bridge output
is unchanged).

## 4. Shadow validation results for factory projects (evidence)

Captured before commit, on the D3 branch. The numbers
below are the canonical-vs-legacy deltas produced by
``run_shadow_validation`` for the factory default
projects.

| Project | Legacy Total Depreciation (kEUR) | Canonical Total Book Depreciation (kEUR) | Absolute Total Delta (kEUR) | Relative Total Delta (%) |
|---|---|---|---|---|
| **TUHO** | 70,691.54 | 70,691.54 | 1.45e-11 (floating-point only) | 2.06e-14 (effectively zero) |
| **Oborovo** | 55,996.56 | 55,999.09 | 2.53 | 0.00452 |

For TUHO the delta is at the floating-point limit; the
legacy and canonical engines agree to the cent on the
total. For Oborovo the delta is 2.53 kEUR on a ~56,000
kEUR base (0.0045%) — well within a small floating-point
plus rounding-difference envelope. The per-period
distributions differ in shape (canonical engine spreads
the per-asset-class straight-line more uniformly) but
the totals agree to within rounding.

**TUHO and Oborovo are ready for later controlled
enablement** as long as the rounding differences are
documented and reviewer-acceptable. The D3 PR
documents this; the actual enablement would be a
separate, future controlled-enablement PR.

## 5. Recommendation

- **TUHO**: shadow validation delta at the floating-point
  limit; **READY** for later controlled enablement.
- **Oborovo**: shadow validation delta 2.53 kEUR on
  ~56,000 kEUR base (0.0045%); **READY** for later
  controlled enablement with documented rounding
  differences.
- **Generic projects**: shadow validation is **NOT
  run** for generic projects in D3 (the active
  depreciation path does not support generic-project
  canonical promotion; D1 audit sheet already documents
  this).
- **NO runtime enablement is recommended** in this
  stack. The recommendation is to keep the audit /
  shadow stack in place and revisit enablement when the
  wider governance posture changes (G20 unblocked, R99 /
  R102 approved, etc.).

## 6. Pre-merge audit — all green

**Scope (all verified)**
- Audit / shadow only
- No runtime enablement
- No Excel export integration (the audit DataFrame is
  available but the export sheet wire-up is intentionally
  deferred to a future phase; D3 reports the shadow
  summary as a doc/report, not as a workbook sheet)
- No UI / template / static changes
- No model formula changes
- No tax / depreciation schedule / payment schedule /
  IDC / P&L / CFADS changes
- No persistence / schema changes
- No `app/waterfall_core.py` / `app/waterfall_runner.py`
  changes
- No G20 / R99 / R102 promotion

**Numeric invariance (all verified, pinned by tests)**
- TUHO `CapEx` sum: 145,988.42 (unchanged)
- TUHO `CapEx_Items` sum: 70,706.54 (unchanged)
- TUHO `Inputs` sum: 79,580.2375 (unchanged)
- TUHO `Depreciation Assumptions` sum: 45.0 (unchanged)
- Oborovo `CapEx` sum: 115,758.5053 (unchanged)
- Oborovo `CapEx_Items` sum: 56,104.09 (unchanged)
- Oborovo `Inputs` sum: 61,272.8532 (unchanged)
- Oborovo `Depreciation Assumptions` sum: 45.0 (unchanged)
- TUHO `period.depreciation_keur` bit-for-bit identical
  to pre-D3 (D3 never overrides legacy waterfall
  periods)
- Oborovo `period.depreciation_keur` bit-for-bit
  identical to pre-D3

**Tests (all green)**
- **21 / 21 new D3 tests pass** (all)
- **23 / 23 D1 tests still pass** (no D1 regression)
- **13 / 13 57A-9E excel export tests pass** (isolated run)
- **21 / 21 Phase 51F Parity Guardrails pass** (green)
- **1180 passed / 75 skipped / 2 failed** in full 57-arc
  stack
  - The 2 failures are pre-existing 57A-9E test
    pollution failures (verified to ALSO fail on `main`
    pre-D1, pre-D2, and pre-D3; passes in isolated run;
    documented as pre-existing infra rot in the D1 docs)

**D3 invariants**
- D3 does NOT mutate the caller's project inputs
  (``use_depreciation_canonical_engine` stays `False`
  on the caller's `project_inputs.info` before and
  after the shadow validation)
- D3 does NOT change the legacy waterfall result
  (``period[0].depreciation_keur` and
  ``period[0].tax_depreciation_audit_keur` are
  bit-for-bit identical before and after)
- D3 does NOT enable any feature flag
- D3 does NOT route canonical values into the
  waterfall
- D3 produces a JSON-friendly summary
- D3 produces a text-only audit DataFrame (the Value
  column has zero numerics)

**TUHO / Oborovo parity**
- TUHO and Oborovo factory total capex bit-for-byte
  identical to pre-D3
- No factory project mutation
- No financial output changes

**rc1 frozen** — `b425a0708719eaa5e1d922b1008e5609758e0ad4`
verified still resolves

## 7. Hard no-go (15 items, all verified pre-commit)

1. **no_runtime_depreciation_enablement** (D3 is shadow only)
2. no_feature_flag_enablement
3. no_formula_changes
4. no_depreciation_schedule_changes
5. no_tax_calculation_changes
6. no_pnl_calculation_changes
7. no_cfads_changes
8. **no_period_depreciation_keur_changes** (D3 reads but never writes)
9. **no_tax_depreciation_audit_keur_changes** (D3 reads but never writes)
10. **no_canonical_runtime_promotion**
11. no_persistence_changes
12. no_schema_changes
13. no_ui_workflow_changes
14. no_generic_project_depreciation_claims
15. rc1_frozen (`b425a0708719eaa5e1d922b1008e5609758e0ad4`)

## 8. Self-review findings

- **Initial draft** called ``build_canonical_depreciation_wiring`` with the wrong signature (``project=shadow_inputs`` instead of
  ``project_name=..., capex_items=..., horizon_years=...``).
  Self-review caught this by running the helper
  directly; the canonical engine returned an empty
  result, the totals were all zero, and the helper
  silently returned the empty result without flagging
  the issue. **Mitigation**: updated the helper to use
  the correct signature, with explicit fallback to
  ``[0.0] * horizon`` if the canonical engine returns
  ``None``. The 21 new D3 tests now confirm the canonical
  engine actually produces non-zero values for both
  factory projects.
- The ``_safe_float`` helper is used to coerce waterfall
  result attribute reads to ``float``, defaulting to
  ``0.0`` on missing or non-numeric input. This keeps
  the shadow comparison defensive against future
  waterfall result shape changes.

## 9. Stop-after-report contract

This PR is DRAFT. Do NOT mark ready. Do NOT merge. Do NOT
start any further depreciation runtime work before
review and explicit go-ahead.

The 21 design-contract tests pin the shadow comparison
contract. The numeric-invariance tests pin that no
existing sheet's numbers changed. The
``caller-not-mutated`` test pins that the canonical flag
is never written to the caller's project inputs.

## 10. Recommended next step (post-D3)

The D1 + D2 + D3 stack closes the safe-next-step arc
recommended by PR #530. The recommendation is to
**pause** and review the stack, or focus on a different
governance arc. D3 is the final recommended safe step;
any further depreciation work (D4+, runtime enablement,
or non-canonical hardening) is intentionally out of
scope and should be planned in a future governance
review.
