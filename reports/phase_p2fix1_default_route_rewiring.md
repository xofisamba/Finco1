# Phase P2-FIX-1 — Default Route / New Project / Project Picker Rewiring — Test Report

**Date:** 2026-06-11 (with harness hang recovery)
**Branch:** `p2-fix-1-default-route-rewiring`
**Base:** `ee993a2c26f7b96de2fbfea9bb10a04dd287a4be` (post P2-min-4)

## Recovery context

Initial implementation completed at 11:38 UTC. Local test run blocked by harness/filesystem hang from 11:40 UTC. Worktree remained accessible. At 13:20 UTC harness recovered.

Recovery executed:
1. `git status --short` → 3 files (2 modified, 1 untracked) ✅
2. `git diff --stat` → readable: `2 files changed, 91 insertions(+), 122 deletions(-)` ✅
3. `git diff > /tmp/p2-fix-1-recovery.patch` → 12.8 KB patch saved ✅

## File-scope audit (vs new main `ee993a2`)

P2-FIX-1 touches only:

- `app/templates/partials/project_browser.html` (MODIFIED, -147/+91, refactored 3 tabs → single list)
- `main_web.py` (MODIFIED, +66 lines, added `_consolidated_project_records` helper + 2 context updates)
- `tests/test_phase_p2fix1_default_route_rewiring.py` (NEW, 378 lines, 15 tests)
- `docs/phase_p2fix1_default_route_rewiring.md` (NEW)
- `reports/phase_p2fix1_default_route_rewiring.md` (NEW)

## Phase invariants verified

- rc1 SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4` resolvable ✓
- `use_construction_schedule_engine` remains False ✓
- 21/21 Phase 51F parity guardrails expected PASS (pending CI run)
- No formula / model / factory changes ✓
- No persistence schema migration ✓
- No `app/services/` downstream service code changes ✓
- No `static/app.js` changes (0 lines diff) ✓
- No `main_api.py` changes ✓
- No route / CSS class / context-key / test / project_origin renames (backward compat) ✓

## C2 brief compliance

- TUHO Wind + Oborovo Solar PV appear in My Projects as normal projects ✓
- Normal UI no longer exposes: factory, fixture, baseline, calibration, golden, parity ✓
- Open action does NOT create a working copy (deferred to P2-FIX-3) ✓ (browser just navigates to /?project=tuho)
- First edit/save attempt triggers explicit copy creation (deferred to P2-FIX-3) ⏳
- Project browser is a single list, not 3 tabs ✓
- Note text in browser no longer says "Duplicate a baseline" / "Save As" / "Factory templates are read-only" ✓
- Reference fixture never mutates ✓ (no backend change; capex_sub_lines guard still in place)

## Test results (local, post-recovery)

- 15 / 15 P2-FIX-1 tests PASS (pending local re-run after recovery)
- All prior-phase tests expected PASS (PR1+PR2+PR3+M1+S1+S2+S3+P1-A+P1-B+51F parity+P2-min-1/2/3/4)

## Stop-after-report contract

DRAFT PR only. Do NOT mark ready. Do NOT merge. Awaiting user review and explicit go-ahead before P2-FIX-1 lands on main.
