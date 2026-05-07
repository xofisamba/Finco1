# Bankable Depreciation — Rebase Summary

## Status: ✅ Rebased and merged with main

Branch `feature/bankable-depreciation` is now merged with `origin/main` via merge (not rebase due to multiple add/add conflicts).

### What changed
- `feature/bankable-depreciation` merged with latest main
- Conflict in `tests/test_custom_input_directionality.py` resolved (branch version kept — includes depreciation wiring tests)
- `app/depreciation_engine.py`, `app/depreciation_bankable.py` integrated

### Test Results
| Suite | Result |
|-------|--------|
| `test_bankable_depreciation.py` | 26 passed ✅ |
| `test_depreciation_engine.py` | 18 passed ✅ |
| `test_depreciation_wiring.py` | 4 passed ✅ |
| Full suite | 1158 passed, 1 xfailed ✅ |

### Architecture Confirmed
- Tax/book separation intact
- `generate_tax_and_book_schedule()` returns `(tax_sched, book_sched)`
- `to_waterfall_depreciation_schedule()` bridges to waterfall
- `build_bankable_waterfall_schedule()` one-step bridge
- OTHER fallback: 10-year straight-line, emits `DepreciationMappingWarning`
- NotImplementedError guards for declining-balance and half-year conventions

### Key Files
- `app/depreciation_bankable.py` — bankable depreciation framework
- `app/depreciation_engine.py` — integration engine
- `tests/test_bankable_depreciation.py` — 26 tests
- `tests/test_depreciation_engine.py` — 18 tests
- `tests/test_depreciation_wiring.py` — 4 tests
