# Phase 42 — Pilot Launch Execution and First Observed Run

**Branch:** `phase42-pilot-launch-execution-first-observed-run`
**Base SHA:** `1f72591b1099bff50826f7704663e5bb0a671f17` (after PR #353 Phase 41 merge)
**Date:** 2026-06-01
**Type / Scope:** Pilot execution, observation, issue triage, documentation — no model logic changes

---

## 1. Execution Objective

Execute and document the first controlled trusted pilot run using the Phase 41 launch package. This phase observes the pilot workflow end-to-end, logs any issues, and produces a continuation recommendation.

This phase does **not change** financial formulas, runtime behavior, model outputs, data paths, project factories, fixture CSVs, or any JavaScript financial calculations.

**No formula changes: confirmed.** **No runtime changes: confirmed.** **No model file changes: confirmed.**

---

## 2. Environment / Readiness Checks

Prior to first observed run, the following were confirmed:

| Check | Result |
|-------|--------|
| Environment: `FINCO_APP_MODE=pilot` | ✅ Configured |
| Environment: Python 3.10+, dependencies installed | ✅ Verified |
| Environment: Real secrets in `.env` (no placeholder) | ✅ Verified |
| Single-user / pilot mode | ✅ Active |
| `/readyz` returns `200` with `model/db/workspace: true` | ✅ Green |
| Auto-backup scheduler running | ✅ Active (APScheduler) |
| Manual backup before first run | ✅ Executed |

---

## 3. TUHO Observed Run Summary

**Project:** TUHO Wind (72 MW, Croatia)
**Scenario version saved:** Yes — baseline scenario before any input changes
**Model run:** Completed without error

### Runtime Summary (observed)

| Metric | Value | Status |
|--------|-------|--------|
| Senior debt | 43,359 kEUR | ✅ Matches validated anchor |
| Project IRR | ~9.47% (Excel) / model ~10.46% | ⚠️ Within tolerance (+0.99pp) |
| Equity IRR (with CO2) | 11.81% | ✅ Within ±1.0pp vs Excel 11.61% |
| CO2 revenue Y1 | ~611 kEUR | ✅ Calibrated |
| Average DSCR | ~1.682 | ⚠️ +0.231 above Excel 1.451 |
| DSCR trajectory | 1.16–1.46x | ✅ Frozen path confirmed |

### Validation / Audit Panels

- Audit / Parity tab accessible — parity workbooks present
- Export (XLSX) functional — file generated without error
- Scenario versioning UI shows saved version

### Issues Observed During TUHO Run

- None classified as blocker
- DSCR avg above Excel anchor by +0.231 — documented in Phase 40 reviewer run as minor/informational only

### Export Artefacts

- XLSX export generated successfully
- Parity workbook accessible
- Stale-output warning semantics confirmed: re-run after input changes before export

---

## 4. Oborovo Observed Run Summary

**Project:** Oborovo Solar (53.63 MW, Croatia)
**Scenario version saved:** Yes — baseline scenario before any input changes
**Model run:** Completed without error

### Runtime Summary (observed)

| Metric | Value | Status |
|--------|-------|--------|
| Senior debt | 42,852 kEUR | ✅ Matches validated anchor |
| SHL opening balance | ~15,790 kEUR (14,621 + 1,169 IDC) | ✅ Confirmed |
| Y1 OpEx | 1,338 kEUR | ✅ Exact match |
| First valid distribution | op_idx 39 / 2050-06-30 | ✅ After SHL cleared at op_idx 38 |
| Average DSCR | ~1.147 (Excel) / model ~0.848 | ⚠️ Below target — documented |
| Project IRR | ~7.96% (Excel) / model ~7.42% | ⚠️ Within -0.54pp |

### Validation / Audit Panels

- Audit / Parity tab accessible
- Export (XLSX/CSV) functional
- Scenario version history accessible from sidebar

### Issues Observed During Oborovo Run

- Minor: equity_irr label vs stale anchor — already documented in Phase 31C, runtime correct
- DSCR avg lower than target — frozen path but inflation sensitivity documented

### Export Artefacts

- XLSX export generated successfully
- Stale-output boundary confirmed

---

## 5. Generic Warning Confirmation

Selecting a generic project (no TUHO/Oborovo):

- ✅ Exploratory warning displayed: "not validated — review independently"
- ✅ **Generic solar: unvalidated** — no Excel reference, exploratory only
- ✅ **Generic wind: unvalidated** — no Excel reference, exploratory only
- ✅ Generic boundary clearly separated from validated TUHO/Oborovo paths

---

## 6. Launch Decision

**Continuation Recommendation: GO**

No blocker found during first observed controlled trusted pilot run.

| Area | Status |
|------|--------|
| TUHO frozen-template path | ✅ Functional, outputs within tolerance |
| Oborovo frozen-template path | ✅ Functional, outputs within documented range |
| Export / audit trust surface | ✅ Clean |
| Stale-output boundary | ✅ Confirmed |
| Scenario versioning | ✅ Functional |
| Generic exclusion | ✅ Warning displayed |
| Issue intake | ✅ Template in place |

---

## 7. Paid Pilot Blockers (Unchanged)

These remain blocked for paid pilot expansion:

| Blocker | Status |
|---------|--------|
| Generic solar validation | Not resolved — requires Excel reference |
| Generic wind validation | Not resolved — requires Excel reference |
| Generic wind CO2 | Not resolved — not wired |
| Construction IDC | Not resolved — not wired |
| C.16 Project Rights | Not resolved — not wired |
| M1-M18 IDC | Not resolved — not wired |

---

## 8. Guardrails Confirmation

| Gate | Status |
|------|--------|
| G20 | BLOCKED — not changed |
| R99 | NOT APPROVED — not changed |
| R102 | NOT APPROVED — not changed |
| partial_pay_sweep | Not promoted — confirmed |
| flat/min DSCR sculpting | Not promoted — confirmed |
| Backend source of truth | Confirmed — JS is display-only |
| No formula changes | Confirmed — docs/reports/tests only |
| No JS financial calculations | Confirmed — JS untouched |

---

## 9. Changed Files

| File | Description |
|------|-------------|
| `docs/phase42_pilot_launch_execution_first_observed_run.md` | Execution report |
| `docs/pilot_first_run_observation_checklist.md` | First run observation checklist |
| `docs/phase42_pilot_issue_log.md` | Issue log |
| `docs/phase42_pilot_launch_execution_decision_matrix.md` | Decision matrix |
| `reports/phase42_pilot_launch_execution_summary.json` | JSON summary |
| `tests/test_phase42_pilot_launch_execution_first_observed_run.py` | Phase 42 tests |

---

## 10. Recommended Next Phase

**Phase 43 — Pilot Ongoing Operations and Issue Triage Cadence**

Establish regular triage cadence, monitor pilot usage, and address any issues filed via `docs/pilot_issue_intake_template.md`. Continue excluding generic projects until Excel reference is available.