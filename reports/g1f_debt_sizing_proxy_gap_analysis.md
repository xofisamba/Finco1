# G1F: Debt-Sizing/Tax-Proxy Methodology Gap Analysis (Generic Solar/Wind)

Status: **Analysis only. No code changed.** Base: `main` @ `be3c8dc4` (post-G1E). The
G1B baseline anchor-parity tests (`tests/test_g1b_generic_anchor_parity.py`, branch
`g1b-anchor-parity-tests`) are pushed but not yet merged at the time of this analysis;
none of the findings below depend on that merge having happened.

Forbidden-area files were read-only inspected, never edited:
`app/waterfall_core.py`, `domain/waterfall/waterfall_engine.py`, `app/project_factories.py`,
`domain/inputs.py`, `domain/revenue/generation.py`, TUHO/Oborovo factories, rc1, R99/R102/G20.

---

## 1. Runtime debt-sizing proxy

**Exact formula** (`domain/waterfall/waterfall_engine.py:387-403`):

```python
# Debt sculpting uses CFADS proxy (EBITDA minus estimated tax), not raw EBITDA
cfads_for_sculpt = [
    max(0.0, ebitda * (1.0 - tax_rate))
    for ebitda in ebitda_schedule[:tenor_periods]
]
sculpt_result = closed_form_sculpt(
    cfads_schedule=cfads_for_sculpt, rate_schedule=rate_schedule,
    tenor_periods=tenor_periods, target_dscr=target_dscr,
    gearing_cap_keur=float('inf'), dscr_schedule=dscr_schedule,
)
dscr_debt = sculpt_result.debt_keur
```

This is a **flat percentage-of-EBITDA** tax proxy — it does **not** net out
depreciation. It feeds `closed_form_sculpt`, which returns the uncapped,
DSCR-constrained debt capacity (`dscr_debt`). The gearing cap is then applied
separately (`gearing_cap_keur = sizing_base_for_gearing * gearing_ratio`,
line 417) and `sizing_debt = min(dscr_debt, gearing_cap_keur)` (or `max` for
the `"gearing_cap"` method) at lines 420-425. When the gearing cap binds
tighter than the DSCR capacity, the debt-service-capacity schedule is
rescaled by `scale = sizing_debt / dscr_debt` (lines 431-468) — this is the
same rescale-convention mechanism that G1E ported into the reference
workbooks.

`WaterfallResult.avg_dscr` / `.min_dscr` (lines 1237-1238) are populated
**from this same sizing-stage `sculpt_result`**, i.e. they reflect the
DSCR achieved against the flat sizing-CFADS proxy, not a true post-financing
realized ratio. A second, separate pair of fields, `actual_avg_dscr` /
`actual_min_dscr` (lines 1241-1242), is computed from the real per-period
DSCR (`all_dsrs`, using actual realized CFADS/tax) and is closer in spirit
to the workbook's "DSCR (true)" row — but, as shown in Section 3, it does
**not** resolve the gap; it is a different number from a different (but
still diverging) calculation, not a missing reconciliation.

**Project IRR's tax line is deliberately, structurally unlevered**
(lines 1148-1153):

```python
# Project IRR = unlevered (EBITDA - unlevered tax)
# Unlevered tax = tax_rate * max(0, EBITDA - dep) — financing-independent
dep = depreciation_schedule[i] if i < len(depreciation_schedule) else 0
unlev_tax = tax_rate * max(0.0, ebitda - dep)
project_cfs.append(ebitda - unlev_tax if ebitda else 0)
```

This nets out depreciation but **never** subtracts interest expense — by
design, so that `project_irr` (computed via `xirr(project_cfs, ...)`,
line 1206) cannot move when only the debt schedule changes. This is a
genuine engineering choice, not an oversight.

**Shared with TUHO/Oborovo?** Yes — `run_waterfall()` is the single shared
sculpting/amortization/returns engine for every project (TUHO, Oborovo,
Generic Solar, Generic Wind all call the same function). There is no
per-project branch in this code path. Confirmed during G1E: TUHO's and
Oborovo's own frozen-baseline tests (`test_tuho_senior_debt_unchanged`,
`test_oborovo_senior_debt_unchanged` in `tests/test_g1b_factory_defaults_fix.py`)
pin exact debt amounts derived from this exact sizing logic.

