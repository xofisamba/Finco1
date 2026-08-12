# C3B3D2B3 — Generic Debt Sizing Case Production Contract

## Stage Identity

| Field | Value |
|-------|-------|
| Stage | C3B3D2B3 |
| Branch | `stage-c3b3d2b3-debt-sizing-case-production` |
| Base SHA | `e71ad5cbf05ff7d8b0a46b8f8d5782a478bb14e8` (squash of PR #925) |
| Verdict | `C3B3D2B3_GENERIC_DEBT_SIZING_CASE_PRODUCTION_CONTRACT_AND_RUNTIME_PROVEN` |
| Status | DRAFT — DO NOT MERGE |

---

## 1. Motivation

Prior to C3B3D2B3, `run_senior_debt_model()` sized senior debt from the **Base
case CFADS** — the same P50 operating model used for the equity performance
case. This is architecturally incorrect: bank DSCR sizing must use a
conservative yield scenario (P90-10y), which produces lower production, lower
revenue, lower EBITDA, and therefore lower CFADS than the Base case.

C3B3D2B3 introduces an explicit, project-identity-free `DebtSizingCaseInput`
contract so that:

1. The bank case is described by **explicit user-supplied fields**, not
   derived from project metadata or dispatch on project name/code.
2. The two economic cases — Base/equity and Bank/debt-sizing — are kept
   clearly separated throughout the result structure.
3. The generic engine default for bank sizing is `P90_10Y` (per
   `GENERIC_BANK_SIZING_DEFAULT_POLICY_IS_P90_10Y`).

---

## 2. New Types

### `financial_engine.inputs.DebtSizingCaseInput`

Frozen dataclass containing **only the fields that deviate from the Base case**.
All project fundamentals (calendar, opex, capex, PPA, tax policy, etc.) are
inherited from `OperatingModelInput` unchanged.

```python
@dataclass(frozen=True)
class DebtSizingCaseInput:
    production_yield_scenario: YieldScenario          # required
    merchant_price_calendar_start_year: int | None    # optional override
    merchant_prices_by_calendar_year_eur_mwh: tuple[float, ...]
    market_prices_curve_eur_mwh: tuple[float, ...]    # optional override
    source_label: str                                 # audit-only, NOT fingerprinted
```

**Governance:**
- `GENERIC_DEBT_SIZING_CASE_IS_EXPLICIT_AND_PROJECT_IDENTITY_FREE`
- `DEBT_SIZING_CASE_FIELDS_ARE_USER_INPUTS_NOT_DERIVED_OUTPUTS`
- `source_label` is excluded from `compute_senior_debt_fingerprint()` — it
  is an audit trail field, not a financial assumption.

### `financial_engine.inputs.SeniorDebtModelInput` (extended)

New required field `debt_sizing_case: DebtSizingCaseInput` added.

For the **generic bank case**: `DebtSizingCaseInput(production_yield_scenario=YieldScenario.P90_10Y)`.

### `financial_engine.results.DebtSizingSchedules`

New frozen dataclass capturing the bank-case economic outputs:

```python
@dataclass(frozen=True)
class DebtSizingSchedules:
    period_indices: tuple[int, ...]
    bank_production_mwh: tuple[float, ...]
    bank_revenue_keur: tuple[float, ...]
    bank_opex_keur: tuple[float, ...]
    bank_ebitda_keur: tuple[float, ...]
    bank_cfads_keur: tuple[float, ...]   # primary: DSCR sizing input
```

### `financial_engine.results.ProjectModelResult` (extended)

New optional field `debt_sizing: DebtSizingSchedules | None = None`.

---

## 3. New Function: `derive_debt_sizing_operating_input`

```python
def derive_debt_sizing_operating_input(
    base_op: OperatingModelInput,
    debt_sizing_case: DebtSizingCaseInput,
) -> OperatingModelInput:
```

**Pure immutable transformer.** Inherits all Base fundamentals and overrides:
- `technical.yield_scenario` → `debt_sizing_case.production_yield_scenario`
- Merchant price schedule → bank-case override (if provided)

**Merchant price override precedence:**
1. Calendar-year form (`merchant_price_calendar_start_year` not None or non-empty tuple)
2. Relative curve form (`market_prices_curve_eur_mwh` non-empty)
3. Base revenue inherited unchanged (neither provided)

The base `OperatingModelInput` is **never mutated** — the function returns a
new frozen dataclass instance.

---

## 4. Refactored: `run_senior_debt_model`

### Two-Case Architecture

| Case | Input | Purpose |
|------|-------|---------|
| Base | `inputs.operating` | Equity/asset performance |
| Bank | `derive_debt_sizing_operating_input(inputs.operating, inputs.debt_sizing_case)` | DSCR sizing |

### Calculation Order

1. **Derive bank operating input** from Base + `DebtSizingCaseInput`.
2. **Run Phase 2B on Base** (`run_tax_cfads_model`) — for base periods/provenance.
3. **Run Phase 2A on Bank** (`run_operating_model`) — bank EBITDA for CFADS sizing.
4. **`tax_cfads_fn` uses bank periods** — sizing CFADS = bank EBITDA − bank cash tax.
5. **Solver converges** on bank CFADS satisfying the DSCR constraint.
6. **Recompute Base CFADS** with the solver's final senior interest — authoritative Base result.
7. **Populate `DebtSizingSchedules`** from bank operating schedules + bank CFADS.
8. Return `ProjectModelResult` with:
   - `operating_schedules` = Base
   - `tax_and_cfads` = Base with final interest
   - `senior_debt` = debt schedule (solver output)
   - `debt_sizing` = bank case schedules

### Invariant

The senior interest schedule that enters `tax_and_cfads` is the **same** final
schedule from the converged solver. The DSCR constraint was met against **bank
CFADS**; the Base CFADS in `tax_and_cfads` reflects the post-interest Base
economics for financial-statement purposes.

---

## 5. Fingerprint

`compute_senior_debt_fingerprint()` now includes `debt_sizing_case` in the
hash payload:

```python
"debt_sizing_case": {
    "production_yield_scenario": dc.production_yield_scenario.value,
    "merchant_price_calendar_start_year": ...,
    "merchant_prices_by_calendar_year_eur_mwh": [...],
    "market_prices_curve_eur_mwh": [...],
    # source_label EXCLUDED (audit-only)
}
```

A change to `production_yield_scenario` (P50 → P90_10Y) produces a different
fingerprint. Two runs differing only in `source_label` produce the **same**
fingerprint.

---

## 6. Governance Constraints

The following constraints remain in force throughout C3B3D2B3 and all
downstream stages:

```
GENERIC_DEBT_SIZING_CASE_IS_EXPLICIT_AND_PROJECT_IDENTITY_FREE
GENERIC_BANK_SIZING_DEFAULT_POLICY_IS_P90_10Y
DEBT_SIZING_CASE_FIELDS_ARE_USER_INPUTS_NOT_DERIVED_OUTPUTS
```

**Forbidden patterns:**
- Project-name dispatch (`"oborovo"`, `"tuho"`) in `financial_engine/`
- `DebtSizingScenario` (wrong abstraction name)
- `ProductionScenarioScope` (wrong abstraction name)
- `bank_sizing_scenario`, `bank_sizing_cfads_keur`, `bank_sizing_dscr`
- `_derive_bank_operating_input` (replaced by `derive_debt_sizing_operating_input`)
- Source workbook vectors as runtime inputs
- Hardcoded output schedules
- Target debt / target CFADS fitting
- Post-engine mutation
- Oborovo/TUHO calculation branches
- Excel-compatibility quirks in the generic case

---

## 7. Positive Acceptance: TUHO

TUHO Wind 1 uses P50 = 4164 h/year and P90-10y = 3620 h/year.

| Metric | Value |
|--------|-------|
| Base yield scenario | P50 (4164 h) |
| Bank yield scenario | P90_10Y (3620 h) |
| Bank/Base production ratio | 3620/4164 = 0.86936… (exact) |
| Bank CFADS at first operating period | ≈ 2539.6 kEUR (generic engine) |
| Source oracle (DS!D51 back-calculation) | 2539.633673 kEUR |

---

## 8. Anti-Overfitting: Oborovo

The Oborovo project's source workbook used a P50 bypass in the bank sizing
case. This bypass **must not enter the generic production engine**.

For all generic tests involving Oborovo, use:
```python
DebtSizingCaseInput(production_yield_scenario=YieldScenario.P90_10Y)
```

The source P50 bypass is an Oborovo-specific compatibility quirk
(`EXCEL_COMPATIBILITY_ONLY_PENDING_GENERIC_REVIEW`); it is NOT productionized.

---

## 9. Test Coverage

Test file: `tests/test_stage_c3b3d2b3_debt_sizing_case_production.py`

| Group | Tests | Focus |
|-------|-------|-------|
| A | A1–A6 | `DebtSizingCaseInput` structure/fields |
| B | B1–B3 | `SeniorDebtModelInput.debt_sizing_case` required |
| C | C1–C10 | `derive_debt_sizing_operating_input` transformer |
| D | D1–D4 | `DebtSizingSchedules` and `ProjectModelResult.debt_sizing` |
| E | E1–E3 | Fingerprint sensitivity and exclusions |
| F | F1–F7 | TUHO P90 positive acceptance |
| G | G1–G3 | Two-case separation (bank ≠ base) |
| H | H1–H3 | Oborovo anti-overfitting |
| I | I1–I5 | Governance: no forbidden names/patterns |
| Verdict | 1 | `C3B3D2B3_...RUNTIME_PROVEN` |

Total: 45 tests.

---

## 10. DO NOT MERGE

This PR is a DRAFT production contract. It must not be merged until the
complete downstream test suite (Phase 2D, waterfall integration) confirms
no regression.
