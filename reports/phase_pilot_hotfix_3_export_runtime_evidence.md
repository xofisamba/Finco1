# Phase PILOT-HOTFIX-3 — Export uses latest successful runtime evidence

> **Status:** DRAFT (not yet merged)
> **Branch:** `phase/pilot-hotfix-3-export-runtime-evidence`
> **Base:** main @ `11b2e5a07e76bdd87a7cc2b9b0212d496fa92b8c` (post PILOT-HOTFIX-2)
> **Type:** runtime fix for export boundary
> **Stop-after-report:** Do NOT mark ready, do NOT merge before review

---

## 1. TL;DR

PILOT-HOTFIX-2 fixed P0 #1 (scenario overrides in `/run`). P0 #2
remained: `POST /download` for a working copy with a successful
run could fail HTTP 400 with "Current form state no longer matches
the last saved runtime boundary" when the user had edited the form
after the run.

PILOT-HOTFIX-3 makes `POST /download` for `user_created` projects
honour `workspace_state.last_runtime_snapshot` (the latest
successful run evidence) when present, and return a clear
"Run the model before exporting." error when no run exists yet.

The fix is a single-service-layer change in
`app/services/download_service.py` (no `repository.py`, no
`main_web.py`, no factory, no engine change).

11 new tests pass; 121/121 Phase 51E1/51E2 download route tests
still pass; 87/87 PILOT-HOTFIX-2 + 51F + 23s + S1-A + S1-C tests
still pass; Engine MD5 + Factory MD5 + rc1 SHA unchanged.

---

## 2. Constraints honoured

- ✅ rc1 SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4` verified
  unchanged
- ✅ Engine MD5 `6bf49f33efc989736c17cea0cb9b7723` unchanged
- ✅ Factory MD5 `cf73065b8a26aa3f19629829e46260d9` unchanged
- ✅ `app/persistence/repository.py` UNCHANGED (P1 file-scope
  constraint)
- ✅ No financial formula / debt / tax / sponsor / construction /
  R99 / R102 / G20 / waterfall change
- ✅ No persistence schema change
- ✅ No static/app.js change
- ✅ TUHO / Oborovo frozen-schedule parity preserved bit-identical
- ✅ `use_construction_schedule_engine` remains `False`
- ✅ `manual_gearing` debt sizing method NOT introduced

---

## 3. Files changed

| File | Status | Lines | Purpose |
|---|---|---|---|
| `app/services/download_service.py` | M | +42 / -10 | Service-layer fix for export boundary |
| `tests/test_phase_pilot_hotfix_3_export_runtime_evidence.py` | A | +761 / -0 | 11 tests across 7 classes + file-scope guard |
| `docs/phase_pilot_hotfix_3_export_runtime_evidence.md` | A | +250 / -0 | Design + validation doc |
| `reports/phase_pilot_hotfix_3_export_runtime_evidence.md` | A | this file | Walkthrough + results |

Total: **2 source files** (1 modified, 1 added) + **2 doc files**.

---

## 4. Live walkthrough (post-fix, on this branch)

A new working copy of TUHO Wind 1 was created. The form was
submitted with the Base scenario (tariff 75), then with a Downside
scenario (override tariff 50). Export requests were issued with
form snapshots that intentionally differed from the saved runtime
boundary (stale tariff, stale `scenario_id`).

| Project | Scenario | Form tariff | Last-runtime tariff | `POST /download` status |
|---|---|---|---|---|
| TUHO Wind 1 (Copy) | Base | 99.0 (stale) | 75.0 | **HTTP 200, 39,544 bytes** |
| TUHO Wind 1 (Copy) | Downside | 75.0 (stale) | 50.0 | **HTTP 200, 39,269 bytes** |
| TUHO Wind 1 (Copy) | (no runtime) | n/a | n/a | **HTTP 400** "Run the model before exporting" |
| TUHO Wind 1 (Copy) | (no runtime, hostile `scenario_id`) | 50.0 | n/a | **HTTP 400** "Run the model before exporting" (cross-project blocked) |
| TUHO reference | Base | 75.0 | (factory) | **HTTP 200** (unchanged) |
| Oborovo reference | Base | 75.0 | (factory) | **HTTP 200** (unchanged) |

### 4.1 Pre-fix reproduction (for contrast)

Same walkthrough before the fix produced:

| Project | Scenario | Form tariff | Last-runtime tariff | `POST /download` status |
|---|---|---|---|---|
| TUHO Wind 1 (Copy) | Base | 99.0 (stale) | 75.0 | **HTTP 400** "Current form state no longer matches..." |
| TUHO Wind 1 (Copy) | Downside | 75.0 (stale) | 50.0 | **HTTP 400** "Current form state no longer matches..." |
| TUHO Wind 1 (Copy) | (no runtime) | n/a | n/a | **HTTP 400** (same boundary message, misleading) |

The runtime was ignoring the workspace's own runtime evidence
because the export service required the current form snapshot to
bit-match the saved runtime boundary, even though export only
needs the last successful runtime result.

---

## 5. Test coverage (11 new tests, all pass)

`tests/test_phase_pilot_hotfix_3_export_runtime_evidence.py`:

| Test class | Tests | Purpose |
|---|---|---|
| T1 | 1 | Working copy after Base run exports POST /download HTTP 200 with XLSX |
| T2 | 1 | Working copy after Downside run exports HTTP 200; override tariff (50) used, stale form (75) ignored |
| T3 | 1 | Working copy after Downside run exports XLSX HTTP 200 (XLSX magic bytes) |
| T4 | 1 | Working copy with no runtime returns clear "Run the model before exporting" error (no traceback, no boundary message) |
| T5 | 1 | Export uses only the working copy's own runtime (not TUHO reference) |
| T6 | 1 | TUHO reference export unchanged (factory path untouched) |
| T7 | 1 | Oborovo reference export unchanged (factory path untouched) |
| T8 | 1 | Cross-project scenario_id cannot be used to extract another project's runtime |
| T9 | 1 | Engine MD5 `6bf49f33efc989736c17cea0cb9b7723` unchanged |
| T10 | 1 | rc1 SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4` ancestor preserved |
| File-scope | 1 | Only `app/services/download_service.py` + test + docs/report changed |

---

## 6. Adjacent suite results (all preserved)

- 11/11 PILOT-HOTFIX-3 tests pass
- 11/11 PILOT-HOTFIX-2 tests pass
- 21/21 Phase 51F parity guardrails pass
- 9/9 Phase 23s combined frozen-schedule parity tests pass
- 20/20 S1-A export tests pass
- 26/26 S1-C factory-resolver consistency tests pass
- 121/121 Phase 51E1 / 51E2 download route golden + vertical
  extraction tests pass

---

## 7. Pre-existing failures (NOT regressions of this PR)

8 pre-existing test failures (25B4 dirty state, 25B4 factory
safety, 25B6 review template) + 12 pre-existing TestClient errors
(missing `httpx2`) were present on `origin/main` before this PR
and are out of scope.

---

## 8. Stop-after-report contract

This PR is the **runtime-boundary fix for `POST /download`** for
user-created projects. Do **NOT** mark ready, do **NOT** merge
before review.

The remaining pilot-walkthrough issues (P1 #1, P1 #2, etc.)
remain explicitly out of scope and require separate analysis and
PRs.
