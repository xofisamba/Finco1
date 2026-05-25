#!/usr/bin/env python3
import requests

pr_body = """## Phase 10 — Data-Feed Fix

### Root Cause
`_num()` was returning `None` for all CSV string values. `csv.DictReader` always returns strings — so `'4060.98'` was being treated as a non-numeric string and returned `None`, causing every Excel row to show `MISSING_EVIDENCE` despite being fully present in `PER_BRIDGE` / `SHL_BRIDGE`.

Secondary issue: SHL bridge column names (`excel_shl_balance_keur`, `excel_shl_interest_keur`) didn't match script expectations (`excel_shl_opening_keur`, `excel_shl_closing_keur`, `excel_shl_gross_accrued_keur`).

### Source Inventory
`reports/phase10_human_readable_calibration_source_inventory.csv` — 10 sources catalogued (PER_BRIDGE, SHL_BRIDGE, SEMESTER_PARITY workbook, etc.)

### What Was Fixed

| Section | Before | After |
|---|---|---|
| Senior Debt DSCR | MISSING_EVIDENCE | COMMITTED (DS!R19 via PER_BRIDGE) |
| Senior Debt DS | MISSING_EVIDENCE | COMMITTED (computed DS!R50+R49) |
| SHL Opening/Closing | MISSING_EVIDENCE | COMMITTED (BS!R24 via SHL_BRIDGE excel_shl_balance_keur) |
| SHL Gross Interest | MISSING_EVIDENCE | COMMITTED (P&L!R27 via SHL_BRIDGE excel_shl_interest_keur) |
| Revenue Electricity | MISSING_EVIDENCE | COMMITTED (P&L!R8 via PER_BRIDGE excel_revenue_keur) |
| Total Revenue | MISSING_EVIDENCE | COMMITTED (P&L!R8 via PER_BRIDGE) |
| OPEX | MISSING_EVIDENCE | COMMITTED (OPEX schedule via PER_BRIDGE) |
| EBITDA | MISSING_EVIDENCE | COMMITTED (P&L!R16 via PER_BRIDGE) |
| CFADS EBITDA | MISSING_EVIDENCE | COMMITTED (P&L!R16 via PER_BRIDGE) |
| Distribution | MISSING_EVIDENCE | COMMITTED (excel_distribution_keur in PER_BRIDGE) |

### What Remains MISSING_EVIDENCE (and why)

- **CO2 Revenue**: CF!R35 not in committed extract
- **Balancing Revenue**: CF!R30 not mapped
- **Book Depreciation**: P&L!R14 not in committed extract
- **Taxable Income (R35)**: P&L!R35 not mapped
- **CIT Cash (R67)**: P&L!R67 not in bridge
- **CFADS / R69**: P&L!R69 not in bridge — use runtime
- **FCF for Distribution (R99)**: not in bridge — use runtime
- **FCF After SHL (R102)**: not in bridge — use runtime
- **SHL Cash Interest**: Eq!R26 not in SHL bridge
- **Equity Invested/Returned**: not in extract

### Tests
- `test_phase10_human_readable_calibration_workbook.py`: **21 passed**
- `test_phase9_5_output_tabs_runtime_summary_binding.py`: **33 passed**
- No runtime files changed (domain/, app/waterfall/, app/ui_runner.py, app/tax_bridge.py)

### G20 / R99 / R102
Unchanged — BLOCKED / NOT APPROVED (governance gates, no promotion)

### Files Changed
- `scripts/export_phase10_human_readable_calibration_workbook.py` — `_num()` fix + SHL/Revenue/Senior Debt column fixes
- `reports/phase10_human_readable_calibration_workbook.xlsx` — regenerated with real data
- `reports/phase10_human_readable_calibration_source_inventory.csv` — new file
"""

resp = requests.post(
    'https://api.github.com/repos/xofisamba/Finco1/pulls',
    headers={
        'Authorization': 'Bearer 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',
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json'
    },
    json={
        'title': 'Phase 10 — Human-Readable Calibration Workbook Data-Feed Fix',
        'head': 'phase10-human-readable-calibration-workbook-datafeed-fix',
        'base': 'main',
        'body': pr_body
    },
    timeout=15
)
pr = resp.json()
print('PR number:', pr.get('number'))
print('PR URL:', pr.get('html_url'))
print('State:', pr.get('state'))
if pr.get('number'):
    # Merge
    merge_resp = requests.put(
        f"https://api.github.com/repos/xofisamba/Finco1/pulls/{pr['number']}/merge",
        headers={
            'Authorization': 'Bearer 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',
            'Accept': 'application/vnd.github.v3+json'
        },
        json={
            'merge_method': 'squash',
            'commit_title': 'Phase 10: Data-feed fix — populate Senior Debt/SHL/Revenue/OPEX/EBITDA from committed Phase 9 artifacts (squashed)'
        },
        timeout=15
    )
    print('Merged:', merge_resp.json().get('merged'))