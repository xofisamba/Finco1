"""Phase 1.5 Portfolio UI + Excel Export.

Scope:
- Minimal portfolio UI layer (app/portfolio_ui.py)
- Minimal portfolio Excel export sheets (app/excel_export.py)
- No HoldCo, No SHL, No Sponsor IRR, No monthly model
- No DSRF funding/release mechanics, No pooled financing

Files changed:
- app/portfolio_ui.py (new) — build_portfolio_summary_table, build_portfolio_spv_table, render_portfolio_summary
- app/excel_export.py (append only) — added Portfolio_Summary, Portfolio_SPVs, Portfolio_Notes sheets
- tests/test_portfolio_ui.py (new)
- tests/test_excel_export.py (extended — existing tests unchanged)
- docs/phase1_5_portfolio_ui_export.md (new)

IRR semantics:
- Simple Average IRRs are unweighted per-SP averages
- NOT true portfolio XIRR
- Label must show "Simple Average (NOT Portfolio XIRR)"

DSRF: placeholder only — enabled=True raises ValueError

Tests:
- test_portfolio_ui.py: 16 tests (UI table building)
- test_excel_export.py: 36 existing tests unchanged
"""