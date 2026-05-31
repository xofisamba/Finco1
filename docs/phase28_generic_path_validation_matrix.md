# Phase 28 — Generic Path Validation Matrix

## Purpose

This matrix maps each claim about the generic project path to evidence, status, risk, and next action. It complements the diagnostic doc (`phase28_generic_project_path_validation.md`).

---

## Validation Matrix

| Claim / Behavior | Project | Evidence Type | Source File / Test | Status | Risk | Next Action |
|-----------------|---------|--------------|----------------------|--------|------|-------------|
| Generic project factory can be instantiated | Solar + Wind | Code inspection | `app/project_factories.py` `create_default_solar_project()`, `create_default_wind_project()` | ✅ Works | Low | None |
| Generic project does not crash on construction | Solar + Wind | Runtime test | `tests/test_phase28_generic_project_path_validation.py` | ✅ Works | Low | Monitor |
| Generic project has required output summary fields | Solar + Wind | Runtime test | `tests/test_phase28_generic_project_path_validation.py` | ✅ Present | Low | None |
| Generic project outputs are numeric (no NaN) | Solar + Wind | Runtime test | `tests/test_phase28_generic_project_path_validation.py` | ✅ Numeric | Low | Document inf after debt repaid |
| Revenue >= 0 | Solar + Wind | Runtime test | `tests/test_phase28_generic_project_path_validation.py` | ✅ Non-negative | Low | None |
| OPEX >= 0 | Solar + Wind | Runtime test | `tests/test_phase28_generic_project_path_validation.py` | ✅ Non-negative | Low | None |
| Debt service >= 0 | Solar + Wind | Runtime test | `tests/test_phase28_generic_project_path_validation.py` | ✅ Non-negative | Low | None |
| Distributions >= 0 | Solar + Wind | Runtime test | `tests/test_phase28_generic_project_path_validation.py` | ✅ Non-negative | Low | None |
| DSCR is positive where debt service exists | Solar + Wind | Runtime test | `tests/test_phase28_generic_project_path_validation.py` | ✅ Positive | Low | None |
| Generic project does NOT use frozen DS fixture | Solar + Wind | Code inspection | `app/project_factories.py` — `use_frozen_excel_senior_debt_schedule=False` | ✅ Confirmed | Low | None |
| Generic project uses live DSCR sculpting engine | Solar + Wind | Code inspection | `app/project_factories.py` — `debt_sizing_method=dscr_sculpt` | ✅ Confirmed | Low | None |
| Senior debt sizing path identified | Solar + Wind | Code inspection | `app/project_factories.py` | ✅ DSCR sculpt | Low | None |
| Generic warning / unvalidated language exists | Solar + Wind | Doc inspection | `docs/pilot_user_guide.md`, `docs/validation_pack_executive_summary.md` | ✅ Present | Medium | Ensure UI also has warning |
| TUHO frozen path unchanged | TUHO | Code inspection | `app/project_factories.py` — `use_frozen_excel_senior_debt_schedule=True` | ✅ Unchanged | Low | None |
| Oborovo frozen path unchanged | Oborovo | Code inspection | `app/project_factories.py` — `use_frozen_excel_senior_debt_schedule=True` | ✅ Unchanged | Low | None |
| No bank/lender/audit/certification claim for generic | Solar + Wind | Doc review | All Phase 27/27B/28 docs | ✅ Denied | Medium | Periodic review |
| No Excel reference for generic projects | Solar + Wind | Design note | This matrix + `phase28_generic_project_path_validation.md` | ⚠️ Out of scope | High | Obtain Excel reference if validation needed |
| No construction IDC (M1–M18) in generic runtime | Solar + Wind | Design note | `app/project_factories.py` | ✅ Not wired | Low | Document |
| Generic path not promoted as bankable | Solar + Wind | Guardrail | Phase 28 guardrails | ✅ Preserved | Medium | Ensure UI does not imply bankability |

---

## Risk Scale

| Symbol | Meaning |
|--------|---------|
| ✅ Low | Functioning as designed; no action required |
| ⚠️ Medium | Working but needs monitoring or explicit user guidance |
| ❌ High | Gap that prevents reliance without external validation |

---

## Out of Scope for Generic Path

| Item | Reason |
|------|--------|
| Excel reference validation | Does not exist for generic projects |
| Bank/lender approval | Not claimed — internal pilot tooling only |
| Certified external audit | Not claimed |
| Live sculpting solver comparison | Frozen path is TUHO/Oborovo only |
| Construction IDC wiring (M1–M18) | Not in scope for generic path |
| CAPEX/OPEX calibration to actual project costs | Round numbers used in generic factories |
