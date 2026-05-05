# Pre-Claude Review Summary — post-rc1-structure-roadmap

_Generated: 2026-05-06_

---

## 1. What Changed Since RC1 (commit range)

**HEAD = 359a65f** — last 5 commits on this branch:

| Commit | Description |
|--------|-------------|
| `821af1e` | STEP 5 — docs: Add ARCHITECTURE.md documenting OPEX/CAPEX engines, scenario_manager, Advanced OPEX UX flow, known limitations |
| `b9e2510` | STEP 4 — scenario_manager: Scenario dataclass + ScenarioManager class |
| `8fa27ac` | feat(capex): CAPEX matrix UI for Solar/Wind in CapEx tab |
| `58fd88e` | feat(capex): CAPEX line-item engine foundation |

**Summary:** This branch adds the CAPEX line-item engine (`app/capex_engine.py`) and the ScenarioManager foundation (`app/scenario_manager.py`), plus documentation. It does NOT modify the waterfall, debt sculpting, or portfolio holding logic.

---

## 2. Current Architecture Overview

```
streamlit_app.py (UI)
        │
        ▼
app/ui_runner.py  ← run_demo_project()
        │
        ├── app/scenarios.apply_scenario()  ← LEGACY ACTIVE SCENARIO ENGINE
        │
        ├── domain/period_engine.py
        │
        ├── domain.portfolio_runner / industry_engine
        │
        └── app.waterfall_runner.run()
```

**Active scenario engine:** `app/scenarios.apply_scenario()` — legacy path with Base/Downside/Upside multipliers (P50, CapEx, OpEx, Degradation, Tariff).

**Foundation layer (inactive):** `app/scenario_manager.ScenarioManager` — clean scenario registry and override application. Not yet wired into `run_demo_project()`. This is the planned migration target.

**CAPEX status:** `app/capex_engine.py` provides `CapexLineItem` and `generate_capex_schedule()`. The CapEx matrix UI is wired in the CapEx tab (`app/ui/pages.py`). However, `capex_line_items` from the UI is **not yet passed to `run_demo_project()`** — the runtime still uses `project_inputs.capex` from the project factory defaults. CAPEX matrix edits are a UI-only feature at this stage.

---

## 3. OPEX Status

**Working:** Advanced OPEX line-item engine is functional end-to-end.

- `OpexLineItem` dataclass with `manual_overrides_keur`, `is_hardcoded`, `override_note`
- `generate_opex_schedule()` handles INFLATED_FROM_BASE, MANUAL_SCHEDULE, MIXED modes
- Shadow styled preview highlights amber override cells
- `last_advanced_opex_signature` diffing triggers reruns
- `run_demo_project()` receives `advanced_opex_line_items` and uses them in the waterfall

