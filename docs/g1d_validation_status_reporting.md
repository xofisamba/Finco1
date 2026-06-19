# G1D — Validation Status Reporting

This note describes the user-facing validation status reporting added for
TUHO, Oborovo, Generic Solar/Wind, BESS/Hybrid, and Portfolio, and how the
UI and Excel export consume it. It is a presentation/classification layer
only — no model formula, factory default, or runtime calculation changes.

## Project-level validation tiers

| Project | Tier | User-facing label |
|---|---|---|
| TUHO | Calibrated frozen internal reference | "Calibrated reference project" |
| Oborovo | Calibrated frozen internal reference | "Calibrated reference project" |
| Generic Solar | Validated generic bootstrap model with caveats | "Validated model with caveats" |
| Generic Wind | Validated generic bootstrap model with caveats | "Validated model with caveats" |
| BESS / Hybrid | Design-only / not externally validated | "Design-only, not externally validated" |
| Portfolio | Experimental / internal only | "Experimental, internal only" |

The internal terms in the left/middle columns (used in audit and dev docs)
are intentionally not surfaced verbatim to end users. The schema in
`app/validation_status.py` only ever exposes the right-most, user-facing
wording — it never renders "factory", "baseline", "hardcoded", or
"bootstrap".

## Metric-level labels for Generic Solar/Wind

**Validated** (close agreement with the internal reference workbook):
CAPEX, Revenue, OPEX, EBITDA, IDC, Bank fees, Senior debt amount, Realized
gearing, Equity funding stack (post-G1H).

**Methodology caveat** (known, documented gap versus the reference
workbook's own debt-sizing proxy — see
`docs/generic_validation_reference_excel_spec.md` §6.2 and
`reports/g1f_debt_sizing_proxy_gap_analysis.md`): Debt service shape,
Average DSCR, Minimum DSCR, Project IRR, Equity IRR (pending a tighter
tolerance review).

## Required disclosure text

1. "Generic Solar and Generic Wind are validated against internal
   reference workbooks, not a full external bank model review."
2. "Debt service shape, DSCR, and IRR figures carry a documented
   methodology caveat versus the reference workbooks (see validation
   notes)."
3. "All outputs are modelling estimates only and do not constitute
   legal, tax, accounting, or investment advice."

The third disclosure is shown for every project (including TUHO, Oborovo,
BESS/Hybrid, and Portfolio); the first two are specific to Generic
Solar/Wind.

## Schema and consumption

`app/validation_status.py` defines:

- `ValidationTier` — the four project-level tiers above.
- `MetricValidationLevel` — `validated` or `methodology_caveat`.
- `MetricValidationLabel` — one metric's display name, level, and
  (for caveated metrics) caveat text.
- `ProjectValidationStatus` — a project's tier, user-facing tier
  label/description, tuple of metric labels, tuple of disclosure strings,
  and an `internal_classification` string (audit/dev-facing only, e.g.
  `"validated generic bootstrap model with caveats"` — never rendered in
  the UI or an export; use `tier_label`/`tier_description` there).
- `get_validation_status(project_key)` — the lookup entry point, tolerant
  of the various spellings already used elsewhere in the codebase
  (`"tuho"`, `"oborovo"`, `"solar"`/`"generic_solar"`,
  `"wind"`/`"generic_wind"`, `"bess"`, `"solar_bess"`, `"wind_bess"`,
  `"portfolio"`). Unknown keys fall back to the experimental/internal-only
  tier rather than raising, since this layer must never block a runtime
  calculation.
- `all_validation_statuses()` — every known project's status, for
  rendering a full validation matrix.

**Excel export**: `app/export/institutional_workbook.py` adds a
"Validation Status" sheet (sheet order 17) to the institutional workbook,
built from `get_validation_status(bundle.active_project)`. It shows the
project's tier, the metric-level validated/methodology-caveat table for
Generic Solar/Wind, and the disclosure text.

**UI**: `app/templates/partials/_validation_status_badge.html` is a new,
reusable Jinja partial that renders a `ProjectValidationStatus` (tier
badge, metric table, disclosures). It is not yet wired into a specific
dashboard route — that wiring is a follow-up, since the existing
dashboard/page-rendering layer does not currently thread a per-project
validation object through its context. The partial and the underlying
`app/validation_status.py` schema are ready for that integration.
