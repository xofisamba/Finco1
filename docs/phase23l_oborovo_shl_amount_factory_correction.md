# Phase 23L: Oborovo SHL Amount Factory Correction

**Type:** Factory configuration correction — no runtime waterfall changes

**Base SHA:** `ed843477175b5ef1a18e1c7a209054c35fddbc09` (after PR #308 merge)
**Branch:** `phase23l-oborovo-shl-amount-factory-correction`

---

## Context

| PR | Title | Status |
|---|---|---|
| #303/23F | TUHO factory frozen senior DS opt-in | Merged |
| #304/23H | Oborovo SHL/distribution lock-up guard (2-tier bug fix) | Merged |
| #306/23J | Oborovo shl_tenor_years 0→20 (20-year bullet alignment) | Merged |
| #308/23K | Oborovo SHL opening balance bridge (diagnostic) | Merged |

**Phase 23K diagnostic conclusion:**
- SHL draw gap: Python 13,547.2 vs Excel 14,621 kEUR — gap = ~1,074 kEUR
- SHL IDC gap: Python 1,169.0 vs Excel 1,170 kEUR — gap ≈ 0
- **Root cause:** factory `shl_amount_keur` understated by ~1,074 kEUR
- **Fix:** change Oborovo `shl_amount_keur` from `13,547.2` → `14,621.0`

---

## Exact Config Change

**File:** `app/project_factories.py` — `create_default_oborovo()` → `FinancingParams`

```
Before: shl_amount_keur=13547.2
After:  shl_amount_keur=14621.0  # Excel SHL draw (from construction template shl_keur=14,620.774)
```

**Unchanged:**
- `shl_idc_keur=1169.0` (IDC matches Excel — no gap)
- `shl_rate=0.08`
- `shl_tenor_years=20` (PR #306/23J)
- `senior_tenor_years=14`
- `use_frozen_excel_senior_debt_schedule=False`
- `use_senior_debt_sizing_engine=False`

---

## Opening SHL Bridge

| Component | Before (23L) | After (23L) | Excel Target | Delta (after vs Excel) |
|---|---|---|---|---|
| SHL draw/principal | **13,547.2 kEUR** | **14,621.0 kEUR** | **14,621 kEUR** | **0 kEUR ≈ 0** |
| SHL IDC | 1,169.0 kEUR | 1,169.0 kEUR | 1,170 kEUR | −1 kEUR ≈ 0 |
| **Opening total** | **14,716.2 kEUR** | **15,790.0 kEUR** | **15,791 kEUR** | **−1 kEUR ≈ 0** |

**Source of Excel target:**
- `domain/construction/templates/oborovo.py`: `shl_keur=14,620.774` (rounded to 14,621)
- `app/project_factories.py` comment: "opening SHL balance = 14,621 + 1,169 = 15,790"

---

## Distribution Timing — No Regression of PR #304/23H + PR #306/23J

| Period | Date | SHL Balance | SHL Service | Distribution | Notes |
|---|---|---|---|---|---|
| Op[37] | 2049-06-30 | 15,790.0 | 583.81 | ~2,362 kEUR | Normal period |
| Op[38] | 2049-12-31 | **0.00** | **16,373.81** | **0.00** | SHL final period (bullet) — PR #304 guard blocks |
| Op[39] | 2050-06-30 | 0.00 | 0.00 | **2,994 kEUR** | First distribution after SHL cleared ✓ |
| Op[40] | 2050-12-31 | 0.00 | 0.00 | 3,333 kEUR | |

**PR #304 guard logic:** At op[38], `shl_svc = 15,790 (principal) + 583 (interest) ≈ 16,374 kEUR` >> `fcf_for_shl ≈ 3,278 kEUR` → distribution = 0 ✓

---

## TUHO Regression — Flags Unchanged

| Flag | TUHO Value | Source |
|---|---|---|
| `use_frozen_excel_senior_debt_schedule` | **True** | PR #303 opt-in |
| `use_senior_debt_sizing_engine` | **True** | PR #303 opt-in |
| SHL fixture-backed frozen path | **Still loads** | No change |

---

## Guardrail Table

| Guardrail | Status |
|---|---|
| G20 BLOCKED | ✓ Untouched |
| R99/R102 NOT APPROVED | ✓ Untouched |
| Oborovo frozen schedule NOT enabled | ✓ `use_frozen_excel_senior_debt_schedule=False` |
| TUHO factory flags unchanged | ✓ PR #303 preserved |
| No Revenue/OPEX/CAPEX/Tax change | ✓ Factory only |
| No SHL/distribution waterfall change | ✓ |
| `partial_pay_sweep` NOT promoted | ✓ Opt-in only |
| Sculpting solver NOT promoted | ✓ |
| C.16 / M1–M18 IDC NOT wired | ✓ |
| PR #299 remains draft / superseded | ✓ |

---

## Known Limitations

1. **Factory config correction, not full construction funding runtime** — opening SHL is set directly, not derived from construction schedule draw timing
2. **Oborovo frozen senior DS fixture still not implemented** — TUHO has one; Oborovo does not
3. **No broader CAPEX/IDC treatment wiring** — IDC field exists but construction-period funding is not modeled
4. **SHL draw timing assumed at COD** — actual Excel may show draw over multiple construction periods; not modeled

---

## Test Results

```
tests/test_phase23l_oborovo_shl_amount_factory_correction.py  6 passed
tests/test_phase23h_oborovo_shl_distribution_lockup_fix.py      6 passed
tests/test_phase23f_tuho_frozen_factory_opt_in_candidate.py    84 passed
tests/test_phase23e_shl_distribution_lockup_fixture_backed_ds  passed
tests/test_phase23d_prep_tuho_fixture_backed_frozen_senior_ds  passed
tests/test_phase23c_shl_distribution_lockup_review_frozen       passed
tests/test_phase23a_frozen_excel_senior_debt_schedule_wiring   passed
tests/test_shl_waterfall_priority.py                            42 passed, 2 xfailed, 1 xpassed
tests/test_tuho_shl_calibration.py                             passed
tests/test_revenue.py                                          passed
tests/test_opex.py                                            passed
```

**138 passed, 2 xfailed, 1 xpassed**

Note: Phase 23K diagnostic tests (test_oborovo_current_shl_opening_balance_documents_gap,
test_oborovo_shl_component_bridge) fail because they tested for the OLD (incorrect)
shl_amount=13,547.2 kEUR. Those tests are superseded by this correction — they
documented the gap that this PR closes.