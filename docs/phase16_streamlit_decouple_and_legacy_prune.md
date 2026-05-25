# Phase 16 Streamlit Decouple and Legacy Prune

## Summary

FincoGPT production is the FastAPI / HTMX application served as `main_web:app`.
This branch removes the accidental production boot dependency on Streamlit and
cleans up the most clearly dead Streamlit-era entrypoint shims.

## What Was Found

- Production service already runs `gunicorn main_web:app`.
- `app/cache.py` still imported `streamlit` at module import time and used
  `@st.cache_data`.
- That created a production boot risk because `main_web.py` could reach
  `app.cache` transitively even though Streamlit is not part of the intended
  production stack.
- README quickstart still told operators to run `streamlit run streamlit_app.py`.
- `src/app.py` and `src/startup.sh` were legacy Streamlit launcher shims with no
  role in the current deployment path.

## What Changed

### Production decouple

- `app/cache.py` now uses a local `cache_data(...)` decorator.
- If Streamlit is installed, the legacy shell can still use `st.cache_data`.
- If Streamlit is missing, `app/cache.py` falls back to a headless-safe cache
  wrapper with a compatible `.clear()` method.
- `main_web.py` no longer requires Streamlit to import successfully.

### Requirements cleanup

`requirements.txt` now reflects the current FastAPI runtime and import surface:

- `jinja2`
- `python-multipart`
- `itsdangerous`
- `bcrypt`
- `pandas`
- `openpyxl`
- `numpy`

`streamlit` was intentionally not added to production requirements.

### Legacy prune

Deleted as clearly dead launch shims:

- `src/app.py`
- `src/startup.sh`

Retained intentionally:

- `app/ui_runner.py`
- `app/waterfall_runner.py`
- `app/waterfall_core.py`
- `app/output_tables.py`

Retained as legacy-only for now:

- `streamlit_app.py`
- `ui/pages/1_Project_Inputs.py`
- `ui/pages/2_Waterfall.py`
- `docs/archive/legacy_ui/4_scenarios.py.txt`

Those files are not part of the current production boot path. They remain only
as legacy/reference material and should not be treated as the current app.

## Docs and Tests Updated

- README quickstart now points to `uvicorn main_web:app --reload` and
  production-style `gunicorn main_web:app`.
- Entry-point tests now assert that `main_web:app` is the production target.
- Import-guard tests now check that `app/cache.py` is Streamlit-optional rather
  than forbidding the compatibility import outright.
- New Phase 16 tests verify `app.cache` and `main_web` import without Streamlit.

## What This Branch Did Not Change

- No runtime/model formula changes
- No workbook calculation changes
- No export calculation changes
- No persistence authority changes
- No scenario workflow changes
- No JavaScript financial calculations

## Remaining Legacy Concerns

- Historical docs outside README still mention Streamlit and should be treated
  as archival context, not current operating guidance.
- `streamlit_app.py` and legacy `ui/pages` remain available as retained archive
  material and can be revisited in a future pruning pass once the team decides
  whether to delete or formally archive them elsewhere.
- Streamlit-style concepts may still appear in old architecture docs and
  reference-project cards. This branch does not rewrite all historical material.
