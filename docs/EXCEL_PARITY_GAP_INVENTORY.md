# Excel Parity Gap Inventory

**Branch:** excel-parity-discovery
**Base SHA:** 9c3487b1189e236573a1dabf1685f77623738db9
**Audit date:** 2026-07-01
**Sprint context:** Post 15-PR Product Reality Gap + Product Acceptance Sprint

---

## Executive Summary

The engine core (`waterfall_core.py` + `domain/waterfall/waterfall_engine.py`) is a
well-built project-finance waterfall that correctly computes CAPEX, IDC, revenue,
OPEX, senior debt sculpting (DSCR-based iterative and closed-form), SHL mechanics,
DSRA reserves, tax (including ATAD interest limitation for TUHO), loss carry-forward,
LLCR/PLCR covenants, project/equity/sponsor IRR, and per-period distributions.

A separate offline `domain/financial_statements/` assembly layer exists and produces
P&L, tax bridge, balance sheet, and PF cash-waterfall outputs — but this layer is
**not connected to the live UI**: it is only called by the export pipeline
(`app/export/institutional_workbook.py`) and offline report scripts.

The UI Reality-Gap Sprint (PR6–PR9) removed misleading static tables and replaced
them with honest "not-yet-connected" panels for Financial Statements, Distribution,
Sponsor, Senior Debt output schedule, and Tax output schedule. None of those gaps
were fixed — they were made honest.

### What is working (engine computes, KPIs surface in UI via `lastRuntimeSummary`)

- CAPEX total, IDC, bank fees — computed and exported
- Revenue (PPA + merchant + CO2 bridge, BESS) — computed per-period
- OPEX (per-period, line-item engine) — computed
- Senior debt sizing (DSCR sculpt, closed-form, fixed-debt, frozen-fixture) — computed
- SHL (bullet, cash sweep, PIK, PIK-then-sweep, partial pay, FCF waterfall) — computed
- DSRA + MRA reserves — computed
- Tax: basic CIT, loss carry-forward, ATAD interest limitation (TUHO), fiscal reintegration — computed
- DSCR / LLCR / PLCR / lockup — computed
- Project IRR, Equity IRR, Sponsor IRR — computed
- Distribution (post-senior, post-DSRA, post-lockup gate) — computed
- Distribution Account engine (DA) — domain module exists, wired as dual-run audit only
- Offline financial statements (P&L, BS, PF cash waterfall) — computed by `assemble_financial_statements()`
- Scenarios (save, compare, matrix run) — fully wired
- Export (CSV runtime summary, XLSX institutional workbook, values-only Excel) — genuine

### What is missing (engine gap or UI-to-engine gap)

- **FS UI connection**: `assemble_financial_statements()` output never reaches any UI tab; Financial Statements tab shows the "not-yet-connected" panel
- **Distribution UI connection**: Distribution tab shows "not-yet-connected" panel; per-period distribution figures from `WaterfallResult.periods` are not rendered per-period in the UI
- **Sponsor / LP–GP waterfall**: Domain module (`domain/sponsor/`) exists and computes sponsor IRR/MOIC; LP/GP promote/waterfall tiers exist; but the Sponsor tab shows "not-yet-connected" panel
- **Senior Debt per-period schedule**: Engine computes full schedule (principal, interest, DSCR per period); the UI shows only top-level KPIs, not the period schedule
- **Tax per-period schedule**: Engine computes CIT accrual, cash tax, loss carry-forward per period; the UI shows only CIT rate and loss carry-forward years as inputs
- **Construction draw schedule**: Engine computes IDC and spending profile but does not expose a construction-period draw table to the UI
- **Balance Sheet in UI**: `assemble_financial_statements().balance_sheet` is computed; not surfaced in the UI
- **Retained earnings / legal reserve**: Computed inside PnL assembly; not surfaced in UI
- **Generic project parity**: TUHO (wind, Croatia) and Oborovo (solar, Croatia) have fixture-backed validation; generic solar/wind have partial validation only
- **Monte Carlo / sensitivity**: `domain/analytics/monte_carlo.py` and `domain/finance/sensitivity.py` exist; not wired to a UI surface
- **BESS/hybrid**: `domain/analytics/bess.py` exists; partial wiring

---

## Stack A — Module Parity Classification

