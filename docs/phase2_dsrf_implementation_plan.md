# Phase 2 DSRF Implementation Plan
**Branch:** `portfolio-dsrf` (from `main` SHA `4004388`)  
**Not implemented yet — planning only.**

---

## A. Files to Inspect/Touch

### New files
- `domain/portfolio/independent/dsrf.py` — DSRF calculation engine (new)
- `tests/test_dsrf.py` — DSRF tests (new)

### Files to inspect (read, understand before touching)
- `domain/portfolio/independent/inputs.py` — DSRFConfig already exists (placeholder)
- `domain/portfolio/independent/result.py` — IndependentPortfolioResult, SPVOutput
- `domain/portfolio/independent/runner.py` — run_independent_portfolio flow
- `domain/waterfall/reserves.py` — existing DSRA engine (DSRA = reference, not to modify)
- `domain/waterfall/cash_flow.py` — CFADS computation
- `domain/waterfall/waterfall_engine.py` — waterfall core
- `app/excel_export.py` — Portfolio_Summary/Portfolio_SPVs/Portfolio_Notes sheets
- `app/portfolio_ui.py` — display helpers
- `docs/phase1_5_portfolio_ui_export.md` — reference for scope

### Not to modify (safety)
- `domain/waterfall/dsra_engine.py` — existing DSRA, do not change
- `domain/waterfall/shl_engine.py` — SHL not in scope
- `domain/portfolio/waterfall.py` — pooled financing, not scope

---

## B. Data Model

### DSRFConfig (already exists in inputs.py, fields to fill)

```python
@dataclass
class DSRFConfig:
    enabled: bool = False              # Phase 2: default False, zero impact when False
    target_method: str = "months"      # "months" | "fixed" | "ratio"
    months_of_debt_service: int = 6     # target = months × (semiannual_debt_service / 2)  [semiannual model]
    fixed_target_keur: float = 0.0      # used when target_method="fixed"
    funding_priority: int = 1           # order to fund relative to other reserves (lower = first)
    release_threshold_dscr: float = 1.35  # release excess DSRF when DSCR > this
    minimum_cash_after_funding_keur: float = 0.0  # minimum cash left after funding DSRF
    # Phase 1 DSRFConfig had: funding_threshold_dscr, release_threshold_dscr
    # Add: target_method, fixed_target_keur, funding_priority, minimum_cash_after_funding_keur
```

### Validation rules
- `enabled=True` + `target_method="months"` + `months_of_debt_service < 1` → error
- `enabled=True` + `release_threshold_dscr <= 0` → error
- `enabled=True` + `release_threshold_dscr < funding_threshold_dscr` → warning (release before funding)
- `enabled=False` → all other fields ignored, no impact

### IndependentPortfolioResult changes
Add fields (only used when dsrf_enabled=True):
- `dsrf_balance_keur: float` — total DSRF balance across portfolio at end of horizon
- `dsrf_funding_total_keur: float` — cumulative DSRF contributions
- `dsrf_release_total_keur: float` — cumulative DSRF releases
- `dsrf_schedule: list[DSRFPeriod]` — per-period DSRF funding/release/balance

### SPVOutput changes
Add per-SPV DSRF fields:
- `dsrf_balance_keur: float`
- `dsrf_funded_keur: float` — cumulative funding this SPV
- `dsrf_released_keur: float` — cumulative releases

---

## C. Waterfall Ordering (Semiannual)

For each SPV period (semiannual):

```
1. CFADS (revenue - opex, taxes paid)
2. Senior Debt Service (principal + interest)
3. DSRA funding/top-up (if DSRA balance < target) — existing logic
4. DSRF funding/top-up (if enabled and DSCR >= funding_threshold_dscr)
   - Target = months × semiannual_debt_service
   - Available = max(0, FCF after senior DS and DSRA)
   - Fund = min(available, target - balance)
5. DSRF release (if enabled and DSCR >= release_threshold_dscr and balance > target)
   - Release = min(balance - target, available)  [returned to cash for distribution]
6. Distributions (FCF after all reserves → equity)
```

