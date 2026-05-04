# Phase 3 Roadmap

## Sponsor IRR Module
- **Objective:** Replace placeholder with real sponsor-level IRR using full project cash flow including sponsor equity injections and distributions
- **What to build:** sponsor cash flow schedule from project inputs, sponsor equity timeline, sponsor distribution logic
- **What NOT to build:** sponsor tax modeling, sponsor-specific debt sizing
- **Risks:** sponsor cash flow definition must match lender constraints; circular reference risk with distributions
- **Required tests:** `test_sponsor_irr_greater_than_project_irr`, `test_sponsor_irr_zero_if_no_equity`

## Portfolio v1 Hardening
- **Objective:** Make portfolio IRR production-ready for Solar+Wind pooled screening
- **What to build:** date-aligned XIRR, portfolio-level DSCR, per-project breakdown in Excel
- **What NOT to build:** portfolio scenarios, sponsor-level portfolio returns
- **Risks:** different tenor/per-project start dates cause misalignment; negative CFADS handling
- **Required tests:** `test_portfolio_cf_alignment`, `test_portfolio_irr_equals_weighted_average`

## BESS/Hybrid Implementation
- **Objective:** Complete battery revenue model + full waterfall integration
- **What to build:** BESS degradation model, BESS revenue stacking (energy + capacity market), BESS-specific capex items
- **What NOT to build:** hybrid optimization (when to charge/discharge), financial modeling of capacity contracts
- **Risks:** BESS degradation is non-linear; multiple revenue streams complicate tax
- **Required tests:** `test_bess_revenue_positive`, `test_bess_watermark_runs_without_error`

## Assumptions Registry
- **Objective:** Single source of truth for all model assumptions, editable via UI
- **What to build:** assumptions.yaml, UI form for assumptions, validation against registry
- **What NOT to build:** assumption propagation to all modules (keep existing inputs)
- **Risks:** breaking existing input flow; version mismatch between registry and model
- **Required tests:** `test_assumptions_load`, `test_assumptions_override_applies`

## Run/Version Persistence
- **Objective:** Store model runs with version info for audit trail
- **What to build:** run history table (SQLite), model version tracking, run comparison view
- **What NOT to build:** full version control; git-based comparison
- **Risks:** SQLite file locked on concurrent access; large run history
- **Required tests:** `test_run_history_saved`, `test_run_version_recorded`

## Deployment/Productization
- **Objective:** Make Finco1 runnable without dev environment
- **What to build:** Docker container, requirements.txt, setup.py, single-command launch
- **What NOT to build:** multi-tenant deployment, cloud hosting, user auth
- **Risks:** platform-specific dependencies (openpyxl, streamlit)
- **Required tests:** `test_docker_build_succeeds`, `test_streamlit_launches`