| Module | Engine Status | UI Status | Parity Classification |
|--------|--------------|-----------|----------------------|
| **CAPEX** | Fully computed: total, IDC, bank fees, commitment fees, per-asset-class items, spending profiles | Editable grid (C1 migration done); KPIs surface post-run | **Near parity** — total matches; per-asset-class depreciation lives wired behind flag; construction draw table not in UI |
| **Construction / IDC** | `domain/construction/` computes construction schedule, IDC by period, funding allocation. Flagged via `use_construction_schedule_engine`. | No UI tab; `sheet_idc.html` exists but has no wired tab or route | **Partial parity** — engine exists, UI not connected |
| **Revenue** | PPA + merchant curves + CO2 bridge + BESS computed per period. Degradation, curtailment, P90/P50 variants. | Editable grid live; revenue KPI surfaces post-run | **Near parity** — formula path is correct; CO2 bridge is TUHO-only behind a flag |
| **OPEX** | Per-period computed. Line-item engine (`use_opex_line_item_engine`) and legacy path. Escalation via HICP. | Editable grid live; total OPEX surfaces post-run | **Near parity** — TUHO/Oborovo templates validated; generic escalation simplified |
| **Senior Debt** | Full DSCR sculpting (iterative + closed-form), senior balance, principal, interest, DSCR, LLCR, PLCR, frozen-fixture path (TUHO + Oborovo) | Top-level KPIs surface post-run; period schedule: "not-yet-connected" panel | **Near parity** — KPIs correct; period schedule not in UI |
| **Tax** | Basic CIT (rate × taxable profit). Loss carry-forward (5-yr Croatia). ATAD 30%-EBITDA interest limitation (TUHO). Fiscal reintegration (TUHO). Cash-tax H2 timing. Tax bridge behind `use_tax_bridge_engine` flag | Inputs (CIT rate, loss carry-forward years) live; output schedule: "not-yet-connected" panel | **Partial parity** — basic CIT correct; ATAD / interest limitation TUHO-only and flag-gated; WHT on SHL in SHL engine but not in Tax tab |
| **Financial Statements (P&L)** | `domain/financial_statements/pnl.py` assembles a full PnL (EBIT → EBT → CIT → net income → retained earnings). Export uses it. | UI tab shows "not-yet-connected" panel | **Partial parity** — engine computes correctly (parity tests pass for TUHO/Oborovo); not connected to UI |
| **Financial Statements (Balance Sheet)** | `domain/financial_statements/balance_sheet.py` assembles full BS (fixed assets, DSRA, cash, equity, debt) | UI tab shows "not-yet-connected" panel | **Partial parity** — computed; not connected to UI |
| **Financial Statements (PF Cash Waterfall)** | `domain/financial_statements/pf_cash_waterfall.py` assembles the project-finance cash waterfall (EBITDA → FCF for banks → FCF for junior → distribution) | Export only; not in UI | **Partial parity** — computed; not connected to UI |
| **Distribution** | Waterfall engine computes `distribution_keur` per period (post-lockup, post-sweep). Distribution Account (`domain/distribution_account/`) is a separate domain module, wired as dual-run audit only (flag `use_distributionaccount_runtime_wiring` blocked at G20/R99/R102 gate). | UI tab shows "not-yet-connected" panel | **Partial parity** — amounts computed by waterfall; DA engine exists but governance-blocked; period schedule not in UI |
| **Sponsor / LP–GP Waterfall** | `domain/sponsor/` has sponsor IRR, MOIC, cashflow runner, multi-investor waterfall, promote tiers, preferred return. `sponsor_irr` surfaces in WaterfallResult. | UI tab shows "not-yet-connected" panel | **Partial parity** — engine computes sponsor IRR; LP/GP waterfall tiers exist; not connected to UI Sponsor tab |
| **Scenarios** | Scenario save/load/compare/matrix-run wired; override model; scenario-level IRR/DSCR from real runs | Fully wired; Scenarios tab and Compare tab are honest | **Near parity** — functional; no sensitivity-range automation (manual override only) |
| **Compare** | `app/services/compare_service.py` orchestrates comparison of two project runs | Compare tab wired; base-vs-active and pair-compare modes | **Near parity** — functional; no delta waterfall breakdown per line item |
| **Export** | Three surfaces: CSV runtime summary, XLSX institutional workbook (includes FS via `assemble_financial_statements`), values-only Excel | All three wired; sheets are genuine | **Near parity** — FS export works; UI-side FS tab still disconnected |
| **Construction draw schedule (UI)** | `domain/construction/` computes construction period cash, IDC by period | No UI tab; `sheet_idc.html` dead partial | **Not implemented** (UI surface) |
| **Monte Carlo / Sensitivity** | `domain/analytics/monte_carlo.py`, `domain/finance/sensitivity.py` exist | No UI surface | **Not implemented** (UI surface) |
| **BESS / Hybrid** | `domain/analytics/bess.py`, `domain/revenue/bess.py` exist; BessParams in inputs | No dedicated BESS UI tab | **Partial parity** — revenue BESS model exists; no UI |

