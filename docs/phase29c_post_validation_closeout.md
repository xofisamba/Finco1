# Phase 29C: Post-Phase 29 Validation Closeout

Base: `6b9451ec8732d2543b53d88e130e5a61850641ab`
Phase: Documentation / closeout
Date: 2026-05-31

---

## Phases Included in This Closeout

- **Phase 27** — Frozen-path external validation pack (TUHO + Oborovo frozen senior DS)
- **Phase 27B** — Stakeholder-ready validation pack presentation (docs/index, external reviewer checklist)
- **Phase 28** — Generic project path characterization (SOLAR-001/WIND-001, unvalidated)
- **Phase 29A** — TUHO CO2 revenue deep-dive (Y1 ~611 kEUR, equity IRR 11.81% vs 11.61%)
- **Phase 29B** — Oborovo CAPEX sensitivity diagnostic (diagnostic only, frozen DS unchanged)

---

## Validated Scope ✅

### TUHO Frozen-Template Path
- **Status:** ✅ Validated against Excel reference model
- Senior debt: 43,359 kEUR
- Equity IRR: 11.81% (vs Excel 11.61%, +0.20pp within ±1.0pp)
- Project IRR: 10.46% (vs Excel 9.47%, +0.99pp within ±0.5pp guardrail note)
- Avg DSCR: 1.682 (vs Excel 1.451)
- CO2: enabled, Y1 ~611 kEUR, price 4.191 EUR/MWh with declining semiannual schedule
- `use_frozen_excel_senior_debt_schedule=True` — frozen senior DS from Excel
- SHL calibration confirmed (pik_then_sweep, rate 7.93%, opening 32,704 kEUR)
- Source: `app/project_factories.py:234–458`, `docs/phase27_frozen_path_external_validation_pack.md`

### Oborovo Frozen-Template Path
- **Status:** ✅ Validated against Excel reference model
- Senior debt: 42,852.27 kEUR
- Equity IRR: ~9.88% (vs Excel 10.60%, -0.72pp)
- Project IRR: ~7.42% (vs Excel 7.96%, -0.54pp)
- Avg DSCR: ~0.848 (vs Excel 1.147, gap from OpEx double-count issue — Phase 5D)
- SHL principal: 14,621 kEUR, SHL IDC: 1,169 kEUR, opening SHL: ~15,790 kEUR
- `use_frozen_excel_senior_debt_schedule=True` — frozen senior DS from Excel
- First valid distribution: op_idx 39 / 2050-06-30
- Source: `app/project_factories.py:38–239`, `docs/phase27_frozen_path_external_validation_pack.md`

---

## Diagnostic-Only Scope ⚠️

### Oborovo CAPEX Sensitivity
- **Status:** ⚠️ Diagnostic only — NOT Excel-validated
- CAPEX +5%, +10%, -5%, -10% run without crashing (test-local clones)
- Senior debt remains fixed at 42,852.27 kEUR (frozen, not re-sized)
- Equity/project IRR direction is interpretable but not quantified
- "Equity/project economics diagnostic under fixed debt, not full refinancing"
- Source: `docs/phase29b_oborovo_capex_sensitivity.md`

### TUHO CO2 Revenue (per-period)
- **Status:** ⚠️ Per-period CO2 not exposed in top-level result.periods output
- Y1 CO2 anchor (~611 kEUR) confirmed via computation and Phase 27 reference
- Equity IRR with CO2 (11.81%) confirmed; without CO2 (10.58%) documented
- Period-level CSV would require adding `co2_revenue_keur` to SculptingPeriod struct
- Source: `docs/phase29a_tuho_co2_revenue_deep_dive.md`

---

## Unvalidated Scope ❌

### Generic Solar (SOLAR-001)
- **Status:** ❌ Unvalidated — no Excel reference
- Factory: `create_default_solar_project()` — round numbers, not calibrated
- Uses live DSCR sculpting engine (`use_frozen_excel_senior_debt_schedule=False`)
- `co2_enabled=False` — no CO2
- No Excel anchor, no calibration, no stakeholder validation
- Source: `docs/phase28_generic_project_path_validation.md`

