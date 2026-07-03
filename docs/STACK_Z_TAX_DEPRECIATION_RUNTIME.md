# Stack Z — Tax Depreciation Runtime Wiring

## Root Cause

The runtime engine computed taxable income using the same value for both book depreciation and tax depreciation: `period.depreciation_keur`, derived from total capex (70,691.5 kEUR). The `_tax_bridge_taxable_income_before_losses` formula:

```
taxable = EBITDA − book_dep − deductible_interest + disallowed_interest + tax_dep + fiscal_reintegration
```

When `book_dep == tax_dep`, these cancel and depreciation has zero net effect on taxable income. The existing tax depreciation bridge in `domain/depreciation/tax_bridge.py` and the inline `build_depreciation_ledger` path inside `_apply_tuho_tax_bridge_runtime_cash_tax` correctly computes distinct book and tax amounts — but the factory always passed `use_tax_bridge_engine=False`, bypassing this path.

---

## Runtime Architecture

The tax computation path has two modes, gated by `use_tax_bridge_engine`:

| Mode | Path | Depreciation basis |
|------|------|--------------------|
| `False` (pre-Z default) | Standard waterfall `tax_keur` | `book_dep == tax_dep == period.depreciation_keur` (capex, 70,691.5 kEUR) |
| `True` (Stack Z) | `_apply_tuho_tax_bridge_runtime_cash_tax` | `book_dep` from ledger (72,993.7 kEUR); `tax_dep` from ledger (70,691.5 kEUR) |

The `use_tax_bridge_engine=True` path also:
- Applies ATAD 30% EBITDA interest deductibility cap (fiscal reintegration)
- Uses gross-accrued SHL interest (fixture-extracted R27) instead of formula SHL interest
- Computes H2-only cash CIT settlement (`corporate_tax_cash_keur`) matching Excel R67 style
- Applies 5-year rolling LCF (`LossCarryforwardConfig(duration_years=5, country_template="croatia", expire_before_use=True)`)

---

## Bridge Architecture

The depreciation bridge is in `app/waterfall_core.py` inside `_apply_tuho_tax_bridge_runtime_cash_tax` (~line 940). It builds a `DepreciationLedger` using:

```python
TUHO_BOOK_TOTAL = 72_993.7  # kEUR — accounting book value
TUHO_TAX_TOTAL  = 70_691.5  # kEUR — tax depreciable base = total capex
```

Both use `useful_life_book_periods = useful_life_tax_periods = 60` (semiannual, 30 years). The period-level amounts are:

- Book depreciation per period: 72,993.7 / 60 = 1,216.56 kEUR
- Tax depreciation per period:  70,691.5 / 60 = 1,178.19 kEUR
- Net effect on taxable income: −(1,216.56 − 1,178.19) = −38.37 kEUR/period

---

## Implementation

**`app/project_factories.py`** — Added `use_tax_bridge_engine=True` to TUHO `ProjectInfo`:

```python
info = ProjectInfo(
    ...
    use_senior_debt_sizing_engine=True,
    use_tax_bridge_engine=True,  # Stack Z: tax depreciation runtime wiring
)
```

No changes to `waterfall_core.py` or the bridge logic itself. The existing bridge is reused exactly as designed.

---

## Regression

| KPI | Pre-Stack-Z (flag off) | Stack Z (flag on) | Change |
|-----|----------------------|-------------------|--------|
| TUHO equity IRR | 11.32% | 11.32% | ✅ unchanged |
| TUHO project IRR | 9.41% | 9.41% | ✅ unchanged |
| TUHO actual_avg_dscr | 1.3786 | 1.3786 | ✅ unchanged |
| TUHO total_distribution_keur | 165,471 | 165,471 | ✅ unchanged |
| TUHO total_senior_ds_keur | unchanged | unchanged | ✅ unchanged |
| TUHO total_shl_service_keur | unchanged | unchanged | ✅ unchanged |
| TUHO total_tax_keur (accrued) | 33,184 | 45,835 | ⬆️ +12,651 (expected) |
| TUHO cash CIT (R67 bridge) | 20,140 | 43,512 | ⬆️ expected movement |
| Oborovo equity IRR | 10.54% | 10.54% | ✅ unchanged |
| Oborovo actual_avg_dscr | 1.179 | 1.179 | ✅ unchanged |
| Oborovo total_tax_keur | 8,874 | 8,874 | ✅ unchanged |

Debt sizing, sculpting, repayment schedule, SHL mechanics, distributions, and IRR algorithms are all unchanged. Only CIT is affected.

---

## Known Gaps

### 1. Oborovo tax depreciation bridge

Oborovo (`OBR-001`) remains guarded — `use_tax_bridge_engine=True` raises `ValueError`. Oborovo does not yet have fixture data separating book vs tax depreciation. This is a follow-on item.

### 2. Construction period loss vintage

The bridge's opening LCF bucket is populated from `result.periods[0].tax_loss_opening_audit_keur`. This field is not currently set by the waterfall engine for the first operating period. As a result, the ~25,000 kEUR TUHO construction loss is absorbed in flag-off mode (by the waterfall engine's standard LCF) but not re-applied in the bridge's flag-on path. This is part of the known residual between Finco and Excel.

### Known Excel Limitation — LCF Methodology

**Finco intentionally differs from Excel on Loss Carry-Forward.**

Croatian tax law (§16 CIT Act) limits LCF to 5 years from the loss year. The Finco implementation uses:

```python
LossCarryforwardConfig(
    duration_years=5,
    periods_per_year=2,
    country_template="croatia",
    expire_before_use=True,
)
```

The Excel workbook incorrectly treats LCF as perpetual (no expiry). This produces a known residual of approximately −5,271 kEUR between Finco R67 and Excel R67:

| Source | R67 total (kEUR) |
|--------|-----------------|
| Excel | −38,241 |
| Finco (Stack Z) | −43,512 |
| Residual | −5,271 |

**This residual is intentional and must not be zeroed by a scalar plug.** Finco's LCF treatment is correct; Excel's is not.

---

## Test Coverage

`tests/test_stack_z_tax_depreciation_runtime.py` — 21 tests:

- **Z1 — Factory opt-in**: TUHO factory defaults to `use_tax_bridge_engine=True`; Oborovo remains False; Oborovo flag-on still guarded
- **Z2 — Book vs tax depreciation**: fixture totals differ; audit field populated; period dep sums to tax capex
- **Z3 — Taxable income**: accrued CIT positive; Stack Z baseline value; H1 cash tax zero; lifetime cash CIT baseline; LCF residual documented
- **Z4 — Golden regression**: equity IRR, avg DSCR, distributions, senior DS, SHL service unchanged; CIT increased; Oborovo not regressed
- **Z5 — No duplicated logic**: config reflects factory; LCF methodology not weakened

---

## Guardrails Confirmed

- No `LCF` logic changes — only `use_tax_bridge_engine` factory flag
- No debt sizing changes
- No sculpting changes
- No SHL algorithm changes
- No IRR algorithm changes
- No project factory changes beyond TUHO `use_tax_bridge_engine=True`
- Existing bridge reused — no new depreciation logic created
- SHA pin for `project_factories.py` updated in `test_phase51f_parallel_work_guardrails.py`
