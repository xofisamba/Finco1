# Repository Cleanup Inventory

**Purpose:** Visibility into stale vs. active files before deletion.
**Scope:** All non-code files (`.md`, `.txt`, `.xlsx`, `.xlsm`, `.csv`, `.json`, `.rst`, `.log`, `.html`) outside `.git`, `.venv`, `__pycache__`.
**Policy:** No files deleted in this sprint. Classifications are for planning only.

---

## Completed in this sprint (2026-05-04)

### Moved to `docs/archive/`
- `docs/FINCOGPT_EXCEL_PARITY_PLAN.md` → `docs/archive/`
- `docs/FINCOGPT_CALIBRATION_STATUS.md` → `docs/archive/calibration/`
- `docs/EXCEL_UX_AND_CALIBRATION_MAPPING.md` → `docs/archive/calibration/`
- `SPRINT*.md`, `SPRINT_BACKLOG.md`, `SPRINT4_BACKLOG.md` → `docs/archive/legacy_prompts/`

### Not deleted (still referenced by tests)
- `tests/fixtures/current_outputs.json` — referenced by `tests/test_regression.py`
- `tests/fixtures/oborovo_base.json` — referenced by `tests/test_inputs.py`
- `tests/fixtures/oborovo_baseline.json` — referenced by `tests/test_regression.py`, `tests/test_oborovo_parity.py`
- `tests/fixtures/oborovo_golden.json` — referenced by `tests/integration/test_fid_deck_excel.py`

### Pre-existing test failure (not caused by this sprint's actions)
- `tests/test_bess_hybrid_full_flow.py::test_sponsor_irr_not_computed` — `TypeError: FinancingParams.__init__() got an unexpected keyword argument 'total_debt_keur'` — existed before cleanup

---

## Summary

| Category | Count | Notes |
|---|---|---|
| KEEP_CURRENT | 4 | Active architecture/manifest docs |
| MOVE_TO_DOCS | 4 | Misplaced docs from repo root |
| ARCHIVE_LEGACY | 8 | Calibration/Oborovo-specific artifacts |
| DELETE_CANDIDATE | 4 | Generated/stale outputs in repo root |
| NEEDS_REVIEW | 3 | Referenced by tests or unclear purpose |

---

## KEEP_CURRENT

| Path | Reason | Runtime refs | Test refs |
|---|---|---|---|
| `docs/CODEX_HANDOFF_FINCOGPT.md` | Architecture/hand-off doc | None | None |
| `docs/EXCEL_UX_AND_CALIBRATION_MAPPING.md` | Design mapping | None | None |
| `docs/FINCOGPT_MODEL_FILE_MANIFEST.md` | Model manifest | None | None |
| `docs/FINCOGPT_CALIBRATION_STATUS.md` | Calibration status | None | None |

---

## MOVE_TO_DOCS

| Path | Reason | Runtime refs | Test refs |
|---|---|---|---|
| `SPRINT*.md` (root level) | Historical sprint reports from root | None | None |
| `SPRINT_BACKLOG.md` | Sprint planning | None | None |

---

## ARCHIVE_LEGACY

| Path | Reason | Runtime refs | Test refs |
|---|---|---|---|
| `oborovo_comparison.xlsx` | Oborovo-specific Excel artifact | None | test fixture |
| `docs/FINCOGPT_EXCEL_PARITY_PLAN.md` | Calibration plan | None | None |
| `tests/fixtures/excel_calibration_targets.json` | Calibration targets | None | None |
| `tests/fixtures/excel_golden_oborovo.json` | Oborovo golden results | None | None |
| `tests/fixtures/excel_golden_tuho.json` | TUHO golden results | None | None |
| `tests/fixtures/excel_oborovo_*.json` (2 files) | Oborovo extracts | None | None |
| `tests/fixtures/excel_tuho_*.json` (2 files) | TUHO extracts | None | None |
| `scripts/run_calibration.py` | Legacy calibration runner | `tools.calibration_legacy` | None |
| `tools/calibration_legacy/` (entire dir) | Legacy calibration tools | Legacy only | None |
| `app/calibration.py` | Shim → legacy | Legacy only | None |
| `app/calibration_runner.py` | Shim → legacy | Legacy only | None |
| `app/project_factories.py::create_default_oborovo` | Oborovo factory | `app/project_factories` | `test_period_day_fractions.py` |