**Limitations:**
- No debt-sculpting-aware OPEX (OPEX doesn't respond to DSCR target changes)
- Inflation compounding is simple uniform rate; no tiered inflation
- OPEX matrix doesn't save back to `project_inputs.opex` after editing (stateless within session)

---

## 4. CAPEX Status

**Foundation layer: COMPLETE — not wired to waterfall.**

- `CapexLineItem` dataclass with `code`, `name`, `group`, `amount_keur`, `asset_class`, `timing_profile`, `timing_fractions`
- `generate_capex_schedule()` per-year draws with ELEVATED, UPFRONT, ANNUITY, CUSTOM profiles
- CAPEX matrix UI in CapEx tab — users can edit line items
- `build_capex_line_items_from_defaults()` per project type (Solar/Wind)

**Not yet connected:**
- UI-edited `capex_line_items` are NOT passed to `run_demo_project()`
- `generate_capex_schedule()` output is NOT fed into the waterfall's CAPEX inputs
- The waterfall still uses `project_inputs.capex` from project factories
- CAPEX matrix → waterfall integration is pending

---

## 5. Scenario Status

**Legacy active:** `app/scenarios.apply_scenario()` drives scenario selection in `run_demo_project()`.

**ScenarioManager (foundation, not integrated):**
- `Scenario` dataclass: `name`, `description`, `is_base`, `revenue/opex/capex_multiplier`, `debt_sculpting_override`, `annual_generation_hours`
- `ScenarioManager`: per-project-type registry, `apply_overrides()` returns deep copy
- Solar/Wind: Base/Downside/Upside defined (0.85x/1.10x/1.05x rev/opex/capex for Downside; 1.15x/0.95x/0.97x for Upside)
- BESS fallback: Base only
- **Migration pending:** ScenarioManager not yet wired into `run_demo_project()`

**Multiplier comparison:**

| Axis | Legacy (scenarios.py) | ScenarioManager |
|------|----------------------|-----------------|
| Revenue/Tariff | Downside -5%, Upside +3% | Downside -15%, Upside +15% |
| OPEX | Downside +10%, Upside -5% | Same |
| CapEx | Downside +5%, Upside -3% | Same |
| P50 Hours | Downside -10%, Upside +5% | Not defined (uses annual_generation_hours override) |
| Degradation | Downside +15%, Upside -10% | Not included |

**Note:** The two engines use different multiplier values for revenue/tariff. This will need reconciliation during ScenarioManager migration.

---

## 6. Export Status

- `app/excel_export.py` — ZIP archive with formatted Excel output
- Sponsor IRR shows "placeholder" label
- CAPEX sheet matches `CapexItem` structure from `domain/inputs.py`

---

## 7. Validation Status

- `domain/validation.py` — `validate_project_inputs()`, `warn_model_unrealistic()`
- Validation run on every `run_demo_project()` call
- `validation_issues` surfaced in UI via `render_validation_panel()`
- 1003 tests pass, 1 xfailed

---

## 8. Runtime Cleanup Status

**Phase 1 (Runtime Stabilization):** ✅ PASSED
- `python3 -c "import streamlit_app; print('OK')"` → `OK`
- `pytest tests/ -x -q` → **1003 passed, 1 xfailed**

**Phase 2 (Scenario Architecture):** ✅ documented
- Legacy `app/scenarios.apply_scenario()` is active runtime
- `ScenarioManager` is foundation layer, not yet integrated
- ARCHITECTURE.md updated accordingly

**Phase 3 (State Management):** ✅ No cleanup needed
- `_opex_sig` vs `_last_opex_sig` naming: intentional dual-key pattern (line 49 vs 56/59 in streamlit_app.py)
- No duplicate/stale session state keys detected
- No debug/print statements left in

---

## 9. Known Weaknesses

1. **CAPEX matrix not wired to waterfall** — UI edits don't affect model results
2. **ScenarioManager not integrated** — legacy scenario engine is still active
3. **Revenue multiplier divergence** — legacy uses -5%/+3%, ScenarioManager uses -15%/+15% (needs reconciliation)
4. **BESS partial model** — revenue-only, no full waterfall
5. **Sponsor IRR placeholder** — not yet implemented
6. **Portfolio IRR experimental** — do not use for investment decisions
7. **No FX conversion** — single currency assumption
8. **Debt sculpting override** — defined in ScenarioManager but not connected to scenario selector UI

---

## 10. Recommended Next Roadmap

1. **Wire CAPEX matrix → `run_demo_project()`** — pass `capex_line_items` to waterfall runner; update `waterfall_run_config` to use `generate_capex_schedule()` output
2. **Migrate scenario engine** — replace `app/scenarios.apply_scenario()` with `ScenarioManager.apply_overrides()` in `run_demo_project()`; reconcile multiplier values first
3. **BESS full waterfall** — complete waterfall integration for BESS/hybrid
4. **Sponsor IRR** — implement equity IRR computation
5. **Debt sculpting UI** — connect `ScenarioManager.debt_sculpting_override` to scenario selector

---

## 11. Technical Debt

| Item | Severity | Notes |
|------|----------|-------|
| CAPEX matrix UI-only | High | Edits don't affect model; waterfall still uses factory defaults |
| ScenarioManager not integrated | High | Two diverging scenario engines with different multiplier values |
| Revenue multiplier mismatch | Medium | Legacy -5%/+3% vs ScenarioManager -15%/+15% — must reconcile before migration |
| BESS partial waterfall | Medium | Revenue-only mode; full model in progress |
| Sponsor IRR placeholder | Medium | Excel export shows placeholder; not investment-ready |
| OPEX doesn't respond to DSCR | Low | Debt-sculpting-aware OPEX not modeled |
| No FX conversion | Low | Single currency; EUR-only assumption |
| Portfolio pooling | Low | Experimental; marked 🔬 |

---

## 12. Branch Readiness

**Is the branch ready for a Claude review?**

**No.** The branch is not ready for Claude review due to:

1. **CAPEX matrix is UI-only** — the most user-visible new feature (the CapEx tab matrix) has no effect on model results. This is a significant disconnect that would be confusing in review.

2. **ScenarioManager divergence** — the two scenario engines use different revenue/tariff multipliers. Any reviewer will flag this as an inconsistency. The migration should land first (or at minimum the reconciliation decision should be documented).

3. **No functional change to core model** — the branch adds foundation infrastructure but the actual runtime behavior is unchanged for the end user. A review at this stage would evaluate scaffolding without the payoff.

**Recommendation:** Land the ScenarioManager migration (unify multipliers + wire into `run_demo_project()`) and wire CAPEX matrix to waterfall runner, then request review.

---

## Appendix: File Inventory (this branch)

```
app/capex_engine.py            — NEW: CapexLineItem + generate_capex_schedule()
app/scenario_manager.py        — NEW: Scenario dataclass + ScenarioManager (foundation)
app/ui/pages.py                — MODIFIED: CAPEX matrix UI added
docs/ARCHITECTURE.md          — NEW: full architecture documentation
streamlit_app.py               — MODIFIED: session state key hygiene (no functional change)
tests/test_capex_engine.py    — NEW: 259 lines, full schedule coverage
tests/test_scenario_manager.py — NEW: 236 lines, ScenarioManager unit tests
```