---

## Stack B — Formula Inventory

### Implemented (confirmed in engine)

| Formula | Location | Notes |
|---------|----------|-------|
| EBITDA = Revenue − OPEX | `waterfall_engine.py` | Per-period, no floor below 0 |
| Senior debt sizing — DSCR sculpt | `domain/financing/sculpting_iterative.py` | Iterative + closed-form; DSCR schedule support |
| Senior debt sizing — fixed debt | `waterfall_engine.py` `fixed_debt_keur` path | Override path for P90-sized scenarios |
| DSRA rolling target = 6-month forward DS | `domain/financing/sculpting_iterative.py::dsra_rolling_target` | 6-month default |
| IDC = ∫ outstanding_debt × rate × day_fraction | `domain/capex/idc.py` | Monthly construction draw |
| Depreciation — straight-line (legacy) | `domain/financing/depreciation_schedule.py` | Per CapexItem asset class |
| Depreciation — canonical (per-asset-class) | `domain/depreciation/` | Behind `use_depreciation_canonical_engine` flag |
| Tax = taxable_profit_after_losses × tax_rate | `domain/waterfall/tax_engine.py` | Basic CIT |
| Loss carry-forward (Croatia 5-yr) | `domain/tax/loss_carryforward.py` | Rolling buckets with expiry |
| ATAD 30%-EBITDA interest limitation | `domain/tax/interest_limitation.py` | TUHO-only, flag-gated |
| LLCR = PV(FCF to maturity) / senior_balance | `waterfall_engine.py::compute_llcr` | Forward-looking |
| PLCR = PV(FCF to project end) / senior_balance | `waterfall_engine.py::compute_plcr` | Full horizon |
| SHL PIK capitalisation | `domain/waterfall/shl_engine.py` | Multiple repayment methods |
| WHT on SHL interest | `domain/waterfall/shl_engine.py` | `shl_wht_rate` |
| Project IRR / XIRR | `domain/returns/xirr.py` | Actual dates |
| Equity IRR | `domain/returns/xirr.py` | Equity-only and share-capital methods |
| Sponsor IRR / MOIC | `domain/sponsor/sponsor_irr_runner.py` | Computed from sponsor cashflows |
| Revenue degradation | `domain/revenue/generation.py` | Linear annual |
| CO2 certificate revenue | `domain/revenue/` | TUHO-only, `use_co2_revenue_bridge` flag |
| DSCR lockup gate (< 1.10 blocks distribution) | `waterfall_engine.py` | Per-period lockup check |
| Cash sweep to senior debt | `domain/financing/sculpting_iterative.py::cash_sweep` | Post-distribution |
| PF Cash Waterfall (EBITDA → FCF banks → FCF junior → dividends) | `domain/financial_statements/pf_cash_waterfall.py` | Offline assembly |
| P&L (revenues → EBIT → EBT → CIT → net income → retained earnings) | `domain/financial_statements/pnl.py` | Offline assembly |
| Balance Sheet (fixed assets, DSRA, equity, SHL, senior debt) | `domain/financial_statements/balance_sheet.py` | Offline assembly |

### Intentionally simplified / known deviations

