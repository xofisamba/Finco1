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

### 2.5 Interest/day-count convention
- Day-count: Actual/360 (source: Oborovo workbook formulas, reviewed 2026-07-22)
- Interest period fraction: `(EOP - BOP + 1) / 360` per construction month (inclusive both endpoints)
- First stub period: 29-Jun-2029 → 30-Jun-2029 → **2 days** under inclusive formula (30 − 29 + 1 = 2), day fraction = 2/360 ≈ 0.5556%
- Construction months: monthly periods thereafter

---

## 3. Facility period state contract

For each financing facility, the generic engine MUST maintain a per-period state record.
Interest and commitment fee formulas must reference the explicitly defined balance basis —
not an implicit or ambiguous "cumulative draw".

```
FacilityPeriodState:
  opening_drawn_balance       # balance at start of period (= prior period closing)
  draws_during_period         # new drawdowns in this period
  repayments_during_period    # scheduled repayments (0 during construction)
  closing_drawn_balance       # = opening + draws - repayments
  opening_undrawn_commitment  # = total_facility - opening_drawn_balance
  closing_undrawn_commitment  # = total_facility - closing_drawn_balance
  applicable_interest_rate    # all-in rate for interest
  applicable_commitment_fee_rate
  day_fraction                # (EOP - BOP + 1) / 360
```

**Balance basis policy** (explicit per facility):

```
interest_balance_basis:
  OPENING    ← prior/opening drawn balance (source-proven for Senior Debt in Oborovo)
  AVERAGE    ← (opening + closing) / 2
  CLOSING    ← end-of-period drawn balance
  CUSTOM     ← facility-specific override

commitment_fee_balance_basis:
  OPENING_UNDRAWN    ← prior/opening undrawn (source-proven for Senior Debt in Oborovo)
  AVERAGE_UNDRAWN
  CLOSING_UNDRAWN
  CUSTOM
```

Oborovo source calibration uses **OPENING** for Senior Debt (see §4 and §5 below).
VAT Facility uses its own separately proven workbook timing (see §6 and §7 below).
Do NOT assume one universal balance convention across all facilities.

---

## 4. Senior Debt IDC — source-proven timing semantics

### 4.0 Senior commitment enforcement

The generic funding waterfall must treat `senior_commitment_keur` as a hard
facility capacity. It tracks cumulative Senior requirement period by period and
raises a typed funding-shortfall error when required Senior funding exceeds the
commitment beyond tolerance.

The engine must not cap Senior draws to hide a breach, must not create a forced
final draw to consume unused commitment, and must not use validation targets to
rebalance the facility. For Oborovo, the frozen closing Senior draw remains
approximately `42,852.266725757 kEUR`, below the configured commitment, preserving
the known source circular residual rather than forcing a final commitment draw.

### Source workbook formula (Oborovo, reviewed 2026-07-22)

```
H57 = ($C57%/100 + H$59) × G$48 × G$6 × H$5
```

Where:
- `G48` = prior-period / opening cumulative Senior Debt drawn balance (column G = prior period)
- `G6`  = interest-period day-fraction associated with that opening balance interval
- `H5`  = current-period construction-active flag
- `$C57%/100 + H$59` = all-in rate (base rate + margin)

### Source-proven formula semantics

```
Senior_IDC[t] = Opening_Drawn_Balance[t]
              × All_In_Rate[t]
              × Day_Fraction[t]
              × Construction_Active_Flag[t]
```

Where `Opening_Drawn_Balance[t]` = cumulative Senior Debt drawn at the **start** of period t
(= closing balance of period t−1).

**Important**: do NOT use end-of-period closing drawn balance as the interest basis.
The source formula uses the opening (prior-period) balance, not the current-period draw.

Calibration target (Oborovo): ≈1,086.032 kEUR cumulative.

---

## 5. Senior Debt commitment fee — source-proven timing semantics

### Source workbook formula (Oborovo, reviewed 2026-07-22)

```
H58 = $C58 × (Inputs!$D$195 - G48) × G$6 × H$5
```

Where:
- `$C58` = commitment fee rate
- `Inputs!$D$195` = total Senior Debt facility amount
- `G48` = prior-period / opening cumulative drawn balance
- `G6`  = day-fraction for that opening interval
- `H5`  = construction-active flag

### Source-proven formula semantics

```
Senior_Commitment_Fee[t] = Commitment_Fee_Rate
                         × Opening_Undrawn_Commitment[t]
                         × Day_Fraction[t]
                         × Construction_Active_Flag[t]
```

Where `Opening_Undrawn_Commitment[t]` = Total_Facility − Opening_Drawn_Balance[t].