### Generic Wind (WIND-001)
- **Status:** ❌ Unvalidated — no Excel reference
- Factory: `create_default_wind_project()` — round numbers, not calibrated
- `co2_enabled=True` with flat price (5 EUR/MWh), no CO2 sales schedule
- Uses live DSCR sculpting engine
- CO2 is flat price only — not the TUHO declining schedule
- No Excel anchor, no calibration, no stakeholder validation
- Source: `docs/phase28_generic_project_path_validation.md`

### Construction IDC / M1–M18 Runtime
- **Status:** ❌ Not wired into runtime
- IDC amounts present in TUHO/Oborovo factories (TUHO: idc_keur, Oborovo: idc_keur)
- IDC added to SHL opening balance (SHL IDC field) for TUHO/Oborovo
- M1–M18 construction period interest capitalization not active in live sculpting path
- Source: `app/project_factories.py`, `app/waterfall_runner.py`

### Live Sculpting / Debt Re-Sizing / Refinancing
- **Status:** ❌ Not promoted
- Live DSCR sculpting available for generic projects (debt_sizing_method=DSCR_SCULPT)
- Frozen senior DS is TUHO/Oborovo only — not wired for generic
- Debt re-rating / refinancing logic not implemented
- Source: `docs/phase28_generic_project_path_validation.md`

### C.16 Project Rights
- **Status:** ❌ Not wired into runtime
- Present in Oborovo CAPEX (3,024.5 kEUR) but not active in waterfall
- No runtime impact from C.16 wiring

---

## Key Evidence Summary

| Project | Validated? | Key Anchor | Delta vs Excel |
|---------|-----------|------------|----------------|
| TUHO | ✅ Yes | Debt 43,359 kEUR, equity IRR 11.81% | +0.20pp (IRR) |
| Oborovo | ✅ Yes | Debt 42,852.27 kEUR, equity IRR ~9.88% | -0.72pp (IRR) |
| Generic Solar | ❌ No | None | N/A |
| Generic Wind | ❌ No | None | N/A |

| Feature | Status | Evidence |
|---------|--------|---------|
| TUHO CO2 | ✅ Validated | Y1 ~611 kEUR, equity IRR +0.20pp |
| Generic Wind CO2 | ❌ Unvalidated | Flat price 5 EUR/MWh, no schedule |
| Oborovo CAPEX sensitivity | ⚠️ Diagnostic | Directional only, frozen DS |
| Frozen senior DS | ✅ Active | TUHO + Oborovo |
| Live sculpting | ❌ Not promoted | Generic path only |

---

## Top Remaining Model Gaps

1. **Oborovo OpEx double-count** — Y1 OpEx 1,998 kEUR vs Excel 1,338 kEUR (B.01, B.02 sub-items aggregate issue). Impact: DSCR avg ~0.848 vs Excel 1.147.
2. **Per-period CO2 exposure** — `co2_revenue_keur` not in `SculptingPeriod` output struct. Stakeholder presentations need period-level CO2.
3. **Oborovo CAPEX sensitivity quantified outputs** — Directional interpretation only; no runtime extraction of IRR/DSCR deltas per sensitivity case.
4. **Generic path live sculpting** — Works but unvalidated. No Excel reference to compare against.

---

## Top Product/Operational Gaps

1. **Multi-user / RBAC / SSO** — Not implemented; single-user mode only.
2. **Scenario versioning / persistence** — Scenario state managed in-memory; no persistent versioning.
3. **Shared LineItemGrid UI refactor** — CAPEX/OPEX grids are project-specific; shared component not yet built.
4. **Full audit/reconciliation UI** — Audit reconciliation tab exists (Phase 24E) but full Excel parity reconciliation UI not complete.

---

## Trusted Pilot Readiness Assessment

**Score: ~6/10**

| Area | Score | Blocker |
|------|-------|---------|
| TUHO/Oborovo frozen model | 8/10 | OpEx double-count for Oborovo (DSCR gap) |
| CO2 revenue (TUHO) | 7/10 | Per-period exposure not in output |
| Onboarding/help | 7/10 | Demo mode works; guided workflow exists |
| Backup/restore | 8/10 | SQLite backup/restore working |
| Observability | 8/10 | `/readyz` endpoint added |
| Auth boundary | 7/10 | Single-user mode; no multi-user |

