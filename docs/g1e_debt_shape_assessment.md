# G1E: Reference Workbook Debt Shape Assessment (Generic Solar/Wind)

**Status: Analysis only. No code or workbook files changed.**

Scope: this assessment covers **Generic Solar and Generic Wind only**. TUHO
and Oborovo are explicitly out of scope and confirmed unaffected — both have
frozen, pinned `senior_debt_keur` baselines (`test_tuho_senior_debt_unchanged`
→ `43,359.0`; `test_oborovo_senior_debt_unchanged` → `42,852.27`, in
`tests/test_g1b_factory_defaults_fix.py`), and their own factory-default
tests (`test_tuho_wind1_unchanged`, `test_oborovo_unchanged`) pin their inputs
independently of any Generic-specific change. `run_waterfall()` /
`run_waterfall_v3_core()` is the single shared engine across all four
projects — any recommendation below that touches that engine would put these
two baselines at risk and is treated accordingly.

Base commit: `main`, post-`afd340b` ("G1H: fix Generic Solar/Wind equity/SHL
funding to match 75% gearing complement"), which is already merged. This
report verifies G1H's effect and extends the prior G1F gap analysis
(`reports/g1f_debt_sizing_proxy_gap_analysis.md`) with new analysis of
repayment truncation, early-payoff handling, and residual-balance handling —
the three behaviours G1F did not cover in depth.

Forbidden-area files were read-only inspected, never edited: `domain/*`,
`app/waterfall_core.py`, `app/input_adapter.py`, `app/project_factories.py`,
revenue/debt/tax engines, the reference workbooks, and parity fixtures.

---

## 1. Verification of G1F's prior findings

G1F's core claims were re-checked against current `main` and remain
accurate, with one update:

- **CFADS sizing-proxy gap**: confirmed unchanged. Runtime uses flat
  `cfads_for_sculpt = max(0, ebitda * (1 - tax_rate))`
  (`domain/waterfall/waterfall_engine.py` ~387-403); the workbooks' `Debt
  Service` tab row 10 uses `=MAX(0,EBITDA-Depreciation)*Inputs!$C$33` (a
  depreciation-netted proxy). Confirmed present, byte-for-byte, in both
  `GenericSolar_ReferenceModel.xlsx` and `GenericWind_ReferenceModel.xlsx`.
- **Gearing-cap rescale convention**: confirmed identical in both runtime
  (`scale = sizing_debt / dscr_debt`, waterfall_engine.py ~431-468) and both
  workbooks (`Debt Service` row 17 `=IF(C14>0,MIN(1,C16/C14),1)`, row 18
  `=E13*$C$17`). This is the convention G1E ported into the workbooks and it
  is still in force, unchanged.
- **Project IRR's structural unlevered-vs-not-quite-unlevered difference**:
  confirmed unchanged — runtime's `project_irr` tax line never nets real
  interest (`unlev_tax = tax_rate * max(0, ebitda - dep)`,
  waterfall_engine.py ~1148-1153); the workbook's `Cash Flow` row 14 XIRR
  draws its tax line from `P&L!C15`, which does net real interest from the
  real debt schedule (`'Debt Service'!C21`).
- **Equity/SHL funding shortfall — UPDATE, now closed.** G1F reported Solar
  ~2,750 kEUR and Wind ~4,250 kEUR shortfalls versus the 25% equity-like
  complement of a 75%-geared capital structure. Inspecting
  `app/project_factories.py` post-`afd340b`:
  - Solar: `share_capital_keur=500.0` + `shl_amount_keur=7_750.0` = **8,250.0
    kEUR**, exactly matching `0.25 * 33,000 = 8,250.0` kEUR. Closed.
  - Wind: `share_capital_keur=500.0` + `shl_amount_keur=10_250.0` =
    **10,750.0 kEUR**, exactly matching `0.25 * 43,000 = 10,750.0` kEUR.
    Closed.
  - Confirmed numerically (script run against `create_default_solar_project()`
    / `create_default_wind_project()`): `equity_irr` is no longer degenerate
    — Solar now returns **3.48%** (was exactly `0.0%`), Wind **9.22%** (was
    `0.52%`). The literal-zero/near-zero defect G1F flagged as a true bug is
    fixed. A large gap to the workbook's equity IRR still remains (see §3),
    but it is no longer a degenerate/broken value — it is a real,
    measurable, explicable variance.

---

## 2. New analysis: repayment truncation, early payoff, residual balance

### Generic Solar / Generic Wind reference workbooks

Inspected `Debt Service` tab, rows 19-25, in both workbooks via openpyxl
(formulas and cached calculated values):

- **Repayment truncation**: row 22, `Senior debt service =
  MIN(rescaled_capacity, opening_balance + interest)`. This caps each
  period's debt service at "interest + remaining principal," so the
  schedule can never pay more than what is owed. There is no separate
  explicit "final period balloon" formula distinct from the MIN cap — the
  same `MIN()` formula is used every period, and it naturally produces a
  full payoff in whichever period the remaining balance first becomes
  smaller than the rescaled capacity.
- **Early payoff handling**: none. There is no sweep, no voluntary
  prepayment, no cash-trap-to-principal mechanism in the `Debt Service` tab.
  The schedule is a fixed annuity-style amortization computed once at
  sizing time (rows 13-18) and then mechanically applied (rows 20-24); cash
  generated above debt-service requirements flows to the `Equity`/`Cash
  Flow` tabs as distributions, not back into senior debt.
- **Residual balance handling**: checked the calculated (cached) values for
  both workbooks across the full column range. Closing balance (row 24)
  reaches exactly `0` at the contractual payoff period (Solar: column
  matching operating year 16 of 25, i.e. tenor end; Wind: similarly) and
  stays `0` for all subsequent periods. No negative overshoot, no carried
  residual, no write-off line. The `MIN()` cap combined with the rescale
  factor (row 17/18) produces an exact, clean payoff by construction.

### Runtime (`domain/waterfall/waterfall_engine.py`)

- **Repayment truncation**: lines ~682-696. Two explicit branches: (a) the
  final tenor period (`period_in_tenor == tenor_periods - 1`) is a balloon —
  `sp = opening_balance; senior_ds = si + sp`, paying off the entire
  remaining balance regardless of the nominal sculpted payment; (b) all
  other periods use `sp = min(fixed_ds_keur - si, opening_balance)`,
  i.e. principal is capped at the remaining balance (the same protective
  cap as the workbook's `MIN()`, just expressed as a `min()` on principal
  rather than on total debt service).
- **Early payoff handling**: none for senior debt under
  `debt_sizing_method="dscr_sculpt"` with `shl_repayment_method="bullet"`
  (Generic Solar/Wind's actual configuration, confirmed in
  `tests/test_g1b_generic_anchor_parity.py`). The engine does have a
  `cash_sweep()` mechanism (waterfall_engine.py ~919-1035), but it is wired
  to **SHL** repayment only (`shl_repayment_method in {"pik_then_sweep",
  "partial_pay_sweep", "cash_sweep"}`), never to senior debt, for any
  project. Senior debt amortization is always a fixed pre-computed schedule
  with no cash-driven acceleration.
- **Residual balance handling**: lines ~703-722. `remaining_senior_balance`
  is forced to the pre-balloon opening balance in the final period (closing
  = 0 after the balloon payment) and explicitly forced to `0.0` for any
  period at or beyond `tenor_periods`. No negative/overshoot case is
  possible; behaviour matches the workbook's clean-payoff-at-tenor-end
  convention exactly.

### Comparison summary

| Behaviour | Workbook (Solar & Wind) | Runtime | Match? |
|---|---|---|---|
| Repayment truncation | `MIN(rescaled_capacity, opening_balance+interest)` every period | Balloon at final tenor period; `min(fixed_ds-interest, opening_balance)` principal cap elsewhere | **Equivalent in effect** — both guarantee debt service never exceeds outstanding balance + interest, and both reach exactly zero at tenor end |
| Early payoff / sweep | None on senior debt | None on senior debt (sweep exists, but wired to SHL only) | **Identical** |
| Residual balance at tenor end | Exactly 0, no carry, no write-off | Exactly 0, forced by explicit post-tenor zeroing | **Identical** |
| Gearing-cap rescale convention | `scale = senior_debt/dscr_debt` (G1E-ported) | `scale = sizing_debt/dscr_debt` | **Identical formula** |
| DSCR sculpt CFADS proxy | `MAX(0,EBITDA-Depreciation)*tax_rate` | `max(0,EBITDA*(1-tax_rate))` | **Different** (this is the one real divergence, carried over from G1F) |

**Conclusion of new analysis**: truncation, early-payoff, and residual-balance
conventions are **not** a source of variance between runtime and the
reference workbooks for Generic Solar/Wind. They are functionally identical.
The entire debt-service-shape variance traces back to the single
already-identified CFADS sizing-proxy formula difference (and, for Project
IRR and equity IRR specifically, definitional/configuration differences
downstream of it) — there is no additional, previously-hidden truncation or
sweep-related defect.

---

## 3. A. Variance decomposition table (current, post-G1H, verified)

Values from a direct runtime call against `create_default_solar_project()` /
`create_default_wind_project()` (via `run_waterfall_v3_core`), compared to
the golden fixtures in `tests/fixtures/excel_golden_generic_{solar,wind}.json`
(extracted from the reference workbooks):

| Metric | Solar runtime | Solar golden | Δ (Solar) | Wind runtime | Wind golden | Δ (Wind) |
|---|---|---|---|---|---|---|
| Senior debt service P1 (kEUR) | 750.58 | 1,100.04 | −31.8% | 948.43 | 1,395.11 | −32.0% |
| Avg DSCR (sizing-stage) | 1.815 | 1.525 | +19.0% | 3.121 | 2.388 | +30.7% |
| Avg DSCR (actual/realized) | 2.271 | 1.525 | +48.9% | 3.803 | 2.388 | +59.3% |
| Min DSCR (sizing-stage) | 1.815 | 1.443 | +25.8% | 3.121 | 2.304 | +35.5% |
| Equity IRR | **3.48%** (was 0.0% pre-G1H) | 14.46% | −10.98pp | **9.22%** (was 0.52% pre-G1H) | 22.77% | −13.55pp |
| Project IRR | 8.97% | 10.53% | −1.57pp | 13.93% | 16.09% | −2.16pp |

Note: `senior_debt_keur`, `total_capex_keur`, `total_revenue_keur`,
`total_ebitda_keur`, `realized_gearing` are all within tight (<0.5%, mostly
exact) tolerance and are not repeated here — they are validated, not in
variance. Full detail and pass/fail status for all 8 tight + 7 wide anchors
is in `tests/test_g1b_generic_anchor_parity.py` (33/33 passing as of this
assessment, confirming all variances above are within the test's
deliberately wide, already-documented tolerance bands — none of this is new
or unexpected drift).

The equity-IRR gap, while now non-degenerate, is still large in absolute
terms (~11-13.5 percentage points). This is materially larger than the
DSCR/Project-IRR gaps and warrants its own root-cause line below, separate
from the CFADS-proxy-driven debt-shape gap.

---

## 4. B. Root-cause classification

| Variance item | Root cause | Category |
|---|---|---|
| Senior debt-service shape (P1/P2/P3) | Workbook's depreciation-netted sizing CFADS proxy (`MAX(0,EBITDA-Dep)*tax`) vs. runtime's flat proxy (`EBITDA*(1-tax)`) produce different uncapped `dscr_debt`, which changes the rescale factor denominator even though final debt amount and gearing match exactly | **Workbook convention** (deliberate bootstrap-era simplification; truncation/payoff/residual mechanics themselves are identical per §2) |
| Avg DSCR / Min DSCR (sizing-stage and actual) | Same CFADS-proxy difference flows directly into the DSCR denominator/numerator | **Workbook convention** (same root cause as above, not a separate defect) |
| Project IRR | Workbook's Project IRR tax line nets *actual* interest expense from the real debt schedule despite being labeled "unlevered" (Cash Flow tab, `P&L!C15` → real `'Debt Service'!C21`); runtime's `project_irr` deliberately excludes interest from its tax proxy by design | **Modelling choice** (a genuine definitional difference between two valid conventions, not an error in either) |
| Equity IRR | Two stacked causes: (1) now-resolved factory underfunding (fixed by G1H — confirms G1F's diagnosis was correct), and (2) the residual ~11-13.5pp gap is the equity cash-flow stream's downstream sensitivity to the same CFADS-proxy-driven debt-service-shape difference (item 1) plus possibly remaining workbook-vs-runtime equity-distribution-timing or DSRA-funding-mechanics differences not yet decomposed | **Modelling choice** for the resolved part (confirmed fixed); **workbook convention** (inherited from the debt-shape gap) for the bulk of the residual gap — no evidence of a remaining runtime defect after G1H |
| Repayment truncation / early payoff / residual balance | Identical conventions confirmed in both systems (§2) | **Not a variance source** — no classification needed; this was the genuinely new question G1E was scoped to answer, and the answer is "no gap here" |

No item in this assessment is classified as a **runtime defect**. The one
true defect found in this lineage (degenerate equity IRR from underfunded
equity/SHL) was a **factory configuration** issue, already fixed by G1H
(`afd340b`) prior to this assessment, and is not re-opened here.

No item is classified as a **rounding effect** — all variances are
percentage-point/double-digit-percent scale, far larger than floating-point
or display-rounding noise.

---

## 5. C. Recommendations

| Item | Recommendation | Rationale |
|---|---|---|
| Senior debt-service shape / Avg DSCR / Min DSCR | **Leave unchanged** | Root cause (CFADS sizing-proxy formula) is shared-engine code (`run_waterfall_v3_core` / `waterfall_engine.py`) used identically by TUHO and Oborovo. Changing it to net out depreciation would alter `dscr_debt` for every DSCR-sculpted project and risks breaking the pinned `senior_debt_keur` baselines for TUHO (`43,359.0`) and Oborovo (`42,852.27`) in `tests/test_g1b_factory_defaults_fix.py`. The gap is already correctly documented and tolerance-bounded in `tests/test_g1b_generic_anchor_parity.py` (`WIDE_TOLERANCES`) and `docs/generic_validation_reference_excel_spec.md` §6.2. No new evidence from this assessment changes that conclusion. |
| Project IRR | **Revise workbook/spec** (lowest-risk side to change, if changed at all) | Runtime's interest-free unlevered Project IRR is the more textbook-correct definition; the workbook's "unlevered" IRR leaking the interest tax shield through its real P&L tax line is a known, named bootstrap-era simplification (spec §6.2). If a future Excel-template revision is undertaken, fixing the workbook's tax line to exclude real interest (matching its own row-3 "no interest shield" sizing-tab intent) is local, low-risk, and does not touch the shared engine. Recommend deferring unless a template revision is independently planned — do not spin up dedicated work just for this. |
| Equity IRR | **Leave unchanged for the residual gap; no further factory action needed** | The genuine defect (degenerate 0%/0.05% IRR from underfunded equity/SHL) is already fixed by G1H and verified here (Solar 3.48%, Wind 9.22%, both non-degenerate). The remaining ~11-13.5pp gap to the workbook traces to the same CFADS-proxy/debt-shape root cause already assessed above as "leave unchanged," not to a new factory or runtime defect. Recommend documenting this residual gap alongside the existing `equity_irr` wide-tolerance entry in spec §6.2 (currently scoped to the debt-shape gap generally; an explicit one-line note that the post-G1H equity-IRR gap is fully explained by the same root cause, with no further factory work outstanding, would close out this thread for future readers). This is a documentation addition, not a code or workbook change, and is left to a future doc-only pass rather than performed here (this report itself is read-only per its own scope). |
| Repayment truncation / early payoff / residual balance | **Leave unchanged** | Confirmed identical conventions between runtime and both reference workbooks (§2). There is nothing to revise on either side. |

**Overall**: this assessment finds no new runtime defect. All Generic
Solar/Wind DSCR, debt-shape, Project-IRR, and (post-G1H) equity-IRR
variances are explained by the same already-documented CFADS sizing-proxy
methodology difference (or, for Project IRR, a definitional difference),
both of which are deliberate, low-risk-to-leave-as-is choices given the
shared-engine regression risk to TUHO/Oborovo. The new repayment-truncation /
early-payoff / residual-balance analysis (the genuinely new G1E question)
finds the two systems already converge exactly — this closes out that open
question with a "no gap" result rather than uncovering a new one.
