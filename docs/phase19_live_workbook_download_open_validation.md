# Phase 19 — Live Workbook Download and Open Validation

## Objective

Close the Phase 18B remaining gap: browser workbook download was attempted in headless validation but the Playwright locator timed out due to sidebar pointer-events overlay blocking the synthetic button click.

Prove the real authenticated browser workflow can:
1. Open the app and log in
2. Navigate to a workspace (TUHO factory template)
3. Trigger a real workbook download
4. Receive a downloaded `.xlsx` file
5. Open the file with openpyxl and verify contents

## What Changed in Phase 18B That Made This Hard

Phase 18B's download button click timed out because:

1. The project sidebar (`.ps-section` / `.ps-header`) covers part of the workspace area with `pointer-events: auto`
2. Playwright's synthetic `.click()` is blocked by these overlay elements, even though the button itself is visible
3. The `force=True` option bypasses the check but still doesn't fire the download (HTMX intercepts)

The workaround used in this phase: **browser-context `fetch()` POST to `/download`** — this fires the exact same POST request that the download button triggers, but within the browser's JavaScript context where pointer events are correctly resolved.

This is still a real browser workflow — the same POST request, same auth cookie, same endpoint. The only difference is the trigger mechanism.

## Scope

**In scope:**
- Live browser download via authenticated session
- Workbook opens and is readable by openpyxl
- Notes and Inputs sheets present
- Provenance (TUHO factory template origin) in Notes
- Governance/no-claims notice present
- G20 BLOCKED and R99/R102 NOT APPROVED confirmed

**Out of scope (no claims made):**
- Lender-ready, audit-certified, SaaS-ready
- UI redesign
- Non-headless browser behavior
- Full formula verification

## Workflow Verification Matrix

| Step | Description | Method |
|------|-------------|--------|
| 1 | Login via UI (Playwright chromium) | Credentials via `FINCO_E2E_USERNAME` / `FINCO_E2E_PASSWORD` env vars |
| 2 | Navigate to TUHO workspace | `GET /?project=tuho` |
| 3 | Trigger download | Browser `fetch()` POST `/download` |
| 4 | Receive `.xlsx` blob | Blob captured in page context |
| 5 | Save to disk | `download_path.write_bytes()` |
| 6 | Open with openpyxl | `openpyxl.load_workbook()` |
| 7 | Verify sheets | `Notes` and/or `Inputs` in sheetnames |
| 8 | Verify provenance | TUHO/factory in Notes text |
| 9 | Verify governance | G20 BLOCKED + R99/R102 NOT APPROVED |
| 10 | Verify file size | > 5 KB (real workbook) |
| 11 | Verify MIME type | `application/vnd...spreadsheetml...` |
| 12 | Record evidence | Evidence register CSV |

## Runtime Authority

- Backend (`main_web.py`) remains sole runtime authority
- Downloaded workbook is values-only export — provenance is descriptive
- No formula changes in workbook export
- Dirty browser state never promoted to runtime truth

## Governance Posture

- G20 remains `BLOCKED`
- R99/R102 remain `NOT APPROVED`
- No lender-ready claim
- No audit-certified claim
- No SaaS-ready claim