**Important**: commitment fee basis is also the **opening/prior-period undrawn** commitment,
not the closing undrawn. This is consistent with the interest balance convention.

Calibration target (Oborovo): ≈188.563 kEUR cumulative.

### 5.1 IDC and commitment percentage/profile rows are derived outputs

Direct Oborovo workbook evidence shows the IDC and commitment-fee percentage rows use formulas such as:

```excel
=IF(SUM($D55;$D57)=0;0;SUM(I55;I57)/SUM($D55;$D57))
=IF(SUM($D56;$D58)=0;0;SUM(I56;I58)/SUM($D56;$D58))
```

These rows divide same-column period financing-cost values by total financing costs. They are audit/display outputs, not primary payment-schedule inputs. In funding-period terms, the engine must fund construction Uses in period `t`, calculate financing cost on the resulting funded balance for the source accrual interval, and capitalize that financing cost in funding period `t+1`.

### 5.2 Senior period-rate formula chain

Direct Oborovo workbook evidence shows:

```excel
All-in base rate[t] = $C59 + row60[t]
C59 = Inputs!$D$202 * Inputs!$D$230 + SUM(Inputs!$D$232:$D$234)/100
row60[t] = IF(Inputs!C$301>0; Inputs!C$301 * $C60; 0)
```

Generic implementation:

```text
hedged_component = base_rate * hedge_coverage + swap_margin + forward_swap_margin + cva
floating_weight = (1 - hedge_coverage) * (1 + external_curve_buffer)
row60[t] = euribor_1m_fixing[t] * floating_weight
senior_idc_rate[t] = hedged_component + row60[t] + senior_margin
```

For Oborovo, C59 is 2.60% from 3.00% base rate × 80% hedge coverage + 20 bps swap margin. The literal effective-rate vector is validation evidence only; runtime inputs are primitive rate assumptions plus the Euribor 1m fixing curve.

---

## 6. Structuring / arrangement fee

```
structuring_fee = structuring_fee_rate × facility_basis
```

Paid once at financial close (or as lender invoice). Capitalised.
`structuring_fee_rate` = explicit input.
Calibration target (Oborovo): ≈477.303 kEUR.

---

## 7. VAT facility — separately proven timing semantics

**VAT Facility formulas use their own source timing convention, distinct from Senior Debt.**
Do NOT apply the Senior Debt opening-balance convention to VAT Facility without separate
workbook evidence.

The VAT facility commitment is an explicit facility input. The VAT schedule uses
the actual period requirement as `vat_drawn_keur`, calculates `vat_undrawn_keur`
as `vat_facility_commitment_keur - vat_requirement_keur`, and raises a typed
funding-shortfall error if the peak requirement exceeds commitment beyond
tolerance. It must not use total VAT payable as the facility commitment.

For Oborovo, the maximum VAT requirement remains `4,877.989945 kEUR`, terminal
VAT requirement remains zero, VAT IDC remains approximately
`208.44761845456716 kEUR`, and VAT commitment fee remains approximately
`13.6219528108125 kEUR`.

### 7.1 VAT construction timing
- `monthly_vat_payable[t]` = monthly_uses[t] × applicable_vat_rate (where VAT applies)
- `monthly_vat_collected[t]` = derived from revenue/income (typically 0 during construction)
- `vat_reimbursement_lag_months`: int (Oborovo: 6 months)
- `cumulative_vat_repayments[t]` = delayed repayment per lag assumption
- `vat_facility_requirement[t]` = cumulative_vat_payable − cumulative_collected − cumulative_repaid

Maximum VAT facility requirement (Oborovo): ≈4,878 kEUR.

### 7.2 VAT facility IDC — source-proven timing semantics

```
Source: =$C68 × H67 × H$6
```

Conceptually:

```
VAT_Facility_IDC[t] = VAT_Facility_All_In_Rate
                    × Current_VAT_Facility_Requirement[t]
                    × Day_Fraction[t]
```

Note: the source formula references the **current-period** VAT facility requirement (`H67`),
not a prior/opening balance. This differs from the Senior Debt opening-balance convention.

Calibration target (Oborovo): ≈208.448 kEUR cumulative.

### 7.3 VAT facility commitment fee — source-proven timing semantics

```
Source: =($D$67 - H67) × $C69 × H$5 × H$6
```

Conceptually:

```
VAT_Facility_Commitment_Fee[t] = (Max_VAT_Facility − Current_VAT_Facility_Requirement[t])
                               × VAT_Commitment_Fee_Rate
                               × Construction_Active_Flag[t]
                               × Day_Fraction[t]
```

Calibration target (Oborovo): ≈13.622 kEUR cumulative.