| Item | Current behaviour | Excel behaviour | Gap |
|------|------------------|----------------|-----|
| CIT cash timing | H2-only annual pairing `-(H1_tax + H2_tax)` paid in H2 | Same for TUHO; Oborovo may differ | Minor timing difference for Oborovo; no regression test for Oborovo cash-tax timing |
| Interest limitation (ATAD) | 30% × EBITDA threshold hard-coded; €3 000 kEUR floor | Same formula; TUHO fixture-backed | ATAD not parameterised for non-TUHO projects |
| Depreciation tax basis | Legacy: same as book; canonical engine: separate book/tax per-asset-class | Excel has separate P&L and fiscal depreciation lives | Canonical engine correct but flagged behind `use_depreciation_canonical_engine` |
| SHL gross-accrued interest (P&L) | Uses period formula by default; TUHO has fixture-backed R27 extraction | R27 = gross accrual, not cash | Non-TUHO projects use formula approximation |
| Construction-period loss | Opening loss bucket modelled as near-expiry single bucket | Excel tracks construction-year vintages separately | Cannot reproduce Excel pre-COD vintage exactly |
| Local taxes / property tax | 0.0 hard-coded | May appear in Oborovo/TUHO Excel as a small expense line | Not modelled |
| Interest income on reserves | 0.0 hard-coded (P&L R19/R20) | Excel may include DSRA interest income | Not modelled |
| Refinancing interest | 0.0 hard-coded (P&L R25) | Some Excel models include refinancing tranches | Out of scope |

### Missing / not yet implemented

| Formula | Excel location | Status |
|---------|---------------|--------|
| Full WHT schedule on dividends (investor-level) | Sponsor waterfall / dividend flow | Not in UI; `domain/sponsor/` computes but not surfaced |
| LP / GP promote / carried interest tiers | Sponsor waterfall tier | Domain module exists (`domain/sponsor/sponsor_waterfall_tier.py`); not wired to UI |
| DSCR ratio covenants (cash-trap, sweep ratio) | Debt covenants sheet | `domain/financing/covenants.py` exists; not verified in tests |
| Merchant price curve escalation | Revenue | Merchant curves basic; no multi-curve scenario |
| Equity contribution schedule (construction-period draws) | Construction funding allocation | `domain/construction/funding_allocation.py` exists; not surfaced in UI |
| Holdco tax / withholding tax overlay | HoldCo layer | `app/holdco_tax_ui.py`, `app/holdco_tax_excel_export.py` exist; not in main waterfall path |
| Portfolio aggregation | Portfolio runner | `domain/portfolio/` exists; not wired to scenario-level UI |

---

## Stack C — Validation Inventory

### Existing golden / parity tests

| Test file | Scope | Status |
|-----------|-------|--------|
| `tests/test_oborovo_parity.py` | Oborovo baseline inputs + financing KPIs | **2 pre-existing failures** (SHL amount, total equity+SHL); remaining 12 tests pass |
| `tests/test_phase23u_full_excel_parity_pack.py` | TUHO + Oborovo senior DS, DSCR trajectory, lockup-distribution parity | All 8 tests pass |
| `tests/test_phase9_final_tuho_parity_closeout_review.py` | TUHO period-level R69/R84/R99/R102 closeout review | Passes |
| `tests/test_phase9_tuho_full_semester_horizontal_parity_workbook.py` | TUHO semester-by-semester horizontal parity | Passes |
| `tests/test_phase9_tuho_full_line_item_parity_pack.py` | TUHO per-line-item parity pack | Passes |
| `tests/test_financial_statements_tuho_pnl_parity.py` | TUHO P&L offline assembly parity | Passes |
| `tests/test_financial_statements_oborovo_pnl_parity.py` | Oborovo P&L offline assembly parity | Passes |
| `tests/test_phase23n_oborovo_post_correction_parity_snapshot.py` | Oborovo post-correction snapshot | Passes |
| `tests/test_phase23p_oborovo_post_lockup_parity_snapshot.py` | Oborovo post-lockup snapshot | Passes |
| `tests/test_phase23o_oborovo_distribution_lockup_policy_parity.py` | Oborovo distribution lockup policy | Passes |
| `tests/test_phase_c4_construction_parity_snapshots.py` | Construction schedule parity snapshots | Passes |
| `tests/test_g1b_generic_anchor_parity.py` | Generic solar/wind anchor parity | Passes |
| `tests/test_phase_stab7_generic_dashboard_parity.py` | Generic dashboard KPIs parity | Passes |
| `tests/test_cache_parity.py` | Cache vs uncached run identity | Passes |

### Known pre-existing test failures (baseline, not regressions)

| Test | File | Reason |
|------|------|--------|
| `test_shl_amount` | `test_oborovo_parity.py` | Oborovo SHL amount in factory (14,621 kEUR) differs from Excel expected (13,547 kEUR); delta ~1,074 kEUR — known calibration gap |
| `test_total_equity_shl` | `test_oborovo_parity.py` | Follows from SHL amount gap above |
| `test_no_recalculation_formula_dependency_or_saverun_code_in_live_model` | `test_c2_pr1_live_model.py` | Governance test for C2-PR1 live model static wiring — pre-existing |

