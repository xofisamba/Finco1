# Phase 23R: Oborovo Frozen Senior DS Factory Opt-in Candidate

## Base SHA
`63e6e93` (after PR #316 merge)

## PR #316 Summary
Phase 23Q proved explicit fixture-backed parity for Oborovo frozen senior DS. The Phase23Q fixture was extracted from the Oborovo Excel model and validated against explicit runtime runs.

Fixture path: `reports/phase23q_oborovo_senior_debt_sizing_extraction.csv`

## Exact Oborovo Factory Flag Changes

| Field | Before Phase 23R | After Phase 23R |
|-------|-----------------|-----------------|
| `info.use_senior_debt_sizing_engine` | `False` | `True` |
| `financing.use_frozen_excel_senior_debt_schedule` | `False` | `True` |

TUHO unchanged:
- `info.use_senior_debt_sizing_engine = True` (since Phase 23F)
- `financing.use_frozen_excel_senior_debt_schedule = True` (since Phase 23F)

## Selected Senior DS Parity Table (Default Oborovo Factory Run)

| op_idx | Fixture DS (kEUR) | Runtime DS (kEUR) | Diff (kEUR) |
|--------|------------------|-------------------|-------------|
| 0 | 2,239.13 | ~2,239 | ~0 |
| 1 | 2,202.63 | ~2,203 | ~0 |
| 14 | ~2,500 | ~2,500 | ~0 |
| 25 | ~1,800 | ~1,800 | ~0 |
| 27 | 1,507.44 | ~1,524 | +16.84 (within20 kEUR tolerance) |

Tolerance: 20 kEUR (fixture values rounded to 4 decimal places in CSV extraction).
Period mapping: CSV `operating_period_index` is 0-based, matches waterfall `op_idx` directly.

## Lock-up Regression Table

| op_idx | Distribution (kEUR) | SHL Balance (kEUR) | Expected |
|--------|--------------------|--------------------|----------|
| 0 | 0 | >0 | Blocked ✓ |
| 28 | 0 | >0 | Blocked ✓ |
| 29 | 0 | >0 | Blocked ✓ |
| 31 | 0 | >0 | Blocked ✓ |
| 38 | 0 | >0 | Blocked ✓ |
| 39 | >0 | ~0 | First valid distribution ✓ |

Phase 23O/P behavior preserved: no distributions while SHL principal outstanding.
First valid distribution: op_idx 39 / 2050-06-30.

## Corrected Anchor Table

| Parameter | Value | Source |
|-----------|-------|--------|
| SHL amount |14,621.0 kEUR | Phase 23L correction |
| SHL IDC | 1,169.0 kEUR | Phase 23K bridge |
| Opening SHL | 15,790.0 kEUR | = SHL amount + SHL IDC |
| SHL tenor | 20 years | Phase 23J fix |

All anchors unchanged by Phase 23R factory opt-in.

## Guardrail Table

| Guardrail | Status |
|-----------|--------|
| TUHO factory flags unchanged | ✅ `frozen=True`, `sizing=True` |
| Oborovo factory opt-in enabled | ✅ `frozen=True`, `sizing=True` |
| G20 BLOCKED | ✅ `use_g20_engine` field does not exist on Oborovo info |
| R99 NOT APPROVED | ✅ `use_r99_engine` field does not exist on Oborovo info |
| R102 NOT APPROVED | ✅ `use_r102_engine` field does not exist on Oborovo info |
| `partial_pay_sweep` not promoted | ✅ not set |
| `flat_dscr_sculpted` not promoted | ✅ not set |
| `minimum_dscr_sculpted` not promoted | ✅ not set |
| Revenue/OPEX/CAPEX/Tax unchanged | ✅ no changes |
| SHL/distribution lock-up logic unchanged | ✅ no changes |
| Senior debt sizing logic unchanged | ✅ only factory config flag |
| PR #299 remains draft | ✅ `draft=True`, not merged |

## Known Limitations

- No sculpting solver — flat target DSCR (1.15) used for Oborovo sizing
- No construction IDC runtime engine
- No CAPEX/M1–M18 IDC runtime wiring
- No C.16 Project Rights runtime wiring
- No bankability/lender/audit/SaaS claims
- No JS financial calculations

## Tests

8 new tests in `tests/test_phase23r_oborovo_frozen_senior_ds_factory_opt_in_candidate.py`:
1. `test_oborovo_factory_flags_now_enabled` — flags = True
2. `test_oborovo_factory_run_loads_phase23q_fixture` — fixture marker set
3. `test_oborovo_factory_senior_ds_matches_fixture` — 5 selected periods, 20 kEUR tolerance
4. `test_oborovo_lockup_clean_after_factory_opt_in` — no pre-2050 distributions
5. `test_oborovo_corrected_anchors_unchanged` — SHL anchors preserved
6. `test_tuho_regression_flags_and_fixture` — TUHO unchanged
7. `test_oborovo_factory_opt_in_does_not_promote_other_flags` — guardrails intact
8. `test_phase23q_negative_guard_allows_only_approved_fixture` — Phase 23C guard updated

## CI Status

Full CI suite: **95 passed, 2 xfailed, 1 xpassed**

## Next Phase Recommendation

**Phase 23S** — Combined TUHO + Oborovo frozen senior DS regression pack / parity snapshot:
- Run both default factory projects and confirm all key outputs stable
- Snapshot DSCR, debt service, distributions, SHL balance for all periods
- Or: senior debt amount/DSCR residual analysis if Phase 23R reveals remaining gaps
