# Phase 36 - Legacy Streamlit Cleanup / Clean-Env CI

Base SHA: `a0d78ed946a7f51ffd534176e3320efe49c6d2b8`

## Purpose

Phase 36 removes clean-environment import blockers caused by legacy Streamlit
usage in modules that are still imported by the FastAPI/HTMX runtime path or by
pytest collection in a Streamlit-free environment.

## Files inspected

- `app/cache.py`
- `app/input_forms.py`
- `app/ui/components.py`
- `tests/test_input_forms.py`
- `tests/test_ui_components.py`
- `tests/test_runtime_import_guards.py`
- `requirements.txt`
- `pyproject.toml`

## Cleanup summary

- `app/cache.py`
  - retained headless-safe cache fallback behavior
  - removed direct Streamlit import statement
  - now resolves Streamlit through optional compatibility lookup only
- `app/input_forms.py`
  - removed direct Streamlit import statement
  - helper and override functions now import cleanly without Streamlit installed
  - render functions fail clearly only when the legacy Streamlit shell is
    actually invoked
- `app/ui/components.py`
  - removed direct Streamlit import statement
  - formatting helpers now import cleanly without Streamlit installed
  - rendering helpers require Streamlit only at call time
- `app/streamlit_compat.py`
  - added minimal optional-import helper so legacy UI modules can stay present
    without breaking clean-environment import or test collection
- `pyproject.toml`
  - removed legacy `streamlit` dependency entry

## Clean-env CI rationale

The application is now FastAPI/HTMX-oriented. Streamlit must not be required
just to import runtime modules or collect tests in CI. This cleanup keeps legacy
Streamlit UI code quarantined behind optional import helpers instead of making
Streamlit a production dependency.

## Dependency confirmation

- `streamlit` was **not** added to `requirements.txt`
- `streamlit` was removed from `pyproject.toml`
- `streamlit` was **not** added to `constraints.txt`

## Scope boundaries

- No financial formula changes
- No runtime calculation changes
- No model output changes
- No project factory changes
- No fixture CSV changes
- No Revenue/OPEX/CAPEX/Tax formula changes
- No senior debt / DSCR / SHL / distribution logic changes
- No JS financial calculations
- No schema migrations
- No generic path promotion
- No live sculpting promotion

## Non-claims

- No lender-ready claim
- No bank-ready claim
- No audit-ready claim
- No certification-ready claim
- No SaaS-ready claim

## Guardrails

- G20 remains BLOCKED
- R99/R102 remain NOT APPROVED
- `partial_pay_sweep` remains not promoted
- flat/min DSCR sculpting remains not promoted
- backend remains source of truth

## Remaining limitation

This phase does **not** remove all legacy Streamlit files from the repository.
It only removes or quarantines the import-time blockers that prevent clean-env
runtime import and pytest collection without Streamlit installed.

In the local validation environment, any remaining `pytest --collect-only`
errors after this cleanup are unrelated dependency gaps (`sqlalchemy`, `scipy`)
rather than `ModuleNotFoundError: streamlit`.

## Recommended next phase

Phase 37 - Pilot UX Walkthrough / Friction Audit