---

## 8. Fixed-point convergence requirement

### 8.0 Timeline policy flags

`active_construction`, `capex_payment_eligible`, `senior_idc_active`, and
`vat_facility_active` are runtime-policy flags, not decorative public metadata.
CAPEX and VAT payable are only materialized for periods where construction is
active and CAPEX payment is eligible. Senior IDC and Senior commitment fee accrue
only while `senior_idc_active` is true. A positive VAT requirement during an
inactive VAT facility period is a funding shortfall.

**CRITICAL**: The construction financing model contains a circular dependency:

```
capitalized financing costs → Total Uses → debt draws → IDC/fees → capitalized financing costs
```

The workbook resolves this via a Macro convergence loop (fixed-point iteration). The source
convergence check (Macro!E10) evaluates a combined absolute residual across all circular
construction outputs — not only Senior IDC.

### 8.1 Source convergence check structure (Oborovo reference)

```
Macro!E10 = ABS(H11 - G11)   ← e.g. Sponsor Carbon Fund IDC (if applicable)
           + ABS(H12 - G12)   ← e.g. Sponsor Carbon Fund Commitment Fees (if applicable)
           + ABS(D18 - D17)   ← e.g. circular construction taxes / other circular amount
           + ABS(H13 - G13)   ← Senior Debt IDC
           + ABS(H14 - G14)   ← Senior Debt Commitment Fees
```

The specific row identities are Oborovo-workbook-specific. The architectural principle is:

**convergence must be checked across ALL circular construction outputs**, not only IDC.

### 8.2 Generic convergence contract

```
circular_outputs_vector[t] = [
  senior_idc,
  senior_commitment_fee,
  junior_or_other_facility_idc,        # if applicable
  other_commitment_fees,               # if applicable
  construction_taxes_if_circular,      # if applicable
  vat_facility_idc,                    # if changes in VAT facility feed back into Total Uses
  vat_facility_commitment_fee,         # if applicable
  other_capitalized_financing_costs,   # any other circularly-derived construction output
]

residual[iteration] = sum(abs(circular_outputs_vector[n] - circular_outputs_vector[n-1]))

Converged when: residual[iteration] <= tolerance
                AND (optionally) max(abs(component_delta)) <= component_tolerance

Recommended tolerance: 0.01 kEUR on combined residual.
```

The set of circular outputs must include **every financing/tax/construction amount that feeds
back into Total Uses**. The engine must not hard-code only Senior IDC.

### 8.3 Iteration count

The engine must expose:
- `max_iterations`: int (configurable; suggest default 50)
- `tolerance`: float (configurable; suggest default 0.01 kEUR)
- `converged: bool`
- `iteration_count: int`
- `final_residual: float`
- `component_residuals: dict[str, float]`

No specific "expected" iteration count is contractually required. Workbook convergence behavior
is source-specific and must not be encoded as financial logic in the generic engine.

### 8.4 Non-convergence fail-fast behavior

If `iteration_count >= max_iterations` and `residual > tolerance`:

```
raise ConstructionFinancingNotConverged(
    iteration_count=iteration_count,
    final_residual=final_residual,
    component_residuals=component_residuals,
    tolerance=tolerance,
)
```

**MUST NOT**:
- silently use last-iteration values
- substitute calibration outputs
- force residual to zero
- use approved_delta or any hardcoded plug

Audit output on failure must include `iteration_count`, `final_residual`, `component_residuals`,
`converged=False`.

---

## 9. Output handoff contract

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

## 10. Book depreciation handoff

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

The construction result does not hard-code these lives as Oborovo identity logic:
the Senior-financing and VAT-financing useful lives are explicit accounting
adapter metadata inputs on the Stage B2 configuration. Oborovo provides 12-year
Senior financing and 20-year VAT financing lives to preserve confirmed output
behavior.

---

## 11. Workbook V2 UI compatibility requirements

Future Workbook V2 UI MUST expose:

**CAPEX UI** (editable inputs):
- CAPEX item name, amount, asset class, payment schedule, depreciation life, depreciable flag

**Construction/Financing UI** (editable inputs):
- Construction duration, start date
- Debt facilities: facility amount, base rate, margin, commitment fee rate, structuring fee rate
- Balance basis policy per facility (OPENING / AVERAGE / CLOSING)
- VAT facility assumptions: applicable VAT rate, reimbursement lag, facility cap
- Funding policy: equity/SHL/senior priority sequence

**Calculated outputs** (display-only audit lines):
- Monthly IDC, commitment fees, VAT facility requirement
- Per-period facility state: opening balance, draws, closing balance, undrawn commitment
- Cumulative senior debt draws, VAT facility draws
- Total capitalized financing costs per component
- Convergence audit: iteration count, final residual, converged flag
- Final Gross Fixed Assets

