# External Pilot Cleanup Sprint — Summary

Source docs: `external_pilot_terminology_audit.md`,
`external_pilot_new_project_review.md`,
`external_pilot_reference_project_review.md`,
`external_pilot_export_audit.md`,
`external_pilot_scenario_review.md`,
`external_pilot_guide_review.md`.

## 1. Executive summary

The prior pilot review concluded GO WITH CAVEATS — the model itself is
sound; the remaining issues are external-user clarity and presentation,
not correctness. This sprint confirms that finding in detail: every
substantive gap found is a wording, labeling, or CSS-class issue. No
engine, persistence, `app/services/*`, `app/project_factories.py`, or
`app/waterfall_core.py` change is required to close any of the identified
gaps. The single highest-priority item is a genuine user-facing leak: raw
internal sentinel strings (`factory_base_runtime`,
`project_factory:tuho/oborovo`) appear unmapped in the downloadable
runtime-summary CSV for both TUHO and Oborovo.

## 2. Findings by category

| Category | Doc | Key finding |
|---|---|---|
| Terminology sweep | `external_pilot_terminology_audit.md` | Remaining "factory" wording is almost entirely (D) internal-only CSS class names; one (A) user-facing form-help-text leak; one (A) disabled export card name |
| New project UX | `external_pilot_new_project_review.md` | Target "4-fields-only" flow is already implemented on the backend; only copy/sequencing gaps remain |
| TUHO/Oborovo UX | `external_pilot_reference_project_review.md` | "Protected original" + first-edit-copy flow already reads correctly; only CSS class names need renaming |
| Export terminology | `external_pilot_export_audit.md` | Runtime-summary CSV leaks raw sentinel values (high priority); disabled Calibration Reconciliation pack has hardcoded "Factory-bound" text (medium) |
| Scenario UX | `external_pilot_scenario_review.md` | KPI math is sound; scenario matrix column assignment is positional/creation-order-based rather than explicit, causing labeling confusion |
| Pilot documentation | `external_pilot_guide_review.md` | `external_pilot_guide.md` and `known_limitations_page.html` need targeted wording fixes; `pilot_user_guide.md` should be structurally split into external vs. internal docs |

## 3. User-facing blockers

Ranked by user impact, not by file count:

1. **Runtime-summary CSV sentinel leak** — raw internal strings in a
   button-click download. (A), highest priority.
2. **R99/R102 codes on the public Known Limitations page** — internal
   governance jargon shown without explanation. (A).
3. **"factory" wording in the new-project form help text**. (A), low
   severity but visible on a core flow.
4. **Scenario matrix positional column assignment** — UX confusion risk,
   not a terminology leak.
5. Everything else (CSS class names, doc wording in `external_pilot_guide.md`,
   the disabled Calibration Reconciliation Pack name) is lower-severity or
   not currently visible to a typical user.

## 4. Recommended cleanup order

1. Fix runtime-summary CSV sentinel-to-display mapping
   (`app/export/runtime_summary.py`) — mirrors the already-shipped XLSX
   fix pattern.
2. Reword the R99/R102 bullet on `known_limitations_page.html` and the
   three terms in `external_pilot_guide.md`.
3. Fix "factory" wording in `new_project_form.html` help text.
4. Rename CSS-only classes (`badge-factory`, `.ps-ap-origin--factory`,
   `.factory-lock-*`, etc.) across templates and `static/styles.css` in one
   commit.
5. Rename the disabled "Calibration Reconciliation Pack" card and its
   hardcoded "Factory-bound" cell text in `calibration_reconciliation.py`.
6. Address scenario matrix explicit slot assignment (larger UX change,
   schedule separately).
7. Split `pilot_user_guide.md` into an external guide and an internal
   audit guide (documentation-only, no app code).

## 5. Estimated effort

| Item | Effort |
|---|---|
| Runtime-summary CSV display mapping | Small (mirrors existing pattern) |
| Known Limitations / pilot guide wording fixes | Trivial (text-only) |
| New-project form wording fix | Trivial (text-only) |
| CSS class renames | Small (mechanical, multi-file, zero behavior change) |
| Calibration Reconciliation Pack rename | Trivial (text) + small (one hardcoded cell string) |
| Scenario matrix explicit slot assignment | Medium (UX + state change, not in this sprint's "no code yet" scope) |
| Pilot guide doc split | Small (docs-only) |

## 6. Safe implementation plan

All items below touch only display text, CSS class names, or doc content.
None touch `app/waterfall_core.py`, `domain/*`, debt sizing, tax logic,
R99/R102/G20 promotion *state*, or TUHO/Oborovo parity fixtures/logic.

- Phase A (this sprint, low-risk, in scope for "small safe UX cleanups"):
  items 2, 3, 4, 5 above.
- Phase B (requires its own review/approval): item 1 (export CSV fix —
  touches a shipped export path, should land as its own reviewed change
  mirroring the PR #686 pattern).
- Phase C (future sprint, explicit UX design needed): item 6, scenario
  matrix slot assignment.
- Phase D (docs-only, can proceed independently): item 7, pilot guide
  split.

No further code changes are proposed beyond what's listed here. Items 2-5
are presentation-text/CSS-only and are candidates for immediate small safe
cleanups within this sprint if approved.
