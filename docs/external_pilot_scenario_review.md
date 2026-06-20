# External Pilot Scenario Workflow UX Review

Scope: review the current scenario workflow (Base/Downside/Upside/Custom),
compare workflow, KPI comparison, and Excel-like usability. No
implementation in this doc.

## Current behaviour

- The scenario matrix (`app/ui/scenario_matrix.py`,
  `app/templates/partials/scenario_matrix.html`) uses a fixed 4-column
  layout: Base, Downside, Upside, Custom.
- Column assignment is **positional**: the first three non-base saved
  scenarios are mapped to Downside/Upside/Custom slots in creation order,
  regardless of the scenario's actual name or what the user intended it to
  represent. A scenario named "Upside" could land in the "Custom" column if
  it was the third one created.
- Comparison views (`scenario_compare.html`, `scenario_compare_multi.html`)
  render KPI deltas across scenarios but inherit the same positional
  labeling from the matrix.
- `_scenario_unified_entry.html` provides the entry point for creating a
  new scenario but does not let the user pick which of the 4 matrix slots
  it should occupy — slot assignment is implicit.

## Evaluation against Excel-like usability

- External finance users are used to scenario columns being labeled by
  what they contain (driven by sliders/assumptions they set), not by
  creation order. The current positional mapping breaks that expectation:
  a user could create a "mild downside" case second and a "severe
  downside" case third, and the severe case would land in "Upside" or
  "Custom" purely by accident of timing.
- KPI comparison itself (the actual numbers, deltas) is sound and not in
  scope for change — this review found no calculation or formatting
  issues, only labeling/assignment UX.

## Recommendations (analysis only, no code)

1. **(a) Compare workflow** — let the user explicitly assign or rename a
   scenario's matrix slot at creation/edit time, rather than relying on
   creation order. This removes the single biggest source of confusion
   identified.
2. **(b) KPI comparison** — no changes recommended; the underlying
   comparison math and rendering are already correct and were not flagged
   in any agent finding.
3. **(c) Excel-like enhancements** — consider exposing the matrix as an
   exportable side-by-side grid (already partially possible via existing
   export registry) so a user can review Base/Downside/Upside/Custom in a
   spreadsheet-like layout outside the app, matching the mental model
   Excel-native users already have.

## Terminology cross-reference

No factory/baseline/golden/calibration wording was found directly in the
scenario matrix or compare templates during this review; this surface's
issue is purely the positional-assignment UX described above, not internal
terminology leakage. No entries from this review need to be added to
`docs/external_pilot_terminology_audit.md`.

## Conclusion

The scenario workflow's KPI math and export integration are sound. The one
substantive UX gap is the implicit, creation-order-based column
assignment, which should be made explicit before broader external pilot
rollout. This is a UX/labeling change, not an engine or calculation
change, and does not touch `app/waterfall_core.py` or any parity-critical
path.
