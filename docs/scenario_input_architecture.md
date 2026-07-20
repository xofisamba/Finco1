# Scenario Input Architecture — Oborovo OPEX

**Status**: Architecture freeze. Design only — no runtime implementation.

---

## A. Authoritative Excel Source Behavior

This section documents what the workbook does. It is source documentation, not a design target.

### Scenario selection in the workbook

The workbook's `Scenarios` sheet stores four side-by-side scenario columns (H–K). Row 3 holds scenario names; row 4 holds sequential indices (1–4). Cell `Scenarios!E4` holds the active index selector.

| Column | Index | Name |
|--------|-------|------|
| H | 1 | HYBRID |
| I | 2 | Fixed NEW OPEX TEMPLATE |
| J | 3 | Tracker system NEW OPEX TEMPLATE |
| K | 4 | DCSA to RTB, no DEV costs |

Current selection: `E4 = 4` → column K ("DCSA to RTB, no DEV costs").

Every OPEX budget cell in column E resolves to the selected scenario's value via:
```
=INDEX(H<row>:K<row>, 0, MATCH($E$4, $H$4:$K$4, 0))
```

Changing `E4` switches all budget inputs atomically — exactly one scenario column is active at any time.

### Activation flags in the workbook

OPEX activation flags (Y1–Y30 per subitem) are structural values on the `OpEx` sheet. Most are constants (0 or 1). Exceptions:

- **B.11.3 Bank Fees** — formula-driven: `=IF(F2<=Inputs!$D$196,1,0)`, where `Inputs!D196` = senior debt tenor (= 14 years, sourced from `Scenarios!E345`). Active Y1–Y14, zero Y15–Y30.

Changing structural activation flags in the current workbook requires manual editing of the `OpEx` sheet. There is no scenario-level flag override mechanism in the workbook itself.

### Scenarios row mapping

Every OPEX subitem whose budget formula links to the Scenarios sheet has a `scenarios_row` recorded in the fixture. Key rows:

| Category | Name | Scenarios row |
|----------|------|---------------|
| B.01 | Technical Management | 236 |
| B.01.1 | Asset Management Contract | 237 |
| B.01.2 | Bazefield | 239 |
| B.02 | Infrastructure Maintenance | 241 |
| B.02.1 | O&M Y1-2 | 242 |
| B.02.2 | O&M Y3-30 | 243 |
| B.02.4 | Inverter service contract / MRA | 247 |
| B.02.5 | Spare parts reprocurement | 248 |
| B.03 | Maintain Site | 264 |
| B.04 | Clean Material | 269 |
| B.05 | Security | 273 |
| B.06 | Insurance | 277 |
| B.07 | Lease & property Tax | 282 |
| B.08 | Power Expenses | 287 |
| B.08.3 | Balancing costs (input: eur/MWh) | 290–291 |
| B.09 | Fees | 292 |
| B.10 | Audit & Accounting & Legal Fees | 297 |
| B.11 | Bank Fees | 304 |
| B.12 | Environmental & Social management | 309 |
| B.13 | Contingencies (rate = 4%) | 315 |

Full row mapping with per-scenario H/I/J/K values is in `tests/fixtures/excel_oborovo_opex_structural_truth.json`.

### Special formula cases

These deviations from the standard `budget × (1 + inf)^(year−1)` formula require explicit handling:

**B.02 — Two-regime O&M with label/flag mismatch**  
B.02.1 is labeled "Y1-2" but actual activation flags: Y1=1, Y2=0 (active Y1 only).  
B.02.2 is labeled "Y3-30" but actual flags: Y2=1 through Y30=1 (active Y2–Y30).  
The workbook labels are misleading; the fixture's `label_flag_mismatch` fields document the true activation.

**B.07 — Pre-COD inflation base**  
Workbook applies inflation with exponent = year (not year−1): `annual_Y1 = 204 × 1.02 = 208.08 kEUR`.

**B.08 — Zero inflation, step change at Y11**  
B.08.3 Balancing costs OFF for Y1–Y10, ON from Y11. `annual_Y1-10 = 176.86 kEUR`, `annual_Y11-30 = 549.76 kEUR`.

**B.09 — Zero inflation**: Flat 14 kEUR per year.

**B.10 — Auditor step-down**  
B.10.1 (16 kEUR) active Y1–Y2 only; B.10.2 (8 kEUR) active Y3–Y30.

**B.11 — Debt-tenor-driven activation**  
B.11.3 activation formula (source cell `OpEx!F68`): `=IF(F2<=Inputs!$D$196,1,0)`, D196 = 14. Active Y1–Y14.

