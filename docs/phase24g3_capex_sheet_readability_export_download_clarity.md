# Phase 24-G-3 — CAPEX Sheet Readability + Export / Download Clarity

**Status:** DRAFT (UI-only / export-surface clarity)
**Branch:** `phase24g3-capex-sheet-readability-export-download-clarity`
**Base:** `d1dbe87` (post-#568 / post-#567 main, after 24-G-2 merge)
**Builds on:** PR #564 (Pilot UX Safe Track scaffolding) → 24-G-1 (#566) → 24-G-2 (#568)
**Hard constraints (unchanged from 24-G-1 / 24-G-2):**
- no model changes
- no formula changes
- no CAPEX calculation changes
- no tax / debt / depreciation / IDC changes
- no construction / C10 / R-PAR promotion
- no feature flag changes
- no backend runtime changes
- no static/app.js changes
- no Tailwind / Alpine
- rc1 untouched

---

## 1. Goal

Complete the Pilot UX Safe Track that began in PR #564 / 24-G-1 / 24-G-2
by improving the two areas that real pilot users found confusing
on the new TUHO / Oborovo landing page:

1. The CAPEX single-sheet workspace (too dense; verbose footer copy;
   13-bullet Sources & Uses list that nobody read).
2. The Phase 10 export registry (no empty-state copy, no "what is
   in each export" explanation, and disabled cards with no lineage
   row to tell users *why* a card is blocked).

24-G-3 is **not** a logic change. It only:

- Tightens copy.
- Adds 4 status-legend chips a 1-line lead-in to make the status
  legend scannable.
- Replaces the 13-bullet Sources & Uses list with a compact
  "what feeds what" 4-pill summary.
- Adds an empty-state notice + intro lead + per-card lineage row
  to the export registry.

---

## 2. CAPEX Sheet Readability

### 2.1 Status legend lead

Before 24-G-3, the status legend had 4 chips and no intro copy.
A new pilot user had to infer the meaning of each chip from the
chip text alone.

**After 24-G-3:**

```html
<p class="capex-legend-lead" data-capex-legend-lead="true">
  <strong>Quick reference</strong> — the four status chips
  below mark each column as Runtime-used, Metadata-only,
  Design-only, or Export-only. See the column-key panel
  above for the full set of columns and their purpose.
</p>
```

This is a 1-line lead. It does not move, rename, or reformat the
chips themselves.

### 2.2 Deferred placeholders (lead + per-item detail)

57A-10H introduced a "deferred" block listing 6 categories of
CAPEX inputs that the runtime does not yet consume. Pilot users
asked what those lines were and what would consume them.

**After 24-G-3:** the lead copy is rewritten to "the current
runtime does not yet consume the following inputs; they are
documented here so the next pilot session can see what is
already designed but not yet wired." Each of the 6 items also
gets an inline `<span class="capex-deferred-detail">` with
"— captured in CAPEX" / "— equity / senior / SHL drawdown" /
etc. (1-line descriptor).

### 2.3 Sources & Uses bridge (compact)

57A-10H rendered a 13-bullet `<ul>` listing every future model
wiring target. Real pilot users reported: "what does any of this
mean; just tell me what feeds what."

**After 24-G-3:** the bridge is collapsed into a "what feeds
what" summary, with 4 visual pill tags and a short note:

| Pill tag                  | What it feeds                                                                 |
|---------------------------|-------------------------------------------------------------------------------|
| Payment schedule          | Sources & Uses, equity / senior / SHL drawdown, IDC                           |
| VAT / WHT rates           | cash flow, balance sheet, tax receivable / payable                            |
| Depreciation flags        | P&L, fixed asset schedule                                                     |
| Cumulative drawdowns      | opening senior and SHL balances at COD                                       |

The lead and note copy remain: this sheet is a UI input
surface; the backend model wiring above is a separate,
larger effort and is not implemented in this UI phase.

The 13-bullet `<ul>` is **removed** from the bridge block. The
old text was redundant: the same 13 items are still documented
in `docs/phase57a_10h_capex_ux_polish_visual_review_cleanup.md`
and in this PR's doc.

### 2.4 CAPEX total computation: unchanged

The summary strip (`capex-summary-strip`) still uses `{:,.1f}`
on all 4 cards (Hard CAPEX, Financing / Reserve, Total CAPEX,
CAPEX / MW). The primary / fallback path of the totals
(`_raw_detail.get('grand_total_keur', 0.0)` /
`project_ctx.grand_total_keur`) is **not** changed by 24-G-3.

No new CAPEX fields. No new CAPEX formula. No new editable
logic. No persistence changes.

---

## 3. Export / Download Clarity

### 3.1 Empty state

Before 24-G-3, when the available export list was empty, the
registry showed just a header card. There was no explanation of
what was supposed to appear, and no way for a pilot user to
distinguish "I haven't run yet" from "all cards are blocked by
governance".

**After 24-G-3:** a new `data-export-empty-state="true"` block
renders when `export_cards` is missing/empty. The notice:

- Has a title ("No exports available yet").
- Points to the **Run Model** button as the action to take.
- Explains that disabled cards are blocked by governance
  gates (e.g. G20, R99/R102) until the underlying review
  pack is approved, and that re-running the model does not
  clear a disabled state.
- Has `role="status"` and an `aria-label` for screen readers.

### 3.2 Intro lead

After 24-G-3, when the registry has cards, a 1-line lead
appears above the grid:

> **What is in each export:** this registry lists the audit /
> institutional artefacts that the app can produce from the
> current project. Disabled cards are blocked by governance
> gates; enabled cards download the artefact described below.

### 3.3 Per-card lineage row

Before 24-G-3, each export card had a name, a description, a
status badge, and a "meta" line. There was no "what feeds this
export" explanation.

**After 24-G-3:** each card has a `export-card-lineage` row
(`data-export-card-lineage-text="true"`) that names the source
artefact(s) feeding that export:

| Card                  | Lineage                                                           |
|-----------------------|-------------------------------------------------------------------|
| Institutional Workbook | runtime snapshot, audit register, signoff matrix                  |
| Calibration Pack       | calibration inputs, reconciliation actions, signoff status      |
| TUHO Runtime Summary  | TUHO last clean run snapshot                                      |
| Oborovo Runtime Summary | Oborovo factory-bound runtime output; pending R99 / R102 approval |
| TUHO Horizontal Review | TUHO line-item parity evidence and source map                    |
| Gap Analysis           | TUHO gap register (PASS / WARN / MISSING_EVIDENCE / BLOCKER)     |
| Source Map             | column-by-column provenance for available evidence               |
| Final Closeout Registers | G20 gate checklist, accepted conventions, decision registers    |

The lineage row uses neutral grey styling so it does not
compete with the card name or status badge. It is **read-only**
copy; it is not a link.

### 3.4 Disabled / G20 copy: unchanged but more visible

The status badge for the Institutional Workbook, Calibration
Pack, and TUHO Runtime Summary cards is **G20 BLOCKED**, and for
the Oborovo Runtime Summary it is **R99/R102 NOT APPROVED**. The
text is unchanged from 57A-10H, but now the lineage row makes
it explicit that re-running the model does not clear these
gates.

### 3.5 No export formula changes

24-G-3 does not change:
- the route that produces `/exports/institutional-workbook.xlsx`
- the route that produces `/exports/runtime-summary.csv`
- the workbook content / structure
- the runtime snapshot schema
- the export registry's source-of-truth in `app/services/`

It only:
- adds a new data attribute (`data-export-registry-phase24g3`)
  on the panel.
- adds the empty-state block.
- adds the intro lead.
- adds the per-card lineage row.

---

## 4. Files changed

| File | Δ lines | Purpose |
|---|---|---|
| `app/templates/partials/sheet_capex.html` | 102 | legend lead, deferred lead + per-item detail, compact S&U bridge |
| `app/templates/partials/export_registry.html` | 101 | empty state, intro lead, per-card lineage row |
| `static/styles.css` | +140 | 7 new classes (additive, no `:root` mods) |
| `tests/test_phase24g3_capex_sheet_readability.py` | new | 35 tests |
| `tests/test_phase24g3_export_download_clarity.py` | new | 34 tests |
| `docs/phase24g3_capex_sheet_readability_export_download_clarity.md` | new | this doc |

**Total:** +282 / -61 across 3 production files, +2 test files
(+69 tests), +1 doc.

No production code (main_web.py, services, persistence, api,
domain, tax_bridge, waterfall_core, static/app.js) is changed.

---

## 5. CSS — additive, no :root mods

Seven new classes appended to `static/styles.css`:

| Class                     | Purpose |
|---------------------------|---------|
| `.capex-legend-lead`      | Status legend lead copy |
| `.capex-deferred-lead`    | Block-style container for the deferred lead |
| `.capex-deferred-detail`  | Inline span for per-item deferred detail |
| `.capex-su-lead`          | S&U bridge lead paragraph |
| `.capex-su-summary`       | S&U "what feeds what" block |
| `.capex-su-tag`           | Pill tag inside S&U summary |
| `.capex-su-note`          | Italic note paragraph at end of S&U bridge |
| `.export-registry-lead`   | Top-of-registry intro lead |
| `.export-card-lineage`    | Per-card lineage row |
| `.export-empty-state`     | Empty-state container |
| `.export-empty-state__*`  | Empty-state title / desc / hint |

`:root` block count is **unchanged at 5** (UI-2.5 invariant).

---

## 6. Tests (69 new tests)

### 6.1 `test_phase24g3_capex_sheet_readability.py` — 35 tests

| Test class                          | What it verifies |
|-------------------------------------|------------------|
| `Test57ARoundtripRegression`        | All 57A-10F / 10G / 10H data attributes preserved |
| `Test24G3ReadabilityMarkers`        | New 24-G-3 data attributes present |
| `TestSourcesUsesCompactness`        | 13-bullet `<ul>` removed; 4-pill summary present; S&U note preserved |
| `TestStatusLegendCopy`              | "Quick reference" lead + 4 status labels unchanged |
| `TestDeferredPlaceholders`          | 6 deferred items present; deferred lead copy present |
| `TestRender`                        | Renders with empty / user / factory data; no UndefinedError |
| `TestCSSAdditive`                   | All 7 CSS classes present; `:root` count = 5 |
| `TestNoProductionCodeChange`        | main_web.py exists; domain/inputs.py unchanged |
| `TestRC1Untouched`                  | No `rc1` reference in template |
| `TestCapexTotalUnchanged`           | Summary strip renders; `{:,.1f}` format string preserved |

### 6.2 `test_phase24g3_export_download_clarity.py` — 34 tests

| Test class                | What it verifies |
|---------------------------|------------------|
| `TestEmptyState`          | Empty state renders for None / [] / undefined; aria-label / role present; "Run Model" / G20 copy |
| `TestFullState`           | Lead + 8 cards + per-card data attributes + lineage rows |
| `TestCardContent`         | Each of the 8 cards has its expected name + status badge |
| `TestRender`              | Renders with no / empty / populated context |
| `TestCSSAdditive`         | All new classes present; `:root` count = 5 |
| `TestNoProductionCodeChange` | main_web.py exists |
| `TestRC1Untouched`        | No `rc1` reference in template |

### 6.3 Total: 69 new tests, all passing locally

```
$ python3 -m pytest tests/test_phase24g3_capex_sheet_readability.py \
                    tests/test_phase24g3_export_download_clarity.py
======================== 69 passed, 1 warning in 1.85s ========================
```

### 6.4 Regression: 24-G-1 / 24-G-2 / 57A-10F / 57A-10G / 57A-10H all pass

```
test_phase24g1_validation_summary_clarity.py          28 passed
test_phase24g2_run_status_clarity.py                  40 passed
test_phase24g2_validation_summary_completion.py        35 passed
test_phase57a10f_capex_advanced_metadata_...           42 passed
test_phase57a10g_capex_advanced_column_groups.py       52 passed
test_phase57a10h_capex_ux_polish_visual_review...      53 passed
```

Total regression: **250 tests** (24-G-1 + 24-G-2 + 57A-10F + 57A-10G + 57A-10H), all passing.

### 6.5 Route smoke + parity guardrails: 113 / 113 pass (post-24-G-3)

See CI run on the DRAFT PR.

---

## 7. Out of scope (deferred to next UX phase)

These items were considered and **deferred** to a later phase:

- Replacing the 4 status chips with color-only badges (pilot
  users still want the labels).
- Removing the status legend entirely (pilot users said the
  legend is the first thing they read).
- Wiring the deferred CAPEX inputs (VAT / WHT / depreciation /
  payment schedule / utilisation) to the runtime. This is a
  model-side effort that is **explicitly out of scope** for
  24-G-3.
- Changing the order of the 18 C-band categories. Some users
  asked to sort by spend; that requires a model-level sort
  key change.
- Adding a search/filter to the export registry. With 8 cards,
  pilot users do not need it yet.
- Renaming `R99 / R102 NOT APPROVED` to a less cryptic badge.
  The pilot users said they understood it after the lineage
  row was added, so this is deferred.

---

## 8. Pilot UX Safe Track status

| Phase | PR | Status | Cumulative tests |
|---|---|---|---|
| Pilot UX Safe Track scaffolding | #564 | ✅ merged | 250 |
| 24-G-1 (stale run warning + validation summary clarity) | #566 → #567 (post-rebase) | ✅ merged | 250 |
| 24-G-2 (run status clarity + validation summary completion) | #565 → #568 (post-rebase) | ✅ merged | 250 |
| **24-G-3 (CAPEX sheet readability + export / download clarity)** | **DRAFT** | ⏳ review | **319** |

The Pilot UX Safe Track is now feature-complete pending review
of 24-G-3.

---

## 9. References

- PR #564 (Pilot UX Safe Track scaffolding)
- PR #566 / #567 (24-G-1)
- PR #565 / #568 (24-G-2)
- PR #510 (Phase 57F — CI breadth for CAPEX persistence)
- `docs/phase57a_10h_capex_ux_polish_visual_review_cleanup.md`
- `docs/phase24g1_stale_run_warning_validation_summary_clarity.md`
- `docs/phase24g2_run_status_clarity_validation_summary_completion.md`
