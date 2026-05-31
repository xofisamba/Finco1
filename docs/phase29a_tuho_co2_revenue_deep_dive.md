# Phase 29A: TUHO CO2 Revenue Deep-Dive

Base: `a43820d16d7f86ed4eac9f898c1d7c99f9fb7ab1`
Phase: Diagnostic / validation / documentation
Date: 2026-05-31

---

## Scope

Inspect, validate, and document the TUHO CO2 certificate revenue treatment — price curve, escalation, production linkage, and contribution to total revenue and equity IRR.

**In scope:**
- TUHO CO2 input fields and price schedule
- CO2 revenue calculation flow (source → aggregation)
- TUHO Y1 CO2 anchor (~611 kEUR) and equity IRR context (11.81% runtime vs 11.61% Excel)
- Period-level CO2 revenue behavior
- TUHO vs generic wind CO2 distinction

**Out of scope:**
- Financial formula changes (revenue, tax, waterfall, senior debt, SHL, distributions)
- Fixture CSV changes
- TUHO/Oborovo factory flag changes
- Live external CO2 API calls
- CO2 trading/certificate portfolio logic
- Generic wind CO2 validation (remains exploratory/unvalidated)

---

## Inspected Files

| File | Relevance |
|------|-----------|
| `app/project_factories.py` | TUHO factory: CO2 fields, price schedule, semiannual values |
| `domain/revenue/generation.py` | `_certificate_revenue_keur()`, `full_revenue_schedule()` |
| `domain/revenue/tariff.py` | `co2_certificates_revenue()` function |
| `domain/waterfall/waterfall_engine.py` | CO2 CIT bridge (`co2_revenue_keur`) |
| `domain/waterfall/tax_engine.py` | CO2 added to EBITDA for taxable income |
| `domain/diagnostics/cfads_bridge.py` | TUHO P4 anchors including `co2_revenue_keur` = 307.91 kEUR (per-period, not Y1 total) |
| `app/ui_runner.py` | `run_demo_project()` for TUHO Base |
| `docs/phase27_frozen_path_external_validation_pack.md` | TUHO CO2 calibration reference |
| `docs/validation_pack_executive_summary.md` | CO2 Y1 ~611 kEUR, equity IRR 11.81% |

---

## CO2 Architecture: Source-to-Output Map

### Input Fields (TUHO factory, `app/project_factories.py`)

```
co2_enabled=True
co2_certificate_price_eur_per_mwh=4.191063312  ← flat default
co2_sales_schedule=RevenueAdjustmentSchedule(semiannual_values=(
    4.191063312, 4.191063312,   ← Y1-H1, Y1-H2
    3.783032455, 3.783032455,   ← Y2-H1, Y2-H2
    3.375001599, 3.375001599,   ← Y3-H1, Y3-H2
    2.966970742, 2.966970742,
    2.45, 2.45,
    ... (30 periods, declining)
))
```

**Fallback priority (per generation.py):**
1. `co2_sales_schedule.value_for_period(...)` — used for TUHO
2. `co2_certificate_price_eur_per_mwh` — flat default if schedule absent
3. `co2_price_eur` — legacy fallback

### Generation Linkage (`domain/revenue/generation.py`)

For each operating period:
```
co2_eur_mwh = co2_sales_schedule.value_for_period(op_idx, year_idx, period_in_year)
co2_certificate_revenue_keur = generation_mwh × co2_eur_mwh / 1000
```

**CO2 is not subtracted from revenue — it is added.**
Net revenue after balancing:
```
net_revenue_after_balancing_keur =
    energy_revenue_keur
  - balancing_cost_pv_keur       ← subtraction
  - balancing_cost_wind_keur     ← subtraction
  + co2_certificate_revenue_keur  ← addition
```

### Revenue Aggregation

`revenue_keur = net_revenue_after_balancing_keur` (legacy alias for backward compat)
→ `total_revenue_keur` accumulates across all periods in the waterfall output.

CO2 is also passed to the tax engine as a CIT bridge:
- `co2_revenue_keur` added to EBITDA for taxable income (`domain/waterfall/tax_engine.py`)
- This means CO2 reduces taxable income (i.e., CO2 is treated as a positive revenue item for tax purposes too)

---

## TUHO CO2 Input Assumptions

| Parameter | Value | Source |
|-----------|-------|--------|
| CO2 enabled | Yes | `co2_enabled=True` |
| Y1 CO2 price (flat default) | 4.191 EUR/MWh | `co2_certificate_price_eur_per_mwh=4.191063312` |
| Y1 CO2 price (schedule H1/H2) | 4.191 EUR/MWh | Semiannual schedule, first 2 entries |
| CO2 sales schedule | 30 semiannual periods, declining from 4.191 → 0.7 | `co2_sales_schedule` in TUHO factory |
| CO2 certificate revenue formula | `generation_mwh × price_EUR/MWh / 1000` | `_certificate_revenue_keur()` in `generation.py` |
| CO2 revenue included in total revenue | Yes | Added to `net_revenue_after_balancing_keur` |
| CO2 revenue included in EBITDA for CIT | Yes | Phase 9 CO2→CIT bridge |

