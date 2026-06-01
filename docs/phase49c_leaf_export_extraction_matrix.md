# Phase 49C — Leaf Export Route Extraction Matrix

**Branch:** `phase49c-extract-remaining-leaf-export-routes`
**Base SHA:** `811a71d3b8fef7a78a705b759c2882d7f0439cd6`

---

## All Routes Inspected (34 total)

| Route | Export? | Phase | Status |
|-------|---------|-------|--------|
| `GET /download` | ✅ Excel | 49B | Already extracted ✅ |
| `GET /exports/runtime-summary.csv` | ✅ CSV | 49B | Already extracted ✅ |
| `GET /exports/institutional-workbook.xlsx` | ✅ Workbook | 49B | Already extracted ✅ |
| `POST /download` | ✅ Excel | 49D | Deferred — complex form/session/provenance |
| `POST /compare` | ❌ HTML | — | Not an export |
| `GET /` | ❌ HTML | — | Not an export |
| `GET /login` | ❌ HTML | — | Not an export |
| `POST /login` | ❌ Auth | — | Not an export |
| `POST /logout` | ❌ Auth | — | Not an export |
| `GET /public-health` | ❌ Health | — | Not an export |
| `GET /readyz` | ❌ Health | — | Not an export |
| `GET /health` | ❌ Health | — | Not an export |
| `POST /validate` | ❌ Validation | — | Not an export |
| `POST /run` | ❌ Model execution | — | Not an export |
| `GET /projects/new` | ❌ HTML | — | Not an export |
| `GET /projects/browse` | ❌ HTML | — | Not an export |
| `POST /projects/create` | ❌ Project | — | Not an export |
| `GET /scenarios` | ❌ HTML | — | Not an export |
| `POST /scenarios/state/draft` | ❌ State | — | Not an export |
| `POST /scenarios/state/discard` | ❌ State | — | Not an export |
| `GET /scenarios/history` | ❌ HTML | — | Not an export |
| `GET /scenarios/compare` | ❌ HTML | — | Not an export |
| `POST /scenarios/save` | ❌ Save | — | Not an export |
| `GET /scenarios/{scenario_id}/load` | ❌ HTML | — | Not an export |
| `POST /scenarios/{scenario_id}/duplicate` | ❌ Duplicate | — | Not an export |
| `POST /scenarios/add` | ❌ Add | — | Not an export |
| `POST /scenarios/{scenario_id}/select` | ❌ Select | — | Not an export |
| `POST /scenarios/{scenario_id}/update-overrides` | ❌ Override | — | Not an export |
| `POST /projects/{project_code}/save-as` | ❌ Save-as | — | Not an export |
| `POST /scenarios/{scenario_id}/rename` | ❌ Rename | — | Not an export |
| `POST /scenarios/{scenario_id}/archive` | ❌ Archive | — | Not an export |
| `GET /runs` | ❌ HTML | — | Not an export |
| `POST /save-run` | ❌ Save | — | Not an export |
| `GET /run/{run_id}` | ❌ HTML | — | Not an export |

---

## Service API — No Changes in Phase 49C

Phase 49C found **no additional leaf exports** to extract. All existing Phase 49B service functions remain unchanged.

```python
# No changes to app/services/export_service.py
```

---

## POST /download Deferral Reasoning

| Criterion | Assessment |
|-----------|------------|
| Form parsing | Complex (12+ fields) |
| Session resolution | Multiple paths (`user_created`, `saved_state`, `saved_baseline`) |
| Provenance complexity | Conditional `runtime_origin` variants |
| Override logic | `build_projectinputs()` vs `build_projectinputs_from_snapshot()` |
| Test coverage needed | 6+ distinct paths |

Recommended for Phase 49D after comprehensive test coverage is added.

---

## Guardrails Status

| Guardrail | Status |
|-----------|--------|
| No formula changes | ✅ Confirmed |
| No runtime changes | ✅ Confirmed |
| No model output changes | ✅ Confirmed |
| G20 BLOCKED | ✅ |
| R99 NOT APPROVED | ✅ |
| R102 NOT APPROVED | ✅ |
| partial_pay_sweep not promoted | ✅ |
| flat/min DSCR sculpting not promoted | ✅ |
| Backend source of truth | ✅ |
| No JS financial calculations | ✅ |
| No fixture CSVs changed | ✅ |
| No schema migrations | ✅ |