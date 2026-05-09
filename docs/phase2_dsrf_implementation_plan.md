# Phase 2 DSRF Implementation Plan
**Branch:** `portfolio-dsrf` (from `main` SHA `4004388`)  
**Not implemented yet — planning only.**

---

## A. Files to Inspect/Touch

### New files
- `domain/portfolio/independent/dsrf.py` — DSRF revolving facility calculation engine (new)
- `tests/test_dsrf.py` — DSRF tests (new)

### Files to inspect (read, understand before touching)
- `domain/portfolio/independent/inputs.py` — DSRFConfig already exists (placeholder)
- `domain/portfolio/independent/result.py` — IndependentPortfolioResult, SPVOutput
- `domain/portfolio/independent/runner.py` — run_independent_portfolio flow
- `domain/waterfall/reserves.py` — existing DSRA engine (DSRA = reference, not to modify)
- `domain/waterfall/cash_flow.py` — CFADS computation
- `domain/waterfall/waterfall_engine.py` — waterfall core
- `app/excel_export.py` — portfolio export sheets
- `app/portfolio_ui.py` — display helpers
- `docs/phase1_5_portfolio_ui_export.md` — reference for scope

### Not to modify (safety)
- `domain/waterfall/dsra_engine.py` — existing DSRA, do not change
- `domain/waterfall/shl_engine.py` — SHL not in scope
- `domain/portfolio/waterfall.py` — pooled financing, not scope

---

## B. Conceptual Distinction: DSRA vs DSRF

### DSRA — Cash Reserve Account
- **Nature:** Physical cash reserve account
- **Funded:** at financial close (initial injection) + topped up through waterfall from excess FCF
- **Has:** actual cash balance
- **Purpose:** ensures cash available if CFADS is temporarily insufficient for debt service
- **Draw:** cash transferred from DSRA to cover shortfall, then replenished from FCF

### DSRF — Revolving Debt Service Reserve Facility (Liquidity Facility)
- **Nature:** revolving credit facility / committed facility
- **Has:** facility limit, drawn amount, undrawn amount — no cash balance
- **Draw trigger:** CFADS is insufficient to cover scheduled senior debt service
- **Costs:**
  - Commitment fee on undrawn amount (paid regardless of draw activity)
  - Interest on drawn amount: EURIBOR + margin
- **Repayment:** drawn amount must be repaid from available cash before distributions
- **Key point:** DSRF does not increase project economics — it only prevents senior debt service default when facility capacity is available

### Critical distinction
- DSRA = cash reserve (funded, topped-up, released — cash terminology applies)
- DSRF = revolving facility (drawn, repaid, interest, commitment fee — credit facility terminology applies)
- DSRF is **not** funded like a cash reserve; it is a committed facility that can be drawn when needed

---

## C. Data Model

### DSRFConfig (update from placeholder)

```python
@dataclass
class DSRFConfig:
    enabled: bool = False
    # Facility limit
    facility_limit_method: str = "months_of_debt_service"  # "months_of_debt_service" | "fixed"
    months_of_debt_service: int = 6   # used when method="months_of_debt_service"
    fixed_facility_limit_keur: float = 0.0  # used when method="fixed"
    # Facility economics
    commitment_fee_rate_pa: float = 0.0    # e.g. 0.5% p.a. on undrawn amount
    margin_rate_pa: float = 0.0           # e.g. 2.0% p.a. on drawn amount
    euribor_rate_pa: float = 0.0           # e.g. 3.0% p.a. reference rate
    period_year_fraction: float = 0.5      # 0.5 for semiannual periods (annual_rate × 0.5 = period charge)
    repayment_priority: str = "before_distributions"  # always repay before distributions
    allow_draw_for_debt_service_shortfall: bool = True
```

**Facility limit formula (semiannual model):**

```
facility_limit_keur = semiannual_debt_service_keur × (months_of_debt_service / 6)
```

Examples:
- `months_of_debt_service = 6` → facility_limit = 1.0 × semiannual debt service
- `months_of_debt_service = 12` → facility_limit = 2.0 × semiannual debt service
- `months_of_debt_service = 3` → facility_limit = 0.5 × semiannual debt service

### Validation rules
- `enabled=True` + `facility_limit_method="months_of_debt_service"` + `months_of_debt_service < 1` → error
- `enabled=True` + `facility_limit_method="fixed"` + `fixed_facility_limit_keur <= 0` → error
- `enabled=True` + any rate < 0 → error
- `enabled=False` → all other fields ignored; outputs are **identical** to `dsrf=None`

### Zero-impact requirement (enabled=False)
`DSRFConfig(enabled=False)` must be **byte-for-byte identical** to `dsrf=None`:
- distributions: unchanged
- IRR: unchanged
- DSCR: unchanged
- senior debt service schedule: unchanged
- warnings: unchanged
- export behavior: no DSRF sheet, no extra rows

