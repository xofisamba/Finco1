# Phase 7H O3b — TUHO OPEX Template Mapping

## Status

**Parity achieved.** All 30 years match Excel exactly within ±0.01 kEUR tolerance.

---

## Parity Results

| Metric | Value |
|--------|-------|
| Max absolute annual delta | **0.00 kEUR** (all Y1–Y30) |
| Y1 delta | +0.00 |
| Y2 delta | +0.00 |
| Y7 delta | +0.00 |
| Y10 delta | +0.00 |
| Y13 delta | +0.00 |
| Y20 delta | +0.00 |
| Y30 delta | +0.00 |
| 30-year Excel total | **84,674.78 kEUR** |
| 30-year Engine total | **84,674.78 kEUR** |
| 30-year delta | **+0.00 kEUR** |
| Years with abs(delta) > 0.01 kEUR | **None** |

---

## Excel Annual OPEX Totals (row 105, cols F–AE)

| Year | Total (kEUR) |
|------|-------------|
| Y1 | 1,998.05 |
| Y2 | 2,029.83 |
| Y3 | 2,147.06 |
| Y4 | 2,180.13 |
| Y5 | 2,213.86 |
| Y6 | 2,378.01 |
| Y7 | 2,413.10 |
| Y8 | 2,448.90 |
| Y9 | 2,485.41 |
| Y10 | 2,522.65 |
| Y11 | 2,603.04 |
| Y12 | 2,641.79 |
| Y13 | 2,681.31 |
| Y14 | 2,721.62 |
| Y15 | 2,734.77 |
| Y16 | 2,827.03 |
| Y17 | 2,869.24 |
| Y18 | 2,912.29 |
| Y19 | 2,956.21 |
| Y20 | 3,001.00 |
| Y21 | 3,131.49 |
| Y22 | 3,178.09 |
| Y23 | 3,225.63 |
| Y24 | 3,274.11 |
| Y25 | 3,323.57 |
| Y26 | 3,450.33 |
| Y27 | 3,501.79 |
| Y28 | 3,554.27 |
| Y29 | 3,607.80 |
| Y30 | 3,662.40 |

---

## Template Structure

### Location

```
domain/opex/templates/tuho.py
tests/test_tuho_opex_template_mapping.py
```

### Builder function

```python
from domain.opex.templates.tuho import build_tuho_opex_template

groups = build_tuho_opex_template()  # -> list[OpexGroup]
result = compute_annual_opex(groups, years=30)
```

### Groups (B.01–B.13)

| Group | Items | Base (kEUR) | Inflation | Notes |
|-------|-------|-------------|-----------|-------|
| B.01 | 6 | 280.00 | 2% | Asset Mgmt, Op Mgmt, Performance, Inspections, Meteo, Bazefield |
| B.02 | 10 | — | — | B.02.1 = explicit schedule (no infl); group infl=0; other items item-level 2% |
| B.03 | 4 | 68.00 | 2% | Vegetation, Roads, Pest, Inspections |
| B.04 | 3 | 5.00 | 2% | Clean Panel/Blades, Water, Others |
| B.05 | 3 | 50.00 | 2% | Surveillance systems, patrols, others |
| B.06 | 5 | 468.75 | 2% | OAR-BI, TPL, DO, Spare parts, Wake effect |
| B.07 | 2 | 248.88 | 2% | Land Leases (200) + Property tax (48.88); **inflation_start_exponent=0** (standard) |
| B.08 | 3 | 93.72 | 2% | Power consumption, Grid Usage, Balancing costs |
| B.09 | 2 | 0.00 | — | Confirmed zero |
| B.10 | 5 | 24.00 | 2% | Auditors, Accounting, Legal closings + book-keeping + formalities |
| B.11 | 2 | 20.00 | 2% | Active Y1–Y14; **explicit 30-element flags `(1,)*14 + (0,)*16`** |
| B.12 | 5 | 200.00 | 2% | Mitigation, Agrinergie, Fauna&Flora, E&S, HSE |
| B.13 | 1 | — | — | **PCT_OF_SELECTED_GROUPS**, 6%, selected=B.01–B.12; `contingency_pct=0.0` |

---

## Special Mappings

### B.02.1 Explicit Schedule

```
Y1–Y2:   385.6
Y3–Y5:   465.6
Y6–Y10:  588.0
Y11–Y15: 628.0
Y16–Y20: 676.0
Y21–Y25: 756.0
Y26–Y30: 828.0
```

- `basis = OpexBasis.EXPLICIT_SCHEDULE` — no inflation applied
- `infl_rate = 0.0` on the item
- Group `inflation_rate = 0.0` to avoid double-inflation
- Other B.02 items use item-level `infl_rate = 0.02`

### B.07 Standard Pattern

**Not exponent=1.** B.07 follows the standard `(F2-1)` pattern:
- `inflation_start_exponent = 0` (default)
- Y1 = 248.88 (= base × 1.02^0)
- Y2 = 253.86 (= base × 1.02^1)
- Y3 = 258.93 (= base × 1.02^2)

Earlier diagnostic v3 incorrectly said `inflation_start_exponent=1`. Corrected.

### B.11 Explicit Active Flags

**Do not use `active_from/active_until` helper** — it falls through to `True` outside the specified range.

Required: explicit 30-element tuple:
```python
ACTIVE_1_14 = (1,)*14 + (0,)*16  # Y1–Y14 active, Y15–Y30 inactive
```

### B.13 Contingency = 6% × sum(B.01–B.12)

```python
basis = OpexBasis.PCT_OF_SELECTED_GROUPS
budget_keur = 6.0   # 6%
selected_group_codes = ("B.01", "B.02", ..., "B.12")
contingency_pct = 0.0   # pct item is the sole mechanism
```

- **No self-reference** — B.13 not in `selected_group_codes`
- **True two-pass** — pass1 skips pct items; pass2 computes from finalized `group_totals`
- **Order-independent** — B.13 can be anywhere in group list; result is same

---

## Offline Only

This template is **NOT wired into runtime**:

- `run_waterfall` — unchanged
- TUHO factory (`ProjectInputs.create_default_tuho_wind1()`) — unchanged, uses old `OpexItem` structure
- Oborovo factory — unchanged
- Revenue, tax, SHL, senior debt, R99 — unchanged

The new engine (`compute_annual_opex`) is a standalone diagnostic fixture only.

---

## Tests

```
tests/test_tuho_opex_template_mapping.py: 29 passed
tests/test_opex_line_item_engine.py:     42 passed
tests/test_opex.py:                      21 passed
tests/test_inputs.py:                    15 passed
─────────────────────────────────────────────────────────
Total:                                   107 passed
```

---

## Next Recommended Step

**Phase 7H O3c** — Runtime integration behind feature flag.

After review:
1. Wire `compute_annual_opex` into `run_waterfall` behind a feature flag
2. Use `build_tuho_opex_template()` to replace inline OPEX construction in TUHO waterfall path
3. Verify full waterfall metrics (debt, equity IRR, DSCR) match Excel within calibration tolerances
4. Add Oborovo template similarly (fixing the B.01/B.02 deduplication issue from Sprint 21)

---

## Files Changed

| File | Change |
|------|--------|
| `domain/opex/templates/tuho.py` | New — TUHO OPEX template builder |
| `domain/opex/templates/__init__.py` | New — makes it a package |
| `tests/test_tuho_opex_template_mapping.py` | New — 29 parity tests |
| `docs/phase7h_tuho_opex_template_mapping.md` | New — this document |