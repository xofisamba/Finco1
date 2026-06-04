# Phase 57D — Live no-go copy scanner implementation

## Status

DRAFT → marked ready → squash merged in the 57D overnight branch
(see `reports/phase57d_live_no_go_copy_scanner.json` for the
merge SHA).

This is a **test-only / test + scanner-helper** phase. It adds a
filesystem-scanning no-go copy test that complements (not
replaces) the existing snapshot-only tests in
`tests/test_phase54h_ui_no_go_copy_scanner.py` and
`tests/test_phase57a_ui3_line_item_grid_capex_summary.py::TestNoGoCopy`.

## Current main SHA (start of 57D)

`09f151a32a12152f5b2650e26394aa4174e215d3` (post-57C, Validation
bar semantics design merged)

## Current main SHA (after 57D)

Reported in the 57D combined report.

## Problem statement

The current no-go copy tests are **snapshot-based**:

- `tests/test_phase54h_ui_no_go_copy_scanner.py` checks that
  the 54H doc/report exist and contain a static list of
  forbidden terms. It does NOT scan the live filesystem.
- `tests/test_phase57a_ui3_line_item_grid_capex_summary.py::TestNoGoCopy`
  scans `sheet_capex.html` and `_line_item_grid.html` for
  forbidden terms, but only as a one-off check tied to the
  57A branch.

There is no **single, always-on, repository-wide no-go copy
scanner** that future PRs can rely on. The risk is that a
new PR (UI-3.2, a CSS consolidation, a Help section update)
silently introduces a forbidden term in a template or a
pilot-facing doc.

## Goal

Implement a **live filesystem-scanning no-go copy test** that:

1. Scans the entire `app/templates/` directory (and selected
   `docs/` and `reports/` files) for forbidden positive claims.
2. Allows explicit no-go list docs and negative / disclaimer
   contexts (e.g. "not validated", "Reference only",
   "parity evidence").
3. Fails on positive user-facing claims.
4. Is fast enough to run in the regular test suite (< 5s).
5. Does not silently rewrite copy; only reports violations.

## Forbidden positive claims (canonical list)

The canonical list of forbidden positive claims, taken from
the 54H / 57A / 57B refreshes and the existing
`tests/test_phase57a_ui3_line_item_grid_capex_summary.py::TestNoGoCopy::NO_GO_TERMS`:

- `bankable`
- `bank-grade`
- `lender-ready`
- `certified`
- `audit-ready`
- `validated` (in positive user-facing context)
- `investor-ready`
- `SaaS-ready`
- `production-ready`
- `external validation`
- `customer reference`
- `investment advice`
- `guaranteed returns`
- `model-validated`
- `LineItemGrid is validated` (or any "X is validated" claim)
- `audit-ready` (already in canonical list)
- `certified` (already in canonical list)

## Allowed contexts (whitelist)

The scanner allows the forbidden term `validated` (and the
other terms) to appear in the following contexts:

1. **No-go list**: any file under
   `docs/external_review/no_go_claims.md` or
   `reports/phase*_no_go*.json` (or similar) may contain
   the forbidden terms as part of the no-go list.
2. **Test files**: any file under `tests/` may contain
   forbidden terms in test names, docstrings, or assertions
   that explicitly check for the absence of forbidden terms.
3. **Negative / disclaimer context**: the scanner recognizes
   sentences like:
   - "not validated"
   - "not approved"
   - "must not be presented as ..."
   - "no-go"
   - "forbidden positive claim"
   - "is not a [X]"
   - "does not validate the model"
   - "presentation refactor only"
