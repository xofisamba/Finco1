# Scenario Override Contract (v4)

This document defines the contract for scenario overrides on
the Finco1 platform. It is enforced by the strict validator
(`validate_manifests.py`) and the v4 builder
(`build_artifacts.py`).

## The contract

The contract is unchanged from v3. The validator and the
builder both enforce:

```
blank override cell        = inherit Base (active) value
explicit 0                  = zero (do not inherit)
missing field               != zero
None (Python null)          != zero
```

This contract is proven by:

* `tests/test_scenario_runner.py`
* `tests/test_workbook_v2_browser_acceptance.py::TestScenarioOverrideAcceptance`
* `tests/test_phase57a9c_capex_sub_lines_save_load.py`

PR #883 (IC Pack hotfix) does **NOT** change this contract.
It only repairs the Jinja2 numeric formatting. The scenario
inheritance rule is the source-of-truth commit.

## v4 Scenarios decision table

Every row on the Scenarios sheet is classified by:

1. **`SECTION_HEADER`** — `active_value_kind = empty` AND
   `active_formula_kind = empty` AND label is a domain
   heading (`TECHNICAL`, `CAPEX`, `OPEX`, `REVENUE`,
   `FINANCING`, `DEBT`, `TAX`, `Inputs by project team`,
   `Fixed values`).
2. **`LEGEND_TOOL`** — `team` starts with `Legend:`.
3. **`ENGINE_OUTPUT`** — `source_type = output/comparison`.
4. **`DERIVED_FORMULA`** — `active_formula_kind = formula`
   AND `active_value_kind ∈ {empty, formula}`.
5. **`CHECK_ONLY`** — label contains `check`, `balance`,
   `control`.
6. **`SCENARIO_OVERRIDE`** — `active_value_kind ∈ {numeric,
   text, date, other}` AND scenario value kind is a real
   kind; or `active_value_kind = empty` (Base inherited) AND
   scenario value kind is a real kind; or `source_type =
   scenario input` AND `active_value_kind` is a real kind.

Every row also carries:

* `classification_reason` — human-readable explanation.
* `classification_confidence` — `CONFIRMED`, `PROBABLE`, or
  `UNRESOLVED`.
* `base_input_relationship` — `DIRECT_BASE_INPUT`,
  `DERIVED_BASE_VALUE`, `OUTPUT_COMPARISON`, `HEADER_OR_TOOL`,
  or `UNRESOLVED`.

## Distinguishing scenario row types (v4)

The brief asks for clarity on:

### 1. Actual sparse override

```
active cell  = (numeric / text / date / other)  ← real Base assumption
scenario range = (numeric / text / date / other / empty)  ← user-overridable
blank scenario = inherit Base
explicit 0     = zero
classification: SCENARIO_OVERRIDE
base_input_relationship: DIRECT_BASE_INPUT
```

This is the v3 case. v4 still classifies these as
`SCENARIO_OVERRIDE` but now also confirms the active value is
real (not empty), so the row is a genuine sparse override and
not a section header.

### 2. Formula-propagated scenario value

```
active cell  = (formula)  ← cell is a formula, not user-editable
scenario range = (numeric / text / date / other)  ← values propagated from Base
classification: DERIVED_FORMULA
base_input_relationship: DERIVED_BASE_VALUE
```

The Scenarios sheet may contain formula-propagated cells that
display the Base value across all scenarios. v4 distinguishes
these from sparse overrides.

### 3. Comparison output

```
active cell  = (numeric / text)  ← output value
scenario range = (numeric / text)  ← comparison column
classification: ENGINE_OUTPUT
base_input_relationship: OUTPUT_COMPARISON
```

These are rows that display engine-produced comparison
outputs (e.g. annual_revenue, annual_pf_cf, IRR, DSCR). The
brief distinguishes these from sparse overrides.

### 4. Section / header

