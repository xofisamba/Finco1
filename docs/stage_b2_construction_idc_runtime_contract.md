# Stage B2 — Generic Construction / IDC Runtime Contract

**Status**: PENDING — this document defines the required architecture for the next workstream.
**Source authority**: Oborovo workbook reviewed 2026-07-22.
**Predecessor**: Stage B1 (`recon-fix-03-stageb1-book-depreciation`, PR #905).

---

## 1. Why this document exists

Stage B1 carries SOURCE-DERIVED CALIBRATION VALUES for capitalized financing costs
(Senior IDC, commitment fees, structuring fees, VAT facility IDC, VAT facility commitment fee)
as temporary override inputs, pending a generic Construction/IDC runtime engine.

These values are DERIVED OUTPUTS of the workbook construction financing model — not permanent
primary user inputs. The current calibration boundaries must be replaced by computed outputs
from a generic engine.

This document is the handoff contract for Stage B2.

---

## 2. Required runtime inputs

### 2.1 Construction timeline
- `construction_start_date`: date
- `construction_months`: int (Oborovo: 12 months)
- `cod_date`: date (derived or explicit)

### 2.2 CAPEX payment schedules (per item)
- `payment_schedule: tuple[float, ...]` — fraction per construction month, must sum to 1.0
- Default: equal spread `(1/N,) * N` where N = construction_months
- User-editable per item in Workbook V2 UI
- Validation: `sum(payment_schedule) == 1.0` within tolerance

Source patterns observed in Oborovo workbook:
  - Equal monthly spread: most EPC/production items
  - 100% at financial close (upfront): insurances, project rights, acquisition, contingencies
  - Completion/commissioning: commissioning item
  - Milestone: some grid/ops items

Parent category schedules = SUMPRODUCT(child amounts × child schedules) / parent amount.
Parent schedules are DERIVED, not independently editable.

### 2.3 Monthly construction uses (cash requirements)
```
monthly_uses[t] = SUM_items(capex_item.amount × payment_schedule[t])
cumulative_uses[t] = SUM(monthly_uses[0:t])
```

### 2.4 Funding draw waterfall
- Equity / SHL / Junior Debt → funded first according to source funding policy
- Senior Debt → drawn against remaining unfunded uses
- `cumulative_senior_debt_draw[t]` → feeds IDC and commitment fee computation

### 2.5 Interest/day-count convention
- Day-count: Actual/360 (source: Oborovo workbook formulas, reviewed 2026-07-22)
- Interest period fraction: `(EOP - BOP + 1) / 360` per construction month (inclusive both endpoints)
- First stub period: 29-Jun-2029 → 30-Jun-2029 → **2 days** under inclusive formula (30 − 29 + 1 = 2), day fraction = 2/360 ≈ 0.5556%
- Construction months: monthly periods thereafter

### 2.6 Senior Debt IDC
```
senior_idc[t] = cumulative_senior_draw[t] × (base_rate + margin) × day_fraction[t]
              × construction_active_flag[t]
```
Cumulative target (Oborovo calibration): ≈1,086.032 kEUR.

### 2.7 Senior Debt commitment fee
```
commitment_fee[t] = (total_facility - cumulative_draw[t])
                  × commitment_fee_rate
                  × day_fraction[t]
                  × construction_active_flag[t]
```
`commitment_fee_rate` = explicit input (not derived from margin)
Cumulative target (Oborovo calibration): ≈188.563 kEUR.

### 2.8 Structuring / arrangement fee
```
structuring_fee = structuring_fee_rate × facility_basis
```
Paid once at financial close (or as lender invoice). Capitalised.
`structuring_fee_rate` = explicit input.
Cumulative target (Oborovo calibration): ≈477.303 kEUR.

### 2.9 VAT construction timing
- `monthly_vat_payable[t]` = monthly_uses[t] × applicable_vat_rate (where VAT applies)
- `monthly_vat_collected[t]` = derived from revenue/income (typically 0 during construction)
- `vat_reimbursement_lag_months`: int (Oborovo: 6 months)
- `cumulative_vat_repayments[t]` = delayed repayment per lag assumption
- `vat_facility_requirement[t]` = cumulative_vat_payable - cumulative_collected - cumulative_repaid

Maximum VAT facility requirement (Oborovo): ≈4,878 kEUR.

### 2.10 VAT facility IDC
```
vat_facility_idc[t] = vat_facility_requirement[t]
                    × vat_facility_all_in_rate
                    × day_fraction[t]
```
Cumulative target (Oborovo calibration): ≈208.448 kEUR.

### 2.11 VAT facility commitment fee
```
vat_facility_commitment_fee[t] = (max_vat_facility - vat_facility_requirement[t])
                               × vat_commitment_fee_rate
                               × construction_active_flag[t]
                               × day_fraction[t]
```
Cumulative target (Oborovo calibration): ≈13.622 kEUR.

---

## 3. Fixed-point convergence requirement

**CRITICAL**: The construction financing model contains a circular dependency:

```
capitalized financing costs → Total Uses → debt draws → IDC/fees → capitalized financing costs
```

The workbook resolves this via a Macro convergence loop (fixed-point iteration).

Future generic engine MUST:
- Detect circularity
- Implement iteration-to-convergence
- Convergence criterion: `|IDC_new - IDC_prev| < tolerance` (suggest 0.01 kEUR)
- Typical convergence: 3–5 iterations
- No one-pass formula permitted when circularity exists

---

## 4. Output handoff contract

```python
@dataclass
class CapitalizedFinancingCosts:
    """Derived output from Construction/IDC runtime. Feeds BookDepreciableAssetBasis."""
    senior_debt_idc_keur: float           # 12y book life
    senior_commitment_fee_keur: float     # 12y book life
    structuring_fees_keur: float          # 12y book life
    vat_facility_idc_keur: float          # 20y book life
    vat_facility_commitment_fee_keur: float  # 20y book life
    other_capitalized_keur: float = 0.0
    source_provenance: str = ""           # audit trail

    @property
    def total_keur(self) -> float:
        return (self.senior_debt_idc_keur + self.senior_commitment_fee_keur
                + self.structuring_fees_keur + self.vat_facility_idc_keur
                + self.vat_facility_commitment_fee_keur + self.other_capitalized_keur)
```

This output replaces the current calibration fields in `CapexStructure`:
- `idc_keur` ← `senior_debt_idc_keur`
- `commitment_fees_keur` ← `senior_commitment_fee_keur`
- `bank_fees_keur` ← `structuring_fees_keur`
- `vat_costs_keur` ← `vat_facility_idc_keur + vat_facility_commitment_fee_keur`
- `vat_facility_idc_keur` ← `vat_facility_idc_keur`
- `vat_facility_commitment_fee_keur` ← `vat_facility_commitment_fee_keur`

---

## 5. Book depreciation handoff

`CapitalizedFinancingCosts` feeds `book_depreciable_capex_items()` through the same
per-component useful-life logic:

| Component | Book life |
|-----------|-----------|
| Senior IDC | 12y |
| Senior commitment fee | 12y |
| Structuring fee | 12y |
| VAT facility IDC | 20y |
| VAT facility commitment fee | 20y |

No changes required to `book_depreciable_capex_items()` or `canonical_wiring.py`.

---

## 6. Workbook V2 UI compatibility requirements

Future Workbook V2 UI MUST expose:

**CAPEX UI** (editable inputs):
- CAPEX item name, amount, asset class, payment schedule, depreciation life, depreciable flag

**Construction/Financing UI** (editable inputs):
- Construction duration, start date
- Debt facilities: facility amount, base rate, margin, commitment fee rate, structuring fee rate
- VAT facility assumptions: applicable VAT rate, reimbursement lag, facility cap
- Funding policy: equity/SHL/senior priority sequence

**Calculated outputs** (display-only audit lines):
- Monthly IDC, commitment fees, VAT facility requirement
- Cumulative senior debt draws, VAT facility draws
- Total capitalized financing costs per component
- Final Gross Fixed Assets

Derived outputs must NEVER be displayed as editable primary inputs in the standard UI.
They may be shown as read-only calibration overrides in an advanced/debug mode.

---

## 7. SHL construction interest (excluded from GFA)

SHL construction interest (~1,170 kEUR for Oborovo) is NOT capitalized into GFA.
It flows through P&L / retained earnings as interest expense during construction.

This distinction must be preserved in Stage B2.

Stage B2 should document the P&L treatment path for SHL IDC separately.

---

## 8. VAT concepts — must remain distinct

| Concept | Oborovo value | Treatment |
|---------|--------------|-----------|
| Construction VAT payable | ≈7,665 kEUR | Working capital flow; NOT in GFA |
| VAT Facility max requirement | ≈4,878 kEUR | Facility drawdown; derived |
| VAT Facility IDC | ≈208.448 kEUR | Capitalized financing cost; 20y book life |
| VAT Facility commitment fee | ≈13.622 kEUR | Capitalized financing cost; 20y book life |
| Depreciation "VAT Costs" | ≈222.070 kEUR | = IDC + commitment fee; GFA item |

---

## 9. Source-Provenance Distinctions (Oborovo vs Generic Engine)

The following table separates SOURCE WORKBOOK BEHAVIOR (Oborovo-specific) from
GENERIC CLEAN-ENGINE POLICY (what the generic engine should expose):

| Aspect | Oborovo Source Workbook | Generic Engine Policy |
|--------|------------------------|-----------------------|
| Construction duration | 12 months | Configurable input (`construction_months: int`) |
| Default payment schedule | Equal 8.33%/month (1/12) | `100% / N` per month, user-editable per item |
| Funding priority | Equity → SHL → Senior Debt | Configurable funding policy; source sequence documented separately |
| Commitment-fee rate | Derived via workbook-specific formula | Explicit economically-meaningful rate input; do not replicate workbook formula as universal rule |
| VAT reimbursement lag | 6 months (Oborovo assumption) | Configurable input (`vat_reimbursement_lag_months: int`) |
| Calibration targets | IDC 1,086.032; commitment 188.563; structuring 477.303; VAT IDC 208.448; VAT commitment 13.622 kEUR | Evidence only — generic engine reproduces via correct inputs, not hardcoded targets |
| First stub period | 29-Jun-2029 → 30-Jun-2029 (Oborovo-specific date) | Generic engine computes from `construction_start_date` |

Parent CAPEX payment schedules are always DERIVED (SUMPRODUCT of child amounts × child
schedules / parent amount) — never independently editable.

---

## 10. Checklist for Stage B2 implementation

- [ ] Monthly construction period grid (date-based, from `construction_start_date`)
- [ ] Per-item payment schedules with validation (sum = 100%)
- [ ] Monthly Uses aggregation
- [ ] Equity/SHL/senior funding draw waterfall
- [ ] Actual/360 day-fraction computation
- [ ] Senior IDC monthly calculation
- [ ] Commitment fee monthly calculation
- [ ] Structuring fee (once at close)
- [ ] Construction VAT timing model
- [ ] VAT reimbursement lag
- [ ] VAT facility requirement
- [ ] VAT facility IDC
- [ ] VAT facility commitment fee
- [ ] Fixed-point convergence loop
- [ ] `CapitalizedFinancingCosts` output type
- [ ] Integration with `CapexStructure.book_depreciable_capex_items()`
- [ ] Calibration tests against Oborovo source targets
- [ ] Remove calibration override fields from `CapexStructure` (or mark deprecated)
