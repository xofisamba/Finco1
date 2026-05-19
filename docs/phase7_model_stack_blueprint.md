# Phase 7 — Canonical Model-Stack Blueprint

**Branch:** `phase7-model-stack-blueprint`
**Base:** main (post-PR #95)
**Type:** Docs/report only. No production code changes. No runtime behavior changes. No flag opt-ins. No R99/R102 promotion.

---

## A. Executive Summary

FincoGPT has spent ~30 PRs in Phase 6 + early Phase 7 calibrating TUHO Excel parity across Revenue, OPEX, Senior Debt, Depreciation, Tax (R35/R67), and SHL. The strategic conclusion from the model-stack comparison workbook + sign concern investigations is:

**Stop chasing Excel parity. Build the canonical model-stack.**

Why now:
- **Revenue and OPEX are reusable.** Total parity verified within ±0.01 kEUR. Runtime flags either default-on (Revenue) or default-off-ready (OPEX).
- **Senior Debt is mostly calibrated** but uses an **Excel-specific sizing CFADS shortcut** that is not yet documented as a canonical model assumption (Macro R50 hardcoded).
- **Tax is governed but not closed.** R67 residual ±5,271 kEUR documented as structural variance; gates fail; R99 blocked.
- **SHL is the largest remaining canonical gap.** Cash-sweep post-senior is undefined as a module. PIK timing, gross accrued source ownership, and post-senior sweep all sit in legacy waterfall code without canonical module boundaries.
- **R99/R102 remain BLOCKED.** Distribution account is audit-only.

Excel is a validation benchmark. It is not product architecture. Two examples now empirically verified:
1. **Loss carryforward** uses 5-period rolling (= 2.5 years semiannual), which contradicts Croatian Zakon o porezu na dobit Čl. 17 (5 years = 10 semiannual periods). Croatia 10-period vintage is canonical.
2. **Senior debt sizing** uses Macro!R50 = hardcoded sizing CFADS values, manually adjusted to maintain Minimum Senior DSCR ≈ 1.45x. The actual CFADS (CF!R69 via Macro!R49) is different. Python should not silently inherit this; it must be a canonical sizing-policy parameter.

The blueprint below codifies what is reusable, what needs canonical refactoring, what stays as legacy baseline, and the recommended 8-branch Phase 7 roadmap.

---

## B. Module Status Table

| Module | Status | Current Evidence | Reusable Code | Known Gaps | Next Action | Priority |
|---|---|---|---|---|---|---|
| **Revenue** | ✅ CLOSED | Δ=0.0 horizon, splits added PR #90 | `domain/revenue/*` | Oborovo merchant curve refinements (future) | Formalize as canonical, no immediate work | P3 |
| **OPEX** | ✅ RUNTIME-READY | offline = 84,675; flag-on TUHO matches; inflation decomposition complete | `domain/opex/*` | UI inputs, export integration | Optional UI/export polish; not blocking | P3 |
| **EBITDA / CFADS** | ✅ RUNTIME-READY | Δ=-734 kEUR (= OPEX flag-off only) | derived from Rev + OPEX | None when OPEX engine enabled | None needed | P3 |
| **Construction CAPEX / IDC / Funding** | ⚠ PARTIAL | offline engines built; runtime not wired to canonical module | `domain/construction/*` | Runtime adapter; canonical module boundary | Stage 2 docs-only design | P2 |
| **Senior Debt** | ⚠ PARTIAL | Δ=-355 kEUR (minor) on senior int/DS; sizing source NOT documented | `domain/senior_sculpting.py`, `domain/senior_rate_schedule.py` | **Macro R50 sizing CFADS not source-mapped**; DSCR PPA/merchant switch not canonical | **SOURCE MAP — PRIORITY** | **P1** |
| **Depreciation** | ⚠ PARTIAL | offline engine exists; canonical decisions made; tax basis matches | `domain/depreciation_offline/*` | Runtime canonical integration; book basis field | Docs-only canonical module design | P2 |
| **Tax** | ⚠ PARTIAL | R35/R41/R43/R67 formula chain documented; loss window canonical; residual +5,271 kEUR | `domain/tax/loss_carryforward.py`, `domain/financial_statements/tax_bridge.py` | Useful-life CIT impact sign concern unresolved; SHL gross-accrued source candidate-only | Accept residual + governance; defer further calibration | P3 |
| **SHL / Junior Debt** | 🚫 BLOCKED (module) | SHL gross-accrued = -3,737 kEUR delta; PIK timing diff; closing balance Δ≈-82k cumulative | `domain/shl_fcf_waterfall.py` (legacy, fixture-bound) | **No canonical SHL module exists**; post-senior cash sweep undefined | **MODULE DESIGN — PRIORITY** | **P1** |
| **Distribution / R99/R102** | 🚫 BLOCKED | audit-only; gates fail | `domain/distribution_account/*` | All upstream modules first | Hold until P1 SHL + Senior Debt done | P4 |
| **Sponsor economics** | ✅ CLOSED | 4,616 LOC IRR/XIRR/multi-investor stable | `domain/sponsor/*` | None | No action | P3 |

---

## C. Canonical Model-Stack Architecture

```
                                ┌──────────────────────────┐
                                │  Inputs / Assumptions    │
                                │  (project_factories.py)  │
                                └────────────┬─────────────┘
                                             │
                ┌────────────────────────────┴────────────────────────────┐
                ▼                                                          ▼
   ┌─────────────────────────┐                          ┌─────────────────────────┐
   │  ConstructionEngine     │                          │   RevenueEngine         │
   │  CAPEX schedule,        │                          │   PPA, merchant, CO2,   │
   │  funding, IDC           │                          │   balancing             │
   └────────────┬────────────┘                          └────────────┬────────────┘
                │                                                     │
                │                                                     ▼
                │                                       ┌─────────────────────────┐
                │                                       │   OpexEngine            │
                │                                       │   B.01-B.13 line items, │
                │                                       │   inflation, schedules  │
                │                                       └────────────┬────────────┘
                │                                                     │
                │                                                     ▼
                │                                       ┌─────────────────────────┐
                │◄──── feeds depreciation base          │  EBITDA / CFADS         │
                ▼                                       │  = Rev − OPEX           │
   ┌─────────────────────────┐                          └────────────┬────────────┘
   │  DepreciationEngine     │                                       │
   │  book + tax basis,      │                                       ▼
   │  per-category life      │                          ┌─────────────────────────┐
   └────────────┬────────────┘                          │   SeniorDebtEngine      │
                │                                       │   sizing_cfads_keur,    │
                │                                       │   target_dscr_by_period │
                │                                       │   interest, principal   │
                │                                       └────────────┬────────────┘
                │                                                     │
                ▼                                                     ▼
   ┌─────────────────────────┐                          ┌─────────────────────────┐
   │  TaxEngine              │◄─────  EBT inputs  ──────│  Post-Senior Cash       │
   │  R35/R41/R43/R67,       │                          │  = CFADS − Senior DS    │
   │  loss carryforward,     │                          │  − cash_reserve (opt)   │
   │  ATAD/R34               │                          └────────────┬────────────┘
   └────────────┬────────────┘                                       │
                │                                                     ▼
                │                                       ┌─────────────────────────┐
                │                                       │   ShlEngine             │
                │                                       │   gross accrued, PIK,   │
                │                                       │   cash int, principal,  │
                │◄────── cash tax outflow ──────────────│   cash sweep            │
                ▼                                       └────────────┬────────────┘
   ┌─────────────────────────┐                                       │
   │  DistributionAccount    │◄──── after SHL fully served ──────────┘
   │  R99 / R102 / R119      │
   │  net dividends          │
   └────────────┬────────────┘
                │
                ▼
   ┌─────────────────────────┐
   │  SponsorEngine          │
   │  IRR, XIRR, MOIC        │
   └─────────────────────────┘
```

### Per-Module Definition

| Module | Inputs | Outputs | Period | Audit Table | Excel Comparison | Runtime SoT |
|---|---|---|---|---|---|---|
| RevenueEngine | PPA price, merchant curve, CO2 price, capacity | electricity_revenue, co2_revenue, balancing_cost | semiannual | Revenue audit fields | CF!R20, sub-rows | ✅ runtime |
| OpexEngine | B-code template, capacity, inflation | per-item kEUR | semiannual | OPEX line audit | CF!R38 / OpEx!R105 | runtime (flag) |
| ConstructionEngine | CAPEX categories, funding ratio, IDC rate | capex by period, debt drawdowns, IDC | construction | Construction audit | CapEx!, IDC! | partial (legacy) |
| DepreciationEngine | CAPEX by category, useful_life_years per category | book_dep, tax_dep | annual+semiannual | dep audit | Dep!R30 / R31 | tax basis only (canonical refactor needed) |
| SeniorDebtEngine | **sizing_cfads** (NOT actual CFADS), target_dscr_by_period, interest rate, day-count | interest, principal, opening/closing balance | semiannual | senior audit | DS!R47-R54 | runtime |
| TaxEngine | EBT inputs, ATAD config, loss config, useful_life | R35, R41, R43, R67 audits | semiannual | R34/R36/R37/R41/R43 | P&L!R32-R44, CF!R67 | runtime (flag) |
| ShlEngine | starting balance, rate, day-count, **post-senior cash, minimum_cash_reserve** | gross_accrued, PIK, cash_int, principal, closing balance | semiannual | SHL audit | DS!R120-R140 | **NO RUNTIME YET (blocked)** |
| DistributionAccount | post-SHL cash, dividend policy | R98/R99/R102/R119 | semiannual | distribution audit | CF!R98-R119 | **AUDIT-ONLY (blocked)** |
| SponsorEngine | equity cashflows, dividend cashflows | IRR, XIRR, MOIC | full horizon | sponsor audit | Eq!, sponsor outputs | runtime |

---

## D. Senior Debt / DSCR Sizing Subsection (MANDATORY)

### Empirical findings from TUHO Excel (verified empirically)

**Hypothesis confirmed via direct cell inspection of `20260330_TUHO_BP.xlsm`:**

| Cell | Formula | Total kEUR | Meaning |
|---|---|---:|---|
| **CF!R69** | derived (Rev − OPEX − cash CIT) | **300,927** | Actual FCF for banks (true CFADS) |
| **Macro!R49** | `=CF!H69` (direct link) | **300,927** | Actual CFADS feed into Macro |
| **Macro!R50** | **HARDCODED NUMERIC VALUES** (e.g. `2539.6336729104755`) | **204,669** | Sizing CFADS — manually adjusted |
| **DS!R20** | `=Macro!R50 / DS!R19` | 66,181 | CF available for senior debt repayment |
| **DS!R19** | DSCR target by period | 1.20 → 1.41 (period 26+) | Target DSCR varies by revenue regime |
| **Inputs!D204** | 1.20 (base DSCR target) | — | Default DSCR target |

**Critical observation:** Macro!R49 = 300,927 kEUR (linked) vs Macro!R50 = 204,669 kEUR (hardcoded) = **96,258 kEUR buffer (32% below actual)**. This buffer is intentionally inserted to maintain Minimum Senior DSCR ≈ 1.45x across the senior loan life.

### DSCR target policy (empirically observed)

DS!R19 shows DSCR transitioning:
- op_idx 0-23 (PPA/contracted period): DSCR = **1.20**
- op_idx 24+ (merchant transition): DSCR = **1.40-1.41**

This matches the prior PR #B1 dual-DSCR finding. The switch is at op_idx 24 = first profit period = PPA→merchant boundary.

### Canonical Senior Debt Sizing Formula

```python
@dataclass(frozen=True)
class SeniorDebtSizingPolicy:
    """Sizing CFADS is NOT the actual CFADS — it is a project assumption."""
    sizing_cfads_keur_by_period: tuple[float, ...]  # SoT: project input, not CF!R69 link
    target_dscr_by_period: tuple[float, ...]        # 1.20 PPA / 1.40 merchant per period
    interest_rate_schedule: tuple[float, ...]
    day_count_fraction: tuple[float, ...]
    opening_balance_keur: float
    maturity_periods: int

# Debt service capacity (per period):
target_debt_service[t] = sizing_cfads[t] / target_dscr[t]

# Interest is opening × rate × fraction:
interest[t] = opening_balance[t] × rate[t] × day_count[t]

# Principal is residual capacity (capped at opening balance + maturity rules):
principal[t] = max(0, target_debt_service[t] - interest[t])
principal[t] = min(principal[t], opening_balance[t])

# Closing balance:
closing[t] = opening[t] - principal[t]
```

### Why this matters for Python

If Python computes senior repayment from `actual CFADS` (CF!R69 / Macro!R49 = 300,927), it will repay debt faster than Excel sized for, producing different senior balances, different cash sweeps, different SHL inputs, different distributions. **The -355 kEUR Δ on senior interest in the model-stack comparison may be downstream of this sizing source mismatch.**

### Required source-verification branch

**`phase7-senior-debt-dscr-source-map`** (docs/report only):
- Read TUHO Macro!R50 cell-by-cell, document hardcoded values
- Verify Oborovo has same Macro!R50 pattern
- Document Inputs!D204 (DSCR base) + period-by-period DSCR override mechanism
- Map Python current senior sizing source: does it use CFADS or sizing_cfads?
- Recommend canonical `SeniorDebtSizingPolicy` with explicit `sizing_cfads_keur_by_period` input
- NO runtime changes; NO flag changes; pure docs

---

## E. SHL / Junior Debt Cash Sweep Subsection (MANDATORY)

### Current empirical state

| Excel observation | Verified |
|---|---|
| CF!R104 SHL Debt Service total = 82,486 kEUR over horizon | ✓ |
| SHL gross accrued = 49,782 (R122 sum) | ✓ |
| SHL PIK = 11,027 (R125 sum) | ✓ |
| SHL cash interest paid = 38,755 (R122 - R125) | ✓ |
| SHL principal = 43,731 (R124 sum) | ✓ |
| Post-senior cash → all to SHL until SHL fully served | empirically true in TUHO (no minimum cash reserve evident) |
| Distribution starts only after SHL service | ✓ CF!R119 is residual |

### Canonical SHL Cash Sweep Module

```python
@dataclass(frozen=True)
class ShlEngineInputs:
    opening_balance_keur: float
    interest_rate: float
    day_count_fraction: tuple[float, ...]
    pik_eligible: bool
    cash_sweep_after_senior: bool = True
    minimum_cash_reserve_keur: float = 0.0   # see Section F

@dataclass(frozen=True)
class ShlPeriodResult:
    opening_balance: float
    drawdown: float
    gross_accrued_interest: float    # opening × rate × frac (ALWAYS — independent of cash)
    cash_interest_paid: float
    pik_capitalized: float           # = gross_accrued - cash_interest_paid
    principal_repaid: float
    closing_balance: float
    cash_consumed: float             # = cash_interest_paid + principal_repaid

# Waterfall order (canonical):
# 1. Compute actual_cfads (CFADS = Rev − OPEX − cash CIT)
# 2. Compute senior_ds_actual (from SeniorDebtEngine)
# 3. cash_after_senior = actual_cfads − senior_ds_actual
# 4. (optional) cash_reserve_retained = min(minimum_cash_reserve, cash_after_senior)
# 5. cash_available_for_shl = cash_after_senior − cash_reserve_retained
# 6. gross_accrued = opening × rate × frac
# 7. cash_interest_paid = min(gross_accrued, cash_available_for_shl)
# 8. pik_capitalized = gross_accrued − cash_interest_paid
# 9. cash_remaining = cash_available_for_shl − cash_interest_paid
# 10. principal_repaid = min(opening_balance + pik_capitalized, cash_remaining)
# 11. closing_balance = opening_balance + pik_capitalized − principal_repaid
# 12. cash_for_distribution = cash_remaining − principal_repaid
```

### Why post-senior 100%-to-SHL is OK as default

TUHO Excel does not show a minimum cash reserve mechanism. Macro and CF both treat post-senior cash as available for SHL. This is industry-standard for project finance: project SPV does not retain working capital because OPEX is small and timed. But the **optional reserve must be a first-class input** for projects that do require working capital (e.g. larger O&M variability, seasonal CO2 income).

### Required source-verification branch

**`phase7-shl-cash-sweep-source-map`** (docs/report only):
- Document SHL waterfall order in TUHO Excel cell-by-cell
- Verify Oborovo SHL has same waterfall order
- Document PIK trigger condition (Excel R138 formula already extracted)
- Recommend canonical `ShlEngine` module signature
- Recommend `phase7-shl-module-design` as immediate follow-up

---

## F. Minimum Cash Reserve / Working Capital Subsection (MANDATORY — future input)

### Design intent

```python
# Future ProjectInfo additions (NOT to be implemented in this branch):
maintain_minimum_cash_reserve: bool = False
minimum_cash_reserve_keur: float = 50.0
```

### Behavior

```python
if maintain_minimum_cash_reserve:
    cash_available_for_shl_or_distribution = max(
        0,
        available_cash_after_senior_debt_service - minimum_cash_reserve_keur
    )
else:
    cash_available_for_shl_or_distribution = max(
        0,
        available_cash_after_senior_debt_service
    )
```

### Default

- `maintain_minimum_cash_reserve = False`
- `minimum_cash_reserve_keur = 50.0` (placeholder if enabled)

### For TUHO

**Default OFF.** TUHO Excel does not maintain minimum cash reserve; flag default-off preserves bit-identical baseline.

### Not now

This is future-design only. **NO implementation in this branch.** It is documented here so that the SHL module is designed with the right hooks from the start, avoiding refactor later.

---

## G. Reuse / Refactor / Replace Table

| Code | Classification | Rationale |
|---|---|---|
| `domain/revenue/*` | **Reuse as-is** | Production-quality; Revenue closed |
| `domain/opex/*` | **Reuse behind flag** | Calibrated; runtime flag default-off ready |
| `domain/construction/*` | **Refactor into canonical** | Strong foundation; needs canonical module boundary |
| `domain/depreciation_offline/*` | **Refactor into canonical** | Engine works; needs runtime integration via canonical module |
| `domain/tax/loss_carryforward.py` | **Refactor into canonical** | Croatia vintage decided; needs runtime flag wiring (already partly done) |
| `domain/financial_statements/tax_bridge.py` | **Refactor into canonical** | Architecture sound; consumes from upstream |
| `domain/senior_sculpting.py` | **Reuse as current baseline** | Calibrated single-facility; multi-tranche future |
| `domain/senior_rate_schedule.py` | **Reuse as current baseline** | Calibrated |
| `domain/shl_fcf_waterfall.py` | **Keep as legacy, plan replacement** | Phase 7L fixture-bound; canonical ShlEngine replaces |
| `domain/distribution_account/*` | **Refactor when R99 promoted** | Audit-only; future canonical module |
| `domain/sponsor/*` | **Reuse as-is** | Stable 4,616 LOC; don't disrupt |
| `app/waterfall_core.py` | **Keep as legacy baseline** | 1,251 LOC monolith; never expand; replace incrementally |
| `app/waterfall_runner.py` | **Keep as legacy baseline** | Operational runner; tests rely on it |
| `app/project_factories.py` | **Reuse as-is** | Factory pattern correct; flag pattern stable |
| Excel extraction/report scripts | **Reuse as-is** | Diagnostic infrastructure valuable |
| Tests + diagnostic fixtures | **Reuse as-is** | 168+ regression net |

---

## H. Runtime Source vs Audit-Only Matrix

| Field / Source | Runtime SoT | Audit-Only | Diagnostic | Blocked | Sizing |
|---|:-:|:-:|:-:|:-:|:-:|
| `revenue_keur`, splits | ✅ | | | | |
| OPEX line-item engine | ✅ (flag) | | | | |
| `actual_cfads` / `r69_fcf_banks_keur` | ✅ | | | | |
| **`debt_sizing_cfads` (Macro!R50 equiv.)** | | | | | ✅ NEW canonical input |
| `target_dscr_by_period` | | | | | ✅ NEW canonical input |
| `debt_service_capacity_keur` | ✅ | | | | |
| `senior_interest_keur`, `senior_principal_keur` | ✅ | | | | |
| `depreciation_keur` (tax basis) | ✅ | | | | |
| `book_depreciation_keur` | | ✅ (planned) | | | |
| Tax audit fields (R35/R37/R41/R43) | ✅ (flag) | | | | |
| `corporate_tax_cash_keur` (R67) | ✅ (flag) | | | | |
| **`shl_gross_accrued_interest_keur`** | | ✅ | | | |
| `shl_pik_keur` | | ✅ | | | |
| **`cash_available_for_shl_keur`** (post-senior) | | | | 🚫 | |
| **`minimum_cash_reserve_keur`** | | | | 🚫 (future) | |
| `r98_distribution_account_keur` | | ✅ | | 🚫 | |
| `r99_fcf_for_distribution_keur` | | ✅ | | 🚫 | |
| `r102_fcf_for_shl_keur` | | ✅ | | 🚫 | |
| `distribution_keur` (R119) | ✅ | | | | |
| Sponsor IRR/XIRR | ✅ | | | | |

---

## I. R99/R102 Gate Policy

**Status: BLOCKED.** No runtime promotion until all gates pass.

### Required gates

| # | Gate | Status |
|---|---|---|
| 1 | R35 formula chain documented | ✅ |
| 2 | R43/R67 timing documented | ✅ |
| 3 | Loss-window canonical decision | ✅ |
| 4 | Useful-life canonical decision | ✅ |
| 5 | Useful-life CIT impact sign reconciled | ⚠ pending |
| 6 | Model-stack comparison workbook | ✅ |
| 7 | Phase 7 blueprint published | ✅ (this doc) |
| 8 | **Senior Debt sizing source map** | ⚠ pending (P1) |
| 9 | **SHL canonical module designed** | ⚠ pending (P1) |
| 10 | **SHL cash sweep source ownership** | ⚠ pending (P1) |
| 11 | **Minimum cash reserve policy defined** | ✅ (this doc) |
| 12 | Tax residual accepted or closed | ⚠ partial |
| 13 | R99/R102 source ownership defined | ⚠ pending |
| 14 | Distribution account source ownership | ⚠ pending |
| 15 | External reviewer sign-off | ⚠ pending |
| 16 | Default-off flag for any R99 promotion | ⚠ pending |

**6/16 done, 10 pending.** Design-only branches allowed; runtime implementation not yet.

---

## J. Phase 7 Roadmap (8 Branches)

| # | Branch | Type | Goal | Effort |
|---|---|---|---|---|
| **1** | **`phase7-senior-debt-dscr-source-map`** | docs/report | Map Macro!R49/R50, DSCR PPA/merchant switch, Python current sizing source. Diagnostic. | 3-4d |
| **2** | **`phase7-shl-cash-sweep-source-map`** | docs/report | Map SHL waterfall in Excel, confirm post-senior 100%-to-SHL logic, identify minimum reserve absence in TUHO | 2-3d |
| **3** | `phase7-shl-canonical-module-design` | docs/report | Design `domain/shl/` module: ShlEngineInputs, ShlPeriodResult, waterfall order. NO impl. | 3-4d |
| **4** | `phase7-senior-debt-canonical-module-design` | docs/report | Design `domain/senior_debt/` module: `SeniorDebtSizingPolicy`, dual-DSCR canonical | 3-4d |
| **5** | `phase7-depreciation-canonical-module-design` | docs/report | Design `domain/depreciation/`: per-category useful_life. Migration from `depreciation_offline/` | 3-4d |
| **6** | `phase7-shl-engine-implementation` | runtime_flag | Implement ShlEngine behind `use_shl_canonical_engine: bool = False` | 5-7d |
| **7** | `phase7-senior-debt-sizing-flag` | runtime_flag | Implement explicit sizing_cfads input behind flag | 5-7d |
| **8** | `phase7-depreciation-runtime-integration` | runtime_flag | Runtime canonical dep engine behind flag | 5-7d |

After 1-8: revisit R99 gates. If 10+ done → R99 design.

---

## K. Stop Rules / No-More-Parity-Chasing Rules

**Stop chasing Excel parity if any of the following:**

1. **Excel contradicts canonical legal/accounting model.** Example: 5-period loss carryforward bug. Canonical is 10-period (Croatian Article 17).
2. **Residual is documented and accepted.** Example: +5,271 kEUR R67 residual gated, accepted as structural variance.
3. **Source ownership is blocked.** R99/R102 distribution account; SHL canonical module not yet designed.
4. **Difference belongs to legacy Excel convention.** Day-count split, contingency methodology.
5. **Module is not runtime source yet.** R99/R102 audit-only.
6. **Excel uses hardcoded sizing values.** Macro!R50 sizing CFADS — treat as canonical assumption parameter, not formula to reverse-engineer.
7. **Cost-benefit per PR < 1 kEUR R67 reduction per developer-day.** Diminishing returns past Phase 6.

---

## L. Oborovo Strategy

**Current support:**
- Revenue: TUHO and Oborovo both have CO2/balancing assumptions
- OPEX: only TUHO template; Oborovo guarded behind ValueError when flag-on
- Senior Debt: works for both (dual-DSCR PR B1)
- Depreciation: offline engine works for both
- Tax: tax_bridge flag works for TUHO; Oborovo guarded

**Roadmap actions:**
- Stage 5 of OPEX path: Oborovo template (`build_oborovo_opex_template()`)
- Senior Debt: Oborovo uses same dual-DSCR pattern (R59 active, thin-cap differs)
- SHL canonical module: must support both projects from day 1 (no TUHO-only architecture)
- Distribution: Oborovo distribution patterns differ; future design

**Anti-pattern to avoid:** TUHO-specific hardcoded values inside canonical modules. Use templates and config objects.

---

## M. Risks and Mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| Overfitting TUHO Excel | High | This blueprint — Excel is benchmark, not architecture |
| Moving too early to implementation | Medium | All Phase 7 stages 1-5 are docs/report only |
| Legacy waterfall expansion | High | `app/waterfall_core.py` frozen; canonical modules replace incrementally |
| R99 promotion too early | High | 10/16 gates pending; explicit gate policy |
| Macro!R50 hardcoded sizing treated as formula | Medium | Stage 1 source-map clarifies; canonical SizingPolicy makes it explicit input |
| Sweeping all post-senior to SHL without minimum reserve | Medium | minimum_cash_reserve future input documented in this blueprint |
| Sign concerns from PR #88 unresolved | Medium | Documented; gated; not blocking blueprint |
| Cross-project Oborovo regression | Low | Guarded ValueError; tests assert |
| Sponsor module disruption | Low | `domain/sponsor/*` reuse as-is |

---

## N. Definition of Done by Module

### Revenue
- ✅ Total parity Δ ≤ ±100 kEUR horizon
- ✅ Splits visible: electricity, CO2, balancing
- ✅ TUHO and Oborovo assumptions documented
- ✅ Tests pass

### OPEX
- ✅ B-code source map
- ✅ Semiannual projection validated vs Excel
- ✅ Runtime flag default-off
- ✅ Inflation decomposition
- ✅ Oborovo template (Stage 5 pending)

### Construction
- ⚠ CAPEX/funding/IDC engines built
- ⚠ Canonical module boundary missing
- ⚠ Runtime integration via legacy waterfall

### Senior Debt
- ⚠ Actual CFADS vs sizing CFADS not separated
- ⚠ Macro!R49/R50 + CF!R69 not source-mapped
- ⚠ PPA/merchant DSCR targets not canonical
- ✅ Interest/principal split structurally correct (±355 minor)
- ⚠ Day-count convention not explicitly documented
- ⚠ Tests pass for current single-facility

### Depreciation
- ✅ Useful-life canonical decision
- ✅ Category CAPEX extraction
- ✅ Tax basis match
- ⚠ Book basis not produced
- ⚠ Canonical module not integrated to runtime

### Tax
- ✅ Canonical loss window (Croatia 10-period)
- ✅ R35/R41/R43/R67 reproducibility
- ✅ Residual +5,271 kEUR documented
- ⚠ Sign concern unresolved
- ⚠ SHL gross-accrued candidate driver

### SHL
- 🚫 No canonical module
- 🚫 Post-senior cash sweep not defined
- 🚫 Optional minimum cash reserve not implemented
- 🚫 Tax interface not formal
- 🚫 No SHL audit table in canonical form

### Distribution / R99
- 🚫 Audit-only
- 🚫 Source ownership not defined
- 🚫 Gates fail

---

## O. Next Branch Recommendation

**`phase7-senior-debt-dscr-source-map`** (Branch #1 in roadmap)

### Rationale

Two P1 modules: Senior Debt sizing source map AND SHL cash sweep source map. Which first?

**Senior Debt first** because:
1. Senior debt sizing CFADS determines what's left for SHL (downstream dependency)
2. Macro!R50 hypothesis empirically verified in this blueprint — small follow-up needed to formalize
3. DSCR PPA/merchant switch already partly understood; quick win
4. SHL cash sweep depends on cleaner senior debt sizing first

After Senior Debt source map → SHL source map → SHL module design → both canonical engines together.

### Allowed scope

- `docs/phase7_senior_debt_dscr_source_map.md` — Macro!R49/R50, DSCR switch, formula chain
- `reports/phase7_tuho_senior_debt_sizing_extraction.csv` — period-by-period extraction
- `tests/test_senior_debt_source_map.py` — assert extraction completeness
- Optional: `tests/test_macro_r50_hardcoded_verification.py` — assert Macro!R50 is hardcoded (not formula)

### Forbidden scope

- No `domain/senior_sculpting.py` changes
- No `domain/senior_rate_schedule.py` changes
- No runtime adapter changes
- No flag changes
- No factory opt-in
- No SHL changes
- No R99/R102 promotion
- No app/* changes

### Acceptance

1. Macro!R50 per-period values extracted and documented
2. DSCR PPA/merchant switch period identified (op_idx 24 confirmed)
3. Python current sizing source documented (CFADS or sizing_cfads)
4. Gap analysis: where Python deviates from Excel sizing convention
5. Recommendation: canonical `SeniorDebtSizingPolicy` parameters
6. Default-off path: how to wire explicit sizing_cfads behind flag
7. All 45+ existing tests still pass

---

## Final Report

| Item | Value |
|---|---|
| Branch | `phase7-model-stack-blueprint` |
| Type | docs/report only |
| Production/runtime behavior changed | **NO** |
| Module statuses | 2 CLOSED (Rev, Sponsor), 1 RUNTIME-READY (OPEX), 4 PARTIAL (Const, Sr Debt, Dep, Tax), 2 BLOCKED (SHL, Dist) |
| Reuse/refactor/replace summary | Reuse: 5 modules; Refactor: 4 modules; Legacy baseline: 3 modules |
| Senior Debt DSCR conclusion | **Macro!R49 = actual CFADS, Macro!R50 = hardcoded sizing CFADS (32% buffer for ~1.45x min DSCR). Canonical `SeniorDebtSizingPolicy` with explicit `sizing_cfads_keur_by_period` recommended.** |
| SHL sweep + reserve conclusion | **Post-senior cash 100% to SHL (TUHO empirical). Optional `minimum_cash_reserve_keur` documented for future input, default OFF.** |
| R99/R102 status | **BLOCKED. 6/16 gates done, 10 pending.** |
| Recommended next branch | `phase7-senior-debt-dscr-source-map` (P1) |
| Roadmap | 8 branches: source-map → module-design → runtime-flag impl |
| Tests | All 45 Phase 6 validation tests pass (no code changes) |
| Merge recommendation | **MERGE** — pure docs/report; no risk to production |