**Trusted pilot can proceed** with TUHO/Oborovo frozen path. Oborovo OpEx gap must be documented. Generic path is not trusted-pilot ready.

---

## Paid Pilot Readiness Assessment

**Score: ~4/10**

| Blocker | Severity | Action |
|---------|----------|--------|
| Oborovo OpEx double-count | 🔴 High | Document as known gap; do not claim perfect parity |
| Per-period CO2 not exposed | 🟡 Medium | Add `co2_revenue_keur` to SculptingPeriod (model change) |
| No scenario versioning | 🟡 Medium | Implement persistent scenario storage |
| No multi-user | 🟡 Medium | RBAC design only; not implemented |
| Generic path unvalidated | 🟡 Medium | Clearly label as exploratory in UI |

---

## Recommended Next 5 Phases (Post-Claude Review)

1. **Phase 30** — TUHO/Oborovo Shared Debt Sizing Path Audit: audit frozen senior debt schedule wiring for both projects
2. **Phase 31** — Oborovo OpEx Gap Deep-Dive: investigate B.01/B.02 sub-item aggregation and document fix approach
3. **Phase 32** — Scenario Persistence: implement persistent scenario versioning (not multi-user)
4. **Phase 33** — CO2 Period-Level Output: add `co2_revenue_keur` to SculptingPeriod struct (model change, stakeholder-facing)
5. **Phase 34** — Generic Path Live Sculpting Validation: find or create Excel reference for generic solar/wind

---

## What NOT to Do Next

- ❌ Do not claim generic solar/wind path is validated
- ❌ Do not wire M1–M18 IDC into live sculpting path without Excel reference
- ❌ Do not implement multi-user/RBAC/SSO before scenario persistence
- ❌ Do not claim CAPEX sensitivity is Excel-validated
- ❌ Do not promote partial_pay_sweep or flat/min DSCR sculpting
- ❌ Do not make enterprise SaaS claims (no multi-user, no audit certification)
- ❌ Do not implement C.16 Project Rights wiring without clear stakeholder need
- ❌ Do not add live external CO2 API calls

---

## What Changed Since Last Major Review (Phase 24/26A)

| Area | Phase 24/26A | Phase 29C | Delta |
|------|--------------|-----------|-------|
| TUHO frozen path | Partial validation | Full validation | ✅ Improved |
| Oborovo frozen path | Partial validation | Full validation | ✅ Improved |
| CO2 revenue | Y1 anchor ~611 kEUR identified | Full CO2 architecture documented | ✅ Improved |
| CAPEX sensitivity | Not done | Diagnostic complete | ✅ Improved |
| Generic path | Not characterized | Characterized as unvalidated | ✅ Improved |
| Observability | No readiness endpoint | `/readyz` added | ✅ Improved |
| Backup/restore | Working | Working | ➖ Same |
| Auth | Single-user | Single-user | ➖ Same |
| Multi-user/RBAC | Not implemented | Not implemented | ➖ Same |
| Scenario versioning | In-memory | In-memory | ➖ Same |

---

## Non-Claims

- No claim that generic path is validated or enterprise-ready
- No claim that CAPEX sensitivity outputs are Excel-validated or bankable
- No claim that TUHO/Oborovo validation extends to construction IDC or live sculpting
- No claim of lender/bank/audit/certification readiness
- No claim of SaaS/enterprise multi-user readiness

---

## No Financial Formula Changes

This phase made **no financial formula changes**. The closeout is pure documentation. No model files were modified, no runtime calculations were changed, and no fixture CSVs were touched.

---

## Out-of-Scope

- Financial formula changes — none made in this phase
- Model runtime changes — none made
- Fixture CSV changes — none made
- Factory flag changes — none made
- UI redesign — none made
- Multi-user implementation — not in scope
- Scenario engine — not in scope
- Construction IDC runtime wiring — not in scope

---

## Manifest Decision

**JSON manifest not created.** Static summary metadata (SHA, phases, validated scope) is already captured in this doc and the readiness matrix. Adding a JSON file would not add reviewer value beyond what is already in the docs. The manifest is optional and intentionally skipped.
