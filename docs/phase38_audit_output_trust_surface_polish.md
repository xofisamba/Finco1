# Phase 38 - Audit Output Enhancement / Trust-Surface Polish

## Base SHA

`13cb3d44ae19b9fe721d37495ad06970f4abef56`

## Type / scope

Phase 38 is audit UX, documentation, tests, and small display-only clarification work.

This phase does **not** change:

- financial formulas
- runtime calculations
- model outputs
- data paths
- project factories
- fixture CSVs
- schema

No JavaScript financial calculations were added.

## Objective

Improve pilot-facing trust surfaces so a reviewer or operator can more easily distinguish:

1. validated frozen-template evidence for TUHO and Oborovo
2. pending, unvalidated, or future-scope rows
3. descriptive exports vs trusted runtime evidence

## Surfaces inspected

- `app/templates/partials/audit_reconciliation_tab.html`
- `app/templates/partials/validation.html`
- `app/templates/partials/debt_dscr_shl_panel.html`
- `app/templates/partials/runtime_summary.html`
- `app/templates/partials/pilot_limitations_notice.html`
- `app/templates/partials/pilot_help_onboarding.html`
- `app/templates/partials/workspace_shell.html`
- `app/templates/partials/scenario_version_history.html`
- `app/templates/index.html`
- `docs/pilot_user_guide.md`
- `docs/pilot_ux_walkthrough_checklist.md`
- `docs/phase37_pilot_ux_walkthrough_friction_audit.md`
- `docs/phase37_pilot_ux_friction_matrix.md`
- `docs/pilot_rc_scope_matrix.md`
- `docs/validation_pack_executive_summary.md`
- `docs/validation_pack_index.md`
- `docs/external_reviewer_checklist.md`

## Audit ambiguity findings

### 1. Audit / Reconciliation mixed trusted and non-trusted rows

Before this phase, the audit tab placed validated TUHO/Oborovo parity rows next to generic-path warnings, CAPEX pending items, and future-scope rows in one continuous reading surface.

That was honest, but it made the operator do too much interpretation.

### 2. Export artefact names were accurate but insider-oriented

The export names were already correct, but some were more team-facing than operator-facing:

- Values-only Excel
- Runtime Summary CSV
- Institutional Workbook
- Parity Workbook
- Gap Register
- Source Map

Phase 38 clarifies what each artefact is for.

### 3. Clean-run boundary needed stronger reinforcement

Phase 37 already documented that runtime and exports reflect the last clean backend run, not unsaved draft edits. Phase 38 keeps that rule but makes it easier to spot near the runtime and download surfaces.

### 4. Generic boundary still needed to stay front-loaded

Generic solar/wind remain exploratory and unvalidated. That rule stays strong in this phase and is repeated in the audit and export trust surfaces.

### 5. Several trust-facing docs/templates still had visible mojibake

Some audit, validation-pack, and debt-panel surfaces still contained garbled display text. Phase 38 cleans those surfaces because they directly affect reviewer trust, but this remains display-only work.

## Display / copy changes made

### Audit / Reconciliation tab

- added a clear **Validated pilot evidence** grouping for TUHO/Oborovo rows
- added a separate **Pending / unvalidated / future scope** grouping
- moved generic-path language into the non-trusted group
- reinforced that the tab is internal review tooling, not an external audit or lender sign-off

### Debt / DSCR / SHL panel

- cleaned display-text mojibake
- kept the frozen-schedule warning intact
- clarified that generic wind/solar are exploratory and unvalidated

### Runtime summary

- cleaned display-text mojibake
- clarified that the panel reflects the last clean backend run
- clarified that exports follow the same clean-run boundary

### Validation surface

- cleaned display-text mojibake
- kept the message focused on input checks, not validation promotion

### Downloads / export context

- clarified export artefact purpose descriptions
- reinforced that trusted pilot evidence is limited to TUHO/Oborovo frozen-template paths
- reinforced that generic projects remain exploratory and unvalidated

### Pilot and validation docs

- cleaned visible mojibake in validation-pack and reviewer docs
- aligned wording with the Phase 37 trust boundary
- preserved non-claims

## Export artefact purpose clarifications

- **Values-only Excel**: spreadsheet copy of submitted values with provenance notes for reviewer handoff
- **Runtime Summary CSV**: compact machine-readable snapshot of the last clean backend run
- **Institutional Workbook**: reviewer-facing workbook with runtime summary, cover notes, and governance context
- **Parity Workbook**: validated frozen-template parity evidence for TUHO/Oborovo review
- **Gap Register**: open gaps, pending items, and out-of-scope rows still requiring judgement
- **Source Map**: provenance map showing where reviewed figures came from

## Validated vs pending / unvalidated separation

### Validated pilot evidence

The trusted pilot evidence surface remains:

- TUHO frozen-template parity
- Oborovo frozen-template parity
- validated revenue, OPEX, debt / DSCR, SHL / distribution anchors

### Pending / unvalidated / future scope

The non-trusted surface remains:

- generic solar / wind projects
- CAPEX per-line runtime gaps
- construction IDC / M1-M18 runtime wiring
- C.16 Project Rights wiring
- live sculpting / dynamic debt resizing

Generic solar/wind remain exploratory and unvalidated. They are excluded from trusted pilot conclusions.

## Remaining limitations

- Audit / Reconciliation still presents dense information, even after grouping.
- Backup / restore remains documented more clearly than it is discoverable in-product.
- Export artefacts are clearer now, but still assume some reviewer familiarity.
- No screenshot-based polish was done in this phase; this was a text/template trust-surface pass only.

## Deferred items

- broad UI redesign
- Shared LineItemGrid work
- full information architecture redesign for audit outputs
- richer operator-specific download catalogue UX
- any runtime or calculation changes

## Guardrails

- No formula changes
- No runtime/model changes
- No data-path changes
- No schema migrations
- No fixture CSV changes
- No JavaScript financial calculations
- TUHO/Oborovo validation behavior unchanged
- generic validation status unchanged
- G20 remains BLOCKED
- R99/R102 remains NOT APPROVED
- `partial_pay_sweep` remains not promoted
- flat/min DSCR sculpting remains not promoted
- backend remains source of truth

## Recommended next phase

**Phase 38B / 39: Audit Output Enhancement / Trust-Surface Polish continuation**

Recommended focus:

- separate validated anchors from pending rows even more visually
- simplify reviewer interpretation notes
- make backup/restore and export usage more discoverable
- keep generic exclusion highly visible in every pilot-facing review pack
