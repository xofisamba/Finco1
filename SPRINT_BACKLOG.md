# Sprint 2 — Arhitekturalni Decoupling

## Cilj
Domain layer nema Streamlit imports (@st.cache_data, @st.cache, streamlit import).
Sve Streamlit-specific stvari idu isključivo u app/ layer.

## Preduvjeti (done: S1-1 do S1-5

## S2-1 (DONE in previous msg — app/cache.py, app/waterfall_runner.py

## S2-3 — Session State Schema

**Task:** Clean session state management

**Acceptance criteria:**
- Session state fields documented
- No implicit streamlit imports in domain

## S2-4 — Fix S2 tests

**Task:** TestS2Architecture - fix imports and run

**Acceptance criteria:**
- S2 tests pass
