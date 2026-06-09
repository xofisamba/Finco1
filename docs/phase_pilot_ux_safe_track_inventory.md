# Pilot UX Safe Track — Inventory & Ranking

> Type: REPORT ONLY, DOCS ONLY
> Status: DRAFT
> Date: 2026-06-09
> Base SHA: `233981e4` (post-pilot-readiness stack)
> Branch: `pilot-ux-safe-track-inventory`
> Hard constraints:
> - No code, no implementation
> - No runtime promotion
> - No waterfall routing
> - No flag flip
> - No senior IDC promotion
> - No Oborovo before TUHO
> - No model/formula change
> - No persistence/schema changes
> - DRAFT until reviewed
> - rc1 untouched
> - **Independence rule:** all items must be implementable
>   **independently of R-PAR-2 and C10** (so the parallel track
>   can proceed in parallel with the R-PAR-2 decision chain)

---

## 0. Purpose

A ranked inventory of low-risk, visible app improvements that
can ship **independently of the R-PAR-2 senior IDC decision and
the C10 implementation chain**. This is the **G (Pilot UX
hardening) parallel track** recommended in PR #561
(`phase_next_sprint_decision_matrix.md` §4.2).

Items are classified by:

- **User value** (1–5, 5 = highest)
- **Parity risk** (1–5, 5 = highest; ideally 0)
- **Implementation risk** (1–5, 5 = highest; ideally 1)
- **Effort** (S/M/L/XL)
- **Independence** — confirmed independent of R-PAR-2 and C10

The goal is a **safe track** that improves pilot satisfaction
without introducing any risk to model parity, runtime promotion,
or the construction-bridge chain.

---

## 1. The five categories

### 1.1 Run status clarity

**What it is:** the user-facing surface that shows the current
state of the last model run. Includes "clean / dirty" state, the
"runtime snapshot" age, and a clear indicator of when the user
needs to re-run.

**Current state (as documented in `phase14c_pilot_readiness_snapshot.md`):**

- "select a supported project template"
- "edit supported Revenue, OPEX, and selected Senior Debt assumptions"
- "save a scenario explicitly"
- "run the model from a clean saved boundary"
- "inspect backend-authored runtime summary"
- "compare saved scenarios"

**Pilot-UX friction observed (synthesized from
`phase15_pilot_feedback_instrumentation.md`,
`phase16_pilot_session_execution.md`,
`phase46_real_user_session_execution_feedback_analysis.md`):**

- Users are unclear **when the runtime snapshot is stale** relative
  to the saved scenario.
- The dirty / clean state of the workspace is not always obvious
  in the UI.
- The "last run" timestamp is sometimes hidden behind a click.
- The "what changed since last run" diff is not surfaced.

**Low-risk improvement candidates:**

1. **Surface the "last run age" prominently** — show
   "Last run: 3 minutes ago" in the project header.
2. **Add a "stale" badge** when the saved scenario has changed
   since the last runtime snapshot, with a one-click "re-run"
   button.
3. **Color-code dirty state** in the sidebar (subtle but visible).
4. **Show the diff between the current scenario and the last-run
   snapshot** in a tooltip or popover.

**Ranking:**

- **User value:** 4/5 (high — direct pilot friction)
- **Parity risk:** 0/5 (UI only, no model touch)
- **Implementation risk:** 1/5 (UI-only)
- **Effort:** M
- **Independence:** ✅ fully independent of R-PAR-2 / C10

### 1.2 Validation summary clarity

**What it is:** when the user saves a scenario or runs the model,
the validation layer reports any issues (e.g. missing required
inputs, out-of-range values, conflicting assumptions). The
current state is documented in `phase22b_uiux_audit_grid_polish_runtime_impact.md`.

**Pilot-UX friction observed:**