4. **Historical mention**: docs that explicitly mark a
   mention as historical / no-go finding (e.g. "where it
   read 'validated'").

## Scanner implementation

The scanner is implemented in
`tests/test_phase57d_live_no_go_copy_scanner.py` and consists
of:

### 1. `NO_GO_TERMS` constant
The canonical list of forbidden terms (see above).

### 2. `ALLOWED_PATH_PATTERNS` set
The set of file path patterns that are allowed to contain
forbidden terms in no-go list / negative contexts:
- `tests/test_phase54h_ui_no_go_copy_scanner.py`
- `tests/test_phase57a_ui3_line_item_grid_capex_summary.py`
- `tests/test_phase57d_live_no_go_copy_scanner.py`
- `docs/phase*_*.md` (any phase doc) — historical / no-go
  mentions are allowed
- `docs/external_review/no_go_claims.md`
- `reports/phase*_no_go*.json`
- `docs/governance/phase53_*.md` and similar governance docs

### 3. `scan_file(path)` function
Reads a file, strips Jinja comments (`{# ... #}`) and HTML
comments (`<!-- ... -->`), then checks each NO_GO_TERM
against the remaining text. For each match, checks the
surrounding context for an allowed negative phrase.

### 4. `scan_repository()` function
Walks `app/templates/`, `docs/`, and `reports/` and applies
`scan_file` to each file.

### 5. `TestLiveNoGoCopyScanner` test class
Calls `scan_repository()` and asserts that no positive
violations were found.

## Tests required for 57D

The 57D test file (`tests/test_phase57d_live_no_go_copy_scanner.py`)
includes the following test classes:

### `TestScannerHelper` (5+ tests)
- `test_no_go_terms_constant_has_canonical_list`
- `test_allowed_path_patterns_contains_test_files`
- `test_allowed_path_patterns_contains_no_go_docs`
- `test_scan_file_finds_no_violations_in_clean_template`
- `test_scan_file_finds_violation_in_template_with_forbidden_term`
- `test_scan_file_skips_jinja_and_html_comments`
- `test_scan_file_recognizes_negative_context`
- `test_scan_file_recognizes_historical_mention`

### `TestLiveRepositoryScan` (3+ tests)
- `test_app_templates_clean`
- `test_docs_clean_except_allowlisted`
- `test_reports_clean_except_allowlisted`

### `TestRc1Untouched` (2 tests)
- `test_rc1_sha_constant_stable`
- `test_rc1_still_in_git_history`

### `TestHardNoGoScope` (5+ tests)
- `test_no_runtime_files_in_diff`
- `test_no_main_web_py_changes`
- `test_no_app_js_changes`
- `test_no_styles_css_changes`
- `test_no_services_or_persistence_changes`

### `TestScannerDoesNotSilentlyRewrite` (2 tests)
- `test_scanner_only_reports_no_writes`
- `test_scanner_no_runtime_side_effects`

## Behavior on existing violations

If the live scanner finds an existing positive violation in
a user-facing template (not a no-go list, not a test file,
not a historical mention):

1. The test fails with a clear violation report (file path,
   line number, forbidden term, surrounding context).
2. The violation is **not silently rewritten**.
3. The violation is reported in the 57D combined report
   so the user can decide whether to:
   - open a small draft fix PR to remove the violation
     copy, or
   - document the violation and defer the fix to a
     future PR.

The 57D phase itself does NOT include a runtime copy fix
PR. If a violation is found, 57D becomes a "report +
deferred fix" PR.

## Hard no-go / scope for 57D

- No financial model changes.
- No `app/waterfall_core.py` changes.
- No `app/project_factories.py` changes.
- No `app/persistence/` changes.
- No `app/services/` changes.
- No `main_web.py` changes.
- No `static/app.js` changes.
- No `static/styles.css` changes.
- No schema / migration changes.
- No fixture CSV changes.
- No frontend dependency changes.
- No Tailwind / Alpine / React / Vue / Svelte.
- No G20/R99/R102 guard promotion.
- No generic Solar/Wind runtime work.
- No BESS / Hybrid / Portfolio work.
- No silent copy rewrites (the scanner only reports).
- rc1 frozen.

## Auto-merge policy

57D is `test-only`. It is auto-merge eligible if all hard
gates pass. The scanner only **reports** violations; it
does not modify any file. The combined report at the end
of the overnight stack includes the scanner's findings.
