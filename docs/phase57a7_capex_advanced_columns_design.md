# Phase 57A-7 — CAPEX advanced columns design (VAT / WHT / depreciation / payment schedule / utilisation)

> Type: docs / report / test-only
> Auto-merge eligible if all hard no-go gates pass.
> Branch: `phase57a7-capex-advanced-columns-design`
> Base: post-57A-6 main (`bfd7e8586b32a50b8a48a22850b95ba659bdedc1`)

## 1. Purpose

The previous 57A-2 design characterized the **target
columns** of the Excel-like CAPEX sheet. This document
**designs each advanced column** in detail. The
columns are:

1. **Cost / MW** — derived metric.
2. **Contingency** — future model input.
3. **VAT** — future model input.
4. **WHT** — future model input.
5. **Depreciation** — future model input.
6. **Comments** — free-form annotation.
7. **Payment schedule M1–M18** — future model input.
8. **Utilisation** — future model input.

This document is **design only**. None of these
columns are wired to the backend in this PR. The
wiring requires backend changes (IDC engine, funding
drawdown, tax engine, depreciation schedule) that
are explicitly out of scope for 57A-7.

## 2. Column-by-column design

### 2.1 Cost / MW

| Attribute | Value |
|---|---|
| Type | derived (read-only) |
| Formula | `amount_keur / capacity_mw` |
| Source | sub-line `amount_keur` + project `capacity_mw` |
| Backend wiring required | none |
| Editable in user project mode | no (derived) |
| Visible in factory reference mode | yes (derived) |
| Phase to wire | 57A-5 already shows this in the top card strip |

Cost / MW is already shown in the top card strip as
"CAPEX / MW" (Hard CAPEX / MW). The per-line
implementation is a future enhancement.

### 2.2 Contingency

| Attribute | Value |
|---|---|
| Type | future model input (editable) |
| Unit | percent (0–100) |
| Source | user input per sub-line |
| Backend wiring required | new `contingency_pct` field on `CapexItem` (or `CapexSubLine` after 57A-6) |
| Editable in user project mode | yes |
| Visible in factory reference mode | yes (read-only) |
| Phase to wire | 57A-8+ (deferred) |

When wired, the contingency cost is computed as
`amount_keur * contingency_pct / 100` and is added
to the sub-line's effective amount. The contingency
cost feeds P&L, Balance Sheet, and Cash Flow.

### 2.3 VAT

| Attribute | Value |
|---|---|
| Type | future model input (editable) |
| Sub-fields | `vat_applicability` (bool), `vat_rate_pct` (percent) |
| Source | user input per sub-line |
| Backend wiring required | new `vat_applicability` and `vat_rate_pct` fields on `CapexItem` |
| Editable in user project mode | yes |
| Visible in factory reference mode | yes (read-only) |
| Phase to wire | 57A-8+ (deferred) |

When wired, the VAT cost is computed as
`amount_keur * vat_applicability * vat_rate_pct / 100`.
The VAT cost feeds:
- Cash Flow (as a separate outflow or inflow
  depending on direction).
- Balance Sheet (VAT receivable or payable).
- Working capital.

### 2.4 WHT

| Attribute | Value |
|---|---|
| Type | future model input (editable) |
| Sub-fields | `wht_rate_pct` (percent) |
| Source | user input per sub-line |
| Backend wiring required | new `wht_rate_pct` field on `CapexItem` |
| Editable in user project mode | yes |
| Visible in factory reference mode | yes (read-only) |
| Phase to wire | 57A-8+ (deferred) |

When wired, the WHT cost is computed as
`amount_keur * wht_rate_pct / 100` and feeds:
- Tax engine.
- Cash Flow.

### 2.5 Depreciation

| Attribute | Value |
|---|---|
| Type | future model input (editable) |
| Sub-fields | `depreciation_category` (text), `useful_life_years` (int), `is_depreciable` (bool) |
| Source | user input per sub-line |
| Backend wiring required | new fields on `CapexItem` + a depreciation schedule generator |
| Editable in user project mode | yes |
| Visible in factory reference mode | yes (read-only) |
| Phase to wire | 57A-8+ (deferred) |

When wired, the depreciation feeds:
- P&L (depreciation expense per year).
- Fixed asset schedule.
- Balance Sheet (accumulated depreciation, net book
  value).
- Tax engine (depreciation deductions where
  applicable).

