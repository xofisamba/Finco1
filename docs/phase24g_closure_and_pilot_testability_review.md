# Phase 24-G Closure Review + Pilot Testability Assessment

> Type: REPORT ONLY, DOCS ONLY, SHAPE TESTS ONLY
> Status: DRAFT (review-only)
> Date: 2026-06-09
> Base SHA: `f69e9e4` (post-#570 merge, post-#569 close)
> Branch: `phase24g-closure-pilot-testability-review`
> Hard constraints:
> - No implementation
> - No runtime changes
> - No UI changes
> - No model changes
> - No persistence changes
> - No C10 / R-PAR work
> - rc1 untouched
> - DRAFT only (no merge in this turn)

---

## 0. Purpose

A consolidated closure review of the **G (Pilot UX Safe) track**
and a **pilot testability assessment** answering the question:

> Is FincoGPT now meaningfully testable by an internal pilot user?

This document does **not**:
- Touch any production code.
- Promote any feature flag.
- Implement any of the items it ranks.
- Commit to a specific next sprint.
- Make any bank / lender / external audit claim.

It is a structured, ranked, evidence-based review that:

1. Summarizes what was delivered across the G track.
2. Tells a pilot user what they can do today.
3. Tells a pilot user what they still cannot do.
4. Ranks the remaining blockers by user impact, parity risk,
   and implementation effort.
5. Answers the four explicit questions a finance user, a
   renewable developer, and a product manager would ask.

---

## 1. What was delivered across the G track

The G track is the 4-PR / 5-doc arc that began with the inventory
in PR #564 and closed with the readability / clarity work in
PR #570. All four PRs are merged into `main`. No further code
work is pending in this track.

### 1.1 PR #564 — Pilot UX Safe Track Inventory

- **Type:** docs + report + shape tests (no code)
- **Branch:** `pilot-ux-safe-track-inventory`
- **Head:** `a421ab5`
- **Status:** ✅ MERGED
- **Deliverable:** 5 categories of low-risk UI improvements,
  ranked by user value × parity risk × implementation effort.
- **Independence rule:** all items must be implementable
  independently of R-PAR-2 and C10 (so the G track can run in
  parallel with the parity / construction chain).

| Rank | Item | User value | Parity risk | Impl. risk | Effort | Independence |
|---|---|---|---|---|---|---|
| 1 | Validation summary clarity | 5 | 0 | 1 | M | ✅ |
| 2 | Stale run warning | 5 | 0 | 1 | S | ✅ |
| 3 | Run status clarity | 4 | 0 | 1 | M | ✅ |
| 4 | CAPEX sheet readability | 4 | 0 | 2 | M | ✅ |
| 5 | Export / download clarity | 3 | 0 | 1 | S | ✅ |

### 1.2 PR #566 (DRAFT, closed) → PR #567 (merged) — Phase 24-G-1

- **Type:** UI-only implementation
- **Branch:** `phase24g1-stale-run-warning-validation-summary-clarity`
- **Head:** `56e81cc`
- **Status:** ✅ MERGED
- **Sprint:** 24-G-1 (parallel to C10 / R-PAR-2 chain)
- **Delivered:**
  - **Stale run warning:** styled "STALE" badge replaces the
    ⏱️ emoji; visible "Re-run" anchor link to the existing
    sidebar button; optional `.esn-stale-changed` span surfaces
    `workspace_state_meta.dirty_label` (e.g. "older than current
    draft (3 fields changed)").
  - **Validation summary clarity (part 1):** plain-language error
    catalog for the top validation errors; group messages by
    severity (Error / Warning / Information); reduce duplicated
    wording.
- **Tests:** 19 + 28 = 47 (all passing)
- **Hard constraints honored:** no model / formula / tax / debt /
  depreciation / IDC / persistence / runtime / project-status /
  generic-promotion / C10 / construction-flag changes. UI only.

### 1.3 PR #565 (DRAFT, closed) → PR #568 (merged) — Phase 24-G-2

- **Type:** UI-only implementation
- **Branch:** `phase24g2-run-status-clarity-validation-summary-completion`
- **Head:** `d1dbe87`
- **Status:** ✅ MERGED
- **Sprint:** 24-G-2
- **Delivered:**
  - **Run status clarity:** OK / ERROR / BLOCKED / — (NO RUN)
    status badge; project association row; scenario association
    row; inline stale / fresh indicator.
  - **Validation summary completion:** strict severity ordering,
    hint subtitles, visual consistency.
  - **Empty-state review:** three new top-of-page empty-state
    partials (`_empty_no_project.html`, `_empty_no_run.html`,
    `_empty_no_scenario.html`).
- **Tests:** 40 + 35 = 75 (all passing)
- **Hard constraints honored:** no backend / service / domain /
  persistence / model / formula / tax / debt / depreciation /
  IDC / runtime / fake-run-IDs / fake-timestamps / app.js /
  Tailwind / Alpine changes. UI only.

### 1.4 PR #569 (DRAFT, closed) → PR #570 (merged) — Phase 24-G-3

- **Type:** UI-only implementation
- **Branch:** `phase24g3-capex-sheet-readability-export-download-clarity`
- **Head:** `a43ba3e` (squash merge)
- **Status:** ✅ MERGED
- **Sprint:** 24-G-3
- **Delivered:**
  - **CAPEX sheet readability:**
    - Status legend lead (1-line intro to the 4 status chips).
    - Deferred placeholders lead + per-item inline descriptor.
    - Sources & Uses bridge: 13-bullet `<ul>` replaced with
      compact "what feeds what" summary using 4 pill tags.
    - CAPEX total computation **unchanged**; summary strip still
      uses `{:,.1f}` on all 4 cards.
  - **Export / download clarity:**
    - Empty state block (renders when `export_cards` is
      missing/empty).
    - Intro lead (1-line "What is in each export" copy).
    - Per-card lineage row (names the source artefact(s)
      feeding each of the 8 exports).
    - G20 / R99 / R102 disabled copy unchanged but more visible.
- **Tests:** 37 + 32 = 69 (all passing)
- **Hard constraints honored:** no model / formula / CAPEX-calc /
  tax / debt / depreciation / IDC / construction / C10 / R-PAR /
  feature-flag / backend-runtime / static/app.js / Tailwind /
  Alpine / rc1 changes. UI only.
- **CSS invariant:** `:root` block count unchanged at 3 (UI-2.5
  invariant preserved). 7 new classes appended (additive).
- **CI green (5/5):** Legacy quarantined sentinels, CAPEX
  persistence and route smoke, Core model tests, Persistence
  and records guardrails, Parity Guardrails (Phase 51F).

### 1.5 Cumulative G-track test footprint

| Phase | Tests |
|---|---|
| #564 (inventory shape tests) | 17 |
| 24-G-1 | 47 |
| 24-G-2 | 75 |
| 24-G-3 | 69 |
| **Total new (G track)** | **208** |

All 208 G-track tests are passing on `main` (post-#570).

### 1.6 G-track scope discipline

Across all four merged G-track PRs, the following were
**strictly forbidden and never touched**:

- `main_web.py`
- `app/services/`
- `app/persistence/`
- `app/domain/`
- `app/api/`
- `app/tax_bridge/`
- `waterfall_core.py`
- `static/app.js`
- `model/`, `formula/`, `tax/`, `debt/`, `depreciation/`, `IDC/`
- Feature flag values
- `use_construction_schedule_engine` (remains `False`)
- `rc1`

G track is therefore a **strictly UI-only** track. It improves
pilot UX without introducing any risk to model parity, runtime
promotion, or the construction-bridge chain.

---

## 2. What a user can do today (post-G track)

A pilot user on the current `main` (commit `f69e9e4`) **can** do
all of the following. Each item is a real, working surface
in the merged product.

### 2.1 Project + scenario workflow

- **Browse existing projects** (TUHO, Oborovo, generic wind,
  generic solar) in the project browser.
- **Create a new project** with a clear form: project name,
  country / market, project type (Solar / Wind), template
  source.
- **Edit draft inputs** in the inputs section
  (Revenue, OPEX, Senior Debt, selected assumptions).
- **Save a named scenario** to the database.
- **See the saved version in the version history**.
- **Run the model from a clean saved boundary.**
- **Inspect the backend-authored runtime summary.**
- **Compare saved scenarios** (the `/compare` route is read-only
  and does not write to the database).
- **Download artefacts** (CSV / XLSX) for the project.

### 2.2 Run status (24-G-2)

- **See a status badge** on the last run indicator: ✓ OK
  (green), ✗ ERROR (red), ⊘ BLOCKED (amber), — NO RUN (grey).
- **See project + scenario association** in the run indicator.
- **See an inline stale / fresh badge** with explanatory copy.
- **See a "Last run error" row** when the last run failed.
- **See a "stale" banner** (24-G-1 work) at the top of the page
  with a one-click "Run again" anchor link.

### 2.3 Validation (24-G-1, 24-G-2)

- **See plain-language error messages** for the top validation
  errors.
- **See grouped, severity-ordered validation messages** with
  hint subtitles.
- **See distinct visual cues** for blockers vs warnings.
- **See the validation status on the scenario save button**
  (red / yellow / green).
- **Locate the validation panel** via the existing
  `_validation_summary_bar.html` partial.

### 2.4 CAPEX workspace (24-G-3)

- **See all 18 C-band categories** (C.01..C.18) with sub-lines
  in the single-sheet grid.
- **See editable amount inputs** for ordinary CAPEX lines
  (user project mode).
- **See derived category subtotals** (read-only).
- **See the summary strip** with Hard CAPEX, Financing /
  Reserve, Total CAPEX, and CAPEX / MW cards.
- **Read the status legend** (Runtime-used / Metadata-only /
  Design-only / Export-only) with a 1-line intro.
- **Read the deferred placeholders** with per-item inline
  descriptors.
- **Read the compact Sources & Uses bridge** (4 pill tags).

### 2.5 Export / download (24-G-3)

- **See an empty-state block** when no exports are available,
  with an explanation and a pointer to the "Run Model" action.
- **See a 1-line intro lead** explaining "What is in each
  export" when the registry has cards.
- **See a per-card lineage row** that names the source
  artefact(s) feeding each export.
- **See the G20 / R99 / R102 status badges** with explanatory
  copy.

### 2.6 Audit / parity (Phase 24E, pre-G)

- **Locate the Audit / Parity tab.**
- **See the parity status** across Revenue, OPEX, CAPEX, Debt,
  SHL, Validation.
- **Distinguish validated TUHO / Oborovo evidence** from
  generic or pending review rows.
- **Understand** that the audit tab is internal review tooling,
  not certified external audit.

### 2.7 Data safety (Phase 24F, pre-G)

- **Trigger an on-demand SQLite backup** from the admin
  surface.
- **Restore from a backup** with safety protections.

### 2.8 Pilot UX walkthrough (24-G-1 / 24-G-2)

The items in `pilot_ux_walkthrough_checklist.md` are now
**passable end-to-end** by a single trusted pilot user. The
checklist has 25 items; the G track contributed to ~6 of them
(stale state visibility, validation visibility, run status
visibility, status legend, S&U bridge, export lineage).

---

## 3. What a user still cannot do

This is the **honest** list. The G track is feature-complete
within its scope, but the G track is **not** the only thing
that determines pilot testability. The broader pilot
testability is gated by the **C10 / R-PAR-2 chain** (out of
scope for the G track) and by **architectural gaps** documented
in `phase_pilot_readiness_gap_analysis.md`.

### 3.1 Architectural gaps (P-blocker)

- **Generic wind / solar not validated for external claims.**
  The generic templates exist and run, but the runtime output
  is **not validated against Excel** for these templates. A
  user who builds a project on `generic_wind` or `generic_solar`
  and tries to rely on the IRR / DSCR / cash flow numbers will
  be making decisions on **unvalidated** output.
- **R-PAR-2 senior IDC effective-rate caveat** is open. The
  current senior IDC accrual path is in the model, but the
  effective-rate caveat (a known calibration gap) means the
  senior IDC numbers are not yet within the agreed ±1%
  tolerance.
- **R-PAR-5 `equity_total_keur` derived-field parity not
  green.** The total field is computed, but the derivation
  path does not yet match the Excel reference exactly.
- **C10 implementation not started.** The runtime seam
  (`app/services/construction_runtime_seam.py`) is
  **scaffolded but not wired into the waterfall**. The
  construction-period engine is documented and has offline
  comparison tests, but the runtime does not call it.
- **Debt sculpting parity** is open. TUHO and Oborovo both
  show "Fixture-backed · No sculpting" because the senior
  debt service is frozen from the Excel reference, not
  computed by the in-app sculpting solver.

### 3.2 UX gaps (UX-blocker)

- **Auto-backup observability** is logs-only. A user does not
  see "Last backup: 3 hours ago" in the project header.
- **Export history** is not surfaced in the sidebar. A user
  must re-export from scratch if they want the same artefact
  again.
- **Export progress** is not surfaced for long-running
  exports.
- **Search / quick-filter** for CAPEX sub-lines is not
  present.
- **Pin of total CAPEX row** at the top of the grid is not
  implemented.
- **Default-collapse of advanced CAPEX columns** is not
  implemented.

### 3.3 Governance gaps (governance-blocker)

- **Bank / lender / external audit certification** is **out
  of scope by claim**. The audit tab is internal review
  tooling, not certified external audit.
- **Approval / signoff orchestration** is not wired. There is
  no "submit for signoff" workflow.
- **R99 / R102 audit chain** is partially closed. The
  calibration reconciliation pack is generated, but the full
  R84 / R98 / R99 / R102 chain is not green.

### 3.4 Commercial gaps (commercial-blocker)

- **Pricing / packaging / SLA** are not defined.
- **Support / on-call rotation** is not defined.
- **Commercial claims** (lender-ready, audit-certified,
  bank-approved) are **explicitly not made**.

### 3.5 Multi-user gaps (architecture-blocker)

- **No multi-user / tenant isolation.** The app is
  single-user only (admin / admin by default).
- **No RBAC.** No admin / viewer / editor roles.
- **No SSO.** No SAML / OIDC integration.
- **No data residency / GDPR controls.**

---

## 4. Biggest blockers preventing meaningful project testing

The phrase "meaningful project testing" is interpreted here as
**building a real project on a validated template (TUHO or
Oborovo), running it from a clean saved boundary, inspecting
the runtime summary, comparing against the Excel reference,
and getting back numbers that are within the agreed tolerance**.

### 4.1 Ranked blockers (P-priority only)

| Rank | Blocker | Impact | Parity risk | Effort | Why it's #N |
|---|---|---|---|---|---|
| 1 | R-PAR-2 senior IDC effective-rate | High | High (parity) | M | The senior IDC numbers are not within ±1% of the Excel reference; a pilot user will see discrepancies in DSCR / IRR. |
| 2 | R-PAR-5 `equity_total_keur` derived | High | High (parity) | M | The total equity field is computed, but the derivation does not match the Excel reference; affects the entire P&L / cash-flow chain. |
| 3 | Debt sculpting parity (TUHO / Oborovo) | High | High (parity) | M | The senior debt service is frozen from the Excel reference, not computed in-app. Pilot users cannot change assumptions and see the sculpted impact. |
| 4 | C10 not wired into the waterfall | High | High (parity) | L | The construction runtime seam exists but is not called. Pilot users running a "construction-period" scenario get the legacy fallback. |
| 5 | Generic wind / solar not validated | High | High (parity) | L | Generic projects run, but the output is unvalidated. A pilot user who builds a generic project will be making decisions on unvalidated numbers. |
| 6 | R99 / R102 audit chain not green | Medium | Medium (testing) | M | The audit register is generated, but the full R84 / R98 / R99 / R102 chain is not green. Pilot users cannot produce a fully-signed-off audit pack. |
| 7 | R67 cash-tax bridge residual (TUHO) | Medium | Medium (parity) | M | The interest-limitation consumer does not yet close out the cash-tax bridge; affects TUHO's after-tax cash flow. |
| 8 | Oborovo distribution lockup residual | Medium | Medium (parity) | S | The distribution lockup policy has a residual; affects Oborovo's IRR. |
| 9 | CAPEX per-line runtime not wired | Medium | Low (UX) | M | The display is there (57A-10F/G/H), but the per-line runtime is not exposed. Pilot users cannot yet see "this CAPEX sub-line drives N% of the IRR". |
| 10 | Oborovo SHL / CFADS waterfall residuals | Medium | Medium (parity) | M | Some SHL / CFADS waterfall residuals remain. |

### 4.2 What a pilot user hits in the first 30 minutes

When a finance user opens the app for the first time, they
will:

1. ✅ Successfully select TUHO (validated).
2. ✅ See the status legend and the S&U bridge.
3. ✅ Edit a draft input (e.g. PPA price).
4. ✅ Save a scenario.
5. ✅ Run the model from a clean boundary.
6. ✅ See the runtime summary with status badge (OK / ERROR /
   BLOCKED / —).
7. ✅ See the stale / fresh indicator.
8. ⚠️ **See the senior IDC number disagree with the Excel
   reference** (R-PAR-2).
9. ⚠️ **See the equity total disagree with the Excel
   reference** (R-PAR-5).
10. ⚠️ **Not be able to change assumptions and re-sculpt
    senior debt** (debt sculpting is frozen from Excel).
11. ⚠️ **Not be able to run a construction-period scenario
    with the runtime engine** (C10 not wired).
12. ⚠️ **Be unable to sign off the audit pack** (R99 / R102
    chain not green).

The first 8 items pass cleanly. Items 8-12 are the
"meaningful project testing" cliff.

---

## 5. Biggest blockers preventing pilot rollout

The phrase "pilot rollout" is interpreted here as **inviting a
small number of internal trusted users (3-5 finance people,
1-2 renewable developers) to use the product in their day-to-day
workflow for a defined period (4-8 weeks) with a defined
scope (TUHO + Oborovo only, no generic, no multi-user,
no external data).**

### 5.1 Ranked blockers (pilot-rollout scope)

| Rank | Blocker | Impact | Parity risk | Effort | Why it blocks rollout |
|---|---|---|---|---|---|
| 1 | All items in §4.1 above | High | High | M–L | Until the P-blockers are closed, a pilot user will see discrepancies vs Excel on day 1. |
| 2 | No user onboarding guide tied to the new UX | Medium | Low (UX) | S | The pilot user will not know which template is validated, which is not, or which buttons are blocked. |
| 3 | No audit log UI for pilot actions | Medium | Low (UX) | M | The pilot user will not be able to point at a "I ran this on this date" trail. |
| 4 | No per-project reproducibility | Medium | Low (UX) | M | The pilot user will not be able to re-run the same project and get the same number (no fixed seed / deterministic replay). |
| 5 | No "report a bug" surface inside the app | Medium | Low (UX) | S | The pilot user will email bugs; we lose structured signal. |
| 6 | No session timeout UX (security) | Low | Low (UX) | S | The pilot user will be left logged in indefinitely. |

### 5.2 What is the gap between "single trusted pilot user" and "pilot rollout"?

- **Single trusted pilot user:** the product works for **one
  user, on one project, with a known Excel reference to
  compare against, with a cofi19-in-the-loop reviewer**. This
  is achievable today.
- **Pilot rollout (3-5 users, multi-project, multi-template,
  with no cofi19 in the loop):** the product needs all of
  the items in §5.1 closed, plus a documented "what is
  validated, what is not" matrix that the pilot user can
  read without us.

---

## 6. Biggest blockers preventing paid product rollout

The phrase "paid product rollout" is interpreted here as **an
external user (bank / fund / boutique consultancy) paying
for the product on a SaaS basis, with an SLA, with multiple
users per organization, with their data, with their projects.**

### 6.1 Ranked blockers (paid-product scope)

| Rank | Blocker | Impact | Parity risk | Effort | Why it blocks paid |
|---|---|---|---|---|---|
| 1 | All P-blockers (§4.1) | High | High | M–L | An external user will not pay for unvalidated output. |
| 2 | Multi-user / RBAC / SSO | High | Low (architecture) | L | The app is single-user; an external user will need a team. |
| 3 | Approval / signoff orchestration | High | Low (governance) | M | An external user will need to demonstrate "this was reviewed and signed off" to their stakeholders. |
| 4 | Audit-export package for paid tier | High | Low (commercial) | M | An external user will need a downloadable audit pack with signoff. |
| 5 | Commercial packaging (pricing, claim scope) | High | Low (commercial) | M | An external user will need to know what they are buying and what they are NOT buying. |
| 6 | Replay-engine behavior | Medium | Low (architecture) | M | An external user will need to re-run a snapshot and get the same number. |
| 7 | External-model-review package for paid customers | High | Low (governance) | L | An external user will want an independent review of the model. |
| 8 | SLA / support / on-call rotation | High | Low (commercial) | M | An external user will need a contractual response-time commitment. |
| 9 | Data residency / GDPR | High | Low (governance) | L | An external EU user will need to know where their data lives. |
| 10 | Enterprise billing / contract | High | Low (commercial) | L | An external user will need a contract. |

### 6.2 What is the gap between "pilot rollout" and "paid product"?

- **Pilot rollout:** the product works for a small set of
  trusted users, on a defined scope, with a known reviewer
  in the loop.
- **Paid product:** the product works for an external user
  with a contract, an SLA, an audit pack, multi-user,
  data-residency controls, replay, and a defined commercial
  claim scope (e.g. "calibration assistance, not audit
  certification").

The gap is **architectural** (multi-user, replay, audit-pack)
and **commercial** (pricing, SLA, claim scope). It is
**not** primarily a parity gap — once the P-blockers are
closed, the parity picture is acceptable for a paid
calibration-assistance product (with a defined claim scope).

---

## 7. Rank remaining blockers (impact × parity × effort)

This is the consolidated rank that the next sprint planning
will use. Each blocker is scored on:

- **User impact** (1–5, 5 = highest)
- **Parity risk** (1–5, 5 = highest; ideally 0)
- **Implementation effort** (1–5, 5 = highest; ideally 1)

The composite score is:
`user_impact × 2 - parity_risk - implementation_effort`

### 7.1 Top 15 (across all horizons)

| # | Blocker | Impact | Parity | Effort | Composite | Horizon |
|---|---------|--------|--------|--------|-----------|---------|
| 1 | R-PAR-2 senior IDC effective-rate | 5 | 5 | 3 | **2** | P, $ |
| 2 | R-PAR-5 `equity_total_keur` derived | 5 | 5 | 3 | **2** | P, $ |
| 3 | Multi-user / RBAC / SSO | 5 | 0 | 4 | **6** | $, E |
| 4 | C10 implementation not started | 5 | 4 | 4 | **2** | P, $ |
| 5 | Debt sculpting parity | 5 | 4 | 3 | **3** | P, $ |
| 6 | Generic wind / solar validation | 4 | 4 | 4 | **0** | P, $ |
| 7 | Approval / signoff orchestration | 4 | 0 | 3 | **5** | $, E |
| 8 | Audit-export package for paid tier | 4 | 0 | 3 | **5** | $ |
| 9 | R99 / R102 audit chain closure | 4 | 3 | 3 | **2** | P, $ |
| 10 | R67 cash-tax bridge residual | 3 | 3 | 3 | **0** | P, $ |
| 11 | Oborovo distribution lockup residual | 3 | 3 | 2 | **1** | P |
| 12 | Oborovo SHL / CFADS waterfall residuals | 3 | 3 | 3 | **0** | P |
| 13 | CAPEX per-line runtime not wired | 3 | 1 | 3 | **2** | P |
| 14 | Auto-backup observability (logs only) | 2 | 0 | 1 | **3** | P |
| 15 | Replay-engine behavior | 3 | 0 | 3 | **3** | $, E |

### 7.2 Read of the rank

- **The parity block (R-PAR-2, R-PAR-5, debt sculpting,
  generic, C10) is a tight cluster** with composite scores
  around 2-3. These are all "the model is not yet right"
  items. They share the same critical path
  (R-PAR-2 → R-PAR-5 → C10) and the same governance gate
  (an external or peer review is required to accept the
  design).
- **The multi-user / RBAC / SSO item** (composite 6) is the
  single highest-leverage architectural item, because it
  is the **only** blocker that is required for paid product
  and that is also a prerequisite for several other paid
  items (audit-export package, replay-engine, signoff
  orchestration).
- **The G-track UX items** (CAPEX per-line runtime, auto-
  backup observability) are **not** in the top 15 because
  they were already partly addressed by the G track
  itself (legend, deferred, S&U bridge, export lineage).

### 7.3 Critical path

The pilot critical path is the same critical path that
`phase_pilot_readiness_gap_analysis.md` identified:

```
R-PAR-2 → R-PAR-5 → C10 (runtime seam) → C10 (sculpting) → Generic F3
```

The paid-product critical path is:

```
Multi-user / RBAC / SSO → Audit-export package → Signoff → Replay → Pricing / SLA / Contract
```

The two critical paths are **independent**. The G track ran
in parallel with both. The G track is now closed.

---

## 8. Explicit answers to the four questions

### 8.1 A. Can a finance user build and test a project today?

**Yes, with caveats.**

- ✅ A finance user can build a project on **TUHO** (validated
  frozen-template path).
- ✅ A finance user can build a project on **Oborovo**
  (validated frozen-template path).
- ✅ A finance user can run the model, see the runtime
  summary, compare scenarios, download artefacts.
- ✅ A finance user can use the G-track UX improvements
  (stale warning, validation clarity, run status, status
  legend, S&U bridge, export lineage).
- ⚠️ The runtime output will **disagree** with the Excel
  reference on:
  - Senior IDC effective rate (R-PAR-2 open)
  - Equity total derived (R-PAR-5 open)
  - Cash-tax bridge residual (R67 open)
  - Oborovo distribution lockup (open)
  - Oborovo SHL / CFADS waterfall residuals (open)
- ⚠️ The finance user **cannot** change assumptions and see
  the sculpted senior debt (debt service is frozen from
  Excel).
- ⚠️ The finance user **cannot** sign off an audit pack
  (R99 / R102 chain not green).

**Verdict for finance user (TUHO / Oborovo):**
**Yes**, the user can build, run, inspect, compare, and
download. The user **cannot** rely on the numbers for a
lender review or an external audit signoff.

**Verdict for finance user (generic wind / solar):**
**No**, the user should not build a generic project and
rely on the numbers, because the generic path is not
validated.

### 8.2 B. Can a renewable developer build and test a project today?

**No, not in the way a renewable developer would expect.**

- ⚠️ A renewable developer typically wants to:
  - Sketch a project in the generic templates.
  - Edit assumptions.
  - See the IRR / DSCR / cash flow respond.
  - Iterate quickly.
- ❌ The generic templates run, but the output is
  **unvalidated** (F-series open).
- ❌ The senior debt does **not** re-sculpt when the
  developer changes assumptions (debt service is frozen).
- ❌ The construction-period engine is **not wired** (C10
  open).
- ❌ The CAPEX per-line runtime is not exposed (the display
  is there, but the runtime is not wired).

**Verdict for renewable developer:**
**No**, the product is not yet a "sketch a project, see
the IRR respond" tool. The product is a "reproduce a
validated TUHO / Oborovo project from a frozen Excel
reference" tool.

### 8.3 C. What is the single highest-value feature missing?

**The single highest-value feature missing is the ability
to edit assumptions and see the senior debt re-sculpt in
real time.**

Concretely: when a pilot user changes the PPA price, the
project IRR / DSCR / cash flow should re-compute, and the
senior debt service should re-sculpt to maintain the
target DSCR. Today, the senior debt service is frozen
from the Excel reference, so changing the PPA price moves
the IRR but **does not** move the senior debt service.
The result is an inconsistent cash-flow waterfall that
confuses the pilot user and makes the model look broken
even when the inputs are reasonable.

This is a **single feature** with three layers:

1. **Layer 1 (UX, low risk):** surface the "frozen senior
   DS path" warning in the runtime summary so the pilot
   user knows the senior debt is frozen.
2. **Layer 2 (architecture, medium risk):** wire the
   sculpting solver into the runtime waterfall.
3. **Layer 3 (parity, high risk):** validate the
   sculpting solver against the Excel reference across
   TUHO and Oborovo.

Layer 1 was already partly addressed in 24-G-2
(`_last_run_indicator.html` warning row). Layer 2 is the
**C10 implementation** that the C-series is designing.
Layer 3 is the **R-PAR-2 / R-PAR-5** work.

The single highest-value **feature** is the full stack
(1 + 2 + 3). The single highest-value **slice** is
Layer 1 (the warning) — which is already done. The
single highest-value **remaining work** is Layer 2
(the runtime seam wiring) + Layer 3 (the parity
validation).

### 8.4 D. What should Sprint 24-H be?

**Sprint 24-H should be a "Live Sculpting / In-app Debt
Re-sizing" sprint** with two parallel tracks:

**Track A: Runtime seam wiring (architectural, L effort)**

- Wire `app/services/construction_runtime_seam.py` into
  the waterfall.
- Add a feature flag `use_sculpting_solver` (default
  `False` to preserve parity with the frozen path).
- Add a "live sculpting" toggle in the project header
  that, when ON, uses the in-app solver instead of the
  frozen debt service.
- Add a "sculpting parity" badge that shows whether the
  in-app solver matches the Excel reference within
  tolerance.

**Track B: Senior IDC effective-rate resolution (parity, M effort)**

- Resolve the R-PAR-2 senior IDC effective-rate caveat
  (per the decision pack in PR #562).
- Implement the chosen option (likely Option B: hybrid
  accrual with effective-rate snapshot).
- Add a fixture-backed test that asserts the senior IDC
  is within ±1% of the Excel reference.
- Add a parity guardrail that fails the CI if the
  senior IDC delta exceeds ±1%.

**Track C: UX follow-ups (S effort, parallel)**

- Auto-backup observability (24F.1) — surface "Last
  backup: 3 hours ago" in the project header.
- Per-project reproducibility (deterministic seed).
- "Report a bug" surface in the runtime summary.

**Why this is the right next sprint:**

1. **It unblocks the pilot critical path.**
   R-PAR-2 + C10 + sculpting is the pilot critical path.
   24-H addresses all three in one sprint with a
   feature-flagged rollout.
2. **It respects the G-track discipline.**
   24-H will be implemented **in parallel** with the G
   track, not as a replacement. The G track is closed.
3. **It honors the "no implementation in this turn"
   constraint.** This document does not implement any
   of the above; it only recommends it for the next
   sprint.
4. **It is feature-flagged.** The default remains the
   frozen, parity-preserving path. The new in-app
   sculpting is opt-in. This means 24-H can ship
   without breaking the existing pilot workflow.
5. **It has a clear "done" definition.** The senior IDC
   is within ±1% of Excel. The sculpting solver
   matches the Excel reference across TUHO and
   Oborovo. The runtime seam is wired and called by
   the waterfall. The "live sculpting" toggle works.

---

## 9. What this document does NOT do

This is a **report-only, docs-only, shape-tests-only**
closure review. It does **not**:

- Touch any production code.
- Promote any feature flag.
- Implement any of the items it ranks.
- Commit to a specific next sprint.
- Make any bank / lender / external audit claim.
- Modify the parity test suite.
- Modify the model.
- Modify the persistence layer.
- Touch C10, R-PAR, or any item in the parity chain.
- Touch rc1.

The machine-readable companion is
`reports/phase24g_closure_and_pilot_testability_review.json`.

---

## 10. Test footprint

This document introduces **shape-only characterization
tests** that assert:

- The document exists.
- The document has 10 sections.
- The document names all 4 G-track PRs (#564, #566/#567,
  #565/#568, #569/#570) and their merged / closed status.
- The document answers the 4 explicit questions (A, B, C, D).
- The document ranks the top 15 blockers with composite
  scores in the range [0, 10].
- The document does not name any production code path
  that is in scope for the G track (no `main_web.py`,
  `app/services/`, `app/persistence/`, `app/domain/`,
  `app/api/`, `app/tax_bridge/`, `waterfall_core.py`,
  `static/app.js`, `model/`, `formula/`, `tax/`, `debt/`,
  `depreciation/`, `IDC/`, `rc1`).
- The document does not flip any feature flag value.
- The document does not change `use_construction_schedule_engine`
  (it remains `False`).

No regression tests are modified. No production tests are
modified. No golden-value assertions are modified. No
fixture files are modified.

---

## 11. References

- `docs/phase_pilot_ux_safe_track_inventory.md` (PR #564)
- `docs/phase24g1_stale_run_warning_validation_summary_clarity.md` (PR #567)
- `docs/phase24g2_run_status_clarity_validation_summary_completion.md` (PR #568)
- `docs/phase24g3_capex_sheet_readability_export_download_clarity.md` (PR #570)
- `docs/phase24_closeout_pilot_readiness_review.md` (PR #326)
- `docs/phase24c1_24f_pilot_safety_decision.md` (PR #324, #325)
- `docs/phase_pilot_readiness_gap_analysis.md` (PR #559)
- `docs/pilot_ux_walkthrough_checklist.md`
- `docs/pilot_user_guide.md`
- `docs/pilot_rc_readiness_checklist.md`
- `docs/pilot_rc_scope_matrix.md`
- `docs/pilot_readiness.md`
- `reports/phase_pilot_ux_safe_track_inventory.json`
- `reports/phase24g1_stale_run_warning_validation_summary_clarity.json`
- `reports/phase24g2_run_status_clarity_validation_summary_completion.json`
- `reports/phase24g3_capex_sheet_readability_export_download_clarity.json`
- `reports/phase24g_closure_and_pilot_testability_review.json` (this report)
