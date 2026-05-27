# Phase 20O — Debt Sizing Mode Architecture

**Branch:** `phase20o-debt-sizing-mode-architecture`  
**Base:** `485f3f14d895d8838dbe5e6852ce90717d8c1a74` (after PR #277)  
**Date:** 2026-05-27  
**Status:** Config/architecture only — no runtime formula changes

---

## 1. Background

Senior debt sizing differs materially between TUHO and Oborovo:

| Project | Sizing approach | DSCR divisor |
|---|---|---|
| TUHO | Frozen per-period Excel schedule (Macro!R50) | 1.20 PPA / ~1.41 merchant |
| Oborovo | Gearing-cap based | 1.15 flat |

**Python runtime currently behaves as Mode C (frozen schedule)** — debt amount and per-period service are treated as frozen inputs and DSCR is back-computed. This is the correct default for calibration parity.

Three sizing modes are required:

| Mode | Value | Description | Status |
|---|---|---|---|
| C | `frozen_excel_schedule` | Debt/service schedule from Excel calibration treated as frozen inputs. DSCR = outcome | ✅ Default — implemented |
| A | `minimum_dscr_sculpted` | Iterative solver finds debt so min DSCR ≈ target (e.g. 1.45). Uses DSCR divisor schedule (1.20/1.41 for TUHO) | 🚧 Future |
| B | `flat_dscr_sculpted` | Iterative solver finds debt so flat DSCR = target (e.g. 1.15) | 🚧 Future |

---

## 2. What Was Added

### 2.1 New Enum: `DebtSizingMode`

```python
class DebtSizingMode(Enum):
    FROZEN_EXCEL_SCHEDULE   = "frozen_excel_schedule"
    MINIMUM_DSCR_SCULPTED  = "minimum_dscr_sculpted"
    FLAT_DSCR_SCULPTED     = "flat_dscr_sculpted"

    def validate_and_resolve(self) -> "DebtSizingMode":
        """Raise NotImplementedError for unimplemented future modes."""
```

`FROZEN_EXCEL_SCHEDULE` resolves successfully.  
`MINIMUM_DSCR_SCULPTED` and `FLAT_DSCR_SCULPTED` raise `NotImplementedError` with a clear message.

### 2.2 New Fields on `FinancingParams`

| Field | Type | Default | Notes |
|---|---|---|---|
| `debt_sizing_mode` | `DebtSizingMode \| None` | `None` | Explicit mode. None = backward-compat (→ FROZEN_EXCEL_SCHEDULE) |
| `target_min_dscr` | `float \| None` | `None` | For Mode A docs/future use |
| `flat_dscr_target` | `float \| None` | `None` | For Mode B docs/future use |
| `frozen_schedule_note` | `str \| None` | `None` | Human-readable source note, e.g. "Macro!R50 frozen schedule" |

### 2.3 New Methods on `FinancingParams`

```python
def resolved_debt_sizing_mode(self) -> DebtSizingMode:
    """Resolve effective mode. Raises NotImplementedError for future modes."""

@property
def sizing_mode_description(self) -> str:
    """Human-readable: returns mode name + source note + DSCR context."""
```

---

## 3. Backward Compatibility

- `debt_sizing_mode=None` (default) maps to `FROZEN_EXCEL_SCHEDULE` — existing behavior unchanged
- `debt_sizing_method` string field is unaffected
- TUHO and Oborovo default to `debt_sizing_mode=None` — runtime output unchanged
- The `resolve_and_validate()` guard fires only when a non-None enum value is explicitly set to a future mode

---

## 4. TUHO-Specific Parameters

If `DebtSizingMode.MINIMUM_DSCR_SCULPTED` is ever implemented for TUHO:

| Parameter | Value | Source |
|---|---|---|
| Target min DSCR | ~1.45 | CF!R150 Minimum Senior DSCR |
| PPA period divisor | 1.20 | DS!R19 |
| Merchant period divisor | ~1.41 | DS!R19 (4 merchant periods) |
| Macro!R50 | Frozen per-period schedule | Hardcoded in Excel Macro sheet (204,669 kEUR total CF for debt repayment) |

---

## 5. Oborovo-Specific Parameters

If `DebtSizingMode.FLAT_DSCR_SCULPTED` is ever implemented for Oborovo:

| Parameter | Value | Source |
|---|---|---|
| Flat target DSCR | 1.15 | Financing inputs |
| Debt method | Gearing-cap (75.24%) | Fixed: `fixed_debt_keur=42,852 kEUR` |

---

## 6. Guard Behavior

| User action | Result |
|---|---|
| No change (default) | `FROZEN_EXCEL_SCHEDULE` resolves normally ✅ |
| Set `debt_sizing_mode=DebtSizingMode.FROZEN_EXCEL_SCHEDULE` | Resolves normally ✅ |
| Set `debt_sizing_mode=DebtSizingMode.MINIMUM_DSCR_SCULPTED` | `NotImplementedError` with clear message ✅ |
| Set `debt_sizing_mode=DebtSizingMode.FLAT_DSCR_SCULPTED` | `NotImplementedError` with clear message ✅ |

---

## 7. Before / After Output Comparison

### TUHO

| Metric | Before (baseline) | After | Delta |
|---|---|---|---|
| total_senior_ds_keur | 65,826 | 65,826 | 0 |
| total_distribution_keur | 173,572 | 173,572 | 0 |
| avg_dscr | 1.230 | 1.230 | 0 |
| equity_irr | 0.1115 | 0.1115 | 0 |
| project_irr | 0.0941 | 0.0941 | 0 |

### Oborovo

| Metric | Before (baseline) | After | Delta |
|---|---|---|---|
| total_senior_ds_keur | 63,501 | 63,501 | 0 |
| total_distribution_keur | 104,699 | 104,699 | 0 |
| avg_dscr | 1.150 | 1.150 | 0 |
| equity_irr | 0.0917 | 0.0917 | 0 |
| project_irr | 0.0798 | 0.0798 | 0 |

**Output unchanged.** No runtime formula changes.

---

## 8. Tests Run

```bash
pytest tests/test_revenue.py tests/test_opex.py tests/test_shl_waterfall_priority.py tests/test_tuho_shl_calibration.py -v
python3 -c "import main_web"
```

**Expected:** All pass. (Results in PR body.)

---

## 9. Known Limitations

1. **Modes A and B are not implemented** — setting them raises `NotImplementedError`. Actual solvers must be built in a future phase.
2. The `frozen_schedule_note` field is for documentation only — it does not affect any runtime calculation.
3. `target_min_dscr` and `flat_dscr_target` are stored on `FinancingParams` for future use but are not yet consumed by any solver.
4. TUHO Macro!R50 frozen schedule source (204,669 kEUR total) is documented but not yet stored as a field.

---

## 10. Recommended Next Phase

**Phase 20P** — Implement Mode B (`FLAT_DSCR_SCULPTED`) solver for Oborovo:
- Flat target DSCR (e.g. 1.15)
- Start with Oborovo since its structure is simpler (no PPA/merchant DSCR split)

**Phase 20Q** — Implement Mode A (`MINIMUM_DSCR_SCULPTED`) solver for TUHO:
- Min DSCR target ~1.45
- Uses existing `dscr_schedule` (1.20 PPA / 1.41 merchant)
- Much more complex — TUHO must also handle construction-period carryforward

---

*This document covers config/architecture only. No runtime formula changes were made.*
