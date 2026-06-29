# C2-PR18 — Preview-Only OPEX Governance

## Summary

C2-PR17 made OPEX Budget `<input>` cells genuinely editable in the
browser, but deliberately gave them no `name=` attribute, so Save
structurally cannot persist OPEX line edits. That decision is correct
and documented, but it creates a UX risk: a user could reasonably
assume an editable cell's edits are saved, when they are not (yet).
This PR closes that risk with a small, plain-language, non-scary UX
note placed directly on the OPEX sheet — no logic change of any kind.

## Exact UX copy added

```
OPEX line edits are preview-only for now. They update the live preview,
but are not saved yet. Run uses the saved model inputs.
```

This is the user-facing text rendered inside a new `<div class="opex-preview-only-note" id="opex-preview-only-note" role="note">` block in
`app/templates/partials/sheet_opex_detail.html`, placed immediately
above the existing "Readonly notice" / summary strip — the first thing
a user sees when landing on the OPEX tab, regardless of whether the
project is protected or a user's own editable copy.

## Why this wording avoids internal jargon

The copy deliberately never mentions "C1", "C2", "PR17", "preview
pipeline", "debounce", "dependency graph", or any other internal
program/PR vocabulary. It uses three short, plain sentences:

1. States the current limitation in user terms ("preview-only for
   now").
2. States the consequence in user terms ("update the live preview, but
   are not saved yet").
3. States what Run actually does, so there is no ambiguity about
   what happens at that point ("Run uses the saved model inputs").

This mirrors the existing wording conventions already established by
PR10/PR13/PR14/PR15/PR16 (e.g. "(unsaved)", "preview", "not the saved
total") — honest, unambiguous, and free of codes/acronyms a non-engineer
reviewer wouldn't understand.

## Where it appears — and where it deliberately does not

The note lives entirely inside `sheet_opex_detail.html`, one of several
`{% include %}`'d partial templates assembled into the single-page
workspace (`app/templates/partials/workspace_shell.html`'s
`panel-opex`, `panel-revenue`, `panel-capex`, `panel-overview` etc. tab
panels). Because each sheet is its own partial template, the note is
structurally confined to the OPEX panel and cannot leak into CAPEX,
Revenue, Overview, or any other sheet — confirmed by
`tests/test_c2_pr18_opex_preview_only_governance.py::TestPreviewOnlyNoteAbsentElsewhere`,
which extracts each panel's HTML by `id="panel-..."` boundary and
asserts the note's text/class is absent from `panel-capex`,
`panel-revenue`, and `panel-overview`.

## No change to PR17's editability behaviour

This PR touches only the OPEX sheet's *markup* (one new note block plus
its scoped CSS). The existing editable Budget `<input>` cells
(`data-fc-editable="true"` for non-contingency rows on user projects,
no `name=` attribute) are completely unchanged — confirmed by
`tests/test_c2_pr18_opex_preview_only_governance.py::TestRegressionOpexBudgetInputHasNoNameAttribute`
and
`tests/test_c2_pr17_opex_line_editability.py`'s full pre-existing suite,
which still passes unmodified.

## Regression tests proving the persistence boundary still holds

`tests/test_c2_pr18_opex_preview_only_governance.py::TestRegressionSaveDoesNotPersistOpexEdits`
re-confirms `main_web.py::_collect_form_snapshot`'s field list still has
no per-child-code OPEX field (no `opex_{code}_keur` analogous to
CAPEX's `capex_{code}_keur`) — the same structural proof PR17
established, re-checked here to confirm this PR's purely-template
change did not disturb it. The full, more detailed PR17 backend test
suite (`tests/test_c2_pr17_opex_line_editability.py::TestSaveDoesNotPersistOpexLineEdits`)
continues to pass unmodified.

## Tests added

- `tests/test_c2_pr18_opex_preview_only_governance.py`:
  - `TestPreviewOnlyNoteVisibleOnOpexSheet` — the note's text is
    present inside the OPEX panel.
  - `TestPreviewOnlyNoteAbsentElsewhere` — the note's text/class is
    absent from the CAPEX, Revenue, and Overview panels.
  - `TestNoInternalJargonInOpexVisibleText` — none of `C1`, `C2`,
    `PR17`, `PR18`, `PR19`, `PR20`, "preview pipeline", "dependency
    graph" appear in the OPEX panel's visible text (HTML tags,
    comments, and `<style>`/`<script>` block contents are stripped
    before the check, since those are never user-visible).
  - `TestRegressionOpexBudgetInputHasNoNameAttribute` — regression
    mirror of the PR17 no-`name=` check.
  - `TestRegressionSaveDoesNotPersistOpexEdits` — regression mirror of
    the PR17 form-snapshot-field-list check.

## No real financial engine use

Confirmed: this PR touches only `sheet_opex_detail.html` (one new
markup block + scoped CSS) and adds one new test file. No import of,
or call into, `domain/*`, `app/waterfall_core.py`,
`app/input_adapter.py`, or `app/project_factories.py`. No new route. No
change to `main_web.py`, `static/modelling/recalc-preview.js`,
`static/modelling/runtime-renderer.js`, `static/modelling/live-model.js`,
or `static/app.js`.
