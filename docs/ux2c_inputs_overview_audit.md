# UX-2C — Inputs & Overview Excel-Feel Cleanup: UX Audit

**Phase:** UX-2C (analysis only — no code changes, no PR)
**Base:** `main` @ `a823ffb17c47b355e62ae8430ac6479638231381`
**Scope of this document:** Inputs tab, Overview/Dashboard tab, New Project flow.
**Out of scope (not touched by this audit or any future implementation of it):**
domain/*, waterfall logic, calculations, persistence, scenario logic, exports,
APIs, validation engines. This is a presentation/UI-only investigation.

---

## 1. Method

A direct codebase inventory (file:line) was taken of every governance/status/
technical badge, label, and KPI-card surface touching Inputs, Overview, and
New Project. Each item below is classified:

- **Keep** — communicates something the end user genuinely needs to act on or
  trust the numbers.
- **Simplify** — useful information, but the current presentation is too
  loud/technical/duplicated; consolidate into a quieter form (icon + tooltip,
  single legend, single surface).
- **Remove** — internal/governance/pilot scaffolding with no end-user value;
  hide behind an expandable "Help"/audit surface or delete from the default
  view entirely.

---

## 2. Inputs tab

| # | Location (file:line) | Element | Purpose | User value | Recommendation |
|---|---|---|---|---|---|
| 1 | `inputs_section.html:7` / `sheet_inputs.html:7-9` | Sheet banner badge — `badge-pass` "User Project — editable" / `badge-muted` "Protected — read-only" | Tells the user whether they can edit this project's inputs | High — directly answers "can I type here?" | **Keep**, but simplify wording: "Editable" / "Read-only" (drop "User Project" / "Protected" prefixes, which are internal classification terms) |
| 2 | `inputs_section.html:74` | "Read-only" badge on protected originals | Marks factory/reference originals as non-editable | Medium | **Keep** (short, already simple) |
| 3 | `inputs_section.html:16-47`, `62-67` | Per-row caveat icons: `ƒ` (calculated), `⚠` (timing/DSCR-sculpt driver), `ⓘ` (indicative) + hover legend | Explains why some fields aren't plain numbers | High — this is good information design (already simplified in UX-1B) | **Keep** — this is the target pattern; extend it rather than reverting to text badges |
| 4 | `inputs_section.html:198` | "⚠ Unsaved edits" dirty-state badge | Warns the user their edits aren't saved yet | High | **Keep** |
| 5 | `inputs_section.html:209` | "EXPLORATORY" badge for generic/user-created projects | Internal classification: distinguishes factory-validated vs ad-hoc projects | Low-Medium for a first-time user; the *information* (this project uses generic defaults, not a validated factory template) has value, but the all-caps governance-style word "EXPLORATORY" reads as a warning/error | **Simplify** — reword to something like "Custom project" with a one-line tooltip, not a red/warn-styled badge |
| 6 | `inputs_section.html:179-180` | Governance gate badges "BLOCKED" / "NOT_APPROVED" (G20/R99/R102) | Internal audit/governance gate status | None to an end user — these are internal control IDs | **Remove** from default Inputs view. Already audit-mode-only; confirm it never renders outside `audit_mode` and is absent from the normal workflow |
| 7 | `inputs_section.html:219-252` | Driver-status legend block (multi-paragraph, shown for exploratory projects) | Explains DSCR sculpt drivers / timing drivers / indicative gearing in prose | Medium — useful the first time, noisy every time | **Simplify** — collapse into a single "[ ? What do these icons mean ]" expandable section (same `<details>` pattern as the UX-2A CAPEX Guide), default collapsed |

### Inputs tab — labels named in the task brief, mapped to the inventory

| Label named in brief | Where it actually lives | Verdict |
|---|---|---|
| INTERNAL | `badge-info`/`badge-muted` "Internal" usages across various partials (e.g. workspace shell badges, scenario tab) | **Remove** from user-facing surfaces; internal-only wording |
| SAVED | `ph-status` ("Clean Saved State" etc.), dirty-state chip | **Simplify** — fold into the single dirty/clean state chip (see Overview §3) |
| TEMPLATE | New Project "Template Source" field/badge | **Simplify** — rename to plain language ("Starting point") or remove as a separate concept once New Project is simplified (§4) |
| MODEL DEFAULT | Implied by un-marked default values pre-fill in New Project extended form | **Remove as a label** — values should just look like normal editable fields; no need to flag "this came from a default" |
| CALCULATED | Caveat icon `ƒ` | **Keep** (already a quiet icon, not a badge) |
| USER PROJECT EDITABLE | Sheet banner badge text "User Project — editable" | **Simplify** → "Editable" (item #1 above) |
| TIMING DRIVER | Caveat icon `⚠` + tooltip | **Keep** (already quiet) |
| INTERNAL USE MODEL | New Project extended-form notice badge `badge-warn` "Internal-use model" for generic templates | **Remove/Simplify** — replaced by New Project simplification (§4); the distinction collapses once the form only asks 4-5 fields |
| USER CREATED PROJECT | "EXPLORATORY" badge condition (`is_user_created` / generic project) | **Simplify** (item #5 above) |

---

## 3. Overview / Dashboard tab

| # | Location (file:line) | Element | Purpose | User value | Recommendation |
|---|---|---|---|---|---|
| 1 | `_dashboard.html:57-71` | Dashboard KPI grid (≤8 cards, server-rendered) | Primary KPI surface | High | **Keep** — this should become *the* single KPI surface |
| 2 | `runtime_summary.html:42-409` | Runtime Summary KPI grid (10 cards: Project IRR, Equity IRR, Avg DSCR, CFADS, Senior Debt, Total CAPEX, Total Revenue, EBITDA, Total OPEX, Distributions) | Secondary/duplicate KPI surface, shown elsewhere in the workspace | Low marginal value — duplicates #1 for 6 of 10 metrics | **Remove as a second full surface.** Fold the unique metrics not already on the Dashboard (CFADS, Total CAPEX, Min DSCR if present, Distributions) into the single Overview KPI surface instead of keeping a parallel grid |
| 3 | `shared_runtime_block.html:141-204` | JS-rendered 8-KPI summary block reused on CAPEX/OPEX/Revenue tabs | Lets a user see context KPIs while editing a specific sheet | Medium, if kept tiny | **Simplify** — shrink to 2-3 KPIs most relevant to that sheet (e.g. CAPEX tab shows Total CAPEX + Senior Debt only), not a near-duplicate of the full Overview grid |
| 4 | `sheet_financials.html:475-487`, `sheet_tax.html:96-100`, `sheet_senior_debt.html:140-142`, `sheet_shl.html:92-95` | Per-sheet JS-rendered mini KPI lists (3-5 KPIs each, all overlapping Project IRR/Equity IRR/Avg DSCR) | Same context-reminder purpose as #3 | Low — four near-identical lists, inconsistent KPI sets per sheet | **Remove** these standalone duplicates; replace with one consistent "current run" mini-strip component reused everywhere (or none at all, given Overview is one tab-click away) |
| 5 | `_dashboard.html:49` | "Last run completed" badge | Confirms KPIs reflect a completed run | Medium | **Keep**, reword to plain confirmation text near the KPI surface rather than a standalone badge |
| 6 | `_dashboard.html:95` | "No KPIs" empty-state badge | Empty state | Medium (only shown when relevant) | **Keep** |
| 7 | `_dashboard.html:26` | "No run yet" CTA | Prompts the user to run the model | High | **Keep** |
| 8 | `runtime_summary.html:16` | `badge-runtime` "Scenario: [name]" | Identifies which scenario the numbers belong to | High — important to avoid mis-reading stale numbers | **Keep**, but display as plain text label next to the KPI surface, not a colored badge |
| 9 | `runtime_summary.html:21,27,29,412,431` | `badge-info`/`badge-pass`/`badge-blocked`/`badge-runtime` cluster: project origin, OK/ERROR, "Runtime", "Error" | Mix of lifecycle/governance signaling | Low-Medium, mostly redundant once duplicate surface (#2) is removed | **Remove** along with the Runtime Summary surface; keep only a single "stale vs current" indicator (see #11) |
| 10 | `runtime_summary.html:412-419` | "Runtime" badge + "Current workspace draft vs last completed run" notice | Tells user whether displayed numbers reflect unsaved edits | High — real risk of misreading stale numbers | **Keep**, consolidate into one small "Showing results for: \<scenario\> · as of \<run time\>" strip directly above the single KPI surface |
| 11 | (named in brief, not yet located verbatim) "Runtime Bound To Saved Scenario Snapshot" / "Clean Saved State" | `project_home.html:92-105` `ph-status` values, dirty-state chip system (`dirty_state_indicators.html`) | Internal lifecycle/state machine vocabulary surfaced directly to users | Low as worded; the underlying state (saved vs not, current vs stale) does matter | **Simplify** — rephrase to "Saved" / "Unsaved changes" / "Needs re-run" in plain language; drop "Runtime Bound To..." phrasing entirely |
| 12 | `_audit_governance_relocated.html:158-199` | Governance Status panel (G20/R99/R102/SHL/Distributions/Tax gate badges) | Internal control evidence | None for normal users (already gated to audit mode per earlier phases) | **Remove** from default Overview; confirm it stays exclusively in the Audit tab |
| 13 | `project_review_card.html:20-42` | Classification bar: "Exploratory project" / "Parity-validated" / "Protected original" with icons | Project provenance | Medium | **Simplify** — keep as one small icon+label, not a full colored bar with three possible variants described in governance language |

### KPI duplication summary (from investigation)

Project IRR, Equity IRR, and Avg DSCR currently render on **8 separate
surfaces** across the app (Dashboard, Runtime Summary, Shared Runtime Block,
Financials, Tax, Senior Debt, SHL, Project Review Card). Total Revenue and
EBITDA render on 5-6 of those. This is the single largest source of "where do
I look for the real number" confusion and the most actionable simplification
in this phase.

---

## 4. New Project flow

Two competing forms currently exist:

- **`new_project_minimal.html`** — 4 required fields: Project Name,
  Technology, Country/Market, Capacity (MW). Already close to the brief's
  target.
- **`new_project_form.html`** — 17 fields, including financial/debt
  assumptions (Gearing, Interest Rate, Tenor, Target DSCR, Tariff, PPA Term,
  OPEX Y1, Total CAPEX, etc.) and a "Use generic defaults" prefill button with
  an "Internal-use model" disclosure badge.

| Field (extended form) | Required today? | Recommendation |
|---|---|---|
| Project Name | Yes | **Keep — required** |
| Technology/Project Type | Yes | **Keep — required** |
| Country/Market | Yes | **Keep — required** |
| Capacity (MW) | Yes | **Keep — required** |
| Currency | Not currently a distinct field in either form (implicit) | **Add as optional** field per brief |
| Template Source | Yes | **Remove from the form** — derive automatically from Technology/Country, or fold into an internal "starting point" choice not shown as a required user decision |
| COD Date | Yes | **Move to Inputs** (already noted in the form's own copy as "read-only-derived for now") |
| Construction Months | Yes | **Move to Inputs** |
| Horizon Years | Yes | **Move to Inputs** |
| Tariff (EUR/MWh) | Yes | **Move to Inputs** |
| PPA Term Years | Yes | **Move to Inputs** |
| P50 Hours | Yes | **Move to Inputs** |
| OPEX Y1 (kEUR) | Yes | **Move to Inputs** |
| Total CAPEX (kEUR) | Yes | **Move to Inputs / CAPEX tab** |
| Gearing (%) | Yes | **Move to Inputs / Debt tab** |
| Interest Rate (%) | Yes | **Move to Inputs / Debt tab** |
| Tenor Years | Yes | **Move to Inputs / Debt tab** |
| Target DSCR | Yes | **Move to Inputs / Debt tab** |

**Recommendation:** standardize on the minimal form's shape
(`new_project_minimal.html`) as the single New Project entry point; retire
`new_project_form.html`'s 17-field variant. All financial/technical
assumptions get sensible template defaults at creation time and are then
edited through the Inputs sheet, consistent with "everything else entered
later through Inputs" in the brief.

---

## 5. Recommended removal list

1. Governance gate badges on Inputs (G20/R99/R102 "BLOCKED"/"NOT_APPROVED") — confirm audit-mode-only, remove from any default-path rendering.
2. "INTERNAL", "INTERNAL USE MODEL" badges/wording on Inputs and New Project.
3. Runtime Summary KPI grid (`runtime_summary.html`) as a *second* full KPI surface — collapse into the single Dashboard/Overview KPI grid.
4. Per-sheet duplicate mini-KPI lists on Financials/Tax/Senior Debt/SHL tabs (4 separate near-identical lists).
5. Governance Status panel on Overview (already relocated to Audit tab per earlier phases — verify and keep it that way, don't let it leak back).
6. "Runtime Bound To Saved Scenario Snapshot" / similar internal state-machine phrasing — replace with plain "Saved"/"Unsaved changes"/"Needs re-run" wording.
7. The 17-field extended New Project form (`new_project_form.html`) and its "Use generic defaults"/"Internal-use model" disclosure flow, in favor of the 4(+1)-field minimal form.
8. "Template Source" as a required, user-facing decision in New Project.

## 6. Recommended keep list

1. Sheet-level editable/read-only banner badge (simplified wording).
2. Caveat icon system (`ƒ`/`⚠`/`ⓘ`) on Inputs rows — this is the model UX-2C should generalize, not remove.
3. Dirty-state ("Unsaved edits") indicator.
4. "No run yet" / "No KPIs" empty states on the Dashboard.
5. Single Dashboard KPI grid, expanded to be the one authoritative KPI surface (Project IRR, Equity IRR, Avg DSCR, Min DSCR, Revenue, EBITDA, Senior Debt, CAPEX, per the brief).
6. Scenario name / "as of" run-time context line above the KPI surface (consolidated from the several Runtime badges).
7. Minimal New Project form (4 required + Currency optional).
8. Project classification icon (exploratory/validated/protected) in a compact, single-line form.

---

## 7. Inputs mockup proposal (Excel workbook feel)

Replace the current single long scrolling form with section-grouped rows that
read like a workbook's named ranges. Each section is a labeled block; each
row is `label — value` with an inline editable field where applicable (same
pattern already used for the per-row caveat icons, just extended consistently
across all sections and with badge clutter removed):

```
Identity
  Project Name        [ TUHO Wind 1                    ]
  Technology           Wind ▾
  Country               Romania
  Currency              EUR ▾

Schedule
  Construction Start    2026-01      ⚠ timing driver
  Construction Months   [ 18        ]
  COD                    2027-07      ƒ calculated
  Horizon (years)       [ 25        ]

Technical
  Capacity (MW)         50.0          ƒ calculated
  P50 Hours             [ 2,450     ]
  Capacity Factor       28.0%         ƒ calculated

Revenue
  Tariff (EUR/MWh)      [ 62.50     ]
  PPA Term (years)      [ 15        ]  ⚠ timing driver

CAPEX
  Total CAPEX (kEUR)    [ 52,800    ]   → see CAPEX tab for detail

OPEX
  OPEX Year 1 (kEUR)    [ 1,998     ]

Debt
  Gearing (%)           [ 70.0      ]  ⓘ indicative
  Interest Rate (%)     [ 4.25      ]  ⚠ DSCR sculpt driver
  Senior Tenor (years)  [ 16        ]  ⚠ DSCR sculpt driver
  Target DSCR           [ 1.30x     ]  ⚠ DSCR sculpt driver

Tax
  Tax Rate (%)          [ 16.0      ]
```

No section header carries a status badge. The single "Editable"/"Read-only"
indicator from §2 item 1 sits once, at the very top of the page (already the
case), not repeated per-section. The `⚠`/`ƒ`/`ⓘ` icon legend collapses into
one "[ ? What do these icons mean ]" expandable, matching the UX-2A CAPEX
Guide pattern.

---

## 8. Overview redesign proposal (single KPI surface)

Remove the Runtime Summary grid and all per-sheet mini-KPI duplicates. The
Overview tab becomes:

```
[ Scenario: Base · Results as of 2026-06-20 14:02 · Saved ]

  Project IRR    Equity IRR     Avg DSCR      Min DSCR
    11.4%          14.8%          1.42x         1.31x

  Revenue        EBITDA         Senior Debt   CAPEX
   8,420 kEUR    6,180 kEUR     43,359 kEUR   52,800 kEUR

[ No run yet ]  /  [ Run model ]   (only one of these CTAs, contextual)
```

One scenario/timestamp/saved-state context line, one 8-card KPI grid (the
brief's exact 8 metrics), one CTA. Everything else currently on
Overview — governance panels, duplicate Runtime Summary, classification
bars — either moves to the Audit tab (governance) or shrinks to a single
inline classification icon next to the project name (provenance).

---

## 9. New Project simplification proposal

Single form, 5 fields:

```
New Project

  Project Name *      [______________________]
  Technology *         Solar ▾ / Wind ▾
  Country *            [______________________]
  Capacity (MW) *      [______________________]
  Currency              EUR ▾   (optional, defaults to EUR)

  [ Create Project ]
```

Everything else (schedule, tariff, CAPEX, OPEX, debt terms, tax) is filled
with sensible template defaults at creation and edited afterward through the
Inputs sheet sections proposed in §7. This removes the "Template Source"
decision, the "Use generic defaults" button, and the "Internal-use model"
disclosure entirely — there is no longer a meaningfully different "generic"
vs "factory" creation path exposed to the user at this step.

---

## 10. Implementation plan (for a future UX-2C build phase — not this phase)

This phase is analysis-only; no code changes are made. A future
implementation phase should sequence as:

1. **Inputs:** generalize the existing caveat-icon pattern (already
   established in UX-1B) across all sections; remove/relocate the
   governance-gate badges and the multi-paragraph driver-status legend into
   a single collapsed Guide (reusing the UX-2A `<details>` pattern).
2. **Overview:** consolidate the Dashboard KPI grid and Runtime Summary grid
   into one 8-card surface with the brief's exact metric set; remove the
   per-sheet duplicate mini-KPI lists on Financials/Tax/Senior Debt/SHL;
   replace governance/runtime badge clusters with one scenario/timestamp/
   saved-state context line.
3. **New Project:** retire the 17-field extended form; promote the 4-field
   minimal form (adding optional Currency) to the only entry point; remove
   "Template Source" as a user-facing required field, deriving it
   server-side from Technology/Country.
4. Each step should ship as its own reviewable PR (mirroring the UX-2A
   pattern: template-only diffs, file-scope guardrail tests updated, a
   dedicated test file proving the specific UX requirement, before/after
   screenshots), with **no changes to domain/, persistence/, exports, APIs,
   or validation engines** at any step.

---

## 11. Confirmation

This document is the sole deliverable of UX-2C. No application code,
templates, or tests were modified. No PR was opened.
