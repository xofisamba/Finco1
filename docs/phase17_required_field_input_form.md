# Phase 17B Required Field Input Form

Phase 17B adds required input capture and validation for user-created projects.

What this phase adds:
- New Project now captures the minimum required modelling assumptions.
- Those assumptions are validated on create and persisted in `baseline_snapshot`.
- Phase 17B persists user assumptions in baseline_snapshot.
- The created project reloads with the captured values visible in the workspace form.
- The project selector still separates factory templates from user-created projects.

What this phase does not change:
- Phase 17B still uses template-seeded runtime.
- Phase 17B does not add a true from-scratch runtime path.
- No runtime/model formulas changed.
- No workbook calculations changed.
- No export calculation logic changed.
- No scenario compare semantics changed.

Required-field interpretation:
- `project_name` and `project_type` remain project metadata.
- The modelling-input layer is the required assumption set stored in `baseline_snapshot`:
  - `country_market`
  - `capacity_mw`
  - `cod_date`
  - `construction_months`
  - `horizon_years`
  - `tariff_eur_mwh`
  - `ppa_term_years`
  - `p50_hours`
  - `opex_y1_keur`
  - `total_capex_keur`
  - `gearing_pct`
  - `interest_rate_pct`
  - `tenor_years`
- `target_dscr` is also captured explicitly in Phase 17B because the current runtime override path already depends on it.

Persistence posture:
- `baseline_snapshot` now stores:
  - project metadata
  - project origin / template source
  - the required assumptions above
  - `target_dscr`
- That snapshot is used to populate the workspace after reload.

Runtime posture:
- Phase 17B persists user assumptions in `baseline_snapshot`.
- Phase 17B still uses template-seeded runtime.
- The current override path can already use:
  - `capacity_mw`
  - `tariff_eur_mwh`
  - `p50_hours`
  - `opex_y1_keur`
  - `gearing_pct`
  - `interest_rate_pct`
  - `tenor_years`
  - `target_dscr`
- Other captured fields are saved and shown in the UI now, but remain only partially runtime-bound until Phase 17C.

Disclosure kept visible in UI:
- Runtime remains template-seeded until Phase 17C from-scratch runtime path.

Factory-template posture:
- TUHO and Oborovo remain templates.
- User-created projects may be seeded from:
  - Generic Wind
  - Generic Solar
  - TUHO
  - Oborovo
- User-entered required fields override the seed inside `baseline_snapshot` and the workspace UI.

Next steps:
- Phase 17C will add true build_projectinputs_from_scratch.

Guardrails unchanged:
- Save does not auto-run.
- Run does not auto-save.
- Frontend/browser state does not become runtime authority.
- G20 remains BLOCKED.
- R99/R102 remain NOT APPROVED.
