# Phase 4A SHL Foundation

## Status
**Implemented:** SHL data model, straight-line amortization engine, HoldCo passthrough preparation.

## Architecture Target

```
SPV waterfall
  → dividend upstream
  → SHL interest upstream
  → SHL principal upstream
  → HoldCo aggregation
  → future tax engine
  → future sponsor layer
```

---

## Implemented Scope

### 1. SHL Data Model (`domain/portfolio/shl/`)

**`SHLFacility`** — single intercompany loan facility:
- `lender_entity_code`, `borrower_entity_code` — entities
- `principal_keur`, `interest_rate_pa`, `tenor_years`
- `sculpted: bool = False` — sculpted (cash flow matching) vs fixed schedule
- `capitalization_allowed: bool = False` — accrued interest added to principal
- `payment_frequency_per_year: int = 2` — {1, 2, 4, 12}
- `start_period_index: int = 0`

**`SHLPortfolioInputs`** — portfolio-level collection of facilities.

### 2. SHL Result Model

**`SHLPeriodResult`** — per-period state:
- `period_index`, `opening_balance_keur`, `interest_accrued_keur`
- `interest_paid_keur`, `principal_paid_keur`, `closing_balance_keur`

**`SHLFacilityResult`** — facility-level totals + all periods.

**`SHLPortfolioResult`** — portfolio-level aggregation.

### 3. SHL Engine (`run_shl_facility`, `run_shl_portfolio`)

Straight-line amortization (no sculpting, no capitalization):
- Principal paid in equal portions each period
- Interest = `opening_balance * rate / frequency`
- Final period: closing balance forced to 0
- No negative balances

### 4. HoldCo Passthrough Preparation

Updated `domain/portfolio/holdco/runner.py`:
- `dividend_share = spv_dist * ownership_pct`
- `shl_interest_share = 0.0` — placeholder (TODO comment for future SHL phase)
- `shl_principal_share = 0.0` — placeholder
- `holdco_income_share = dividend_share + shl_interest_share`
- **SHL principal excluded from `period_gross`** (balance-sheet only)

Placeholder comments added:
```
# TODO(SHL): read from waterfall period shl_interest_keur
# TODO(SHL): read from waterfall period shl_principal_keur
```

### 5. Waterfall Passthrough

- `WaterfallPeriod.shl_interest_keur` already exists in `domain/reporting/financial_statements.py`
- `WaterfallPeriod.shl_principal_keur` already exists
- No changes needed to waterfall engine

---

## Income Component Relationships

| Component | Contributes to `period_gross`? | Notes |
|-----------|--------------------------------|-------|
| `dividend_keur` | ✅ Yes | Raw SPV distribution × ownership % |
| `shl_interest_keur` | ✅ Yes (future) | SHL interest income |
| `shl_principal_keur` | ❌ No | Balance-sheet only — return of capital |

Current state: all SHL = 0.0, `period_gross = dividend_share`

---

## Explicit Non-Scope

The following are **NOT implemented** in this phase:

| Feature | Reason |
|---------|--------|
| SHL capitalization | Accrued interest → principal not implemented |
| SHL sculpting | Cash flow matching not implemented |
| Circular intercompany loops | No recursion detection |
| Recursive ownership | No recursive ownership graph |
| Tax optimization | No ATAD, withholding tax, or detailed tax logic |
| HoldCo IRR | Deferred beyond Phase 4A |
| Sponsor IRR | Deferred beyond Phase 4A |
| Retained earnings | Not in scope |
| Refinancing | Not in scope |
| Monthly model | Separate model |
| Pooled financing redesign | Frozen |

---

## Future SHL Phases (Roadmap)

1. **Phase 4B:** Connect SHL engine output to HoldCo runner — replace `shl_interest_share = 0.0` placeholders with actual upstream values from waterfall period's `shl_interest_keur`/`shl_principal_keur`

2. **Future:** SHL sculpting (cash flow matching) — replace straight-line with sculpted payments

3. **Future:** SHL capitalization — when `capitalization_allowed=True`, accrued interest is added to principal

4. **Future:** Circular loop detection — prevent infinite recursion in intercompany flows

