# Phase 17A New Project Foundation

Phase 17A creates project records and selector workflow for real user-created projects in the HTMX/FastAPI app.

What this branch adds:
- a DB-backed project record separate from scenario snapshots
- a real New Project route and creation form
- project selector sections for factory templates and user-created projects
- workspace binding for user-created projects
- baseline snapshot seeding so a created project can be selected, saved, loaded, and run through the current template-seeded path

What this branch does not add:
- Phase 17A does not yet implement full from-scratch runtime
- Phase 17A does not add the required 13-field creation form
- Phase 17A does not redesign workbook export, scenario compare, or runtime formulas

User-facing policy:
- TUHO/Oborovo remain templates
- user-created projects are real project records
- runtime remains template-seeded for now
- the UI discloses: project record created, runtime still uses template-seeded defaults until Phase 17C from-scratch runtime path

Next phases:
- Phase 17B adds required 13-field form
- Phase 17C adds build_projectinputs_from_scratch

Guardrails preserved:
- save does not auto-run
- run does not auto-save
- frontend/browser state does not become runtime authority
- no runtime/model formula changes
- no workbook calculation changes
- no export calculation changes
- no scenario compare behavior changes
- G20 remains BLOCKED
- R99/R102 remains NOT APPROVED
