# Phase 51F — Parallel-work and runtime-refactor guardrails

## Why these guardrails are needed before /save-run and parallel work

Phase 50/51 + 51E-2 are now complete. main_web.py is materially
reduced. The next major route, `POST /save-run`, is
**runtime-persistence sensitive**: it touches behavior such as
`record_workspace_runtime` and
`update_scenario_last_run_summary`. Before extracting or
characterizing it further, we need to lock down the things that
/save-run must not accidentally change.

Concretely, the risks are:

1. **Silent model regression** during refactor.
   /save-run uses the same waterfall engine as /run, /compare,
   /download. Any change to the engine (waterfall_core.py,
   project_factories.py, senior debt schedule CSVs) that shifts
   distributions / DSCR / OpEx would silently break every
   downstream route, not just /save-run.

2. **Two agents working in parallel.**
   Going forward, we want to support an "Agent A extracts routes"
   + "Agent B docs/validation" split. Without explicit guardrails:
   - Agent A could regress parity-core files that Agent B depends
     on for validation golden values.
   - Agent B could update parity-core files as part of "validation
     cleanup" without coordination.

3. **Import-direction drift.**
   The Phase 51 architecture established a one-way import
   direction: services are leaf modules that may not pull in
   main_web. If a service starts importing main_web, the deps
   bundle pattern breaks and routes couple back to services.

This phase adds three guardrails that protect against all three
risks. They are **behavior-level** (not call-count), survive
refactors, and fail only if the model output, parity-core content,
or import direction actually changes.

## What each guardrail protects

### Guardrail 1 — Engine-output golden
**Test class:** `TestEngineOutputGoldenTUHO` /
`TestEngineOutputGoldenOborovo` (10 tests)

Pins current model outputs (DSCR, first distribution period, total
operating periods, OpEx total, OpEx Y1) for TUHO and Oborovo. A
refactor of routes/services must not change these. Only an
intentional model change updates them.

### Guardrail 2 — Parity-core lock
**Test class:** `TestParityCoreLock` (4 parametrized tests, one
per locked file)

Pins SHA-256 of parity-sensitive files. Any unintended edit to
these files triggers the test.