---

## D. Waterfall Ordering (Semiannual)

For each SPV per semiannual period:

```
1. CFADS (revenue - opex - taxes paid)
2. Scheduled senior debt service due
3. Determine senior debt service shortfall:
   shortfall = max(0, scheduled_senior_ds - CFADS_available)
   if shortfall > 0: draw DSRF up to undrawn facility amount
   draw = min(shortfall, undrawn_start)
4. Pay senior debt service using CFADS + DSRF draw
5. Calculate DSRF interest on drawn amount:
   drawn_interest = drawn_start × (euribor_rate_pa + margin_rate_pa) × period_year_fraction
6. Calculate commitment fee on undrawn amount:
   commitment_fee = undrawn_start × commitment_fee_rate_pa × period_year_fraction
7. Pay DSRF interest and commitment fee from remaining cash
8. Repay drawn DSRF from remaining cash before distributions:
   repayment = min(remaining_cash_after_fees, drawn_start + draw)
9. Distributions (remaining cash after DSRF repayment → equity)
```

**Key clarifications:**
- **Draw happens BEFORE senior debt service is paid** — shortfall is covered by DSRF draw so senior debt service can be paid in full
- **Commitment fee** applies only on undrawn amount (never on drawn)
- **Interest** applies only on drawn amount (never on undrawn)
- **Repayment** consumes available cash before distributions — drawn_end = drawn_start + draw − repayment
- `enabled=False`: entire DSRF block is skipped; senior debt service is paid using CFADS only

---

## E. Result Model

### IndependentPortfolioResult changes
Add fields (populated when `dsrf_enabled=True`):
- `dsrf_facility_limit_keur: float` — total facility limit
- `dsrf_drawn_total_keur: float` — cumulative amount drawn across all SPVs
- `dsrf_repayment_total_keur: float` — cumulative repayments
- `dsrf_commitment_fee_total_keur: float` — cumulative commitment fees paid
- `dsrf_interest_total_keur: float` — cumulative interest paid
- `dsrf_debt_service_support_total_keur: float` — total shortfall covered by DSRF draws
- `dsrf_schedule: list[DSRFPeriod]` — per-period detail

### SPVOutput changes
Add per-SPV DSRF fields:
- `dsrf_drawn_total_keur: float`
- `dsrf_repayment_total_keur: float`
- `dsrf_commitment_fee_keur: float`
- `dsrf_interest_keur: float`

### DSRFPeriod (per-period detail)
| Field | Description |
|-------|-------------|
| `period` | Semiannual period index |
| `spv_code` | SPV identifier |
| `facility_limit_keur` | Facility limit this period |
| `drawn_start_keur` | Drawn amount at period start |
| `undrawn_start_keur` | Undrawn at period start (= facility_limit − drawn_start) |
| `scheduled_senior_ds_keur` | Scheduled senior debt service this period |
| `cfads_available_keur` | CFADS available for debt service |
| `debt_service_shortfall_keur` | Shortfall covered by DSRF draw |
| `draw_keur` | Amount drawn this period |
| `drawn_interest_keur` | Interest on drawn amount this period |
| `commitment_fee_keur` | Commitment fee on undrawn amount |
| `repayment_keur` | DSRF repayment this period |
| `drawn_end_keur` | Drawn amount at period end |
| `undrawn_end_keur` | Undrawn at period end (= facility_limit − drawn_end) |

---

## F. Export

### New Excel sheet: `DSRF` (when enabled=True)
| Column | Description |
|--------|-------------|
| Period | Semiannual period index |
| SPV Code | Per-SPV |
| Facility Limit (kEUR) | Facility limit |
| Drawn Start (kEUR) | Drawn amount at period open |
| Undrawn Start (kEUR) | Undrawn at period open |
| Scheduled Senior DS (kEUR) | Scheduled senior debt service |
| CFADS Available (kEUR) | CFADS for debt service |
| Debt Service Shortfall (kEUR) | Shortfall covered by DSRF draw |
| Draw (kEUR) | Amount drawn this period |
| Drawn Interest (kEUR) | Interest on drawn amount |
| Commitment Fee (kEUR) | Fee on undrawn amount |
| Repayment (kEUR) | DSRF repayment this period |
| Drawn End (kEUR) | Drawn amount at period close |
| Undrawn End (kEUR) | Undrawn at period close |

### Portfolio_Summary rows (when enabled)
- `DSRF Facility Limit (kEUR)` — total facility
- `DSRF Drawn End (kEUR)` — drawn amount outstanding
- `DSRF Total Drawn (kEUR)` — cumulative drawn
- `DSRF Total Repaid (kEUR)` — cumulative repaid
- `DSRF Commitment Fee Paid (kEUR)` — cumulative commitment fees
- `DSRF Interest Paid (kEUR)` — cumulative interest
- `DSRF Debt Service Support (kEUR)` — total shortfall covered

