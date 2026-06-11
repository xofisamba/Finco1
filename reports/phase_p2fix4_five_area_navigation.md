# Phase P2-FIX-4 — Final Report

**Branch:** `p2-fix-4-five-area-nav`
**Base:** `main` @ `510db16` (post P2-FIX-2)
**Type:** presentation / navigation cleanup only
**Status:** DRAFT (PR #618 pending)

---

## Summary

Reduced the 20-tab workspace ribbon to a 5-area navigation
model:

1. Dashboard
2. Inputs
3. Results (with sub-nav for 13 output sheets)
4. Scenarios
5. Export & Audit (+ Help secondary)

All 20 underlying `ws-tab` buttons are preserved
(hidden != deleted). The compressed view is enabled for
EVERY project (not just user_created). The Dashboard is
the new default landing tab.

---

## Files changed

| File | Status | Lines |
|---|---|---|
| `app/templates/partials/_nav_compression.html` | MODIFIED | +35 / -23 |
| `app/templates/partials/_results_subnav.html` | NEW | +91 / -0 |
| `app/templates/partials/_dashboard.html` | MODIFIED | +37 / -0 |
| `app/templates/partials/workspace_shell.html` | MODIFIED | +4 / -0 |
| `app/ui/dashboard.py` | MODIFIED | +15 / -0 |
| `main_web.py` | MODIFIED | +18 / -3 |
| `tests/test_phase_p2fix4_five_area_navigation.py` | NEW | +575 / -0 |
| `docs/phase_p2fix4_five_area_navigation.md` | NEW | +250 / -0 |
| `reports/phase_p2fix4_five_area_navigation.md` | NEW | +180 / -0 |

---

## Tests (24 PASS, 1 SKIP, 0 FAIL)

| Test class | Count | Verifies |
|---|---|---|
| `TestFiveAreaNavigation` | 5 | 5 main nav tabs render for TUHO, Oborovo, Generic. Help secondary link preserved. 17 underlying ws-tab buttons still in DOM. |
| `TestDashboardDefault` | 5 | Dashboard renders for all 3 project types. Default active = Dashboard. Run CTA + run-status chip present. KPI grid + chart grid referenced. |
| `TestResultsSubNavigation` | 3 | 13 sub-nav buttons present, call existing switchTab. |
| `TestNormalModeNegative` | 4 | Workspace, Inputs, Scenarios, CAPEX sheet — no forbidden terms in normal mode. |
| `TestPriorBehaviorPreserved` | 7 | P2-FIX-1 default route, P2-FIX-2 audit tab, P2-FIX-3 first-edit (SKIPPED, gated on P2-FIX-3 merge), export / compare / scenario routes still work. |
| `TestFileScope` | 1 | Only allowed files changed. |

**Total: 24 PASS, 1 SKIP, 0 FAIL (2 consecutive runs identical).**

### Pre-existing test suites still pass
- `tests/test_phase_p2fix2_shell_strip.py` — **25 / 25 PASS**
- `tests/test_phase51f_parallel_work_guardrails.py` — **21 / 21 PASS**

**Grand total: 70 / 70 PASS, 1 SKIP (2 consecutive runs).**

---

## Hard constraints preserved

- ✅ rc1 SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4` preserved
- ✅ TUHO parity netaknut
- ✅ Oborovo parity netaknut
- ✅ `use_construction_schedule_engine` = False
- ✅ No formula / debt / DSCR / tax / IDC / construction / R-PAR / C10 / R99 / R102 / G20 promotion changes
- ✅ No destructive persistence migration
- ✅ No `static/app.js` changes (0 lines diff)
- ✅ No `main_api.py` changes
- ✅ No route / CSS class / context-key / project_origin renames
- ✅ No new dependencies
- ✅ No Tailwind / Alpine / React / Vue / Svelte
- ✅ No Chart.js / Plotly / D3
- ✅ `factory_template` / `saved_baseline` literals still in `app/persistence/` (hidden != deleted)
- ✅ Frozen senior debt schedule unchanged (fixture-backed)
- ✅ Excel goldens unchanged

---

## P2-FIX arc status

1. P2-FIX-1 — MERGED @ `c8564fa` (PR #615)
2. P2-FIX-2 — MERGED @ `510db16` (PR #616)
3. P2-FIX-3 — DRAFT #617 (head `23ae0bf`; awaiting merge)
4. P2-FIX-4 — DRAFT (this PR)

`manual_gearing` is NOT on this roadmap.

---

## Stop-after-report

- ✅ PR #618 is DRAFT, not marked ready, not merged
- ✅ No P2-FIX-5 work started
- ✅ No other arc work started
