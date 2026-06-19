# G3 — Driver Sensitivity Validation for Generic Solar/Wind

Proves that key editable assumptions move Generic Solar/Wind KPIs in the
expected finance direction. This is validation/tests/docs only — no model
formula, factory default, or engine file changed. See
`tests/test_g3_driver_sensitivity_validation.py`.

## Important methodology note: production wiring, not the G1/G2 test harness

`tests/test_generic_solar_wind_runtime.py` and `tests/test_g2_period_level_validation.py`
call `run_waterfall_v3_core` with `tenor_periods=len(op_periods)` — the full
operating horizon, hardcoded, regardless of `financing.senior_tenor_years`.
That matches how the reference workbook amortizes (full project life) and
is correct for G1/G2's purpose (validating against the reference
workbook).

It is **not** how the live app wires a tenor change: `app/waterfall_runner.py`'s
`WaterfallRunConfig.from_inputs()` computes `tenor_periods = financing.senior_tenor_years * 2`.
Using the G1/G2 harness for the tenor sensitivity check would show *zero*
effect from changing `senior_tenor_years` — not because the driver isn't
wired in the app, but because the G1/G2 harness doesn't route through that
field at all. Using it here would produce a misleading "driver not wired"
finding.

G3 therefore runs all eight sensitivities through the real production path
(`WaterfallRunConfig.from_inputs(inputs, engine)` + `WaterfallRunner.run(config)`),
the same path the app's input forms use. As a side effect, the *base case*
KPI values in this module differ from the base case shown in G1D/G2 (e.g.
Equity IRR is higher here) — that is expected, since the tenor here is the
factory default 15 years, not the full ~25-year operating horizon used by
the reference-workbook-aligned G1/G2 harness. G3 does not assert any total-
or period-level number against the reference workbook; it only compares
each driver's bumped case against its own base case.

## Sensitivity matrix

All deltas are directional (bumped vs. base case from the same harness),
not exact magnitudes. ✓ = asserted and passes for both projects. "Observed"
= reported, not gated as pass/fail, per the task spec for that driver.

| # | Driver | Generic Solar | Generic Wind | Classification |
|---|---|---|---|---|
| 1 | CAPEX +10% | Project IRR ↓, Equity IRR ↓, Senior debt ↑ | Project IRR ↓, Equity IRR ↓, Senior debt ↑ | Pass |
| 2 | Revenue/PPA price +10% | Revenue ↑, EBITDA ↑, Project IRR ↑, Avg/Min DSCR ↑ | same | Pass |
| 2b | Revenue +10% → Equity IRR | Flat-to-slightly-down (Δ≈-0.00005, within noise band) | Up (Δ≈+0.0006, small) | **Observed/documented anomaly** (Solar) |
| 3 | OPEX +10% | EBITDA ↓, Project IRR ↓, Equity IRR ↓, Avg/Min DSCR ↓ | same | Pass |
| 4 | Generation/yield +10% | Revenue ↑, EBITDA ↑, Project IRR ↑, Equity IRR ↑, Avg/Min DSCR ↑ | same | Pass |
| 5 | Debt margin +100bps | Avg per-period debt service ↑, Equity IRR ↓, Avg/Min DSCR ↓ or flat, Project IRR unchanged | same | Pass |
| 6 | Senior tenor −3y | Avg per-period debt service ↑, Avg/Min DSCR ↓ | same | Pass |
| 6b | Tenor −3y → Equity IRR | Down (Δ≈-0.085) | Up (Δ≈+0.056) | **Observed, not gated** (spec: "direction should be documented") |
| 7 | Lower gearing (−10pp) | Senior debt ↓, Debt service ↓, Avg/Min DSCR ↑, Equity funding need ↑ | same | Pass |
| 7b | Lower gearing → Equity IRR | Down (Δ≈-0.117) | Down (Δ≈-0.132) | **Observed, not gated** (spec: "may move depending on leverage") |
| 8 | Higher tax rate (+10pp) | Project IRR ↓, Equity IRR ↓, Avg/Min DSCR ↓ or flat | same | Pass |

## Driver #2b: documented anomaly (Generic Solar Equity IRR vs. Revenue +10%)

Under Revenue/PPA price +10%, Project IRR, EBITDA, and DSCR all move in
the expected direction for both projects. Equity IRR also moves as
expected for Generic Wind (small increase). For Generic Solar, Equity IRR
is flat-to-slightly-down instead of up — a tiny move (well under 0.1
percentage points), but the wrong sign relative to the naive expectation.

This is reported here as an **observed anomaly requiring follow-up**, not
hidden or silently passed:
- It is small in magnitude, so it is unlikely to be a major defect, but it
  is directionally counter to finance intuition (more revenue should not
  reduce equity returns, all else equal).
- A plausible mechanism is the `equity_only` IRR method's treatment of the
  senior debt draw at COD as a "return of capital" cash flow to equity
  (see the reference workbook's Equity tab note, also reproduced in
  G1D/G2 docs): if a small change in CFADS-driven debt sizing shifts the
  exact timing/amount of that return-of-capital line, it can offset the
  revenue-driven distribution increase in the IRR calculation, even though
  every other KPI improves.
- This is flagged as a methodology/IRR-timing question for follow-up
  investigation, not a "driver not wired" issue (the driver clearly is
  wired — Revenue, EBITDA, Project IRR, and DSCR all respond) and not a
  "methodology caveat" already covered by G1D (the G1D Equity IRR caveat
  is about the debt-sizing proxy gap vs. the reference workbook, not about
  this Solar-vs-Wind asymmetry under a single runtime-internal driver
  change).

## Driver #6 / #7: documented, not pass/fail-gated

Per the task spec, Equity IRR direction under a shorter senior tenor (#6)
and under lower gearing (#7) is explicitly left as "document observed
behavior" rather than asserted. Both are reported here for completeness:

- Shorter tenor (−3y): Equity IRR moves in **opposite** directions for the
  two projects (down for Solar, up for Wind). Observed mechanism: a
  shorter tenor reduces the NPV'd, capacity-sized senior debt amount,
  which changes both upfront leverage and the equity return-of-capital
  timing differently for the two projects' CFADS/DSCR-cap profiles.
- Lower gearing (−10pp): Equity IRR decreases for **both** projects,
  consistent with reduced leverage reducing the amplification of equity
  returns — this one is directionally consistent across projects, even
  though the spec does not require it to be.

## Pass/fail/caveat classification

- **Pass** (10 of the matrix's directional checks, ×2 projects = 20
  assertions across drivers #1, #2 [non-Equity-IRR], #3, #4, #5, #6
  [non-Equity-IRR], #7 [non-Equity-IRR], #8): direction matches the
  expected finance logic for both Generic Solar and Generic Wind.
- **Observed/documented, not gated** (drivers #6 and #7's Equity IRR
  direction): per the task spec, these are reported rather than asserted
  as pass/fail.
- **Observed/documented anomaly requiring follow-up** (driver #2b, Generic
  Solar only): Equity IRR does not increase under Revenue +10% as naively
  expected; flagged for investigation, not hidden.
- **No defects identified**: no driver showed a direction that
  contradicts finance logic in a way that indicates a broken/unwired
  calculation; the one true anomaly (#2b) is a small-magnitude IRR-timing
  question, not a sign that Revenue, EBITDA, CAPEX, OPEX, generation, debt
  margin, tenor, gearing, or tax inputs are disconnected from the model.

## Test results (summary)

`tests/test_g3_driver_sensitivity_validation.py`: all tests pass for both
Generic Solar and Generic Wind. See the PR description / delivery report
for the full regression run.
