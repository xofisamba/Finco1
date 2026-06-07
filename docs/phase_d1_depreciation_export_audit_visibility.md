# Phase D1 — Depreciation Export / Audit Visibility Hardening

**Type**: docs + export audit visibility (no runtime enablement).

**Status**: DRAFT PR. **Do NOT mark ready.** Do NOT merge.
Do NOT start any further depreciation runtime work before
review and explicit go-ahead.

**Base**: `22d816277c494dd1926f133b15dad5bf2f10d173` (post-PR #530).

**Branch**: `phase-depreciation-d1-export-audit-visibility`

## 1. Summary

This PR is the next safe step recommended by PR #530
(depreciation enablement readiness review). PR #530 concluded
**NO-GO** for broad runtime depreciation enablement. The
recommendation was to improve **audit visibility, flag
discipline, and shadow validation first**, before any
runtime promotion.

D1 implements the **first of those three** improvements —
audit visibility. It does NOT enable any feature flag. It
does NOT change depreciation schedules, tax calculations,
P&L, CFADS, or waterfall runtime authority. It does NOT
make generic-project depreciation claims. It only ADDS a
single, text-only `Depreciation Audit` sheet to the
workbook that discloses:

- the active depreciation runtime path
- the runtime authority source
- the canonical depreciation engine flag status
- the canonical tax bridge flag status
- the tax-bridge-engine flag status
- the book-depreciation P&L bridge flag status
- the audit-only / runtime / known-limitations surfaces
- whether the active path supports generic projects (it
  does not)

## 2. Changed files (3 files, +440 / -10)

| Status | File | Rationale |
|---|---|---|
| A | `app/depreciation_audit_visibility.py` | New module: `_resolve_depreciation_runtime_authority` reads the current flag snapshot (from `provenance_metadata` or via `runtime_flag_snapshot`) and returns a dict of disclosure strings. `build_depreciation_audit_dataframe` produces the (Field, Value) DataFrame for the sheet. Pure read-side / disclosure code. No write to model / runtime. |
| M | `app/excel_export.py` | Three small additions: (1) `from app.depreciation_audit_visibility import build_depreciation_audit_dataframe` import. (2) New `_write_depreciation_audit_sheet(writer, project_inputs, provenance_metadata)` helper that writes a text-only "Depreciation Audit" sheet. (3) Wire-up call in `build_excel_export` immediately after the existing Book Depreciation Disclosure call. |
| A | `tests/test_phase_d1_depreciation_export_audit_visibility.py` | 23 new design-contract tests pinning: sheet existence in both factory exports (TUHO, Oborovo); required disclosure fields; flag status disclosure; helper-text-only invariant; numeric invariance (TUHO and Oborovo existing sheet sums unchanged); existing sheets still present; no feature flag enabled; rc1 frozen. |

The Excel import line and the wire-up call preserve the
existing CRLF / LF mixed line-ending convention used by the
rest of `app/excel_export.py`.

## 3. Exact wording of the new "Depreciation Audit" sheet

The sheet has 14 rows. All values are text. The auto-index
column (0..13) is the only numeric artifact, and it is not
a financial value.

| Field | Value |
|---|---|
| Phase | D1 — Depreciation Export / Audit Visibility Hardening |
| Scope | Audit visibility only. NO runtime enablement. NO formula / schedule / tax / P&L / CFADS change. |
| Notice | Depreciation export visibility only — no runtime authority change. |
| Active Depreciation Path | `legacy_depreciation_runtime` (TUHO/Oborovo baseline; becomes `canonical_depreciation_engine` iff `use_depreciation_canonical_engine=True`) |
| Runtime Authority Source | `waterfall_core.LegacyDepreciationPath` (or `domain.depreciation.engine.DepreciationEngine` if canonical on) |
| Canonical Depreciation Engine Enabled | `NO` (TUHO/Oborovo baseline) |
| Canonical Tax Bridge Enabled | `NO` |
| Tax Bridge Engine Enabled | `NO` |
| Book Depreciation P&L Bridge Enabled | `NO` |
| Values Reflect | Current active backend runtime path (NOT a canonical-promotion simulation). |
| Audit-Only Surfaces | Depreciation Assumptions; Depreciation Audit (this sheet); canonical audit rows when present in `result._canonical_depreciation_wiring` (advisory only, not runtime authority). |
| Runtime Surfaces | Tax_Depreciation; Tax Depreciation; Book Depreciation; waterfall `period.depreciation_keur` (when produced by the active runtime path). |
| Known Limitations | Canonical DepreciationEngine is not runtime-authoritative unless explicitly enabled. Audit values from the canonical engine, when present, are advisory and do NOT change the waterfall output. Generic-project depreciation claims are NOT supported. Depreciation visibility is consolidated only for the active runtime path. |
| Generic Project Support | NO — depreciation runtime authority for generic (non-TUHO, non-Oborovo) projects is out of scope for the active runtime path. This audit sheet applies to the current active path only. |

## 4. Pre-merge audit — all green

**Scope (all verified)**
- Export / audit visibility only
- NO Excel export integration beyond the new sheet
- NO UI / template changes (`app/templates/`, `static/app.js`, `static/styles.css` not modified)
- NO model formula changes
- NO tax / depreciation schedule / payment schedule / IDC / P&L / CFADS changes
- NO persistence changes
- NO schema changes
- NO G20 / R99 / R102 promotion
- NO feature flag enablement (canonical engine is still off; the audit sheet reports this)

**Numeric invariance (all verified, pinned by tests)**
- TUHO `CapEx` sum: 145,988.42 (unchanged)
- TUHO `CapEx_Items` sum: 70,706.54 (unchanged)
- TUHO `Inputs` sum: 79,580.2375 (unchanged)
- TUHO `Depreciation Assumptions` sum: 45.0 (unchanged)
- TUHO `Tax Depreciation` sum: 0.0 (unchanged)
- TUHO `Tax_Depreciation` sum: 0.0 (unchanged)
- TUHO `Book Depreciation` sum: 0.0 (unchanged)
- Oborovo `CapEx` sum: 115,758.5053 (unchanged)
- Oborovo `CapEx_Items` sum: 56,104.09 (unchanged)
- Oborovo `Inputs` sum: 61,272.8532 (unchanged)
- Oborovo `Depreciation Assumptions` sum: 45.0 (unchanged)
- Oborovo `Tax Depreciation` sum: 0.0 (unchanged)
- Oborovo `Tax_Depreciation` sum: 0.0 (unchanged)
- Oborovo `Book Depreciation` sum: 0.0 (unchanged)
- (new) `Depreciation Audit` sum: text-only (auto-index column only, no financial value)

**Existing sheets still present (all verified, pinned by tests)**
- TUHO: all 14 pre-existing sheets still present (Dashboard, Returns, Waterfall, Revenue, Debt, Tax_Depreciation, Notes, Inputs, CapEx, CapEx_Items, Validation, Depreciation Assumptions, Tax Depreciation, Book Depreciation) + the new Depreciation Audit
- Oborovo: same 14 + Depreciation Audit

**No runtime enablement (all verified, pinned by tests)**
- `use_depreciation_canonical_engine` is still `False` in baseline
- `use_canonical_tax_depreciation_bridge` is still `False`
- `use_book_depreciation_for_pnl` is still `False`
- The audit sheet correctly reports `NO` for all canonical flags in baseline

**Tests (all green)**
- 23 / 23 new D1 tests pass
- 13 / 13 57A-9E excel export tests pass (isolated run)
- 21 / 21 Phase 51F Parity Guardrails pass (green)
- 55 pass / 12 skip Phase 57pre route smoke (green)
- 2 known pre-existing test failures in `test_phase57a9e_capex_sub_lines_excel_export.py` and `test_depreciation_canonical_wiring.py` — verified to ALSO fail on `main` (pre-existing infra rot, not D1 regressions)

**rc1 frozen** — `b425a0708719eaa5e1d922b1008e5609758e0ad4` verified still resolves

## 5. Hard no-go (12 items, all verified pre-push)

1. **no_runtime_depreciation_enablement** (D1 is visibility only)
2. no_feature_flag_enablement
3. no_formula_changes
4. no_depreciation_schedule_changes
5. no_tax_calculation_changes
6. no_pnl_calculation_changes
7. no_cfads_changes
8. no_persistence_changes
9. no_schema_changes
10. no_ui_workflow_changes_unless_readonly_label
11. no_generic_project_depreciation_claims
12. rc1_frozen (`b425a0708719eaa5e1d922b1008e5609758e0ad4`)

## 6. Stop-after-report contract

This PR is DRAFT. Do NOT mark ready. Do NOT merge. Do NOT
start any further depreciation runtime work before review
and explicit go-ahead.

The 23 design-contract tests pin the audit-visibility
contract. The numeric-invariance tests pin that no existing
sheet's numbers changed. The flag-status tests pin that no
feature flag is enabled by D1.

## 7. Recommended next step (post-D1)

After D1 review, the recommended next safe steps are:

- **Phase D2** — flag discipline hardening: make the
  exposure / shadow-validation surface for the canonical
  depreciation engine single-source-of-truth clean
- **Phase D3** — shadow validation: run canonical and
  legacy side-by-side, log audit deltas, never promote
  the canonical values to runtime authority
- OR alternative tracks: pause and review the depreciation
  arc, defer until TUHO/Oborovo G20/R99/R102 posture
  changes, or focus on a different governance arc