**Would changing it affect frozen reference parity?** Yes, materially.
Changing `cfads_for_sculpt` to net out depreciation (to mirror the workbook)
would change `dscr_debt` for every project that uses DSCR-constrained sizing,
which would shift `sculpt_result.debt_keur`/`avg_dscr`/`min_dscr` and likely
break the TUHO (`debt_keur == 43_359.0`) and Oborovo (`debt_keur == 42_852.27`)
pinned baselines — both currently rely on the flat proxy. This is exactly the
risk flagged (and avoided) during G1E for the rescale-vs-truncate question,
and it applies with equal force here.

---

## 2. Workbook debt-sizing/tax proxy

Read directly from `validation/reference_models/GenericSolar_ReferenceModel.xlsx`
(Wind is structurally identical, only cell coordinates differ by one column).

**`Debt Service` tab** (the sizing/amortization proxy, rows 8-22):

| Row | Label | Formula |
|---|---|---|
| 8 | EBITDA | `=Revenue!C13-OpEx!C10` |
| 9 | Depreciation (straight-line) | `=CapEx!$BD$11/Inputs!$C$37/2` |
| 10 | **Tax (sizing proxy, no interest shield)** | `=MAX(0,C8-C9)*Inputs!$C$33` |
| 11 | CFADS (sizing proxy) | `=C8-C10` |
| 13 | Debt-service capacity per period | `=E11/Inputs!$C$32` (i.e. `/target_dscr`) |
| 14 | Sized senior debt (NPV of capacity) | `=NPV(rate, E13:AH13)` |
| 15 | Gearing cap amount | `=Inputs!$C$28*CapEx!$BD$11` |
| 16 | **SENIOR DEBT** | `=MIN(C14,C15)` |
| 17 | Schedule rescale factor | `=IF(C14>0,MIN(1,C16/C14),1)` (the G1E addition) |
| 18 | Rescaled debt-service capacity | `=E13*$C$17` |
| 20-22 | Amortization (opening balance / interest / **senior debt service**) | standard annuity-style sweep against row 18 |

So the workbook's sizing tax proxy is `MAX(0, EBITDA - Depreciation) * tax_rate`
— it nets out depreciation, but (per the row label itself, which explicitly
calls out "no interest shield") deliberately excludes interest, same intent
as the runtime's design but a **different formula** (depreciation-netted vs.
flat-percentage).

**`Cash Flow` tab** (the *true*/realized metrics, rows 6-14):

| Row | Label | Formula |
|---|---|---|
| 7 | EBITDA | `='P&L'!C7` |
| 8 | Tax | `='P&L'!C15` |
| 9 | **CFADS (true)** | `=C7-C8` |
| 10 | Senior debt service | `='Debt Service'!C22` |
| 11 | **DSCR (true)** | `=C9/C10` |
| 12 | Unlevered project cash flow | `=C6(Capex)+C9` |
| 14 | **PROJECT IRR** | `=XIRR(C12:BB12,C4:BB4)` |

`P&L!C15` (the real tax line feeding both DSCR-true and Project IRR) is
computed as `Pre-tax profit * tax_rate` after loss relief, where
`Pre-tax profit = EBITDA - Depreciation - Interest expense (actual)`, and
`Interest expense (actual)` is sourced directly from `'Debt Service'!C21`
— the **real, actual** interest on the **real, actual** debt balance for
that period (not a proxy).

