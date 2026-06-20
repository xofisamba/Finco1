# External Pilot Terminology Audit

Scope: every user-visible occurrence of "Factory", "Baseline", "Golden",
"create_default_", "Resolver", "Calibration" remaining after prior
cleanups (U5 Export Polish, U7 Error/Warning Cleanup, U9 Remaining
Terminology Cleanup, and the PR #686 fix-before-merge pass).

Classification key: **(A)** user-facing normal-mode surface, **(B)**
audit-only panel, **(C)** admin/internal dev surface, **(D)**
internal-only (never reaches an HTTP response).

## Findings

| File | Location | Current term | Class | Replacement | User impact |
|---|---|---|---|---|---|
| `app/templates/partials/new_project_form.html` | "Use generic defaults" help text (~L75-76) | "...factory. Review every field before saving." | **A** | "Prefills round-number defaults from the generic templates. Review every field before saving." | Visible on the new-project screen; "factory" reads as a dev-tool word to an external user filling in a form. |
| `app/templates/partials/export_registry.html` | "Coming Soon" export card name (~L86) | "Calibration Reconciliation Pack" | **A** | "Validation Reconciliation Pack" | Card is disabled today, but the name is already visible in the registry grid. Low urgency, fix before it ships enabled. |
| `app/templates/partials/export_registry.html` | Governance badges (G20 BLOCKED / R99/R102 NOT APPROVED, multiple cards) | "G20 BLOCKED", "R99/R102 NOT APPROVED" | **A** | Out of scope for terminology (these are governance codes, not factory/baseline/calibration wording) — flagged separately in the Pilot Guide Review doc, recommend collapsing to "Advanced governance review pending" wording or moving behind an audit-only toggle. | Pilots see internal-sounding gate codes with no explanation in the registry itself. |
| `app/templates/partials/_factory_lock_indicator.html` | CSS classes (`factory-lock-indicator`, `factory-lock-icon`, `factory-lock-body`, `factory-lock-title`, `factory-lock-desc`) | "factory" in class names only | **D** | Rename to `protected-lock-*` for internal consistency. | None — rendered text is already "Protected original"; this is cosmetic/internal-only cleanup. |
| `app/templates/partials/sheet_capex_detail.html` | Legend badge class (~L465, L684) | `badge-factory` CSS class; rendered text is "template" / "template default value" | **D** (class) / already fixed (text) | Rename class to `badge-template`; no text change needed. | None — text is already clean. |
| `app/templates/partials/sheet_opex_detail.html` | Legend badge class (~L285, L569) | `badge-factory` CSS class; rendered text is "reference" / "reference/default value" | **D** | Rename class to `badge-reference`. | None — text is already clean. |
| `app/templates/partials/project_selector.html` | Origin badge classes (~L24, L43) | `.ps-ap-origin--factory`, `.ps-ap-origin--baseline` CSS classes; rendered text is "Example Project" | **D** | Rename classes to `--template` / `--saved-base`. | None — text is already clean. |
| `app/templates/partials/scenario_version_history.html` | Code comment + Jinja value (~L109, L119) | comment: "Hidden for factory projects (TUHO/Oborovo)"; value: `"factory_template"` (never rendered, only used for conditional routing) | **D** | No change required; internal classification value. | None. |
| `app/templates/partials/inputs_section.html` | Conditional check (~L51) | `project_ctx.data_source == "Factory Reference"` (rendered output is "Template" / "Saved") | **D** | No change required. | None. |
| `app/templates/partials/project_review_card.html` | Jinja condition value (~L25) | `review.classification == "factory_template"` (rendered text is "Protected original — read-only reference") | **D** | No change required. | None. |
| `app/templates/partials/sheet_opex.html`, `sheet_capex.html` | Code comments | "Readonly notice for baselines"; "Read-only notice for factory / reference projects" | **D** | No change required (comments only). | None. |
| `static/styles.css` | `.badge-factory`, `.fc-cell-factory`, `.ps-ap-origin--factory`, `.ps-ap-origin--baseline` definitions | class names only | **D** | Rename alongside the template class renames above, in the same commit, to avoid orphaned CSS selectors. | None. |
| `docs/external_pilot_guide.md` | Lines 100, 131, 139 | "Excel-parity validation/validated", "R99/R102 promoted workflow" | **B** (these are governance/QA terms, not factory/baseline/calibration — see Pilot Guide Review doc for full treatment) | "validated against reference models"; remove R99/R102 codes | Covered in detail in `docs/external_pilot_guide_review.md`. |
| `docs/pilot_user_guide.md` | Lines 22, 28, 36-40, 63, 79, 106, 127 | "frozen-template", "parity evidence", "Parity Workbook", "factory mode", "Audit / Parity tab" | **B/C** | See `docs/external_pilot_guide_review.md` — recommend this file be re-scoped as an internal review checklist, not handed to external pilots as-is. | This file reads like an internal QA doc, not a pilot-facing guide; high risk if shared externally under its current name. |

## Already clean (verified, no action needed)

- `app/templates/partials/project_browser.html` — "Example Projects" section, "TUHO Wind", "Oborovo Solar PV" plain names, no seed/factory/fixture suffixes (pinned by `tests/test_phase_p2fix5e_reference_ux.py`).
- `app/templates/partials/workspace_shell.html` — "Example project" / "Saved project" lifecycle labels (fixed in U9).
- `app/templates/partials/sheet_opex.html`, `sheet_capex_detail.html`, `sheet_opex_detail.html` — rendered text (fixed in U9).
- `app/export/institutional_workbook.py` — zero "factory" substrings in any generated cell across TUHO and Oborovo workbooks (fixed in PR #686 fix-before-merge pass).
- `app/templates/partials/export_registry.html` rendered prose for Oborovo lineage (fixed in PR #686 fix-before-merge pass).

## New finding carried over from the Export Audit (see `docs/external_pilot_export_audit.md`)

The institutional workbook's display-mapping fix was never applied to the **runtime-summary CSV** export. `build_runtime_summary_rows()` (`app/export/runtime_summary.py`) writes the raw sentinel strings `factory_base_runtime` and `project_factory:tuho` / `project_factory:oborovo` directly into the `runtime_origin` / `template_origin` CSV columns with no display mapping — these reach the actual downloadable CSV bytes for both TUHO and Oborovo. This is classified **(A) user-facing** (it's a button-click download, not gated behind audit mode) and is the highest-priority remaining terminology leak. See the Export Audit doc for the recommended fix (apply the same `_display_runtime_origin` / `_display_template_origin` style mapping at the row-construction boundary, without touching the sentinel values themselves).

## Recommended replacement table (for reference)

| Internal term | External replacement |
|---|---|
| Factory | Template |
| Baseline | Base Project |
| Golden | Reference |
| Calibration | Validation |
| Factory Project | Project Template |
| `create_default_*` | (internal only — no user-facing replacement needed) |
| Resolver | (internal only — no user-facing replacement needed) |
