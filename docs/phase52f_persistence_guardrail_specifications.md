# Phase 52F — Persistence Guardrail Specifications

**Base SHA:** `bff3e9846e0b71e0b5b06378390ffd0e2ad28a53` (post-52E main)
**Phase:** 52F — guardrail specifications + safe-to-implement tests
**Type:** docs/report/test only (with non-invasive structural guardrail tests)
**Status:** SPEC + safe tests implemented. No runtime code changes. No refactor.

## 1. Scope

This document specifies the structural guardrails that should be in place **before** Phase 53 begins. It identifies which guardrails are safe to implement now, which are deferred to Phase 53+ (because they are brittle or require runtime behavior change), and what the exact failure conditions are for each.

The guardrails are organized into:
- **G1–G6 (implemented now):** non-invasive, no false-positive risk on formatting changes, fail only on clear boundary violations
- **D1–D4 (deferred):** would be brittle, or require runtime behavior change, or have no stable source yet

## 2. Current guardrail inventory

| Guardrail | Source | Status |
|---|---|---|
| Engine-output golden (TUHO + Oborovo) | `tests/test_phase51f_parallel_work_guardrails.py` (TestEngineOutputGoldenTUHO + TestEngineOutputGoldenOborovo) | active, 6 tests |
| Parity-core lock (4 SHA-256 files) | `tests/test_phase51f_parallel_work_guardrails.py` (TestParityCoreLock) | active, 4 tests |
| No-service-imports-main_web/main_api | `tests/test_phase51f_parallel_work_guardrails.py` (TestGuardrailDocsCrossCheck + NoServiceImportsMainWeb) | active, 6 tests |
| Phase 51 doc cross-check | `tests/test_phase51f_parallel_work_guardrails.py` (TestGuardrailDocsCrossCheck) | active, 5 tests |
| **Total Phase 51F** | | **21 tests** |

## 3. Proposed new guardrails

### 3.1 G1 — No direct sqlite3 / SQLAlchemy imports outside app/persistence/*

