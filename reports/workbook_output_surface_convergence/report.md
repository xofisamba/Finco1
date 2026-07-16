# Workbook Output Surface Convergence — PR-B Hardening Report

**Branch:** `feat/workbook-convergence-outputs`  
**Date:** 2026-07-16  
**Status:** All acceptance criteria met

---

## 1. Revenue Data Authority

**Change:** `_build_revenue_ctx()` in `app/v2/router.py` now reads from `projection.fs.meta` and `projection.fs.runtime_summary` instead of `projection.debt.*`.

**Rationale:** `projection.fs` and `projection.debt` share the same `runtime_summary` dict object, but `.meta` differs. Using `projection.debt.meta` caused Revenue to show UNAVAILABLE whenever the Debt schedule was absent, even when the FS payload was present. Revenue state must be independent of Debt availability.

**Verified by:** `TestRevenueIndependentOfDebt` (4 unit tests) + `test_revenue_exact_clean_after_run` (browser).

---

## 2. Revenue Derivation Key Contract

**Persisted keys in `runtime_summary["revenue_derivation"]`:**

| Key | Type (persisted) | Type (formatted) |
|-----|-----------------|-----------------|
| `display_value_keur` | float | str `"1,234 kEUR"` or `"NOT_AVAILABLE"` |
| `summary_method` | str | str (unchanged) |
| `period_formula` | str | str (unchanged) |
| `period_count` | int | int (unchanged) |
| `sample_period_label` | str | str (unchanged) |
| `sample_generation_mwh` | float | str `"1,000 MWh — 2029-01"` or `"NOT_AVAILABLE"` |
| `sample_revenue_keur` | float | str `"55 kEUR"` or `"NOT_AVAILABLE"` |
| `audit_source` | str | str (unchanged) |

**Source:** `app/ui/runtime_summary._format_revenue_derivation()` called in `router.py` Step 11b.

**Verified by:** `TestRevenueDerivatonKeyContract` (8 unit tests).

---

## 3. Zero-vs-Missing Semantics

**Rule:** `0` (numeric zero) formats to `"0 kEUR"` / `"0 MWh"`, not `"NOT_AVAILABLE"`. `None` and missing keys → `"NOT_AVAILABLE"`.

**Template fix (`sheet_revenue.html`):**
- Replaced `{% if gen and ... %}` → `{% if gen is not none and gen != "NOT_AVAILABLE" %}`
- Replaced `{% if sr and ... %}{{ sr }} kEUR` → `{% if sr is not none and ... %}{{ sr }}` (removed duplicate " kEUR")
- Replaced `{% if total %}` → `{% if total is not none and total != "NOT_AVAILABLE" %}`

**Verified by:** `TestRevenueDerivatonZeroVsMissing` (7 unit tests).

---

## 4. Balance-Check Server-Side Classification

**Change:** Removed Jinja numeric threshold comparison (`v > 1.0 or v < -1.0`) from `sheet_financial_statements.html`. Added `annotate_balance_check_row()` in `app/workbook/runtime_projection.py`.

**Logic:** `abs(v) > 1.0` for any non-None value → `balance_check_ok=False`, `css_class="v2-bs-balance-check-warn"`, `status_title="Balance sheet does not balance"`. Otherwise `v2-bs-balance-check-ok` / `"Balanced within ±1 kEUR"`.

**Template now reads:** `bc.css_class`, `bc.status_title`, `bc.balance_check_ok` — no arithmetic.

**Verified by:** `TestAnnotateBalanceCheckRow` (7 unit tests) + `TestJinjaNoFinancialCalculation` (parametrized over 4 templates).

---

## 5. Schedule Table CSS Contract

**CSS rule (per-`th` sticky, not per-`tr`):**

```css
.v2-schedule-table thead th          { position: sticky; top: 0; z-index: 2; }
.v2-schedule-table thead th:first-child { position: sticky; top: 0; left: 0; z-index: 3; }
.v2-schedule-table tbody td:first-child { position: sticky; left: 0; z-index: 1; }
```

