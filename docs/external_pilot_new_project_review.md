# External Pilot New Project Creation UX Review

Scope: review the current New Project flow against a target "4-fields-only"
flow (Project Name, Technology, Country, Capacity MW; everything else
editable later via Inputs). No code changes in this doc.

## Current flow

- `_validate_new_project_payload` (`main_web.py:844-976`) already validates
  only four fields strictly: Project Name, Technology (`project_type`),
  Country (`market`), Capacity MW. Every other financial/technical field is
  parsed with `optional_float` / `optional_int` (`main_web.py:937-967`) and
  is not required.
- `_apply_new_project_required_inputs` (`main_web.py:979-1044`) overlays any
  non-empty user-provided values onto generic technology defaults sourced
  from `app/project_factories.py:460-600` (Solar/Wind default builders).
  Any field the user leaves blank silently falls back to the generic
  default.
- The "Use generic defaults" help text on the new-project form
  (`app/templates/partials/new_project_form.html` ~L75-76) already tells
  the user this is happening, but currently uses the word "factory"
  (tracked separately in `docs/external_pilot_terminology_audit.md`).
- After creation, the user lands on the project's Inputs tab where all
  prefilled defaults are visible and editable.

## Target flow

1. User enters Project Name, Technology, Country, Capacity MW only.
2. Project is created immediately with round-number generic defaults for
   everything else.
3. User is routed to Inputs and prompted to review/edit before running the
   model — Run is available but the UI nudges the user to check inputs
   first rather than blocking Run outright.

## Blockers

| # | Blocker | Detail | Severity |
|---|---|---|---|
| 1 | None at the validation layer | The backend already accepts a 4-field-only payload today; no schema change needed. | None |
| 2 | Wording on the defaults-overlay explanation | "factory" wording on the form needs the terminology fix already tracked in the terminology audit doc. | Low |
| 3 | Run-readiness messaging | `run_demo_project()` (`app/ui_runner.py:124`) requires a fully populated `ProjectInputs`, which it already has via the generic-default overlay — but the UI does not currently explain to a 4-field user that the model can run immediately on defaults. This is a copy/sequencing gap, not a backend blocker. | Low |
| 4 | Discoverability of "edit later" | Nothing in the current new-project UI explicitly states that all non-required fields can be edited after creation; this should be made explicit in the form copy to support the target flow's promise. | Low |

## Implementation effort

| Change | Files | Effort |
|---|---|---|
| Fix "factory" wording in defaults help text | `app/templates/partials/new_project_form.html` | Trivial (text-only) |
| Add "you can edit everything later" microcopy | `app/templates/partials/new_project_form.html` | Trivial (text-only) |
| Add a "Review before running" nudge on first Inputs visit for a newly created project | `app/templates/partials/inputs_section.html`, possibly `main_web.py` route handling | Small |
| No backend/validation schema changes needed | — | None |

## Conclusion

The backend already implements the target "4-fields-only" flow. The
remaining work is entirely presentation/copy: removing internal wording,
and adding microcopy that reassures the user defaults are safe-but-generic
and fully editable. No engine, validation, or persistence change is
required.