- **What it checks:** no `import sqlite3` or `from sqlalchemy import ...` (or `peewee`, `pymongo`, `psycopg2`) outside `app/persistence/*`
- **Why:** the persistence layer is the single choke point. A direct DB-API import in `main_web.py` or in a service would bypass the choke point and split transactional behavior across modules.
- **Implementation:** `tests/test_phase52f_persistence_guardrail_regression.py::TestG1NoDirectDbImportsOutsidePersistence` (2 parametrized tests)
- **Failure condition:** any `import sqlite3` or `from sqlalchemy` line in `app/` outside `app/persistence/`
- **False-positive risk:** **none** (string match on full import line; doesn't trigger on `sqlite3` mentioned in docstrings or comments)
- **Required before Phase 53:** yes (Group F–J all preserve the choke point)
- **Owner:** Phase 52 (this PR)

### 3.2 G2 — No service imports main_web or main_api (re-affirm Phase 51F)

- **What it checks:** no `import main_web` or `from main_web import ...` (or `main_api`) in any `app/services/*.py`
- **Why:** services exist to be the narrowing layer between routes and persistence. A reverse import would couple them back to the route layer and undermine Phase 51's architecture.
- **Implementation:** `tests/test_phase52f_persistence_guardrail_regression.py::TestG2NoServiceImportsMainWebOrApi` (2 tests)
- **Failure condition:** any `import main_web` or `from main_api` line in `app/services/*.py`
- **False-positive risk:** **none** (string match on import line; doesn't trigger on `main_web` mentioned in comments)
- **Required before Phase 53:** yes
- **Owner:** Phase 52 (this PR, complements the existing 51F guardrail)

### 3.3 G3 — No sqlite3.Connection / sqlite3.connect instantiation outside app/persistence/*

- **What it checks:** no `sqlite3.Connection(...)` or `sqlite3.connect(...)` call outside `app/persistence/*`
- **Why:** even if `import sqlite3` is allowed (e.g. for type hint), actually instantiating a connection outside the choke point would bypass the transactional contract.
- **Implementation:** `tests/test_phase52f_persistence_guardrail_regression.py::TestG3NoDirectConnectionInstantiationOutsidePersistence` (1 test)
- **Failure condition:** any `sqlite3.Connection(` or `sqlite3.connect(` call in `app/` outside `app/persistence/`
- **False-positive risk:** **none** (regex on actual call, not on type hint)
- **Required before Phase 53:** yes
- **Owner:** Phase 52 (this PR)

### 3.4 G4 — No service or route imports get_cursor directly

- **What it checks:** no usage of `get_cursor` outside `app/persistence/*`
- **Why:** `get_cursor` is the transactional choke point. It must only be used inside `app/persistence/*` to preserve the contract that all writes go through a single function.
- **Implementation:** `tests/test_phase52f_persistence_guardrail_regression.py::TestG4NoServiceImportsGetCursor` (1 test)
- **Failure condition:** any `get_cursor` token in `app/` outside `app/persistence/`
- **False-positive risk:** **low** (string match; would only trigger if someone uses `get_cursor` as a variable name outside persistence, which is unlikely)
- **Required before Phase 53:** yes
- **Owner:** Phase 52 (this PR)

### 3.5 G5 — repository.py has the single-transaction pattern

- **What it checks:** `app/persistence/repository.py` uses the single-transaction `with get_cursor()` pattern: imports `get_cursor`, no explicit `cur.commit()` or `cur.flush()` calls, at least 20 `with get_cursor()` blocks
- **Why:** the 52B side-effect map established that all 15 write functions use a single `with get_cursor() as cur:` block per function call. A regression here (e.g. nested transactions, explicit commits) would break the transactional contract that Phase 53 will preserve.
- **Implementation:** `tests/test_phase52f_persistence_guardrail_regression.py::TestG5RepositorySingleTransactionPattern` (3 tests)
- **Failure conditions:** missing `from app.persistence.db import get_cursor`; any `cur.commit(` or `cur.flush(`; fewer than 20 `with get_cursor()` blocks
- **False-positive risk:** **none** (AST-level checks)
- **Required before Phase 53:** yes
- **Owner:** Phase 52 (this PR)

### 3.6 G6 — Services use public surface of repository only

- **What it checks:** no service imports a private (underscore-prefixed) function from `app.persistence.repository`
- **Why:** the public surface of `app.persistence.repository` is the documented contract. A service importing a private function (e.g. `_compute_baseline_snapshot`) would couple to internal implementation details that Phase 53 may move.
- **Implementation:** `tests/test_phase52f_persistence_guardrail_regression.py::TestG6ServicesUsePublicSurfaceOnly` (1 test)
- **Failure condition:** any `from app.persistence.repository import _name` in `app/services/*.py`
- **False-positive risk:** **none** (regex on full import line)
- **Required before Phase 53:** yes
- **Owner:** Phase 52 (this PR)

## 4. Deferred guardrails

The following guardrails are **deferred to Phase 53+** because they would be brittle, or require runtime behavior change, or have no stable source yet.

### 4.1 D1 — Route no-refattening

- **What it would check:** that `main_web.py` route bodies don't grow beyond their post-Phase-51 baseline
- **Why deferred:** the route body size baseline is sensitive to inline comments, blank lines, and the way docstrings are counted. A regression test that checks "no route > N non-blank lines" would be brittle. The Phase 51T hotspot map documents the current baseline (0 routes > 30 non-blank) and that should be re-checked after each Phase 53 PR.
- **Recommended approach:** add a manual checkpoint test in 53G (Group C) and 53J (Group B) that re-runs the hotspot count and fails if it grows.

### 4.2 D2 — Service-count / no-new-service-without-justification

- **What it would check:** that the service count stays at the current baseline (18 services, post-Phase 50d)
- **Why deferred:** a count-only check is brittle (any new service triggers a failure, even if the service is legitimate). A justification check is too opinionated. The Phase 50d closeout already documents the baseline.
- **Recommended approach:** add a soft check in 53F (Group A-2) that the service count is 18 ± 0 unless an explicit justification PR adds a new one.

### 4.3 D3 — UI context key contract

- **What it would check:** that all `request.context` / template context keys have stable names
- **Why deferred:** the context surface is large (10+ route templates) and the key names are not documented in a single place. Building the contract requires a separate Phase 51-style documentation pass.
- **Recommended approach:** defer to Phase 54 (after the persistence layer is split).

### 4.4 D4 — Docs no-go scanner

- **What it would check:** that newly-introduced docs don't include forbidden no-go claims (lender-ready, bankable, audit/certified, SaaS-ready, etc.)
- **Why deferred:** the docs surface is large and a regex-based scanner would have high false-positive risk. The current no-go claims are documented in the user prompt and re-stated in each Phase 5x/5y closeout.
- **Recommended approach:** defer to Phase 54+ (after the docs surface is reduced).

## 5. Implemented-now vs deferred summary

| Guardrail | Status | Tests | Owner |
|---|---|---:|---|
| G1 — no direct sqlite3/sqlalchemy imports outside persistence | **implemented** | 2 | Phase 52F |
| G2 — no service imports main_web or main_api | **implemented** | 2 | Phase 52F |
| G3 — no sqlite3.Connection/connect instantiation outside persistence | **implemented** | 1 | Phase 52F |
| G4 — no service or route imports get_cursor directly | **implemented** | 1 | Phase 52F |
| G5 — repository.py has the single-transaction pattern | **implemented** | 3 | Phase 52F |
| G6 — services use public surface of repository only | **implemented** | 1 | Phase 52F |
| D1 — route no-refattening | **deferred** | (manual) | Phase 53G/53J |
| D2 — service-count / no-new-service-without-justification | **deferred** | (soft) | Phase 53F |
| D3 — UI context key contract | **deferred** | none | Phase 54 |
| D4 — docs no-go scanner | **deferred** | none | Phase 54+ |
| **Total implemented-now** | | **10** | |

## 6. Required before Phase 53

All 6 implemented guardrails (G1–G6) are required to pass before Phase 53 begins. They are not new tests added in the same PR as the Phase 53 refactor; they are added in Phase 52F and verified at the start of each Phase 53 PR.

## 7. Required before Phase 54

D3 (UI context key contract) is the only deferred guardrail that should be in place by Phase 54.

## 8. False-positive risk analysis

| Guardrail | False-positive risk | Mitigation |
|---|---|---|
| G1 | none | matches full import line only |
| G2 | none | matches full import line only |
| G3 | none | matches `sqlite3.Connection(` call only |
| G4 | low | matches token `get_cursor` only; would only trigger on unusual variable name use |
| G5 | none | AST-level checks on specific patterns |
| G6 | none | matches underscore-prefixed symbols in `from app.persistence.repository import ...` lines only |

## 9. Recommended next step

**Phase 52G — Phase 52 closeout and Phase 53 launch plan.** Close Phase 52 with a final report and prepare a precise Phase 53 launch plan.