### Missing validation coverage

| Area | Gap | Priority |
|------|-----|----------|
| Oborovo SHL calibration | SHL amount factory default does not match Excel (1,074 kEUR gap); no corrected-value test | High |
| Generic project parity | Generic solar and wind projects have KPI-level anchor tests only; no period-level parity against a reference Excel | Medium |
| Financial Statements UI round-trip | `assemble_financial_statements()` is tested offline; no test that the export XLSX actually matches the offline-assembled FS values | Medium |
| Distribution Account full validation | DA engine has unit tests; no test that confirms DA output equals Excel-validated distribution schedule for TUHO/Oborovo | High |
| Sponsor / LP–GP waterfall output | Sponsor IRR is computed (result.sponsor_irr); no test that sponsor IRR matches Excel sponsor waterfall | Medium |
| Balance sheet identity (Assets = Liabilities + Equity) | `max_abs_balance_check_keur` property exists; no test asserting it is near-zero for TUHO/Oborovo | Medium |
| Tax cash timing (Oborovo) | TUHO cash-tax H2 pairing validated; Oborovo cash-tax timing against Excel not validated | Medium |
| ATAD interest limitation (generic projects) | ATAD is TUHO-only behind a flag; no test that non-TUHO projects without the flag produce correct un-limited CIT | Low |
| Construction draw schedule (period-level) | Construction schedule engine has unit tests; no parity test against Excel construction tab | Low |
| LLCR / PLCR trajectory | DSCR trajectory tested; LLCR/PLCR period trajectory not tested | Low |

---

## Stack D — Remaining Blockers (Prioritised)

### Critical

| # | Item | Impact | Complexity | Dependency | Est. PR size |
|---|------|--------|------------|------------|-------------|
| D1 | **Connect Financial Statements to UI** — wire `assemble_financial_statements(runtime_result)` into the post-run response payload and render the P&L, BS, and PF cash waterfall on the FS tab | Users cannot see P&L/BS/CF from the UI; Export has it but the tab shows "not-yet-connected" | Medium — offline assembly already exists; needs a Jinja template and a payload key | Requires post-`/run` payload extension and template rebuild | 1 focused PR |
| D2 | **Oborovo SHL calibration** — fix the SHL amount factory default (14,621 vs 13,547 kEUR) and restore the 2 currently-failing parity tests | Two known test failures persist from pre-existing calibration gap | Small — factory value change + test value update | None; standalone fix | Small PR |

### High

| # | Item | Impact | Complexity | Dependency | Est. PR size |
|---|------|--------|------------|------------|-------------|
| D3 | **Connect Distribution tab to per-period distribution** — render `WaterfallResult.periods[i].distribution_keur` as a period schedule in the Distribution UI tab | Distribution tab shows "not-yet-connected" panel despite engine computing values | Medium — Jinja template + payload key; no engine change | Post-`/run` payload extension; D1 pattern reusable | 1 PR |
| D4 | **Connect Senior Debt per-period schedule to UI** — render principal, interest, DSCR, LLCR per period in the Senior Debt tab | Engine computes all values; users see only top-level KPIs | Medium — template + payload; same pattern as D1/D3 | Post-`/run` payload extension | 1 PR |
| D5 | **Connect Tax per-period schedule to UI** — render CIT accrual, cash tax, taxable income, loss carry-forward per period in Tax tab | Tax tab shows only CIT rate and loss carry-forward inputs; no per-period output | Medium — template + payload | Post-`/run` payload extension; tax bridge already assembled | 1 PR |
| D6 | **Distribution Account runtime promotion** — promote `use_distributionaccount_runtime_wiring` out of G20/R99/R102 governance block for validated projects | DA engine is fully implemented and dual-run validated; governance gate blocks production use | Low engine complexity; governance process complexity | G20 / R99/R102 approval process | Governance + 1 small wiring PR |

### Medium