---

## DELETE_CANDIDATE

| Path | Reason | Runtime refs | Test refs |
|---|---|---|---|
| `tests/fixtures/current_outputs.json` | Generated output, likely stale | None | None |
| `tests/fixtures/oborovo_base.json` | Duplicate fixture | None | None |
| `tests/fixtures/oborovo_baseline.json` | Duplicate fixture | None | None |
| `tests/fixtures/oborovo_golden.json` | Duplicate fixture | None | None |

---

## NEEDS_REVIEW

| Path | Reason | Runtime refs | Test refs |
|---|---|---|---|
| `tests/fixtures/tuho_wind1_golden.json` | TUHO fixture | None | Likely test fixture |
| `tests/test_period_day_fractions.py` | Uses `ProjectInputs.create_default_oborovo` | `domain.inputs` (broken) | Yes — test uses broken legacy call |
| `SPRINT4_BACKLOG.md` | Sprint backlog from root | None | None |

---

## High-risk items (do not delete without manual review)

1. **`tests/test_period_day_fractions.py`** — References broken `ProjectInputs.create_default_oborovo()`. Tests may be testing period fraction logic using Oborovo dates. Needs review before any change.

2. **`app/calibration.py`** and **`app/calibration_runner.py`** — These are shim files that redirect to `tools.calibration_legacy`. They exist to prevent import errors if anything references them. Deleting them would break `tools/calibration_legacy/run_calibration.py` and `scripts/run_calibration.py`.

3. **`tools/calibration_legacy/`** — Entire directory. References `ProjectInputs.create_default_oborovo()`. Used by `scripts/run_calibration.py`. Must remain until that script is explicitly deprecated.

4. **`tests/fixtures/excel_golden_*.json`** — These are calibration result files. They may be referenced by test code that validates Excel export parity. Must check before deletion.

---

## Files containing prohibited strings

The following files contain patterns that must be flagged for removal or cleanup:

| File | Prohibited content |
|---|---|
| `app/calibration.py` | `tools.calibration_legacy` |
| `app/calibration_runner.py` | `tools.calibration_legacy` |
| `scripts/run_calibration.py` | `tools.calibration_legacy`, `create_default_oborovo` |
| `tools/calibration_legacy/` | Multiple legacy references |
| `app/project_factories.py` | `create_default_oborovo` (legacy compatibility stub) |
| `tests/test_period_day_fractions.py` | `ProjectInputs.create_default_oborovo` |
| `/root/.openclaw` paths | None found in runtime (sandbox paths removed in previous sprints) |

---

## Suggested cleanup PR plan

**Stage 1 — Move docs** (low risk)
```
mkdir -p docs/archive/  # move old sprint reports here
git mv SPRINT*.md docs/archive/
git mv SPRINT_BACKLOG.md docs/archive/
git mv SPRINT4_BACKLOG.md docs/archive/
```

**Stage 2 — Isolate legacy calibration** (medium risk)
```
# Archive calibration files but keep them importable
mkdir -p tools/archive_calibration_legacy/   # future cleanup
# Do NOT delete tools/calibration_legacy/ yet
```

**Stage 3 — Remove generated outputs** (after confirming no runtime/test references)
```
# Delete only after confirming tests/fixtures don't reference them:
# - tests/fixtures/current_outputs.json
# - tests/fixtures/oborovo_base.json
# - tests/fixtures/oborovo_baseline.json
# - tests/fixtures/oborovo_golden.json
```

**Stage 4 — Fix test_period_day_fractions.py**
```
# Replace ProjectInputs.create_default_oborovo with generic factory
# Requires understanding what dates are being tested
```

**Stage 5 — Deprecate shim files** (after confirming no active imports)
```
# app/calibration.py and app/calibration_runner.py
# Add deprecation warnings and mark for removal in next sprint
```

---

## Notes

- `app/project_factories.create_default_oborovo` and `create_default_tuho_wind1` are **not broken** — they exist as compatibility stubs in `app/project_factories.py`. They are used by `tools/calibration_legacy/` and are acceptable to keep as long as runtime guard tests don't flag them in active runtime paths.
- Runtime import guards in `tests/test_runtime_import_guards.py` already check for `ProjectInputs.create_default_oborovo` in runtime paths.
- `tools/calibration_legacy/` is isolated and does not import from `app/` or `domain/` runtime paths.