**B.12 — Monitoring expiry**  
B.12.3 (Fauna & Flora) and B.12.5 (E&S monitoring) active Y1–Y2 only. `annual_Y3+ = 12 kEUR` (B.12.1 + B.12.6 only).

**B.13 — Contingency**  
`annual_Yn = 0.04 × SUM(annual_Yn for B.01–B.12 + D + F)`. Claims (C) excluded. Rate cell: `OpEx!D76`. Base rows: `[3,8,26,31,35,39,45,48,53,58,65,70,82,90]`.

---

## B. Target Finco1 Scenario Architecture

This section defines the intended product architecture for Finco1. It is a design target, not a description of any currently implemented runtime.

### Model

```
Base Project Inputs
+
one selected named Scenario Override
=
Resolved Immutable Inputs
→
Clean Engine
```

A project holds many saved scenarios. Exactly **one** scenario is selected for a computation run. The selected scenario supplies sparse overrides; all non-overridden inputs inherit the Base Project Inputs unchanged.

### Scenario storage

A newly created scenario:

- **Visually** begins as a copy of Base Case (full input set displayed to the user).
- **Technically** stores only sparse overrides — a set of `(field, value)` pairs.
- Does not duplicate the complete project input set.

If Base Case changes after a scenario is saved:

- Non-overridden scenario fields automatically inherit the new Base value.
- Explicitly overridden fields remain unchanged.

Resetting an override to Base:

- Removes the override entry from the sparse set.
- Does **not** copy the current Base value into the scenario as a new override.

### No multi-scenario stacking

There is no multi-scenario composition, stacking, or last-write-wins merging. One scenario is selected; its sparse overrides and the Base Project Inputs together produce one fully determined input set.

### Scope of scenario overrides

A selected scenario may override inputs in any module:

- Timeline
- Technical
- Production
- Revenue / PPA
- OPEX (see below)
- CAPEX
- Senior Debt
- Tax inputs and policies
- SHL and reserve modules (future)

### OPEX-specific overrides

For OPEX, a selected scenario may override:

| Override target | Description |
|----------------|-------------|
| Subitem amount | Budget value for an individual subitem |
| Inflation / escalation policy | Where permitted per category |
| Activation mode | Automatic driver or MANUAL |
| Annual Y1–Y30 activation flags | Explicit flag vector per subitem |
| Advanced H1/H2 activation overrides | Sub-annual activation control |

**Base Case activation flags are inherited** by the scenario unless explicitly overridden. A scenario override of flags replaces the Base flags for that subitem entirely.

**Bank Fees (B.11) target behavior**

| Mode | Behavior |
|------|----------|
| Default | `SENIOR_DEBT_ACTIVE` — activation follows the senior debt tenor input |
| Manual override | Explicit Y1–Y30 flag vector replaces the automatic driver |

Manual mode fully replaces the automatic driver. The two modes must not be silently combined.

### Category totals

Category totals (B.01 through B.13) remain derived, read-only computed values. They are never direct scenario inputs.

### UI independence

The persistence architecture must support either presentation style without any financial engine or database redesign:

| Style | Description |
|-------|-------------|
| Dropdown / editor UI | One scenario selected from a list; fields edited individually |
| Excel-style matrix | Multiple scenarios displayed side-by-side; selection column highlighted |

Switching presentation style is a UI concern only. The underlying sparse-override model and the "one selected scenario" computation contract are identical in both cases.

---

## Inflation Sources

| Category | Source | Rate |
|----------|--------|------|
| B.01–B.06, B.10, B.11, B.12 | `Inputs!D85` (EUR CPI) → `=D93` → 0.02 | 2% |
| B.07 | Workbook D column (EUR CPI, exponent = year) | 2% |
| B.08 | Hardcoded 0 | 0% |
| B.09 | Hardcoded 0 | 0% |
| B.13 | Rate = 4% applied to annual base sum | n/a |

Inflation chain is fully traced in the fixture: `inputs.inflation_rate.chain` records `OpEx!C102 → Inputs!D85 → Inputs!D93 → 0.02`.

---

## What This Document Does NOT Cover

- No implementation of a Scenario runtime, database, or UI.
- No changes to `finco_core/` OPEX schedules.
- No changes to the financial waterfall.
- Depreciation, tax, merchant pricing, SHL, DSRA are out of scope.
- No Recon Fix 02B.

See `tests/fixtures/excel_oborovo_opex_structural_truth.json` for the machine-readable structural truth.  
See `docs/reconciliation/oborovo_opex_structural_truth.md` for the human-readable audit report.
