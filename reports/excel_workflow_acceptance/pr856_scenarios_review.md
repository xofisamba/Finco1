# PR #856 — Scenarios Excel Matrix Cleanup: Acceptance Review

**Branch:** `claude/festive-cerf-uaq5hb`
**PR:** https://github.com/xofisamba/Finco1/pull/856
**Date:** 2026-07-10
**Reviewer:** Claude Code (automated browser verification)

---

## Checklist

| # | Item | Result |
|---|------|--------|
| 1 | Protected project read-only state | ✅ PASS |
| 2 | User-created scenario behavior (add-form, ondblclick) | ✅ PASS |
| 3 | "Scenario Assumptions" banner present | ✅ PASS |
| 4 | "Scenario Outputs" banner present | ✅ PASS |
| 5 | "Live project values" sub-label on Base Case column | ✅ PASS |
| 6 | Downside / Upside / Custom column sub-labels | ✅ PASS |
| 7 | Override indicator (▲) on overridden cells | ✅ PASS (test-verified) |
| 8 | Empty KPI cells render as `—` | ✅ PASS |
| 9 | No engine / math / persistence / schema changes | ✅ PASS |
| 10 | No CAPEX / OPEX / Inputs / Revenue changes | ✅ PASS |
| 11 | Alias map unchanged | ✅ PASS |
| 12 | Browser screenshots taken | ✅ PASS (6 screenshots) |
| 13 | Dark theme renders correctly | ✅ PASS |
| 14 | 30 Jinja2 tests all green | ✅ PASS |

---

## Browser Evidence

Screenshots in `reports/excel_workflow_acceptance/screenshots_pr856/`.

### 01 — TUHO (protected) — Scenarios tab, scrolled mid

`01_protected_full.png`

Visible: KPI Outputs table (Base Case / Downside / Upside / Custom with sub-labels),
Scenario Assumptions banner with "PROTECTED ORIGINAL" badge, Base Case column
with "Live project values" sub-label, no Add Scenario form.

### 06 — Top of Scenarios tab (key verification screenshot)

`06_top_of_tab.png`

Visible top-to-bottom:
- **"SCENARIO OUTPUTS"** banner with green left-rail and note "Headline model results — read-only. Run the model to refresh."
- KPI table: Base Case (bold, tinted) | Downside Scenario 1 | Upside Scenario 2 | Custom Scenario 3
- "Live project values" sub-label under Base Case header
- Revenue 323,640 kEUR, EBITDA 242,584 kEUR, Project IRR 7.33%, Equity IRR 9.04%, etc.
- Empty scenario columns show `—`
- **"SCENARIO ASSUMPTIONS"** banner with accent left-rail and "PROTECTED ORIGINAL" badge

### 03 — Assumptions matrix scrolled

`03_assumptions_matrix.png`

Visible: Section groups (IDENTITY, SCHEDULE, TECHNICAL, REVENUE / PPA, CAPEX SUMMARY, OPEX SUMMARY, FINANCING), all business-readable labels, Base Case column with tinted background, no editable inputs.

### 05 — Dark theme

`05_dark_theme.png`

Same layout in dark mode — top bar, KPI table, and Scenario Assumptions banner all render correctly with correct contrast.

---

## DOM Verification (automated, Playwright)

```
Outputs banner:      'SCENARIO OUTPUTS\nHeadline model results — read-only. Run the model to refresh.'
Assumptions banner:  'SCENARIO ASSUMPTIONS\nPROTECTED ORIGINAL Read-only — use Create Working Copy to add or edit scenarios.'
Add form count:      0  (correct — protected project, no Add Scenario form)
ondblclick present:  False  (correct — no editable cells in protected project)
'Live project values' in DOM:  True
'Scenario Outputs' in DOM:     True
'Scenario Assumptions' in DOM: True
'Protected original' in DOM:   True
```

---

## Out-of-scope / not changed

| Area | Status |
|------|--------|
| CAPEX grid (`sheet_capex_grid.html`) | Unchanged |
| OPEX grid (`sheet_opex_grid.html`) | Unchanged |
| Inputs section (`inputs_section.html`) | Unchanged |
| Revenue / Financial Statements | Unchanged |
| Scenario engine / math (`scenario_matrix.py`) | Unchanged |
| Persistence / schema / run endpoints | Unchanged |
| Alias map (`_SC_ALIAS_TO_CANONICAL`) | Unchanged |
| `SCENARIO_EDITABLE_FIELDS` names and labels | Unchanged |

---

## Test Results

```
tests/test_scenarios_excel_matrix.py    30 passed
tests/test_inputs_control_tower.py      39 passed
tests/test_sheet_opex_grid.py           44 passed
```

---

## Known cosmetic issue (pre-existing, out of scope)

Total CAPEX in the assumptions matrix shows raw float `72993.70999999999999` from `base_input_set`. This is a display formatting issue in `scenario_matrix.py` / `effectiveValue()` macro that predates PR #856 and should be addressed in a separate PR.

---

## Verdict

All acceptance criteria pass. PR #856 is ready for review and merge.