### Guardrail 3 — No-service-imports-main_web/main_api
**Test class:** `TestNoServiceImportsMainWebOrMainApi` (1 AST test
across all app/services/*.py)

AST-walks each service file. Fails on `import main_web`,
`from main_web import ...`, `import main_api`,
`from main_api import ...`. Docstrings and comments mentioning
"extracted from main_web" are ALLOWED — only actual import
statements are checked.

## Exact golden values pinned

### TUHO (Wind 1, 35 MW × 5 turbines)
| Field | Golden | Tolerance | Description |
|---|---|---|---|
| First finite DSCR | 1.450695 | ±0.001 | Period idx 0, year 1 |
| First distribution op idx | 35 | exact | First op period with positive distribution_keur |
| Total operating periods | 61 | exact | Semiannual, 30y + construction overhang |
| OpEx total | 85408.27 kEUR | ±0.5 kEUR | Sum over operating periods |
| OpEx year 1 (semiannual sum) | 1998.01 kEUR | ±0.5 kEUR | First 2 operating periods |

### Oborovo (Solar PV, 75.26 MWp)
| Field | Golden | Tolerance | Description |
|---|---|---|---|
| First finite DSCR | 1.150038 | ±0.001 | Period idx 0, year 1; matches target_dscr=1.15 |
| First distribution op idx | 39 | exact | First op period with positive distribution_keur |
| Total operating periods | 60 | exact | Semiannual, 30y + construction overhang |
| OpEx total | 48847.50 kEUR | ±0.5 kEUR | Sum over operating periods |
| OpEx year 1 (semiannual sum) | 1338.56 kEUR | ±0.5 kEUR | First 2 operating periods |

DSCR tolerance is intentionally tight (0.001) to catch silent
regressions. OpEx tolerance (0.5 kEUR) absorbs micro-floating-point
drift in the summation but still catches any meaningful change.

Integer fields (first distribution op idx, total op periods) are
exact — they are structural, not floating-point.

## Exact parity-core files locked

The following 4 files are locked via SHA-256 content hash. They
govern model parity (waterfall core, project factories) and
Excel-extracted senior debt schedules for the two golden
reference projects.

| File | SHA-256 |
|---|---|
| `app/waterfall_core.py` | `d8ab56fdb5c01847be605f68a3710c14ddf91f097db86a107e2073eebff21a63` |
| `app/project_factories.py` | `1b795b96bfaf3e2795d6e5c389c447cd8c157de720e13ebab0484949b387258a` |
| `reports/phase7_tuho_senior_debt_sizing_extraction.csv` | `80e79977f039310158b084e2613ae17251a86916b970d4fda1985467bbde3442` |
| `reports/phase23q_oborovo_senior_debt_sizing_extraction.csv` | `8afdad21025df890b2103c73e40423bb6e4a99f755a94c9fec7b68f1cc3f58f6` |

The locked file inventory itself is asserted by
`TestGuardrailInventory::test_parity_core_files_inventory_is_frozen`.

## How to update hashes / goldens intentionally

**These are NOT bumps you do as part of a refactor PR.** They are
bumps you do as part of a **dedicated, intentional model-change
PR**.

1. Open a dedicated PR with title pattern
   `Phase XX: <what model change>` (e.g. `Phase 52: New DSCR
   sculpting policy`).
2. In the PR body, document:
   - What changed in the model / parity-core file.
   - Why the change is correct (Excel alignment, sponsor review
     sign-off, etc.).
   - Old vs new golden values.
3. In the same PR, update:
   - The `GOLDEN_TUHO` / `GOLDEN_OBOROVO` dicts in
     `tests/test_phase51f_parallel_work_guardrails.py`.
   - The `PARITY_CORE_FILES` SHA-256 dict in
     `tests/test_phase51f_parallel_work_guardrails.py`.
   - This docs file's `Exact golden values pinned` and `Exact
     parity-core files locked` tables.
4. Run `python -m pytest tests/test_phase51*.py` and confirm
   357+ (pre-Phase-51F) + 15 (Phase 51F) = ≥372 passed.
5. **Never** update a hash as part of an unrelated refactor PR
   (route extraction, service extraction, scenario state, etc.).

If a refactor PR triggers a parity-core hash mismatch, that is a
**blocker**, not a thing to paper over. The refactor must be
adjusted so the parity-core file is unchanged.

## Merge protocol for two agents

When Agent A and Agent B work in parallel:

1. **Branch ownership is exclusive.** See `File ownership rules`
   below. Agent A may not touch `docs/` or `reports/`. Agent B
   may not touch `main_web.py` or `app/services/`.
2. **Parity-core files are off-limits to both agents** unless
   the work is explicitly approved as a model-change PR.
3. **Each agent rebases against `main` daily** (or before
   pushing any commit). The guardrails will catch a divergence
   caused by the other agent.
4. **If a guardrail fails on Agent A's branch after a rebase
   from main:**
   - Check the diff: did Agent B (or anyone else) touch a
     parity-core file?
   - If yes, escalate: which model change made it through?
   - If no, the failure is on Agent A — adjust the refactor.
5. **PR ordering:** when merging, the model-change PR (if any)
   merges FIRST. Then Agent A and Agent B PRs can merge in any
   order. A parity-core hash bump that was not yet on main will
   fail Agent A's CI; this is a feature, not a bug.

## File ownership rules

| Owner | May write | May not write |
|---|---|---|
| **Agent A (route extraction)** | `main_web.py`, `app/services/`, `tests/test_phase51*.py` (route/service tests), `docs/phase51*.md`, `reports/phase51*.json` | parity-core files (4 locked), `app/templates/`, `app/static/` (UI track owns) |
| **Agent B (docs/validation)** | `docs/`, `reports/`, `tests/test_*validation*.py`, `tests/golden/` | `main_web.py`, `app/services/`, `app/templates/`, `app/static/`, parity-core files |
| **UI track** | `app/templates/`, `app/static/`, `tests/test_*ui*.py` | `main_web.py`, `app/services/`, parity-core files. UI track may NOT add new route context fields (those would require Agent A). |

Parity-core files (4 locked) must not be touched by either agent
unless explicitly approved as a model-change PR.

`rc1` remains frozen (not touched by any Phase 51 commit, including
Phase 51F).

## Test commands and current results

| Command | Result |
|---|---|
| `python -m pytest tests/test_phase51f_parallel_work_guardrails.py` | 15 passed (engine output × 10, parity lock × 4, no-service-imports × 1) |
| `python -m pytest tests/test_phase51*.py` | 357 + 15 = 372 passed |
| CI on PR: `python -m pytest tests/test_phase51f_parallel_work_guardrails.py` | green, ~30s |

## Simulated failures (proof each guardrail actually fails)

To be performed and reverted before commit (see PR body for
results):

1. **No-service-imports guardrail:** temporarily add
   `import main_web` to one of `app/services/*.py` →
   `test_all_services_have_no_main_web_or_main_api_imports` fails.
2. **Parity-core hash guardrail:** temporarily modify
   `app/waterfall_core.py` (e.g. add a comment line) → SHA-256
   changes → `test_parity_core_file_sha256[app/waterfall_core.py-...]`
   fails.
3. **Senior debt CSV hash guardrail:** temporarily modify
   `reports/phase7_tuho_senior_debt_sizing_extraction.csv` (e.g.
   add a trailing newline) → SHA-256 changes →
   `test_parity_core_file_sha256[reports/phase7_tuho_senior_debt_sizing_extraction.csv-...]`
   fails.

All three must be reverted before commit.

## Guardrails preserved

- No financial formula changes.
- No model output changes (golden outputs ARE the model).
- No fixture CSV changes, except temporary local simulation
  reverted before commit.
- No schema/migration changes.
- No JavaScript financial calculations.
- No runtime flag promotions.
- G20 remains BLOCKED.
- R99/R102 remain NOT APPROVED.
- partial_pay_sweep remains not promoted.
- flat/min DSCR sculpting remains not promoted.
- Generic solar/wind remain exploratory and unvalidated.
- No lender/bank/audit/certification/SaaS claims.
- Backend remains source of truth.
- rc1 remains frozen.
- PR #299 remains closed (no longer active guardrail).
- /run, /compare, /validate, /download routes from Phases 51A–51E-2
  remain intact.

## Recommended next phase

**Phase 51G-1** — Golden characterization of `POST /save-run`
(behavior + parity pinning). This is a guardrail/test phase
similar to 51E-1 but for the runtime-persistence-sensitive
/save-run route. It captures the exact call sequence
(record_workspace_runtime, update_scenario_last_run_summary,
record_compare_run if any) and locks it.

**Phase 51G-2** — Extract /save-run route family into
`app/services/save_run_service.py` (similar to 51B/51C-2/51D-2/51E-2).

Both phases inherit the Phase 51F guardrails and use them to catch
any silent regression during /save-run extraction.
