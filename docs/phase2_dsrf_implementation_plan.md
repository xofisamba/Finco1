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
    enabled: bool = False              # default False; zero impact on all outputs when False
    target_method: str = "months"     # "months" | "fixed" — "months" is primary path
    months_of_debt_service: int = 6   # semiannual periods; target = semiannual_DS × (months / 6)
    fixed_target_keur: float = 0.0    # used when target_method="fixed"
    funding_priority: int = 1          # order to fund relative to other reserves (lower = first)
    release_threshold_dscr: float = 1.35  # release excess DSRF when DSCR > this
    minimum_cash_after_funding_keur: float = 0.0  # minimum cash left after funding DSRF
    # Add: target_method, fixed_target_keur, funding_priority, minimum_cash_after_funding_keur
```

**DSRF target formula (semiannual model):**

```
target_keur = semiannual_debt_service_keur × (months_of_debt_service / 6)
```

Examples:
- `months_of_debt_service = 6` → target = 1.0 × semiannual debt service
- `months_of_debt_service = 12` → target = 2.0 × semiannual debt service
- `months_of_debt_service = 3` → target = 0.5 × semiannual debt service

### Validation rules
- `enabled=True` + `target_method="months"` + `months_of_debt_service < 1` → error
- `enabled=True` + `release_threshold_dscr <= 0` → error
- `enabled=True` + `release_threshold_dscr < funding_threshold_dscr` → warning (release before funding could happen)
- `enabled=False` → all other fields ignored; outputs are **identical** to `dsrf=None`

### Zero-impact requirement (enabled=False)
`DSRFConfig(enabled=False)` must be **byte-for-byte identical** to `dsrf=None`:
- distributions: unchanged
- IRR: unchanged
- DSCR: unchanged
- warnings: unchanged
- export behavior: no DSRF sheet, no extra rows

### IndependentPortfolioResult changes
Add fields (only populated when `dsrf_enabled=True`):
- `dsrf_balance_keur: float` — total DSRF balance at end of horizon
- `dsrf_funding_total_keur: float` — cumulative DSRF contributions
- `dsrf_release_total_keur: float` — cumulative DSRF releases
- `dsrf_schedule: list[DSRFPeriod]` — per-period funding/release/balance

### SPVOutput changes
Add per-SPV DSRF fields:
- `dsrf_balance_keur: float`
- `dsrf_funded_keur: float` — cumulative funding
- `dsrf_released_keur: float` — cumulative releases

---

## C. Waterfall Ordering (Semiannual)

For each SPV period (semiannual):

```
1. CFADS (revenue - opex, taxes paid)
2. Senior Debt Service (principal + interest)
3. DSRA funding/top-up — existing logic (funded first, from FCF after senior DS)
4. DSRF funding/top-up (if enabled and DSCR >= funding_threshold_dscr)
   - target = semiannual_debt_service × (months / 6)
   - available = max(0, FCF after senior DS and DSRA)
   - fund = min(available, max(0, target − balance))
   - funding must not create negative cash
5. DSRF release (if enabled and DSCR >= release_threshold_dscr and balance > target)
   - release = min(balance − target, available)  [returned to cash for distribution]
6. Distributions (FCF after all reserves → equity)
```

### DSRF funding source
DSRF funding comes **from cash available after senior debt service and DSRA/top-up**.
DSRF release **increases cash available for distributions** only when release criteria are met.
Funding must not create negative cash — `available = max(0, FCF)` enforces this.

### Key decisions
- **DSCR for triggers:** Use actual period DSCR (CFADS / debt service)
- **DSRA interaction:** DSRF and DSRA coexist. DSRA is funded first (existing), DSRF second.
- **Months semantics:** 1 semiannual period = 6 months. `months=6` = 1 period of DS. `months=12` = 2 periods.
- **No HoldCo, no SHL, no Sponsor IRR.**

---

## D. Export

### New Excel sheet: `DSRF` (when enabled=True)
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
- Semiannual interpretation of months (target = semiannual_DS × months/6)
- Funding/release triggers
- No impact when enabled=False

---

## E. Tests

### Zero-impact tests (enabled=False)
- `test_dsrf_disabled_identical_to_none`: DSRFConfig(enabled=False) == dsrf=None, distributions/IRR/DSCR/warnings identical
- `test_dsrf_disabled_no_export_changes`: no DSRF sheet created, no extra rows in Portfolio_Summary
- `test_dsrf_disabled_no_warnings`: no additional warnings generated

### Functional tests (enabled=True)
- `test_dsrf_funding_reduces_distributions`: when DSRF is funded, distributions decrease
- `test_dsrf_release_increases_distributions`: when DSRF is released, distributions increase
- `test_dsrf_funding_only_when_dscr_above_threshold`: DSRF only funded when DSCR >= threshold
- `test_dsrf_release_only_when_dscr_above_release_threshold`: release only when DSCR >= release threshold and balance > target
- `test_dsrf_target_semiannual_formula`: months=6 → target = semiannual_DS; months=12 → target = 2× semiannual_DS
- `test_dsrf_schedule_has_correct_columns`: DSRF sheet exists with correct columns when enabled

### Warning tests
- `test_dsrf_warns_when_release_threshold_below_funding_threshold`
- `test_dsrf_warns_when_months_less_than_1`

### No HoldCo/SHL/Sponsor IRR tests
- `test_no_holdco_sheet_created`: HoldCo sheet not created
- `test_no_sponsor_irr_in_results`: sponsor_irr not computed

---

## F. Risks

### 1. DSRA interaction
DSRA and DSRF both reserve cash. Funding order: DSRA first (existing), DSRF second. Explicit funding priority field ensures correct sequencing. Neither should starve the other — DSRA uses 30% of excess FCF; DSRF uses remaining FCF.

### 2. IRR/distribution impact
`enabled=True` is **expected** to reduce distributions in funding periods (cash diverted to DSRF) → equity IRR decreases vs `enabled=False`. This is the whole point of the reserve. Document clearly.

### 3. Semiannual interpretation of months
Formula: `target = semiannual_debt_service × (months / 6)`

Examples:
- `months=6` → target = 1.0 × semiannual_DS
- `months=12` → target = 2.0 × semiannual_DS
- `months=3` → target = 0.5 × semiannual_DS

### 4. Silent behavior changes (enabled=False)
`enabled=False` must be zero-impact — byte-for-byte identical to `dsrf=None`. Even logging is a regression.
**Mitigation:** Strict equality tests on distributions and IRR with/without DSRFConfig.

### 5. Threshold DSCR computation
DSCR = CFADS / debt service. If CFADS < 0 or debt service = 0, handle carefully. DSRF should not fund when DSCR < 0.

---

## Non-Scope (explicit)
- No HoldCo entity
- No SHL / intercompany flows
- No Sponsor IRR
- No monthly model frequency
- No pooled financing
- No cross-SP cash pooling
- No tax template engine yet