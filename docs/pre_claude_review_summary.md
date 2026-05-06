# Pre-Claude Review Summary — post-rc1-structure-roadmap

_Generated: 2026-05-06 | Updated: 2026-05-06 (stabilization pass)_

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

**Stabilization pass (this update) fixes:**
- Dashboard DSCR display: was showing sculpted DSCR (1.32×) instead of actual DSCR (1.44×); now corrected to `actual_min_dscr` / `actual_avg_dscr` in `app/ui/pages.py`.
- Excel export `project_type`: was always defaulting to "Solar" in Notes sheet; now correctly passed from `streamlit_app.py`.
- Duplicate `import pandas as pd` inside scenario table block removed.

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

**Wired to waterfall as of 2026-05-06.**

- `CapexLineItem` dataclass with `code`, `name`, `group`, `amount_keur`, `asset_class`, `timing_profile`, `timing_fractions`
- `generate_capex_schedule()` per-year draws with ELEVATED, UPFRONT, ANNUITY, CUSTOM profiles
- CAPEX matrix UI in CapEx tab — users can edit line items
- `build_capex_line_items_from_defaults()` per project type (Solar/Wind)
- **Runtime integration complete:** `capex_line_items` from UI → `run_demo_project()` → `waterfall_core` → total CAPEX override applied

**Note:** Default CapexLineItem totals (84,850 kEUR for 50MW Solar) differ from factory defaults (30,700 kEUR) — this is intentional as the line-item engine models a more granular cost build-up. Users see the higher total when Advanced CAPEX is active.

---

## 5. Scenario Status

**ScenarioManager is the active runtime engine as of 2026-05-06.**
`app/scenarios.apply_scenario()` is preserved for backward compatibility.

**ScenarioManager (now active):**
- `Scenario` dataclass: `name`, `description`, `is_base`, `revenue/opex/capex_multiplier`, `debt_sculpting_override`, `annual_generation_hours`
- `ScenarioManager`: per-project-type registry, `apply_overrides()` returns deep copy
- Solar/Wind: Base/Downside/Upside defined (revenue -5%/+3%, capex +5%/-3%, opex +10%/-5%)
- BESS fallback: Base only
- **Integrated:** `ScenarioManager.apply_overrides()` called in `run_demo_project()` for Solar/Wind non-Base scenarios

**Multiplier reconciliation (2026-05-06):** Both engines now use the same values.

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

1. **BESS partial model** — revenue-only, no full waterfall
2. **Sponsor IRR placeholder** — not yet implemented
3. **Portfolio IRR experimental** — do not use for investment decisions
4. **No FX conversion** — single currency assumption
5. **Debt sculpting override** — defined in ScenarioManager but not connected to scenario selector UI
6. **CAPEX matrix totals differ from factory defaults** — CapexLineItem defaults (84,850 kEUR for 50MW Solar) vs factory (30,700 kEUR); intentional but users may notice

**Resolved (2026-05-06):**
- CAPEX matrix now wired to waterfall — UI edits affect IRR/DSCR/distributions
- ScenarioManager now active runtime engine — multiplier divergence resolved

---

## 10. Recommended Next Roadmap

1. **BESS full waterfall** — complete waterfall integration for BESS/hybrid
2. **Sponsor IRR** — implement equity IRR computation
3. **Debt sculpting UI** — connect `ScenarioManager.debt_sculpting_override` to scenario selector
4. **CAPEX matrix alignment** — consider aligning CapexLineItem default totals with factory defaults (or document the gap for users)

---

## 11. Technical Debt

| Item | Severity | Notes |
|------|----------|-------|
| CAPEX matrix totals vs factory | Medium | CapexLineItem defaults (84,850 kEUR) vs factory (30,700 kEUR); intentional but may confuse users
| BESS partial waterfall | Medium | Revenue-only mode; full model in progress |
| Sponsor IRR placeholder | Medium | Excel export shows placeholder; not investment-ready |
| OPEX doesn't respond to DSCR | Low | Debt-sculpting-aware OPEX not modeled |
| No FX conversion | Low | Single currency; EUR-only assumption |
| Portfolio pooling | Low | Experimental; marked 🔬 |
| Debt sculpting override | Low | Defined in ScenarioManager but not connected to UI selector |

---

## 12. Branch Readiness

**Is the branch ready for a Claude review?**

**Yes — with known limitations documented.**

This stabilization pass fixed three runtime bugs found during smoke-testing:
1. **Dashboard DSCR**: was displaying sculpted target (1.32×) instead of actual realised DSCR (1.44×); now correct.
2. **Excel export project_type**: was always "Solar" in Notes sheet regardless of actual project type; now passed correctly.
3. **Duplicate import**: removed spurious `import pandas as pd` inside scenario table rendering block.

**All remaining limitations are documented** in `docs/known_limitations.md`:
- BESS/hybrid partial — documented with ⚠️ status
- Sponsor IRR placeholder — documented with ⏳ label
- Portfolio IRR experimental — documented with 🔬 label

**Test status:** `pytest tests/ -x -q` → **1003 passed, 1 xfailed**

**Resolved this session (2026-05-06):**
- CAPEX matrix → waterfall integration: `capex_line_items` from UI now flows through `run_demo_project()` → `waterfall_core` → total CAPEX override applied. Changing Amount in CAPEX matrix visibly changes IRR/DSCR.
- ScenarioManager migration: `ScenarioManager.apply_overrides()` now drives runtime scenarios. Multiplier values reconciled to match legacy engine (-5%/+3% for revenue, +10%/-5% for opex, +5%/-3% for capex).
- Excel export CAPEX warning: Notes sheet now includes "Advanced CAPEX: Manual values present" when `capex_line_items` have `is_manual=True`.

---

## Appendix: File Inventory (this branch + stabilization pass)

```
app/capex_engine.py             — NEW: CapexLineItem + generate_capex_schedule()
app/scenario_manager.py         — NEW: Scenario dataclass + ScenarioManager (foundation)
app/ui/pages.py                 — MODIFIED: CAPEX matrix UI + DSCR display fix
docs/ARCHITECTURE.md           — NEW: full architecture documentation
docs/known_limitations.md      — NEW: supported scope, experimental, partials, placeholders
streamlit_app.py                — MODIFIED: project_type passed to excel_export + import cleanup
tests/test_capex_engine.py     — NEW: 259 lines, full schedule coverage
tests/test_scenario_manager.py — NEW: 236 lines, ScenarioManager unit tests
```
