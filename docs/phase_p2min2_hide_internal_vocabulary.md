# Phase P2-min-2 — Hide Internal Vocabulary (presentation only)

**Type:** Presentation / UX simplification
**Base:** branch `p2-min-1-project-home-minimal-new-project` (PR1 DRAFT, PR #609)
**Status:** DRAFT, awaiting review

---

## Goal

Relocate internal implementation vocabulary from the
normal user UI to the Export & Audit area. The
brief: one clear status line per screen saying
**"Internal-use model — results are indicative."**

**Hidden ≠ deleted.** Factory templates (TUHO,
Oborovo), baselines, parity, calibration, G20, R99,
R102, and runtime-source labels remain reachable
from `/projects/browse`, the audit fixture paths,
and the export registry. They are not deleted.

---

## What changed

### New: `_generic_status_line.html` partial

A small partial that renders the brief-approved
status line for any project where the
generic-disclosure rule applies. Includes the
single line: *"Internal-use model — results are
indicative."* with a small dot icon.

Renders nothing when the project is not
exploratory (e.g., TUHO / Oborovo factory
projects).

### `workspace_shell.html`

The new partial is included at the top of the
Overview panel (one clear status line per screen).

### `static/styles.css`

A small `.generic-status-line` CSS block that
reuses the existing CSS variables
(`--surface`, `--border`, `--text-2`). No new
dependency.

### `tests/test_phase_p2min2_hide_internal_vocabulary.py`

15 tests across 7 test classes:

- `TestGenericDisclosureRule` (2 tests) — the
  partial exists, the copy is brief-approved, and
  it is included in `workspace_shell.html`.
- `TestProjectHomeStaysClean` (3 tests) — the
  Project Home (PR1) partial does not expose
  factory / parity / calibration / G20 / R99 / R102
  / TUHO / Oborovo / OBR-001 in rendered visible
  text.
- `TestMinimalFormStaysClean` (1 test) — the
  minimal New Project form (PR1) does not expose
  internal vocabulary in rendered visible text.
- `TestExportAuditStillExposesAuditInfo`
  (2 tests) — the audit reconciliation tab and
  the export registry still expose the full
  audit / parity / calibration vocabulary.
- `TestNoRenameOfImplementationDetails` (3 tests)
  — route names, factory template options, and
  `project_origin` literals are not renamed.
- `TestPhaseInvariants` (3 tests) — rc1 SHA,
  `use_construction_schedule_engine=False`, and
  Phase 51F parity guardrails.
- `TestPriorPhaseTestsPreserved` (1 test) — the
  full prior-phase test stack
  (PR1+PR2+PR3+M1+P1-A+P1-B+51F+P2-min-1) passes.

### Cross-arc test patches

The P2-min-2 follow-up adds five new file paths
(`_generic_status_line.html`, `workspace_shell.html`,
`docs/phase_p2min2...`, `reports/phase_p2min2...`,
`tests/test_phase_p2min2...`). The file-scope
allowlist in the following tests is extended to
include the new paths:

- `tests/test_phase_pr1_form_timing_fields.py`
- `tests/test_phase_pr2_realized_gearing.py`
- `tests/test_phase_pr3_taxonomy.py`
- `tests/test_phase_m1_scenario_matrix.py`

---

## What did NOT change (pinned by tests)

- No formula changes
- No debt sizing changes
- No DSCR sculpt semantics changes
- No TUHO / Oborovo factory path changes
  (hidden ≠ deleted)
- No Excel goldens changes
- No tax / depreciation / IDC changes
- No construction / C10 / R-PAR changes
- No `manual_gearing` / `gearing_cap` /
  `min(gearing_cap, sculpt)` blend
- No R99 / R102 / G20 promotion
- No persistence schema migration
- No `app/services/` downstream service code
  changes
- No `app/persistence/` changes
- No `static/app.js` changes
- No `main_api.py` changes
- No Tailwind / Alpine / React / Vue / Svelte
- No Chart.js / Plotly / D3
- No new dependency
- No JS calc
- No route rename
- No CSS class rename
- No context-key rename
- No test rename
- `use_construction_schedule_engine` remains
  False
- rc1 SHA preserved

---

## Roadmap (post-PR2)

PR2 is the second PR in the P2-min stacked UX
simplification arc:

1. **PR1** (PR #609) — Project Home + Minimal New
   Project
2. **PR2** (this PR) — Hide Internal Vocabulary
3. **PR3** — Dashboard v1 (depends on PR2)
4. **PR4** — Navigation Compression (depends on
   PR3)

`manual_gearing` is **not** on this roadmap.

DO NOT START: PR3 until PR2 is approved and merged.
DO NOT START: M2, pilot execution, persistence
changes, scenario override implementation.

---

## Test results

- **15 / 15** P2-min-2 tests PASS
- **342 / 342** cross-arc tests
  (PR1+PR2+PR3+M1+P1-A+P1-B+51F parity+P2-min-1+P2-min-2)
- 21 / 21 Phase 51F parity guardrails PASS
- 0 failed
- rc1 SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4`
  preserved
- `use_construction_schedule_engine` remains
  False

---

## Stop-after-report contract

DRAFT PR only. Do NOT mark ready. Do NOT merge.
Awaiting user review and explicit go-ahead before
PR2 lands on PR1.
