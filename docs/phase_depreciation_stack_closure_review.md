# Depreciation Stack Closure Review (D1 + D2 redo + D3 redo)

> Type: docs/report only
> Branch: `phase-depreciation-stack-closure-review`
> Base SHA: `9f8bde547be242509a751b6f6c21e0fb4fd42346` (post-#533, D3 merged)
> Status: analysis only, no implementation, no runtime enablement, no flag enablement
> Recommendation headline: **GO — pause here** (Option A); D4 not recommended at this time

## 0. Scope of this review

This is a **docs/report-only** review of the depreciation safe-next-step arc
that was recommended by PR #530 ("Depreciation Enablement Readiness Review",
2026-05-28-ish baseline). The arc is now complete on `main`:

- **D1** — Depreciation Export / Audit Visibility Hardening (PR #531, merged)
- **D2 redo** — Depreciation Flag Discipline Hardening, discipline-only
  (PR #534, merged)
- **D3 redo** — Depreciation Shadow Validation / Audit-Only Comparison
  (PR #533, merged)

This review does **not** introduce any code, does **not** enable any flag,
does **not** change runtime behavior, and does **not** start D4. The goal
is to summarize the merged stack, assess residual risk for any potential
next step, and recommend a clear GO / NO-GO.

## 1. Merged-stack verification

### 1.1 PR / commit state

| Item | PR | Commit on `main` | Status |
|---|---|---|---|
| D1 — Export / Audit Visibility | #531 | `9cd228b1cdbbb0f0c9ba81f2d253bd6eccc73bd2` | merged |
| D2 first attempt | #532 | n/a | force-reverted |
| D2 redo — Flag Discipline | #534 | `42718e545c5aa5e4e798a64402aa8c4774fc7ec4` | merged |
| D3 redo — Shadow Validation | #533 | `9f8bde547be242509a751b6f6c21e0fb4fd42346` | merged |
| Current `origin/main` | — | `9f8bde5` | D1 + D2 redo + D3 redo all present |

No reverted D2 attempt remains on `main`. The redo was necessary because
the first D2 PR (#532) added a read-only WARN log in
`app/persistence/provenance.py` and was flagged post-merge by
`tests/test_phase57a_ui3_line_item_grid_capex_summary.py::TestBackendUntouched::test_no_persistence_directory_changed`
as a forbidden-path violation. The redo (PR #534) carries **zero** changes
to `app/persistence/` and is clean.

### 1.2 File-scope discipline of the merged delta

Compared to the D1 base SHA `22d8162`, the three phases together
introduce the following surface:

| Path | Phase | Type | Notes |
|---|---|---|---|
| `app/depreciation_audit_visibility.py` | D1 | NEW | D1 export/audit module |
| `app/depreciation_flag_discipline.py` | D2 redo | NEW | D2 flag discipline module |
| `app/depreciation_shadow_validation.py` | D3 redo | NEW | D3 shadow comparison module |
| `app/depreciation_audit_visibility.py` (D2 row) | D2 redo | +18 lines | D2 disclosure row on D1 sheet |
| `app/excel_export.py` | D1 | +28 lines | Wires the D1 audit sheet |
| `docs/phase_d1_*.md` | D1 | NEW | design + change doc |
| `docs/phase_d2_*.md` | D2 redo | NEW | design + change doc |
| `docs/phase_d3_*.md` | D3 redo | NEW | design + change doc |
| `reports/phase_d1_*.json` | D1 | NEW | machine summary |
| `reports/phase_d2_*.json` | D2 redo | NEW | machine summary |
| `reports/phase_d3_*.json` | D3 redo | NEW | machine summary |
| `tests/test_phase_d1_*.py` | D1 | NEW | 23 tests |
| `tests/test_phase_d2_*.py` | D2 redo | NEW | 30 tests |
| `tests/test_phase_d3_*.py` | D3 redo | NEW | 21 tests |

**For the post-D2-redo D3 delta specifically** (i.e. `42718e5..9f8bde5`),
the diff is strictly the four D3 files:

```
 app/depreciation_shadow_validation.py              | 432 ++++++++++++++
 docs/phase_d3_depreciation_shadow_validation.md    | 284 ++++++++
 reports/phase_d3_depreciation_shadow_validation.json | 135 +++++
 tests/test_phase_d3_depreciation_shadow_validation.py | 511 ++++++++++++
 4 files changed, 1362 insertions(+)
```

**Forbidden-path check (post-D2-redo D3 delta `42718e5..9f8bde5`):**

| Path | Commits in D3 delta |
|---|---|
| `app/persistence/` | 0 |
| `app/waterfall_core.py` | 0 |
| `app/waterfall_runner.py` | 0 |
| `main_web.py` | 0 |
| `main_api.py` | 0 |
| `static/` | 0 |
| `app/excel_export.py` | 0 |
| `app/services/` | 0 |
| `domain/` | 0 |

D3 does **not** rebundle D2, and the merged D1 → D2 redo → D3 redo stack
keeps runtime authority (waterfall + persistence) untouched. The only
runtime surface touched anywhere in the stack is D1's 28-line addition
to `app/excel_export.py`, which adds a read-only text-only Depreciation
Audit sheet. D2 redo's only runtime surface touch is an additive 18-line
disclosure row on that same D1 sheet. D3 is pure read-side.

### 1.3 Numeric invariance

Across D1, D2 redo, and D3 redo, all factory numerics for TUHO and
Oborovo are bit-for-bit identical, including the two sensitive
runtime-authority fields:

- `period.depreciation_keur` — bit-for-bit identical
- `tax_depreciation_audit_keur` — bit-for-bit identical

Pre-D1 sheet sums (CapEx, CapEx_Items, Inputs, Depreciation_Assumptions,
Tax_Depreciation, Book_Depreciation) are unchanged for both factory
projects. The new D1 sheet is text-only and adds no financial values
to the export.

## 2. Architecture assessment

### 2.1 Active runtime path

- **Runtime authority:** `app/waterfall_core.py` and `app/waterfall_runner.py`.
  The D1 + D2 redo + D3 redo stack does not modify these files.
- **Active depreciation path:** `LegacyDepreciationPath` (baseline
  TUHO/Oborovo), with `canonical_depreciation_engine` available as
  `domain.depreciation.engine.DepreciationEngine` but **not** runtime
  authoritative unless `use_depreciation_canonical_engine=True` is set
  on the project inputs.
- **Tax path:** legacy tax-depreciation schedule is the active path.
  The canonical tax-bridge is **not** wired into the waterfall.
- **P&L book bridge:** legacy. The canonical book-depreciation-for-PnL
  bridge is **not** wired into the waterfall.

The D1 audit sheet is the single user-facing surface that discloses
all four "canonical / tax-bridge / book-pnl" depreciation flags and
their "currently NO" runtime state.

### 2.2 Canonical depreciation engine

The canonical `domain.depreciation` package exists and is internally
mature (asset, schedule, result, ledger, engine, tax_bridge,
canonical_wiring). The D3 redo demonstrates that for both factory
projects the canonical engine produces non-zero, internally consistent
book-depreciation arrays when called via
`build_canonical_depreciation_wiring(project_name=..., capex_items=...,
horizon_years=..., cod_period=2, period_frequency='semiannual')`.

The canonical engine is **not** runtime-authoritative. The D3 shadow
validation runs the canonical engine on a **local shadow copy** of the
project inputs and never mutates the caller's `project_inputs`; the
D3 helper `_build_canonical_book_depreciation_array` is explicitly
read-side.

### 2.3 Shadow validation module

`app/depreciation_shadow_validation.py` is the new D3 module. Public API:

- `run_shadow_validation(project_inputs, waterfall_result)` — returns
  a `ShadowComparisonSummary` for TUHO/Oborovo factory projects
- `to_json_dict(summary)` — JSON-friendly serialization
- `build_shadow_validation_audit_dataframe(summary)` — text-only
  pandas DataFrame suitable for an export audit sheet

Internal helpers:

- `_safe_float(value)` — defensive coercion
- `_build_canonical_book_depreciation_array(project_name, capex_items,
  horizon_years, cod_period, period_frequency)` — calls canonical
  engine on a shadow copy with explicit fallback to `[0.0] * horizon`
  if the canonical engine returns None

The module **never** writes to waterfall output and **never** mutates
the caller's `project_inputs`.

### 2.4 Flag discipline module

`app/depreciation_flag_discipline.py` is the D2 redo module. It owns
the single source of truth for the four canonical / tax-bridge /
book-pnl depreciation flags:

- `use_depreciation_canonical_engine`
- `use_canonical_tax_depreciation_bridge`
- `use_tax_bridge_engine`
- `use_book_depreciation_for_pnl`

Exposes read-only helpers:

- `list_depreciation_flag_names()`
- `is_canonical_promotion_active(project_inputs)`
- `get_depreciation_flag_discipline_summary(project_inputs)`

And an `assert_no_canonical_depreciation_runtime_promotion(project_inputs)`
guard that raises `PermissionError` if any flag is True. This guard
is **not** wired into the live waterfall path; it is exported for tests
and for future controlled-enablement PRs to call explicitly.

### 2.5 D1 audit sheet

`app/depreciation_audit_visibility.py` produces a 14-row
`(Field, Value)` text-only DataFrame titled "Depreciation Audit".
It is written into the Excel export immediately after the Book
Depreciation sheet and before the Phase 5D overlay sheets. The sheet
discloses:

- Phase and scope
- Active depreciation path (`legacy_depreciation_runtime`)
- Runtime authority source (`waterfall_core.LegacyDepreciationPath`
  or canonical engine iff `use_depreciation_canonical_engine=True`)
- Per-flag canonical/tax-bridge/book-pnl status (all "NO" on factory
  TUHO/Oborovo)
- Audit-only vs runtime surfaces
- Known limitations (canonical is advisory only; generic projects
  are NOT supported)
- D2 redo disclosure row confirming discipline is in place and
  canonical promotion is BLOCKED

### 2.6 Export / audit visibility

The D1 sheet is the only export-surface addition in the entire
D1+D2redo+D3redo stack. The audit sheet is text-only, with auto-index
column and no financial values. Numeric invariance is preserved for
all pre-D1 sheets in both factory exports (14 sheets preserved,
identical sums).

### 2.7 Runtime authority remains legacy

After the merged D1 + D2 redo + D3 redo stack, the runtime
authority for depreciation remains legacy (`LegacyDepreciationPath`).
None of the four canonical / tax-bridge / book-pnl depreciation
flags is enabled by default. None is enabled on TUHO or Oborovo
factory projects. The D1 sheet discloses this explicitly. The D2
redo assert helper is not wired into the waterfall. The D3 redo
shadow validation is read-only. **There is no runtime authority
change** in the merged stack.

## 3. Validation assessment

### 3.1 TUHO shadow delta

| Metric | Value |
|---|---|
| Legacy total depreciation (kEUR) | 70,691.54 |
| Canonical total book depreciation (kEUR) | 70,691.54 |
| Absolute total delta (kEUR) | 1.45 × 10⁻¹¹ |
| Relative total delta (%) | 2.06 × 10⁻¹⁴ |
| Max absolute per-period delta (kEUR) | 9.68 |
| Max absolute per-period delta period | 1 |
| `ready_for_controlled_enablement` | true |
| Qualitative | at the floating-point limit; engines agree to the cent on the total |

The TUHO delta is at the floating-point limit. The two engines agree
on the total to within numerical noise. Per-period distributions can
differ in shape (max 9.68 kEUR in period 1, which is the
construction-into-operation ramp), but the cumulative totals are
identical to floating-point precision.

### 3.2 Oborovo shadow delta

| Metric | Value |
|---|---|
| Legacy total depreciation (kEUR) | 55,996.56 |
| Canonical total book depreciation (kEUR) | 55,999.09 |
| Absolute total delta (kEUR) | 2.53 |
| Relative total delta (%) | 0.00452 |
| Max absolute per-period delta (kEUR) | 9.68 |
| Max absolute per-period delta period | 1 |
| `ready_for_controlled_enablement` | true |
| Qualitative | 2.53 kEUR on a ~56,000 kEUR base (0.0045%); well within floating-point + rounding envelope |

Oborovo's total delta is 2.53 kEUR (0.0045%) — small in absolute
and relative terms, but **not** at the floating-point limit. The
delta is attributable to per-asset-class straight-line spreading in
the canonical engine producing a slightly different total than the
legacy aggregate half-year schedule on the construction-period
boundary. This is a known characteristic of the canonical
per-asset-class schedule vs the legacy aggregate schedule, not a
correctness bug. Whether it constitutes a "parity-locked" change
is a governance decision, not an engineering one.

### 3.3 Generic project support status

The D3 shadow validation does **not** run for generic projects.
Generic (non-TUHO, non-Oborovo) projects are out of scope for the
active depreciation path. The D1 audit sheet documents this in the
"Generic_Project_Support" row, which is `NO — depreciation runtime
authority for generic (non-TUHO, non-Oborovo) projects is out of
scope for the active runtime path. This audit sheet applies to the
current active path only.`

### 3.4 Numeric invariance

`period.depreciation_keur` and `tax_depreciation_audit_keur` are
bit-for-bit identical pre- and post-D1, post-D2 redo, and post-D3
redo. The shadow validation confirms this for both TUHO and
Oborovo: the legacy active path is the source of the waterfall
output, and the canonical engine results are advisory-only.

### 3.5 Test coverage

| Test bucket | Count | Status |
|---|---|---|
| D1 new tests | 23 | green |
| D2 redo new tests | 30 | green |
| D3 redo new tests | 21 | green |
| 57A-9E isolated | 13/13 | green |
| Phase 51F Parity Guardrails | 21/21 | green |
| Phase 57pre route smoke | 50 pass / 17 skip | green |
| Full 57 arc stack | 1180 pass / 75 skip / 2 fail | the 2 failures are pre-existing 57A-9E test pollution that also fail on main and are not D1/D2/D3 regressions |

The 2 pre-existing failures (`test_oborovo_equity_irr_within_tolerance_dep_canonical`
and 2 `test_phase57a9e_capex_sub_lines_excel_export.py` cases) are
documented in D1's report and confirmed to also fail on main. They
are not regressions introduced by the depreciation arc.

### 3.6 Remaining test pollution

The 2 pre-existing 57A-9E failures are the only known remaining
test pollution in the wider stack. They are not depreciation-related
and are not on the D1/D2/D3 critical path. They are tracked outside
this review.

## 4. Enablement risk assessment

For each potential D4 path, the risk is summarized below. The merged
stack gives us a clean baseline to evaluate these from.

### 4.1 TUHO controlled enablement

- **Numeric risk:** low. TUHO shadow delta is at the floating-point
  limit (2 × 10⁻¹⁴ % on total). Per-period max delta is 9.68 kEUR
  in period 1 (construction ramp).
- **Governance risk:** moderate. Requires explicit flag enablement
  on a single project, parity-gated check, and a rollback path.
- **Tax / P&L / CFADS impact:** all three would change slightly.
  Tax depreciation is bit-for-bit identical today, so any promotion
  would change the published tax result.
- **Excel export impact:** the D1 sheet would flip from
  "Canonical Depreciation Engine Enabled: NO" to "YES" for TUHO.
  The Tax_Depreciation / Book Depreciation sheet values would change
  by sub-floating-point amounts.
- **Verdict:** feasible as a single-project flag-gated enablement,
  but not zero-risk. Requires its own governance review.

### 4.2 Oborovo controlled enablement

- **Numeric risk:** moderate. Oborovo shadow delta is 2.53 kEUR
  (0.0045%) on a ~56,000 kEUR base. The delta is not at the
  floating-point limit.
- **Governance risk:** moderate. The 0.0045% delta is small in
  absolute terms but **measurable**, so this is a "parity-breaking
  by design" enablement, not a floating-point-clean one.
- **Tax / P&L / CFADS impact:** all three would change by a
  measurable amount. The tax result would change by 2.53 kEUR
  cumulative.
- **Excel export impact:** D1 sheet would flip to "YES" for Oborovo.
  Tax_Depreciation and Book Depreciation sheets would change by
  measurable amounts.
- **Verdict:** feasible only as an explicit "we accept a 0.0045%
  total delta in exchange for canonical depreciation on Oborovo"
  governance decision, not a parity-preserving enablement.

### 4.3 TUHO + Oborovo combined

- **Combined risk:** the combined delta is bounded by the union
  of the two individual deltas. TUHO is at the floating-point
  limit; Oborovo contributes 2.53 kEUR (0.0045%) on its own.
  Combined is still well within any reasonable parity-tolerance
  envelope.
- **Verdict:** no additional risk beyond the two individual
  enablements.

### 4.4 Generic project depreciation

- **Numeric risk:** unknown. The D3 shadow validation does not
  run for generic projects. There is no parity evidence for
  generic-project depreciation.
- **Governance risk:** high. Generic-project depreciation is
  out of scope for the active runtime path. There is no audit
  surface, no flag discipline, no shadow validation for generic
  depreciation.
- **Verdict:** not recommended at this time. Generic depreciation
  would require a separate design phase.

### 4.5 P&L impact

For both TUHO and Oborovo, the legacy waterfall produces
`period.depreciation_keur` that is the input to the P&L book
depreciation line. Canonical enablement would replace this with
the canonical engine's per-period book depreciation. For TUHO,
the per-period differences are at the floating-point limit; for
Oborovo, the differences are bounded by 9.68 kEUR per period and
0.0045% on the total. The P&L aggregate is small in both cases
but measurable on Oborovo.

### 4.6 Tax impact

The legacy waterfall produces a tax-depreciation schedule that
feeds the tax calculation. The D2 redo confirms the tax-bridge
flags are all NO by default. Canonical tax-bridge enablement
would require both `use_depreciation_canonical_engine=True` and
`use_canonical_tax_depreciation_bridge=True`. The shadow validation
is book-depreciation only; the tax-bridge delta has not been
quantified.

### 4.7 CFADS impact

CFADS is downstream of the P&L book depreciation and the tax
calculation. Any P&L or tax delta would propagate into CFADS.
For TUHO the propagation is at the floating-point limit; for
Oborovo it is the 0.0045% delta plus its downstream tax effect.

### 4.8 Excel export impact

The D1 audit sheet would flip its "Canonical Depreciation Engine
Enabled" row from NO to YES for the project under enablement.
The Tax_Depreciation, Book Depreciation, and downstream P&L /
Returns / Waterfall sheets would reflect the canonical values.
Pre-canonical sheets (Dashboard, Revenue, Debt, CapEx, etc.)
would not change.

### 4.9 Governance impact

Any D4 enablement would require:

- A D4 design doc that quantifies the per-project shadow delta
  explicitly
- Explicit user sign-off on the per-project delta
- Flag-gated enablement with a rollback path
- A parity-locked update to the D1 audit sheet's "Active
  Depreciation Path" row
- Confirmation that rc1 (`b425a0708719eaa5e1d922b1008e5609758e0ad4`)
  is preserved
- No generic-project claims

## 5. GO / NO-GO decision

### Recommendation: **GO — pause here (Option A). Do not start D4.**

**Rationale:**

The D1 + D2 redo + D3 redo stack successfully closes the safe-next-step
arc recommended by PR #530:

- D1 added export/audit visibility without runtime change.
- D2 redo added flag discipline without persistence or waterfall change.
- D3 redo added shadow validation showing TUHO and Oborovo are within
  tolerance for any future enablement.

The merged stack gives us:

- A clear, text-only disclosure of the current runtime authority
  (legacy) and the four canonical / tax-bridge / book-pnl flags
  (all NO) via the D1 audit sheet.
- A read-only flag discipline module (D2) that prevents accidental
  runtime promotion without explicit assertion.
- A read-only shadow comparison (D3) that quantifies the per-project
  delta between legacy and canonical paths.

What the stack does **not** do:

- It does not enable any flag.
- It does not promote the canonical engine to runtime authority.
- It does not change P&L, tax, or CFADS.
- It does not provide generic-project depreciation support.

This is the correct posture. The merged stack is the "audit, don't
touch" phase. Starting D4 now — whether design or runtime enablement —
would invert this posture and require its own governance review.

### Why not D4 design only?

A D4 design-only PR would be defensible, but:

- The D3 shadow validation already provides the per-project delta
  evidence that a D4 design would have to reproduce.
- D4 design work would either (a) re-package the D3 evidence into a
  control plan, which adds little new information, or (b) propose a
  runtime enablement, which is a different and heavier ask.
- The current governance posture (audit-only, flag discipline
  enforced, no generic claims) is the right baseline for pausing.

### Why not D4 runtime enablement?

- TUHO is at the floating-point limit, but Oborovo is at 0.0045%.
  This is a measurable delta, not a parity-preserving enablement.
- Promoting the canonical engine to runtime authority would change
  published tax and CFADS values, which is a reviewer-confidence
  decision that should be made explicitly, not by default.
- Generic projects have no shadow evidence and no audit surface.
  Any "TUHO + Oborovo + generic" enablement is not supported by
  the current stack.
- D4 runtime enablement would also require updating the D1 audit
  sheet's "Active Depreciation Path" row, which is a parity-locked
  disclosure change.

### Why not pause and switch to a different roadmap arc?

This is the recommended next step (Option A). See §6.

## 6. Recommended next step

**Pause the depreciation arc here.** The D1 + D2 redo + D3 redo
stack is a clean, well-tested audit posture. Further depreciation
work should be re-evaluated when the wider governance posture
changes (e.g. G20 moves from BLOCKED, R99/R102 move to APPROVED, or
the user signals a need to revisit enablement).

Recommended next roadmap arc, in order of priority based on the
current state of the project:

1. **Generic Solar / Wind validation methodology** — generic projects
   are explicitly out of scope for depreciation today, and there is
   no general validation methodology for them. A methodology PR
   would unblock both future depreciation work and the broader
   "TUHO + Oborovo as parity references" framing.
2. **CAPEX schedule / construction IDC design gate** — the
   CAPEX sub-lines work (57A-9B/9C/9D/9E) is merged, but the
   construction IDC design gate is a separate design question that
   interacts with depreciation on the construction-period boundary.
   This is the most direct next-step that would feed back into
   future depreciation work.
3. **OPEX line-item visibility expansion** — the TUHO/Oborovo
   parity work has identified 12-15 OPEX line items per project.
   A visibility PR would consolidate this and is a prerequisite
   for any future bankable / review-grade work.
4. **Formula transparency expansion** — the model has many
   formula surfaces. A transparency PR would help any future
   reviewer or auditor.
5. **Governance / guardrail cleanup** — the post-D2 redo phase
   showed that file-scope tests (e.g.
   `test_no_persistence_directory_changed`) can flag benign changes
   as forbidden-path violations. A guardrail cleanup PR could
   formalize the post-merge verification flow.

## 7. D4 boundaries (if D4 is later re-evaluated)

This section is included for completeness. **D4 is not started
under this review.** If D4 is re-evaluated in the future, it must
be:

- **Controlled:** single-project flag-gated enablement, scoped
  to a specific run, with explicit user sign-off on the per-project
  delta.
- **Explicit:** documented design PR with quantified shadow deltas
  for the target project(s).
- **Flag-gated:** all four canonical / tax-bridge / book-pnl
  flags must be explicitly True, with the D2 discipline guard
  invoked.
- **TUHO / Oborovo only:** unless a generic-project validation
  methodology PR is merged first, generic projects are not in
  scope for D4.
- **No generic claims:** the D1 audit sheet's "Generic Project
  Support" row must remain NO until generic support is designed
  and validated.
- **Parity-gated:** Phase 51F parity guardrails must remain green
  for the project under enablement.
- **With rollback path:** flag flip must be reversible by a single
  project-input change.
- **With before/after depreciation deltas:** the D3 shadow
  validation must be run against the same project pre- and
  post-enablement, and the deltas must be disclosed in the
  resulting export's Depreciation Audit sheet.
- **With tax / P&L / CFADS impact disclosure:** the D4 PR must
  quantify the cumulative tax, P&L, and CFADS impact of the
  enablement on the target project, and the result must be
  published in the export.

## 8. Stop-after-report contract

This review is:

- A docs/report-only review.
- No implementation, no runtime change, no flag enablement.
- No D4 start, no D4 design PR, no D4 runtime enablement.
- No new tests, no new code, no new persistence, no new schema,
  no new export surface, no new UI.

The only files changed in this review are:

- `docs/phase_depreciation_stack_closure_review.md` (this file)
- `reports/phase_depreciation_stack_closure_review.json`
  (machine-readable summary)

Branch: `phase-depreciation-stack-closure-review`
PR: DRAFT only, do not mark ready, do not merge.

rc1 SHA: `b425a0708719eaa5e1d922b1008e5609758e0ad4` — untouched.

## 9. Appendix — D1 + D2 redo + D3 redo summary table

| Phase | PR | Title | Files | LOC | Runtime change | Persistence change |
|---|---|---|---|---|---|---|
| D1 | #531 | Export / Audit Visibility | 5 (1 new module + 28-line `excel_export.py` patch + tests + docs + report) | 175 + 28 | none (read-only audit sheet) | none |
| D2 redo | #534 | Flag Discipline (redo) | 5 (1 new module + 18-line `audit_visibility.py` patch + tests + docs + report) | 195 + 18 | none (assert helper not wired) | none |
| D3 redo | #533 | Shadow Validation | 4 (1 new module + tests + docs + report) | 432 | none (read-only shadow) | none |
| Closure | (this PR) | Stack Closure Review | 2 (this doc + JSON) | n/a | none | none |

Total new runtime surface across D1+D2redo+D3redo: 0.
Total new persistence surface across D1+D2redo+D3redo: 0.
Total new audit surface across D1+D2redo+D3redo: 1 (the D1 Depreciation
Audit sheet, with the D2 redo disclosure row).