### Portfolio_Notes update
Add DSRF section:
- DSRF is a revolving facility, not a cash reserve
- Facility limit = semiannual_DS × (months / 6)
- Draw covers shortfalls before debt service is paid
- Commitment fee on undrawn; interest on drawn
- Repayment before distributions
- No impact when enabled=False
- **No DSRA terminology** should appear in DSRF output labels (no "top-up", "release", "balance")

---

## G. Tests

### Zero-impact tests (enabled=False)
- `test_dsrf_disabled_identical_to_none`: DSRFConfig(enabled=False) == dsrf=None; distributions/IRR/DSCR/senior_DS/warnings identical
- `test_dsrf_disabled_no_export_changes`: no DSRF sheet, no extra rows in Portfolio_Summary
- `test_dsrf_disabled_no_warnings`: no additional warnings generated

### Facility limit tests
- `test_facility_limit_formula_months_6`: months=6 → limit = 1.0 × semiannual_DS
- `test_facility_limit_formula_months_12`: months=12 → limit = 2.0 × semiannual_DS
- `test_facility_limit_formula_months_3`: months=3 → limit = 0.5 × semiannual_DS
- `test_fixed_facility_limit_used_when_method_fixed`

### Fee tests
- `test_commitment_fee_on_undrawn_only`: fee = undrawn_start × commitment_fee_rate_pa × 0.5; not on drawn
- `test_drawn_interest_on_drawn_only`: interest = drawn_start × (margin_pa + euribor_pa) × 0.5; not on undrawn
- `test_no_fees_when_facility_undrawn`: when drawn=0, commitment_fee only

### Draw/repayment tests
- `test_draw_only_on_shortfall`: draw > 0 only when CFADS < scheduled senior debt service
- `test_draw_before_debt_service_paid`: shortfall triggers draw before debt service is scheduled
- `test_draw_capped_by_undrawn`: draw ≤ undrawn_amount at start of period
- `test_repayment_reduces_drawn`: drawn_end = drawn_start + draw − repayment
- `test_repayment_before_distributions`: repayment consumes available cash before distributions
- `test_no_negative_draw`: draw is never negative

### Economic impact tests (enabled=True)
- `test_commitment_fee_reduces_distributions`: commitment fee reduces cash available for distributions
- `test_interest_reduces_distributions`: drawn interest reduces cash available for distributions
- `test_dsrf_draw_covers_shortfall`: shortfall covered by draw → senior debt service is paid in full
- `test_dsrf_undrawn_amount_increases_after_repayment`: undrawn_end = facility_limit − drawn_end

### Export tests
- `test_dsrf_sheet_exists_when_enabled`: DSRF sheet present
- `test_dsrf_sheet_columns`: all 14 columns present including draw, interest, fee, repayment
- `test_dsrf_sheet_absent_when_disabled`: no DSRF sheet when enabled=False
- `test_dsrf_output_no_cash_reserve_terminology`: no "top-up", "release", "balance", "funded" in DSRF sheet labels (facility terminology only)

### No new scope tests
- `test_no_holdco_sheet_created`: HoldCo sheet not created
- `test_no_sponsor_irr_in_results`: sponsor_irr not computed
- `test_no_shl_mechanics`: no SHL flows introduced

---

## H. Risks

### 1. DSRA vs DSRF terminology confusion
DSRA is a cash reserve; DSRF is a credit facility. Implementation must use correct terminology:
- DSRF uses "draw", "repayment", "drawn", "undrawn", "facility limit"
- DSRF must NOT use "fund", "top-up", "release", "balance" (these are DSRA concepts)

### 2. Draw timing
DSRF draw must happen BEFORE senior debt service is paid — proceeds go directly to cover the shortfall. This differs from DSRA which is drawn after shortfalls are identified. Correct sequencing is critical.

### 3. Interest/fee formulas
All rates are annual. Semiannual charge = annual_rate × `period_year_fraction` (0.5).
- Interest: `drawn_start × (margin_pa + euribor_pa) × 0.5`
- Commitment fee: `undrawn_start × commitment_fee_rate_pa × 0.5`

### 4. Zero-impact guarantee
`enabled=False` must be byte-for-byte identical to `dsrf=None`. Even logging or comment changes are regressions.

### 5. Repayment and cash priority
Repayment consumes available cash before distributions. Ensure repayment calculation handles the case where remaining cash < drawn amount (repayment capped at available cash).

---

## Non-Scope (explicit)
- No HoldCo entity
- No SHL / intercompany flows
- No Sponsor IRR
- No monthly model frequency
- No pooled financing
- No cross-SP cash pooling
- No tax template engine yet