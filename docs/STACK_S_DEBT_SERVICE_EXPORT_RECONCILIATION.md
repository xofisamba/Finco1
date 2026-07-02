# Stack S — Debt Service Export Reconciliation

**Branch:** `stack-s-debt-service-export-reconciliation`
**Base:** `main` at Stack R squash-merge `e34970b`
**Date:** 2026-07-02

---

## Executive Summary

Stack S addresses DD finding R1: three inconsistent Debt Service representations
in the export layer.  The fix is a targeted rename of the two per-period engine
component columns in `utils/export.py` to make their pre-overlay nature explicit.

No engine changes.  No parity numbers move.

---

## Root Cause

Phase 23A in `app/waterfall_core.py` overwrites `period.senior_ds_keur` with
canonical sizing values from the frozen fixture CSV (DSCR/display overlay).  It
does NOT update `period.senior_interest_keur` or `period.senior_principal_keur`,
and it does NOT recalculate `result.total_senior_ds_keur`.

This produces three representations with different values:

| Representation | Source | Values |
|----------------|--------|--------|
| `p.senior_ds_keur` | Phase 23A overlay (frozen fixture) | TUHO: 2116–2875 kEUR/period; only 14 of 28 DS periods non-zero |
| `p.senior_interest_keur + p.senior_principal_keur` | Engine pre-overlay | Full 28-period schedule; diverges from overlay by 50–130 kEUR/period |
| `result.total_senior_ds_keur` | Engine pre-overlay total | TUHO: 65,826 kEUR; Oborovo: 63,522 kEUR |

### Why sum(p.senior_ds_keur) ≠ result.total_senior_ds_keur

The overlay is sourced from a fixture CSV containing annual DS capacity values for
operating periods 1–14.  Semi-annual periods 15–28 have zero in the fixture, so
their `senior_ds_keur` is set to 0 by the overlay.

| Project | sum(p.senior_ds_keur) post-overlay | result.total_senior_ds_keur (engine) |
|---------|-----------------------------------|--------------------------------------|
| TUHO | ~32,853 kEUR | 65,826 kEUR ✅ correct |
| Oborovo | ~86,481 kEUR | 63,522 kEUR ✅ correct |

Recalculating `total_senior_ds_keur` from period values would produce the wrong
financial total and break all parity tests.  The engine total is correct and must
not be changed.

---

## Implementation

### Change — `utils/export.py`

Renamed the per-period engine component columns in `export_waterfall_csv()`:

| Before | After | Meaning |
|--------|-------|---------|
| `senior_interest_keur` | `senior_interest_keur_engine` | Interest on senior debt — engine pre-overlay value |
| `senior_principal_keur` | `senior_principal_keur_engine` | Principal repayment — engine pre-overlay value |

Both the `fieldnames` list (header) and the row dict are updated.

The `senior_ds_keur` column (frozen overlay value) is unchanged.
The `result.total_senior_ds_keur` summary KPI is unchanged.

---

## Files Changed

| File | Change |
|------|--------|
| `utils/export.py` | Renamed `senior_interest_keur` → `senior_interest_keur_engine`; `senior_principal_keur` → `senior_principal_keur_engine` |
| `tests/test_excel_parity_stack_s.py` | 24 new tests (created) |
| `docs/STACK_S_DEBT_SERVICE_EXPORT_RECONCILIATION.md` | This document (created) |

**Not changed:** `app/waterfall_core.py`, `domain/`, `app/waterfall_core.py`,
`domain/waterfall/waterfall_engine.py`, all financial formulas, Golden parity
values, SHA locks, `result.total_senior_ds_keur`.

---

## Regression Strategy

- No engine code is touched; all period values and KPIs are identical.
- `result.total_senior_ds_keur` is not recalculated; Golden Parity is preserved.
- The `senior_ds_keur` column in the export is unchanged; DSCR display is unaffected.
- `reporting/excel_export.py` accesses `p.senior_principal_keur` as a Python
  attribute (not a CSV column name); those references are unaffected by this rename.
- The `_resolve_user_inputs` and engine paths are not touched.

---

## Golden Parity Confirmation

| Metric | Pre-Stack-S | Post-Stack-S | Change |
|--------|------------|--------------|--------|
| TUHO equity IRR | 11.59% | 11.59% | Unchanged ✅ |
| TUHO project IRR | 9.41% | 9.41% | Unchanged ✅ |
| TUHO avg DSCR | 1.3786 | 1.3786 | Unchanged ✅ |
| TUHO senior debt | 43,359 kEUR | 43,359 kEUR | Unchanged ✅ |
| TUHO total_senior_ds | 65,826 kEUR | 65,826 kEUR | Unchanged ✅ |
| Oborovo equity IRR | 10.66% | 10.66% | Unchanged ✅ |
| Oborovo project IRR | 8.09% | 8.09% | Unchanged ✅ |
| Oborovo avg DSCR | 1.179 | 1.179 | Unchanged ✅ |
| Oborovo senior debt | 42,852 kEUR | 42,852 kEUR | Unchanged ✅ |
| Oborovo total_senior_ds | 63,522 kEUR | 63,522 kEUR | Unchanged ✅ |

---

## Acceptance Criteria

- ✅ CSV export contains `senior_interest_keur_engine` column
- ✅ CSV export contains `senior_principal_keur_engine` column
- ✅ CSV export no longer contains bare `senior_interest_keur` or `senior_principal_keur`
- ✅ `result.total_senior_ds_keur` unchanged for TUHO (65,826 kEUR) and Oborovo (63,522 kEUR)
- ✅ All Golden Parity KPIs unchanged
- ✅ All 183+ Stack K–R parity tests green
- ✅ 24 Stack S tests pass

---

## Guardrail Confirmation

- ✅ No changes to `domain/` (any file)
- ✅ No changes to `app/waterfall_core.py`
- ✅ No changes to `domain/waterfall/waterfall_engine.py`
- ✅ No changes to `app/project_factories.py`
- ✅ No financial formula changes
- ✅ No debt sizing changes
- ✅ No SHL mechanic changes
- ✅ No tax engine changes
- ✅ No IRR calculation changes
- ✅ No serialisation changes
- ✅ No Golden parity numbers moved
- ✅ SHA locks in `test_phase51f_parallel_work_guardrails.py` unchanged