- Validation messages are sometimes too technical (e.g.
  "CapexItem.field_vat_operating is None" instead of "VAT
  operating cost: please enter a value").
- Multiple errors are sometimes shown in a flat list without
  grouping by section.
- There is no "fix and re-run" link from a validation error.
- The summary does not distinguish **blockers** (must fix) from
  **warnings** (review recommended).

**Low-risk improvement candidates:**

1. **Plain-language error messages** — translate technical
   field names into human terms.
2. **Group errors by section** (Inputs, CAPEX, OPEX, Senior
   Debt, etc.) with collapsible accordions.
3. **Distinguish blockers vs warnings** with clear visual cues.
4. **Add "fix" links** that take the user to the offending
   field.
5. **Show validation status on the scenario save button** (red
   for blockers, yellow for warnings, green for clean).

**Ranking:**

- **User value:** 5/5 (very high — every user hits validation)
- **Parity risk:** 0/5 (UI only)
- **Implementation risk:** 1/5 (UI + small error-message catalog)
- **Effort:** M
- **Independence:** ✅ fully independent

### 1.3 CAPEX sheet readability

**What it is:** the CAPEX input grid is the most complex surface
in the project workspace. Recent work (57A-10F/G/H) added
metadata, column groups, and UX polish.

**Pilot-UX friction observed (synthesized from
`phase57a10h_capex_ux_polish_visual_review_cleanup.md` and
related docs):**

- 15 CAPEX sub-lines are visible by default, which can be
  overwhelming for new users.
- Some advanced metadata columns (e.g. cost/MW derived,
  contingency, VAT/WHT/depreciation-basis) are visible by
  default but rarely used by pilot users.
- The "total CAPEX" line is at the bottom of the grid, not
  pinned.
- There is no quick-filter or search.

**Low-risk improvement candidates:**

1. **Default-collapse advanced columns** — show only the 4–5
   most-used columns by default; expand on demand.
2. **Pin the total CAPEX row** at the top of the grid.
3. **Add a search / quick-filter** to find a specific sub-line.
4. **Group sub-lines by category** (e.g. "turbines", "civil",
   "grid connection") with collapsible groups.
5. **Highlight cells that are part of a "complete" CAPEX
   profile** (vs an "incomplete" one).

**Ranking:**

- **User value:** 4/5 (high for first-time users)
- **Parity risk:** 0/5 (UI only)
- **Implementation risk:** 2/5 (touches 57A-10F/G/H area; need
  careful regression)
- **Effort:** M
- **Independence:** ✅ fully independent (no model impact)

### 1.4 Export/download clarity

**What it is:** the export pipeline produces multiple artefacts
(Excel workbook, calibration reconciliation, audit-export
bundle, ZIP publish). The current surface is documented in
`phase11_institutional_export_product_polish.md` and
`phase44_audit_export_hygiene_matrix.md`.

**Pilot-UX friction observed:**

- Users are sometimes confused about **which artefact they
  should download** for a given purpose (e.g. "for a lender
  review, download the calibration reconciliation; for a peer
  review, download the audit-export bundle").
- Export progress is not always visible (long-running exports
  may appear frozen).
- The download filename is not always descriptive enough
  (e.g. `export_2026-06-09.xlsx` vs
  `TUHO_calibration_reconciliation_2026-06-09.xlsx`).
- There is no "export history" — users re-export the same thing
  multiple times.

**Low-risk improvement candidates:**

1. **Add an "export guide" tooltip** that explains the purpose
   of each artefact.
2. **Show export progress** with a clear "Exporting… 60%"
   indicator.
3. **Use descriptive filenames** that include project name,
   artefact type, and date.
4. **Add an "export history"** (read-only) in the sidebar so
   users can re-download a recent export.
5. **Surface the "what was last exported, when, and by whom"**
   in the project header.

**Ranking:**

- **User value:** 3/5 (medium — most users learn the workflow)
- **Parity risk:** 0/5 (UI only)
- **Implementation risk:** 1/5 (UI + filename conventions)
- **Effort:** S
- **Independence:** ✅ fully independent

### 1.5 Stale run warning

**What it is:** when a saved scenario changes after a runtime
run, the next time the user opens the project, the runtime
summary they see is **stale** (from the previous run, not the
current scenario). The current state is documented in
`phase49d1_post_download_behavior_matrix.md` and
`phase49d2_post_download_extraction_matrix.md`.

**Pilot-UX friction observed:**

- The "stale" warning is not always surfaced prominently.
- Sometimes the warning appears as a small icon that users miss.
- There is no clear "what to do" — users may not realize they
  need to re-run.
- The "what changed" diff is not always shown.

**Low-risk improvement candidates:**

1. **Prominent "stale" banner** at the top of the runtime
   summary, with a one-click "re-run" button.
2. **Inline "stale" indicator** next to each KPI in the runtime
   summary.
3. **"What changed" diff** between the current scenario and the
   last-run snapshot, shown in a popover.
4. **Confirm-before-discard** prompt if the user tries to close
   the project while it's in a stale state.
5. **Audit log entry** when a stale state is detected.

**Ranking:**

- **User value:** 5/5 (very high — stale state is a top pilot
  complaint)
- **Parity risk:** 0/5 (UI only)
- **Implementation risk:** 1/5 (UI only)
- **Effort:** S
- **Independence:** ✅ fully independent

---

## 2. Consolidated ranking (by user value × parity risk)

| Rank | Item | User value | Parity risk | Impl. risk | Effort | Independence |
|---|---|---|---|---|---|---|
| 1 | Validation summary clarity | 5 | 0 | 1 | M | ✅ |
| 2 | Stale run warning | 5 | 0 | 1 | S | ✅ |
| 3 | Run status clarity | 4 | 0 | 1 | M | ✅ |
| 4 | CAPEX sheet readability | 4 | 0 | 2 | M | ✅ |
| 5 | Export/download clarity | 3 | 0 | 1 | S | ✅ |

**Composite score** (user_value × 2 - parity_risk - impl_risk):

1. Validation summary: 10 - 0 - 1 = **9** ✅
2. Stale run warning: 10 - 0 - 1 = **9** ✅
3. Run status clarity: 8 - 0 - 1 = **7** ✅
4. CAPEX sheet readability: 8 - 0 - 2 = **6** ✅
5. Export/download clarity: 6 - 0 - 1 = **5** ✅

---

## 3. Recommended safe-track sprint plan

**Sprint 24-G-1 (parallel to Sprint 24-A):**

- **Item 1 (partial):** Validation summary clarity — plain-language
  error catalog for top 20 validation errors.
- **Item 2 (full):** Stale run warning — prominent banner +
  one-click re-run.

**Sprint 24-G-2 (parallel to Sprint 24-B/C):**

- **Item 1 (completion):** Validation summary — group by
  section, blocker vs warning visual cues.
- **Item 3 (full):** Run status clarity — last-run age, dirty
  badge, what-changed diff.

**Sprint 24-G-3 (parallel to Sprint 24-D/E):**

- **Item 4 (full):** CAPEX sheet readability — collapse
  advanced columns, pin total, quick-filter.
- **Item 5 (full):** Export/download clarity — descriptive
  filenames, export progress, export history.

Each sprint is **independent** and can be sliced, reordered, or
deferred without blocking the others.

---

## 4. Hard-rule coverage

| Hard rule | How this PR complies |
|---|---|
| No code, no implementation | All items are design-only; no PRs open for these yet |
| No runtime promotion | None of the items touch the waterfall |
| No waterfall routing | None of the items touch the bridge |
| No flag flip | None of the items flip any feature flag |
| No senior IDC promotion | None of the items touch R-PAR-2 fields |
| No Oborovo before TUHO | None of the items touch Oborovo-specific surfaces |
| No model/formula change | All items are UI only |
| No persistence/schema change | None of the items add fields or change schema |
| All PRs DRAFT | This PR is DRAFT (the only PR in this stack) |
| rc1 untouched | rc1 not touched in this PR |
| Independence from R-PAR-2 / C10 | Confirmed for all 5 items |

---

## 5. What this document does NOT do

- No implementation
- No flag flip
- No promotion
- No commitment to a specific sprint
- No test impact (this is a report-only PR)
- No code change

The machine-readable companion is
`reports/phase_pilot_ux_safe_track_inventory.json`.

---

## 6. Test footprint

This PR introduces shape-only characterization tests that assert
the document exists, has the 5 sections (one per category), and
the consolidated ranking lists exactly 5 items with
`parity_risk=0` for each.
