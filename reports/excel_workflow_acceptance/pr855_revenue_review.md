# PR 855 Revenue Excel Sheet Cleanup

## Scope

Revenue sheet cleanup only. The change updates the user-facing Revenue sheet presentation and tests that it remains backend-authoritative.

No engine, model, persistence, schema, factory, parity, CAPEX, OPEX, Inputs, Scenario, Financial Statement, or Senior Debt changes are included.

## Runtime and data-source position

The Revenue sheet displays existing `ProjectContext.revenue_items` assumptions and a read-only runtime evidence section. It does not calculate revenue in Jinja and does not introduce a `revenue_vm`.

Editable user-project field retained:

- `rev_ppa_base_tariff`

Protected reference behavior retained:

- TUHO and Oborovo render as read-only.
- The protected notice remains visible.
- No editable `rev_*` inputs render for protected projects.

## Cleanup checklist

- Main working view avoids a visible Code column.
- Production section is labelled `Production assumptions`.
- PPA / merchant section is labelled `Price assumptions`.
- Runtime output section is labelled `Revenue output`.
- Calculated revenue rows are read-only and point users to Runtime Summary / export evidence after Run.
- The sheet explicitly states that it does not recompute revenue.
- Unsupported merchant / certificate decomposition is documented as future Revenue v2 evidence.

## Screenshot evidence checklist

Screenshots were reviewed locally under the browser workflow. Binary screenshots are intentionally not committed.

Suggested evidence path for local runs:

`reports/excel_workflow_acceptance/screenshots/pr855/`

Checklist:

1. Protected TUHO Revenue top.
2. Protected TUHO Revenue output section.
3. Protected Oborovo Revenue top.
4. User-created Revenue top.
5. User-created editable PPA Price field.
6. Revenue output section showing runtime-authoritative wording.
7. No visible Code column in the main Revenue working view.

## Follow-up recommendation

Revenue v2 should expose backend-authoritative year-by-year production, pricing, merchant, certificate, and capture-price evidence before displaying a full decomposition. This PR intentionally does not infer or reconstruct those values.