5. **Future:** HoldCo IRR computation — `HoldCoResult.holdco_irr`

6. **Future:** Tax template engine — replace flat `tax_rate_pa` with detailed tax treatment

---

## Files Changed (Phase 4A)

| File | Change |
|------|--------|
| `domain/portfolio/shl/__init__.py` | SHL package exports |
| `domain/portfolio/shl/inputs.py` | `SHLFacility`, `SHLPortfolioInputs` |
| `domain/portfolio/shl/result.py` | `SHLPeriodResult`, `SHLFacilityResult`, `SHLPortfolioResult` |
| `domain/portfolio/shl/runner.py` | `run_shl_facility`, `run_shl_portfolio` |
| `domain/portfolio/holdco/runner.py` | SHL placeholder comments, TODO markers |
| `tests/test_shl_inputs.py` | SHL input validation tests |
| `tests/test_shl_result.py` | SHL result structure tests |
| `tests/test_shl_runner.py` | SHL engine straight-line amortization tests |
| `docs/phase4a_shl_foundation.md` | This document |

---

## Testing

```
83 passed (SHL + HoldCo targeted suites)
1620+ passed (full regression)
```

All existing portfolio, DSRF, and HoldCo tests continue to pass.

---

## P4B: SHL Upstream Integration

**Implemented in commit `portfolio-shl-phase2` (PR to main).**

### Changes to HoldCo Runner

The HoldCo aggregation runner now reads SHL interest and principal directly from `WaterfallPeriod`:

```python
# P4B: SHL upstreaming — three cash flow components
wf_period = periods_data[period_idx]
shl_interest_raw = _safe_get_float(wf_period, 'shl_interest_keur', 0.0)
shl_principal_raw = _safe_get_float(wf_period, 'shl_principal_keur', 0.0)

dividend_share = spv_dist * ownership_pct
shl_interest_share = shl_interest_raw * ownership_pct
shl_principal_share = shl_principal_raw * ownership_pct

# holdco_income = dividend + SHL interest (principal excluded from taxable income)
holdco_income_share = dividend_share + shl_interest_share
period_gross += holdco_income_share
```

### Income vs Balance-Sheet Treatment

| Component | HoldCo gross income | HoldCo tax base | Notes |
|-----------|---------------------|-----------------|-------|
| `dividend_keur` | ✅ Yes | ✅ Yes | Equity distribution |
| `shl_interest_keur` | ✅ Yes | ✅ Yes | Taxable income |
| `shl_principal_keur` | ❌ No | ❌ No | Cash movement only |

### SHL Interest + Dividend Inclusion

`total_gross_income_keur = total_dividend_keur + total_shl_interest_keur`

`total_shl_principal_keur` is tracked separately but **never** flows through `gross_income_keur`.

### Why Principal is Excluded

SHL principal repayment is a return of capital, not income. Including it in `gross_income` would overstate HoldCo's taxable earnings. The principal is still tracked in:
- `HoldCoPeriodResult.shl_principal_keur`
- `HoldCoSPVContribution.shl_principal_keur`
- `HoldCoResult.total_shl_principal_keur`

---

## Explicit Non-Scope (P4B Extension)

The current phase does **NOT** calculate:

- **Withholding tax** — applicable to cross-border dividend/interest payments
- **Transfer pricing** — arm's length pricing for intercompany transactions
- **SHL capitalization** — accrued interest added to principal (future phase)
- **SHL sculpting** — cash flow matching (future phase)
- **Tax deductibility limits** — thin capitalization, earnings stripping rules
- **ATAD** — Anti-Tax Avoidance Directive compliance
- **Circular structures** — recursive intercompany flows
- **HoldCo IRR** — deferred beyond P4B
- **Sponsor IRR** — deferred beyond P4B

These will be addressed in future phases with the tax template engine.

---

## Future Tax Engine Dependency

HoldCo's current `tax_rate_pa` is a flat placeholder. Future tax template engine will:

1. Apply different rates to dividend vs SHL interest vs SHL principal
2. Handle withholding tax on cross-border flows
3. Apply participation exemption rules
4. Implement ATAD anti-avoidance rules

The P4B architecture (separate dividend/interest/principal fields) enables this future transition without schema changes.