Derived outputs must NEVER be displayed as editable primary inputs in the standard UI.
They may be shown as read-only calibration overrides in an advanced/debug mode.

---

## 12. SHL construction interest (excluded from GFA)

SHL construction interest (~1,170 kEUR for Oborovo) is NOT capitalized into GFA.
It flows through P&L / retained earnings as interest expense during construction.

This distinction must be preserved in Stage B2.

Stage B2 should document the P&L treatment path for SHL IDC separately.

---

## 13. VAT concepts — must remain distinct

| Concept | Oborovo value | Treatment |
|---------|--------------|-----------|
| Construction VAT payable | ≈7,665 kEUR | Working capital flow; NOT in GFA |
| VAT Facility max requirement | ≈4,878 kEUR | Facility drawdown; derived |
| VAT Facility IDC | ≈208.448 kEUR | Capitalized financing cost; 20y book life |
| VAT Facility commitment fee | ≈13.622 kEUR | Capitalized financing cost; 20y book life |
| Depreciation "VAT Costs" | ≈222.070 kEUR | = IDC + commitment fee; GFA item |

---

## 14. Source-Provenance Distinctions (Oborovo vs Generic Engine)

The following table separates SOURCE WORKBOOK BEHAVIOR (Oborovo-specific) from
GENERIC CLEAN-ENGINE POLICY (what the generic engine should expose):

| Aspect | Oborovo Source Workbook | Generic Engine Policy |
|--------|------------------------|-----------------------|
| Construction duration | 12 months | Configurable input (`construction_months: int`) |
| Default payment schedule | Equal 8.33%/month (1/12) | `100% / N` per month, user-editable per item |
| Funding priority | Equity → SHL → Senior Debt | Configurable funding policy; source sequence documented separately |
| Senior IDC balance basis | Opening/prior-period drawn balance (workbook-proven: G48 = prior column) | Configurable `interest_balance_basis` per facility |
| Senior commitment fee basis | Opening/prior-period undrawn (workbook-proven: Total_Facility − G48) | Configurable `commitment_fee_balance_basis` per facility |
| Commitment-fee rate | Derived via workbook-specific formula | Explicit economically-meaningful rate input; do not replicate workbook formula as universal rule |
| VAT facility IDC timing | Current-period requirement (H67) — differs from Senior Debt opening-balance | Facility-specific; do not conflate with Senior Debt convention |
| VAT reimbursement lag | 6 months (Oborovo assumption) | Configurable input (`vat_reimbursement_lag_months: int`) |
| Calibration targets | IDC 1,086.032; commitment 188.563; structuring 477.303; VAT IDC 208.448; VAT commitment 13.622 kEUR | Evidence only — generic engine reproduces via correct inputs, not hardcoded targets |
| First stub period | 29-Jun-2029 → 30-Jun-2029 (Oborovo-specific date) | Generic engine computes from `construction_start_date` |

Parent CAPEX payment schedules are always DERIVED (SUMPRODUCT of child amounts × child
schedules / parent amount) — never independently editable.

---

## 15. Checklist for Stage B2 implementation

- [ ] Monthly construction period grid (date-based, from `construction_start_date`)
- [ ] Per-item payment schedules with validation (sum = 100%)
- [ ] Monthly Uses aggregation
- [ ] Equity/SHL/senior funding draw waterfall
- [ ] Actual/360 day-fraction computation
- [ ] Per-period `FacilityPeriodState` for each facility (opening/draws/closing/undrawn)
- [ ] Senior IDC: opening-balance × all-in rate × day_fraction × active_flag
- [ ] Senior commitment fee: opening-undrawn × commitment_fee_rate × day_fraction × active_flag
- [ ] Structuring fee (once at close)
- [ ] Construction VAT timing model
- [ ] VAT reimbursement lag
- [ ] VAT facility requirement
- [ ] VAT facility IDC: current-period requirement × rate × day_fraction
- [ ] VAT facility commitment fee: (max_facility − current_requirement) × rate × active_flag × day_fraction
- [ ] Fixed-point convergence loop over all circular outputs vector
- [ ] Convergence audit output (iteration_count, final_residual, component_residuals, converged)
- [ ] `ConstructionFinancingNotConverged` exception on non-convergence (fail-fast)
- [ ] `CapitalizedFinancingCosts` output type
- [ ] Integration with `CapexStructure.book_depreciable_capex_items()`
- [ ] Calibration tests against Oborovo source targets
- [ ] Remove calibration override fields from `CapexStructure` (or mark deprecated)