### Key decisions
- **Months interpretation (semiannual):** `months=6` means 6 months of annual debt service → target = 6/12 × annual_DS = semiannual_DS × 3? Or 6/12 × annual_DS = semiannual_DS × 1? Clarify: "6 months of senior debt service" → in semiannual model, 1 period = 6 months, so `months=6` = 1 full semiannual period of DS → target = semiannual_debt_service × 1. `months=12` = semiannual_DS × 2.
- **DSCR for funding/release triggers:** Use actual period DSCR (CFADS / debt service)
- **Interaction with DSRA:** DSRF and DSRA are separate reserves; both can coexist. DSRA is funded first (priority=0 or 1), then DSRF.
- **DSRF funding source:** FCF after senior DS and DSRA contribution. If FCF is insufficient, DSRF is not funded.

---

## D. Export

### New Excel sheet: `DSRF`
| Column | Description |
|--------|-------------|
| Period | Semiannual period index |
| SPV Code | Per-SPV |
| DSCR | Period DSCR |
| DSRF Target (kEUR) | Target balance |
| DSRF Balance Start (kEUR) | Opening balance |
| DSRF Funded (kEUR) | Funding this period |
| DSRF Released (kEUR) | Release this period |
| DSRF Balance End (kEUR) | Closing balance |

### Portfolio_Summary changes
Add rows (when enabled):
- `DSRF Balance (kEUR)` — closing balance
- `DSRF Funded (kEUR)` — cumulative
- `DSRF Released (kEUR)` — cumulative

### Portfolio_Notes update
Add DSRF section explaining:
- Semiannual interpretation of months
- Funding/release triggers
- No impact when enabled=False

---

## E. Tests

### Zero-impact tests (enabled=False)
- `test_dsrf_disabled_zero_impact_on_distributions`: same output with/without DSRF config
- `test_dsrf_disabled_zero_impact_on_irr`: IRR unchanged
- `test_dsrf_disabled_no_schedule_created`: dsrf_schedule is empty

### Functional tests (enabled=True)
- `test_dsrf_funding_reduces_cash_for_distribution`: when DSRF is funded, distributions decrease
- `test_dsrf_release_increases_cash_for_distribution`: when DSRF is released, distributions increase
- `test_dsrf_funding_only_when_dscr_above_threshold`: DSRF only funded when DSCR >= threshold
- `test_dsrf_release_only_when_dscr_above_release_threshold`: release only when DSCR >= release threshold
- `test_dsrf_target_uses_semiannual_debt_service`: months=6 → target = semiannual_DS
- `test_dsrf_schedule_has_correct_columns`: DSRF sheet exists with correct columns

### Warning tests
- `test_dsrf_warns_when_release_threshold_below_funding_threshold`
- `test_dsrf_warns_when_months_less_than_1`

### No HoldCo/SHL/Sponsor IRR tests
- `test_no_holdco_sheet_created`: HoldCo sheet not created
- `test_no_sponsor_irr_in_results`: sponsor_irr not computed

---

## F. Risks

### 1. DSRA interaction
DSRA and DSRF both reserve cash. Funding order matters. Need to ensure DSRF funding doesn't starve DSRA or vice versa.
**Mitigation:** Explicit funding priority field; DSRA funded first (existing), DSRF second.

### 2. IRR/distribution impact
Adding DSRF reduces distributions in funding periods → equity IRR decreases. Must be explicit in Portfolio_Notes.
**Mitigation:** Test that enabled=True changes distributions; document clearly.

### 3. Semiannual interpretation of "months"
Confusion: `months=6` could mean 6 months of annual DS (target = annual_DS/2) or 6 months of semiannual DS (target = semiannual_DS). Clarify as: `months` × annual_debt_service / 12 = semiannual_target × (months/6).
**Mitigation:** Document clearly; tests with months=6 vs months=12.

### 4. Silent behavior changes
enabled=False must be truly zero-impact. Any side effect (even logging) is a regression.
**Mitigation:** Strict equality tests on distributions and IRR with enabled=True vs disabled.

### 5. Threshold DSCR computation
DSCR = CFADS / debt_service. If CFADS < 0, DSCR is negative — DSRF shouldn't fund in that case.
**Mitigation:** Funding only when DSCR >= threshold AND FCF > 0.

---

## Non-Scope (explicit)
- No HoldCo entity
- No SHL / intercompany flows
- No Sponsor IRR
- No monthly model frequency
- No pooled financing
- No cross-SP cash pooling
- No tax template engine yet