# V2 Import Audit Checklist

**Purpose**: Pre-extraction import dependency audit. To be completed during V2-3 (Engine extraction).  
**Status**: Scaffold only — not yet executed.  
**Baseline**: Finco1-RC2 @ `b52d39c`

---

## Overview

Before each engine module is ported into `finco_core`, its full import graph must be audited. This document provides the checklist. The audit ensures:

1. Every dependency of the ported module is either (a) already in `finco_core`, (b) stdlib, or (c) explicitly classified for resolution.
2. No hidden shell dependencies (Streamlit, session state, UI helpers) enter `finco_core`.
3. No circular import paths are created.

---

## Audit Checklist — by Module

### `domain/inputs.py` → `finco_core/inputs/`

- [ ] List all imports in `domain/inputs.py`
- [ ] Classify each import: stdlib / domain-internal / app-shell / third-party
- [ ] Verify no Streamlit imports
- [ ] Verify no `app/` imports
- [ ] Verify no `tests/` imports
- [ ] Document any third-party dependencies required

### `domain/waterfall/waterfall_engine.py` → `finco_core/waterfall/`

- [ ] List all imports
- [ ] Classify: stdlib / finco_core-internal / shell dependency
- [ ] Verify no `app/waterfall_core.py` back-references
- [ ] Verify no `app/waterfall_runner.py` back-references
- [ ] Document `WaterfallPeriod` field inventory
- [ ] Confirm `cash_tax_bridge_reconciliation_keur` is present (Phase 0 Z2)
- [ ] Confirm no `cf_after_tax_keur` override exists in engine

### `domain/tax/` → `finco_core/tax/`

- [ ] List all imports across all files in `domain/tax/`
- [ ] Classify each
- [ ] Verify LCF: 5-year rolling, `expire_before_use=True`, Croatian §16
- [ ] Verify tax bridge formula: `EBITDA − tax_dep − deductible_interest + fiscal_reintegration` (Phase 0 Z1)
- [ ] Verify no identity guards remain

### `domain/shl/` → `finco_core/shl/`

- [ ] List all imports
- [ ] Verify no identity guards (`code == "TUHO-WIND-1"` pattern absent)
- [ ] Verify capability flag dispatch only (`use_shl_gross_accrued_for_pnl`, `use_tuho_shl_repayment_alignment`)
- [ ] Document SHL repayment alignment trigger conditions

### `domain/financing/` → `finco_core/debt/`

- [ ] List all imports
- [ ] Classify: stdlib / finco_core-internal / shell dependency
- [ ] Verify frozen DS fixture path dispatch is config-driven (`frozen_senior_ds_fixture_path`)
- [ ] Verify no `code == "TUHO-WIND-1"` or `code == "Oborovo"` guards

### `domain/depreciation/` → `finco_core/depreciation/`

- [ ] List all imports
- [ ] Verify book_dep and tax_dep are maintained separately
- [ ] Confirm tax bridge formula uses `tax_depreciation_keur`, not `book_depreciation_keur`

### `domain/sponsor/` → `finco_core/sponsor/`

- [ ] List all imports
- [ ] Verify XIRR/XNPV implementations are self-contained (no external solver dependency)
- [ ] Classify any third-party numeric dependencies

### `domain/returns/xirr.py`, `domain/returns/xnpv.py` → `finco_core/sponsor/`

- [ ] Confirm no external solver (scipy, numpy) required for base path
- [ ] If scipy is used, document and add to pyproject.toml dependencies

### `domain/construction/` → `finco_core/` (TBD placement)

- [ ] List all imports
- [ ] Classify

### `domain/period_engine.py` → `finco_core/` (TBD placement)

- [ ] List all imports
- [ ] Classify

### `app/waterfall_core.py` — Shell Only (NOT ported)

- [ ] Identify which functions are engine orchestration (port to `finco_core/engine/`)
- [ ] Identify which functions are shell wiring (discard)
- [ ] List all `app/waterfall_core.py` imports that are currently in `domain/`
- [ ] Confirm all identity guards are absent (Phase 0 Y3 — should be clean)

---

## Audit Categories

| Category | Action |
|----------|--------|
| **stdlib** | No action required |
| **finco_core-internal** | Import already ported or will be ported in same PR |
| **domain-internal** | Port the dependency before or in the same PR |
| **app-shell** | Must NOT enter finco_core — refactor or remove |
| **third-party (allowed)** | Add to `pyproject.toml` dependencies |
| **third-party (disallowed)** | Document and find stdlib alternative |
| **Streamlit** | Hard prohibited — must be eliminated before port |
| **tests/** | Hard prohibited — no runtime import from test tree |

---

## Shell Dependency Hunt

Before V2-3, perform a full search for hidden shell imports:

- [ ] `grep -r "import streamlit" domain/` — must return empty
- [ ] `grep -r "from app import" domain/` — classify each hit
- [ ] `grep -r "from tests import" domain/` — must return empty
- [ ] `grep -r "st\." domain/` — must return empty (Streamlit widget calls)
- [ ] `grep -r "session_state" domain/` — must return empty
- [ ] `grep -r "code == " app/waterfall_core.py` — must return empty (Phase 0 Y3 verified)

---

## Circular Import Check

After each extraction PR:

- [ ] Run `python -c "import finco_core"` — must succeed
- [ ] Run `python -c "import finco_core.engine"` — must succeed
- [ ] Verify `finco_core` does not import `finco_app`
- [ ] Verify `finco_core` does not import `finco_parity`
- [ ] Run `pydeps finco_core --noshow` (if installed) and inspect graph

---

## Notes

This document is a scaffold. Actual import listings will be populated during V2-3 execution. Each checklist item will be checked off and annotated with findings before the V2-3 PR is opened.

*Do not begin the import audit until V2-2 (Inputs) is merged.*
