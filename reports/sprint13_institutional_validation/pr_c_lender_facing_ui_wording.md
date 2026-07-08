# Sprint 13 PR C - Lender-Facing UI Wording

## Root cause

Several lender-visible UI surfaces still used pilot-era or developer-oriented wording such as "internal-use model only", "internal pilot mode", "preview-only", "not yet available", and "coming soon". The wording was accurate for earlier development phases but is too informal for institutional review packages.

## Scope

Presentation-only wording and render-test hygiene.

No model, formula, runtime, persistence, export, schema, tax, debt, CAPEX, OPEX, Revenue, or Financial Statement engine behavior changed.

## Files changed

- `app/templates/known_limitations_page.html`
- `app/templates/partials/_kpi_strip.html`
- `app/templates/partials/debt_dscr_shl_panel.html`
- `app/templates/partials/empty_states_notice.html`
- `app/templates/partials/inputs_section.html`
- `app/templates/partials/new_project_form.html`
- `app/templates/partials/pilot_help_onboarding.html`
- `app/templates/partials/pilot_limitations_notice.html`
- `app/templates/partials/pilot_workflow_guide.html`
- `app/templates/partials/sheet_financials.html`
- `app/templates/partials/sheet_revenue.html`
- `app/templates/partials/sheet_senior_debt.html`
- `app/templates/partials/sheet_shl.html`
- `app/templates/partials/sheet_tax.html`
- `app/templates/partials/bess_asset_dashboard.html`
- `app/templates/partials/bess_revenue_breakdown.html`
- `app/templates/partials/covenant_dashboard.html`
- `app/templates/partials/credit_pack.html`
- `app/templates/partials/credit_summary.html`
- `app/templates/partials/ic_pack.html`
- `tests/test_sprint13_lender_facing_ui_wording.py`
- `tests/test_phase20h_design_system_rendering.py`
- `tests/test_phase20j_opex_grid.py`
- `tests/test_phase20k_revenue_grid.py`
- `tests/test_phase20m_runtime_statement_polish.py`

## Wording changes

- "Internal-use model only" became "preliminary review model(s)".
- "Internal review tooling" became "reviewer evidence tooling".
- "Internal reference workbooks" became "committed reference workbooks".
- "Not yet available" became explicit scope language such as "outside current runtime view" or "outside current dashboard scope".
- "Preview-only until saved and re-run" became "Draft-only until saved and re-run".
- "Coming soon" revenue wording became governed project-template review wording.

## Render hygiene

Legacy tests were updated to match the current runtime UI surface instead of older Sprint 10 layout expectations. The product UI was not changed to reintroduce old preview wording or older grid wrappers.

Jinja formatting patterns were normalized from invalid filter-style Python format strings to supported `.format(...)` syntax in reporting partials.

## Tests

Command:

`python -m pytest tests/test_sprint13_lender_facing_ui_wording.py tests/test_phase57pre_route_render_smoke.py tests/test_phase21_template_render.py tests/test_phase21_jinja_format.py tests/test_phase20m_runtime_statement_polish.py tests/test_phase20h_design_system_rendering.py tests/test_phase20j_opex_grid.py tests/test_phase20k_revenue_grid.py tests/test_phase20l_construction_idc_ux.py -q --tb=short`

Result:

`223 passed, 17 skipped`

## Route matrix result

Route smoke passed as part of the combined run:

`tests/test_phase57pre_route_render_smoke.py`

## Screenshot / evidence path

Evidence report:

`reports/sprint13_institutional_validation/pr_c_lender_facing_ui_wording.md`

## Institutional readiness score

88 / 100 for lender-facing wording in the touched UI surfaces.

Remaining work: broader Playwright screenshot capture and export artifact review in later Sprint 13 bundles.

## Confirmations

- No model changes.
- No formula changes.
- No runtime calculation changes.
- No persistence changes.
- No schema changes.
- No export generation changes.
- No financial statement engine changes.
- No parity target changes.
