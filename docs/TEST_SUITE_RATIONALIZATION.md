# Stack AA — Test Suite Rationalization & Engineering Baseline

**Date:** 2026-07-03  
**Branch:** `stack-aa-test-suite-rationalization`  
**Status:** Governance documentation — no financial logic changed

---

## Executive Summary

The Finco1 test suite has grown organically across ~50 development phases, accumulating 879 test files and 19,520 collected tests. The financial engine is healthy; the test suite does not accurately reflect that health. The majority of non-CI tests are historical characterization artifacts written during construction, not product defect indicators.

**Current CI runs 22 specific test files.** All 5 CI jobs are green. The remaining 857 files are not part of any CI pipeline and are not actively maintained.

This document classifies every test file, documents its maintenance value, and provides a roadmap for evolving the suite into an accurate engineering asset — without changing any financial logic.

---

## AA1 — Test Census

### Top-level Counts

| Metric | Count |
|--------|-------|
| Total test files (`test_*.py`) | 879 |
| Support files (conftest, helpers, __init__) | 12 |
| **Total files in `tests/`** | **891** |
| Tests collected by pytest | 19,520 |
| Tests in active CI | ~290 (22 files) |
| Test files in CI | 22 |
| Test files NOT in any CI pipeline | ~857 |

### File Distribution by Category

| Category | Files | Est. Tests | CI Coverage | Maintenance Value |
|----------|-------|-----------|-------------|-------------------|
| Core engine | ~200 | ~4,500 | Partial (6 files in CI) | **HIGH** |
| Phase development (all phases) | 459 | ~12,925 | None (0 files in CI) | Mixed — see AA2/AA3 |
| Stack / Golden parity | 21 | ~578 | Full (parity_guardrails.yml) | **HIGH** |
| Browser / Playwright | 39 | ~647 | None | Medium (environment-gated) |
| UI component (non-browser) | 32 | ~800 | None | Medium |
| Integration | 5 | ~50 | None | High (but partially disabled) |
| Golden validation | 1 | ~12 | None | High |
| Product gap / acceptance | ~18 | ~300 | None | Medium |
| Runtime / fixture audit | ~90 | ~800 | None | High (engine invariants) |
| API / auth / persistence | ~20 | ~300 | None | High |
| Disabled (calibration) | 15 | ~500 | Skipped in conftest | Low (app.calibration disabled) |
| Quarantined (SQLAlchemy) | 2 | ~60 | Skipped in file | Legacy only |
| Legacy (core module absent) | 12 | ~200 | Skipped in conftest | Requires `core` package |
| Support / helpers | 12 | — | — | Required |

---

## AA2 — Characterization Audit

### Pattern Summary

Of the 459 phase test files, three patterns dominate:

**Pattern 1: Git-diff source guards** (~205 files)
Tests that run `git diff` or `subprocess` to assert no production code was changed during a development phase. These were valid at merge time but are **permanently stale** — they compare the current HEAD to historical SHAs or to `origin/main` at the time they were written. In a steady state they either pass vacuously or fail on unrelated differences.

Examples:
- `test_phase37_pilot_ux_walkthrough_friction_audit.py` — asserts git diff shows no changes to financial files
- `test_phase49_closeout_export_service_audit_extraction.py` — asserts no fixture CSV changes via `git diff`
- `test_phase51a_run_route_golden_characterization.py` — contains guardrails asserting specific files don't exist yet

**Recommendation:** These tests served their purpose during construction. The behavioral invariants they protected are now covered by the Phase 51F parity guardrails and stack parity tests. They should NOT be deleted individually, but should be excluded from the default collection profile (see AA7).

**Pattern 2: Design document existence tests** (~80 files, especially phase 9–16)
Tests that assert specific documentation files exist in `docs/` or `reports/`. These validate that design artifacts were created during a phase but test no runtime behaviour.

