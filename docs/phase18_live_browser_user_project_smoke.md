# Phase 18B — Live Browser User Project Smoke

## Objective

Prove the real browser workflow for a user-created project end-to-end using Playwright chromium in a live session.

**Primary browser workflow:**
1. Open app
2. Login (admin / fincoGPT2026!)
3. Open New Project
4. Fill required fields with test project data
5. Submit project
6. Confirm project appears in User-Created Projects selector
7. Select/load the project; confirm form values are restored
8. Save scenario
9. Confirm saved/clean state
10. Run model
11. Confirm runtime summary appears
12. Confirm dirty edit blocks run
13. Revert dirty edit
14. Confirm run works again after clean state restored
15. Export/download workbook
16. Confirm workbook file downloads
17. If openpyxl available, open workbook and inspect Notes/Inputs
18. Confirm TUHO and Oborovo still appear as Factory Templates
19. Confirm G20 BLOCKED and R99/R102 NOT APPROVED
20. No browser page errors

## Test Project Data

```
project_name = Browser Smoke Wind
project_type = Wind
template_source = generic_wind
country_market = Croatia
capacity_mw = 50
cod_date = 2027-01-01
construction_months = 12
horizon_years = 25
tariff_eur_mwh = 100
ppa_term_years = 15
p50_hours = 1600
opex_y1_keur = 1000
total_capex_keur = 50000
gearing_pct = 70
interest_rate_pct = 5
tenor_years = 15
target_dscr = 1.30
```

## Scope

**In scope:**
- Live browser smoke via Playwright chromium
- Full user project workflow: create → save → run → export
- Dirty state guard verification
- TUHO/Oborovo factory template visibility
- Governance notice presence (G20 BLOCKED, R99/R102 NOT APPROVED)
- Workbook download smoke
- Evidence register with honest status

**Out of scope (no claims made):**
- Lender-ready, audit-certified, SaaS-ready
- Full formula verification across all model sheets
- Multi-browser compatibility
- Non-headless browser behavior
- Performance/load testing

## Skip Policy

If Playwright or Chromium binaries are unavailable, the test **skips honestly** with:
```
reason="OPTIONAL_BROWSER_DEPENDENCY_MISSING: install playwright and chromium to run live browser smoke"
```
or
```
reason="OPTIONAL_BROWSER_DEPENDENCY_MISSING_BROWSER_BINARIES: {exc}"
```

No fake pass is recorded. The evidence register records `SKIP` with the skip reason.

## Runtime Authority

- Backend (`main_web.py`) remains the sole runtime authority
- Frontend/browser state does not become runtime authority
- Dirty browser draft is never promoted to runtime truth
- Workbook export uses backend-authored provenance and Notes/Inputs sheets
- Save does not auto-run; Run does not auto-save

## Governance Posture

- G20 remains `BLOCKED`
- R99/R102 remain `NOT APPROVED`
- No lender-ready claim
- No audit-certified claim
- No SaaS-ready claim

## Files

| File | Purpose |
|------|---------|
| `tests/test_phase18_live_browser_user_project_smoke.py` | Main Playwright smoke test |
| `reports/phase18_live_browser_smoke_matrix.csv` | Step-by-step workflow matrix |
| `reports/phase18_live_browser_evidence_register.csv` | Evidence from actual test runs |
| `reports/phase18_live_browser_remaining_gaps.csv` | Known gaps with severity and follow-up |
| `docs/phase18_live_browser_user_project_smoke.md` | This document |

## Architecture References

- User-created projects use `saved_project_assumptions` as runtime source
- `build_projectinputs_from_snapshot()` builds `ProjectInputs` directly from saved assumptions
- TUHO and Oborovo remain factory templates
- Dirty browser state is blocked from runtime by `runtime_guard_for_snapshot`
- Export provenance metadata identifies `runtime_origin: saved_state` for user-created projects