**Why Project IRR moves with the debt schedule:** Project IRR's cash-flow
row (`C12`) never includes debt service directly — it looks "unlevered" by
construction. But its tax line (`C8`→`P&L!C15`) is computed net of the
*real* interest expense from the *real* debt schedule. Any change to the
debt-service shape (e.g. G1E's truncate→rescale convention change) changes
the real interest expense per period, which changes the real tax, which
changes "true" CFADS, which changes the cash flow that feeds the XIRR. This
is a genuine interest-tax-shield leak into a metric the workbook labels
"unlevered" — confirmed during the G1E recalculation fix and reconfirmed
here. It is a **definitional simplification in the bootstrap workbook**, not
a bug introduced by G1E and not something G1E was scoped to fix.

---

## 3. Difference decomposition

Measured on current `main` (post-G1E) using
`create_default_solar_project()` / `create_default_wind_project()`:

| Quantity | Solar runtime | Solar golden | Wind runtime | Wind golden |
|---|---|---|---|---|
| `total_capex_keur` | 33,000.00 | 33,000.00 | 43,000.00 | 43,000.00 |
| `senior_debt_keur` | 24,750.00 | 24,750.00 | 32,250.00 | 32,250.00 |
| `realized_gearing` | 75.0% | 75.0% | 75.0% | 75.0% |
| `total_revenue_keur` | 129,716.66 | 129,903.91 (Δ ‑0.14%) | 284,786.08 | 285,195.73 (Δ ‑0.14%) |
| `total_ebitda_keur` | 117,545.15 | 117,732.39 (Δ ‑0.16%) | 267,168.31 | 267,579.06 (Δ ‑0.15%) |
| `avg_dscr` (sizing-stage) | 1.815 | 1.525 (Δ +19.0%) | 3.121 | 2.388 (Δ +30.7%) |
| `avg_dscr` (actual/realized) | 2.271 | 1.525 (Δ +48.9%) | 3.803 | 2.388 (Δ +59.3%) |
| `min_dscr` (sizing-stage) | 1.815 | 1.443 (Δ +25.8%) | 3.121 | 2.304 (Δ +35.5%) |
| `senior_debt_service_p1_keur` | 750.58 | 1,100.04 (Δ ‑31.8%) | 948.43 | 1,395.11 (Δ ‑32.0%) |
| `project_irr` | 0.0897 | 0.1053 (Δ ‑1.57pp) | 0.1393 | 0.1609 (Δ ‑2.16pp) |
| `equity_irr` | 0.0000 | 0.1446 (Δ ‑14.46pp) | 0.0052 | 0.2277 (Δ ‑22.25pp) |

**Decomposition:**

1. **CFADS sizing-proxy difference** (the dominant driver of the debt-service
   shape, DSCR, and indirectly Project IRR gaps): runtime's flat
   `EBITDA*(1-tax_rate)` proxy vs. the workbook's depreciation-netted
   `MAX(0,EBITDA-Depreciation)*tax_rate` proxy produce different *uncapped*
   `dscr_debt` capacities (confirmed in the prior G1E investigation: ~7-12%
   apart). Because the gearing cap binds identically in both systems
   (debt = 75% of capex exactly, matching to the cent), the *amount* of debt
   sized is unaffected — but the **rescale factor** (`scale = sizing_debt /
   dscr_debt`) differs because its denominator differs, which changes the
   **shape/profile** of the debt-service schedule even though total
   principal is identical. This shows up directly as the workbook's `C17`
   rescale factor (0.836 for Solar) vs. the implied runtime scale (~0.95),
   and explains why `senior_debt_service_p1/p2/p3` diverge by ~32% even
   though `senior_debt_keur` matches exactly.

2. **Tax shield difference** (Project IRR specifically): the workbook's
   Project IRR nets real interest expense into its "unlevered" cash flow via
   the real P&L tax line, while runtime's Project IRR computes a genuinely
   interest-free unlevered tax (`tax_rate*max(0,EBITDA-dep)`). This is a
   **definitional** difference, not a numerical proxy bug — runtime's
   Project IRR is, if anything, the more textbook-correct "unlevered" metric.
   It explains the bulk of the ~1.6-2.2 percentage-point Project IRR gap, on
   top of whatever residual effect the CFADS-proxy/debt-shape difference
   above contributes through other channels (e.g. depreciation timing).

3. **Debt-service shape difference after G1E**: confirmed structural (see #1)
   — not a leftover defect from G1E. G1E correctly ported the
   *rescale-vs-truncate convention*; it did not, and was not scoped to,
   reconcile the *upstream CFADS proxy* that determines the rescale factor's
   magnitude.

4. **Equity/SHL configuration difference**: `create_default_solar_project()`
   sets `share_capital_keur=500.0` and `shl_amount_keur=5000.0` (total
   "equity-like" financing = 5,500 kEUR), against a 75%-geared capital
   structure that implies a 25% equity-like share of 33,000 kEUR = 8,250
   kEUR. The ~2,750 kEUR shortfall (Wind: similar, 500+6,000=6,500 vs.
   43,000*0.25=10,750, a ~4,250 kEUR shortfall) is **not** a methodology
   proxy question — it is a `app/project_factories.py` configuration gap,
   independent of and additive to items 1-3. It plausibly explains why
   Solar's `equity_irr` comes back as exactly `0.0` (likely an
   underfunded/degenerate equity cash-flow stream) rather than merely "off
   by a documented amount." This file is in this analysis's forbidden list,
   so it is flagged here as a finding, not fixed.

---

## 4. Options

| Option | Description | Assessment |
|---|---|---|
| **A** | Change workbook to match runtime's flat sizing proxy and interest-free Project IRR | Workbook is the bootstrap *reference* deliverable; rewriting its CFADS/tax formulas a second time (after G1E) to chase the runtime proxy risks turning it into a runtime mirror rather than an independent check, and doesn't fix the equity/SHL config gap (item 4) regardless. |
| **B** | Change runtime proxy to match workbook (depreciation-netted sizing CFADS; interest-inclusive Project IRR tax) | Touches the single shared sculpting engine used by TUHO/Oborovo — high regression risk to frozen baselines (`test_tuho_senior_debt_unchanged`, `test_oborovo_senior_debt_unchanged`), explicitly forbidden in this analysis's scope and in G1E's prior scope for the same reason. Also would make Project IRR *less* correct (re-introducing the interest-tax-shield leak runtime currently avoids). |
| **C** | Keep both, classify DSCR/debt-service/IRR as baseline-guarded but not Excel-grade | Honest and low-risk, but offers no path to closing the gap or even labeling *which* anchors are closer to closing vs. structurally divergent. |
| **D** | Split anchors into validated/tight vs. known-methodology-gap categories, with documented rationale per anchor | Already implemented in `tests/test_g1b_generic_anchor_parity.py` (`TIGHT_TOLERANCES` vs. `WIDE_TOLERANCES`) and `docs/generic_validation_reference_excel_spec.md` §6.2. Most actionable — it doesn't just label the gap, it explains the mechanism per anchor so a future ticket can target the right root cause (CFADS proxy vs. Project IRR definition vs. factory equity config) individually instead of one undifferentiated "Generic DSCR/IRR is wrong" bucket. |

---

## 5. Recommendation

**Treatment by anchor:**

| Anchor | Treatment | Rationale |
|---|---|---|
| `total_capex_keur`, `total_revenue_keur`, `total_opex_keur`, `total_ebitda_keur`, `idc_keur`, `bank_fees_keur`, `senior_debt_keur`, `realized_gearing` | **Validated / tight** | Agree to <0.2% (revenue/EBITDA) or exactly (capex/debt/gearing). No further action. |
| `avg_dscr`, `min_dscr`, `senior_debt_service_p1/p2/p3_keur` | **Known-methodology-gap, documented (Option D)** | Root cause is the CFADS sizing-proxy formula difference (item 1), shared engine code, fixable only via a cross-project change (Option B) that is out of scope and risky. Recommend a dedicated follow-up ticket to evaluate switching the runtime's flat `EBITDA*(1-tax_rate)` sizing proxy to a depreciation-netted proxy *with* a full TUHO/Oborovo regression re-baseline — do not attempt as a side effect of Generic-only work. |
| `project_irr` | **Known-methodology-gap, documented (Option D) — but flag the workbook, not the runtime, as the side to reconsider** | Runtime's interest-free unlevered Project IRR is the more defensible definition. If anything is "fixed" here, it should be the *workbook's* Project IRR formula (excluding real interest from the tax line) in a future Excel-template revision — not the runtime. Until then, document the wide tolerance as accommodating a workbook simplification, exactly as already done in spec §6.2. |
| `equity_irr` | **Needs a factory-level fix before relying on it externally** | Unlike the others, this is not a methodology question — `app/project_factories.py`'s Generic Solar/Wind defaults under-fund the equity-like financing relative to the stated 75% gearing ratio, which plausibly degenerates Solar's equity IRR to exactly `0.0`. Recommend a follow-up ticket (similar in shape to the G1B/G1C factory-default fixes) to align `share_capital_keur`/`shl_amount_keur` with the stated capital structure. Do not present Generic Solar/Wind equity IRR to external stakeholders until this is resolved — a `0.0%` headline number is more likely to read as "broken" than "methodology caveat." |

**Go/no-go for G1D validation reporting:** **GO, with an explicit caveat.**
Generic Solar/Wind can be labeled "validated" for capex, revenue, opex,
EBITDA, senior debt amount, and gearing (all within Excel-grade tolerance).
DSCR, debt-service shape, and Project IRR should be labeled "directionally
consistent, methodology caveat documented" (pointing at spec §6.2) rather
than "validated" outright — they are pinned regression baselines, not
Excel-grade matches, for reasons that are structural and well understood
(item 1 and the Project-IRR definitional difference), not unexplained drift.

**Equity IRR should not be included in the G1D "validated" or even
"caveated" external-facing summary at all** until the factory equity/SHL
funding gap is fixed — it is the one item in this analysis that is a latent
defect rather than a documented methodology choice, and showing it
externally in its current state (a `0.0%` IRR for the Solar baseline) would
undermine confidence in the rest of the validated set.