| # | Item | Impact | Complexity | Dependency | Est. PR size |
|---|------|--------|------------|------------|-------------|
| D7 | **Connect Sponsor tab** — wire `domain/sponsor/` sponsor IRR/MOIC + LP/GP waterfall into the Sponsor UI tab | Sponsor tab shows "not-yet-connected" panel; engine computes sponsor IRR already | Medium — new template section; LP/GP tiers need UI design | D3 (distribution values feed sponsor cashflows) | 1 PR |
| D8 | **Balance Sheet identity test** — add a regression test asserting `max_abs_balance_check_keur < 1.0` for TUHO and Oborovo | Ensures balance sheet closure; currently no test | Small | None | Characterization test only |
| D9 | **Generic project period-level parity** — build a reference Excel for a generic solar/wind project and add period-level parity tests | Generic projects have KPI-level tests only; no period-level validation | Medium — requires reference Excel fixture | None | 1 PR (fixture + tests) |
| D10 | **Construction draw schedule UI tab** — wire `sheet_idc.html` to a real route and render per-period construction draws | Dead partial exists; no UI surface for construction schedule | Medium — route wiring + template population | `use_construction_schedule_engine` flag must be default-on | 1 PR |

### Low

| # | Item | Impact | Complexity | Dependency | Est. PR size |
|---|------|--------|------------|------------|-------------|
| D11 | **ATAD parameterisation** — make 30%-EBITDA cap and €3,000 kEUR floor configurable per project (not hard-coded) | Affects non-TUHO projects when ATAD applies | Small | None | Small PR |
| D12 | **Interest income on reserves** — model DSRA interest income in P&L (currently 0.0) | Minor P&L line; low materiality for large projects | Small | None | Small PR |
| D13 | **Local tax / property tax** — add a property-tax line item to OPEX/P&L | Very minor; <0.5% of revenue for typical projects | Small | None | Small PR |
| D14 | **Monte Carlo / Sensitivity UI** — wire `domain/analytics/monte_carlo.py` to a UI surface | Domain module exists; no UI | High complexity — UI design required | None | Large PR |
| D15 | **Portfolio UI** — wire `domain/portfolio/` aggregation to a portfolio-level view | Domain module exists; no UI | High complexity | D3/D4/D5 | Large PR |
| D16 | **HoldCo tax overlay** — wire `app/holdco_tax_ui.py` into the main waterfall path | HoldCo module exists as standalone; not integrated | Medium | D5 (tax) | 1 PR |

---

## Stack E — Recommended Implementation Order

### Rationale

Prefer: highest user-visible value / reuses existing engine work / smallest PR surface / no financial-logic risk.

### Tier 1 — Connect existing engines to UI (no engine changes, templates only)

1. **D2 — Oborovo SHL calibration** (Small, isolated, fixes 2 known test failures immediately)
2. **D1 — Financial Statements UI connection** (Highest user value; engine already assembles all three statements; template + payload work only)
3. **D4 — Senior Debt per-period schedule UI** (Users ask for debt schedule; all values computed; template work)
4. **D5 — Tax per-period schedule UI** (Pairs with D1; tax bridge already assembled alongside P&L)
5. **D3 — Distribution tab per-period schedule** (Distribution amounts computed; template work)

### Tier 2 — Wire domain modules to UI (domain modules ready; governance or UI design needed)

6. **D6 — Distribution Account runtime promotion** (Governance process; existing dual-run validation proves correctness)
7. **D7 — Sponsor tab** (Engine ready; LP/GP tiers need UI design decisions)
8. **D8 — Balance Sheet identity test** (Quick characterization test; no code change)
9. **D10 — Construction draw schedule UI** (Dead partial already exists; route wiring work)

### Tier 3 — New features (new engine work or complex UI)

10. **D9 — Generic project period-level parity** (Needs reference Excel fixture; medium effort)
11. **D11/D12/D13 — ATAD parameterisation, interest income, local tax** (Minor P&L accuracy improvements)
12. **D16 — HoldCo tax overlay** (Useful for multi-jurisdiction structures)
13. **D14 — Monte Carlo/Sensitivity UI** (Large effort; high value for underwriting workflows)
14. **D15 — Portfolio UI** (Large effort; multi-project use case)

---

## Guardrail confirmation

This PR contains only:
- `docs/EXCEL_PARITY_GAP_INVENTORY.md` (this file)
- `tests/test_excel_parity_characterization.py` (characterization tests, no financial logic)

No changes were made to:
- `domain/` (any file)
- `app/waterfall_core.py`
- `app/input_adapter.py`
- `app/project_factories.py`
- Any financial formula, Run logic, Save logic, or persistence code

`git diff main --stat` will show only these two new files.
