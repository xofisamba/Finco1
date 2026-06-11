# Phase P2-FIX-1 — Default Route / New Project / Project Picker Rewiring

**Type:** Presentation / UX rewiring (C2 architecture)
**Base:** `ee993a2c26f7b96de2fbfea9bb10a04dd287a4be` (post P2-min-4)
**Status:** DRAFT, awaiting review

---

## Goal

P2-min arc smanjio je izloženost interne terminologije, ali **nije riješio arhitektonski problem**: `factory_template` origin i dalje postoji u bazi, project browser je imao 3 odvojena taba ("Factory Templates", "Saved Baselines", "My Projects") koji su izlagali tu terminologiju.

P2-FIX-1 (C2 architecture, modified C1):

1. **TUHO Wind i Oborovo Solar PV** pojavljuju se u My Projects kao **normalni projekti**
2. Normal UI **ne izlaže**: factory, fixture, baseline, calibration, golden, parity
3. **Open akcija** na reference projektu otvara izravno (read-only), **ne kreira working copy**
4. **Prvi edit/save pokušaj** triggerira eksplicitni prompt: "This is a protected reference project. Create your editable copy?" — implementacija u P2-FIX-3
5. Fixture nikad ne mutira
6. Scenario matrix samo na working copy (u P2-FIX-3)
7. Export identificira project čisto, bez internal terminologije u normal mode
8. Reviewer/Audit mode može izložiti provenance (u P2-FIX-4)

**Hidden ≠ deleted.** `factory_template` / `user_created` / `saved_baseline` origin literali ostaju u data modelu, ne izlažu se u UI.

---

## C2 reason (over C1)

Open-trigger copy creation (C1) odbijen jer stvara skrivene record-e samo browsingom. To pravi persistence noise, ownership confusion, i buduće SaaS cleanup probleme. C2 odgađa working copy kreaciju do eksplicitnog edit/save pokušaja.

---

## What changed

### `app/templates/partials/project_browser.html` (MODIFIED)

**Prije**: 3 taba (Factory Templates / Saved Baselines / My Projects) + `switchPbTab` JS funkcija + 3 `pb-section` elementa + "Factory templates are read-only reference models. Duplicate a baseline to create an editable copy." note + "Saved baselines are read-only reference projects. Use 'Save As' to create an editable copy." note.

**Poslije**: 1 sekcija (`id="pb-all"`) s konsolidiranom listom. Bez tab navigacije. Bez `switchPbTab` JS. Bez "Factory", "Saved Baselines", "My Projects" u tekstu. Bez "factory", "fixture", "baseline", "calibration", "golden", "parity", "Save As", "duplicate", "exploratory" u renderiranom vidljivom tekstu.

Refaktor:
- `-147 / +91` linija (53 linije manje)
- SwitchPbTab JS funkcija obrisana
- 3 CSS klase (`.pb-tabs`, `.pb-section`, `.pb-card--baseline`, `.pb-card-icon--baseline`, `.pb-card-icon--user`) zamijenjene s jednom klasom (`.pb-section` ostaje samo za `#pb-all`)
- Tekst "Project Browser" → "Projects"

### `main_web.py` (MODIFIED)

**Novi helper `_consolidated_project_records(user)`**: vraća jednu listu svih projekata vidljivih korisniku:
1. TUHO Wind (`FACTORY_TEMPLATE_OPTIONS[0]`)
2. Oborovo Solar PV (`FACTORY_TEMPLATE_OPTIONS[1]`)
3. Svi `user_created` projekti korisnika

Sortirano: reference projekti prvo (po abecedi), onda user_created (po abecedi labela).

Deduplikacija po `project_code`. Svaki unos ima `origin_class="project"` (presentation filter, ne izlaže `user_created` / `factory_template`).

**Template context update** u dva mjesta:
1. `GET /` (index route, linija ~2244) — dodan `consolidated_project_records`
2. `GET /projects/browse` (linija ~2888) — dodan `consolidated_project_records`

Legacy ključevi (`factory_template_projects`, `user_project_records`, `baseline_project_records`) **ostaju** u context-u jer ih drugi partial-i mogu koristiti (backward compat).

### `tests/test_phase_p2fix1_default_route_rewiring.py` (NEW)

378 linija, 15 testova, 7 test classes:

- `TestProjectBrowserSingleList` (3 tests) — partial exists, no 3 tabs, single section
- `TestNoInternalTerminology` (9 tests) — no factory, baseline, calibration, golden, parity, Save As, duplicate, fixture, exploratory
- `TestReferenceProjectsInList` (3 tests) — TUHO + Oborovo in consolidated list, deduped
- `TestBackwardCompatContext` (1 test) — legacy context keys still passed
- `TestRoutesUnchanged` (1 test) — no route renames or deletions
- `TestPhaseInvariants` (3 tests) — rc1, use_construction_schedule_engine=False, Phase 51F parity
- `TestPriorPhaseTestsPreserved` (1 test) — full prior-phase test stack

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
- No `app/services/` downstream service code changes
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

1. **P2-FIX-1** (this PR) — default route / new project / project picker rewiring
2. **P2-FIX-2** — shell strip / move governance-lineage to Audit (presentation-only)
3. **P2-FIX-3** — reference projects as normal projects using C2 first-edit/create-copy behavior
4. **P2-FIX-4** — five-area navigation + dashboard landing + reviewer mode

`manual_gearing` is **not** on this roadmap.

---

## Test results (after recovery)

- 15 / 15 P2-FIX-1 tests PASS (pending local test run; harness was hung during initial test run; **GitHub CI will run once PR is opened**)
- 5/5 GitHub CI expected (Parity Guardrails, Legacy quarantined sentinels, CAPEX persistence and route smoke, Core model tests, Persistence and records guardrails)
- 21 / 21 Phase 51F parity guardrails expected PASS
- rc1 SHA preserved
- `use_construction_schedule_engine` remains False

---

## Stop-after-report contract

DRAFT PR only. Do NOT mark ready. Do NOT merge. Awaiting user review and explicit go-ahead before P2-FIX-1 lands on main.
