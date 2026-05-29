# Phase 23Q: Oborovo Frozen Senior DS Fixture Extraction

**Type:** Fixture extraction + parity proof
**Base SHA:** `612e911c9e22bdebba76ee4e8b553cea41b8de3f` (after PR #315)
**Branch:** `phase23q-oborovo-frozen-senior-ds-fixture-extraction`

---

## PR #299 Status

Draft / not merged / superseded. Oborovo frozen schedule factory opt-in BLOCKED pending Phase 23Q parity proof.

---

## Phase 23H/J/L/O/P Summary

| Phase | PR | Fix |
|---|---|---|
| 23H | #307 | SHL/distribution shortfall guard |
| 23J | #308 | shl_tenor_years corrected to 20 |
| 23L | #309 | shl_amount_keur corrected to 14,621.0 |
| 23O | #314 | Bullet SHL distribution lock-up |
| 23P | #315 | Post-lockup diagnostic, mismatch=0 |

---

## Fixture Source

**File:** `reports/phase23q_oborovo_senior_debt_sizing_extraction.csv`
**Source:** Oborovo Excel DS sheet, rows 7-49, cols H-@W
**Anchors:** Debt=42,852 kEUR, repaid period 27 (2044-06-30), DSCR=1.15 (0-24), 1.35 (25-27)

---

## Senior DS Parity (Selected)

| Op# | Date | Fixture DS | Runtime DS | OK |
|---|---|---|---|---|
| 0 | 2030-12-31 | 2,239.13 | 2,239.13 | ✅ |
| 1 | 2031-06-30 | 2,202.63 | 2,202.63 | ✅ |
| 14 | 2037-12-31 | 2,471.54 | 2,471.54 | ✅ |
| 25 | 2043-06-30 | 1,558.40 | 1,558.40 | ✅ |
| 27 | 2044-06-30 | 1,507.44 | 1,507.44 | ✅ |
| 28 | 2044-12-31 | 0.00 | 0.00 | ✅ |

---

## Lock-up Regression (Phase 23O Intact)

- No distributions while SHL outstanding ✅
- First post-SHL dist: op_idx 39 (2050-06-30), ~2,994 kEUR ✅
- Phase 23N blocker resolved ✅

---

## TUHO Regression

| Check | Result |
|---|---|
| TUHO frozen=True / sizing=True | ✅ unchanged |
| TUHO fixture still loads | ✅ |

---

## Factory Opt-in Statement

**Oborovo factory opt-in remains BLOCKED.** Explicit test/control runs only.

---

## Known Limitations

- No factory opt-in | No sculpting solver | No construction IDC
- No CAPEX/M1-M18 wiring | No bankability claims
- G20 BLOCKED | R99/R102 NOT APPROVED