Examples:
- `test_phase9_5_excel_like_project_workspace_ui_design.py` — asserts docs/*.md files exist
- `test_phase10_calibration_reconciliation_pack.py` — asserts reports/*.xlsx files exist

**Recommendation:** Low ongoing value. Document as Legacy-Characterization. Retain as historical record.

**Pattern 3: Route/API structure pinning** (~100 files, phase 49–57)
Tests that pin the structure of API responses, route existence, and HTML template structure. These have genuine value if kept current. Phase 51 tests in this category are the most robust — they are characterization tests that will catch structural regressions.

**High-value phase characterization (retain and consider promoting to CI):**
- `tests/test_phase51f_parallel_work_guardrails.py` — SHA pinning + AST checks (in CI ✅)
- `tests/test_phase52f_persistence_guardrail_*.py` — persistence invariants (in CI ✅)
- `tests/test_phase53i*.py` — records module shape (in CI ✅)
- `tests/test_phase57a9*.py` — CAPEX persistence (in CI ✅)
- `tests/test_phase57f_legacy_quarantine.py` — quarantine enforcement (in CI ✅)

### Source-Text Assertion Tests

114 test files use `grep`, `ast.parse`, `inspect.getsource`, or `open(__file__)` to assert on source code content. These are **characterization tests by nature** — they pin the code structure at a point in time rather than testing runtime behaviour.

| Sub-category | Count | Value |
|---|---|---|
| SHA pinning (`hashlib.sha256`) | 20 | High where pinned files change slowly |
| `git diff` assertions | 205 | Stale — historical only |
| AST / import structure checks | 30 | Medium — fragile but informative |
| Template content `in html` | 40 | Medium — catches regressions in rendered output |

---

## AA3 — Legacy Audit

### Group 1: `CORE_LEGACY_TEST_FILES` (conftest-skipped)

These 12 files require a `core` package that is no longer present in the active engine. They are skipped silently via `conftest.pytest_ignore_collect`. They represent the pre-refactor waterfall engine.

| File | Reason Skipped |
|------|----------------|
| `test_hybrid_clipping.py` | Requires `core.hybrid` |
| `test_wind1_fixture.py` | Requires `core.wind` |
| `test_bess_engine.py` | Requires `core.bess` |
| `test_capex_tree.py` | Requires `core.capex` |
| `test_equity.py` | Requires `core.equity` |
| `test_generic_tax.py` | Requires `core.tax` |
| `test_goal_seek.py` | Requires `core.goal_seek` |
| `test_hybrid_engine.py` | Requires `core.hybrid` |
| `test_hybrid_lp_engine.py` | Requires `core.lp` |
| `test_monte_carlo.py` | Requires `core.monte_carlo` |
| `test_waterfall_dscr.py` | Requires `core.waterfall` |
| `test_wind_engine.py` | Requires `core.wind` |

**Recommendation:** Move to `tests/legacy/core_engine/`. These will never run in the active CI and confuse the count. Retaining them preserves historical context if the `core` package is ever restored.

**Status in this stack:** Not moved (conservative per AA spec). Listed here for future action.

### Group 2: `_CALIBRATION_DISABLED_FILES` (conftest-skipped)

15 files that import from `app.calibration`, which raises `ImportError` at the module level (guarded by `app/calibration.py` itself). These are skipped via `conftest.pytest_ignore_collect` when `app.calibration` is unavailable (which is always the case in the active engine).

| File | Reason |
|------|--------|
| `test_debt_dscr_schedule_policy.py` | Uses `app.calibration.load_project_inputs` |
| `test_debt_excel_alignment.py` | Uses `app.calibration` |
| `test_finco_gpt_calibration_runner.py` | Calibration GPT runner |
| `test_finco_gpt_calibration_serialization.py` | Calibration GPT |
| `test_finco_gpt_headless_core.py` | Calibration GPT |
| `test_headless_calibration_runner.py` | Calibration runner |
| `test_oborovo_excel_reconciliation.py` | Uses `app.calibration` |
| `test_opex_excel_alignment.py` | Uses `app.calibration` |
| `test_period_engine_excel_alignment.py` | Uses `app.calibration` |
| `test_pl_tax_excel_alignment.py` | Uses `app.calibration` |
| `test_project_irr_excel_alignment.py` | Uses `app.calibration` |
| `test_regression.py` | Uses `app.calibration` |
| `test_revenue_excel_alignment.py` | Uses `app.calibration` |
| `test_revenue_formula_units.py` | Uses `app.calibration` |
| `test_shl_excel_alignment.py` | Uses `app.calibration` |
| `test_tuho_excel_reconciliation.py` | Uses `app.calibration` |

Note: `test_shl_excel_alignment.py` is also listed separately due to SHA-pinning assertions.

**Recommendation:** These files have historical diagnostic value for when `app.calibration` is re-enabled. They satisfy AA8 removal criteria (obsolete in current engine, duplicated by active parity tests, no runtime validation, fully documented here). However, per conservative AA8 policy, they are retained with explicit conftest skip documentation.

### Group 3: Explicitly Quarantined

| File | Status |
|------|--------|
| `tests/test_persistence.py` | `pytest.skip(allow_module_level=True)` — SQLAlchemy legacy |
| `tests/test_repository.py` | `pytest.skip(allow_module_level=True)` — SQLAlchemy legacy |

These are enforced by `test_phase57f_legacy_quarantine.py` (in CI). Pattern is correct — skip marker in the file itself, enforcement test in CI.

### Group 4: `integration/test_fid_deck_excel.py`

Skipped via conftest because it requires `ProjectInputs.create_default_oborovo` from `app.calibration`. Same root cause as Group 2.

---

## AA4 — Playwright / Browser Audit

### Overview

39 `*_browser.py` files, ~647 tests.

All browser tests fall into one of two sub-patterns:

**Sub-pattern A: Static fixture tests** (~12 files)
Run against a standalone HTML fixture file via Playwright. Server not required. Self-skip via `pytest.importorskip("playwright.sync_api")` when Playwright is absent.

Examples: `test_c1_pr1_grid_registry_browser.py` through `test_c1_pr9_fill_controller_browser.py`

**Sub-pattern B: Live uvicorn server tests** (~27 files)
Spawn a real uvicorn server as a subprocess. Require Playwright + uvicorn + a running database. Self-skip via `pytest.importorskip` when Playwright is absent.

Examples: `test_product_gap_pr1_capex_excel_editing_browser.py`, all `*_c1_migration_browser.py`

### Failure Classification

In the current CI environment:
- **Environment failure rate: 100%** — Playwright is not installed in any current CI job.
- All 647 browser tests **skip** (not fail) due to `pytest.importorskip`.
- These are **not product defects**. They are environment gaps.

### CI Recommendation

| Test group | Recommended CI home |
|------------|---------------------|
| Static fixture browser (sub-pattern A) | New `browser-static` CI job with Playwright installed |
| Live server browser (sub-pattern B) | Nightly or staging-only; require running app instance |
| Current behavior (skip on missing playwright) | Retain as fallback — do not hard-fail |

**The current self-skip mechanism is correct.** Do not replace it with hard errors. Add a dedicated CI job with Playwright available to actually exercise them.

---

## AA5 — Duplicate Coverage Analysis

### High-duplication areas

**Tax / CIT computation:**
The following files all test overlapping aspects of CIT, R67, and the tax bridge. Coverage is intentionally layered — each file has a distinct focal point — but there is semantic overlap.

| File | Focus |
|------|-------|
| `test_tax.py` | Core tax engine unit |
| `test_tax_engine.py` | Tax engine behaviour |
| `test_tax_bridge_runtime_flag.py` | Flag routing |
| `test_tax_bridge_residual_r67_final_calibration.py` | R67 residual calibration |
| `test_r67_cash_tax_diagnostic_field.py` | R67 field presence |
| `test_r67_cash_tax_source_bridge.py` | R67 source attribution |
| `test_r67_full_calibration_validation.py` | R67 full validation |
| `test_cit_h2_annual_trigger.py` | H2 cash settlement |
| `test_stack_z_tax_depreciation_runtime.py` | Stack Z: book vs tax dep |
| `test_excel_parity_stack_p/t.py` | Golden parity |

**Recommendation:** Retain all. Each file has a distinct purpose. The overlap is intentional layering, not duplication.

**SHL computation:**
Similar intentional layering across `test_shl_engine.py`, `test_shl_runner.py`, `test_shl_integration.py`, `test_shl_waterfall_priority.py`, `test_shl_canonical_wiring.py`, `test_shl_fcf_waterfall_runtime_flag.py`, etc.

**Recommendation:** Retain all. The SHL engine is complex; each file tests a distinct invariant.

**Phase tests duplicating engine tests:**
Many `test_phase*.py` files re-test behaviour that is already covered by the named engine test files. For example, `test_phase23a_frozen_excel_senior_debt_schedule_runtime_wiring.py` covers senior debt scheduling — which is also covered by `test_senior_debt_alignment.py`, `test_senior_dscr_sculpting_runtime_flag.py`, etc.

**Recommendation:** The phase tests are historical characterization. The named engine tests are the canonical source. Do not remove phase tests — they serve as a historical record. Where behaviour changes, update the named engine tests first; phase tests become informational.

---

## AA6 — Canonical Test Structure

### Current directory structure

```
tests/
├── conftest.py
├── reconciliation_helpers.py
├── golden/
│   ├── fixtures/          (oborovo_golden.py, tuho_golden.py)
│   ├── utils/             (comparison, formatting, snapshot)
│   └── test_golden_validation.py
├── integration/
│   ├── test_fid_deck_excel.py   (disabled — calibration)
│   ├── test_hybrid_clipping.py  (disabled — core)
│   ├── test_solar1_fixture.py
│   ├── test_tuho_wind1_fixture.py
│   └── test_wind1_fixture.py    (disabled — core)
└── test_*.py              (877 flat files)
```

### Proposed long-term structure

The following is a migration target, NOT implemented in this stack. No files are moved here.

```
tests/
├── conftest.py
├── reconciliation_helpers.py
├── golden/                       (retain as-is)
├── integration/                  (retain as-is)
│
├── core_engine/                  # ~200 high-value engine unit tests
│   ├── test_depreciation*.py
│   ├── test_tax*.py
│   ├── test_shl*.py
│   ├── test_waterfall*.py
│   ├── test_loss_carryforward*.py
│   ├── test_senior_debt*.py
│   ├── test_financial_formulas.py
│   └── ...
│
├── parity/                       # Stack / golden parity (21 files)
│   ├── test_excel_parity_stack_*.py
│   └── test_stack_*.py
│
├── runtime/                      # R35, R67, R99 audit, construction, period engine
│   ├── test_r35*.py
│   ├── test_r67*.py
│   ├── test_r99*.py
│   ├── test_s1*.py
│   └── ...
│
├── api/                          # API + auth + persistence
│   ├── test_api.py
│   ├── test_auth_lite.py
│   ├── test_persistence.py       (quarantined)
│   └── ...
│
├── ui/                           # UI component tests (non-browser)
│   ├── test_c1_*.py
│   ├── test_c2_*.py
│   └── ...
│
├── browser/                      # Playwright tests
│   └── test_*_browser.py
│
├── phase/                        # Historical phase characterization (read-only)
│   └── test_phase*.py
│
└── legacy/                       # Disabled / skipped files
    ├── core_engine/              # CORE_LEGACY_TEST_FILES
    └── calibration/              # _CALIBRATION_DISABLED_FILES
```

**Migration priority:**
1. (P1) Create `tests/legacy/` — move 29 disabled files. Low risk; these are already skipped.
2. (P2) Create `tests/parity/` — move 21 stack/parity files. High value; keeps CI targets clear.
3. (P3) Create `tests/browser/` — move 39 browser files. Enables per-directory CI targeting.
4. (P4) Create `tests/core_engine/` — move ~200 named engine tests. Largest effort; defer.
5. (P5) Archive `tests/phase/` — read-only historical record.

---

## AA7 — CI Strategy

### Current CI

| Job | Files | Scope |
|-----|-------|-------|
| Core model tests | 6 | SHL waterfall priority, frozen schedule, revenue, opex, SHL calibration |
| CAPEX persistence and route smoke | 8 | Phase 57 CAPEX hierarchy, persistence, route smoke |
| Persistence and records guardrails | 6 | Phase 52F persistence, Phase 53I records relocation |
| Legacy quarantined sentinels | 1 | Quarantine enforcement (test_phase57f) |
| Parity Guardrails (Phase 51F) | 1 | SHA pinning + AST checks + engine output golden |

Total: **22 files**, **~290 tests**, **green on every PR**.

### Recommended CI Strategy

#### Fast CI (current, every PR)
Keep current. It covers the most critical invariants and runs in < 3 minutes.

Potential additions — **low risk** if added to Fast CI:
- `tests/test_stack_z_tax_depreciation_runtime.py` (Stack Z golden)
- `tests/test_excel_parity_stack_p.py` (Golden parity)
- `tests/test_excel_parity_stack_t.py` (T-baseline golden)
- `tests/test_waterfall_runner.py` (core waterfall)
- `tests/test_shl_waterfall_priority.py` (already in CI ✅)
- `tests/test_loss_carryforward_rolling_engine.py` (LCF engine)
- `tests/test_senior_dscr_sculpting_runtime_flag.py` (sculpting flag)
- `tests/test_depreciation.py` (depreciation engine)

Estimated addition: ~400 tests, ~30s.

#### Extended CI (PR + main push, allow up to 5 minutes)
Add the named engine test files that aren't in Fast CI:
- All `tests/test_depreciation*.py` (non-disabled)
- All `tests/test_tax*.py` (non-disabled)
- All `tests/test_shl*.py`
- `tests/test_waterfall_*.py`
- `tests/test_loss_carryforward_*.py`
- `tests/test_senior_debt*.py` (non-disabled)
- `tests/test_financial_formulas.py`
- `tests/test_xirr.py`, `tests/test_period_engine.py`
- Stack parity files (all 21)

Estimated: ~2,000 tests, ~60s.

#### Nightly
- All non-browser tests excluding phase characterization
- Catches breakage in the 99% of tests not in Fast/Extended CI
- Target: < 10 minutes, accept occasional phase-test noise

#### Browser CI (separate workflow, requires Playwright)
- All `*_browser.py` files
- Requires: `pip install playwright && playwright install chromium`
- Static fixture tests only for PR CI; full live-server tests for nightly/staging

#### Phase characterization (optional / advisory)
- `tests/test_phase*.py` — no CI pipeline required
- These are informational history, not quality gates
- Run locally with `pytest tests/test_phase*.py` for historical investigation

### Recommended `pytest.ini` marker additions

The following markers are defined in this stack to support selective test execution:

```
pytest -m "engine"      # Core engine tests
pytest -m "parity"      # Golden parity tests
pytest -m "browser"     # Browser tests (requires playwright)
pytest -m "legacy"      # Skip these — legacy/disabled
pytest -m "not browser" # Everything except browser tests
```

---

## AA8 — Low-Value Test Removal

### Criteria (all four must be met)
1. Obsolete — tests behaviour that no longer exists
2. Duplicated — covered by a current maintained test
3. No longer validates behaviour — only history
4. Fully documented here

### Removed in this stack

**None.** After careful review, no test files meet ALL four criteria unambiguously without risk of removing genuine invariant coverage.

Rationale:
- The calibration-disabled files (Group 2) are already skipped — they have zero CI cost.
- The core-legacy files (Group 1) are already skipped — zero CI cost.
- The phase characterization files are not "duplicated" — they pin historical states that may re-emerge as regression signals.
- Git-diff-style tests (Pattern 1) are stale but harmless; removing them offers no CI benefit since they are not run in CI.

### Near-term removal candidates (future stacks)

The following files are strong candidates for deletion in a future stack, subject to explicit sign-off:

| File | Why | Risk |
|------|-----|------|
| `tests/test_phase9_5_excel_like_project_workspace_ui_design.py` | Asserts doc files exist — docs since evolved | Low |
| `tests/test_phase10_calibration_reconciliation_pack.py` | Requires `openpyxl` + calibration reports; tests no runtime behaviour | Low |
| `tests/test_phase10_human_readable_calibration_workbook.py` | Same | Low |
| `tests/test_phase10_institutional_workbook_skeleton.py` | Same | Low |
| Phase 9–12 "file existence" tests (bulk) | No runtime behaviour | Low |

**These are NOT removed here.** They are documented for a future cleanup stack.

---

## Retained Tests — Explicit Confirmation

### Confirmed retained (no changes)

| Category | Files | Justification |
|----------|-------|---------------|
| All stack/parity tests | 21 | Golden parity; CI-protected |
| All core engine named tests | ~200 | Active financial regression coverage |
| All phase 51 tests | 35 | Route/API characterization; Phase 51F in CI |
| All phase 52–57 tests | ~200 | Recent; partially in CI |
| All browser tests | 39 | Self-skip when Playwright absent; environment gap not product defect |
| All UI component tests | 32 | Non-browser; markup contract |
| All golden/ tests | 1 | Golden validation |
| All integration/ tests | 5 | Integration coverage (2 skip due to calibration/core) |
| test_persistence.py | 1 | Quarantined in-file; tracked by CI sentinel |
| test_repository.py | 1 | Quarantined in-file; tracked by CI sentinel |
| All `_CALIBRATION_DISABLED_FILES` | 15 | Skipped in conftest; retained for calibration revival |
| All `CORE_LEGACY_TEST_FILES` | 12 | Skipped in conftest; retained for core revival |

---

## Known Technical Debt

1. **19,200 tests not in CI.** The majority of the test suite has no CI home. This is the primary technical debt item.

2. **git-diff tests are permanently stale.** 205 phase tests assert `git diff` shows specific changes. These comparisons are relative to historical SHAs and may produce misleading results locally.

3. **`app.calibration` is disabled.** 15 test files are silently skipped. The calibration workflow is not tested in CI at all.

4. **Browser tests have no CI home.** 39 files, 647 tests — all skip in CI. A dedicated Playwright job would catch UI regressions.

5. **Flat test directory.** 877 files at `tests/` root makes navigation difficult. The migration plan in AA6 addresses this.

6. **`pytest.ini` and `pyproject.toml` both define test configuration.** `pytest.ini` takes precedence. Both files should be reconciled.

---

## Engineering Recommendations

### Immediate (this stack)
1. ✅ Add marker definitions to `pytest.ini` for: `engine`, `parity`, `browser`, `legacy`
2. ✅ Document the test suite census and categories in this file
3. ✅ Confirm zero production code changes

### Next stack (AA-followup)
1. Create `tests/legacy/` directory; move 29 disabled files
2. Expand Fast CI to include stack parity tests and core engine named tests
3. Add a `browser` CI workflow with Playwright installed

### Medium term
1. Add Extended CI job covering ~2,000 core engine tests
2. Add nightly job covering all non-browser, non-phase tests
3. Migrate `tests/parity/` and `tests/browser/` directories

### Long term
1. Complete directory restructure per AA6 proposal
2. Evaluate phase test archival (move to `tests/phase/` read-only)
3. Re-enable `app.calibration` or delete calibration test files

---

## Guardrails Confirmed

- ✅ Zero production code changes
- ✅ Zero financial logic changes
- ✅ Zero parity test changes
- ✅ No Golden parity tests removed
- ✅ No invariant tests removed
- ✅ No financial regression tests removed
- ✅ CI remains green (all 5 jobs pass)
