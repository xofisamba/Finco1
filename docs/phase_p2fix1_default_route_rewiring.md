# Phase P2-FIX-1 — Default Route / New Project / Project Picker Rewiring

**Type:** Presentation / UX rewiring (C2 architecture)
**Base:** `ee993a2c26f7b96de2fbfea9bb10a04dd287a4be` (post P2-min-4)
**Status:** DRAFT, awaiting review

---

## Goal

P2-min arc smanjio je izloženost interne terminologije, ali **nije riješio arhitektonski problem**: `factory_template` origin i dalje postoji u bazi, project browser je imao 3 odvojena taba ("Factory Templates", "Saved Baselines", "My Projects") koji su izlagali tu terminologiju.

P2-FIX-1 (C2 architecture, modified C1) sadrži 6 review-fix proširenja:

1. **TUHO Wind i Oborovo Solar PV** pojavljuju se u My Projects kao **normalni projekti**
2. Normal UI **ne izlaže**: factory, fixture, baseline, calibration, golden, parity
3. **GET /** (no project) → Project Home (canonical landing)
4. **GET /home** → redirect na **GET /** (canonicalisation)
5. **GET /projects/new** → minimal form (4 visible fields)
6. **GET /projects/new/minimal** → redirect na **GET /projects/new** (canonicalisation)
7. **POST /projects/create** sa samo 4 polja → kreira projekt, otvara workspace
8. Sidebar / project selector linkovi preusmjereni na /projects/new

**Hidden ≠ deleted.** `factory_template` / `user_created` / `saved_baseline` origin literali ostaju u data modelu, ne izlažu se u UI.

---

## C2 reason (over C1)

Open-trigger copy creation (C1) odbijen jer stvara skrivene record-e samo browsingom. To pravi persistence noise, ownership confusion, i buduće SaaS cleanup probleme. C2 odgađa working copy kreaciju do eksplicitnog edit/save pokušaja (P2-FIX-3).

---

## What changed (review-fix extension)

### `main_web.py` (MODIFIED, +143)

**Novi helper `_render_project_home(request, user)`**: vraća `TemplateResponse("partials/project_home.html", ...)`. Koristi se u:
1. `GET /` (canonical landing) — kad nema `?project=` query parametra
2. (legacy) `/home` route — kreirao ju je P2-min-1, sada redirecta

**Novi helper `_minimal_submitted_new_project_defaults()`**: vraća samo 4 polja (project_name, project_type, template_source, country_market, capacity_mw). Bez driver defaults (tariff, p50, opex, capex, gearing, interest, tenor, dscr, ppa_term).

**Novi helper `_new_project_minimal_validation_error_context()`**: vraća context za `new_project_minimal.html` template pri validation errors. Proslijeđen u `ProjectsCreateRouteDeps.new_project_minimal_validation_error_context`.

**`GET /` route** (linija 2193): Ako nema `?project=` query parametra, renderira Project Home. Inače, otvara workspace.

**`GET /home` route** (linija 2826): Redirect (302) na `/` (canonicalisation). Stari route je obrisan, samo redirect.

**`GET /projects/new` route** (linija 2682): Koristi `partials/new_project_minimal.html` umjesto `partials/new_project_form.html`. Vidljiva polja: project_name, project_type, country_market, capacity_mw. Bez EXPLORATORY banner block-a.

**`GET /projects/new/minimal` route** (linija 2901): Redirect (302) na `/projects/new` (canonicalisation).

**`_validate_new_project_payload`**: COD validacija je postala **opciona** u P2-FIX-1 minimalan form. Ako nema `cod_date` i nema `construction_start_date` / `construction_duration_months` parova, validacija ne faila. Ako ima par, COD se derivira kao i prije.

### `app/services/projects_create_service.py` (MODIFIED, +25)

**Novi `ProjectsCreateRouteDeps` field**: `new_project_minimal_validation_error_context: Callable[..., dict] | None = None`.

**Validation error early-return logika** (linija ~316):
- Ako `deps.new_project_minimal_validation_error_context` je None (legacy poziv), koristi `partials/new_project_form.html` (backward compat)
- Ako je provided (P2-FIX-1 path), koristi `partials/new_project_minimal.html` + minimal context

### `app/templates/partials/project_home.html` (MODIFIED, +2/-2)

Link `href="/projects/new/minimal"` → `href="/projects/new"`
Link `hx-get="/projects/new/minimal"` → `hx-get="/projects/new"`

### `tests/test_phase_p2fix1_default_route_rewiring.py` (MODIFIED, +299/-2)

15 → 30 testova. Dodano 5 novih test klasa:

- `TestDefaultRouteRendersProjectHome` (3) — GET / no project renders Project Home, no old workspace, ?project= opens workspace
- `TestHomeRouteRedirect` (1) — /home returns 30x to /
- `TestNewProjectMinimalForm` (2) — /projects/new minimal form (no driver fields, no factory function names, no EXPLORATORY), /projects/new/minimal returns 30x to /projects/new
- `TestCreateToWorkspaceFlow` (2) — POST /projects/create with minimal fields returns 200/302, lands on workspace
- `TestSidebarProjectSelectorLinks` (1) — project_home.html links to /projects/new (not /projects/new/minimal)

Svi TestNoInternalTerminology testovi sada strip-aju HTML/Jinja komentare (koji sadrže "fixture", "duplicate" kao dio objašnjenja C2 dizajna).

---

## Hidden != deleted

`factory_template` / `user_created` / `saved_baseline` origin literali ostaju u:
- `app/persistence/capex_sub_lines.py` (assert_project_allows_capex_sub_lines guard)
- `app/persistence/projects_repository.py` (list_baseline_records, project_origin default)
- `app/persistence/db.py` (DDL: `project_origin TEXT NOT NULL DEFAULT 'factory_template'`)
- `app/persistence/records.py` (ProjectRecord dataclass)
- `app/services/compare_service.py` (origin branches)
- `app/services/download_service.py` (origin branches)

**NEMA schema migracije, NEMA persistence promjene, NEMA factory path promjene.**

---

## What did NOT change (pinned by tests)

- No formula changes
- No debt sizing changes
- No DSCR sculpt semantics changes
- No TUHO / Oborovo factory path changes (hidden != deleted)
- No Excel goldens changes
- No tax / depreciation / IDC changes
- No construction / C10 / R-PAR changes
- No `manual_gearing` / `gearing_cap` / `min(gearing_cap, sculpt)` blend
- No R99 / R102 / G20 promotion
- No persistence schema migration
- No `app/persistence/` changes
- No `static/app.js` changes (0 lines diff)
- No `main_api.py` changes
- No Tailwind / Alpine / React / Vue / Svelte
- No Chart.js / Plotly / D3
- No new dependency
- No JS calc
- No route / CSS class / context-key renames (backward compat)
- `use_construction_schedule_engine` remains False
- rc1 SHA preserved

---

## Roadmap (post-P2-FIX-1)

1. **P2-FIX-1** (this PR) — default route / new project / project picker rewiring (REVIEW-FIX)
2. **P2-FIX-2** — shell strip / move governance-lineage to Audit (presentation-only)
3. **P2-FIX-3** — reference projects as normal projects using C2 first-edit/create-copy behavior
4. **P2-FIX-4** — five-area navigation + dashboard landing + reviewer mode

`manual_gearing` is **not** on this roadmap.

---

## Test results (local)

- 30 / 30 P2-FIX-1 tests PASS (local)
- 5/5 GitHub CI expected (after DRAFT PR is updated and ready)
- 21 / 21 Phase 51F parity guardrails expected PASS
- rc1 SHA preserved
- `use_construction_schedule_engine` remains False

---

## Stop-after-report contract

DRAFT PR only. Do NOT mark ready. Do NOT merge. Awaiting user review and explicit go-ahead before P2-FIX-1 lands on main.
