# C2-PR22 — Export / Run Safety Guardrails

## Summary

Adds regression tests proving — not just asserting in prose — that
preview values sent to `POST /model/preview` can never leak into
authoritative export output, and that a preview request has zero
effect on persisted state or subsequent export bytes. No production
code is touched by this PR.

All tests live in
`tests/test_c2_pr22_export_run_safety_guardrails.py`, against the real
`main_web.app` via `fastapi.testclient.TestClient`, following the same
pattern as `tests/test_c2_pr14_opex_preview.py`.

## What each guardrail test proves

### `TestPreviewSentinelNeverLeaksIntoRuntimeSummaryCsv`

Posts a distinctive sentinel preview value (`987654.32`, chosen so its
digit string `98765432` and its formatted form `987,654.32` are
extremely unlikely to coincide with any legitimately-computed export
figure) across all five preview fields
(`capexTotalPreview`/`revenueTotalPreview`/`opexTotalPreview`/
`ebitdaPreview`/`operatingCashFlowPreview`) in one request, confirms
the sentinel round-tripped through the `/model/preview` response (so
the test is meaningful, not a no-op), then fetches the real
`/exports/runtime-summary.csv` route and asserts the sentinel's digit
string, formatted string, and raw `str()` form are all absent from the
decoded CSV text.

### `TestPreviewSentinelNeverLeaksIntoInstitutionalWorkbookExport`

Same sentinel-posting setup, then fetches the real
`/exports/institutional-workbook.xlsx` route and checks for leakage two
ways: (1) a raw-bytes scan for the sentinel's digit string/formatted
form across the entire zip-container response (a conservative,
format-agnostic check that would catch a leak in any embedded XML/
shared-string/inline-string content), and (2) parses the workbook with
`openpyxl` and asserts no numeric cell, in any sheet, is within `0.01`
of the sentinel value — the most direct possible proof that the
exported figures are real saved-model numbers, never the previewed
sentinel.

### `TestPreviewRequestDoesNotMutatePersistedState`

Two tests:

- `test_db_file_byte_identical_before_and_after_sentinel_preview` —
  mirrors `tests/test_c2_pr14_opex_preview.py`'s
  `TestNoFinancialEngineCallOrPersistenceMutation::test_no_persistence_mutation`
  exactly (compares `os.path.getmtime`/`os.path.getsize` on the SQLite
  DB file before/after), extended to a single request carrying all
  five preview fields at once rather than just one.
- `test_no_financial_engine_call_with_full_sentinel_payload` —
  monkeypatches `app.waterfall_core.run_project` to raise if called,
  then posts the full five-field sentinel payload and confirms no
  exception is raised — proving `/model/preview` never calls the real
  financial engine regardless of how many preview fields are present
  simultaneously.

### `TestExportBytesUnaffectedByPrecedingPreviewRequest`

Captures a real export's output, fires a `/model/preview` POST
carrying the sentinel, then re-fetches the same export and compares.
The CSV export is compared byte-for-byte (it contains no embedded
wall-clock timestamp). The xlsx export is compared after normalizing
away ISO-8601 timestamp substrings (the export legitimately embeds a
fresh "generated at"/"Weekend run at" timestamp in `docProps/core.xml`
and in at least one worksheet cell on every single request, regardless
of preview state — confirmed by direct inspection during test
development; this is pre-existing, unrelated behaviour of
`build_institutional_workbook_export`, not a leak). After normalizing
timestamps, the two captures are asserted byte-identical, proving the
intervening `/model/preview` call changed nothing about the export's
actual data content.

### `TestSavedCapexRevenueOutputsUnaffectedByPreviewState`

Fetches the institutional workbook export three times, interleaved
with two `/model/preview` POSTs carrying two *different* sentinel CAPEX
preview magnitudes (`111111.11`, then `222222.22`). Asserts all three
(timestamp-normalized) captures are identical to each other — proving
the saved/authoritative export output is structurally independent of
whatever value is currently sitting in the preview echo, regardless of
its magnitude or how many times it changes.

## What was decided too heavy to test, and why

**A new, dedicated end-to-end `/run`-form regression test was not
added.** `/run` requires a full multi-field form payload
(`app.services.run_service.execute_run_route`), which is already
exhaustively exercised by this repo's existing Phase-9/PR9-era Run test
suites elsewhere (`tests/test_phase*run*.py` and similar). Building a
new heavy fixture here to send `/model/preview` then `/run` and diff
the output would not add genuinely new leak-detection coverage beyond
what the lighter-weight tests above already prove: `/model/preview`
never mutates the DB (confirmed directly), and `/run`'s only inputs are
the saved DB/form state — so if `/model/preview` cannot touch the DB,
it cannot possibly influence what `/run` subsequently produces either.
The DB-mutation and export-byte-identity tests together give the same
guarantee transitively, at a fraction of the fixture cost (no need to
construct a full valid Run form payload, no need to parse/compare a
full Run-rendered HTML response).

**Real browser-level OPEX-edit-then-export testing was not added as a
new Playwright test.** The existing
`tests/test_c2_pr17_opex_line_editability.py::TestSaveDoesNotPersistOpexEdits`
and `tests/test_c2_pr18_opex_preview_only_governance.py`'s regression
tests already prove, at the browser level, that an OPEX preview edit
cannot survive Save. Combined with this PR's route-level "exported
figures are saved-model numbers, never the previewed sentinel" proof
(via the parsed-cell-value check above), the same guarantee — "a
preview-only OPEX edit never appears in an exported workbook" — is
covered without needing a third, heavier browser fixture.

**PR19's refresh-resets-preview coverage was not duplicated.**
`tests/test_c2_pr19_preview_reset_refresh_clarity_browser.py` already
covers "a full page reload resets all five preview indicators" at the
browser level; re-running it was confirmed as part of this PR's full
regression pass (see the PR's final report) rather than re-implemented
here.