---

## TUHO CO2 Period-Level Behavior

Extracted from `run_demo_project('TUHO', 'Base')` using `full_revenue_schedule()`:

**Y1-H1 (op_idx ~2):**
- Generation: ~72,271 MWh
- CO2 price: 4.191 EUR/MWh
- CO2 certificate revenue: ~72,271 × 4.191 / 1000 = **~303 kEUR**

**Y1-H2 (op_idx ~3):**
- Generation: ~73,469 MWh
- CO2 price: 4.191 EUR/MWh
- CO2 certificate revenue: ~73,469 × 4.191 / 1000 = **~308 kEUR**

**Y1 total (H1+H2): ~611 kEUR** — matches Phase 27 anchor.

The semiannual price declines roughly every 2 periods, reaching ~0.7 EUR/MWh by period 30 (year 15).

---

## TUHO Y1 CO2 Anchor

| Anchor | Value | Source |
|--------|-------|--------|
| Y1 CO2 revenue | ~611 kEUR | Phase 27 validation pack / MEMORY.md Sprint 21 |
| Per-period (H1) | ~303 kEUR | Computed from generation × 4.191/1000 |
| Per-period (H2) | ~308 kEUR | Computed from generation × 4.191/1000 |
| CO2 price Y1 | 4.191 EUR/MWh | TUHO factory `co2_certificate_price_eur_per_mwh` |
| CO2 schedule Y1 | 4.191 (flat) | Semiannual schedule, first 2 entries |

---

## TUHO Equity IRR Context

| Metric | Value | Note |
|--------|-------|------|
| Runtime equity IRR | 11.81% | `run_demo_project('TUHO', 'Base')` result |
| Excel reference IRR | 11.61% | Phase 27 validation pack |
| Delta | +0.20 pp | Within ±1.0pp tolerance |
| CO2 included | Yes | `co2_enabled=True` confirmed |
| IRR classification | Validated | Within documented tolerance |

**Note:** Equity IRR includes CO2 certificate revenue as part of total revenue. Removing CO2 would lower the equity IRR. The Phase 27 calibration with CO2 enabled produced 11.81% vs Excel's 11.61% — within the ±1.0pp guardrail.

---

## Generic Wind CO2 Non-Validation Statement

**Generic Wind (WIND-001):**
- `co2_enabled=True`, `co2_price_eur=5.0`
- No CO2 sales schedule defined (flat price, no escalation)
- No Excel reference
- **Status: ⚠️ Exploratory / Unvalidated**

**TUHO Wind:**
- `co2_enabled=True`, `co2_sales_schedule` defined (30 semiannual declining values)
- Y1 CO2 anchor ~611 kEUR confirmed
- **Status: ✅ Validated** (within TUHO frozen-template calibration)

**This phase does not validate generic wind CO2. Generic wind CO2 remains exploratory.**

---

## Limitations and Classification

| Item | Classification | Note |
|------|--------------|------|
| TUHO Y1 CO2 ~611 kEUR | ✅ Anchor confirmed | Phase 27 reference + runtime computation |
| TUHO equity IRR 11.81% vs 11.61% | ✅ Within tolerance | ±1.0pp guardrail maintained |
| TUHO CO2 price schedule | ✅ Identified | 30 semiannual values, declining |
| TUHO production→CO2 linkage | ✅ Identified | `generation_mwh × price / 1000` |
| TUHO CO2→CIT bridge | ✅ Identified | Phase 9, added to EBITDA for tax |
| Generic wind CO2 | ⚠️ Unvalidated | No Excel reference, no schedule |
| Period-level CO2 in output result | ⚠️ Not exposed | `result.periods` doesn't expose CO2 per period in top-level attrs |
| CO2 certificate market assumptions | ❌ Out of scope | No live API, no market data source |

---

## Non-Claims

- No claim that CO2 certificate revenue is independently audited or verified by third party
- No claim that CO2 price schedule reflects live market data
- No claim that generic wind CO2 is validated
- No claim that TUHO CO2 is bankable or lender-approved
- No claim that CO2 revenue is stable or guaranteed

---

## Recommended Next Steps

1. **Phase 29B** — Oborovo CAPEX Sensitivity: test CAPEX variation impact on senior debt and equity IRR for Oborovo (higher priority per cofix interest)

2. **Phase 29C** — TUHO CO2 Period-Level CSV: if period-level CO2 exposure is needed for stakeholder presentation, consider adding `co2_revenue_keur` to the `SculptingPeriod` output struct (not in this phase — would require model change)

3. **Phase 30** — TUHO/Oborovo Shared Debt Sizing Path Audit: audit the frozen senior debt schedule wiring for both projects to confirm no unintended divergence

---

## Out-of-Scope List

- Revenue formula changes
- Tax formula changes
- Waterfall logic changes
- Senior debt sizing changes
- SHL/distribution logic changes
- Fixture CSV changes
- TUHO/Oborovo factory flag changes
- Live external CO2 API calls
- CO2 trading/certificate portfolio logic
- Construction IDC runtime engine
- M1–M18 IDC wiring
- C.16 Project Rights wiring
- Generic wind CO2 validation