**Templates updated:** `sheet_senior_debt.html`, `sheet_tax.html` — scroll wrapper changed from inline `style="overflow-x:auto;"` to `class="v2-schedule-scroll"`.

**Verified by:** `test_debt_schedule_sticky_and_scroll`, `test_tax_schedule_sticky_and_scroll` (computed-style browser tests).

---

## 6. Statement Table CSS Contract

**New classes in `static/css/workbook_v2.css`:**

| Class | Role |
|-------|------|
| `.v2-statement-scroll` | Overflow wrapper |
| `.v2-statement-table` | Table base |
| `.v2-statement-corner` | Top-left corner `<th>` (sticky X+Y, z-index 3) |
| `.v2-statement-period-header` | Period column headers (sticky Y, z-index 2) |
| `.v2-statement-row-label` | Row label `<td>` (sticky X, z-index 1) |
| `.v2-statement-num` | Numeric cell (tabular nums) |
| `.v2-statement-total` | Total row emphasis |

**Verified by:** `test_fs_statement_sticky_and_scroll` (computed-style browser test).

---

## 7. Protected-Reference Notice

**Change:** Added `{% if not project_editable %}<div class="v2-protected-notice">…</div>{% endif %}` to `sheet_financial_statements.html`. All four output sheet templates now carry this block.

**Verified by:** `test_protected_reference_outputs_visible_no_mutation` (iterates all 4 tabs).

---

## 8. UNAVAILABLE State Tests

| Test | Scenario |
|------|----------|
| `test_revenue_unavailable_when_no_derivation` | Revenue UNAVAILABLE when `revenue_derivation` stripped from `last_runtime_summary_json` |
| `test_debt_unavailable_state_no_outputs_current` | Debt UNAVAILABLE when `last_debt_schedule_json='{}'` |

Both tests patch `workspace_states` directly via SQLite, reload the workbook page, and assert the CLEAN badge is absent.

---

## 9. Revenue Derivation Persistence

**Change in `router.py` (Step 11b):** After run, `result["derivation_evidence"]["revenue"]` is formatted via `_format_revenue_derivation()` and merged into `runtime_summary` under key `revenue_derivation` before the atomic DB commit.

This ensures `revenue_derivation` survives page reload and is available to `_build_revenue_ctx()`.

---

## 10. Test Results

```
tests/test_workbook_prb_focused.py          31 passed
tests/test_workbook_v2_output_surface_browser.py   28 passed
```

**Pre-existing failures (present on `main`, not introduced by this branch):**
- `TestProjectRows` — 3-tuple vs 4-tuple mismatch in fixture
- `TestOobViewHelpers` — missing `FinancialStatementsProjection` args  
- `TestInactiveSurfaceGuard` — asyncio event loop destroyed by browser tests

---

## 11. Files Changed

| File | Nature |
|------|--------|
| `app/workbook/runtime_projection.py` | Added `annotate_balance_check_row()` |
| `app/v2/router.py` | Revenue authority + Step 11b derivation persistence |
| `app/templates/v2/partials/sheet_revenue.html` | Zero-vs-missing semantics |
| `app/templates/v2/partials/sheet_financial_statements.html` | Server-side balance-check + protected notice + statement CSS classes |
| `app/templates/v2/partials/sheet_senior_debt.html` | Scroll wrapper class |
| `app/templates/v2/partials/sheet_tax.html` | Scroll wrapper class |
| `static/css/workbook_v2.css` | Schedule per-th sticky + statement table classes |
| `tests/test_workbook_prb_focused.py` | New: 31 focused unit tests |
| `tests/test_workbook_v2_output_surface_browser.py` | Extended: deterministic protected-reference, UNAVAILABLE, exact CLEAN, sticky/scroll tests |

---

## 12. Governance

- Engine formulas: **unchanged**
- Registry definitions: **unchanged**  
- Persistence schema: **unchanged**
- Parity targets / golden fixtures: **unchanged**
- PR status: **Draft** — not marked Ready, not merged