### 2.6 Comments

| Attribute | Value |
|---|---|
| Type | free-form text annotation |
| Source | user input per sub-line |
| Backend wiring required | new `comments` field on `CapexItem` |
| Editable in user project mode | yes |
| Visible in factory reference mode | yes (read-only) |
| Phase to wire | 57A-8+ (deferred) |

Comments have **no model effect**. They are a
display-only annotation. Safe to add first in any
runtime PR.

### 2.7 Payment schedule M1–M18

| Attribute | Value |
|---|---|
| Type | future model input (editable) |
| Unit | fraction (0.0–1.0) per construction month |
| Source | user input per sub-line |
| Backend wiring required | new `monthly_schedule: tuple[float, ...]` field on `CapexItem` |
| Editable in user project mode | yes |
| Visible in factory reference mode | yes (read-only) |
| Phase to wire | 57A-8+ (deferred) |

When wired, the payment schedule feeds:
- Equity drawdown (equity-funded portion).
- Senior loan drawdown (senior-debt-funded portion).
- SHL drawdown (SHL-funded portion).
- Senior IDC + SHL IDC.
- Opening senior debt balance at COD.
- Opening SHL balance at COD.

The total of the fractions must equal 1.0 (or be
normalised to 1.0 by the backend).

### 2.8 Utilisation

| Attribute | Value |
|---|---|
| Type | future model input (editable) |
| Unit | fraction (0.0–1.0) — the percentage of the
  amount that is actually drawn each month |
| Source | user input per sub-line (or derived from
  payment schedule) |
| Backend wiring required | new `utilisation: tuple[float, ...]` field on `CapexItem` |
| Editable in user project mode | yes |
| Visible in factory reference mode | yes (read-only) |
| Phase to wire | 57A-8+ (deferred) |

When wired, the utilisation feeds the same drawdown
/ IDC chain as the payment schedule. Utilisation is
typically derived from the payment schedule (1.0
utilisation = 100% of the month's payment is drawn).

## 3. Staged backend integration

The columns are **not** wired in 57A-7. The
recommended stage plan:

### 3.1 Stage 1: Comments (no model effect)

A future runtime PR adds the Comments column to the
CAPEX sheet. The Comments column is purely
display-only. The backend change is a new
`comments: str` field on `CapexItem`. This is the
**safest** column to wire first because it has no
downstream model effect.

### 3.2 Stage 2: Cost / MW (derived)

Cost / MW is already shown in the top card strip.
The per-line implementation is a UI-only change (no
backend). Stage 2 is a UI PR that adds the Cost / MW
column to the line grid as a read-only derived
value.

### 3.3 Stage 3: Contingency / VAT / WHT

These three columns together affect the same
downstream chains (cash flow, balance sheet, working
capital, tax). The recommended stage is a single
runtime PR that adds the three input fields and
wires them to a new `capex.tax_engine` module. The
PR must include a new `contingency_pct`,
`vat_applicability`, `vat_rate_pct`, and
`wht_rate_pct` field on `CapexItem`.

### 3.4 Stage 4: Depreciation

Depreciation requires a depreciation schedule
generator. This is a larger effort that should be
its own PR. The new fields are
`depreciation_category`, `useful_life_years`, and
`is_depreciable` on `CapexItem`.

### 3.5 Stage 5: Payment schedule + Utilisation

Payment schedule and Utilisation together feed the
IDC and funding drawdown chain. This is the largest
stage and requires changes to the construction
funding engine. The new fields are
`monthly_schedule: tuple[float, ...]` and
`utilisation: tuple[float, ...]` on `CapexItem`.

## 4. What is NOT in 57A-7

- No new columns in the CAPEX sheet.
- No new fields on `CapexItem` or `CapexStructure`.
- No tax engine.
- No depreciation schedule.
- No IDC calculation change.
- No construction funding engine change.
- No senior debt / SHL drawdown logic change.

## 5. Hard no-go (preserved throughout)

- No financial formula changes.
- No IDC calculation changes.
- No construction funding changes.
- No G20 / R99 / R102 promotion.
- No Tailwind / Alpine.
- No Portfolio / BESS / Hybrid.
- No schema / migration in 57A-7.
- No backend keys visible in UI.
- rc1 (`b425a0708719eaa5e1d922b1008e5609758e0ad4`)
  frozen.
