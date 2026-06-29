# C2-PR21 — Operating Preview Panel

## Summary

Consolidates the five existing, previously-separate preview indicator
`<div>` blocks in `app/templates/partials/workspace_shell.html`
(C2-PR10 CAPEX, C2-PR13 Revenue, C2-PR14 OPEX, C2-PR15 EBITDA, C2-PR16
Operating Cash Flow) into one cohesive, clearly-labeled "Operating
Preview Panel" container on the Overview tab. This is a pure
template/markup (plus trivial scoped CSS) change — no calculation
logic, request/response shape, or JS state-machine code was touched.

## Where the panel physically lives

All five indicators were already located inside `panel-overview`
(`app/templates/partials/workspace_shell.html`, immediately after the
C2-PR8 `#overview-runtime-status` indicator and before the
`#model-output-area` HTMX swap target) — they were never on a
different tab, just not visually/structurally grouped. No relocation
was needed; the change wraps the five existing `<div>` blocks in one
new `<div class="operating-preview-panel" id="operating-preview-panel">`
container, in place, without moving any of them.

## Exact heading/copy text

- **Heading:** `Operating preview (unsaved)`
- **Explanatory copy:** `These values are live previews only. Save/Run and exports use the saved model.`

Both strings appear verbatim in
`app/templates/partials/workspace_shell.html` inside
`.operating-preview-panel__title` / `.operating-preview-panel__desc`
respectively. Neither contains any internal jargon ("C1", "C2",
"PR10"–"PR23", "preview pipeline", "dependency graph", etc.) — verified
by `tests/test_c2_pr21_operating_preview_panel.py::TestNoInternalJargonInPanelCopy`.

## Element IDs preserved (unchanged)

The following IDs/attributes are byte-for-byte unchanged from their
pre-PR21 markup — `static/modelling/runtime-renderer.js` targets these
directly and none of its code was touched:

- Value elements: `#capex-total-preview-value`,
  `#revenue-total-preview-value`, `#opex-total-preview-value`,
  `#ebitda-preview-value`, `#operating-cf-preview-value`.
- Region/indicator container elements: `#capex-total-preview`,
  `#revenue-total-preview`, `#opex-total-preview`, `#ebitda-preview`,
  `#operating-cf-preview`.
- sr-only label elements: `#capex-total-preview-sr`,
  `#revenue-total-preview-sr`, `#opex-total-preview-sr`,
  `#ebitda-preview-sr`, `#operating-cf-preview-sr`.
- All `data-c2pr10-capex-preview`/`data-c2pr13-revenue-preview`/
  `data-c2pr14-opex-preview`/`data-c2pr15-ebitda-preview`/
  `data-c2pr16-ocf-preview`/`data-c2pr11-runtime-state` attributes.

## Accessibility attributes preserved

Each of the five region containers keeps its pre-existing
`role="status"`, `aria-live="polite"`, `aria-busy="false"` (toggled at
runtime by the existing JS), and `aria-label="..."` attributes
unchanged. The panel wrapper itself adds no new ARIA role — it is a
plain visual/structural grouping container; each individual indicator
remains its own independently-announced live region exactly as before,
so no change to screen-reader announcement behaviour was introduced.

## Visual distinction from authoritative KPIs

The panel reuses the existing `badge`/`badge-preview-only` convention
already present on each of the five value elements (unchanged), and
adds one new, narrowly-scoped CSS rule set in `static/styles.css`
(`.operating-preview-panel`, `.operating-preview-panel__header`,
`.operating-preview-panel__title`, `.operating-preview-panel__desc`) —
a light amber/warning-toned card background and border, following the
same visual language `badge-preview-only` already uses (`#fef3c7`
background / `#92400e` text / `#fcd34d` border) so the whole panel
reads as "unsaved preview" at a glance, distinct from any
`.sheet-card`/`.dashboard-kpi-value` authoritative element on the same
page. No existing CSS rule was modified.

## Tests added

`tests/test_c2_pr21_operating_preview_panel.py` (12 tests, route-level,
`fastapi.testclient.TestClient` against the real `main_web.app`,
mirroring `tests/test_c2_pr18_opex_preview_only_governance.py`'s
pattern):

- Exact heading/copy text present inside `panel-overview`.
- Panel wrapper element (`#operating-preview-panel`) present.
- All five value/region/sr-only IDs still present, and the value IDs
  specifically present *inside* the new panel boundary.
- `role="status"`/`aria-live`/`aria-busy`/`aria-label` preserved on all
  five region containers.
- No internal jargon in the new panel's own heading/copy text.
- The panel heading/wrapper does not leak into the CAPEX, Revenue, or
  OPEX tab panels.