```
active cell  = empty
active formula = empty
label = domain heading  (e.g. TECHNICAL, CAPEX, OPEX, REVENUE, FINANCING, DEBT, TAX)
classification: SECTION_HEADER
base_input_relationship: HEADER_OR_TOOL
```

v3's logic was too permissive and mis-classified these as
`SCENARIO_OVERRIDE`. v4 explicitly rejects that.

## Validator enforcement

The validator's
`check_scenario_semantic_classification` rejects:

* `SCENARIO_OVERRIDE` with `active_value_kind = empty` AND
  `active_formula_kind = empty` AND label is a domain heading.
* `SCENARIO_OVERRIDE` with `active_formula_kind = formula`
  AND `active_value_kind ∈ {empty, formula}`.

The validator's `check_scenario_zero_unsupported` rejects
any `UNSUPPORTED` row in the scenarios manifest (all 550 rows
must be classified).

## v4 TUHO Scenarios classification (194 rows)

| Class | Count |
|---|---|
| `SCENARIO_OVERRIDE` | 170 |
| `SECTION_HEADER` | 7 |
| `ENGINE_OUTPUT` | 16 |
| `CHECK_ONLY` | 1 |
| `UNSUPPORTED` | 0 |

## v4 Oborovo Scenarios classification (356 rows)

| Class | Count |
|---|---|
| `SCENARIO_OVERRIDE` | 328 |
| `SECTION_HEADER` | 9 |
| `ENGINE_OUTPUT` | 16 |
| `CHECK_ONLY` | 3 |
| `UNSUPPORTED` | 0 |

Total: 550 rows (matches `Finco1_Scenario_Row_Map.csv`
exactly).

## v5 changes

v5 introduces two new scenario-level fields per row in the
manifest:

### `active_cell_role`

The role of the **active cell** (column D) on the Inputs or
Scenarios sheet:

| Role | Meaning |
|---|---|
| `DIRECT_BASE_INPUT` | an editable Base input on Inputs sheet |
| `LINKED_BASE_VALUE` | a Base value linked from another cell |
| `DERIVED_BASE_FORMULA` | a Base formula (not an input) |
| `OUTPUT` | an output cell (engine or computed) |
| `CHECK` | a check / balance / control cell |
| `HEADER` | a section / domain header |
| `UNRESOLVED` | role cannot be determined from sanitized extraction |

### `scenario_range_role`

The role of the **scenario range** (columns E..J for 6
scenarios) on the Scenarios sheet:

| Role | Meaning |
|---|---|
| `SPARSE_OVERRIDE` | scenario values are sparse; each cell overrides the Base value |
| `FORMULA_PROPAGATION` | scenario cells contain formulas that propagate from Base |
| `OUTPUT_COMPARISON` | scenario cells show comparison of engine outputs |
| `HEADER_PRESENTATION` | scenario cells are presentation-only (e.g. headers / labels) |
| `NO_OVERRIDE` | no override cells for this row |
| `UNRESOLVED` | role cannot be determined |

The validator (`check_scenario_semantic`) rejects
`active_cell_role=DIRECT_BASE_INPUT` combined with
`active_formula_kind=formula` (a formula cannot be a direct
Base input).

## v5 TUHO Scenarios classification (194 rows)

| Class | Count |
|---|---|
| `SCENARIO_OVERRIDE` | 170 |
| `SECTION_HEADER` | 7 |
| `ENGINE_OUTPUT` | 16 |
| `CHECK_ONLY` | 1 |
| `UNSUPPORTED` | 0 |

## v5 Oborovo Scenarios classification (356 rows)

| Class | Count |
|---|---|
| `SCENARIO_OVERRIDE` | 329 |
| `SECTION_HEADER` | 8 |
| `ENGINE_OUTPUT` | 16 |
| `CHECK_ONLY` | 3 |
| `UNSUPPORTED` | 0 |

Total: 550 rows (matches `Finco1_Scenario_Row_Map.csv`
exactly).

