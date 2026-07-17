# Phase 2A — Reuse Inventory

Base SHA: `f23030cf8fc28d2c17f49540af0b1dbfc38f3a7c`

---

## Required Schedules

| Schedule | Production Owner | Candidate Reusable Leaf | Input Type | Output Type | Identity-Blind | Pure | Reused Directly | Reason if Not |
|---|---|---|---|---|---|---|---|---|
| Period grid | `finco_core.engine.period_engine.PeriodEngine` | `PeriodEngine(fc, construction_months, horizon_years, ppa_years, frequency).periods()` | `date, int, int, int, PeriodFrequency` | `List[PeriodMeta]` | Yes | Yes | Yes | — |
| Production | `finco_core.revenue.generation.full_generation_schedule` | `full_generation_schedule(inputs: ProjectInputs, engine: PeriodEngine)` | `ProjectInputs, PeriodEngine` | `dict[int, float]` | Yes | Yes | Yes | — |
| Revenue total | `finco_core.revenue.generation.full_revenue_schedule` | `full_revenue_schedule(inputs: ProjectInputs, engine: PeriodEngine)` | `ProjectInputs, PeriodEngine` | `dict[int, float]` | Yes | Yes | Yes | — |
| Revenue decomposition | `finco_core.revenue.generation.revenue_decomposition_schedule` | `revenue_decomposition_schedule(inputs, engine)` | `ProjectInputs, PeriodEngine` | `dict[int, dict[str, float\|bool]]` | Yes | Yes | Yes | — |
| OPEX total | `finco_core.opex.projections.opex_schedule_period` | `opex_schedule_period(inputs: ProjectInputs, engine)` | `ProjectInputs, PeriodEngine` | `dict[int, float]` | Yes | Yes | Yes | — |
| OPEX line schedule | `finco_core.opex.projections.opex_breakdown_year` | `opex_breakdown_year(inputs, year_index)` per year | `ProjectInputs, int` | `dict[str, float]` | Yes | Yes | Yes | — |
| EBITDA | Assembled by orchestrator | `revenue_keur - opex_keur` per period | Derived | `dict[int, float]` | Yes | Yes | N/A | Simple arithmetic assembled by orchestrator |
| Book depreciation | `finco_core.depreciation.engine.DepreciationEngine.compute` | `DepreciationEngine.compute(DepreciationEngineInputs(...))` | `DepreciationEngineInputs` | `DepreciationEngineResult` | Yes* | Yes | Yes | *`project_name` stored verbatim, not dispatched on |
| Tax depreciation | `finco_core.depreciation.engine.DepreciationEngine.compute` | Same engine; `.total_tax_depreciation_keur` per period | `DepreciationEngineInputs` | `DepreciationEngineResult` | Yes* | Yes | Yes | — |

---

## Modules Not Reused in Phase 2A

| Module | Reason |
|---|---|
| `app.waterfall_core.run_waterfall_v3_core` | Orchestrator with TUHO-named parameters, CSV reads, conditional domain.* imports, identity-aware flag dispatch |
| `finco_core.engine.distribution_account.*` | Explicit `is_tuho`/`is_oborovo` fields; distribution gate is out of Phase 2A scope |
| `finco_core.shl.*` | SHL out of Phase 2A scope |
| `finco_core.sponsor.*` | Returns/waterfall out of Phase 2A scope |
| `finco_core.financial_statements.*` | Financial statements out of Phase 2A scope |
| `finco_core.debt.*` (except `depreciation_schedule`) | Senior debt out of Phase 2A scope |
| `app.opex_engine.build_opex_line_items_from_defaults` | Technology-type dispatch; not used — opex items come from `ProjectInputs.opex` already |

---

## `ProjectInputs` Fields Ignored by Phase 2A Adapter

Fields present in `ProjectInputs` that are mathematically unnecessary for the Phase 2A operating core and therefore ignored by the adapter:

| Field | Reason Ignored |
|---|---|
| `info.use_opex_line_item_engine` | Feature flag for legacy alternate OPEX path; adapter uses canonical `finco_core.opex.projections` directly |
| `info.use_construction_schedule_engine` | CapEx construction schedule not in Phase 2A scope |
| `info.use_senior_rate_schedule_engine` | Debt rate scheduling not in Phase 2A scope |
| `info.use_senior_sculpting_basis_engine` | Debt sizing not in Phase 2A scope |
| `info.use_shl_fcf_waterfall_engine` | SHL waterfall not in Phase 2A scope |
| `info.use_shl_canonical_engine` | SHL not in Phase 2A scope |
| `info.use_canonical_tax_depreciation_bridge` | Handled directly by `DepreciationEngine` |
| `info.use_depreciation_canonical_engine` | Always True in Phase 2A |
| `info.use_tax_bridge_engine` | Tax bridge not in Phase 2A scope |
| `info.use_senior_debt_sizing_engine` | Debt sizing not in Phase 2A scope |
| `info.use_shl_gross_accrued_for_pnl` | SHL not in Phase 2A scope |
| `info.use_book_depreciation_for_pnl` | Financial statements not in Phase 2A scope |
| `financing.*` | All financing assumptions; debt, SHL, DSRA out of Phase 2A scope |
| `tax.*` | Tax parameters; tax calculation out of Phase 2A scope |
| `technical.bess_enabled`, `technical.bess` | BESS not in Phase 2A scope |

---

## Limitations

This inventory documents what can be reused for the Phase 2A operating core.
Tax, CFADS, financing, waterfall, financial statements and returns are out of scope.
